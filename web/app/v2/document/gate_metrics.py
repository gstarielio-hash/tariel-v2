"""Observabilidade leve e local-only do soft gate documental incremental do V2."""

from __future__ import annotations

from collections import Counter, deque
from threading import Lock
from typing import Any

from app.v2.document.gate_models import DocumentSoftGateSummaryV1, DocumentSoftGateTraceV1
from app.v2.runtime import V2_DOCUMENT_SOFT_GATE_FLAG, v2_document_soft_gate_enabled

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_RECENT_TRACE_LIMIT = 60

_lock = Lock()
_totals: Counter[str] = Counter()
_by_operation_kind: Counter[tuple[str, str]] = Counter()
_by_blocker_code: Counter[tuple[str, str, str]] = Counter()
_by_tenant: Counter[tuple[str, str]] = Counter()
_recent_traces: deque[DocumentSoftGateTraceV1] = deque(maxlen=_RECENT_TRACE_LIMIT)


def document_soft_gate_observability_enabled() -> bool:
    return v2_document_soft_gate_enabled()


def _is_local_host(remote_host: str | None) -> bool:
    host = str(remote_host or "").strip().lower()
    if not host:
        return True
    return host in _LOCAL_HOSTS


def ensure_document_soft_gate_local_access(remote_host: str | None) -> None:
    if not _is_local_host(remote_host):
        raise PermissionError("Ação disponível apenas em contexto local controlado.")


def record_document_soft_gate_trace(trace: DocumentSoftGateTraceV1) -> None:
    decision = trace.decision
    operation_kind = str(trace.route_context.operation_kind or "").strip() or "unknown"
    tenant_id = str(trace.tenant_id or "").strip() or "unknown"

    with _lock:
        _totals["decisions"] += 1
        _by_operation_kind[(operation_kind, "decisions")] += 1
        _by_tenant[(tenant_id, "decisions")] += 1

        if decision.materialization_would_be_blocked:
            _totals["materialization_would_block"] += 1
            _by_operation_kind[(operation_kind, "materialization_would_block")] += 1
            _by_tenant[(tenant_id, "materialization_would_block")] += 1
        else:
            _totals["materialization_would_allow"] += 1
            _by_operation_kind[(operation_kind, "materialization_would_allow")] += 1
            _by_tenant[(tenant_id, "materialization_would_allow")] += 1

        if decision.issue_would_be_blocked:
            _totals["issue_would_block"] += 1
            _by_operation_kind[(operation_kind, "issue_would_block")] += 1
            _by_tenant[(tenant_id, "issue_would_block")] += 1
        else:
            _totals["issue_would_allow"] += 1
            _by_operation_kind[(operation_kind, "issue_would_allow")] += 1
            _by_tenant[(tenant_id, "issue_would_allow")] += 1

        for blocker in decision.blockers:
            blocker_code = str(blocker.blocker_code or "").strip() or "unknown"
            blocker_kind = str(blocker.blocker_kind or "").strip() or "unknown"
            _by_blocker_code[(blocker_code, blocker_kind, "count")] += 1
            if blocker.applies_to_materialization:
                _by_blocker_code[(blocker_code, blocker_kind, "materialization_impacts")] += 1
            if blocker.applies_to_issue:
                _by_blocker_code[(blocker_code, blocker_kind, "issue_impacts")] += 1

        _recent_traces.appendleft(trace)


def get_document_soft_gate_operational_summary() -> dict[str, Any]:
    with _lock:
        totals = dict(_totals)
        by_operation_kind = dict(_by_operation_kind)
        by_blocker_code = dict(_by_blocker_code)
        by_tenant = dict(_by_tenant)
        recent_traces = list(_recent_traces)

    summary = DocumentSoftGateSummaryV1(
        feature_flag=V2_DOCUMENT_SOFT_GATE_FLAG,
        totals={
            "decisions": int(totals.get("decisions", 0)),
            "materialization_would_block": int(totals.get("materialization_would_block", 0)),
            "materialization_would_allow": int(totals.get("materialization_would_allow", 0)),
            "issue_would_block": int(totals.get("issue_would_block", 0)),
            "issue_would_allow": int(totals.get("issue_would_allow", 0)),
        },
        by_operation_kind=[
            {
                "operation_kind": operation_kind,
                "decisions": int(by_operation_kind.get((operation_kind, "decisions"), 0)),
                "materialization_would_block": int(
                    by_operation_kind.get((operation_kind, "materialization_would_block"), 0)
                ),
                "materialization_would_allow": int(
                    by_operation_kind.get((operation_kind, "materialization_would_allow"), 0)
                ),
                "issue_would_block": int(
                    by_operation_kind.get((operation_kind, "issue_would_block"), 0)
                ),
                "issue_would_allow": int(
                    by_operation_kind.get((operation_kind, "issue_would_allow"), 0)
                ),
            }
            for operation_kind in sorted({key[0] for key in by_operation_kind})
        ],
        by_blocker_code=[
            {
                "blocker_code": blocker_code,
                "blocker_kind": blocker_kind,
                "count": int(by_blocker_code.get((blocker_code, blocker_kind, "count"), 0)),
                "materialization_impacts": int(
                    by_blocker_code.get((blocker_code, blocker_kind, "materialization_impacts"), 0)
                ),
                "issue_impacts": int(
                    by_blocker_code.get((blocker_code, blocker_kind, "issue_impacts"), 0)
                ),
            }
            for blocker_code, blocker_kind in sorted({(key[0], key[1]) for key in by_blocker_code})
        ],
        by_tenant=[
            {
                "tenant_id": tenant_id,
                "decisions": int(by_tenant.get((tenant_id, "decisions"), 0)),
                "materialization_would_block": int(
                    by_tenant.get((tenant_id, "materialization_would_block"), 0)
                ),
                "materialization_would_allow": int(
                    by_tenant.get((tenant_id, "materialization_would_allow"), 0)
                ),
                "issue_would_block": int(by_tenant.get((tenant_id, "issue_would_block"), 0)),
                "issue_would_allow": int(by_tenant.get((tenant_id, "issue_would_allow"), 0)),
            }
            for tenant_id in sorted({key[0] for key in by_tenant})
        ],
        recent_traces=recent_traces,
    )
    return summary.model_dump(mode="json")


def clear_document_soft_gate_metrics_for_tests() -> None:
    with _lock:
        _totals.clear()
        _by_operation_kind.clear()
        _by_blocker_code.clear()
        _by_tenant.clear()
        _recent_traces.clear()


__all__ = [
    "clear_document_soft_gate_metrics_for_tests",
    "document_soft_gate_observability_enabled",
    "ensure_document_soft_gate_local_access",
    "get_document_soft_gate_operational_summary",
    "record_document_soft_gate_trace",
]
