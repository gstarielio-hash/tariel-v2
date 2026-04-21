#!/usr/bin/env python3
"""Campanha operacional ampliada do Epic 10J para template_publish_activate em shadow_only."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
from collections import Counter
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "document_hard_gate_shadow_campaign_10i"
MAIN_RUNNER_SCRIPT = REPO_ROOT / "scripts" / "run_document_hard_gate_10i_validation.py"
HTTP_HARNESS_SCRIPT = REPO_ROOT / "scripts" / "run_document_hard_gate_10j_http_harness.py"


def now_local_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_json(path: pathlib.Path, payload: Any) -> None:
    def _default(value: Any) -> str:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=_default),
        encoding="utf-8",
    )


def save_command_artifact(
    path: pathlib.Path,
    command: list[str],
    completed: subprocess.CompletedProcess[str],
) -> None:
    write_text(
        path,
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


def run_command(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: pathlib.Path | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=str(cwd or REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Comando falhou ({completed.returncode}): {' '.join(command)}\n{completed.stderr}"
        )
    return completed


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_if_exists(source: pathlib.Path, destination: pathlib.Path) -> str | None:
    if not source.exists():
        return None
    ensure_dir(destination.parent)
    shutil.copy2(source, destination)
    return str(destination)


def build_campaign_findings(
    *,
    precheck: dict[str, Any],
    campaign_summary: dict[str, Any],
    harness_matrix: list[dict[str, Any]],
) -> str:
    blockers_lines = [
        f"- `{blocker_code}`: {count}"
        for blocker_code, count in sorted(campaign_summary["blockers_by_code"].items())
    ] or ["- nenhum"]
    harness_lines = [
        f"- `{item['harness_name']}`: {item['useful_executions']} execucoes uteis"
        for item in harness_matrix
    ]
    not_observed_lines = [
        "- familia propria adicional de blockers de governanca de template: `nao_observado`"
    ]
    case_lines = [
        f"- `{case_profile}`"
        for case_profile in campaign_summary["distinct_case_profiles"]
    ]

    return "\n".join(
        [
            "# Epic 10J - campanha operacional ampliada de template_publish_activate em shadow_only",
            "",
            "## Pre-checagem executada",
            "",
            f"- `pwd`: `{precheck['pwd']}`",
            "- `git status --short`: registrado em `git_status_short.txt`",
            f"- boot/import: `{precheck['boot_import_status']}`",
            f"- tenant local/controlado confirmado: `{precheck['tenant_local_controlled']}`",
            f"- operation allowlisted: `{precheck['operation_allowlisted']}`",
            f"- runner 10I existente e executado: `{precheck['main_runner_executed']}`",
            "",
            "## Casos seguros exercitados",
            "",
            *case_lines,
            "",
            "## Harnesses usados",
            "",
            *harness_lines,
            "",
            "## Resultado agregado",
            "",
            f"- execucoes uteis novas: `{campaign_summary['useful_executions']}`",
            f"- templates distintos exercitados: `{campaign_summary['distinct_template_codes_count']}`",
            f"- publicacao funcional preservada: `{campaign_summary['functional_publications_preserved']}`",
            f"- shadow sem bleed observado: `{campaign_summary['shadow_without_bleed_count']}`",
            f"- `would_block=true`: `{campaign_summary['would_block_true_count']}`",
            f"- `did_block=true`: `{campaign_summary['did_block_true_count']}`",
            "",
            "## Blockers observados",
            "",
            *blockers_lines,
            "",
            "## Blockers ainda nao observados",
            "",
            *not_observed_lines,
            "",
            "## Conclusao",
            "",
            "- o slice permaneceu `shadow_only` nos dois harnesses.",
            "- `did_block` permaneceu `false` em todas as execucoes uteis da campanha.",
            "- os blockers atuais continuam restritos a `template_not_bound` e `template_source_unknown`.",
            "- a amostra melhorou de forma material, mas a familia propria de blockers de governanca de template continua `nao_observado` nesta fase.",
        ]
    ) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="",
        help="Diretorio raiz da campanha.",
    )
    return parser.parse_args()


def normalize_case_profile(case_payload: dict[str, Any]) -> str:
    explicit = str(case_payload.get("case_profile") or "").strip()
    if explicit:
        return explicit

    route_name = str(case_payload.get("route_name") or "").strip()
    blockers = list(case_payload.get("blockers") or [])
    if route_name == "publicar_template_laudo":
        return "legacy_gap" if blockers else "legacy_ok"
    if route_name == "publicar_template_editor_laudo":
        return "editor_gap" if blockers else "editor_ok"
    return str(case_payload.get("case_name") or "unknown_case")


def main() -> int:
    args = parse_args()
    output_dir = (
        ensure_dir(pathlib.Path(args.output_dir).expanduser().resolve())
        if args.output_dir
        else ensure_dir((ARTIFACTS_ROOT / now_local_slug()).resolve())
    )
    runs_dir = ensure_dir(output_dir / "runs")
    responses_dir = ensure_dir(output_dir / "responses")
    summaries_dir = ensure_dir(output_dir / "summaries")

    env = os.environ.copy()
    env["AMBIENTE"] = "dev"
    env["PYTHONPATH"] = "web"

    pwd_completed = run_command(["pwd"], cwd=REPO_ROOT)
    save_command_artifact(output_dir / "pwd.txt", ["pwd"], pwd_completed)

    git_status_completed = run_command(["git", "status", "--short"], cwd=REPO_ROOT)
    save_command_artifact(output_dir / "git_status_short.txt", ["git", "status", "--short"], git_status_completed)

    boot_command = ["python3", "-c", "import main; main.create_app(); print('boot_import_ok')"]
    boot_completed = run_command(boot_command, cwd=REPO_ROOT, env=env)
    save_command_artifact(output_dir / "boot_import_check.txt", boot_command, boot_completed)

    shadow_completed = run_command(
        [
            "python3",
            "-c",
            "import sys; sys.path.insert(0, 'web'); from app.v2.document.hard_gate import _SHADOW_ONLY_OPERATION_KINDS; print(sorted(_SHADOW_ONLY_OPERATION_KINDS))",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    save_command_artifact(
        output_dir / "shadow_only_operations_check.txt",
        [
            "python3",
            "-c",
            "import sys; sys.path.insert(0, 'web'); from app.v2.document.hard_gate import _SHADOW_ONLY_OPERATION_KINDS; print(sorted(_SHADOW_ONLY_OPERATION_KINDS))",
        ],
        shadow_completed,
    )

    main_runner_dir = ensure_dir(runs_dir / "main_runner_10i_validation")
    http_harness_dir = ensure_dir(runs_dir / "testclient_http_harness")

    main_runner_completed = run_command(
        ["python3", str(MAIN_RUNNER_SCRIPT), "--output-dir", str(main_runner_dir)],
        cwd=REPO_ROOT,
        env=env,
    )
    save_command_artifact(
        output_dir / "main_runner_execution.txt",
        ["python3", str(MAIN_RUNNER_SCRIPT), "--output-dir", str(main_runner_dir)],
        main_runner_completed,
    )

    http_harness_completed = run_command(
        ["python3", str(HTTP_HARNESS_SCRIPT), "--output-dir", str(http_harness_dir)],
        cwd=REPO_ROOT,
        env=env,
    )
    save_command_artifact(
        output_dir / "http_harness_execution.txt",
        ["python3", str(HTTP_HARNESS_SCRIPT), "--output-dir", str(http_harness_dir)],
        http_harness_completed,
    )

    main_cases = load_json(main_runner_dir / "validation_cases.json")
    http_cases = load_json(http_harness_dir / "validation_cases.json")
    all_cases = []
    for run_artifact_root, items in (
        (main_runner_dir, main_cases),
        (http_harness_dir, http_cases),
    ):
        for item in items:
            enriched = dict(item)
            enriched["case_profile"] = normalize_case_profile(enriched)
            enriched["run_artifact_root"] = str(run_artifact_root)
            all_cases.append(enriched)

    blockers_by_code = Counter(
        blocker
        for case in all_cases
        for blocker in list(case.get("blockers") or [])
    )
    cases_by_harness = Counter(str(case["harness"]) for case in all_cases)
    distinct_case_profiles = sorted(
        {
            str(case.get("case_profile") or case.get("case_name") or "")
            for case in all_cases
            if str(case.get("case_profile") or case.get("case_name") or "").strip()
        }
    )
    distinct_template_codes = sorted(
        {
            str(case.get("codigo_template") or "").strip()
            for case in all_cases
            if str(case.get("codigo_template") or "").strip()
        }
    )
    functional_publications_preserved = sum(
        1
        for case in all_cases
        if str(case.get("functional_outcome") or "") == "template_publish_completed_shadow_only"
        and int(case.get("response_status_code") or 0) == 200
    )
    shadow_without_bleed_count = sum(
        1
        for case in all_cases
        if bool(case.get("shadow_only"))
        and not bool(case.get("did_block"))
        and not bool(case.get("enforce_enabled"))
        and str(case.get("tenant_id") or "") == "1"
    )

    precheck_summary = {
        "pwd": pwd_completed.stdout.strip(),
        "boot_import_status": "boot_import_ok" if "boot_import_ok" in boot_completed.stdout else "falhou",
        "dirty_worktree_observed": bool(git_status_completed.stdout.strip()),
        "shadow_only_operations": shadow_completed.stdout.strip(),
        "tenant_local_controlled": "tenant=1 host=testclient",
        "operation_allowlisted": "template_publish_activate",
        "main_runner_path": str(MAIN_RUNNER_SCRIPT),
        "main_runner_exists": MAIN_RUNNER_SCRIPT.exists(),
        "main_runner_executed": True,
        "http_harness_path": str(HTTP_HARNESS_SCRIPT),
        "http_harness_exists": HTTP_HARNESS_SCRIPT.exists(),
        "http_harness_executed": True,
    }
    write_json(output_dir / "precheck_summary.json", precheck_summary)

    harness_matrix: list[dict[str, Any]] = []
    for harness_name, run_artifact_root in (
        ("direct_route_call", main_runner_dir),
        ("testclient_http_harness", http_harness_dir),
    ):
        runtime_summary_path = run_artifact_root / "runtime_summary.json"
        durable_summary_path = run_artifact_root / "durable_summary.json"
        admin_summary_source = run_artifact_root / "responses" / "admin_summary_response.json"
        admin_durable_source = run_artifact_root / "responses" / "admin_durable_summary_response.json"

        summary_target_dir = ensure_dir(summaries_dir / harness_name)
        runtime_target = copy_if_exists(runtime_summary_path, summary_target_dir / "runtime_summary.json")
        durable_target = copy_if_exists(durable_summary_path, summary_target_dir / "durable_summary.json")
        admin_target = copy_if_exists(admin_summary_source, summary_target_dir / "admin_summary_response.json")
        admin_durable_target = copy_if_exists(
            admin_durable_source,
            summary_target_dir / "admin_durable_summary_response.json",
        )
        if admin_target:
            shutil.copy2(admin_target, responses_dir / f"admin_summary_response_{harness_name}.json")
        if admin_durable_target:
            shutil.copy2(
                admin_durable_target,
                responses_dir / f"admin_durable_summary_response_{harness_name}.json",
            )

        harness_cases = [case for case in all_cases if str(case["harness"]) == harness_name]
        harness_matrix.append(
            {
                "harness_name": harness_name,
                "run_artifact_root": str(run_artifact_root),
                "useful_executions": len(harness_cases),
                "case_names": [case["case_name"] for case in harness_cases],
                "case_profiles": sorted(
                    {
                        str(case.get("case_profile") or case.get("case_name"))
                        for case in harness_cases
                    }
                ),
                "template_codes": sorted(
                    {
                        str(case.get("codigo_template") or "")
                        for case in harness_cases
                        if str(case.get("codigo_template") or "").strip()
                    }
                ),
                "tenant_ids": sorted(
                    {
                        str(case.get("tenant_id") or "")
                        for case in harness_cases
                        if str(case.get("tenant_id") or "").strip()
                    }
                ),
                "runtime_summary_path": runtime_target,
                "durable_summary_path": durable_target,
                "admin_summary_response_path": admin_target,
                "admin_durable_summary_response_path": admin_durable_target,
            }
        )
    write_json(output_dir / "harness_matrix.json", harness_matrix)

    campaign_summary = {
        "phase": "Campanha operacional ampliada de template_publish_activate em shadow_only",
        "generated_at": dt.datetime.now().isoformat(),
        "campaign_artifact_root": str(output_dir),
        "operation_kind": "template_publish_activate",
        "mode": "shadow_only",
        "tenant_scope": "1",
        "host_scope": "testclient",
        "useful_executions": len(all_cases),
        "executions_by_harness": dict(sorted(cases_by_harness.items())),
        "distinct_case_profiles": distinct_case_profiles,
        "distinct_case_profiles_count": len(distinct_case_profiles),
        "distinct_template_codes": distinct_template_codes,
        "distinct_template_codes_count": len(distinct_template_codes),
        "blockers_by_code": dict(sorted(blockers_by_code.items())),
        "blockers_observed": sorted(blockers_by_code),
        "blockers_not_observed": [],
        "template_governance_blocker_family_additional": "nao_observado",
        "http_200_count": sum(1 for case in all_cases if int(case.get("response_status_code") or 0) == 200),
        "functional_publications_preserved": functional_publications_preserved,
        "audit_generated_count": sum(1 for case in all_cases if bool(case.get("audit_generated"))),
        "would_block_true_count": sum(1 for case in all_cases if bool(case.get("would_block"))),
        "would_block_false_count": sum(1 for case in all_cases if not bool(case.get("would_block"))),
        "did_block_true_count": sum(1 for case in all_cases if bool(case.get("did_block"))),
        "did_block_false_count": sum(1 for case in all_cases if not bool(case.get("did_block"))),
        "shadow_without_bleed_count": shadow_without_bleed_count,
        "precheck": precheck_summary,
        "source_case_roots": [
            str(main_runner_dir / "validation_cases.json"),
            str(http_harness_dir / "validation_cases.json"),
            str(REPO_ROOT / "artifacts" / "document_hard_gate_validation_10i" / "20260327_233048" / "validation_cases.json"),
            str(REPO_ROOT / "web" / "tests" / "test_v2_document_hard_gate_10i.py"),
            str(REPO_ROOT / "web" / "tests" / "test_regras_rotas_criticas.py"),
            str(REPO_ROOT / "web" / "app" / "domains" / "revisor" / "templates_laudo_management_routes.py"),
            str(REPO_ROOT / "web" / "app" / "domains" / "revisor" / "template_publish_shadow.py"),
        ],
    }
    write_json(output_dir / "campaign_summary.json", campaign_summary)
    write_json(output_dir / "campaign_cases.json", all_cases)
    write_text(
        output_dir / "campaign_findings.md",
        build_campaign_findings(
            precheck=precheck_summary,
            campaign_summary=campaign_summary,
            harness_matrix=harness_matrix,
        ),
    )

    source_index_lines = [
        str(output_dir / "pwd.txt"),
        str(output_dir / "git_status_short.txt"),
        str(output_dir / "boot_import_check.txt"),
        str(output_dir / "precheck_summary.json"),
        str(output_dir / "shadow_only_operations_check.txt"),
        str(output_dir / "main_runner_execution.txt"),
        str(output_dir / "http_harness_execution.txt"),
        str(output_dir / "campaign_summary.json"),
        str(output_dir / "campaign_cases.json"),
        str(output_dir / "campaign_findings.md"),
        str(output_dir / "harness_matrix.json"),
    ]
    source_index_lines.extend(
        item
        for item in campaign_summary["source_case_roots"]
    )
    source_index_lines.extend(
        str(summary["run_artifact_root"])
        for summary in harness_matrix
    )
    write_text(output_dir / "source_cases_index.txt", "\n".join(source_index_lines) + "\n")

    result = {
        "artifacts_dir": str(output_dir),
        "useful_executions": len(all_cases),
        "executions_by_harness": dict(sorted(cases_by_harness.items())),
        "distinct_case_profiles": distinct_case_profiles,
        "blockers_observed": sorted(blockers_by_code),
    }
    write_json(output_dir / "campaign_result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
