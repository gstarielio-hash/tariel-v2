#!/usr/bin/env python3
"""Runner local de QA documental/PDF.

Objetivo:
- agrupar os checks mais úteis do pipeline documental em um comando só;
- registrar disponibilidade de ferramentas de inspeção PDF;
- opcionalmente inspecionar PDFs emitidos localmente com pdfinfo/pdftotext/qpdf;
- consolidar evidências em artifacts para depuração rápida.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "document_pdf_qa"
WEB_PYTHON = (
    WEB_ROOT / ".venv-linux" / "bin" / "python"
    if (WEB_ROOT / ".venv-linux" / "bin" / "python").exists()
    else pathlib.Path(sys.executable)
)

SYSTEM_PACKAGE_HINTS = {
    "qpdf": "sudo apt install qpdf",
    "pdfinfo": "sudo apt install poppler-utils",
    "pdftotext": "sudo apt install poppler-utils",
    "diffpdf": "sudo apt install diffpdf",
    "magick": "sudo apt install imagemagick",
}

BANNED_TEXT_MARKERS = (
    "template tecnico tariel.ia",
    "preencher automaticamente",
    "family key",
    "scope mismatch",
)


@dataclass
class CommandSpec:
    name: str
    command: list[str]
    cwd: pathlib.Path
    category: str
    targets: list[str] = field(default_factory=list)


@dataclass
class CommandResult:
    name: str
    category: str
    command: list[str]
    cwd: str
    returncode: int
    started_at: str
    finished_at: str
    log_path: str
    targets: list[str] = field(default_factory=list)


@dataclass
class PdfProbeResult:
    pdf_path: str
    status: str
    file_size_bytes: int
    pages: int | None
    text_length: int | None
    banned_markers_found: list[str] = field(default_factory=list)
    checks: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)


def now_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_json(path: pathlib.Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def relative_to_repo(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run_command(spec: CommandSpec, *, artifacts_dir: pathlib.Path) -> CommandResult:
    logs_dir = ensure_dir(artifacts_dir / "logs")
    started_at = dt.datetime.now().isoformat()
    completed = subprocess.run(
        spec.command,
        cwd=str(spec.cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    finished_at = dt.datetime.now().isoformat()
    log_path = logs_dir / f"{spec.name}.txt"
    write_text(
        log_path,
        "\n".join(
            [
                f"$ {' '.join(spec.command)}",
                f"[cwd] {spec.cwd}",
                f"[category] {spec.category}",
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
    return CommandResult(
        name=spec.name,
        category=spec.category,
        command=spec.command,
        cwd=str(spec.cwd),
        returncode=completed.returncode,
        started_at=started_at,
        finished_at=finished_at,
        log_path=relative_to_repo(log_path),
        targets=list(spec.targets),
    )


def available_tools() -> dict[str, str | None]:
    imagemagick_path = shutil.which("magick") or shutil.which("compare") or shutil.which("convert")
    return {
        "pdfinfo": shutil.which("pdfinfo"),
        "pdftotext": shutil.which("pdftotext"),
        "qpdf": shutil.which("qpdf"),
        "diffpdf": shutil.which("diffpdf"),
        "magick": imagemagick_path,
    }


def build_command_specs(profile: str) -> list[CommandSpec]:
    specs = [
        CommandSpec(
            name="document_core_unit",
            category="pytest",
            cwd=WEB_ROOT,
            command=[
                str(WEB_PYTHON),
                "-m",
                "pytest",
                "-q",
                "tests/test_catalog_nr12_overlay.py",
                "tests/test_catalog_pdf_templates.py",
                "-k",
                (
                    "snapshot or field_mapping or rich_runtime_preview "
                    "or nr12_overlay or nr12_comparative_visual_qa_for_promoted_families "
                    "or nr12_risk_visual_qa_materializes_primary_matrix_from_payload"
                ),
                "tests/test_catalog_pdf_visual_qa.py",
            ],
            targets=[
                "tests/test_catalog_nr12_overlay.py",
                "tests/test_catalog_pdf_templates.py",
                "tests/test_catalog_pdf_visual_qa.py",
            ],
        ),
        CommandSpec(
            name="document_preview_routes",
            category="pytest",
            cwd=WEB_ROOT,
            command=[
                str(WEB_PYTHON),
                "-m",
                "pytest",
                "-q",
                "tests/test_v2_document_soft_gate_integration.py",
                "tests/test_admin_client_routes.py",
                "-k",
                (
                    "admin_catalogo_preview_pdf_retorna_documento_canonico "
                    "or preview_legado_repassa_mapeamento_resolvido "
                    "or promove_template_legado_fraco_para_preview_editor_rico "
                    "or rota_pdf_com_soft_gate_preserva_retorno_publico_e_registra_decisao"
                ),
            ],
            targets=[
                "tests/test_v2_document_soft_gate_integration.py",
                "tests/test_admin_client_routes.py",
            ],
        ),
        CommandSpec(
            name="document_preview_critical_routes",
            category="pytest",
            cwd=WEB_ROOT,
            command=[
                str(WEB_PYTHON),
                "-m",
                "pytest",
                "-q",
                "tests/test_regras_rotas_criticas.py",
                "-k",
                (
                    "test_api_gerar_pdf_prioriza_template_ativo_especifico_da_familia_catalogada "
                    "or test_api_gerar_pdf_fallback_legacy_quando_nao_ha_template_ativo "
                    "or test_api_gerar_pdf_fallback_legacy_quando_template_ativo_invalido"
                ),
            ],
            targets=["tests/test_regras_rotas_criticas.py"],
        ),
    ]
    if profile == "full":
        specs.extend(
            [
                CommandSpec(
                    name="document_catalog_templates_full",
                    category="pytest",
                    cwd=WEB_ROOT,
                    command=[
                        str(WEB_PYTHON),
                        "-m",
                        "pytest",
                        "-q",
                        "tests/test_catalog_pdf_templates.py",
                    ],
                    targets=["tests/test_catalog_pdf_templates.py"],
                ),
                CommandSpec(
                    name="document_v2_contracts",
                    category="pytest",
                    cwd=WEB_ROOT,
                    command=[
                        str(WEB_PYTHON),
                        "-m",
                        "pytest",
                        "-q",
                        "tests/test_v2_document_facade.py",
                        "tests/test_v2_document_shadow.py",
                        "tests/test_v2_document_soft_gate.py",
                    ],
                    targets=[
                        "tests/test_v2_document_facade.py",
                        "tests/test_v2_document_shadow.py",
                        "tests/test_v2_document_soft_gate.py",
                    ],
                ),
                CommandSpec(
                    name="document_phase_acceptance",
                    category="runner",
                    cwd=REPO_ROOT,
                    command=["python3", "scripts/run_document_phase_acceptance.py"],
                    targets=["scripts/run_document_phase_acceptance.py"],
                ),
                CommandSpec(
                    name="document_pdf_smoke_waves",
                    category="pytest",
                    cwd=WEB_ROOT,
                    command=[
                        str(WEB_PYTHON),
                        "-m",
                        "pytest",
                        "-q",
                        "tests/test_catalog_wave1_pdf_smoke.py",
                        "tests/test_catalog_wave2_pdf_smoke.py",
                        "tests/test_catalog_wave3_pdf_smoke.py",
                    ],
                    targets=[
                        "tests/test_catalog_wave1_pdf_smoke.py",
                        "tests/test_catalog_wave2_pdf_smoke.py",
                        "tests/test_catalog_wave3_pdf_smoke.py",
                    ],
                ),
            ]
        )
    return specs


def run_simple_command(
    *,
    command: list[str],
    cwd: pathlib.Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def parse_pages_from_pdfinfo(text: str) -> int | None:
    match = re.search(r"^Pages:\s+(\d+)\s*$", str(text or ""), flags=re.MULTILINE)
    if match is None:
        return None
    return int(match.group(1))


def probe_pdf(
    *,
    pdf_path: pathlib.Path,
    artifacts_dir: pathlib.Path,
    tools: dict[str, str | None],
) -> PdfProbeResult:
    probe_dir = ensure_dir(artifacts_dir / "pdf_probes")
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", pdf_path.stem)[:80] or "pdf"
    result = PdfProbeResult(
        pdf_path=str(pdf_path),
        status="ok",
        file_size_bytes=pdf_path.stat().st_size if pdf_path.exists() else 0,
        pages=None,
        text_length=None,
    )

    if not pdf_path.exists():
        result.status = "failed"
        result.warnings.append("Arquivo PDF não encontrado.")
        return result

    if result.file_size_bytes <= 0:
        result.status = "failed"
        result.warnings.append("Arquivo PDF vazio.")
        return result

    if tools.get("pdfinfo"):
        completed = run_simple_command(command=[str(tools["pdfinfo"]), str(pdf_path)], cwd=REPO_ROOT)
        info_log = probe_dir / f"{stem}.pdfinfo.txt"
        write_text(info_log, completed.stdout + ("\n" + completed.stderr if completed.stderr else ""))
        result.artifacts["pdfinfo"] = relative_to_repo(info_log)
        if completed.returncode == 0:
            result.checks["pdfinfo"] = "ok"
            result.pages = parse_pages_from_pdfinfo(completed.stdout)
            if result.pages is not None and result.pages <= 0:
                result.status = "failed"
                result.warnings.append("pdfinfo reportou zero páginas.")
        else:
            result.checks["pdfinfo"] = "failed"
            result.status = "failed"
            result.warnings.append("pdfinfo falhou ao ler o arquivo.")
    else:
        result.checks["pdfinfo"] = "missing"

    if tools.get("pdftotext"):
        completed = run_simple_command(
            command=[str(tools["pdftotext"]), "-enc", "UTF-8", str(pdf_path), "-"],
            cwd=REPO_ROOT,
        )
        text_log = probe_dir / f"{stem}.pdftotext.txt"
        write_text(text_log, completed.stdout)
        result.artifacts["pdftotext"] = relative_to_repo(text_log)
        if completed.returncode == 0:
            extracted = completed.stdout
            result.checks["pdftotext"] = "ok"
            result.text_length = len(extracted.strip())
            lowered = extracted.casefold()
            banned_found = [marker for marker in BANNED_TEXT_MARKERS if marker in lowered]
            result.banned_markers_found = banned_found
            if banned_found:
                result.status = "failed"
                result.warnings.append("Marcadores internos/placeholder encontrados no texto extraído.")
            elif not extracted.strip():
                result.warnings.append("pdftotext não extraiu texto útil deste PDF.")
                if result.status == "ok":
                    result.status = "warning"
        else:
            result.checks["pdftotext"] = "failed"
            result.warnings.append("pdftotext falhou ao extrair texto.")
            if result.status == "ok":
                result.status = "warning"
    else:
        result.checks["pdftotext"] = "missing"

    if tools.get("qpdf"):
        completed = run_simple_command(command=[str(tools["qpdf"]), "--check", str(pdf_path)], cwd=REPO_ROOT)
        qpdf_log = probe_dir / f"{stem}.qpdf.txt"
        write_text(qpdf_log, completed.stdout + ("\n" + completed.stderr if completed.stderr else ""))
        result.artifacts["qpdf"] = relative_to_repo(qpdf_log)
        if completed.returncode == 0:
            result.checks["qpdf"] = "ok"
        else:
            result.checks["qpdf"] = "failed"
            result.status = "failed"
            result.warnings.append("qpdf --check encontrou problema estrutural no arquivo.")
    else:
        result.checks["qpdf"] = "missing"

    return result


def build_summary_payload(
    *,
    profile: str,
    tools: dict[str, str | None],
    command_results: list[CommandResult],
    pdf_results: list[PdfProbeResult],
) -> dict[str, Any]:
    command_failed = any(item.returncode != 0 for item in command_results)
    pdf_failed = any(item.status == "failed" for item in pdf_results)
    summary_status = "failed" if command_failed or pdf_failed else "ok"

    recommendations = []
    for tool_name, install_hint in SYSTEM_PACKAGE_HINTS.items():
        if not tools.get(tool_name):
            recommendations.append(
                {
                    "tool": tool_name,
                    "install_hint": install_hint,
                }
            )

    return {
        "status": summary_status,
        "profile": profile,
        "executed_at": dt.datetime.now().isoformat(),
        "tools": {
            key: {"available": bool(value), "path": value}
            for key, value in tools.items()
        },
        "commands": [asdict(item) for item in command_results],
        "pdf_probes": [asdict(item) for item in pdf_results],
        "recommendations": recommendations,
    }


def build_final_report(summary: dict[str, Any]) -> str:
    lines = [
        "# QA documental local",
        "",
        f"- status: {summary['status']}",
        f"- profile: {summary['profile']}",
        f"- executed_at: {summary['executed_at']}",
        "",
        "## Ferramentas",
    ]
    for tool_name, payload in summary["tools"].items():
        lines.append(
            f"- `{tool_name}`: {'ok' if payload['available'] else 'missing'}"
            + (f" (`{payload['path']}`)" if payload["path"] else "")
        )

    lines.extend(["", "## Commands"])
    for item in summary["commands"]:
        lines.append(f"- `{item['name']}`: returncode={item['returncode']}")
        lines.append(f"  command: {' '.join(item['command'])}")

    if summary["pdf_probes"]:
        lines.extend(["", "## PDF Probes"])
        for item in summary["pdf_probes"]:
            lines.append(
                f"- `{item['pdf_path']}`: status={item['status']} size={item['file_size_bytes']} pages={item['pages']} text_length={item['text_length']}"
            )
            if item["warnings"]:
                lines.append(f"  warnings: {' | '.join(item['warnings'])}")
            if item["banned_markers_found"]:
                lines.append(f"  banned_markers: {' | '.join(item['banned_markers_found'])}")

    if summary["recommendations"]:
        lines.extend(["", "## Instalação sugerida"])
        for item in summary["recommendations"]:
            lines.append(f"- `{item['tool']}`: `{item['install_hint']}`")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa QA documental/PDF local.")
    parser.add_argument(
        "--profile",
        choices=("quick", "full"),
        default="quick",
        help="Escolhe a profundidade da QA documental local.",
    )
    parser.add_argument(
        "--pdf",
        action="append",
        default=[],
        help="Caminho de PDF para inspeção adicional com pdfinfo/pdftotext/qpdf. Pode repetir.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifacts_dir = ensure_dir(ARTIFACTS_ROOT / now_slug())
    tools = available_tools()
    command_results = [run_command(spec, artifacts_dir=artifacts_dir) for spec in build_command_specs(args.profile)]

    pdf_results: list[PdfProbeResult] = []
    for raw_path in list(args.pdf or []):
        pdf_path = pathlib.Path(raw_path).expanduser().resolve()
        pdf_results.append(probe_pdf(pdf_path=pdf_path, artifacts_dir=artifacts_dir, tools=tools))

    summary = build_summary_payload(
        profile=args.profile,
        tools=tools,
        command_results=command_results,
        pdf_results=pdf_results,
    )
    write_json(artifacts_dir / "document_pdf_qa_summary.json", summary)
    write_text(artifacts_dir / "final_report.md", build_final_report(summary))
    print(str(artifacts_dir))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
