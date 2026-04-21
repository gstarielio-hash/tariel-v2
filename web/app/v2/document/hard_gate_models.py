"""Modelos canonicos do primeiro hard gate documental controlado do V2."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.envelopes import utc_now

DocumentHardGateMode = Literal["disabled", "shadow_only", "enforce_controlled"]
DocumentHardGateBlockerScope = Literal["enforce", "shadow_only"]


class DocumentHardGateBlockerV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentHardGateBlockerV1"] = "DocumentHardGateBlockerV1"
    contract_version: str = "v1"
    blocker_code: str
    blocker_kind: str
    message: str
    source: str | None = None
    signal_state: str | None = None
    blocking: bool = True
    applies_to_current_operation: bool = True
    enforcement_scope: DocumentHardGateBlockerScope = "enforce"
    enforce_blocking: bool = True


class DocumentHardGateDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentHardGateDecisionV1"] = "DocumentHardGateDecisionV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    document_id: str | None = None
    operation_kind: str
    route_name: str | None = None
    route_path: str | None = None
    source_channel: str | None = None
    legacy_pipeline_name: str | None = None
    hard_gate_enabled: bool
    enforce_requested: bool = False
    enforce_enabled: bool = False
    shadow_only: bool = False
    local_request: bool = False
    tenant_allowlisted: bool = False
    operation_allowlisted: bool = False
    would_block: bool
    did_block: bool
    blockers: list[DocumentHardGateBlockerV1] = Field(default_factory=list)
    decision_source: list[str] = Field(default_factory=list)
    policy_summary: dict[str, Any] = Field(default_factory=dict)
    document_readiness: dict[str, Any] = Field(default_factory=dict)
    provenance_summary: dict[str, Any] | None = None
    mode: DocumentHardGateMode = "disabled"
    correlation_id: str | None = None
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class DocumentHardGateEnforcementResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentHardGateEnforcementResultV1"] = (
        "DocumentHardGateEnforcementResultV1"
    )
    contract_version: str = "v1"
    decision: DocumentHardGateDecisionV1
    blocked_response_status: int | None = None
    blocked_response_code: str | None = None
    blocked_response_message: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class DocumentHardGateSummaryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["DocumentHardGateSummaryV1"] = "DocumentHardGateSummaryV1"
    contract_version: str = "v1"
    feature_flags: dict[str, Any] = Field(default_factory=dict)
    totals: dict[str, int] = Field(default_factory=dict)
    by_operation_kind: list[dict[str, Any]] = Field(default_factory=list)
    by_blocker_code: list[dict[str, Any]] = Field(default_factory=list)
    by_tenant: list[dict[str, Any]] = Field(default_factory=list)
    recent_results: list[DocumentHardGateEnforcementResultV1] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


__all__ = [
    "DocumentHardGateBlockerV1",
    "DocumentHardGateBlockerScope",
    "DocumentHardGateDecisionV1",
    "DocumentHardGateEnforcementResultV1",
    "DocumentHardGateMode",
    "DocumentHardGateSummaryV1",
]
