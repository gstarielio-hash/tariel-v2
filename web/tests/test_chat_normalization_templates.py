from __future__ import annotations

from app.domains.chat.normalization import (
    codigos_template_compativeis,
    nome_template_humano,
    normalizar_setor,
    normalizar_tipo_template,
    resolver_familia_padrao_template,
)


def test_normalizar_tipo_template_suporta_templates_guiados_expandidos() -> None:
    assert normalizar_tipo_template("nr10_loto") == "loto"
    assert normalizar_tipo_template("nr10_inspecao_spda") == "spda"
    assert normalizar_tipo_template("nr11_inspecao_movimentacao_armazenagem") == "nr11_movimentacao"
    assert normalizar_tipo_template("nr13_calculo_espessura_minima_vaso_pressao") == "nr13_ultrassom"
    assert normalizar_tipo_template("nr13_calibracao_valvulas_manometros") == "nr13_calibracao"
    assert normalizar_tipo_template("nr20_prontuario_instalacoes_inflamaveis") == "nr20_instalacoes"
    assert normalizar_tipo_template("nr35_inspecao_ponto_ancoragem") == "nr35_ponto_ancoragem"
    assert normalizar_tipo_template("nr35_montagem_linha_de_vida") == "nr35_montagem"
    assert normalizar_tipo_template("nr35_projeto_protecao_queda") == "nr35_projeto"


def test_codigos_template_compativeis_preserva_variantes_canonicas_do_template() -> None:
    codigos_nr33 = codigos_template_compativeis("nr33")
    codigos_nr35 = codigos_template_compativeis("nr35_projeto")

    assert "nr33_avaliacao_espaco_confinado" in codigos_nr33
    assert "nr33_permissao_entrada_trabalho" in codigos_nr33
    assert "nr35_projeto_linha_vida" in codigos_nr35
    assert "projeto_nr35" in codigos_nr35


def test_nome_humano_e_setor_reconhecem_novos_templates() -> None:
    assert nome_template_humano("nr13_teste_hidrostatico") == "NR-13 Teste Hidrostatico e Estanqueidade"
    assert nome_template_humano("nr35_montagem") == "NR-35 Montagem e Fabricacao"
    assert normalizar_setor("nr11") == "nr11"
    assert normalizar_setor("nr33") == "nr33"


def test_resolver_familia_padrao_template_aponta_para_familias_documentais_existentes() -> None:
    assert resolver_familia_padrao_template("loto") == {
        "template_key": "loto",
        "template_label": "NR-10 LOTO",
        "family_key": "nr10_implantacao_loto",
        "family_label": "NR10 Implantacao e Gerenciamento de LOTO",
    }
    assert resolver_familia_padrao_template("spda") == {
        "template_key": "spda",
        "template_label": "SPDA Proteção Descargas",
        "family_key": "nr10_inspecao_spda",
        "family_label": "NR10 Inspecao de SPDA",
    }
    assert resolver_familia_padrao_template("rti") == {
        "template_key": "rti",
        "template_label": "NR-10 RTI Elétrica",
        "family_key": "nr10_inspecao_instalacoes_eletricas",
        "family_label": "NR10 Inspecao de Instalacoes Eletricas",
    }
    assert resolver_familia_padrao_template("nr33_espaco_confinado") == {
        "template_key": "nr33_espaco_confinado",
        "template_label": "NR-33 Espaco Confinado",
        "family_key": "nr33_avaliacao_espaco_confinado",
        "family_label": "NR33 Avaliacao de Espaco Confinado",
    }
    assert resolver_familia_padrao_template("nr35_projeto") == {
        "template_key": "nr35_projeto",
        "template_label": "NR-35 Projeto de Protecao Contra Queda",
        "family_key": "nr35_projeto_protecao_queda",
        "family_label": "NR35 Projeto de Protecao Contra Queda",
    }
    assert resolver_familia_padrao_template("nr13_calibracao") == {
        "template_key": "nr13_calibracao",
        "template_label": "NR-13 Calibracao de Valvulas e Manometros",
        "family_key": "nr13_calibracao_valvulas_manometros",
        "family_label": "NR13 Calibracao de Valvulas e Manometros",
    }
