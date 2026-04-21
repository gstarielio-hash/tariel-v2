"""Modelos canonicos minimos da facade documental incremental do V2."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.envelopes import utc_now
from app.v2.contracts.provenance import OriginKind

DocumentTemplateSourceKind = Literal[
    "legacy_pdf",
    "editor_rico",
    "docx_word",
    "structured_template_future",
    "unknown",
]
DocumentBindingStatus = Literal["bound", "not_bound"]
DocumentReadinessState = Literal[
    "not_applicable",
    "blocked",
    "ready_for_materialization",
    "ready_for_issue",
]
DocumentBlockerKind = Literal["template", "policy", "review", "approval", "data", "document", "unknown"]
DocumentHumanApprovalState = Literal["not_required", "required_pending", "required_satisfied"]
DocumentTransparencyStatus = Literal["not_applicable", "pending_legal_definition"]
DocumentTemplateEditabilityStatus = Literal[
    "editable_source_available",
    "legacy_pdf_transition",
    "unknown",
]


class DocumentTemplateBindingRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentTemplateBindingRefV1"] = "DocumentTemplateBindingRefV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    document_id: str | None = None
    thread_id: str | None = None
    template_id: int | None = None
    template_key: str | None = None
    template_version: int | None = None
    template_source_kind: DocumentTemplateSourceKind = "unknown"
    binding_status: DocumentBindingStatus = "not_bound"
    legacy_template_status: str | None = None
    legacy_template_mode: str | None = None
    legacy_pdf_base_available: bool | None = None
    legacy_editor_document_present: bool | None = None
    source_channel: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class DocumentPolicyViewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentPolicyViewSummaryV1"] = "DocumentPolicyViewSummaryV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    template_key: str | None = None
    review_required: bool | None = None
    review_mode: str | None = None
    engineer_approval_required: bool | None = None
    materialization_allowed: bool | None = None
    issue_allowed: bool | None = None
    policy_source_summary: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class DocumentBlockerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentBlockerSummaryV1"] = "DocumentBlockerSummaryV1"
    contract_version: str = "v1"
    blocker_code: str
    blocker_kind: DocumentBlockerKind
    message: str
    blocking: bool = True
    source: str | None = None


class DocumentMaterializationReadinessV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentMaterializationReadinessV1"] = "DocumentMaterializationReadinessV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    document_id: str | None = None
    thread_id: str | None = None
    template_id: int | None = None
    template_key: str | None = None
    template_source_kind: DocumentTemplateSourceKind = "unknown"
    materialization_allowed: bool = False
    issue_allowed: bool = False
    review_required: bool | None = None
    engineer_approval_required: bool | None = None
    current_case_status: str
    current_review_status: str | None = None
    current_document_status: str
    has_form_data: bool | None = None
    has_ai_draft: bool | None = None
    provenance_summary: dict[str, Any] | None = None
    blockers: list[DocumentBlockerSummary] = Field(default_factory=list)
    policy_source_summary: dict[str, Any] = Field(default_factory=dict)
    readiness_state: DocumentReadinessState = "blocked"
    timestamp: datetime = Field(default_factory=utc_now)


class DocumentGovernanceSummaryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentGovernanceSummaryV1"] = "DocumentGovernanceSummaryV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    template_source_kind: DocumentTemplateSourceKind = "unknown"
    template_editability_status: DocumentTemplateEditabilityStatus = "unknown"
    has_ai_content: bool = False
    ai_transparency_status: DocumentTransparencyStatus = "not_applicable"
    human_approval_state: DocumentHumanApprovalState = "not_required"
    provenance_quality: str | None = None
    provenance_has_legacy_unknown_content: bool = False
    retention_policy_status: Literal["pending_legal_definition"] = "pending_legal_definition"
    timestamp: datetime = Field(default_factory=utc_now)


class LegacyDocumentPipelineShadowInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["LegacyDocumentPipelineShadowInputV1"] = "LegacyDocumentPipelineShadowInputV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    document_id: str | None = None
    thread_id: str | None = None
    source_channel: str
    template_binding: DocumentTemplateBindingRef
    document_policy: DocumentPolicyViewSummary
    document_readiness: DocumentMaterializationReadinessV1
    provenance_summary: dict[str, Any] | None = None
    legacy_preview_overlay_viable: bool | None = None
    rich_runtime_preview_viable: bool | None = None
    resolved_template_family_key: str | None = None
    resolved_template_source_kind: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class LegacyDocumentReadinessComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["LegacyDocumentReadinessComparisonV1"] = "LegacyDocumentReadinessComparisonV1"
    contract_version: str = "v1"
    canonical_materialization_allowed: bool
    legacy_materialization_allowed: bool
    canonical_issue_allowed: bool
    legacy_issue_allowed: bool
    template_binding_agrees: bool | None = None
    blockers_match: bool | None = None
    divergences: list[str] = Field(default_factory=list)
    compatibility_state: Literal["aligned", "diverged", "partial", "unknown"] = "unknown"
    comparison_quality: Literal["high", "partial", "low"] = "partial"
    timestamp: datetime = Field(default_factory=utc_now)


class LegacyDocumentPipelineShadowResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["LegacyDocumentPipelineShadowResultV1"] = "LegacyDocumentPipelineShadowResultV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    document_id: str | None = None
    thread_id: str | None = None
    pipeline_name: str
    template_resolution: dict[str, Any] = Field(default_factory=dict)
    materialization_allowed: bool = False
    issue_allowed: bool = False
    blockers: list[DocumentBlockerSummary] = Field(default_factory=list)
    comparison: LegacyDocumentReadinessComparison
    timestamp: datetime = Field(default_factory=utc_now)


class CanonicalDocumentFacadeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["CanonicalDocumentFacadeV1"] = "CanonicalDocumentFacadeV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    document_id: str | None = None
    thread_id: str | None = None
    origin_kind: OriginKind = "system"
    source_channel: str
    template_binding: DocumentTemplateBindingRef
    document_policy: DocumentPolicyViewSummary
    document_readiness: DocumentMaterializationReadinessV1
    document_governance: DocumentGovernanceSummaryV1
    legacy_pipeline_shadow: LegacyDocumentPipelineShadowResult | None = None
    timestamp: datetime = Field(default_factory=utc_now)


__all__ = [
    "CanonicalDocumentFacadeV1",
    "DocumentBlockerSummary",
    "DocumentGovernanceSummaryV1",
    "DocumentMaterializationReadinessV1",
    "DocumentPolicyViewSummary",
    "DocumentTemplateBindingRef",
    "LegacyDocumentPipelineShadowInput",
    "LegacyDocumentPipelineShadowResult",
    "LegacyDocumentReadinessComparison",
]
