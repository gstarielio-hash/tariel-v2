"""Contratos publicos versionados do mobile V2 para leitura do Inspetor."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.domains.mesa.contracts import PacoteMesaLaudo
from app.domains.mesa.semantics import MesaItemKind, MesaMessageKind, MesaPendencyState
from app.v2.acl import (
    resolve_allowed_mobile_review_decisions,
    resolve_supports_mobile_block_reopen,
)
from app.v2.acl.technical_case_core import (
    TechnicalCaseActiveOwnerRole,
    TechnicalCaseLifecycleStatus,
    TechnicalCaseWorkflowMode,
)
from app.v2.contracts.envelopes import utc_now
from app.v2.contracts.interactions import (
    InspectorCaseConversationViewV1,
    InspectorCaseInteractionViewV1,
    InspectorCaseThreadMessageV1,
    InspectorVisibleReviewSignalsV1,
)
from app.v2.contracts.projections import InspectorCaseViewProjectionV1

_MOBILE_ATTACHMENT_SUPPORTED_CATEGORIES = ("imagem", "documento")
_MOBILE_ATTACHMENT_SUPPORTED_MIME_TYPES = (
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
)
_MOBILE_CASE_LIFECYCLE_STATUSES = (
    "analise_livre",
    "pre_laudo",
    "laudo_em_coleta",
    "aguardando_mesa",
    "em_revisao_mesa",
    "devolvido_para_correcao",
    "aprovado",
    "emitido",
)
_MOBILE_CASE_WORKFLOW_MODES = (
    "analise_livre",
    "laudo_guiado",
    "laudo_com_mesa",
)


def _is_open_pendency_state(state: MesaPendencyState | str | None) -> bool:
    return str(state or "").strip().lower() == "open"


def _is_resolved_pendency_state(state: MesaPendencyState | str | None) -> bool:
    return str(state or "").strip().lower() == "resolved"


class MobileInspectorCaseCardV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorCaseCardV2"] = "MobileInspectorCaseCardV2"
    contract_version: Literal["v2"] = "v2"
    legacy_laudo_id: int | None = None
    title: str = ""
    preview: str = ""
    template_key: str = ""
    review_status: str = ""
    card_status: str = ""
    card_status_label: str = ""
    date_iso: str = ""
    date_display: str = ""
    time_display: str = ""
    is_pinned: bool = False
    allows_edit: bool = False
    allows_reopen: bool = False
    has_history: bool = False
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorReviewSignalsV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorReviewSignalsV2"] = "MobileInspectorReviewSignalsV2"
    contract_version: Literal["v2"] = "v2"
    review_visible_to_inspector: bool = False
    total_visible_interactions: int = 0
    visible_feedback_count: int = 0
    open_feedback_count: int = 0
    resolved_feedback_count: int = 0
    latest_feedback_message_id: int | None = None
    latest_feedback_at: datetime | None = None
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorFeedbackPolicyV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorFeedbackPolicyV2"] = (
        "MobileInspectorFeedbackPolicyV2"
    )
    contract_version: Literal["v2"] = "v2"
    policy_name: Literal["android_feedback_sync_policy"] = (
        "android_feedback_sync_policy"
    )
    feedback_mode: Literal["hidden", "visible_feedback_only"] = "hidden"
    feedback_counters_visible: bool = False
    feedback_message_bodies_visible: bool = False
    latest_feedback_pointer_visible: bool = False
    mesa_internal_details_visible: Literal[False] = False
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorInteractionSummaryV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "MobileInspectorInteractionSummaryV2"
    contract_version: Literal["v2"] = "v2"
    interaction_id: str
    message_id: int | None = None
    actor_role: str = "unknown"
    actor_kind: str = "unknown"
    origin_kind: str = "system"
    content_kind: str = "unknown"
    legacy_message_type: str = ""
    item_kind: MesaItemKind = "message"
    message_kind: MesaMessageKind = "system_message"
    pendency_state: MesaPendencyState = "not_applicable"
    text_preview: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
    sender_id: int | None = None
    client_message_id: str | None = None
    reference_message_id: int | None = None
    operational_context: dict[str, Any] | None = None
    is_read: bool = False
    has_attachments: bool = False
    review_feedback_visible: bool = False
    review_marker_visible: bool = False
    highlight_marker: bool = False
    pending_open: bool = False
    pending_resolved: bool = False
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorCollaborationSummaryV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorCollaborationSummaryV2"] = (
        "MobileInspectorCollaborationSummaryV2"
    )
    contract_version: Literal["v2"] = "v2"
    feedback_visible_to_inspector: bool = False
    visible_feedback_count: int = 0
    unread_feedback_count: int = 0
    open_feedback_count: int = 0
    resolved_feedback_count: int = 0
    latest_feedback_message_id: int | None = None
    latest_feedback_at: datetime | None = None
    latest_feedback_preview: str = ""
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorCollaborationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorCollaborationV2"] = (
        "MobileInspectorCollaborationV2"
    )
    contract_version: Literal["v2"] = "v2"
    summary: MobileInspectorCollaborationSummaryV2 = Field(
        default_factory=MobileInspectorCollaborationSummaryV2
    )
    latest_feedback: MobileInspectorInteractionSummaryV2 | None = None
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorAttachmentV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorAttachmentV2"] = "MobileInspectorAttachmentV2"
    contract_version: Literal["v2"] = "v2"
    attachment_id: int | None = None
    name: str = ""
    mime_type: str = ""
    category: str = ""
    size_bytes: int = 0
    download_url: str | None = None
    is_image: bool = False
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorAttachmentPolicyV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorAttachmentPolicyV2"] = (
        "MobileInspectorAttachmentPolicyV2"
    )
    contract_version: Literal["v2"] = "v2"
    policy_name: Literal["android_attachment_sync_policy"] = (
        "android_attachment_sync_policy"
    )
    upload_allowed: bool = True
    download_allowed: bool = True
    inline_preview_allowed: bool = True
    supported_categories: list[str] = Field(
        default_factory=lambda: list(_MOBILE_ATTACHMENT_SUPPORTED_CATEGORIES)
    )
    supported_mime_types: list[str] = Field(
        default_factory=lambda: list(_MOBILE_ATTACHMENT_SUPPORTED_MIME_TYPES)
    )
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorReviewPackageV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorReviewPackageV2"] = (
        "MobileInspectorReviewPackageV2"
    )
    contract_version: Literal["v2"] = "v2"
    review_mode: str | None = None
    review_required: bool | None = None
    policy_summary: dict[str, Any] | None = None
    document_readiness: dict[str, Any] | None = None
    document_blockers: list[dict[str, Any]] = Field(default_factory=list)
    revisao_por_bloco: dict[str, Any] | None = None
    coverage_map: dict[str, Any] | None = None
    inspection_history: dict[str, Any] | None = None
    human_override_summary: dict[str, Any] | None = None
    public_verification: dict[str, Any] | None = None
    anexo_pack: dict[str, Any] | None = None
    emissao_oficial: dict[str, Any] | None = None
    historico_refazer_inspetor: list[dict[str, Any]] = Field(default_factory=list)
    memoria_operacional_familia: dict[str, Any] | None = None
    red_flags: list[dict[str, Any]] = Field(default_factory=list)
    tenant_entitlements: dict[str, Any] | None = None
    allowed_decisions: list[str] = Field(default_factory=list)
    supports_block_reopen: bool = False
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorFeedItemV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorFeedItemV2"] = "MobileInspectorFeedItemV2"
    contract_version: Literal["v2"] = "v2"
    tenant_id: str
    source_channel: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    thread_id: str | None = None
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"
    case_status: str = ""
    case_lifecycle_status: Literal[
        "analise_livre",
        "pre_laudo",
        "laudo_em_coleta",
        "aguardando_mesa",
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
        "emitido",
    ] = "analise_livre"
    case_workflow_mode: Literal[
        "analise_livre",
        "laudo_guiado",
        "laudo_com_mesa",
    ] = "analise_livre"
    active_owner_role: Literal["inspetor", "mesa", "none"] = "inspetor"
    allowed_next_lifecycle_statuses: list[str] = Field(default_factory=list)
    allowed_lifecycle_transitions: list[dict[str, Any]] = Field(default_factory=list)
    allowed_surface_actions: list[str] = Field(default_factory=list)
    human_validation_required: bool = False
    legacy_public_state: str = ""
    allows_edit: bool = False
    allows_reopen: bool = False
    has_interaction: bool = False
    case_card: MobileInspectorCaseCardV2 | None = None
    updated_at: datetime | None = None
    total_visible_interactions: int = 0
    unread_visible_interactions: int = 0
    open_feedback_count: int = 0
    resolved_feedback_count: int = 0
    latest_interaction: MobileInspectorInteractionSummaryV2 | None = None
    review_signals: MobileInspectorReviewSignalsV2 = Field(
        default_factory=MobileInspectorReviewSignalsV2
    )
    feedback_policy: MobileInspectorFeedbackPolicyV2 = Field(
        default_factory=MobileInspectorFeedbackPolicyV2
    )
    collaboration: MobileInspectorCollaborationV2 = Field(
        default_factory=MobileInspectorCollaborationV2
    )
    provenance_summary: dict[str, Any] | None = None
    policy_summary: dict[str, Any] | None = None
    document_readiness: dict[str, Any] | None = None
    document_blockers: list[dict[str, Any]] = Field(default_factory=list)


class MobileInspectorFeedV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorFeedV2"] = "MobileInspectorFeedV2"
    contract_version: Literal["v2"] = "v2"
    tenant_id: str
    source_channel: str
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"
    requested_laudo_ids: list[int] = Field(default_factory=list)
    cursor_current: str = ""
    total_requested_cases: int = 0
    returned_item_count: int = 0
    items: list[MobileInspectorFeedItemV2] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class MobileInspectorThreadMessageV2(MobileInspectorInteractionSummaryV2):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorThreadMessageV2"] = "MobileInspectorThreadMessageV2"
    content_text: str = ""
    display_date: str = ""
    resolved_at: datetime | None = None
    resolved_at_label: str = ""
    resolved_by_name: str = ""
    attachments: list[MobileInspectorAttachmentV2] = Field(default_factory=list)
    delivery_status: str = "persisted"
    order_index: int = 0
    cursor_id: int | None = None
    is_delta_item: bool = False


class MobileInspectorThreadSyncV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorThreadSyncV2"] = "MobileInspectorThreadSyncV2"
    contract_version: Literal["v2"] = "v2"
    mode: Literal["full", "delta"] = "full"
    cursor_after_id: int | None = None
    next_cursor_id: int | None = None
    cursor_last_message_id: int | None = None
    has_more: bool = False


class MobileInspectorSyncPolicyV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorSyncPolicyV2"] = "MobileInspectorSyncPolicyV2"
    contract_version: Literal["v2"] = "v2"
    policy_name: Literal["android_thread_sync_policy"] = "android_thread_sync_policy"
    mode: Literal["full", "delta"] = "full"
    offline_queue_supported: bool = True
    incremental_sync_supported: bool = True
    attachment_sync_supported: bool = True
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class MobileInspectorThreadV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["MobileInspectorThreadV2"] = "MobileInspectorThreadV2"
    contract_version: Literal["v2"] = "v2"
    tenant_id: str
    source_channel: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    thread_id: str | None = None
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"
    case_status: str = ""
    case_lifecycle_status: Literal[
        "analise_livre",
        "pre_laudo",
        "laudo_em_coleta",
        "aguardando_mesa",
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
        "emitido",
    ] = "analise_livre"
    case_workflow_mode: Literal[
        "analise_livre",
        "laudo_guiado",
        "laudo_com_mesa",
    ] = "analise_livre"
    active_owner_role: Literal["inspetor", "mesa", "none"] = "inspetor"
    allowed_next_lifecycle_statuses: list[str] = Field(default_factory=list)
    allowed_lifecycle_transitions: list[dict[str, Any]] = Field(default_factory=list)
    allowed_surface_actions: list[str] = Field(default_factory=list)
    human_validation_required: bool = False
    legacy_public_state: str = ""
    allows_edit: bool = False
    allows_reopen: bool = False
    case_card: MobileInspectorCaseCardV2 | None = None
    total_visible_messages: int = 0
    unread_visible_messages: int = 0
    open_feedback_count: int = 0
    resolved_feedback_count: int = 0
    latest_interaction: MobileInspectorInteractionSummaryV2 | None = None
    review_signals: MobileInspectorReviewSignalsV2 = Field(
        default_factory=MobileInspectorReviewSignalsV2
    )
    feedback_policy: MobileInspectorFeedbackPolicyV2 = Field(
        default_factory=MobileInspectorFeedbackPolicyV2
    )
    collaboration: MobileInspectorCollaborationV2 = Field(
        default_factory=MobileInspectorCollaborationV2
    )
    provenance_summary: dict[str, Any] | None = None
    policy_summary: dict[str, Any] | None = None
    document_readiness: dict[str, Any] | None = None
    document_blockers: list[dict[str, Any]] = Field(default_factory=list)
    mobile_review_package: MobileInspectorReviewPackageV2 | None = None
    attachment_policy: MobileInspectorAttachmentPolicyV2 = Field(
        default_factory=MobileInspectorAttachmentPolicyV2
    )
    sync: MobileInspectorThreadSyncV2 = Field(default_factory=MobileInspectorThreadSyncV2)
    sync_policy: MobileInspectorSyncPolicyV2 = Field(
        default_factory=MobileInspectorSyncPolicyV2
    )
    items: list[MobileInspectorThreadMessageV2] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


def _public_payload_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    if isinstance(value, dict):
        return dict(value)
    return None


def _resolve_mobile_case_lifecycle_status(value: Any) -> TechnicalCaseLifecycleStatus:
    normalized = str(value or "").strip()
    if normalized in _MOBILE_CASE_LIFECYCLE_STATUSES:
        return cast(TechnicalCaseLifecycleStatus, normalized)
    return "analise_livre"


def _resolve_mobile_case_workflow_mode(value: Any) -> TechnicalCaseWorkflowMode:
    normalized = str(value or "").strip()
    if normalized in _MOBILE_CASE_WORKFLOW_MODES:
        return cast(TechnicalCaseWorkflowMode, normalized)
    return "analise_livre"


def _resolve_mobile_active_owner_role(value: Any) -> TechnicalCaseActiveOwnerRole:
    normalized = str(value or "").strip()
    if normalized in {"inspetor", "mesa", "none"}:
        return cast(TechnicalCaseActiveOwnerRole, normalized)
    return "inspetor"


def _resolve_mobile_allowed_lifecycle_transitions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if hasattr(item, "model_dump"):
            normalized.append(item.model_dump(mode="python"))
        elif isinstance(item, dict):
            normalized.append(dict(item))
    return normalized


def _resolve_mobile_allowed_surface_actions(value: Any) -> list[str]:
    return [
        str(item).strip()
        for item in list(value or [])
        if str(item).strip()
    ]


def _sort_interactions(
    interactions: list[InspectorCaseInteractionViewV1],
) -> list[InspectorCaseInteractionViewV1]:
    return sorted(
        interactions,
        key=lambda item: (
            item.timestamp,
            int(item.message_id or 0),
        ),
    )


def _build_case_card_from_projection(
    projection: InspectorCaseViewProjectionV1,
) -> MobileInspectorCaseCardV2 | None:
    projection_payload = projection.payload
    laudo_card = dict(projection_payload.get("laudo_card") or {})
    if not laudo_card:
        return None

    report_types = dict(projection_payload.get("report_types") or {})
    return MobileInspectorCaseCardV2(
        legacy_laudo_id=int(
            projection_payload.get("legacy_laudo_id") or laudo_card.get("id") or 0
        )
        or None,
        title=str(laudo_card.get("titulo") or ""),
        preview=str(laudo_card.get("preview") or ""),
        template_key=str(
            laudo_card.get("tipo_template")
            or next(iter(report_types.keys()), "")
        ),
        review_status=str(
            laudo_card.get("status_revisao")
            or projection_payload.get("legacy_review_status")
            or ""
        ),
        card_status=str(
            laudo_card.get("status_card")
            or projection_payload.get("legacy_status_card")
            or ""
        ),
        card_status_label=str(laudo_card.get("status_card_label") or ""),
        date_iso=str(laudo_card.get("data_iso") or ""),
        date_display=str(laudo_card.get("data_br") or ""),
        time_display=str(laudo_card.get("hora_br") or ""),
        is_pinned=bool(laudo_card.get("pinado")),
        allows_edit=bool(laudo_card.get("permite_edicao", projection_payload.get("allows_edit"))),
        allows_reopen=bool(
            laudo_card.get("permite_reabrir", projection_payload.get("allows_reopen"))
        ),
        has_history=bool(
            laudo_card.get("possui_historico", projection_payload.get("has_active_report"))
        ),
    )


def _build_review_signals(
    visible_review_signals: InspectorVisibleReviewSignalsV1 | None,
) -> MobileInspectorReviewSignalsV2:
    if visible_review_signals is None:
        return MobileInspectorReviewSignalsV2()
    return MobileInspectorReviewSignalsV2(
        review_visible_to_inspector=visible_review_signals.review_visible_to_inspector,
        total_visible_interactions=visible_review_signals.total_visible_interactions,
        visible_feedback_count=visible_review_signals.visible_feedback_count,
        open_feedback_count=visible_review_signals.open_feedback_count,
        resolved_feedback_count=visible_review_signals.resolved_feedback_count,
        latest_feedback_message_id=visible_review_signals.latest_feedback_message_id,
        latest_feedback_at=visible_review_signals.latest_feedback_at,
    )


def _build_feedback_policy(
    *,
    projection: InspectorCaseViewProjectionV1,
    visible_review_signals: InspectorVisibleReviewSignalsV1 | None,
) -> MobileInspectorFeedbackPolicyV2:
    review_visible = False
    if visible_review_signals is not None:
        review_visible = bool(visible_review_signals.review_visible_to_inspector)
    else:
        review_visible = bool(projection.payload.get("review_visible_to_inspector"))
    if not review_visible:
        return MobileInspectorFeedbackPolicyV2()
    return MobileInspectorFeedbackPolicyV2(
        feedback_mode="visible_feedback_only",
        feedback_counters_visible=True,
        feedback_message_bodies_visible=True,
        latest_feedback_pointer_visible=True,
    )


def _is_interaction_visible_for_mobile(
    interaction: InspectorCaseInteractionViewV1,
    *,
    feedback_policy: MobileInspectorFeedbackPolicyV2,
) -> bool:
    if interaction.actor_role != "mesa":
        return True
    return feedback_policy.feedback_message_bodies_visible and interaction.review_feedback_visible


def _is_thread_message_visible_for_mobile(
    message: InspectorCaseThreadMessageV1,
    *,
    feedback_policy: MobileInspectorFeedbackPolicyV2,
) -> bool:
    if message.actor_role != "mesa":
        return True
    return feedback_policy.feedback_message_bodies_visible and message.review_feedback_visible


def _build_interaction_summary(
    interaction: InspectorCaseInteractionViewV1 | None,
) -> MobileInspectorInteractionSummaryV2 | None:
    if interaction is None:
        return None
    return MobileInspectorInteractionSummaryV2(
        interaction_id=interaction.interaction_id,
        message_id=interaction.message_id,
        actor_role=interaction.actor_role,
        actor_kind=interaction.actor_kind,
        origin_kind=interaction.origin_kind,
        content_kind=interaction.content_kind,
        legacy_message_type=interaction.legacy_message_type,
        item_kind=interaction.item_kind,
        message_kind=interaction.message_kind,
        pendency_state=interaction.pendency_state,
        text_preview=interaction.text_preview,
        timestamp=interaction.timestamp,
        sender_id=interaction.sender_id,
        client_message_id=interaction.client_message_id,
        reference_message_id=interaction.reference_message_id,
        operational_context=_public_payload_dict(interaction.operational_context),
        is_read=interaction.is_read,
        has_attachments=interaction.has_attachments,
        review_feedback_visible=interaction.review_feedback_visible,
        review_marker_visible=interaction.review_marker_visible,
        highlight_marker=_is_open_pendency_state(interaction.pendency_state),
        pending_open=_is_open_pendency_state(interaction.pendency_state),
        pending_resolved=_is_resolved_pendency_state(interaction.pendency_state),
    )


def _build_attachment(value: Any) -> MobileInspectorAttachmentV2:
    if hasattr(value, "model_dump"):
        raw = value.model_dump(mode="python")
    elif isinstance(value, dict):
        raw = dict(value)
    else:
        raw = {}
    attachment_id = raw.get("attachment_id", raw.get("id"))
    size_bytes = raw.get("size_bytes", raw.get("tamanho_bytes"))
    return MobileInspectorAttachmentV2(
        attachment_id=int(attachment_id) if isinstance(attachment_id, int) else None,
        name=str(raw.get("name", raw.get("nome")) or ""),
        mime_type=str(raw.get("mime_type") or ""),
        category=str(raw.get("category", raw.get("categoria")) or ""),
        size_bytes=max(0, int(size_bytes or 0)),
        download_url=str(raw.get("download_url", raw.get("url")) or "").strip() or None,
        is_image=bool(raw.get("is_image", raw.get("eh_imagem"))),
    )


def _build_collaboration(
    *,
    review_signals: InspectorVisibleReviewSignalsV1 | None,
    feedback_policy: MobileInspectorFeedbackPolicyV2,
    latest_feedback: MobileInspectorInteractionSummaryV2 | None,
    unread_feedback_count: int,
    open_feedback_count: int,
    resolved_feedback_count: int,
) -> MobileInspectorCollaborationV2:
    if not feedback_policy.feedback_counters_visible:
        unread_feedback_count = 0
        open_feedback_count = 0
        resolved_feedback_count = 0
    if not feedback_policy.latest_feedback_pointer_visible:
        latest_feedback = None

    visible_feedback_count = 0
    feedback_visible_to_inspector = False
    if review_signals is not None:
        visible_feedback_count = int(review_signals.visible_feedback_count)
        feedback_visible_to_inspector = bool(
            review_signals.review_visible_to_inspector
        )
    elif feedback_policy.feedback_message_bodies_visible:
        feedback_visible_to_inspector = True
        visible_feedback_count = 1 if latest_feedback is not None else 0

    return MobileInspectorCollaborationV2(
        summary=MobileInspectorCollaborationSummaryV2(
            feedback_visible_to_inspector=feedback_visible_to_inspector,
            visible_feedback_count=visible_feedback_count,
            unread_feedback_count=int(unread_feedback_count),
            open_feedback_count=int(open_feedback_count),
            resolved_feedback_count=int(resolved_feedback_count),
            latest_feedback_message_id=(
                latest_feedback.message_id if latest_feedback is not None else None
            ),
            latest_feedback_at=(
                latest_feedback.timestamp if latest_feedback is not None else None
            ),
            latest_feedback_preview=(
                latest_feedback.text_preview if latest_feedback is not None else ""
            ),
        ),
        latest_feedback=latest_feedback,
    )


def _build_thread_message(
    message: InspectorCaseThreadMessageV1,
) -> MobileInspectorThreadMessageV2:
    return MobileInspectorThreadMessageV2(
        interaction_id=message.interaction_id,
        message_id=message.message_id,
        actor_role=message.actor_role,
        actor_kind=message.actor_kind,
        origin_kind=message.origin_kind,
        content_kind=message.content_kind,
        legacy_message_type=message.legacy_message_type,
        item_kind=message.item_kind,
        message_kind=message.message_kind,
        pendency_state=message.pendency_state,
        text_preview=message.text_preview,
        timestamp=message.timestamp,
        sender_id=message.sender_id,
        client_message_id=message.client_message_id,
        reference_message_id=message.reference_message_id,
        operational_context=_public_payload_dict(message.operational_context),
        is_read=message.is_read,
        has_attachments=message.has_attachments,
        review_feedback_visible=message.review_feedback_visible,
        review_marker_visible=message.review_marker_visible,
        highlight_marker=_is_open_pendency_state(message.pendency_state),
        pending_open=_is_open_pendency_state(message.pendency_state),
        pending_resolved=_is_resolved_pendency_state(message.pendency_state),
        content_text=message.content_text,
        display_date=message.display_date,
        resolved_at=message.resolved_at,
        resolved_at_label=message.resolved_at_label,
        resolved_by_name=message.resolved_by_name,
        attachments=[_build_attachment(item) for item in list(message.attachments)],
        delivery_status=message.delivery_status,
        order_index=message.order_index,
        cursor_id=message.cursor_id,
        is_delta_item=message.is_delta_item,
    )


def _resolve_updated_at(
    *,
    projection: InspectorCaseViewProjectionV1,
    interactions: list[InspectorCaseInteractionViewV1],
    case_metadata: dict[str, Any] | None,
    feedback_policy: MobileInspectorFeedbackPolicyV2,
) -> datetime | None:
    ordered = _sort_interactions(interactions)
    if feedback_policy.latest_feedback_pointer_visible:
        updated_at_iso = str((case_metadata or {}).get("updated_at_iso") or "").strip()
        if updated_at_iso:
            try:
                return datetime.fromisoformat(updated_at_iso)
            except ValueError:
                return None
    if ordered:
        return ordered[-1].timestamp
    projection_timestamp = getattr(projection, "timestamp", None)
    if isinstance(projection_timestamp, datetime):
        return projection_timestamp
    return None


def build_mobile_inspector_review_package_v2(
    *,
    projection: InspectorCaseViewProjectionV1 | None = None,
    pacote_mesa: PacoteMesaLaudo | None = None,
) -> MobileInspectorReviewPackageV2 | None:
    projection_payload = projection.payload if projection is not None else {}
    policy_summary = _public_payload_dict(projection_payload.get("policy_summary"))
    document_readiness = _public_payload_dict(
        projection_payload.get("document_readiness")
    )
    document_blockers = list(projection_payload.get("document_blockers") or [])
    revisao_por_bloco = (
        pacote_mesa.revisao_por_bloco.model_dump(mode="python")
        if pacote_mesa is not None and pacote_mesa.revisao_por_bloco is not None
        else None
    )
    coverage_map = (
        pacote_mesa.coverage_map.model_dump(mode="python")
        if pacote_mesa is not None and pacote_mesa.coverage_map is not None
        else None
    )
    inspection_history = (
        pacote_mesa.historico_inspecao.model_dump(mode="python")
        if pacote_mesa is not None and pacote_mesa.historico_inspecao is not None
        else None
    )
    human_override_summary = (
        dict(pacote_mesa.human_override_summary or {})
        if pacote_mesa is not None
        and isinstance(pacote_mesa.human_override_summary, dict)
        else None
    )
    public_verification = (
        pacote_mesa.verificacao_publica.model_dump(mode="python")
        if pacote_mesa is not None and pacote_mesa.verificacao_publica is not None
        else None
    )
    anexo_pack = (
        pacote_mesa.anexo_pack.model_dump(mode="python")
        if pacote_mesa is not None and pacote_mesa.anexo_pack is not None
        else None
    )
    emissao_oficial = (
        pacote_mesa.emissao_oficial.model_dump(mode="python")
        if pacote_mesa is not None and pacote_mesa.emissao_oficial is not None
        else None
    )
    historico_refazer_inspetor = (
        [
            item.model_dump(mode="python")
            for item in pacote_mesa.historico_refazer_inspetor
        ]
        if pacote_mesa is not None
        else []
    )
    memoria_operacional_familia = (
        pacote_mesa.memoria_operacional_familia.model_dump(mode="python")
        if pacote_mesa is not None
        and pacote_mesa.memoria_operacional_familia is not None
        else None
    )
    red_flags = []
    tenant_entitlements = None
    if isinstance(policy_summary, dict):
        red_flags = list(policy_summary.get("red_flags") or [])
        if isinstance(policy_summary.get("tenant_entitlements"), dict):
            tenant_entitlements = dict(policy_summary.get("tenant_entitlements") or {})
    review_mode = str(projection_payload.get("review_mode") or "").strip() or None
    review_required = projection_payload.get("review_required")
    if not isinstance(review_required, bool):
        review_required = None
    allows_edit = bool(projection_payload.get("allows_edit"))
    case_lifecycle_status = _resolve_mobile_case_lifecycle_status(
        projection_payload.get("case_lifecycle_status")
    )
    allowed_decisions = list(
        resolve_allowed_mobile_review_decisions(
            lifecycle_status=case_lifecycle_status,
            allows_edit=allows_edit,
            review_mode=review_mode,
        )
    )
    supports_block_reopen = resolve_supports_mobile_block_reopen(
        lifecycle_status=case_lifecycle_status,
        allows_edit=allows_edit,
        has_block_review_items=bool(revisao_por_bloco and revisao_por_bloco.get("items")),
    )

    if (
        review_mode is None
        and review_required is None
        and policy_summary is None
        and document_readiness is None
        and not document_blockers
        and revisao_por_bloco is None
        and coverage_map is None
        and inspection_history is None
        and human_override_summary is None
        and public_verification is None
        and anexo_pack is None
        and emissao_oficial is None
        and not historico_refazer_inspetor
        and memoria_operacional_familia is None
        and not red_flags
        and tenant_entitlements is None
        and not allowed_decisions
        and not supports_block_reopen
    ):
        return None

    return MobileInspectorReviewPackageV2(
        review_mode=review_mode,
        review_required=review_required,
        policy_summary=policy_summary,
        document_readiness=document_readiness,
        document_blockers=document_blockers,
        revisao_por_bloco=revisao_por_bloco,
        coverage_map=coverage_map,
        inspection_history=inspection_history,
        human_override_summary=human_override_summary,
        public_verification=public_verification,
        anexo_pack=anexo_pack,
        emissao_oficial=emissao_oficial,
        historico_refazer_inspetor=historico_refazer_inspetor,
        memoria_operacional_familia=memoria_operacional_familia,
        red_flags=red_flags,
        tenant_entitlements=tenant_entitlements,
        allowed_decisions=allowed_decisions,
        supports_block_reopen=supports_block_reopen,
    )


def build_mobile_inspector_feed_item_v2(
    *,
    projection: InspectorCaseViewProjectionV1,
    interactions: list[InspectorCaseInteractionViewV1],
    source_channel: str,
    visible_review_signals: InspectorVisibleReviewSignalsV1 | None = None,
    provenance_summary: Any = None,
    case_metadata: dict[str, Any] | None = None,
) -> MobileInspectorFeedItemV2:
    projection_payload = projection.payload
    feedback_policy = _build_feedback_policy(
        projection=projection,
        visible_review_signals=visible_review_signals,
    )
    ordered_interactions = [
        item
        for item in _sort_interactions(interactions)
        if _is_interaction_visible_for_mobile(
            item,
            feedback_policy=feedback_policy,
        )
    ]
    latest_interaction = ordered_interactions[-1] if ordered_interactions else None
    visible_feedback = [
        item
        for item in ordered_interactions
        if item.actor_role == "mesa" and item.review_feedback_visible
    ]
    unread_feedback_count = sum(1 for item in visible_feedback if not item.is_read)
    open_feedback_count = sum(
        1 for item in visible_feedback if _is_open_pendency_state(item.pendency_state)
    )
    resolved_feedback_count = sum(
        1
        for item in visible_feedback
        if _is_resolved_pendency_state(item.pendency_state)
    )
    latest_feedback = _build_interaction_summary(
        visible_feedback[-1] if visible_feedback else None
    )
    return MobileInspectorFeedItemV2(
        tenant_id=str(projection.tenant_id),
        source_channel=source_channel,
        case_id=str(projection.case_id or "") or None,
        legacy_laudo_id=int(projection_payload.get("legacy_laudo_id") or 0) or None,
        thread_id=str(projection.thread_id or "") or None,
        case_status=str(projection_payload.get("case_status") or ""),
        case_lifecycle_status=_resolve_mobile_case_lifecycle_status(
            projection_payload.get("case_lifecycle_status")
        ),
        case_workflow_mode=_resolve_mobile_case_workflow_mode(
            projection_payload.get("case_workflow_mode")
        ),
        active_owner_role=_resolve_mobile_active_owner_role(
            projection_payload.get("active_owner_role")
        ),
        allowed_next_lifecycle_statuses=[
            str(item).strip()
            for item in list(
                projection_payload.get("allowed_next_lifecycle_statuses") or []
            )
            if str(item).strip()
        ],
        allowed_lifecycle_transitions=_resolve_mobile_allowed_lifecycle_transitions(
            projection_payload.get("allowed_lifecycle_transitions")
        ),
        allowed_surface_actions=_resolve_mobile_allowed_surface_actions(
            projection_payload.get("allowed_surface_actions")
        ),
        human_validation_required=bool(
            projection_payload.get("human_validation_required")
        ),
        legacy_public_state=str(projection_payload.get("legacy_public_state") or ""),
        allows_edit=bool(projection_payload.get("allows_edit")),
        allows_reopen=bool(projection_payload.get("allows_reopen")),
        has_interaction=bool(projection_payload.get("has_interaction")),
        case_card=_build_case_card_from_projection(projection),
        updated_at=_resolve_updated_at(
            projection=projection,
            interactions=ordered_interactions,
            case_metadata=case_metadata,
            feedback_policy=feedback_policy,
        ),
        total_visible_interactions=len(ordered_interactions),
        unread_visible_interactions=unread_feedback_count,
        open_feedback_count=open_feedback_count,
        resolved_feedback_count=resolved_feedback_count,
        latest_interaction=_build_interaction_summary(latest_interaction),
        review_signals=_build_review_signals(visible_review_signals),
        feedback_policy=feedback_policy,
        collaboration=_build_collaboration(
            review_signals=visible_review_signals,
            feedback_policy=feedback_policy,
            latest_feedback=latest_feedback,
            unread_feedback_count=unread_feedback_count,
            open_feedback_count=open_feedback_count,
            resolved_feedback_count=resolved_feedback_count,
        ),
        provenance_summary=_public_payload_dict(provenance_summary),
        policy_summary=_public_payload_dict(projection_payload.get("policy_summary")),
        document_readiness=_public_payload_dict(
            projection_payload.get("document_readiness")
        ),
        document_blockers=list(projection_payload.get("document_blockers") or []),
    )


def build_mobile_inspector_feed_v2(
    *,
    tenant_id: str,
    source_channel: str,
    requested_laudo_ids: list[int],
    cursor_current: str,
    items: list[MobileInspectorFeedItemV2],
) -> MobileInspectorFeedV2:
    return MobileInspectorFeedV2(
        tenant_id=str(tenant_id),
        source_channel=source_channel,
        requested_laudo_ids=[int(item) for item in requested_laudo_ids],
        cursor_current=str(cursor_current or ""),
        total_requested_cases=len(requested_laudo_ids),
        returned_item_count=len(items),
        items=items,
    )


def build_mobile_inspector_thread_v2(
    *,
    projection: InspectorCaseViewProjectionV1,
    conversation: InspectorCaseConversationViewV1,
    source_channel: str,
    visible_review_signals: InspectorVisibleReviewSignalsV1 | None = None,
    provenance_summary: Any = None,
    mobile_review_package: MobileInspectorReviewPackageV2 | None = None,
) -> MobileInspectorThreadV2:
    projection_payload = projection.payload
    feedback_policy = _build_feedback_policy(
        projection=projection,
        visible_review_signals=visible_review_signals,
    )
    items = [
        _build_thread_message(message)
        for message in sorted(
            conversation.items,
            key=lambda item: (
                item.order_index,
                item.timestamp,
                int(item.message_id or 0),
            ),
        )
        if _is_thread_message_visible_for_mobile(
            message,
            feedback_policy=feedback_policy,
        )
    ]
    visible_feedback_messages = [
        item
        for item in items
        if item.actor_role == "mesa" and item.review_feedback_visible
    ]
    latest_interaction = None
    if items:
        latest_interaction = max(
            items,
            key=lambda item: (
                item.timestamp,
                int(item.message_id or 0),
            ),
        )
    unread_visible_messages = sum(
        1 for item in visible_feedback_messages if not item.is_read
    )
    open_feedback_count = sum(
        1
        for item in visible_feedback_messages
        if _is_open_pendency_state(item.pendency_state)
    )
    resolved_feedback_count = sum(
        1
        for item in visible_feedback_messages
        if _is_resolved_pendency_state(item.pendency_state)
    )
    return MobileInspectorThreadV2(
        tenant_id=str(projection.tenant_id),
        source_channel=source_channel,
        case_id=str(projection.case_id or "") or None,
        legacy_laudo_id=int(projection_payload.get("legacy_laudo_id") or 0) or None,
        thread_id=str(projection.thread_id or "") or None,
        case_status=str(projection_payload.get("case_status") or ""),
        case_lifecycle_status=_resolve_mobile_case_lifecycle_status(
            projection_payload.get("case_lifecycle_status")
        ),
        case_workflow_mode=_resolve_mobile_case_workflow_mode(
            projection_payload.get("case_workflow_mode")
        ),
        active_owner_role=_resolve_mobile_active_owner_role(
            projection_payload.get("active_owner_role")
        ),
        allowed_next_lifecycle_statuses=[
            str(item).strip()
            for item in list(
                projection_payload.get("allowed_next_lifecycle_statuses") or []
            )
            if str(item).strip()
        ],
        allowed_lifecycle_transitions=_resolve_mobile_allowed_lifecycle_transitions(
            projection_payload.get("allowed_lifecycle_transitions")
        ),
        allowed_surface_actions=_resolve_mobile_allowed_surface_actions(
            projection_payload.get("allowed_surface_actions")
        ),
        human_validation_required=bool(
            projection_payload.get("human_validation_required")
        ),
        legacy_public_state=str(projection_payload.get("legacy_public_state") or ""),
        allows_edit=bool(projection_payload.get("allows_edit")),
        allows_reopen=bool(projection_payload.get("allows_reopen")),
        case_card=_build_case_card_from_projection(projection),
        total_visible_messages=len(items),
        unread_visible_messages=unread_visible_messages,
        open_feedback_count=open_feedback_count,
        resolved_feedback_count=resolved_feedback_count,
        latest_interaction=_build_interaction_summary(latest_interaction),
        review_signals=_build_review_signals(visible_review_signals),
        feedback_policy=feedback_policy,
        collaboration=_build_collaboration(
            review_signals=visible_review_signals,
            feedback_policy=feedback_policy,
            latest_feedback=_build_interaction_summary(
                visible_feedback_messages[-1] if visible_feedback_messages else None
            ),
            unread_feedback_count=unread_visible_messages,
            open_feedback_count=open_feedback_count,
            resolved_feedback_count=resolved_feedback_count,
        ),
        provenance_summary=_public_payload_dict(provenance_summary),
        policy_summary=_public_payload_dict(projection_payload.get("policy_summary")),
        document_readiness=_public_payload_dict(
            projection_payload.get("document_readiness")
        ),
        document_blockers=list(projection_payload.get("document_blockers") or []),
        mobile_review_package=mobile_review_package,
        attachment_policy=MobileInspectorAttachmentPolicyV2(),
        sync=MobileInspectorThreadSyncV2(
            mode=conversation.sync_mode,
            cursor_after_id=conversation.cursor_after_id,
            next_cursor_id=conversation.next_cursor_id,
            cursor_last_message_id=conversation.cursor_last_message_id,
            has_more=conversation.has_more,
        ),
        sync_policy=MobileInspectorSyncPolicyV2(
            mode=conversation.sync_mode,
            incremental_sync_supported=conversation.sync_mode == "delta",
        ),
        items=items,
    )


__all__ = [
    "MobileInspectorCaseCardV2",
    "MobileInspectorAttachmentPolicyV2",
    "MobileInspectorAttachmentV2",
    "MobileInspectorCollaborationSummaryV2",
    "MobileInspectorCollaborationV2",
    "MobileInspectorFeedbackPolicyV2",
    "MobileInspectorFeedItemV2",
    "MobileInspectorFeedV2",
    "MobileInspectorInteractionSummaryV2",
    "MobileInspectorReviewPackageV2",
    "MobileInspectorReviewSignalsV2",
    "MobileInspectorSyncPolicyV2",
    "MobileInspectorThreadMessageV2",
    "MobileInspectorThreadSyncV2",
    "MobileInspectorThreadV2",
    "build_mobile_inspector_review_package_v2",
    "build_mobile_inspector_feed_item_v2",
    "build_mobile_inspector_feed_v2",
    "build_mobile_inspector_thread_v2",
]
