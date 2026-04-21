"""Modelos canonicos do soft gate documental incremental do V2."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.envelopes import utc_now

DocumentSoftGateOperationKind = Literal[
    "preview_pdf",
    "review_package_read",
    "review_package_pdf_export",
    "report_finalize",
    "report_finalize_stream",
    "template_publish_activate",
    "review_approve",
    "review_reject",
    "review_issue",
]
DocumentSoftGateBlockerKind = Literal[
    "template",
    "policy",
    "review",
    "approval",
    "data",
    "document",
    "provenance",
    "unknown",
]
DocumentSoftGateSignalState = Literal["confirmed", "derived", "unknown"]


class DocumentSoftGateRouteContextV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentSoftGateRouteContextV1"] = (
        "DocumentSoftGateRouteContextV1"
    )
    contract_version: str = "v1"
    route_name: str
    route_path: str
    http_method: str
    source_channel: str
    operation_kind: DocumentSoftGateOperationKind
    side_effect_free: bool = True
    legacy_pipeline_name: str | None = None
    legacy_compatibility_state: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class DocumentSoftGateBlockerV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentSoftGateBlockerV1"] = "DocumentSoftGateBlockerV1"
    contract_version: str = "v1"
    blocker_code: str
    blocker_kind: DocumentSoftGateBlockerKind
    message: str
    source: str | None = None
    signal_state: DocumentSoftGateSignalState = "derived"
    blocking: bool = True
    applies_to_materialization: bool = False
    applies_to_issue: bool = False


class DocumentSoftGateDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentSoftGateDecisionV1"] = "DocumentSoftGateDecisionV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    document_id: str | None = None
    template_id: int | None = None
    template_key: str | None = None
    template_source_kind: str | None = None
    route_context: DocumentSoftGateRouteContextV1
    materialization_would_be_blocked: bool
    issue_would_be_blocked: bool
    blockers: list[DocumentSoftGateBlockerV1] = Field(default_factory=list)
    current_case_status: str | None = None
    current_review_status: str | None = None
    canonic_document_status: str | None = None
    document_readiness: str | None = None
    policy_summary: dict[str, Any] = Field(default_factory=dict)
    provenance_summary: dict[str, Any] | None = None
    decision_source: list[str] = Field(default_factory=list)
    source_kind: Literal["document_soft_gate"] = "document_soft_gate"
    correlation_id: str | None = None
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class DocumentSoftGateTraceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentSoftGateTraceV1"] = "DocumentSoftGateTraceV1"
    contract_version: str = "v1"
    trace_id: str
    tenant_id: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    route_context: DocumentSoftGateRouteContextV1
    decision: DocumentSoftGateDecisionV1
    correlation_id: str | None = None
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class DocumentSoftGateSummaryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentSoftGateSummaryV1"] = "DocumentSoftGateSummaryV1"
    contract_version: str = "v1"
    feature_flag: str
    totals: dict[str, int] = Field(default_factory=dict)
    by_operation_kind: list[dict[str, Any]] = Field(default_factory=list)
    by_blocker_code: list[dict[str, Any]] = Field(default_factory=list)
    by_tenant: list[dict[str, Any]] = Field(default_factory=list)
    recent_traces: list[DocumentSoftGateTraceV1] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


__all__ = [
    "DocumentSoftGateBlockerV1",
    "DocumentSoftGateDecisionV1",
    "DocumentSoftGateOperationKind",
    "DocumentSoftGateRouteContextV1",
    "DocumentSoftGateSignalState",
    "DocumentSoftGateSummaryV1",
    "DocumentSoftGateTraceV1",
]
