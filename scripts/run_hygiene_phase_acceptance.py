#!/usr/bin/env python3
"""Runner oficial da Fase 11 - Higiene permanente e governança."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "hygiene_phase_acceptance"


def now_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_json(path: pathlib.Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def run_command(
    *,
    name: str,
    command: list[str],
    cwd: pathlib.Path,
    artifacts_dir: pathlib.Path,
) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    write_text(
        artifacts_dir / f"{name}.txt",
        "\n".join(
            [
                f"$ {' '.join(command)}",
                "",
                "[stdout]",
                completed.stdout.strip(),
                "",
                "[stderr]",
                completed.stderr.strip(),
                "",
                f"[returncode] {completed.returncode}",
            ]
        ).strip()
        + "\n",
    )
    return {
        "name": name,
        "cwd": str(cwd),
        "command": command,
        "returncode": completed.returncode,
    }


def build_final_report(results: list[dict[str, Any]]) -> str:
    status = "ok" if all(int(item["returncode"]) == 0 for item in results) else "failed"
    lines = [
        "# Fase 11 - aceite operacional",
        "",
        f"- status: {status}",
        f"- executed_at: {dt.datetime.now().isoformat()}",
        "",
        "## Commands",
    ]
    for item in results:
        lines.extend(
            [
                f"- `{item['name']}`: returncode={item['returncode']}",
                f"  command: {' '.join(item['command'])}",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    artifacts_dir = ensure_dir(ARTIFACTS_ROOT / now_slug())
    results = [
        run_command(
            name="hygiene_check",
            command=["python3", "scripts/check_workspace_hygiene.py"],
            cwd=REPO_ROOT,
            artifacts_dir=artifacts_dir,
        ),
        run_command(
            name="git_worktree_list",
            command=["git", "worktree", "list"],
            cwd=REPO_ROOT,
            artifacts_dir=artifacts_dir,
        ),
    ]

    summary_payload = {
        "status": "ok" if all(int(item["returncode"]) == 0 for item in results) else "failed",
        "executed_at": dt.datetime.now().isoformat(),
        "commands": results,
    }
    write_json(artifacts_dir / "hygiene_phase_acceptance_summary.json", summary_payload)
    write_text(artifacts_dir / "final_report.md", build_final_report(results))
    print(str(artifacts_dir))
    return 0 if summary_payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
