"""Observabilidade e evidencia do slice template_publish_activate."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import Request
from sqlalchemy.orm import Session

from app.domains.revisor.templates_laudo_support import PORTAL_AUDITORIA_TEMPLATES
from app.shared.database import RegistroAuditoriaEmpresa, TemplateLaudo, Usuario
from app.v2.contracts.provenance import ProvenanceEntry, build_content_origin_summary
from app.v2.document.gate_metrics import record_document_soft_gate_trace
from app.v2.document.gate_models import (
    DocumentSoftGateBlockerV1,
    DocumentSoftGateDecisionV1,
    DocumentSoftGateTraceV1,
)
from app.v2.document.gates import build_document_soft_gate_route_context
from app.v2.document.hard_gate import (
    build_document_hard_gate_decision,
    build_document_hard_gate_enforcement_result,
)
from app.v2.document.hard_gate_evidence import record_document_hard_gate_durable_evidence
from app.v2.document.hard_gate_metrics import record_document_hard_gate_result
from app.v2.document.hard_gate_models import DocumentHardGateEnforcementResultV1
from app.v2.runtime import (
    v2_document_hard_gate_enabled,
    v2_document_hard_gate_operation_allowlist,
    v2_document_hard_gate_template_code_allowlist,
    v2_document_hard_gate_tenant_allowlist,
    v2_document_soft_gate_enabled,
)

_LOCAL_CONTROLLED_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_TEMPLATE_PUBLISH_OPERATION: Literal["template_publish_activate"] = "template_publish_activate"
_TEMPLATE_PUBLISH_SOURCE_CHANNEL = "review_templates_api"
_TEMPLATE_PUBLISH_LEGACY_PIPELINE = "legacy_template_publish_activate"


def _normalized_template_code(template: TemplateLaudo) -> str:
    return str(getattr(template, "codigo_template", "") or "").strip().lower()


def _template_code_allowlisted(template: TemplateLaudo) -> bool:
    allowlist = {item.strip().lower() for item in v2_document_hard_gate_template_code_allowlist() if item.strip()}
    if not allowlist:
        return True
    return _normalized_template_code(template) in allowlist


def template_publish_shadow_scope_enabled(
    *,
    request: Request,
    usuario: Usuario,
    template: TemplateLaudo,
) -> bool:
    if not v2_document_hard_gate_enabled():
        return False

    remote_host = str(getattr(getattr(request, "client", None), "host", "") or "").strip().lower()
    if remote_host and remote_host not in _LOCAL_CONTROLLED_HOSTS:
        return False

    tenant_id = str(getattr(usuario, "empresa_id", "") or "").strip()
    if tenant_id not in set(v2_document_hard_gate_tenant_allowlist()):
        return False

    if _TEMPLATE_PUBLISH_OPERATION not in set(v2_document_hard_gate_operation_allowlist()):
        return False

    return _template_code_allowlisted(template)


def build_template_publish_shadow_scope_payload(
    *,
    request: Request,
    usuario: Usuario,
    template: TemplateLaudo,
    route_name: str,
    scope_enabled: bool,
) -> dict[str, Any]:
    return {
        "operation_kind": _TEMPLATE_PUBLISH_OPERATION,
        "route_name": route_name,
        "route_path": str(request.scope.get("path") or ""),
        "remote_host": str(getattr(getattr(request, "client", None), "host", "") or ""),
        "tenant_id": str(getattr(usuario, "empresa_id", "") or ""),
        "template_id": int(getattr(template, "id", 0) or 0),
        "codigo_template": str(getattr(template, "codigo_template", "") or ""),
        "versao": int(getattr(template, "versao", 0) or 0),
        "modo_editor": str(getattr(template, "modo_editor", "") or ""),
        "enabled": bool(scope_enabled),
        "template_code_allowlisted": _template_code_allowlisted(template),
    }


def _build_template_publish_blockers(
    *,
    has_active_template_before_publish: bool,
) -> list[DocumentSoftGateBlockerV1]:
    if has_active_template_before_publish:
        return []

    return [
        DocumentSoftGateBlockerV1(
            blocker_code="template_not_bound",
            blocker_kind="template",
            message="Nao havia template operacional ativo vinculado antes desta publicacao.",
            source="template_publish_shadow",
            signal_state="confirmed",
            blocking=True,
            applies_to_materialization=True,
            applies_to_issue=False,
        ),
        DocumentSoftGateBlockerV1(
            blocker_code="template_source_unknown",
            blocker_kind="template",
            message="A origem operacional do template permanecia indefinida antes da ativacao publicada.",
            source="template_publish_shadow",
            signal_state="unknown",
            blocking=True,
            applies_to_materialization=True,
            applies_to_issue=False,
        ),
    ]


def evaluate_template_publish_activate_shadow(
    *,
    request: Request,
    usuario: Usuario,
    template: TemplateLaudo,
    route_name: str,
    has_active_template_before_publish: bool,
) -> tuple[DocumentSoftGateTraceV1 | None, DocumentHardGateEnforcementResultV1 | None]:
    soft_gate_enabled = v2_document_soft_gate_enabled()
    hard_gate_enabled = v2_document_hard_gate_enabled()
    if not soft_gate_enabled and not hard_gate_enabled:
        return None, None

    tenant_id = str(getattr(usuario, "empresa_id", "") or "").strip()
    template_code = str(getattr(template, "codigo_template", "") or "").strip()
    correlation_id = (
        request.headers.get("X-Correlation-ID")
        or request.headers.get("X-Request-ID")
        or uuid.uuid4().hex
    )
    request_id = request.headers.get("X-Request-ID") or correlation_id
    blockers = _build_template_publish_blockers(
        has_active_template_before_publish=has_active_template_before_publish,
    )
    provenance = build_content_origin_summary(
        entries=[
            ProvenanceEntry(
                origin_kind="system",
                source="template_publish_route",
                confidence="confirmed",
                signal_count=1,
            )
        ],
        notes=["template_publish_activate_shadow"],
    )
    route_context = build_document_soft_gate_route_context(
        route_name=route_name,
        route_path=str(request.scope.get("path") or ""),
        http_method=str(request.method or "POST"),
        source_channel=_TEMPLATE_PUBLISH_SOURCE_CHANNEL,
        operation_kind=_TEMPLATE_PUBLISH_OPERATION,
        side_effect_free=False,
        legacy_pipeline_name=_TEMPLATE_PUBLISH_LEGACY_PIPELINE,
    )
    would_block = bool(blockers)
    decision = DocumentSoftGateDecisionV1(
        tenant_id=tenant_id,
        case_id=f"template_publish:{tenant_id}:{int(getattr(template, 'id', 0) or 0)}",
        document_id=f"template:{tenant_id}:{int(getattr(template, 'id', 0) or 0)}",
        template_id=int(getattr(template, "id", 0) or 0),
        template_key=template_code or None,
        template_source_kind="library_active_template" if has_active_template_before_publish else "unknown",
        route_context=route_context,
        materialization_would_be_blocked=would_block,
        issue_would_be_blocked=False,
        blockers=blockers,
        current_case_status=None,
        current_review_status=str(getattr(template, "status_template", "") or "") or None,
        canonic_document_status="template_publish_pending_activation",
        document_readiness=(
            "template_publish_shadow_observed"
            if has_active_template_before_publish
            else "template_publish_template_gap"
        ),
        policy_summary={
            "template_publish_shadow_only": True,
            "has_active_template_before_publish": bool(has_active_template_before_publish),
            "audit_expected": True,
            "template_code_allowlisted": _template_code_allowlisted(template),
            "candidate_blockers_shadow": [item.blocker_code for item in blockers],
        },
        provenance_summary=provenance.model_dump(mode="python"),
        decision_source=["template_publish_activate_shadow"],
        correlation_id=correlation_id,
        request_id=request_id,
    )
    trace = DocumentSoftGateTraceV1(
        trace_id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        case_id=decision.case_id,
        legacy_laudo_id=None,
        route_context=route_context,
        decision=decision,
        correlation_id=correlation_id,
        request_id=request_id,
    )

    request.state.v2_document_soft_gate_decision = decision.model_dump(mode="python")
    request.state.v2_document_soft_gate_trace = trace.model_dump(mode="python")
    if soft_gate_enabled:
        record_document_soft_gate_trace(trace)

    hard_gate_result = None
    if hard_gate_enabled:
        hard_gate_result = build_document_hard_gate_enforcement_result(
            decision=build_document_hard_gate_decision(
                soft_gate_trace=trace,
                remote_host=getattr(getattr(request, "client", None), "host", None),
            )
        )
        request.state.v2_document_hard_gate_decision = hard_gate_result.decision.model_dump(mode="python")
        request.state.v2_document_hard_gate_enforcement = hard_gate_result.model_dump(mode="python")
        record_document_hard_gate_result(hard_gate_result)

    return trace, hard_gate_result


def find_latest_template_publish_audit_record(
    *,
    banco: Session,
    usuario: Usuario,
    template_id: int,
    action: str = "template_publicado",
) -> RegistroAuditoriaEmpresa | None:
    registros = (
        banco.query(RegistroAuditoriaEmpresa)
        .filter(
            RegistroAuditoriaEmpresa.empresa_id == int(usuario.empresa_id),
            RegistroAuditoriaEmpresa.portal == PORTAL_AUDITORIA_TEMPLATES,
            RegistroAuditoriaEmpresa.acao == action,
        )
        .order_by(RegistroAuditoriaEmpresa.id.desc())
        .limit(10)
        .all()
    )
    for registro in registros:
        payload = getattr(registro, "payload_json", None) or {}
        if int(payload.get("template_id") or 0) == int(template_id):
            return registro
    return None


def persist_template_publish_shadow_observation(
    *,
    request: Request,
    usuario: Usuario,
    template: TemplateLaudo,
    route_name: str,
    hard_gate_result: DocumentHardGateEnforcementResultV1 | None,
    audit_record: RegistroAuditoriaEmpresa | None,
    functional_outcome: str = "template_publish_completed_shadow_only",
    response_status_code: int = 200,
) -> str | None:
    if hard_gate_result is None:
        return None

    artifact_path = record_document_hard_gate_durable_evidence(
        hard_gate_result,
        remote_host=getattr(getattr(request, "client", None), "host", None),
        observation_context={
            "functional_outcome": functional_outcome,
            "response": {
                "status_code": int(response_status_code),
                "media_type": "application/json",
                "audit_generated": audit_record is not None,
            },
            "target": {
                "template_id": int(getattr(template, "id", 0) or 0),
                "codigo_template": str(getattr(template, "codigo_template", "") or ""),
                "versao": int(getattr(template, "versao", 0) or 0),
                "status_template": str(getattr(template, "status_template", "") or ""),
                "modo_editor": str(getattr(template, "modo_editor", "") or ""),
                "ativo": bool(getattr(template, "ativo", False)),
            },
            "source_context": {
                "slice_name": _TEMPLATE_PUBLISH_OPERATION,
                "route_context": route_name,
                "tenant_id": str(getattr(usuario, "empresa_id", "") or ""),
                "template_code_allowlisted": _template_code_allowlisted(template),
                "audit_record_id": int(getattr(audit_record, "id", 0) or 0) if audit_record is not None else None,
                "audit_portal": PORTAL_AUDITORIA_TEMPLATES,
            },
        },
    )
    if artifact_path:
        request.state.v2_template_publish_shadow_artifact_path = artifact_path
    return artifact_path


__all__ = [
    "build_template_publish_shadow_scope_payload",
    "evaluate_template_publish_activate_shadow",
    "find_latest_template_publish_audit_record",
    "persist_template_publish_shadow_observation",
    "template_publish_shadow_scope_enabled",
]
