from __future__ import annotations

import json
import zipfile
from pathlib import Path

from app.domains.revisor.reference_package_workspace import (
    discover_reference_workspace,
    inspect_reference_package_zip,
    promote_reference_package_to_workspace,
    validate_reference_package_workspace_intake,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_sample_zip(tmp_path: Path, *, family_key: str, manifest_fallback: bool = False) -> Path:
    package_root = tmp_path / "package_source" / family_key
    assets_dir = package_root / "assets"
    pdf_dir = package_root / "pdf"
    assets_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    (assets_dir / "IMG_001.png").write_bytes(b"fake-image")
    (pdf_dir / f"{family_key}_referencia_sintetica.pdf").write_bytes(b"%PDF-1.4 fake")

    _write_json(
        package_root / "manifest.json",
        ({
            "schema_type": "filled_reference_package_manifest",
            "schema_version": 1,
            "family_key": family_key,
            "package_status": "synthetic_baseline",
            "source_kind": "synthetic_repo_baseline",
            "bundle_file": "tariel_filled_reference_bundle.json",
            "reference_count": 1,
        }
        | (
            {
                "references": [
                    {
                        "reference_id": f"{family_key}.synthetic.v1",
                        "pdf_file": f"pdf/{family_key}_referencia_sintetica.pdf",
                        "assets_dir": "assets",
                        "document_code": "REL-TEST-001",
                        "status_final": "ajuste",
                    }
                ],
                "files": [
                    "assets/IMG_001.png",
                    f"pdf/{family_key}_referencia_sintetica.pdf",
                    "tariel_filled_reference_bundle.json",
                ],
            }
            if manifest_fallback
            else {}
        )),
    )
    _write_json(
        package_root / "tariel_filled_reference_bundle.json",
        {
            "schema_type": "tariel_filled_reference_bundle",
            "schema_version": 1,
            "family_key": family_key,
            "template_code": "sample_template",
            "reference_id": f"{family_key}.synthetic.v1",
            "source_kind": "synthetic_repo_baseline",
            "reference_summary": {
                "title": "Baseline sintetica de teste",
                "document_code": "REL-TEST-001",
                "status_final": "ajuste",
                **(
                    {}
                    if manifest_fallback
                    else {
                        "pdf_file": f"pdf/{family_key}_referencia_sintetica.pdf",
                        "asset_files": ["assets/IMG_001.png"],
                    }
                ),
            },
            "required_slots_snapshot": {"codigo_ativo": "CAL-01"},
            "documental_sections_snapshot": ["capa / folha de rosto"],
            "notes": ["pacote de teste"],
            "laudo_output_snapshot": {"conclusao": {"status_final": "ajuste"}},
        },
    )

    zip_path = tmp_path / f"{family_key}.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for file_path in package_root.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(package_root.parent))
    return zip_path


def test_promote_reference_package_to_workspace_copies_assets_and_updates_status(tmp_path: Path) -> None:
    family_key = "nr13_inspecao_caldeira"
    workspace_root = tmp_path / "docs" / "portfolio_empresa_nr13_material_real" / family_key
    _write_json(
        workspace_root / "manifesto_coleta.json",
        {"family_key": family_key, "kind": "inspection"},
    )
    _write_json(
        workspace_root / "status_refino.json",
        {
            "family_key": family_key,
            "status_refino": "aguardando_material_real",
            "material_recebido": [],
            "lacunas_abertas": [
                "Aguardando pacote sintetico externo da familia para baseline visual e documental inicial."
            ],
            "base_sintetica_disponivel": True,
        },
    )

    zip_path = _build_sample_zip(tmp_path, family_key=family_key)
    result = promote_reference_package_to_workspace(
        zip_path=zip_path,
        workspace_root=workspace_root,
        validation_date="2026-04-09",
    )

    assert result["family_key"] == family_key
    assert Path(result["raw_zip_path"]).exists()
    assert Path(result["raw_pdf_path"]).exists()
    assert Path(result["promoted_manifest_path"]).exists()
    assert Path(result["promoted_bundle_path"]).exists()

    promoted_manifest = json.loads(Path(result["promoted_manifest_path"]).read_text(encoding="utf-8"))
    promoted_bundle = json.loads(Path(result["promoted_bundle_path"]).read_text(encoding="utf-8"))
    promoted_status = json.loads((workspace_root / "status_refino.json").read_text(encoding="utf-8"))

    assert promoted_manifest["imported_on"] == "2026-04-09"
    assert promoted_manifest["imported_from"] == (
        f"coleta_entrada/referencia_sintetica_externa/{family_key}.zip"
    )
    assert promoted_bundle["reference_summary"]["status_final"] == "ajuste"

    assert promoted_status["status_refino"] == "baseline_sintetica_externa_validada"
    assert promoted_status["baseline_sintetica_externa_validada"] is True
    assert promoted_status["pacote_referencia_sintetico_disponivel"] is True
    assert "Aguardando pacote sintetico externo" not in " ".join(promoted_status["lacunas_abertas"])
    assert promoted_status["artefatos_externos_validados"][0]["fonte"] == (
        f"coleta_entrada/referencia_sintetica_externa/{family_key}.zip"
    )

    pacote_dir = workspace_root / "pacote_referencia"
    assert (pacote_dir / "assets" / "IMG_001.png").exists()
    assert (pacote_dir / "pdf" / f"{family_key}_referencia_sintetica.pdf").exists()


def test_discover_reference_workspace_resolves_unique_family_workspace(tmp_path: Path) -> None:
    family_key = "nr35_inspecao_linha_de_vida"
    workspace_root = tmp_path / "docs" / "portfolio_empresa_nr35_material_real" / family_key
    workspace_root.mkdir(parents=True, exist_ok=True)

    resolved = discover_reference_workspace(tmp_path, family_key)
    assert resolved == workspace_root


def test_inspect_reference_package_zip_validates_required_files(tmp_path: Path) -> None:
    family_key = "nr13_inspecao_vaso_pressao"
    zip_path = _build_sample_zip(tmp_path, family_key=family_key)

    metadata = inspect_reference_package_zip(zip_path)

    assert metadata["family_key"] == family_key
    assert metadata["manifest"]["family_key"] == family_key
    assert metadata["bundle"]["reference_summary"]["pdf_file"] == (
        f"pdf/{family_key}_referencia_sintetica.pdf"
    )


def test_promote_reference_package_to_workspace_uses_manifest_file_references_when_bundle_is_partial(
    tmp_path: Path,
) -> None:
    family_key = "nr10_inspecao_instalacoes_eletricas"
    workspace_root = tmp_path / "docs" / "portfolio_empresa_nr10_material_real" / family_key
    _write_json(
        workspace_root / "manifesto_coleta.json",
        {"family_key": family_key, "kind": "inspection"},
    )
    _write_json(
        workspace_root / "status_refino.json",
        {
            "family_key": family_key,
            "status_refino": "aguardando_material_real",
            "material_recebido": [],
            "lacunas_abertas": [
                "Aguardando pacote sintetico externo da familia para baseline visual e documental inicial."
            ],
        },
    )

    zip_path = _build_sample_zip(tmp_path, family_key=family_key, manifest_fallback=True)
    result = promote_reference_package_to_workspace(
        zip_path=zip_path,
        workspace_root=workspace_root,
        validation_date="2026-04-10",
    )

    pacote_dir = workspace_root / "pacote_referencia"
    promoted_status = json.loads((workspace_root / "status_refino.json").read_text(encoding="utf-8"))

    assert Path(result["raw_pdf_path"]).exists()
    assert (pacote_dir / "assets" / "IMG_001.png").exists()
    assert (pacote_dir / "pdf" / f"{family_key}_referencia_sintetica.pdf").exists()
    assert any(
        "pacote_referencia/" in observation
        for observation in promoted_status["artefatos_externos_validados"][0]["observacoes"]
    )


def test_promote_reference_package_to_workspace_is_idempotent_when_reusing_raw_inputs(
    tmp_path: Path,
) -> None:
    family_key = "nr13_inspecao_caldeira"
    workspace_root = tmp_path / "docs" / "portfolio_empresa_nr13_material_real" / family_key
    _write_json(
        workspace_root / "manifesto_coleta.json",
        {"family_key": family_key, "kind": "inspection"},
    )
    _write_json(
        workspace_root / "status_refino.json",
        {
            "family_key": family_key,
            "status_refino": "aguardando_material_real",
            "material_recebido": [],
            "lacunas_abertas": [],
        },
    )

    zip_path = _build_sample_zip(tmp_path, family_key=family_key)
    first_result = promote_reference_package_to_workspace(
        zip_path=zip_path,
        workspace_root=workspace_root,
        validation_date="2026-04-10",
    )
    second_result = promote_reference_package_to_workspace(
        zip_path=Path(first_result["raw_zip_path"]),
        workspace_root=workspace_root,
        pdf_path=Path(first_result["raw_pdf_path"]),
        validation_date="2026-04-10",
    )

    assert Path(second_result["raw_zip_path"]).exists()
    assert Path(second_result["raw_pdf_path"]).exists()
    assert (workspace_root / "pacote_referencia" / "assets" / "IMG_001.png").exists()


def test_validate_reference_package_workspace_intake_reports_readiness_and_package_files(
    tmp_path: Path,
) -> None:
    family_key = "nr20_prontuario_instalacoes_inflamaveis"
    workspace_root = tmp_path / "docs" / "portfolio_empresa_nr20_material_real" / family_key
    _write_json(
        workspace_root / "manifesto_coleta.json",
        {"family_key": family_key, "kind": "documentation"},
    )
    _write_json(
        workspace_root / "status_refino.json",
        {
            "family_key": family_key,
            "status_refino": "aguardando_material_real",
            "workspace_pronta_para_importacao_externa": True,
            "lacunas_abertas": ["Aguardando documento final real."],
        },
    )
    (workspace_root / "pacote_referencia").mkdir(parents=True, exist_ok=True)
    _write_json(workspace_root / "pacote_referencia" / "manifest.json", {"family_key": family_key})
    _write_json(
        workspace_root / "pacote_referencia" / "tariel_filled_reference_bundle.json",
        {"family_key": family_key},
    )

    zip_path = _build_sample_zip(tmp_path, family_key=family_key)

    payload = validate_reference_package_workspace_intake(
        zip_path=zip_path,
        workspace_root=workspace_root,
    )

    assert payload["ok"] is True
    assert payload["family_key"] == family_key
    assert payload["workspace_family_key"] == family_key
    assert payload["workspace_status_key"] == "aguardando_material_real"
    assert payload["resolved_files_count"] == 2
    assert payload["resolved_pdf_files"] == [f"pdf/{family_key}_referencia_sintetica.pdf"]
    assert payload["resolved_asset_files"] == ["assets/IMG_001.png"]
    assert payload["warnings"]
    assert any("lacuna" in item.lower() for item in payload["warnings"])
    assert any("sobrescrever" in item.lower() for item in payload["warnings"])


def test_validate_reference_package_workspace_intake_blocks_family_mismatch_and_missing_pdf(
    tmp_path: Path,
) -> None:
    family_key = "nr13_inspecao_vaso_pressao"
    workspace_root = tmp_path / "docs" / "portfolio_empresa_nr13_material_real" / family_key
    _write_json(
        workspace_root / "manifesto_coleta.json",
        {"family_key": family_key, "kind": "inspection"},
    )
    _write_json(
        workspace_root / "status_refino.json",
        {
            "family_key": family_key,
            "status_refino": "workspace_bootstrapped",
            "workspace_pronta_para_importacao_externa": False,
        },
    )

    zip_path = _build_sample_zip(tmp_path, family_key="nr13_inspecao_caldeira")
    missing_pdf = tmp_path / "ausente.pdf"

    payload = validate_reference_package_workspace_intake(
        zip_path=zip_path,
        workspace_root=workspace_root,
        pdf_path=missing_pdf,
    )

    assert payload["ok"] is False
    assert payload["external_pdf_path"] == missing_pdf.resolve().as_posix()
    assert any("nao pronta para importacao" in item.lower() for item in payload["blocking_issues"])
    assert any("nao corresponde a workspace" in item.lower() for item in payload["blocking_issues"])
    assert any("pdf externo nao encontrado" in item.lower() for item in payload["blocking_issues"])
