from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR21_META: dict[str, dict[str, Any]] = {
    "nr21_condicoes_trabalho_ceu_aberto": {
        "object_paths": ["condicoes_ceu_aberto", "frente_ceu_aberto", "frente_trabalho"],
        "parameter_fields": [
            ("Abrigos", ["abrigos", "protecoes_climaticas"]),
            ("Hidratacao", ["hidratacao", "pontos_agua"]),
            ("Jornada", ["jornada", "pausas"]),
            ("Acesso", ["acessos", "vias_circulacao"]),
        ],
        "document_fields": [
            ("PGR", ["pgr", "documento_pgr"]),
            ("APR", ["apr", "analise_preliminar_risco"]),
            ("Clima", ["plano_contingencia_climatica", "monitoramento_climatico"]),
            ("Treinamento", ["treinamento_equipes", "registro_treinamento"]),
        ],
    },
}


def apply_nr21_projection(
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
        registry=_NR21_META,
    )
