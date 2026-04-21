from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR11_META: dict[str, dict[str, Any]] = {
    "nr11_inspecao_movimentacao_armazenagem": {
        "object_paths": ["movimentacao_armazenagem", "centro_distribuicao", "armazenagem"],
        "parameter_fields": [
            ("Empilhadeiras", ["empilhadeiras", "equipamentos_movimentacao"]),
            ("Armazenagem", ["armazenagem", "porta_paletes"]),
            ("Sinalizacao", ["sinalizacao", "demarcacao_solo"]),
            ("Treinamento", ["treinamento_operadores", "habilitacao_operadores"]),
        ],
        "document_fields": [
            ("Checklist", ["checklist_operacao", "checklist_equipamentos"]),
            ("Treinamento", ["treinamento_operadores"]),
            ("Plano trafego", ["plano_trafego", "fluxo_interno"]),
            ("Procedimento", ["procedimento_operacional", "instrucoes_trabalho"]),
        ],
    },
    "nr11_inspecao_equipamento_icamento": {
        "object_paths": ["equipamento_icamento", "equipamento_içamento", "guindaste"],
        "parameter_fields": [
            ("Guindaste", ["guindaste", "equipamento_içamento", "equipamento_icamento"]),
            ("Carga", ["carga_maxima", "capacidade_nominal"]),
            ("Acessorios", ["acessorios_içamento", "acessorios_icamento", "lingas"]),
            ("Plano", ["plano_içamento", "plano_icamento"]),
        ],
        "document_fields": [
            ("Plano icamento", ["plano_içamento", "plano_icamento"]),
            ("Checklist", ["checklist_equipamento", "checklist_icamento"]),
            ("ART", ["art", "art_numero"]),
            ("Certificados", ["certificados_acessorios", "certificados"]),
        ],
    },
}


def apply_nr11_projection(
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
        registry=_NR11_META,
    )
