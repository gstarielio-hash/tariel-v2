"""Helpers de normalização e catálogos do domínio Chat/Inspetor."""

from __future__ import annotations

import re

SETORES_PERMITIDOS = frozenset(
    {
        "geral",
        "eletrica",
        "mecanica",
        "caldeiraria",
        "spda",
        "loto",
        "nr11",
        "nr10",
        "nr12",
        "nr13",
        "nr20",
        "nr33",
        "nr35",
        "avcb",
        "pie",
        "rti",
    }
)

TIPOS_TEMPLATE_VALIDOS = {
    "cbmgo": "CBM-GO Vistoria Bombeiro",
    "loto": "NR-10 LOTO",
    "nr11_movimentacao": "NR-11 Movimentacao e Armazenagem",
    "nr12maquinas": "NR-12 Maquinas e Equipamentos",
    "nr13": "NR-13 Inspecoes e Integridade",
    "nr13_calibracao": "NR-13 Calibracao de Valvulas e Manometros",
    "nr13_teste_hidrostatico": "NR-13 Teste Hidrostatico e Estanqueidade",
    "nr13_ultrassom": "NR-13 Medicao por Ultrassom",
    "nr20_instalacoes": "NR-20 Instalacoes e Analise de Riscos",
    "nr33_espaco_confinado": "NR-33 Espaco Confinado",
    "nr35_linha_vida": "NR-35 Inspecao de Linha de Vida",
    "nr35_montagem": "NR-35 Montagem e Fabricacao",
    "nr35_ponto_ancoragem": "NR-35 Ponto de Ancoragem",
    "nr35_projeto": "NR-35 Projeto de Protecao Contra Queda",
    "rti": "NR-10 RTI Elétrica",
    "nr10_rti": "NR-10 RTI Elétrica",
    "nr13_caldeira": "NR-13 Inspecoes e Integridade",
    "nr12_maquinas": "NR-12 Maquinas e Equipamentos",
    "spda": "SPDA Proteção Descargas",
    "pie": "PIE Instalações Elétricas",
    "avcb": "AVCB Projeto Bombeiro",
    "padrao": "Inspeção Geral (Padrão)",
}

FAMILIAS_PADRAO_POR_TEMPLATE: dict[str, dict[str, str]] = {
    "spda": {
        "family_key": "nr10_inspecao_spda",
        "family_label": "NR10 Inspecao de SPDA",
    },
    "loto": {
        "family_key": "nr10_implantacao_loto",
        "family_label": "NR10 Implantacao e Gerenciamento de LOTO",
    },
    "rti": {
        "family_key": "nr10_inspecao_instalacoes_eletricas",
        "family_label": "NR10 Inspecao de Instalacoes Eletricas",
    },
    "pie": {
        "family_key": "nr10_prontuario_instalacoes_eletricas",
        "family_label": "NR10 Prontuario das Instalacoes Eletricas",
    },
    "nr11_movimentacao": {
        "family_key": "nr11_inspecao_movimentacao_armazenagem",
        "family_label": "NR11 Inspecao de Movimentacao e Armazenagem",
    },
    "nr12maquinas": {
        "family_key": "nr12_inspecao_maquina_equipamento",
        "family_label": "NR12 Inspecao de Maquina e Equipamento",
    },
    "nr13": {
        "family_key": "nr13_inspecao_caldeira",
        "family_label": "NR13 Inspecao de Caldeira",
    },
    "nr13_calibracao": {
        "family_key": "nr13_calibracao_valvulas_manometros",
        "family_label": "NR13 Calibracao de Valvulas e Manometros",
    },
    "nr13_ultrassom": {
        "family_key": "nr13_calculo_espessura_minima_vaso_pressao",
        "family_label": "NR13 Calculo de Espessura Minima por Ultrassom",
    },
    "nr13_teste_hidrostatico": {
        "family_key": "nr13_teste_hidrostatico",
        "family_label": "NR13 Teste Hidrostatico",
    },
    "nr20_instalacoes": {
        "family_key": "nr20_inspecao_instalacoes_inflamaveis",
        "family_label": "NR20 Inspecao de Instalacoes com Inflamaveis",
    },
    "nr33_espaco_confinado": {
        "family_key": "nr33_avaliacao_espaco_confinado",
        "family_label": "NR33 Avaliacao de Espaco Confinado",
    },
    "nr35_linha_vida": {
        "family_key": "nr35_inspecao_linha_de_vida",
        "family_label": "NR35 Inspecao de Linha de Vida",
    },
    "nr35_ponto_ancoragem": {
        "family_key": "nr35_inspecao_ponto_ancoragem",
        "family_label": "NR35 Inspecao de Ponto de Ancoragem",
    },
    "nr35_projeto": {
        "family_key": "nr35_projeto_protecao_queda",
        "family_label": "NR35 Projeto de Protecao Contra Queda",
    },
    "nr35_montagem": {
        "family_key": "nr35_montagem_linha_de_vida",
        "family_label": "NR35 Montagem e Fabricacao de Linha de Vida",
    },
}

ALIASES_TEMPLATE = {
    "calibracao_manometros": "nr13_calibracao",
    "calibracao_valvulas_seguranca": "nr13_calibracao",
    "loto": "loto",
    "loto_nr10": "loto",
    "nr10": "rti",
    "nr10_implantacao_loto": "loto",
    "nr10_inspecao_spda": "spda",
    "nr10_inspecao_instalacoes_eletricas": "rti",
    "nr10_loto": "loto",
    "nr10_pie": "pie",
    "nr10_prontuario_instalacoes_eletricas": "pie",
    "nr10_spda": "spda",
    "nr11": "nr11_movimentacao",
    "nr11_inspecao_equipamento_icamento": "nr11_movimentacao",
    "nr11_inspecao_movimentacao_armazenagem": "nr11_movimentacao",
    "nr11_movimentacao": "nr11_movimentacao",
    "nr35": "nr35_linha_vida",
    "nr35_fabricacao": "nr35_montagem",
    "nr35_fabricacao_linha_vida": "nr35_montagem",
    "nr35_inspecao_linha_de_vida": "nr35_linha_vida",
    "nr35_inspecao_ponto_ancoragem": "nr35_ponto_ancoragem",
    "nr35_linha_vida": "nr35_linha_vida",
    "nr35_montagem": "nr35_montagem",
    "nr35_montagem_geral": "nr35_montagem",
    "nr35_montagem_linha_de_vida": "nr35_montagem",
    "nr35_ponto_ancoragem": "nr35_ponto_ancoragem",
    "nr35_projeto": "nr35_projeto",
    "nr35_projeto_protecao_queda": "nr35_projeto",
    "nr35_projeto_linha_vida": "nr35_projeto",
    "nr35_usina": "nr35_linha_vida",
    "linha_vida_nr35": "nr35_linha_vida",
    "projeto_nr35": "nr35_projeto",
    "nr12": "nr12maquinas",
    "nr12_apreciacao_risco_maquina": "nr12maquinas",
    "nr12_inspecao_maquina_equipamento": "nr12maquinas",
    "nr12_maquinas": "nr12maquinas",
    "nr12maquinas": "nr12maquinas",
    "rti": "rti",
    "nr10_rti": "rti",
    "nr13": "nr13",
    "nr13_caldeira": "nr13",
    "nr13_calculo_espessura_minima_tubulacao": "nr13_ultrassom",
    "nr13_calculo_espessura_minima_vaso_pressao": "nr13_ultrassom",
    "nr13_calibracao": "nr13_calibracao",
    "nr13_calibracao_valvulas_manometros": "nr13_calibracao",
    "nr13_inspecao_caldeira": "nr13",
    "nr13_inspecao_tubulacao": "nr13",
    "nr13_inspecao_vaso_pressao": "nr13",
    "nr13_integridade_caldeira": "nr13",
    "nr13_medicao_espessura_ultrassom": "nr13_ultrassom",
    "nr13_teste_estanqueidade_tubulacao_gas": "nr13_teste_hidrostatico",
    "nr13_teste_hidrostatico": "nr13_teste_hidrostatico",
    "nr13_ultrassom": "nr13_ultrassom",
    "nr20": "nr20_instalacoes",
    "nr20_inspecao_instalacoes_inflamaveis": "nr20_instalacoes",
    "nr20_instalacoes": "nr20_instalacoes",
    "nr20_prontuario_instalacoes_inflamaveis": "nr20_instalacoes",
    "nr33": "nr33_espaco_confinado",
    "nr33_avaliacao_espaco_confinado": "nr33_espaco_confinado",
    "nr33_espaco_confinado": "nr33_espaco_confinado",
    "nr33_permissao_entrada_trabalho": "nr33_espaco_confinado",
    "cbmgo": "cbmgo",
    "spda": "spda",
    "pie": "pie",
    "avcb": "avcb",
    "padrao": "padrao",
}


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def normalizar_setor(valor: str) -> str:
    setor = (valor or "").strip().lower()
    return setor if setor in SETORES_PERMITIDOS else "geral"


def normalizar_tipo_template(valor: str) -> str:
    bruto = (valor or "").strip().lower()
    return ALIASES_TEMPLATE.get(bruto, "padrao")


def codigos_template_compativeis(tipo_template: str) -> list[str]:
    tipo = normalizar_tipo_template(tipo_template)
    variantes_por_tipo: dict[str, list[str]] = {
        "cbmgo": ["cbmgo", "cbmgo_cmar", "checklist_cbmgo"],
        "loto": ["loto", "loto_nr10", "nr10_loto", "nr10_implantacao_loto"],
        "nr11_movimentacao": [
            "nr11_movimentacao",
            "nr11",
            "nr11_inspecao_movimentacao_armazenagem",
            "nr11_inspecao_equipamento_icamento",
        ],
        "nr35_linha_vida": [
            "nr35_linha_vida",
            "nr35",
            "nr35_usina",
            "linha_vida_nr35",
            "nr35_inspecao_linha_de_vida",
        ],
        "nr35_montagem": [
            "nr35_montagem",
            "nr35_montagem_geral",
            "nr35_fabricacao",
            "nr35_fabricacao_linha_vida",
            "nr35_montagem_linha_de_vida",
        ],
        "nr35_ponto_ancoragem": [
            "nr35_ponto_ancoragem",
            "nr35_inspecao_ponto_ancoragem",
        ],
        "nr35_projeto": [
            "nr35_projeto",
            "nr35_projeto_linha_vida",
            "projeto_nr35",
            "nr35_projeto_protecao_queda",
        ],
        "rti": ["rti", "nr10_rti"],
        "nr12maquinas": [
            "nr12maquinas",
            "nr12_maquinas",
            "nr12",
            "nr12_inspecao_maquina_equipamento",
            "nr12_apreciacao_risco_maquina",
        ],
        "nr13": [
            "nr13",
            "nr13_caldeira",
            "nr13_inspecao_caldeira",
            "nr13_inspecao_vaso_pressao",
            "nr13_inspecao_tubulacao",
            "nr13_integridade_caldeira",
        ],
        "nr13_calibracao": [
            "nr13_calibracao",
            "calibracao_valvulas_seguranca",
            "calibracao_manometros",
            "nr13_calibracao_valvulas_manometros",
        ],
        "nr13_teste_hidrostatico": [
            "nr13_teste_hidrostatico",
            "nr13_teste_estanqueidade_tubulacao_gas",
        ],
        "nr13_ultrassom": [
            "nr13_ultrassom",
            "nr13_medicao_espessura_ultrassom",
            "nr13_calculo_espessura_minima_vaso_pressao",
            "nr13_calculo_espessura_minima_tubulacao",
        ],
        "nr20_instalacoes": [
            "nr20_instalacoes",
            "nr20",
            "nr20_inspecao_instalacoes_inflamaveis",
            "nr20_prontuario_instalacoes_inflamaveis",
        ],
        "nr33_espaco_confinado": [
            "nr33_espaco_confinado",
            "nr33",
            "nr33_avaliacao_espaco_confinado",
            "nr33_permissao_entrada_trabalho",
        ],
        "spda": ["spda", "nr10_spda", "nr10_inspecao_spda"],
        "padrao": ["padrao"],
    }

    candidatos = [tipo, *variantes_por_tipo.get(tipo, [])]
    vistos: set[str] = set()
    codigos: list[str] = []
    for item in candidatos:
        codigo = re.sub(r"[^a-z0-9_-]+", "_", str(item or "").strip().lower()).strip("_-")
        if not codigo or codigo in vistos:
            continue
        vistos.add(codigo)
        codigos.append(codigo)
    return codigos


def nome_template_humano(tipo_template: str) -> str:
    tipo = normalizar_tipo_template(tipo_template)
    return TIPOS_TEMPLATE_VALIDOS.get(tipo, TIPOS_TEMPLATE_VALIDOS["padrao"])


def resolver_familia_padrao_template(tipo_template: str | None) -> dict[str, str | None]:
    tipo = normalizar_tipo_template(str(tipo_template or ""))
    family = FAMILIAS_PADRAO_POR_TEMPLATE.get(tipo) or {}
    return {
        "template_key": tipo,
        "template_label": TIPOS_TEMPLATE_VALIDOS.get(tipo, TIPOS_TEMPLATE_VALIDOS["padrao"]),
        "family_key": str(family.get("family_key") or "").strip() or None,
        "family_label": str(family.get("family_label") or "").strip() or None,
    }


__all__ = [
    "SETORES_PERMITIDOS",
    "TIPOS_TEMPLATE_VALIDOS",
    "ALIASES_TEMPLATE",
    "normalizar_email",
    "normalizar_setor",
    "normalizar_tipo_template",
    "codigos_template_compativeis",
    "nome_template_humano",
    "FAMILIAS_PADRAO_POR_TEMPLATE",
    "resolver_familia_padrao_template",
]
