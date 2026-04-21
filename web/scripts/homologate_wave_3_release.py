from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WEB_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_ROOT = WEB_ROOT / ".test-artifacts" / "homologacao" / "wave_3"
LATEST_JSON_PATH = ARTIFACTS_ROOT / "latest.json"
LATEST_MD_PATH = ARTIFACTS_ROOT / "latest.md"
WAVE_3_SCOPED_FAMILIES: tuple[str, ...] = (
    "nr01_gro_pgr",
    "nr01_ordem_servico_sst",
    "nr04_diagnostico_sesmt",
    "nr05_implantacao_cipa",
    "nr05_auditoria_cipa",
    "nr06_gestao_epi",
    "nr07_pcmso",
    "nr08_inspecao_edificacao_industrial",
    "nr09_avaliacao_exposicoes_ocupacionais",
    "nr11_inspecao_movimentacao_armazenagem",
    "nr11_inspecao_equipamento_icamento",
    "nr14_inspecao_forno_industrial",
    "nr15_laudo_insalubridade",
    "nr16_laudo_periculosidade",
    "nr17_analise_ergonomica_trabalho",
    "nr17_checklist_ergonomia",
    "nr19_inspecao_area_explosivos",
    "nr21_condicoes_trabalho_ceu_aberto",
    "nr23_inspecao_protecao_incendios",
    "nr24_condicoes_sanitarias_conforto",
    "nr25_gestao_residuos_industriais",
    "nr26_sinalizacao_seguranca",
)
WAVE_3_PENDING_FAMILIES: tuple[str, ...] = ()
WAVE_3_ROUTE_GATE_TESTS: tuple[str, ...] = ()

if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from scripts.linux_cli import resolve_python_executable  # noqa: E402


@dataclass(frozen=True)
class ReleaseStep:
    key: str
    label: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class ReleaseStepResult:
    key: str
    label: str
    ok: bool
    returncode: int
    duration_seconds: float
    command: tuple[str, ...]
    stdout_log_path: str
    stderr_log_path: str
    stdout_tail: str
    stderr_tail: str


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_wave_3_release_steps(*, python_executable: str, skip_tests: bool, skip_provisioning: bool) -> list[ReleaseStep]:
    steps: list[ReleaseStep] = []
    if not skip_tests:
        steps.extend(
            [
                ReleaseStep(
                    key="runtime_unit",
                    label="Runtime canônico por família da onda 3",
                    command=(python_executable, "-m", "pytest", "tests/test_catalog_wave3_runtime.py", "-q"),
                ),
                ReleaseStep(
                    key="fixtures_regression",
                    label="Regressão por fixtures oficiais da onda 3",
                    command=(python_executable, "-m", "pytest", "tests/test_catalog_wave3_fixtures.py", "-q"),
                ),
                ReleaseStep(
                    key="pdf_smoke",
                    label="Smoke de emissão PDF por fixture oficial da onda 3",
                    command=(python_executable, "-m", "pytest", "tests/test_catalog_wave3_pdf_smoke.py", "-q"),
                ),
                ReleaseStep(
                    key="route_gate",
                    label="Gate crítico de rotas e finalização da onda 3",
                    command=(python_executable, "-m", "pytest", "tests/test_catalog_wave3_routes.py", "-q"),
                ),
            ]
        )
    if not skip_provisioning:
        steps.append(
            ReleaseStep(
                key="catalog_homologation",
                label="Homologação operacional da onda 3 no tenant piloto",
                command=(python_executable, "scripts/homologate_wave_3_core_templates.py"),
            )
        )
    return steps


def _tail(text: str, *, limit: int = 14) -> str:
    lines = [line for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-limit:])


def _write_log(path: Path, content: str) -> str:
    path.write_text(content or "", encoding="utf-8")
    return str(path)


def _run_step(step: ReleaseStep, *, index: int, run_dir: Path) -> ReleaseStepResult:
    started = time.perf_counter()
    completed = subprocess.run(
        list(step.command),
        cwd=WEB_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    duration = time.perf_counter() - started
    stdout_path = run_dir / f"{index:02d}_{step.key}.stdout.log"
    stderr_path = run_dir / f"{index:02d}_{step.key}.stderr.log"
    stdout_log_path = _write_log(stdout_path, completed.stdout)
    stderr_log_path = _write_log(stderr_path, completed.stderr)
    return ReleaseStepResult(
        key=step.key,
        label=step.label,
        ok=completed.returncode == 0,
        returncode=int(completed.returncode),
        duration_seconds=round(duration, 3),
        command=step.command,
        stdout_log_path=stdout_log_path,
        stderr_log_path=stderr_log_path,
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )


def _parse_json_from_log(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def build_wave_3_release_markdown(*, report: dict[str, Any]) -> str:
    lines = [
        "# Onda 3: Homologacao Completa",
        "",
        f"- gerado em: `{report['finished_at']}`",
        f"- status final: `{'ok' if report['ok'] else 'falha'}`",
        f"- familias homologadas no gate operacional: `{report['familias_homologadas_no_gate']}`",
        "",
        "## Escopo",
        "",
        f"- familias cobertas ponta a ponta: `{', '.join(report['wave_3_scoped_families'])}`",
    ]
    pending_families = report.get("wave_3_pending_families") or []
    if pending_families:
        lines.append(f"- familias ainda fora deste gate por falta de cobertura equivalente de finalizacao/runtime: `{', '.join(pending_families)}`")
    lines.extend(
        [
            f"- artefato principal de homologacao profissional: `{report['catalog_doc_path']}`"
            if report.get("catalog_doc_path")
            else "- artefato principal de homologacao profissional: `nao gerado`",
            f"- relatorio json desta rodada: `{report['report_json_path']}`",
            f"- relatorio markdown desta rodada: `{report['report_md_path']}`",
            "",
            "## Etapas",
            "",
            "| Etapa | Status | Duracao (s) |",
            "| --- | --- | --- |",
        ]
    )
    for step in report.get("steps") or []:
        lines.append(f"| `{step['label']}` | `{'ok' if step['ok'] else 'falha'}` | `{step['duration_seconds']}` |")

    homologation_summary = report.get("homologation_summary") or {}
    if homologation_summary:
        lines.extend(
            [
                "",
                "## Resumo operacional",
                "",
                f"- familias homologadas: `{homologation_summary.get('familias_homologadas', 0)}`",
                f"- familias ativas: `{homologation_summary.get('familias_ativas', 0)}`",
                f"- demos emitidas: `{homologation_summary.get('demos_emitidas', 0)}`",
                f"- documento gerado: `{homologation_summary.get('doc_saida', '')}`",
            ]
        )

    lines.extend(["", "## Logs", ""])
    for step in report.get("steps") or []:
        lines.extend(
            [
                f"### {step['label']}",
                "",
                f"- comando: `{' '.join(step['command'])}`",
                f"- stdout: `{step['stdout_log_path']}`",
                f"- stderr: `{step['stderr_log_path']}`",
            ]
        )
        if step.get("stdout_tail"):
            lines.extend(["", "```text", step["stdout_tail"], "```"])
        if step.get("stderr_tail"):
            lines.extend(["", "```text", step["stderr_tail"], "```"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa a homologacao completa da onda 3 com gate e relatorio.")
    parser.add_argument("--skip-tests", action="store_true", help="Pula o gate de testes.")
    parser.add_argument("--skip-provisioning", action="store_true", help="Pula a homologacao operacional no tenant piloto.")
    parser.add_argument(
        "--output-root",
        default=str(ARTIFACTS_ROOT),
        help="Diretorio raiz para relatórios e logs.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    python_executable = resolve_python_executable()
    output_root = _ensure_directory(Path(args.output_root).resolve())
    run_dir = _ensure_directory(output_root / _timestamp_slug())
    report_json_path = run_dir / "report.json"
    report_md_path = run_dir / "report.md"
    started_at = datetime.now(timezone.utc).isoformat()

    steps = build_wave_3_release_steps(
        python_executable=python_executable,
        skip_tests=bool(args.skip_tests),
        skip_provisioning=bool(args.skip_provisioning),
    )

    results: list[ReleaseStepResult] = []
    for index, step in enumerate(steps, start=1):
        result = _run_step(step, index=index, run_dir=run_dir)
        results.append(result)
        if not result.ok:
            break

    homologation_summary: dict[str, Any] | None = None
    catalog_doc_path = ""
    for result in results:
        if result.key != "catalog_homologation" or not result.ok:
            continue
        parsed = _parse_json_from_log(Path(result.stdout_log_path))
        if parsed:
            homologation_summary = parsed
            catalog_doc_path = str(parsed.get("doc_saida") or "")
        break

    finished_at = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "started_at": started_at,
        "finished_at": finished_at,
        "ok": bool(results) and all(item.ok for item in results) or not steps,
        "familias_homologadas_no_gate": len(WAVE_3_SCOPED_FAMILIES),
        "wave_3_scoped_families": list(WAVE_3_SCOPED_FAMILIES),
        "wave_3_pending_families": list(WAVE_3_PENDING_FAMILIES),
        "catalog_doc_path": catalog_doc_path,
        "report_json_path": str(report_json_path),
        "report_md_path": str(report_md_path),
        "homologation_summary": homologation_summary,
        "steps": [asdict(item) for item in results],
    }
    report_md = build_wave_3_release_markdown(report=report)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_md_path.write_text(report_md, encoding="utf-8")
    _ensure_directory(LATEST_JSON_PATH.parent)
    LATEST_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LATEST_MD_PATH.write_text(report_md, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
