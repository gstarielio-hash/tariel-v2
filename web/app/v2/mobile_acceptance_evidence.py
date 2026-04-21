from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.settings import env_int, env_str

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_STATE_FILE = _REPO_ROOT / ".tmp_online" / "devkit" / "mobile_pilot_lane_status.json"
_ALLOWED_PILOT_OUTCOMES = {"healthy", "candidate_for_real_tenant"}


@dataclass(frozen=True, slots=True)
class MobileV2DurableAcceptanceEvidence:
    available: bool
    valid_for_closure: bool
    status: str
    reason: str
    generated_at: str | None
    age_hours: float | None
    max_age_hours: int
    state_file: str
    artifact_dir: str | None
    final_report_path: str | None
    lane_status: str | None
    lane_result: str | None
    operator_run_outcome: str | None
    operator_run_reason: str | None
    feed_covered: bool
    thread_covered: bool
    environment_failure_signals: tuple[str, ...]
    pilot_outcome_after: str | None
    organic_validation_outcome_after: str | None
    candidate_ready_for_real_tenant_after: bool | None

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "valid_for_closure": self.valid_for_closure,
            "status": self.status,
            "reason": self.reason,
            "generated_at": self.generated_at,
            "age_hours": self.age_hours,
            "max_age_hours": self.max_age_hours,
            "state_file": self.state_file,
            "artifact_dir": self.artifact_dir,
            "final_report_path": self.final_report_path,
            "lane_status": self.lane_status,
            "lane_result": self.lane_result,
            "operator_run_outcome": self.operator_run_outcome,
            "operator_run_reason": self.operator_run_reason,
            "feed_covered": self.feed_covered,
            "thread_covered": self.thread_covered,
            "environment_failure_signals": list(self.environment_failure_signals),
            "pilot_outcome_after": self.pilot_outcome_after,
            "organic_validation_outcome_after": self.organic_validation_outcome_after,
            "candidate_ready_for_real_tenant_after": self.candidate_ready_for_real_tenant_after,
        }


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


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _read_final_report(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}
    payload: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            continue
        payload[key] = value.strip()
    return payload


def _state_file_path() -> Path:
    raw = env_str("TARIEL_MOBILE_ACCEPTANCE_STATE_FILE", str(_DEFAULT_STATE_FILE))
    return Path(raw).expanduser()


def _max_age_hours() -> int:
    return max(env_int("TARIEL_MOBILE_ACCEPTANCE_MAX_AGE_HOURS", 168), 1)


def load_mobile_v2_durable_acceptance_evidence() -> MobileV2DurableAcceptanceEvidence:
    state_file = _state_file_path()
    max_age_hours = _max_age_hours()
    if not state_file.is_file():
        return MobileV2DurableAcceptanceEvidence(
            available=False,
            valid_for_closure=False,
            status="missing",
            reason="state_file_missing",
            generated_at=None,
            age_hours=None,
            max_age_hours=max_age_hours,
            state_file=str(state_file),
            artifact_dir=None,
            final_report_path=None,
            lane_status=None,
            lane_result=None,
            operator_run_outcome=None,
            operator_run_reason=None,
            feed_covered=False,
            thread_covered=False,
            environment_failure_signals=(),
            pilot_outcome_after=None,
            organic_validation_outcome_after=None,
            candidate_ready_for_real_tenant_after=None,
        )

    payload = _read_json(state_file)
    if payload is None:
        return MobileV2DurableAcceptanceEvidence(
            available=False,
            valid_for_closure=False,
            status="invalid",
            reason="state_file_invalid_json",
            generated_at=None,
            age_hours=None,
            max_age_hours=max_age_hours,
            state_file=str(state_file),
            artifact_dir=None,
            final_report_path=None,
            lane_status=None,
            lane_result=None,
            operator_run_outcome=None,
            operator_run_reason=None,
            feed_covered=False,
            thread_covered=False,
            environment_failure_signals=(),
            pilot_outcome_after=None,
            organic_validation_outcome_after=None,
            candidate_ready_for_real_tenant_after=None,
        )

    generated_at = _parse_iso(payload.get("generatedAt"))
    age_hours = None
    if generated_at is not None:
        age_hours = round((_now_utc() - generated_at).total_seconds() / 3600, 4)

    artifact_dir_raw = str(payload.get("artifactDir") or "").strip()
    artifact_dir = Path(artifact_dir_raw).expanduser() if artifact_dir_raw else None
    final_report_path = artifact_dir / "final_report.md" if artifact_dir is not None else None
    final_report = _read_final_report(final_report_path) if final_report_path and final_report_path.is_file() else {}

    lane_status = str(payload.get("status") or "").strip() or None
    lane_result = str(payload.get("result") or "").strip() or None
    operator_run_outcome = str(payload.get("operatorRunOutcome") or "").strip() or None
    operator_run_reason = str(payload.get("operatorRunReason") or "").strip() or None
    feed_covered = bool(payload.get("feedCovered", False))
    thread_covered = bool(payload.get("threadCovered", False))
    environment_failure_signals = tuple(
        str(item).strip()
        for item in (payload.get("environmentFailureSignals") or [])
        if str(item).strip()
    )
    pilot_outcome_after = str(final_report.get("pilot_outcome_after") or "").strip() or None
    organic_validation_outcome_after = (
        str(final_report.get("organic_validation_outcome_after") or "").strip() or None
    )
    candidate_after_raw = str(final_report.get("candidate_ready_for_real_tenant_after") or "").strip().lower()
    candidate_ready_for_real_tenant_after = None
    if candidate_after_raw in {"true", "false"}:
        candidate_ready_for_real_tenant_after = candidate_after_raw == "true"

    status = "observing"
    reason = "durable_evidence_unverified"
    valid_for_closure = False
    if generated_at is None:
        status = "invalid"
        reason = "generated_at_missing"
    elif age_hours is None or age_hours > max_age_hours:
        status = "stale"
        reason = "durable_evidence_too_old"
    elif lane_status != "ok":
        status = "invalid"
        reason = "lane_status_not_ok"
    elif lane_result != "success_human_confirmed":
        status = "invalid"
        reason = "lane_result_not_success_human_confirmed"
    elif operator_run_outcome != "completed_successfully":
        status = "invalid"
        reason = "operator_run_not_completed_successfully"
    elif not feed_covered or not thread_covered:
        status = "invalid"
        reason = "required_surfaces_not_covered"
    elif environment_failure_signals:
        status = "invalid"
        reason = "environment_failure_signals_present"
    elif not final_report_path or not final_report_path.is_file():
        status = "invalid"
        reason = "final_report_missing"
    elif pilot_outcome_after not in _ALLOWED_PILOT_OUTCOMES:
        status = "invalid"
        reason = "pilot_outcome_after_not_promotable"
    else:
        status = "valid"
        reason = "durable_mobile_acceptance_evidence"
        valid_for_closure = True

    return MobileV2DurableAcceptanceEvidence(
        available=True,
        valid_for_closure=valid_for_closure,
        status=status,
        reason=reason,
        generated_at=generated_at.isoformat().replace("+00:00", "Z") if generated_at else None,
        age_hours=age_hours,
        max_age_hours=max_age_hours,
        state_file=str(state_file),
        artifact_dir=str(artifact_dir) if artifact_dir else None,
        final_report_path=str(final_report_path) if final_report_path else None,
        lane_status=lane_status,
        lane_result=lane_result,
        operator_run_outcome=operator_run_outcome,
        operator_run_reason=operator_run_reason,
        feed_covered=feed_covered,
        thread_covered=thread_covered,
        environment_failure_signals=environment_failure_signals,
        pilot_outcome_after=pilot_outcome_after,
        organic_validation_outcome_after=organic_validation_outcome_after,
        candidate_ready_for_real_tenant_after=candidate_ready_for_real_tenant_after,
    )


__all__ = [
    "MobileV2DurableAcceptanceEvidence",
    "load_mobile_v2_durable_acceptance_evidence",
]
