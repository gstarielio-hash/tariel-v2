from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR23_META: dict[str, dict[str, Any]] = {
    "nr23_inspecao_protecao_incendios": {
        "object_paths": ["protecao_incendios", "sistema_incendio", "edificacao"],
        "parameter_fields": [
            ("Extintores", ["extintores", "sistema_extintores"]),
            ("Hidrantes", ["hidrantes", "rede_hidrantes"]),
            ("Rotas", ["rotas_fuga", "saidas_emergencia"]),
            ("Brigada", ["brigada_incendio", "treinamento_brigada"]),
        ],
        "document_fields": [
            ("AVCB", ["avcb", "clcb"]),
            ("Projeto", ["projeto_incendio", "planta_incendio"]),
            ("Inspecao", ["relatorio_inspecao", "checklist_incendio"]),
            ("Brigada", ["brigada_incendio", "treinamento_brigada"]),
        ],
    },
}


def apply_nr23_projection(
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
        registry=_NR23_META,
    )
