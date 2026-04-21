from __future__ import annotations

from pathlib import Path

import app.core.paths as core_paths


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _relative_files(root: Path) -> list[Path]:
    return sorted(path.relative_to(root) for path in root.rglob("*") if path.is_file())


def test_bundled_canonical_docs_match_repo_docs() -> None:
    repo_root = _repo_root()
    repo_docs = repo_root / "docs"
    bundle_root = repo_root / "web" / "canonical_docs"

    for name in ("family_schemas", "master_templates"):
        source_root = repo_docs / name
        bundled_dir = bundle_root / name
        source_files = _relative_files(source_root)
        bundled_files = _relative_files(bundled_dir)

        assert bundled_files == source_files
        for relative_path in source_files:
            assert (bundled_dir / relative_path).read_bytes() == (source_root / relative_path).read_bytes()


def test_resolve_canonical_docs_dir_falls_back_to_bundled_copy(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    web_root = tmp_path / "web"
    bundled_docs = web_root / "canonical_docs"
    family_dir = bundled_docs / "family_schemas"
    master_dir = bundled_docs / "master_templates"

    family_dir.mkdir(parents=True)
    master_dir.mkdir(parents=True)
    (family_dir / "nr13_demo.json").write_text("{}", encoding="utf-8")
    (master_dir / "library_registry.json").write_text('{"templates":[]}', encoding="utf-8")

    monkeypatch.delenv("TARIEL_CANONICAL_DOCS_DIR", raising=False)
    monkeypatch.setattr(core_paths, "REPO_ROOT", repo_root)
    monkeypatch.setattr(core_paths, "WEB_ROOT", web_root)
    monkeypatch.setattr(core_paths, "CANONICAL_DOCS_BUNDLE_DIR", bundled_docs)

    assert core_paths.resolve_canonical_docs_dir() == bundled_docs.resolve()
    assert core_paths.resolve_family_schemas_dir() == family_dir.resolve()
    assert core_paths.resolve_master_templates_dir() == master_dir.resolve()
    assert core_paths.canonical_docs_logical_path(master_dir / "library_registry.json") == (
        "docs/master_templates/library_registry.json"
    )
