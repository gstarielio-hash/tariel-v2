from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _copy_if_needed(source: Path, target: Path) -> None:
    source = Path(source)
    target = Path(target)
    if target.exists():
        try:
            if source.samefile(target):
                return
        except FileNotFoundError:
            pass
    shutil.copy2(source, target)


def _append_unique(items: list[str], value: str | None) -> None:
    if value and value not in items:
        items.append(value)


def _relative_workspace_path(path: Path, workspace_root: Path) -> str:
    return path.relative_to(workspace_root).as_posix()


def _find_unique_file(root: Path, filename: str) -> Path:
    matches = [candidate for candidate in root.rglob(filename) if candidate.is_file()]
    if not matches:
        raise FileNotFoundError(f"Arquivo obrigatorio ausente no pacote: {filename}")
    if len(matches) > 1:
        raise ValueError(f"Arquivo duplicado no pacote: {filename}")
    return matches[0]


def _validate_relative_package_path(raw_path: str) -> Path:
    relative_path = Path(raw_path)
    if relative_path.is_absolute():
        raise ValueError(f"Caminho absoluto nao permitido no bundle: {raw_path}")
    if ".." in relative_path.parts:
        raise ValueError(f"Caminho relativo invalido no bundle: {raw_path}")
    return relative_path


def _resolve_reference_package_files(
    *,
    manifest: dict[str, Any],
    bundle: dict[str, Any],
    package_root: Path,
) -> list[str]:
    resolved_files: list[str] = []
    seen: set[str] = set()

    def append_relative_file(raw_path: str | None, *, kind: str) -> None:
        if not isinstance(raw_path, str) or not raw_path.strip():
            return
        relative_path = _validate_relative_package_path(raw_path.strip())
        source_path = package_root / relative_path
        if not source_path.exists():
            raise FileNotFoundError(f"{kind} referenciado nao encontrado no pacote: {raw_path}")
        normalized = relative_path.as_posix()
        if normalized in seen:
            return
        seen.add(normalized)
        resolved_files.append(normalized)

    reference_summary = bundle.get("reference_summary") or {}
    append_relative_file(reference_summary.get("pdf_file"), kind="PDF")
    for asset_file in list(reference_summary.get("asset_files") or []):
        append_relative_file(asset_file, kind="Asset")
    if resolved_files:
        return resolved_files

    manifest_references = [
        item for item in list(manifest.get("references") or []) if isinstance(item, dict)
    ]
    for reference in manifest_references:
        append_relative_file(reference.get("pdf_file"), kind="PDF")

    asset_dir_prefixes: list[str] = []
    for reference in manifest_references:
        assets_dir = reference.get("assets_dir")
        if not isinstance(assets_dir, str) or not assets_dir.strip():
            continue
        relative_dir = _validate_relative_package_path(assets_dir.strip())
        source_dir = package_root / relative_dir
        if not source_dir.exists() or not source_dir.is_dir():
            raise FileNotFoundError(f"Diretorio de assets referenciado nao encontrado no pacote: {assets_dir}")
        asset_dir_prefixes.append(relative_dir.as_posix())

    manifest_files = [item for item in list(manifest.get("files") or []) if isinstance(item, str)]
    if manifest_files:
        for raw_path in manifest_files:
            relative_path = _validate_relative_package_path(raw_path.strip())
            normalized = relative_path.as_posix()
            if normalized.endswith("manifest.json") or normalized.endswith(
                "tariel_filled_reference_bundle.json"
            ):
                continue
            if normalized.startswith("pdf/") or any(
                normalized.startswith(prefix.rstrip("/") + "/") for prefix in asset_dir_prefixes
            ):
                append_relative_file(normalized, kind="Arquivo")
        if resolved_files:
            return resolved_files

    for asset_dir_prefix in asset_dir_prefixes:
        assets_root = package_root / Path(asset_dir_prefix)
        for asset_path in sorted(candidate for candidate in assets_root.rglob("*") if candidate.is_file()):
            append_relative_file(
                asset_path.relative_to(package_root).as_posix(),
                kind="Asset",
            )

    return resolved_files


def inspect_reference_package_zip(zip_path: Path) -> dict[str, Any]:
    zip_path = Path(zip_path).expanduser().resolve()
    if not zip_path.exists() or not zip_path.is_file():
        raise FileNotFoundError(f"Pacote ZIP nao encontrado: {zip_path}")

    with tempfile.TemporaryDirectory(prefix="tariel-reference-package-") as temp_dir:
        extracted_root = Path(temp_dir)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extracted_root)

        manifest_path = _find_unique_file(extracted_root, "manifest.json")
        bundle_path = _find_unique_file(extracted_root, "tariel_filled_reference_bundle.json")
        manifest = _load_json(manifest_path)
        bundle = _load_json(bundle_path)

        if manifest.get("schema_type") != "filled_reference_package_manifest":
            raise ValueError("manifest.json invalido para pacote de referencia preenchida.")
        if bundle.get("schema_type") != "tariel_filled_reference_bundle":
            raise ValueError("tariel_filled_reference_bundle.json invalido.")

        family_key = str(bundle.get("family_key") or manifest.get("family_key") or "").strip()
        if not family_key:
            raise ValueError("family_key ausente no pacote.")
        if manifest.get("family_key") not in {None, "", family_key}:
            raise ValueError("family_key divergente entre manifest e bundle.")

        package_root = bundle_path.parent
        resolved_files = _resolve_reference_package_files(
            manifest=manifest,
            bundle=bundle,
            package_root=package_root,
        )

        return {
            "family_key": family_key,
            "manifest": manifest,
            "bundle": bundle,
            "resolved_files": resolved_files,
        }


def validate_reference_package_workspace_intake(
    *,
    zip_path: Path,
    workspace_root: Path,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    zip_path = Path(zip_path).expanduser().resolve()
    workspace_root = Path(workspace_root).expanduser().resolve()
    manifest_path = workspace_root / "manifesto_coleta.json"
    status_path = workspace_root / "status_refino.json"
    pacote_dir = workspace_root / "pacote_referencia"
    pacote_manifest_path = pacote_dir / "manifest.json"
    pacote_bundle_path = pacote_dir / "tariel_filled_reference_bundle.json"

    blocking_issues: list[str] = []
    warnings: list[str] = []
    workspace_manifest: dict[str, Any] = {}
    workspace_status: dict[str, Any] = {}
    workspace_family_key: str | None = None

    if not workspace_root.exists() or not workspace_root.is_dir():
        blocking_issues.append(f"Workspace da familia nao encontrada: {workspace_root}")
    if manifest_path.exists():
        workspace_manifest = _load_json(manifest_path)
        workspace_family_key = str(workspace_manifest.get("family_key") or "").strip() or None
        if workspace_family_key is None:
            blocking_issues.append(f"family_key ausente em {manifest_path}")
    else:
        blocking_issues.append(f"manifesto_coleta.json ausente na workspace: {workspace_root}")

    if status_path.exists():
        workspace_status = _load_json(status_path)
        if workspace_status.get("workspace_pronta_para_importacao_externa") is False:
            blocking_issues.append(
                "Workspace marcada como nao pronta para importacao externa em status_refino.json."
            )
        lacunas = [
            str(item).strip()
            for item in list(workspace_status.get("lacunas_abertas") or [])
            if str(item).strip()
        ]
        if lacunas:
            warnings.append(
                f"Workspace ainda possui {len(lacunas)} lacuna(s) aberta(s) em status_refino.json."
            )
    else:
        warnings.append("status_refino.json ausente na workspace; a promocao ainda pode ocorrer.")

    package_metadata: dict[str, Any] | None = None
    try:
        package_metadata = inspect_reference_package_zip(zip_path)
    except Exception as exc:  # pragma: no cover - protecao estrutural do preflight
        blocking_issues.append(str(exc))

    family_key = str((package_metadata or {}).get("family_key") or "").strip() or None
    resolved_files = [
        str(item).strip()
        for item in list((package_metadata or {}).get("resolved_files") or [])
        if str(item).strip()
    ]
    resolved_pdf_files = [
        item for item in resolved_files if Path(item).parts[:1] == ("pdf",)
    ]
    resolved_asset_files = [
        item for item in resolved_files if Path(item).parts[:1] != ("pdf",)
    ]

    external_pdf_path: str | None = None
    if pdf_path is not None:
        pdf_candidate = Path(pdf_path).expanduser().resolve()
        external_pdf_path = pdf_candidate.as_posix()
        if not pdf_candidate.exists() or not pdf_candidate.is_file():
            blocking_issues.append(f"PDF externo nao encontrado: {pdf_candidate}")

    if family_key and workspace_family_key and family_key != workspace_family_key:
        blocking_issues.append(
            f"Pacote da familia {family_key} nao corresponde a workspace {workspace_family_key}."
        )

    if not resolved_pdf_files and external_pdf_path is None:
        blocking_issues.append(
            "O pacote nao referencia PDF em pdf/ e nenhum pdf_path externo foi informado."
        )
    if not resolved_asset_files:
        warnings.append("O pacote nao referencia assets complementares alem do PDF.")
    if pacote_manifest_path.exists() and pacote_bundle_path.exists():
        warnings.append(
            "A workspace ja possui pacote_referencia consolidado; a promocao vai sobrescrever esse bundle."
        )

    ok = not blocking_issues
    return {
        "ok": ok,
        "family_key": family_key,
        "workspace_root": workspace_root.as_posix(),
        "workspace_family_key": workspace_family_key,
        "workspace_status_key": str(workspace_status.get("status_refino") or "").strip() or None,
        "workspace_ready_for_external_import": (
            None
            if not workspace_status
            else bool(workspace_status.get("workspace_pronta_para_importacao_externa", True))
        ),
        "has_manifesto_coleta": manifest_path.exists(),
        "has_status_refino": status_path.exists(),
        "has_reference_package": pacote_manifest_path.exists() and pacote_bundle_path.exists(),
        "resolved_files_count": len(resolved_files),
        "resolved_pdf_files": resolved_pdf_files,
        "resolved_asset_files": resolved_asset_files,
        "pdf_source": "external" if external_pdf_path is not None else "package",
        "external_pdf_path": external_pdf_path,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
    }


def discover_reference_workspace(repo_root: Path, family_key: str) -> Path:
    repo_root = Path(repo_root).expanduser().resolve()
    docs_root = repo_root / "docs"
    matches = [
        candidate
        for candidate in docs_root.glob(f"portfolio_empresa_*_material_real/{family_key}")
        if candidate.is_dir()
    ]
    if not matches:
        raise FileNotFoundError(f"Workspace da familia nao encontrada: {family_key}")
    if len(matches) > 1:
        raise ValueError(f"Workspace ambigua para a familia: {family_key}")
    return matches[0]


def _promote_referenced_files(
    *,
    package_root: Path,
    pacote_referencia_dir: Path,
    resolved_files: list[str],
) -> list[str]:
    top_level_dirs = {
        _validate_relative_package_path(relative_path).parts[0]
        for relative_path in resolved_files
        if len(_validate_relative_package_path(relative_path).parts) > 1
    }
    for top_level_dir in top_level_dirs:
        target_dir = pacote_referencia_dir / top_level_dir
        if target_dir.exists():
            shutil.rmtree(target_dir)

    promoted_paths: list[str] = []
    for relative_path in resolved_files:
        relative_package_path = _validate_relative_package_path(relative_path)
        source_path = package_root / relative_package_path
        target_path = pacote_referencia_dir / relative_package_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        promoted_paths.append(target_path.as_posix())
    return promoted_paths


def _build_validation_observations(bundle: dict[str, Any], promoted_files: list[str]) -> list[str]:
    reference_summary = bundle.get("reference_summary") or {}
    status_final = (
        reference_summary.get("status_final")
        or reference_summary.get("status")
        or (bundle.get("laudo_output_snapshot") or {}).get("conclusao", {}).get("status_final")
    )
    observations = [
        "ZIP autocontido com assets, manifest, bundle e PDF.",
        "manifest.json aderente ao contrato filled_reference_package_manifest.",
        "tariel_filled_reference_bundle.json aderente ao contrato tariel_filled_reference_bundle.",
    ]
    if status_final:
        observations.append(f"Status final consolidado no bundle: {status_final}.")
    if promoted_files:
        promoted_targets = sorted(
            {
                Path(*parts[1:]).parts[0]
                for relative_path in promoted_files
                if (parts := Path(relative_path).parts) and parts[0] == "pacote_referencia" and len(parts) > 1
            }
        )
        if promoted_targets:
            observations.append(
                "Arquivos promovidos para "
                + ", ".join(f"pacote_referencia/{target}/" for target in promoted_targets)
                + "."
            )
        else:
            observations.append("Arquivos promovidos para pacote_referencia/.")
    return observations


def _update_workspace_status(
    *,
    workspace_root: Path,
    bundle: dict[str, Any],
    raw_zip_path: Path,
    raw_pdf_path: Path | None,
    promoted_files: list[str],
    validation_date: str,
) -> None:
    status_path = workspace_root / "status_refino.json"
    if not status_path.exists():
        return

    status = _load_json(status_path)
    status["status_refino"] = "baseline_sintetica_externa_validada"
    status["base_sintetica_disponivel"] = True
    status["pacote_referencia_sintetico_disponivel"] = True
    status["baseline_sintetica_externa_validada"] = True

    material_recebido = list(status.get("material_recebido") or [])
    _append_unique(material_recebido, "pacote_referencia/manifest.json")
    _append_unique(material_recebido, "pacote_referencia/tariel_filled_reference_bundle.json")
    _append_unique(material_recebido, "pacote_referencia/assets/")
    _append_unique(material_recebido, "pacote_referencia/pdf/")
    _append_unique(material_recebido, _relative_workspace_path(raw_zip_path, workspace_root))
    if raw_pdf_path is not None:
        _append_unique(material_recebido, _relative_workspace_path(raw_pdf_path, workspace_root))
    status["material_recebido"] = material_recebido

    lacunas = [
        item
        for item in list(status.get("lacunas_abertas") or [])
        if "pacote sintetico externo" not in str(item).lower()
    ]
    status["lacunas_abertas"] = lacunas

    validation_entry = {
        "fonte": _relative_workspace_path(raw_zip_path, workspace_root),
        "validacao_em": validation_date,
        "resultado": "ok",
        "observacoes": _build_validation_observations(bundle, promoted_files),
    }
    validated_entries = []
    for item in list(status.get("artefatos_externos_validados") or []):
        if not isinstance(item, dict):
            continue
        if item.get("fonte") == validation_entry["fonte"]:
            continue
        validated_entries.append(item)
    validated_entries.append(validation_entry)
    status["artefatos_externos_validados"] = validated_entries

    if status.get("workspace_pronta_para_importacao_externa") is None:
        status["workspace_pronta_para_importacao_externa"] = True
    status["proximo_passo"] = (
        "Usar a baseline sintetica externa validada para calibrar o overlay visual/documental e depois complementar com material real da empresa."
    )

    _write_json(status_path, status)


def promote_reference_package_to_workspace(
    *,
    zip_path: Path,
    workspace_root: Path,
    pdf_path: Path | None = None,
    validation_date: str | None = None,
) -> dict[str, Any]:
    zip_path = Path(zip_path).expanduser().resolve()
    workspace_root = Path(workspace_root).expanduser().resolve()
    validation_date = validation_date or date.today().isoformat()

    workspace_manifest_path = workspace_root / "manifesto_coleta.json"
    if not workspace_manifest_path.exists():
        raise FileNotFoundError(f"manifesto_coleta.json ausente na workspace: {workspace_root}")
    workspace_manifest = _load_json(workspace_manifest_path)
    expected_family_key = str(workspace_manifest.get("family_key") or "").strip()
    if not expected_family_key:
        raise ValueError(f"family_key ausente em {workspace_manifest_path}")

    package_metadata = inspect_reference_package_zip(zip_path)
    family_key = package_metadata["family_key"]
    if family_key != expected_family_key:
        raise ValueError(
            f"Pacote da familia {family_key} nao corresponde a workspace {expected_family_key}."
        )

    raw_dir = workspace_root / "coleta_entrada" / "referencia_sintetica_externa"
    pacote_referencia_dir = workspace_root / "pacote_referencia"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pacote_referencia_dir.mkdir(parents=True, exist_ok=True)

    raw_zip_target = raw_dir / zip_path.name
    _copy_if_needed(zip_path, raw_zip_target)

    with tempfile.TemporaryDirectory(prefix="tariel-reference-promote-") as temp_dir:
        extracted_root = Path(temp_dir)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extracted_root)

        manifest_path = _find_unique_file(extracted_root, "manifest.json")
        bundle_path = _find_unique_file(extracted_root, "tariel_filled_reference_bundle.json")
        package_root = bundle_path.parent
        manifest = _load_json(manifest_path)
        bundle = _load_json(bundle_path)
        resolved_files = list(package_metadata["resolved_files"])

        promoted_files = _promote_referenced_files(
            package_root=package_root,
            pacote_referencia_dir=pacote_referencia_dir,
            resolved_files=resolved_files,
        )

        promoted_manifest = dict(manifest)
        promoted_manifest["imported_on"] = validation_date
        promoted_manifest["imported_from"] = _relative_workspace_path(raw_zip_target, workspace_root)
        notes = list(promoted_manifest.get("notes") or [])
        import_note = "Manifest promovido a partir de baseline sintetica externa validada."
        files_note = "Os assets e o PDF referenciados pelo bundle oficial foram descompactados em pacote_referencia/."
        if import_note not in notes:
            notes.append(import_note)
        if files_note not in notes:
            notes.append(files_note)
        promoted_manifest["notes"] = notes

        shutil.copy2(bundle_path, pacote_referencia_dir / "tariel_filled_reference_bundle.json")
        _write_json(pacote_referencia_dir / "manifest.json", promoted_manifest)

        raw_pdf_target: Path | None = None
        pdf_source: Path | None = None
        if pdf_path is not None:
            pdf_source = Path(pdf_path).expanduser().resolve()
            if not pdf_source.exists() or not pdf_source.is_file():
                raise FileNotFoundError(f"PDF externo nao encontrado: {pdf_source}")
            raw_pdf_target = raw_dir / pdf_source.name
            _copy_if_needed(pdf_source, raw_pdf_target)
        elif resolved_files:
            pdf_candidates = [
                relative_path for relative_path in resolved_files if Path(relative_path).parts[:1] == ("pdf",)
            ]
            pdf_source = (
                package_root / _validate_relative_package_path(pdf_candidates[0])
                if pdf_candidates
                else None
            )
            if pdf_source is not None:
                raw_pdf_target = raw_dir / pdf_source.name
                _copy_if_needed(pdf_source, raw_pdf_target)
        elif (bundle.get("reference_summary") or {}).get("pdf_file"):
            pdf_source = package_root / _validate_relative_package_path(
                str((bundle.get("reference_summary") or {}).get("pdf_file")).strip()
            )
            raw_pdf_target = raw_dir / pdf_source.name
            _copy_if_needed(pdf_source, raw_pdf_target)

    _update_workspace_status(
        workspace_root=workspace_root,
        bundle=package_metadata["bundle"],
        raw_zip_path=raw_zip_target,
        raw_pdf_path=raw_pdf_target,
        promoted_files=[
            _relative_workspace_path(Path(path), workspace_root)
            for path in promoted_files
        ],
        validation_date=validation_date,
    )

    return {
        "family_key": family_key,
        "workspace_root": workspace_root.as_posix(),
        "raw_zip_path": raw_zip_target.as_posix(),
        "raw_pdf_path": raw_pdf_target.as_posix() if raw_pdf_target else None,
        "promoted_manifest_path": (pacote_referencia_dir / "manifest.json").as_posix(),
        "promoted_bundle_path": (pacote_referencia_dir / "tariel_filled_reference_bundle.json").as_posix(),
        "promoted_files": promoted_files,
    }
