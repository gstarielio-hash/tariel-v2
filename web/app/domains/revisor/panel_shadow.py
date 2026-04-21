from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import Request

from app.domains.revisor.panel_state import ReviewPanelState
from app.v2.adapters.review_queue_dashboard import (
    ReviewQueueDashboardShadowResult,
    build_review_queue_dashboard_shadow_result,
)
from app.v2.runtime import actor_role_from_user
from app.shared.database import Usuario


def _normalize_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _dict_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_queue_item(item: Any) -> dict[str, Any]:
    payload = dict(item or {})
    payload["atualizado_em"] = _coerce_datetime(payload.get("atualizado_em"))
    payload["criado_em"] = _coerce_datetime(payload.get("criado_em"))
    return payload


def build_review_panel_projection_template_overrides(
    *,
    shadow_result: ReviewQueueDashboardShadowResult | dict[str, Any] | None,
) -> dict[str, Any] | None:
    if shadow_result is None:
        return None

    resultado = (
        shadow_result.model_dump(mode="python")
        if isinstance(shadow_result, ReviewQueueDashboardShadowResult)
        else dict(shadow_result)
    )
    if not bool(resultado.get("compatible")):
        return None

    projection = resultado.get("projection")
    if not isinstance(projection, dict):
        return None
    payload = projection.get("payload")
    if not isinstance(payload, dict):
        return None

    queue_summary = _dict_payload(payload.get("queue_summary"))
    queue_sections = _dict_payload(payload.get("queue_sections"))
    operation_totals = _dict_payload(payload.get("operation_totals"))
    template_operation_summary = _dict_payload(payload.get("template_operation_summary"))

    return {
        "whispers_pendentes": list(payload.get("pending_whispers_preview") or []),
        "laudos_em_andamento": [
            _normalize_queue_item(item)
            for item in list(queue_sections.get("em_andamento") or [])
        ],
        "laudos_pendentes": [
            _normalize_queue_item(item)
            for item in list(queue_sections.get("aguardando_avaliacao") or [])
        ],
        "laudos_avaliados": [
            _normalize_queue_item(item)
            for item in list(queue_sections.get("historico") or [])
        ],
        "total_aprendizados_pendentes": _normalize_int(queue_summary.get("total_pending_learning")),
        "total_pendencias_abertas": _normalize_int(queue_summary.get("total_open_pendencies")),
        "total_whispers_pendentes": _normalize_int(queue_summary.get("total_pending_whispers")),
        "totais_operacao": dict(operation_totals),
        "templates_operacao": dict(template_operation_summary),
        "review_queue_projection": projection,
        "review_queue_projection_preferred": True,
    }


def build_review_panel_template_context(
    *,
    request: Request,
    usuario: Usuario,
    panel_state: ReviewPanelState,
    shadow_result: ReviewQueueDashboardShadowResult | dict[str, Any] | None,
) -> dict[str, Any]:
    template_context = panel_state.to_template_context(
        request=request,
        usuario=usuario,
    )
    request.state.v2_review_queue_projection_preferred = False
    overrides = build_review_panel_projection_template_overrides(
        shadow_result=shadow_result,
    )
    if overrides is None:
        if shadow_result is not None:
            resultado = (
                shadow_result.model_dump(mode="python")
                if isinstance(shadow_result, ReviewQueueDashboardShadowResult)
                else dict(shadow_result)
            )
            if resultado.get("compatible") is False:
                request.state.v2_review_queue_projection_prefer_error = (
                    "review_queue_projection_diverged_from_legacy"
                )
        return template_context
    request.state.v2_review_queue_projection_preferred = True
    return {
        **template_context,
        **overrides,
    }


def registrar_shadow_review_queue_dashboard(
    *,
    request: Request,
    usuario: Usuario,
    panel_state: ReviewPanelState,
) -> ReviewQueueDashboardShadowResult | None:
    resultado = build_review_queue_dashboard_shadow_result(
        tenant_id=usuario.empresa_id,
        filtro_inspetor_id=panel_state.filtro_inspetor_id,
        filtro_busca=panel_state.filtro_busca,
        filtro_aprendizados=panel_state.filtro_aprendizados,
        filtro_operacao=panel_state.filtro_operacao,
        whispers_pendentes=panel_state.whispers_pendentes,
        laudos_em_andamento=panel_state.laudos_em_andamento,
        laudos_pendentes=panel_state.laudos_pendentes,
        laudos_avaliados=panel_state.laudos_avaliados,
        total_aprendizados_pendentes=panel_state.total_aprendizados_pendentes,
        total_pendencias_abertas=panel_state.total_pendencias_abertas,
        total_whispers_pendentes=panel_state.total_whispers_pendentes,
        totais_operacao=panel_state.totais_operacao,
        templates_operacao=panel_state.templates_operacao,
        actor_id=usuario.id,
        actor_role=actor_role_from_user(usuario),
        source_channel="review_panel",
        legacy_dashboard_data={
            "filtro_inspetor_id": panel_state.filtro_inspetor_id,
            "filtro_busca": panel_state.filtro_busca,
            "filtro_aprendizados": panel_state.filtro_aprendizados,
            "filtro_operacao": panel_state.filtro_operacao,
            "total_aprendizados_pendentes": panel_state.total_aprendizados_pendentes,
            "total_pendencias_abertas": panel_state.total_pendencias_abertas,
            "total_whispers_pendentes": panel_state.total_whispers_pendentes,
            "totais_operacao": panel_state.totais_operacao,
            "templates_operacao": panel_state.templates_operacao,
        },
    )
    request.state.v2_review_queue_projection_result = resultado.model_dump(mode="python")
    return resultado


__all__ = [
    "build_review_panel_template_context",
    "build_review_panel_projection_template_overrides",
    "registrar_shadow_review_queue_dashboard",
]
