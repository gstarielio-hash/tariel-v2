#!/usr/bin/env python3
"""Runner oficial da Fase 09 - Documento, template e IA."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "document_phase_acceptance"
WEB_PYTHON = (
    WEB_ROOT / ".venv-linux" / "bin" / "python"
    if (WEB_ROOT / ".venv-linux" / "bin" / "python").exists()
    else pathlib.Path("python3")
)


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
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def build_final_report(results: list[dict[str, Any]]) -> str:
    status = "ok" if all(int(item["returncode"]) == 0 for item in results) else "failed"
    lines = [
        "# Fase 09 - aceite operacional",
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


def extract_json_payload(raw_output: str) -> Any | None:
    text = str(raw_output or "").strip()
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None

    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    artifacts_dir = ensure_dir(ARTIFACTS_ROOT / now_slug())
    results: list[dict[str, Any]] = []

    results.append(
        run_command(
            name="document_hard_gate_10g",
            command=["python3", "scripts/run_document_hard_gate_10g_validation.py"],
            cwd=REPO_ROOT,
            artifacts_dir=artifacts_dir,
        )
    )
    results.append(
        run_command(
            name="document_hard_gate_10i",
            command=["python3", "scripts/run_document_hard_gate_10i_validation.py"],
            cwd=REPO_ROOT,
            artifacts_dir=artifacts_dir,
        )
    )
    results.append(
        run_command(
            name="web_document_template_tests",
            command=[
                str(WEB_PYTHON),
                "-m",
                "pytest",
                "-q",
                "tests/test_template_publish_contract.py",
                "tests/test_revisor_templates_diff_critico.py",
                "tests/test_v2_document_soft_gate_summary.py",
                "tests/test_v2_document_hard_gate_summary.py",
                "tests/test_v2_document_hard_gate_10g.py",
                "tests/test_v2_document_operations_summary.py",
            ],
            cwd=WEB_ROOT,
            artifacts_dir=artifacts_dir,
        )
    )

    summary_payload = {
        "status": "ok" if all(int(item["returncode"]) == 0 for item in results) else "failed",
        "executed_at": dt.datetime.now().isoformat(),
        "commands": [
            {
                "name": item["name"],
                "cwd": item["cwd"],
                "command": item["command"],
                "returncode": item["returncode"],
            }
            for item in results
        ],
        "document_hard_gate_10g_artifact": results[0]["stdout"].strip().splitlines()[-1]
        if results[0]["stdout"].strip()
        else None,
        "document_hard_gate_10i_result": extract_json_payload(results[1]["stdout"]),
    }
    write_json(artifacts_dir / "document_phase_acceptance_summary.json", summary_payload)
    write_text(artifacts_dir / "final_report.md", build_final_report(results))
    print(str(artifacts_dir))
    return 0 if summary_payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
