from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR04_META: dict[str, dict[str, Any]] = {
    "nr04_diagnostico_sesmt": {
        "object_paths": ["diagnostico_sesmt", "sesmt", "programa"],
        "parameter_fields": [
            ("Dimensionamento", ["dimensionamento_sesmt", "quadro_sesmt"]),
            ("Grau risco", ["grau_risco", "grau_de_risco"]),
            ("Colaboradores", ["numero_colaboradores", "headcount"]),
            ("Cobertura", ["cobertura_unidades", "unidades_cobertas"]),
        ],
        "document_fields": [
            ("Dimensionamento", ["dimensionamento_sesmt", "planilha_dimensionamento"]),
            ("Organograma", ["organograma_sesmt", "organograma"]),
            ("Indicadores", ["indicadores_ssma", "indicadores_sesmt"]),
            ("Plano acao", ["plano_acao", "plano_melhoria"]),
        ],
    },
}


def apply_nr04_projection(
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
        registry=_NR04_META,
    )
