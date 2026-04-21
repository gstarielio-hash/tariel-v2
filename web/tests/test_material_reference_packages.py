from __future__ import annotations

import json
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json(relative_path: str) -> dict:
    path = _repo_root() / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def test_nr13_inspecao_vaso_pressao_has_synthetic_reference_package() -> None:
    family_root = (
        _repo_root() / "docs" / "portfolio_empresa_nr13_material_real" / "nr13_inspecao_vaso_pressao"
    )
    status = _load_json(
        "docs/portfolio_empresa_nr13_material_real/nr13_inspecao_vaso_pressao/status_refino.json"
    )
    manifest = _load_json(
        "docs/portfolio_empresa_nr13_material_real/nr13_inspecao_vaso_pressao/pacote_referencia/manifest.json"
    )
    bundle = _load_json(
        "docs/portfolio_empresa_nr13_material_real/nr13_inspecao_vaso_pressao/pacote_referencia/tariel_filled_reference_bundle.json"
    )

    assert status["status_refino"] == "baseline_sintetica_externa_validada"
    assert status["base_sintetica_disponivel"] is True
    assert status["pacote_referencia_sintetico_disponivel"] is True
    assert status["baseline_sintetica_externa_validada"] is True

    assert manifest["schema_type"] == "filled_reference_package_manifest"
    assert manifest["family_key"] == "nr13_inspecao_vaso_pressao"
    assert manifest["bundle_file"] == "tariel_filled_reference_bundle.json"
    assert manifest["package_status"] == "synthetic_baseline"
    assert manifest["imported_from"] == "coleta_entrada/referencia_sintetica_externa/nr13_inspecao_vaso_pressao.zip"

    assert bundle["schema_type"] == "tariel_filled_reference_bundle"
    assert bundle["family_key"] == manifest["family_key"]
    assert bundle["template_code"] == "nr13_vaso_pressao"
    assert bundle["source_kind"] == "synthetic_repo_baseline"
    assert bundle["reference_summary"]["status_final"] == "ajuste"
    assert bundle["documental_sections_snapshot"][0] == "capa / folha de rosto"
    assert bundle["required_slots_snapshot"]["codigo_ativo"] == "VP-204"
    assert bundle["laudo_output_snapshot"]["conclusao"]["status_final"] == "ajuste"

    pacote_dir = family_root / "pacote_referencia"
    referencia_externa_dir = family_root / "coleta_entrada" / "referencia_sintetica_externa"
    assert (pacote_dir / bundle["reference_summary"]["pdf_file"]).exists()
    for asset_path in bundle["reference_summary"]["asset_files"]:
        assert (pacote_dir / asset_path).exists()
    assert (referencia_externa_dir / "nr13_inspecao_vaso_pressao.zip").exists()
    assert (
        referencia_externa_dir / "nr13_inspecao_vaso_pressao_referencia_sintetica.pdf"
    ).exists()
    assert (referencia_externa_dir / "README.md").exists()


def test_nr35_inspecao_linha_de_vida_has_workspace_and_synthetic_reference_package() -> None:
    family_root = (
        _repo_root() / "docs" / "portfolio_empresa_nr35_material_real" / "nr35_inspecao_linha_de_vida"
    )
    status = _load_json(
        "docs/portfolio_empresa_nr35_material_real/nr35_inspecao_linha_de_vida/status_refino.json"
    )
    manifest = _load_json(
        "docs/portfolio_empresa_nr35_material_real/nr35_inspecao_linha_de_vida/pacote_referencia/manifest.json"
    )
    bundle = _load_json(
        "docs/portfolio_empresa_nr35_material_real/nr35_inspecao_linha_de_vida/pacote_referencia/tariel_filled_reference_bundle.json"
    )
    workspace_manifest = _load_json(
        "docs/portfolio_empresa_nr35_material_real/nr35_inspecao_linha_de_vida/manifesto_coleta.json"
    )

    assert status["status_refino"] == "baseline_sintetica_externa_validada"
    assert status["base_sintetica_disponivel"] is True
    assert status["pacote_referencia_sintetico_disponivel"] is True
    assert status["baseline_sintetica_externa_validada"] is True

    assert workspace_manifest["family_key"] == "nr35_inspecao_linha_de_vida"
    assert workspace_manifest["kind"] == "inspection"
    assert len(workspace_manifest["required_slots_snapshot"]) == 4
    assert workspace_manifest["output_sections_snapshot"][0] == "Identificacao geral"

    assert manifest["schema_type"] == "filled_reference_package_manifest"
    assert manifest["family_key"] == "nr35_inspecao_linha_de_vida"
    assert manifest["bundle_file"] == "tariel_filled_reference_bundle.json"
    assert manifest["package_status"] == "synthetic_baseline"
    assert manifest["imported_from"] == "coleta_entrada/referencia_sintetica_externa/nr35_inspecao_linha_de_vida.zip"

    assert bundle["schema_type"] == "tariel_filled_reference_bundle"
    assert bundle["family_key"] == manifest["family_key"]
    assert bundle["template_code"] == "nr35_inspecao_linha_de_vida"
    assert bundle["source_kind"] == "synthetic_repo_baseline"
    assert bundle["reference_summary"]["status_final"] == "bloqueio"
    assert bundle["documental_sections_snapshot"][0] == "capa / folha de rosto"
    assert bundle["required_slots_snapshot"]["identificacao_sistema"] == "LVV-T03-EA-17"
    assert bundle["laudo_output_snapshot"]["conclusao"]["status_final"] == "bloqueio"

    pacote_dir = family_root / "pacote_referencia"
    referencia_externa_dir = family_root / "coleta_entrada" / "referencia_sintetica_externa"
    assert (pacote_dir / bundle["reference_summary"]["pdf_file"]).exists()
    for asset_path in bundle["reference_summary"]["asset_files"]:
        assert (pacote_dir / asset_path).exists()
    assert (referencia_externa_dir / "nr35_inspecao_linha_de_vida.zip").exists()
    assert (
        referencia_externa_dir / "nr35_inspecao_linha_de_vida_referencia_sintetica.pdf"
    ).exists()
    assert (referencia_externa_dir / "README.md").exists()

    readme_path = _repo_root() / "web/docs/portfolio_empresa_nr35_material_real.md"
    assert readme_path.exists()


def test_nr13_inspecao_caldeira_workspace_has_validated_synthetic_baseline() -> None:
    family_root = (
        _repo_root() / "docs" / "portfolio_empresa_nr13_material_real" / "nr13_inspecao_caldeira"
    )
    status = _load_json(
        "docs/portfolio_empresa_nr13_material_real/nr13_inspecao_caldeira/status_refino.json"
    )
    workspace_manifest = _load_json(
        "docs/portfolio_empresa_nr13_material_real/nr13_inspecao_caldeira/manifesto_coleta.json"
    )

    assert status["status_refino"] == "baseline_sintetica_externa_validada"
    assert status["workspace_pronta_para_importacao_externa"] is True
    assert status["base_sintetica_disponivel"] is True
    assert status["pacote_referencia_sintetico_disponivel"] is True
    assert status["baseline_sintetica_externa_validada"] is True

    assert workspace_manifest["family_key"] == "nr13_inspecao_caldeira"
    assert workspace_manifest["kind"] == "inspection"
    assert len(workspace_manifest["required_slots_snapshot"]) == 6
    assert workspace_manifest["output_sections_snapshot"][0] == "Identificacao"

    assert (family_root / "prompt_chatgpt_pro_nr13_inspecao_caldeira.md").exists()
    assert (
        family_root / "coleta_entrada" / "referencia_sintetica_externa" / "README.md"
    ).exists()
    assert (family_root / "pacote_referencia" / "README.md").exists()


def test_nr10_inspecao_instalacoes_eletricas_workspace_has_validated_synthetic_baseline() -> None:
    family_root = (
        _repo_root()
        / "docs"
        / "portfolio_empresa_nr10_material_real"
        / "nr10_inspecao_instalacoes_eletricas"
    )
    status = _load_json(
        "docs/portfolio_empresa_nr10_material_real/nr10_inspecao_instalacoes_eletricas/status_refino.json"
    )
    workspace_manifest = _load_json(
        "docs/portfolio_empresa_nr10_material_real/nr10_inspecao_instalacoes_eletricas/manifesto_coleta.json"
    )

    assert status["status_refino"] == "baseline_sintetica_externa_validada"
    assert status["workspace_pronta_para_importacao_externa"] is True
    assert status["base_sintetica_disponivel"] is True
    assert status["pacote_referencia_sintetico_disponivel"] is True
    assert status["baseline_sintetica_externa_validada"] is True

    assert workspace_manifest["family_key"] == "nr10_inspecao_instalacoes_eletricas"
    assert workspace_manifest["kind"] == "inspection"
    assert len(workspace_manifest["required_slots_snapshot"]) == 5
    assert workspace_manifest["output_sections_snapshot"][0] == "Identificacao"

    assert (
        family_root / "prompt_chatgpt_pro_nr10_inspecao_instalacoes_eletricas.md"
    ).exists()
    assert (
        family_root / "coleta_entrada" / "referencia_sintetica_externa" / "README.md"
    ).exists()
    assert (family_root / "pacote_referencia" / "README.md").exists()


def test_wave1_critical_material_real_portfolios_have_validated_synthetic_baseline() -> None:
    portfolios = {
        "portfolio_empresa_nr12_material_real": {
            "title": "Portfolio Empresa NR12: Material Real",
            "families": {
                "nr12_apreciacao_risco_maquina": "engineering",
                "nr12_inspecao_maquina_equipamento": "inspection",
            },
        },
        "portfolio_empresa_nr20_material_real": {
            "title": "Portfolio Empresa NR20: Material Real",
            "families": {
                "nr20_inspecao_instalacoes_inflamaveis": "inspection",
                "nr20_prontuario_instalacoes_inflamaveis": "documentation",
            },
        },
        "portfolio_empresa_nr33_material_real": {
            "title": "Portfolio Empresa NR33: Material Real",
            "families": {
                "nr33_avaliacao_espaco_confinado": "inspection",
                "nr33_permissao_entrada_trabalho": "inspection",
            },
        },
    }

    for portfolio_slug, config in portfolios.items():
        docs_readme = _repo_root() / "docs" / portfolio_slug / "README.md"
        web_summary = _repo_root() / "web" / "docs" / f"{portfolio_slug}.md"

        assert docs_readme.exists()
        assert web_summary.exists()
        assert config["title"] in docs_readme.read_text(encoding="utf-8")

        for family_key, expected_kind in config["families"].items():
            family_root = _repo_root() / "docs" / portfolio_slug / family_key
            status = _load_json(f"docs/{portfolio_slug}/{family_key}/status_refino.json")
            manifest = _load_json(f"docs/{portfolio_slug}/{family_key}/manifesto_coleta.json")
            package_manifest = _load_json(
                f"docs/{portfolio_slug}/{family_key}/pacote_referencia/manifest.json"
            )
            bundle = _load_json(
                f"docs/{portfolio_slug}/{family_key}/pacote_referencia/tariel_filled_reference_bundle.json"
            )
            package_dir = family_root / "pacote_referencia"
            raw_dir = family_root / "coleta_entrada" / "referencia_sintetica_externa"

            assert status["status_refino"] == "baseline_sintetica_externa_validada"
            assert status["workspace_pronta_para_importacao_externa"] is True
            assert status["base_sintetica_disponivel"] is True
            assert status["pacote_referencia_sintetico_disponivel"] is True
            assert status["baseline_sintetica_externa_validada"] is True

            assert manifest["family_key"] == family_key
            assert manifest["kind"] == expected_kind
            assert manifest["wave"] == 1

            assert package_manifest["schema_type"] == "filled_reference_package_manifest"
            assert package_manifest["family_key"] == family_key
            assert package_manifest["bundle_file"] == "tariel_filled_reference_bundle.json"
            assert package_manifest["package_status"] == "synthetic_baseline"
            assert package_manifest["imported_from"].endswith(f"/{family_key}.zip")

            assert bundle["schema_type"] == "tariel_filled_reference_bundle"
            assert bundle["family_key"] == family_key
            assert bundle["source_kind"] == "synthetic_repo_baseline"
            assert bundle["reference_summary"]["pdf_file"].startswith("pdf/")
            assert bundle["reference_summary"]["asset_files"]

            assert (family_root / "briefing_real.md").exists()
            assert (family_root / "coleta_entrada" / "README.md").exists()
            assert (raw_dir / "README.md").exists()
            assert (family_root / "pacote_referencia" / "README.md").exists()
            assert (
                family_root / f"prompt_fallback_sintetica_externa_{family_key}.md"
            ).exists()
            assert (package_dir / bundle["reference_summary"]["pdf_file"]).exists()
            for asset_path in bundle["reference_summary"]["asset_files"]:
                assert (package_dir / asset_path).exists()
            assert (raw_dir / f"{family_key}.zip").exists()
            assert any(raw_dir.glob(f"{family_key}*.pdf"))
