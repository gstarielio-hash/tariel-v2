"""Observabilidade leve do rollout de report packs semanticos."""

from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.core.settings import env_bool

REPORT_PACK_ROLLOUT_OBSERVABILITY_FLAG = "TARIEL_V2_REPORT_PACK_ROLLOUT_OBSERVABILITY"
REPORT_PACK_ROLLOUT_CONTRACT_NAME = "ReportPackRolloutObservabilityV1"
REPORT_PACK_ROLLOUT_CONTRACT_VERSION = "v1"
_RECENT_EVENT_LIMIT = 120

_lock = Lock()
_totals: Counter[str] = Counter()
_by_template_mode: Counter[tuple[str, str, str]] = Counter()
_by_family_mode: Counter[tuple[str, str, str]] = Counter()
_by_preference_effective: Counter[tuple[str, str]] = Counter()
_by_tenant_metric: Counter[tuple[str, str]] = Counter()
_recent_events: deque[dict[str, Any]] = deque(maxlen=_RECENT_EVENT_LIMIT)


def report_pack_rollout_observability_enabled() -> bool:
    return env_bool(REPORT_PACK_ROLLOUT_OBSERVABILITY_FLAG, True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(value: Any, *, fallback: str = "unknown") -> str:
    normalized = str(value or "").strip()
    return normalized or fallback


def _quality_gates(draft: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(draft, dict):
        return {}
    quality_gates = draft.get("quality_gates")
    return quality_gates if isinstance(quality_gates, dict) else {}


def _telemetry(draft: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(draft, dict):
        return {}
    telemetry = draft.get("telemetry")
    return telemetry if isinstance(telemetry, dict) else {}


def _collect_normative_leafs(payload: dict[str, Any] | None) -> dict[str, str]:
    result: dict[str, str] = {}

    def _walk(value: Any, path: tuple[str, ...]) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                _walk(value[key], (*path, str(key)))
            return
        if isinstance(value, list):
            return
        if not path:
            return
        field_name = path[-1]
        if field_name not in {"condicao", "status"}:
            return
        result[".".join(path)] = _normalize_text(value, fallback="")

    _walk(payload or {}, ())
    return result


def _compute_divergence(laudo: Any, draft: dict[str, Any] | None) -> dict[str, Any]:
    candidate = draft.get("structured_data_candidate") if isinstance(draft, dict) else None
    actual = getattr(laudo, "dados_formulario", None)
    if not isinstance(candidate, dict) or not isinstance(actual, dict):
        return {
            "comparable": False,
            "comparable_fields": 0,
            "divergent_fields": 0,
            "divergent_paths": [],
        }

    candidate_leafs = _collect_normative_leafs(candidate)
    actual_leafs = _collect_normative_leafs(actual)
    comparable_paths = sorted(set(candidate_leafs) & set(actual_leafs))
    divergent_paths = [
        path
        for path in comparable_paths
        if candidate_leafs.get(path) != actual_leafs.get(path)
    ]
    return {
        "comparable": bool(comparable_paths),
        "comparable_fields": len(comparable_paths),
        "divergent_fields": len(divergent_paths),
        "divergent_paths": divergent_paths[:24],
    }


def _context(
    *,
    laudo: Any,
    draft: dict[str, Any] | None,
) -> dict[str, Any]:
    quality_gates = _quality_gates(draft)
    telemetry = _telemetry(draft)
    preference = _normalize_text(
        telemetry.get("entry_mode_preference") or getattr(laudo, "entry_mode_preference", None),
    )
    effective = _normalize_text(
        telemetry.get("entry_mode_effective") or getattr(laudo, "entry_mode_effective", None),
    )
    family = _normalize_text((draft or {}).get("family"))
    template_key = _normalize_text(
        (draft or {}).get("template_key") or getattr(laudo, "tipo_template", None),
    )
    missing_evidence = list(quality_gates.get("missing_evidence") or [])
    divergence = _compute_divergence(laudo, draft)
    return {
        "tenant_id": _normalize_text(getattr(laudo, "empresa_id", None)),
        "laudo_id": int(getattr(laudo, "id", 0) or 0),
        "template_key": template_key,
        "family": family,
        "entry_mode_preference": preference,
        "entry_mode_effective": effective,
        "mode_switch_observed": preference != effective,
        "missing_evidence_count": len(missing_evidence),
        "autonomy_ready": bool(quality_gates.get("autonomy_ready")),
        "final_validation_mode": _normalize_text(
            quality_gates.get("final_validation_mode") or "mesa_required",
        ),
        "max_conflict_score": int(quality_gates.get("max_conflict_score") or 0),
        "divergence": divergence,
    }


def _bump_metric(metric: str, context: dict[str, Any], amount: int = 1) -> None:
    _totals[metric] += int(amount)
    _by_tenant_metric[(context["tenant_id"], metric)] += int(amount)
    _by_template_mode[(context["template_key"], context["entry_mode_effective"], metric)] += int(amount)
    _by_family_mode[(context["family"], context["entry_mode_effective"], metric)] += int(amount)


def _record_event(kind: str, *, context: dict[str, Any], payload: dict[str, Any] | None = None) -> None:
    event = {
        "timestamp": _now_iso(),
        "kind": kind,
        "tenant_id": context["tenant_id"],
        "laudo_id": context["laudo_id"],
        "template_key": context["template_key"],
        "family": context["family"],
        "entry_mode_preference": context["entry_mode_preference"],
        "entry_mode_effective": context["entry_mode_effective"],
        "mode_switch_observed": context["mode_switch_observed"],
        "missing_evidence_count": context["missing_evidence_count"],
        "autonomy_ready": context["autonomy_ready"],
        "final_validation_mode": context["final_validation_mode"],
        "max_conflict_score": context["max_conflict_score"],
        "divergent_fields": context["divergence"]["divergent_fields"],
    }
    if payload:
        event.update(payload)
    _recent_events.appendleft(event)


def record_report_pack_gate_observation(
    *,
    laudo: Any,
    report_pack_draft: dict[str, Any] | None,
    approved: bool,
    review_mode_sugerido: str,
) -> None:
    if not report_pack_rollout_observability_enabled():
        return

    context = _context(laudo=laudo, draft=report_pack_draft)
    with _lock:
        _by_preference_effective[(context["entry_mode_preference"], context["entry_mode_effective"])] += 1
        _bump_metric("gate_checks", context)
        _bump_metric("gate_approved" if approved else "gate_blocked", context)
        _bump_metric("missing_evidence_total", context, context["missing_evidence_count"])
        if context["mode_switch_observed"]:
            _bump_metric("mode_switches", context)
        if str(review_mode_sugerido or "").strip().lower() == "mobile_autonomous":
            _bump_metric("gate_suggested_mobile_autonomous", context)
        else:
            _bump_metric("gate_suggested_mesa_required", context)
        _record_event(
            "gate_observation",
            context=context,
            payload={
                "approved": bool(approved),
                "review_mode_sugerido": _normalize_text(review_mode_sugerido, fallback="mesa_required"),
            },
        )


def record_report_pack_finalization_observation(
    *,
    laudo: Any,
    report_pack_draft: dict[str, Any] | None,
    final_validation_mode: str,
    status_revisao: str,
) -> None:
    if not report_pack_rollout_observability_enabled():
        return

    context = _context(laudo=laudo, draft=report_pack_draft)
    divergence = context["divergence"]
    with _lock:
        _by_preference_effective[(context["entry_mode_preference"], context["entry_mode_effective"])] += 1
        _bump_metric("finalizations", context)
        if str(final_validation_mode or "").strip().lower() == "mobile_autonomous":
            _bump_metric("auto_approved", context)
        else:
            _bump_metric("routed_to_mesa", context)
        if divergence["divergent_fields"] > 0:
            _bump_metric("divergence_events", context)
            _bump_metric("divergence_fields_total", context, divergence["divergent_fields"])
        _record_event(
            "finalization_observation",
            context=context,
            payload={
                "status_revisao": _normalize_text(status_revisao),
                "final_validation_mode": _normalize_text(final_validation_mode, fallback="mesa_required"),
                "divergent_paths": divergence["divergent_paths"],
            },
        )


def record_report_pack_review_decision(
    *,
    laudo: Any,
    action: str,
    status_revisao: str,
) -> None:
    if not report_pack_rollout_observability_enabled():
        return

    report_pack_draft = getattr(laudo, "report_pack_draft_json", None)
    context = _context(laudo=laudo, draft=report_pack_draft)
    divergence = context["divergence"]
    action_key = _normalize_text(action)
    with _lock:
        _by_preference_effective[(context["entry_mode_preference"], context["entry_mode_effective"])] += 1
        _bump_metric("review_decisions", context)
        if action_key == "aprovar":
            _bump_metric("review_approved", context)
        elif action_key == "rejeitar":
            _bump_metric("review_rejected", context)
        if divergence["divergent_fields"] > 0:
            _bump_metric("divergence_events", context)
            _bump_metric("divergence_fields_total", context, divergence["divergent_fields"])
        _record_event(
            "review_decision",
            context=context,
            payload={
                "action": action_key,
                "status_revisao": _normalize_text(status_revisao),
                "divergent_paths": divergence["divergent_paths"],
            },
        )


def get_report_pack_rollout_operational_summary() -> dict[str, Any]:
    with _lock:
        totals = dict(_totals)
        by_template_mode = dict(_by_template_mode)
        by_family_mode = dict(_by_family_mode)
        by_preference_effective = dict(_by_preference_effective)
        by_tenant_metric = dict(_by_tenant_metric)
        recent_events = list(_recent_events)

    template_mode_keys = sorted({(key[0], key[1]) for key in by_template_mode})
    family_mode_keys = sorted({(key[0], key[1]) for key in by_family_mode})
    preference_effective_keys = sorted(by_preference_effective)
    tenant_keys = sorted({key[0] for key in by_tenant_metric})

    return {
        "contract_name": REPORT_PACK_ROLLOUT_CONTRACT_NAME,
        "contract_version": REPORT_PACK_ROLLOUT_CONTRACT_VERSION,
        "observability_enabled": report_pack_rollout_observability_enabled(),
        "totals": {
            "gate_checks": int(totals.get("gate_checks", 0)),
            "gate_approved": int(totals.get("gate_approved", 0)),
            "gate_blocked": int(totals.get("gate_blocked", 0)),
            "finalizations": int(totals.get("finalizations", 0)),
            "auto_approved": int(totals.get("auto_approved", 0)),
            "routed_to_mesa": int(totals.get("routed_to_mesa", 0)),
            "review_decisions": int(totals.get("review_decisions", 0)),
            "review_approved": int(totals.get("review_approved", 0)),
            "review_rejected": int(totals.get("review_rejected", 0)),
            "mode_switches": int(totals.get("mode_switches", 0)),
            "missing_evidence_total": int(totals.get("missing_evidence_total", 0)),
            "divergence_events": int(totals.get("divergence_events", 0)),
            "divergence_fields_total": int(totals.get("divergence_fields_total", 0)),
        },
        "by_template_mode": [
            {
                "template_key": template_key,
                "entry_mode_effective": entry_mode_effective,
                "gate_checks": int(by_template_mode.get((template_key, entry_mode_effective, "gate_checks"), 0)),
                "gate_approved": int(by_template_mode.get((template_key, entry_mode_effective, "gate_approved"), 0)),
                "gate_blocked": int(by_template_mode.get((template_key, entry_mode_effective, "gate_blocked"), 0)),
                "finalizations": int(by_template_mode.get((template_key, entry_mode_effective, "finalizations"), 0)),
                "auto_approved": int(by_template_mode.get((template_key, entry_mode_effective, "auto_approved"), 0)),
                "routed_to_mesa": int(by_template_mode.get((template_key, entry_mode_effective, "routed_to_mesa"), 0)),
                "review_decisions": int(by_template_mode.get((template_key, entry_mode_effective, "review_decisions"), 0)),
                "review_approved": int(by_template_mode.get((template_key, entry_mode_effective, "review_approved"), 0)),
                "review_rejected": int(by_template_mode.get((template_key, entry_mode_effective, "review_rejected"), 0)),
                "mode_switches": int(by_template_mode.get((template_key, entry_mode_effective, "mode_switches"), 0)),
                "missing_evidence_total": int(by_template_mode.get((template_key, entry_mode_effective, "missing_evidence_total"), 0)),
                "divergence_events": int(by_template_mode.get((template_key, entry_mode_effective, "divergence_events"), 0)),
                "divergence_fields_total": int(by_template_mode.get((template_key, entry_mode_effective, "divergence_fields_total"), 0)),
            }
            for template_key, entry_mode_effective in template_mode_keys
        ],
        "by_family_mode": [
            {
                "family": family,
                "entry_mode_effective": entry_mode_effective,
                "gate_checks": int(by_family_mode.get((family, entry_mode_effective, "gate_checks"), 0)),
                "gate_approved": int(by_family_mode.get((family, entry_mode_effective, "gate_approved"), 0)),
                "gate_blocked": int(by_family_mode.get((family, entry_mode_effective, "gate_blocked"), 0)),
                "finalizations": int(by_family_mode.get((family, entry_mode_effective, "finalizations"), 0)),
                "auto_approved": int(by_family_mode.get((family, entry_mode_effective, "auto_approved"), 0)),
                "routed_to_mesa": int(by_family_mode.get((family, entry_mode_effective, "routed_to_mesa"), 0)),
                "review_decisions": int(by_family_mode.get((family, entry_mode_effective, "review_decisions"), 0)),
                "review_approved": int(by_family_mode.get((family, entry_mode_effective, "review_approved"), 0)),
                "review_rejected": int(by_family_mode.get((family, entry_mode_effective, "review_rejected"), 0)),
                "mode_switches": int(by_family_mode.get((family, entry_mode_effective, "mode_switches"), 0)),
                "missing_evidence_total": int(by_family_mode.get((family, entry_mode_effective, "missing_evidence_total"), 0)),
                "divergence_events": int(by_family_mode.get((family, entry_mode_effective, "divergence_events"), 0)),
                "divergence_fields_total": int(by_family_mode.get((family, entry_mode_effective, "divergence_fields_total"), 0)),
            }
            for family, entry_mode_effective in family_mode_keys
        ],
        "by_preference_effective": [
            {
                "entry_mode_preference": preference,
                "entry_mode_effective": effective,
                "count": int(by_preference_effective.get((preference, effective), 0)),
            }
            for preference, effective in preference_effective_keys
        ],
        "by_tenant": [
            {
                "tenant_id": tenant_id,
                "gate_checks": int(by_tenant_metric.get((tenant_id, "gate_checks"), 0)),
                "finalizations": int(by_tenant_metric.get((tenant_id, "finalizations"), 0)),
                "auto_approved": int(by_tenant_metric.get((tenant_id, "auto_approved"), 0)),
                "routed_to_mesa": int(by_tenant_metric.get((tenant_id, "routed_to_mesa"), 0)),
                "review_decisions": int(by_tenant_metric.get((tenant_id, "review_decisions"), 0)),
                "divergence_events": int(by_tenant_metric.get((tenant_id, "divergence_events"), 0)),
            }
            for tenant_id in tenant_keys
        ],
        "recent_events": recent_events,
    }


def clear_report_pack_rollout_metrics_for_tests() -> None:
    with _lock:
        _totals.clear()
        _by_template_mode.clear()
        _by_family_mode.clear()
        _by_preference_effective.clear()
        _by_tenant_metric.clear()
        _recent_events.clear()


__all__ = [
    "REPORT_PACK_ROLLOUT_CONTRACT_NAME",
    "REPORT_PACK_ROLLOUT_CONTRACT_VERSION",
    "REPORT_PACK_ROLLOUT_OBSERVABILITY_FLAG",
    "clear_report_pack_rollout_metrics_for_tests",
    "get_report_pack_rollout_operational_summary",
    "record_report_pack_finalization_observation",
    "record_report_pack_gate_observation",
    "record_report_pack_review_decision",
    "report_pack_rollout_observability_enabled",
]
