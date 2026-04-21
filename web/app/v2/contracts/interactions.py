"""Contratos internos de interacao/feed canônico do Inspetor."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domains.mesa.semantics import MesaItemKind, MesaMessageKind, MesaPendencyState
from app.v2.contracts.envelopes import utc_now
from app.v2.contracts.provenance import OriginKind


InteractionActorRole = Literal["inspetor", "mesa", "system", "unknown"]
InteractionActorKind = Literal["human", "system", "unknown"]
InteractionContentKind = Literal["text", "attachment", "mixed", "unknown"]


class InspectorCaseInteractionViewV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "InspectorCaseInteractionViewV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    thread_id: str | None = None
    interaction_id: str
    message_id: int | None = None
    actor_role: InteractionActorRole = "unknown"
    actor_kind: InteractionActorKind = "unknown"
    origin_kind: OriginKind = "system"
    content_kind: InteractionContentKind = "unknown"
    legacy_message_type: str = ""
    item_kind: MesaItemKind = "message"
    message_kind: MesaMessageKind = "system_message"
    pendency_state: MesaPendencyState = "not_applicable"
    text_preview: str = ""
    content_text: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
    display_date: str = ""
    sender_id: int | None = None
    client_message_id: str | None = None
    reference_message_id: int | None = None
    operational_context: dict[str, Any] | None = None
    resolved_at: datetime | None = None
    resolved_at_label: str = ""
    resolved_by_name: str = ""
    is_read: bool = False
    has_attachments: bool = False
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    delivery_status: str = "persisted"
    review_feedback_visible: bool = False
    review_marker_visible: bool = False
    highlight_marker: bool = False
    redirect_target_message_id: int | None = None
    pending_open: bool = False
    pending_resolved: bool = False
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"


class InspectorVisibleReviewSignalsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["InspectorVisibleReviewSignalsV1"] = "InspectorVisibleReviewSignalsV1"
    contract_version: str = "v1"
    review_visible_to_inspector: bool = False
    total_visible_interactions: int = 0
    visible_feedback_count: int = 0
    open_feedback_count: int = 0
    resolved_feedback_count: int = 0
    latest_feedback_message_id: int | None = None
    latest_feedback_at: datetime | None = None
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"
    timestamp: datetime = Field(default_factory=utc_now)


class InspectorCaseThreadMessageV1(InspectorCaseInteractionViewV1):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["InspectorCaseThreadMessageV1"] = "InspectorCaseThreadMessageV1"
    order_index: int = 0
    cursor_id: int | None = None
    is_delta_item: bool = False


class InspectorCaseConversationViewV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["InspectorCaseConversationViewV1"] = "InspectorCaseConversationViewV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    thread_id: str | None = None
    items: list[InspectorCaseThreadMessageV1] = Field(default_factory=list)
    total_visible_messages: int = 0
    unread_visible_messages: int = 0
    open_feedback_count: int = 0
    resolved_feedback_count: int = 0
    latest_message_id: int | None = None
    latest_message_at: datetime | None = None
    latest_message_preview: str = ""
    latest_message_type: str = ""
    latest_message_sender_id: int | None = None
    latest_message_client_message_id: str | None = None
    has_more: bool = False
    next_cursor_id: int | None = None
    cursor_after_id: int | None = None
    cursor_last_message_id: int | None = None
    sync_mode: Literal["full", "delta"] = "full"
    visibility_scope: Literal["inspetor_mobile"] = "inspetor_mobile"
    timestamp: datetime = Field(default_factory=utc_now)


__all__ = [
    "InspectorCaseConversationViewV1",
    "InspectorCaseInteractionViewV1",
    "InspectorCaseThreadMessageV1",
    "InspectorVisibleReviewSignalsV1",
    "InteractionActorKind",
    "InteractionActorRole",
    "InteractionContentKind",
]
