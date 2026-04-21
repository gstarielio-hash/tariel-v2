"""Derivação incremental de provenance mínima sobre sinais confiáveis do legado."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domains.mesa.contracts import PacoteMesaLaudo
from app.shared.database import MensagemLaudo, TipoMensagem
from app.v2.contracts.provenance import (
    ContentOriginSummary,
    ProvenanceEntry,
    build_content_origin_summary,
)


class MessageOriginCounters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_messages: int = Field(default=0, ge=0)
    inspector_whispers: int = Field(default=0, ge=0)
    review_whispers: int = Field(default=0, ge=0)
    ai_messages: int = Field(default=0, ge=0)
    other_messages: int = Field(default=0, ge=0)

    @property
    def human_messages(self) -> int:
        return int(self.user_messages) + int(self.inspector_whispers) + int(self.review_whispers)

    @property
    def total_messages(self) -> int:
        return (
            int(self.user_messages)
            + int(self.inspector_whispers)
            + int(self.review_whispers)
            + int(self.ai_messages)
            + int(self.other_messages)
        )


def load_message_origin_counters(
    banco: Session,
    *,
    laudo_id: int | None,
) -> MessageOriginCounters:
    if not laudo_id:
        return MessageOriginCounters()

    rows = (
        banco.query(MensagemLaudo.tipo, func.count(MensagemLaudo.id))
        .filter(MensagemLaudo.laudo_id == int(laudo_id))
        .group_by(MensagemLaudo.tipo)
        .all()
    )

    counts: dict[str, int] = {
        TipoMensagem.USER.value: 0,
        TipoMensagem.HUMANO_INSP.value: 0,
        TipoMensagem.HUMANO_ENG.value: 0,
        TipoMensagem.IA.value: 0,
        "__other__": 0,
    }
    for raw_tipo, total in rows:
        tipo = str(raw_tipo or "")
        normalized_total = int(total or 0)
        if tipo in counts:
            counts[tipo] += normalized_total
        else:
            counts["__other__"] += normalized_total

    return MessageOriginCounters(
        user_messages=counts[TipoMensagem.USER.value],
        inspector_whispers=counts[TipoMensagem.HUMANO_INSP.value],
        review_whispers=counts[TipoMensagem.HUMANO_ENG.value],
        ai_messages=counts[TipoMensagem.IA.value],
        other_messages=counts["__other__"],
    )


def _append_entry(
    entries: list[ProvenanceEntry],
    *,
    origin_kind: str,
    source: str,
    signal_count: int,
    confidence: str = "confirmed",
    details: str | None = None,
) -> None:
    if int(signal_count or 0) <= 0:
        return
    entries.append(
        ProvenanceEntry(
            origin_kind=origin_kind,  # type: ignore[arg-type]
            source=source,
            confidence=confidence,  # type: ignore[arg-type]
            signal_count=int(signal_count),
            details=details,
        )
    )


def _normalize_review_origin(origem: Any) -> str:
    value = str(origem or "").strip().lower()
    if value in {"ia", "ai", "assistente"}:
        return "ai_generated"
    if value in {"ai_assisted", "ia_assistida", "assistida", "copiloto", "copilot"}:
        return "ai_assisted"
    if value in {"humano", "manual", "usuario", "inspetor", "revisor", "engenheiro"}:
        return "human"
    if value in {"system", "sistema"}:
        return "system"
    return "legacy_unknown"


def build_inspector_content_origin_summary(
    *,
    laudo: Any | None,
    message_counters: MessageOriginCounters | None,
    has_active_report: bool,
) -> ContentOriginSummary:
    entries: list[ProvenanceEntry] = []
    notes: list[str] = []

    counters = message_counters or MessageOriginCounters()
    _append_entry(
        entries,
        origin_kind="human",
        source="message_types",
        signal_count=counters.human_messages,
        confidence="confirmed",
        details="Mensagens humanas do inspetor ou da mesa observadas no legado.",
    )
    _append_entry(
        entries,
        origin_kind="ai_generated",
        source="message_types",
        signal_count=counters.ai_messages,
        confidence="confirmed",
        details="Mensagens da IA persistidas no histórico do laudo.",
    )
    _append_entry(
        entries,
        origin_kind="legacy_unknown",
        source="message_types.other",
        signal_count=counters.other_messages,
        confidence="legacy_unknown",
        details="Tipos de mensagem fora do conjunto canônico atual.",
    )

    primeira_mensagem = str(getattr(laudo, "primeira_mensagem", "") or "").strip()
    if primeira_mensagem and counters.human_messages <= 0:
        _append_entry(
            entries,
            origin_kind="human",
            source="laudo.primeira_mensagem",
            signal_count=1,
            confidence="confirmed",
            details="Preview inicial do laudo salvo com origem humana.",
        )

    parecer_ia = str(getattr(laudo, "parecer_ia", "") or "").strip()
    confianca_ia = getattr(laudo, "confianca_ia_json", None)
    if (parecer_ia or confianca_ia) and counters.ai_messages <= 0:
        _append_entry(
            entries,
            origin_kind="ai_generated",
            source="laudo.parecer_ia",
            signal_count=1,
            confidence="confirmed",
            details="Campo legado de parecer da IA no laudo.",
        )

    if getattr(laudo, "dados_formulario", None):
        _append_entry(
            entries,
            origin_kind="legacy_unknown",
            source="laudo.dados_formulario",
            signal_count=1,
            confidence="legacy_unknown",
            details="Formulario legado sem autoria confiavel persistida.",
        )
        notes.append("dados_formulario permanece sem classificacao confiavel de autoria no legado atual")

    if not entries:
        if has_active_report:
            _append_entry(
                entries,
                origin_kind="legacy_unknown",
                source="legacy_report_state",
                signal_count=1,
                confidence="legacy_unknown",
                details="Ha relatorio ativo, mas o legado nao oferece sinais suficientes de origem do conteudo.",
            )
        else:
            _append_entry(
                entries,
                origin_kind="system",
                source="status.public_state",
                signal_count=1,
                confidence="derived",
                details="Sem relatorio ativo; apenas estado sistêmico observado.",
            )

    return build_content_origin_summary(entries=entries, notes=notes)


def build_reviewdesk_content_origin_summary(
    *,
    pacote: PacoteMesaLaudo,
) -> ContentOriginSummary:
    entries: list[ProvenanceEntry] = []
    notes: list[str] = []

    human_signals = int(pacote.resumo_mensagens.inspetor) + int(pacote.resumo_mensagens.mesa)
    _append_entry(
        entries,
        origin_kind="human",
        source="package.message_summary",
        signal_count=human_signals,
        confidence="confirmed",
        details="Mensagens humanas observadas no pacote da mesa.",
    )
    _append_entry(
        entries,
        origin_kind="ai_generated",
        source="package.message_summary",
        signal_count=int(pacote.resumo_mensagens.ia),
        confidence="confirmed",
        details="Mensagens de IA observadas no pacote da mesa.",
    )
    _append_entry(
        entries,
        origin_kind="legacy_unknown",
        source="package.message_summary.other",
        signal_count=int(pacote.resumo_mensagens.sistema_outros),
        confidence="legacy_unknown",
        details="Mensagens fora da classificacao humana/IA/mesa no resumo legado.",
    )

    if str(pacote.parecer_ia or "").strip():
        _append_entry(
            entries,
            origin_kind="ai_generated",
            source="package.ai_draft",
            signal_count=1,
            confidence="confirmed",
            details="Parecer de IA materializado no laudo legado.",
        )

    if pacote.dados_formulario:
        _append_entry(
            entries,
            origin_kind="legacy_unknown",
            source="package.form_data",
            signal_count=1,
            confidence="legacy_unknown",
            details="Dados estruturados do formulario sem autoria confiavel no legado.",
        )
        notes.append("dados_formulario da mesa ainda nao diferencia preenchimento humano e IA com seguranca")

    review_origin_counts: dict[str, int] = {
        "human": 0,
        "ai_generated": 0,
        "ai_assisted": 0,
        "system": 0,
        "legacy_unknown": 0,
    }
    for revisao in pacote.revisoes_recentes:
        review_origin_counts[_normalize_review_origin(getattr(revisao, "origem", None))] += 1

    for kind, count in review_origin_counts.items():
        _append_entry(
            entries,
            origin_kind=kind,
            source="package.review_history",
            signal_count=count,
            confidence="confirmed" if kind != "legacy_unknown" else "legacy_unknown",
            details="Origem das revisoes recentes persistidas no legado.",
        )

    if not entries:
        _append_entry(
            entries,
            origin_kind="legacy_unknown",
            source="legacy_review_package",
            signal_count=1,
            confidence="legacy_unknown",
            details="Pacote legado da mesa sem sinais suficientes para classificar origem do conteudo.",
        )

    return build_content_origin_summary(entries=entries, notes=notes)


__all__ = [
    "MessageOriginCounters",
    "build_inspector_content_origin_summary",
    "build_reviewdesk_content_origin_summary",
    "load_message_origin_counters",
]
