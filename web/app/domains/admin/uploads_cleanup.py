from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import app.shared.database as banco_dados
from app.core.settings import get_settings
from app.shared.database import AnexoMesa, AprendizadoVisualIa, Usuario
from app.v2.contracts.envelopes import utc_now

fcntl: Any
try:
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None

_REPORTS_DIRNAME = "_cleanup_reports"
_LOCK_FILENAME = ".uploads_cleanup.lock"
_STATE_FILENAME = "uploads_cleanup_runtime.json"
_SLEEP_SECONDS = 60
_WEB_ROOT = Path(__file__).resolve().parents[3]
_scheduler_thread: threading.Thread | None = None
_scheduler_stop = threading.Event()
_scheduler_lock = threading.Lock()
_scheduler_ready_probe: Callable[[], bool] | None = None
_scheduler_wait_reason: str | None = None


@dataclass(frozen=True, slots=True)
class UploadCleanupTarget:
    category: str
    root: Path
    retention_days: int


@dataclass(frozen=True, slots=True)
class UploadCleanupCandidate:
    category: str
    path: Path
    age_days: float
    referenced: bool
    eligible: bool
    reason: str


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_targets() -> tuple[UploadCleanupTarget, ...]:
    settings = get_settings()
    default_profile_root = _WEB_ROOT / "static" / "uploads" / "perfis"
    default_mesa_root = Path(tempfile.gettempdir()) / "tariel_control" / "mesa_anexos"
    default_learning_root = _WEB_ROOT / "static" / "uploads" / "aprendizados_ia"

    def _resolve_root(raw_value: str, fallback: Path) -> Path:
        raw = str(raw_value or "").strip()
        if not raw:
            return fallback
        candidate = Path(raw).expanduser()
        return candidate if candidate.is_absolute() else (_WEB_ROOT / candidate)

    return (
        UploadCleanupTarget(
            category="profile_uploads",
            root=_resolve_root(settings.profile_uploads_path, default_profile_root),
            retention_days=settings.uploads_profile_retention_days,
        ),
        UploadCleanupTarget(
            category="mesa_attachments",
            root=_resolve_root(settings.mesa_attachments_path, default_mesa_root),
            retention_days=settings.uploads_mesa_retention_days,
        ),
        UploadCleanupTarget(
            category="visual_learning_uploads",
            root=_resolve_root(
                settings.visual_learning_uploads_path,
                default_learning_root,
            ),
            retention_days=settings.uploads_learning_retention_days,
        ),
    )


def _shared_root(targets: tuple[UploadCleanupTarget, ...]) -> Path:
    paths = [str(target.root.resolve()) for target in targets if str(target.root).strip()]
    if not paths:
        return Path.cwd()
    try:
        common = Path(os.path.commonpath(paths))
    except Exception:
        return targets[0].root.resolve()
    if str(common) in {common.anchor, "/"} or len(common.parts) <= 1:
        return targets[0].root.resolve().parent
    return common


def _reports_dir(targets: tuple[UploadCleanupTarget, ...]) -> Path:
    return _shared_root(targets) / _REPORTS_DIRNAME


def _runtime_state_path(targets: tuple[UploadCleanupTarget, ...]) -> Path:
    return _reports_dir(targets) / _STATE_FILENAME


def _lock_path(targets: tuple[UploadCleanupTarget, ...]) -> Path:
    return _shared_root(targets) / _LOCK_FILENAME


def _acquire_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    if fcntl is None:
        return handle
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def _release_lock(handle) -> None:
    if handle is None:
        return
    try:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        handle.close()
    except Exception:
        pass


def _path_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def _profile_path_from_url(root: Path, raw_url: str | None) -> Path | None:
    value = str(raw_url or "").strip()
    prefix = "/static/uploads/perfis/"
    if not value.startswith(prefix):
        return None
    relative = value.removeprefix(prefix).strip("/")
    if not relative:
        return None
    candidate = root / relative
    return candidate if _path_under_root(candidate, root) else None


def _normalize_db_path(root: Path, raw_path: str | None) -> Path | None:
    value = str(raw_path or "").strip()
    if not value:
        return None
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate if _path_under_root(candidate, root) else None


def _referenced_paths_by_category(targets: tuple[UploadCleanupTarget, ...]) -> dict[str, set[Path]]:
    by_category: dict[str, set[Path]] = {target.category: set() for target in targets}
    root_by_category = {target.category: target.root for target in targets}
    with banco_dados.SessaoLocal() as banco:
        for url in banco.query(Usuario.foto_perfil_url).filter(Usuario.foto_perfil_url.isnot(None)).all():
            path = _profile_path_from_url(root_by_category["profile_uploads"], url[0])
            if path is not None:
                by_category["profile_uploads"].add(path.resolve())
        for row in banco.query(AnexoMesa.caminho_arquivo).filter(AnexoMesa.caminho_arquivo.isnot(None)).all():
            path = _normalize_db_path(root_by_category["mesa_attachments"], row[0])
            if path is not None:
                by_category["mesa_attachments"].add(path.resolve())
        for row in banco.query(AprendizadoVisualIa.caminho_arquivo).filter(AprendizadoVisualIa.caminho_arquivo.isnot(None)).all():
            path = _normalize_db_path(root_by_category["visual_learning_uploads"], row[0])
            if path is not None:
                by_category["visual_learning_uploads"].add(path.resolve())
    return by_category


def _candidate_reason(*, referenced: bool, eligible: bool, exists: bool) -> str:
    if not exists:
        return "missing_on_disk"
    if referenced:
        return "referenced_in_database"
    if eligible:
        return "orphan_older_than_retention"
    return "orphan_within_grace_window"


def _scan_candidates(
    *,
    targets: tuple[UploadCleanupTarget, ...],
    grace_days: int,
    report_dir: Path,
    now: datetime,
) -> tuple[list[UploadCleanupCandidate], dict[str, Any]]:
    referenced_paths = _referenced_paths_by_category(targets)
    candidates: list[UploadCleanupCandidate] = []
    summary_rows: dict[str, Any] = {}

    for target in targets:
        root = target.root
        root.mkdir(parents=True, exist_ok=True)
        referenced = referenced_paths.get(target.category, set())
        scanned = 0
        referenced_count = 0
        orphan_count = 0
        eligible_count = 0
        skipped_recent = 0
        row_candidates: list[UploadCleanupCandidate] = []

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if report_dir in path.parents or path.name in {_LOCK_FILENAME, _STATE_FILENAME}:
                continue
            scanned += 1
            resolved = path.resolve()
            is_referenced = resolved in referenced
            age_days = max((now - datetime.fromtimestamp(resolved.stat().st_mtime, timezone.utc)).total_seconds() / 86400, 0.0)
            eligible_age = target.retention_days + grace_days
            eligible = (not is_referenced) and age_days >= eligible_age
            if is_referenced:
                referenced_count += 1
            else:
                orphan_count += 1
                if eligible:
                    eligible_count += 1
                else:
                    skipped_recent += 1
            row_candidates.append(
                UploadCleanupCandidate(
                    category=target.category,
                    path=resolved,
                    age_days=round(age_days, 4),
                    referenced=is_referenced,
                    eligible=eligible,
                    reason=_candidate_reason(
                        referenced=is_referenced,
                        eligible=eligible,
                        exists=True,
                    ),
                )
            )

        candidates.extend(row_candidates)
        summary_rows[target.category] = {
            "category": target.category,
            "root": str(root.resolve()),
            "retention_days": target.retention_days,
            "scanned_files": scanned,
            "referenced_files": referenced_count,
            "orphan_files": orphan_count,
            "eligible_files": eligible_count,
            "skipped_recent_orphans": skipped_recent,
        }

    return candidates, summary_rows


def _prune_empty_dirs(root: Path, *, protected_dirs: set[Path]) -> int:
    removed = 0
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not path.is_dir() or path in protected_dirs:
            continue
        try:
            next(path.iterdir())
        except StopIteration:
            try:
                path.rmdir()
                removed += 1
            except Exception:
                continue
        except Exception:
            continue
    return removed


def _write_report(report_dir: Path, payload: dict[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"uploads_cleanup_{timestamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_runtime_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _load_latest_report(report_dir: Path) -> dict[str, Any] | None:
    if not report_dir.is_dir():
        return None
    reports = sorted(
        path
        for path in report_dir.glob("uploads_cleanup_*.json")
        if path.name != _STATE_FILENAME
    )
    if not reports:
        return None
    try:
        payload = json.loads(reports[-1].read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _load_runtime_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _scheduler_gate_status() -> tuple[bool, str | None]:
    if _scheduler_ready_probe is None:
        return True, None
    try:
        ready = bool(_scheduler_ready_probe())
    except Exception:
        return False, "scheduler_readiness_probe_failed"
    if ready:
        return True, None
    return False, _scheduler_wait_reason or "dependency_not_ready"


def describe_uploads_cleanup_runtime() -> dict[str, Any]:
    settings = get_settings()
    targets = _resolve_targets()
    report_dir = _reports_dir(targets)
    runtime_state_path = _runtime_state_path(targets)
    latest_report = _load_latest_report(report_dir)
    runtime_state = _load_runtime_state(runtime_state_path)
    return {
        "cleanup_enabled": settings.uploads_cleanup_enabled,
        "cleanup_interval_hours": settings.uploads_cleanup_interval_hours,
        "cleanup_max_deletions_per_run": settings.uploads_cleanup_max_deletions_per_run,
        "scheduler_running": bool(runtime_state.get("scheduler_running", False)),
        "scheduler_started_at": runtime_state.get("started_at"),
        "scheduler_stopped_at": runtime_state.get("stopped_at"),
        "scheduler_last_run_at": runtime_state.get("last_run_at"),
        "scheduler_last_status": runtime_state.get("last_status"),
        "scheduler_last_report_path": runtime_state.get("last_report_path"),
        "scheduler_last_mode": runtime_state.get("last_mode"),
        "scheduler_last_source": runtime_state.get("last_source"),
        "scheduler_wait_reason": runtime_state.get("wait_reason"),
        "latest_report": latest_report,
        "report_dir": str(report_dir),
    }


def run_uploads_cleanup(
    *,
    apply: bool,
    source: str,
    strict: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    targets = _resolve_targets()
    report_dir = _reports_dir(targets)
    runtime_state_path = _runtime_state_path(targets)
    lock_path = _lock_path(targets)
    now_utc = now or _now_utc()
    handle = _acquire_lock(lock_path)
    if handle is None:
        payload: dict[str, Any] = {
            "contract_name": "UploadsCleanupReportV1",
            "contract_version": "v1",
            "generated_at": utc_now().isoformat(),
            "status": "locked",
            "source": source,
            "mode": "apply" if apply else "dry_run",
            "cleanup_enabled": settings.uploads_cleanup_enabled,
            "report_dir": str(report_dir),
            "blockers": ["cleanup_lock_unavailable"],
            "warnings": [],
        }
        if strict:
            payload["strict_failure"] = True
        return payload

    try:
        candidates, per_category = _scan_candidates(
            targets=targets,
            grace_days=settings.uploads_cleanup_grace_days,
            report_dir=report_dir,
            now=now_utc,
        )
        eligible = [item for item in candidates if item.eligible]
        deleted: list[str] = []
        errors: list[dict[str, str]] = []
        warnings: list[str] = []
        max_deletions = settings.uploads_cleanup_max_deletions_per_run
        if apply and len(eligible) > max_deletions:
            warnings.append("eligible_files_exceed_max_deletions_per_run")
        for item in eligible[: max_deletions if apply else len(eligible)]:
            if not apply:
                continue
            try:
                item.path.unlink(missing_ok=True)
                deleted.append(str(item.path))
            except Exception as exc:
                errors.append({"path": str(item.path), "error": str(exc)})
        empty_dirs_removed = 0
        if apply:
            protected_dirs = {report_dir.resolve()}
            for target in targets:
                empty_dirs_removed += _prune_empty_dirs(target.root, protected_dirs=protected_dirs)

        production_safe = len(errors) == 0 and (
            not apply or len(deleted) <= max_deletions
        )
        payload = {
            "contract_name": "UploadsCleanupReportV1",
            "contract_version": "v1",
            "generated_at": utc_now().isoformat(),
            "status": "ok" if production_safe else "attention",
            "source": source,
            "mode": "apply" if apply else "dry_run",
            "cleanup_enabled": settings.uploads_cleanup_enabled,
            "cleanup_grace_days": settings.uploads_cleanup_grace_days,
            "cleanup_interval_hours": settings.uploads_cleanup_interval_hours,
            "cleanup_max_deletions_per_run": max_deletions,
            "report_dir": str(report_dir),
            "targets": list(per_category.values()),
            "totals": {
                "scanned_files": sum(int(row["scanned_files"]) for row in per_category.values()),
                "referenced_files": sum(int(row["referenced_files"]) for row in per_category.values()),
                "orphan_files": sum(int(row["orphan_files"]) for row in per_category.values()),
                "eligible_files": len(eligible),
                "deleted_files": len(deleted),
                "deletion_errors": len(errors),
                "empty_dirs_removed": empty_dirs_removed,
            },
            "eligible_candidates": [
                {
                    "category": item.category,
                    "path": str(item.path),
                    "age_days": item.age_days,
                    "reason": item.reason,
                }
                for item in eligible
            ],
            "deleted_paths": deleted,
            "errors": errors,
            "warnings": warnings,
            "blockers": [],
        }
        report_path = _write_report(report_dir, payload)
        payload["report_path"] = str(report_path)
        previous_state = _load_runtime_state(runtime_state_path)
        _write_runtime_state(
            runtime_state_path,
            {
                "scheduler_running": bool(_scheduler_thread and _scheduler_thread.is_alive()),
                "started_at": previous_state.get("started_at"),
                "stopped_at": None if bool(_scheduler_thread and _scheduler_thread.is_alive()) else previous_state.get("stopped_at"),
                "last_run_at": payload["generated_at"],
                "last_status": payload["status"],
                "last_report_path": str(report_path),
                "last_mode": payload["mode"],
                "last_source": source,
                "wait_reason": None,
            },
        )
        if strict and (payload["blockers"] or errors):
            payload["strict_failure"] = True
        return payload
    finally:
        _release_lock(handle)


def _scheduler_loop() -> None:
    targets = _resolve_targets()
    runtime_state_path = _runtime_state_path(targets)
    settings = get_settings()
    while not _scheduler_stop.is_set():
        state = describe_uploads_cleanup_runtime()
        latest_report = dict(state.get("latest_report") or {})
        latest_generated_at = _parse_iso(latest_report.get("generated_at"))
        due = latest_generated_at is None or (_now_utc() - latest_generated_at) >= timedelta(hours=settings.uploads_cleanup_interval_hours)
        if settings.uploads_cleanup_enabled and due:
            scheduler_ready, wait_reason = _scheduler_gate_status()
            if not scheduler_ready:
                previous_state = _load_runtime_state(runtime_state_path)
                _write_runtime_state(
                    runtime_state_path,
                    {
                        "scheduler_running": True,
                        "started_at": previous_state.get("started_at"),
                        "stopped_at": None,
                        "last_run_at": previous_state.get("last_run_at"),
                        "last_status": previous_state.get("last_status"),
                        "last_report_path": previous_state.get("last_report_path"),
                        "last_mode": previous_state.get("last_mode"),
                        "last_source": previous_state.get("last_source"),
                        "wait_reason": wait_reason,
                    },
                )
                _scheduler_stop.wait(_SLEEP_SECONDS)
                continue
            payload = run_uploads_cleanup(apply=True, source="web_scheduler", strict=False)
            previous_state = _load_runtime_state(runtime_state_path)
            _write_runtime_state(
                runtime_state_path,
                {
                    "scheduler_running": True,
                    "started_at": previous_state.get("started_at"),
                    "stopped_at": None,
                    "last_run_at": payload.get("generated_at"),
                    "last_status": payload.get("status"),
                    "last_report_path": payload.get("report_path"),
                    "last_mode": payload.get("mode"),
                    "last_source": payload.get("source"),
                    "wait_reason": None,
                },
            )
        _scheduler_stop.wait(_SLEEP_SECONDS)
    previous_state = _load_runtime_state(runtime_state_path)
    _write_runtime_state(
        runtime_state_path,
        {
            "scheduler_running": False,
            "started_at": previous_state.get("started_at"),
            "stopped_at": utc_now().isoformat(),
            "last_run_at": previous_state.get("last_run_at"),
            "last_status": previous_state.get("last_status"),
            "last_report_path": previous_state.get("last_report_path"),
            "last_mode": previous_state.get("last_mode"),
            "last_source": previous_state.get("last_source"),
            "wait_reason": None,
        },
    )


def start_uploads_cleanup_scheduler(
    *,
    ready_probe: Callable[[], bool] | None = None,
    wait_reason: str | None = None,
) -> None:
    settings = get_settings()
    if not settings.uploads_cleanup_enabled:
        return
    global _scheduler_ready_probe, _scheduler_thread, _scheduler_wait_reason
    with _scheduler_lock:
        if _scheduler_thread is not None and _scheduler_thread.is_alive():
            return
        _scheduler_ready_probe = ready_probe
        _scheduler_wait_reason = wait_reason
        targets = _resolve_targets()
        runtime_state_path = _runtime_state_path(targets)
        previous_state = _load_runtime_state(runtime_state_path)
        _, active_wait_reason = _scheduler_gate_status()
        _write_runtime_state(
            runtime_state_path,
            {
                "scheduler_running": True,
                "started_at": utc_now().isoformat(),
                "stopped_at": None,
                "last_run_at": previous_state.get("last_run_at"),
                "last_status": previous_state.get("last_status"),
                "last_report_path": previous_state.get("last_report_path"),
                "last_mode": previous_state.get("last_mode"),
                "last_source": previous_state.get("last_source"),
                "wait_reason": active_wait_reason,
            },
        )
        _scheduler_stop.clear()
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            name="tariel-uploads-cleanup",
            daemon=True,
        )
        _scheduler_thread.start()


def stop_uploads_cleanup_scheduler() -> None:
    global _scheduler_ready_probe, _scheduler_thread, _scheduler_wait_reason
    with _scheduler_lock:
        if _scheduler_thread is None:
            return
        _scheduler_stop.set()
        _scheduler_thread.join(timeout=5)
        targets = _resolve_targets()
        runtime_state_path = _runtime_state_path(targets)
        previous_state = _load_runtime_state(runtime_state_path)
        _write_runtime_state(
            runtime_state_path,
            {
                "scheduler_running": False,
                "started_at": previous_state.get("started_at"),
                "stopped_at": utc_now().isoformat(),
                "last_run_at": previous_state.get("last_run_at"),
                "last_status": previous_state.get("last_status"),
                "last_report_path": previous_state.get("last_report_path"),
                "last_mode": previous_state.get("last_mode"),
                "last_source": previous_state.get("last_source"),
                "wait_reason": None,
            },
        )
        _scheduler_thread = None
        _scheduler_ready_probe = None
        _scheduler_wait_reason = None


__all__ = [
    "describe_uploads_cleanup_runtime",
    "run_uploads_cleanup",
    "start_uploads_cleanup_scheduler",
    "stop_uploads_cleanup_scheduler",
]
