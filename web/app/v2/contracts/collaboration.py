"""Read model canonico de colaboracao da Mesa no V2."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domains.mesa.contracts import MensagemPacoteMesa, PacoteMesaLaudo, RevisaoPacoteMesa
from app.domains.mesa.semantics import (
    MesaMessageKind,
    MesaPendencyState,
    build_mesa_message_semantics,
)


class ReviewDeskCollaborationMessageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    item_kind: Literal["pendency", "whisper"]
    message_kind: MesaMessageKind
    pendency_state: MesaPendencyState = "not_applicable"
    text: str = ""
    created_at: datetime
    sender_id: int | None = None
    is_read: bool = False
    reference_message_id: int | None = None
    resolved_at: datetime | None = None
    resolved_by_id: int | None = None
    resolved_by_name: str | None = None
    attachment_count: int = 0


class ReviewDeskCollaborationReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    origin: str
    summary: str | None = None
    confidence: str | None = None
    created_at: datetime


class ReviewDeskCollaborationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    open_pendency_count: int = 0
    resolved_pendency_count: int = 0
    recent_whisper_count: int = 0
    unread_whisper_count: int = 0
    recent_review_count: int = 0
    has_open_pendencies: bool = False
    has_recent_whispers: bool = False
    requires_reviewer_attention: bool = False


class ReviewDeskCollaborationReadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: ReviewDeskCollaborationSummary
    open_pendencies: list[ReviewDeskCollaborationMessageItem] = Field(default_factory=list)
    recent_resolved_pendencies: list[ReviewDeskCollaborationMessageItem] = Field(
        default_factory=list
    )
    recent_whispers: list[ReviewDeskCollaborationMessageItem] = Field(default_factory=list)
    recent_reviews: list[ReviewDeskCollaborationReviewItem] = Field(default_factory=list)


def build_reviewdesk_collaboration_summary(
    *,
    open_pendency_count: int = 0,
    resolved_pendency_count: int = 0,
    recent_whisper_count: int = 0,
    unread_whisper_count: int = 0,
    recent_review_count: int = 0,
    requires_reviewer_attention: bool | None = None,
) -> ReviewDeskCollaborationSummary:
    open_pendencies = max(0, int(open_pendency_count or 0))
    resolved_pendencies = max(0, int(resolved_pendency_count or 0))
    recent_whispers = max(0, int(recent_whisper_count or 0))
    unread_whispers = max(0, int(unread_whisper_count or 0))
    recent_reviews = max(0, int(recent_review_count or 0))
    if requires_reviewer_attention is None:
        requires_reviewer_attention = bool(open_pendencies or unread_whispers)

    return ReviewDeskCollaborationSummary(
        open_pendency_count=open_pendencies,
        resolved_pendency_count=resolved_pendencies,
        recent_whisper_count=recent_whispers,
        unread_whisper_count=unread_whispers,
        recent_review_count=recent_reviews,
        has_open_pendencies=bool(open_pendencies),
        has_recent_whispers=bool(recent_whispers),
        requires_reviewer_attention=bool(requires_reviewer_attention),
    )


def _build_message_item(
    item: MensagemPacoteMesa,
    *,
    item_kind: Literal["pendency", "whisper"],
) -> ReviewDeskCollaborationMessageItem:
    semantics = build_mesa_message_semantics(
        legacy_message_type=item.tipo,
        resolved_at=item.resolvida_em,
        is_whisper=item.item_kind == "whisper",
    )
    canonical_item_kind = item.item_kind if item.item_kind in {"pendency", "whisper"} else item_kind
    message_kind = (
        semantics.message_kind
        if item.message_kind == "system_message" and str(item.tipo or "").strip()
        else item.message_kind
    )
    pendency_state = (
        semantics.pendency_state
        if item.pendency_state == "not_applicable" and canonical_item_kind == "pendency"
        else item.pendency_state
    )
    return ReviewDeskCollaborationMessageItem(
        id=int(item.id),
        item_kind=canonical_item_kind,
        message_kind=message_kind,
        pendency_state=pendency_state,
        text=str(item.texto or ""),
        created_at=item.criado_em,
        sender_id=item.remetente_id,
        is_read=bool(item.lida),
        reference_message_id=item.referencia_mensagem_id,
        resolved_at=item.resolvida_em,
        resolved_by_id=item.resolvida_por_id,
        resolved_by_name=item.resolvida_por_nome,
        attachment_count=len(item.anexos),
    )


def _build_review_item(item: RevisaoPacoteMesa) -> ReviewDeskCollaborationReviewItem:
    return ReviewDeskCollaborationReviewItem(
        version=int(item.numero_versao),
        origin=str(item.origem or ""),
        summary=item.resumo,
        confidence=item.confianca_geral,
        created_at=item.criado_em,
    )


def build_reviewdesk_collaboration_read_model(
    *,
    pacote: PacoteMesaLaudo,
    requires_reviewer_action: bool = False,
) -> ReviewDeskCollaborationReadModel:
    open_pendencies = [
        _build_message_item(item, item_kind="pendency")
        for item in pacote.pendencias_abertas
    ]
    recent_resolved_pendencies = [
        _build_message_item(item, item_kind="pendency")
        for item in pacote.pendencias_resolvidas_recentes
    ]
    recent_whispers = [
        _build_message_item(item, item_kind="whisper")
        for item in pacote.whispers_recentes
    ]
    recent_reviews = [_build_review_item(item) for item in pacote.revisoes_recentes]
    unread_whisper_count = sum(1 for item in recent_whispers if not item.is_read)
    summary = build_reviewdesk_collaboration_summary(
        open_pendency_count=len(open_pendencies),
        resolved_pendency_count=len(recent_resolved_pendencies),
        recent_whisper_count=len(recent_whispers),
        unread_whisper_count=unread_whisper_count,
        recent_review_count=len(recent_reviews),
        requires_reviewer_attention=bool(
            requires_reviewer_action or open_pendencies or unread_whisper_count
        ),
    )
    return ReviewDeskCollaborationReadModel(
        summary=summary,
        open_pendencies=open_pendencies,
        recent_resolved_pendencies=recent_resolved_pendencies,
        recent_whispers=recent_whispers,
        recent_reviews=recent_reviews,
    )


__all__ = [
    "ReviewDeskCollaborationMessageItem",
    "ReviewDeskCollaborationReadModel",
    "ReviewDeskCollaborationReviewItem",
    "ReviewDeskCollaborationSummary",
    "build_reviewdesk_collaboration_summary",
    "build_reviewdesk_collaboration_read_model",
]
