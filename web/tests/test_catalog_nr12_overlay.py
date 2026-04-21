from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from nucleo.template_editor_word import montar_html_documento_editor

from app.domains.chat.catalog_pdf_templates import ResolvedPdfTemplateRef, build_catalog_pdf_payload
from app.shared.database import StatusRevisao
from nucleo.template_editor_word import MODO_EDITOR_RICO


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_fixture(name: str) -> dict:
    return json.loads((_repo_root() / "docs" / "family_schemas" / name).read_text(encoding="utf-8"))


def _template_ref(*, family_key: str, template_code: str) -> ResolvedPdfTemplateRef:
    return ResolvedPdfTemplateRef(
        source_kind="catalog_canonical_seed",
        family_key=family_key,
        template_id=None,
        codigo_template=template_code,
        versao=1,
        modo_editor=MODO_EDITOR_RICO,
        arquivo_pdf_base="",
        documento_editor_json={},
        estilo_json={},
        assets_json=[],
    )


def test_nr12_overlay_artifacts_keep_real_machine_contract() -> None:
    output_seed = _load_fixture("nr12_inspecao_maquina_equipamento.laudo_output_seed.json")
    output_example = _load_fixture("nr12_inspecao_maquina_equipamento.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr12_inspecao_maquina_equipamento.template_master_seed.json")

    assert output_seed["identificacao"]["relatorio_codigo"] is None
    assert output_seed["objetivo_e_base_normativa"]["objetivo"] is None
    assert output_seed["checklist_grupos"]["sistemas_seguranca_transportadores"]["risco_nivel"] is None
    assert output_seed["analise_risco"]["grafico_risco_categoria"] is None
    assert output_seed["conclusao"]["parecer_final"] is None

    assert output_example["identificacao"]["numero_laudo"] == "ITM0722WF_CRM"
    assert output_example["identificacao"]["tag"] == "FT RC 02"
    assert output_example["checklist_grupos"]["sistemas_seguranca_transportadores"]["risco_nivel"] == "Alto"
    assert output_example["documentacao_e_registros"]["manual_maquina"] == "DOC_203 - manual_operacional_ft_rc_02.pdf"
    assert output_example["analise_risco"]["grafico_risco_categoria"] == "Categoria 2 | S2 F1 P1"
    assert output_example["conclusao"]["parecer_final"] == "Necessita adequacao NR12 antes do fechamento definitivo."

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append("".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text"))

    assert "1. Quadro de Controle do Documento" in headings
    assert "3. Objetivo, Normas e Premissas" in headings
    assert "4. Identificacao do Objeto Inspecionado" in headings
    assert "5. Execucao Tecnica" in headings
    assert "5.1 Checklist NR12 por Grupo" in headings
    assert "10. Conclusao Tecnica" in headings
    assert "12. Assinatura e Responsabilidade" in headings


def test_nr12_overlay_renders_real_machine_sections_from_example() -> None:
    template_seed = _load_fixture("nr12_inspecao_maquina_equipamento.template_master_seed.json")
    output_example = _load_fixture("nr12_inspecao_maquina_equipamento.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR12 - Inspecao maquina equipamento" in html
    assert "Conj. Motor da Fita Transportadora FT RC 02" in html
    assert "ITM0722WF_CRM" in html
    assert "Categoria 2 | S2 F1 P1" in html
    assert "Necessita adequacao NR12" in html
    assert 'class="doc-matrix"' in html


def test_nr12_overlay_artifacts_keep_risk_analysis_contract() -> None:
    output_seed = _load_fixture("nr12_apreciacao_risco_maquina.laudo_output_seed.json")
    output_example = _load_fixture("nr12_apreciacao_risco_maquina.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr12_apreciacao_risco_maquina.template_master_seed.json")

    assert output_seed["analise_de_risco"] == []

    first_risk = output_example["analise_de_risco"][0]
    assert output_example["identificacao"]["objeto_principal"] == "Prensa hidraulica PH-07"
    assert output_example["execucao_servico"]["evidencia_execucao"]["referencias_texto"] == (
        "DOC_061 - matriz_risco_ph07.pdf; DOC_062 - checklist_nr12_ph07.pdf"
    )
    assert first_risk["perigo"] == "Aprisionamento na zona de alimentacao durante setup e limpeza."
    assert first_risk["categoria"] == "Alto"
    assert first_risk["acao_recomendada"].startswith("Intertravar o acesso frontal")
    assert "Checklist NR12:" in output_example["documentacao_e_registros"]["documentos_disponiveis"]

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append("".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text"))

    assert "3. Escopo e Premissas da Apreciacao" in headings
    assert "4. Identificacao da Maquina e Referencias de Campo" in headings
    assert "5. Enquadramento e Parametros da Apreciacao" in headings
    assert "5.1 Matriz de Risco Principal" in headings
    assert "6. Evidencias e Base Documental" in headings
    assert "8. Lacunas, Criticidade e Interfaces" in headings


def test_nr12_overlay_renders_risk_matrix_from_example() -> None:
    template_seed = _load_fixture("nr12_apreciacao_risco_maquina.template_master_seed.json")
    laudo = SimpleNamespace(
        id=618,
        empresa_id=12,
        catalog_family_key="nr12_apreciacao_risco_maquina",
        catalog_family_label="NR12 · Apreciacao de risco",
        catalog_variant_label="Prime engineering",
        status_revisao=StatusRevisao.APROVADO.value,
        setor_industrial="estamparia",
        parecer_ia="Foi identificado risco alto de aprisionamento na zona de alimentacao durante setup da prensa.",
        primeira_mensagem="Apreciacao de risco na prensa hidraulica PH-07 da linha de estampagem",
        motivo_rejeicao=None,
        dados_formulario={
            "local_inspecao": "Linha de estampagem - prensa PH-07",
            "objeto_principal": "Prensa hidraulica PH-07",
            "codigo_interno": "PH-07",
            "referencia_principal": "IMG_451 - vista geral da PH-07",
            "modo_execucao": "analise e modelagem",
            "metodo_aplicado": "Apreciacao de risco com matriz HRN, checklist NR12 e memoria tecnica.",
            "perigo_identificado": "Aprisionamento na zona de alimentacao durante setup e limpeza.",
            "zona_risco": "Zona frontal de alimentacao com acesso perigoso ao ferramental.",
            "categoria_risco": "alto",
            "severidade": "grave",
            "probabilidade": "provavel",
            "medidas_existentes": "Protecoes laterais fixas e parada de emergencia frontal.",
            "medidas_recomendadas": "Intertravar acesso frontal e revisar procedimento de setup seguro.",
            "evidencia_principal": "DOC_061 - matriz_risco_ph07.pdf",
            "evidencia_complementar": "IMG_452 - zona de alimentacao frontal",
            "apreciacao_risco": "DOC_061 - matriz_risco_ph07.pdf",
            "checklist_nr12": "DOC_062 - checklist_nr12_ph07.pdf",
            "manual_maquina": "DOC_063 - manual_prensa_ph07.pdf",
            "descricao_pontos_atencao": "Risco alto de aprisionamento na zona de alimentacao durante setup.",
            "observacoes": "Implementar intertravamento frontal, revisar o procedimento e revalidar a matriz apos ajuste.",
        },
    )
    output_example = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=_template_ref(
            family_key="nr12_apreciacao_risco_maquina",
            template_code="nr12_apreciacao_risco_maquina",
        ),
        diagnostico="Resumo executivo do caso piloto NR12 para apreciacao de risco de prensa hidraulica.",
        inspetor="Gabriel Santos",
        empresa="Empresa Teste NR12",
        data="09/04/2026",
    )

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR12 - Apreciacao risco maquina" in html
    assert "Prensa hidraulica PH-07" in html
    assert "Aprisionamento na zona de alimentacao durante setup e limpeza." in html
    assert "Zona frontal de alimentacao com acesso perigoso ao ferramental" in html
    assert "Intertravar acesso frontal e revisar procedimento de setup seguro." in html
    assert 'class="doc-matrix"' in html
