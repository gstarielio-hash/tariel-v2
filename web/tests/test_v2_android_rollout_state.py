from __future__ import annotations

from types import SimpleNamespace

from app.shared.database import NivelAcesso
from app.v2.mobile_rollout import (
    resolve_mobile_v2_capabilities_for_user,
    resolve_mobile_v2_rollout_state_for_user,
)


def _build_user(*, empresa_id: int = 33) -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=empresa_id,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def test_rollout_state_explicitamente_legacy_only_por_tenant(monkeypatch) -> None:
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST", "33")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", "33=legacy_only")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")

    rollout = resolve_mobile_v2_rollout_state_for_user(_build_user())
    capabilities = resolve_mobile_v2_capabilities_for_user(_build_user())

    assert rollout.rollout_state == "legacy_only"
    assert rollout.feed.state == "legacy_only"
    assert rollout.thread.state == "legacy_only"
    assert rollout.feed.enabled is False
    assert rollout.thread.enabled is False
    assert capabilities.mobile_v2_reads_enabled is False
    assert capabilities.feed_rollout_state == "legacy_only"
    assert capabilities.thread_rollout_state == "legacy_only"


def test_rollout_state_permanece_pilot_enabled_quando_tenant_esta_no_piloto(monkeypatch) -> None:
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST", "33")
    monkeypatch.delenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", raising=False)
    monkeypatch.delenv("TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES", raising=False)
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")

    rollout = resolve_mobile_v2_rollout_state_for_user(_build_user())

    assert rollout.rollout_state == "pilot_enabled"
    assert rollout.feed.state == "pilot_enabled"
    assert rollout.thread.state == "pilot_enabled"
    assert rollout.feed.enabled is True
    assert rollout.thread.enabled is True


def test_rollout_state_suporta_promocao_hold_e_rollback_por_superficie(monkeypatch) -> None:
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", "33=pilot_enabled")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES",
        "33:feed=promoted,33:thread=hold",
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")

    rollout = resolve_mobile_v2_rollout_state_for_user(_build_user())
    capabilities = resolve_mobile_v2_capabilities_for_user(_build_user())

    assert rollout.rollout_state == "pilot_enabled"
    assert rollout.feed.state == "promoted"
    assert rollout.feed.promoted is True
    assert rollout.feed.enabled is True
    assert rollout.thread.state == "hold"
    assert rollout.thread.hold is True
    assert rollout.thread.enabled is False
    assert capabilities.mobile_v2_reads_enabled is True
    assert capabilities.feed_promoted is True
    assert capabilities.thread_hold is True
    assert capabilities.thread_rollback_forced is False
    assert capabilities.mobile_v2_architecture_status == "hold"
    assert capabilities.mobile_v2_legacy_fallback_policy == "required_for_continuity"
    assert capabilities.mobile_v2_transition_active is False


def test_rollout_state_suporta_rollback_forced_por_superficie(monkeypatch) -> None:
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", "33=pilot_enabled")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES",
        "33:thread=rollback_forced",
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")

    rollout = resolve_mobile_v2_rollout_state_for_user(_build_user())

    assert rollout.feed.state == "pilot_enabled"
    assert rollout.thread.state == "rollback_forced"
    assert rollout.thread.rollback_forced is True
    assert rollout.thread.enabled is False
