"""Projecao canonica incremental para o portal admin-cliente."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.acl.technical_case_snapshot import TechnicalCaseSnapshotV1
from app.v2.billing import build_tenant_billing_metering_snapshot
from app.v2.contracts.envelopes import ProjectionEnvelope, utc_now


class TenantAdminSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    tenant_name: str
    tenant_status: str


class TenantAdminCaseCountsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_cases: int = 0
    open_cases: int = 0
    approved_cases: int = 0
    issued_cases: int = 0


class TenantAdminReviewCountsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pending_review: int = 0
    in_review: int = 0
    sent_back_for_adjustment: int = 0


class TenantAdminDocumentCountsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_documents: int = 0
    issued_documents: int = 0
    approved_for_issue: int = 0


class TenantAdminBillingSnapshotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_name: str
    usage_status: str
    usage_percent: int | None = None
    recommended_plan: str | None = None


class TenantAdminUserSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_users: int = 0
    active_users: int = 0
    inspectors: int = 0
    reviewers: int = 0
    admin_clients: int = 0


class TenantAdminVisibilityPolicyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    management_projection_authoritative: bool = True
    technical_access_mode: Literal["surface_scoped_operational"] = "surface_scoped_operational"
    per_case_visibility_configurable: bool = True
    per_case_action_configurable: bool = True
    per_case_governance_owner: Literal["admin_ceo_contract_setup"] = (
        "admin_ceo_contract_setup"
    )
    commercial_operating_model: Literal["standard", "mobile_single_operator"] = "standard"
    mobile_primary: bool = False
    contract_operational_user_limit: int | None = None
    shared_mobile_operator_enabled: bool = False
    shared_mobile_operator_web_inspector_enabled: bool = False
    shared_mobile_operator_web_review_enabled: bool = False
    shared_mobile_operator_surface_set: list[str] = Field(default_factory=list)
    operational_user_cross_portal_enabled: bool = False
    operational_user_admin_portal_enabled: bool = False
    tenant_assignable_portal_set: list[Literal["cliente", "inspetor", "revisor"]] = (
        Field(default_factory=lambda: ["inspetor", "revisor"])
    )
    commercial_package_scope: Literal["tenant_isolated_contract"] = "tenant_isolated_contract"
    commercial_capability_axes: list[
        Literal[
            "mesa",
            "offline",
            "retention",
            "sla",
            "branding",
            "guided_flow_depth",
            "mobile_unified_operator",
        ]
    ] = Field(
        default_factory=lambda: [
            "mesa",
            "offline",
            "retention",
            "sla",
            "branding",
            "guided_flow_depth",
            "mobile_unified_operator",
        ]
    )
    cross_surface_session_strategy: Literal["governed_links_and_grants"] = (
        "governed_links_and_grants"
    )
    cross_surface_session_unified: bool = False
    cross_surface_session_note: str = (
        "A continuidade entre mobile, inspetor web e mesa web segue grants e "
        "links governados pelo tenant; sessao unica real continua como "
        "evolucao futura opcional."
    )
    operational_identity_slots_in_use: int = 0
    operational_identity_slots_remaining: int | None = None
    admin_client_case_visibility_mode: Literal["summary_only", "case_list"] = "case_list"
    admin_client_case_action_mode: Literal["read_only", "case_actions"] = "case_actions"
    case_list_visible: bool = True
    case_actions_enabled: bool = True
    raw_evidence_access: Literal["not_granted_by_projection"] = "not_granted_by_projection"
    issued_document_access: Literal["tenant_scope_only"] = "tenant_scope_only"
    exceptional_support_access: Literal["disabled", "approval_required", "incident_controlled"] = (
        "approval_required"
    )
    exceptional_support_scope_level: Literal["metadata_only", "administrative", "tenant_diagnostic"] = (
        "administrative"
    )
    support_exceptional_protocol: Literal["approval_scoped_temporary_audited"] = (
        "approval_scoped_temporary_audited"
    )
    exceptional_support_step_up_required: bool = True
    exceptional_support_approval_required: bool = True
    exceptional_support_justification_required: bool = True
    exceptional_support_max_duration_minutes: int = 120
    tenant_retention_policy_owner: Literal["admin_ceo_contract_setup"] = (
        "admin_ceo_contract_setup"
    )
    technical_case_retention_min_days: int = 365
    issued_document_retention_min_days: int = 1825
    audit_retention_min_days: int = 1825
    human_signoff_required: bool = True
    ai_assistance_audit_required: bool = True
    human_override_justification_required: bool = True
    consent_collection_mode: Literal["tenant_terms_and_user_notice"] = (
        "tenant_terms_and_user_notice"
    )
    mandatory_audit_fields: list[str] = Field(
        default_factory=lambda: [
            "actor_user_id",
            "actor_role",
            "tenant_id",
            "case_id",
            "case_lifecycle_status",
            "ai_assistance_present",
            "human_override_reason",
            "human_override_recorded_at",
            "final_signatory_name",
            "final_signatory_registration",
            "issued_document_version",
        ]
    )
    audit_scope: Literal["tenant_operational_timeline"] = "tenant_operational_timeline"
    audit_categories_visible: list[Literal["access", "commercial", "team", "support", "chat", "mesa"]] = (
        Field(default_factory=lambda: ["access", "commercial", "team", "support", "chat", "mesa"])
    )


class TenantAdminViewProjectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_summary: TenantAdminSummaryPayload
    case_counts: TenantAdminCaseCountsPayload
    review_counts: TenantAdminReviewCountsPayload
    document_counts: TenantAdminDocumentCountsPayload
    billing_snapshot: TenantAdminBillingSnapshotPayload
    user_summary: TenantAdminUserSummaryPayload
    visibility_policy: TenantAdminVisibilityPolicyPayload = Field(
        default_factory=TenantAdminVisibilityPolicyPayload
    )
    allowed_document_refs: list[str] = Field(default_factory=list)
    observed_case_ids: list[str] = Field(default_factory=list)


class TenantAdminViewProjectionV1(ProjectionEnvelope):
    contract_name: Literal["TenantAdminViewProjectionV1"] = "TenantAdminViewProjectionV1"
    projection_name: Literal["TenantAdminViewProjectionV1"] = "TenantAdminViewProjectionV1"
    projection_audience: Literal["tenant_admin_web"] = "tenant_admin_web"
    projection_type: Literal["tenant_admin_projection"] = "tenant_admin_projection"


def _iter_snapshots(case_snapshots: Iterable[TechnicalCaseSnapshotV1]) -> list[TechnicalCaseSnapshotV1]:
    return list(case_snapshots)


def build_tenant_admin_view_projection(
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
    visibility_policy: TenantAdminVisibilityPolicyPayload | dict[str, Any] | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> TenantAdminViewProjectionV1:
    snapshots = _iter_snapshots(case_snapshots)
    tenant_id_text = str(tenant_id or "").strip()
    now = timestamp or utc_now()
    resolved_visibility_policy = TenantAdminVisibilityPolicyPayload.model_validate(visibility_policy or {})
    case_refs_visible = bool(resolved_visibility_policy.case_list_visible)
    allowed_document_refs = (
        sorted(
            {
                str(item.active_document_version_id or item.case_ref.document_id or "").strip()
                for item in snapshots
                if item.current_document_state == "issued"
                and str(item.active_document_version_id or item.case_ref.document_id or "").strip()
            }
        )
        if case_refs_visible
        else []
    )
    payload = TenantAdminViewProjectionPayload(
        tenant_summary=TenantAdminSummaryPayload(
            tenant_id=tenant_id_text,
            tenant_name=str(tenant_name or "").strip(),
            tenant_status=str(tenant_status or "").strip() or "active",
        ),
        case_counts=TenantAdminCaseCountsPayload(
            total_cases=len(snapshots),
            open_cases=sum(1 for item in snapshots if item.case_state not in {"issued", "archived"}),
            approved_cases=sum(1 for item in snapshots if item.case_state == "approved"),
            issued_cases=sum(1 for item in snapshots if item.case_state == "issued"),
        ),
        review_counts=TenantAdminReviewCountsPayload(
            pending_review=sum(1 for item in snapshots if item.current_review_state == "pending_review"),
            in_review=sum(1 for item in snapshots if item.current_review_state == "in_review"),
            sent_back_for_adjustment=sum(
                1 for item in snapshots if item.current_review_state == "sent_back_for_adjustment"
            ),
        ),
        document_counts=TenantAdminDocumentCountsPayload(
            draft_documents=sum(
                1
                for item in snapshots
                if item.current_document_state in {
                    "draft_document",
                    "partially_filled",
                    "awaiting_approval",
                    "approved_for_issue",
                    "reopened",
                }
            ),
            issued_documents=sum(1 for item in snapshots if item.current_document_state == "issued"),
            approved_for_issue=sum(
                1 for item in snapshots if item.current_document_state == "approved_for_issue"
            ),
        ),
        billing_snapshot=TenantAdminBillingSnapshotPayload(
            **build_tenant_billing_metering_snapshot(
                plan_name=plan_name,
                usage_status=usage_status,
                usage_percent=usage_percent,
                recommended_plan=recommended_plan,
            ).model_dump(mode="python")
        ),
        user_summary=TenantAdminUserSummaryPayload(
            total_users=max(0, int(total_users or 0)),
            active_users=max(0, int(active_users or 0)),
            inspectors=max(0, int(inspectors or 0)),
            reviewers=max(0, int(reviewers or 0)),
            admin_clients=max(0, int(admin_clients or 0)),
        ),
        visibility_policy=resolved_visibility_policy,
        allowed_document_refs=allowed_document_refs,
        observed_case_ids=(
            [str(item.case_ref.case_id or "") for item in snapshots if item.case_ref.case_id]
            if case_refs_visible
            else []
        ),
    )

    return TenantAdminViewProjectionV1(
        tenant_id=tenant_id_text,
        actor_id=str(actor_id),
        actor_role=str(actor_role or "").strip() or "admin_cliente",
        correlation_id=correlation_id or uuid.uuid4().hex,
        causation_id=causation_id,
        idempotency_key=idempotency_key or f"tenant-admin-view:{tenant_id_text or 'unknown'}",
        source_channel=str(source_channel or "").strip() or "admin_cliente_bootstrap",
        origin_kind="system",
        sensitivity="administrative",
        visibility_scope="tenant_admin",
        timestamp=now,
        payload=payload.model_dump(mode="python"),
    )


__all__ = [
    "TenantAdminBillingSnapshotPayload",
    "TenantAdminCaseCountsPayload",
    "TenantAdminDocumentCountsPayload",
    "TenantAdminReviewCountsPayload",
    "TenantAdminSummaryPayload",
    "TenantAdminUserSummaryPayload",
    "TenantAdminVisibilityPolicyPayload",
    "TenantAdminViewProjectionPayload",
    "TenantAdminViewProjectionV1",
    "build_tenant_admin_view_projection",
]
