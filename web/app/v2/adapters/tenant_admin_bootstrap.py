"""Adapter incremental do tenant admin view para o bootstrap legado do portal cliente."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.acl.technical_case_snapshot import TechnicalCaseSnapshotV1
from app.v2.contracts.tenant_admin import build_tenant_admin_view_projection


class TenantAdminBootstrapShadowResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["TenantAdminBootstrapShadowResultV1"] = "TenantAdminBootstrapShadowResultV1"
    contract_version: str = "v1"
    compatible: bool
    divergences: list[str] = Field(default_factory=list)
    used_projection: bool = True
    delivery_mode: Literal["shadow_only"] = "shadow_only"
    observed_case_count: int = 0
    projection: dict[str, Any]


def _normalize_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _dict_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def build_tenant_admin_bootstrap_shadow_result(
    *,
    tenant_id: Any,
    tenant_name: Any,
    tenant_status: Any,
    case_snapshots: Iterable[TechnicalCaseSnapshotV1],
    plan_name: Any,
    usage_status: Any,
    usage_percent: int | None,
    recommended_plan: Any,
    total_users: int,
    active_users: int,
    inspectors: int,
    reviewers: int,
    admin_clients: int,
    actor_id: Any,
    actor_role: str,
    source_channel: str,
    legacy_bootstrap_payload: dict[str, Any],
    correlation_id: str | None = None,
    timestamp: datetime | None = None,
) -> TenantAdminBootstrapShadowResult:
    snapshots = list(case_snapshots)
    projection = build_tenant_admin_view_projection(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        tenant_status=tenant_status,
        case_snapshots=snapshots,
        plan_name=plan_name,
        usage_status=usage_status,
        usage_percent=usage_percent,
        recommended_plan=recommended_plan,
        total_users=total_users,
        active_users=active_users,
        inspectors=inspectors,
        reviewers=reviewers,
        admin_clients=admin_clients,
        actor_id=actor_id,
        actor_role=actor_role,
        source_channel=source_channel,
        correlation_id=correlation_id,
        timestamp=timestamp,
    )
    projection_payload = projection.payload
    legacy_empresa = _dict_payload(legacy_bootstrap_payload.get("empresa"))
    legacy_saude_operacional = _dict_payload(legacy_empresa.get("saude_operacional"))
    legacy_usuarios = legacy_bootstrap_payload.get("usuarios")
    legacy_users = legacy_usuarios if isinstance(legacy_usuarios, list) else []
    tenant_summary = _dict_payload(projection_payload.get("tenant_summary"))
    case_counts = _dict_payload(projection_payload.get("case_counts"))
    user_summary = _dict_payload(projection_payload.get("user_summary"))

    divergences: list[str] = []
    if str(tenant_summary.get("tenant_id") or "") != str(
        legacy_empresa.get("id") or ""
    ):
        divergences.append("tenant_id")
    if str(tenant_summary.get("tenant_name") or "") != str(
        legacy_empresa.get("nome_fantasia") or ""
    ):
        divergences.append("tenant_name")
    if _normalize_int(case_counts.get("total_cases")) != _normalize_int(
        legacy_empresa.get("total_laudos")
    ):
        divergences.append("total_cases")
    if _normalize_int(user_summary.get("total_users")) != _normalize_int(
        legacy_empresa.get("total_usuarios")
    ):
        divergences.append("total_users")
    legacy_active_users = legacy_saude_operacional.get("usuarios_ativos_total")
    if legacy_active_users is None:
        legacy_active_users = sum(1 for item in legacy_users if bool(item.get("ativo")))

    if _normalize_int(user_summary.get("active_users")) != _normalize_int(
        legacy_active_users
    ):
        divergences.append("active_users")

    return TenantAdminBootstrapShadowResult(
        compatible=not divergences,
        divergences=divergences,
        observed_case_count=len(snapshots),
        projection=projection.model_dump(mode="json"),
    )


__all__ = [
    "TenantAdminBootstrapShadowResult",
    "build_tenant_admin_bootstrap_shadow_result",
]
