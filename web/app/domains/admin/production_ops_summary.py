from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from app.core.settings import get_settings
from app.domains.admin.uploads_cleanup import describe_uploads_cleanup_runtime
from app.shared.security_session_store import describe_session_operational_policy
from app.v2.contracts.envelopes import utc_now

_RENDER_UPLOADS_ROOT = Path("/opt/render/project/src/web/static/uploads")
_WEB_ROOT = Path(__file__).resolve().parents[3]


def _resolve_ops_path(raw_value: str | None, fallback: Path) -> Path:
    raw = str(raw_value or "").strip()
    if not raw:
        return fallback
    candidate = Path(raw).expanduser()
    return candidate if candidate.is_absolute() else (_WEB_ROOT / candidate)


def _resolve_shared_root(paths: list[Path]) -> str | None:
    valid_paths = [str(path.resolve()) for path in paths if str(path).strip()]
    if not valid_paths:
        return None
    try:
        return str(Path(os.path.commonpath(valid_paths)))
    except Exception:
        return None


def _path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def build_admin_production_operations_summary() -> dict[str, Any]:
    settings = get_settings()
    session_policy = describe_session_operational_policy()
    cleanup_runtime = describe_uploads_cleanup_runtime()
    latest_cleanup_report = dict(cleanup_runtime.get("latest_report") or {})

    profile_path = _resolve_ops_path(
        settings.profile_uploads_path,
        _WEB_ROOT / "static" / "uploads" / "perfis",
    )
    mesa_path = _resolve_ops_path(
        settings.mesa_attachments_path,
        Path(tempfile.gettempdir()) / "tariel_control" / "mesa_anexos",
    )
    learning_path = _resolve_ops_path(
        settings.visual_learning_uploads_path,
        _WEB_ROOT / "static" / "uploads" / "aprendizados_ia",
    )
    shared_root = _resolve_shared_root([profile_path, mesa_path, learning_path])
    persistent_root_ready = all(
        _path_is_under(path, _RENDER_UPLOADS_ROOT)
        for path in (profile_path, mesa_path, learning_path)
    )

    blockers: list[str] = []
    warnings: list[str] = []

    if settings.em_producao:
        if settings.uploads_storage_mode not in {"persistent_disk", "custom"}:
            blockers.append("uploads_storage_mode_not_suitable_for_production")
        if settings.uploads_storage_mode == "persistent_disk" and not persistent_root_ready:
            blockers.append("persistent_disk_paths_not_under_expected_mount")
        if not settings.uploads_backup_required:
            blockers.append("uploads_backup_requirement_disabled")
        if not settings.uploads_restore_drill_required:
            blockers.append("uploads_restore_drill_requirement_disabled")
        if not bool(session_policy.get("multi_instance_ready", False)):
            blockers.append("session_policy_not_multi_instance_ready")
        if not settings.uploads_cleanup_enabled:
            blockers.append("automatic_upload_cleanup_disabled")

    if settings.uploads_cleanup_enabled and settings.uploads_cleanup_grace_days <= 0:
        warnings.append("automatic_upload_cleanup_without_grace_window")
    if settings.uploads_cleanup_enabled and not latest_cleanup_report:
        warnings.append("automatic_upload_cleanup_has_not_run_yet")
    if latest_cleanup_report.get("status") == "attention":
        blockers.append("automatic_upload_cleanup_last_run_attention")

    return {
        "contract_name": "AdminProductionOpsSummaryV1",
        "contract_version": "v1",
        "generated_at": utc_now().isoformat(),
        "environment": settings.ambiente,
        "uploads": {
            "storage_mode": settings.uploads_storage_mode,
            "shared_root": shared_root,
            "expected_persistent_root": str(_RENDER_UPLOADS_ROOT),
            "persistent_root_ready": persistent_root_ready,
            "profile_uploads_path": str(profile_path),
            "profile_retention_days": settings.uploads_profile_retention_days,
            "mesa_attachments_path": str(mesa_path),
            "mesa_retention_days": settings.uploads_mesa_retention_days,
            "visual_learning_uploads_path": str(learning_path),
            "learning_retention_days": settings.uploads_learning_retention_days,
            "cleanup_enabled": settings.uploads_cleanup_enabled,
            "cleanup_grace_days": settings.uploads_cleanup_grace_days,
            "cleanup_interval_hours": settings.uploads_cleanup_interval_hours,
            "cleanup_max_deletions_per_run": settings.uploads_cleanup_max_deletions_per_run,
            "cleanup_mode": "automatic" if settings.uploads_cleanup_enabled else "manual_review",
            "backup_required": settings.uploads_backup_required,
            "restore_drill_required": settings.uploads_restore_drill_required,
            "cleanup_runtime": cleanup_runtime,
        },
        "sessions": session_policy,
        "readiness": {
            "production_ready": len(blockers) == 0,
            "blockers": blockers,
            "warnings": warnings,
        },
    }


__all__ = ["build_admin_production_operations_summary"]
