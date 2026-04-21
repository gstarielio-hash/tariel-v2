#!/usr/bin/env python3
"""Runner operacional do piloto mobile V2 no tenant demo local."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime as dt
import hashlib
import html
import hmac
import http.cookiejar
import json
import os
import pathlib
import re
import shutil
import signal
import sqlite3
import struct
import subprocess
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ANDROID_ROOT = REPO_ROOT / "android"
WEB_ROOT = REPO_ROOT / "web"
ARTIFACTS_ROOT = REPO_ROOT / "artifacts" / "mobile_pilot_run"
DEVKIT_RUNTIME_ROOT = REPO_ROOT / ".tmp_online" / "devkit"
MOBILE_PILOT_LANE_STATE_FILE = DEVKIT_RUNTIME_ROOT / "mobile_pilot_lane_status.json"
DEFAULT_PORTS = (8000, 8081, 19000, 19001)
DEFAULT_MOBILE_PASSWORD = "Dev@123456"
DEFAULT_TIMEOUT = 30
LOCAL_MOBILE_API_BASE_URL = "http://127.0.0.1:8000"
HEALTH_URL = "http://127.0.0.1:8000/health"
PACKAGE_NAME = "com.tarielia.inspetor"
FLOW_PATH = ANDROID_ROOT / "maestro" / "mobile-v2-pilot-run.yaml"
DEVICE_TMP_DIR = "/data/local/tmp"
MAESTRO_ENVIRONMENT_RETRY_LIMIT = 1
ANDROID_BOOT_TIMEOUT_SECONDS = 420
ANDROID_HEALTH_STABLE_PASSES = 3
_BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
_RUNNER_DB_SNAPSHOT_CACHE: dict[str, str | None] | None = None


class RunnerError(RuntimeError):
    """Erro operacional do runner."""


@dataclasses.dataclass
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclasses.dataclass
class ExecutionState:
    artifacts_dir: pathlib.Path
    screenshots_dir: pathlib.Path
    ui_dumps_dir: pathlib.Path
    maestro_debug_dir: pathlib.Path
    summary_before: dict[str, Any] | None = None
    summary_after: dict[str, Any] | None = None
    capabilities_before: dict[str, Any] | None = None
    capabilities_after: dict[str, Any] | None = None
    operator_status_before: dict[str, Any] | None = None
    operator_status_after: dict[str, Any] | None = None
    operator_run_started: bool = False
    operator_run_finished: bool = False
    backend_started_here: bool = False
    backend_pid: int | None = None
    logcat_process: subprocess.Popen[str] | None = None
    device_id: str = ""
    package_name: str = PACKAGE_NAME
    main_activity: str = ".MainActivity"
    mobile_email: str = ""
    admin_email: str = ""
    mobile_token: str = ""
    target_laudo_id: int | None = None
    operator_run_outcome: str = ""
    operator_run_reason: str = ""
    outcome_label: str = "partial_execution"
    flow_ran: bool = False
    feed_covered: bool = False
    thread_covered: bool = False
    notes: list[str] = dataclasses.field(default_factory=list)
    commands_used: list[str] = dataclasses.field(default_factory=list)
    build_used_existing_install: bool = False
    ui_marker_summary: dict[str, Any] | None = None
    maestro_target_tap_completed: bool = False
    maestro_selection_callback_confirmed: bool = False
    maestro_shell_selection_confirmed: bool = False
    maestro_selection_callback_wait_failed: bool = False
    maestro_shell_selection_wait_failed: bool = False
    maestro_activity_center_terminal_confirmed: bool = False
    maestro_activity_center_v2_confirmed: bool = False
    visual_mode: bool = False
    maestro_attempts: int = 0
    maestro_environment_retry_used: bool = False
    environment_failure_signals: list[str] = dataclasses.field(default_factory=list)
    host_phase_events: list[dict[str, Any]] = dataclasses.field(default_factory=list)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_local_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_json(path: pathlib.Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def append_note(state: ExecutionState, note: str) -> None:
    state.notes.append(note)


def env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def record_phase_event(
    state: ExecutionState,
    *,
    phase: str,
    status: str,
    detail: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "timestamp_utc": now_utc(),
        "phase": phase,
        "status": status,
        "detail": detail,
    }
    if extra:
        payload["extra"] = extra
    state.host_phase_events.append(payload)
    write_json(state.artifacts_dir / "host_phase_events.json", state.host_phase_events)


def write_mobile_pilot_lane_state(
    state: ExecutionState,
    *,
    status: str,
    detail: str,
) -> None:
    payload = {
        "generatedAt": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspace": str(REPO_ROOT),
        "status": status,
        "detail": detail,
        "device": state.device_id,
        "visualMode": state.visual_mode,
        "result": state.outcome_label,
        "operatorRunOutcome": state.operator_run_outcome,
        "operatorRunReason": state.operator_run_reason,
        "maestroAttempts": state.maestro_attempts,
        "maestroEnvironmentRetryUsed": state.maestro_environment_retry_used,
        "environmentFailureSignals": state.environment_failure_signals,
        "feedCovered": state.feed_covered,
        "threadCovered": state.thread_covered,
        "artifactDir": str(state.artifacts_dir),
    }
    write_json(MOBILE_PILOT_LANE_STATE_FILE, payload)


def command_display(command: list[str]) -> str:
    return " ".join(command)


def has_graphical_display() -> bool:
    if sys.platform.startswith("linux"):
        return bool(os.getenv("DISPLAY", "").strip() or os.getenv("WAYLAND_DISPLAY", "").strip())
    return True


def running_in_ci() -> bool:
    return os.getenv("CI", "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_visual_mode(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return bool(explicit) and has_graphical_display()

    raw = os.getenv("MOBILE_VISUAL", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return has_graphical_display()
    if running_in_ci():
        return False
    return False


def should_force_fresh_emulator_boot() -> bool:
    return env_flag("MOBILE_FORCE_FRESH_BOOT", True)


def should_wipe_emulator_on_install_recovery() -> bool:
    return env_flag("MOBILE_WIPE_ON_INSTALL_RECOVERY", True)


def force_mobile_install() -> bool:
    return os.getenv("MOBILE_FORCE_INSTALL", "").strip().lower() in {"1", "true", "yes", "on"}


def log_step(message: str) -> None:
    timestamp = dt.datetime.now().strftime("%H:%M:%S")
    print(f"[mobile-acceptance {timestamp}] {message}", flush=True)


def _start_stream_threads(
    process: subprocess.Popen[str],
    *,
    stdout_sink,
    stderr_sink,
) -> tuple[list[threading.Thread], list[str], list[str]]:
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def _pump(stream, sink, chunks: list[str]) -> None:
        try:
            for line in iter(stream.readline, ""):
                chunks.append(line)
                sink.write(line)
                sink.flush()
        finally:
            stream.close()

    stdout_thread = threading.Thread(
        target=_pump,
        args=(process.stdout, stdout_sink, stdout_chunks),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_pump,
        args=(process.stderr, stderr_sink, stderr_chunks),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    return [stdout_thread, stderr_thread], stdout_chunks, stderr_chunks


def _terminate_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except Exception:
        try:
            process.kill()
        except ProcessLookupError:
            return


def run_command(
    command: list[str],
    *,
    cwd: pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
    check: bool = True,
    stream_output: bool = False,
) -> CommandResult:
    if stream_output:
        print(f"$ {command_display(command)}", flush=True)
        process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        threads, stdout_chunks, stderr_chunks = _start_stream_threads(
            process,
            stdout_sink=sys.stdout,
            stderr_sink=sys.stderr,
        )
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process)
            process.wait()
            raise
        finally:
            for thread in threads:
                thread.join()
        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)
        result = CommandResult(
            command=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )
        if check and returncode != 0:
            raise RunnerError(
                f"Comando falhou ({returncode}): {command_display(command)}\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )
        return result

    process = subprocess.Popen(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate_process_group(process)
        process.wait()
        raise
    result = CommandResult(
        command=command,
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
    )
    if check and process.returncode != 0:
        raise RunnerError(
            f"Comando falhou ({process.returncode}): {command_display(command)}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    return result


def save_command_artifact(path: pathlib.Path, result: CommandResult) -> None:
    write_text(
        path,
        "\n".join(
            [
                f"$ {command_display(result.command)}",
                "",
                "[stdout]",
                result.stdout.strip(),
                "",
                "[stderr]",
                result.stderr.strip(),
                "",
                f"[returncode] {result.returncode}",
            ]
        ).strip()
        + "\n",
    )


def load_env_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        value = raw_value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


def parse_application_id() -> tuple[str, str]:
    build_gradle = (ANDROID_ROOT / "android" / "app" / "build.gradle").read_text(
        encoding="utf-8"
    )
    manifest = (
        ANDROID_ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    ).read_text(encoding="utf-8")

    app_match = re.search(r"applicationId\s+'([^']+)'", build_gradle)
    activity_match = re.search(r'<activity android:name="([^"]+MainActivity)"', manifest)
    package_name = app_match.group(1) if app_match else PACKAGE_NAME
    main_activity = activity_match.group(1) if activity_match else ".MainActivity"
    return package_name, main_activity


def load_android_package_info() -> dict[str, Any]:
    package_json = json.loads((ANDROID_ROOT / "package.json").read_text(encoding="utf-8"))
    package_name, main_activity = parse_application_id()
    preferred_script = "android:preview"
    available_scripts = package_json.get("scripts") or {}
    if preferred_script not in available_scripts:
        preferred_script = "android:dev" if "android:dev" in available_scripts else "android"
    return {
        "npm_name": package_json.get("name"),
        "preferred_install_script": preferred_script,
        "package_name": package_name,
        "main_activity": main_activity,
        "scripts": available_scripts,
    }


def resolve_web_python_binary() -> str:
    candidates = (
        WEB_ROOT / ".venv-linux" / "bin" / "python",
        WEB_ROOT / ".venv" / "bin" / "python",
        pathlib.Path(sys.executable),
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "python3"


def sqlite_rows(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    db_path = WEB_ROOT / "tariel_admin (1).db"
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(query, params)
        return cursor.fetchall()


def load_runner_db_snapshot() -> dict[str, str | None]:
    global _RUNNER_DB_SNAPSHOT_CACHE

    if _RUNNER_DB_SNAPSHOT_CACHE is not None:
        return dict(_RUNNER_DB_SNAPSHOT_CACHE)

    script = textwrap.dedent(
        """
        import json
        from sqlalchemy import case, select

        import app.shared.database as banco_dados
        from app.shared.database import NivelAcesso, Usuario

        with banco_dados.SessaoLocal() as banco:
            mobile_email = banco.execute(
                select(Usuario.email)
                .where(Usuario.empresa_id == 1)
                .where(Usuario.nivel_acesso == int(NivelAcesso.INSPETOR))
                .where(Usuario.ativo.is_(True))
                .order_by(
                    case((Usuario.email == "inspetor@tariel.ia", 0), else_=1),
                    Usuario.id.asc(),
                )
                .limit(1)
            ).scalar()

            admin_row = banco.execute(
                select(Usuario.email, Usuario.mfa_secret_b32)
                .where(Usuario.nivel_acesso == int(NivelAcesso.DIRETORIA))
                .where(Usuario.ativo.is_(True))
                .order_by(
                    case(
                        (Usuario.email == "admin@tariel.ia", 0),
                        (Usuario.email == "admin-legado@tariel.ia", 1),
                        else_=2,
                    ),
                    Usuario.id.asc(),
                )
                .limit(1)
            ).first()

        payload = {
            "mobile_email": str(mobile_email or "").strip() or None,
            "admin_email": str(getattr(admin_row, "email", "") or "").strip() or None,
            "admin_mfa_secret": str(getattr(admin_row, "mfa_secret_b32", "") or "").strip().upper() or None,
        }
        print(json.dumps(payload, ensure_ascii=False))
        """
    ).strip()

    result = run_command(
        [resolve_web_python_binary(), "-c", script],
        cwd=WEB_ROOT,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        _RUNNER_DB_SNAPSHOT_CACHE = {}
        return {}

    try:
        payload = json.loads(str(result.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        _RUNNER_DB_SNAPSHOT_CACHE = {}
        return {}

    snapshot = {
        "mobile_email": str(payload.get("mobile_email") or "").strip() or None,
        "admin_email": str(payload.get("admin_email") or "").strip() or None,
        "admin_mfa_secret": str(payload.get("admin_mfa_secret") or "").strip().upper() or None,
    }
    _RUNNER_DB_SNAPSHOT_CACHE = snapshot
    return dict(snapshot)


def _normalize_totp_secret(secret: str) -> str:
    normalized = "".join(
        ch for ch in str(secret or "").strip().upper() if ch in _BASE32_ALPHABET
    )
    if not normalized:
        raise RunnerError("Segredo TOTP do Admin-CEO inválido ou ausente.")
    return normalized


def _decode_totp_secret(secret: str) -> bytes:
    normalized = _normalize_totp_secret(secret)
    padded = normalized + "=" * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(padded, casefold=True)


def current_totp(secret: str, *, at_time: int | float | None = None) -> str:
    timestamp = int(time.time() if at_time is None else at_time)
    counter = timestamp // 30
    digest = hmac.new(
        _decode_totp_secret(secret),
        struct.pack(">Q", int(counter)),
        hashlib.sha1,
    ).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % 1_000_000).zfill(6)


def lookup_admin_totp_secret(email: str) -> str | None:
    snapshot = load_runner_db_snapshot()
    snapshot_email = str(snapshot.get("admin_email") or "").strip().lower()
    if snapshot_email and snapshot_email == str(email or "").strip().lower():
        value = str(snapshot.get("admin_mfa_secret") or "").strip().upper()
        if value:
            return value

    rows = sqlite_rows(
        """
        select mfa_secret_b32
        from usuarios
        where lower(email) = lower(?) and ativo = 1
        limit 1
        """,
        (email,),
    )
    if not rows:
        return None
    value = str(rows[0]["mfa_secret_b32"] or "").strip().upper()
    return value or None


def extract_csrf_token(html_body: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html_body)
    csrf_token = html.unescape(match.group(1)) if match else ""
    if not csrf_token:
        raise RunnerError("Não foi possível extrair csrf_token da página do Admin-CEO.")
    return csrf_token


def extract_totp_secret_from_html(html_body: str) -> str | None:
    match_uri = re.search(r"secret=([A-Z2-7]+)", html_body)
    if match_uri:
        return match_uri.group(1)
    match_code = re.search(r"Segredo TOTP:\s*<code>([A-Z2-7 ]+)</code>", html_body)
    if match_code:
        return re.sub(r"\s+", "", match_code.group(1))
    match_text = re.search(r"Segredo TOTP:\s*([A-Z2-7 ]+)", html_body)
    if match_text:
        return re.sub(r"\s+", "", match_text.group(1))
    return None


def submit_admin_mfa(
    opener: urllib.request.OpenerDirector,
    *,
    path: str,
    html_body: str,
    email: str,
) -> str:
    csrf_token = extract_csrf_token(html_body)
    # The setup page reflects the secret from the backend that is currently
    # serving the local smoke. Prefer that over the legacy SQLite fallback,
    # which may point at a different database than the one used by uvicorn.
    secret = extract_totp_secret_from_html(html_body) or lookup_admin_totp_secret(email)
    if not secret:
        raise RunnerError("Segredo TOTP do Admin-CEO indisponível para concluir MFA.")
    payload = urllib.parse.urlencode(
        {
            "csrf_token": csrf_token,
            "codigo": current_totp(secret),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:8000{path}",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with opener.open(request, timeout=20) as response:
        final_url = response.geturl()
        response.read()
    return final_url


def resolve_credentials(web_env: dict[str, str]) -> tuple[str, str, str]:
    mobile_password = (
        web_env.get("SEED_INSPETOR_SENHA")
        or web_env.get("SEED_DEV_SENHA_PADRAO")
        or DEFAULT_MOBILE_PASSWORD
    )
    admin_password = (
        web_env.get("SEED_ADMIN_SENHA")
        or web_env.get("SEED_DEV_SENHA_PADRAO")
        or DEFAULT_MOBILE_PASSWORD
    )

    snapshot = load_runner_db_snapshot()

    mobile_candidates = sqlite_rows(
        """
        select email
        from usuarios
        where empresa_id = 1 and nivel_acesso = 1 and ativo = 1
        order by case when email = 'inspetor@tariel.ia' then 0 else 1 end, id
        """
    )
    admin_candidates = sqlite_rows(
        """
        select email
        from usuarios
        where nivel_acesso = 99 and ativo = 1
        order by case when email = 'admin-legado@tariel.ia' then 0 else 1 end, id
        """
    )
    mobile_email = str(snapshot.get("mobile_email") or "").strip()
    if not mobile_email:
        mobile_email = (
            str(mobile_candidates[0]["email"]).strip()
            if mobile_candidates
            else "inspetor@tariel.ia"
        )

    admin_email = str(snapshot.get("admin_email") or "").strip()
    if not admin_email:
        admin_email = (
            str(admin_candidates[0]["email"]).strip()
            if admin_candidates
            else "admin-legado@tariel.ia"
        )
    return mobile_email, mobile_password, admin_email


def build_environment_report(package_info: dict[str, Any]) -> str:
    sections = [
        f"timestamp_utc={now_utc()}",
        f"repo_root={REPO_ROOT}",
        f"android_root={ANDROID_ROOT}",
        f"web_root={WEB_ROOT}",
        f"package_name={package_info['package_name']}",
        f"main_activity={package_info['main_activity']}",
        f"preferred_install_script={package_info['preferred_install_script']}",
    ]
    for command in (
        ["adb", "version"],
        ["adb", "devices", "-l"],
        ["node", "--version"],
        ["npm", "--version"],
        ["python3", "--version"],
        ["maestro", "--version"],
    ):
        try:
            result = run_command(command, check=False, timeout=DEFAULT_TIMEOUT)
            sections.extend(
                [
                    "",
                    f"$ {command_display(command)}",
                    result.stdout.strip() or result.stderr.strip(),
                ]
            )
        except Exception as exc:  # pragma: no cover - defensive
            sections.extend(["", f"$ {command_display(command)}", str(exc)])
    return "\n".join(sections).strip() + "\n"


def healthcheck() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def parse_adb_devices_output(output: str) -> list[tuple[str, str]]:
    devices: list[tuple[str, str]] = []
    for line in output.splitlines():
        if line.startswith("List of devices attached"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))
    return devices


def probe_device_health_by_serial(serial: str) -> dict[str, Any]:
    def _probe(command: list[str]) -> CommandResult:
        return run_command(command, check=False, timeout=12)

    sys_boot = _probe(["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"])
    dev_boot = _probe(["adb", "-s", serial, "shell", "getprop", "dev.bootcomplete"])
    bootanim = _probe(["adb", "-s", serial, "shell", "getprop", "init.svc.bootanim"])
    package_probe = _probe(
        [
            "adb",
            "-s",
            serial,
            "shell",
            "cmd",
            "package",
            "resolve-activity",
            "--brief",
            "com.android.settings",
        ]
    )
    uptime_probe = _probe(["adb", "-s", serial, "shell", "cat", "/proc/uptime"])
    package_output = f"{package_probe.stdout}\n{package_probe.stderr}".strip()
    uptime_seconds = None
    uptime_first = str(uptime_probe.stdout or "").strip().split()
    if uptime_first:
        try:
            uptime_seconds = float(uptime_first[0])
        except ValueError:
            uptime_seconds = None

    return {
        "serial": serial,
        "sys_boot_completed": str(sys_boot.stdout or "").strip(),
        "dev_bootcomplete": str(dev_boot.stdout or "").strip(),
        "bootanim_state": str(bootanim.stdout or "").strip(),
        "package_service_ready": package_probe.returncode == 0
        and "com.android.settings" in package_output
        and "/" in package_output,
        "package_service_detail": package_output or str(package_probe.returncode),
        "uptime_seconds": uptime_seconds,
    }


def device_health_ready(health: dict[str, Any]) -> bool:
    sys_boot = str(health.get("sys_boot_completed") or "").strip()
    dev_boot = str(health.get("dev_bootcomplete") or "").strip()
    bootanim_state = str(health.get("bootanim_state") or "").strip()
    package_ready = bool(health.get("package_service_ready"))
    return (
        sys_boot == "1"
        and (not dev_boot or dev_boot == "1")
        and (not bootanim_state or bootanim_state == "stopped")
        and package_ready
    )


def start_backend(state: ExecutionState) -> None:
    if healthcheck():
        append_note(state, "Backend local já estava ativo em 127.0.0.1:8000.")
        return

    script = REPO_ROOT / "scripts" / "start_local_mobile_api_background.sh"
    result = run_command([str(script)], cwd=REPO_ROOT, timeout=90)
    state.commands_used.append(command_display([str(script)]))
    save_command_artifact(state.artifacts_dir / "backend_start.txt", result)

    deadline = time.time() + 45
    while time.time() < deadline:
        if healthcheck():
            state.backend_started_here = True
            pid_file = REPO_ROOT / "local-mobile-api.pid"
            if pid_file.exists():
                try:
                    state.backend_pid = int(pid_file.read_text(encoding="utf-8").strip())
                except ValueError:
                    state.backend_pid = None
            return
        time.sleep(1)

    raise RunnerError("Backend local não respondeu em http://127.0.0.1:8000/health.")


def stop_backend_if_needed(state: ExecutionState) -> None:
    if not state.backend_started_here or not state.backend_pid:
        return
    try:
        os.kill(state.backend_pid, signal.SIGTERM)
        time.sleep(1)
    except ProcessLookupError:
        return
    except Exception as exc:  # pragma: no cover - cleanup defensivo
        append_note(state, f"Falha ao encerrar backend local iniciado pelo runner: {exc}")


def boot_emulator_with_policy(
    state: ExecutionState,
    *,
    label: str,
    wipe_data: bool,
) -> None:
    script = REPO_ROOT / "scripts" / "dev" / "run_android_emulator_stack.sh"
    if not script.exists():
        raise RunnerError("Lane Android do devkit nao encontrada para subir o emulador.")

    fresh_boot = should_force_fresh_emulator_boot() or wipe_data
    command = [
        str(script),
        "--mode",
        "boot",
        "--boot-timeout",
        str(ANDROID_BOOT_TIMEOUT_SECONDS),
    ]
    if fresh_boot:
        command.append("--force-cold-boot")
    if wipe_data:
        command.append("--wipe-data")
    if not state.visual_mode:
        command.append("--headless")

    detail_parts = []
    if wipe_data:
        detail_parts.append("wipe-data")
    if fresh_boot:
        detail_parts.append("cold-boot")
    if not detail_parts:
        detail_parts.append("reuse-allowed")
    detail = " + ".join(detail_parts)
    log_step(
        f"Garantindo emulador Android {'visível' if state.visual_mode else 'headless'} com {detail}."
    )
    record_phase_event(
        state,
        phase=label,
        status="running",
        detail=detail,
        extra={"visual_mode": state.visual_mode, "wipe_data": wipe_data},
    )
    result = run_command(
        command,
        cwd=REPO_ROOT,
        timeout=ANDROID_BOOT_TIMEOUT_SECONDS + 180,
        stream_output=True,
    )
    state.commands_used.append(command_display(command))
    save_command_artifact(state.artifacts_dir / f"{label}.txt", result)
    record_phase_event(
        state,
        phase=label,
        status="ok",
        detail=detail,
    )


def ensure_local_emulator(state: ExecutionState) -> None:
    preferred_device = (
        os.getenv("ANDROID_SERIAL", "").strip()
        or os.getenv("MOBILE_DEVICE_ID", "").strip()
    )
    if preferred_device and not preferred_device.startswith("emulator-"):
        append_note(
            state,
            f"Bootstrap do emulador foi pulado porque um device físico foi fixado: {preferred_device}.",
        )
        return

    boot_emulator_with_policy(
        state,
        label="emulator_boot",
        wipe_data=False,
    )


def resolve_device(state: ExecutionState) -> str:
    result = run_command(["adb", "devices", "-l"])
    state.commands_used.append(command_display(["adb", "devices", "-l"]))
    save_command_artifact(state.artifacts_dir / "adb_devices.txt", result)

    connected = parse_adb_devices_output(result.stdout)
    devices = [serial for serial, device_state in connected if device_state == "device"]
    if not devices:
        raise RunnerError("Nenhum device/emulador ADB em estado 'device' foi encontrado.")

    preferred_device = (
        os.getenv("ANDROID_SERIAL", "").strip()
        or os.getenv("MOBILE_DEVICE_ID", "").strip()
    )
    if preferred_device:
        if preferred_device not in devices:
            raise RunnerError(
                f"Dispositivo solicitado não está disponível via adb: {preferred_device}"
            )
        return preferred_device

    emulators = [serial for serial in devices if serial.startswith("emulator-")]
    if emulators:
        return emulators[0]

    return devices[0]


def wait_for_device_disconnect(serial: str, *, timeout_seconds: int = 40) -> None:
    deadline = time.time() + max(timeout_seconds, 5)
    while time.time() < deadline:
        result = run_command(["adb", "devices", "-l"], check=False, timeout=10)
        current_serials = {
            device_serial
            for device_serial, _device_state in parse_adb_devices_output(result.stdout)
        }
        if serial not in current_serials:
            return
        time.sleep(2)
    raise RunnerError(f"Serial do emulador nao saiu do adb apos kill: {serial}")


def ensure_adb_reverse(state: ExecutionState, ports: tuple[int, ...]) -> None:
    lines = []
    for port in ports:
        command = [
            "adb",
            "-s",
            state.device_id,
            "reverse",
            f"tcp:{port}",
            f"tcp:{port}",
        ]
        result = run_command(command, check=False)
        state.commands_used.append(command_display(command))
        status = "ok" if result.returncode == 0 else f"erro:{result.returncode}"
        lines.append(f"{port}: {status}")
        if result.stdout.strip():
            lines.append(result.stdout.strip())
        if result.stderr.strip():
            lines.append(result.stderr.strip())
    write_text(state.artifacts_dir / "adb_reverse.txt", "\n".join(lines).strip() + "\n")


def restart_emulator_instance(
    state: ExecutionState,
    *,
    label: str,
    wipe_data: bool = False,
) -> None:
    if not state.device_id.startswith("emulator-"):
        raise RunnerError(
            f"Tentativa de restart controlado em device nao-emulador: {state.device_id}"
        )

    kill_command = ["adb", "-s", state.device_id, "emu", "kill"]
    state.commands_used.append(command_display(kill_command))
    try:
        kill_result = run_command(
            kill_command,
            check=False,
            timeout=12,
        )
    except subprocess.TimeoutExpired:
        kill_result = CommandResult(
            command=kill_command,
            returncode=124,
            stdout="",
            stderr="timeout",
        )
        append_note(
            state,
            f"Encerramento controlado do emulador excedeu timeout ({label}); o runner tentou subir uma nova instancia mesmo assim.",
        )
    save_command_artifact(state.artifacts_dir / f"{label}_emu_kill.txt", kill_result)
    if kill_result.returncode == 0:
        wait_for_device_disconnect(state.device_id)
    time.sleep(5)
    boot_emulator_with_policy(state, label=f"{label}_boot", wipe_data=wipe_data)
    state.device_id = resolve_device(state)
    ensure_adb_reverse(state, DEFAULT_PORTS)
    wait_for_package_service_ready(state, timeout_seconds=240)
    if state.visual_mode:
        keep_device_visible(state)


def keep_device_visible(state: ExecutionState) -> None:
    lines = []
    commands = [
        ["adb", "-s", state.device_id, "shell", "svc", "power", "stayon", "true"],
        ["adb", "-s", state.device_id, "shell", "input", "keyevent", "KEYCODE_WAKEUP"],
        ["adb", "-s", state.device_id, "shell", "wm", "dismiss-keyguard"],
    ]
    for command in commands:
        lines.append(f"$ {command_display(command)}")
        try:
            result = run_command(command, check=False, timeout=8)
            state.commands_used.append(command_display(command))
            if result.stdout.strip():
                lines.append(result.stdout.strip())
            if result.stderr.strip():
                lines.append(result.stderr.strip())
            lines.append(f"[returncode] {result.returncode}")
        except subprocess.TimeoutExpired:
            append_note(
                state,
                f"Comando de visibilidade do device excedeu timeout e foi ignorado: {command_display(command)}",
            )
            lines.append("[timeout] true")
        lines.append("")
    write_text(state.artifacts_dir / "device_visibility.txt", "\n".join(lines).strip() + "\n")


def prime_device_for_automation(state: ExecutionState, *, label: str) -> None:
    lines = []
    commands = [
        ["adb", "-s", state.device_id, "shell", "input", "keyevent", "KEYCODE_WAKEUP"],
        ["adb", "-s", state.device_id, "shell", "wm", "dismiss-keyguard"],
        ["adb", "-s", state.device_id, "shell", "input", "keyevent", "KEYCODE_HOME"],
        ["adb", "-s", state.device_id, "shell", "settings", "put", "global", "window_animation_scale", "0"],
        ["adb", "-s", state.device_id, "shell", "settings", "put", "global", "transition_animation_scale", "0"],
        ["adb", "-s", state.device_id, "shell", "settings", "put", "global", "animator_duration_scale", "0"],
    ]
    for command in commands:
        lines.append(f"$ {command_display(command)}")
        try:
            result = run_command(command, check=False, timeout=12)
            state.commands_used.append(command_display(command))
            if result.stdout.strip():
                lines.append(result.stdout.strip())
            if result.stderr.strip():
                lines.append(result.stderr.strip())
            lines.append(f"[returncode] {result.returncode}")
        except subprocess.TimeoutExpired:
            append_note(
                state,
                f"Comando de preparo do device excedeu timeout e foi ignorado: {command_display(command)}",
            )
            lines.append("[timeout] true")
        lines.append("")
    write_text(
        state.artifacts_dir / f"{label}_device_prime.txt",
        "\n".join(lines).strip() + "\n",
    )
    time.sleep(2)


def package_service_ready(state: ExecutionState) -> tuple[bool, str]:
    result = run_command(
        [
            "adb",
            "-s",
            state.device_id,
            "shell",
            "cmd",
            "package",
            "resolve-activity",
            "--brief",
            "com.android.settings",
        ],
        check=False,
        timeout=12,
    )
    state.commands_used.append(
        command_display(
            [
                "adb",
                "-s",
                state.device_id,
                "shell",
                "cmd",
                "package",
                "resolve-activity",
                "--brief",
                "com.android.settings",
            ]
        )
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or str(result.returncode)
        return False, detail
    output = result.stdout or ""
    if "com.android.settings" in output and "/" in output:
        return True, "package_service_present"
    return False, "package_service_missing"


def wait_for_package_service_ready(state: ExecutionState, *, timeout_seconds: int = 120) -> None:
    deadline = time.time() + max(timeout_seconds, 10)
    stable_passes = 0
    last_health: dict[str, Any] = {
        "sys_boot_completed": "",
        "dev_bootcomplete": "",
        "bootanim_state": "",
        "package_service_detail": "package_service_missing",
    }
    while time.time() < deadline:
        try:
            health = probe_device_health_by_serial(state.device_id)
        except subprocess.TimeoutExpired:
            last_health = {
                "sys_boot_completed": "",
                "dev_bootcomplete": "",
                "bootanim_state": "",
                "package_service_detail": "health_probe_timeout",
            }
            stable_passes = 0
            time.sleep(2)
            continue
        last_health = health
        if device_health_ready(health):
            stable_passes += 1
            if stable_passes >= ANDROID_HEALTH_STABLE_PASSES:
                write_json(
                    state.artifacts_dir / "package_service_wait_health.json",
                    {
                        "stable_passes_required": ANDROID_HEALTH_STABLE_PASSES,
                        "stable_passes_observed": stable_passes,
                        "health": health,
                    },
                )
                return
        else:
            stable_passes = 0
        time.sleep(2)
    raise RunnerError(
        "Package service do Android indisponivel: "
        f"sys={last_health.get('sys_boot_completed') or '0'} "
        f"dev={last_health.get('dev_bootcomplete') or '0'} "
        f"bootanim={last_health.get('bootanim_state') or 'unknown'} "
        f"package={last_health.get('package_service_detail') or 'missing'} "
        f"stable={stable_passes}/{ANDROID_HEALTH_STABLE_PASSES}"
    )


def ensure_device_package_service_ready(state: ExecutionState) -> None:
    try:
        wait_for_package_service_ready(state, timeout_seconds=90)
        return
    except RunnerError as exc:
        detail = str(exc)

    if state.device_id.startswith("emulator-"):
        log_step("Package service indisponivel no emulador; reiniciando a instancia para recuperar o Android.")
        restart_emulator_instance(state, label="package_service_recovery")
        if state.visual_mode:
            keep_device_visible(state)
        return

    raise RunnerError(f"Package service do Android indisponivel no device: {detail}")


def ensure_mobile_pilot_seed_data(
    state: ExecutionState,
    *,
    inspector_email: str,
) -> None:
    script = WEB_ROOT / "scripts" / "seed_mobile_pilot_data.py"
    if not script.exists():
        raise RunnerError(f"Script de seed do piloto mobile nao encontrado: {script}")

    command = [
        resolve_web_python_binary(),
        str(script),
        "--inspetor-email",
        inspector_email,
    ]
    log_step("Garantindo seed local minimo do piloto mobile.")
    result = run_command(
        command,
        cwd=WEB_ROOT,
        timeout=120,
        stream_output=state.visual_mode,
    )
    state.commands_used.append(command_display(command))
    save_command_artifact(state.artifacts_dir / "mobile_pilot_seed.txt", result)


def capture_screenshot(state: ExecutionState, name: str) -> pathlib.Path:
    remote_path = f"{DEVICE_TMP_DIR}/{name}.png"
    local_path = state.screenshots_dir / f"{name}.png"
    try:
        capture = run_command(
            ["adb", "-s", state.device_id, "shell", "screencap", "-p", remote_path],
            check=False,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        append_note(
            state,
            f"Falha ao capturar screenshot {name}: timeout no adb screencap.",
        )
        return local_path
    if capture.returncode != 0:
        append_note(
            state,
            f"Falha ao capturar screenshot {name}: {(capture.stderr or capture.stdout).strip() or capture.returncode}",
        )
        return local_path
    pull = run_command(
        ["adb", "-s", state.device_id, "pull", remote_path, str(local_path)],
        check=False,
        timeout=20,
    )
    if pull.returncode != 0:
        append_note(
            state,
            f"Falha ao puxar screenshot {name}: {(pull.stderr or pull.stdout).strip() or pull.returncode}",
        )
    run_command(
        ["adb", "-s", state.device_id, "shell", "rm", "-f", remote_path],
        check=False,
    )
    return local_path


def capture_ui_dump(state: ExecutionState, name: str) -> pathlib.Path:
    remote_path = f"{DEVICE_TMP_DIR}/{name}.xml"
    local_path = state.ui_dumps_dir / f"{name}.xml"
    try:
        dump = run_command(
            ["adb", "-s", state.device_id, "shell", "uiautomator", "dump", remote_path],
            check=False,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        append_note(
            state,
            f"Falha ao capturar UI dump {name}: timeout no adb uiautomator dump.",
        )
        return local_path
    if dump.returncode != 0:
        append_note(
            state,
            f"Falha ao capturar UI dump {name}: {(dump.stderr or dump.stdout).strip() or dump.returncode}",
        )
        return local_path
    pull = run_command(
        ["adb", "-s", state.device_id, "pull", remote_path, str(local_path)],
        check=False,
        timeout=20,
    )
    if pull.returncode != 0:
        append_note(
            state,
            f"Falha ao puxar UI dump {name}: {(pull.stderr or pull.stdout).strip() or pull.returncode}",
        )
    run_command(["adb", "-s", state.device_id, "shell", "rm", "-f", remote_path], check=False)
    return local_path


def extract_ui_test_ids(path: pathlib.Path) -> set[str]:
    if not path.exists():
        return set()
    content = path.read_text(encoding="utf-8", errors="replace")
    return {
        item
        for item in re.findall(r'resource-id="([^"]+)"', content)
        if item and item != "android:id/content"
    }


def extract_ui_content_descs(path: pathlib.Path) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="replace")
    return [
        html.unescape(item)
        for item in re.findall(r'content-desc="([^"]*)"', content)
        if item
    ]


def extract_ui_texts(path: pathlib.Path) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="replace")
    return [
        html.unescape(item)
        for item in re.findall(r'text="([^"]*)"', content)
        if item
    ]


def detect_environment_failure_signals(
    ui_dump_path: pathlib.Path,
    *,
    screenshot_path: pathlib.Path | None = None,
    maestro_output: str = "",
) -> list[str]:
    texts = [item.lower() for item in extract_ui_texts(ui_dump_path)]
    content_descs = [item.lower() for item in extract_ui_content_descs(ui_dump_path)]
    combined = texts + content_descs
    signals: list[str] = []

    if not ui_dump_path.exists():
        signals.append("ui_dump_unavailable")
    if screenshot_path is not None and not screenshot_path.exists():
        signals.append("screenshot_unavailable")

    if any("isn't responding" in item or "nao esta respondendo" in item or "não está respondendo" in item for item in combined):
        if any("system ui" in item or "sistema ui" in item for item in combined):
            signals.append("system_ui_not_responding")
        else:
            signals.append("app_not_responding_dialog")
    if any(item in {"wait", "esperar"} or "close app" in item or "fechar app" in item for item in combined):
        signals.append("system_dialog_action_visible")
    if (
        "Assert that id: login-email-input is visible... FAILED" in maestro_output
        and not combined
    ):
        signals.append("failed_before_login_without_ui_dump")
    return sorted(set(signals))


def read_focused_activity(state: ExecutionState) -> str | None:
    command = [
        "adb",
        "-s",
        state.device_id,
        "shell",
        "dumpsys",
        "window",
        "windows",
    ]
    result = run_command(command, check=False, timeout=15)
    state.commands_used.append(command_display(command))
    output = "\n".join(
        item for item in (result.stdout.strip(), result.stderr.strip()) if item
    )
    patterns = (
        r"mCurrentFocus=Window\{[^\}]+\s([^\s]+\.[^\s/]+/[^\s\}]+)\}",
        r"mCurrentFocus=Window\{[^\}]+\s([^\s]+/[^\s\}]+)\}",
        r"mFocusedApp=.*? ([^\s]+/[^\s\}]+)\}",
    )
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)
    return None


def write_device_health_snapshot(state: ExecutionState, *, label: str) -> dict[str, Any]:
    health = probe_device_health_by_serial(state.device_id)
    focused_activity = read_focused_activity(state)
    payload = {
        "timestamp_utc": now_utc(),
        "label": label,
        "boot_completed": str(health.get("sys_boot_completed") or "") == "1",
        "boot_completed_raw": health.get("sys_boot_completed"),
        "dev_bootcomplete_raw": health.get("dev_bootcomplete"),
        "bootanim_state": health.get("bootanim_state"),
        "package_service_ready": health.get("package_service_ready"),
        "package_service_detail": health.get("package_service_detail"),
        "uptime_seconds": health.get("uptime_seconds"),
        "focused_activity": focused_activity,
    }
    write_json(state.artifacts_dir / f"{label}_device_health.json", payload)
    return payload


def stabilize_device_for_maestro(state: ExecutionState, *, label: str) -> None:
    ensure_device_package_service_ready(state)
    prime_device_for_automation(state, label=label)
    write_device_health_snapshot(state, label=label)


def recover_emulator_from_environment_failure(
    state: ExecutionState,
    *,
    reason: str,
) -> None:
    if not state.device_id.startswith("emulator-"):
        raise RunnerError(
            f"Falha ambiental detectada ({reason}), mas o device atual nao e um emulador para recovery controlado."
        )

    append_note(
        state,
        f"Falha ambiental detectada antes do fluxo funcional ({reason}); o runner reiniciou o emulador e repetira o Maestro uma vez.",
    )
    restart_emulator_instance(state, label="environment_retry")
    stabilize_device_for_maestro(state, label="post_environment_recovery")
    force_stop_app(state, label="post_environment_recovery")


def parse_probe_descriptor(content_descs: list[str], prefix: str) -> dict[str, str]:
    for descriptor in content_descs:
        if not descriptor.startswith(f"{prefix};"):
            continue
        parsed: dict[str, str] = {}
        for chunk in descriptor.split(";")[1:]:
            if "=" not in chunk:
                continue
            key, value = chunk.split("=", 1)
            parsed[key.strip()] = value.strip()
        return parsed
    return {}


def parse_selection_probe(content_descs: list[str]) -> dict[str, str]:
    return parse_probe_descriptor(content_descs, "pilot_selection_probe")


def parse_activity_center_probe(content_descs: list[str]) -> dict[str, str]:
    return parse_probe_descriptor(content_descs, "pilot_activity_center_probe")


def parse_login_probe(content_descs: list[str]) -> dict[str, str]:
    return parse_probe_descriptor(content_descs, "pilot_login_probe")


def summarize_ui_markers(ui_dump_path: pathlib.Path, target_laudo_id: int | None) -> dict[str, Any]:
    test_ids = extract_ui_test_ids(ui_dump_path)
    content_descs = extract_ui_content_descs(ui_dump_path)
    selection_probe = parse_selection_probe(content_descs)
    activity_center_probe = parse_activity_center_probe(content_descs)
    login_probe = parse_login_probe(content_descs)
    target_id = int(target_laudo_id or 0) if target_laudo_id else 0
    activity_center_terminal_state = "unknown"
    if "activity-center-terminal-state-no-request" in test_ids:
        activity_center_terminal_state = "no_request"
    elif "activity-center-terminal-state-empty" in test_ids:
        activity_center_terminal_state = "empty"
    elif "activity-center-terminal-state-loaded-legacy" in test_ids:
        activity_center_terminal_state = "loaded_legacy"
    elif "activity-center-terminal-state-loaded-v2" in test_ids:
        activity_center_terminal_state = "loaded_v2"
    elif "activity-center-terminal-state-loaded-unknown" in test_ids:
        activity_center_terminal_state = "loaded_unknown"
    elif "activity-center-terminal-state-error" in test_ids:
        activity_center_terminal_state = "error"
    elif activity_center_probe.get("terminal_state") not in (None, "", "none"):
        activity_center_terminal_state = str(activity_center_probe.get("terminal_state"))

    activity_center_state = "unknown"
    if "activity-center-state-loading" in test_ids:
        activity_center_state = "loading"
    elif activity_center_terminal_state != "unknown":
        activity_center_state = activity_center_terminal_state
    elif "activity-center-empty-state" in test_ids:
        activity_center_state = "empty"

    activity_center_delivery_mode = "unknown"
    if "activity-center-feed-v2-served" in test_ids:
        activity_center_delivery_mode = "v2"
    elif "activity-center-feed-legacy-served" in test_ids:
        activity_center_delivery_mode = "legacy"
    elif "activity-center-request-not-started" in test_ids:
        activity_center_delivery_mode = "not_started"
    elif activity_center_probe.get("delivery"):
        activity_center_delivery_mode = str(activity_center_probe.get("delivery"))

    activity_center_request_dispatched = bool(
        "activity-center-request-dispatched" in test_ids
        or activity_center_probe.get("request_dispatched") == "true"
    )
    activity_center_request_not_started = bool(
        "activity-center-request-not-started" in test_ids
        or activity_center_terminal_state == "no_request"
        or activity_center_probe.get("request_dispatched") == "false"
    )
    requested_targets_raw = str(activity_center_probe.get("requested_targets") or "")
    activity_center_requested_targets = sorted(
        {
            int(item)
            for item in requested_targets_raw.split(",")
            if item.isdigit() and int(item) > 0
        }
        | {
            int(match.group(1))
            for match in (
                re.match(r"activity-center-request-target-(\d+)$", test_id)
                for test_id in test_ids
            )
            if match
        }
    )
    activity_center_skip_reason = "none"
    if "activity-center-skip-already-monitoring" in test_ids:
        activity_center_skip_reason = "already_monitoring"
    elif "activity-center-skip-network-blocked" in test_ids:
        activity_center_skip_reason = "network_blocked"
    elif "activity-center-skip-no-target" in test_ids:
        activity_center_skip_reason = "no_target"
    elif activity_center_probe.get("skip_reason") not in (None, "", "none"):
        activity_center_skip_reason = str(activity_center_probe.get("skip_reason"))

    request_status_raw = str(activity_center_probe.get("request_status") or "").strip()
    activity_center_request_status = (
        int(request_status_raw)
        if request_status_raw.isdigit()
        else None
    )
    request_attempt_sequence_raw = str(
        activity_center_probe.get("request_attempt_sequence") or ""
    ).strip()
    activity_center_request_attempt_sequence = [
        item
        for item in request_attempt_sequence_raw.split("|")
        if item and item != "none"
    ]
    activity_center_request_phase = str(
        activity_center_probe.get("request_phase") or "not_created"
    ).strip() or "not_created"
    activity_center_request_trace_id = (
        str(activity_center_probe.get("request_trace_id") or "").strip() or None
    )
    activity_center_request_flag_enabled = (
        str(activity_center_probe.get("request_flag_enabled") or "").strip()
        or "unknown"
    )
    activity_center_request_flag_raw_value = (
        str(activity_center_probe.get("request_flag_raw_value") or "").strip()
        or None
    )
    activity_center_request_flag_source = (
        str(activity_center_probe.get("request_flag_source") or "").strip()
        or None
    )
    activity_center_request_route_decision = (
        str(activity_center_probe.get("request_route_decision") or "").strip()
        or "unknown"
    )
    activity_center_request_decision_reason = (
        str(activity_center_probe.get("request_decision_reason") or "").strip()
        or None
    )
    activity_center_request_decision_source = (
        str(activity_center_probe.get("request_decision_source") or "").strip()
        or None
    )
    activity_center_request_actual_route = (
        str(activity_center_probe.get("request_actual_route") or "").strip()
        or "unknown"
    )
    activity_center_request_endpoint_path = (
        str(activity_center_probe.get("request_endpoint_path") or "").strip() or None
    )
    activity_center_request_failure_kind = (
        str(activity_center_probe.get("request_failure_kind") or "").strip() or None
    )
    activity_center_request_fallback_reason = (
        str(activity_center_probe.get("request_fallback_reason") or "").strip()
        or None
    )
    activity_center_request_backend_request_id = (
        str(activity_center_probe.get("request_backend_request_id") or "").strip()
        or None
    )
    activity_center_request_validation_session = (
        str(activity_center_probe.get("request_validation_session") or "").strip()
        or None
    )
    activity_center_request_operator_run = (
        str(activity_center_probe.get("request_operator_run") or "").strip() or None
    )
    runtime_flag_enabled = (
        str(selection_probe.get("runtime_flag_enabled") or "").strip() or "unknown"
    )
    runtime_flag_raw_value = (
        str(selection_probe.get("runtime_flag_raw_value") or "").strip() or None
    )
    runtime_flag_source = (
        str(selection_probe.get("runtime_flag_source") or "").strip() or None
    )
    login_stage = str(login_probe.get("stage") or "").strip() or "unknown"
    login_status_api = str(login_probe.get("status_api") or "").strip() or "unknown"
    login_entrando = str(login_probe.get("entrando") or "").strip() == "1"
    login_carregando = str(login_probe.get("carregando") or "").strip() == "1"
    login_error = str(login_probe.get("erro") or "").strip() or None

    selection_callback_fired = bool(
        target_id
        and (
            f"history-selection-callback-fired-{target_id}" in test_ids
            or selection_probe.get("callback_fired") == str(target_id)
        )
    )
    selection_callback_completed = bool(
        target_id
        and (
            f"history-selection-callback-completed-{target_id}" in test_ids
            or selection_probe.get("callback_completed") == str(target_id)
        )
    )
    selection_lost = bool(
        target_id
        and (
            f"authenticated-shell-selection-lost-{target_id}" in test_ids
            or selection_probe.get("selection_lost") == str(target_id)
        )
    )
    selected_target_id = bool(
        target_id
        and (
            f"selected-history-item-id-{target_id}" in test_ids
            or f"authenticated-shell-selected-laudo-id-{target_id}" in test_ids
            or selection_probe.get("selected_laudo_id") == str(target_id)
        )
    )
    shell_selection_ready = bool(
        target_id
        and (
            f"authenticated-shell-selection-ready-{target_id}" in test_ids
            or selection_probe.get("selection_ready") == str(target_id)
        )
    )

    return {
        "selected_history_item_marker": "selected-history-item-marker" in test_ids,
        "selected_history_item_none": "selected-history-item-none" in test_ids,
        "selected_target_id": selected_target_id,
        "selection_callback_fired": selection_callback_fired,
        "selection_callback_completed": selection_callback_completed,
        "shell_selection_ready": shell_selection_ready,
        "selection_lost": selection_lost,
        "history_target_visible": bool(
            target_id and f"history-target-visible-{target_id}" in test_ids
        ),
        "activity_center_modal": "activity-center-modal" in test_ids,
        "activity_center_state": activity_center_state,
        "activity_center_terminal_state": activity_center_terminal_state,
        "activity_center_request_dispatched": activity_center_request_dispatched,
        "activity_center_request_not_started": activity_center_request_not_started,
        "activity_center_requested_targets": activity_center_requested_targets,
        "activity_center_target_requested": bool(
            target_id
            and (
                f"activity-center-request-target-{target_id}" in test_ids
                or target_id in activity_center_requested_targets
            )
        ),
        "activity_center_delivery_mode": activity_center_delivery_mode,
        "activity_center_skip_reason": activity_center_skip_reason,
        "activity_center_request_phase": activity_center_request_phase,
        "activity_center_request_trace_id": activity_center_request_trace_id,
        "activity_center_request_flag_enabled": activity_center_request_flag_enabled,
        "activity_center_request_flag_raw_value": activity_center_request_flag_raw_value,
        "activity_center_request_flag_source": activity_center_request_flag_source,
        "activity_center_request_route_decision": activity_center_request_route_decision,
        "activity_center_request_decision_reason": activity_center_request_decision_reason,
        "activity_center_request_decision_source": activity_center_request_decision_source,
        "activity_center_request_actual_route": activity_center_request_actual_route,
        "activity_center_request_attempt_sequence": activity_center_request_attempt_sequence,
        "activity_center_request_endpoint_path": activity_center_request_endpoint_path,
        "activity_center_request_status": activity_center_request_status,
        "activity_center_request_failure_kind": activity_center_request_failure_kind,
        "activity_center_request_fallback_reason": activity_center_request_fallback_reason,
        "activity_center_request_backend_request_id": activity_center_request_backend_request_id,
        "activity_center_request_validation_session": activity_center_request_validation_session,
        "activity_center_request_operator_run": activity_center_request_operator_run,
        "login_stage": login_stage,
        "login_status_api": login_status_api,
        "login_entrando": login_entrando,
        "login_carregando": login_carregando,
        "login_error": login_error,
        "runtime_flag_enabled": runtime_flag_enabled,
        "runtime_flag_raw_value": runtime_flag_raw_value,
        "runtime_flag_source": runtime_flag_source,
        "activity_center_target_v2": bool(
            target_id and f"activity-center-feed-v2-target-{target_id}" in test_ids
        ),
        "thread_surface_visible": "mesa-thread-surface" in test_ids,
        "thread_loaded_visible": "mesa-thread-loaded" in test_ids,
        "thread_empty_visible": "mesa-thread-empty-state" in test_ids,
        "login_probe": login_probe,
        "selection_probe": selection_probe,
        "activity_center_probe": activity_center_probe,
        "raw_content_descs": sorted(content_descs),
        "raw_test_ids": sorted(test_ids),
        "ui_dump_path": str(ui_dump_path),
    }


def start_logcat_capture(state: ExecutionState) -> None:
    run_command(["adb", "-s", state.device_id, "logcat", "-c"], check=False)
    full_log_path = state.artifacts_dir / "logcat_full.txt"
    handle = full_log_path.open("w", encoding="utf-8")
    state.logcat_process = subprocess.Popen(
        ["adb", "-s", state.device_id, "logcat", "-v", "time"],
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )


def stop_logcat_capture(state: ExecutionState) -> None:
    if not state.logcat_process:
        return
    process = state.logcat_process
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    finally:
        state.logcat_process = None


def write_logcat_excerpt(state: ExecutionState) -> None:
    full_path = state.artifacts_dir / "logcat_full.txt"
    excerpt_path = state.artifacts_dir / "logcat_excerpt.txt"
    if not full_path.exists():
        write_text(excerpt_path, "logcat_full.txt não foi gerado.\n")
        return
    pattern = re.compile(r"(tariel|expo|fallback|validation|mobile|v2)", re.IGNORECASE)
    lines = [
        line.rstrip()
        for line in full_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if pattern.search(line)
    ]
    write_text(excerpt_path, "\n".join(lines[-400:]).strip() + ("\n" if lines else ""))


def build_mobile_request(
    path: str,
    *,
    token: str | None = None,
    method: str = "GET",
    data: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
) -> urllib.request.Request:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    return urllib.request.Request(
        f"http://127.0.0.1:8000{path}",
        data=data,
        headers=headers,
        method=method,
    )


def read_json_response(request: urllib.request.Request, opener: Any | None = None) -> dict[str, Any]:
    if opener is None:
        response = urllib.request.urlopen(request, timeout=20)
    else:
        response = opener.open(request, timeout=20)
    with response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def login_mobile(email: str, password: str) -> dict[str, Any]:
    payload = json.dumps({"email": email, "senha": password, "lembrar": False}).encode("utf-8")
    request = build_mobile_request(
        "/app/api/mobile/auth/login",
        method="POST",
        data=payload,
        extra_headers={"Content-Type": "application/json"},
    )
    return read_json_response(request)


def build_admin_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def admin_login(opener: urllib.request.OpenerDirector, email: str, password: str) -> None:
    with opener.open("http://127.0.0.1:8000/admin/login", timeout=20) as response:
        html_body = response.read().decode("utf-8")
    csrf_token = extract_csrf_token(html_body)

    payload = urllib.parse.urlencode(
        {
            "email": email,
            "senha": password,
            "csrf_token": csrf_token,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:8000/admin/login",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with opener.open(request, timeout=20) as response:
        final_url = response.geturl()
        final_body = response.read().decode("utf-8", errors="replace")

    if final_url.endswith("/admin/mfa/setup"):
        final_url = submit_admin_mfa(
            opener,
            path="/admin/mfa/setup",
            html_body=final_body,
            email=email,
        )
    elif final_url.endswith("/admin/mfa/challenge"):
        final_url = submit_admin_mfa(
            opener,
            path="/admin/mfa/challenge",
            html_body=final_body,
            email=email,
        )

    if not final_url.endswith("/admin/painel"):
        raise RunnerError(f"Login admin não concluiu no painel: {final_url}")


def admin_json(
    opener: urllib.request.OpenerDirector,
    path: str,
    *,
    method: str = "GET",
    query: str = "",
) -> dict[str, Any]:
    suffix = f"?{query}" if query else ""
    request = urllib.request.Request(
        f"http://127.0.0.1:8000{path}{suffix}",
        method=method,
        headers={"Accept": "application/json"},
    )
    return read_json_response(request, opener=opener)


def save_http_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)


def detect_installed_package(state: ExecutionState) -> bool:
    result = run_command(
        [
            "adb",
            "-s",
            state.device_id,
            "shell",
            "cmd",
            "package",
            "resolve-activity",
            "--brief",
            state.package_name,
        ],
        check=False,
        timeout=15,
    )
    return result.returncode == 0 and state.package_name in (result.stdout + result.stderr)


def install_failure_is_environmental(result: CommandResult) -> bool:
    output = "\n".join((result.stdout or "", result.stderr or "")).lower()
    signals = (
        "can't find service: package",
        "device offline",
        "device not found",
        "more than one device/emulator",
        "broken pipe",
        "closed",
        "timeout",
        "failed to commit install session",
    )
    return any(signal in output for signal in signals)


def install_or_reuse_app(state: ExecutionState, package_info: dict[str, Any]) -> None:
    if state.visual_mode and not force_mobile_install() and detect_installed_package(state):
        state.build_used_existing_install = True
        append_note(
            state,
            "Package Android ja instalado no device; runner local visual reutilizou a instalacao existente.",
        )
        return

    env = os.environ.copy()
    env["ANDROID_PREVIEW_CLEAN"] = "1"
    env["EXPO_PUBLIC_API_BASE_URL"] = LOCAL_MOBILE_API_BASE_URL
    env["EXPO_PUBLIC_AUTH_WEB_BASE_URL"] = LOCAL_MOBILE_API_BASE_URL
    env["EXPO_PUBLIC_MOBILE_AUTOMATION_DIAGNOSTICS"] = "1"
    append_note(
        state,
        "Build Android executado com EXPO_PUBLIC_MOBILE_AUTOMATION_DIAGNOSTICS=1 para materializar o probe de selecao no shell autenticado.",
    )
    append_note(
        state,
        f"Build Android forçado para API local {LOCAL_MOBILE_API_BASE_URL} com limpeza fria do preview para evitar bundle stale.",
    )
    command = ["npm", "run", package_info["preferred_install_script"]]
    for attempt in (1, 2):
        install_log = state.artifacts_dir / (
            "android_install.log" if attempt == 1 else f"android_install_retry_{attempt}.log"
        )
        state.commands_used.append(command_display(command))
        log_step(
            f"Instalando/atualizando o app Android via {package_info['preferred_install_script']} (tentativa {attempt}/2)."
        )
        record_phase_event(
            state,
            phase="install",
            status="running",
            detail=f"attempt={attempt}",
        )
        result = run_command(
            command,
            cwd=ANDROID_ROOT,
            env=env,
            timeout=1800,
            check=False,
            stream_output=state.visual_mode,
        )
        write_text(
            install_log,
            "\n".join(
                [
                    f"$ {command_display(command)}",
                    "",
                    "[stdout]",
                    result.stdout.strip(),
                    "",
                    "[stderr]",
                    result.stderr.strip(),
                    "",
                    f"[returncode] {result.returncode}",
                ]
            )
            .strip()
            + "\n",
        )

        if result.returncode == 0:
            record_phase_event(
                state,
                phase="install",
                status="ok",
                detail=f"attempt={attempt}",
            )
            return

        if detect_installed_package(state):
            state.build_used_existing_install = True
            append_note(
                state,
                "Build/instalação Android falhou, mas o package já estava instalado; o runner seguiu com a instalação existente.",
            )
            record_phase_event(
                state,
                phase="install",
                status="warn",
                detail=f"attempt={attempt} reused_existing_install",
            )
            return

        environmental_failure = install_failure_is_environmental(result)
        record_phase_event(
            state,
            phase="install",
            status="fail",
            detail=f"attempt={attempt} environmental={str(environmental_failure).lower()}",
        )
        if (
            attempt == 1
            and environmental_failure
            and state.device_id.startswith("emulator-")
        ):
            wipe_data = should_wipe_emulator_on_install_recovery()
            append_note(
                state,
                "Falha ambiental na instalação Android detectada; o runner reiniciou o emulador e repetira a instalação uma única vez.",
            )
            restart_emulator_instance(
                state,
                label="install_environment_recovery",
                wipe_data=wipe_data,
            )
            stabilize_device_for_maestro(
                state,
                label="post_install_environment_recovery",
            )
            continue

        raise RunnerError("Não foi possível instalar o app Android no device.")


def force_stop_app(state: ExecutionState, *, label: str) -> None:
    if not state.device_id or not state.package_name:
        return

    command = [
        "adb",
        "-s",
        state.device_id,
        "shell",
        "am",
        "force-stop",
        state.package_name,
    ]
    state.commands_used.append(command_display(command))
    try:
        result = run_command(
            command,
            check=False,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        append_note(
            state,
            f"Force-stop do pacote {state.package_name} excedeu timeout ({label}); o runner tentou recuperacao leve e repetiu o comando.",
        )
        ensure_device_package_service_ready(state)
        prime_device_for_automation(state, label=f"{label}_force_stop_recovery")
        result = run_command(
            command,
            check=False,
            timeout=30,
        )
    save_command_artifact(state.artifacts_dir / f"{label}_force_stop.txt", result)
    if result.returncode == 0:
        append_note(
            state,
            f"Processo Android do pacote {state.package_name} encerrado antes da rodada ativa ({label}).",
        )
        return
    append_note(
        state,
        f"Falha ao encerrar o pacote {state.package_name} antes da rodada ativa ({label}); o runner seguiu mesmo assim.",
    )


def launch_app(state: ExecutionState) -> None:
    activity_name = state.main_activity
    if not str(activity_name).startswith("."):
        activity_name = f".{str(activity_name).split('.')[-1]}"
    activity_spec = f"{state.package_name}/{activity_name}"

    primary_command = [
        "adb",
        "-s",
        state.device_id,
        "shell",
        "am",
        "start",
        "-W",
        "-n",
        activity_spec,
    ]
    primary_timed_out = False
    try:
        primary_result = run_command(
            primary_command,
            check=False,
            timeout=20,
        )
        state.commands_used.append(command_display(primary_command))

        combined_output = "\n".join(
            item.strip()
            for item in (primary_result.stdout, primary_result.stderr)
            if item.strip()
        )
        if primary_result.returncode == 0 and "Error:" not in combined_output:
            save_command_artifact(state.artifacts_dir / "app_launch.txt", primary_result)
            return
    except subprocess.TimeoutExpired:
        primary_timed_out = True
        primary_result = CommandResult(
            command=primary_command,
            returncode=124,
            stdout="",
            stderr="timeout",
        )
        append_note(
            state,
            "Launch primario via am start excedeu timeout; tentando fallback via monkey.",
        )
        state.commands_used.append(command_display(primary_command))

    fallback_command = [
        "adb",
        "-s",
        state.device_id,
        "shell",
        "monkey",
        "-p",
        state.package_name,
        "-c",
        "android.intent.category.LAUNCHER",
        "1",
    ]
    fallback_timed_out = False
    try:
        fallback_result = run_command(
            fallback_command,
            check=False,
            timeout=15,
        )
        state.commands_used.append(command_display(fallback_command))
    except subprocess.TimeoutExpired:
        fallback_timed_out = True
        fallback_result = CommandResult(
            command=fallback_command,
            returncode=124,
            stdout="",
            stderr="timeout",
        )
        append_note(
            state,
            "Launch fallback via monkey excedeu timeout; seguindo para o Maestro assim mesmo.",
        )
        state.commands_used.append(command_display(fallback_command))
    write_text(
        state.artifacts_dir / "app_launch.txt",
        "\n".join(
            [
                f"$ {command_display(primary_command)}",
                "",
                "[primary stdout]",
                primary_result.stdout.strip(),
                "",
                "[primary stderr]",
                primary_result.stderr.strip(),
                "",
                f"[primary returncode] {primary_result.returncode}",
                f"[primary timeout] {primary_timed_out}",
                "",
                f"$ {command_display(fallback_command)}",
                "",
                "[fallback stdout]",
                fallback_result.stdout.strip(),
                "",
                "[fallback stderr]",
                fallback_result.stderr.strip(),
                "",
                f"[fallback returncode] {fallback_result.returncode}",
                f"[fallback timeout] {fallback_timed_out}",
            ]
        ).strip()
        + "\n",
    )
    if fallback_result.returncode != 0:
        append_note(
            state,
            "Runner nao confirmou a abertura previa do app; o fluxo seguiu e delegou o launch ao Maestro.",
        )


def run_maestro_flow(state: ExecutionState, mobile_password: str) -> CommandResult:
    if not state.target_laudo_id or state.target_laudo_id <= 0:
        raise RunnerError("Operator run não expôs um target de thread válido para o Maestro.")
    command = [
        "maestro",
        "test",
        "--device",
        state.device_id,
        "--debug-output",
        str(state.maestro_debug_dir),
        "--test-output-dir",
        str(state.screenshots_dir),
        str(FLOW_PATH),
    ]
    env = os.environ.copy()
    env["MAESTRO_LOGIN_EMAIL"] = state.mobile_email
    env["MAESTRO_LOGIN_PASSWORD"] = mobile_password
    env["MAESTRO_TARGET_LAUDO_ID"] = str(state.target_laudo_id)
    state.commands_used.append(command_display(command))
    log_step(
        f"Executando o flow Maestro no device Android ({'visual' if state.visual_mode else 'headless'})."
    )
    state.maestro_attempts += 1
    result = run_command(
        command,
        env=env,
        timeout=600,
        check=False,
        stream_output=state.visual_mode,
    )
    output = result.stdout or ""
    state.maestro_target_tap_completed = (
        "Tap on id: history-item-${TARGET_LAUDO_ID}... COMPLETED" in output
        or f"Tap on id: history-item-{state.target_laudo_id}... COMPLETED" in output
    )
    state.maestro_selection_callback_confirmed = (
        "Assert that id: history-selection-callback-fired-${TARGET_LAUDO_ID} is visible... COMPLETED"
        in output
        or f"Assert that id: history-selection-callback-fired-{state.target_laudo_id} is visible... COMPLETED"
        in output
    )
    state.maestro_shell_selection_confirmed = (
        "Assert that id: authenticated-shell-selection-ready-${TARGET_LAUDO_ID} is visible... COMPLETED"
        in output
        or f"Assert that id: authenticated-shell-selection-ready-{state.target_laudo_id} is visible... COMPLETED"
        in output
    )
    state.maestro_selection_callback_wait_failed = (
        "Assert that id: history-selection-callback-fired-${TARGET_LAUDO_ID} is visible... FAILED"
        in output
        or f"Assert that id: history-selection-callback-fired-{state.target_laudo_id} is visible... FAILED"
        in output
    )
    state.maestro_shell_selection_wait_failed = (
        "Assert that id: authenticated-shell-selection-ready-${TARGET_LAUDO_ID} is visible... FAILED"
        in output
        or f"Assert that id: authenticated-shell-selection-ready-{state.target_laudo_id} is visible... FAILED"
        in output
    )
    state.maestro_activity_center_terminal_confirmed = (
        "Assert that id: activity-center-terminal-state is visible... COMPLETED"
        in output
    )
    state.maestro_activity_center_v2_confirmed = (
        "Run flow when id: activity-center-feed-v2-served is visible... COMPLETED"
        in output
        or "Assert that id: activity-center-feed-v2-target-${TARGET_LAUDO_ID} is visible... COMPLETED"
        in output
        or (
            state.target_laudo_id is not None
            and f"Assert that id: activity-center-feed-v2-target-{state.target_laudo_id} is visible... COMPLETED"
            in output
        )
    )
    save_command_artifact(state.artifacts_dir / "maestro_run.txt", result)
    state.flow_ran = True
    return result


def resolve_operator_thread_target_id(
    operator_status: dict[str, Any] | None,
) -> int | None:
    status_payload = operator_status or {}
    run_payload = status_payload.get("operator_run") or {}
    required_targets = run_payload.get("required_targets") or []
    for item in required_targets:
        if str(item.get("surface") or "") != "thread":
            continue
        try:
            target_id = int(item.get("target_id"))
        except (TypeError, ValueError):
            continue
        if target_id > 0:
            return target_id
    return None


def resolve_operator_run_session_id(state: ExecutionState) -> str | None:
    for payload in (
        state.operator_status_before,
        state.operator_status_after,
        state.capabilities_before,
        state.capabilities_after,
    ):
        if not payload:
            continue
        for key in ("operator_run_session_id", "organic_validation_session_id"):
            value = str(payload.get(key) or "").strip()
            if value:
                return value
        run_payload = payload.get("operator_run") or {}
        value = str(run_payload.get("session_id") or "").strip()
        if value:
            return value
    return None


def resolve_operator_run_id(state: ExecutionState) -> str | None:
    for payload in (
        state.operator_status_before,
        state.operator_status_after,
        state.capabilities_before,
        state.capabilities_after,
    ):
        if not payload:
            continue
        for key in ("operator_run_id", "operator_validation_run_id"):
            value = str(payload.get(key) or "").strip()
            if value:
                return value
        run_payload = payload.get("operator_run") or {}
        value = str(run_payload.get("operator_run_id") or "").strip()
        if value:
            return value
    return None


def resolve_capabilities_version(state: ExecutionState) -> str | None:
    for payload in (state.capabilities_before, state.capabilities_after):
        if not payload:
            continue
        value = str(payload.get("capabilities_version") or "").strip()
        if value:
            return value
    return None


def resolve_rollout_bucket(state: ExecutionState) -> str | None:
    for payload in (state.capabilities_before, state.capabilities_after):
        if not payload:
            continue
        value = payload.get("rollout_bucket")
        if isinstance(value, int):
            return str(value)
        raw = str(value or "").strip()
        if raw:
            return raw
    return None


def post_mobile_human_ack(
    state: ExecutionState,
    *,
    surface: str,
    target_id: int,
) -> dict[str, Any]:
    session_id = resolve_operator_run_session_id(state)
    operator_run_id = resolve_operator_run_id(state)
    if not session_id:
        raise RunnerError("Sessão orgânica do operator run não foi resolvida para registrar human ack.")
    if not state.mobile_token:
        raise RunnerError("Token mobile ausente para registrar human ack.")

    payload = json.dumps(
        {
            "session_id": session_id,
            "surface": surface,
            "target_id": int(target_id),
            "checkpoint_kind": "rendered",
            "delivery_mode": "v2",
            "operator_run_id": operator_run_id,
        }
    ).encode("utf-8")
    extra_headers = {
        "Content-Type": "application/json",
        "X-Tariel-Mobile-Validation-Session": session_id,
    }
    capabilities_version = resolve_capabilities_version(state)
    rollout_bucket = resolve_rollout_bucket(state)
    if capabilities_version:
        extra_headers["X-Tariel-Mobile-V2-Capabilities-Version"] = capabilities_version
    if rollout_bucket:
        extra_headers["X-Tariel-Mobile-V2-Rollout-Bucket"] = rollout_bucket
    if operator_run_id:
        extra_headers["X-Tariel-Mobile-Operator-Run"] = operator_run_id

    request = build_mobile_request(
        "/app/api/mobile/v2/organic-validation/ack",
        token=state.mobile_token,
        method="POST",
        data=payload,
        extra_headers=extra_headers,
    )
    return read_json_response(request)


def record_human_acks_from_ui(state: ExecutionState) -> None:
    target_id = state.target_laudo_id
    if not target_id:
        return
    ui_summary = state.ui_marker_summary or {}
    ack_conditions = {
        "feed": bool(
            state.maestro_activity_center_v2_confirmed
            or ui_summary.get("activity_center_delivery_mode") == "v2"
            or ui_summary.get("activity_center_target_v2")
        ),
        "thread": bool(
            state.maestro_shell_selection_confirmed
            or ui_summary.get("shell_selection_ready")
            or ui_summary.get("thread_surface_visible")
        ),
    }
    for surface, should_ack in ack_conditions.items():
        if not should_ack:
            continue
        try:
            payload = post_mobile_human_ack(
                state,
                surface=surface,
                target_id=int(target_id),
            )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            write_text(
                state.artifacts_dir / f"human_ack_{surface}_error.txt",
                body or f"HTTP {exc.code}\n",
            )
            append_note(
                state,
                f"Falha ao registrar human ack de {surface}: HTTP {exc.code}.",
            )
            continue
        except Exception as exc:
            write_text(
                state.artifacts_dir / f"human_ack_{surface}_error.txt",
                f"{exc}\n",
            )
            append_note(state, f"Falha ao registrar human ack de {surface}: {exc}")
            continue
        save_http_json(state.artifacts_dir / f"human_ack_{surface}.json", payload)
        duplicate = bool(payload.get("duplicate"))
        append_note(
            state,
            f"Human ack de {surface} registrado para o laudo {target_id} ({'duplicate' if duplicate else 'accepted'}).",
        )


def summarize_surface_coverage(summary: dict[str, Any]) -> tuple[bool, bool]:
    feed = False
    thread = False
    for row in summary.get("tenant_surface_states") or []:
        if str(row.get("tenant_key")) != "1":
            continue
        surface = str(row.get("surface") or "")
        completed = bool(row.get("operator_run_surface_completed"))
        human_met = bool(row.get("human_confirmed_required_coverage_met"))
        if surface == "feed" and (completed or human_met):
            feed = True
        if surface == "thread" and (completed or human_met):
            thread = True
    return feed, thread


def extract_backend_evidence(summary: dict[str, Any] | None) -> dict[str, Any]:
    payload = summary or {}
    tenant_payload = payload.get("first_promoted_tenant") or {}
    return {
        "recent_events": payload.get("recent_events") or [],
        "request_traces_recent": payload.get("request_traces_recent") or [],
        "human_ack_recent_events": payload.get("human_ack_recent_events")
        or tenant_payload.get("human_ack_recent_events")
        or [],
        "human_confirmed_targets": payload.get("human_confirmed_targets")
        or tenant_payload.get("human_confirmed_targets")
        or {},
    }


def find_backend_request_traces(
    summary: dict[str, Any] | None,
    trace_id: str | None,
) -> list[dict[str, Any]]:
    resolved_trace_id = str(trace_id or "").strip()
    if not resolved_trace_id:
        return []
    backend_evidence = extract_backend_evidence(summary)
    return [
        item
        for item in backend_evidence.get("request_traces_recent") or []
        if str(item.get("trace_id") or "").strip() == resolved_trace_id
    ]


def extract_app_request_trace_summary(ui_summary: dict[str, Any] | None) -> dict[str, Any]:
    payload = ui_summary or {}
    return {
        "runtime_flag_enabled": payload.get("runtime_flag_enabled"),
        "runtime_flag_raw_value": payload.get("runtime_flag_raw_value"),
        "runtime_flag_source": payload.get("runtime_flag_source"),
        "request_trace_id": payload.get("activity_center_request_trace_id"),
        "request_phase": payload.get("activity_center_request_phase"),
        "request_flag_enabled": payload.get("activity_center_request_flag_enabled"),
        "request_flag_raw_value": payload.get("activity_center_request_flag_raw_value"),
        "request_flag_source": payload.get("activity_center_request_flag_source"),
        "request_route_decision": payload.get("activity_center_request_route_decision"),
        "request_decision_reason": payload.get("activity_center_request_decision_reason"),
        "request_decision_source": payload.get("activity_center_request_decision_source"),
        "request_actual_route": payload.get("activity_center_request_actual_route"),
        "request_attempt_sequence": payload.get("activity_center_request_attempt_sequence"),
        "request_endpoint_path": payload.get("activity_center_request_endpoint_path"),
        "request_status": payload.get("activity_center_request_status"),
        "request_failure_kind": payload.get("activity_center_request_failure_kind"),
        "request_fallback_reason": payload.get("activity_center_request_fallback_reason"),
        "request_backend_request_id": payload.get("activity_center_request_backend_request_id"),
        "request_validation_session": payload.get("activity_center_request_validation_session"),
        "request_operator_run": payload.get("activity_center_request_operator_run"),
    }


def wait_for_backend_evidence(
    opener: urllib.request.OpenerDirector,
    state: ExecutionState,
    *,
    timeout_seconds: int = 18,
    poll_seconds: int = 2,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    deadline = time.time() + max(timeout_seconds, poll_seconds)
    last_summary: dict[str, Any] | None = None
    last_status: dict[str, Any] | None = None

    while time.time() < deadline:
        last_status = admin_json(
            opener,
            "/admin/api/mobile-v2-rollout/operator-run/status",
        )
        last_summary = admin_json(opener, "/admin/api/mobile-v2-rollout/summary")
        feed_covered, thread_covered = summarize_surface_coverage(last_summary)
        if feed_covered and thread_covered:
            break
        time.sleep(poll_seconds)

    return last_summary, last_status


def finish_operator_run(
    opener: urllib.request.OpenerDirector,
    state: ExecutionState,
    *,
    abort: bool,
) -> dict[str, Any]:
    query = "abort=1" if abort else ""
    payload = admin_json(
        opener,
        "/admin/api/mobile-v2-rollout/operator-run/finish",
        method="POST",
        query=query,
    )
    state.operator_run_finished = True
    return payload


def evaluate_result(state: ExecutionState) -> str:
    if not state.device_id:
        return "blocked_no_device"
    if not state.summary_after:
        return "partial_execution"
    operator_outcome = (
        state.operator_status_after or {}
    ).get("operator_run_outcome") or state.operator_run_outcome
    backend_evidence = extract_backend_evidence(state.summary_after)
    ui_summary = state.ui_marker_summary or {}
    request_trace_id = str(
        ui_summary.get("activity_center_request_trace_id") or ""
    ).strip() or None
    request_phase = str(
        ui_summary.get("activity_center_request_phase") or "not_created"
    ).strip() or "not_created"
    backend_request_traces = find_backend_request_traces(
        state.summary_after,
        request_trace_id,
    )
    backend_request_counted_kinds = {
        str(item.get("counted_kind") or "").strip()
        for item in backend_request_traces
        if str(item.get("counted_kind") or "").strip()
    }
    backend_request_delivery_paths = {
        str(item.get("delivery_path") or "").strip()
        for item in backend_request_traces
        if str(item.get("delivery_path") or "").strip()
    }
    request_flag_enabled = str(
        ui_summary.get("activity_center_request_flag_enabled") or "unknown"
    ).strip()
    runtime_flag_enabled = str(
        ui_summary.get("runtime_flag_enabled") or "unknown"
    ).strip()
    request_route_decision = str(
        ui_summary.get("activity_center_request_route_decision") or "unknown"
    ).strip()
    request_actual_route = str(
        ui_summary.get("activity_center_request_actual_route") or "unknown"
    ).strip()
    activity_center_terminal_state = str(
        ui_summary.get("activity_center_terminal_state") or "unknown"
    )
    if ui_summary.get("selection_lost"):
        return "selection_lost_after_update"
    saw_v2_or_ack_evidence = bool(
        int(((state.summary_after.get("totals") or {}).get("v2_served") or 0)) > 0
        or backend_evidence["human_ack_recent_events"]
    )
    if state.feed_covered and state.thread_covered:
        if operator_outcome == "completed_successfully":
            return "success_human_confirmed"
        return "partial_execution"
    if (
        state.flow_ran
        and state.feed_covered
        and runtime_flag_enabled == "true"
        and (
            state.maestro_activity_center_v2_confirmed
            or ui_summary.get("activity_center_delivery_mode") == "v2"
            or ui_summary.get("activity_center_target_v2")
        )
    ):
        return "request_received_backend_v2"
    if state.flow_ran and state.feed_covered:
        return "feed_only_confirmed"
    if state.flow_ran and state.thread_covered:
        return "thread_only_confirmed"
    if ui_summary.get("activity_center_modal"):
        if request_flag_enabled == "false":
            return "flag_runtime_false"
        if (
            request_flag_enabled == "true"
            and request_route_decision == "legacy"
            and request_actual_route == "legacy"
        ):
            return "flag_runtime_true_but_gate_denied"
        if request_actual_route == "v2":
            if backend_request_traces:
                return "request_received_backend_v2"
            return "v2_route_selected"
        if request_phase == "intent_created":
            return "request_created_not_sent"
        if request_phase in {
            "request_sent",
            "response_received",
            "request_failed",
            "request_cancelled",
        } and request_trace_id and not backend_request_traces:
            return "request_sent_not_received_backend"
        if "legacy" in backend_request_delivery_paths:
            return "request_received_backend_legacy_only"
        if "v2" in backend_request_delivery_paths and (
            "v2_served" not in backend_request_counted_kinds
            or ui_summary.get("activity_center_delivery_mode") == "unknown"
        ):
            return "request_received_backend_v2_but_no_metadata"
        if activity_center_terminal_state == "no_request":
            return "central_no_request_fired"
        if activity_center_terminal_state == "empty":
            return "central_loaded_empty"
        if activity_center_terminal_state == "loaded_legacy":
            return "central_loaded_legacy"
        if activity_center_terminal_state == "loaded_v2":
            return "central_loaded_v2"
        if activity_center_terminal_state == "error":
            return "central_error"
        if (
            state.maestro_activity_center_terminal_confirmed
            or ui_summary.get("activity_center_state") == "loading"
        ):
            return "central_unknown_terminal_state"
    if (
        state.maestro_shell_selection_confirmed
        or ui_summary.get("shell_selection_ready")
        or ui_summary.get("selected_target_id")
    ):
        return "selected_laudo_confirmed"
    if state.maestro_target_tap_completed and state.maestro_selection_callback_wait_failed:
        return "target_tapped_but_callback_not_fired"
    if (
        (
            state.maestro_selection_callback_confirmed
            or state.maestro_target_tap_completed
        )
        and (
            ui_summary.get("selection_callback_fired")
            or ui_summary.get("selection_callback_completed")
            or state.maestro_selection_callback_confirmed
            or state.maestro_shell_selection_wait_failed
        )
    ):
        return "callback_fired_but_shell_not_updated"
    if state.flow_ran and operator_outcome == "completed_inconclusive" and saw_v2_or_ack_evidence:
        return "blocked_backend_accounting"
    if state.flow_ran and operator_outcome == "completed_inconclusive":
        return "thread_opened_but_no_human_ack"
    if state.flow_ran:
        if state.target_laudo_id and not ui_summary.get("selected_target_id"):
            return "app_opened_but_target_not_reached"
        return "blocked_no_ui_path"
    return "partial_execution"


def build_final_report(state: ExecutionState) -> str:
    before = state.summary_before or {}
    after = state.summary_after or {}
    operator_after = state.operator_status_after or {}
    backend_evidence_after = extract_backend_evidence(after)
    request_trace_id = str(
        (state.ui_marker_summary or {}).get("activity_center_request_trace_id") or ""
    ).strip() or None
    backend_request_traces_after = find_backend_request_traces(after, request_trace_id)
    summary_before_tenant = before.get("first_promoted_tenant") or {}
    summary_after_tenant = after.get("first_promoted_tenant") or {}
    return "\n".join(
        [
            f"timestamp_utc: {now_utc()}",
            f"device_id: {state.device_id}",
            f"tenant: 1 - Empresa Demo (DEV)",
            f"package_name: {state.package_name}",
            f"main_activity: {state.main_activity}",
            f"mobile_email: {state.mobile_email}",
            f"admin_email: {state.admin_email}",
            f"target_laudo_id: {state.target_laudo_id}",
            f"maestro_attempts: {state.maestro_attempts}",
            f"maestro_environment_retry_used: {state.maestro_environment_retry_used}",
            f"environment_failure_signals: {state.environment_failure_signals}",
            f"feed_covered: {state.feed_covered}",
            f"thread_covered: {state.thread_covered}",
            f"operator_run_outcome: {operator_after.get('operator_run_outcome')}",
            f"operator_run_reason: {operator_after.get('operator_run_reason')}",
            f"v2_served_total_after: {(after.get('totals') or {}).get('v2_served')}",
            f"human_ack_recent_events_after: {len(backend_evidence_after.get('human_ack_recent_events') or [])}",
            f"ui_login_stage: {(state.ui_marker_summary or {}).get('login_stage')}",
            f"ui_login_status_api: {(state.ui_marker_summary or {}).get('login_status_api')}",
            f"ui_login_entrando: {(state.ui_marker_summary or {}).get('login_entrando')}",
            f"ui_login_carregando: {(state.ui_marker_summary or {}).get('login_carregando')}",
            f"ui_login_error: {(state.ui_marker_summary or {}).get('login_error')}",
            f"ui_selected_target_id: {(state.ui_marker_summary or {}).get('selected_target_id')}",
            f"ui_selection_callback_fired: {(state.ui_marker_summary or {}).get('selection_callback_fired')}",
            f"ui_selection_callback_completed: {(state.ui_marker_summary or {}).get('selection_callback_completed')}",
            f"ui_shell_selection_ready: {(state.ui_marker_summary or {}).get('shell_selection_ready')}",
            f"ui_selection_lost: {(state.ui_marker_summary or {}).get('selection_lost')}",
            f"ui_runtime_flag_enabled: {(state.ui_marker_summary or {}).get('runtime_flag_enabled')}",
            f"ui_runtime_flag_raw_value: {(state.ui_marker_summary or {}).get('runtime_flag_raw_value')}",
            f"ui_runtime_flag_source: {(state.ui_marker_summary or {}).get('runtime_flag_source')}",
            f"maestro_selection_callback_confirmed: {state.maestro_selection_callback_confirmed}",
            f"maestro_shell_selection_confirmed: {state.maestro_shell_selection_confirmed}",
            f"maestro_activity_center_terminal_confirmed: {state.maestro_activity_center_terminal_confirmed}",
            f"maestro_activity_center_v2_confirmed: {state.maestro_activity_center_v2_confirmed}",
            f"ui_activity_center_state: {(state.ui_marker_summary or {}).get('activity_center_state')}",
            f"ui_activity_center_terminal_state: {(state.ui_marker_summary or {}).get('activity_center_terminal_state')}",
            f"ui_activity_center_delivery_mode: {(state.ui_marker_summary or {}).get('activity_center_delivery_mode')}",
            f"ui_activity_center_request_dispatched: {(state.ui_marker_summary or {}).get('activity_center_request_dispatched')}",
            f"ui_activity_center_requested_targets: {(state.ui_marker_summary or {}).get('activity_center_requested_targets')}",
            f"ui_activity_center_skip_reason: {(state.ui_marker_summary or {}).get('activity_center_skip_reason')}",
            f"ui_activity_center_request_phase: {(state.ui_marker_summary or {}).get('activity_center_request_phase')}",
            f"ui_activity_center_request_trace_id: {request_trace_id}",
            f"ui_activity_center_request_flag_enabled: {(state.ui_marker_summary or {}).get('activity_center_request_flag_enabled')}",
            f"ui_activity_center_request_flag_raw_value: {(state.ui_marker_summary or {}).get('activity_center_request_flag_raw_value')}",
            f"ui_activity_center_request_flag_source: {(state.ui_marker_summary or {}).get('activity_center_request_flag_source')}",
            f"ui_activity_center_request_route_decision: {(state.ui_marker_summary or {}).get('activity_center_request_route_decision')}",
            f"ui_activity_center_request_decision_reason: {(state.ui_marker_summary or {}).get('activity_center_request_decision_reason')}",
            f"ui_activity_center_request_decision_source: {(state.ui_marker_summary or {}).get('activity_center_request_decision_source')}",
            f"ui_activity_center_request_actual_route: {(state.ui_marker_summary or {}).get('activity_center_request_actual_route')}",
            f"ui_activity_center_request_attempt_sequence: {(state.ui_marker_summary or {}).get('activity_center_request_attempt_sequence')}",
            f"ui_activity_center_request_endpoint_path: {(state.ui_marker_summary or {}).get('activity_center_request_endpoint_path')}",
            f"ui_activity_center_request_status: {(state.ui_marker_summary or {}).get('activity_center_request_status')}",
            f"ui_activity_center_request_failure_kind: {(state.ui_marker_summary or {}).get('activity_center_request_failure_kind')}",
            f"ui_activity_center_request_fallback_reason: {(state.ui_marker_summary or {}).get('activity_center_request_fallback_reason')}",
            f"ui_activity_center_request_backend_request_id: {(state.ui_marker_summary or {}).get('activity_center_request_backend_request_id')}",
            f"backend_request_trace_matches_after: {len(backend_request_traces_after)}",
            f"backend_request_trace_counted_kinds_after: {[item.get('counted_kind') for item in backend_request_traces_after]}",
            f"pilot_outcome_before: {summary_before_tenant.get('pilot_outcome')}",
            f"pilot_outcome_after: {summary_after_tenant.get('pilot_outcome')}",
            f"organic_validation_outcome_after: {summary_after_tenant.get('organic_validation_outcome')}",
            f"candidate_ready_for_real_tenant_after: {summary_after_tenant.get('candidate_ready_for_real_tenant')}",
            f"result: {state.outcome_label}",
            "",
            "notes:",
            *(f"- {note}" for note in state.notes),
            "",
            "commands:",
            *(f"- {item}" for item in state.commands_used),
        ]
    ).strip() + "\n"


def execute(state: ExecutionState) -> ExecutionState:
    package_info = load_android_package_info()
    state.package_name = str(package_info["package_name"])
    state.main_activity = str(package_info["main_activity"])
    write_text(state.artifacts_dir / "environment.txt", build_environment_report(package_info))
    log_step("Iniciando runner operacional do smoke mobile.")
    record_phase_event(
        state,
        phase="host_preflight",
        status="running",
        detail="runner_started",
        extra={
            "visual_mode": state.visual_mode,
            "fresh_emulator_boot": should_force_fresh_emulator_boot(),
        },
    )

    web_env = load_env_file(WEB_ROOT / ".env")
    android_env = load_env_file(ANDROID_ROOT / ".env")
    write_json(
        state.artifacts_dir / "flags_snapshot.json",
        {
            "web_env": web_env,
            "android_env": android_env,
        },
    )

    ensure_local_emulator(state)

    log_step("Resolvendo device Android disponível.")
    state.device_id = resolve_device(state)
    log_step(f"Device selecionado: {state.device_id}")
    record_phase_event(
        state,
        phase="host_preflight",
        status="ok",
        detail="device_resolved",
        extra=probe_device_health_by_serial(state.device_id),
    )
    ensure_adb_reverse(state, DEFAULT_PORTS)
    if state.visual_mode:
        keep_device_visible(state)
    log_step("Garantindo backend local do mobile.")
    start_backend(state)

    mobile_email, mobile_password, admin_email = resolve_credentials(web_env)
    state.mobile_email = mobile_email
    state.admin_email = admin_email
    append_note(state, f"Credencial mobile usada: {mobile_email}")
    append_note(state, f"Credencial admin usada: {admin_email}")
    ensure_mobile_pilot_seed_data(state, inspector_email=mobile_email)

    opener = build_admin_opener()
    admin_login(
        opener,
        admin_email,
        web_env.get("SEED_ADMIN_SENHA")
        or web_env.get("SEED_DEV_SENHA_PADRAO")
        or DEFAULT_MOBILE_PASSWORD,
    )
    mobile_login_payload = login_mobile(mobile_email, mobile_password)
    state.mobile_token = str(mobile_login_payload.get("access_token") or "")
    if not state.mobile_token:
        raise RunnerError("Login mobile não retornou access_token.")
    write_json(state.artifacts_dir / "mobile_login.json", mobile_login_payload)
    force_stop_app(state, label="pre_operator_run")

    # baseline pré-run para comparação adicional
    save_http_json(
        state.artifacts_dir / "backend_summary_preflight.json",
        admin_json(opener, "/admin/api/mobile-v2-rollout/summary"),
    )
    save_http_json(
        state.artifacts_dir / "operator_run_status_preflight.json",
        admin_json(opener, "/admin/api/mobile-v2-rollout/operator-run/status"),
    )

    preflight_status = admin_json(opener, "/admin/api/mobile-v2-rollout/operator-run/status")
    if preflight_status.get("operator_run_active"):
        append_note(state, "Operator run anterior estava ativo; o runner abortou o estado anterior antes da nova rodada.")
        save_http_json(
            state.artifacts_dir / "operator_run_abort_previous.json",
            finish_operator_run(opener, state, abort=True),
        )
        state.operator_run_started = False
        state.operator_run_finished = False

    start_response = admin_json(opener, "/admin/api/mobile-v2-rollout/operator-run/start", method="POST")
    state.operator_run_started = True
    save_http_json(state.artifacts_dir / "operator_run_start.json", start_response)

    state.operator_status_before = admin_json(opener, "/admin/api/mobile-v2-rollout/operator-run/status")
    save_http_json(
        state.artifacts_dir / "operator_run_status_before.json",
        state.operator_status_before,
    )
    state.target_laudo_id = resolve_operator_thread_target_id(
        state.operator_status_before
    )
    if state.target_laudo_id:
        append_note(
        state,
        f"Target de thread resolvido para automação Maestro: laudo {state.target_laudo_id}.",
    )
    state.summary_before = admin_json(opener, "/admin/api/mobile-v2-rollout/summary")
    save_http_json(state.artifacts_dir / "backend_summary_before.json", state.summary_before)
    state.capabilities_before = read_json_response(
        build_mobile_request("/app/api/mobile/v2/capabilities", token=state.mobile_token)
    )
    save_http_json(state.artifacts_dir / "capabilities_before.json", state.capabilities_before)

    capture_screenshot(state, "device_before_install")
    capture_ui_dump(state, "ui_before_install")

    log_step("Iniciando captura do logcat e preparando o app.")
    start_logcat_capture(state)
    ensure_device_package_service_ready(state)
    install_or_reuse_app(state, package_info)
    if state.visual_mode:
        keep_device_visible(state)
    ensure_device_package_service_ready(state)
    force_stop_app(state, label="post_install")
    stabilize_device_for_maestro(state, label="pre_maestro")
    append_note(
        state,
        "Launch manual do app foi pulado; o flow do Maestro faz launchApp e virou a fonte canonica da abertura.",
    )

    maestro_result = run_maestro_flow(state, mobile_password)
    screenshot_path: pathlib.Path
    if maestro_result.returncode != 0:
        append_note(state, "O flow do Maestro falhou; o runner coletou screenshot/UI dump e prosseguiu para fechamento conservador.")
        screenshot_path = capture_screenshot(state, "device_after_maestro_failure")
        ui_dump_path = capture_ui_dump(state, "ui_after_maestro_failure")
        environment_failure_signals = detect_environment_failure_signals(
            ui_dump_path,
            screenshot_path=screenshot_path,
            maestro_output=(maestro_result.stdout or "") + "\n" + (maestro_result.stderr or ""),
        )
        state.environment_failure_signals = environment_failure_signals
        write_json(
            state.artifacts_dir / "environment_failure_signals.json",
            {
                "signals": environment_failure_signals,
                "ui_dump_path": str(ui_dump_path),
                "screenshot_path": str(screenshot_path),
            },
        )
        should_retry_for_environment = bool(
            environment_failure_signals
            and state.maestro_attempts <= MAESTRO_ENVIRONMENT_RETRY_LIMIT
            and (
                "system_ui_not_responding" in environment_failure_signals
                or "app_not_responding_dialog" in environment_failure_signals
                or "ui_dump_unavailable" in environment_failure_signals
                or "screenshot_unavailable" in environment_failure_signals
                or "failed_before_login_without_ui_dump" in environment_failure_signals
            )
        )
        if should_retry_for_environment:
            state.maestro_environment_retry_used = True
            recover_emulator_from_environment_failure(
                state,
                reason=",".join(environment_failure_signals),
            )
            maestro_result = run_maestro_flow(state, mobile_password)
            if maestro_result.returncode != 0:
                append_note(
                    state,
                    "A repeticao unica do Maestro apos recovery ambiental tambem falhou; a lane permaneceu inconclusiva.",
                )
                screenshot_path = capture_screenshot(
                    state,
                    "device_after_maestro_failure_retry",
                )
                ui_dump_path = capture_ui_dump(
                    state,
                    "ui_after_maestro_failure_retry",
                )
                state.environment_failure_signals = detect_environment_failure_signals(
                    ui_dump_path,
                    screenshot_path=screenshot_path,
                    maestro_output=(maestro_result.stdout or "")
                    + "\n"
                    + (maestro_result.stderr or ""),
                )
                write_json(
                    state.artifacts_dir / "environment_failure_signals_retry.json",
                    {
                        "signals": state.environment_failure_signals,
                        "ui_dump_path": str(ui_dump_path),
                        "screenshot_path": str(screenshot_path),
                    },
                )
            else:
                append_note(
                    state,
                    "A repeticao unica do Maestro apos recovery ambiental fechou verde.",
                )
                screenshot_path = capture_screenshot(
                    state,
                    "device_after_maestro_retry",
                )
                ui_dump_path = capture_ui_dump(state, "ui_after_maestro_retry")
    else:
        screenshot_path = capture_screenshot(state, "device_after_maestro")
        ui_dump_path = capture_ui_dump(state, "ui_after_maestro")
    state.ui_marker_summary = summarize_ui_markers(ui_dump_path, state.target_laudo_id)
    save_http_json(
        state.artifacts_dir / "ui_marker_summary.json",
        state.ui_marker_summary,
    )
    save_http_json(
        state.artifacts_dir / "app_request_trace_summary.json",
        extract_app_request_trace_summary(state.ui_marker_summary),
    )
    if maestro_result.returncode == 0:
        record_human_acks_from_ui(state)

    summary_post_ui_wait, operator_status_post_ui_wait = wait_for_backend_evidence(
        opener,
        state,
    )
    if summary_post_ui_wait is not None:
        save_http_json(
            state.artifacts_dir / "backend_summary_post_ui_wait.json",
            summary_post_ui_wait,
        )
        save_http_json(
            state.artifacts_dir / "backend_evidence_post_ui_wait.json",
            extract_backend_evidence(summary_post_ui_wait),
        )
        save_http_json(
            state.artifacts_dir / "backend_request_trace_summary_post_ui_wait.json",
            {
                "trace_id": (state.ui_marker_summary or {}).get(
                    "activity_center_request_trace_id"
                ),
                "matches": find_backend_request_traces(
                    summary_post_ui_wait,
                    (state.ui_marker_summary or {}).get(
                        "activity_center_request_trace_id"
                    ),
                ),
            },
        )
    if operator_status_post_ui_wait is not None:
        save_http_json(
            state.artifacts_dir / "operator_run_status_post_ui_wait.json",
            operator_status_post_ui_wait,
        )

    if state.operator_run_started and not state.operator_run_finished:
        finish_payload = finish_operator_run(
            opener,
            state,
            abort=maestro_result.returncode != 0,
        )
        save_http_json(state.artifacts_dir / "operator_run_finish.json", finish_payload)

    state.operator_status_after = admin_json(opener, "/admin/api/mobile-v2-rollout/operator-run/status")
    save_http_json(
        state.artifacts_dir / "operator_run_status_after.json",
        state.operator_status_after,
    )
    state.summary_after = admin_json(opener, "/admin/api/mobile-v2-rollout/summary")
    save_http_json(state.artifacts_dir / "backend_summary_after.json", state.summary_after)
    save_http_json(
        state.artifacts_dir / "backend_request_trace_summary_after.json",
        {
            "trace_id": (state.ui_marker_summary or {}).get(
                "activity_center_request_trace_id"
            ),
            "matches": find_backend_request_traces(
                state.summary_after,
                (state.ui_marker_summary or {}).get(
                    "activity_center_request_trace_id"
                ),
            ),
        },
    )
    state.capabilities_after = read_json_response(
        build_mobile_request("/app/api/mobile/v2/capabilities", token=state.mobile_token)
    )
    save_http_json(state.artifacts_dir / "capabilities_after.json", state.capabilities_after)

    state.feed_covered, state.thread_covered = summarize_surface_coverage(state.summary_after)
    state.operator_run_outcome = str(
        (state.operator_status_after or {}).get("operator_run_outcome") or ""
    )
    state.operator_run_reason = str(
        (state.operator_status_after or {}).get("operator_run_reason") or ""
    )

    state.outcome_label = evaluate_result(state)
    save_http_json(
        state.artifacts_dir / "request_trace_gap_summary.json",
        {
            "result": state.outcome_label,
            "app_request_trace": extract_app_request_trace_summary(
                state.ui_marker_summary
            ),
            "backend_request_traces": find_backend_request_traces(
                state.summary_after,
                (state.ui_marker_summary or {}).get(
                    "activity_center_request_trace_id"
                ),
            ),
        },
    )
    write_text(state.artifacts_dir / "final_report.md", build_final_report(state))
    return state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa o runner operacional do piloto Android V2 no tenant demo."
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Liga o modo visual local de forma explícita (emulador com janela + logs espelhados).",
    )
    parser.add_argument(
        "--no-visual",
        action="store_true",
        help="Força o modo headless do mobile mesmo fora da CI.",
    )
    args = parser.parse_args()

    visual_mode = resolve_visual_mode(
        True if args.visual else False if args.no_visual else None
    )

    artifacts_dir = ensure_dir(ARTIFACTS_ROOT / now_local_slug())
    state = ExecutionState(
        artifacts_dir=artifacts_dir,
        screenshots_dir=ensure_dir(artifacts_dir / "screenshots"),
        ui_dumps_dir=ensure_dir(artifacts_dir / "ui_dumps"),
        maestro_debug_dir=ensure_dir(artifacts_dir / "maestro_debug"),
        visual_mode=visual_mode,
    )
    try:
        state = execute(state)
        if state.outcome_label == "success_human_confirmed":
            write_mobile_pilot_lane_state(
                state,
                status="ok",
                detail="lane oficial concluida com sucesso_human_confirmed",
            )
            return 0
        write_mobile_pilot_lane_state(
            state,
            status="fail",
            detail=f"lane oficial inconclusiva: {state.outcome_label}",
        )
        print(
            f"Smoke mobile inconclusivo: {state.outcome_label}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        append_note(state, f"Falha operacional: {exc}")
        write_mobile_pilot_lane_state(
            state,
            status="fail",
            detail=f"falha_operacional: {exc}",
        )
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        stop_logcat_capture(state)
        write_logcat_excerpt(state)
        if not (state.artifacts_dir / "final_report.md").exists():
            write_text(state.artifacts_dir / "final_report.md", build_final_report(state))
        stop_backend_if_needed(state)


if __name__ == "__main__":
    raise SystemExit(main())
