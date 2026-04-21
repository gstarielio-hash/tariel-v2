from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.observability_privacy import protected_header_names
from app.core.settings import get_settings
from app.domains.admin.production_ops_summary import (
    build_admin_production_operations_summary,
)
from app.core.telemetry_support import observability_runtime_snapshot
from app.v2.contracts.envelopes import utc_now

_REPO_ROOT = Path(__file__).resolve().parents[4]
_REQUIRED_CHECKS = (
    "quality",
    "backend-stack",
    "contract-check",
    "web-e2e-mesa",
    "mobile-quality",
)


def _path_exists(relative_path: str) -> bool:
    return (_REPO_ROOT / relative_path).exists()


def build_admin_observability_operational_summary() -> dict[str, Any]:
    settings = get_settings()
    runtime = observability_runtime_snapshot(settings)

    return {
        "contract_name": "AdminObservabilitySummaryV1",
        "contract_version": "v1",
        "generated_at": utc_now().isoformat(),
        "environment": settings.ambiente,
        "release": settings.observability_release,
        "runtime": runtime,
        "privacy": {
            "lgpd_mode": "metadata_minimizada",
            "scrubbed_headers": list(protected_header_names()),
            "log_retention_days": settings.observability_log_retention_days,
            "perf_retention_days": settings.observability_perf_retention_days,
            "artifact_retention_days": settings.observability_artifact_retention_days,
            "replay_allowed_in_browser": bool(settings.browser_replay_enabled),
        },
        "repo_governance": {
            "codeowners_present": _path_exists(".github/CODEOWNERS"),
            "pull_request_template_present": _path_exists(".github/pull_request_template.md"),
            "branch_policy_doc_present": _path_exists(
                "docs/developer-experience/05_branch_protection_and_merge_policy.md"
            ),
            "automation_inventory_present": _path_exists(
                "docs/developer-experience/06_repo_automation_inventory.md"
            ),
            "required_checks": list(_REQUIRED_CHECKS),
        },
        "production_ops": build_admin_production_operations_summary(),
    }


__all__ = ["build_admin_observability_operational_summary"]
