"""Observabilidade leve do hard gate documental controlado do V2."""

from __future__ import annotations

from collections import Counter, deque
from threading import Lock
from typing import Any

from app.v2.document.hard_gate import document_hard_gate_observability_flags
from app.v2.document.hard_gate_models import (
    DocumentHardGateEnforcementResultV1,
    DocumentHardGateSummaryV1,
)
from app.v2.runtime import v2_document_hard_gate_enabled

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_RECENT_RESULT_LIMIT = 60

_lock = Lock()
_totals: Counter[str] = Counter()
_by_operation_kind: Counter[tuple[str, str]] = Counter()
_by_blocker_code: Counter[tuple[str, str, str]] = Counter()
_by_tenant: Counter[tuple[str, str]] = Counter()
_recent_results: deque[DocumentHardGateEnforcementResultV1] = deque(maxlen=_RECENT_RESULT_LIMIT)


def document_hard_gate_observability_enabled() -> bool:
    return v2_document_hard_gate_enabled()


def _is_local_host(remote_host: str | None) -> bool:
    host = str(remote_host or "").strip().lower()
    if not host:
        return True
    return host in _LOCAL_HOSTS


def ensure_document_hard_gate_local_access(remote_host: str | None) -> None:
    if not _is_local_host(remote_host):
        raise PermissionError("Ação disponível apenas em contexto local controlado.")


def record_document_hard_gate_result(
    result: DocumentHardGateEnforcementResultV1,
) -> None:
    decision = result.decision
    operation_kind = str(decision.operation_kind or "").strip() or "unknown"
    tenant_id = str(decision.tenant_id or "").strip() or "unknown"

    with _lock:
        _totals["evaluations"] += 1
        _by_operation_kind[(operation_kind, "evaluations")] += 1
        _by_tenant[(tenant_id, "evaluations")] += 1

        mode_key = str(decision.mode or "disabled")
        _totals[mode_key] += 1
        _by_operation_kind[(operation_kind, mode_key)] += 1
        _by_tenant[(tenant_id, mode_key)] += 1

        if decision.would_block:
            _totals["would_block"] += 1
            _by_operation_kind[(operation_kind, "would_block")] += 1
            _by_tenant[(tenant_id, "would_block")] += 1
        else:
            _totals["would_allow"] += 1
            _by_operation_kind[(operation_kind, "would_allow")] += 1
            _by_tenant[(tenant_id, "would_allow")] += 1

        if decision.did_block:
            _totals["did_block"] += 1
            _by_operation_kind[(operation_kind, "did_block")] += 1
            _by_tenant[(tenant_id, "did_block")] += 1
        else:
            _totals["did_allow"] += 1
            _by_operation_kind[(operation_kind, "did_allow")] += 1
            _by_tenant[(tenant_id, "did_allow")] += 1

        for blocker in decision.blockers:
            blocker_code = str(blocker.blocker_code or "").strip() or "unknown"
            blocker_kind = str(blocker.blocker_kind or "").strip() or "unknown"
            _by_blocker_code[(blocker_code, blocker_kind, "count")] += 1
            scope = "enforce" if getattr(blocker, "enforce_blocking", True) else "shadow_only"
            _by_blocker_code[(blocker_code, blocker_kind, scope)] += 1
            if decision.did_block and getattr(blocker, "enforce_blocking", True):
                _by_blocker_code[(blocker_code, blocker_kind, "did_block")] += 1

        _recent_results.appendleft(result)


def get_document_hard_gate_operational_summary() -> dict[str, Any]:
    with _lock:
        totals = dict(_totals)
        by_operation_kind = dict(_by_operation_kind)
        by_blocker_code = dict(_by_blocker_code)
        by_tenant = dict(_by_tenant)
        recent_results = list(_recent_results)

    summary = DocumentHardGateSummaryV1(
        feature_flags=document_hard_gate_observability_flags(),
        totals={
            "evaluations": int(totals.get("evaluations", 0)),
            "would_block": int(totals.get("would_block", 0)),
            "would_allow": int(totals.get("would_allow", 0)),
            "did_block": int(totals.get("did_block", 0)),
            "did_allow": int(totals.get("did_allow", 0)),
            "shadow_only": int(totals.get("shadow_only", 0)),
            "enforce_controlled": int(totals.get("enforce_controlled", 0)),
            "disabled": int(totals.get("disabled", 0)),
        },
        by_operation_kind=[
            {
                "operation_kind": operation_kind,
                "evaluations": int(by_operation_kind.get((operation_kind, "evaluations"), 0)),
                "would_block": int(by_operation_kind.get((operation_kind, "would_block"), 0)),
                "would_allow": int(by_operation_kind.get((operation_kind, "would_allow"), 0)),
                "did_block": int(by_operation_kind.get((operation_kind, "did_block"), 0)),
                "did_allow": int(by_operation_kind.get((operation_kind, "did_allow"), 0)),
                "shadow_only": int(by_operation_kind.get((operation_kind, "shadow_only"), 0)),
                "enforce_controlled": int(
                    by_operation_kind.get((operation_kind, "enforce_controlled"), 0)
                ),
                "disabled": int(by_operation_kind.get((operation_kind, "disabled"), 0)),
            }
            for operation_kind in sorted({key[0] for key in by_operation_kind})
        ],
        by_blocker_code=[
            {
                "blocker_code": blocker_code,
                "blocker_kind": blocker_kind,
                "count": int(by_blocker_code.get((blocker_code, blocker_kind, "count"), 0)),
                "enforce": int(by_blocker_code.get((blocker_code, blocker_kind, "enforce"), 0)),
                "shadow_only": int(
                    by_blocker_code.get((blocker_code, blocker_kind, "shadow_only"), 0)
                ),
                "did_block": int(by_blocker_code.get((blocker_code, blocker_kind, "did_block"), 0)),
            }
            for blocker_code, blocker_kind in sorted({(key[0], key[1]) for key in by_blocker_code})
        ],
        by_tenant=[
            {
                "tenant_id": tenant_id,
                "evaluations": int(by_tenant.get((tenant_id, "evaluations"), 0)),
                "would_block": int(by_tenant.get((tenant_id, "would_block"), 0)),
                "would_allow": int(by_tenant.get((tenant_id, "would_allow"), 0)),
                "did_block": int(by_tenant.get((tenant_id, "did_block"), 0)),
                "did_allow": int(by_tenant.get((tenant_id, "did_allow"), 0)),
                "shadow_only": int(by_tenant.get((tenant_id, "shadow_only"), 0)),
                "enforce_controlled": int(by_tenant.get((tenant_id, "enforce_controlled"), 0)),
                "disabled": int(by_tenant.get((tenant_id, "disabled"), 0)),
            }
            for tenant_id in sorted({key[0] for key in by_tenant})
        ],
        recent_results=recent_results,
    )
    return summary.model_dump(mode="json")


def clear_document_hard_gate_metrics_for_tests() -> None:
    with _lock:
        _totals.clear()
        _by_operation_kind.clear()
        _by_blocker_code.clear()
        _by_tenant.clear()
        _recent_results.clear()


__all__ = [
    "clear_document_hard_gate_metrics_for_tests",
    "document_hard_gate_observability_enabled",
    "ensure_document_hard_gate_local_access",
    "get_document_hard_gate_operational_summary",
    "record_document_hard_gate_result",
]
