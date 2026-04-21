from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR17_META: dict[str, dict[str, Any]] = {
    "nr17_analise_ergonomica_trabalho": {
        "object_paths": ["analise_ergonomica_trabalho", "aet", "ergonomia"],
        "parameter_fields": [
            ("Postos", ["postos_avaliados", "posto_trabalho"]),
            ("Biomecanica", ["sobrecarga_biomecanica", "demanda_postural"]),
            ("Organizacao", ["organizacao_trabalho", "ritmo_jornada"]),
            ("Plano acao", ["plano_acao", "acoes_ergonomicas"]),
        ],
        "document_fields": [
            ("AET", ["aet", "analise_ergonomica"]),
            ("Checklist", ["checklist_ergonomico", "checklist_ergonomia"]),
            ("Medicoes", ["medicoes", "registros_medicao"]),
            ("Plano acao", ["plano_acao"]),
        ],
    },
    "nr17_checklist_ergonomia": {
        "object_paths": ["checklist_ergonomia", "ergonomia", "posto_trabalho"],
        "parameter_fields": [
            ("Posto", ["posto_trabalho", "postos_avaliados"]),
            ("Mobiliario", ["mobiliario", "posto_mobiliario"]),
            ("Iluminacao", ["iluminacao", "conforto_visual"]),
            ("Pausas", ["pausas", "ritmo_jornada"]),
        ],
        "document_fields": [
            ("Checklist", ["checklist_ergonomia", "checklist_ergonomico"]),
            ("Fotos", ["registro_fotografico", "evidencias"]),
            ("Plano acao", ["plano_acao", "acoes_ergonomicas"]),
            ("Treinamento", ["treinamento_ergonomia", "orientacoes"]),
        ],
    },
}


def apply_nr17_projection(
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
        registry=_NR17_META,
    )
