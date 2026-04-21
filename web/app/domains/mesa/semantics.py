"""Semântica canônica da colaboração da Mesa Avaliadora."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, TypeAlias

from app.shared.database import TipoMensagem

MesaItemKind: TypeAlias = Literal["message", "whisper", "pendency"]
MesaCollaborationItemKind: TypeAlias = Literal["whisper", "pendency"]
MesaMessageKind: TypeAlias = Literal[
    "inspector_message",
    "inspector_whisper",
    "mesa_pendency",
    "ai_message",
    "system_message",
]
MesaPendencyState: TypeAlias = Literal["not_applicable", "open", "resolved"]


@dataclass(frozen=True, slots=True)
class MesaMessageSemantics:
    item_kind: MesaItemKind
    message_kind: MesaMessageKind
    pendency_state: MesaPendencyState


def _normalized_legacy_message_type(value: Any) -> str:
    return str(value or "").strip().lower()


def resolve_mesa_message_kind(*, legacy_message_type: Any) -> MesaMessageKind:
    normalized = _normalized_legacy_message_type(legacy_message_type)
    if normalized == TipoMensagem.USER.value:
        return "inspector_message"
    if normalized == TipoMensagem.HUMANO_INSP.value:
        return "inspector_whisper"
    if normalized == TipoMensagem.HUMANO_ENG.value:
        return "mesa_pendency"
    if normalized == TipoMensagem.IA.value:
        return "ai_message"
    return "system_message"


def build_mesa_message_semantics(
    *,
    legacy_message_type: Any,
    resolved_at: datetime | str | None = None,
    is_whisper: bool | None = None,
) -> MesaMessageSemantics:
    message_kind = resolve_mesa_message_kind(legacy_message_type=legacy_message_type)

    if message_kind == "mesa_pendency":
        return MesaMessageSemantics(
            item_kind="pendency",
            message_kind=message_kind,
            pendency_state="resolved" if resolved_at else "open",
        )

    if message_kind == "inspector_whisper":
        return MesaMessageSemantics(
            item_kind="whisper",
            message_kind=message_kind,
            pendency_state="not_applicable",
        )

    return MesaMessageSemantics(
        item_kind="whisper" if is_whisper else "message",
        message_kind=message_kind,
        pendency_state="not_applicable",
    )


def is_open_pendency(
    *,
    legacy_message_type: Any,
    resolved_at: datetime | str | None = None,
    is_whisper: bool | None = None,
) -> bool:
    semantics = build_mesa_message_semantics(
        legacy_message_type=legacy_message_type,
        resolved_at=resolved_at,
        is_whisper=is_whisper,
    )
    return semantics.pendency_state == "open"


def is_resolved_pendency(
    *,
    legacy_message_type: Any,
    resolved_at: datetime | str | None = None,
    is_whisper: bool | None = None,
) -> bool:
    semantics = build_mesa_message_semantics(
        legacy_message_type=legacy_message_type,
        resolved_at=resolved_at,
        is_whisper=is_whisper,
    )
    return semantics.pendency_state == "resolved"


__all__ = [
    "MesaCollaborationItemKind",
    "MesaItemKind",
    "MesaMessageKind",
    "MesaMessageSemantics",
    "MesaPendencyState",
    "build_mesa_message_semantics",
    "is_open_pendency",
    "is_resolved_pendency",
    "resolve_mesa_message_kind",
]
