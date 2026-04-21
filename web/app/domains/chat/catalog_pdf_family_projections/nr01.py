from __future__ import annotations

from typing import Any

from app.shared.database import Laudo

from .wave3_common import apply_wave3_generic_projection

_NR01_META: dict[str, dict[str, Any]] = {
    "nr01_gro_pgr": {
        "object_paths": ["gro_pgr", "programa_gro_pgr", "programa"],
        "parameter_fields": [
            ("Inventario riscos", ["inventario_riscos", "inventario_riscos_ocupacionais"]),
            ("Plano acao", ["plano_acao", "plano_acao_riscos"]),
            ("Processos", ["processos_avaliados", "processos_escopo"]),
            ("Responsavel", ["responsavel_programa", "responsavel_tecnico"]),
        ],
        "document_fields": [
            ("PGR", ["pgr", "documento_pgr"]),
            ("Inventario", ["inventario_riscos", "inventario_riscos_ocupacionais"]),
            ("Plano acao", ["plano_acao", "cronograma_plano_acao"]),
            ("Matriz", ["matriz_riscos", "matriz_risco"]),
        ],
    },
    "nr01_ordem_servico_sst": {
        "object_paths": ["ordem_servico_sst", "ordem_servico", "programa"],
        "parameter_fields": [
            ("Funcoes", ["funcoes_cobertas", "cargos_cobertos"]),
            ("Treinamento", ["treinamento_obrigatorio", "integracao_sst"]),
            ("EPIs", ["epis_exigidos", "epi"]),
            ("Regras", ["regras_execucao", "medidas_disciplinares"]),
        ],
        "document_fields": [
            ("Ordem servico", ["ordem_servico", "documento_ordem_servico"]),
            ("Lista funcoes", ["lista_funcoes", "funcoes_cobertas"]),
            ("Registros", ["registros_ciencia", "assinaturas_colaboradores"]),
            ("Treinamento", ["treinamento_obrigatorio", "registro_treinamento"]),
        ],
    },
}


def apply_nr01_projection(
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
        registry=_NR01_META,
    )
