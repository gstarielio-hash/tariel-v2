from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR09_META: dict[str, dict[str, Any]] = {
    "nr09_avaliacao_exposicoes_ocupacionais": {
        "object_paths": ["avaliacao_exposicoes", "avaliacao_higienica", "ghe"],
        "parameter_fields": [
            ("Agentes", ["agentes_avaliados", "agentes_ocupacionais"]),
            ("Dosimetria", ["dosimetria", "avaliacao_quantitativa"]),
            ("GHE", ["ghe", "grupos_homogeneos"]),
            ("Controles", ["medidas_controle", "controles_existentes"]),
        ],
        "document_fields": [
            ("Relatorio higienico", ["relatorio_higienico", "relatorio_avaliacao"]),
            ("Planilha", ["planilha_amostragem", "dosimetria"]),
            ("Calibracao", ["certificados_calibracao", "calibracao"]),
            ("Inventario", ["inventario_riscos", "pgr"]),
        ],
    },
}


def apply_nr09_projection(
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
        registry=_NR09_META,
    )
