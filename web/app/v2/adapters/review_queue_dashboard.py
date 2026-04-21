"""Adapter incremental da projecao canonica da fila da mesa para o painel legado."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.review_queue import build_review_queue_dashboard_projection


class ReviewQueueDashboardShadowResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["ReviewQueueDashboardShadowResultV1"] = "ReviewQueueDashboardShadowResultV1"
    contract_version: str = "v1"
    compatible: bool
    divergences: list[str] = Field(default_factory=list)
    used_projection: bool = True
    delivery_mode: Literal["shadow_only"] = "shadow_only"
    observed_case_count: int = 0
    projection: dict[str, Any]


def _normalize_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _ids(items: Iterable[dict[str, Any]]) -> list[str]:
    return [str(_normalize_int(item.get("id"))) for item in items if _normalize_int(item.get("id")) > 0]


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text_list(values: Any) -> list[str]:
    return [
        _normalize_text(value)
        for value in list(values or [])
        if _normalize_text(value)
    ]


def _compare_queue_item_fields(
    *,
    divergences: list[str],
    section_name: str,
    legacy_items: list[dict[str, Any]],
    projected_items: list[dict[str, Any]],
) -> None:
    for index, (legacy_item, projected_item) in enumerate(zip(legacy_items, projected_items, strict=False)):
        if _normalize_int(legacy_item.get("id")) != _normalize_int(projected_item.get("id")):
            divergences.append(f"queue_sections.{section_name}[{index}].id")
        if _normalize_text(projected_item.get("queue_section")) != section_name:
            divergences.append(f"queue_sections.{section_name}[{index}].queue_section")
        for field_name in (
            "fila_operacional",
            "status_revisao",
            "case_status",
            "case_lifecycle_status",
            "case_workflow_mode",
            "active_owner_role",
            "proxima_acao",
        ):
            if _normalize_text(legacy_item.get(field_name)) != _normalize_text(projected_item.get(field_name)):
                divergences.append(f"queue_sections.{section_name}[{index}].{field_name}")
        for field_name in ("allowed_next_lifecycle_statuses", "allowed_surface_actions"):
            if _normalize_text_list(legacy_item.get(field_name)) != _normalize_text_list(
                projected_item.get(field_name)
            ):
                divergences.append(f"queue_sections.{section_name}[{index}].{field_name}")


def build_review_queue_dashboard_shadow_result(
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
    legacy_dashboard_data: dict[str, Any],
    correlation_id: str | None = None,
    timestamp: datetime | None = None,
) -> ReviewQueueDashboardShadowResult:
    whispers = list(whispers_pendentes)
    em_andamento = list(laudos_em_andamento)
    aguardando = list(laudos_pendentes)
    historico = list(laudos_avaliados)

    projection = build_review_queue_dashboard_projection(
        tenant_id=tenant_id,
        filtro_inspetor_id=filtro_inspetor_id,
        filtro_busca=filtro_busca,
        filtro_aprendizados=filtro_aprendizados,
        filtro_operacao=filtro_operacao,
        whispers_pendentes=whispers,
        laudos_em_andamento=em_andamento,
        laudos_pendentes=aguardando,
        laudos_avaliados=historico,
        total_aprendizados_pendentes=total_aprendizados_pendentes,
        total_pendencias_abertas=total_pendencias_abertas,
        total_whispers_pendentes=total_whispers_pendentes,
        totais_operacao=totais_operacao,
        templates_operacao=templates_operacao,
        actor_id=actor_id,
        actor_role=actor_role,
        source_channel=source_channel,
        correlation_id=correlation_id,
        timestamp=timestamp,
    )

    payload = projection.payload
    queue_summary = payload.get("queue_summary", {})
    filter_summary = payload.get("filter_summary", {})
    template_summary = payload.get("template_operation_summary", {})
    operation_totals = payload.get("operation_totals", {})
    legacy_totais = legacy_dashboard_data.get("totais_operacao", {})
    legacy_templates = legacy_dashboard_data.get("templates_operacao", {})

    divergences: list[str] = []
    if _normalize_int(filter_summary.get("inspector_id")) != _normalize_int(
        legacy_dashboard_data.get("filtro_inspetor_id")
    ):
        divergences.append("filtro_inspetor_id")
    if str(filter_summary.get("search_query") or "") != str(legacy_dashboard_data.get("filtro_busca") or ""):
        divergences.append("filtro_busca")
    if str(filter_summary.get("learning_filter") or "") != str(
        legacy_dashboard_data.get("filtro_aprendizados") or ""
    ):
        divergences.append("filtro_aprendizados")
    if str(filter_summary.get("operation_filter") or "") != str(
        legacy_dashboard_data.get("filtro_operacao") or ""
    ):
        divergences.append("filtro_operacao")
    if _normalize_int(queue_summary.get("in_field_count")) != len(em_andamento):
        divergences.append("in_field_count")
    if _normalize_int(queue_summary.get("awaiting_review_count")) != len(aguardando):
        divergences.append("awaiting_review_count")
    if _normalize_int(queue_summary.get("recent_history_count")) != len(historico):
        divergences.append("recent_history_count")
    if _normalize_int(queue_summary.get("whisper_pending_count")) != len(whispers):
        divergences.append("whisper_pending_count")
    if _normalize_int(queue_summary.get("total_pending_learning")) != _normalize_int(
        legacy_dashboard_data.get("total_aprendizados_pendentes")
    ):
        divergences.append("total_pending_learning")
    if _normalize_int(queue_summary.get("total_open_pendencies")) != _normalize_int(
        legacy_dashboard_data.get("total_pendencias_abertas")
    ):
        divergences.append("total_open_pendencies")
    if _normalize_int(queue_summary.get("total_pending_whispers")) != _normalize_int(
        legacy_dashboard_data.get("total_whispers_pendentes")
    ):
        divergences.append("total_pending_whispers")
    if list(queue_summary.get("observed_case_ids") or []) != [*_ids(em_andamento), *_ids(aguardando), *_ids(historico)]:
        divergences.append("observed_case_ids")

    queue_sections = payload.get("queue_sections", {})
    _compare_queue_item_fields(
        divergences=divergences,
        section_name="em_andamento",
        legacy_items=em_andamento,
        projected_items=list(queue_sections.get("em_andamento") or []),
    )
    _compare_queue_item_fields(
        divergences=divergences,
        section_name="aguardando_avaliacao",
        legacy_items=aguardando,
        projected_items=list(queue_sections.get("aguardando_avaliacao") or []),
    )
    _compare_queue_item_fields(
        divergences=divergences,
        section_name="historico",
        legacy_items=historico,
        projected_items=list(queue_sections.get("historico") or []),
    )

    for chave in (
        "responder_agora",
        "validar_aprendizado",
        "aguardando_inspetor",
        "fechamento_mesa",
        "acompanhamento",
    ):
        if _normalize_int(operation_totals.get(chave)) != _normalize_int(legacy_totais.get(chave)):
            divergences.append(f"operation_totals.{chave}")

    for chave in (
        "total_templates",
        "total_codigos",
        "total_ativos",
        "total_em_teste",
        "total_rascunhos",
        "total_word",
        "total_pdf",
        "total_codigos_sem_ativo",
        "total_codigos_em_operacao",
        "total_codigos_em_operacao_sem_ativo",
        "total_bases_manuais",
    ):
        if _normalize_int(template_summary.get(chave)) != _normalize_int(legacy_templates.get(chave)):
            divergences.append(f"template_operation_summary.{chave}")

    return ReviewQueueDashboardShadowResult(
        compatible=not divergences,
        divergences=divergences,
        observed_case_count=len(queue_summary.get("observed_case_ids") or []),
        projection=projection.model_dump(mode="python"),
    )


__all__ = [
    "ReviewQueueDashboardShadowResult",
    "build_review_queue_dashboard_shadow_result",
]
