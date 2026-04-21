"""Trilha duravel local-only para evidencias do hard gate documental."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.settings import env_bool, env_str
from app.v2.document.hard_gate import document_hard_gate_observability_flags
from app.v2.document.hard_gate_metrics import ensure_document_hard_gate_local_access
from app.v2.document.hard_gate_models import DocumentHardGateEnforcementResultV1

_DURABLE_EVIDENCE_FLAG = "TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE"
_DURABLE_EVIDENCE_DIR_FLAG = "TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR"
_DEFAULT_EVIDENCE_ROOT = Path(__file__).resolve().parents[4] / "artifacts" / "document_hard_gate_shadow_evidence"
_RECENT_ENTRY_LIMIT = 20
_index_lock = Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_local_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _normalize_token(value: Any, *, fallback: str = "na") -> str:
    normalized = re.sub(r"[^a-z0-9._-]+", "_", str(value or "").strip().lower()).strip("._-")
    return normalized or fallback


def document_hard_gate_durable_evidence_enabled() -> bool:
    configured_dir = str(env_str(_DURABLE_EVIDENCE_DIR_FLAG, "") or "").strip()
    return bool(configured_dir) or env_bool(_DURABLE_EVIDENCE_FLAG, False)


def get_document_hard_gate_durable_evidence_root() -> Path | None:
    configured_dir = str(env_str(_DURABLE_EVIDENCE_DIR_FLAG, "") or "").strip()
    if configured_dir:
        return Path(configured_dir).expanduser()
    if env_bool(_DURABLE_EVIDENCE_FLAG, False):
        return _DEFAULT_EVIDENCE_ROOT
    return None


def _build_durable_entry(
    result: DocumentHardGateEnforcementResultV1,
    *,
    observation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = result.decision.model_dump(mode="json")
    context = dict(observation_context or {})
    route_context = {
        "route_name": decision.get("route_name"),
        "route_path": decision.get("route_path"),
        "source_channel": decision.get("source_channel"),
        "legacy_pipeline_name": decision.get("legacy_pipeline_name"),
    }
    correlation = {
        "correlation_id": decision.get("correlation_id"),
        "request_id": decision.get("request_id"),
    }
    response = context.get("response") if isinstance(context.get("response"), dict) else {}
    target = context.get("target") if isinstance(context.get("target"), dict) else {}
    source_context = context.get("source_context") if isinstance(context.get("source_context"), dict) else {}

    return {
        "contract_name": "DocumentHardGateDurableEvidenceEntryV1",
        "contract_version": "v1",
        "recorded_at": _utc_now_iso(),
        "timestamp": decision.get("timestamp"),
        "operation_kind": decision.get("operation_kind"),
        "tenant_id": decision.get("tenant_id"),
        "case_id": decision.get("case_id"),
        "legacy_laudo_id": decision.get("legacy_laudo_id"),
        "document_id": decision.get("document_id"),
        "route_context": route_context,
        "correlation": correlation,
        "source_context": source_context,
        "target": target,
        "response": response,
        "functional_outcome": str(context.get("functional_outcome") or "unknown"),
        "would_block": bool(decision.get("would_block")),
        "did_block": bool(decision.get("did_block")),
        "shadow_only": bool(decision.get("shadow_only")),
        "enforce_enabled": bool(decision.get("enforce_enabled")),
        "mode": str(decision.get("mode") or "disabled"),
        "blockers": list(decision.get("blockers") or []),
        "decision_sources": list(decision.get("decision_source") or []),
        "hard_gate_result": result.model_dump(mode="json"),
    }


def record_document_hard_gate_durable_evidence(
    result: DocumentHardGateEnforcementResultV1,
    *,
    observation_context: dict[str, Any] | None = None,
    remote_host: str | None = None,
) -> str | None:
    root = get_document_hard_gate_durable_evidence_root()
    if root is None:
        return None

    ensure_document_hard_gate_local_access(remote_host)
    entry = _build_durable_entry(
        result,
        observation_context=observation_context,
    )
    operation_kind = _normalize_token(entry.get("operation_kind"), fallback="unknown_operation")
    correlation = entry.get("correlation") or {}
    correlation_id = _normalize_token(
        correlation.get("correlation_id") or correlation.get("request_id"),
        fallback="no_correlation",
    )
    tenant_id = _normalize_token(entry.get("tenant_id"), fallback="unknown_tenant")
    laudo_id = _normalize_token(entry.get("legacy_laudo_id"), fallback="no_laudo")

    execution_dir = _ensure_dir(root / "executions" / operation_kind)
    artifact_path = execution_dir / (
        f"{_now_local_slug()}__tenant_{tenant_id}__laudo_{laudo_id}__corr_{correlation_id}.json"
    )

    index_entry = {
        **entry,
        "artifact_path": str(artifact_path),
    }
    _write_json(artifact_path, index_entry)

    index_path = _ensure_dir(root).joinpath("index.jsonl")
    with _index_lock:
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(index_entry, ensure_ascii=False, sort_keys=True) + "\n")

    return str(artifact_path)


def load_document_hard_gate_durable_entries(
    *,
    root: str | Path | None = None,
    operation_kind: str | None = None,
) -> list[dict[str, Any]]:
    evidence_root = Path(root).expanduser() if root else get_document_hard_gate_durable_evidence_root()
    if evidence_root is None:
        return []

    index_path = evidence_root / "index.jsonl"
    if not index_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for raw_line in index_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if operation_kind and str(entry.get("operation_kind") or "").strip() != operation_kind:
            continue
        entries.append(entry)

    entries.sort(
        key=lambda item: str(item.get("recorded_at") or item.get("timestamp") or ""),
        reverse=True,
    )
    return entries


def get_document_hard_gate_durable_summary(
    *,
    root: str | Path | None = None,
    operation_kind: str | None = None,
) -> dict[str, Any]:
    evidence_root = Path(root).expanduser() if root else get_document_hard_gate_durable_evidence_root()
    entries = load_document_hard_gate_durable_entries(
        root=evidence_root,
        operation_kind=operation_kind,
    )

    totals: Counter[str] = Counter()
    by_operation_kind: Counter[tuple[str, str]] = Counter()
    by_blocker_code: Counter[tuple[str, str, str]] = Counter()
    by_tenant: Counter[tuple[str, str]] = Counter()

    for entry in entries:
        operation = str(entry.get("operation_kind") or "").strip() or "unknown"
        tenant_id = str(entry.get("tenant_id") or "").strip() or "unknown"
        mode = str(entry.get("mode") or "disabled")

        totals["evaluations"] += 1
        totals[mode] += 1
        by_operation_kind[(operation, "evaluations")] += 1
        by_operation_kind[(operation, mode)] += 1
        by_tenant[(tenant_id, "evaluations")] += 1
        by_tenant[(tenant_id, mode)] += 1

        if bool(entry.get("would_block")):
            totals["would_block"] += 1
            by_operation_kind[(operation, "would_block")] += 1
            by_tenant[(tenant_id, "would_block")] += 1
        else:
            totals["would_allow"] += 1
            by_operation_kind[(operation, "would_allow")] += 1
            by_tenant[(tenant_id, "would_allow")] += 1

        if bool(entry.get("did_block")):
            totals["did_block"] += 1
            by_operation_kind[(operation, "did_block")] += 1
            by_tenant[(tenant_id, "did_block")] += 1
        else:
            totals["did_allow"] += 1
            by_operation_kind[(operation, "did_allow")] += 1
            by_tenant[(tenant_id, "did_allow")] += 1

        for blocker in list(entry.get("blockers") or []):
            blocker_code = str(blocker.get("blocker_code") or "").strip() or "unknown"
            blocker_kind = str(blocker.get("blocker_kind") or "").strip() or "unknown"
            by_blocker_code[(blocker_code, blocker_kind, "count")] += 1
            scope = "enforce" if bool(blocker.get("enforce_blocking", True)) else "shadow_only"
            by_blocker_code[(blocker_code, blocker_kind, scope)] += 1
            if bool(entry.get("did_block")) and bool(blocker.get("enforce_blocking", True)):
                by_blocker_code[(blocker_code, blocker_kind, "did_block")] += 1

    return {
        "contract_name": "DocumentHardGateDurableSummaryV1",
        "contract_version": "v1",
        "durable_evidence_enabled": document_hard_gate_durable_evidence_enabled(),
        "durable_evidence_root": str(evidence_root) if evidence_root else None,
        "feature_flags": document_hard_gate_observability_flags(),
        "totals": {
            "evaluations": int(totals.get("evaluations", 0)),
            "would_block": int(totals.get("would_block", 0)),
            "would_allow": int(totals.get("would_allow", 0)),
            "did_block": int(totals.get("did_block", 0)),
            "did_allow": int(totals.get("did_allow", 0)),
            "shadow_only": int(totals.get("shadow_only", 0)),
            "enforce_controlled": int(totals.get("enforce_controlled", 0)),
            "disabled": int(totals.get("disabled", 0)),
        },
        "by_operation_kind": [
            {
                "operation_kind": current_operation,
                "evaluations": int(by_operation_kind.get((current_operation, "evaluations"), 0)),
                "would_block": int(by_operation_kind.get((current_operation, "would_block"), 0)),
                "would_allow": int(by_operation_kind.get((current_operation, "would_allow"), 0)),
                "did_block": int(by_operation_kind.get((current_operation, "did_block"), 0)),
                "did_allow": int(by_operation_kind.get((current_operation, "did_allow"), 0)),
                "shadow_only": int(by_operation_kind.get((current_operation, "shadow_only"), 0)),
                "enforce_controlled": int(
                    by_operation_kind.get((current_operation, "enforce_controlled"), 0)
                ),
                "disabled": int(by_operation_kind.get((current_operation, "disabled"), 0)),
            }
            for current_operation in sorted({key[0] for key in by_operation_kind})
        ],
        "by_blocker_code": [
            {
                "blocker_code": blocker_code,
                "blocker_kind": blocker_kind,
                "count": int(by_blocker_code.get((blocker_code, blocker_kind, "count"), 0)),
                "enforce": int(by_blocker_code.get((blocker_code, blocker_kind, "enforce"), 0)),
                "shadow_only": int(by_blocker_code.get((blocker_code, blocker_kind, "shadow_only"), 0)),
                "did_block": int(by_blocker_code.get((blocker_code, blocker_kind, "did_block"), 0)),
            }
            for blocker_code, blocker_kind in sorted({(key[0], key[1]) for key in by_blocker_code})
        ],
        "by_tenant": [
            {
                "tenant_id": current_tenant,
                "evaluations": int(by_tenant.get((current_tenant, "evaluations"), 0)),
                "would_block": int(by_tenant.get((current_tenant, "would_block"), 0)),
                "would_allow": int(by_tenant.get((current_tenant, "would_allow"), 0)),
                "did_block": int(by_tenant.get((current_tenant, "did_block"), 0)),
                "did_allow": int(by_tenant.get((current_tenant, "did_allow"), 0)),
                "shadow_only": int(by_tenant.get((current_tenant, "shadow_only"), 0)),
                "enforce_controlled": int(by_tenant.get((current_tenant, "enforce_controlled"), 0)),
                "disabled": int(by_tenant.get((current_tenant, "disabled"), 0)),
            }
            for current_tenant in sorted({key[0] for key in by_tenant})
        ],
        "recent_entries": entries[:_RECENT_ENTRY_LIMIT],
        "generated_at": _utc_now_iso(),
    }


def export_document_hard_gate_durable_snapshot(
    destination_dir: str | Path,
    *,
    operation_kind: str | None = None,
) -> dict[str, str]:
    destination = _ensure_dir(Path(destination_dir).expanduser())
    entries = load_document_hard_gate_durable_entries(operation_kind=operation_kind)
    summary = get_document_hard_gate_durable_summary(operation_kind=operation_kind)

    summary_path = destination / "durable_summary.json"
    entries_path = destination / "durable_entries.json"
    _write_json(summary_path, summary)
    _write_json(entries_path, entries)

    return {
        "summary_path": str(summary_path),
        "entries_path": str(entries_path),
    }


def clear_document_hard_gate_durable_evidence_for_tests(
    *,
    root: str | Path | None = None,
) -> None:
    evidence_root = Path(root).expanduser() if root else get_document_hard_gate_durable_evidence_root()
    if evidence_root is not None and evidence_root.exists():
        shutil.rmtree(evidence_root)


__all__ = [
    "clear_document_hard_gate_durable_evidence_for_tests",
    "document_hard_gate_durable_evidence_enabled",
    "export_document_hard_gate_durable_snapshot",
    "get_document_hard_gate_durable_evidence_root",
    "get_document_hard_gate_durable_summary",
    "load_document_hard_gate_durable_entries",
    "record_document_hard_gate_durable_evidence",
]
