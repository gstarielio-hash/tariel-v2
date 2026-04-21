from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR08_META: dict[str, dict[str, Any]] = {
    "nr08_inspecao_edificacao_industrial": {
        "object_paths": ["edificacao_industrial", "edificacao", "predio_industrial"],
        "parameter_fields": [
            ("Estrutura", ["estrutura_civil", "integridade_estrutura"]),
            ("Cobertura", ["cobertura", "telhado"]),
            ("Acessos", ["acessos", "rotas_fuga"]),
            ("Instalacoes", ["instalacoes_apoio", "instalacoes_prediais"]),
        ],
        "document_fields": [
            ("Laudo estrutural", ["laudo_estrutural", "relatorio_tecnico"]),
            ("Plano manutencao", ["plano_manutencao", "cronograma_manutencao"]),
            ("AVCB", ["avcb", "clcb"]),
            ("Projeto", ["projeto_executivo", "plantas"]),
        ],
    },
}


def apply_nr08_projection(
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
        registry=_NR08_META,
    )
