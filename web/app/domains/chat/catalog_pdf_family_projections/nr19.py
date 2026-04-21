from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR19_META: dict[str, dict[str, Any]] = {
    "nr19_inspecao_area_explosivos": {
        "object_paths": ["area_explosivos", "paiol", "explosivos"],
        "parameter_fields": [
            ("Armazenamento", ["armazenamento_explosivos", "paiol"]),
            ("Distancias", ["distancias_seguranca", "distanciamento"]),
            ("Controle acesso", ["controle_acesso", "segregacao_area"]),
            ("Plano emergencia", ["plano_emergencia", "resposta_emergencia"]),
        ],
        "document_fields": [
            ("Licenca", ["licenca_explosivos", "autorizacao_explosivos"]),
            ("Mapa", ["mapa_paiol", "planta_area"]),
            ("Plano emergencia", ["plano_emergencia"]),
            ("Procedimento", ["procedimento_operacional", "instrucoes_trabalho"]),
        ],
    },
}


def apply_nr19_projection(
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
        registry=_NR19_META,
    )
