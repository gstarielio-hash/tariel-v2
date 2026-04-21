#!/usr/bin/env python3
"""Valida a política local de hygiene/worktree/artifacts do repositório."""

from __future__ import annotations

import json
import pathlib
import subprocess
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    ".gitignore",
    "AGENTS.md",
    "PLANS.md",
    "README.md",
    "android/.gitignore",
    "web/.gitignore",
    "artifacts/.gitignore",
    "artifacts/README.md",
    "web/artifacts/.gitignore",
    "web/artifacts/README.md",
    "docs/developer-experience/04_git_worktree_policy.md",
    "docs/developer-experience/08_artifacts_and_workspace_hygiene_policy.md",
)

REQUIRED_TEXT_CHECKS = (
    ("AGENTS.md", "make hygiene-check"),
    ("AGENTS.md", "git worktree"),
    ("AGENTS.md", "PLANS.md"),
    ("README.md", "make hygiene-check"),
    ("docs/developer-experience/04_git_worktree_policy.md", "PLANS.md"),
    ("docs/developer-experience/04_git_worktree_policy.md", "git worktree add"),
    ("docs/developer-experience/08_artifacts_and_workspace_hygiene_policy.md", "artifacts/<lane>/<timestamp>/"),
    ("docs/developer-experience/08_artifacts_and_workspace_hygiene_policy.md", "make hygiene-check"),
)

IGNORED_PATH_SAMPLES = (
    "artifacts/hygiene_phase_acceptance/20990101_000000/final_report.md",
    "artifacts/observability_phase_acceptance/20990101_000000/summary.json",
    "web/artifacts/visual/inspetor/20990101-000000/report.json",
    "web/static/uploads/local-upload.bin",
    "android/dist/app-release.apk",
    "android/android/build/intermediates/output.txt",
    ".tmp_online/baseline/20990101_000000/status.txt",
)


def rel(path: pathlib.Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def git_check_ignore(relative_path: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "check-ignore", "-v", relative_path],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "path": relative_path,
        "ignored": completed.returncode == 0,
        "match": completed.stdout.strip(),
    }


def list_worktrees() -> list[str]:
    completed = subprocess.run(
        ["git", "worktree", "list"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def build_summary() -> dict[str, Any]:
    missing_files = [path for path in REQUIRED_FILES if not (REPO_ROOT / path).exists()]
    missing_text_checks = [
        {"path": path, "needle": needle}
        for path, needle in REQUIRED_TEXT_CHECKS
        if needle not in read_text(path)
    ]
    ignored_samples = [git_check_ignore(path) for path in IGNORED_PATH_SAMPLES]
    non_ignored_samples = [item for item in ignored_samples if not item["ignored"]]
    worktrees = list_worktrees()
    status = "ok" if not missing_files and not missing_text_checks and not non_ignored_samples else "failed"

    return {
        "status": status,
        "required_files": {
            "checked": list(REQUIRED_FILES),
            "missing": missing_files,
        },
        "required_text_checks": {
            "checked": [{"path": path, "needle": needle} for path, needle in REQUIRED_TEXT_CHECKS],
            "missing": missing_text_checks,
        },
        "ignored_path_samples": ignored_samples,
        "worktrees": worktrees,
    }


def main() -> int:
    summary = build_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
