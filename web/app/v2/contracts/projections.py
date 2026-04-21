"""Projeções canônicas incrementais do V2."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domains.mesa.contracts import PacoteMesaLaudo
from app.v2.acl.technical_case_core import TechnicalCaseStatusSnapshot
from app.v2.contracts.collaboration import (
    ReviewDeskCollaborationReadModel,
    build_reviewdesk_collaboration_read_model,
)
from app.v2.contracts.envelopes import ProjectionEnvelope
from app.v2.contracts.provenance import ContentOriginSummary
from app.v2.document.models import CanonicalDocumentFacadeV1
from app.v2.policy.models import TechnicalCasePolicyDecision
from app.v2.runtime import actor_role_from_user


class InspectorCaseStatusProjectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legacy_laudo_id: int | None = None
    state: str
    case_lifecycle_status: str
    case_workflow_mode: str
    active_owner_role: str
    allowed_next_lifecycle_statuses: list[str] = Field(default_factory=list)
    allowed_lifecycle_transitions: list[dict[str, Any]] = Field(default_factory=list)
    allowed_surface_actions: list[str] = Field(default_factory=list)
    human_validation_required: bool = False
    state_source: Literal["legacy_public_state", "technical_case_acl"] = "legacy_public_state"
    legacy_public_state: str | None = None
    legacy_review_status: str | None = None
    allows_reopen: bool | None = None
    has_active_report: bool = False
    laudo_card: dict[str, Any] | None = None
    legacy_payload_keys: list[str] = Field(default_factory=list)


class InspectorCaseViewProjectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legacy_laudo_id: int | None = None
    case_status: str
    case_lifecycle_status: str
    case_workflow_mode: str
    active_owner_role: str
    allowed_next_lifecycle_statuses: list[str] = Field(default_factory=list)
    allowed_lifecycle_transitions: list[dict[str, Any]] = Field(default_factory=list)
    allowed_surface_actions: list[str] = Field(default_factory=list)
    human_validation_required: bool = False
    legacy_public_state: str
    legacy_status_card: str | None = None
    legacy_review_status: str | None = None
    allows_edit: bool = False
    allows_reopen: bool | None = None
    has_active_report: bool = False
    has_interaction: bool = False
    review_requested: bool = False
    review_feedback_pending: bool = False
    review_visible_to_inspector: bool = False
    document_available: bool = False
    document_approved: bool = False
    origin_summary: dict[str, Any] | None = None
    has_human_inputs: bool | None = None
    has_ai_outputs: bool | None = None
    has_ai_assisted_content: bool | None = None
    has_legacy_unknown_content: bool | None = None
    human_vs_ai_mix: str | None = None
    provenance_quality: str | None = None
    policy_summary: dict[str, Any] | None = None
    review_required: bool | None = None
    review_mode: str | None = None
    engineer_approval_required: bool | None = None
    materialization_allowed: bool | None = None
    issue_allowed: bool | None = None
    policy_source_summary: dict[str, Any] | None = None
    policy_rationale: str | None = None
    document_readiness: dict[str, Any] | None = None
    template_binding_summary: dict[str, Any] | None = None
    document_blockers: list[dict[str, Any]] = Field(default_factory=list)
    inspection_history: dict[str, Any] | None = None
    public_verification: dict[str, Any] | None = None
    emissao_oficial: dict[str, Any] | None = None
    legacy_pipeline_shadow: dict[str, Any] | None = None
    legacy_pipeline_name: str | None = None
    legacy_template_resolution: dict[str, Any] | None = None
    legacy_materialization_allowed: bool | None = None
    legacy_issue_allowed: bool | None = None
    legacy_blockers: list[dict[str, Any]] = Field(default_factory=list)
    compatibility_summary: dict[str, Any] | None = None
    laudo_card: dict[str, Any] | None = None
    report_types: dict[str, str] = Field(default_factory=dict)
    case_snapshot_timestamp: datetime | None = None


class ReviewDeskCaseViewProjectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legacy_laudo_id: int
    codigo_hash: str
    tipo_template: str
    setor_industrial: str
    case_status: str
    case_lifecycle_status: str
    case_workflow_mode: str
    active_owner_role: str
    allowed_next_lifecycle_statuses: list[str] = Field(default_factory=list)
    allowed_lifecycle_transitions: list[dict[str, Any]] = Field(default_factory=list)
    allowed_surface_actions: list[str] = Field(default_factory=list)
    human_validation_required: bool = False
    review_status: str
    document_status: str
    legacy_review_status: str
    status_conformidade: str
    has_open_pendencies: bool
    has_recent_whispers: bool
    requires_reviewer_action: bool
    origin_summary: dict[str, Any] | None = None
    has_human_inputs: bool | None = None
    has_ai_outputs: bool | None = None
    has_ai_assisted_content: bool | None = None
    has_legacy_unknown_content: bool | None = None
    human_vs_ai_mix: str | None = None
    provenance_quality: str | None = None
    policy_summary: dict[str, Any] | None = None
    review_required: bool | None = None
    review_mode: str | None = None
    engineer_approval_required: bool | None = None
    materialization_allowed: bool | None = None
    issue_allowed: bool | None = None
    policy_source_summary: dict[str, Any] | None = None
    policy_rationale: str | None = None
    document_readiness: dict[str, Any] | None = None
    template_binding_summary: dict[str, Any] | None = None
    document_blockers: list[dict[str, Any]] = Field(default_factory=list)
    legacy_pipeline_shadow: dict[str, Any] | None = None
    legacy_pipeline_name: str | None = None
    legacy_template_resolution: dict[str, Any] | None = None
    legacy_materialization_allowed: bool | None = None
    legacy_issue_allowed: bool | None = None
    legacy_blockers: list[dict[str, Any]] = Field(default_factory=list)
    compatibility_summary: dict[str, Any] | None = None
    pending_open_count: int
    pending_resolved_count: int
    recent_whispers_count: int
    recent_reviews_count: int
    created_at: datetime
    updated_at: datetime | None = None
    last_interaction_at: datetime | None = None
    field_time_minutes: int = 0
    inspector_id: int | None = None
    reviewer_id: int | None = None
    has_form_data: bool = False
    has_ai_draft: bool = False
    summary_messages: dict[str, Any]
    summary_evidence: dict[str, Any]
    summary_pending: dict[str, Any]
    revisao_por_bloco: dict[str, Any] | None = None
    coverage_map: dict[str, Any] | None = None
    inspection_history: dict[str, Any] | None = None
    public_verification: dict[str, Any] | None = None
    anexo_pack: dict[str, Any] | None = None
    emissao_oficial: dict[str, Any] | None = None
    historico_refazer_inspetor: list[dict[str, Any]] = Field(default_factory=list)
    memoria_operacional_familia: dict[str, Any] | None = None
    collaboration: ReviewDeskCollaborationReadModel
    open_pendencies: list[dict[str, Any]] = Field(default_factory=list)
    recent_resolved_pendencies: list[dict[str, Any]] = Field(default_factory=list)
    recent_whispers: list[dict[str, Any]] = Field(default_factory=list)
    recent_reviews: list[dict[str, Any]] = Field(default_factory=list)
    dados_formulario: dict[str, Any] | None = None
    parecer_ia: str | None = None
    visibility_scope: Literal["review_desk"] = "review_desk"
    case_snapshot_timestamp: datetime | None = None


class InspectorCaseStatusProjectionV1(ProjectionEnvelope):
    contract_name: Literal["InspectorCaseStatusProjectionV1"] = "InspectorCaseStatusProjectionV1"
    projection_name: Literal["InspectorCaseStatusProjectionV1"] = "InspectorCaseStatusProjectionV1"
    projection_audience: Literal["inspetor"] = "inspetor"
    projection_type: Literal["operational_read_model"] = "operational_read_model"


class InspectorCaseViewProjectionV1(ProjectionEnvelope):
    contract_name: Literal["InspectorCaseViewProjectionV1"] = "InspectorCaseViewProjectionV1"
    projection_name: Literal["InspectorCaseViewProjectionV1"] = "InspectorCaseViewProjectionV1"
    projection_audience: Literal["inspetor"] = "inspetor"
    projection_type: Literal["operational_read_model"] = "operational_read_model"


class ReviewDeskCaseViewProjectionV1(ProjectionEnvelope):
    contract_name: Literal["ReviewDeskCaseViewProjectionV1"] = "ReviewDeskCaseViewProjectionV1"
    projection_name: Literal["ReviewDeskCaseViewProjectionV1"] = "ReviewDeskCaseViewProjectionV1"
    projection_audience: Literal["mesa"] = "mesa"
    projection_type: Literal["operational_read_model"] = "operational_read_model"


def _stringify_optional_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _projection_provenance_fields(summary: ContentOriginSummary | None) -> dict[str, Any]:
    if summary is None:
        return {
            "origin_summary": None,
            "has_human_inputs": None,
            "has_ai_outputs": None,
            "has_ai_assisted_content": None,
            "has_legacy_unknown_content": None,
            "human_vs_ai_mix": None,
            "provenance_quality": None,
        }

    return {
        "origin_summary": summary.model_dump(mode="python"),
        "has_human_inputs": summary.has_human_inputs,
        "has_ai_outputs": summary.has_ai_outputs,
        "has_ai_assisted_content": summary.has_ai_assisted_content,
        "has_legacy_unknown_content": summary.has_legacy_unknown_content,
        "human_vs_ai_mix": summary.mix_kind,
        "provenance_quality": summary.quality,
    }


def _projection_policy_fields(policy_decision: TechnicalCasePolicyDecision | None) -> dict[str, Any]:
    if policy_decision is None:
        return {
            "policy_summary": None,
            "review_required": None,
            "review_mode": None,
            "engineer_approval_required": None,
            "materialization_allowed": None,
            "issue_allowed": None,
            "policy_source_summary": None,
            "policy_rationale": None,
        }

    summary = policy_decision.summary
    return {
        "policy_summary": summary.model_dump(mode="python"),
        "review_required": summary.review_required,
        "review_mode": summary.review_mode,
        "engineer_approval_required": summary.engineer_approval_required,
        "materialization_allowed": summary.document_materialization_allowed,
        "issue_allowed": summary.document_issue_allowed,
        "policy_source_summary": dict(summary.source_summary),
        "policy_rationale": summary.rationale,
    }


def _projection_document_fields(document_facade: CanonicalDocumentFacadeV1 | None) -> dict[str, Any]:
    if document_facade is None:
        return {
            "document_readiness": None,
            "template_binding_summary": None,
            "document_blockers": [],
            "legacy_pipeline_shadow": None,
            "legacy_pipeline_name": None,
            "legacy_template_resolution": None,
            "legacy_materialization_allowed": None,
            "legacy_issue_allowed": None,
            "legacy_blockers": [],
            "compatibility_summary": None,
        }

    legacy_shadow = document_facade.legacy_pipeline_shadow
    return {
        "document_readiness": document_facade.document_readiness.model_dump(mode="python"),
        "template_binding_summary": document_facade.template_binding.model_dump(mode="python"),
        "document_blockers": [
            item.model_dump(mode="python")
            for item in document_facade.document_readiness.blockers
        ],
        "legacy_pipeline_shadow": (
            legacy_shadow.model_dump(mode="python")
            if legacy_shadow is not None
            else None
        ),
        "legacy_pipeline_name": (
            legacy_shadow.pipeline_name
            if legacy_shadow is not None
            else None
        ),
        "legacy_template_resolution": (
            dict(legacy_shadow.template_resolution)
            if legacy_shadow is not None
            else None
        ),
        "legacy_materialization_allowed": (
            legacy_shadow.materialization_allowed
            if legacy_shadow is not None
            else None
        ),
        "legacy_issue_allowed": (
            legacy_shadow.issue_allowed
            if legacy_shadow is not None
            else None
        ),
        "legacy_blockers": [
            item.model_dump(mode="python")
            for item in (legacy_shadow.blockers if legacy_shadow is not None else [])
        ],
        "compatibility_summary": (
            legacy_shadow.comparison.model_dump(mode="python")
            if legacy_shadow is not None
            else None
        ),
    }


def _projection_case_lifecycle_fields(
    case_snapshot: TechnicalCaseStatusSnapshot,
) -> dict[str, Any]:
    return {
        "case_lifecycle_status": case_snapshot.case_lifecycle_status,
        "case_workflow_mode": case_snapshot.workflow_mode,
        "active_owner_role": case_snapshot.active_owner_role,
        "allowed_next_lifecycle_statuses": list(
            case_snapshot.allowed_next_lifecycle_statuses
        ),
        "allowed_lifecycle_transitions": [
            item.model_dump(mode="python")
            for item in case_snapshot.allowed_lifecycle_transitions
        ],
        "allowed_surface_actions": list(case_snapshot.allowed_surface_actions),
        "human_validation_required": case_snapshot.human_validation_required,
    }


def build_inspector_case_status_projection_from_case_snapshot(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    actor_id: Any,
    actor_role: str,
    source_channel: str,
    legacy_payload: dict[str, Any],
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> InspectorCaseStatusProjectionV1:
    case_ref = case_snapshot.case_ref
    case_lifecycle_fields = _projection_case_lifecycle_fields(case_snapshot)
    payload = InspectorCaseStatusProjectionPayload(
        legacy_laudo_id=case_ref.legacy_laudo_id,
        state=case_snapshot.canonical_status,
        case_lifecycle_status=case_lifecycle_fields["case_lifecycle_status"],
        case_workflow_mode=case_lifecycle_fields["case_workflow_mode"],
        active_owner_role=case_lifecycle_fields["active_owner_role"],
        allowed_next_lifecycle_statuses=list(
            case_lifecycle_fields["allowed_next_lifecycle_statuses"]
        ),
        allowed_lifecycle_transitions=list(
            case_lifecycle_fields["allowed_lifecycle_transitions"]
        ),
        allowed_surface_actions=list(case_lifecycle_fields["allowed_surface_actions"]),
        human_validation_required=bool(
            case_lifecycle_fields["human_validation_required"]
        ),
        state_source="technical_case_acl",
        legacy_public_state=case_snapshot.legacy_public_state,
        legacy_review_status=case_snapshot.legacy_review_status,
        allows_reopen=case_snapshot.allows_reopen,
        has_active_report=case_snapshot.has_active_report,
        laudo_card=legacy_payload.get("laudo_card"),
        legacy_payload_keys=sorted(str(key) for key in legacy_payload.keys()),
    )

    return InspectorCaseStatusProjectionV1(
        tenant_id=case_snapshot.tenant_id,
        case_id=case_ref.case_id,
        thread_id=case_ref.thread_id,
        document_id=case_ref.document_id,
        actor_id=str(actor_id),
        actor_role=actor_role,
        correlation_id=correlation_id or case_snapshot.correlation_id or uuid.uuid4().hex,
        causation_id=causation_id,
        idempotency_key=idempotency_key or f"shadow-status:{case_ref.legacy_laudo_id or 'none'}",
        source_channel=source_channel,
        origin_kind=case_snapshot.origin_kind,
        sensitivity="technical",
        visibility_scope="actor",
        timestamp=timestamp or case_snapshot.timestamp,
        payload=payload.model_dump(mode="python"),
    )


def build_inspector_case_view_projection(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    actor_id: Any,
    actor_role: str,
    source_channel: str,
    allows_edit: bool,
    has_interaction: bool,
    report_types: dict[str, str] | None,
    laudo_card: dict[str, Any] | None,
    public_verification: dict[str, Any] | None = None,
    emissao_oficial: dict[str, Any] | None = None,
    policy_decision: TechnicalCasePolicyDecision | None = None,
    document_facade: CanonicalDocumentFacadeV1 | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> InspectorCaseViewProjectionV1:
    case_ref = case_snapshot.case_ref
    canonical_status = case_snapshot.canonical_status
    case_lifecycle_fields = _projection_case_lifecycle_fields(case_snapshot)
    provenance_fields = _projection_provenance_fields(case_snapshot.content_origin_summary)
    policy_fields = _projection_policy_fields(policy_decision)
    document_fields = _projection_document_fields(document_facade)
    payload = InspectorCaseViewProjectionPayload(
        legacy_laudo_id=case_ref.legacy_laudo_id,
        case_status=canonical_status,
        case_lifecycle_status=case_lifecycle_fields["case_lifecycle_status"],
        case_workflow_mode=case_lifecycle_fields["case_workflow_mode"],
        active_owner_role=case_lifecycle_fields["active_owner_role"],
        allowed_next_lifecycle_statuses=list(
            case_lifecycle_fields["allowed_next_lifecycle_statuses"]
        ),
        allowed_lifecycle_transitions=list(
            case_lifecycle_fields["allowed_lifecycle_transitions"]
        ),
        allowed_surface_actions=list(case_lifecycle_fields["allowed_surface_actions"]),
        human_validation_required=bool(
            case_lifecycle_fields["human_validation_required"]
        ),
        legacy_public_state=case_snapshot.legacy_public_state,
        legacy_status_card=case_snapshot.legacy_status_card,
        legacy_review_status=case_snapshot.legacy_review_status,
        allows_edit=bool(allows_edit),
        allows_reopen=case_snapshot.allows_reopen,
        has_active_report=case_snapshot.has_active_report,
        has_interaction=bool(has_interaction),
        review_requested=canonical_status in {"needs_reviewer", "review_feedback_pending", "approved"},
        review_feedback_pending=canonical_status == "review_feedback_pending",
        review_visible_to_inspector=canonical_status in {"needs_reviewer", "review_feedback_pending", "approved"},
        document_available=case_snapshot.has_active_report,
        document_approved=canonical_status == "approved",
        origin_summary=provenance_fields["origin_summary"],
        has_human_inputs=provenance_fields["has_human_inputs"],
        has_ai_outputs=provenance_fields["has_ai_outputs"],
        has_ai_assisted_content=provenance_fields["has_ai_assisted_content"],
        has_legacy_unknown_content=provenance_fields["has_legacy_unknown_content"],
        human_vs_ai_mix=provenance_fields["human_vs_ai_mix"],
        provenance_quality=provenance_fields["provenance_quality"],
        policy_summary=policy_fields["policy_summary"],
        review_required=policy_fields["review_required"],
        review_mode=policy_fields["review_mode"],
        engineer_approval_required=policy_fields["engineer_approval_required"],
        materialization_allowed=policy_fields["materialization_allowed"],
        issue_allowed=policy_fields["issue_allowed"],
        policy_source_summary=policy_fields["policy_source_summary"],
        policy_rationale=policy_fields["policy_rationale"],
        document_readiness=document_fields["document_readiness"],
        template_binding_summary=document_fields["template_binding_summary"],
        document_blockers=document_fields["document_blockers"],
        inspection_history=None,
        public_verification=public_verification,
        emissao_oficial=emissao_oficial,
        legacy_pipeline_shadow=document_fields["legacy_pipeline_shadow"],
        legacy_pipeline_name=document_fields["legacy_pipeline_name"],
        legacy_template_resolution=document_fields["legacy_template_resolution"],
        legacy_materialization_allowed=document_fields["legacy_materialization_allowed"],
        legacy_issue_allowed=document_fields["legacy_issue_allowed"],
        legacy_blockers=document_fields["legacy_blockers"],
        compatibility_summary=document_fields["compatibility_summary"],
        laudo_card=laudo_card,
        report_types=dict(report_types or {}),
        case_snapshot_timestamp=case_snapshot.timestamp,
    )

    return InspectorCaseViewProjectionV1(
        tenant_id=case_snapshot.tenant_id,
        case_id=case_ref.case_id,
        thread_id=case_ref.thread_id,
        document_id=case_ref.document_id,
        actor_id=str(actor_id),
        actor_role=actor_role,
        correlation_id=correlation_id or case_snapshot.correlation_id or uuid.uuid4().hex,
        causation_id=causation_id,
        idempotency_key=idempotency_key or f"inspector-case-view:{case_ref.legacy_laudo_id or 'none'}",
        source_channel=source_channel,
        origin_kind=case_snapshot.origin_kind,
        sensitivity="technical",
        visibility_scope="actor",
        timestamp=timestamp or case_snapshot.timestamp,
        payload=payload.model_dump(mode="python"),
    )


def _resolve_reviewdesk_review_status(case_snapshot: TechnicalCaseStatusSnapshot) -> str:
    canonical_status = case_snapshot.canonical_status
    if canonical_status == "approved":
        return "approved"
    if canonical_status == "review_feedback_pending":
        return "sent_back_for_adjustment"
    if canonical_status == "needs_reviewer":
        return "pending_review"
    if canonical_status == "draft":
        return "not_requested"
    return "in_review"


def _resolve_reviewdesk_document_status(case_snapshot: TechnicalCaseStatusSnapshot) -> str:
    if not case_snapshot.has_active_report:
        return "not_started"
    if case_snapshot.canonical_status == "approved":
        return "approved_for_issue"
    return "draft_document"


def build_reviewdesk_case_view_projection(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    pacote: PacoteMesaLaudo,
    actor_id: Any,
    actor_role: str,
    source_channel: str,
    policy_decision: TechnicalCasePolicyDecision | None = None,
    document_facade: CanonicalDocumentFacadeV1 | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> ReviewDeskCaseViewProjectionV1:
    case_ref = case_snapshot.case_ref
    case_lifecycle_fields = _projection_case_lifecycle_fields(case_snapshot)
    provenance_fields = _projection_provenance_fields(case_snapshot.content_origin_summary)
    policy_fields = _projection_policy_fields(policy_decision)
    document_fields = _projection_document_fields(document_facade)
    requires_reviewer_action = case_snapshot.canonical_status in {
        "needs_reviewer",
        "review_feedback_pending",
    }
    collaboration = build_reviewdesk_collaboration_read_model(
        pacote=pacote,
        requires_reviewer_action=requires_reviewer_action,
    )
    payload = ReviewDeskCaseViewProjectionPayload(
        legacy_laudo_id=int(pacote.laudo_id),
        codigo_hash=str(pacote.codigo_hash or ""),
        tipo_template=str(pacote.tipo_template or ""),
        setor_industrial=str(pacote.setor_industrial or ""),
        case_status=case_snapshot.canonical_status,
        case_lifecycle_status=case_lifecycle_fields["case_lifecycle_status"],
        case_workflow_mode=case_lifecycle_fields["case_workflow_mode"],
        active_owner_role=case_lifecycle_fields["active_owner_role"],
        allowed_next_lifecycle_statuses=list(
            case_lifecycle_fields["allowed_next_lifecycle_statuses"]
        ),
        allowed_lifecycle_transitions=list(
            case_lifecycle_fields["allowed_lifecycle_transitions"]
        ),
        allowed_surface_actions=list(case_lifecycle_fields["allowed_surface_actions"]),
        human_validation_required=bool(
            case_lifecycle_fields["human_validation_required"]
        ),
        review_status=_resolve_reviewdesk_review_status(case_snapshot),
        document_status=_resolve_reviewdesk_document_status(case_snapshot),
        legacy_review_status=str(pacote.status_revisao or ""),
        status_conformidade=str(pacote.status_conformidade or ""),
        has_open_pendencies=collaboration.summary.has_open_pendencies,
        has_recent_whispers=collaboration.summary.has_recent_whispers,
        requires_reviewer_action=requires_reviewer_action,
        origin_summary=provenance_fields["origin_summary"],
        has_human_inputs=provenance_fields["has_human_inputs"],
        has_ai_outputs=provenance_fields["has_ai_outputs"],
        has_ai_assisted_content=provenance_fields["has_ai_assisted_content"],
        has_legacy_unknown_content=provenance_fields["has_legacy_unknown_content"],
        human_vs_ai_mix=provenance_fields["human_vs_ai_mix"],
        provenance_quality=provenance_fields["provenance_quality"],
        policy_summary=policy_fields["policy_summary"],
        review_required=policy_fields["review_required"],
        review_mode=policy_fields["review_mode"],
        engineer_approval_required=policy_fields["engineer_approval_required"],
        materialization_allowed=policy_fields["materialization_allowed"],
        issue_allowed=policy_fields["issue_allowed"],
        policy_source_summary=policy_fields["policy_source_summary"],
        policy_rationale=policy_fields["policy_rationale"],
        document_readiness=document_fields["document_readiness"],
        template_binding_summary=document_fields["template_binding_summary"],
        document_blockers=document_fields["document_blockers"],
        legacy_pipeline_shadow=document_fields["legacy_pipeline_shadow"],
        legacy_pipeline_name=document_fields["legacy_pipeline_name"],
        legacy_template_resolution=document_fields["legacy_template_resolution"],
        legacy_materialization_allowed=document_fields["legacy_materialization_allowed"],
        legacy_issue_allowed=document_fields["legacy_issue_allowed"],
        legacy_blockers=document_fields["legacy_blockers"],
        compatibility_summary=document_fields["compatibility_summary"],
        pending_open_count=collaboration.summary.open_pendency_count,
        pending_resolved_count=collaboration.summary.resolved_pendency_count,
        recent_whispers_count=collaboration.summary.recent_whisper_count,
        recent_reviews_count=collaboration.summary.recent_review_count,
        created_at=pacote.criado_em,
        updated_at=pacote.atualizado_em,
        last_interaction_at=pacote.ultima_interacao_em,
        field_time_minutes=int(pacote.tempo_em_campo_minutos),
        inspector_id=pacote.inspetor_id,
        reviewer_id=pacote.revisor_id,
        has_form_data=bool(pacote.dados_formulario),
        has_ai_draft=bool(str(pacote.parecer_ia or "").strip()),
        summary_messages=pacote.resumo_mensagens.model_dump(mode="python"),
        summary_evidence=pacote.resumo_evidencias.model_dump(mode="python"),
        summary_pending=pacote.resumo_pendencias.model_dump(mode="python"),
        revisao_por_bloco=(
            pacote.revisao_por_bloco.model_dump(mode="python")
            if pacote.revisao_por_bloco
            else None
        ),
        coverage_map=pacote.coverage_map.model_dump(mode="python") if pacote.coverage_map else None,
        inspection_history=(
            pacote.historico_inspecao.model_dump(mode="python")
            if pacote.historico_inspecao
            else None
        ),
        public_verification=(
            pacote.verificacao_publica.model_dump(mode="python")
            if pacote.verificacao_publica
            else None
        ),
        anexo_pack=(
            pacote.anexo_pack.model_dump(mode="python")
            if pacote.anexo_pack
            else None
        ),
        emissao_oficial=(
            pacote.emissao_oficial.model_dump(mode="python")
            if pacote.emissao_oficial
            else None
        ),
        historico_refazer_inspetor=[item.model_dump(mode="python") for item in pacote.historico_refazer_inspetor],
        memoria_operacional_familia=(
            pacote.memoria_operacional_familia.model_dump(mode="python")
            if pacote.memoria_operacional_familia
            else None
        ),
        collaboration=collaboration,
        open_pendencies=[item.model_dump(mode="python") for item in pacote.pendencias_abertas],
        recent_resolved_pendencies=[item.model_dump(mode="python") for item in pacote.pendencias_resolvidas_recentes],
        recent_whispers=[item.model_dump(mode="python") for item in pacote.whispers_recentes],
        recent_reviews=[item.model_dump(mode="python") for item in pacote.revisoes_recentes],
        dados_formulario=pacote.dados_formulario,
        parecer_ia=pacote.parecer_ia,
        case_snapshot_timestamp=case_snapshot.timestamp,
    )

    return ReviewDeskCaseViewProjectionV1(
        tenant_id=case_snapshot.tenant_id,
        case_id=case_ref.case_id,
        thread_id=case_ref.thread_id,
        document_id=case_ref.document_id,
        actor_id=str(actor_id),
        actor_role=actor_role,
        correlation_id=correlation_id or case_snapshot.correlation_id or uuid.uuid4().hex,
        causation_id=causation_id,
        idempotency_key=idempotency_key or f"reviewdesk-case-view:{case_ref.legacy_laudo_id}",
        source_channel=source_channel,
        origin_kind=case_snapshot.origin_kind,
        sensitivity="technical",
        visibility_scope="review_desk",
        timestamp=timestamp or case_snapshot.timestamp,
        payload=payload.model_dump(mode="python"),
    )


def build_inspector_case_status_projection(
    *,
    tenant_id: Any,
    actor_id: Any,
    actor_role: str,
    source_channel: str,
    legacy_payload: dict[str, Any],
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> InspectorCaseStatusProjectionV1:
    legacy_laudo_id = legacy_payload.get("laudo_id")
    payload = InspectorCaseStatusProjectionPayload(
        legacy_laudo_id=int(legacy_laudo_id) if legacy_laudo_id is not None else None,
        state=str(legacy_payload.get("estado") or "sem_relatorio"),
        state_source="legacy_public_state",
        legacy_public_state=str(legacy_payload.get("estado") or "sem_relatorio"),
        legacy_review_status=(
            str((legacy_payload.get("laudo_card") or {}).get("status_revisao") or "").strip()
            or None
        ),
        allows_reopen=(
            bool(legacy_payload.get("permite_reabrir"))
            if legacy_payload.get("permite_reabrir") is not None
            else None
        ),
        has_active_report=bool(legacy_payload.get("laudo_id")),
        laudo_card=legacy_payload.get("laudo_card"),
        legacy_payload_keys=sorted(str(key) for key in legacy_payload.keys()),
    )

    return InspectorCaseStatusProjectionV1(
        tenant_id=str(tenant_id),
        case_id=_stringify_optional_id(legacy_laudo_id),
        thread_id=None,
        document_id=None,
        actor_id=str(actor_id),
        actor_role=actor_role,
        correlation_id=correlation_id or uuid.uuid4().hex,
        causation_id=causation_id,
        idempotency_key=idempotency_key or f"shadow-status:{legacy_laudo_id or 'none'}",
        source_channel=source_channel,
        origin_kind="system",
        sensitivity="technical",
        visibility_scope="actor",
        timestamp=timestamp or datetime.now(timezone.utc),
        payload=payload.model_dump(mode="python"),
    )


def build_inspector_case_status_projection_for_user(
    *,
    usuario: Any,
    legacy_payload: dict[str, Any],
    case_snapshot: TechnicalCaseStatusSnapshot | None = None,
    source_channel: str = "web_app",
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
) -> InspectorCaseStatusProjectionV1:
    if case_snapshot is not None:
        return build_inspector_case_status_projection_from_case_snapshot(
            case_snapshot=case_snapshot,
            actor_id=getattr(usuario, "id", ""),
            actor_role=actor_role_from_user(usuario),
            source_channel=source_channel,
            legacy_payload=legacy_payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
            idempotency_key=idempotency_key,
        )

    return build_inspector_case_status_projection(
        tenant_id=getattr(usuario, "empresa_id", ""),
        actor_id=getattr(usuario, "id", ""),
        actor_role=actor_role_from_user(usuario),
        source_channel=source_channel,
        legacy_payload=legacy_payload,
        correlation_id=correlation_id,
        causation_id=causation_id,
        idempotency_key=idempotency_key,
    )


__all__ = [
    "ReviewDeskCaseViewProjectionPayload",
    "ReviewDeskCaseViewProjectionV1",
    "InspectorCaseViewProjectionPayload",
    "InspectorCaseViewProjectionV1",
    "InspectorCaseStatusProjectionPayload",
    "InspectorCaseStatusProjectionV1",
    "build_inspector_case_view_projection",
    "build_inspector_case_status_projection",
    "build_inspector_case_status_projection_from_case_snapshot",
    "build_inspector_case_status_projection_for_user",
    "build_reviewdesk_case_view_projection",
]
