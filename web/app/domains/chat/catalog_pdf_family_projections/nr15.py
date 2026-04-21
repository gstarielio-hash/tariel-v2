from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR15_META: dict[str, dict[str, Any]] = {
    "nr15_laudo_insalubridade": {
        "object_paths": ["laudo_insalubridade", "insalubridade", "avaliacao_ambiente"],
        "parameter_fields": [
            ("Agentes", ["agentes_insalubres", "agentes_avaliados"]),
            ("Setores", ["setores_avaliados", "setores"]),
            ("Dosimetria", ["dosimetria", "avaliacao_quantitativa"]),
            ("Enquadramento", ["enquadramento_normativo", "anexo_nr15"]),
        ],
        "document_fields": [
            ("Laudo", ["laudo_insalubridade", "documento_laudo"]),
            ("Planilha", ["planilha_amostragem", "dosimetria"]),
            ("LTCAT", ["ltcat", "ltcat_correlato"]),
            ("Inventario", ["inventario_riscos", "pgr"]),
        ],
    },
}


def apply_nr15_projection(
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
        registry=_NR15_META,
    )
