"""Modelos canonicos do policy engine incremental do V2."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.envelopes import utc_now

PolicySourceKind = Literal["tenant", "template", "default", "system"]
ReviewMode = Literal[
    "none",
    "optional",
    "required",
    "mesa_required",
    "engineer_required",
    "mobile_review_allowed",
    "mobile_autonomous",
]


class PolicySourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["PolicySourceRefV1"] = "PolicySourceRefV1"
    contract_version: str = "v1"
    policy_source_kind: PolicySourceKind
    policy_source_id: str | None = None
    tenant_id: str | None = None
    template_key: str | None = None
    summary: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class ReviewRequirementDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["ReviewRequirementDecisionV1"] = "ReviewRequirementDecisionV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    template_key: str | None = None
    laudo_type: str | None = None
    review_required: bool
    review_mode: ReviewMode
    engineer_approval_required: bool
    policy_source: PolicySourceRef
    certainty: str | None = None
    rationale: str | None = None
    family_policy_summary: dict[str, Any] = Field(default_factory=dict)
    tenant_entitlements: dict[str, Any] = Field(default_factory=dict)
    runtime_operational_context: dict[str, Any] = Field(default_factory=dict)
    red_flags: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class DocumentMaterializationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentMaterializationDecisionV1"] = "DocumentMaterializationDecisionV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    template_key: str | None = None
    document_type: str | None = None
    document_materialization_allowed: bool
    document_issue_allowed: bool
    policy_source: PolicySourceRef
    certainty: str | None = None
    rationale: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class PolicyDecisionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["PolicyDecisionSummaryV1"] = "PolicyDecisionSummaryV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    template_key: str | None = None
    laudo_type: str | None = None
    document_type: str | None = None
    review_required: bool
    review_mode: ReviewMode
    engineer_approval_required: bool
    document_materialization_allowed: bool
    document_issue_allowed: bool
    primary_policy_source_kind: PolicySourceKind
    primary_policy_source_id: str | None = None
    source_summary: dict[str, dict[str, object]] = Field(default_factory=dict)
    rationale: str | None = None
    certainty: str | None = None
    family_policy_summary: dict[str, Any] = Field(default_factory=dict)
    tenant_entitlements: dict[str, Any] = Field(default_factory=dict)
    runtime_operational_context: dict[str, Any] = Field(default_factory=dict)
    red_flags: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class TechnicalCasePolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["TechnicalCasePolicyDecisionV1"] = "TechnicalCasePolicyDecisionV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    template_key: str | None = None
    laudo_type: str | None = None
    document_type: str | None = None
    review: ReviewRequirementDecision
    document: DocumentMaterializationDecision
    summary: PolicyDecisionSummary
    timestamp: datetime = Field(default_factory=utc_now)


__all__ = [
    "DocumentMaterializationDecision",
    "PolicyDecisionSummary",
    "PolicySourceKind",
    "PolicySourceRef",
    "ReviewMode",
    "ReviewRequirementDecision",
    "TechnicalCasePolicyDecision",
]
