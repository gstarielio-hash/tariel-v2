"""Primeiro hard gate documental controlado, derivado do soft gate do V2."""

from __future__ import annotations

from typing import Any

from app.v2.document.gate_models import DocumentSoftGateTraceV1
from app.v2.document.hard_gate_models import (
    DocumentHardGateBlockerV1,
    DocumentHardGateDecisionV1,
    DocumentHardGateEnforcementResultV1,
)
from app.v2.runtime import (
    V2_DOCUMENT_HARD_GATE_ENFORCE_FLAG,
    V2_DOCUMENT_HARD_GATE_FLAG,
    V2_DOCUMENT_HARD_GATE_OPERATIONS_FLAG,
    V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES_FLAG,
    V2_DOCUMENT_HARD_GATE_TENANTS_FLAG,
    v2_document_hard_gate_enabled,
    v2_document_hard_gate_enforce_enabled,
    v2_document_hard_gate_operation_allowlist,
    v2_document_hard_gate_template_code_allowlist,
    v2_document_hard_gate_tenant_allowlist,
)

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_BLOCKED_RESPONSE_CODE = "DOCUMENT_HARD_GATE_BLOCKED"
_BLOCKED_RESPONSE_STATUS = 422
_BLOCKED_RESPONSE_MESSAGE = (
    "Operação bloqueada pelo hard gate documental controlado do V2."
)
_SHADOW_ONLY_OPERATION_KINDS = {
    "review_reject",
    "report_finalize_stream",
}
_REPORT_FINALIZE_ENFORCE_CODES = {
    "materialization_disallowed_by_policy",
    "no_active_report",
    "template_not_bound",
    "template_source_unknown",
}
_TEMPLATE_PUBLISH_ENFORCE_CODES = {
    "template_not_bound",
    "template_source_unknown",
}
_REVIEW_APPROVE_ENFORCE_CODES = {
    "materialization_disallowed_by_policy",
    "no_active_report",
    "template_not_bound",
    "template_source_unknown",
}


def _is_local_host(remote_host: str | None) -> bool:
    host = str(remote_host or "").strip().lower()
    if not host:
        return True
    return host in _LOCAL_HOSTS


def _operation_relevant_for_hard_gate(
    *,
    operation_kind: str,
    blocker: Any,
) -> bool:
    blocker_code = str(getattr(blocker, "blocker_code", "") or "").strip()
    if operation_kind in {"report_finalize", "report_finalize_stream"}:
        return bool(getattr(blocker, "applies_to_materialization", False))
    if operation_kind == "template_publish_activate":
        return bool(
            str(getattr(blocker, "blocker_kind", "") or "").strip() == "template"
            or blocker_code in {"template_not_bound", "template_source_unknown"}
        )
    if operation_kind == "review_approve":
        return bool(
            getattr(blocker, "applies_to_materialization", False)
            or getattr(blocker, "applies_to_issue", False)
        )
    if operation_kind == "review_reject":
        return bool(
            getattr(blocker, "applies_to_materialization", False)
            or getattr(blocker, "applies_to_issue", False)
        )
    return False


def _blocker_enforcement_scope(
    *,
    operation_kind: str,
    blocker: Any,
) -> str:
    blocker_code = str(getattr(blocker, "blocker_code", "") or "").strip()
    if operation_kind in _SHADOW_ONLY_OPERATION_KINDS:
        return "shadow_only"
    if operation_kind == "report_finalize":
        return "enforce" if blocker_code in _REPORT_FINALIZE_ENFORCE_CODES else "shadow_only"
    if operation_kind == "template_publish_activate":
        return "enforce" if blocker_code in _TEMPLATE_PUBLISH_ENFORCE_CODES else "shadow_only"
    if operation_kind == "review_approve":
        return "enforce" if blocker_code in _REVIEW_APPROVE_ENFORCE_CODES else "shadow_only"
    return "shadow_only"


def build_document_hard_gate_decision(
    *,
    soft_gate_trace: DocumentSoftGateTraceV1,
    remote_host: str | None,
) -> DocumentHardGateDecisionV1:
    operation_kind = str(soft_gate_trace.route_context.operation_kind or "").strip() or "unknown"
    tenant_id = str(soft_gate_trace.tenant_id or "").strip()
    hard_gate_enabled = v2_document_hard_gate_enabled()
    enforce_requested = v2_document_hard_gate_enforce_enabled()
    local_request = _is_local_host(remote_host)
    tenant_allowlisted = tenant_id in set(v2_document_hard_gate_tenant_allowlist())
    operation_allowlisted = operation_kind in set(v2_document_hard_gate_operation_allowlist())
    shadow_scope_allowed = bool(
        hard_gate_enabled and tenant_allowlisted and operation_allowlisted
    )
    shadow_only_operation = operation_kind in _SHADOW_ONLY_OPERATION_KINDS
    enforce_enabled = bool(
        hard_gate_enabled
        and enforce_requested
        and tenant_allowlisted
        and operation_allowlisted
        and not shadow_only_operation
    )
    if shadow_only_operation:
        shadow_only = shadow_scope_allowed
    else:
        shadow_only = bool(hard_gate_enabled and not enforce_enabled)

    blockers: list[DocumentHardGateBlockerV1] = []
    for item in soft_gate_trace.decision.blockers:
        if not item.blocking:
            continue
        if not _operation_relevant_for_hard_gate(
            operation_kind=operation_kind,
            blocker=item,
        ):
            continue
        enforcement_scope = _blocker_enforcement_scope(
            operation_kind=operation_kind,
            blocker=item,
        )
        blockers.append(
            DocumentHardGateBlockerV1(
                blocker_code=item.blocker_code,
                blocker_kind=item.blocker_kind,
                message=item.message,
                source=item.source,
                signal_state=item.signal_state,
                blocking=item.blocking,
                applies_to_current_operation=True,
                enforcement_scope=enforcement_scope,  # type: ignore[arg-type]
                enforce_blocking=enforcement_scope == "enforce",
            )
        )
    if shadow_only_operation:
        would_block = bool(blockers)
        did_block = False
    else:
        would_block = any(item.enforce_blocking for item in blockers)
        did_block = bool(enforce_enabled and would_block)

    if not hard_gate_enabled:
        mode = "disabled"
    elif shadow_only_operation and not shadow_scope_allowed:
        mode = "disabled"
    elif enforce_enabled:
        mode = "enforce_controlled"
    else:
        mode = "shadow_only"

    decision_sources = set(soft_gate_trace.decision.decision_source)
    decision_sources.add("document_hard_gate")

    return DocumentHardGateDecisionV1(
        tenant_id=tenant_id,
        case_id=soft_gate_trace.case_id,
        legacy_laudo_id=soft_gate_trace.legacy_laudo_id,
        document_id=soft_gate_trace.decision.document_id,
        operation_kind=operation_kind,
        route_name=soft_gate_trace.route_context.route_name,
        route_path=soft_gate_trace.route_context.route_path,
        source_channel=soft_gate_trace.route_context.source_channel,
        legacy_pipeline_name=soft_gate_trace.route_context.legacy_pipeline_name,
        hard_gate_enabled=hard_gate_enabled,
        enforce_requested=enforce_requested,
        enforce_enabled=enforce_enabled,
        shadow_only=shadow_only,
        local_request=local_request,
        tenant_allowlisted=tenant_allowlisted,
        operation_allowlisted=operation_allowlisted,
        would_block=would_block,
        did_block=did_block,
        blockers=blockers,
        decision_source=sorted(decision_sources),
        policy_summary=dict(soft_gate_trace.decision.policy_summary),
        document_readiness={
            "readiness_state": soft_gate_trace.decision.document_readiness,
            "current_case_status": soft_gate_trace.decision.current_case_status,
            "current_review_status": soft_gate_trace.decision.current_review_status,
            "canonic_document_status": soft_gate_trace.decision.canonic_document_status,
            "template_id": soft_gate_trace.decision.template_id,
            "template_key": soft_gate_trace.decision.template_key,
            "template_source_kind": soft_gate_trace.decision.template_source_kind,
        },
        provenance_summary=soft_gate_trace.decision.provenance_summary,
        mode=mode,
        correlation_id=soft_gate_trace.correlation_id,
        request_id=soft_gate_trace.request_id,
    )


def build_document_hard_gate_enforcement_result(
    *,
    decision: DocumentHardGateDecisionV1,
) -> DocumentHardGateEnforcementResultV1:
    return DocumentHardGateEnforcementResultV1(
        decision=decision,
        blocked_response_status=_BLOCKED_RESPONSE_STATUS if decision.did_block else None,
        blocked_response_code=_BLOCKED_RESPONSE_CODE if decision.did_block else None,
        blocked_response_message=_BLOCKED_RESPONSE_MESSAGE if decision.did_block else None,
    )


def build_document_hard_gate_block_detail(
    result: DocumentHardGateEnforcementResultV1,
) -> dict[str, Any]:
    decision = result.decision
    return {
        "codigo": _BLOCKED_RESPONSE_CODE,
        "permitido": False,
        "operacao": decision.operation_kind,
        "modo": decision.mode,
        "mensagem": _BLOCKED_RESPONSE_MESSAGE,
        "blockers": [
            {
                "blocker_code": item.blocker_code,
                "blocker_kind": item.blocker_kind,
                "message": item.message,
                "source": item.source,
            }
            for item in decision.blockers
            if item.enforce_blocking
        ],
    }


def document_hard_gate_observability_flags() -> dict[str, Any]:
    return {
        "hard_gate_flag": V2_DOCUMENT_HARD_GATE_FLAG,
        "hard_gate_enabled": v2_document_hard_gate_enabled(),
        "enforce_flag": V2_DOCUMENT_HARD_GATE_ENFORCE_FLAG,
        "enforce_requested": v2_document_hard_gate_enforce_enabled(),
        "tenant_allowlist_flag": V2_DOCUMENT_HARD_GATE_TENANTS_FLAG,
        "tenant_allowlist": list(v2_document_hard_gate_tenant_allowlist()),
        "operation_allowlist_flag": V2_DOCUMENT_HARD_GATE_OPERATIONS_FLAG,
        "operation_allowlist": list(v2_document_hard_gate_operation_allowlist()),
        "template_code_allowlist_flag": V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES_FLAG,
        "template_code_allowlist": list(v2_document_hard_gate_template_code_allowlist()),
    }


__all__ = [
    "build_document_hard_gate_block_detail",
    "build_document_hard_gate_decision",
    "build_document_hard_gate_enforcement_result",
    "document_hard_gate_observability_flags",
]
