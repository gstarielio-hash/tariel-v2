"""Sessao formal de validacao organica do piloto mobile V2."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select

import app.shared.database as banco_dados
from app.core.settings import env_bool, env_int, env_str
from app.shared.database import Empresa, Laudo, MensagemLaudo, NivelAcesso, Usuario
from app.v2.mobile_rollout_metrics import get_mobile_v2_surface_metrics_snapshot

V2_ANDROID_PILOT_TENANT_KEY_FLAG = "TARIEL_V2_ANDROID_PILOT_TENANT_KEY"
V2_ANDROID_ORGANIC_VALIDATION_WINDOW_MINUTES_FLAG = (
    "TARIEL_V2_ANDROID_ORGANIC_VALIDATION_WINDOW_MINUTES"
)
V2_ANDROID_ORGANIC_VALIDATION_MIN_REQUESTS_PER_SURFACE_FLAG = (
    "TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MIN_REQUESTS_PER_SURFACE"
)
V2_ANDROID_ORGANIC_VALIDATION_MAX_FALLBACK_RATE_PERCENT_FLAG = (
    "TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_FALLBACK_RATE_PERCENT"
)
V2_ANDROID_ORGANIC_VALIDATION_MAX_VISIBILITY_VIOLATIONS_FLAG = (
    "TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_VISIBILITY_VIOLATIONS"
)
V2_ANDROID_ORGANIC_VALIDATION_MAX_PARSE_ERRORS_FLAG = (
    "TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_PARSE_ERRORS"
)
V2_ANDROID_ORGANIC_VALIDATION_MAX_HTTP_FAILURES_FLAG = (
    "TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_HTTP_FAILURES"
)
V2_ANDROID_ORGANIC_VALIDATION_REQUIRE_FULL_WINDOW_FLAG = (
    "TARIEL_V2_ANDROID_ORGANIC_VALIDATION_REQUIRE_FULL_WINDOW"
)
V2_ANDROID_ORGANIC_VALIDATION_TARGET_LIMIT_FLAG = (
    "TARIEL_V2_ANDROID_ORGANIC_VALIDATION_TARGET_LIMIT"
)

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_SURFACES = ("feed", "thread")
_SAFE_INTERNAL_EMAIL_SUFFIXES = ("@tariel.ia",)
_HTTP_FAILURE_REASONS = (
    "http_404",
    "http_error",
    "adapter_error",
    "capabilities_fetch_error",
    "unknown",
)
_VALIDATION_USAGE_MODE = "organic_validation"
_HUMAN_CHECKPOINT_KINDS = frozenset({"rendered", "opened", "viewed"})
_HUMAN_DELIVERY_MODES = frozenset({"v2", "legacy_fallback"})
_HUMAN_CONFIRMED_DELIVERY_MODE = "v2"
_HUMAN_SOURCE_CHANNEL = "android_app"
_HUMAN_ACK_EVENT_LIMIT = 80

_lock = Lock()
_session_state: "MobileV2OrganicValidationSession | None" = None
_human_confirmation_state: dict[str, dict[str, "MobileOrganicHumanCheckpoint"]] = {}
_human_ack_recent_events: deque[dict[str, Any]] = deque(maxlen=_HUMAN_ACK_EVENT_LIMIT)


@dataclass(frozen=True, slots=True)
class MobileV2OrganicValidationThresholds:
    min_requests_per_surface: int
    max_fallback_rate_percent: int
    max_visibility_violations: int
    max_parse_errors: int
    max_http_failures: int
    window_minutes: int
    require_full_window: bool
    target_limit: int

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "min_requests_per_surface": self.min_requests_per_surface,
            "max_fallback_rate_percent": self.max_fallback_rate_percent,
            "max_visibility_violations": self.max_visibility_violations,
            "max_parse_errors": self.max_parse_errors,
            "max_http_failures": self.max_http_failures,
            "window_minutes": self.window_minutes,
            "require_full_window": self.require_full_window,
            "target_limit": self.target_limit,
        }


@dataclass(frozen=True, slots=True)
class MobileV2OrganicValidationTargetSummary:
    surface: str
    suggested_target_ids: tuple[int, ...]
    covered_target_ids: tuple[int, ...]
    missing_target_ids: tuple[int, ...]
    distinct_targets_observed: int
    coverage_met: bool
    targets_available: bool
    detail: str

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "suggested_target_ids": list(self.suggested_target_ids),
            "covered_target_ids": list(self.covered_target_ids),
            "missing_target_ids": list(self.missing_target_ids),
            "distinct_targets_observed": self.distinct_targets_observed,
            "coverage_met": self.coverage_met,
            "targets_available": self.targets_available,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class MobileV2OrganicValidationBaseline:
    surface: str
    validation_v2_served: int
    validation_legacy_fallbacks: int
    validation_fallback_reasons: tuple[tuple[str, int], ...]
    validation_target_counts: tuple[tuple[str, int], ...]
    probe_v2_served: int
    probe_legacy_fallbacks: int

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "validation_v2_served": self.validation_v2_served,
            "validation_legacy_fallbacks": self.validation_legacy_fallbacks,
            "validation_fallback_reasons": [
                {"reason": reason, "count": count}
                for reason, count in self.validation_fallback_reasons
            ],
            "validation_target_counts": [
                {"target_id": int(target_id), "count": count}
                for target_id, count in self.validation_target_counts
            ],
            "probe_v2_served": self.probe_v2_served,
            "probe_legacy_fallbacks": self.probe_legacy_fallbacks,
        }


@dataclass(frozen=True, slots=True)
class MobileV2OrganicValidationSession:
    tenant_key: str
    tenant_label: str | None
    session_id: str
    surfaces: tuple[str, ...]
    started_at: str
    expires_at: str
    active: bool
    ended_at: str | None
    trigger_source: str
    stop_source: str | None
    baselines: tuple[MobileV2OrganicValidationBaseline, ...]

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "tenant_key": self.tenant_key,
            "tenant_label": self.tenant_label,
            "session_id": self.session_id,
            "surfaces": list(self.surfaces),
            "started_at": self.started_at,
            "expires_at": self.expires_at,
            "active": self.active,
            "ended_at": self.ended_at,
            "trigger_source": self.trigger_source,
            "stop_source": self.stop_source,
            "baselines": [item.to_public_payload() for item in self.baselines],
        }


@dataclass(frozen=True, slots=True)
class MobileOrganicHumanCheckpoint:
    tenant_key: str
    session_id: str
    surface: str
    target_id: int
    checkpoint_kind: str
    confirmed_at: str
    source_channel: str
    delivery_mode: str
    operator_run_id: str | None
    capabilities_version: str | None
    rollout_bucket: int | None

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "target_id": self.target_id,
            "checkpoint_kind": self.checkpoint_kind,
            "confirmed_at": self.confirmed_at,
            "source_channel": self.source_channel,
            "delivery_mode": self.delivery_mode,
            "operator_run_id": self.operator_run_id,
        }


@dataclass(frozen=True, slots=True)
class MobileOrganicHumanSurfaceSummary:
    surface: str
    human_confirmed_count: int
    human_confirmed_targets: tuple[int, ...]
    human_confirmed_last_seen_at: str | None
    human_confirmed_required_coverage_met: bool
    legacy_rendered_under_validation_count: int

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "human_confirmed_count": self.human_confirmed_count,
            "human_confirmed_targets": list(self.human_confirmed_targets),
            "human_confirmed_last_seen_at": self.human_confirmed_last_seen_at,
            "human_confirmed_required_coverage_met": (
                self.human_confirmed_required_coverage_met
            ),
            "legacy_rendered_under_validation_count": (
                self.legacy_rendered_under_validation_count
            ),
        }


@dataclass(frozen=True, slots=True)
class MobileV2OrganicSurfaceValidationSummary:
    surface: str
    outcome: str
    organic_requests_v2: int
    organic_requests_fallback: int
    organic_fallback_rate: float
    organic_fallback_reason_breakdown: tuple[tuple[str, int], ...]
    coverage_met: bool
    sufficient_evidence: bool
    candidate_ready_for_real_tenant: bool
    target_summary: MobileV2OrganicValidationTargetSummary
    human_surface_summary: MobileOrganicHumanSurfaceSummary

    def to_public_payload(self) -> dict[str, Any]:
        payload = self.target_summary.to_public_payload()
        payload.update(
            {
                "surface": self.surface,
                "outcome": self.outcome,
                "organic_requests_v2": self.organic_requests_v2,
                "organic_requests_fallback": self.organic_requests_fallback,
                "organic_fallback_rate": self.organic_fallback_rate,
                "organic_fallback_reason_breakdown": [
                    {"reason": reason, "count": count}
                    for reason, count in self.organic_fallback_reason_breakdown
                ],
                "coverage_met": self.coverage_met,
                "sufficient_evidence": self.sufficient_evidence,
                "candidate_ready_for_real_tenant": self.candidate_ready_for_real_tenant,
                **self.human_surface_summary.to_public_payload(),
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class MobileV2OrganicValidationSummary:
    session: MobileV2OrganicValidationSession | None
    active: bool
    expired: bool
    started_at: str | None
    ended_at: str | None
    expires_at: str | None
    window_elapsed: bool
    outcome: str | None
    candidate_ready_for_real_tenant: bool
    organic_requests_v2: int
    organic_requests_fallback: int
    organic_fallback_rate: float
    organic_validation_reason_breakdown: tuple[tuple[str, int], ...]
    surface_summaries: tuple[MobileV2OrganicSurfaceValidationSummary, ...]
    surface_coverage_summary: dict[str, Any]
    distinct_targets: dict[str, Any]
    missing_targets: dict[str, list[int]]
    human_confirmed_count: int
    human_confirmed_targets: dict[str, Any]
    human_confirmed_last_seen_at: str | None
    human_confirmed_required_coverage_met: bool
    human_confirmed_surface_summaries: tuple[MobileOrganicHumanSurfaceSummary, ...]
    human_ack_recent_events: tuple[dict[str, Any], ...]
    probe_vs_organic_evidence: dict[str, Any]
    thresholds: MobileV2OrganicValidationThresholds

    def to_public_payload(self) -> dict[str, Any]:
        surface_payloads = [item.to_public_payload() for item in self.surface_summaries]
        human_surface_payloads = [
            item.to_public_payload() for item in self.human_confirmed_surface_summaries
        ]
        return {
            "organic_validation_active": self.active,
            "organic_validation_expired": self.expired,
            "organic_validation_started_at": self.started_at,
            "organic_validation_ended_at": self.ended_at,
            "organic_validation_expires_at": self.expires_at,
            "organic_validation_window_elapsed": self.window_elapsed,
            "organic_validation_outcome": self.outcome,
            "candidate_ready_for_real_tenant": self.candidate_ready_for_real_tenant,
            "organic_validation_requests_v2": self.organic_requests_v2,
            "organic_validation_requests_fallback": self.organic_requests_fallback,
            "organic_validation_fallback_rate": self.organic_fallback_rate,
            "organic_validation_reason_breakdown": [
                {"reason": reason, "count": count}
                for reason, count in self.organic_validation_reason_breakdown
            ],
            "organic_validation_surface_summaries": surface_payloads,
            "organic_validation_surface_coverage": surface_payloads,
            "surface_coverage_summary": dict(self.surface_coverage_summary),
            "organic_validation_distinct_targets": dict(self.distinct_targets),
            "organic_validation_missing_targets": {
                surface: list(target_ids)
                for surface, target_ids in self.missing_targets.items()
            },
            "human_confirmed_count": self.human_confirmed_count,
            "human_confirmed_targets": {
                surface: list(target_ids)
                for surface, target_ids in self.human_confirmed_targets.items()
            },
            "human_confirmed_last_seen_at": self.human_confirmed_last_seen_at,
            "human_confirmed_required_coverage_met": (
                self.human_confirmed_required_coverage_met
            ),
            "human_confirmed_surface_summaries": human_surface_payloads,
            "human_ack_recent_events": [
                dict(item) for item in self.human_ack_recent_events
            ],
            "probe_vs_organic_evidence": dict(self.probe_vs_organic_evidence),
            "organic_validation_thresholds": self.thresholds.to_public_payload(),
            "organic_validation_session": (
                self.session.to_public_payload() if self.session is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class MobileV2OrganicRequestClassification:
    traffic_class: str
    validation_session_id: str | None
    counts_for_validation: bool

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "traffic_class": self.traffic_class,
            "validation_session_id": self.validation_session_id,
            "counts_for_validation": self.counts_for_validation,
        }


def _normalize_reason_rows(reason_counts: dict[str, int]) -> tuple[tuple[str, int], ...]:
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


def _normalize_target_rows(target_counts: dict[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted(
            (
                (str(target_id), int(count))
                for target_id, count in target_counts.items()
                if str(target_id).strip() and int(count) > 0
            ),
            key=lambda item: (int(item[0]), -item[1]),
        )
    )


def _subtract_reason_counts(
    total_counts: dict[str, int],
    subtract_counts: dict[str, int],
) -> dict[str, int]:
    remaining: dict[str, int] = {}
    for reason in set(total_counts) | set(subtract_counts):
        count = int(total_counts.get(reason, 0)) - int(subtract_counts.get(reason, 0))
        if count > 0:
            remaining[str(reason)] = count
    return remaining


def _subtract_target_counts(
    total_counts: dict[str, int],
    subtract_counts: dict[str, int],
) -> dict[str, int]:
    remaining: dict[str, int] = {}
    for target_id in set(total_counts) | set(subtract_counts):
        count = int(total_counts.get(target_id, 0)) - int(subtract_counts.get(target_id, 0))
        if count > 0:
            remaining[str(target_id)] = count
    return remaining


def _sorted_target_ids(values: set[int] | list[int] | tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted({int(item) for item in values if int(item) > 0}))


def _surface_human_checkpoint_key(
    *,
    surface: str,
    target_id: int,
    checkpoint_kind: str,
    delivery_mode: str,
) -> str:
    return f"{surface}:{target_id}:{checkpoint_kind}:{delivery_mode}"


def _thresholds() -> MobileV2OrganicValidationThresholds:
    return MobileV2OrganicValidationThresholds(
        min_requests_per_surface=max(
            env_int(V2_ANDROID_ORGANIC_VALIDATION_MIN_REQUESTS_PER_SURFACE_FLAG, 3),
            1,
        ),
        max_fallback_rate_percent=max(
            0,
            min(
                100,
                env_int(V2_ANDROID_ORGANIC_VALIDATION_MAX_FALLBACK_RATE_PERCENT_FLAG, 15),
            ),
        ),
        max_visibility_violations=max(
            env_int(V2_ANDROID_ORGANIC_VALIDATION_MAX_VISIBILITY_VIOLATIONS_FLAG, 0),
            0,
        ),
        max_parse_errors=max(
            env_int(V2_ANDROID_ORGANIC_VALIDATION_MAX_PARSE_ERRORS_FLAG, 0),
            0,
        ),
        max_http_failures=max(
            env_int(V2_ANDROID_ORGANIC_VALIDATION_MAX_HTTP_FAILURES_FLAG, 0),
            0,
        ),
        window_minutes=max(
            env_int(V2_ANDROID_ORGANIC_VALIDATION_WINDOW_MINUTES_FLAG, 60),
            5,
        ),
        require_full_window=env_bool(
            V2_ANDROID_ORGANIC_VALIDATION_REQUIRE_FULL_WINDOW_FLAG,
            True,
        ),
        target_limit=max(env_int(V2_ANDROID_ORGANIC_VALIDATION_TARGET_LIMIT_FLAG, 2), 1),
    )


def _default_summary_payload() -> MobileV2OrganicValidationSummary:
    thresholds = _thresholds()
    return MobileV2OrganicValidationSummary(
        session=None,
        active=False,
        expired=False,
        started_at=None,
        ended_at=None,
        expires_at=None,
        window_elapsed=False,
        outcome=None,
        candidate_ready_for_real_tenant=False,
        organic_requests_v2=0,
        organic_requests_fallback=0,
        organic_fallback_rate=0.0,
        organic_validation_reason_breakdown=(),
        surface_summaries=(),
        surface_coverage_summary={
            "covered_surfaces": [],
            "missing_surfaces": list(_SURFACES),
            "both_surfaces_covered": False,
            "has_partial_coverage": False,
        },
        distinct_targets={"feed": 0, "thread": 0, "total": 0},
        missing_targets={"feed": [], "thread": []},
        human_confirmed_count=0,
        human_confirmed_targets={"feed": [], "thread": [], "total": []},
        human_confirmed_last_seen_at=None,
        human_confirmed_required_coverage_met=False,
        human_confirmed_surface_summaries=(),
        human_ack_recent_events=(),
        probe_vs_organic_evidence={
            "probe_ignored_for_validation": True,
            "probe_requests_v2_since_start": 0,
            "probe_requests_fallback_since_start": 0,
            "organic_requests_v2_since_start": 0,
            "organic_requests_fallback_since_start": 0,
            "evidence_source": "none",
        },
        thresholds=thresholds,
    )


def get_mobile_v2_organic_validation_default_payload() -> dict[str, Any]:
    return _default_summary_payload().to_public_payload()


def get_mobile_v2_organic_validation_signal(
    *,
    tenant_key: str,
) -> dict[str, Any]:
    summary = get_mobile_v2_organic_validation_summary()
    session = summary.session
    if session is None or not summary.active or session.tenant_key != str(tenant_key or "").strip():
        return {
            "organic_validation_active": False,
            "organic_validation_session_id": None,
            "organic_validation_surfaces": [],
            "organic_validation_target_suggestions": [],
            "organic_validation_surface_coverage": [],
            "organic_validation_has_partial_coverage": False,
            "organic_validation_targets_ready": False,
        }
    surface_payloads = [item.to_public_payload() for item in summary.surface_summaries]
    return {
        "organic_validation_active": True,
        "organic_validation_session_id": session.session_id,
        "organic_validation_surfaces": list(session.surfaces),
        "organic_validation_target_suggestions": surface_payloads,
        "organic_validation_surface_coverage": surface_payloads,
        "organic_validation_has_partial_coverage": summary.surface_coverage_summary.get(
            "has_partial_coverage",
            False,
        ),
        "organic_validation_targets_ready": any(
            bool(item["suggested_target_ids"]) for item in surface_payloads
        ),
    }


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _record_human_ack_event(
    *,
    status: str,
    tenant_key: str,
    session_id: str,
    surface: str,
    target_id: int | None,
    checkpoint_kind: str,
    delivery_mode: str,
    operator_run_id: str | None = None,
    capabilities_version: str | None = None,
    rollout_bucket: int | None = None,
    rejection_reason: str | None = None,
) -> None:
    _human_ack_recent_events.appendleft(
        {
            "timestamp": _iso(_now_utc()),
            "status": str(status or "").strip() or "unknown",
            "tenant_key": str(tenant_key or "").strip() or "unknown",
            "session_id": str(session_id or "").strip() or None,
            "surface": str(surface or "").strip() or None,
            "target_id": int(target_id) if isinstance(target_id, int) else None,
            "checkpoint_kind": str(checkpoint_kind or "").strip() or None,
            "delivery_mode": str(delivery_mode or "").strip() or None,
            "operator_run_id": str(operator_run_id or "").strip() or None,
            "capabilities_version": str(capabilities_version or "").strip() or None,
            "rollout_bucket": int(rollout_bucket)
            if isinstance(rollout_bucket, int)
            else None,
            "rejection_reason": str(rejection_reason or "").strip() or None,
        }
    )


def _parse_iso(value: str | None) -> datetime | None:
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


def _pilot_tenant_key() -> str:
    return str(env_str(V2_ANDROID_PILOT_TENANT_KEY_FLAG, "") or "").strip()


def _is_local_host(remote_host: str | None) -> bool:
    host = str(remote_host or "").strip().lower()
    if not host:
        return True
    return host in _LOCAL_HOSTS


def _resolve_tenant_label(tenant_key: str) -> str | None:
    if not tenant_key:
        return None
    try:
        tenant_id = int(tenant_key)
    except (TypeError, ValueError):
        return None
    with banco_dados.SessaoLocal() as banco:
        empresa = banco.get(Empresa, tenant_id)
        if empresa is None:
            return None
        return str(getattr(empresa, "nome_fantasia", "") or "").strip() or None


def resolve_demo_mobile_organic_validation_targets(
    *,
    tenant_key: str | None = None,
) -> dict[str, tuple[int, ...]]:
    resolved_tenant_key = str(tenant_key or _pilot_tenant_key() or "").strip()
    thresholds = _thresholds()
    current_session = get_mobile_v2_organic_validation_session()
    session_tenant_match = bool(
        current_session is not None
        and current_session.tenant_key == resolved_tenant_key
    )
    if not session_tenant_match and not _safe_demo_tenant_ready(resolved_tenant_key):
        return {surface: () for surface in _SURFACES}

    tenant_id = int(resolved_tenant_key)

    with banco_dados.SessaoLocal() as banco:
        inspector_user_ids = _resolve_demo_mobile_validation_user_ids(
            banco,
            tenant_id=tenant_id,
        )

        feed_query = select(Laudo.id).where(Laudo.empresa_id == tenant_id)
        thread_query = (
            select(Laudo.id)
            .join(MensagemLaudo, MensagemLaudo.laudo_id == Laudo.id)
            .where(Laudo.empresa_id == tenant_id)
            .group_by(Laudo.id)
            .having(func.count(MensagemLaudo.id) > 0)
        )
        if inspector_user_ids:
            feed_query = feed_query.where(Laudo.usuario_id.in_(inspector_user_ids))
            thread_query = thread_query.where(
                Laudo.usuario_id.in_(inspector_user_ids)
            )

        feed_targets = banco.execute(
            feed_query.order_by(Laudo.criado_em.desc(), Laudo.id.desc()).limit(
                thresholds.target_limit
            )
        ).scalars().all()
        thread_targets = banco.execute(
            thread_query.order_by(Laudo.criado_em.desc(), Laudo.id.desc()).limit(
                thresholds.target_limit
            )
        ).scalars().all()
    return {
        "feed": tuple(int(item) for item in feed_targets),
        "thread": tuple(int(item) for item in thread_targets),
    }


def _resolve_demo_mobile_validation_user_ids(
    banco: Any,
    *,
    tenant_id: int,
) -> tuple[int, ...]:
    safe_internal_user_ids = banco.execute(
        select(Usuario.id)
        .where(Usuario.empresa_id == tenant_id)
        .where(Usuario.nivel_acesso == int(NivelAcesso.INSPETOR))
        .where(
            func.lower(func.coalesce(Usuario.email, "")).like(
                f"%{_SAFE_INTERNAL_EMAIL_SUFFIXES[0]}"
            )
        )
        .order_by(Usuario.id.asc())
    ).scalars().all()
    if safe_internal_user_ids:
        return tuple(int(item) for item in safe_internal_user_ids)

    fallback_inspector_user_ids = banco.execute(
        select(Usuario.id)
        .where(Usuario.empresa_id == tenant_id)
        .where(Usuario.nivel_acesso == int(NivelAcesso.INSPETOR))
        .order_by(Usuario.id.asc())
    ).scalars().all()
    return tuple(int(item) for item in fallback_inspector_user_ids)


def _usage_metric(snapshot: dict[str, Any], traffic_class: str, metric: str) -> int:
    traffic_metrics = snapshot.get("traffic_metrics", {})
    traffic_row = traffic_metrics.get(traffic_class, {})
    return int(traffic_row.get(metric, 0))


def _usage_reason_counts(
    snapshot: dict[str, Any],
    traffic_class: str,
    metric: str,
) -> dict[str, int]:
    traffic_reason_counts = snapshot.get("traffic_reason_counts", {})
    traffic_row = traffic_reason_counts.get(traffic_class, {})
    return {
        str(reason): int(count)
        for reason, count in dict(traffic_row.get(metric, {})).items()
        if int(count) > 0
    }


def _usage_target_counts(
    snapshot: dict[str, Any],
    traffic_class: str,
    metric: str,
) -> dict[str, int]:
    traffic_target_metrics = snapshot.get("traffic_target_metrics", {})
    traffic_row = traffic_target_metrics.get(traffic_class, {})
    return {
        str(target_id): int(count)
        for target_id, count in dict(traffic_row.get(metric, {})).items()
        if int(count) > 0
    }


def _build_surface_snapshot(*, tenant_key: str, surface: str) -> dict[str, Any]:
    snapshot = get_mobile_v2_surface_metrics_snapshot(tenant_key=tenant_key, endpoint=surface)
    validation_target_counts = dict(
        _usage_target_counts(snapshot, "organic_validation", "v2_served")
    )
    for target_id, count in _usage_target_counts(
        snapshot,
        "legacy_fallback_from_validation",
        "legacy_fallbacks",
    ).items():
        validation_target_counts[target_id] = (
            int(validation_target_counts.get(target_id, 0)) + int(count)
        )
    return {
        "surface": surface,
        "validation_v2_served": _usage_metric(snapshot, "organic_validation", "v2_served"),
        "validation_legacy_fallbacks": _usage_metric(
            snapshot,
            "legacy_fallback_from_validation",
            "legacy_fallbacks",
        ),
        "validation_reason_counts": _usage_reason_counts(
            snapshot,
            "legacy_fallback_from_validation",
            "legacy_fallbacks",
        ),
        "validation_target_counts": validation_target_counts,
        "probe_v2_served": int(snapshot.get("probe_metrics", {}).get("v2_served", 0)),
        "probe_legacy_fallbacks": int(
            snapshot.get("probe_metrics", {}).get("legacy_fallbacks", 0)
        ),
    }


def _safe_demo_tenant_ready(tenant_key: str) -> bool:
    if not tenant_key:
        return False
    from app.v2.mobile_rollout import discover_mobile_v2_safe_pilot_candidates

    return any(item.tenant_key == tenant_key for item in discover_mobile_v2_safe_pilot_candidates())


def _pilot_surfaces_are_promoted(tenant_key: str) -> bool:
    if not tenant_key:
        return False
    from app.v2.mobile_rollout import resolve_mobile_v2_rollout_state_for_tenant_key

    rollout_state = resolve_mobile_v2_rollout_state_for_tenant_key(tenant_key)
    return all(getattr(rollout_state, surface).state == "promoted" for surface in _SURFACES)


def _baseline_by_surface(
    session: MobileV2OrganicValidationSession,
) -> dict[str, MobileV2OrganicValidationBaseline]:
    return {item.surface: item for item in session.baselines}


def _human_checkpoints_for_session(
    session_id: str,
) -> tuple[MobileOrganicHumanCheckpoint, ...]:
    with _lock:
        rows = dict(_human_confirmation_state.get(session_id, {}))
    return tuple(
        sorted(
            rows.values(),
            key=lambda item: (
                item.confirmed_at,
                item.surface,
                item.target_id,
                item.checkpoint_kind,
            ),
        )
    )


def list_mobile_v2_organic_human_checkpoints(
    session_id: str | None = None,
) -> tuple[MobileOrganicHumanCheckpoint, ...]:
    resolved_session_id = str(session_id or "").strip()
    if not resolved_session_id:
        current_session = get_mobile_v2_organic_validation_session()
        if current_session is None:
            return ()
        resolved_session_id = current_session.session_id
    return _human_checkpoints_for_session(resolved_session_id)


def _session_is_currently_active(
    session: MobileV2OrganicValidationSession | None,
) -> bool:
    if session is None or not session.active or session.ended_at:
        return False
    expires_at = _parse_iso(session.expires_at)
    if expires_at is None:
        return False
    return _now_utc() < expires_at


def _target_is_eligible_for_surface(
    *,
    tenant_key: str,
    surface: str,
    target_id: int,
) -> bool:
    if not tenant_key or surface not in _SURFACES or int(target_id) <= 0:
        return False

    with banco_dados.SessaoLocal() as banco:
        if surface == "feed":
            eligible = banco.scalar(
                select(Laudo.id).where(
                    Laudo.id == int(target_id),
                    Laudo.empresa_id == int(tenant_key),
                )
            )
            return eligible is not None

        eligible = banco.scalar(
            select(Laudo.id)
            .join(MensagemLaudo, MensagemLaudo.laudo_id == Laudo.id)
            .where(
                Laudo.id == int(target_id),
                Laudo.empresa_id == int(tenant_key),
            )
            .group_by(Laudo.id)
            .having(func.count(MensagemLaudo.id) > 0)
        )
        return eligible is not None


def record_mobile_v2_organic_human_checkpoint(
    *,
    tenant_key: str,
    session_id: str,
    surface: str,
    target_id: int,
    checkpoint_kind: str,
    delivery_mode: str,
    operator_run_id: str | None = None,
    capabilities_version: str | None = None,
    rollout_bucket: int | None = None,
    source_channel: str = _HUMAN_SOURCE_CHANNEL,
) -> dict[str, Any]:
    session = get_mobile_v2_organic_validation_session()
    resolved_tenant_key = str(tenant_key or "").strip()
    resolved_session_id = str(session_id or "").strip()
    resolved_surface = str(surface or "").strip()
    resolved_target_id = int(target_id)
    resolved_checkpoint_kind = str(checkpoint_kind or "").strip().lower()
    resolved_delivery_mode = str(delivery_mode or "").strip().lower()
    resolved_operator_run_id = str(operator_run_id or "").strip()[:64] or None
    resolved_capabilities_version = str(capabilities_version or "").strip() or None
    resolved_rollout_bucket = (
        int(rollout_bucket) if isinstance(rollout_bucket, int) else None
    )

    if not _session_is_currently_active(session) or session is None:
        _record_human_ack_event(
            status="rejected",
            tenant_key=resolved_tenant_key,
            session_id=resolved_session_id,
            surface=resolved_surface,
            target_id=resolved_target_id,
            checkpoint_kind=resolved_checkpoint_kind,
            delivery_mode=resolved_delivery_mode,
            operator_run_id=resolved_operator_run_id,
            capabilities_version=resolved_capabilities_version,
            rollout_bucket=resolved_rollout_bucket,
            rejection_reason="organic_validation_ack_session_inactive",
        )
        raise RuntimeError("organic_validation_ack_session_inactive")
    if session.tenant_key != resolved_tenant_key or not _safe_demo_tenant_ready(
        resolved_tenant_key
    ):
        _record_human_ack_event(
            status="rejected",
            tenant_key=resolved_tenant_key,
            session_id=resolved_session_id,
            surface=resolved_surface,
            target_id=resolved_target_id,
            checkpoint_kind=resolved_checkpoint_kind,
            delivery_mode=resolved_delivery_mode,
            operator_run_id=resolved_operator_run_id,
            capabilities_version=resolved_capabilities_version,
            rollout_bucket=resolved_rollout_bucket,
            rejection_reason="organic_validation_ack_tenant_not_eligible",
        )
        raise PermissionError("organic_validation_ack_tenant_not_eligible")
    if resolved_session_id != session.session_id:
        _record_human_ack_event(
            status="rejected",
            tenant_key=resolved_tenant_key,
            session_id=resolved_session_id,
            surface=resolved_surface,
            target_id=resolved_target_id,
            checkpoint_kind=resolved_checkpoint_kind,
            delivery_mode=resolved_delivery_mode,
            operator_run_id=resolved_operator_run_id,
            capabilities_version=resolved_capabilities_version,
            rollout_bucket=resolved_rollout_bucket,
            rejection_reason="organic_validation_ack_session_mismatch",
        )
        raise RuntimeError("organic_validation_ack_session_mismatch")
    if resolved_surface not in session.surfaces:
        _record_human_ack_event(
            status="rejected",
            tenant_key=resolved_tenant_key,
            session_id=resolved_session_id,
            surface=resolved_surface,
            target_id=resolved_target_id,
            checkpoint_kind=resolved_checkpoint_kind,
            delivery_mode=resolved_delivery_mode,
            operator_run_id=resolved_operator_run_id,
            capabilities_version=resolved_capabilities_version,
            rollout_bucket=resolved_rollout_bucket,
            rejection_reason="organic_validation_ack_surface_not_active",
        )
        raise RuntimeError("organic_validation_ack_surface_not_active")
    if resolved_checkpoint_kind not in _HUMAN_CHECKPOINT_KINDS:
        _record_human_ack_event(
            status="rejected",
            tenant_key=resolved_tenant_key,
            session_id=resolved_session_id,
            surface=resolved_surface,
            target_id=resolved_target_id,
            checkpoint_kind=resolved_checkpoint_kind,
            delivery_mode=resolved_delivery_mode,
            operator_run_id=resolved_operator_run_id,
            capabilities_version=resolved_capabilities_version,
            rollout_bucket=resolved_rollout_bucket,
            rejection_reason="organic_validation_ack_invalid_checkpoint",
        )
        raise RuntimeError("organic_validation_ack_invalid_checkpoint")
    if resolved_delivery_mode not in _HUMAN_DELIVERY_MODES:
        _record_human_ack_event(
            status="rejected",
            tenant_key=resolved_tenant_key,
            session_id=resolved_session_id,
            surface=resolved_surface,
            target_id=resolved_target_id,
            checkpoint_kind=resolved_checkpoint_kind,
            delivery_mode=resolved_delivery_mode,
            operator_run_id=resolved_operator_run_id,
            capabilities_version=resolved_capabilities_version,
            rollout_bucket=resolved_rollout_bucket,
            rejection_reason="organic_validation_ack_invalid_delivery_mode",
        )
        raise RuntimeError("organic_validation_ack_invalid_delivery_mode")
    if not _target_is_eligible_for_surface(
        tenant_key=resolved_tenant_key,
        surface=resolved_surface,
        target_id=resolved_target_id,
    ):
        _record_human_ack_event(
            status="rejected",
            tenant_key=resolved_tenant_key,
            session_id=resolved_session_id,
            surface=resolved_surface,
            target_id=resolved_target_id,
            checkpoint_kind=resolved_checkpoint_kind,
            delivery_mode=resolved_delivery_mode,
            operator_run_id=resolved_operator_run_id,
            capabilities_version=resolved_capabilities_version,
            rollout_bucket=resolved_rollout_bucket,
            rejection_reason="organic_validation_ack_target_not_eligible",
        )
        raise RuntimeError("organic_validation_ack_target_not_eligible")

    checkpoint = MobileOrganicHumanCheckpoint(
        tenant_key=resolved_tenant_key,
        session_id=resolved_session_id,
        surface=resolved_surface,
        target_id=resolved_target_id,
        checkpoint_kind=resolved_checkpoint_kind,
        confirmed_at=_iso(_now_utc()) or "",
        source_channel=str(source_channel or _HUMAN_SOURCE_CHANNEL).strip()
        or _HUMAN_SOURCE_CHANNEL,
        delivery_mode=resolved_delivery_mode,
        operator_run_id=resolved_operator_run_id,
        capabilities_version=resolved_capabilities_version,
        rollout_bucket=resolved_rollout_bucket,
    )
    checkpoint_key = _surface_human_checkpoint_key(
        surface=checkpoint.surface,
        target_id=checkpoint.target_id,
        checkpoint_kind=checkpoint.checkpoint_kind,
        delivery_mode=checkpoint.delivery_mode,
    )
    with _lock:
        session_rows = _human_confirmation_state.setdefault(resolved_session_id, {})
        duplicate = checkpoint_key in session_rows
        if not duplicate:
            session_rows[checkpoint_key] = checkpoint
        _record_human_ack_event(
            status="duplicate" if duplicate else "accepted",
            tenant_key=resolved_tenant_key,
            session_id=resolved_session_id,
            surface=resolved_surface,
            target_id=resolved_target_id,
            checkpoint_kind=resolved_checkpoint_kind,
            delivery_mode=resolved_delivery_mode,
            operator_run_id=resolved_operator_run_id,
            capabilities_version=resolved_capabilities_version,
            rollout_bucket=resolved_rollout_bucket,
        )

    return {
        "ok": True,
        "duplicate": duplicate,
        "checkpoint": checkpoint.to_public_payload(),
    }


def resolve_mobile_v2_organic_request_classification(
    *,
    tenant_key: str,
    endpoint: str,
    usage_mode: str | None,
    validation_session_id: str | None,
    is_probe: bool,
    is_fallback: bool,
) -> MobileV2OrganicRequestClassification:
    if is_probe:
        return MobileV2OrganicRequestClassification(
            traffic_class="probe",
            validation_session_id=None,
            counts_for_validation=False,
        )

    session = get_mobile_v2_organic_validation_session()
    tenant = str(tenant_key or "").strip()
    route = str(endpoint or "").strip()
    mode = str(usage_mode or "").strip().lower()
    session_id = str(validation_session_id or "").strip()
    if (
        _session_is_currently_active(session)
        and session is not None
        and session.tenant_key == tenant
        and route in session.surfaces
        and mode == _VALIDATION_USAGE_MODE
        and session.session_id == session_id
    ):
        return MobileV2OrganicRequestClassification(
            traffic_class=(
                "legacy_fallback_from_validation"
                if is_fallback
                else "organic_validation"
            ),
            validation_session_id=session.session_id,
            counts_for_validation=True,
        )
    return MobileV2OrganicRequestClassification(
        traffic_class="legacy_general" if is_fallback else "organic_general",
        validation_session_id=None,
        counts_for_validation=False,
    )


def _surface_outcome(
    *,
    delta_requests: int,
    delta_fallbacks: int,
    reason_counts: dict[str, int],
    thresholds: MobileV2OrganicValidationThresholds,
    window_elapsed: bool,
    covered_target_ids: tuple[int, ...],
) -> str:
    parse_errors = int(reason_counts.get("parse_error", 0))
    visibility_errors = int(reason_counts.get("visibility_violation", 0))
    http_failures = sum(int(reason_counts.get(reason, 0)) for reason in _HTTP_FAILURE_REASONS)
    fallback_rate = (delta_fallbacks / delta_requests) if delta_requests > 0 else 0.0
    if parse_errors > thresholds.max_parse_errors:
        return "rollback_recommended"
    if visibility_errors > thresholds.max_visibility_violations:
        return "rollback_recommended"
    if http_failures > thresholds.max_http_failures:
        return "hold_recommended"
    if fallback_rate > (thresholds.max_fallback_rate_percent / 100):
        return "hold_recommended"
    if delta_requests <= 0:
        return "insufficient_evidence"
    if delta_requests < thresholds.min_requests_per_surface or not covered_target_ids:
        return "observing"
    if thresholds.require_full_window and not window_elapsed:
        return "healthy"
    return "candidate_ready_for_real_tenant"


def _build_target_summary(
    *,
    surface: str,
    suggested_target_ids: tuple[int, ...],
    observed_target_ids: tuple[int, ...],
    delta_requests: int,
    thresholds: MobileV2OrganicValidationThresholds,
) -> MobileV2OrganicValidationTargetSummary:
    observed_set = set(observed_target_ids)
    suggested_set = set(suggested_target_ids)
    covered = tuple(sorted(suggested_set & observed_set))
    missing = tuple(sorted(suggested_set - observed_set))
    targets_available = bool(suggested_target_ids)
    coverage_met = (
        delta_requests >= thresholds.min_requests_per_surface
        and (bool(covered) if targets_available else False)
    )
    detail = (
        "targets_suggested"
        if targets_available
        else "no_eligible_targets"
    )
    return MobileV2OrganicValidationTargetSummary(
        surface=surface,
        suggested_target_ids=suggested_target_ids,
        covered_target_ids=covered,
        missing_target_ids=missing,
        distinct_targets_observed=len(observed_set),
        coverage_met=coverage_met,
        targets_available=targets_available,
        detail=detail,
    )


def start_mobile_v2_organic_validation_session(
    *,
    remote_host: str | None = None,
    trigger_source: str = "admin_api",
) -> MobileV2OrganicValidationSummary:
    if not _is_local_host(remote_host):
        raise PermissionError("organic_validation_requires_local_host")

    tenant_key = _pilot_tenant_key()
    if not _safe_demo_tenant_ready(tenant_key):
        raise RuntimeError("organic_validation_tenant_not_safe")
    if not _pilot_surfaces_are_promoted(tenant_key):
        raise RuntimeError("organic_validation_requires_promoted_surfaces")

    thresholds = _thresholds()
    now = _now_utc()
    baselines: list[MobileV2OrganicValidationBaseline] = []
    for surface in _SURFACES:
        snapshot = _build_surface_snapshot(tenant_key=tenant_key, surface=surface)
        baselines.append(
            MobileV2OrganicValidationBaseline(
                surface=surface,
                validation_v2_served=snapshot["validation_v2_served"],
                validation_legacy_fallbacks=snapshot["validation_legacy_fallbacks"],
                validation_fallback_reasons=_normalize_reason_rows(
                    snapshot["validation_reason_counts"]
                ),
                validation_target_counts=_normalize_target_rows(
                    snapshot["validation_target_counts"]
                ),
                probe_v2_served=snapshot["probe_v2_served"],
                probe_legacy_fallbacks=snapshot["probe_legacy_fallbacks"],
            )
        )

    session = MobileV2OrganicValidationSession(
        tenant_key=tenant_key,
        tenant_label=_resolve_tenant_label(tenant_key),
        session_id=f"orgv_{uuid4().hex[:12]}",
        surfaces=_SURFACES,
        started_at=_iso(now) or "",
        expires_at=_iso(now + timedelta(minutes=thresholds.window_minutes)) or "",
        active=True,
        ended_at=None,
        trigger_source=trigger_source,
        stop_source=None,
        baselines=tuple(baselines),
    )
    with _lock:
        global _session_state
        _session_state = session
        _human_confirmation_state.clear()
        _human_confirmation_state[session.session_id] = {}
        _human_ack_recent_events.clear()
    return get_mobile_v2_organic_validation_summary()


def stop_mobile_v2_organic_validation_session(
    *,
    remote_host: str | None = None,
    trigger_source: str = "admin_api",
) -> MobileV2OrganicValidationSummary:
    if not _is_local_host(remote_host):
        raise PermissionError("organic_validation_requires_local_host")
    already_stopped = False
    with _lock:
        global _session_state
        session = _session_state
        if session is None:
            raise RuntimeError("organic_validation_not_started")
        if not session.active or session.ended_at:
            already_stopped = True
        else:
            _session_state = MobileV2OrganicValidationSession(
                tenant_key=session.tenant_key,
                tenant_label=session.tenant_label,
                session_id=session.session_id,
                surfaces=session.surfaces,
                started_at=session.started_at,
                expires_at=session.expires_at,
                active=False,
                ended_at=_iso(_now_utc()),
                trigger_source=session.trigger_source,
                stop_source=trigger_source,
                baselines=session.baselines,
            )
    if already_stopped:
        return get_mobile_v2_organic_validation_summary()
    return get_mobile_v2_organic_validation_summary()


def clear_mobile_v2_organic_validation_session_for_tests() -> None:
    with _lock:
        global _session_state
        _session_state = None
        _human_confirmation_state.clear()
        _human_ack_recent_events.clear()


def get_mobile_v2_organic_validation_session() -> MobileV2OrganicValidationSession | None:
    with _lock:
        return _session_state


def get_mobile_v2_organic_validation_summary() -> MobileV2OrganicValidationSummary:
    session = get_mobile_v2_organic_validation_session()
    if session is None:
        return _default_summary_payload()

    thresholds = _thresholds()
    ended_at = _parse_iso(session.ended_at)
    expires_at = _parse_iso(session.expires_at)
    now = _now_utc()
    reference_time = ended_at or now
    window_elapsed = bool(expires_at is not None and reference_time >= expires_at)
    active = bool(session.active and not ended_at and not window_elapsed)
    expired = bool(window_elapsed and ended_at is None)

    baselines = _baseline_by_surface(session)
    target_suggestions = resolve_demo_mobile_organic_validation_targets(
        tenant_key=session.tenant_key
    )
    aggregate_reason_counts: dict[str, int] = {}
    surface_summaries: list[MobileV2OrganicSurfaceValidationSummary] = []
    validation_requests_v2 = 0
    validation_requests_fallback = 0
    probe_requests_v2 = 0
    probe_requests_fallback = 0
    distinct_targets: dict[str, Any] = {"feed": 0, "thread": 0, "total": 0}
    missing_targets: dict[str, list[int]] = {"feed": [], "thread": []}
    all_observed_target_ids: set[int] = set()
    checkpoints = _human_checkpoints_for_session(session.session_id)
    checkpoints_by_surface = {
        surface: tuple(item for item in checkpoints if item.surface == surface)
        for surface in _SURFACES
    }
    human_surface_summaries: list[MobileOrganicHumanSurfaceSummary] = []
    human_confirmed_targets: dict[str, list[int]] = {
        "feed": [],
        "thread": [],
        "total": [],
    }
    human_confirmed_last_seen_at: str | None = None

    for surface in _SURFACES:
        baseline = baselines[surface]
        current_snapshot = _build_surface_snapshot(tenant_key=session.tenant_key, surface=surface)
        baseline_reason_counts = dict(baseline.validation_fallback_reasons)
        baseline_target_counts = dict(baseline.validation_target_counts)
        delta_reason_counts = _subtract_reason_counts(
            current_snapshot["validation_reason_counts"],
            baseline_reason_counts,
        )
        delta_target_counts = _subtract_target_counts(
            current_snapshot["validation_target_counts"],
            baseline_target_counts,
        )
        delta_v2 = max(
            0,
            int(current_snapshot["validation_v2_served"]) - int(baseline.validation_v2_served),
        )
        delta_fallback = max(
            0,
            int(current_snapshot["validation_legacy_fallbacks"])
            - int(baseline.validation_legacy_fallbacks),
        )
        delta_probe_v2 = max(
            0,
            int(current_snapshot["probe_v2_served"]) - int(baseline.probe_v2_served),
        )
        delta_probe_fallback = max(
            0,
            int(current_snapshot["probe_legacy_fallbacks"])
            - int(baseline.probe_legacy_fallbacks),
        )
        delta_requests = delta_v2 + delta_fallback
        observed_target_ids = _sorted_target_ids(
            {int(target_id) for target_id in delta_target_counts.keys() if str(target_id).strip()}
        )
        target_summary = _build_target_summary(
            surface=surface,
            suggested_target_ids=target_suggestions.get(surface, ()),
            observed_target_ids=observed_target_ids,
            delta_requests=delta_requests,
            thresholds=thresholds,
        )
        surface_checkpoints = checkpoints_by_surface.get(surface, ())
        human_confirmed_targets_for_surface = _sorted_target_ids(
            {
                item.target_id
                for item in surface_checkpoints
                if item.delivery_mode == _HUMAN_CONFIRMED_DELIVERY_MODE
            }
        )
        human_matching_targets = _sorted_target_ids(
            set(human_confirmed_targets_for_surface)
            & set(target_summary.covered_target_ids)
        )
        human_last_seen_at = max(
            (
                item.confirmed_at
                for item in surface_checkpoints
                if item.delivery_mode == _HUMAN_CONFIRMED_DELIVERY_MODE
            ),
            default=None,
        )
        human_surface_summary = MobileOrganicHumanSurfaceSummary(
            surface=surface,
            human_confirmed_count=len(human_confirmed_targets_for_surface),
            human_confirmed_targets=human_confirmed_targets_for_surface,
            human_confirmed_last_seen_at=human_last_seen_at,
            human_confirmed_required_coverage_met=bool(human_matching_targets),
            legacy_rendered_under_validation_count=sum(
                1
                for item in surface_checkpoints
                if item.delivery_mode != _HUMAN_CONFIRMED_DELIVERY_MODE
            ),
        )
        fallback_rate = (delta_fallback / delta_requests) if delta_requests > 0 else 0.0
        outcome = _surface_outcome(
            delta_requests=delta_requests,
            delta_fallbacks=delta_fallback,
            reason_counts=delta_reason_counts,
            thresholds=thresholds,
            window_elapsed=window_elapsed,
            covered_target_ids=target_summary.covered_target_ids,
        )
        if (
            outcome == "candidate_ready_for_real_tenant"
            and not human_surface_summary.human_confirmed_required_coverage_met
        ):
            outcome = "healthy"
        surface_summaries.append(
            MobileV2OrganicSurfaceValidationSummary(
                surface=surface,
                outcome=outcome,
                organic_requests_v2=delta_v2,
                organic_requests_fallback=delta_fallback,
                organic_fallback_rate=round(fallback_rate, 4),
                organic_fallback_reason_breakdown=_normalize_reason_rows(delta_reason_counts),
                coverage_met=target_summary.coverage_met,
                sufficient_evidence=delta_requests > 0,
                candidate_ready_for_real_tenant=(
                    outcome == "candidate_ready_for_real_tenant"
                ),
                target_summary=target_summary,
                human_surface_summary=human_surface_summary,
            )
        )
        human_surface_summaries.append(human_surface_summary)
        validation_requests_v2 += delta_v2
        validation_requests_fallback += delta_fallback
        probe_requests_v2 += delta_probe_v2
        probe_requests_fallback += delta_probe_fallback
        distinct_targets[surface] = target_summary.distinct_targets_observed
        missing_targets[surface] = list(target_summary.missing_target_ids)
        all_observed_target_ids.update(observed_target_ids)
        human_confirmed_targets[surface] = list(human_confirmed_targets_for_surface)
        if human_last_seen_at and (
            human_confirmed_last_seen_at is None
            or human_last_seen_at > human_confirmed_last_seen_at
        ):
            human_confirmed_last_seen_at = human_last_seen_at
        for reason, count in delta_reason_counts.items():
            aggregate_reason_counts[reason] = int(aggregate_reason_counts.get(reason, 0)) + int(count)

    distinct_targets["total"] = len(all_observed_target_ids)
    human_confirmed_targets["total"] = list(
        _sorted_target_ids(
            {
                target_id
                for surface in _SURFACES
                for target_id in human_confirmed_targets.get(surface, [])
            }
        )
    )
    total_requests = validation_requests_v2 + validation_requests_fallback
    fallback_rate = (validation_requests_fallback / total_requests) if total_requests > 0 else 0.0
    covered_surfaces = [item.surface for item in surface_summaries if item.coverage_met]
    missing_surfaces = [item.surface for item in surface_summaries if not item.coverage_met]

    if any(item.outcome == "rollback_recommended" for item in surface_summaries):
        outcome = "rollback_recommended"
    elif any(item.outcome == "hold_recommended" for item in surface_summaries):
        outcome = "hold_recommended"
    elif total_requests <= 0:
        outcome = "insufficient_evidence"
    elif any(item.outcome == "insufficient_evidence" for item in surface_summaries):
        outcome = "insufficient_evidence"
    elif any(item.outcome == "observing" for item in surface_summaries):
        outcome = "observing"
    elif all(
        item.outcome == "candidate_ready_for_real_tenant"
        for item in surface_summaries
    ):
        outcome = "candidate_ready_for_real_tenant"
    else:
        outcome = "healthy"

    if (
        validation_requests_v2 + validation_requests_fallback <= 0
        and probe_requests_v2 + probe_requests_fallback <= 0
    ):
        evidence_source = "none"
    elif validation_requests_v2 + validation_requests_fallback <= 0:
        evidence_source = "probe_only"
    elif probe_requests_v2 + probe_requests_fallback <= 0:
        evidence_source = "organic_only"
    else:
        evidence_source = "mixed"
    human_confirmed_required_coverage_met = bool(human_surface_summaries) and all(
        item.human_confirmed_required_coverage_met for item in human_surface_summaries
    )
    with _lock:
        human_ack_recent_events = tuple(dict(item) for item in _human_ack_recent_events)

    return MobileV2OrganicValidationSummary(
        session=session,
        active=active,
        expired=expired,
        started_at=session.started_at,
        ended_at=_iso(ended_at),
        expires_at=session.expires_at,
        window_elapsed=window_elapsed,
        outcome=outcome,
        candidate_ready_for_real_tenant=(outcome == "candidate_ready_for_real_tenant"),
        organic_requests_v2=validation_requests_v2,
        organic_requests_fallback=validation_requests_fallback,
        organic_fallback_rate=round(fallback_rate, 4),
        organic_validation_reason_breakdown=_normalize_reason_rows(aggregate_reason_counts),
        surface_summaries=tuple(surface_summaries),
        surface_coverage_summary={
            "covered_surfaces": covered_surfaces,
            "missing_surfaces": missing_surfaces,
            "both_surfaces_covered": len(missing_surfaces) == 0 and bool(surface_summaries),
            "has_partial_coverage": bool(covered_surfaces) and bool(missing_surfaces),
        },
        distinct_targets=distinct_targets,
        missing_targets=missing_targets,
        human_confirmed_count=sum(
            item.human_confirmed_count for item in human_surface_summaries
        ),
        human_confirmed_targets=human_confirmed_targets,
        human_confirmed_last_seen_at=human_confirmed_last_seen_at,
        human_confirmed_required_coverage_met=(
            human_confirmed_required_coverage_met
        ),
        human_confirmed_surface_summaries=tuple(human_surface_summaries),
        human_ack_recent_events=human_ack_recent_events,
        probe_vs_organic_evidence={
            "probe_ignored_for_validation": True,
            "probe_requests_v2_since_start": probe_requests_v2,
            "probe_requests_fallback_since_start": probe_requests_fallback,
            "organic_requests_v2_since_start": validation_requests_v2,
            "organic_requests_fallback_since_start": validation_requests_fallback,
            "evidence_source": evidence_source,
        },
        thresholds=thresholds,
    )
