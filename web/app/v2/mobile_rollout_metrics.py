"""Agregacao operacional leve do rollout mobile V2."""

from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.core.settings import env_bool

MOBILE_V2_ROLLOUT_OBSERVABILITY_FLAG = "TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY"
MOBILE_V2_PILOT_OBSERVABILITY_CONTRACT_NAME = "MobileInspectorPilotObservabilityV1"
MOBILE_V2_PILOT_OBSERVABILITY_CONTRACT_VERSION = "v1"
_METRIC_NAMES = (
    "capabilities_checks",
    "rollout_denied",
    "v2_served",
    "legacy_fallbacks",
)
_RECENT_EVENT_LIMIT = 120
_REQUEST_TRACE_LIMIT = 120

_lock = Lock()
_totals: Counter[str] = Counter()
_by_tenant: Counter[tuple[str, str]] = Counter()
_by_endpoint: Counter[tuple[str, str]] = Counter()
_by_reason: Counter[tuple[str, str]] = Counter()
_by_bucket: Counter[tuple[str, str]] = Counter()
_by_tenant_endpoint_metric: Counter[tuple[str, str, str]] = Counter()
_by_tenant_endpoint_reason: Counter[tuple[str, str, str, str]] = Counter()
_by_tenant_endpoint_traffic_metric: Counter[tuple[str, str, str, str]] = Counter()
_by_tenant_endpoint_traffic_reason: Counter[tuple[str, str, str, str, str]] = Counter()
_by_tenant_endpoint_traffic_target_metric: Counter[
    tuple[str, str, str, str, str]
] = Counter()
_probe_totals: Counter[str] = Counter()
_probe_by_tenant_endpoint_metric: Counter[tuple[str, str, str]] = Counter()
_probe_by_tenant_endpoint_reason: Counter[tuple[str, str, str, str]] = Counter()
_probe_runtime_state: dict[str, Any] = {}
_recent_events: deque[dict[str, Any]] = deque(maxlen=_RECENT_EVENT_LIMIT)
_recent_request_traces: deque[dict[str, Any]] = deque(maxlen=_REQUEST_TRACE_LIMIT)


def mobile_v2_rollout_observability_enabled() -> bool:
    return env_bool(MOBILE_V2_ROLLOUT_OBSERVABILITY_FLAG, False)


def _metric_name(kind: str) -> str:
    if kind not in _METRIC_NAMES:
        raise ValueError(f"Unsupported mobile V2 rollout metric kind: {kind}")
    return kind


def _bucket_key(rollout_bucket: int | None) -> str:
    if rollout_bucket is None:
        return "unknown"
    return str(int(rollout_bucket))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _traffic_class_key(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _target_keys(values: list[int] | tuple[int, ...] | None) -> list[str]:
    keys: set[str] = set()
    for item in values or ():
        try:
            target_id = int(item)
        except (TypeError, ValueError):
            continue
        if target_id > 0:
            keys.add(str(target_id))
    return sorted(keys, key=int)


def _normalized_optional_text(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _record_event(
    *,
    kind: str,
    tenant_key: str,
    endpoint: str,
    reason: str,
    source: str,
    rollout_bucket: int | None,
    capabilities_version: str,
    client_capabilities_version: str | None = None,
    client_rollout_bucket: int | None = None,
    probe_label: str | None = None,
    probe_source: str | None = None,
    traffic_class: str | None = None,
    validation_session_id: str | None = None,
    target_ids: list[int] | tuple[int, ...] | None = None,
) -> None:
    metric = _metric_name(kind)
    tenant = str(tenant_key or "").strip() or "unknown"
    endpoint_key = str(endpoint or "").strip() or "unknown"
    reason_key = str(reason or "").strip() or "unknown"
    source_key = str(source or "").strip() or "unknown"
    bucket_key = _bucket_key(rollout_bucket)
    probe_key = str(probe_label or "").strip() or None
    probe_source_key = str(probe_source or "").strip() or None
    traffic_key = _traffic_class_key(traffic_class)
    validation_session_key = str(validation_session_id or "").strip() or None
    target_keys = _target_keys(target_ids)

    with _lock:
        _totals[metric] += 1
        _by_tenant[(tenant, metric)] += 1
        _by_endpoint[(endpoint_key, metric)] += 1
        _by_reason[(reason_key, metric)] += 1
        _by_bucket[(bucket_key, metric)] += 1
        _by_tenant_endpoint_metric[(tenant, endpoint_key, metric)] += 1
        _by_tenant_endpoint_reason[(tenant, endpoint_key, reason_key, metric)] += 1
        if traffic_key and metric in {"v2_served", "legacy_fallbacks"}:
            _by_tenant_endpoint_traffic_metric[(tenant, endpoint_key, traffic_key, metric)] += 1
            _by_tenant_endpoint_traffic_reason[
                (tenant, endpoint_key, traffic_key, reason_key, metric)
            ] += 1
            for target_key in target_keys:
                _by_tenant_endpoint_traffic_target_metric[
                    (tenant, endpoint_key, traffic_key, target_key, metric)
                ] += 1
        if probe_key and metric in {"v2_served", "legacy_fallbacks"}:
            _probe_totals[metric] += 1
            _probe_by_tenant_endpoint_metric[(tenant, endpoint_key, metric)] += 1
            _probe_by_tenant_endpoint_reason[(tenant, endpoint_key, reason_key, metric)] += 1
        _recent_events.appendleft(
            {
                "timestamp": _now_iso(),
                "kind": metric,
                "tenant_key": tenant,
                "endpoint": endpoint_key,
                "reason": reason_key,
                "source": source_key,
                "rollout_bucket": rollout_bucket,
                "capabilities_version": capabilities_version,
                "client_capabilities_version": client_capabilities_version,
                "client_rollout_bucket": client_rollout_bucket,
                "probe_label": probe_key,
                "probe_source": probe_source_key,
                "traffic_class": traffic_key,
                "validation_session_id": validation_session_key,
                "target_ids": target_keys,
            }
        )


def record_mobile_v2_request_trace(
    *,
    phase: str,
    endpoint: str,
    route: str,
    delivery_path: str,
    trace_id: str | None,
    attempted: bool,
    validation_session_id: str | None = None,
    operator_run_id: str | None = None,
    tenant_key: str | None = None,
    target_ids: list[int] | tuple[int, ...] | None = None,
    traffic_class: str | None = None,
    usage_mode: str | None = None,
    counted_kind: str | None = None,
    metadata_available: bool | None = None,
    capabilities_version: str | None = None,
    rollout_bucket: int | None = None,
    http_status: int | None = None,
    correlation_id: str | None = None,
    client_route: str | None = None,
) -> None:
    with _lock:
        _recent_request_traces.appendleft(
            {
                "timestamp": _now_iso(),
                "phase": _normalized_optional_text(phase) or "unknown",
                "endpoint": _normalized_optional_text(endpoint) or "unknown",
                "route": _normalized_optional_text(route) or "unknown",
                "delivery_path": _normalized_optional_text(delivery_path) or "unknown",
                "trace_id": _normalized_optional_text(trace_id),
                "attempted": bool(attempted),
                "validation_session_id": _normalized_optional_text(validation_session_id),
                "operator_run_id": _normalized_optional_text(operator_run_id),
                "tenant_key": _normalized_optional_text(tenant_key),
                "target_ids": _target_keys(target_ids),
                "traffic_class": _traffic_class_key(traffic_class),
                "usage_mode": _normalized_optional_text(usage_mode),
                "counted_kind": _normalized_optional_text(counted_kind),
                "metadata_available": metadata_available,
                "capabilities_version": _normalized_optional_text(capabilities_version),
                "rollout_bucket": rollout_bucket,
                "http_status": http_status,
                "correlation_id": _normalized_optional_text(correlation_id),
                "client_route": _normalized_optional_text(client_route),
            }
        )


def record_mobile_v2_capabilities_check(
    *,
    tenant_key: str,
    rollout_bucket: int | None,
    capabilities_version: str,
    reason: str,
    source: str,
    feed_enabled: bool,
    feed_reason: str,
    thread_enabled: bool,
    thread_reason: str,
) -> None:
    _record_event(
        kind="capabilities_checks",
        tenant_key=tenant_key,
        endpoint="capabilities",
        reason=reason,
        source=source,
        rollout_bucket=rollout_bucket,
        capabilities_version=capabilities_version,
    )
    if not feed_enabled:
        _record_event(
            kind="rollout_denied",
            tenant_key=tenant_key,
            endpoint="feed",
            reason=feed_reason,
            source=source,
            rollout_bucket=rollout_bucket,
            capabilities_version=capabilities_version,
        )
    if not thread_enabled:
        _record_event(
            kind="rollout_denied",
            tenant_key=tenant_key,
            endpoint="thread",
            reason=thread_reason,
            source=source,
            rollout_bucket=rollout_bucket,
            capabilities_version=capabilities_version,
        )


def record_mobile_v2_public_read(
    *,
    tenant_key: str,
    endpoint: str,
    reason: str,
    source: str,
    rollout_bucket: int | None,
    capabilities_version: str,
    client_capabilities_version: str | None = None,
    client_rollout_bucket: int | None = None,
    probe_label: str | None = None,
    probe_source: str | None = None,
    traffic_class: str | None = None,
    validation_session_id: str | None = None,
    target_ids: list[int] | tuple[int, ...] | None = None,
) -> None:
    _record_event(
        kind="v2_served",
        tenant_key=tenant_key,
        endpoint=endpoint,
        reason=reason,
        source=source,
        rollout_bucket=rollout_bucket,
        capabilities_version=capabilities_version,
        client_capabilities_version=client_capabilities_version,
        client_rollout_bucket=client_rollout_bucket,
        probe_label=probe_label,
        probe_source=probe_source,
        traffic_class=traffic_class,
        validation_session_id=validation_session_id,
        target_ids=target_ids,
    )


def record_mobile_v2_legacy_fallback(
    *,
    tenant_key: str,
    endpoint: str,
    reason: str,
    source: str,
    rollout_bucket: int | None,
    capabilities_version: str,
    client_capabilities_version: str | None = None,
    client_rollout_bucket: int | None = None,
    probe_label: str | None = None,
    probe_source: str | None = None,
    traffic_class: str | None = None,
    validation_session_id: str | None = None,
    target_ids: list[int] | tuple[int, ...] | None = None,
) -> None:
    _record_event(
        kind="legacy_fallbacks",
        tenant_key=tenant_key,
        endpoint=endpoint,
        reason=reason,
        source=source,
        rollout_bucket=rollout_bucket,
        capabilities_version=capabilities_version,
        client_capabilities_version=client_capabilities_version,
        client_rollout_bucket=client_rollout_bucket,
        probe_label=probe_label,
        probe_source=probe_source,
        traffic_class=traffic_class,
        validation_session_id=validation_session_id,
        target_ids=target_ids,
    )


def record_mobile_v2_probe_run(
    *,
    probe_active: bool,
    status: str,
    tenant_key: str,
    tenant_label: str | None,
    probe_source: str,
    surfaces_exercised: list[str],
    requests_v2: int,
    requests_fallback: int,
    targets_resolved: bool,
    detail: str,
) -> None:
    with _lock:
        _probe_runtime_state.clear()
        _probe_runtime_state.update(
            {
                "probe_active": bool(probe_active),
                "probe_last_run_at": _now_iso(),
                "probe_status": str(status or "").strip() or "unknown",
                "probe_tenant_key": str(tenant_key or "").strip() or None,
                "probe_tenant_label": str(tenant_label or "").strip() or None,
                "probe_source": str(probe_source or "").strip() or None,
                "probe_surfaces_exercised": list(
                    sorted({str(item).strip() for item in surfaces_exercised if str(item).strip()})
                ),
                "probe_requests_v2": int(requests_v2),
                "probe_requests_fallback": int(requests_fallback),
                "probe_targets_resolved": bool(targets_resolved),
                "probe_detail": str(detail or "").strip() or None,
            }
        )


def get_mobile_v2_probe_runtime_state() -> dict[str, Any]:
    with _lock:
        payload = dict(_probe_runtime_state)
        payload.setdefault("probe_active", False)
        payload.setdefault("probe_last_run_at", None)
        payload.setdefault("probe_status", None)
        payload.setdefault("probe_tenant_key", None)
        payload.setdefault("probe_tenant_label", None)
        payload.setdefault("probe_source", None)
        payload.setdefault("probe_surfaces_exercised", [])
        payload.setdefault("probe_requests_v2", 0)
        payload.setdefault("probe_requests_fallback", 0)
        payload.setdefault("probe_targets_resolved", False)
        payload.setdefault("probe_detail", None)
        return payload


def _build_dimension_rows(
    *,
    counter: Counter[tuple[str, str]],
    field_name: str,
    convert_value,
) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for (dimension, metric), count in counter.items():
        row = rows.setdefault(
            dimension,
            {
                field_name: convert_value(dimension),
                "capabilities_checks": 0,
                "rollout_denied": 0,
                "v2_served": 0,
                "legacy_fallbacks": 0,
            },
        )
        row[metric] += int(count)
    return sorted(
        rows.values(),
        key=lambda item: (
            -(item["v2_served"] + item["legacy_fallbacks"] + item["rollout_denied"]),
            str(item[field_name]),
        ),
    )


def get_mobile_v2_observed_tenant_keys() -> list[str]:
    with _lock:
        tenants = {
            tenant
            for (tenant, _metric) in _by_tenant.keys()
            if tenant and tenant != "unknown"
        }
    return sorted(tenants)


def get_mobile_v2_surface_metrics_snapshot(
    *,
    tenant_key: str,
    endpoint: str,
) -> dict[str, Any]:
    tenant = str(tenant_key or "").strip() or "unknown"
    endpoint_key = str(endpoint or "").strip() or "unknown"

    with _lock:
        metrics = {
            metric: int(_by_tenant_endpoint_metric.get((tenant, endpoint_key, metric), 0))
            for metric in _METRIC_NAMES
        }
        probe_metrics = {
            metric: int(_probe_by_tenant_endpoint_metric.get((tenant, endpoint_key, metric), 0))
            for metric in ("v2_served", "legacy_fallbacks")
        }
        reason_counts: dict[str, dict[str, int]] = {
            metric: {} for metric in _METRIC_NAMES
        }
        probe_reason_counts: dict[str, dict[str, int]] = {
            metric: {} for metric in ("v2_served", "legacy_fallbacks")
        }
        traffic_metrics: dict[str, dict[str, int]] = {}
        traffic_reason_counts: dict[str, dict[str, dict[str, int]]] = {}
        traffic_target_metrics: dict[str, dict[str, dict[str, int]]] = {}
        for (row_tenant, row_endpoint, reason, metric), count in _by_tenant_endpoint_reason.items():
            if row_tenant != tenant or row_endpoint != endpoint_key:
                continue
            reason_counts.setdefault(metric, {})[reason] = int(count)
        for (row_tenant, row_endpoint, reason, metric), count in _probe_by_tenant_endpoint_reason.items():
            if row_tenant != tenant or row_endpoint != endpoint_key:
                continue
            probe_reason_counts.setdefault(metric, {})[reason] = int(count)
        for (
            row_tenant,
            row_endpoint,
            traffic_class,
            metric,
        ), count in _by_tenant_endpoint_traffic_metric.items():
            if row_tenant != tenant or row_endpoint != endpoint_key:
                continue
            row = traffic_metrics.setdefault(
                traffic_class,
                {"v2_served": 0, "legacy_fallbacks": 0},
            )
            row[metric] += int(count)
        for (
            row_tenant,
            row_endpoint,
            traffic_class,
            reason,
            metric,
        ), count in _by_tenant_endpoint_traffic_reason.items():
            if row_tenant != tenant or row_endpoint != endpoint_key:
                continue
            traffic_reason_counts.setdefault(traffic_class, {}).setdefault(metric, {})[
                reason
            ] = int(count)
        for (
            row_tenant,
            row_endpoint,
            traffic_class,
            target_id,
            metric,
        ), count in _by_tenant_endpoint_traffic_target_metric.items():
            if row_tenant != tenant or row_endpoint != endpoint_key:
                continue
            traffic_target_metrics.setdefault(traffic_class, {}).setdefault(metric, {})[
                target_id
            ] = int(count)

    return {
        "tenant_key": tenant,
        "endpoint": endpoint_key,
        "metrics": metrics,
        "reason_counts": reason_counts,
        "probe_metrics": probe_metrics,
        "probe_reason_counts": probe_reason_counts,
        "traffic_metrics": traffic_metrics,
        "traffic_reason_counts": traffic_reason_counts,
        "traffic_target_metrics": traffic_target_metrics,
    }


def get_mobile_v2_rollout_operational_summary() -> dict[str, Any]:
    with _lock:
        totals = {name: int(_totals.get(name, 0)) for name in _METRIC_NAMES}
        by_tenant = _build_dimension_rows(
            counter=_by_tenant,
            field_name="tenant_key",
            convert_value=lambda value: value,
        )
        by_endpoint = _build_dimension_rows(
            counter=_by_endpoint,
            field_name="endpoint",
            convert_value=lambda value: value,
        )
        by_reason = [
            {
                "reason": reason,
                "kind": metric,
                "count": int(count),
            }
            for (reason, metric), count in sorted(
                _by_reason.items(),
                key=lambda item: (-item[1], item[0][0], item[0][1]),
            )
        ]
        by_cohort_bucket = _build_dimension_rows(
            counter=_by_bucket,
            field_name="rollout_bucket",
            convert_value=lambda value: None if value == "unknown" else int(value),
        )
        recent_events = [dict(item) for item in _recent_events]
        request_traces_recent = [dict(item) for item in _recent_request_traces]

    payload = {
        "ok": True,
        "contract_name": MOBILE_V2_PILOT_OBSERVABILITY_CONTRACT_NAME,
        "contract_version": MOBILE_V2_PILOT_OBSERVABILITY_CONTRACT_VERSION,
        "observability_enabled": mobile_v2_rollout_observability_enabled(),
        "totals": totals,
        "by_tenant": by_tenant,
        "by_endpoint": by_endpoint,
        "by_reason": by_reason,
        "by_cohort_bucket": by_cohort_bucket,
        "recent_events": recent_events,
        "request_traces_recent": request_traces_recent,
        "probe_totals": {
            "v2_served": int(_probe_totals.get("v2_served", 0)),
            "legacy_fallbacks": int(_probe_totals.get("legacy_fallbacks", 0)),
        },
    }
    payload.update(get_mobile_v2_probe_runtime_state())
    try:
        from app.v2.mobile_rollout import build_mobile_v2_rollout_governance_summary

        payload.update(
            build_mobile_v2_rollout_governance_summary(
                observed_tenant_keys=get_mobile_v2_observed_tenant_keys()
            )
        )
    except Exception:
        payload.setdefault("tenant_rollout_states", [])
        payload.setdefault("tenant_surface_states", [])
        payload.setdefault("promotion_thresholds", {})
        payload.setdefault("pilot_evaluation_thresholds", {})
        payload.setdefault("first_promoted_tenant", None)
        payload.setdefault("mobile_v2_closure_summary", None)
        payload.setdefault("mobile_v2_durable_acceptance_evidence", None)
        payload.setdefault("probe_active", False)
        payload.setdefault("probe_last_run_at", None)
        payload.setdefault("probe_requests_v2", 0)
        payload.setdefault("probe_requests_fallback", 0)
        payload.setdefault("probe_surfaces_exercised", [])
        payload.setdefault("probe_status", None)
        payload.setdefault("probe_detail", None)
        payload.setdefault("organic_validation_active", False)
        payload.setdefault("organic_validation_expired", False)
        payload.setdefault("organic_validation_started_at", None)
        payload.setdefault("organic_validation_ended_at", None)
        payload.setdefault("organic_validation_expires_at", None)
        payload.setdefault("organic_validation_window_elapsed", False)
        payload.setdefault("organic_validation_outcome", None)
        payload.setdefault("candidate_ready_for_real_tenant", False)
        payload.setdefault("organic_validation_requests_v2", 0)
        payload.setdefault("organic_validation_requests_fallback", 0)
        payload.setdefault("organic_validation_fallback_rate", 0.0)
        payload.setdefault("organic_validation_reason_breakdown", [])
        payload.setdefault("organic_validation_surface_summaries", [])
        payload.setdefault("organic_validation_surface_coverage", [])
        payload.setdefault(
            "organic_validation_distinct_targets",
            {"feed": 0, "thread": 0, "total": 0},
        )
        payload.setdefault(
            "organic_validation_missing_targets",
            {"feed": [], "thread": []},
        )
        payload.setdefault(
            "surface_coverage_summary",
            {
                "covered_surfaces": [],
                "missing_surfaces": [],
                "both_surfaces_covered": False,
            },
        )
        payload.setdefault(
            "probe_vs_organic_evidence",
            {
                "probe_ignored_for_validation": True,
                "probe_requests_v2_since_start": 0,
                "probe_requests_fallback_since_start": 0,
                "organic_requests_v2_since_start": 0,
                "organic_requests_fallback_since_start": 0,
                "evidence_source": "none",
            },
        )
        payload.setdefault("organic_validation_thresholds", {})
        payload.setdefault("organic_validation_session", None)
        payload.setdefault("operator_run_active", False)
        payload.setdefault("operator_run_id", None)
        payload.setdefault("operator_run_outcome", None)
        payload.setdefault("operator_run_reason", None)
        payload.setdefault("operator_run_started_at", None)
        payload.setdefault("operator_run_ended_at", None)
        payload.setdefault("operator_run_session_id", None)
        payload.setdefault("operator_run_progress", None)
        payload.setdefault("operator_run_instructions", [])
        payload.setdefault("required_surfaces", [])
        payload.setdefault("covered_surfaces", [])
        payload.setdefault("missing_targets", {"feed": [], "thread": []})
        payload.setdefault("human_coverage_from_operator_run", False)
        payload.setdefault("validation_session_source", "none")
    return payload


def clear_mobile_v2_rollout_metrics_for_tests() -> None:
    with _lock:
        _totals.clear()
        _by_tenant.clear()
        _by_endpoint.clear()
        _by_reason.clear()
        _by_bucket.clear()
        _by_tenant_endpoint_metric.clear()
        _by_tenant_endpoint_reason.clear()
        _by_tenant_endpoint_traffic_metric.clear()
        _by_tenant_endpoint_traffic_reason.clear()
        _by_tenant_endpoint_traffic_target_metric.clear()
        _probe_totals.clear()
        _probe_by_tenant_endpoint_metric.clear()
        _probe_by_tenant_endpoint_reason.clear()
        _probe_runtime_state.clear()
        _recent_events.clear()
        _recent_request_traces.clear()
    try:
        from app.v2.mobile_organic_validation import (
            clear_mobile_v2_organic_validation_session_for_tests,
        )

        clear_mobile_v2_organic_validation_session_for_tests()
    except Exception:
        pass
