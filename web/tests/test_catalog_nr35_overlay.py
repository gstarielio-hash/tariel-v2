from __future__ import annotations

import json
from pathlib import Path

from nucleo.template_editor_word import montar_html_documento_editor


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_fixture(name: str) -> dict:
    return json.loads((_repo_root() / "docs" / "family_schemas" / name).read_text(encoding="utf-8"))


def test_nr35_overlay_artifacts_include_family_specific_fields() -> None:
    output_seed = _load_fixture("nr35_inspecao_linha_de_vida.laudo_output_seed.json")
    output_example = _load_fixture("nr35_inspecao_linha_de_vida.laudo_output_exemplo.json")
    template_seed = _load_fixture("nr35_inspecao_linha_de_vida.template_master_seed.json")

    assert output_seed["identificacao"]["numero_laudo_inspecao"] is None
    assert output_seed["identificacao"]["numero_laudo_fabricante"] is None
    assert output_seed["identificacao"]["documento_codigo"] is None
    assert output_seed["identificacao"]["tipo_sistema"] is None
    assert output_seed["identificacao"]["art_numero"] is None
    assert output_seed["metodologia_e_recursos"]["instrumentos_utilizados"] is None
    assert output_seed["registros_fotograficos"]["referencias_texto"] is None
    assert output_seed["checklist_componentes"]["condicao_cabo_aco"]["condicao"] is None
    assert output_seed["conclusao"]["proxima_inspecao_periodica"] is None
    assert output_seed["conclusao"]["status_operacional"] is None

    assert output_example["identificacao"]["numero_laudo_inspecao"] == "AT-IN-OZ-001-01-26"
    assert output_example["identificacao"]["numero_laudo_fabricante"] == "MC-CRMR-0032"
    assert output_example["identificacao"]["documento_codigo"] == "AT-IN-OZ-001-01-26"
    assert output_example["identificacao"]["tipo_sistema"] == "Linha de vida vertical"
    assert "Dinamometro" in output_example["metodologia_e_recursos"]["instrumentos_utilizados"]
    assert "Vista geral" in output_example["registros_fotograficos"]["referencias_texto"]
    assert output_example["checklist_componentes"]["condicao_cabo_aco"]["condicao"] == "NC"
    assert output_example["conclusao"]["status"] == "Reprovado"
    assert output_example["conclusao"]["status_operacional"] == "bloqueio"
    assert output_example["conclusao"]["proxima_inspecao_periodica"] == "2026-07"

    headings = []
    for node in template_seed["documento_editor_json"]["doc"]["content"]:
        if node.get("type") != "heading":
            continue
        headings.append(
            "".join(part.get("text", "") for part in node.get("content", []) if part.get("type") == "text")
        )

    assert "1. Capa / Folha de Rosto" in headings
    assert "6. Checklist Tecnico dos Componentes" in headings
    assert "7. Registros Fotograficos e Evidencias" in headings
    assert "9. Conclusao, Proxima Inspecao e Observacoes" in headings
    assert "11. Assinaturas e Responsabilidade Tecnica" in headings


def test_nr35_overlay_renders_professional_sections_from_example() -> None:
    template_seed = _load_fixture("nr35_inspecao_linha_de_vida.template_master_seed.json")
    output_example = _load_fixture("nr35_inspecao_linha_de_vida.laudo_output_exemplo.json")

    html = montar_html_documento_editor(
        documento_editor_json=template_seed["documento_editor_json"],
        estilo_json=template_seed["estilo_json"],
        assets_json=[],
        dados_formulario=output_example,
    )

    assert "NR35 - Inspecao linha de vida" in html
    assert "MC-CRMR-0032" in html
    assert "Cabo de aco" in html
    assert "Inspecao Periodica" in html
    assert "Dinamometro" in html
    assert "bloqueio" in html
    assert "2026-07" in html
    assert 'class="doc-cover doc-compact"' in html
    assert 'class="doc-matrix"' in html
