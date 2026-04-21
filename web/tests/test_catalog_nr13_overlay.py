from __future__ import annotations

import json
from pathlib import Path

from nucleo.template_editor_word import montar_html_documento_editor


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_fixture(name: str) -> dict:
    return json.loads((_repo_root() / "docs" / "family_schemas" / name).read_text(encoding="utf-8"))


def test_nr13_overlay_artifacts_keep_family_specific_contract() -> None:
    output_seed = _load_fixture("nr13_inspecao_vaso_pressao.laudo_output_seed.json")
    output_example = _load_fixture("nr13_inspecao_vaso_pressao.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr13_inspecao_vaso_pressao.template_master_seed.json")

    assert output_seed["identificacao"]["placa_identificacao"]["descricao"] is None
    assert output_seed["dispositivos_e_acessorios"]["valvula_seguranca_detalhe"]["descricao"] is None
    assert output_seed["documentacao_e_registros"]["prontuario"]["referencias"] == []
    assert output_seed["conclusao"]["justificativa"] is None

    assert output_example["identificacao"]["identificacao_do_vaso"] == "Vaso de pressao vertical VP-204"
    assert output_example["identificacao"]["placa_identificacao"]["referencias_texto"] == "IMG_001; DOC_014"
    assert output_example["dispositivos_e_acessorios"]["manometro"]["descricao"] == "Manometro com visor legivel durante a inspecao."
    assert output_example["nao_conformidades"]["ha_nao_conformidades"] is True
    assert output_example["conclusao"]["status"] == "ajuste"

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append(
            "".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text")
        )

    assert "1. Capa / Folha de Rosto" in headings
    assert "5. Identificacao Tecnica do Vaso" in headings
    assert "6. Inspecao Visual e Integridade Aparente" in headings
    assert "8. Documentacao, Registros e Evidencias" in headings
    assert "10. Conclusao, Parecer e Proxima Acao" in headings
    assert "12. Assinaturas e Responsabilidade Tecnica" in headings


def test_nr13_overlay_renders_professional_sections_from_example() -> None:
    template_seed = _load_fixture("nr13_inspecao_vaso_pressao.template_master_seed.json")
    output_example = _load_fixture("nr13_inspecao_vaso_pressao.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR13 - Inspecao de vaso de pressao" in html
    assert "Vaso de pressao vertical VP-204" in html
    assert "DOC_014 - prontuario_vp204.pdf" in html
    assert "corrosao superficial" in html.lower()
    assert 'class="doc-cover doc-compact"' in html
    assert 'class="doc-matrix"' in html


def test_nr13_caldeira_overlay_artifacts_keep_family_specific_contract() -> None:
    output_seed = _load_fixture("nr13_inspecao_caldeira.laudo_output_seed.json")
    output_example = _load_fixture("nr13_inspecao_caldeira.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr13_inspecao_caldeira.template_master_seed.json")

    assert output_seed["identificacao"]["identificacao_da_caldeira"] is None
    assert output_seed["caracterizacao_do_equipamento"]["vista_geral_caldeira"]["descricao"] is None
    assert output_seed["dispositivos_e_controles"]["painel_e_comandos"]["descricao"] is None
    assert output_seed["documentacao_e_registros"]["prontuario"]["referencias"] == []
    assert output_seed["conclusao"]["justificativa"] is None

    assert output_example["identificacao"]["identificacao_da_caldeira"] == "Caldeira horizontal CAL-01"
    assert output_example["identificacao"]["placa_identificacao"]["referencias_texto"] == "IMG_101; DOC_021"
    assert (
        output_example["caracterizacao_do_equipamento"]["vista_geral_caldeira"]["descricao"]
        == "Vista frontal e lateral da caldeira instalada em base fixa com acesso operacional frontal."
    )
    assert (
        output_example["inspecao_visual"]["chamine_ou_exaustao"]["descricao"]
        == "Trecho aparente da exaustao registrado sem desalinhamento visual relevante."
    )
    assert (
        output_example["dispositivos_e_controles"]["leitura_dos_comandos_e_indicadores"]
        == "Painel com identificacao visual suficiente para revisao, com comandos principais acessiveis e indicadores aparentes em condicao operacional."
    )
    assert output_example["nao_conformidades"]["ha_nao_conformidades"] is True
    assert output_example["conclusao"]["status"] == "ajuste"

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append(
            "".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text")
        )

    assert "NR13 - Inspecao de Caldeira" in headings
    assert "4. Identificacao do Equipamento" in headings
    assert "5. Caracterizacao Operacional e Inspecao" in headings
    assert "6. Dispositivos, Itens Criticos e Controles" in headings
    assert "8. Nao Conformidades e Recomendacoes" in headings
    assert "9. Conclusao Tecnica" in headings
    assert "11. Assinatura e Responsabilidade" in headings


def test_nr13_caldeira_overlay_renders_professional_sections_from_example() -> None:
    template_seed = _load_fixture("nr13_inspecao_caldeira.template_master_seed.json")
    output_example = _load_fixture("nr13_inspecao_caldeira.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR13 - Inspecao de Caldeira" in html
    assert "Caldeira horizontal CAL-01" in html
    assert "DOC_021 - prontuario_caldeira_cal01.pdf" in html
    assert "fuligem" in html.lower()
    assert "Painel frontal e comandos principais registrados durante a inspecao." in html
    assert "Documentacao e Registros" in html
    assert "Nao Conformidades e Recomendacoes" in html


def test_nr13_tubulacao_overlay_artifacts_keep_family_specific_contract() -> None:
    output_seed = _load_fixture("nr13_inspecao_tubulacao.laudo_output_seed.json")
    output_example = _load_fixture("nr13_inspecao_tubulacao.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr13_inspecao_tubulacao.template_master_seed.json")

    assert output_seed["identificacao"]["objeto_principal"] is None
    assert output_seed["checklist_componentes"]["suportes_e_ancoragens"]["condicao"] is None
    assert output_seed["checklist_componentes"]["isolamento_e_protecao"]["observacao"] is None
    assert output_seed["documentacao_e_registros"]["documentos_disponiveis"] is None
    assert output_seed["conclusao"]["justificativa"] is None

    assert output_example["identificacao"]["objeto_principal"] == "Tubulacao de vapor linha TV-203"
    assert output_example["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_001; DOC_001"
    assert output_example["checklist_componentes"]["suportes_e_ancoragens"]["condicao"] == "ajuste"
    assert (
        output_example["checklist_componentes"]["isolamento_e_protecao"]["observacao"]
        == "Identificacao visual da linha e acabamento externo demandam recomposicao localizada."
    )
    assert (
        output_example["nao_conformidades_ou_lacunas"]["descricao"]
        == "Oxidacao superficial localizada em suporte secundario e necessidade de reforcar identificacao visual da linha."
    )
    assert output_example["conclusao"]["status"] == "ajuste"

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append(
            "".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text")
        )

    assert "NR13 - Inspecao de Tubulacao" in headings
    assert "4. Identificacao do Trecho e Referencias" in headings
    assert "5. Escopo e Execucao Tecnica" in headings
    assert "6. Checklist Tecnico do Trecho" in headings
    assert "7. Evidencias e Registros Criticos" in headings
    assert "8. Documentacao e Registros" in headings
    assert "9. Nao Conformidades e Recomendacoes" in headings
    assert "10. Conclusao Tecnica" in headings
    assert "12. Assinatura e Responsabilidade" in headings


def test_nr13_tubulacao_overlay_renders_professional_sections_from_example() -> None:
    template_seed = _load_fixture("nr13_inspecao_tubulacao.template_master_seed.json")
    output_example = _load_fixture("nr13_inspecao_tubulacao.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR13 - Inspecao de Tubulacao" in html
    assert "Tubulacao de vapor linha TV-203" in html
    assert "Checklist Tecnico do Trecho" in html
    assert "Suportes e ancoragens" in html
    assert "Oxidacao superficial localizada" in html
    assert "Fluxograma das linhas e relatorio anterior da tubulacao." in html
    assert "Identificacao visual da linha e acabamento externo demandam recomposicao localizada." in html


def test_nr13_integridade_caldeira_overlay_artifacts_keep_family_specific_contract() -> None:
    output_seed = _load_fixture("nr13_integridade_caldeira.laudo_output_seed.json")
    output_example = _load_fixture("nr13_integridade_caldeira.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr13_integridade_caldeira.template_master_seed.json")

    assert output_seed["identificacao"]["objeto_principal"] is None
    assert output_seed["execucao_servico"]["metodo_aplicado"] is None
    assert output_seed["documentacao_e_registros"]["documentos_disponiveis"] is None
    assert output_seed["nao_conformidades_ou_lacunas"]["descricao"] is None
    assert output_seed["conclusao"]["justificativa"] is None

    assert output_example["identificacao"]["objeto_principal"] == "Caldeira horizontal CAL-02"
    assert output_example["identificacao"]["referencia_principal"]["referencias_texto"] == "IMG_001; DOC_001"
    assert (
        output_example["execucao_servico"]["metodo_aplicado"]
        == "Analise de integridade combinando evidencias visuais, registros tecnicos disponiveis e apontamentos complementares da equipe responsavel."
    )
    assert (
        output_example["nao_conformidades_ou_lacunas"]["descricao"]
        == "Necessidade de complementar memoria historica e consolidar registros de espessura e intervencoes anteriores."
    )
    assert output_example["conclusao"]["status"] == "ajuste"

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append(
            "".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text")
        )

    assert "NR13 - Integridade de Caldeira" in headings
    assert "4. Identificacao da Caldeira e Referencias" in headings
    assert "5. Escopo e Analise de Integridade" in headings
    assert "6. Evidencias, Historico e Registros Criticos" in headings
    assert "7. Documentacao e Registros" in headings
    assert "8. Lacunas Tecnicas e Recomendacoes" in headings
    assert "9. Conclusao Tecnica" in headings
    assert "11. Assinatura e Responsabilidade" in headings


def test_nr13_integridade_caldeira_overlay_renders_professional_sections_from_example() -> None:
    template_seed = _load_fixture("nr13_integridade_caldeira.template_master_seed.json")
    output_example = _load_fixture("nr13_integridade_caldeira.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR13 - Integridade de Caldeira" in html
    assert "Caldeira horizontal CAL-02" in html
    assert "Escopo e Analise de Integridade" in html
    assert "Analise de integridade combinando evidencias visuais" in html
    assert "Necessidade de complementar memoria historica" in html
    assert "Prontuario da caldeira, relatorio anterior e registros de acompanhamento." in html
    assert "Lacunas Tecnicas e Recomendacoes" in html


def test_nr13_teste_hidrostatico_overlay_artifacts_keep_family_specific_contract() -> None:
    output_seed = _load_fixture("nr13_teste_hidrostatico.laudo_output_seed.json")
    output_example = _load_fixture("nr13_teste_hidrostatico.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr13_teste_hidrostatico.template_master_seed.json")

    assert output_seed["identificacao"]["objeto_principal"] is None
    assert output_seed["execucao_servico"]["metodo_aplicado"] is None
    assert output_seed["documentacao_e_registros"]["documentos_disponiveis"] is None
    assert output_seed["nao_conformidades_ou_lacunas"]["descricao"] is None
    assert output_seed["conclusao"]["justificativa"] is None

    assert output_example["identificacao"]["objeto_principal"] == "Vaso de pressao VPH-11 submetido a teste hidrostatico"
    assert output_example["identificacao"]["localizacao"] == "Area controlada de manutencao pesada"
    assert (
        output_example["execucao_servico"]["metodo_aplicado"]
        == "Preparacao do ativo, aplicacao do procedimento de teste, registro dos parametros e consolidacao do comportamento observado durante a execucao."
    )
    assert (
        output_example["documentacao_e_registros"]["documentos_disponiveis"]
        == "Procedimento de teste e ficha de registro da execucao."
    )
    assert output_example["conclusao"]["status"] == "conforme"

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append(
            "".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text")
        )

    assert "NR13 - Teste Hidrostatico" in headings
    assert "4. Identificacao do Ativo e Referencias de Teste" in headings
    assert "5. Escopo e Procedimento do Teste" in headings
    assert "6. Evidencias, Parametros e Registros Criticos" in headings
    assert "7. Documentacao e Registros" in headings
    assert "8. Desvios e Recomendacoes" in headings
    assert "9. Conclusao Tecnica" in headings
    assert "11. Assinatura e Responsabilidade" in headings


def test_nr13_teste_hidrostatico_overlay_renders_professional_sections_from_example() -> None:
    template_seed = _load_fixture("nr13_teste_hidrostatico.template_master_seed.json")
    output_example = _load_fixture("nr13_teste_hidrostatico.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR13 - Teste Hidrostatico" in html
    assert "Vaso de pressao VPH-11 submetido a teste hidrostatico" in html
    assert "Escopo e Procedimento do Teste" in html
    assert "Preparacao do ativo, aplicacao do procedimento de teste" in html
    assert "Procedimento de teste e ficha de registro da execucao." in html
    assert "Desvios e Recomendacoes" in html


def test_nr13_teste_estanqueidade_overlay_artifacts_keep_family_specific_contract() -> None:
    output_seed = _load_fixture("nr13_teste_estanqueidade_tubulacao_gas.laudo_output_seed.json")
    output_example = _load_fixture("nr13_teste_estanqueidade_tubulacao_gas.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr13_teste_estanqueidade_tubulacao_gas.template_master_seed.json")

    assert output_seed["identificacao"]["objeto_principal"] is None
    assert output_seed["execucao_servico"]["metodo_aplicado"] is None
    assert output_seed["documentacao_e_registros"]["documentos_disponiveis"] is None
    assert output_seed["nao_conformidades_ou_lacunas"]["descricao"] is None
    assert output_seed["conclusao"]["justificativa"] is None

    assert output_example["identificacao"]["objeto_principal"] == "Tubulacao de gas combustivel linha TG-12"
    assert output_example["identificacao"]["localizacao"] == "Casa de utilidades e alimentacao do queimador principal"
    assert (
        output_example["execucao_servico"]["metodo_aplicado"]
        == "Preparacao do trecho, aplicacao do teste de estanqueidade e registro das leituras e do comportamento observado."
    )
    assert output_example["documentacao_e_registros"]["documentos_disponiveis"] == "Ficha do teste e croqui do trecho inspecionado."
    assert output_example["conclusao"]["status"] == "conforme"

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append(
            "".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text")
        )

    assert "NR13 - Teste de Estanqueidade em Tubulacao de Gas" in headings
    assert "4. Identificacao do Trecho e Referencias de Teste" in headings
    assert "5. Escopo e Procedimento do Teste" in headings
    assert "6. Evidencias, Parametros e Registros Criticos" in headings
    assert "7. Documentacao e Registros" in headings
    assert "8. Desvios e Recomendacoes" in headings
    assert "9. Conclusao Tecnica" in headings
    assert "11. Assinatura e Responsabilidade" in headings


def test_nr13_teste_estanqueidade_overlay_renders_professional_sections_from_example() -> None:
    template_seed = _load_fixture("nr13_teste_estanqueidade_tubulacao_gas.template_master_seed.json")
    output_example = _load_fixture("nr13_teste_estanqueidade_tubulacao_gas.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR13 - Teste de Estanqueidade em Tubulacao de Gas" in html
    assert "Tubulacao de gas combustivel linha TG-12" in html
    assert "Escopo e Procedimento do Teste" in html
    assert "Preparacao do trecho, aplicacao do teste de estanqueidade" in html
    assert "Ficha do teste e croqui do trecho inspecionado." in html
    assert "Desvios e Recomendacoes" in html
