#!/usr/bin/env python3
"""Runner mestre de regressao operacional do produto.

Objetivo:
- executar suites locais criticas que cobrem criacao de contas, portais e emissao;
- opcionalmente executar a jornada online no ambiente hospedado;
- consolidar evidencias em artifacts;
- gerar um bug registry inicial para facilitar correcao por fila.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "full_regression_audit"
WEB_PYTHON = (
    WEB_ROOT / ".venv-linux" / "bin" / "python"
    if (WEB_ROOT / ".venv-linux" / "bin" / "python").exists()
    else pathlib.Path(sys.executable)
)
DEFAULT_BASE_URL = os.getenv("TARIEL_AUDIT_BASE_URL", "").strip()


@dataclass
class CommandSpec:
    name: str
    command: list[str]
    cwd: pathlib.Path
    category: str
    targets: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class CommandResult:
    name: str
    category: str
    command: list[str]
    cwd: str
    env_overrides: dict[str, str]
    returncode: int
    started_at: str
    finished_at: str
    log_path: str
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class BugEntry:
    bug_id: str
    title: str
    severity: str
    source: str
    status: str
    evidence: str
    details: str


def now_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def graphical_session_available() -> bool:
    return bool(os.getenv("DISPLAY", "").strip() or os.getenv("WAYLAND_DISPLAY", "").strip())


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
    env = os.environ.copy()
    env.update(spec.env)
    completed = subprocess.run(
        spec.command,
        cwd=str(spec.cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    finished_at = dt.datetime.now().isoformat()
    log_path = logs_dir / f"{spec.name}.txt"
    lines = [
        f"$ {' '.join(spec.command)}",
        f"[cwd] {spec.cwd}",
        f"[category] {spec.category}",
    ]
    if spec.env:
        lines.append(f"[env] {json.dumps(spec.env, ensure_ascii=False, sort_keys=True)}")
    lines.extend(
        [
            "",
            "[stdout]",
            completed.stdout.strip(),
            "",
            "[stderr]",
            completed.stderr.strip(),
            "",
            f"[returncode] {completed.returncode}",
        ]
    )
    write_text(log_path, "\n".join(lines).strip() + "\n")
    return CommandResult(
        name=spec.name,
        category=spec.category,
        command=spec.command,
        cwd=str(spec.cwd),
        env_overrides=dict(spec.env),
        returncode=completed.returncode,
        started_at=started_at,
        finished_at=finished_at,
        log_path=relative_to_repo(log_path),
    )


def warm_hosted_base_url(*, base_url: str, log_path: pathlib.Path, timeout_seconds: int = 120) -> bool:
    endpoints = (
        ("/health", "status"),
        ("/admin/login", 'name="email"'),
    )
    deadline = time.time() + timeout_seconds
    attempts: list[str] = []

    while time.time() < deadline:
        all_ready = True
        for suffix, marker in endpoints:
            target = f"{base_url.rstrip('/')}{suffix}"
            try:
                request = urllib.request.Request(
                    target,
                    headers={"User-Agent": "tariel-full-regression-audit/1.0"},
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    body = response.read(4096).decode("utf-8", errors="ignore")
                    status_code = int(getattr(response, "status", 0) or 0)
                ready = status_code < 500 and marker in body
                attempts.append(f"{target} -> status={status_code} ready={ready}")
                if not ready:
                    all_ready = False
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                attempts.append(f"{target} -> error={type(exc).__name__}: {exc}")
                all_ready = False
        if all_ready:
            write_text(log_path, "\n".join(attempts) + "\n")
            return True
        time.sleep(4)

    write_text(log_path, "\n".join(attempts) + "\n")
    return False


def should_retry_online(log_text: str) -> bool:
    normalized = str(log_text or "")
    return (
        "status of 503" in normalized
        or ('waiting for locator("input[name=\\"email\\"]")' in normalized and "/admin/login" in normalized)
        or 'waiting for locator("input[name=\\"email\\"]")' in normalized
    )


def latest_subdir(root: pathlib.Path) -> pathlib.Path | None:
    if not root.exists():
        return None
    subdirs = [item for item in root.iterdir() if item.is_dir()]
    if not subdirs:
        return None
    return sorted(subdirs)[-1]


def read_text_if_exists(path: pathlib.Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def infer_severity(text: str, *, fallback: str = "media") -> str:
    normalized = str(text or "").lower()
    high_markers = (
        "500",
        "erro ao emitir",
        "emissao",
        "pdf",
        "login",
        "403",
        "timeout",
        "nao apareceu",
        "não apareceu",
        "oficial",
        "hash",
        "verificacao publica",
        "verification",
        "traceback",
        "run error",
    )
    medium_markers = (
        "console",
        "csp",
        "sse",
        "visual",
        "overflow",
        "attachment",
        "anexo",
        "false positive",
    )
    if any(marker in normalized for marker in high_markers):
        return "alta"
    if any(marker in normalized for marker in medium_markers):
        return "media"
    return fallback


def extract_pytest_failures(log_text: str) -> list[tuple[str, str, str]]:
    issues: list[tuple[str, str, str]] = []
    pattern = re.compile(r"^(FAILED|ERROR)\s+([^\s]+)\s+-\s*(.+)$", re.MULTILINE)
    for level, test_id, message in pattern.findall(log_text):
        issues.append((level, test_id.strip(), message.strip()))
    return issues


def normalize_bug_title(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    return value[:240] or "Falha sem titulo"


def bugs_from_command_results(results: list[CommandResult]) -> list[BugEntry]:
    entries: list[BugEntry] = []
    counter = 1
    for result in results:
        if int(result.returncode) == 0:
            continue
        if result.name == "online_render_journey" and result.extras.get("online_report_json"):
            continue
        log_path = REPO_ROOT / result.log_path
        log_text = read_text_if_exists(log_path)
        pytest_failures = extract_pytest_failures(log_text)
        if pytest_failures:
            for _level, test_id, message in pytest_failures:
                entries.append(
                    BugEntry(
                        bug_id=f"BUG-{counter:03d}",
                        title=normalize_bug_title(f"{test_id}: {message}"),
                        severity=infer_severity(message),
                        source=result.name,
                        status="open",
                        evidence=result.log_path,
                        details=f"Falha capturada na suite `{result.name}`.",
                    )
                )
                counter += 1
            continue
        entries.append(
            BugEntry(
                bug_id=f"BUG-{counter:03d}",
                title=normalize_bug_title(f"Suite `{result.name}` falhou"),
                severity=infer_severity(log_text, fallback="alta"),
                source=result.name,
                status="open",
                evidence=result.log_path,
                details="Ver log completo da suite para stack trace, stdout e stderr.",
            )
        )
        counter += 1
    return entries


def bugs_from_online_report(
    payload: dict[str, Any] | None,
    *,
    source: str,
    evidence_path: str,
    starting_index: int,
) -> list[BugEntry]:
    if not payload:
        return []

    entries: list[BugEntry] = []
    counter = starting_index

    run_error = str(payload.get("run_error") or "").strip()
    if run_error:
        entries.append(
            BugEntry(
                bug_id=f"BUG-{counter:03d}",
                title=normalize_bug_title(f"Jornada online falhou: {run_error}"),
                severity="alta",
                source=source,
                status="open",
                evidence=evidence_path,
                details="O runner online terminou com erro antes de concluir toda a jornada.",
            )
        )
        counter += 1

    for item in list(payload.get("missing_items") or []):
        entries.append(
            BugEntry(
                bug_id=f"BUG-{counter:03d}",
                title=normalize_bug_title(str(item)),
                severity=infer_severity(str(item), fallback="alta"),
                source=source,
                status="open",
                evidence=evidence_path,
                details="Item marcado pelo runner online como faltante ou com falha funcional.",
            )
        )
        counter += 1

    for item in list(payload.get("false_positive_items") or []):
        entries.append(
            BugEntry(
                bug_id=f"BUG-{counter:03d}",
                title=normalize_bug_title(str(item)),
                severity=infer_severity(str(item), fallback="media"),
                source=source,
                status="open",
                evidence=evidence_path,
                details="Comportamento aparentemente bem-sucedido, mas inconsistente no resultado final.",
            )
        )
        counter += 1

    seen_console: set[str] = set()
    for item in list(payload.get("console_issues") or []) + list(payload.get("page_errors") or []):
        if not isinstance(item, dict):
            continue
        text = normalize_bug_title(item.get("text"))
        if not text or text in seen_console:
            continue
        seen_console.add(text)
        entries.append(
            BugEntry(
                bug_id=f"BUG-{counter:03d}",
                title=text,
                severity=infer_severity(text, fallback="baixa"),
                source=f"{source}/console",
                status="open",
                evidence=evidence_path,
                details=f"Console/page error registrado em `{item.get('page') or 'page'}`.",
            )
        )
        counter += 1

    return entries


def build_bug_registry_md(entries: list[BugEntry]) -> str:
    if not entries:
        return "# Bug Registry\n\nNenhum bug aberto foi registrado nesta rodada.\n"

    lines = [
        "# Bug Registry",
        "",
        "| ID | Severidade | Origem | Status | Titulo | Evidencia |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in entries:
        title = item.title.replace("|", "/")
        evidence = item.evidence.replace("|", "/")
        lines.append(
            f"| {item.bug_id} | {item.severity} | {item.source} | {item.status} | {title} | `{evidence}` |"
        )
    lines.extend(["", "## Detalhes"])
    for item in entries:
        lines.extend(
            [
                "",
                f"### {item.bug_id} - {item.title}",
                f"- severidade: {item.severity}",
                f"- origem: {item.source}",
                f"- status: {item.status}",
                f"- evidencia: `{item.evidence}`",
                f"- detalhes: {item.details}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def build_success_registry_md(
    *,
    results: list[CommandResult],
    online_report_payload: dict[str, Any] | None,
) -> str:
    lines = ["# Success Registry", ""]

    local_ok = [item for item in results if int(item.returncode) == 0]
    if local_ok:
        lines.extend(["## Suites Verdes"])
        for item in local_ok:
            lines.append(f"- `{item.name}` passou em `{item.category}`.")
        lines.append("")

    if online_report_payload:
        ok_items = list(online_report_payload.get("ok_items") or [])
        steps = list(online_report_payload.get("steps") or [])
        visual_notes = list(online_report_payload.get("visual_notes") or [])

        if ok_items:
            lines.extend(["## Acertos da Jornada Online"])
            for item in ok_items:
                lines.append(f"- {item}")
            lines.append("")

        if steps:
            lines.extend(["## Passos Registrados"])
            for step in steps:
                if not isinstance(step, dict):
                    continue
                status = str(step.get("status") or "").strip() or "unknown"
                details = str(step.get("details") or "").strip() or "sem detalhes"
                name = str(step.get("name") or "").strip() or "step"
                lines.append(f"- `{name}` [{status}]: {details}")
            lines.append("")

        if visual_notes:
            lines.extend(["## Observacoes Visuais"])
            for item in visual_notes:
                lines.append(f"- {item}")
            lines.append("")

    if len(lines) == 2:
        lines.append("Nenhum acerto adicional foi registrado nesta rodada.")
        lines.append("")
    return "\n".join(lines)


def build_summary_md(
    *,
    results: list[CommandResult],
    bug_entries: list[BugEntry],
    online_report_path: str | None,
    base_url: str | None,
    profile: str,
) -> str:
    status = "ok" if all(int(item.returncode) == 0 for item in results) else "failed"
    category_counts: dict[str, int] = {}
    for item in results:
        category_counts[item.category] = category_counts.get(item.category, 0) + 1
    lines = [
        "# Full Regression Audit",
        "",
        f"- status: {status}",
        f"- executed_at: {dt.datetime.now().isoformat()}",
        f"- profile: {profile}",
        f"- base_url: {base_url or 'local-only'}",
        f"- total_suites: {len(results)}",
        f"- bugs_abertos: {len(bug_entries)}",
    ]
    if online_report_path:
        lines.append(f"- online_report: `{online_report_path}`")
    lines.extend(["", "## Categorias"])
    for category, total in sorted(category_counts.items()):
        lines.append(f"- `{category}`: {total}")
    lines.extend(["", "## Suites"])
    for item in results:
        lines.extend(
            [
                f"- `{item.name}`: returncode={item.returncode}",
                f"  category: {item.category}",
                f"  log: `{item.log_path}`",
            ]
        )
    lines.extend(["", "## Proximo uso", "", "1. Abra `bug_registry.md`.", "2. Corrija por severidade.", "3. Rode o mesmo runner novamente para confirmar regressao zero.", ""])
    return "\n".join(lines)


def pytest_spec(
    *,
    name: str,
    category: str,
    targets: list[str],
    env: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
    cwd: pathlib.Path = WEB_ROOT,
) -> CommandSpec:
    command = [str(WEB_PYTHON), "-m", "pytest", "-q", "-rfEX", *targets]
    if extra_args:
        command.extend(extra_args)
    return CommandSpec(
        name=name,
        category=category,
        cwd=cwd,
        env=env or {},
        targets=list(targets),
        command=command,
    )


def python_script_spec(
    *,
    name: str,
    category: str,
    script_path: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    cwd: pathlib.Path = REPO_ROOT,
) -> CommandSpec:
    command = [sys.executable, script_path]
    if args:
        command.extend(args)
    return CommandSpec(
        name=name,
        category=category,
        cwd=cwd,
        env=env or {},
        targets=[script_path],
        command=command,
    )


def npm_spec(
    *,
    name: str,
    category: str,
    npm_args: list[str],
    cwd: pathlib.Path = REPO_ROOT / "android",
    env: dict[str, str] | None = None,
) -> CommandSpec:
    return CommandSpec(
        name=name,
        category=category,
        cwd=cwd,
        env=env or {},
        targets=list(npm_args),
        command=["npm", *npm_args],
    )


def dedupe_targets(targets: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in targets:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def discover_backend_test_targets() -> list[str]:
    targets: list[str] = []
    tests_root = WEB_ROOT / "tests"
    for path in sorted(tests_root.rglob("test_*.py")):
        relative = path.relative_to(WEB_ROOT).as_posix()
        if relative.startswith("tests/e2e/") or relative.startswith("tests/load/"):
            continue
        targets.append(relative)
    return dedupe_targets(targets)


BACKEND_GROUPS: dict[str, list[str]] = {
    "portal_backend_critical": [
        "tests/test_portais_acesso_critico.py",
        "tests/test_session_auth_audit_matrix.py",
        "tests/test_cliente_portal_critico.py",
        "tests/test_admin_client_routes.py",
    ],
    "inspetor_backend_critical": [
        "tests/test_smoke.py",
        "tests/test_regras_rotas_criticas.py",
        "tests/test_inspetor_comandos_dominio.py",
        "tests/test_inspetor_confianca_dominio.py",
        "tests/test_inspector_active_report_authority.py",
        "tests/test_operational_memory.py",
    ],
    "mesa_backend_critical": [
        "tests/test_reviewer_panel_boot_hotfix.py",
        "tests/test_revisor_command_handlers.py",
        "tests/test_revisor_command_side_effects.py",
        "tests/test_revisor_mesa_api_side_effects.py",
        "tests/test_revisor_realtime.py",
        "tests/test_public_verification.py",
        "tests/test_official_issue_package.py",
        "tests/test_template_publish_contract.py",
    ],
    "document_catalog_backend": [
        "tests/test_catalog_document_contract.py",
        "tests/test_catalog_pdf_templates.py",
        "tests/test_tenant_report_catalog.py",
        "tests/test_v2_document_facade.py",
        "tests/test_v2_reviewdesk_projection.py",
        "tests/test_v2_review_queue_projection.py",
    ],
    "release_catalog_backend": [
        "tests/test_catalog_nr13_overlay.py",
        "tests/test_catalog_nr35_overlay.py",
        "tests/test_catalog_wave1_fixtures.py",
        "tests/test_catalog_wave1_pdf_smoke.py",
        "tests/test_catalog_wave2_fixtures.py",
        "tests/test_catalog_wave2_pdf_smoke.py",
        "tests/test_catalog_wave3_fixtures.py",
        "tests/test_catalog_wave3_pdf_smoke.py",
        "tests/test_catalog_wave3_routes.py",
        "tests/test_catalog_wave3_runtime.py",
        "tests/test_catalog_wave4_governance.py",
        "tests/test_homologate_wave_1_release.py",
        "tests/test_homologate_wave_2_release.py",
        "tests/test_homologate_wave_3_release.py",
        "tests/test_homologate_wave_4_release.py",
        "tests/test_master_template_library.py",
        "tests/test_material_reference_packages.py",
        "tests/test_reference_package_workspace.py",
        "tests/test_report_pack_rollout_metrics.py",
        "tests/test_revisor_templates_diff_critico.py",
        "tests/test_semantic_report_pack_catalog_fallback.py",
        "tests/test_semantic_report_pack_cbmgo_autonomy.py",
        "tests/test_semantic_report_pack_nr35_autonomy.py",
        "tests/test_template_editor_word_placeholders.py",
        "tests/test_templates_ia_cbmgo.py",
        "tests/test_templates_ia_nr35.py",
    ],
    "account_policy_backend": [
        "tests/test_admin_services.py",
        "tests/test_app_boot_query_reduction.py",
        "tests/test_chat_notifications.py",
        "tests/test_chat_runtime_support.py",
        "tests/test_cliente_route_support.py",
        "tests/test_core_support.py",
        "tests/test_legacy_wrappers.py",
        "tests/test_multiportal_bootstrap_contracts.py",
        "tests/test_password_hashing.py",
        "tests/test_perf_support.py",
        "tests/test_post_plan_benchmarks.py",
        "tests/test_production_ops_summary.py",
        "tests/test_rbac_action_matrix.py",
        "tests/test_tenant_access.py",
        "tests/test_tenant_boundary_matrix.py",
        "tests/test_transaction_contract.py",
        "tests/test_uploads_cleanup.py",
    ],
    "inspection_entry_backend": [
        "tests/test_inspection_entry_mode_phase_a.py",
        "tests/test_inspection_entry_mode_phase_b.py",
        "tests/test_inspection_entry_mode_phase_c_web.py",
        "tests/test_inspection_entry_mode_phase_d_mobile.py",
        "tests/test_mesa_mobile_sync.py",
    ],
    "v2_core_backend": [
        "tests/test_v2_billing_metering.py",
        "tests/test_v2_case_core_acl.py",
        "tests/test_v2_document_hard_gate.py",
        "tests/test_v2_document_hard_gate_10c.py",
        "tests/test_v2_document_hard_gate_10d.py",
        "tests/test_v2_document_hard_gate_10f.py",
        "tests/test_v2_document_hard_gate_10g.py",
        "tests/test_v2_document_hard_gate_10i.py",
        "tests/test_v2_document_hard_gate_enforce.py",
        "tests/test_v2_document_hard_gate_summary.py",
        "tests/test_v2_document_operations_summary.py",
        "tests/test_v2_document_shadow.py",
        "tests/test_v2_document_soft_gate.py",
        "tests/test_v2_document_soft_gate_integration.py",
        "tests/test_v2_document_soft_gate_summary.py",
        "tests/test_v2_envelopes.py",
        "tests/test_v2_inspector_document_projection.py",
        "tests/test_v2_inspector_projection.py",
        "tests/test_v2_platform_admin_projection.py",
        "tests/test_v2_policy_engine.py",
        "tests/test_v2_projection_shadow.py",
        "tests/test_v2_provenance.py",
        "tests/test_v2_technical_case_snapshot.py",
        "tests/test_v2_tenant_admin_projection.py",
    ],
    "v2_android_backend": [
        "tests/test_v2_android_ack_accounting.py",
        "tests/test_v2_android_case_adapter.py",
        "tests/test_v2_android_case_feed_adapter.py",
        "tests/test_v2_android_case_thread_adapter.py",
        "tests/test_v2_android_human_ack.py",
        "tests/test_v2_android_human_coverage.py",
        "tests/test_v2_android_operator_run.py",
        "tests/test_v2_android_operator_run_summary.py",
        "tests/test_v2_android_organic_coverage.py",
        "tests/test_v2_android_organic_session_signal.py",
        "tests/test_v2_android_organic_validation.py",
        "tests/test_v2_android_organic_validation_summary.py",
        "tests/test_v2_android_pilot_evaluation.py",
        "tests/test_v2_android_pilot_probe.py",
        "tests/test_v2_android_probe_targets.py",
        "tests/test_v2_android_public_contract.py",
        "tests/test_v2_android_request_trace_gap.py",
        "tests/test_v2_android_rollout.py",
        "tests/test_v2_android_rollout_metrics.py",
        "tests/test_v2_android_rollout_pilot.py",
        "tests/test_v2_android_rollout_promotion.py",
        "tests/test_v2_android_rollout_state.py",
        "tests/test_v2_android_surface_served_accounting.py",
    ],
}

BACKEND_PROFILE_GROUPS: dict[str, list[str]] = {
    "critical": [
        "portal_backend_critical",
        "inspetor_backend_critical",
        "mesa_backend_critical",
        "document_catalog_backend",
    ],
    "broad": [
        "portal_backend_critical",
        "inspetor_backend_critical",
        "mesa_backend_critical",
        "document_catalog_backend",
        "release_catalog_backend",
        "account_policy_backend",
        "inspection_entry_backend",
        "v2_core_backend",
        "v2_android_backend",
    ],
    "exhaustive": [
        "portal_backend_critical",
        "inspetor_backend_critical",
        "mesa_backend_critical",
        "document_catalog_backend",
        "release_catalog_backend",
        "account_policy_backend",
        "inspection_entry_backend",
        "v2_core_backend",
        "v2_android_backend",
    ],
}

E2E_PROFILE_SPECS: dict[str, list[tuple[str, list[str]]]] = {
    "critical": [
        (
            "local_e2e_multiportal_critical",
            [
                "tests/e2e/test_portais_playwright.py::test_e2e_admin_ceo_cria_empresa_ilimitada_e_admin_cliente_consume_mesmo_tenant",
                "tests/e2e/test_portais_playwright.py::test_e2e_fluxo_bilateral_inspetor_e_revisor_no_canal_mesa",
                "tests/e2e/test_portais_playwright.py::test_e2e_revisor_exibe_painel_operacional_da_mesa",
                "tests/e2e/test_portais_playwright.py::test_e2e_revisor_exporta_pacote_tecnico_da_mesa",
                "tests/e2e/test_portais_playwright.py::test_e2e_inspetor_anexa_arquivo_no_widget_mesa_e_revisor_visualiza",
                "tests/e2e/test_portais_playwright.py::test_e2e_revisor_anexa_arquivo_e_inspetor_visualiza_no_widget_mesa",
                "tests/e2e/test_inspector_active_report_authority_playwright.py::test_e2e_query_laudo_e_home_forcada_preservam_contexto_autoritativo",
            ],
        ),
    ],
    "broad": [
        (
            "local_e2e_portais_broad",
            [
                "tests/e2e/test_portais_playwright.py",
                "tests/e2e/test_inspector_active_report_authority_playwright.py",
                "tests/e2e/test_inspetor_visual_playwright.py",
            ],
        ),
    ],
    "exhaustive": [
        (
            "local_e2e_portais_exhaustive",
            [
                "tests/e2e/test_portais_playwright.py",
                "tests/e2e/test_inspector_active_report_authority_playwright.py",
                "tests/e2e/test_inspetor_visual_playwright.py",
            ],
        ),
        (
            "local_e2e_stress_exhaustive",
            [
                "tests/e2e/test_local_stress_playwright.py",
                "tests/e2e/test_local_parallel_stress_playwright.py",
            ],
        ),
    ],
}


def build_coverage_manifest_md(
    *,
    profile: str,
    specs: list[CommandSpec],
    base_url: str | None,
    human_paced: bool,
) -> str:
    lines = [
        "# Coverage Manifest",
        "",
        f"- profile: {profile}",
        f"- base_url: {base_url or 'local-only'}",
        f"- human_paced: {human_paced}",
        f"- suites_planejadas: {len(specs)}",
        "",
        "## Escopo",
        "",
        "- Este manifesto lista tudo o que o runner realmente tentou executar nesta rodada.",
        "- O perfil `exhaustive` cobre os testes automatizados descobertos no repositório web, a matriz E2E local mais ampla e os gates auxiliares do repositório.",
        "- Ainda assim, superfícies sem automação dedicada continuam dependendo de testes novos, não de promessa de cobertura.",
    ]

    categories: dict[str, list[CommandSpec]] = {}
    for item in specs:
        categories.setdefault(item.category, []).append(item)

    for category, category_specs in sorted(categories.items()):
        lines.extend(["", f"## {category}"])
        for spec in category_specs:
            lines.append("")
            lines.append(f"### {spec.name}")
            lines.append(f"- cwd: `{relative_to_repo(spec.cwd)}`")
            if spec.targets:
                lines.append("- targets:")
                for target in spec.targets:
                    lines.append(f"  - `{target}`")
            lines.append(f"- command: `{' '.join(spec.command)}`")

    lines.extend(
        [
            "",
            "## Limites honestos",
            "",
            "- Integrações externas sem harness dedicado ainda dependem de automação nova.",
            "- Produção real com serviços terceiros, notificações externas e identidades corporativas exige probes específicos.",
            "- Cobertura absoluta só existe até a fronteira do que já está automatizado no repositório.",
            "",
        ]
    )
    return "\n".join(lines)


def build_specs(
    *,
    profile: str,
    include_local_e2e: bool,
    base_url: str | None,
    online_artifact_root: pathlib.Path,
    human_paced: bool,
) -> list[CommandSpec]:
    specs: list[CommandSpec] = []

    for group_name in BACKEND_PROFILE_GROUPS[profile]:
        specs.append(
            pytest_spec(
                name=group_name,
                category="local-backend",
                cwd=WEB_ROOT,
                env={"PYTHONPATH": "."},
                targets=dedupe_targets(BACKEND_GROUPS[group_name]),
            )
        )

    if profile == "exhaustive":
        assigned_targets = {
            target
            for group_name in BACKEND_PROFILE_GROUPS[profile]
            for target in BACKEND_GROUPS[group_name]
        }
        remaining_targets = [
            target for target in discover_backend_test_targets() if target not in assigned_targets
        ]
        if remaining_targets:
            specs.append(
                pytest_spec(
                    name="backend_remaining_discovered",
                    category="local-backend-discovered",
                    cwd=WEB_ROOT,
                    env={"PYTHONPATH": "."},
                    targets=remaining_targets,
                )
            )

    if profile in {"broad", "exhaustive"}:
        specs.extend(
            [
                python_script_spec(
                    name="workspace_hygiene_check",
                    category="repo-ops",
                    script_path="scripts/check_workspace_hygiene.py",
                ),
                python_script_spec(
                    name="production_ops_check_json",
                    category="repo-ops",
                    script_path="scripts/run_production_ops_check.py",
                    args=["--json"],
                ),
                python_script_spec(
                    name="uploads_cleanup_check_strict",
                    category="repo-ops",
                    script_path="scripts/run_uploads_cleanup.py",
                    args=["--json", "--strict"],
                ),
                python_script_spec(
                    name="document_phase_acceptance",
                    category="repo-acceptance",
                    script_path="scripts/run_document_phase_acceptance.py",
                ),
                python_script_spec(
                    name="observability_phase_acceptance",
                    category="repo-acceptance",
                    script_path="scripts/run_observability_phase_acceptance.py",
                ),
                python_script_spec(
                    name="hygiene_phase_acceptance",
                    category="repo-acceptance",
                    script_path="scripts/run_hygiene_phase_acceptance.py",
                ),
                python_script_spec(
                    name="v2_phase_acceptance",
                    category="repo-acceptance",
                    script_path="scripts/run_v2_phase_acceptance.py",
                ),
                python_script_spec(
                    name="post_plan_benchmarks",
                    category="repo-benchmarks",
                    script_path="scripts/run_post_plan_benchmarks.py",
                ),
                npm_spec(
                    name="mobile_typecheck",
                    category="mobile-baseline",
                    npm_args=["run", "typecheck"],
                ),
                npm_spec(
                    name="mobile_lint",
                    category="mobile-baseline",
                    npm_args=["run", "lint"],
                ),
                npm_spec(
                    name="mobile_test",
                    category="mobile-baseline",
                    npm_args=["run", "test", "--", "--runInBand"],
                ),
                npm_spec(
                    name="mobile_format_check",
                    category="mobile-baseline",
                    npm_args=["run", "format:check"],
                ),
            ]
        )

    if include_local_e2e:
        e2e_env = {
            "PYTHONPATH": ".",
            "RUN_E2E": "1",
            "RUN_E2E_LOCAL": "1" if profile == "exhaustive" else "0",
            "E2E_VISUAL": "1" if human_paced else "0",
            "E2E_SLOWMO_MS": "700" if human_paced else ("300" if profile == "critical" else "380"),
            "E2E_VISUAL_STEP_PAUSE_MS": "2400" if human_paced else "0",
            "E2E_VISUAL_FINAL_PAUSE_MS": "5200" if human_paced else "0",
        }
        e2e_extra_args = [
            "--browser",
            "chromium",
            "--tracing",
            "retain-on-failure",
            "--video",
            "retain-on-failure",
            "--screenshot",
            "only-on-failure",
            "--output",
            str(online_artifact_root.parent / "playwright-output"),
            "-s",
        ]
        for spec_name, targets in E2E_PROFILE_SPECS[profile]:
            specs.append(
                pytest_spec(
                    name=spec_name,
                    category="local-e2e",
                    cwd=WEB_ROOT,
                    env=e2e_env,
                    targets=targets,
                    extra_args=e2e_extra_args,
                )
            )

    if base_url:
        online_command = [
            str(WEB_PYTHON),
            "scripts/render_ui_user_journey.py",
            "--base-url",
            base_url,
            "--artifact-root",
            str(online_artifact_root),
        ]
        if human_paced and graphical_session_available():
            online_command.append("--headful")
        online_command.extend(["--slow-mo-ms", "550" if human_paced else "140"])
        online_command.extend(["--pause-scale", "2.2" if human_paced else "1.0"])
        specs.append(
            CommandSpec(
                name="online_render_journey",
                category="hosted-e2e",
                cwd=WEB_ROOT,
                env={"PYTHONPATH": "."},
                command=online_command,
            )
        )
    return specs


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa regressao operacional ampla e gera bug registry.")
    parser.add_argument("--artifact-root", default=str(ARTIFACTS_ROOT))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--profile",
        choices=("critical", "broad", "exhaustive"),
        default="broad",
        help="Define a profundidade da rodada automatizada.",
    )
    parser.add_argument("--skip-local-e2e", action="store_true")
    parser.add_argument("--human-paced", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    artifact_root = ensure_dir(pathlib.Path(args.artifact_root))
    artifacts_dir = ensure_dir(artifact_root / now_slug())
    online_artifact_root = ensure_dir(artifacts_dir / "online_journey")

    specs = build_specs(
        profile=str(args.profile),
        include_local_e2e=not bool(args.skip_local_e2e),
        base_url=str(args.base_url or "").strip() or None,
        online_artifact_root=online_artifact_root,
        human_paced=bool(args.human_paced),
    )

    if args.dry_run:
        payload = {
            "artifacts_dir": str(artifacts_dir),
            "profile": str(args.profile),
            "suites": [
                {
                    "name": item.name,
                    "category": item.category,
                    "cwd": str(item.cwd),
                    "command": item.command,
                    "env": item.env,
                }
                for item in specs
            ],
        }
        write_json(artifacts_dir / "dry_run.json", payload)
        print(str(artifacts_dir))
        return 0

    results: list[CommandResult] = []
    for spec in specs:
        if spec.name == "online_render_journey":
            warm_hosted_base_url(
                base_url=str(args.base_url),
                log_path=ensure_dir(artifacts_dir / "logs") / "online_warmup.txt",
            )
        result = run_command(spec, artifacts_dir=artifacts_dir)
        if spec.name == "online_render_journey":
            log_text = read_text_if_exists(REPO_ROOT / result.log_path)
            if int(result.returncode) != 0 and should_retry_online(log_text):
                result.extras["retried_after_warmup"] = True
                warm_hosted_base_url(
                    base_url=str(args.base_url),
                    log_path=ensure_dir(artifacts_dir / "logs") / "online_warmup_retry.txt",
                )
                result = run_command(spec, artifacts_dir=artifacts_dir)
        if spec.name == "online_render_journey":
            latest = latest_subdir(online_artifact_root)
            if latest is not None:
                result.extras["online_artifact_dir"] = relative_to_repo(latest)
                report_json = latest / "report.json"
                if report_json.exists():
                    result.extras["online_report_json"] = relative_to_repo(report_json)
        results.append(result)

    command_bug_entries = bugs_from_command_results(results)

    online_report_payload: dict[str, Any] | None = None
    online_report_path: str | None = None
    for item in results:
        report_path = item.extras.get("online_report_json")
        if report_path:
            online_report_path = str(report_path)
            online_report_payload = json.loads((REPO_ROOT / report_path).read_text(encoding="utf-8"))
            break

    online_bug_entries = bugs_from_online_report(
        online_report_payload,
        source="online_render_journey",
        evidence_path=online_report_path or "artifacts indisponiveis",
        starting_index=len(command_bug_entries) + 1,
    )
    bug_entries = command_bug_entries + online_bug_entries

    summary_payload = {
        "status": "ok" if all(int(item.returncode) == 0 for item in results) else "failed",
        "executed_at": dt.datetime.now().isoformat(),
        "profile": str(args.profile),
        "base_url": str(args.base_url or "").strip() or None,
        "human_paced": bool(args.human_paced),
        "commands": [asdict(item) for item in results],
        "bug_entries": [asdict(item) for item in bug_entries],
        "online_report_path": online_report_path,
    }

    write_json(artifacts_dir / "summary.json", summary_payload)
    write_json(artifacts_dir / "bug_registry.json", [asdict(item) for item in bug_entries])
    write_text(
        artifacts_dir / "coverage_manifest.md",
        build_coverage_manifest_md(
            profile=str(args.profile),
            specs=specs,
            base_url=str(args.base_url or "").strip() or None,
            human_paced=bool(args.human_paced),
        ),
    )
    write_text(
        artifacts_dir / "success_registry.md",
        build_success_registry_md(results=results, online_report_payload=online_report_payload),
    )
    write_text(
        artifacts_dir / "summary.md",
        build_summary_md(
            results=results,
            bug_entries=bug_entries,
            online_report_path=online_report_path,
            base_url=str(args.base_url or "").strip() or None,
            profile=str(args.profile),
        ),
    )
    write_text(artifacts_dir / "bug_registry.md", build_bug_registry_md(bug_entries))
    print(str(artifacts_dir))
    return 0 if summary_payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
