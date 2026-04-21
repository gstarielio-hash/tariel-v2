"""Avaliador canonico do soft gate documental incremental do V2."""

from __future__ import annotations

import uuid

from app.v2.acl.technical_case_core import TechnicalCaseStatusSnapshot
from app.v2.document.gate_models import (
    DocumentSoftGateBlockerV1,
    DocumentSoftGateDecisionV1,
    DocumentSoftGateOperationKind,
    DocumentSoftGateRouteContextV1,
    DocumentSoftGateTraceV1,
)
from app.v2.document.models import CanonicalDocumentFacadeV1, DocumentBlockerSummary


def build_document_soft_gate_route_context(
    *,
    route_name: str,
    route_path: str,
    http_method: str,
    source_channel: str,
    operation_kind: DocumentSoftGateOperationKind,
    side_effect_free: bool,
    legacy_pipeline_name: str | None = None,
    legacy_compatibility_state: str | None = None,
) -> DocumentSoftGateRouteContextV1:
    return DocumentSoftGateRouteContextV1(
        route_name=str(route_name or "").strip() or "unknown",
        route_path=str(route_path or "").strip() or "unknown",
        http_method=str(http_method or "").strip().upper() or "GET",
        source_channel=str(source_channel or "").strip() or "unknown",
        operation_kind=operation_kind,
        side_effect_free=bool(side_effect_free),
        legacy_pipeline_name=str(legacy_pipeline_name or "").strip() or None,
        legacy_compatibility_state=str(legacy_compatibility_state or "").strip() or None,
    )


def _append_blocker(
    items: dict[str, DocumentSoftGateBlockerV1],
    *,
    blocker_code: str,
    blocker_kind: str,
    message: str,
    source: str | None,
    signal_state: str,
    blocking: bool,
    applies_to_materialization: bool,
    applies_to_issue: bool,
) -> None:
    existing = items.get(blocker_code)
    if existing is None:
        items[blocker_code] = DocumentSoftGateBlockerV1(
            blocker_code=blocker_code,
            blocker_kind=blocker_kind,  # type: ignore[arg-type]
            message=message,
            source=source,
            signal_state=signal_state,  # type: ignore[arg-type]
            blocking=bool(blocking),
            applies_to_materialization=bool(applies_to_materialization),
            applies_to_issue=bool(applies_to_issue),
        )
        return

    items[blocker_code] = existing.model_copy(
        update={
            "blocking": bool(existing.blocking or blocking),
            "applies_to_materialization": bool(
                existing.applies_to_materialization or applies_to_materialization
            ),
            "applies_to_issue": bool(existing.applies_to_issue or applies_to_issue),
        }
    )


def _map_facade_blocker(
    items: dict[str, DocumentSoftGateBlockerV1],
    blocker: DocumentBlockerSummary,
) -> None:
    code = str(blocker.blocker_code or "").strip()
    if not code:
        return

    applies_to_materialization = code in {
        "no_active_report",
        "template_not_bound",
        "materialization_disallowed_by_policy",
    }
    applies_to_issue = code in {
        "no_active_report",
        "template_not_bound",
        "materialization_disallowed_by_policy",
        "review_still_required_for_issue",
        "engineer_approval_pending",
        "legacy_content_origin_unknown",
    }
    blocking = code not in {"legacy_content_origin_unknown"}
    if code in {"review_still_required_for_issue", "engineer_approval_pending"}:
        blocking = True

    _append_blocker(
        items,
        blocker_code=code,
        blocker_kind=str(blocker.blocker_kind or "unknown"),
        message=str(blocker.message or "").strip() or code,
        source=str(blocker.source or "").strip() or None,
        signal_state="derived",
        blocking=blocking,
        applies_to_materialization=applies_to_materialization,
        applies_to_issue=applies_to_issue,
    )


def _build_soft_gate_blockers(
    *,
    document_facade: CanonicalDocumentFacadeV1,
    case_snapshot: TechnicalCaseStatusSnapshot,
) -> list[DocumentSoftGateBlockerV1]:
    items: dict[str, DocumentSoftGateBlockerV1] = {}
    template_binding = document_facade.template_binding
    readiness = document_facade.document_readiness
    policy = document_facade.document_policy
    provenance_summary = readiness.provenance_summary or (
        case_snapshot.content_origin_summary.model_dump(mode="python")
        if case_snapshot.content_origin_summary is not None
        else {}
    )

    for blocker in readiness.blockers:
        _map_facade_blocker(items, blocker)

    if template_binding.binding_status != "bound":
        _append_blocker(
            items,
            blocker_code="template_not_bound",
            blocker_kind="template",
            message="O soft gate documental encontrou ausencia de template vinculado.",
            source="template_binding",
            signal_state="confirmed",
            blocking=True,
            applies_to_materialization=True,
            applies_to_issue=True,
        )
    if template_binding.template_source_kind == "unknown":
        _append_blocker(
            items,
            blocker_code="template_source_unknown",
            blocker_kind="template",
            message="O source kind do template legado e desconhecido para gate documental seguro.",
            source="template_binding",
            signal_state="unknown",
            blocking=True,
            applies_to_materialization=True,
            applies_to_issue=True,
        )
    if not bool(policy.materialization_allowed):
        _append_blocker(
            items,
            blocker_code="materialization_disallowed_by_policy",
            blocker_kind="policy",
            message="A politica canonica atual nao permite materializacao neste contexto.",
            source="policy_engine",
            signal_state="derived",
            blocking=True,
            applies_to_materialization=True,
            applies_to_issue=True,
        )
    if not bool(policy.issue_allowed):
        _append_blocker(
            items,
            blocker_code="issue_disallowed_by_policy",
            blocker_kind="policy",
            message="A politica canonica atual ainda nao permite emissao neste contexto.",
            source="policy_engine",
            signal_state="derived",
            blocking=True,
            applies_to_materialization=False,
            applies_to_issue=True,
        )
    if bool(policy.review_required) and case_snapshot.canonical_status != "approved":
        _append_blocker(
            items,
            blocker_code="review_requirement_not_satisfied",
            blocker_kind="review",
            message="O soft gate ainda exige satisfacao do gate de revisao antes da emissao.",
            source="policy_engine",
            signal_state="derived",
            blocking=True,
            applies_to_materialization=False,
            applies_to_issue=True,
        )
    if bool(policy.engineer_approval_required) and not bool(policy.issue_allowed):
        _append_blocker(
            items,
            blocker_code="engineer_approval_requirement_not_satisfied",
            blocker_kind="approval",
            message="A aprovacao humana final do engenheiro ainda nao esta satisfeita.",
            source="policy_engine",
            signal_state="derived",
            blocking=True,
            applies_to_materialization=False,
            applies_to_issue=True,
        )
    if not provenance_summary:
        _append_blocker(
            items,
            blocker_code="provenance_summary_unavailable",
            blocker_kind="provenance",
            message="Nao houve provenance suficiente para avaliar o gate documental com confianca.",
            source="provenance",
            signal_state="unknown",
            blocking=True,
            applies_to_materialization=False,
            applies_to_issue=True,
        )
    elif bool(provenance_summary.get("has_legacy_unknown_content")):
        _append_blocker(
            items,
            blocker_code="document_source_insufficient",
            blocker_kind="provenance",
            message="A origem documental ainda contem sinais legacy_unknown insuficientes para emissao controlada.",
            source="provenance",
            signal_state="unknown",
            blocking=True,
            applies_to_materialization=False,
            applies_to_issue=True,
        )

    return sorted(
        items.values(),
        key=lambda item: (
            item.blocker_code,
            item.blocker_kind,
        ),
    )


def build_document_soft_gate_trace(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    document_facade: CanonicalDocumentFacadeV1,
    route_context: DocumentSoftGateRouteContextV1,
    correlation_id: str | None = None,
    request_id: str | None = None,
) -> DocumentSoftGateTraceV1:
    blockers = _build_soft_gate_blockers(
        document_facade=document_facade,
        case_snapshot=case_snapshot,
    )
    materialization_would_be_blocked = any(
        item.blocking and item.applies_to_materialization for item in blockers
    )
    issue_would_be_blocked = any(
        item.blocking and item.applies_to_issue for item in blockers
    )

    decision_sources = {
        "document_soft_gate",
        "document_facade",
        "technical_case_acl",
    }
    for blocker in blockers:
        if blocker.source:
            decision_sources.add(blocker.source)
    if document_facade.legacy_pipeline_shadow is not None:
        decision_sources.add("document_shadow")

    decision = DocumentSoftGateDecisionV1(
        tenant_id=case_snapshot.tenant_id,
        case_id=case_snapshot.case_ref.case_id,
        legacy_laudo_id=case_snapshot.case_ref.legacy_laudo_id,
        document_id=case_snapshot.case_ref.document_id,
        template_id=document_facade.template_binding.template_id,
        template_key=document_facade.template_binding.template_key,
        template_source_kind=document_facade.template_binding.template_source_kind,
        route_context=route_context,
        materialization_would_be_blocked=materialization_would_be_blocked,
        issue_would_be_blocked=issue_would_be_blocked,
        blockers=blockers,
        current_case_status=case_snapshot.canonical_status,
        current_review_status=document_facade.document_readiness.current_review_status,
        canonic_document_status=document_facade.document_readiness.current_document_status,
        document_readiness=document_facade.document_readiness.readiness_state,
        policy_summary=document_facade.document_policy.model_dump(mode="python"),
        provenance_summary=document_facade.document_readiness.provenance_summary,
        decision_source=sorted(decision_sources),
        correlation_id=correlation_id or case_snapshot.correlation_id,
        request_id=request_id or correlation_id or case_snapshot.correlation_id,
    )

    return DocumentSoftGateTraceV1(
        trace_id=uuid.uuid4().hex,
        tenant_id=decision.tenant_id,
        case_id=decision.case_id,
        legacy_laudo_id=decision.legacy_laudo_id,
        route_context=route_context,
        decision=decision,
        correlation_id=decision.correlation_id,
        request_id=decision.request_id,
    )


__all__ = [
    "build_document_soft_gate_route_context",
    "build_document_soft_gate_trace",
]
