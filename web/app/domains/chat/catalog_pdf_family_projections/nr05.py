from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR05_META: dict[str, dict[str, Any]] = {
    "nr05_implantacao_cipa": {
        "object_paths": ["implantacao_cipa", "cipa", "comissao_interna"],
        "parameter_fields": [
            ("Mandato", ["mandato_cipa", "vigencia_mandato"]),
            ("Representacao", ["representantes", "membros_cipa"]),
            ("Calendario", ["calendario_reunioes", "agenda_reunioes"]),
            ("Treinamento", ["treinamento_cipa", "capacitacao"]),
        ],
        "document_fields": [
            ("Ata", ["ata_eleicao", "ata_posse"]),
            ("Calendario", ["calendario_reunioes"]),
            ("Treinamento", ["treinamento_cipa", "registro_treinamento"]),
            ("Mapa riscos", ["mapa_riscos", "inventario_riscos"]),
        ],
    },
    "nr05_auditoria_cipa": {
        "object_paths": ["auditoria_cipa", "cipa", "comissao_interna"],
        "parameter_fields": [
            ("Reunioes", ["reunioes_realizadas", "atas_reunioes"]),
            ("Inspecoes", ["inspecoes_cipa", "inspecoes_realizadas"]),
            ("Plano acao", ["plano_acao", "acoes_pendentes"]),
            ("Treinamento", ["treinamento_cipa", "reciclagem"]),
        ],
        "document_fields": [
            ("Atas", ["atas_reunioes", "ata_reuniao"]),
            ("Plano acao", ["plano_acao"]),
            ("Evidencias", ["evidencias_auditoria", "registro_evidencias"]),
            ("Treinamento", ["treinamento_cipa"]),
        ],
    },
}


def apply_nr05_projection(
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
        registry=_NR05_META,
    )
