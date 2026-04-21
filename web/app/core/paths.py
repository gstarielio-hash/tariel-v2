"""Paths canônicos da aplicação web."""

from __future__ import annotations

import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = APP_ROOT.parent
REPO_ROOT = WEB_ROOT.parent
TEMPLATES_DIR = WEB_ROOT / "templates"
CANONICAL_DOCS_BUNDLE_DIR = WEB_ROOT / "canonical_docs"


def _valid_canonical_docs_dir(path: Path) -> bool:
    return (path / "family_schemas").is_dir() and (path / "master_templates").is_dir()


def resolve_canonical_docs_dir() -> Path:
    env_override = os.getenv("TARIEL_CANONICAL_DOCS_DIR", "").strip()
    candidates = []
    if env_override:
        candidates.append(Path(env_override).expanduser())
    candidates.extend(
        [
            REPO_ROOT / "docs",
            CANONICAL_DOCS_BUNDLE_DIR,
        ]
    )

    for candidate in candidates:
        candidate_resolved = candidate.resolve()
        if _valid_canonical_docs_dir(candidate_resolved):
            return candidate_resolved

    return (REPO_ROOT / "docs").resolve()


def resolve_family_schemas_dir() -> Path:
    return (resolve_canonical_docs_dir() / "family_schemas").resolve()


def resolve_master_templates_dir() -> Path:
    return (resolve_canonical_docs_dir() / "master_templates").resolve()


def canonical_docs_logical_path(path: Path | None) -> str | None:
    if path is None:
        return None

    path_resolved = path.resolve()
    roots = [
        (REPO_ROOT / "docs").resolve(),
        CANONICAL_DOCS_BUNDLE_DIR.resolve(),
    ]
    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        if path_resolved.is_relative_to(root):
            return str((Path("docs") / path_resolved.relative_to(root)).as_posix())
    return None

__all__ = [
    "APP_ROOT",
    "CANONICAL_DOCS_BUNDLE_DIR",
    "REPO_ROOT",
    "TEMPLATES_DIR",
    "WEB_ROOT",
    "canonical_docs_logical_path",
    "resolve_canonical_docs_dir",
    "resolve_family_schemas_dir",
    "resolve_master_templates_dir",
]
