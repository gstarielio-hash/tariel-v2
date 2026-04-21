from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR26_META: dict[str, dict[str, Any]] = {
    "nr26_sinalizacao_seguranca": {
        "object_paths": ["sinalizacao_seguranca", "sinalizacao", "rota_emergencia"],
        "parameter_fields": [
            ("Placas", ["placas_sinalizacao", "placas"]),
            ("Demarcacao", ["demarcacao_solo", "demarcacoes"]),
            ("Rotas", ["rotas_fuga", "sinalizacao_emergencia"]),
            ("Bloqueio", ["bloqueio_identificacao", "etiquetagem"]),
        ],
        "document_fields": [
            ("Projeto", ["projeto_sinalizacao", "layout_sinalizacao"]),
            ("Checklist", ["checklist_sinalizacao", "relatorio_inspecao"]),
            ("Inventario", ["inventario_placas", "lista_placas"]),
            ("Plano acao", ["plano_acao", "acoes_corretivas"]),
        ],
    },
}


def apply_nr26_projection(
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
        registry=_NR26_META,
    )
