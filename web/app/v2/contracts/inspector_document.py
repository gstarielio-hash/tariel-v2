"""Projecao documental dedicada do inspetor no V2."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.acl.technical_case_core import TechnicalCaseStatusSnapshot
from app.v2.contracts.envelopes import ProjectionEnvelope
from app.v2.document.models import CanonicalDocumentFacadeV1


class InspectorDocumentStatusSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_case_status: str
    current_review_status: str | None = None
    current_document_status: str
    readiness_state: str
    materialization_allowed: bool
    issue_allowed: bool
    review_required: bool | None = None
    engineer_approval_required: bool | None = None
    has_form_data: bool | None = None
    has_ai_draft: bool | None = None
    template_source_kind: str = "unknown"


class InspectorDocumentTemplateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: int | None = None
    template_key: str | None = None
    template_version: int | None = None
    binding_status: str
    template_source_kind: str = "unknown"
    legacy_template_status: str | None = None
    legacy_template_mode: str | None = None
    legacy_pdf_base_available: bool | None = None
    legacy_editor_document_present: bool | None = None


class InspectorDocumentPolicySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_required: bool | None = None
    review_mode: str | None = None
    engineer_approval_required: bool | None = None
    materialization_allowed: bool | None = None
    issue_allowed: bool | None = None
    policy_source_summary: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class InspectorDocumentBlockerItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocker_code: str
    blocker_kind: str
    message: str
    blocking: bool = True
    source: str | None = None


class InspectorDocumentLegacyPipelineSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_name: str
    materialization_allowed: bool
    issue_allowed: bool
    compatibility_state: str
    comparison_quality: str
    divergences: list[str] = Field(default_factory=list)
    template_resolution: dict[str, Any] = Field(default_factory=dict)


class InspectorDocumentViewProjectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legacy_laudo_id: int | None = None
    document_status_summary: InspectorDocumentStatusSummary
    template_summary: InspectorDocumentTemplateSummary
    policy_summary: InspectorDocumentPolicySummary
    provenance_summary: dict[str, Any] | None = None
    blockers: list[InspectorDocumentBlockerItem] = Field(default_factory=list)
    legacy_pipeline_summary: InspectorDocumentLegacyPipelineSummary | None = None
    case_snapshot_timestamp: datetime | None = None


class InspectorDocumentViewProjectionV1(ProjectionEnvelope):
    contract_name: Literal["InspectorDocumentViewProjectionV1"] = "InspectorDocumentViewProjectionV1"
    projection_name: Literal["InspectorDocumentViewProjectionV1"] = "InspectorDocumentViewProjectionV1"
    projection_audience: Literal["inspetor_document_web"] = "inspetor_document_web"
    projection_type: Literal["document_operational_read_model"] = "document_operational_read_model"


def build_inspector_document_view_projection(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    document_facade: CanonicalDocumentFacadeV1,
    actor_id: Any,
    actor_role: str,
    source_channel: str,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> InspectorDocumentViewProjectionV1:
    case_ref = case_snapshot.case_ref
    readiness = document_facade.document_readiness
    template_binding = document_facade.template_binding
    policy = document_facade.document_policy
    legacy_shadow = document_facade.legacy_pipeline_shadow

    payload = InspectorDocumentViewProjectionPayload(
        legacy_laudo_id=case_ref.legacy_laudo_id,
        document_status_summary=InspectorDocumentStatusSummary(
            current_case_status=readiness.current_case_status,
            current_review_status=readiness.current_review_status,
            current_document_status=readiness.current_document_status,
            readiness_state=readiness.readiness_state,
            materialization_allowed=readiness.materialization_allowed,
            issue_allowed=readiness.issue_allowed,
            review_required=readiness.review_required,
            engineer_approval_required=readiness.engineer_approval_required,
            has_form_data=readiness.has_form_data,
            has_ai_draft=readiness.has_ai_draft,
            template_source_kind=readiness.template_source_kind,
        ),
        template_summary=InspectorDocumentTemplateSummary(
            template_id=template_binding.template_id,
            template_key=template_binding.template_key,
            template_version=template_binding.template_version,
            binding_status=template_binding.binding_status,
            template_source_kind=template_binding.template_source_kind,
            legacy_template_status=template_binding.legacy_template_status,
            legacy_template_mode=template_binding.legacy_template_mode,
            legacy_pdf_base_available=template_binding.legacy_pdf_base_available,
            legacy_editor_document_present=template_binding.legacy_editor_document_present,
        ),
        policy_summary=InspectorDocumentPolicySummary(
            review_required=policy.review_required,
            review_mode=policy.review_mode,
            engineer_approval_required=policy.engineer_approval_required,
            materialization_allowed=policy.materialization_allowed,
            issue_allowed=policy.issue_allowed,
            policy_source_summary=dict(policy.policy_source_summary),
            rationale=policy.rationale,
        ),
        provenance_summary=(
            dict(readiness.provenance_summary)
            if isinstance(readiness.provenance_summary, dict)
            else readiness.provenance_summary
        ),
        blockers=[
            InspectorDocumentBlockerItem(
                blocker_code=item.blocker_code,
                blocker_kind=item.blocker_kind,
                message=item.message,
                blocking=item.blocking,
                source=item.source,
            )
            for item in readiness.blockers
        ],
        legacy_pipeline_summary=(
            InspectorDocumentLegacyPipelineSummary(
                pipeline_name=legacy_shadow.pipeline_name,
                materialization_allowed=legacy_shadow.materialization_allowed,
                issue_allowed=legacy_shadow.issue_allowed,
                compatibility_state=legacy_shadow.comparison.compatibility_state,
                comparison_quality=legacy_shadow.comparison.comparison_quality,
                divergences=list(legacy_shadow.comparison.divergences),
                template_resolution=dict(legacy_shadow.template_resolution),
            )
            if legacy_shadow is not None
            else None
        ),
        case_snapshot_timestamp=case_snapshot.timestamp,
    )

    return InspectorDocumentViewProjectionV1(
        tenant_id=case_snapshot.tenant_id,
        case_id=case_ref.case_id,
        thread_id=case_ref.thread_id,
        document_id=case_ref.document_id,
        actor_id=str(actor_id),
        actor_role=actor_role,
        correlation_id=correlation_id or case_snapshot.correlation_id or uuid.uuid4().hex,
        causation_id=causation_id,
        idempotency_key=idempotency_key or f"inspector-document-view:{case_ref.legacy_laudo_id or 'none'}",
        source_channel=source_channel,
        origin_kind=document_facade.origin_kind,
        sensitivity="technical",
        visibility_scope="actor_document",
        timestamp=timestamp or case_snapshot.timestamp,
        payload=payload.model_dump(mode="python"),
    )


__all__ = [
    "InspectorDocumentBlockerItem",
    "InspectorDocumentLegacyPipelineSummary",
    "InspectorDocumentPolicySummary",
    "InspectorDocumentStatusSummary",
    "InspectorDocumentTemplateSummary",
    "InspectorDocumentViewProjectionPayload",
    "InspectorDocumentViewProjectionV1",
    "build_inspector_document_view_projection",
]
