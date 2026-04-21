from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR24_META: dict[str, dict[str, Any]] = {
    "nr24_condicoes_sanitarias_conforto": {
        "object_paths": ["condicoes_sanitarias", "instalacoes_conforto", "ambiente_apoio"],
        "parameter_fields": [
            ("Sanitarios", ["sanitarios", "instalacoes_sanitarias"]),
            ("Vestiarios", ["vestiarios", "instalacoes_vestiario"]),
            ("Refeitorio", ["refeitorio", "area_refeicao"]),
            ("Limpeza", ["higienizacao", "limpeza"]),
        ],
        "document_fields": [
            ("Checklist", ["checklist_sanitario", "checklist_conforto"]),
            ("Plano limpeza", ["plano_limpeza", "procedimento_limpeza"]),
            ("Manutencao", ["plano_manutencao", "ordens_servico"]),
            ("Treinamento", ["treinamento_higiene", "registro_treinamento"]),
        ],
    },
}


def apply_nr24_projection(
    *,
    payload: dict[str, Any],
    existing_payload: dict[str, Any] | None,
    family_key: str,
    laudo: Laudo | None,
    location_hint: str | None,
    summary_hint: str | None,
    recommendation_hint: str | None,
    title_hint: str | None,
) -> None:
    apply_wave3_generic_projection(
        payload=payload,
        existing_payload=existing_payload,
        family_key=family_key,
        laudo=laudo,
        location_hint=location_hint,
        summary_hint=summary_hint,
        recommendation_hint=recommendation_hint,
        title_hint=title_hint,
        registry=_NR24_META,
    )
