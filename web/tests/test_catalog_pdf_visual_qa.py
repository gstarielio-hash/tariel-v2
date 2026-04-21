# ruff: noqa: E501
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domains.chat.catalog_pdf_templates import (
    RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    ResolvedPdfTemplateRef,
    build_catalog_pdf_payload,
    materialize_runtime_document_editor_json,
)
from app.shared.database import StatusRevisao
from nucleo.template_editor_word import MODO_EDITOR_RICO
from nucleo.template_editor_word import montar_html_documento_editor


FAMILY_VISUAL_MATRIX: tuple[tuple[str, str, str], ...] = (
    ("nr01_gro_pgr", "nr01_gro_pgr", "Inventario, Classificacao e Plano de Acao"),
    ("nr10_implantacao_loto", "nr10_implantacao_loto", "Checklist Tecnico"),
    ("nr10_inspecao_instalacoes_eletricas", "nr10_inspecao_instalacoes_eletricas", "Checklist Tecnico"),
    ("nr10_inspecao_spda", "nr10_inspecao_spda", "Checklist Tecnico"),
    ("nr10_prontuario_instalacoes_eletricas", "nr10_prontuario_instalacoes_eletricas", "Indice e Documentacao Base"),
    ("nr12_apreciacao_risco_maquina", "nr12_apreciacao_risco_maquina", "Matriz de Risco"),
    ("nr12_inspecao_maquina_equipamento", "nr12_inspecao_maquina_equipamento", "Checklist Tecnico"),
    ("nr13_inspecao_caldeira", "nr13_caldeira", "Checklist Tecnico"),
    ("nr13_inspecao_vaso_pressao", "nr13_vaso_pressao", "Checklist Tecnico"),
    ("nr13_inspecao_tubulacao", "nr13_inspecao_tubulacao", "Checklist Tecnico"),
    ("nr33_avaliacao_espaco_confinado", "nr33_avaliacao_espaco_confinado", "Matriz de Risco"),
    ("nr35_inspecao_linha_de_vida", "nr35_inspecao_linha_de_vida", "Checklist Tecnico"),
    ("nr35_inspecao_ponto_ancoragem", "nr35_inspecao_ponto_ancoragem", "Checklist Tecnico"),
)

NR10_COMPARATIVE_VISUAL_MATRIX: tuple[tuple[str, list[str], list[str]], ...] = (
    (
        "nr10_implantacao_loto",
        [
            "NR10 - Implantacao e gerenciamento de LOTO",
            "1. Quadro de Controle do Documento",
            "2. Resumo Executivo",
            "3. Escopo Tecnico e Premissas",
            "4. Identificacao do Ativo e Referencias de Campo",
            "5. Execucao do Bloqueio e Desenergizacao",
            "6. Checklist de Bloqueio e Condicao Segura",
            "7. Evidencias do Bloqueio e Registros Criticos",
            "8. Documentacao do Procedimento e Registros",
            "9. Desvios, Pendencias e Recomendacoes",
            "10. Conclusao Tecnica",
            "11. Governanca da Mesa",
            "12. Assinatura e Responsabilidade",
        ],
        [
            "Prensa hidraulica P-07",
            "Checklist de Bloqueio e Condicao Segura",
            "DOC_410 - procedimento_loto_p07.pdf",
            "Sinalizacao complementar da fonte hidraulica ainda nao estava posicionada no painel lateral.",
        ],
    ),
    (
        "nr10_inspecao_spda",
        [
            "NR10 - Inspecao de SPDA",
            "1. Quadro de Controle do Documento",
            "2. Resumo Executivo",
            "3. Escopo Tecnico e Premissas",
            "4. Identificacao do Sistema e Referencias",
            "5. Execucao da Vistoria do SPDA",
            "6. Checklist do SPDA e Aterramento",
            "7. Evidencias e Registros de Medicao",
            "8. Documentacao e Registros",
            "9. Nao Conformidades e Acoes Recomendadas",
            "10. Conclusao Tecnica",
            "11. Governanca da Mesa",
            "12. Assinatura e Responsabilidade",
        ],
        [
            "SPDA do galpao principal",
            "Checklist do SPDA e Aterramento",
            "DOC_510 - medicao_aterramento_2025.pdf",
            "Conexao lateral da descida leste com necessidade de reaperto e revisao local.",
        ],
    ),
)

NR12_COMPARATIVE_VISUAL_MATRIX: tuple[tuple[str, list[str], list[str]], ...] = (
    (
        "nr12_apreciacao_risco_maquina",
        [
            "NR12 - Apreciacao risco maquina",
            "1. Quadro de Controle do Documento",
            "2. Resumo Executivo",
            "3. Escopo e Premissas da Apreciacao",
            "4. Identificacao da Maquina e Referencias de Campo",
            "5. Enquadramento e Parametros da Apreciacao",
            "5.1 Matriz de Risco Principal",
            "6. Evidencias e Base Documental",
            "7. Documentacao e Registros",
            "8. Lacunas, Criticidade e Interfaces",
            "9. Recomendacoes",
            "10. Conclusao Tecnica",
            "11. Governanca da Mesa",
            "12. Assinatura e Responsabilidade",
        ],
        [
            "Prensa hidraulica PH-07",
            "Aprisionamento na zona de alimentacao durante setup e limpeza.",
            "Intertravar o acesso frontal, revisar o procedimento de setup seguro e revalidar a matriz de risco apos a adequacao.",
        ],
    ),
    (
        "nr12_inspecao_maquina_equipamento",
        [
            "NR12 - Inspecao maquina equipamento",
            "1. Quadro de Controle do Documento",
            "2. Resumo Executivo",
            "3. Objetivo, Normas e Premissas",
            "4. Identificacao do Objeto Inspecionado",
            "5. Execucao Tecnica",
            "5.1 Checklist NR12 por Grupo",
            "6. Matriz de Evidencias",
            "7. Documentacao e Registros",
            "8. Achados Tecnicos e Providencias",
            "9. Recomendacoes",
            "10. Conclusao Tecnica",
            "11. Governanca da Mesa",
            "12. Assinatura e Responsabilidade",
        ],
        [
            "Conj. Motor da Fita Transportadora FT RC 02",
            "Necessario instalar protecao mecanica no decorrer da fita, no rolo de tracao, na corrente de tracao e na correia de acoplamento.",
            "Necessita adequacao NR12 antes do fechamento definitivo.",
        ],
    ),
)

NR13_COMPARATIVE_VISUAL_MATRIX: tuple[tuple[str, list[str], list[str]], ...] = (
    (
        "nr13_inspecao_caldeira",
        [
            "NR13 - Inspecao de Caldeira",
            "1. Quadro de Controle do Documento",
            "2. Resumo Executivo",
            "3. Escopo Tecnico e Premissas",
            "4. Identificacao do Equipamento",
            "5. Caracterizacao Operacional e Inspecao",
            "6. Dispositivos, Itens Criticos e Controles",
            "7. Documentacao e Registros",
            "8. Nao Conformidades e Recomendacoes",
            "9. Conclusao Tecnica",
            "10. Governanca da Mesa",
            "11. Assinatura e Responsabilidade",
        ],
        [
            "Caldeira horizontal CAL-01",
            "Painel frontal e comandos principais registrados durante a inspecao.",
            "DOC_021 - prontuario_caldeira_cal01.pdf",
        ],
    ),
    (
        "nr13_inspecao_tubulacao",
        [
            "NR13 - Inspecao de Tubulacao",
            "1. Quadro de Controle do Documento",
            "2. Resumo Executivo",
            "3. Escopo Tecnico e Premissas",
            "4. Identificacao do Trecho e Referencias",
            "5. Escopo e Execucao Tecnica",
            "6. Checklist Tecnico do Trecho",
            "7. Evidencias e Registros Criticos",
            "8. Documentacao e Registros",
            "9. Nao Conformidades e Recomendacoes",
            "10. Conclusao Tecnica",
            "11. Governanca da Mesa",
            "12. Assinatura e Responsabilidade",
        ],
        [
            "Tubulacao de vapor linha TV-203",
            "Suportes e ancoragens",
            "Identificacao visual da linha e acabamento externo demandam recomposicao localizada.",
        ],
    ),
    (
        "nr13_integridade_caldeira",
        [
            "NR13 - Integridade de Caldeira",
            "1. Quadro de Controle do Documento",
            "2. Resumo Executivo",
            "3. Escopo Tecnico e Premissas",
            "4. Identificacao da Caldeira e Referencias",
            "5. Escopo e Analise de Integridade",
            "6. Evidencias, Historico e Registros Criticos",
            "7. Documentacao e Registros",
            "8. Lacunas Tecnicas e Recomendacoes",
            "9. Conclusao Tecnica",
            "10. Governanca da Mesa",
            "11. Assinatura e Responsabilidade",
        ],
        [
            "Caldeira horizontal CAL-02",
            "Necessidade de complementar memoria historica e consolidar registros de espessura e intervencoes anteriores.",
            "Prontuario da caldeira, relatorio anterior e registros de acompanhamento.",
        ],
    ),
    (
        "nr13_teste_hidrostatico",
        [
            "NR13 - Teste Hidrostatico",
            "1. Quadro de Controle do Documento",
            "2. Resumo Executivo",
            "3. Escopo Tecnico e Premissas",
            "4. Identificacao do Ativo e Referencias de Teste",
            "5. Escopo e Procedimento do Teste",
            "6. Evidencias, Parametros e Registros Criticos",
            "7. Documentacao e Registros",
            "8. Desvios e Recomendacoes",
            "9. Conclusao Tecnica",
            "10. Governanca da Mesa",
            "11. Assinatura e Responsabilidade",
        ],
        [
            "Vaso de pressao VPH-11 submetido a teste hidrostatico",
            "Preparacao do ativo, aplicacao do procedimento de teste",
            "Procedimento de teste e ficha de registro da execucao.",
        ],
    ),
    (
        "nr13_teste_estanqueidade_tubulacao_gas",
        [
            "NR13 - Teste de Estanqueidade em Tubulacao de Gas",
            "1. Quadro de Controle do Documento",
            "2. Resumo Executivo",
            "3. Escopo Tecnico e Premissas",
            "4. Identificacao do Trecho e Referencias de Teste",
            "5. Escopo e Procedimento do Teste",
            "6. Evidencias, Parametros e Registros Criticos",
            "7. Documentacao e Registros",
            "8. Desvios e Recomendacoes",
            "9. Conclusao Tecnica",
            "10. Governanca da Mesa",
            "11. Assinatura e Responsabilidade",
        ],
        [
            "Tubulacao de gas combustivel linha TG-12",
            "Preparacao do trecho, aplicacao do teste de estanqueidade",
            "Ficha do teste e croqui do trecho inspecionado.",
        ],
    ),
)


def _heading_texts(documento_editor_json: dict[str, object]) -> list[str]:
    headings: list[str] = []
    doc = documento_editor_json.get("doc") if isinstance(documento_editor_json, dict) else None
    stack = list(doc.get("content") if isinstance(doc, dict) and isinstance(doc.get("content"), list) else [])
    while stack:
        node = stack.pop(0)
        if not isinstance(node, dict):
            continue
        if str(node.get("type") or "") == "heading":
            heading = "".join(
                str(part.get("text") or "")
                for part in node.get("content", [])
                if isinstance(part, dict) and str(part.get("type") or "") == "text"
            ).strip()
            if heading:
                headings.append(heading)
        content = node.get("content")
        if isinstance(content, list):
            stack[:0] = content
    return headings


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_family_fixture(name: str) -> dict[str, object]:
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


@pytest.mark.parametrize(("family_key", "template_code", "expected_heading"), FAMILY_VISUAL_MATRIX)
def test_blank_preview_visual_qa_for_main_families(
    family_key: str,
    template_code: str,
    expected_heading: str,
) -> None:
    laudo = SimpleNamespace(
        id=501,
        empresa_id=12,
        catalog_family_key=family_key,
        catalog_family_label=family_key.replace("_", " ").title(),
        catalog_variant_label="Premium",
        status_revisao=StatusRevisao.RASCUNHO.value,
        setor_industrial="industrial",
        parecer_ia=None,
        primeira_mensagem=None,
        motivo_rejeicao=None,
        dados_formulario={},
    )
    template_ref = _template_ref(family_key=family_key, template_code=template_code)

    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=template_ref,
        render_mode=RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    )
    document = materialize_runtime_document_editor_json(
        template_ref=template_ref,
        payload=payload,
        render_mode=RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    )
    headings = _heading_texts(document)
    serialized = json.dumps(document, ensure_ascii=False)

    assert "Resumo Executivo" in headings
    assert "Conclusao Tecnica" in headings
    assert "Assinaturas e Responsabilidade Tecnica" in headings
    assert expected_heading in headings
    assert "Empresa Demo" not in serialized
    assert "Preview de Template (fallback)" not in serialized
    assert "Family key" not in serialized
    assert "Scope mismatch" not in serialized
    assert "fallback" not in serialized.lower()


def test_visual_qa_family_blueprints_are_declared_for_main_families() -> None:
    family_dir = Path(__file__).resolve().parents[2] / "docs" / "family_schemas"
    expected_sections = {
        "Inventario, Classificacao e Plano de Acao": "inventario_e_classificacao",
        "Matriz de Risco": "analise_de_risco",
        "Checklist Tecnico": "checklist_tecnico",
        "Indice e Documentacao Base": "indice_e_documentacao_base",
    }
    for family_key, _template_code, expected_heading in FAMILY_VISUAL_MATRIX:
        schema = json.loads((family_dir / f"{family_key}.json").read_text(encoding="utf-8"))
        blueprint = schema.get("document_blueprint")
        assert isinstance(blueprint, dict)
        assert blueprint.get("section_order")
        assert blueprint.get("signature_roles")
        assert expected_sections[expected_heading] in set(blueprint.get("section_order") or [])


def test_nr10_family_standard_and_official_basis_are_registered() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    standard_doc = (repo_root / "docs" / "padrao_base_oficial_familias_nr.md").read_text(encoding="utf-8")

    assert "Toda implementacao ou reforco de familia NR deve" in standard_doc
    for family_key in (
        "nr10_implantacao_loto",
        "nr10_inspecao_instalacoes_eletricas",
        "nr10_inspecao_spda",
        "nr10_prontuario_instalacoes_eletricas",
    ):
        schema = _load_family_fixture(f"{family_key}.json")
        basis = schema.get("normative_basis")
        assert isinstance(basis, dict)
        assert basis.get("sources")
        assert basis.get("editorial_inference_notice")


@pytest.mark.parametrize(("family_key", "expected_headings", "content_markers"), NR10_COMPARATIVE_VISUAL_MATRIX)
def test_nr10_comparative_visual_qa_for_promoted_families(
    family_key: str,
    expected_headings: list[str],
    content_markers: list[str],
) -> None:
    template_seed = _load_family_fixture(f"{family_key}.template_master_seed.json")
    output_example = _load_family_fixture(f"{family_key}.laudo_output_exemplo.json")

    document = template_seed["documento_editor_json"]
    headings = _heading_texts(document)
    html = montar_html_documento_editor(
        documento_editor_json=document,
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert headings == expected_headings
    for marker in content_markers:
        assert marker in html
    assert "Preview de Template (fallback)" not in html
    assert "fallback" not in html.lower()


def test_nr12_risk_visual_qa_materializes_primary_matrix_from_payload() -> None:
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
    template_ref = _template_ref(
        family_key="nr12_apreciacao_risco_maquina",
        template_code="nr12_apreciacao_risco_maquina",
    )

    payload = build_catalog_pdf_payload(laudo=laudo, template_ref=template_ref)
    document = materialize_runtime_document_editor_json(template_ref=template_ref, payload=payload)
    headings = _heading_texts(document)
    serialized = json.dumps(document, ensure_ascii=False)

    assert "Matriz de Risco" in headings
    assert "Aprisionamento na zona de alimentacao durante setup e limpeza." in serialized
    assert "Zona frontal de alimentacao com acesso perigoso ao ferramental." in serialized
    assert "Intertravar acesso frontal e revisar procedimento de setup seguro." in serialized
    assert "Protecoes laterais fixas e parada de emergencia frontal." in serialized


@pytest.mark.parametrize(("family_key", "expected_headings", "content_markers"), NR12_COMPARATIVE_VISUAL_MATRIX)
def test_nr12_comparative_visual_qa_for_promoted_families(
    family_key: str,
    expected_headings: list[str],
    content_markers: list[str],
) -> None:
    template_seed = _load_family_fixture(f"{family_key}.template_master_seed.json")
    output_example = _load_family_fixture(f"{family_key}.laudo_output_exemplo.json")

    document = template_seed["documento_editor_json"]
    headings = _heading_texts(document)
    html = montar_html_documento_editor(
        documento_editor_json=document,
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert headings == expected_headings
    for marker in content_markers:
        assert marker in html
    assert "Preview de Template (fallback)" not in html
    assert "fallback" not in html.lower()


@pytest.mark.parametrize(("family_key", "expected_headings", "content_markers"), NR13_COMPARATIVE_VISUAL_MATRIX)
def test_nr13_comparative_visual_qa_for_promoted_families(
    family_key: str,
    expected_headings: list[str],
    content_markers: list[str],
) -> None:
    template_seed = _load_family_fixture(f"{family_key}.template_master_seed.json")
    output_example = _load_family_fixture(f"{family_key}.laudo_output_exemplo.json")

    document = template_seed["documento_editor_json"]
    headings = _heading_texts(document)
    html = montar_html_documento_editor(
        documento_editor_json=document,
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert headings == expected_headings
    for marker in content_markers:
        assert marker in html
    assert "Preview de Template (fallback)" not in html
    assert "fallback" not in html.lower()
