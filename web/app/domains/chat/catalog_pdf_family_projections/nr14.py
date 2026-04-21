from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR14_META: dict[str, dict[str, Any]] = {
    "nr14_inspecao_forno_industrial": {
        "object_paths": ["forno_industrial", "forno", "linha_termica"],
        "parameter_fields": [
            ("Temperatura", ["temperatura_operacao", "temperatura"]),
            ("Combustivel", ["combustivel", "linha_combustivel"]),
            ("Intertravamentos", ["intertravamentos", "sistemas_seguranca"]),
            ("Exaustao", ["exaustao", "ventilacao_exaustao"]),
        ],
        "document_fields": [
            ("Procedimento", ["procedimento_partida_parada", "procedimento_operacional"]),
            ("Inspecao", ["relatorio_inspecao", "laudo_tecnico"]),
            ("Calibracao", ["calibracao_instrumentos", "certificados_calibracao"]),
            ("Manutencao", ["plano_manutencao", "ordens_servico"]),
        ],
    },
}


def apply_nr14_projection(
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
        registry=_NR14_META,
    )
