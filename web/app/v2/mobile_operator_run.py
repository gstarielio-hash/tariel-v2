"""Run operacional controlado para validacao humana do mobile V2."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.settings import env_int, env_str
from app.shared.database import Empresa
from app.v2.mobile_organic_validation import (
    V2_ANDROID_PILOT_TENANT_KEY_FLAG,
    get_mobile_v2_organic_validation_session,
    get_mobile_v2_organic_validation_summary,
    list_mobile_v2_organic_human_checkpoints,
    resolve_demo_mobile_organic_validation_targets,
    start_mobile_v2_organic_validation_session,
    stop_mobile_v2_organic_validation_session,
)

import app.shared.database as banco_dados

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_SURFACES = ("feed", "thread")
_OUTCOMES = frozenset(
    {
        "blocked_no_targets",
        "in_progress",
        "completed_successfully",
        "completed_with_fallback",
        "completed_inconclusive",
        "aborted",
    }
)

_lock = Lock()
_operator_run_state: "MobileOperatorValidationRun | None" = None


@dataclass(frozen=True, slots=True)
class MobileOperatorValidationTarget:
    surface: str
    target_id: int
    instruction: str
    covered_in_validation: bool = False
    human_confirmed: bool = False
    completed: bool = False

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "target_id": self.target_id,
            "instruction": self.instruction,
            "covered_in_validation": self.covered_in_validation,
            "human_confirmed": self.human_confirmed,
            "completed": self.completed,
        }


@dataclass(frozen=True, slots=True)
class MobileOperatorValidationRun:
    tenant_key: str
    tenant_label: str | None
    session_id: str | None
    operator_run_id: str
    started_at: str
    ended_at: str | None
    active: bool
    required_surfaces: tuple[str, ...]
    required_targets: tuple[MobileOperatorValidationTarget, ...]
    outcome: str | None
    outcome_reason: str | None
    trigger_source: str
    finish_source: str | None

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "tenant_key": self.tenant_key,
            "tenant_label": self.tenant_label,
            "session_id": self.session_id,
            "operator_run_id": self.operator_run_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "active": self.active,
            "required_surfaces": list(self.required_surfaces),
            "required_targets": [
                item.to_public_payload() for item in self.required_targets
            ],
            "outcome": self.outcome,
            "outcome_reason": self.outcome_reason,
            "trigger_source": self.trigger_source,
            "finish_source": self.finish_source,
        }


@dataclass(frozen=True, slots=True)
class MobileOperatorValidationProgress:
    feed_completed: bool
    thread_completed: bool
    human_confirmed_minimum_met: bool
    fallback_observed: bool
    fallback_excessive: bool
    critical_issue_detected: bool
    required_surfaces: tuple[str, ...]
    covered_surfaces: tuple[str, ...]
    missing_surfaces: tuple[str, ...]
    covered_targets: dict[str, tuple[int, ...]]
    human_confirmed_targets: dict[str, tuple[int, ...]]
    missing_targets: dict[str, tuple[int, ...]]
    targets: tuple[MobileOperatorValidationTarget, ...]
    target_count_required: int
    target_count_completed: int
    organic_validation_outcome: str | None
    organic_validation_window_elapsed: bool
    human_coverage_from_operator_run: bool

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "feed_completed": self.feed_completed,
            "thread_completed": self.thread_completed,
            "human_confirmed_minimum_met": self.human_confirmed_minimum_met,
            "fallback_observed": self.fallback_observed,
            "fallback_excessive": self.fallback_excessive,
            "critical_issue_detected": self.critical_issue_detected,
            "required_surfaces": list(self.required_surfaces),
            "covered_surfaces": list(self.covered_surfaces),
            "missing_surfaces": list(self.missing_surfaces),
            "covered_targets": {
                surface: list(target_ids)
                for surface, target_ids in self.covered_targets.items()
            },
            "human_confirmed_targets": {
                surface: list(target_ids)
                for surface, target_ids in self.human_confirmed_targets.items()
            },
            "missing_targets": {
                surface: list(target_ids)
                for surface, target_ids in self.missing_targets.items()
            },
            "targets": [item.to_public_payload() for item in self.targets],
            "target_count_required": self.target_count_required,
            "target_count_completed": self.target_count_completed,
            "organic_validation_outcome": self.organic_validation_outcome,
            "organic_validation_window_elapsed": (
                self.organic_validation_window_elapsed
            ),
            "human_coverage_from_operator_run": self.human_coverage_from_operator_run,
        }


@dataclass(frozen=True, slots=True)
class MobileOperatorValidationStatus:
    run: MobileOperatorValidationRun | None
    progress: MobileOperatorValidationProgress | None
    operator_run_active: bool
    operator_run_id: str | None
    operator_run_outcome: str | None
    operator_run_reason: str | None
    operator_run_started_at: str | None
    operator_run_ended_at: str | None
    operator_run_session_id: str | None
    tenant_key: str | None
    tenant_label: str | None
    required_surfaces: tuple[str, ...]
    covered_surfaces: tuple[str, ...]
    missing_targets: dict[str, tuple[int, ...]]
    operator_run_instructions: tuple[str, ...]
    human_coverage_from_operator_run: bool
    validation_session_source: str

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "operator_run_active": self.operator_run_active,
            "operator_run_id": self.operator_run_id,
            "operator_run_outcome": self.operator_run_outcome,
            "operator_run_reason": self.operator_run_reason,
            "operator_run_started_at": self.operator_run_started_at,
            "operator_run_ended_at": self.operator_run_ended_at,
            "operator_run_session_id": self.operator_run_session_id,
            "operator_run_progress": (
                self.progress.to_public_payload() if self.progress is not None else None
            ),
            "required_surfaces": list(self.required_surfaces),
            "covered_surfaces": list(self.covered_surfaces),
            "missing_targets": {
                surface: list(target_ids)
                for surface, target_ids in self.missing_targets.items()
            },
            "operator_run_instructions": list(self.operator_run_instructions),
            "human_coverage_from_operator_run": self.human_coverage_from_operator_run,
            "validation_session_source": self.validation_session_source,
            "operator_run": self.run.to_public_payload() if self.run is not None else None,
            "tenant_key": self.tenant_key,
            "tenant_label": self.tenant_label,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def _is_local_host(remote_host: str | None) -> bool:
    host = str(remote_host or "").strip().lower()
    if not host:
        return True
    return host in _LOCAL_HOSTS


def _pilot_tenant_key() -> str:
    return str(env_str(V2_ANDROID_PILOT_TENANT_KEY_FLAG, "") or "").strip()


def _required_targets_per_surface() -> int:
    return max(
        env_int("TARIEL_V2_ANDROID_OPERATOR_RUN_REQUIRED_TARGETS_PER_SURFACE", 1),
        1,
    )


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


def _resolve_target_instruction(surface: str, target_id: int) -> str:
    if surface == "feed":
        return (
            f"Abrir a central de atividade do tenant demo e confirmar o laudo {target_id} "
            "visivel no feed V2."
        )
    return (
        f"Abrir a aba Mesa do laudo {target_id} e aguardar a thread V2 renderizar com mensagens."
    )


def _build_required_targets(
    target_map: dict[str, tuple[int, ...]],
) -> tuple[MobileOperatorValidationTarget, ...]:
    targets: list[MobileOperatorValidationTarget] = []
    required_per_surface = _required_targets_per_surface()
    for surface in _SURFACES:
        for target_id in tuple(target_map.get(surface, ())[:required_per_surface]):
            targets.append(
                MobileOperatorValidationTarget(
                    surface=surface,
                    target_id=int(target_id),
                    instruction=_resolve_target_instruction(surface, int(target_id)),
                )
            )
    return tuple(targets)


def _surface_target_ids(
    targets: tuple[MobileOperatorValidationTarget, ...],
    *,
    surface: str,
) -> tuple[int, ...]:
    return tuple(int(item.target_id) for item in targets if item.surface == surface)


def _resolve_operator_targets() -> dict[str, tuple[int, ...]]:
    resolved = resolve_demo_mobile_organic_validation_targets(tenant_key=_pilot_tenant_key())
    required_per_surface = _required_targets_per_surface()
    return {
        surface: tuple(int(item) for item in resolved.get(surface, ())[:required_per_surface])
        for surface in _SURFACES
    }


def _build_progress(
    run: MobileOperatorValidationRun,
) -> MobileOperatorValidationProgress:
    summary = get_mobile_v2_organic_validation_summary()
    surface_rows = {item.surface: item for item in summary.surface_summaries}
    checkpoints = list_mobile_v2_organic_human_checkpoints(run.session_id)

    covered_surfaces: list[str] = []
    missing_surfaces: list[str] = []
    covered_targets: dict[str, tuple[int, ...]] = {}
    human_targets: dict[str, tuple[int, ...]] = {}
    missing_targets: dict[str, tuple[int, ...]] = {}
    progress_targets: list[MobileOperatorValidationTarget] = []
    human_coverage_from_run = False

    for surface in run.required_surfaces:
        required_target_ids = set(_surface_target_ids(run.required_targets, surface=surface))
        surface_summary = surface_rows.get(surface)
        covered_target_ids = set(
            getattr(getattr(surface_summary, "target_summary", None), "covered_target_ids", ())
            or ()
        )
        matching_checkpoints = [
            item
            for item in checkpoints
            if item.surface == surface
            and item.delivery_mode == "v2"
            and (
                item.operator_run_id in {None, run.operator_run_id}
                or not run.operator_run_id
            )
        ]
        human_target_ids = {int(item.target_id) for item in matching_checkpoints}
        if human_target_ids:
            human_coverage_from_run = True

        completed_target_ids = tuple(sorted(required_target_ids & covered_target_ids & human_target_ids))
        covered_targets[surface] = tuple(sorted(required_target_ids & covered_target_ids))
        human_targets[surface] = tuple(sorted(required_target_ids & human_target_ids))
        missing_targets[surface] = tuple(sorted(required_target_ids - set(completed_target_ids)))

        surface_completed = (
            bool(required_target_ids)
            and set(completed_target_ids) == required_target_ids
        )
        if surface_completed:
            covered_surfaces.append(surface)
        else:
            missing_surfaces.append(surface)

        for base_target in run.required_targets:
            if base_target.surface != surface:
                continue
            progress_targets.append(
                MobileOperatorValidationTarget(
                    surface=base_target.surface,
                    target_id=base_target.target_id,
                    instruction=base_target.instruction,
                    covered_in_validation=base_target.target_id in covered_targets[surface],
                    human_confirmed=base_target.target_id in human_targets[surface],
                    completed=base_target.target_id in completed_target_ids,
                )
            )

    fallback_observed = summary.organic_requests_fallback > 0
    fallback_excessive = summary.outcome == "hold_recommended" or any(
        item.outcome == "hold_recommended" for item in summary.surface_summaries
    )
    critical_issue_detected = summary.outcome == "rollback_recommended" or any(
        item.outcome == "rollback_recommended" for item in summary.surface_summaries
    )

    target_count_required = len(run.required_targets)
    target_count_completed = sum(1 for item in progress_targets if item.completed)
    human_confirmed_minimum_met = (
        len(covered_surfaces) == len(run.required_surfaces) and target_count_completed == target_count_required
    )

    return MobileOperatorValidationProgress(
        feed_completed="feed" in covered_surfaces,
        thread_completed="thread" in covered_surfaces,
        human_confirmed_minimum_met=human_confirmed_minimum_met,
        fallback_observed=fallback_observed,
        fallback_excessive=fallback_excessive,
        critical_issue_detected=critical_issue_detected,
        required_surfaces=run.required_surfaces,
        covered_surfaces=tuple(covered_surfaces),
        missing_surfaces=tuple(missing_surfaces),
        covered_targets=covered_targets,
        human_confirmed_targets=human_targets,
        missing_targets=missing_targets,
        targets=tuple(progress_targets),
        target_count_required=target_count_required,
        target_count_completed=target_count_completed,
        organic_validation_outcome=summary.outcome,
        organic_validation_window_elapsed=summary.window_elapsed,
        human_coverage_from_operator_run=human_coverage_from_run,
    )


def _resolve_completed_outcome(
    run: MobileOperatorValidationRun,
    progress: MobileOperatorValidationProgress,
) -> tuple[str, str]:
    if progress.critical_issue_detected:
        return "completed_inconclusive", "rollback_recommended_during_run"
    if progress.fallback_excessive:
        return "completed_inconclusive", "fallback_excessive_during_run"
    if not progress.human_confirmed_minimum_met:
        return "completed_inconclusive", "minimum_human_coverage_not_met"
    if progress.fallback_observed:
        return "completed_with_fallback", "required_surfaces_completed_with_fallback"
    return "completed_successfully", "required_surfaces_completed"


def _default_status() -> MobileOperatorValidationStatus:
    return MobileOperatorValidationStatus(
        run=None,
        progress=None,
        operator_run_active=False,
        operator_run_id=None,
        operator_run_outcome=None,
        operator_run_reason=None,
        operator_run_started_at=None,
        operator_run_ended_at=None,
        operator_run_session_id=None,
        tenant_key=None,
        tenant_label=None,
        required_surfaces=(),
        covered_surfaces=(),
        missing_targets={surface: () for surface in _SURFACES},
        operator_run_instructions=(),
        human_coverage_from_operator_run=False,
        validation_session_source="none",
    )


def get_mobile_v2_operator_validation_default_payload() -> dict[str, Any]:
    return _default_status().to_public_payload()


def get_mobile_v2_operator_validation_status(
    *,
    remote_host: str | None = None,
) -> MobileOperatorValidationStatus:
    if not _is_local_host(remote_host):
        raise PermissionError("operator_run_requires_local_host")

    with _lock:
        run = _operator_run_state
    if run is None:
        return _default_status()

    progress = None
    if run.session_id:
        progress = _build_progress(run)

    instructions = tuple(item.instruction for item in run.required_targets)
    if progress is None:
        covered_surfaces: tuple[str, ...] = ()
        missing_targets = {
            surface: _surface_target_ids(run.required_targets, surface=surface)
            for surface in run.required_surfaces
        }
        human_coverage_from_run = False
    else:
        covered_surfaces = progress.covered_surfaces
        missing_targets = progress.missing_targets
        human_coverage_from_run = progress.human_coverage_from_operator_run

    return MobileOperatorValidationStatus(
        run=run,
        progress=progress,
        operator_run_active=run.active,
        operator_run_id=run.operator_run_id,
        operator_run_outcome=run.outcome,
        operator_run_reason=run.outcome_reason,
        operator_run_started_at=run.started_at,
        operator_run_ended_at=run.ended_at,
        operator_run_session_id=run.session_id,
        tenant_key=run.tenant_key,
        tenant_label=run.tenant_label,
        required_surfaces=run.required_surfaces,
        covered_surfaces=covered_surfaces,
        missing_targets=missing_targets,
        operator_run_instructions=instructions,
        human_coverage_from_operator_run=human_coverage_from_run,
        validation_session_source="operator_run",
    )


def get_mobile_v2_operator_validation_signal(
    *,
    tenant_key: str,
) -> dict[str, Any]:
    status = get_mobile_v2_operator_validation_status()
    if (
        not status.operator_run_active
        or not status.run
        or status.tenant_key != str(tenant_key or "").strip()
    ):
        return {
            "operator_validation_run_active": False,
            "operator_validation_run_id": None,
            "operator_validation_required_surfaces": [],
        }
    return {
        "operator_validation_run_active": True,
        "operator_validation_run_id": status.operator_run_id,
        "operator_validation_required_surfaces": list(status.required_surfaces),
    }


def start_mobile_v2_operator_validation_run(
    *,
    remote_host: str | None = None,
    trigger_source: str = "admin_api",
) -> MobileOperatorValidationStatus:
    global _operator_run_state
    if not _is_local_host(remote_host):
        raise PermissionError("operator_run_requires_local_host")

    with _lock:
        current_run = _operator_run_state
    if current_run is not None and current_run.active:
        return get_mobile_v2_operator_validation_status(remote_host=remote_host)

    tenant_key = _pilot_tenant_key()
    tenant_label = _resolve_tenant_label(tenant_key)
    target_map = _resolve_operator_targets()
    required_targets = _build_required_targets(target_map)
    missing_surfaces = [
        surface for surface in _SURFACES if not tuple(target_map.get(surface, ()))
    ]
    now = _now_iso()

    if missing_surfaces:
        blocked_run = MobileOperatorValidationRun(
            tenant_key=tenant_key,
            tenant_label=tenant_label,
            session_id=None,
            operator_run_id=f"oprv_{uuid4().hex[:12]}",
            started_at=now,
            ended_at=now,
            active=False,
            required_surfaces=tuple(_SURFACES),
            required_targets=required_targets,
            outcome="blocked_no_targets",
            outcome_reason=(
                "eligible_targets_missing_for_" + "_".join(sorted(missing_surfaces))
            ),
            trigger_source=trigger_source,
            finish_source="blocked_before_start",
        )
        with _lock:
            _operator_run_state = blocked_run
        return get_mobile_v2_operator_validation_status(remote_host=remote_host)

    organic_summary = start_mobile_v2_organic_validation_session(
        remote_host=remote_host,
        trigger_source="operator_run",
    )
    session = organic_summary.session
    if session is None:
        raise RuntimeError("operator_run_session_not_started")

    run = MobileOperatorValidationRun(
        tenant_key=session.tenant_key,
        tenant_label=session.tenant_label,
        session_id=session.session_id,
        operator_run_id=f"oprv_{uuid4().hex[:12]}",
        started_at=session.started_at,
        ended_at=None,
        active=True,
        required_surfaces=session.surfaces,
        required_targets=required_targets,
        outcome="in_progress",
        outcome_reason="operator_run_started",
        trigger_source=trigger_source,
        finish_source=None,
    )
    with _lock:
        _operator_run_state = run
    return get_mobile_v2_operator_validation_status(remote_host=remote_host)


def finish_mobile_v2_operator_validation_run(
    *,
    remote_host: str | None = None,
    trigger_source: str = "admin_api",
    abort: bool = False,
) -> MobileOperatorValidationStatus:
    global _operator_run_state
    if not _is_local_host(remote_host):
        raise PermissionError("operator_run_requires_local_host")

    with _lock:
        run = _operator_run_state
    if run is None:
        raise RuntimeError("operator_run_not_started")
    if not run.active:
        return get_mobile_v2_operator_validation_status(remote_host=remote_host)

    if abort:
        if run.session_id and get_mobile_v2_organic_validation_session() is not None:
            try:
                stop_mobile_v2_organic_validation_session(
                    remote_host=remote_host,
                    trigger_source="operator_run_abort",
                )
            except RuntimeError:
                pass
        aborted_run = replace(
            run,
            active=False,
            ended_at=_now_iso(),
            outcome="aborted",
            outcome_reason="operator_aborted",
            finish_source=trigger_source,
        )
        with _lock:
            _operator_run_state = aborted_run
        return get_mobile_v2_operator_validation_status(remote_host=remote_host)

    if run.session_id and get_mobile_v2_organic_validation_session() is not None:
        stop_mobile_v2_organic_validation_session(
            remote_host=remote_host,
            trigger_source="operator_run_finish",
        )

    progress = _build_progress(run)
    outcome, outcome_reason = _resolve_completed_outcome(run, progress)
    completed_run = replace(
        run,
        active=False,
        ended_at=_now_iso(),
        outcome=outcome,
        outcome_reason=outcome_reason,
        finish_source=trigger_source,
    )
    with _lock:
        _operator_run_state = completed_run
    return get_mobile_v2_operator_validation_status(remote_host=remote_host)


def clear_mobile_v2_operator_validation_run_for_tests() -> None:
    with _lock:
        global _operator_run_state
        _operator_run_state = None


__all__ = [
    "MobileOperatorValidationProgress",
    "MobileOperatorValidationRun",
    "MobileOperatorValidationStatus",
    "MobileOperatorValidationTarget",
    "clear_mobile_v2_operator_validation_run_for_tests",
    "finish_mobile_v2_operator_validation_run",
    "get_mobile_v2_operator_validation_default_payload",
    "get_mobile_v2_operator_validation_signal",
    "get_mobile_v2_operator_validation_status",
    "start_mobile_v2_operator_validation_run",
]
