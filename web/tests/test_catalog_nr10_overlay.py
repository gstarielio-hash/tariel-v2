from __future__ import annotations

import json
from pathlib import Path

from nucleo.template_editor_word import montar_html_documento_editor


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_fixture(name: str) -> dict:
    return json.loads((_repo_root() / "docs" / "family_schemas" / name).read_text(encoding="utf-8"))


def test_nr10_loto_overlay_artifacts_keep_official_basis_and_contract() -> None:
    schema = _load_fixture("nr10_implantacao_loto.json")
    output_seed = _load_fixture("nr10_implantacao_loto.laudo_output_seed.json")
    output_example = _load_fixture("nr10_implantacao_loto.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr10_implantacao_loto.template_master_seed.json")

    assert schema["normative_basis"]["sources"][0]["anchors"] == ["10.2.8.2", "10.3.1", "10.5.1", "10.5.2"]
    assert output_seed["checklist_componentes"]["fontes_de_energia"]["condicao"] is None
    assert output_seed["checklist_componentes"]["dispositivos_e_sinalizacao"]["observacao"] is None
    assert output_seed["documentacao_e_registros"]["documentos_disponiveis"] is None

    assert output_example["identificacao"]["objeto_principal"] == "Prensa hidraulica P-07"
    assert output_example["checklist_componentes"]["dispositivos_e_sinalizacao"]["condicao"] == "ajuste"
    assert (
        output_example["nao_conformidades_ou_lacunas"]["descricao"]
        == "Sinalizacao complementar da fonte hidraulica ainda nao estava posicionada no painel lateral."
    )
    assert output_example["conclusao"]["status"] == "ajuste"

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append(
            "".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text")
        )

    assert "NR10 - Implantacao e gerenciamento de LOTO" in headings
    assert "4. Identificacao do Ativo e Referencias de Campo" in headings
    assert "6. Checklist de Bloqueio e Condicao Segura" in headings
    assert "8. Documentacao do Procedimento e Registros" in headings
    assert "9. Desvios, Pendencias e Recomendacoes" in headings


def test_nr10_loto_overlay_renders_professional_sections_from_example() -> None:
    template_seed = _load_fixture("nr10_implantacao_loto.template_master_seed.json")
    output_example = _load_fixture("nr10_implantacao_loto.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR10 - Implantacao e gerenciamento de LOTO" in html
    assert "Prensa hidraulica P-07" in html
    assert "Checklist de Bloqueio e Condicao Segura" in html
    assert "DOC_410 - procedimento_loto_p07.pdf" in html
    assert "Sinalizacao complementar da fonte hidraulica ainda nao estava posicionada no painel lateral." in html


def test_nr10_spda_overlay_artifacts_keep_official_basis_and_contract() -> None:
    schema = _load_fixture("nr10_inspecao_spda.json")
    output_seed = _load_fixture("nr10_inspecao_spda.laudo_output_seed.json")
    output_example = _load_fixture("nr10_inspecao_spda.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr10_inspecao_spda.template_master_seed.json")

    assert schema["normative_basis"]["sources"][0]["anchors"] == ["10.2.3", "10.2.4.b", "10.2.4.g", "10.4.4"]
    assert output_seed["checklist_componentes"]["captacao"]["condicao"] is None
    assert output_seed["checklist_componentes"]["medicoes_ou_testes"]["observacao"] is None
    assert output_seed["documentacao_e_registros"]["documentos_disponiveis"] is None

    assert output_example["identificacao"]["objeto_principal"] == "SPDA do galpao principal"
    assert output_example["checklist_componentes"]["descidas"]["condicao"] == "ajuste"
    expected_documents = (
        "Medicao/relatorio: DOC_510 - medicao_aterramento_2025.pdf; "
        "Projeto/croqui: DOC_511 - croqui_spda_galpao01.pdf; "
        "Historico anterior: DOC_512 - relatorio_spda_2024.pdf"
    )
    assert output_example["documentacao_e_registros"]["documentos_disponiveis"] == expected_documents
    assert output_example["conclusao"]["status"] == "ajuste"

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append(
            "".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text")
        )

    assert "NR10 - Inspecao de SPDA" in headings
    assert "4. Identificacao do Sistema e Referencias" in headings
    assert "6. Checklist do SPDA e Aterramento" in headings
    assert "7. Evidencias e Registros de Medicao" in headings
    assert "9. Nao Conformidades e Acoes Recomendadas" in headings


def test_nr10_spda_overlay_renders_professional_sections_from_example() -> None:
    template_seed = _load_fixture("nr10_inspecao_spda.template_master_seed.json")
    output_example = _load_fixture("nr10_inspecao_spda.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR10 - Inspecao de SPDA" in html
    assert "SPDA do galpao principal" in html
    assert "Checklist do SPDA e Aterramento" in html
    assert "DOC_510 - medicao_aterramento_2025.pdf" in html
    assert "Conexao lateral da descida leste com necessidade de reaperto e revisao local." in html
