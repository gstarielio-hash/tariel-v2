"""Rollout e capabilities do contrato publico mobile V2."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request

from app.core.settings import env_bool, env_int, env_str
from app.shared.database import NivelAcesso
from app.v2.mobile_acceptance_evidence import (
    MobileV2DurableAcceptanceEvidence,
    load_mobile_v2_durable_acceptance_evidence,
)
from app.v2.mobile_rollout_metrics import (
    get_mobile_v2_probe_runtime_state,
    get_mobile_v2_surface_metrics_snapshot,
    record_mobile_v2_capabilities_check,
    record_mobile_v2_legacy_fallback,
    record_mobile_v2_public_read,
    record_mobile_v2_request_trace,
)
from app.v2.mobile_rollout_types import (
    MobileV2ArchitectureClosure,
    MobileV2BaseRolloutDecision,
    MobileV2PilotEvaluation,
    MobileV2PilotEvaluationThresholds,
    MobileV2PilotSurfaceWindow,
    MobileV2PilotTenantCandidate,
    MobileV2PromotionReadiness,
    MobileV2PromotionThresholds,
    MobileV2SurfaceEvaluation,
    MobileV2SurfaceState,
)
from app.v2.runtime import v2_android_public_contract_enabled

logger = logging.getLogger("tariel.rotas_inspetor")

MOBILE_V2_CAPABILITIES_CONTRACT_NAME = "MobileInspectorCapabilitiesV2"
MOBILE_V2_CAPABILITIES_CONTRACT_VERSION = "v2"
MOBILE_V2_CAPABILITIES_VERSION = "2026-03-25.09e"
MOBILE_V2_ROLLOUT_STATES = frozenset(
    {
        "legacy_only",
        "pilot_enabled",
        "candidate_for_promotion",
        "promoted",
        "hold",
        "rollback_forced",
    }
)
MOBILE_V2_READ_ENABLED_STATES = frozenset(
    {"pilot_enabled", "candidate_for_promotion", "promoted"}
)
MOBILE_V2_SURFACES = ("feed", "thread")
V2_ANDROID_ROLLOUT_FLAG = "TARIEL_V2_ANDROID_ROLLOUT"
V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST_FLAG = "TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST"
V2_ANDROID_ROLLOUT_COHORT_ALLOWLIST_FLAG = "TARIEL_V2_ANDROID_ROLLOUT_COHORT_ALLOWLIST"
V2_ANDROID_ROLLOUT_PERCENT_FLAG = "TARIEL_V2_ANDROID_ROLLOUT_PERCENT"
V2_ANDROID_ROLLOUT_STATE_OVERRIDES_FLAG = "TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES"
V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES_FLAG = "TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES"
V2_ANDROID_FEED_ENABLED_FLAG = "TARIEL_V2_ANDROID_FEED_ENABLED"
V2_ANDROID_THREAD_ENABLED_FLAG = "TARIEL_V2_ANDROID_THREAD_ENABLED"
V2_ANDROID_PROMOTION_MIN_REQUESTS_FLAG = "TARIEL_V2_ANDROID_PROMOTION_MIN_REQUESTS"
V2_ANDROID_PROMOTION_MAX_FALLBACK_RATE_PERCENT_FLAG = (
    "TARIEL_V2_ANDROID_PROMOTION_MAX_FALLBACK_RATE_PERCENT"
)
V2_ANDROID_PROMOTION_MAX_SERVICE_ERRORS_FLAG = (
    "TARIEL_V2_ANDROID_PROMOTION_MAX_SERVICE_ERRORS"
)
V2_ANDROID_PROMOTION_MAX_PARSE_VISIBILITY_ERRORS_FLAG = (
    "TARIEL_V2_ANDROID_PROMOTION_MAX_PARSE_VISIBILITY_ERRORS"
)
V2_ANDROID_PILOT_TENANT_KEY_FLAG = "TARIEL_V2_ANDROID_PILOT_TENANT_KEY"
V2_ANDROID_PILOT_PROMOTED_SINCE_FLAG = "TARIEL_V2_ANDROID_PILOT_PROMOTED_SINCE"
V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT_FLAG = (
    "TARIEL_V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT"
)
V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS_FLAG = (
    "TARIEL_V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS"
)
V2_ANDROID_PILOT_SOURCE_FLAG = "TARIEL_V2_ANDROID_PILOT_SOURCE"
V2_ANDROID_PILOT_NOTE_FLAG = "TARIEL_V2_ANDROID_PILOT_NOTE"
V2_ANDROID_PILOT_MIN_REQUESTS_FLAG = "TARIEL_V2_ANDROID_PILOT_MIN_REQUESTS"
V2_ANDROID_PILOT_MAX_FALLBACK_RATE_PERCENT_FLAG = (
    "TARIEL_V2_ANDROID_PILOT_MAX_FALLBACK_RATE_PERCENT"
)
V2_ANDROID_PILOT_MAX_VISIBILITY_VIOLATIONS_FLAG = (
    "TARIEL_V2_ANDROID_PILOT_MAX_VISIBILITY_VIOLATIONS"
)
V2_ANDROID_PILOT_MAX_PARSE_ERRORS_FLAG = "TARIEL_V2_ANDROID_PILOT_MAX_PARSE_ERRORS"
V2_ANDROID_PILOT_MAX_HTTP_FAILURES_FLAG = "TARIEL_V2_ANDROID_PILOT_MAX_HTTP_FAILURES"
V2_ANDROID_PILOT_REQUIRE_FULL_WINDOW_FLAG = "TARIEL_V2_ANDROID_PILOT_REQUIRE_FULL_WINDOW"
V2_ANDROID_PILOT_ALLOW_CANDIDATE_WITHOUT_WINDOW_ELAPSED_FLAG = (
    "TARIEL_V2_ANDROID_PILOT_ALLOW_CANDIDATE_WITHOUT_WINDOW_ELAPSED"
)
V2_ANDROID_PILOT_PROBE_FLAG = "TARIEL_V2_ANDROID_PILOT_PROBE"
HEADER_V2_ATTEMPTED = "X-Tariel-Mobile-V2-Attempted"
HEADER_V2_ROUTE = "X-Tariel-Mobile-V2-Route"
HEADER_V2_FALLBACK_REASON = "X-Tariel-Mobile-V2-Fallback-Reason"
HEADER_V2_GATE_SOURCE = "X-Tariel-Mobile-V2-Gate-Source"
HEADER_V2_CAPABILITIES_VERSION = "X-Tariel-Mobile-V2-Capabilities-Version"
HEADER_V2_ROLLOUT_BUCKET = "X-Tariel-Mobile-V2-Rollout-Bucket"
HEADER_V2_PROBE = "X-Tariel-Mobile-V2-Probe"
HEADER_V2_PROBE_SOURCE = "X-Tariel-Mobile-V2-Probe-Source"
HEADER_V2_USAGE_MODE = "X-Tariel-Mobile-Usage-Mode"
HEADER_V2_VALIDATION_SESSION = "X-Tariel-Mobile-Validation-Session"
HEADER_V2_OPERATOR_RUN = "X-Tariel-Mobile-Operator-Run"
HEADER_MOBILE_CENTRAL_TRACE = "X-Tariel-Mobile-Central-Trace"

_TOKEN_SANITIZER = re.compile(r"[^a-z0-9_.:-]+", re.IGNORECASE)
_TRUE_VALUES = {"1", "true", "t", "yes", "y", "sim", "on"}
_OVERRIDE_ENTRY_SPLIT = re.compile(r"[;,]+")
_SURFACE_FLAG_BY_NAME = {
    "feed": V2_ANDROID_FEED_ENABLED_FLAG,
    "thread": V2_ANDROID_THREAD_ENABLED_FLAG,
}
_SURFACE_DISABLED_REASON = {
    "feed": "feed_route_disabled",
    "thread": "thread_route_disabled",
}
_PILOT_SURFACE_STATES = frozenset({"promoted", "hold", "rollback_forced"})
_REMOTE_GATE_FALLBACK_REASONS = frozenset(
    {"rollout_denied", "legacy_only", "hold", "rollback_forced", "route_disabled"}
)
MOBILE_V2_PILOT_OUTCOMES = frozenset(
    {
        "insufficient_evidence",
        "observing",
        "healthy",
        "attention",
        "hold_recommended",
        "rollback_recommended",
        "candidate_for_real_tenant",
    }
)
MOBILE_V2_ARCHITECTURE_STATUSES = frozenset(
    {
        "observing",
        "closed_with_guardrails",
        "hold",
        "rollback_forced",
    }
)


@dataclass(frozen=True, slots=True)
class MobileV2RolloutState:
    rollout_state: str
    reason: str
    source: str
    tenant_key: str
    cohort_key: str
    rollout_bucket: int | None
    tenant_allowed: bool
    cohort_allowed: bool
    feed: MobileV2SurfaceState
    thread: MobileV2SurfaceState
    pilot_evaluation: MobileV2PilotEvaluation | None = None

    def to_capabilities(self) -> "MobileV2Capabilities":
        mobile_v2_reads_enabled = self.feed.enabled or self.thread.enabled
        from app.v2.mobile_organic_validation import get_mobile_v2_organic_validation_signal
        from app.v2.mobile_operator_run import get_mobile_v2_operator_validation_signal

        organic_signal = get_mobile_v2_organic_validation_signal(
            tenant_key=self.tenant_key,
        )
        operator_signal = get_mobile_v2_operator_validation_signal(
            tenant_key=self.tenant_key,
        )
        durable_acceptance_evidence = (
            load_mobile_v2_durable_acceptance_evidence()
            if self.tenant_key == _pilot_tenant_key()
            else None
        )
        architecture_closure = _resolve_mobile_v2_architecture_closure(
            rollout_state=self.rollout_state,
            feed=self.feed,
            thread=self.thread,
            pilot_evaluation=self.pilot_evaluation,
            organic_validation_active=bool(
                organic_signal.get("organic_validation_active", False)
            ),
            operator_validation_run_active=bool(
                operator_signal.get("operator_validation_run_active", False)
            ),
            durable_acceptance_evidence=durable_acceptance_evidence,
        )
        return MobileV2Capabilities(
            mobile_v2_reads_enabled=mobile_v2_reads_enabled,
            mobile_v2_feed_enabled=self.feed.enabled,
            mobile_v2_thread_enabled=self.thread.enabled,
            tenant_allowed=self.tenant_allowed,
            cohort_allowed=self.cohort_allowed,
            reason=self.reason,
            rollout_reason=self.reason,
            source=self.source,
            feed_reason=self.feed.reason,
            feed_source=self.feed.source,
            thread_reason=self.thread.reason,
            thread_source=self.thread.source,
            feed_endpoint_allowed=self.feed.endpoint_allowed,
            thread_endpoint_allowed=self.thread.endpoint_allowed,
            tenant_key=self.tenant_key,
            cohort_key=self.cohort_key,
            rollout_bucket=self.rollout_bucket,
            rollout_state=self.rollout_state,
            feed_rollout_state=self.feed.state,
            thread_rollout_state=self.thread.state,
            feed_candidate_for_promotion=self.feed.promotion_readiness.candidate_for_promotion,
            thread_candidate_for_promotion=self.thread.promotion_readiness.candidate_for_promotion,
            feed_promoted=self.feed.promoted,
            thread_promoted=self.thread.promoted,
            feed_hold=self.feed.hold,
            thread_hold=self.thread.hold,
            feed_rollback_forced=self.feed.rollback_forced,
            thread_rollback_forced=self.thread.rollback_forced,
            feed_promoted_since=self.feed.promoted_since,
            thread_promoted_since=self.thread.promoted_since,
            feed_rollout_window_started_at=self.feed.rollout_window_started_at,
            thread_rollout_window_started_at=self.thread.rollout_window_started_at,
            feed_rollback_window_until=self.feed.rollback_window_until,
            thread_rollback_window_until=self.thread.rollback_window_until,
            feed_rollback_window_active=self.feed.rollback_window_active,
            thread_rollback_window_active=self.thread.rollback_window_active,
            organic_validation_active=bool(
                organic_signal.get("organic_validation_active", False)
            ),
            organic_validation_session_id=(
                str(organic_signal.get("organic_validation_session_id") or "").strip()
                or None
            ),
            organic_validation_surfaces=tuple(
                str(item).strip()
                for item in organic_signal.get("organic_validation_surfaces", [])
                if str(item).strip()
            ),
            organic_validation_target_suggestions=tuple(
                dict(item)
                for item in organic_signal.get(
                    "organic_validation_target_suggestions",
                    [],
                )
                if isinstance(item, dict)
            ),
            organic_validation_surface_coverage=tuple(
                dict(item)
                for item in organic_signal.get(
                    "organic_validation_surface_coverage",
                    [],
                )
                if isinstance(item, dict)
            ),
            organic_validation_has_partial_coverage=bool(
                organic_signal.get("organic_validation_has_partial_coverage", False)
            ),
            organic_validation_targets_ready=bool(
                organic_signal.get("organic_validation_targets_ready", False)
            ),
            operator_validation_run_active=bool(
                operator_signal.get("operator_validation_run_active", False)
            ),
            operator_validation_run_id=(
                str(operator_signal.get("operator_validation_run_id") or "").strip()
                or None
            ),
            operator_validation_required_surfaces=tuple(
                str(item).strip()
                for item in operator_signal.get(
                    "operator_validation_required_surfaces",
                    [],
                )
                if str(item).strip()
            ),
            mobile_v2_architecture_status=architecture_closure.status,
            mobile_v2_architecture_reason=architecture_closure.reason,
            mobile_v2_legacy_fallback_policy=(
                architecture_closure.legacy_fallback_policy
            ),
            mobile_v2_transition_active=architecture_closure.transition_active,
        )

    def to_summary_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tenant_key": self.tenant_key,
            "cohort_key": self.cohort_key,
            "rollout_bucket": self.rollout_bucket,
            "rollout_state": self.rollout_state,
            "reason": self.reason,
            "source": self.source,
            "tenant_allowed": self.tenant_allowed,
            "cohort_allowed": self.cohort_allowed,
            "mobile_v2_reads_enabled": self.feed.enabled or self.thread.enabled,
            "feed_state": self.feed.state,
            "thread_state": self.thread.state,
        }
        if self.pilot_evaluation is not None:
            payload.update(self.pilot_evaluation.to_public_payload())
        else:
            payload.update(
                {
                    "pilot_outcome": None,
                    "evidence_level": None,
                    "evaluation_reason": None,
                    "candidate_for_real_tenant": False,
                    "requires_hold": False,
                    "requires_rollback": False,
                    "window_elapsed": False,
                    "requests_v2_observed": 0,
                    "requests_fallback_observed": 0,
                    "fallback_rate": 0.0,
                    "fallback_reason_breakdown": [],
                    "organic_requests_v2": 0,
                    "organic_requests_fallback": 0,
                    "probe_requests_v2": 0,
                    "probe_requests_fallback": 0,
                    "probe_reason_breakdown": [],
                    "probe_resolved_insufficient_evidence": False,
                    "evaluation_thresholds": {},
                }
            )
        return payload


@dataclass(frozen=True, slots=True)
class MobileV2Capabilities:
    mobile_v2_reads_enabled: bool
    mobile_v2_feed_enabled: bool
    mobile_v2_thread_enabled: bool
    tenant_allowed: bool
    cohort_allowed: bool
    reason: str
    rollout_reason: str
    source: str
    feed_reason: str
    feed_source: str
    thread_reason: str
    thread_source: str
    feed_endpoint_allowed: bool
    thread_endpoint_allowed: bool
    tenant_key: str
    cohort_key: str
    rollout_bucket: int | None
    rollout_state: str
    feed_rollout_state: str
    thread_rollout_state: str
    feed_candidate_for_promotion: bool
    thread_candidate_for_promotion: bool
    feed_promoted: bool
    thread_promoted: bool
    feed_hold: bool
    thread_hold: bool
    feed_rollback_forced: bool
    thread_rollback_forced: bool
    feed_promoted_since: str | None = None
    thread_promoted_since: str | None = None
    feed_rollout_window_started_at: str | None = None
    thread_rollout_window_started_at: str | None = None
    feed_rollback_window_until: str | None = None
    thread_rollback_window_until: str | None = None
    feed_rollback_window_active: bool = False
    thread_rollback_window_active: bool = False
    organic_validation_active: bool = False
    organic_validation_session_id: str | None = None
    organic_validation_surfaces: tuple[str, ...] = ()
    organic_validation_target_suggestions: tuple[dict[str, Any], ...] = ()
    organic_validation_surface_coverage: tuple[dict[str, Any], ...] = ()
    organic_validation_has_partial_coverage: bool = False
    organic_validation_targets_ready: bool = False
    operator_validation_run_active: bool = False
    operator_validation_run_id: str | None = None
    operator_validation_required_surfaces: tuple[str, ...] = ()
    mobile_v2_architecture_status: str = "observing"
    mobile_v2_architecture_reason: str = "not_evaluated"
    mobile_v2_legacy_fallback_policy: str = "allowed_during_transition"
    mobile_v2_transition_active: bool = True
    capabilities_version: str = MOBILE_V2_CAPABILITIES_VERSION

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "contract_name": MOBILE_V2_CAPABILITIES_CONTRACT_NAME,
            "contract_version": MOBILE_V2_CAPABILITIES_CONTRACT_VERSION,
            "capabilities_version": self.capabilities_version,
            "mobile_v2_reads_enabled": self.mobile_v2_reads_enabled,
            "mobile_v2_feed_enabled": self.mobile_v2_feed_enabled,
            "mobile_v2_thread_enabled": self.mobile_v2_thread_enabled,
            "tenant_allowed": self.tenant_allowed,
            "cohort_allowed": self.cohort_allowed,
            "reason": self.reason,
            "rollout_reason": self.rollout_reason,
            "source": self.source,
            "feed_reason": self.feed_reason,
            "feed_source": self.feed_source,
            "thread_reason": self.thread_reason,
            "thread_source": self.thread_source,
            "rollout_bucket": self.rollout_bucket,
            "rollout_state": self.rollout_state,
            "feed_rollout_state": self.feed_rollout_state,
            "thread_rollout_state": self.thread_rollout_state,
            "feed_candidate_for_promotion": self.feed_candidate_for_promotion,
            "thread_candidate_for_promotion": self.thread_candidate_for_promotion,
            "feed_promoted": self.feed_promoted,
            "thread_promoted": self.thread_promoted,
            "feed_hold": self.feed_hold,
            "thread_hold": self.thread_hold,
            "feed_rollback_forced": self.feed_rollback_forced,
            "thread_rollback_forced": self.thread_rollback_forced,
            "feed_promoted_since": self.feed_promoted_since,
            "thread_promoted_since": self.thread_promoted_since,
            "feed_rollout_window_started_at": self.feed_rollout_window_started_at,
            "thread_rollout_window_started_at": self.thread_rollout_window_started_at,
            "feed_rollback_window_until": self.feed_rollback_window_until,
            "thread_rollback_window_until": self.thread_rollback_window_until,
            "feed_rollback_window_active": self.feed_rollback_window_active,
            "thread_rollback_window_active": self.thread_rollback_window_active,
            "organic_validation_active": self.organic_validation_active,
            "organic_validation_session_id": self.organic_validation_session_id,
            "organic_validation_surfaces": list(self.organic_validation_surfaces),
            "organic_validation_target_suggestions": [
                dict(item) for item in self.organic_validation_target_suggestions
            ],
            "organic_validation_surface_coverage": [
                dict(item) for item in self.organic_validation_surface_coverage
            ],
            "organic_validation_has_partial_coverage": (
                self.organic_validation_has_partial_coverage
            ),
            "organic_validation_targets_ready": self.organic_validation_targets_ready,
            "operator_validation_run_active": self.operator_validation_run_active,
            "operator_validation_run_id": self.operator_validation_run_id,
            "operator_validation_required_surfaces": list(
                self.operator_validation_required_surfaces
            ),
            "mobile_v2_architecture_status": self.mobile_v2_architecture_status,
            "mobile_v2_architecture_reason": self.mobile_v2_architecture_reason,
            "mobile_v2_legacy_fallback_policy": self.mobile_v2_legacy_fallback_policy,
            "mobile_v2_transition_active": self.mobile_v2_transition_active,
        }

    def to_debug_summary(self) -> dict[str, Any]:
        payload = self.to_public_payload()
        payload.update(
            {
                "tenant_key": self.tenant_key,
                "cohort_key": self.cohort_key,
                "feed_endpoint_allowed": self.feed_endpoint_allowed,
                "thread_endpoint_allowed": self.thread_endpoint_allowed,
            }
        )
        return payload


def _normalize_token(value: object, *, fallback: str) -> str:
    raw = str(value or "").strip().lower()
    cleaned = _TOKEN_SANITIZER.sub("_", raw).strip("_.:-")
    return cleaned[:80] or fallback


def _normalize_rollout_state(value: object) -> str:
    state = _normalize_token(value, fallback="")
    return state if state in MOBILE_V2_ROLLOUT_STATES else ""


def _parse_allowlist(raw_value: str) -> set[str]:
    return {item.strip() for item in str(raw_value or "").split(",") if item.strip()}


def _parse_bucket_allowlist(raw_value: str) -> set[int]:
    buckets: set[int] = set()
    for item in str(raw_value or "").split(","):
        value = item.strip()
        if not value:
            continue
        try:
            buckets.add(max(0, min(99, int(value))))
        except ValueError:
            continue
    return buckets


def _parse_state_overrides(raw_value: str) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for entry in _OVERRIDE_ENTRY_SPLIT.split(str(raw_value or "")):
        raw_entry = entry.strip()
        if not raw_entry or "=" not in raw_entry:
            continue
        tenant_key, raw_state = raw_entry.split("=", 1)
        tenant = str(tenant_key or "").strip()
        state = _normalize_rollout_state(raw_state)
        if tenant and state:
            overrides[tenant] = state
    return overrides


def _parse_surface_state_overrides(raw_value: str) -> dict[tuple[str, str], str]:
    overrides: dict[tuple[str, str], str] = {}
    for entry in _OVERRIDE_ENTRY_SPLIT.split(str(raw_value or "")):
        raw_entry = entry.strip()
        if not raw_entry or "=" not in raw_entry or ":" not in raw_entry:
            continue
        raw_target, raw_state = raw_entry.split("=", 1)
        tenant_key, surface = raw_target.split(":", 1)
        tenant = str(tenant_key or "").strip()
        normalized_surface = _normalize_token(surface, fallback="")
        state = _normalize_rollout_state(raw_state)
        if tenant and normalized_surface in MOBILE_V2_SURFACES and state:
            overrides[(tenant, normalized_surface)] = state
    return overrides


def _clamp_percentage(value: int) -> int:
    return max(0, min(100, int(value)))


def _stable_bucket(cohort_key: str) -> int:
    digest = hashlib.sha256(cohort_key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def _promotion_thresholds() -> MobileV2PromotionThresholds:
    return MobileV2PromotionThresholds(
        min_requests=max(env_int(V2_ANDROID_PROMOTION_MIN_REQUESTS_FLAG, 5), 1),
        max_fallback_rate_percent=_clamp_percentage(
            env_int(V2_ANDROID_PROMOTION_MAX_FALLBACK_RATE_PERCENT_FLAG, 15)
        ),
        max_service_errors=max(env_int(V2_ANDROID_PROMOTION_MAX_SERVICE_ERRORS_FLAG, 0), 0),
        max_parse_visibility_errors=max(
            env_int(V2_ANDROID_PROMOTION_MAX_PARSE_VISIBILITY_ERRORS_FLAG, 0),
            0,
        ),
    )


def _pilot_evaluation_thresholds() -> MobileV2PilotEvaluationThresholds:
    promotion_thresholds = _promotion_thresholds()
    return MobileV2PilotEvaluationThresholds(
        min_requests=max(
            env_int(V2_ANDROID_PILOT_MIN_REQUESTS_FLAG, promotion_thresholds.min_requests),
            1,
        ),
        max_fallback_rate_percent=_clamp_percentage(
            env_int(
                V2_ANDROID_PILOT_MAX_FALLBACK_RATE_PERCENT_FLAG,
                promotion_thresholds.max_fallback_rate_percent,
            )
        ),
        max_visibility_violations=max(
            env_int(V2_ANDROID_PILOT_MAX_VISIBILITY_VIOLATIONS_FLAG, 0),
            0,
        ),
        max_parse_errors=max(env_int(V2_ANDROID_PILOT_MAX_PARSE_ERRORS_FLAG, 0), 0),
        max_http_failures=max(
            env_int(
                V2_ANDROID_PILOT_MAX_HTTP_FAILURES_FLAG,
                promotion_thresholds.max_service_errors,
            ),
            0,
        ),
        require_full_window=env_bool(V2_ANDROID_PILOT_REQUIRE_FULL_WINDOW_FLAG, True),
        allow_candidate_without_window_elapsed=env_bool(
            V2_ANDROID_PILOT_ALLOW_CANDIDATE_WITHOUT_WINDOW_ELAPSED_FLAG,
            False,
        ),
    )


def _parse_iso_datetime(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _datetime_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _pilot_tenant_key() -> str:
    return str(env_str(V2_ANDROID_PILOT_TENANT_KEY_FLAG, "") or "").strip()


def _pilot_window_hours() -> int:
    return max(env_int(V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS_FLAG, 24), 1)


def _pilot_promoted_since() -> datetime | None:
    return _parse_iso_datetime(env_str(V2_ANDROID_PILOT_PROMOTED_SINCE_FLAG, ""))


def _pilot_rollout_window_started_at() -> datetime | None:
    started_at = _parse_iso_datetime(
        env_str(V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT_FLAG, "")
    )
    return started_at or _pilot_promoted_since()


def _pilot_health_status(
    *,
    state: str,
    readiness: MobileV2PromotionReadiness,
) -> tuple[str, str]:
    if state == "rollback_forced":
        return ("rollback_forced", "rollback_ativo")
    if state == "hold":
        return ("attention", "piloto_em_hold")
    if readiness.observed_requests <= 0 or readiness.v2_served <= 0:
        return ("attention", "aguardando_uso_v2_confirmado")
    if readiness.service_errors > readiness.thresholds.max_service_errors:
        return ("attention", "instabilidade_operacional")
    if (
        readiness.parse_errors + readiness.visibility_errors
        > readiness.thresholds.max_parse_visibility_errors
    ):
        return ("attention", "sinais_de_incompatibilidade")
    if readiness.fallback_rate > (readiness.thresholds.max_fallback_rate_percent / 100):
        return ("attention", "fallback_acima_do_limite")
    return ("healthy", "piloto_estavel")


def _build_pilot_window(
    *,
    tenant_key: str,
    configured_state: str,
    state: str,
    readiness: MobileV2PromotionReadiness,
) -> MobileV2PilotSurfaceWindow | None:
    pilot_tenant_key = _pilot_tenant_key()
    if not pilot_tenant_key or tenant_key != pilot_tenant_key:
        return None

    if configured_state not in _PILOT_SURFACE_STATES and state not in _PILOT_SURFACE_STATES:
        return None

    promoted_since = _pilot_promoted_since()
    rollout_window_started_at = _pilot_rollout_window_started_at() or promoted_since
    rollback_window_until = (
        rollout_window_started_at + timedelta(hours=_pilot_window_hours())
        if rollout_window_started_at is not None
        else None
    )
    now = datetime.now(timezone.utc)
    rollback_window_active = bool(
        rollback_window_until and now <= rollback_window_until
    )
    window_elapsed = bool(rollback_window_until and now > rollback_window_until)
    health_status, health_reason = _pilot_health_status(
        state=state,
        readiness=readiness,
    )
    return MobileV2PilotSurfaceWindow(
        promoted_since=_datetime_to_iso(promoted_since),
        rollout_window_started_at=_datetime_to_iso(rollout_window_started_at),
        rollback_window_until=_datetime_to_iso(rollback_window_until),
        rollback_window_active=rollback_window_active,
        window_elapsed=window_elapsed,
        source=_normalize_token(
            env_str(V2_ANDROID_PILOT_SOURCE_FLAG, "manual_promotion"),
            fallback="manual_promotion",
        ),
        note=_normalize_token(env_str(V2_ANDROID_PILOT_NOTE_FLAG, ""), fallback=""),
        health_status=health_status,
        health_reason=health_reason,
    )


def discover_mobile_v2_safe_pilot_candidates() -> list[MobileV2PilotTenantCandidate]:
    from sqlalchemy import func, select

    from app.shared.database import Empresa, SessaoLocal, Usuario

    candidates: list[MobileV2PilotTenantCandidate] = []
    with SessaoLocal() as banco:
        empresas = banco.execute(
            select(
                Empresa.id,
                Empresa.nome_fantasia,
                Empresa.cnpj,
                Empresa.observacoes,
            )
        ).all()

        for empresa_id, nome_fantasia, cnpj, observacoes in empresas:
            nome = str(nome_fantasia or "").strip()
            cnpj_normalizado = re.sub(r"\D+", "", str(cnpj or ""))
            observacoes_norm = str(observacoes or "").strip().lower()
            safety_reason = ""
            source = ""
            if nome == "Empresa Demo (DEV)" and cnpj_normalizado == "00000000000000":
                safety_reason = "seed_dev_demo_company"
                source = "bootstrap_seed"
            elif nome == "Tariel.ia Interno (DEV)" and cnpj_normalizado == "99999999999999":
                safety_reason = "seed_dev_internal_company"
                source = "bootstrap_seed"
            elif "carga local" in observacoes_norm and "teste" in observacoes_norm:
                safety_reason = "local_load_lab_company"
                source = "company_observations"

            if not safety_reason:
                continue

            inspector_users = int(
                banco.scalar(
                    select(func.count())
                    .select_from(Usuario)
                    .where(
                        Usuario.empresa_id == int(empresa_id),
                        Usuario.nivel_acesso == int(NivelAcesso.INSPETOR.value),
                        Usuario.ativo.is_(True),
                    )
                )
                or 0
            )
            if inspector_users <= 0:
                continue

            candidates.append(
                MobileV2PilotTenantCandidate(
                    tenant_key=str(empresa_id),
                    tenant_label=nome,
                    safety_reason=safety_reason,
                    source=source,
                    inspector_users=inspector_users,
                )
            )
    priority = {
        "seed_dev_demo_company": 0,
        "seed_dev_internal_company": 1,
        "local_load_lab_company": 2,
    }
    candidates.sort(
        key=lambda item: (
            priority.get(item.safety_reason, 99),
            item.tenant_key,
        )
    )
    return candidates


def _reason_rows(reason_counts: dict[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted(
            (
                (str(reason), int(count))
                for reason, count in reason_counts.items()
                if int(count) > 0
            ),
            key=lambda item: (-item[1], item[0]),
        )
    )


def _subtract_reason_counts(
    total_counts: dict[str, int],
    probe_counts: dict[str, int],
) -> dict[str, int]:
    remaining: dict[str, int] = {}
    reason_keys = set(total_counts) | set(probe_counts)
    for reason in reason_keys:
        count = int(total_counts.get(reason, 0)) - int(probe_counts.get(reason, 0))
        if count > 0:
            remaining[str(reason)] = count
    return remaining


def _resolve_base_rollout_for_principal(
    *,
    tenant_key: str,
    nivel_acesso: int,
) -> MobileV2BaseRolloutDecision:
    tenant_key = str(tenant_key or "").strip()
    cohort_key = f"tenant:{tenant_key or 'unknown'}"
    rollout_bucket = _stable_bucket(cohort_key) if tenant_key else None
    tenant_allowlist = _parse_allowlist(env_str(V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST_FLAG, ""))
    tenant_allowed = bool(tenant_key and tenant_key in tenant_allowlist)
    cohort_allowlist = _parse_bucket_allowlist(env_str(V2_ANDROID_ROLLOUT_COHORT_ALLOWLIST_FLAG, ""))
    cohort_allowed = rollout_bucket is not None and rollout_bucket in cohort_allowlist
    state_overrides = _parse_state_overrides(env_str(V2_ANDROID_ROLLOUT_STATE_OVERRIDES_FLAG, ""))

    if nivel_acesso != int(NivelAcesso.INSPETOR.value):
        return MobileV2BaseRolloutDecision(
            state="legacy_only",
            enabled=False,
            reason="role_not_supported",
            source="role",
            tenant_key=tenant_key,
            cohort_key=cohort_key,
            rollout_bucket=rollout_bucket,
            tenant_allowed=tenant_allowed,
            cohort_allowed=bool(cohort_allowed),
        )

    if not v2_android_public_contract_enabled():
        return MobileV2BaseRolloutDecision(
            state="legacy_only",
            enabled=False,
            reason="backend_public_contract_disabled",
            source="public_contract_flag",
            tenant_key=tenant_key,
            cohort_key=cohort_key,
            rollout_bucket=rollout_bucket,
            tenant_allowed=tenant_allowed,
            cohort_allowed=bool(cohort_allowed),
        )

    if not env_bool(V2_ANDROID_ROLLOUT_FLAG, False):
        return MobileV2BaseRolloutDecision(
            state="legacy_only",
            enabled=False,
            reason="backend_rollout_disabled",
            source="rollout_flag",
            tenant_key=tenant_key,
            cohort_key=cohort_key,
            rollout_bucket=rollout_bucket,
            tenant_allowed=tenant_allowed,
            cohort_allowed=bool(cohort_allowed),
        )

    override_state = state_overrides.get(tenant_key, "")
    if override_state:
        return MobileV2BaseRolloutDecision(
            state=override_state,
            enabled=override_state in MOBILE_V2_READ_ENABLED_STATES,
            reason=override_state,
            source="tenant_state_override",
            tenant_key=tenant_key,
            cohort_key=cohort_key,
            rollout_bucket=rollout_bucket,
            tenant_allowed=tenant_allowed,
            cohort_allowed=bool(cohort_allowed),
        )

    if tenant_allowed:
        return MobileV2BaseRolloutDecision(
            state="pilot_enabled",
            enabled=True,
            reason="tenant_allowlisted",
            source="tenant_allowlist",
            tenant_key=tenant_key,
            cohort_key=cohort_key,
            rollout_bucket=rollout_bucket,
            tenant_allowed=True,
            cohort_allowed=bool(cohort_allowed),
        )

    if cohort_allowed:
        return MobileV2BaseRolloutDecision(
            state="pilot_enabled",
            enabled=True,
            reason="cohort_allowlisted",
            source="cohort_allowlist",
            tenant_key=tenant_key,
            cohort_key=cohort_key,
            rollout_bucket=rollout_bucket,
            tenant_allowed=False,
            cohort_allowed=True,
        )

    rollout_percent = _clamp_percentage(env_int(V2_ANDROID_ROLLOUT_PERCENT_FLAG, 0))
    if rollout_percent >= 100 and rollout_bucket is not None:
        return MobileV2BaseRolloutDecision(
            state="pilot_enabled",
            enabled=True,
            reason="cohort_full_rollout",
            source="cohort",
            tenant_key=tenant_key,
            cohort_key=cohort_key,
            rollout_bucket=rollout_bucket,
            tenant_allowed=False,
            cohort_allowed=True,
        )

    if rollout_percent > 0 and rollout_bucket is not None and rollout_bucket < rollout_percent:
        return MobileV2BaseRolloutDecision(
            state="pilot_enabled",
            enabled=True,
            reason="cohort_rollout",
            source="cohort",
            tenant_key=tenant_key,
            cohort_key=cohort_key,
            rollout_bucket=rollout_bucket,
            tenant_allowed=False,
            cohort_allowed=True,
        )

    if not tenant_key:
        return MobileV2BaseRolloutDecision(
            state="legacy_only",
            enabled=False,
            reason="tenant_missing_for_rollout",
            source="tenant",
            tenant_key=tenant_key,
            cohort_key=cohort_key,
            rollout_bucket=rollout_bucket,
            tenant_allowed=False,
            cohort_allowed=False,
        )

    return MobileV2BaseRolloutDecision(
        state="legacy_only",
        enabled=False,
        reason="cohort_not_allowed",
        source="cohort",
        tenant_key=tenant_key,
        cohort_key=cohort_key,
        rollout_bucket=rollout_bucket,
        tenant_allowed=False,
        cohort_allowed=False,
    )


def evaluate_mobile_v2_promotion_readiness(
    *,
    tenant_key: str,
    surface: str,
) -> MobileV2PromotionReadiness:
    thresholds = _promotion_thresholds()
    if surface not in MOBILE_V2_SURFACES:
        raise ValueError(f"Unsupported mobile V2 surface: {surface}")

    if not tenant_key:
        return MobileV2PromotionReadiness(
            surface=surface,
            candidate_for_promotion=False,
            observed_requests=0,
            v2_served=0,
            legacy_fallbacks=0,
            rollout_denied=0,
            parse_errors=0,
            visibility_errors=0,
            service_errors=0,
            fallback_rate=0.0,
            reasons=("tenant_missing_for_rollout",),
            legacy_fallback_reasons=(),
            rollout_denied_reasons=(),
            thresholds=thresholds,
        )

    snapshot = get_mobile_v2_surface_metrics_snapshot(tenant_key=tenant_key, endpoint=surface)
    metrics = snapshot["metrics"]
    reason_counts = snapshot["reason_counts"]
    probe_metrics = snapshot.get("probe_metrics", {})
    probe_reason_counts = snapshot.get("probe_reason_counts", {})
    fallback_reasons = dict(reason_counts.get("legacy_fallbacks", {}))
    probe_fallback_reasons = dict(probe_reason_counts.get("legacy_fallbacks", {}))
    rollout_denied_reasons = dict(reason_counts.get("rollout_denied", {}))

    rollout_denied = int(metrics.get("rollout_denied", 0))
    organic_fallback_reasons = _subtract_reason_counts(
        fallback_reasons,
        probe_fallback_reasons,
    )
    remote_gate_fallbacks = {
        reason: int(count)
        for reason, count in organic_fallback_reasons.items()
        if reason in _REMOTE_GATE_FALLBACK_REASONS and int(count) > 0
    }
    for reason, count in remote_gate_fallbacks.items():
        rollout_denied_reasons[reason] = int(rollout_denied_reasons.get(reason, 0)) + int(count)
    rollout_denied += sum(remote_gate_fallbacks.values())
    actual_fallback_reasons = {
        reason: int(count)
        for reason, count in organic_fallback_reasons.items()
        if reason not in _REMOTE_GATE_FALLBACK_REASONS and int(count) > 0
    }
    actual_fallbacks = sum(actual_fallback_reasons.values())
    total_v2_served = int(metrics.get("v2_served", 0))
    probe_v2_served = int(probe_metrics.get("v2_served", 0))
    organic_v2_served = max(0, total_v2_served - probe_v2_served)
    probe_legacy_fallbacks = int(probe_metrics.get("legacy_fallbacks", 0))
    observed_requests = total_v2_served + actual_fallbacks
    parse_errors = int(actual_fallback_reasons.get("parse_error", 0))
    visibility_errors = int(actual_fallback_reasons.get("visibility_violation", 0))
    service_errors = sum(
        int(actual_fallback_reasons.get(reason, 0))
        for reason in (
            "http_404",
            "http_error",
            "capabilities_fetch_error",
            "adapter_error",
            "unknown",
        )
    )
    fallback_rate = (
        round(actual_fallbacks / observed_requests, 4) if observed_requests > 0 else 0.0
    )

    reasons: list[str] = []
    if observed_requests < thresholds.min_requests:
        reasons.append("insufficient_volume")
    if fallback_rate > (thresholds.max_fallback_rate_percent / 100):
        reasons.append("fallback_rate_high")
    if (parse_errors + visibility_errors) > thresholds.max_parse_visibility_errors:
        reasons.append("parse_or_visibility_errors_detected")
    if service_errors > thresholds.max_service_errors:
        reasons.append("service_errors_detected")

    return MobileV2PromotionReadiness(
        surface=surface,
        candidate_for_promotion=not reasons,
        observed_requests=observed_requests,
        v2_served=total_v2_served,
        legacy_fallbacks=actual_fallbacks,
        rollout_denied=rollout_denied,
        parse_errors=parse_errors,
        visibility_errors=visibility_errors,
        service_errors=service_errors,
        fallback_rate=fallback_rate,
        reasons=tuple(reasons),
        legacy_fallback_reasons=_reason_rows(actual_fallback_reasons),
        rollout_denied_reasons=_reason_rows(rollout_denied_reasons),
        organic_v2_served=organic_v2_served,
        organic_legacy_fallbacks=actual_fallbacks,
        probe_v2_served=probe_v2_served,
        probe_legacy_fallbacks=probe_legacy_fallbacks,
        probe_legacy_fallback_reasons=_reason_rows(probe_fallback_reasons),
        thresholds=thresholds,
    )


def _pilot_evidence_level(
    *,
    observed_requests: int,
    thresholds: MobileV2PilotEvaluationThresholds,
) -> str:
    if observed_requests <= 0:
        return "none"
    if observed_requests < thresholds.min_requests:
        return "limited"
    return "sufficient"


def _evaluate_mobile_v2_surface_pilot(
    *,
    tenant_key: str,
    surface: str,
    state: str,
    readiness: MobileV2PromotionReadiness,
    pilot_window: MobileV2PilotSurfaceWindow | None,
) -> MobileV2SurfaceEvaluation:
    thresholds = _pilot_evaluation_thresholds()
    window_elapsed = bool(pilot_window and pilot_window.window_elapsed)
    observed_requests = readiness.observed_requests
    organic_observed_requests = (
        readiness.organic_v2_served + readiness.organic_legacy_fallbacks
    )
    evidence_level = _pilot_evidence_level(
        observed_requests=observed_requests,
        thresholds=thresholds,
    )
    fallback_rate_limit = thresholds.max_fallback_rate_percent / 100
    parse_errors = readiness.parse_errors
    visibility_errors = readiness.visibility_errors
    http_failures = readiness.service_errors
    fallback_rate = readiness.fallback_rate
    has_window_requirement = (
        thresholds.require_full_window
        and not window_elapsed
        and not thresholds.allow_candidate_without_window_elapsed
    )
    probe_resolved_insufficient_evidence = (
        observed_requests >= thresholds.min_requests
        and organic_observed_requests < thresholds.min_requests
        and readiness.probe_v2_served > 0
    )

    pilot_outcome = "healthy"
    evaluation_reason = "pilot_stable"
    candidate_for_real_tenant = False
    requires_hold = False
    requires_rollback = False

    if state == "rollback_forced":
        pilot_outcome = "rollback_recommended"
        evaluation_reason = "rollback_forced_by_override"
        requires_rollback = True
    elif (
        parse_errors > thresholds.max_parse_errors
        or visibility_errors > thresholds.max_visibility_violations
    ):
        pilot_outcome = "rollback_recommended"
        evaluation_reason = "contract_safety_threshold_exceeded"
        requires_rollback = True
    elif state == "hold":
        pilot_outcome = "hold_recommended"
        evaluation_reason = "hold_requested_by_override"
        requires_hold = True
    elif observed_requests <= 0:
        pilot_outcome = "insufficient_evidence"
        evaluation_reason = "no_v2_traffic_observed"
    elif observed_requests < thresholds.min_requests:
        pilot_outcome = "observing" if not window_elapsed else "insufficient_evidence"
        evaluation_reason = (
            "collecting_minimum_volume"
            if not window_elapsed
            else "minimum_volume_not_reached"
        )
    elif http_failures > thresholds.max_http_failures:
        pilot_outcome = "hold_recommended" if window_elapsed else "attention"
        evaluation_reason = "http_failures_above_threshold"
        requires_hold = pilot_outcome == "hold_recommended"
    elif fallback_rate > fallback_rate_limit:
        pilot_outcome = "hold_recommended" if window_elapsed else "attention"
        evaluation_reason = "fallback_rate_above_threshold"
        requires_hold = pilot_outcome == "hold_recommended"
    elif has_window_requirement:
        pilot_outcome = "observing"
        evaluation_reason = "awaiting_full_rollback_window"
    elif (
        readiness.legacy_fallbacks > 0
        or http_failures > 0
        or parse_errors > 0
        or visibility_errors > 0
    ):
        pilot_outcome = "attention"
        evaluation_reason = "fallbacks_or_failures_observed"
    else:
        candidate_for_real_tenant = (
            tenant_key == _pilot_tenant_key()
            and state == "promoted"
            and organic_observed_requests >= thresholds.min_requests
            and (window_elapsed or thresholds.allow_candidate_without_window_elapsed)
        )
        pilot_outcome = (
            "candidate_for_real_tenant" if candidate_for_real_tenant else "healthy"
        )
        evaluation_reason = (
            "ready_for_real_tenant_candidate"
            if candidate_for_real_tenant
            else (
                "pilot_healthy_via_probe"
                if probe_resolved_insufficient_evidence
                else "pilot_healthy"
            )
        )

    return MobileV2SurfaceEvaluation(
        surface=surface,
        pilot_outcome=pilot_outcome,
        evidence_level=evidence_level,
        evaluation_reason=evaluation_reason,
        candidate_for_real_tenant=candidate_for_real_tenant,
        requires_hold=requires_hold,
        requires_rollback=requires_rollback,
        window_elapsed=window_elapsed,
        requests_v2_observed=readiness.v2_served,
        requests_fallback_observed=readiness.legacy_fallbacks,
        fallback_rate=fallback_rate,
        fallback_reason_breakdown=readiness.legacy_fallback_reasons,
        organic_requests_v2=readiness.organic_v2_served,
        organic_requests_fallback=readiness.organic_legacy_fallbacks,
        probe_requests_v2=readiness.probe_v2_served,
        probe_requests_fallback=readiness.probe_legacy_fallbacks,
        probe_reason_breakdown=readiness.probe_legacy_fallback_reasons,
        probe_resolved_insufficient_evidence=probe_resolved_insufficient_evidence,
        thresholds=thresholds,
    )


def _evaluate_mobile_v2_pilot(
    *,
    tenant_key: str,
    feed: MobileV2SurfaceState,
    thread: MobileV2SurfaceState,
) -> MobileV2PilotEvaluation:
    thresholds = _pilot_evaluation_thresholds()
    surfaces = (feed, thread)
    fallback_reason_breakdown: dict[str, int] = {}
    probe_reason_breakdown: dict[str, int] = {}
    requests_v2_observed = 0
    requests_fallback_observed = 0
    organic_requests_v2 = 0
    organic_requests_fallback = 0
    probe_requests_v2 = 0
    probe_requests_fallback = 0
    observed_requests = 0
    any_window_elapsed = False
    all_required_windows_elapsed = True
    active_surfaces = 0

    for surface in surfaces:
        evaluation = surface.pilot_evaluation
        if evaluation is None:
            continue
        active_surfaces += 1
        requests_v2_observed += evaluation.requests_v2_observed
        requests_fallback_observed += evaluation.requests_fallback_observed
        organic_requests_v2 += evaluation.organic_requests_v2
        organic_requests_fallback += evaluation.organic_requests_fallback
        probe_requests_v2 += evaluation.probe_requests_v2
        probe_requests_fallback += evaluation.probe_requests_fallback
        observed_requests += (
            evaluation.requests_v2_observed + evaluation.requests_fallback_observed
        )
        any_window_elapsed = any_window_elapsed or evaluation.window_elapsed
        if surface.state == "promoted":
            all_required_windows_elapsed = (
                all_required_windows_elapsed and evaluation.window_elapsed
            )
        for reason, count in evaluation.fallback_reason_breakdown:
            fallback_reason_breakdown[reason] = (
                int(fallback_reason_breakdown.get(reason, 0)) + int(count)
            )
        for reason, count in evaluation.probe_reason_breakdown:
            probe_reason_breakdown[reason] = (
                int(probe_reason_breakdown.get(reason, 0)) + int(count)
            )

    if active_surfaces <= 0:
        all_required_windows_elapsed = False

    fallback_rate = (
        round(requests_fallback_observed / observed_requests, 4)
        if observed_requests > 0
        else 0.0
    )
    evidence_level = _pilot_evidence_level(
        observed_requests=observed_requests,
        thresholds=thresholds,
    )
    probe_resolved_insufficient_evidence = (
        observed_requests >= thresholds.min_requests
        and (organic_requests_v2 + organic_requests_fallback) < thresholds.min_requests
        and probe_requests_v2 > 0
    )

    if any(
        surface.pilot_evaluation and surface.pilot_evaluation.requires_rollback
        for surface in surfaces
    ):
        pilot_outcome = "rollback_recommended"
        evaluation_reason = "surface_requires_rollback"
        requires_rollback = True
        requires_hold = False
    elif any(
        surface.pilot_evaluation and surface.pilot_evaluation.requires_hold
        for surface in surfaces
    ):
        pilot_outcome = "hold_recommended"
        evaluation_reason = "surface_requires_hold"
        requires_rollback = False
        requires_hold = True
    elif observed_requests <= 0:
        pilot_outcome = "insufficient_evidence"
        evaluation_reason = "no_v2_traffic_observed"
        requires_rollback = False
        requires_hold = False
    elif any(
        surface.pilot_evaluation
        and surface.pilot_evaluation.pilot_outcome == "insufficient_evidence"
        for surface in surfaces
    ):
        pilot_outcome = "insufficient_evidence"
        evaluation_reason = "surface_missing_required_evidence"
        requires_rollback = False
        requires_hold = False
    elif any(
        surface.pilot_evaluation
        and surface.pilot_evaluation.pilot_outcome == "observing"
        for surface in surfaces
    ):
        pilot_outcome = "observing"
        evaluation_reason = "surface_still_under_observation"
        requires_rollback = False
        requires_hold = False
    elif any(
        surface.pilot_evaluation
        and surface.pilot_evaluation.pilot_outcome == "attention"
        for surface in surfaces
    ):
        pilot_outcome = "attention"
        evaluation_reason = "surface_requires_attention"
        requires_rollback = False
        requires_hold = False
    else:
        candidate_for_real_tenant = (
            tenant_key == _pilot_tenant_key()
            and all(surface.state == "promoted" for surface in surfaces)
            and all(
                surface.pilot_evaluation
                and surface.pilot_evaluation.pilot_outcome
                in {"healthy", "candidate_for_real_tenant"}
                for surface in surfaces
            )
            and (organic_requests_v2 + organic_requests_fallback) >= thresholds.min_requests
            and (
                all_required_windows_elapsed
                or thresholds.allow_candidate_without_window_elapsed
            )
        )
        pilot_outcome = (
            "candidate_for_real_tenant" if candidate_for_real_tenant else "healthy"
        )
        evaluation_reason = (
            "ready_for_real_tenant_candidate"
            if candidate_for_real_tenant
            else (
                "pilot_healthy_via_probe"
                if probe_resolved_insufficient_evidence
                else "pilot_healthy"
            )
        )
        requires_rollback = False
        requires_hold = False
        return MobileV2PilotEvaluation(
            pilot_outcome=pilot_outcome,
            evidence_level=evidence_level,
            evaluation_reason=evaluation_reason,
            candidate_for_real_tenant=candidate_for_real_tenant,
            requires_hold=requires_hold,
            requires_rollback=requires_rollback,
            window_elapsed=all_required_windows_elapsed,
            requests_v2_observed=requests_v2_observed,
            requests_fallback_observed=requests_fallback_observed,
            fallback_rate=fallback_rate,
            fallback_reason_breakdown=_reason_rows(fallback_reason_breakdown),
            organic_requests_v2=organic_requests_v2,
            organic_requests_fallback=organic_requests_fallback,
            probe_requests_v2=probe_requests_v2,
            probe_requests_fallback=probe_requests_fallback,
            probe_reason_breakdown=_reason_rows(probe_reason_breakdown),
            probe_resolved_insufficient_evidence=probe_resolved_insufficient_evidence,
            thresholds=thresholds,
        )

    return MobileV2PilotEvaluation(
        pilot_outcome=pilot_outcome,
        evidence_level=evidence_level,
        evaluation_reason=evaluation_reason,
        candidate_for_real_tenant=False,
        requires_hold=requires_hold,
        requires_rollback=requires_rollback,
        window_elapsed=all_required_windows_elapsed or any_window_elapsed,
        requests_v2_observed=requests_v2_observed,
        requests_fallback_observed=requests_fallback_observed,
        fallback_rate=fallback_rate,
        fallback_reason_breakdown=_reason_rows(fallback_reason_breakdown),
        organic_requests_v2=organic_requests_v2,
        organic_requests_fallback=organic_requests_fallback,
        probe_requests_v2=probe_requests_v2,
        probe_requests_fallback=probe_requests_fallback,
        probe_reason_breakdown=_reason_rows(probe_reason_breakdown),
        probe_resolved_insufficient_evidence=probe_resolved_insufficient_evidence,
        thresholds=thresholds,
    )


def _resolve_surface_state(
    *,
    tenant_key: str,
    surface: str,
    base_decision: MobileV2BaseRolloutDecision,
) -> MobileV2SurfaceState:
    if surface not in MOBILE_V2_SURFACES:
        raise ValueError(f"Unsupported mobile V2 surface: {surface}")

    surface_overrides = _parse_surface_state_overrides(
        env_str(V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES_FLAG, "")
    )
    configured_state = surface_overrides.get((tenant_key, surface), base_decision.state)
    reason = base_decision.reason
    source = base_decision.source
    if (tenant_key, surface) in surface_overrides:
        reason = configured_state
        source = "surface_state_override"

    readiness = evaluate_mobile_v2_promotion_readiness(tenant_key=tenant_key, surface=surface)
    state = configured_state
    if configured_state == "pilot_enabled" and readiness.candidate_for_promotion:
        state = "candidate_for_promotion"
        reason = "candidate_for_promotion"
        source = "promotion_readiness"

    endpoint_allowed = env_bool(_SURFACE_FLAG_BY_NAME[surface], True)
    if not endpoint_allowed and state in MOBILE_V2_READ_ENABLED_STATES:
        state = "legacy_only"
        reason = _SURFACE_DISABLED_REASON[surface]
        source = "route_flag"

    enabled = endpoint_allowed and state in MOBILE_V2_READ_ENABLED_STATES
    pilot_window = _build_pilot_window(
        tenant_key=tenant_key,
        configured_state=configured_state,
        state=state,
        readiness=readiness,
    )
    pilot_evaluation = _evaluate_mobile_v2_surface_pilot(
        tenant_key=tenant_key,
        surface=surface,
        state=state,
        readiness=readiness,
        pilot_window=pilot_window,
    )
    return MobileV2SurfaceState(
        surface=surface,
        configured_state=configured_state,
        state=state,
        enabled=enabled,
        reason=reason,
        source=source,
        endpoint_allowed=endpoint_allowed,
        promotion_readiness=readiness,
        pilot_window=pilot_window,
        pilot_evaluation=pilot_evaluation,
    )


def _safe_nivel_acesso(value: object) -> int:
    if value is None or isinstance(value, bool):
        return 0
    if not isinstance(value, (int, float, str, bytes, bytearray)):
        return 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def resolve_mobile_v2_rollout_state_for_user(usuario: Any) -> MobileV2RolloutState:
    tenant_key = str(getattr(usuario, "empresa_id", "") or "").strip()
    base_decision = _resolve_base_rollout_for_principal(
        tenant_key=tenant_key,
        nivel_acesso=_safe_nivel_acesso(getattr(usuario, "nivel_acesso", 0)),
    )
    feed = _resolve_surface_state(
        tenant_key=base_decision.tenant_key,
        surface="feed",
        base_decision=base_decision,
    )
    thread = _resolve_surface_state(
        tenant_key=base_decision.tenant_key,
        surface="thread",
        base_decision=base_decision,
    )
    pilot_evaluation = _evaluate_mobile_v2_pilot(
        tenant_key=base_decision.tenant_key,
        feed=feed,
        thread=thread,
    )
    return MobileV2RolloutState(
        rollout_state=base_decision.state,
        reason=base_decision.reason,
        source=base_decision.source,
        tenant_key=base_decision.tenant_key,
        cohort_key=base_decision.cohort_key,
        rollout_bucket=base_decision.rollout_bucket,
        tenant_allowed=base_decision.tenant_allowed,
        cohort_allowed=base_decision.cohort_allowed,
        feed=feed,
        thread=thread,
        pilot_evaluation=pilot_evaluation,
    )


def resolve_mobile_v2_rollout_state_for_tenant_key(tenant_key: str) -> MobileV2RolloutState:
    usuario = type(
        "MobileV2RolloutTenantUser",
        (),
        {
            "empresa_id": tenant_key,
            "nivel_acesso": NivelAcesso.INSPETOR.value,
        },
    )()
    return resolve_mobile_v2_rollout_state_for_user(usuario)


def resolve_mobile_v2_capabilities_for_user(usuario: Any) -> MobileV2Capabilities:
    return resolve_mobile_v2_rollout_state_for_user(usuario).to_capabilities()


def _configured_tenant_keys() -> list[str]:
    keys = set(_parse_allowlist(env_str(V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST_FLAG, "")))
    keys.update(
        _parse_state_overrides(env_str(V2_ANDROID_ROLLOUT_STATE_OVERRIDES_FLAG, "")).keys()
    )
    keys.update(
        tenant_key
        for tenant_key, _surface in _parse_surface_state_overrides(
            env_str(V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES_FLAG, "")
        ).keys()
    )
    pilot_tenant_key = _pilot_tenant_key()
    if pilot_tenant_key:
        keys.add(pilot_tenant_key)
    return sorted(key for key in keys if key)


def _build_first_promoted_tenant_summary() -> dict[str, Any] | None:
    pilot_tenant_key = _pilot_tenant_key()
    if not pilot_tenant_key:
        return None

    rollout_state = resolve_mobile_v2_rollout_state_for_tenant_key(pilot_tenant_key)
    candidate_by_key = {
        candidate.tenant_key: candidate
        for candidate in discover_mobile_v2_safe_pilot_candidates()
    }
    safe_candidate = candidate_by_key.get(pilot_tenant_key)
    surface_states = [rollout_state.feed, rollout_state.thread]
    promoted_surfaces = [
        surface.surface for surface in surface_states if surface.state == "promoted"
    ]
    window_surfaces = [surface for surface in surface_states if surface.pilot_window is not None]

    if any(surface.rollback_forced for surface in window_surfaces):
        pilot_health = "rollback_forced"
    elif any(surface.hold for surface in window_surfaces):
        pilot_health = "attention"
    elif any(surface.pilot_health_status == "attention" for surface in window_surfaces):
        pilot_health = "attention"
    else:
        pilot_health = "healthy" if promoted_surfaces else "not_promoted"

    promoted_since = next(
        (surface.promoted_since for surface in window_surfaces if surface.promoted_since),
        None,
    )
    rollout_window_started_at = next(
        (
            surface.rollout_window_started_at
            for surface in window_surfaces
            if surface.rollout_window_started_at
        ),
        None,
    )
    rollback_window_until = next(
        (
            surface.rollback_window_until
            for surface in window_surfaces
            if surface.rollback_window_until
        ),
        None,
    )
    promotion_source = next(
        (surface.promotion_source for surface in window_surfaces if surface.promotion_source),
        None,
    )
    promotion_note = next(
        (surface.promotion_note for surface in window_surfaces if surface.promotion_note),
        None,
    )
    rollback_window_active = any(
        surface.rollback_window_active for surface in window_surfaces
    )
    pilot_evaluation = rollout_state.pilot_evaluation
    total_observed_requests = (
        pilot_evaluation.requests_v2_observed + pilot_evaluation.requests_fallback_observed
        if pilot_evaluation is not None
        else sum(surface.promotion_readiness.observed_requests for surface in surface_states)
    )
    total_v2_served = (
        pilot_evaluation.requests_v2_observed
        if pilot_evaluation is not None
        else sum(surface.promotion_readiness.v2_served for surface in surface_states)
    )
    total_legacy_fallbacks = (
        pilot_evaluation.requests_fallback_observed
        if pilot_evaluation is not None
        else sum(surface.promotion_readiness.legacy_fallbacks for surface in surface_states)
    )

    payload: dict[str, Any] = {
        "tenant_key": pilot_tenant_key,
        "tenant_label": safe_candidate.tenant_label if safe_candidate else None,
        "safe_for_pilot": safe_candidate is not None,
        "safe_reason": safe_candidate.safety_reason if safe_candidate else "not_verified",
        "safe_source": safe_candidate.source if safe_candidate else "not_verified",
        "promoted_surfaces": promoted_surfaces,
        "surface_states": [surface.state for surface in surface_states],
        "promoted_since": promoted_since,
        "rollout_window_started_at": rollout_window_started_at,
        "rollback_window_until": rollback_window_until,
        "rollback_window_active": rollback_window_active,
        "promotion_source": promotion_source,
        "promotion_note": promotion_note,
        "pilot_health": pilot_health,
        "observed_requests": total_observed_requests,
        "v2_served": total_v2_served,
        "legacy_fallbacks": total_legacy_fallbacks,
    }
    if pilot_evaluation is not None:
        payload.update(pilot_evaluation.to_public_payload())
    else:
        payload.update(
            {
                "pilot_outcome": None,
                "evidence_level": None,
                "evaluation_reason": None,
                "candidate_for_real_tenant": False,
                "requires_hold": False,
                "requires_rollback": False,
                "window_elapsed": False,
                "requests_v2_observed": total_v2_served,
                "requests_fallback_observed": total_legacy_fallbacks,
                "fallback_rate": 0.0,
                "fallback_reason_breakdown": [],
                "organic_requests_v2": total_v2_served,
                "organic_requests_fallback": total_legacy_fallbacks,
                "probe_requests_v2": 0,
                "probe_requests_fallback": 0,
                "probe_reason_breakdown": [],
                "probe_resolved_insufficient_evidence": False,
                "evaluation_thresholds": {},
            }
        )
    runtime = get_mobile_v2_probe_runtime_state()
    if runtime.get("probe_tenant_key") == pilot_tenant_key:
        payload.update(
            {
                "probe_active": runtime.get("probe_active", False),
                "probe_last_run_at": runtime.get("probe_last_run_at"),
                "probe_surfaces_exercised": runtime.get("probe_surfaces_exercised", []),
                "probe_status": runtime.get("probe_status"),
                "probe_detail": runtime.get("probe_detail"),
            }
        )
    else:
        payload.update(
            {
                "probe_active": env_bool(V2_ANDROID_PILOT_PROBE_FLAG, False),
                "probe_last_run_at": None,
                "probe_surfaces_exercised": [],
                "probe_status": None,
                "probe_detail": None,
            }
        )
    return payload


def _default_organic_validation_surface_payload() -> dict[str, Any]:
    return {
        "organic_validation_active": False,
        "organic_validation_expired": False,
        "organic_validation_started_at": None,
        "organic_validation_ended_at": None,
        "organic_validation_expires_at": None,
        "organic_validation_window_elapsed": False,
        "organic_validation_outcome": None,
        "organic_validation_requests_v2": 0,
        "organic_validation_requests_fallback": 0,
        "organic_validation_fallback_rate": 0.0,
        "organic_validation_reason_breakdown": [],
        "organic_validation_coverage_met": False,
        "organic_validation_sufficient_evidence": False,
        "organic_validation_candidate_ready_for_real_tenant": False,
        "organic_validation_distinct_targets_observed": 0,
        "organic_validation_suggested_target_ids": [],
        "organic_validation_covered_target_ids": [],
        "organic_validation_missing_target_ids": [],
        "organic_validation_targets_available": False,
        "organic_validation_target_detail": None,
        "human_confirmed_count": 0,
        "human_confirmed_targets": [],
        "human_confirmed_last_seen_at": None,
        "human_confirmed_required_coverage_met": False,
        "legacy_rendered_under_validation_count": 0,
    }


def _default_operator_run_payload() -> dict[str, Any]:
    return {
        "operator_run_active": False,
        "operator_run_id": None,
        "operator_run_outcome": None,
        "operator_run_reason": None,
        "operator_run_started_at": None,
        "operator_run_ended_at": None,
        "operator_run_session_id": None,
        "operator_run_progress": None,
        "required_surfaces": [],
        "covered_surfaces": [],
        "missing_targets": {"feed": [], "thread": []},
        "operator_run_instructions": [],
        "human_coverage_from_operator_run": False,
        "validation_session_source": "none",
        "tenant_key": None,
        "tenant_label": None,
        "operator_run": None,
    }


def _resolve_mobile_v2_architecture_closure(
    *,
    rollout_state: str,
    feed: MobileV2SurfaceState,
    thread: MobileV2SurfaceState,
    pilot_evaluation: MobileV2PilotEvaluation | None,
    organic_validation_active: bool,
    operator_validation_run_active: bool,
    durable_acceptance_evidence: MobileV2DurableAcceptanceEvidence | None = None,
) -> MobileV2ArchitectureClosure:
    surfaces = (feed, thread)

    if any(surface.rollback_forced for surface in surfaces) or rollout_state == "rollback_forced":
        return MobileV2ArchitectureClosure(
            status="rollback_forced",
            reason="surface_rollback_forced",
            legacy_fallback_policy="required_for_continuity",
            transition_active=False,
        )

    if any(surface.hold for surface in surfaces) or rollout_state == "hold":
        return MobileV2ArchitectureClosure(
            status="hold",
            reason="surface_hold_active",
            legacy_fallback_policy="required_for_continuity",
            transition_active=False,
        )

    if organic_validation_active:
        return MobileV2ArchitectureClosure(
            status="observing",
            reason="organic_validation_active",
            legacy_fallback_policy="allowed_during_transition",
            transition_active=True,
        )

    if operator_validation_run_active:
        return MobileV2ArchitectureClosure(
            status="observing",
            reason="operator_validation_active",
            legacy_fallback_policy="allowed_during_transition",
            transition_active=True,
        )

    durable_ready = bool(
        durable_acceptance_evidence is not None
        and durable_acceptance_evidence.valid_for_closure
        and all(surface.state == "promoted" for surface in surfaces)
    )
    durable_reason = (
        durable_acceptance_evidence.reason
        if durable_acceptance_evidence is not None
        else "durable_acceptance_unavailable"
    )

    if pilot_evaluation is None:
        if durable_ready:
            return MobileV2ArchitectureClosure(
                status="closed_with_guardrails",
                reason=durable_reason,
                legacy_fallback_policy="guardrail_only",
                transition_active=False,
            )
        return MobileV2ArchitectureClosure(
            status="observing",
            reason="pilot_evaluation_unavailable",
            legacy_fallback_policy="allowed_during_transition",
            transition_active=True,
        )

    if pilot_evaluation.requires_rollback:
        return MobileV2ArchitectureClosure(
            status="rollback_forced",
            reason=pilot_evaluation.evaluation_reason,
            legacy_fallback_policy="required_for_continuity",
            transition_active=False,
        )

    if pilot_evaluation.requires_hold:
        return MobileV2ArchitectureClosure(
            status="hold",
            reason=pilot_evaluation.evaluation_reason,
            legacy_fallback_policy="required_for_continuity",
            transition_active=False,
        )

    if durable_ready and pilot_evaluation.pilot_outcome in {
        "observing",
        "insufficient_evidence",
        "healthy",
        "candidate_for_real_tenant",
    }:
        return MobileV2ArchitectureClosure(
            status="closed_with_guardrails",
            reason=durable_reason,
            legacy_fallback_policy="guardrail_only",
            transition_active=False,
        )

    if pilot_evaluation.pilot_outcome in {"observing", "insufficient_evidence", "attention"}:
        return MobileV2ArchitectureClosure(
            status="observing",
            reason=pilot_evaluation.evaluation_reason,
            legacy_fallback_policy="allowed_during_transition",
            transition_active=True,
        )

    if all(surface.state == "promoted" for surface in surfaces) and pilot_evaluation.pilot_outcome in {
        "healthy",
        "candidate_for_real_tenant",
    }:
        return MobileV2ArchitectureClosure(
            status="closed_with_guardrails",
            reason="all_required_surfaces_promoted_and_healthy",
            legacy_fallback_policy="guardrail_only",
            transition_active=False,
        )

    return MobileV2ArchitectureClosure(
        status="observing",
        reason="rollout_not_fully_promoted",
        legacy_fallback_policy="allowed_during_transition",
        transition_active=True,
    )


def _organic_validation_enrichment() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    from app.v2.mobile_organic_validation import (
        get_mobile_v2_organic_validation_default_payload,
        get_mobile_v2_organic_validation_summary,
    )

    organic_summary = get_mobile_v2_organic_validation_summary()
    organic_payload = organic_summary.to_public_payload()
    default_payload = get_mobile_v2_organic_validation_default_payload()
    session_payload = organic_payload.get("organic_validation_session") or {}
    session_tenant_key = str(session_payload.get("tenant_key", "") or "").strip()
    surface_rows = {
        str(item.get("surface", "") or "").strip(): dict(item)
        for item in organic_payload.get("organic_validation_surface_summaries", [])
        if str(item.get("surface", "") or "").strip()
    }
    return organic_payload, default_payload | {"session_tenant_key": session_tenant_key}, surface_rows


def _operator_run_enrichment() -> tuple[dict[str, Any], dict[str, Any], str]:
    from app.v2.mobile_operator_run import (
        get_mobile_v2_operator_validation_default_payload,
        get_mobile_v2_operator_validation_status,
    )

    operator_status = get_mobile_v2_operator_validation_status()
    operator_payload = operator_status.to_public_payload()
    default_payload = get_mobile_v2_operator_validation_default_payload()
    default_payload.pop("tenant_key", None)
    default_payload.pop("tenant_label", None)
    operator_tenant_key = str(operator_payload.get("tenant_key", "") or "").strip()
    return (
        operator_payload,
        default_payload | {"operator_tenant_key": operator_tenant_key},
        operator_tenant_key,
    )


def build_mobile_v2_rollout_governance_summary(
    *,
    observed_tenant_keys: list[str],
) -> dict[str, Any]:
    tenant_keys = sorted(
        {str(key).strip() for key in observed_tenant_keys + _configured_tenant_keys() if str(key).strip()}
    )
    tenant_rollout_states: list[dict[str, Any]] = []
    tenant_surface_states: list[dict[str, Any]] = []

    for tenant_key in tenant_keys:
        rollout_state = resolve_mobile_v2_rollout_state_for_tenant_key(tenant_key)
        tenant_rollout_states.append(rollout_state.to_summary_payload())
        tenant_surface_states.append(
            rollout_state.feed.to_summary_payload(
                tenant_key=tenant_key,
                rollout_state=rollout_state.rollout_state,
            )
        )
        tenant_surface_states.append(
            rollout_state.thread.to_summary_payload(
                tenant_key=tenant_key,
                rollout_state=rollout_state.rollout_state,
            )
        )

    tenant_surface_states.sort(
        key=lambda item: (
            str(item["tenant_key"]),
            str(item["surface"]),
        )
    )
    tenant_rollout_states.sort(key=lambda item: str(item["tenant_key"]))
    organic_payload, organic_default_payload, organic_surface_rows = (
        _organic_validation_enrichment()
    )
    organic_session_tenant_key = organic_default_payload.pop("session_tenant_key", "")
    operator_payload, operator_default_payload, operator_tenant_key = (
        _operator_run_enrichment()
    )
    operator_default_payload.pop("operator_tenant_key", "")
    pilot_tenant_key = _pilot_tenant_key()
    durable_acceptance_evidence = (
        load_mobile_v2_durable_acceptance_evidence()
        if pilot_tenant_key
        else None
    )
    for row in tenant_rollout_states:
        row.update(
            organic_payload
            if row["tenant_key"] == organic_session_tenant_key
            else organic_default_payload
        )
        row.update(
            operator_payload
            if row["tenant_key"] == operator_tenant_key
            else operator_default_payload
        )
        rollout_state = resolve_mobile_v2_rollout_state_for_tenant_key(str(row["tenant_key"]))
        row.update(
            _resolve_mobile_v2_architecture_closure(
                rollout_state=rollout_state.rollout_state,
                feed=rollout_state.feed,
                thread=rollout_state.thread,
                pilot_evaluation=rollout_state.pilot_evaluation,
                organic_validation_active=bool(
                    row.get("organic_validation_active", False)
                ),
                operator_validation_run_active=bool(
                    row.get("operator_run_active", False)
                ),
                durable_acceptance_evidence=(
                    durable_acceptance_evidence
                    if str(row.get("tenant_key") or "") == pilot_tenant_key
                    else None
                ),
            ).to_public_payload()
        )
    for row in tenant_surface_states:
        surface_payload = _default_organic_validation_surface_payload()
        if row["tenant_key"] == organic_session_tenant_key:
            surface_payload.update(
                {
                    "organic_validation_active": organic_payload.get(
                        "organic_validation_active", False
                    ),
                    "organic_validation_expired": organic_payload.get(
                        "organic_validation_expired", False
                    ),
                    "organic_validation_started_at": organic_payload.get(
                        "organic_validation_started_at"
                    ),
                    "organic_validation_ended_at": organic_payload.get(
                        "organic_validation_ended_at"
                    ),
                    "organic_validation_expires_at": organic_payload.get(
                        "organic_validation_expires_at"
                    ),
                    "organic_validation_window_elapsed": organic_payload.get(
                        "organic_validation_window_elapsed", False
                    ),
                }
            )
            surface_entry = organic_surface_rows.get(str(row["surface"]))
            if surface_entry is not None:
                surface_payload.update(
                    {
                        "organic_validation_outcome": surface_entry.get("outcome"),
                        "organic_validation_requests_v2": surface_entry.get(
                            "organic_requests_v2", 0
                        ),
                        "organic_validation_requests_fallback": surface_entry.get(
                            "organic_requests_fallback", 0
                        ),
                        "organic_validation_fallback_rate": surface_entry.get(
                            "organic_fallback_rate", 0.0
                        ),
                        "organic_validation_reason_breakdown": surface_entry.get(
                            "organic_fallback_reason_breakdown", []
                        ),
                        "organic_validation_coverage_met": surface_entry.get(
                            "coverage_met", False
                        ),
                        "organic_validation_sufficient_evidence": surface_entry.get(
                            "sufficient_evidence", False
                        ),
                        "organic_validation_candidate_ready_for_real_tenant": (
                            surface_entry.get("candidate_ready_for_real_tenant", False)
                        ),
                        "organic_validation_distinct_targets_observed": surface_entry.get(
                            "distinct_targets_observed",
                            0,
                        ),
                        "organic_validation_suggested_target_ids": surface_entry.get(
                            "suggested_target_ids",
                            [],
                        ),
                        "organic_validation_covered_target_ids": surface_entry.get(
                            "covered_target_ids",
                            [],
                        ),
                        "organic_validation_missing_target_ids": surface_entry.get(
                            "missing_target_ids",
                            [],
                        ),
                        "organic_validation_targets_available": surface_entry.get(
                            "targets_available",
                            False,
                        ),
                        "organic_validation_target_detail": surface_entry.get(
                            "detail",
                        ),
                        "human_confirmed_count": surface_entry.get(
                            "human_confirmed_count",
                            0,
                        ),
                        "human_confirmed_targets": surface_entry.get(
                            "human_confirmed_targets",
                            [],
                        ),
                        "human_confirmed_last_seen_at": surface_entry.get(
                            "human_confirmed_last_seen_at"
                        ),
                        "human_confirmed_required_coverage_met": surface_entry.get(
                            "human_confirmed_required_coverage_met",
                            False,
                        ),
                        "legacy_rendered_under_validation_count": surface_entry.get(
                            "legacy_rendered_under_validation_count",
                            0,
                        ),
                    }
                )
        row.update(surface_payload)
        if row["tenant_key"] == operator_tenant_key:
            operator_progress = dict(operator_payload.get("operator_run_progress") or {})
            row.update(
                {
                    "operator_run_active": operator_payload.get(
                        "operator_run_active",
                        False,
                    ),
                    "operator_run_id": operator_payload.get("operator_run_id"),
                    "operator_run_outcome": operator_payload.get(
                        "operator_run_outcome"
                    ),
                    "operator_run_reason": operator_payload.get(
                        "operator_run_reason"
                    ),
                    "operator_run_started_at": operator_payload.get(
                        "operator_run_started_at"
                    ),
                    "operator_run_ended_at": operator_payload.get(
                        "operator_run_ended_at"
                    ),
                    "operator_run_session_id": operator_payload.get(
                        "operator_run_session_id"
                    ),
                    "operator_run_surface_completed": (
                        row["surface"] in operator_progress.get("covered_surfaces", [])
                    ),
                    "operator_run_missing_targets": list(
                        dict(operator_payload.get("missing_targets") or {}).get(
                            row["surface"],
                            [],
                        )
                    ),
                    "human_coverage_from_operator_run": operator_payload.get(
                        "human_coverage_from_operator_run",
                        False,
                    ),
                    "validation_session_source": operator_payload.get(
                        "validation_session_source",
                        "none",
                    ),
                }
            )
        else:
            row.update(
                {
                    "operator_run_active": False,
                    "operator_run_id": None,
                    "operator_run_outcome": None,
                    "operator_run_reason": None,
                    "operator_run_started_at": None,
                    "operator_run_ended_at": None,
                    "operator_run_session_id": None,
                    "operator_run_surface_completed": False,
                    "operator_run_missing_targets": [],
                    "human_coverage_from_operator_run": False,
                    "validation_session_source": "none",
                }
            )
    runtime = get_mobile_v2_probe_runtime_state()
    first_promoted_tenant = _build_first_promoted_tenant_summary()
    if first_promoted_tenant is not None:
        first_promoted_tenant.update(
            organic_payload
            if first_promoted_tenant.get("tenant_key") == organic_session_tenant_key
            else organic_default_payload
        )
        first_promoted_tenant.update(
            operator_payload
            if first_promoted_tenant.get("tenant_key") == operator_tenant_key
            else operator_default_payload
        )
        first_promoted_rollout = resolve_mobile_v2_rollout_state_for_tenant_key(
            str(first_promoted_tenant.get("tenant_key") or "")
        )
        first_promoted_tenant.update(
            _resolve_mobile_v2_architecture_closure(
                rollout_state=first_promoted_rollout.rollout_state,
                feed=first_promoted_rollout.feed,
                thread=first_promoted_rollout.thread,
                pilot_evaluation=first_promoted_rollout.pilot_evaluation,
                organic_validation_active=bool(
                    first_promoted_tenant.get("organic_validation_active", False)
                ),
                operator_validation_run_active=bool(
                    first_promoted_tenant.get("operator_run_active", False)
                ),
                durable_acceptance_evidence=(
                    durable_acceptance_evidence
                    if str(first_promoted_tenant.get("tenant_key") or "")
                    == pilot_tenant_key
                    else None
                ),
            ).to_public_payload()
        )
    closure_summary = None
    if pilot_tenant_key:
        pilot_rollout = resolve_mobile_v2_rollout_state_for_tenant_key(pilot_tenant_key)
        pilot_row = next(
            (
                row
                for row in tenant_rollout_states
                if str(row.get("tenant_key") or "") == pilot_tenant_key
            ),
            None,
        )
        closure_summary = {
            "tenant_key": pilot_tenant_key,
            **_resolve_mobile_v2_architecture_closure(
                rollout_state=pilot_rollout.rollout_state,
                feed=pilot_rollout.feed,
                thread=pilot_rollout.thread,
                pilot_evaluation=pilot_rollout.pilot_evaluation,
                organic_validation_active=bool(
                    pilot_row and pilot_row.get("organic_validation_active", False)
                ),
                operator_validation_run_active=bool(
                    pilot_row and pilot_row.get("operator_run_active", False)
                ),
                durable_acceptance_evidence=durable_acceptance_evidence,
            ).to_public_payload(),
        }
        if durable_acceptance_evidence is not None:
            closure_summary["mobile_v2_durable_acceptance_evidence"] = (
                durable_acceptance_evidence.to_public_payload()
            )
    if first_promoted_tenant is not None and durable_acceptance_evidence is not None:
        first_promoted_tenant["mobile_v2_durable_acceptance_evidence"] = (
            durable_acceptance_evidence.to_public_payload()
        )
    return {
        "tenant_rollout_states": tenant_rollout_states,
        "tenant_surface_states": tenant_surface_states,
        "promotion_thresholds": _promotion_thresholds().to_public_payload(),
        "pilot_evaluation_thresholds": _pilot_evaluation_thresholds().to_public_payload(),
        "first_promoted_tenant": first_promoted_tenant,
        "mobile_v2_closure_summary": closure_summary,
        "mobile_v2_durable_acceptance_evidence": (
            durable_acceptance_evidence.to_public_payload()
            if durable_acceptance_evidence is not None
            else None
        ),
        "probe_active": env_bool(V2_ANDROID_PILOT_PROBE_FLAG, False),
        "probe_last_run_at": runtime.get("probe_last_run_at"),
        "probe_requests_v2": runtime.get("probe_requests_v2", 0),
        "probe_requests_fallback": runtime.get("probe_requests_fallback", 0),
        "probe_surfaces_exercised": runtime.get("probe_surfaces_exercised", []),
        "probe_status": runtime.get("probe_status"),
        "probe_detail": runtime.get("probe_detail"),
        **organic_payload,
        **operator_payload,
    }


def observe_mobile_v2_capabilities_request(
    request: Request,
    *,
    usuario: Any,
    capabilities: MobileV2Capabilities,
) -> None:
    resumo = capabilities.to_debug_summary()
    resumo.update(
        {
            "route": "/app/api/mobile/v2/capabilities",
            "usuario_id": int(getattr(usuario, "id", 0) or 0),
        }
    )
    request.state.v2_android_capabilities_summary = resumo
    record_mobile_v2_capabilities_check(
        tenant_key=capabilities.tenant_key,
        rollout_bucket=capabilities.rollout_bucket,
        capabilities_version=capabilities.capabilities_version,
        reason=capabilities.reason,
        source=capabilities.source,
        feed_enabled=capabilities.mobile_v2_feed_enabled,
        feed_reason=capabilities.feed_reason,
        thread_enabled=capabilities.mobile_v2_thread_enabled,
        thread_reason=capabilities.thread_reason,
    )
    logger.info(
        "Mobile V2 capabilities | usuario_id=%s | tenant=%s | rollout_state=%s | reads=%s | feed=%s(%s) | thread=%s(%s) | source=%s | bucket=%s | version=%s",
        getattr(usuario, "id", None),
        capabilities.tenant_key or "unknown",
        capabilities.rollout_state,
        capabilities.mobile_v2_reads_enabled,
        capabilities.mobile_v2_feed_enabled,
        capabilities.feed_rollout_state,
        capabilities.mobile_v2_thread_enabled,
        capabilities.thread_rollout_state,
        capabilities.source,
        capabilities.rollout_bucket,
        capabilities.capabilities_version,
    )


def _parse_rollout_bucket_header(value: object) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return max(0, min(99, int(raw)))
    except (TypeError, ValueError):
        return None


def extract_mobile_v2_request_metadata(request: Request) -> dict[str, Any]:
    attempted = str(request.headers.get(HEADER_V2_ATTEMPTED, "") or "").strip().lower() in _TRUE_VALUES
    capabilities_version = _normalize_token(
        request.headers.get(HEADER_V2_CAPABILITIES_VERSION),
        fallback="",
    )
    return {
        "attempted": attempted,
        "route": _normalize_token(request.headers.get(HEADER_V2_ROUTE), fallback="unknown"),
        "capabilities_version": capabilities_version or None,
        "client_rollout_bucket": _parse_rollout_bucket_header(
            request.headers.get(HEADER_V2_ROLLOUT_BUCKET)
        ),
        "probe": str(request.headers.get(HEADER_V2_PROBE, "") or "").strip().lower()
        in _TRUE_VALUES,
        "probe_source": _normalize_token(
            request.headers.get(HEADER_V2_PROBE_SOURCE),
            fallback="",
        )
        or None,
        "usage_mode": _normalize_token(
            request.headers.get(HEADER_V2_USAGE_MODE),
            fallback="",
        )
        or None,
        "validation_session_id": _normalize_token(
            request.headers.get(HEADER_V2_VALIDATION_SESSION),
            fallback="",
        )
        or None,
        "operator_run_id": _normalize_token(
            request.headers.get(HEADER_V2_OPERATOR_RUN),
            fallback="",
        )
        or None,
        "central_trace_id": _normalize_token(
            request.headers.get(HEADER_MOBILE_CENTRAL_TRACE),
            fallback="",
        )
        or None,
    }


def observe_mobile_v2_route_received(
    request: Request,
    *,
    usuario: Any,
    endpoint: str,
    route: str,
    delivery_path: str,
    target_ids: list[int] | tuple[int, ...] | None = None,
) -> dict[str, Any]:
    metadata = extract_mobile_v2_request_metadata(request)
    rollout_state = resolve_mobile_v2_rollout_state_for_user(usuario)
    capabilities = rollout_state.to_capabilities()
    from app.v2.mobile_organic_validation import (
        resolve_mobile_v2_organic_request_classification,
    )

    classification = resolve_mobile_v2_organic_request_classification(
        tenant_key=capabilities.tenant_key,
        endpoint=endpoint,
        usage_mode=metadata["usage_mode"],
        validation_session_id=metadata["validation_session_id"],
        is_probe=metadata["probe"],
        is_fallback=delivery_path == "legacy",
    )
    resumo = {
        "phase": "received_route",
        "endpoint": endpoint,
        "route": route,
        "delivery_path": delivery_path,
        "trace_id": metadata["central_trace_id"],
        "attempted": metadata["attempted"],
        "usage_mode": metadata["usage_mode"],
        "validation_session_id": metadata["validation_session_id"],
        "operator_run_id": metadata["operator_run_id"],
        "tenant_key": capabilities.tenant_key,
        "traffic_class": classification.traffic_class,
        "target_ids": [int(item) for item in target_ids or () if int(item) > 0],
        "correlation_id": getattr(request.state, "correlation_id", None),
        "client_route": metadata["route"],
    }
    request.state.v2_android_request_trace_received = resumo
    record_mobile_v2_request_trace(
        phase="received_route",
        endpoint=endpoint,
        route=route,
        delivery_path=delivery_path,
        trace_id=metadata["central_trace_id"],
        attempted=metadata["attempted"],
        validation_session_id=metadata["validation_session_id"],
        operator_run_id=metadata["operator_run_id"],
        tenant_key=capabilities.tenant_key,
        target_ids=target_ids,
        traffic_class=classification.traffic_class,
        usage_mode=metadata["usage_mode"],
        capabilities_version=capabilities.capabilities_version,
        rollout_bucket=capabilities.rollout_bucket,
        http_status=200,
        correlation_id=getattr(request.state, "correlation_id", None),
        client_route=metadata["route"],
    )
    return resumo


def extract_mobile_v2_fallback_observation(request: Request) -> dict[str, Any] | None:
    metadata = extract_mobile_v2_request_metadata(request)
    if not metadata["attempted"]:
        return None

    return {
        "route": metadata["route"],
        "reason": _normalize_token(
            request.headers.get(HEADER_V2_FALLBACK_REASON),
            fallback="unknown",
        ),
        "gate_source": _normalize_token(
            request.headers.get(HEADER_V2_GATE_SOURCE),
            fallback="unknown",
        ),
        "capabilities_version": metadata["capabilities_version"],
        "client_rollout_bucket": metadata["client_rollout_bucket"],
    }


def observe_mobile_v2_legacy_fallback(
    request: Request,
    *,
    usuario: Any,
    legacy_route: str,
    target_ids: list[int] | tuple[int, ...] | None = None,
) -> dict[str, Any] | None:
    metadata = extract_mobile_v2_request_metadata(request)
    observation = extract_mobile_v2_fallback_observation(request)
    if observation is None:
        return None

    capabilities = resolve_mobile_v2_capabilities_for_user(usuario)
    from app.v2.mobile_organic_validation import (
        resolve_mobile_v2_organic_request_classification,
    )

    classification = resolve_mobile_v2_organic_request_classification(
        tenant_key=capabilities.tenant_key,
        endpoint=observation["route"],
        usage_mode=metadata["usage_mode"],
        validation_session_id=metadata["validation_session_id"],
        is_probe=metadata["probe"],
        is_fallback=True,
    )
    resumo = {
        "legacy_route": legacy_route,
        "mobile_v2_attempted": True,
        "route": observation["route"],
        "reason": observation["reason"],
        "gate_source": observation["gate_source"],
        "probe": metadata["probe"],
        "probe_source": metadata["probe_source"],
        "usage_mode": metadata["usage_mode"],
        "validation_session_id": metadata["validation_session_id"],
        "operator_run_id": metadata["operator_run_id"],
        "traffic_class": classification.traffic_class,
        "usuario_id": int(getattr(usuario, "id", 0) or 0),
        "tenant_key": capabilities.tenant_key,
        "capabilities_version": capabilities.capabilities_version,
        "rollout_bucket": capabilities.rollout_bucket,
        "client_capabilities_version": observation["capabilities_version"],
        "client_rollout_bucket": observation["client_rollout_bucket"],
        "target_ids": [int(item) for item in target_ids or () if int(item) > 0],
    }
    request.state.v2_android_legacy_fallback_summary = resumo
    record_mobile_v2_legacy_fallback(
        tenant_key=capabilities.tenant_key,
        endpoint=observation["route"],
        reason=observation["reason"],
        source=observation["gate_source"],
        rollout_bucket=capabilities.rollout_bucket,
        capabilities_version=capabilities.capabilities_version,
        client_capabilities_version=observation["capabilities_version"],
        client_rollout_bucket=observation["client_rollout_bucket"],
        probe_label="pilot_probe" if metadata["probe"] else None,
        probe_source=metadata["probe_source"],
        traffic_class=classification.traffic_class,
        validation_session_id=classification.validation_session_id,
        target_ids=target_ids,
    )
    record_mobile_v2_request_trace(
        phase="counted",
        endpoint=observation["route"],
        route=legacy_route,
        delivery_path="legacy",
        trace_id=metadata["central_trace_id"],
        attempted=metadata["attempted"],
        validation_session_id=metadata["validation_session_id"],
        operator_run_id=metadata["operator_run_id"],
        tenant_key=capabilities.tenant_key,
        target_ids=target_ids,
        traffic_class=classification.traffic_class,
        usage_mode=metadata["usage_mode"],
        counted_kind="legacy_fallbacks",
        metadata_available=True,
        capabilities_version=capabilities.capabilities_version,
        rollout_bucket=capabilities.rollout_bucket,
        http_status=200,
        correlation_id=getattr(request.state, "correlation_id", None),
        client_route=observation["route"],
    )
    logger.info(
        "Mobile V2 fallback -> legado | usuario_id=%s | tenant=%s | legacy_route=%s | route=%s | reason=%s | gate_source=%s | bucket=%s | version=%s",
        getattr(usuario, "id", None),
        capabilities.tenant_key or "unknown",
        legacy_route,
        observation["route"],
        observation["reason"],
        observation["gate_source"],
        capabilities.rollout_bucket,
        observation["capabilities_version"] or capabilities.capabilities_version,
    )
    return resumo


def observe_mobile_v2_public_contract_read(
    request: Request,
    *,
    usuario: Any,
    endpoint: str,
    route: str,
    target_ids: list[int] | tuple[int, ...] | None = None,
) -> dict[str, Any]:
    rollout_state = resolve_mobile_v2_rollout_state_for_user(usuario)
    capabilities = rollout_state.to_capabilities()
    metadata = extract_mobile_v2_request_metadata(request)
    from app.v2.mobile_organic_validation import (
        resolve_mobile_v2_organic_request_classification,
    )

    classification = resolve_mobile_v2_organic_request_classification(
        tenant_key=capabilities.tenant_key,
        endpoint=endpoint,
        usage_mode=metadata["usage_mode"],
        validation_session_id=metadata["validation_session_id"],
        is_probe=metadata["probe"],
        is_fallback=False,
    )
    surface_state = rollout_state.feed if endpoint == "feed" else rollout_state.thread
    resumo = {
        "route": route,
        "endpoint": endpoint,
        "usuario_id": int(getattr(usuario, "id", 0) or 0),
        "tenant_key": capabilities.tenant_key,
        "rollout_reason": capabilities.reason,
        "rollout_source": capabilities.source,
        "surface_state": surface_state.state,
        "surface_source": surface_state.source,
        "rollback_window_active": surface_state.rollback_window_active,
        "probe": metadata["probe"],
        "probe_source": metadata["probe_source"],
        "usage_mode": metadata["usage_mode"],
        "validation_session_id": metadata["validation_session_id"],
        "operator_run_id": metadata["operator_run_id"],
        "traffic_class": classification.traffic_class,
        "rollout_bucket": capabilities.rollout_bucket,
        "capabilities_version": capabilities.capabilities_version,
        "client_capabilities_version": metadata["capabilities_version"],
        "client_rollout_bucket": metadata["client_rollout_bucket"],
        "target_ids": [int(item) for item in target_ids or () if int(item) > 0],
    }
    request.state.v2_android_public_contract_pilot_summary = resumo
    record_mobile_v2_public_read(
        tenant_key=capabilities.tenant_key,
        endpoint=endpoint,
        reason=surface_state.state,
        source=surface_state.source,
        rollout_bucket=capabilities.rollout_bucket,
        capabilities_version=capabilities.capabilities_version,
        client_capabilities_version=metadata["capabilities_version"],
        client_rollout_bucket=metadata["client_rollout_bucket"],
        probe_label="pilot_probe" if metadata["probe"] else None,
        probe_source=metadata["probe_source"],
        traffic_class=classification.traffic_class,
        validation_session_id=classification.validation_session_id,
        target_ids=target_ids,
    )
    record_mobile_v2_request_trace(
        phase="counted",
        endpoint=endpoint,
        route=route,
        delivery_path="v2",
        trace_id=metadata["central_trace_id"],
        attempted=metadata["attempted"],
        validation_session_id=metadata["validation_session_id"],
        operator_run_id=metadata["operator_run_id"],
        tenant_key=capabilities.tenant_key,
        target_ids=target_ids,
        traffic_class=classification.traffic_class,
        usage_mode=metadata["usage_mode"],
        counted_kind="v2_served",
        metadata_available=True,
        capabilities_version=capabilities.capabilities_version,
        rollout_bucket=capabilities.rollout_bucket,
        http_status=200,
        correlation_id=getattr(request.state, "correlation_id", None),
        client_route=metadata["route"],
    )
    logger.info(
        "Mobile V2 public read | route=%s | endpoint=%s | usuario_id=%s | tenant=%s | reason=%s | source=%s | bucket=%s | version=%s",
        route,
        endpoint,
        getattr(usuario, "id", None),
        capabilities.tenant_key or "unknown",
        surface_state.state,
        surface_state.source,
        capabilities.rollout_bucket,
        metadata["capabilities_version"] or capabilities.capabilities_version,
    )
    return resumo
