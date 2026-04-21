"""Shadow canônico do bootstrap do portal admin-cliente."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domains.chat.laudo_state_helpers import (
    laudo_permite_reabrir,
    laudo_tem_interacao,
    obter_estado_api_laudo,
    obter_status_card_laudo,
    serializar_card_laudo,
)
from app.domains.admin.services import get_support_exceptional_policy_snapshot
from app.shared.database import Empresa, Laudo, Usuario
from app.shared.tenant_admin_policy import (
    summarize_tenant_admin_policy,
    tenant_admin_user_occupies_operational_slot,
)
from app.v2.acl import build_technical_case_snapshot_for_user
from app.v2.adapters.tenant_admin_bootstrap import build_tenant_admin_bootstrap_shadow_result
from app.v2.contracts.tenant_admin import (
    TenantAdminVisibilityPolicyPayload,
    build_tenant_admin_view_projection,
)
from app.v2.runtime import (
    actor_role_from_user,
    v2_case_core_acl_enabled,
    v2_tenant_admin_projection_enabled,
)


def _safe_int_optional(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float, str, bytes, bytearray)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _legacy_case_payload_for_tenant_admin(
    banco: Session,
    laudo: Laudo,
) -> dict[str, Any]:
    status_card = obter_status_card_laudo(banco, laudo)
    return {
        "estado": obter_estado_api_laudo(banco, laudo),
        "laudo_id": int(laudo.id),
        "status_card": status_card,
        "permite_reabrir": laudo_permite_reabrir(banco, laudo),
        "tem_interacao": laudo_tem_interacao(banco, int(laudo.id)),
        "laudo_card": serializar_card_laudo(banco, laudo) if status_card != "oculto" else None,
    }


def _build_case_snapshots_for_tenant_admin(
    *,
    banco: Session,
    usuario: Usuario,
) -> list[Any]:
    laudos = list(
        banco.scalars(
            select(Laudo)
            .options(selectinload(Laudo.revisoes))
            .where(Laudo.empresa_id == usuario.empresa_id)
            .order_by(func.coalesce(Laudo.atualizado_em, Laudo.criado_em).desc(), Laudo.id.desc())
        ).all()
    )
    return [
        build_technical_case_snapshot_for_user(
            usuario=usuario,
            legacy_payload=_legacy_case_payload_for_tenant_admin(banco, laudo),
            laudo=laudo,
            source_channel="admin_cliente_bootstrap",
        )
        for laudo in laudos
    ]


def _resolve_tenant_admin_projection_timestamp(case_snapshots: list[Any]) -> datetime:
    def _normalize_observed_datetime(value: Any) -> datetime | None:
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    observed_datetimes = [
        normalized
        for snapshot in case_snapshots
        for normalized in (
            _normalize_observed_datetime(getattr(snapshot, "updated_at", None)),
            _normalize_observed_datetime(getattr(snapshot, "created_at", None)),
        )
        if normalized is not None
    ]
    if observed_datetimes:
        return max(observed_datetimes)
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def build_tenant_admin_projection_for_bootstrap(
    *,
    banco: Session,
    usuario: Usuario,
    empresa_summary: dict[str, Any],
    usuarios: list[Usuario],
):
    support_policy = get_support_exceptional_policy_snapshot(banco)
    empresa = banco.get(Empresa, int(usuario.empresa_id))
    tenant_admin_policy = summarize_tenant_admin_policy(
        getattr(empresa, "admin_cliente_policy_json", None)
    )
    operational_identity_slots_in_use = sum(
        1
        for item in usuarios
        if tenant_admin_user_occupies_operational_slot(
            getattr(empresa, "admin_cliente_policy_json", None),
            access_level=getattr(item, "nivel_acesso", None),
            stored_portals=getattr(item, "allowed_portals", ()),
        )
    )
    contract_operational_user_limit = tenant_admin_policy[
        "contract_operational_user_limit"
    ]
    case_snapshots = _build_case_snapshots_for_tenant_admin(
        banco=banco,
        usuario=usuario,
    )
    projection = build_tenant_admin_view_projection(
        tenant_id=empresa_summary.get("id"),
        tenant_name=empresa_summary.get("nome_fantasia"),
        tenant_status="blocked" if bool(empresa_summary.get("status_bloqueio")) else "active",
        case_snapshots=case_snapshots,
        plan_name=empresa_summary.get("plano_ativo"),
        usage_status=empresa_summary.get("capacidade_status"),
        usage_percent=_safe_int_optional(empresa_summary.get("uso_percentual")),
        recommended_plan=empresa_summary.get("plano_sugerido"),
        total_users=int(empresa_summary.get("total_usuarios") or 0),
        active_users=sum(1 for item in usuarios if bool(getattr(item, "ativo", False))),
        inspectors=int(empresa_summary.get("inspetores") or 0),
        reviewers=int(empresa_summary.get("revisores") or 0),
        admin_clients=int(empresa_summary.get("admins_cliente") or 0),
        actor_id=usuario.id,
        actor_role=actor_role_from_user(usuario),
        source_channel="admin_cliente_bootstrap",
        visibility_policy=TenantAdminVisibilityPolicyPayload(
            technical_access_mode="surface_scoped_operational",
            commercial_operating_model=str(tenant_admin_policy["operating_model"]),
            mobile_primary=bool(tenant_admin_policy["mobile_primary"]),
            contract_operational_user_limit=tenant_admin_policy[
                "contract_operational_user_limit"
            ],
            shared_mobile_operator_enabled=bool(
                tenant_admin_policy["shared_mobile_operator_enabled"]
            ),
            shared_mobile_operator_web_inspector_enabled=bool(
                tenant_admin_policy["shared_mobile_operator_web_inspector_enabled"]
            ),
            shared_mobile_operator_web_review_enabled=bool(
                tenant_admin_policy["shared_mobile_operator_web_review_enabled"]
            ),
            shared_mobile_operator_surface_set=list(
                tenant_admin_policy["shared_mobile_operator_surface_set"]
            ),
            operational_user_cross_portal_enabled=bool(
                tenant_admin_policy["operational_user_cross_portal_enabled"]
            ),
            operational_user_admin_portal_enabled=bool(
                tenant_admin_policy["operational_user_admin_portal_enabled"]
            ),
            tenant_assignable_portal_set=list(
                tenant_admin_policy["tenant_assignable_portal_set"]
            ),
            commercial_package_scope=str(
                tenant_admin_policy["commercial_package_scope"]
            ),
            commercial_capability_axes=list(
                tenant_admin_policy["commercial_capability_axes"]
            ),
            cross_surface_session_strategy=str(
                tenant_admin_policy["cross_surface_session_strategy"]
            ),
            cross_surface_session_unified=bool(
                tenant_admin_policy["cross_surface_session_unified"]
            ),
            cross_surface_session_note=str(
                tenant_admin_policy["cross_surface_session_note"]
            ),
            operational_identity_slots_in_use=int(operational_identity_slots_in_use),
            operational_identity_slots_remaining=(
                max(int(contract_operational_user_limit) - int(operational_identity_slots_in_use), 0)
                if isinstance(contract_operational_user_limit, int)
                else None
            ),
            admin_client_case_visibility_mode=str(
                tenant_admin_policy["case_visibility_mode"]
            ),
            admin_client_case_action_mode=str(
                tenant_admin_policy["case_action_mode"]
            ),
            case_list_visible=bool(tenant_admin_policy["case_list_visible"]),
            case_actions_enabled=bool(tenant_admin_policy["case_actions_enabled"]),
            exceptional_support_access=str(support_policy["mode"]),
            exceptional_support_scope_level=str(support_policy["scope_level"]),
            support_exceptional_protocol=str(
                tenant_admin_policy["support_exceptional_protocol"]
            ),
            exceptional_support_step_up_required=bool(support_policy["step_up_required"]),
            exceptional_support_approval_required=bool(support_policy["approval_required"]),
            exceptional_support_justification_required=bool(support_policy["justification_required"]),
            exceptional_support_max_duration_minutes=int(support_policy["max_duration_minutes"]),
            tenant_retention_policy_owner=str(
                tenant_admin_policy["tenant_retention_policy_owner"]
            ),
            technical_case_retention_min_days=int(
                tenant_admin_policy["technical_case_retention_min_days"]
            ),
            issued_document_retention_min_days=int(
                tenant_admin_policy["issued_document_retention_min_days"]
            ),
            audit_retention_min_days=int(
                tenant_admin_policy["audit_retention_min_days"]
            ),
            human_signoff_required=bool(
                tenant_admin_policy["human_signoff_required"]
            ),
            ai_assistance_audit_required=bool(
                tenant_admin_policy["ai_assistance_audit_required"]
            ),
            human_override_justification_required=bool(
                tenant_admin_policy["human_override_justification_required"]
            ),
            consent_collection_mode=str(
                tenant_admin_policy["consent_collection_mode"]
            ),
            mandatory_audit_fields=list(
                tenant_admin_policy["mandatory_audit_fields"]
            ),
            audit_scope="tenant_operational_timeline",
            audit_categories_visible=["access", "commercial", "team", "support", "chat", "mesa"],
        ),
        correlation_id=f"tenant-admin-bootstrap:{usuario.empresa_id}",
        idempotency_key=f"tenant-admin-bootstrap:{usuario.empresa_id}",
        timestamp=_resolve_tenant_admin_projection_timestamp(case_snapshots),
    )
    return projection, case_snapshots


def registrar_shadow_tenant_admin_bootstrap(
    *,
    request: Request,
    banco: Session,
    usuario: Usuario,
    empresa_summary: dict[str, Any],
    usuarios: list[Usuario],
    payload_publico: dict[str, Any],
) -> None:
    if not (v2_case_core_acl_enabled() and v2_tenant_admin_projection_enabled()):
        return

    projection, case_snapshots = build_tenant_admin_projection_for_bootstrap(
        banco=banco,
        usuario=usuario,
        empresa_summary=empresa_summary,
        usuarios=usuarios,
    )
    resultado = build_tenant_admin_bootstrap_shadow_result(
        tenant_id=empresa_summary.get("id"),
        tenant_name=empresa_summary.get("nome_fantasia"),
        tenant_status="blocked" if bool(empresa_summary.get("status_bloqueio")) else "active",
        case_snapshots=case_snapshots,
        plan_name=empresa_summary.get("plano_ativo"),
        usage_status=empresa_summary.get("capacidade_status"),
        usage_percent=_safe_int_optional(empresa_summary.get("uso_percentual")),
        recommended_plan=empresa_summary.get("plano_sugerido"),
        total_users=int(empresa_summary.get("total_usuarios") or 0),
        active_users=sum(1 for item in usuarios if bool(getattr(item, "ativo", False))),
        inspectors=int(empresa_summary.get("inspetores") or 0),
        reviewers=int(empresa_summary.get("revisores") or 0),
        admin_clients=int(empresa_summary.get("admins_cliente") or 0),
        actor_id=usuario.id,
        actor_role=actor_role_from_user(usuario),
        source_channel="admin_cliente_bootstrap",
        legacy_bootstrap_payload=payload_publico,
    )
    resultado.projection = projection.model_dump(mode="json")
    request.state.v2_tenant_admin_projection_result = resultado.model_dump(mode="python")


__all__ = [
    "build_tenant_admin_projection_for_bootstrap",
    "registrar_shadow_tenant_admin_bootstrap",
]
