from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, cast

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.domains.revisor.base import logger
from app.domains.revisor.service_contracts import PacoteMesaCarregado
from app.domains.revisor.service_package import (
    carregar_complementos_legado_laudo_revisor,
    carregar_laudo_completo_revisor,
    carregar_pacote_mesa_laudo_revisor,
)
from app.shared.database import Laudo, Usuario
from app.shared.tenant_entitlement_guard import tenant_access_policy_for_user
from app.v2.adapters.reviewdesk_package import adapt_reviewdesk_case_view_projection_to_legacy_package
from app.v2.acl.technical_case_core import build_case_status_visual_label
from app.v2.document import DocumentHardGateEnforcementResultV1, DocumentSoftGateTraceV1
from app.v2.contracts.collaboration import build_reviewdesk_collaboration_read_model
from app.v2.contracts.projections import build_reviewdesk_case_view_projection
from app.v2.case_runtime import (
    build_legacy_case_status_payload_from_laudo,
    build_technical_case_runtime_bundle,
)
from app.v2.document import (
    build_document_hard_gate_decision,
    build_document_hard_gate_enforcement_result,
    build_document_soft_gate_route_context,
    build_document_soft_gate_trace,
    record_document_hard_gate_result,
    record_document_soft_gate_trace,
)
from app.v2.provenance import build_reviewdesk_content_origin_summary
from app.v2.runtime import (
    actor_role_from_user,
    v2_case_core_acl_enabled,
    v2_document_facade_enabled,
    v2_document_hard_gate_enabled,
    v2_document_hard_gate_operation_allowlist,
    v2_document_hard_gate_tenant_allowlist,
    v2_document_shadow_enabled,
    v2_document_soft_gate_enabled,
    v2_policy_engine_enabled,
    v2_provenance_enabled,
)


@dataclass(slots=True)
class ReviewDeskDocumentBoundaryResult:
    pacote_carregado: PacoteMesaCarregado
    payload_publico: dict[str, Any]
    legacy_payload_publico: dict[str, Any] = field(default_factory=dict)
    public_projection: dict[str, Any] | None = None
    projection_compatible: bool = False
    projection_divergences: list[str] = field(default_factory=list)
    provenance_summary: Any | None = None
    case_snapshot: Any | None = None
    tenant_policy_context: Any | None = None
    policy_decision: Any | None = None
    document_facade: Any | None = None
    soft_gate_trace: DocumentSoftGateTraceV1 | None = None
    hard_gate_result: DocumentHardGateEnforcementResultV1 | None = None


_PUBLIC_REVIEWDESK_NULL_FIELDS = (
    "origin_summary",
    "has_human_inputs",
    "has_ai_outputs",
    "has_ai_assisted_content",
    "has_legacy_unknown_content",
    "human_vs_ai_mix",
    "provenance_quality",
    "policy_summary",
    "review_required",
    "review_mode",
    "engineer_approval_required",
    "materialization_allowed",
    "issue_allowed",
    "policy_source_summary",
    "policy_rationale",
    "document_readiness",
    "template_binding_summary",
    "legacy_pipeline_shadow",
    "legacy_pipeline_name",
    "legacy_template_resolution",
    "legacy_materialization_allowed",
    "legacy_issue_allowed",
    "compatibility_summary",
    "case_snapshot_timestamp",
)
_PUBLIC_REVIEWDESK_EMPTY_LIST_FIELDS = (
    "document_blockers",
    "legacy_blockers",
)


def build_public_reviewdesk_case_view(
    projection: Any,
) -> dict[str, Any]:
    projection_payload = projection.model_dump(mode="json")
    payload = dict(projection_payload.get("payload") or {})

    for field_name in _PUBLIC_REVIEWDESK_NULL_FIELDS:
        if field_name in payload:
            payload[field_name] = None
    for field_name in _PUBLIC_REVIEWDESK_EMPTY_LIST_FIELDS:
        if field_name in payload:
            payload[field_name] = []

    stable_timestamp = payload.get("updated_at") or payload.get("created_at")
    projection_payload["correlation_id"] = str(
        projection_payload.get("case_id")
        or projection_payload.get("idempotency_key")
        or projection_payload.get("document_id")
        or ""
    )
    projection_payload["timestamp"] = stable_timestamp
    projection_payload["payload"] = payload
    return projection_payload


def _compose_reviewdesk_package_public_payload(
    *,
    legacy_payload_publico: dict[str, Any],
    adapted_payload: dict[str, Any] | None,
    public_projection: dict[str, Any] | None,
    compatible: bool,
) -> dict[str, Any]:
    payload_publico = dict(legacy_payload_publico)
    if isinstance(public_projection, dict):
        payload_publico["reviewer_case_view"] = public_projection
    payload_publico["reviewer_case_view_preferred"] = bool(compatible and public_projection)
    if compatible and isinstance(adapted_payload, dict):
        payload_publico.update(adapted_payload)
    return payload_publico


def _format_complete_summary_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        instant = value
    else:
        raw = str(value or "").strip()
        if not raw:
            return ""
        try:
            instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw
    return instant.astimezone().strftime("%d/%m/%Y %H:%M")


def merge_reviewdesk_boundary_into_complete_payload(
    *,
    legacy_payload: dict[str, Any],
    boundary_result: ReviewDeskDocumentBoundaryResult,
) -> dict[str, Any]:
    payload = dict(legacy_payload)
    package_payload = dict(boundary_result.payload_publico or {})

    reviewer_case_view = package_payload.get("reviewer_case_view")
    if isinstance(reviewer_case_view, dict):
        payload["reviewer_case_view"] = reviewer_case_view
    payload["reviewer_case_view_preferred"] = bool(boundary_result.projection_compatible)

    laudo_id = package_payload.get("laudo_id")
    if laudo_id is not None:
        payload["id"] = int(laudo_id)
    codigo_hash = str(package_payload.get("codigo_hash") or "").strip()
    if codigo_hash:
        payload["hash"] = codigo_hash[-6:]

    field_mapping = {
        "setor": "setor_industrial",
        "status": "status_revisao",
        "case_status": "case_status",
        "case_lifecycle_status": "case_lifecycle_status",
        "case_workflow_mode": "case_workflow_mode",
        "active_owner_role": "active_owner_role",
        "allowed_next_lifecycle_statuses": "allowed_next_lifecycle_statuses",
        "allowed_surface_actions": "allowed_surface_actions",
        "tipo_template": "tipo_template",
    }
    for target_key, source_key in field_mapping.items():
        if source_key in package_payload:
            payload[target_key] = package_payload[source_key]

    created_at = package_payload.get("criado_em")
    if created_at is not None:
        payload["criado_em"] = _format_complete_summary_timestamp(created_at)

    payload["status_visual_label"] = build_case_status_visual_label(
        lifecycle_status=payload.get("case_lifecycle_status"),
        active_owner_role=payload.get("active_owner_role"),
    )

    return payload


def build_legacy_case_status_payload_for_review(
    *,
    banco: Session,
    laudo: Laudo | None,
) -> dict[str, object]:
    return build_legacy_case_status_payload_from_laudo(
        banco=banco,
        laudo=laudo,
        include_case_lifecycle_context=False,
    )


def review_reject_shadow_scope_enabled(
    *,
    request: Request,
    usuario: Usuario,
) -> bool:
    if not v2_document_hard_gate_enabled():
        return False

    tenant_id = str(getattr(usuario, "empresa_id", "") or "").strip()
    if tenant_id not in set(v2_document_hard_gate_tenant_allowlist()):
        return False

    return "review_reject" in set(v2_document_hard_gate_operation_allowlist())


def build_reviewdesk_document_boundary(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
    laudo_id: int,
    limite_whispers: int,
    limite_pendencias: int,
    limite_revisoes: int,
    operation_kind: str,
    route_name: str,
    legacy_pipeline_name: str,
    side_effect_free: bool,
    route_path_fallback: str,
    enable_projection: bool,
    enable_soft_gate_trace: bool,
    enable_hard_gate: bool,
    graceful_failures: bool,
) -> ReviewDeskDocumentBoundaryResult:
    pacote_carregado = carregar_pacote_mesa_laudo_revisor(
        banco,
        laudo_id=laudo_id,
        empresa_id=usuario.empresa_id,
        limite_whispers=limite_whispers,
        limite_pendencias=limite_pendencias,
        limite_revisoes=limite_revisoes,
    )
    payload_publico = pacote_carregado.pacote.model_dump(mode="json")
    payload_publico["tenant_access_policy"] = tenant_access_policy_for_user(usuario)

    soft_gate_runtime_enabled = bool(enable_soft_gate_trace and v2_document_soft_gate_enabled())
    hard_gate_runtime_enabled = bool(enable_hard_gate and v2_document_hard_gate_enabled())
    gate_trace_required = bool(enable_soft_gate_trace and (soft_gate_runtime_enabled or hard_gate_runtime_enabled))

    provenance_summary = None
    if v2_provenance_enabled() or gate_trace_required:
        provenance_summary = build_reviewdesk_content_origin_summary(
            pacote=pacote_carregado.pacote,
        )
        request.state.v2_content_provenance_summary = provenance_summary.model_dump(mode="python")

    legacy_case_payload = build_legacy_case_status_payload_for_review(
        banco=banco,
        laudo=pacote_carregado.laudo,
    )
    runtime_bundle = build_technical_case_runtime_bundle(
        request=request,
        banco=banco,
        usuario=usuario,
        laudo=pacote_carregado.laudo,
        legacy_payload=legacy_case_payload,
        source_channel="review_api",
        template_key=pacote_carregado.pacote.tipo_template,
        family_key=getattr(pacote_carregado.laudo, "catalog_family_key", None),
        variant_key=getattr(pacote_carregado.laudo, "catalog_variant_key", None),
        laudo_type=pacote_carregado.pacote.tipo_template,
        document_type=pacote_carregado.pacote.tipo_template,
        provenance_summary=provenance_summary,
        current_review_status=pacote_carregado.pacote.status_revisao,
        has_form_data=bool(pacote_carregado.pacote.dados_formulario),
        has_ai_draft=bool(str(pacote_carregado.pacote.parecer_ia or "").strip()),
        report_pack_draft=getattr(pacote_carregado.laudo, "report_pack_draft_json", None),
        include_full_snapshot=True,
        include_policy_decision=bool(v2_policy_engine_enabled() or gate_trace_required),
        include_document_facade=bool(v2_document_facade_enabled() or gate_trace_required),
        attach_document_shadow=v2_document_shadow_enabled(),
        allow_partial_failures=graceful_failures,
    )
    base_case_snapshot = runtime_bundle.case_snapshot
    payload_publico["collaboration"] = build_reviewdesk_collaboration_read_model(
        pacote=pacote_carregado.pacote,
        requires_reviewer_action=bool(
            base_case_snapshot is not None
            and base_case_snapshot.canonical_status in {
                "needs_reviewer",
                "review_feedback_pending",
            }
        ),
    ).model_dump(mode="json")
    legacy_payload_publico = dict(payload_publico)

    case_snapshot = None
    tenant_policy_context = None
    policy_decision = None
    document_facade = None
    soft_gate_trace: DocumentSoftGateTraceV1 | None = None
    hard_gate_result: DocumentHardGateEnforcementResultV1 | None = None
    public_reviewdesk_projection = None
    projection_compatible = False
    projection_divergences: list[str] = []

    case_snapshot_required = (
        v2_case_core_acl_enabled()
        or enable_projection
        or v2_policy_engine_enabled()
        or v2_document_facade_enabled()
        or gate_trace_required
    )
    if case_snapshot_required:
        case_snapshot = base_case_snapshot
        tenant_policy_context = runtime_bundle.tenant_policy_context
        if v2_policy_engine_enabled() or gate_trace_required:
            policy_decision = runtime_bundle.policy_decision
        if v2_document_facade_enabled() or gate_trace_required:
            document_facade = runtime_bundle.document_facade

    def _compute_soft_gate_trace() -> Any | None:
        nonlocal soft_gate_trace
        if case_snapshot is None or document_facade is None:
            return None
        route_context = build_document_soft_gate_route_context(
            route_name=route_name,
            route_path=str(request.scope.get("path") or route_path_fallback),
            http_method=str(request.method or "GET"),
            source_channel="review_api",
            operation_kind=cast(
                Literal[
                    "preview_pdf",
                    "review_package_read",
                    "review_package_pdf_export",
                    "report_finalize",
                    "report_finalize_stream",
                    "template_publish_activate",
                    "review_approve",
                    "review_reject",
                    "review_issue",
                ],
                operation_kind,
            ),
            side_effect_free=side_effect_free,
            legacy_pipeline_name=legacy_pipeline_name,
        )
        soft_gate_trace = build_document_soft_gate_trace(
            case_snapshot=case_snapshot,
            document_facade=document_facade,
            route_context=route_context,
            correlation_id=case_snapshot.correlation_id,
            request_id=(
                request.headers.get("X-Request-ID")
                or request.headers.get("X-Correlation-ID")
                or case_snapshot.correlation_id
            ),
        )
        request.state.v2_document_soft_gate_decision = soft_gate_trace.decision.model_dump(mode="python")
        request.state.v2_document_soft_gate_trace = soft_gate_trace.model_dump(mode="python")
        if soft_gate_runtime_enabled:
            record_document_soft_gate_trace(soft_gate_trace)
        return soft_gate_trace

    if gate_trace_required and case_snapshot is not None and document_facade is not None:
        if graceful_failures:
            try:
                _compute_soft_gate_trace()
            except Exception:
                logger.debug("Falha ao registrar soft gate documental da mesa.", exc_info=True)
                request.state.v2_document_soft_gate_error = "review_package_soft_gate_failed"
                soft_gate_trace = None
        else:
            _compute_soft_gate_trace()

    if hard_gate_runtime_enabled and soft_gate_trace is not None:
        hard_gate_result = build_document_hard_gate_enforcement_result(
            decision=build_document_hard_gate_decision(
                soft_gate_trace=soft_gate_trace,
                remote_host=getattr(getattr(request, "client", None), "host", None),
            )
        )
        request.state.v2_document_hard_gate_decision = hard_gate_result.decision.model_dump(mode="python")
        request.state.v2_document_hard_gate_enforcement = hard_gate_result.model_dump(mode="python")
        record_document_hard_gate_result(hard_gate_result)

    if enable_projection and case_snapshot is not None:
        reviewdesk_projection = build_reviewdesk_case_view_projection(
            case_snapshot=case_snapshot,
            pacote=pacote_carregado.pacote,
            actor_id=usuario.id,
            actor_role=actor_role_from_user(usuario),
            source_channel="review_api",
            policy_decision=policy_decision,
            document_facade=document_facade,
        )
        adapted = adapt_reviewdesk_case_view_projection_to_legacy_package(
            projection=reviewdesk_projection,
            expected_legacy_payload=payload_publico,
        )
        public_reviewdesk_projection = build_public_reviewdesk_case_view(
            reviewdesk_projection,
        )
        projection_compatible = bool(adapted.compatible)
        projection_divergences = list(adapted.divergences)
        request.state.v2_reviewdesk_projection_result = {
            "projection": reviewdesk_projection.model_dump(mode="python"),
            "public_projection": public_reviewdesk_projection,
            "compatible": adapted.compatible,
            "divergences": adapted.divergences,
            "used_projection": True,
            "provenance": (
                provenance_summary.model_dump(mode="python")
                if provenance_summary is not None
                else None
            ),
            "policy": (
                policy_decision.summary.model_dump(mode="python")
                if policy_decision is not None
                else None
            ),
            "document_facade": (
                document_facade.model_dump(mode="python")
                if document_facade is not None
                else None
            ),
            "document_shadow": (
                document_facade.legacy_pipeline_shadow.model_dump(mode="python")
                if document_facade is not None and document_facade.legacy_pipeline_shadow is not None
                else None
            ),
            "document_soft_gate": (
                soft_gate_trace.model_dump(mode="python")
                if soft_gate_trace is not None
                else None
            ),
        }
        payload_publico = _compose_reviewdesk_package_public_payload(
            legacy_payload_publico=legacy_payload_publico,
            adapted_payload=adapted.payload,
            public_projection=public_reviewdesk_projection,
            compatible=projection_compatible,
        )
        request.state.v2_reviewdesk_projection_preferred = projection_compatible
        if not adapted.compatible:
            request.state.v2_reviewdesk_projection_prefer_error = (
                "reviewdesk_projection_diverged_from_legacy"
            )
            logger.debug(
                "V2 reviewdesk projection divergiu | laudo_id=%s | divergences=%s",
                laudo_id,
                ",".join(adapted.divergences),
            )

    return ReviewDeskDocumentBoundaryResult(
        pacote_carregado=pacote_carregado,
        payload_publico=payload_publico,
        legacy_payload_publico=legacy_payload_publico,
        public_projection=public_reviewdesk_projection,
        projection_compatible=projection_compatible,
        projection_divergences=projection_divergences,
        provenance_summary=provenance_summary,
        case_snapshot=case_snapshot,
        tenant_policy_context=tenant_policy_context,
        policy_decision=policy_decision,
        document_facade=document_facade,
        soft_gate_trace=soft_gate_trace,
        hard_gate_result=hard_gate_result,
    )


def build_reviewdesk_case_package_payload(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
    laudo_id: int,
    limite_whispers: int,
    limite_pendencias: int,
    limite_revisoes: int,
    enable_soft_gate_trace: bool = True,
) -> dict[str, object]:
    result = build_reviewdesk_document_boundary(
        request=request,
        usuario=usuario,
        banco=banco,
        laudo_id=laudo_id,
        limite_whispers=limite_whispers,
        limite_pendencias=limite_pendencias,
        limite_revisoes=limite_revisoes,
        operation_kind="review_package_read",
        route_name="obter_pacote_mesa_laudo",
        legacy_pipeline_name="legacy_review_package",
        side_effect_free=True,
        route_path_fallback="/revisao/api/laudo/{laudo_id}/pacote",
        enable_projection=True,
        enable_soft_gate_trace=enable_soft_gate_trace,
        enable_hard_gate=False,
        graceful_failures=True,
    )
    return result.payload_publico


def build_reviewdesk_complete_payload(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
    laudo_id: int,
    incluir_historico: bool,
    cursor: int | None,
    limite: int,
) -> dict[str, object]:
    try:
        boundary_result = build_reviewdesk_document_boundary(
            request=request,
            usuario=usuario,
            banco=banco,
            laudo_id=laudo_id,
            limite_whispers=80,
            limite_pendencias=80,
            limite_revisoes=10,
            operation_kind="review_complete_read",
            route_name="obter_laudo_completo",
            legacy_pipeline_name="legacy_review_complete",
            side_effect_free=True,
            route_path_fallback="/revisao/api/laudo/{laudo_id}/completo",
            enable_projection=True,
            enable_soft_gate_trace=False,
            enable_hard_gate=False,
            graceful_failures=True,
        )
    except HTTPException:
        raise
    except Exception:
        logger.debug(
            "Falha ao promover reviewdesk projection para o caso aberto do shell legado.",
            exc_info=True,
        )
        request.state.v2_reviewdesk_projection_preferred = False
        request.state.v2_reviewdesk_projection_prefer_error = "reviewdesk_projection_prefer_failed"
        payload = carregar_laudo_completo_revisor(
            banco,
            laudo_id=laudo_id,
            empresa_id=usuario.empresa_id,
            incluir_historico=incluir_historico,
            cursor=cursor,
            limite=limite,
        )
        payload["reviewer_case_view_preferred"] = False
        return payload

    legacy_payload = carregar_complementos_legado_laudo_revisor(
        banco,
        laudo=boundary_result.pacote_carregado.laudo,
        empresa_id=usuario.empresa_id,
        incluir_historico=incluir_historico,
        cursor=cursor,
        limite=limite,
    )
    payload = merge_reviewdesk_boundary_into_complete_payload(
        legacy_payload=legacy_payload,
        boundary_result=boundary_result,
    )
    request.state.v2_reviewdesk_projection_preferred = bool(
        getattr(request.state, "v2_reviewdesk_projection_preferred", False)
    )
    return payload


def evaluate_reviewdesk_document_gate_for_decision(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
    laudo_id: int,
    operation_kind: Literal["review_approve", "review_reject"],
    route_name: str,
    legacy_pipeline_name: str,
) -> tuple[DocumentSoftGateTraceV1 | None, DocumentHardGateEnforcementResultV1 | None]:
    result = build_reviewdesk_document_boundary(
        request=request,
        usuario=usuario,
        banco=banco,
        laudo_id=laudo_id,
        limite_whispers=40,
        limite_pendencias=40,
        limite_revisoes=10,
        operation_kind=operation_kind,
        route_name=route_name,
        legacy_pipeline_name=legacy_pipeline_name,
        side_effect_free=False,
        route_path_fallback="/revisao/api/laudo/{laudo_id}/avaliar",
        enable_projection=False,
        enable_soft_gate_trace=True,
        enable_hard_gate=True,
        graceful_failures=False,
    )
    return result.soft_gate_trace, result.hard_gate_result


__all__ = [
    "ReviewDeskDocumentBoundaryResult",
    "build_legacy_case_status_payload_for_review",
    "build_reviewdesk_complete_payload",
    "build_public_reviewdesk_case_view",
    "build_reviewdesk_case_package_payload",
    "build_reviewdesk_document_boundary",
    "merge_reviewdesk_boundary_into_complete_payload",
    "evaluate_reviewdesk_document_gate_for_decision",
    "review_reject_shadow_scope_enabled",
]
