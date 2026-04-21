from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR16_META: dict[str, dict[str, Any]] = {
    "nr16_laudo_periculosidade": {
        "object_paths": ["laudo_periculosidade", "periculosidade", "avaliacao_area"],
        "parameter_fields": [
            ("Fonte risco", ["fontes_perigo", "fontes_risco"]),
            ("Areas", ["areas_classificadas", "areas_avaliadas"]),
            ("Atividades", ["atividades_perigosas", "atividades_avaliadas"]),
            ("Enquadramento", ["enquadramento_normativo", "anexo_nr16"]),
        ],
        "document_fields": [
            ("Laudo", ["laudo_periculosidade", "documento_laudo"]),
            ("Mapa areas", ["mapa_areas_classificadas", "plantas_area"]),
            ("PT", ["permissao_trabalho", "pte"]),
            ("Inventario", ["inventario_riscos", "pgr"]),
        ],
    },
}


def apply_nr16_projection(
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
        registry=_NR16_META,
    )
