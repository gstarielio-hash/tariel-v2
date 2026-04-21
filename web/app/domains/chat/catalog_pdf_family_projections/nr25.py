from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR25_META: dict[str, dict[str, Any]] = {
    "nr25_gestao_residuos_industriais": {
        "object_paths": ["gestao_residuos", "pgrs", "residuos_industriais"],
        "parameter_fields": [
            ("Inventario", ["inventario_residuos", "tipos_residuos"]),
            ("Segregacao", ["segregacao_residuos", "segregacao"]),
            ("Destinacao", ["destinacao_final", "mtrs"]),
            ("Armazenamento", ["armazenamento_temporario", "abrigo_residuos"]),
        ],
        "document_fields": [
            ("PGRS", ["pgrs", "plano_gerenciamento_residuos"]),
            ("MTR", ["mtr", "mtrs"]),
            ("Licencas", ["licencas_ambientais", "licenca_ambiental"]),
            ("Manifestos", ["manifestos_transporte", "ctr"]),
        ],
    },
}


def apply_nr25_projection(
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
        registry=_NR25_META,
    )
