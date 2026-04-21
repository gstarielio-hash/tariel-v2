from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.v2.mobile_rollout import (
    MOBILE_V2_CAPABILITIES_VERSION,
    discover_mobile_v2_safe_pilot_candidates,
    resolve_mobile_v2_rollout_state_for_tenant_key,
)
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
    record_mobile_v2_public_read,
)


def _record_pilot_reads(*, tenant_key: str, surface: str, requests: int) -> None:
    for _ in range(requests):
        record_mobile_v2_public_read(
            tenant_key=tenant_key,
            endpoint=surface,
            reason="promoted",
            source="surface_state_override",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        )


def test_discovery_reconhece_tenants_locais_seguro_para_piloto() -> None:
    candidates = discover_mobile_v2_safe_pilot_candidates()
    by_key = {candidate.tenant_key: candidate for candidate in candidates}

    assert by_key["1"].tenant_label == "Empresa Demo (DEV)"
    assert by_key["1"].safety_reason == "seed_dev_demo_company"
    assert by_key["1"].inspector_users >= 1
    if "3" in by_key:
        assert by_key["3"].safety_reason in {
            "seed_dev_internal_company",
            "local_load_lab_company",
        }


def test_promoted_surface_expoe_janela_formal_e_resumo_do_primeiro_tenant(monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    started_at = datetime.now(timezone.utc).replace(microsecond=0)

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", "33=pilot_enabled")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES",
        "33:feed=promoted,33:thread=promoted",
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", "33")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_PILOT_PROMOTED_SINCE",
        started_at.isoformat().replace("+00:00", "Z"),
    )
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT",
        started_at.isoformat().replace("+00:00", "Z"),
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS", "24")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_SOURCE", "seed_dev_demo_company")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_NOTE", "first_local_pilot")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")

    _record_pilot_reads(tenant_key="33", surface="feed", requests=2)
    _record_pilot_reads(tenant_key="33", surface="thread", requests=1)

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")
    summary = get_mobile_v2_rollout_operational_summary()
    first_promoted = summary["first_promoted_tenant"]

    assert rollout.feed.promoted is True
    assert rollout.thread.promoted is True
    assert rollout.feed.promoted_since == started_at.isoformat().replace("+00:00", "Z")
    assert rollout.feed.rollback_window_until == (
        started_at + timedelta(hours=24)
    ).isoformat().replace("+00:00", "Z")
    assert rollout.feed.rollback_window_active is True
    assert rollout.feed.pilot_health_status == "healthy"
    assert first_promoted["tenant_key"] == "33"
    assert first_promoted["promoted_surfaces"] == ["feed", "thread"]
    assert first_promoted["promotion_source"] == "seed_dev_demo_company"
    assert first_promoted["promotion_note"] == "first_local_pilot"
    assert first_promoted["pilot_health"] == "healthy"
    assert first_promoted["observed_requests"] == 3
    assert first_promoted["v2_served"] == 3
    assert first_promoted["legacy_fallbacks"] == 0


def test_hold_e_rollback_forced_mantem_metadados_do_piloto(monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    started_at = datetime.now(timezone.utc).replace(microsecond=0)

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", "33=pilot_enabled")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES",
        "33:feed=hold,33:thread=rollback_forced",
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", "33")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_PILOT_PROMOTED_SINCE",
        started_at.isoformat().replace("+00:00", "Z"),
    )
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT",
        started_at.isoformat().replace("+00:00", "Z"),
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS", "24")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_SOURCE", "seed_dev_demo_company")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_NOTE", "first_local_pilot")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")
    payload = get_mobile_v2_rollout_operational_summary()
    by_surface = {
        (row["tenant_key"], row["surface"]): row for row in payload["tenant_surface_states"]
    }

    assert rollout.feed.hold is True
    assert rollout.feed.promoted_since == started_at.isoformat().replace("+00:00", "Z")
    assert rollout.feed.pilot_health_status == "attention"
    assert rollout.thread.rollback_forced is True
    assert rollout.thread.pilot_health_status == "rollback_forced"
    assert by_surface[("33", "feed")]["promotion_source"] == "seed_dev_demo_company"
    assert by_surface[("33", "feed")]["health_status"] == "attention"
    assert by_surface[("33", "thread")]["rollback_forced"] is True
    assert by_surface[("33", "thread")]["health_status"] == "rollback_forced"
