"""Facade documental incremental do V2 para readiness e binding canonicos."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.v2.acl.technical_case_core import TechnicalCaseStatusSnapshot
from app.v2.billing import TenantPolicyCapabilitySnapshot
from app.v2.contracts.provenance import ContentOriginSummary
from app.v2.document.models import (
    CanonicalDocumentFacadeV1,
    DocumentBlockerSummary,
    DocumentGovernanceSummaryV1,
    DocumentMaterializationReadinessV1,
    DocumentPolicyViewSummary,
)
from app.v2.document.template_binding import resolve_document_template_binding
from app.v2.policy import TechnicalCasePolicyDecision, build_technical_case_policy_decision


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _has_meaningful_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def _resolve_current_document_status(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    has_form_data: bool,
    has_ai_draft: bool,
) -> str:
    if not case_snapshot.has_active_report:
        return "not_started"
    if case_snapshot.canonical_status == "approved":
        return "approved_for_issue"
    if has_form_data or has_ai_draft:
        return "partially_filled"
    return "draft_document"


def _build_document_policy_view(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    policy_decision: TechnicalCasePolicyDecision | None,
    template_key: str | None,
    tenant_policy_context: TenantPolicyCapabilitySnapshot | None,
) -> tuple[TechnicalCasePolicyDecision, DocumentPolicyViewSummary]:
    resolved_policy_decision = policy_decision or build_technical_case_policy_decision(
        case_snapshot=case_snapshot,
        template_key=template_key,
        laudo_type=template_key,
        document_type=template_key,
        tenant_policy_context=tenant_policy_context,
    )
    summary = resolved_policy_decision.summary
    return resolved_policy_decision, DocumentPolicyViewSummary(
        tenant_id=summary.tenant_id,
        case_id=summary.case_id,
        template_key=summary.template_key,
        review_required=summary.review_required,
        review_mode=summary.review_mode,
        engineer_approval_required=summary.engineer_approval_required,
        materialization_allowed=summary.document_materialization_allowed,
        issue_allowed=summary.document_issue_allowed,
        policy_source_summary=dict(summary.source_summary),
        rationale=summary.rationale,
    )


def _build_document_blockers(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    template_bound: bool,
    policy_view: DocumentPolicyViewSummary,
    provenance_summary: ContentOriginSummary | None,
) -> list[DocumentBlockerSummary]:
    blockers: list[DocumentBlockerSummary] = []
    if not case_snapshot.has_active_report:
        blockers.append(
            DocumentBlockerSummary(
                blocker_code="no_active_report",
                blocker_kind="data",
                message="Nao existe laudo ativo para materializacao canonica.",
                blocking=True,
                source="technical_case_acl",
            )
        )
    if not template_bound:
        blockers.append(
            DocumentBlockerSummary(
                blocker_code="template_not_bound",
                blocker_kind="template",
                message="Nao ha template ativo vinculado na biblioteca para materializacao canonica.",
                blocking=True,
                source="template_binding",
            )
        )
    if not bool(policy_view.materialization_allowed):
        blockers.append(
            DocumentBlockerSummary(
                blocker_code="materialization_disallowed_by_policy",
                blocker_kind="policy",
                message="A politica minima atual nao permite materializacao documental neste estado.",
                blocking=True,
                source="policy_engine",
            )
        )
    if bool(policy_view.review_required) and case_snapshot.canonical_status != "approved":
        blockers.append(
            DocumentBlockerSummary(
                blocker_code="review_still_required_for_issue",
                blocker_kind="review",
                message="A Mesa ainda participa do gate documental antes da emissao.",
                blocking=False,
                source="policy_engine",
            )
        )
    if bool(policy_view.engineer_approval_required) and not bool(policy_view.issue_allowed):
        blockers.append(
            DocumentBlockerSummary(
                blocker_code="engineer_approval_pending",
                blocker_kind="approval",
                message="A aprovacao humana final ainda nao esta satisfeita para emissao.",
                blocking=False,
                source="policy_engine",
            )
        )
    if provenance_summary is not None and provenance_summary.has_legacy_unknown_content:
        blockers.append(
            DocumentBlockerSummary(
                blocker_code="legacy_content_origin_unknown",
                blocker_kind="document",
                message="Parte do conteudo legado ainda tem origem documental incerta.",
                blocking=False,
                source="provenance",
            )
        )
    return blockers


def _build_document_governance(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    template_source_kind: str,
    policy_view: DocumentPolicyViewSummary,
    provenance_summary: ContentOriginSummary | None,
) -> DocumentGovernanceSummaryV1:
    has_ai_content = False
    provenance_quality: str | None = None
    provenance_has_legacy_unknown_content = False
    if provenance_summary is not None:
        has_ai_content = bool(
            provenance_summary.has_ai_outputs
            or provenance_summary.has_ai_assisted_content
        )
        provenance_quality = str(provenance_summary.quality or "").strip() or None
        provenance_has_legacy_unknown_content = bool(
            provenance_summary.has_legacy_unknown_content
        )

    human_approval_state = "not_required"
    if bool(policy_view.engineer_approval_required):
        human_approval_state = (
            "required_satisfied" if bool(policy_view.issue_allowed) else "required_pending"
        )

    if template_source_kind in {"editor_rico", "docx_word"}:
        template_editability_status = "editable_source_available"
    elif template_source_kind == "legacy_pdf":
        template_editability_status = "legacy_pdf_transition"
    else:
        template_editability_status = "unknown"

    return DocumentGovernanceSummaryV1(
        tenant_id=case_snapshot.tenant_id,
        case_id=case_snapshot.case_ref.case_id,
        template_source_kind=template_source_kind,
        template_editability_status=template_editability_status,
        has_ai_content=has_ai_content,
        ai_transparency_status=(
            "pending_legal_definition" if has_ai_content else "not_applicable"
        ),
        human_approval_state=human_approval_state,
        provenance_quality=provenance_quality,
        provenance_has_legacy_unknown_content=provenance_has_legacy_unknown_content,
    )


def build_canonical_document_facade(
    *,
    banco: Session | None,
    case_snapshot: TechnicalCaseStatusSnapshot,
    source_channel: str,
    template_key: Any = None,
    policy_decision: TechnicalCasePolicyDecision | None = None,
    tenant_policy_context: TenantPolicyCapabilitySnapshot | None = None,
    provenance_summary: ContentOriginSummary | None = None,
    current_review_status: Any = None,
    has_form_data: bool = False,
    has_ai_draft: bool = False,
) -> CanonicalDocumentFacadeV1:
    template_key_text = _normalize_optional_text(template_key)
    resolved_policy_decision, policy_view = _build_document_policy_view(
        case_snapshot=case_snapshot,
        policy_decision=policy_decision,
        template_key=template_key_text,
        tenant_policy_context=tenant_policy_context,
    )
    template_binding = resolve_document_template_binding(
        banco=banco,
        case_snapshot=case_snapshot,
        template_key=template_key_text,
        source_channel=source_channel,
    )
    blockers = _build_document_blockers(
        case_snapshot=case_snapshot,
        template_bound=template_binding.binding_status == "bound",
        policy_view=policy_view,
        provenance_summary=provenance_summary,
    )

    if not case_snapshot.has_active_report:
        readiness_state = "not_applicable"
    elif any(item.blocking for item in blockers):
        readiness_state = "blocked"
    elif bool(policy_view.issue_allowed):
        readiness_state = "ready_for_issue"
    else:
        readiness_state = "ready_for_materialization"

    case_ref = case_snapshot.case_ref
    readiness = DocumentMaterializationReadinessV1(
        tenant_id=case_snapshot.tenant_id,
        case_id=case_ref.case_id,
        legacy_laudo_id=case_ref.legacy_laudo_id,
        document_id=case_ref.document_id,
        thread_id=case_ref.thread_id,
        template_id=template_binding.template_id,
        template_key=template_binding.template_key,
        template_source_kind=template_binding.template_source_kind,
        materialization_allowed=bool(policy_view.materialization_allowed),
        issue_allowed=bool(policy_view.issue_allowed),
        review_required=policy_view.review_required,
        engineer_approval_required=policy_view.engineer_approval_required,
        current_case_status=case_snapshot.canonical_status,
        current_review_status=_normalize_optional_text(current_review_status) or case_snapshot.legacy_review_status,
        current_document_status=_resolve_current_document_status(
            case_snapshot=case_snapshot,
            has_form_data=bool(has_form_data),
            has_ai_draft=bool(has_ai_draft),
        ),
        has_form_data=bool(has_form_data),
        has_ai_draft=bool(has_ai_draft),
        provenance_summary=(
            provenance_summary.model_dump(mode="python")
            if provenance_summary is not None
            else None
        ),
        blockers=blockers,
        policy_source_summary=dict(policy_view.policy_source_summary),
        readiness_state=readiness_state,
    )
    governance = _build_document_governance(
        case_snapshot=case_snapshot,
        template_source_kind=template_binding.template_source_kind,
        policy_view=policy_view,
        provenance_summary=provenance_summary,
    )

    return CanonicalDocumentFacadeV1(
        tenant_id=case_snapshot.tenant_id,
        case_id=case_ref.case_id,
        legacy_laudo_id=case_ref.legacy_laudo_id,
        document_id=case_ref.document_id,
        thread_id=case_ref.thread_id,
        origin_kind=case_snapshot.origin_kind,
        source_channel=source_channel,
        template_binding=template_binding,
        document_policy=policy_view,
        document_readiness=readiness,
        document_governance=governance,
    )


__all__ = ["build_canonical_document_facade"]
