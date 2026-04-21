"""Probe controlado de leitura para o piloto mobile V2."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from itertools import cycle
from typing import Any

from sqlalchemy import func, select
from starlette.requests import Request

import app.shared.database as banco_dados
from app.core.settings import env_bool, env_int, env_str
from app.domains.chat.mesa import (
    feed_mesa_mobile,
    feed_mesa_mobile_public_v2,
    listar_mensagens_mesa_laudo,
    listar_mensagens_mesa_laudo_mobile_public_v2,
)
from app.shared.database import Empresa, Laudo, MensagemLaudo, NivelAcesso, Usuario
from app.v2.mobile_rollout import (
    HEADER_V2_ATTEMPTED,
    HEADER_V2_CAPABILITIES_VERSION,
    HEADER_V2_FALLBACK_REASON,
    HEADER_V2_GATE_SOURCE,
    HEADER_V2_PROBE,
    HEADER_V2_PROBE_SOURCE,
    HEADER_V2_ROLLOUT_BUCKET,
    HEADER_V2_ROUTE,
    MOBILE_V2_CAPABILITIES_VERSION,
    V2_ANDROID_PILOT_PROBE_FLAG,
    discover_mobile_v2_safe_pilot_candidates,
    resolve_mobile_v2_rollout_state_for_user,
)
from app.v2.mobile_rollout_metrics import (
    get_mobile_v2_probe_runtime_state,
    record_mobile_v2_probe_run,
)

V2_ANDROID_PILOT_PROBE_MAX_REQUESTS_PER_SURFACE_FLAG = (
    "TARIEL_V2_ANDROID_PILOT_PROBE_MAX_REQUESTS_PER_SURFACE"
)
V2_ANDROID_PILOT_PROBE_TARGET_LIMIT_FLAG = "TARIEL_V2_ANDROID_PILOT_PROBE_TARGET_LIMIT"
V2_ANDROID_PILOT_PROBE_TIMEOUT_MS_FLAG = "TARIEL_V2_ANDROID_PILOT_PROBE_TIMEOUT_MS"
V2_ANDROID_PILOT_PROBE_DELAY_MS_FLAG = "TARIEL_V2_ANDROID_PILOT_PROBE_DELAY_MS"
V2_ANDROID_PILOT_PROBE_INCLUDE_LEGACY_COMPARE_FLAG = (
    "TARIEL_V2_ANDROID_PILOT_PROBE_INCLUDE_LEGACY_COMPARE"
)
V2_ANDROID_PILOT_TENANT_KEY_FLAG = "TARIEL_V2_ANDROID_PILOT_TENANT_KEY"
V2_ANDROID_PILOT_MIN_REQUESTS_FLAG = "TARIEL_V2_ANDROID_PILOT_MIN_REQUESTS"

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_PROBE_LABEL = "pilot_probe"
_PROBE_SOURCE = "demo_controlled"


@dataclass(frozen=True, slots=True)
class MobileV2ProbeTargets:
    tenant_key: str
    tenant_label: str | None
    inspector_user_id: int | None
    inspector_email: str | None
    feed_laudo_ids: tuple[int, ...]
    thread_laudo_ids: tuple[int, ...]
    ready: bool
    detail: str

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "tenant_key": self.tenant_key,
            "tenant_label": self.tenant_label,
            "inspector_user_id": self.inspector_user_id,
            "inspector_email": self.inspector_email,
            "feed_laudo_ids": list(self.feed_laudo_ids),
            "thread_laudo_ids": list(self.thread_laudo_ids),
            "ready": self.ready,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class MobileV2PilotProbeResult:
    ok: bool
    status: str
    tenant_key: str | None
    tenant_label: str | None
    detail: str
    targets: MobileV2ProbeTargets | None
    probe_requests_v2: int
    probe_requests_fallback: int
    probe_surfaces_exercised: tuple[str, ...]
    probe_last_run_at: str | None = None
    errors: tuple[str, ...] = ()

    def to_public_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "tenant_key": self.tenant_key,
            "tenant_label": self.tenant_label,
            "detail": self.detail,
            "targets": self.targets.to_public_payload() if self.targets is not None else None,
            "probe_requests_v2": self.probe_requests_v2,
            "probe_requests_fallback": self.probe_requests_fallback,
            "probe_surfaces_exercised": list(self.probe_surfaces_exercised),
            "probe_last_run_at": self.probe_last_run_at,
            "errors": list(self.errors),
        }


def mobile_v2_pilot_probe_enabled() -> bool:
    return env_bool(V2_ANDROID_PILOT_PROBE_FLAG, False)


def _pilot_probe_tenant_key() -> str:
    return str(env_str(V2_ANDROID_PILOT_TENANT_KEY_FLAG, "") or "").strip()


def _probe_target_limit() -> int:
    return max(1, min(5, env_int(V2_ANDROID_PILOT_PROBE_TARGET_LIMIT_FLAG, 2)))


def _probe_requests_per_surface() -> int:
    baseline = max(env_int(V2_ANDROID_PILOT_MIN_REQUESTS_FLAG, 5), 1)
    configured = max(env_int(V2_ANDROID_PILOT_PROBE_MAX_REQUESTS_PER_SURFACE_FLAG, baseline), 1)
    return min(configured, 12)


def _probe_timeout_ms() -> int:
    return max(env_int(V2_ANDROID_PILOT_PROBE_TIMEOUT_MS_FLAG, 4000), 500)


def _probe_delay_ms() -> int:
    return max(env_int(V2_ANDROID_PILOT_PROBE_DELAY_MS_FLAG, 0), 0)


def _probe_include_legacy_compare() -> bool:
    return env_bool(V2_ANDROID_PILOT_PROBE_INCLUDE_LEGACY_COMPARE_FLAG, False)


def _is_local_probe_host(remote_host: str | None) -> bool:
    host = str(remote_host or "").strip().lower()
    if not host:
        return True
    return host in _LOCAL_HOSTS


def resolve_demo_mobile_probe_targets() -> MobileV2ProbeTargets:
    tenant_key = _pilot_probe_tenant_key()
    safe_candidates = {
        item.tenant_key: item for item in discover_mobile_v2_safe_pilot_candidates()
    }
    safe_candidate = safe_candidates.get(tenant_key)
    if not tenant_key or safe_candidate is None:
        return MobileV2ProbeTargets(
            tenant_key=tenant_key or "",
            tenant_label=None,
            inspector_user_id=None,
            inspector_email=None,
            feed_laudo_ids=(),
            thread_laudo_ids=(),
            ready=False,
            detail="pilot_tenant_not_safe_for_probe",
        )

    target_limit = _probe_target_limit()
    with banco_dados.SessaoLocal() as banco:
        tenant = banco.get(Empresa, int(tenant_key))
        if tenant is None:
            return MobileV2ProbeTargets(
                tenant_key=tenant_key,
                tenant_label=safe_candidate.tenant_label,
                inspector_user_id=None,
                inspector_email=None,
                feed_laudo_ids=(),
                thread_laudo_ids=(),
                ready=False,
                detail="pilot_tenant_not_found",
            )

        inspector = banco.scalar(
            select(Usuario)
            .where(
                Usuario.empresa_id == int(tenant_key),
                Usuario.nivel_acesso == int(NivelAcesso.INSPETOR.value),
                Usuario.ativo.is_(True),
            )
            .order_by(Usuario.id.asc())
            .limit(1)
        )
        if inspector is None:
            return MobileV2ProbeTargets(
                tenant_key=tenant_key,
                tenant_label=str(getattr(tenant, "nome_fantasia", "") or safe_candidate.tenant_label),
                inspector_user_id=None,
                inspector_email=None,
                feed_laudo_ids=(),
                thread_laudo_ids=(),
                ready=False,
                detail="pilot_probe_inspector_missing",
            )

        feed_laudos = banco.execute(
            select(Laudo.id)
            .where(Laudo.empresa_id == int(tenant_key))
            .order_by(Laudo.id.asc())
            .limit(target_limit)
        ).scalars().all()
        thread_laudos = banco.execute(
            select(Laudo.id)
            .join(MensagemLaudo, MensagemLaudo.laudo_id == Laudo.id)
            .where(Laudo.empresa_id == int(tenant_key))
            .group_by(Laudo.id)
            .having(func.count(MensagemLaudo.id) > 0)
            .order_by(Laudo.id.asc())
            .limit(target_limit)
        ).scalars().all()

        ready = bool(feed_laudos) and bool(thread_laudos)
        detail = "probe_targets_resolved" if ready else "probe_targets_missing"
        return MobileV2ProbeTargets(
            tenant_key=tenant_key,
            tenant_label=str(getattr(tenant, "nome_fantasia", "") or safe_candidate.tenant_label),
            inspector_user_id=int(getattr(inspector, "id", 0) or 0) or None,
            inspector_email=str(getattr(inspector, "email", "") or "").strip() or None,
            feed_laudo_ids=tuple(int(item) for item in feed_laudos),
            thread_laudo_ids=tuple(int(item) for item in thread_laudos),
            ready=ready,
            detail=detail,
        )


def _build_probe_request(
    *,
    path: str,
    route: str,
    rollout_bucket: int | None,
    fallback_reason: str | None = None,
) -> Request:
    headers: dict[str, str] = {
        HEADER_V2_ATTEMPTED: "1",
        HEADER_V2_ROUTE: route,
        HEADER_V2_CAPABILITIES_VERSION: MOBILE_V2_CAPABILITIES_VERSION,
        HEADER_V2_PROBE: "1",
        HEADER_V2_PROBE_SOURCE: _PROBE_SOURCE,
    }
    if rollout_bucket is not None:
        headers[HEADER_V2_ROLLOUT_BUCKET] = str(int(rollout_bucket))
    if fallback_reason:
        headers[HEADER_V2_FALLBACK_REASON] = fallback_reason
        headers[HEADER_V2_GATE_SOURCE] = f"{_PROBE_LABEL}_{_PROBE_SOURCE}"
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [
                (key.lower().encode("utf-8"), value.encode("utf-8"))
                for key, value in headers.items()
            ],
            "query_string": b"",
            "session": {},
            "state": {},
            "client": ("127.0.0.1", 0),
        }
    )


async def _run_feed_probe_once(
    *,
    usuario: Usuario,
    banco,
    rollout_bucket: int | None,
    laudo_ids: tuple[int, ...],
) -> None:
    request = _build_probe_request(
        path="/app/api/mobile/v2/mesa/feed",
        route="feed",
        rollout_bucket=rollout_bucket,
    )
    response = await feed_mesa_mobile_public_v2(
        request=request,
        laudo_ids=",".join(str(item) for item in laudo_ids),
        cursor_atualizado_em=None,
        usuario=usuario,
        banco=banco,
    )
    if int(getattr(response, "status_code", 500) or 500) >= 400:
        raise RuntimeError("feed_probe_failed")


async def _run_thread_probe_once(
    *,
    usuario: Usuario,
    banco,
    rollout_bucket: int | None,
    laudo_id: int,
) -> None:
    request = _build_probe_request(
        path=f"/app/api/mobile/v2/laudo/{laudo_id}/mesa/mensagens",
        route="thread",
        rollout_bucket=rollout_bucket,
    )
    response = await listar_mensagens_mesa_laudo_mobile_public_v2(
        laudo_id=laudo_id,
        request=request,
        cursor=None,
        apos_id=None,
        limite=40,
        usuario=usuario,
        banco=banco,
    )
    if int(getattr(response, "status_code", 500) or 500) >= 400:
        raise RuntimeError("thread_probe_failed")


async def _run_legacy_compare_once(
    *,
    surface: str,
    usuario: Usuario,
    banco,
    rollout_bucket: int | None,
    feed_laudo_ids: tuple[int, ...],
    thread_laudo_id: int | None,
) -> None:
    fallback_reason = "probe_legacy_compare"
    if surface == "feed":
        request = _build_probe_request(
            path="/app/api/mobile/mesa/feed",
            route="feed",
            rollout_bucket=rollout_bucket,
            fallback_reason=fallback_reason,
        )
        response = await feed_mesa_mobile(
            request=request,
            laudo_ids=",".join(str(item) for item in feed_laudo_ids),
            cursor_atualizado_em=None,
            usuario=usuario,
            banco=banco,
        )
    else:
        laudo_id = int(thread_laudo_id or 0)
        request = _build_probe_request(
            path=f"/app/api/laudo/{laudo_id}/mesa/mensagens",
            route="thread",
            rollout_bucket=rollout_bucket,
            fallback_reason=fallback_reason,
        )
        response = await listar_mensagens_mesa_laudo(
            laudo_id=laudo_id,
            request=request,
            cursor=None,
            apos_id=None,
            limite=40,
            usuario=usuario,
            banco=banco,
        )
    if int(getattr(response, "status_code", 500) or 500) >= 400:
        raise RuntimeError(f"{surface}_legacy_probe_failed")


async def execute_demo_mobile_v2_pilot_probe(
    *,
    remote_host: str | None = None,
    trigger_source: str = "local_runner",
) -> MobileV2PilotProbeResult:
    probe_active = mobile_v2_pilot_probe_enabled()
    if not probe_active:
        record_mobile_v2_probe_run(
            probe_active=False,
            status="disabled",
            tenant_key=_pilot_probe_tenant_key(),
            tenant_label=None,
            probe_source=trigger_source,
            surfaces_exercised=[],
            requests_v2=0,
            requests_fallback=0,
            targets_resolved=False,
            detail="pilot_probe_disabled",
        )
        return MobileV2PilotProbeResult(
            ok=False,
            status="disabled",
            tenant_key=_pilot_probe_tenant_key() or None,
            tenant_label=None,
            detail="pilot_probe_disabled",
            targets=None,
            probe_requests_v2=0,
            probe_requests_fallback=0,
            probe_surfaces_exercised=(),
            probe_last_run_at=get_mobile_v2_probe_runtime_state().get("probe_last_run_at"),
        )

    if not _is_local_probe_host(remote_host):
        record_mobile_v2_probe_run(
            probe_active=True,
            status="blocked",
            tenant_key=_pilot_probe_tenant_key(),
            tenant_label=None,
            probe_source=trigger_source,
            surfaces_exercised=[],
            requests_v2=0,
            requests_fallback=0,
            targets_resolved=False,
            detail="pilot_probe_requires_local_host",
        )
        return MobileV2PilotProbeResult(
            ok=False,
            status="blocked",
            tenant_key=_pilot_probe_tenant_key() or None,
            tenant_label=None,
            detail="pilot_probe_requires_local_host",
            targets=None,
            probe_requests_v2=0,
            probe_requests_fallback=0,
            probe_surfaces_exercised=(),
            probe_last_run_at=get_mobile_v2_probe_runtime_state().get("probe_last_run_at"),
        )

    targets = resolve_demo_mobile_probe_targets()
    if not targets.ready:
        record_mobile_v2_probe_run(
            probe_active=True,
            status="blocked",
            tenant_key=targets.tenant_key,
            tenant_label=targets.tenant_label,
            probe_source=trigger_source,
            surfaces_exercised=[],
            requests_v2=0,
            requests_fallback=0,
            targets_resolved=False,
            detail=targets.detail,
        )
        return MobileV2PilotProbeResult(
            ok=False,
            status="blocked",
            tenant_key=targets.tenant_key or None,
            tenant_label=targets.tenant_label,
            detail=targets.detail,
            targets=targets,
            probe_requests_v2=0,
            probe_requests_fallback=0,
            probe_surfaces_exercised=(),
            probe_last_run_at=get_mobile_v2_probe_runtime_state().get("probe_last_run_at"),
        )

    requested_per_surface = _probe_requests_per_surface()
    timeout_deadline = time.monotonic() + (_probe_timeout_ms() / 1000)
    delay_seconds = _probe_delay_ms() / 1000
    include_legacy_compare = _probe_include_legacy_compare()
    probe_requests_v2 = 0
    probe_requests_fallback = 0
    errors: list[str] = []
    surfaces_exercised: set[str] = set()

    with banco_dados.SessaoLocal() as banco:
        usuario = banco.get(Usuario, int(targets.inspector_user_id or 0))
        if usuario is None:
            detail = "pilot_probe_inspector_not_found"
            record_mobile_v2_probe_run(
                probe_active=True,
                status="blocked",
                tenant_key=targets.tenant_key,
                tenant_label=targets.tenant_label,
                probe_source=trigger_source,
                surfaces_exercised=[],
                requests_v2=0,
                requests_fallback=0,
                targets_resolved=True,
                detail=detail,
            )
            return MobileV2PilotProbeResult(
                ok=False,
                status="blocked",
                tenant_key=targets.tenant_key,
                tenant_label=targets.tenant_label,
                detail=detail,
                targets=targets,
                probe_requests_v2=0,
                probe_requests_fallback=0,
                probe_surfaces_exercised=(),
                probe_last_run_at=get_mobile_v2_probe_runtime_state().get("probe_last_run_at"),
            )

        rollout_state = resolve_mobile_v2_rollout_state_for_user(usuario)
        rollout_bucket = rollout_state.rollout_bucket

        try:
            for _ in range(requested_per_surface):
                if time.monotonic() >= timeout_deadline:
                    raise TimeoutError("pilot_probe_timeout")
                await _run_feed_probe_once(
                    usuario=usuario,
                    banco=banco,
                    rollout_bucket=rollout_bucket,
                    laudo_ids=targets.feed_laudo_ids,
                )
                probe_requests_v2 += 1
                surfaces_exercised.add("feed")
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)

            thread_target_ids = cycle(targets.thread_laudo_ids)
            for _ in range(requested_per_surface):
                if time.monotonic() >= timeout_deadline:
                    raise TimeoutError("pilot_probe_timeout")
                await _run_thread_probe_once(
                    usuario=usuario,
                    banco=banco,
                    rollout_bucket=rollout_bucket,
                    laudo_id=int(next(thread_target_ids)),
                )
                probe_requests_v2 += 1
                surfaces_exercised.add("thread")
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)

            if include_legacy_compare:
                await _run_legacy_compare_once(
                    surface="feed",
                    usuario=usuario,
                    banco=banco,
                    rollout_bucket=rollout_bucket,
                    feed_laudo_ids=targets.feed_laudo_ids,
                    thread_laudo_id=None,
                )
                probe_requests_fallback += 1
                surfaces_exercised.add("feed")
                await _run_legacy_compare_once(
                    surface="thread",
                    usuario=usuario,
                    banco=banco,
                    rollout_bucket=rollout_bucket,
                    feed_laudo_ids=targets.feed_laudo_ids,
                    thread_laudo_id=targets.thread_laudo_ids[0],
                )
                probe_requests_fallback += 1
                surfaces_exercised.add("thread")
            status = "completed"
            detail = "pilot_probe_completed"
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            status = "aborted"
            detail = "pilot_probe_aborted"

    record_mobile_v2_probe_run(
        probe_active=True,
        status=status,
        tenant_key=targets.tenant_key,
        tenant_label=targets.tenant_label,
        probe_source=trigger_source,
        surfaces_exercised=sorted(surfaces_exercised),
        requests_v2=probe_requests_v2,
        requests_fallback=probe_requests_fallback,
        targets_resolved=True,
        detail=detail,
    )
    return MobileV2PilotProbeResult(
        ok=status == "completed",
        status=status,
        tenant_key=targets.tenant_key,
        tenant_label=targets.tenant_label,
        detail=detail,
        targets=targets,
        probe_requests_v2=probe_requests_v2,
        probe_requests_fallback=probe_requests_fallback,
        probe_surfaces_exercised=tuple(sorted(surfaces_exercised)),
        probe_last_run_at=get_mobile_v2_probe_runtime_state().get("probe_last_run_at"),
        errors=tuple(errors),
    )


def run_demo_mobile_v2_pilot_probe(
    *,
    remote_host: str | None = None,
    trigger_source: str = "local_runner",
) -> MobileV2PilotProbeResult:
    return asyncio.run(
        execute_demo_mobile_v2_pilot_probe(
            remote_host=remote_host,
            trigger_source=trigger_source,
        )
    )
