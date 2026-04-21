from __future__ import annotations

import json
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _family_schema_paths() -> list[Path]:
    paths: list[Path] = []
    for path in sorted((_repo_root() / "docs" / "family_schemas").glob("nr*.json")):
        name = path.name
        if name.endswith(".laudo_output_exemplo.json") or name.endswith(".laudo_output_seed.json") or name.endswith(
            ".template_master_seed.json"
        ):
            continue
        paths.append(path)
    return paths


def _load_schema(name: str) -> dict:
    path = _repo_root() / "docs" / "family_schemas" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_project_declares_official_nr_basis_standard() -> None:
    content = (_repo_root() / "docs" / "padrao_base_oficial_familias_nr.md").read_text(encoding="utf-8")
    assert "Toda implementacao ou reforco de familia NR deve" in content
    assert "python3 scripts/sync_nr_official_basis.py" in content
    assert "monitoramento oficial preparado, mas com gatilho manual" in content
    assert "Nao atualizar template oficial automaticamente sem revisao humana do admin responsavel." in content


def test_all_nr_family_schemas_register_official_sources() -> None:
    overview_url = (
        "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/"
        "seguranca-e-saude-no-trabalho/ctpp-nrs/normas-regulamentadoras-nrs"
    )
    for path in _family_schema_paths():
        schema = json.loads(path.read_text(encoding="utf-8"))
        family_key = str(schema.get("family_key") or path.stem).strip().lower()
        match = re.match(r"^(nr\d{2})_", family_key)
        assert match, path.name
        nr_number = match.group(1)[2:]

        basis = schema.get("normative_basis")
        assert isinstance(basis, dict), path.name
        assert basis.get("policy_version") == 1, path.name
        assert basis.get("editorial_inference_notice"), path.name
        assert basis.get("implementation_note"), path.name

        sources = basis.get("sources")
        assert isinstance(sources, list) and sources, path.name
        urls = [str(source.get("url") or "").strip() for source in sources if isinstance(source, dict)]
        assert overview_url in urls, path.name
        official_urls = [url for url in urls if "gov.br" in url]
        assert official_urls, path.name
        assert any(url != overview_url for url in official_urls), path.name
        assert any(
            url.endswith(f"/nr-{nr_number}.pdf")
            or f"nr-{nr_number}" in url.lower()
            or f"nr_{nr_number}" in url.lower()
            or f"nr{nr_number}" in url.lower()
            for url in official_urls
            if url != overview_url
        ), path.name


def test_priority_family_blocks_have_granular_official_basis() -> None:
    priority_families = [
        "nr09_avaliacao_exposicoes_ocupacionais.json",
        "nr15_laudo_insalubridade.json",
        "nr06_gestao_epi.json",
        "nr07_pcmso.json",
        "nr05_auditoria_cipa.json",
        "nr05_implantacao_cipa.json",
        "nr10_implantacao_loto.json",
        "nr10_inspecao_spda.json",
        "nr10_inspecao_instalacoes_eletricas.json",
        "nr10_prontuario_instalacoes_eletricas.json",
        "nr01_gro_pgr.json",
        "nr01_ordem_servico_sst.json",
        "nr20_inspecao_instalacoes_inflamaveis.json",
        "nr20_prontuario_instalacoes_inflamaveis.json",
        "nr12_apreciacao_risco_maquina.json",
        "nr12_inspecao_maquina_equipamento.json",
        "nr13_inspecao_caldeira.json",
        "nr13_integridade_caldeira.json",
        "nr13_inspecao_tubulacao.json",
        "nr13_teste_hidrostatico.json",
        "nr13_teste_estanqueidade_tubulacao_gas.json",
        "nr13_calibracao_valvulas_manometros.json",
        "nr35_inspecao_linha_de_vida.json",
        "nr35_inspecao_ponto_ancoragem.json",
        "nr35_montagem_linha_de_vida.json",
        "nr35_projeto_protecao_queda.json",
        "nr33_avaliacao_espaco_confinado.json",
        "nr33_permissao_entrada_trabalho.json",
        "nr32_inspecao_servico_saude.json",
        "nr32_plano_risco_biologico.json",
        "nr04_diagnostico_sesmt.json",
        "nr08_inspecao_edificacao_industrial.json",
        "nr14_inspecao_forno_industrial.json",
        "nr16_laudo_periculosidade.json",
        "nr19_inspecao_area_explosivos.json",
        "nr21_condicoes_trabalho_ceu_aberto.json",
        "nr23_inspecao_protecao_incendios.json",
        "nr24_condicoes_sanitarias_conforto.json",
        "nr25_gestao_residuos_industriais.json",
        "nr26_sinalizacao_seguranca.json",
        "nr29_inspecao_operacao_portuaria.json",
        "nr30_inspecao_trabalho_aquaviario.json",
        "nr31_inspecao_frente_rural.json",
        "nr34_inspecao_frente_naval.json",
        "nr36_inspecao_unidade_abate_processamento.json",
        "nr37_inspecao_plataforma_petroleo.json",
        "nr38_inspecao_limpeza_urbana_residuos.json",
        "nr11_inspecao_equipamento_icamento.json",
        "nr11_inspecao_movimentacao_armazenagem.json",
        "nr17_analise_ergonomica_trabalho.json",
        "nr17_checklist_ergonomia.json",
        "nr18_inspecao_canteiro_obra.json",
        "nr18_inspecao_frente_construcao.json",
        "nr22_inspecao_area_mineracao.json",
        "nr22_inspecao_instalacao_mineira.json",
        "nr13_abertura_livro_registro_seguranca.json",
        "nr13_adequacao_planta_industrial.json",
        "nr13_calculo_espessura_minima_caldeira.json",
        "nr13_calculo_espessura_minima_tubulacao.json",
        "nr13_calculo_espessura_minima_vaso_pressao.json",
        "nr13_calculo_pmta_vaso_pressao.json",
        "nr13_fluxograma_linhas_acessorios.json",
        "nr13_inspecao_vaso_pressao.json",
        "nr13_levantamento_in_loco_equipamentos.json",
        "nr13_par_projeto_alteracao_reparo.json",
        "nr13_projeto_instalacao.json",
        "nr13_reconstituicao_prontuario.json",
        "nr13_treinamento_operacao_caldeira.json",
        "nr13_treinamento_operacao_unidades_processo.json",
    ]

    for name in priority_families:
        schema = _load_schema(name)
        basis = schema.get("normative_basis")
        assert isinstance(basis, dict), name
        assert basis.get("status") == "official_basis_family_mapped", name

        sources = basis.get("sources")
        assert isinstance(sources, list) and sources, name
        anchored_sources = [
            source
            for source in sources
            if isinstance(source, dict) and isinstance(source.get("anchors"), list) and source.get("anchors")
        ]
        assert anchored_sources, name
        assert sum(len(source["anchors"]) for source in anchored_sources) >= 3, name

        requirement_mapping = basis.get("requirement_mapping")
        assert isinstance(requirement_mapping, list) and len(requirement_mapping) >= 3, name
        for item in requirement_mapping:
            assert isinstance(item, dict), name
            assert item.get("requirement_id"), name
            assert isinstance(item.get("source_refs"), list) and item.get("source_refs"), name
            assert isinstance(item.get("maps_to"), list) and item.get("maps_to"), name
            assert item.get("application_note"), name

    nr12_schema = _load_schema("nr12_apreciacao_risco_maquina.json")
    nr12_sources = nr12_schema["normative_basis"]["sources"]
    assert any(
        "manual-de-aplicacao-da-nr-12.pdf" in str(source.get("url") or "")
        for source in nr12_sources
        if isinstance(source, dict)
    )

    nr10_schema = _load_schema("nr10_implantacao_loto.json")
    nr10_sources = nr10_schema["normative_basis"]["sources"]
    assert any(
        "manual_de_auxilio_na_interpretacao_e_aplicacao_da_nr_10.pdf" in str(source.get("url") or "")
        for source in nr10_sources
        if isinstance(source, dict)
    )

    nr01_schema = _load_schema("nr01_gro_pgr.json")
    nr01_sources = nr01_schema["normative_basis"]["sources"]
    assert any(
        "guia-nr-01-revisado.pdf" in str(source.get("url") or "")
        for source in nr01_sources
        if isinstance(source, dict)
    )

    nr20_schema = _load_schema("nr20_inspecao_instalacoes_inflamaveis.json")
    nr20_sources = nr20_schema["normative_basis"]["sources"]
    assert any(
        "nr20_nota_informativa.pdf" in str(source.get("url") or "")
        for source in nr20_sources
        if isinstance(source, dict)
    )

    nr05_schema = _load_schema("nr05_implantacao_cipa.json")
    nr05_sources = nr05_schema["normative_basis"]["sources"]
    assert any(
        "nr-05-atualizada-2023.pdf" in str(source.get("url") or "")
        for source in nr05_sources
        if isinstance(source, dict)
    )

    nr06_schema = _load_schema("nr06_gestao_epi.json")
    nr06_sources = nr06_schema["normative_basis"]["sources"]
    assert any(
        "nr-06-atualizada-2025-ii.pdf" in str(source.get("url") or "")
        for source in nr06_sources
        if isinstance(source, dict)
    )
    assert any(
        "equipamentos-de-protecao-individual" in str(source.get("url") or "")
        for source in nr06_sources
        if isinstance(source, dict)
    )

    nr07_schema = _load_schema("nr07_pcmso.json")
    nr07_sources = nr07_schema["normative_basis"]["sources"]
    assert any(
        "nr-07-atualizada-2022-1.pdf" in str(source.get("url") or "")
        for source in nr07_sources
        if isinstance(source, dict)
    )
    assert any(
        "norma-regulamentadora-no-7-nr-7" in str(source.get("url") or "")
        for source in nr07_sources
        if isinstance(source, dict)
    )

    nr09_schema = _load_schema("nr09_avaliacao_exposicoes_ocupacionais.json")
    nr09_sources = nr09_schema["normative_basis"]["sources"]
    assert any(
        "nr-09-atualizada-2026.pdf" in str(source.get("url") or "")
        for source in nr09_sources
        if isinstance(source, dict)
    )
    assert any(
        "norma-regulamentadora-no-9-nr-9" in str(source.get("url") or "")
        for source in nr09_sources
        if isinstance(source, dict)
    )

    nr15_schema = _load_schema("nr15_laudo_insalubridade.json")
    nr15_sources = nr15_schema["normative_basis"]["sources"]
    assert any(
        "nr-15-atualizada-2025.pdf" in str(source.get("url") or "")
        for source in nr15_sources
        if isinstance(source, dict)
    )
    assert any(
        "norma-regulamentadora-n-15-atividades-e-operacoes-insalubres" in str(source.get("url") or "")
        for source in nr15_sources
        if isinstance(source, dict)
    )

    nr35_schema = _load_schema("nr35_inspecao_linha_de_vida.json")
    nr35_sources = nr35_schema["normative_basis"]["sources"]
    assert any(
        "manual_consolidado_da_nr_35.pdf" in str(source.get("url") or "")
        for source in nr35_sources
        if isinstance(source, dict)
    )

    nr33_schema = _load_schema("nr33_avaliacao_espaco_confinado.json")
    nr33_sources = nr33_schema["normative_basis"]["sources"]
    assert any(
        "guia-tecnico-da-nr-33-ano-2013.pdf" in str(source.get("url") or "")
        for source in nr33_sources
        if isinstance(source, dict)
    )

    nr32_schema = _load_schema("nr32_plano_risco_biologico.json")
    nr32_sources = nr32_schema["normative_basis"]["sources"]
    assert any(
        "guia_tecnico_de_riscos_biologicos_nr_32.pdf" in str(source.get("url") or "")
        for source in nr32_sources
        if isinstance(source, dict)
    )
