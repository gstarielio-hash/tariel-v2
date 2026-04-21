#!/usr/bin/env python3
"""Runner oficial da Fase 12 - Evolucao estrutural V2."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
ANDROID_ROOT = REPO_ROOT / "android"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "v2_phase_acceptance"
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
    }


def build_final_report(results: list[dict[str, Any]]) -> str:
    status = "ok" if all(int(item["returncode"]) == 0 for item in results) else "failed"
    lines = [
        "# Fase 12 - aceite operacional",
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
    results: list[dict[str, Any]] = []

    results.append(
        run_command(
            name="web_v2_core",
            command=[
                str(WEB_PYTHON),
                "-m",
                "pytest",
                "-q",
                "tests/test_v2_billing_metering.py",
                "tests/test_v2_envelopes.py",
                "tests/test_v2_case_core_acl.py",
                "tests/test_v2_technical_case_snapshot.py",
                "tests/test_v2_provenance.py",
                "tests/test_v2_policy_engine.py",
                "tests/test_v2_document_facade.py",
                "tests/test_v2_document_soft_gate.py",
                "tests/test_v2_document_shadow.py",
                "tests/test_v2_inspector_projection.py",
                "tests/test_v2_reviewdesk_projection.py",
                "tests/test_v2_inspector_document_projection.py",
                "tests/test_v2_review_queue_projection.py",
                "tests/test_v2_tenant_admin_projection.py",
                "tests/test_v2_platform_admin_projection.py",
                "tests/test_v2_android_case_feed_adapter.py",
                "tests/test_v2_android_case_thread_adapter.py",
            ],
            cwd=WEB_ROOT,
            artifacts_dir=artifacts_dir,
        )
    )
    results.append(
        run_command(
            name="android_v2_contracts",
            command=[
                "npm",
                "run",
                "test",
                "--",
                "--runInBand",
                "src/config/mesaApi.test.ts",
                "src/config/mobileV2MesaAdapter.test.ts",
                "src/config/mobileV2HumanValidation.test.ts",
                "src/config/mobilePilotRequestTrace.test.ts",
            ],
            cwd=ANDROID_ROOT,
            artifacts_dir=artifacts_dir,
        )
    )
    results.append(
        run_command(
            name="contract_check",
            command=["make", "contract-check"],
            cwd=REPO_ROOT,
            artifacts_dir=artifacts_dir,
        )
    )

    summary_payload = {
        "status": "ok" if all(int(item["returncode"]) == 0 for item in results) else "failed",
        "executed_at": dt.datetime.now().isoformat(),
        "commands": results,
    }
    write_json(artifacts_dir / "v2_phase_acceptance_summary.json", summary_payload)
    write_text(artifacts_dir / "final_report.md", build_final_report(results))
    print(str(artifacts_dir))
    return 0 if summary_payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
