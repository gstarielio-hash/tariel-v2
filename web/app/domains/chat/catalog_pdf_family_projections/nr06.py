from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR06_META: dict[str, dict[str, Any]] = {
    "nr06_gestao_epi": {
        "object_paths": ["gestao_epi", "programa_epi", "controle_epi"],
        "parameter_fields": [
            ("CA", ["ca_epi", "certificado_aprovacao"]),
            ("Entrega", ["registros_entrega_epi", "fichas_entrega"]),
            ("Higienizacao", ["higienizacao_epi", "limpeza_epi"]),
            ("Estoque", ["estoque_critico", "controle_estoque"]),
        ],
        "document_fields": [
            ("Fichas entrega", ["fichas_entrega", "registros_entrega_epi"]),
            ("CA", ["ca_epi", "certificado_aprovacao"]),
            ("Treinamento", ["treinamento_epi", "capacita_epi"]),
            ("Inventario", ["inventario_epi", "estoque_critico"]),
        ],
    },
}


def apply_nr06_projection(
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
        registry=_NR06_META,
    )
