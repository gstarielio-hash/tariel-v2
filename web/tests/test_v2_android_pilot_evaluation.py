from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.v2.mobile_rollout import (
    MOBILE_V2_CAPABILITIES_VERSION,
    resolve_mobile_v2_rollout_state_for_tenant_key,
)
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
    record_mobile_v2_legacy_fallback,
    record_mobile_v2_public_read,
)


def _configure_promoted_pilot(
    monkeypatch,
    *,
    tenant_key: str = "33",
    window_started_at: datetime | None = None,
) -> None:
    started_at = window_started_at or datetime.now(timezone.utc).replace(microsecond=0)
    timestamp = started_at.isoformat().replace("+00:00", "Z")

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", f"{tenant_key}=pilot_enabled")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES",
        f"{tenant_key}:feed=promoted,{tenant_key}:thread=promoted",
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", tenant_key)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROMOTED_SINCE", timestamp)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT", timestamp)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS", "24")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_SOURCE", "seed_dev_demo_company")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_NOTE", "first_local_pilot")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MIN_REQUESTS", "3")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_FALLBACK_RATE_PERCENT", "15")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_VISIBILITY_VIOLATIONS", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_PARSE_ERRORS", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_HTTP_FAILURES", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_REQUIRE_FULL_WINDOW", "1")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_PILOT_ALLOW_CANDIDATE_WITHOUT_WINDOW_ELAPSED",
        "0",
    )


def _record_surface_activity(
    *,
    tenant_key: str,
    surface: str,
    v2_served: int = 0,
    fallback_reasons: tuple[str, ...] = (),
) -> None:
    for _ in range(v2_served):
        record_mobile_v2_public_read(
            tenant_key=tenant_key,
            endpoint=surface,
            reason="promoted",
            source="surface_state_override",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        )
    for reason in fallback_reasons:
        record_mobile_v2_legacy_fallback(
            tenant_key=tenant_key,
            endpoint=surface,
            reason=reason,
            source="v2_read",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        )


def test_pilot_evaluation_sem_trafego_fica_insufficient_evidence(monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_promoted_pilot(
        monkeypatch,
        window_started_at=datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=2),
    )

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")

    assert rollout.feed.pilot_evaluation is not None
    assert rollout.feed.pilot_evaluation.window_elapsed is True
    assert rollout.feed.pilot_evaluation.pilot_outcome == "insufficient_evidence"
    assert rollout.thread.pilot_evaluation is not None
    assert rollout.thread.pilot_evaluation.pilot_outcome == "insufficient_evidence"
    assert rollout.pilot_evaluation is not None
    assert rollout.pilot_evaluation.pilot_outcome == "insufficient_evidence"
    assert rollout.pilot_evaluation.evidence_level == "none"
    assert rollout.pilot_evaluation.candidate_for_real_tenant is False


def test_pilot_evaluation_observing_com_volume_parcial_antes_do_fim_da_janela(
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_promoted_pilot(monkeypatch)
    _record_surface_activity(tenant_key="33", surface="feed", v2_served=2)
    _record_surface_activity(tenant_key="33", surface="thread", v2_served=1)

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")

    assert rollout.feed.pilot_evaluation is not None
    assert rollout.feed.pilot_evaluation.pilot_outcome == "observing"
    assert rollout.thread.pilot_evaluation is not None
    assert rollout.thread.pilot_evaluation.pilot_outcome == "observing"
    assert rollout.pilot_evaluation is not None
    assert rollout.pilot_evaluation.pilot_outcome == "observing"
    assert rollout.pilot_evaluation.evaluation_reason == "surface_still_under_observation"


def test_pilot_evaluation_healthy_quando_estavel_sem_promover_tenant_real(
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_promoted_pilot(monkeypatch, tenant_key="44")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_REQUIRE_FULL_WINDOW", "0")

    _record_surface_activity(tenant_key="44", surface="feed", v2_served=3)
    _record_surface_activity(tenant_key="44", surface="thread", v2_served=3)

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("44")

    assert rollout.feed.pilot_evaluation is not None
    assert rollout.feed.pilot_evaluation.pilot_outcome == "healthy"
    assert rollout.thread.pilot_evaluation is not None
    assert rollout.thread.pilot_evaluation.pilot_outcome == "healthy"
    assert rollout.pilot_evaluation is not None
    assert rollout.pilot_evaluation.pilot_outcome == "healthy"
    assert rollout.pilot_evaluation.candidate_for_real_tenant is False


def test_pilot_evaluation_attention_quando_fallbacks_ficam_abaixo_do_limite(
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_promoted_pilot(monkeypatch)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_REQUIRE_FULL_WINDOW", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_FALLBACK_RATE_PERCENT", "50")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_HTTP_FAILURES", "1")

    _record_surface_activity(
        tenant_key="33",
        surface="feed",
        v2_served=3,
        fallback_reasons=("http_error",),
    )
    _record_surface_activity(tenant_key="33", surface="thread", v2_served=3)

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")

    assert rollout.feed.pilot_evaluation is not None
    assert rollout.feed.pilot_evaluation.pilot_outcome == "attention"
    assert rollout.feed.pilot_evaluation.fallback_reason_breakdown == (("http_error", 1),)
    assert rollout.pilot_evaluation is not None
    assert rollout.pilot_evaluation.pilot_outcome == "attention"


def test_pilot_evaluation_hold_recommended_quando_fallback_rate_estoura_apos_janela(
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_promoted_pilot(
        monkeypatch,
        window_started_at=datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=2),
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_MAX_FALLBACK_RATE_PERCENT", "10")

    _record_surface_activity(
        tenant_key="33",
        surface="feed",
        v2_served=3,
        fallback_reasons=("http_error",),
    )
    _record_surface_activity(tenant_key="33", surface="thread", v2_served=3)

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")

    assert rollout.feed.pilot_evaluation is not None
    assert rollout.feed.pilot_evaluation.pilot_outcome == "hold_recommended"
    assert rollout.feed.pilot_evaluation.requires_hold is True
    assert rollout.pilot_evaluation is not None
    assert rollout.pilot_evaluation.pilot_outcome == "hold_recommended"


def test_pilot_evaluation_rollback_recommended_quando_parse_error_aparece(
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_promoted_pilot(monkeypatch)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_REQUIRE_FULL_WINDOW", "0")

    _record_surface_activity(tenant_key="33", surface="feed", v2_served=3)
    _record_surface_activity(
        tenant_key="33",
        surface="thread",
        v2_served=3,
        fallback_reasons=("parse_error",),
    )

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")

    assert rollout.thread.pilot_evaluation is not None
    assert rollout.thread.pilot_evaluation.pilot_outcome == "rollback_recommended"
    assert rollout.thread.pilot_evaluation.requires_rollback is True
    assert rollout.pilot_evaluation is not None
    assert rollout.pilot_evaluation.pilot_outcome == "rollback_recommended"


def test_pilot_evaluation_candidate_for_real_tenant_so_apos_janela_com_duas_superficies_saudaveis(
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_promoted_pilot(
        monkeypatch,
        window_started_at=datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=2),
    )
    _record_surface_activity(tenant_key="33", surface="feed", v2_served=3)
    _record_surface_activity(tenant_key="33", surface="thread", v2_served=3)

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")
    summary = get_mobile_v2_rollout_operational_summary()
    by_surface = {
        (row["tenant_key"], row["surface"]): row for row in summary["tenant_surface_states"]
    }
    by_tenant = {row["tenant_key"]: row for row in summary["tenant_rollout_states"]}

    assert rollout.feed.pilot_evaluation is not None
    assert rollout.feed.pilot_evaluation.pilot_outcome == "candidate_for_real_tenant"
    assert rollout.thread.pilot_evaluation is not None
    assert rollout.thread.pilot_evaluation.pilot_outcome == "candidate_for_real_tenant"
    assert rollout.pilot_evaluation is not None
    assert rollout.pilot_evaluation.pilot_outcome == "candidate_for_real_tenant"
    assert rollout.pilot_evaluation.candidate_for_real_tenant is True
    assert summary["pilot_evaluation_thresholds"]["require_full_window"] is True
    assert by_surface[("33", "feed")]["candidate_for_real_tenant"] is True
    assert by_tenant["33"]["pilot_outcome"] == "candidate_for_real_tenant"
    assert summary["first_promoted_tenant"]["pilot_outcome"] == "candidate_for_real_tenant"
    serialized = str(summary).lower()
    assert "conteudo" not in serialized
    assert "mensagem" not in serialized
