"""Tipos e serializers do contrato publico de rollout mobile V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MobileV2BaseRolloutDecision:
    state: str
    enabled: bool
    reason: str
    source: str
    tenant_key: str
    cohort_key: str
    rollout_bucket: int | None
    tenant_allowed: bool
    cohort_allowed: bool


@dataclass(frozen=True, slots=True)
class MobileV2PromotionThresholds:
    min_requests: int
    max_fallback_rate_percent: int
    max_service_errors: int
    max_parse_visibility_errors: int

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "min_requests": self.min_requests,
            "max_fallback_rate_percent": self.max_fallback_rate_percent,
            "max_service_errors": self.max_service_errors,
            "max_parse_visibility_errors": self.max_parse_visibility_errors,
        }


@dataclass(frozen=True, slots=True)
class MobileV2PilotEvaluationThresholds:
    min_requests: int
    max_fallback_rate_percent: int
    max_visibility_violations: int
    max_parse_errors: int
    max_http_failures: int
    require_full_window: bool
    allow_candidate_without_window_elapsed: bool

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "min_requests": self.min_requests,
            "max_fallback_rate_percent": self.max_fallback_rate_percent,
            "max_visibility_violations": self.max_visibility_violations,
            "max_parse_errors": self.max_parse_errors,
            "max_http_failures": self.max_http_failures,
            "require_full_window": self.require_full_window,
            "allow_candidate_without_window_elapsed": (
                self.allow_candidate_without_window_elapsed
            ),
        }


@dataclass(frozen=True, slots=True)
class MobileV2PromotionReadiness:
    surface: str
    candidate_for_promotion: bool
    observed_requests: int
    v2_served: int
    legacy_fallbacks: int
    rollout_denied: int
    parse_errors: int
    visibility_errors: int
    service_errors: int
    fallback_rate: float
    reasons: tuple[str, ...]
    legacy_fallback_reasons: tuple[tuple[str, int], ...]
    rollout_denied_reasons: tuple[tuple[str, int], ...]
    thresholds: MobileV2PromotionThresholds
    organic_v2_served: int = 0
    organic_legacy_fallbacks: int = 0
    probe_v2_served: int = 0
    probe_legacy_fallbacks: int = 0
    probe_legacy_fallback_reasons: tuple[tuple[str, int], ...] = ()

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "candidate_for_promotion": self.candidate_for_promotion,
            "observed_requests": self.observed_requests,
            "v2_served": self.v2_served,
            "legacy_fallbacks": self.legacy_fallbacks,
            "rollout_denied": self.rollout_denied,
            "parse_errors": self.parse_errors,
            "visibility_errors": self.visibility_errors,
            "service_errors": self.service_errors,
            "fallback_rate": self.fallback_rate,
            "reasons": list(self.reasons),
            "legacy_fallback_reasons": [
                {"reason": reason, "count": count}
                for reason, count in self.legacy_fallback_reasons
            ],
            "rollout_denied_reasons": [
                {"reason": reason, "count": count}
                for reason, count in self.rollout_denied_reasons
            ],
            "organic_v2_served": self.organic_v2_served,
            "organic_legacy_fallbacks": self.organic_legacy_fallbacks,
            "probe_v2_served": self.probe_v2_served,
            "probe_legacy_fallbacks": self.probe_legacy_fallbacks,
            "probe_legacy_fallback_reasons": [
                {"reason": reason, "count": count}
                for reason, count in self.probe_legacy_fallback_reasons
            ],
            "thresholds": self.thresholds.to_public_payload(),
        }


@dataclass(frozen=True, slots=True)
class MobileV2PilotSurfaceWindow:
    promoted_since: str | None
    rollout_window_started_at: str | None
    rollback_window_until: str | None
    rollback_window_active: bool
    window_elapsed: bool
    source: str | None
    note: str | None
    health_status: str
    health_reason: str

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "promoted_since": self.promoted_since,
            "rollout_window_started_at": self.rollout_window_started_at,
            "rollback_window_until": self.rollback_window_until,
            "rollback_window_active": self.rollback_window_active,
            "window_elapsed": self.window_elapsed,
            "promotion_source": self.source,
            "promotion_note": self.note,
            "health_status": self.health_status,
            "health_reason": self.health_reason,
        }


@dataclass(frozen=True, slots=True)
class MobileV2PilotTenantCandidate:
    tenant_key: str
    tenant_label: str
    safety_reason: str
    source: str
    inspector_users: int

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "tenant_key": self.tenant_key,
            "tenant_label": self.tenant_label,
            "safety_reason": self.safety_reason,
            "source": self.source,
            "inspector_users": self.inspector_users,
        }


@dataclass(frozen=True, slots=True)
class MobileV2SurfaceEvaluation:
    surface: str
    pilot_outcome: str
    evidence_level: str
    evaluation_reason: str
    candidate_for_real_tenant: bool
    requires_hold: bool
    requires_rollback: bool
    window_elapsed: bool
    requests_v2_observed: int
    requests_fallback_observed: int
    fallback_rate: float
    fallback_reason_breakdown: tuple[tuple[str, int], ...]
    organic_requests_v2: int
    organic_requests_fallback: int
    probe_requests_v2: int
    probe_requests_fallback: int
    probe_reason_breakdown: tuple[tuple[str, int], ...]
    probe_resolved_insufficient_evidence: bool
    thresholds: MobileV2PilotEvaluationThresholds

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "pilot_outcome": self.pilot_outcome,
            "evidence_level": self.evidence_level,
            "evaluation_reason": self.evaluation_reason,
            "candidate_for_real_tenant": self.candidate_for_real_tenant,
            "requires_hold": self.requires_hold,
            "requires_rollback": self.requires_rollback,
            "window_elapsed": self.window_elapsed,
            "requests_v2_observed": self.requests_v2_observed,
            "requests_fallback_observed": self.requests_fallback_observed,
            "fallback_rate": self.fallback_rate,
            "fallback_reason_breakdown": [
                {"reason": reason, "count": count}
                for reason, count in self.fallback_reason_breakdown
            ],
            "organic_requests_v2": self.organic_requests_v2,
            "organic_requests_fallback": self.organic_requests_fallback,
            "probe_requests_v2": self.probe_requests_v2,
            "probe_requests_fallback": self.probe_requests_fallback,
            "probe_reason_breakdown": [
                {"reason": reason, "count": count}
                for reason, count in self.probe_reason_breakdown
            ],
            "probe_resolved_insufficient_evidence": (
                self.probe_resolved_insufficient_evidence
            ),
            "evaluation_thresholds": self.thresholds.to_public_payload(),
        }


@dataclass(frozen=True, slots=True)
class MobileV2PilotEvaluation:
    pilot_outcome: str
    evidence_level: str
    evaluation_reason: str
    candidate_for_real_tenant: bool
    requires_hold: bool
    requires_rollback: bool
    window_elapsed: bool
    requests_v2_observed: int
    requests_fallback_observed: int
    fallback_rate: float
    fallback_reason_breakdown: tuple[tuple[str, int], ...]
    organic_requests_v2: int
    organic_requests_fallback: int
    probe_requests_v2: int
    probe_requests_fallback: int
    probe_reason_breakdown: tuple[tuple[str, int], ...]
    probe_resolved_insufficient_evidence: bool
    thresholds: MobileV2PilotEvaluationThresholds

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "pilot_outcome": self.pilot_outcome,
            "evidence_level": self.evidence_level,
            "evaluation_reason": self.evaluation_reason,
            "candidate_for_real_tenant": self.candidate_for_real_tenant,
            "requires_hold": self.requires_hold,
            "requires_rollback": self.requires_rollback,
            "window_elapsed": self.window_elapsed,
            "requests_v2_observed": self.requests_v2_observed,
            "requests_fallback_observed": self.requests_fallback_observed,
            "fallback_rate": self.fallback_rate,
            "fallback_reason_breakdown": [
                {"reason": reason, "count": count}
                for reason, count in self.fallback_reason_breakdown
            ],
            "organic_requests_v2": self.organic_requests_v2,
            "organic_requests_fallback": self.organic_requests_fallback,
            "probe_requests_v2": self.probe_requests_v2,
            "probe_requests_fallback": self.probe_requests_fallback,
            "probe_reason_breakdown": [
                {"reason": reason, "count": count}
                for reason, count in self.probe_reason_breakdown
            ],
            "probe_resolved_insufficient_evidence": (
                self.probe_resolved_insufficient_evidence
            ),
            "evaluation_thresholds": self.thresholds.to_public_payload(),
        }


@dataclass(frozen=True, slots=True)
class MobileV2ArchitectureClosure:
    status: str
    reason: str
    legacy_fallback_policy: str
    transition_active: bool

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "mobile_v2_architecture_status": self.status,
            "mobile_v2_architecture_reason": self.reason,
            "mobile_v2_legacy_fallback_policy": self.legacy_fallback_policy,
            "mobile_v2_transition_active": self.transition_active,
        }


@dataclass(frozen=True, slots=True)
class MobileV2SurfaceState:
    surface: str
    configured_state: str
    state: str
    enabled: bool
    reason: str
    source: str
    endpoint_allowed: bool
    promotion_readiness: MobileV2PromotionReadiness
    pilot_window: MobileV2PilotSurfaceWindow | None = None
    pilot_evaluation: MobileV2SurfaceEvaluation | None = None

    @property
    def promoted(self) -> bool:
        return self.state == "promoted"

    @property
    def hold(self) -> bool:
        return self.state == "hold"

    @property
    def rollback_forced(self) -> bool:
        return self.state == "rollback_forced"

    @property
    def rollback_window_active(self) -> bool:
        return bool(self.pilot_window and self.pilot_window.rollback_window_active)

    @property
    def promoted_since(self) -> str | None:
        return self.pilot_window.promoted_since if self.pilot_window else None

    @property
    def rollout_window_started_at(self) -> str | None:
        return self.pilot_window.rollout_window_started_at if self.pilot_window else None

    @property
    def rollback_window_until(self) -> str | None:
        return self.pilot_window.rollback_window_until if self.pilot_window else None

    @property
    def promotion_source(self) -> str | None:
        return self.pilot_window.source if self.pilot_window else None

    @property
    def promotion_note(self) -> str | None:
        return self.pilot_window.note if self.pilot_window else None

    @property
    def pilot_health_status(self) -> str:
        return self.pilot_window.health_status if self.pilot_window else "not_applicable"

    @property
    def pilot_health_reason(self) -> str:
        return self.pilot_window.health_reason if self.pilot_window else "not_promoted"

    def to_summary_payload(self, *, tenant_key: str, rollout_state: str) -> dict[str, Any]:
        payload = {
            "tenant_key": tenant_key,
            "surface": self.surface,
            "rollout_state": rollout_state,
            "configured_state": self.configured_state,
            "surface_state": self.state,
            "enabled": self.enabled,
            "reason": self.reason,
            "source": self.source,
            "endpoint_allowed": self.endpoint_allowed,
            "candidate_for_promotion": self.promotion_readiness.candidate_for_promotion,
            "promoted": self.promoted,
            "hold": self.hold,
            "rollback_forced": self.rollback_forced,
            "promotion_readiness": self.promotion_readiness.to_public_payload(),
        }
        if self.pilot_window is not None:
            payload.update(self.pilot_window.to_public_payload())
        else:
            payload.update(
                {
                    "promoted_since": None,
                    "rollout_window_started_at": None,
                    "rollback_window_until": None,
                    "rollback_window_active": False,
                    "window_elapsed": False,
                    "promotion_source": None,
                    "promotion_note": None,
                    "health_status": "not_applicable",
                    "health_reason": "not_promoted",
                }
            )
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


__all__ = [
    "MobileV2ArchitectureClosure",
    "MobileV2BaseRolloutDecision",
    "MobileV2PilotEvaluation",
    "MobileV2PilotEvaluationThresholds",
    "MobileV2PilotSurfaceWindow",
    "MobileV2PilotTenantCandidate",
    "MobileV2PromotionReadiness",
    "MobileV2PromotionThresholds",
    "MobileV2SurfaceEvaluation",
    "MobileV2SurfaceState",
]
