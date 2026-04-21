"""Observabilidade leve dos hotspots criticos do backend."""

from __future__ import annotations

import time
from collections import Counter, deque, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Iterator

from fastapi import HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from app.core.perf_support import request_perf_atual
from app.core.settings import env_bool, get_settings

BACKEND_HOTSPOT_OBSERVABILITY_FLAG = "TARIEL_BACKEND_HOTSPOT_OBSERVABILITY"
BACKEND_HOTSPOT_CONTRACT_NAME = "BackendCriticalPathObservabilityV1"
BACKEND_HOTSPOT_CONTRACT_VERSION = "v1"
_RECENT_EVENT_LIMIT = 160

_GOVERNED_DETAIL_HINTS = (
    "admin-ceo",
    "desabilitada para esta empresa",
    "desabilitado para esta empresa",
    "governan",
    "capacidade solicitada",
    "portal correto",
    "revogada",
    "revogado",
)
_INTEGRATION_MODULE_HINTS = (
    "httpx",
    "requests",
    "google",
    "openai",
    "redis",
    "urllib3",
)


@dataclass(slots=True)
class BackendHotspotObservation:
    endpoint: str
    request: Request | None = None
    surface: str | None = None
    route_path: str | None = None
    method: str | None = None
    tenant_id: int | str | None = None
    user_id: int | str | None = None
    laudo_id: int | str | None = None
    case_id: int | str | None = None
    outcome: str = "success"
    status: str | None = None
    error_class: str | None = None
    error_code: str | None = None
    response_status_code: int | None = None
    detail: dict[str, Any] = field(default_factory=dict)


_lock = Lock()
_totals: Counter[str] = Counter()
_endpoint_counts: Counter[str] = Counter()
_endpoint_status: Counter[tuple[str, str]] = Counter()
_endpoint_outcome: Counter[tuple[str, str]] = Counter()
_endpoint_total_ms: defaultdict[str, float] = defaultdict(float)
_endpoint_max_ms: defaultdict[str, float] = defaultdict(float)
_endpoint_slow_count: Counter[str] = Counter()
_endpoint_sql_total: Counter[str] = Counter()
_endpoint_sql_max: Counter[str] = Counter()
_endpoint_sql_observed: Counter[str] = Counter()
_surface_status: Counter[tuple[str, str]] = Counter()
_error_class_counts: Counter[str] = Counter()
_recent_events: deque[dict[str, Any]] = deque(maxlen=_RECENT_EVENT_LIMIT)


def backend_hotspot_observability_enabled() -> bool:
    return env_bool(BACKEND_HOTSPOT_OBSERVABILITY_FLAG, True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(value: Any, *, fallback: str = "") -> str:
    normalized = str(value or "").strip()
    return normalized or fallback


def _normalize_identifier(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _safe_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return {}
    result: dict[str, Any] = {}
    for key, value in list(detail.items())[:20]:
        text_key = str(key).strip()
        if not text_key:
            continue
        if value is None or isinstance(value, (str, int, float, bool)):
            result[text_key] = value
        elif isinstance(value, (list, tuple)):
            result[text_key] = [str(item)[:120] for item in list(value)[:8]]
        elif isinstance(value, dict):
            result[text_key] = {
                str(sub_key)[:80]: str(sub_value)[:120]
                for sub_key, sub_value in list(value.items())[:8]
            }
        else:
            result[text_key] = str(value)[:120]
    return result


def _classify_http_exception(exc: HTTPException) -> tuple[str, str]:
    status_code = int(exc.status_code or 500)
    detail = _normalize_text(getattr(exc, "detail", ""), fallback="http_exception").lower()
    if any(hint in detail for hint in _GOVERNED_DETAIL_HINTS):
        return "governed", f"http_{status_code}"
    if status_code >= 500:
        return "infra", f"http_{status_code}"
    return "business", f"http_{status_code}"


def classify_backend_exception(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, HTTPException):
        return _classify_http_exception(exc)
    if isinstance(exc, PermissionError):
        return "governed", exc.__class__.__name__
    if isinstance(exc, ValueError):
        return "business", exc.__class__.__name__
    if isinstance(exc, SQLAlchemyError):
        return "infra", exc.__class__.__name__

    module_name = _normalize_text(exc.__class__.__module__).lower()
    class_name = _normalize_text(exc.__class__.__name__, fallback="Exception")
    if any(hint in module_name for hint in _INTEGRATION_MODULE_HINTS):
        return "integration", class_name
    if any(hint in class_name.lower() for hint in ("timeout", "connection", "transport")):
        return "integration", class_name
    return "infra", class_name


def _request_attr(request: Request | None, attr_name: str) -> Any:
    state = getattr(request, "state", None)
    if state is None:
        return None
    return getattr(state, attr_name, None)


def _route_slow_ms() -> float:
    return float(get_settings().perf_route_slow_ms)


def _record_observation(
    observation: BackendHotspotObservation,
    *,
    duration_ms: float,
) -> None:
    if not backend_hotspot_observability_enabled():
        return

    perf_state = request_perf_atual()
    endpoint = _normalize_text(observation.endpoint, fallback="unknown")
    surface = _normalize_text(observation.surface, fallback="unknown")
    method = _normalize_text(
        observation.method or getattr(getattr(observation.request, "method", None), "upper", lambda: observation.method)(),
        fallback="SERVICE",
    )
    route_path = _normalize_text(
        observation.route_path or getattr(getattr(observation.request, "url", None), "path", None),
        fallback=f"service:{endpoint}",
    )
    request_id = _normalize_identifier(_request_attr(observation.request, "request_id")) or _normalize_identifier(
        getattr(perf_state, "request_id", None)
    )
    correlation_id = _normalize_identifier(_request_attr(observation.request, "correlation_id")) or _normalize_identifier(
        getattr(perf_state, "correlation_id", None)
    )
    trace_id = _normalize_identifier(_request_attr(observation.request, "trace_id"))
    status = _normalize_text(observation.status, fallback="success")
    error_class = _normalize_text(observation.error_class, fallback="")
    error_code = _normalize_text(observation.error_code, fallback="")
    sql_count = int(getattr(perf_state, "sql_count", 0) or 0) if perf_state is not None else None
    slow_sql_count = int(getattr(perf_state, "slow_sql_count", 0) or 0) if perf_state is not None else None
    rounded_duration = round(max(float(duration_ms or 0.0), 0.0), 3)
    slow = rounded_duration >= _route_slow_ms()
    detail = _safe_detail(observation.detail)

    payload = {
        "timestamp": _now_iso(),
        "endpoint": endpoint,
        "surface": surface,
        "method": method,
        "route_path": route_path,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "trace_id": trace_id,
        "tenant_id": _normalize_identifier(observation.tenant_id),
        "user_id": _normalize_identifier(observation.user_id),
        "laudo_id": _normalize_identifier(observation.laudo_id),
        "case_id": _normalize_identifier(observation.case_id),
        "outcome": _normalize_text(observation.outcome, fallback="success"),
        "status": status,
        "error_class": error_class or None,
        "error_code": error_code or None,
        "response_status_code": observation.response_status_code,
        "duration_ms": rounded_duration,
        "slow": slow,
        "sql_count": sql_count,
        "slow_sql_count": slow_sql_count,
        "detail": detail,
    }

    with _lock:
        _totals["observations"] += 1
        _totals[status] += 1
        if error_class:
            _totals[f"error_class:{error_class}"] += 1
            _error_class_counts[error_class] += 1

        _endpoint_counts[endpoint] += 1
        _endpoint_status[(endpoint, status)] += 1
        outcome = str(payload.get("outcome") or "")
        _endpoint_outcome[(endpoint, outcome)] += 1
        _endpoint_total_ms[endpoint] += rounded_duration
        _endpoint_max_ms[endpoint] = max(float(_endpoint_max_ms.get(endpoint, 0.0)), rounded_duration)
        if slow:
            _endpoint_slow_count[endpoint] += 1
        if sql_count is not None:
            _endpoint_sql_total[endpoint] += sql_count
            _endpoint_sql_observed[endpoint] += 1
            _endpoint_sql_max[endpoint] = max(int(_endpoint_sql_max.get(endpoint, 0)), sql_count)
        _surface_status[(surface, status)] += 1
        _recent_events.appendleft(payload)


@contextmanager
def observe_backend_hotspot(
    endpoint: str,
    *,
    request: Request | None = None,
    surface: str | None = None,
    route_path: str | None = None,
    method: str | None = None,
    tenant_id: int | str | None = None,
    user_id: int | str | None = None,
    laudo_id: int | str | None = None,
    case_id: int | str | None = None,
    detail: dict[str, Any] | None = None,
) -> Iterator[BackendHotspotObservation]:
    observation = BackendHotspotObservation(
        endpoint=endpoint,
        request=request,
        surface=surface,
        route_path=route_path,
        method=method,
        tenant_id=tenant_id,
        user_id=user_id,
        laudo_id=laudo_id,
        case_id=case_id,
        detail=dict(detail or {}),
    )
    if not backend_hotspot_observability_enabled():
        yield observation
        return

    started_at = time.perf_counter()
    try:
        yield observation
    except Exception as exc:
        error_class, error_code = classify_backend_exception(exc)
        observation.error_class = observation.error_class or error_class
        observation.error_code = observation.error_code or error_code
        observation.status = observation.status or ("blocked" if observation.error_class == "governed" else "error")
        if isinstance(exc, HTTPException):
            observation.response_status_code = observation.response_status_code or int(exc.status_code or 500)
        raise
    finally:
        _record_observation(
            observation,
            duration_ms=(time.perf_counter() - started_at) * 1000,
        )


def get_backend_hotspot_operational_summary() -> dict[str, Any]:
    with _lock:
        totals = dict(_totals)
        endpoint_counts = dict(_endpoint_counts)
        endpoint_status = dict(_endpoint_status)
        endpoint_outcome = dict(_endpoint_outcome)
        endpoint_total_ms = dict(_endpoint_total_ms)
        endpoint_max_ms = dict(_endpoint_max_ms)
        endpoint_slow_count = dict(_endpoint_slow_count)
        endpoint_sql_total = dict(_endpoint_sql_total)
        endpoint_sql_max = dict(_endpoint_sql_max)
        endpoint_sql_observed = dict(_endpoint_sql_observed)
        surface_status = dict(_surface_status)
        error_class_counts = dict(_error_class_counts)
        recent_events = list(_recent_events)

    endpoint_rows: list[dict[str, Any]] = []
    for endpoint in sorted(endpoint_counts):
        count = int(endpoint_counts.get(endpoint, 0))
        observed_sql_count = int(endpoint_sql_observed.get(endpoint, 0))
        avg_duration_ms = round(float(endpoint_total_ms.get(endpoint, 0.0)) / max(count, 1), 3)
        avg_sql_count = None
        if observed_sql_count > 0:
            avg_sql_count = round(float(endpoint_sql_total.get(endpoint, 0.0)) / observed_sql_count, 3)
        endpoint_rows.append(
            {
                "endpoint": endpoint,
                "count": count,
                "success": int(endpoint_status.get((endpoint, "success"), 0)),
                "blocked": int(endpoint_status.get((endpoint, "blocked"), 0)),
                "error": int(endpoint_status.get((endpoint, "error"), 0)),
                "slow_count": int(endpoint_slow_count.get(endpoint, 0)),
                "avg_duration_ms": avg_duration_ms,
                "max_duration_ms": round(float(endpoint_max_ms.get(endpoint, 0.0)), 3),
                "avg_sql_count": avg_sql_count,
                "max_sql_count": int(endpoint_sql_max.get(endpoint, 0) or 0),
                "outcomes": [
                    {
                        "outcome": outcome,
                        "count": int(endpoint_outcome.get((endpoint, outcome), 0)),
                    }
                    for outcome in sorted(
                        {
                            outcome_name
                            for endpoint_name, outcome_name in endpoint_outcome
                            if endpoint_name == endpoint
                        }
                    )
                ],
            }
        )

    top_hotspots = sorted(
        endpoint_rows,
        key=lambda row: (
            float(row.get("avg_duration_ms") or 0.0),
            float(row.get("max_duration_ms") or 0.0),
            int(row.get("count") or 0),
        ),
        reverse=True,
    )[:5]

    return {
        "contract_name": BACKEND_HOTSPOT_CONTRACT_NAME,
        "contract_version": BACKEND_HOTSPOT_CONTRACT_VERSION,
        "generated_at": _now_iso(),
        "observability_enabled": backend_hotspot_observability_enabled(),
        "totals": {
            "observations": int(totals.get("observations", 0)),
            "success": int(totals.get("success", 0)),
            "blocked": int(totals.get("blocked", 0)),
            "error": int(totals.get("error", 0)),
            "governed": int(totals.get("error_class:governed", 0)),
            "business": int(totals.get("error_class:business", 0)),
            "integration": int(totals.get("error_class:integration", 0)),
            "infra": int(totals.get("error_class:infra", 0)),
        },
        "by_endpoint": endpoint_rows,
        "top_hotspots": top_hotspots,
        "by_surface": [
            {
                "surface": surface,
                "success": int(surface_status.get((surface, "success"), 0)),
                "blocked": int(surface_status.get((surface, "blocked"), 0)),
                "error": int(surface_status.get((surface, "error"), 0)),
            }
            for surface in sorted({surface_name for surface_name, _metric in surface_status})
        ],
        "by_error_class": [
            {
                "error_class": error_class,
                "count": int(error_class_counts.get(error_class, 0)),
            }
            for error_class in sorted(error_class_counts)
        ],
        "recent_events": recent_events,
    }


def clear_backend_hotspot_metrics_for_tests() -> None:
    with _lock:
        _totals.clear()
        _endpoint_counts.clear()
        _endpoint_status.clear()
        _endpoint_outcome.clear()
        _endpoint_total_ms.clear()
        _endpoint_max_ms.clear()
        _endpoint_slow_count.clear()
        _endpoint_sql_total.clear()
        _endpoint_sql_max.clear()
        _endpoint_sql_observed.clear()
        _surface_status.clear()
        _error_class_counts.clear()
        _recent_events.clear()


__all__ = [
    "BACKEND_HOTSPOT_CONTRACT_NAME",
    "BACKEND_HOTSPOT_CONTRACT_VERSION",
    "backend_hotspot_observability_enabled",
    "BackendHotspotObservation",
    "classify_backend_exception",
    "clear_backend_hotspot_metrics_for_tests",
    "get_backend_hotspot_operational_summary",
    "observe_backend_hotspot",
]
