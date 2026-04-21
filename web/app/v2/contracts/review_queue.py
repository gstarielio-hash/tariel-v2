"""Projecao canonica incremental da fila especializada da mesa."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.acl.technical_case_core import build_case_status_visual_label
from app.v2.contracts.envelopes import ProjectionEnvelope, utc_now


class ReviewQueueFilterSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inspector_id: int | None = None
    search_query: str = ""
    learning_filter: str = ""
    operation_filter: str = ""


class ReviewQueueSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    in_field_count: int = 0
    awaiting_review_count: int = 0
    recent_history_count: int = 0
    whisper_pending_count: int = 0
    total_pending_learning: int = 0
    total_open_pendencies: int = 0
    total_pending_whispers: int = 0
    observed_case_ids: list[str] = Field(default_factory=list)


class ReviewQueueOperationTotalsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    responder_agora: int = 0
    validar_aprendizado: int = 0
    aguardando_inspetor: int = 0
    fechamento_mesa: int = 0
    acompanhamento: int = 0


class ReviewQueueTemplateOperationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_templates: int = 0
    total_codigos: int = 0
    total_ativos: int = 0
    total_em_teste: int = 0
    total_rascunhos: int = 0
    total_word: int = 0
    total_pdf: int = 0
    total_codigos_sem_ativo: int = 0
    total_codigos_em_operacao: int = 0
    total_codigos_em_operacao_sem_ativo: int = 0
    total_bases_manuais: int = 0
    ultima_utilizacao_em: str | None = None
    ultima_utilizacao_em_label: str = ""


class ReviewQueueWhisperPreviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    laudo_id: int
    hash: str
    texto: str
    timestamp: str = ""
    case_lifecycle_status: str = ""
    active_owner_role: str = ""
    status_visual_label: str = ""
    collaboration_summary: "ReviewQueueCollaborationSummaryPayload | None" = None


class ReviewQueueCollaborationSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    open_pendency_count: int = 0
    resolved_pendency_count: int = 0
    recent_whisper_count: int = 0
    unread_whisper_count: int = 0
    recent_review_count: int = 0
    has_open_pendencies: bool = False
    has_recent_whispers: bool = False
    requires_reviewer_attention: bool = False


class ReviewQueueItemPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    queue_section: Literal["em_andamento", "aguardando_avaliacao", "historico"]
    hash_curto: str
    primeira_mensagem: str
    setor_industrial: str
    status_revisao: str
    atualizado_em: datetime | None = None
    criado_em: datetime | None = None
    inspetor_nome: str
    whispers_nao_lidos: int = 0
    pendencias_abertas: int = 0
    aprendizados_pendentes: int = 0
    collaboration_summary: ReviewQueueCollaborationSummaryPayload | None = None
    tempo_em_campo: str = ""
    tempo_em_campo_status: str = ""
    fila_operacional: str
    fila_operacional_label: str
    prioridade_operacional: str
    prioridade_operacional_label: str
    proxima_acao: str
    case_status: str = ""
    case_lifecycle_status: str = ""
    case_workflow_mode: str = ""
    active_owner_role: str = ""
    allowed_next_lifecycle_statuses: list[str] = Field(default_factory=list)
    allowed_surface_actions: list[str] = Field(default_factory=list)
    status_visual_label: str = ""


class ReviewQueueSectionsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    em_andamento: list[ReviewQueueItemPayload] = Field(default_factory=list)
    aguardando_avaliacao: list[ReviewQueueItemPayload] = Field(default_factory=list)
    historico: list[ReviewQueueItemPayload] = Field(default_factory=list)


class ReviewQueueDashboardProjectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filter_summary: ReviewQueueFilterSummaryPayload
    queue_summary: ReviewQueueSummaryPayload
    operation_totals: ReviewQueueOperationTotalsPayload
    template_operation_summary: ReviewQueueTemplateOperationPayload
    pending_whispers_preview: list[ReviewQueueWhisperPreviewPayload] = Field(default_factory=list)
    queue_sections: ReviewQueueSectionsPayload


class ReviewQueueDashboardProjectionV1(ProjectionEnvelope):
    contract_name: Literal["ReviewQueueDashboardProjectionV1"] = "ReviewQueueDashboardProjectionV1"
    projection_name: Literal["ReviewQueueDashboardProjectionV1"] = "ReviewQueueDashboardProjectionV1"
    projection_audience: Literal["review_queue_web"] = "review_queue_web"
    projection_type: Literal["review_queue_projection"] = "review_queue_projection"


def _normalize_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _serialize_queue_item(
    item: dict[str, Any],
    *,
    queue_section: Literal["em_andamento", "aguardando_avaliacao", "historico"],
) -> ReviewQueueItemPayload:
    collaboration_summary = item.get("collaboration_summary")
    case_lifecycle_status = str(item.get("case_lifecycle_status") or "")
    active_owner_role = str(item.get("active_owner_role") or "")
    return ReviewQueueItemPayload(
        id=_normalize_int(item.get("id")),
        queue_section=queue_section,
        hash_curto=str(item.get("hash_curto") or ""),
        primeira_mensagem=str(item.get("primeira_mensagem") or ""),
        setor_industrial=str(item.get("setor_industrial") or ""),
        status_revisao=str(item.get("status_revisao") or ""),
        atualizado_em=item.get("atualizado_em"),
        criado_em=item.get("criado_em"),
        inspetor_nome=str(item.get("inspetor_nome") or ""),
        whispers_nao_lidos=_normalize_int(item.get("whispers_nao_lidos")),
        pendencias_abertas=_normalize_int(item.get("pendencias_abertas")),
        aprendizados_pendentes=_normalize_int(item.get("aprendizados_pendentes")),
        collaboration_summary=(
            ReviewQueueCollaborationSummaryPayload.model_validate(collaboration_summary)
            if isinstance(collaboration_summary, dict)
            else None
        ),
        tempo_em_campo=str(item.get("tempo_em_campo") or ""),
        tempo_em_campo_status=str(item.get("tempo_em_campo_status") or ""),
        fila_operacional=str(item.get("fila_operacional") or ""),
        fila_operacional_label=str(item.get("fila_operacional_label") or ""),
        prioridade_operacional=str(item.get("prioridade_operacional") or ""),
        prioridade_operacional_label=str(item.get("prioridade_operacional_label") or ""),
        proxima_acao=str(item.get("proxima_acao") or ""),
        case_status=str(item.get("case_status") or ""),
        case_lifecycle_status=case_lifecycle_status,
        case_workflow_mode=str(item.get("case_workflow_mode") or ""),
        active_owner_role=active_owner_role,
        allowed_next_lifecycle_statuses=[
            str(value or "") for value in list(item.get("allowed_next_lifecycle_statuses") or []) if str(value or "").strip()
        ],
        allowed_surface_actions=[
            str(value or "") for value in list(item.get("allowed_surface_actions") or []) if str(value or "").strip()
        ],
        status_visual_label=(
            str(item.get("status_visual_label") or "").strip()
            or build_case_status_visual_label(
                lifecycle_status=case_lifecycle_status,
                active_owner_role=active_owner_role,
            )
        ),
    )


def _serialize_whisper_preview(item: dict[str, Any]) -> ReviewQueueWhisperPreviewPayload:
    collaboration_summary = item.get("collaboration_summary")
    case_lifecycle_status = str(item.get("case_lifecycle_status") or "")
    active_owner_role = str(item.get("active_owner_role") or "")
    return ReviewQueueWhisperPreviewPayload(
        laudo_id=_normalize_int(item.get("laudo_id")),
        hash=str(item.get("hash") or ""),
        texto=str(item.get("texto") or ""),
        timestamp=str(item.get("timestamp") or ""),
        case_lifecycle_status=case_lifecycle_status,
        active_owner_role=active_owner_role,
        status_visual_label=(
            str(item.get("status_visual_label") or "").strip()
            or build_case_status_visual_label(
                lifecycle_status=case_lifecycle_status,
                active_owner_role=active_owner_role,
            )
        ),
        collaboration_summary=(
            ReviewQueueCollaborationSummaryPayload.model_validate(collaboration_summary)
            if isinstance(collaboration_summary, dict)
            else None
        ),
    )


def build_review_queue_dashboard_projection(
    *,
    tenant_id: Any,
    filtro_inspetor_id: int | None,
    filtro_busca: Any,
    filtro_aprendizados: Any,
    filtro_operacao: Any,
    whispers_pendentes: Iterable[dict[str, Any]],
    laudos_em_andamento: Iterable[dict[str, Any]],
    laudos_pendentes: Iterable[dict[str, Any]],
    laudos_avaliados: Iterable[dict[str, Any]],
    total_aprendizados_pendentes: int,
    total_pendencias_abertas: int,
    total_whispers_pendentes: int,
    totais_operacao: dict[str, Any],
    templates_operacao: dict[str, Any],
    actor_id: Any,
    actor_role: str,
    source_channel: str,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> ReviewQueueDashboardProjectionV1:
    em_andamento = [
        _serialize_queue_item(item, queue_section="em_andamento")
        for item in laudos_em_andamento
    ]
    aguardando = [
        _serialize_queue_item(item, queue_section="aguardando_avaliacao")
        for item in laudos_pendentes
    ]
    historico = [
        _serialize_queue_item(item, queue_section="historico")
        for item in laudos_avaliados
    ]
    whispers_preview = [_serialize_whisper_preview(item) for item in whispers_pendentes]
    tenant_id_text = str(tenant_id or "").strip()
    now = timestamp or utc_now()

    observed_case_ids = [
        str(item.id)
        for item in [*em_andamento, *aguardando, *historico]
        if int(item.id or 0) > 0
    ]

    payload = ReviewQueueDashboardProjectionPayload(
        filter_summary=ReviewQueueFilterSummaryPayload(
            inspector_id=(_normalize_int(filtro_inspetor_id) or None),
            search_query=str(filtro_busca or ""),
            learning_filter=str(filtro_aprendizados or ""),
            operation_filter=str(filtro_operacao or ""),
        ),
        queue_summary=ReviewQueueSummaryPayload(
            in_field_count=len(em_andamento),
            awaiting_review_count=len(aguardando),
            recent_history_count=len(historico),
            whisper_pending_count=len(whispers_preview),
            total_pending_learning=_normalize_int(total_aprendizados_pendentes),
            total_open_pendencies=_normalize_int(total_pendencias_abertas),
            total_pending_whispers=_normalize_int(total_whispers_pendentes),
            observed_case_ids=observed_case_ids,
        ),
        operation_totals=ReviewQueueOperationTotalsPayload(
            responder_agora=_normalize_int(totais_operacao.get("responder_agora")),
            validar_aprendizado=_normalize_int(totais_operacao.get("validar_aprendizado")),
            aguardando_inspetor=_normalize_int(totais_operacao.get("aguardando_inspetor")),
            fechamento_mesa=_normalize_int(totais_operacao.get("fechamento_mesa")),
            acompanhamento=_normalize_int(totais_operacao.get("acompanhamento")),
        ),
        template_operation_summary=ReviewQueueTemplateOperationPayload(
            total_templates=_normalize_int(templates_operacao.get("total_templates")),
            total_codigos=_normalize_int(templates_operacao.get("total_codigos")),
            total_ativos=_normalize_int(templates_operacao.get("total_ativos")),
            total_em_teste=_normalize_int(templates_operacao.get("total_em_teste")),
            total_rascunhos=_normalize_int(templates_operacao.get("total_rascunhos")),
            total_word=_normalize_int(templates_operacao.get("total_word")),
            total_pdf=_normalize_int(templates_operacao.get("total_pdf")),
            total_codigos_sem_ativo=_normalize_int(templates_operacao.get("total_codigos_sem_ativo")),
            total_codigos_em_operacao=_normalize_int(templates_operacao.get("total_codigos_em_operacao")),
            total_codigos_em_operacao_sem_ativo=_normalize_int(
                templates_operacao.get("total_codigos_em_operacao_sem_ativo")
            ),
            total_bases_manuais=_normalize_int(templates_operacao.get("total_bases_manuais")),
            ultima_utilizacao_em=(
                str(templates_operacao.get("ultima_utilizacao_em") or "").strip() or None
            ),
            ultima_utilizacao_em_label=str(
                templates_operacao.get("ultima_utilizacao_em_label") or ""
            ),
        ),
        pending_whispers_preview=whispers_preview,
        queue_sections=ReviewQueueSectionsPayload(
            em_andamento=em_andamento,
            aguardando_avaliacao=aguardando,
            historico=historico,
        ),
    )

    return ReviewQueueDashboardProjectionV1(
        tenant_id=tenant_id_text,
        actor_id=str(actor_id),
        actor_role=str(actor_role or "").strip() or "revisor",
        correlation_id=correlation_id or uuid.uuid4().hex,
        causation_id=causation_id,
        idempotency_key=idempotency_key or f"review-queue-dashboard:{tenant_id_text or 'unknown'}",
        source_channel=str(source_channel or "").strip() or "review_panel",
        origin_kind="system",
        sensitivity="technical",
        visibility_scope="review_queue",
        timestamp=now,
        payload=payload.model_dump(mode="python"),
    )


__all__ = [
    "ReviewQueueDashboardProjectionPayload",
    "ReviewQueueDashboardProjectionV1",
    "ReviewQueueFilterSummaryPayload",
    "ReviewQueueItemPayload",
    "ReviewQueueOperationTotalsPayload",
    "ReviewQueueSectionsPayload",
    "ReviewQueueSummaryPayload",
    "ReviewQueueTemplateOperationPayload",
    "ReviewQueueWhisperPreviewPayload",
    "build_review_queue_dashboard_projection",
]
