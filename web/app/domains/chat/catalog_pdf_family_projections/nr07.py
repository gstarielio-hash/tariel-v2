from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR07_META: dict[str, dict[str, Any]] = {
    "nr07_pcmso": {
        "object_paths": ["pcmso", "programa_pcmso", "controle_medico"],
        "parameter_fields": [
            ("ASO", ["aso", "controle_aso"]),
            ("Exames", ["exames_ocupacionais", "programa_exames"]),
            ("Cronograma", ["cronograma_pcmso", "vigencia_pcmso"]),
            ("Coordenador", ["medico_coordenador", "responsavel_pcmso"]),
        ],
        "document_fields": [
            ("PCMSO", ["pcmso", "documento_pcmso"]),
            ("ASO", ["aso", "controle_aso"]),
            ("Relatorio anual", ["relatorio_anual", "relatorio_pcmso"]),
            ("Rede", ["rede_credenciada", "prestadores"]),
        ],
    },
}


def apply_nr07_projection(
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
        registry=_NR07_META,
    )
