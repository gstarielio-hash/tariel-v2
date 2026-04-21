from __future__ import annotations

from app.v2.mobile_rollout import (
    MobileV2PromotionReadiness,
    MobileV2PromotionThresholds,
    MobileV2SurfaceState,
)


def test_surface_state_summary_payload_preenche_defaults_sem_janela_ou_avaliacao() -> None:
    readiness = MobileV2PromotionReadiness(
        surface="feed",
        candidate_for_promotion=False,
        observed_requests=0,
        v2_served=0,
        legacy_fallbacks=0,
        rollout_denied=0,
        parse_errors=0,
        visibility_errors=0,
        service_errors=0,
        fallback_rate=0.0,
        reasons=(),
        legacy_fallback_reasons=(),
        rollout_denied_reasons=(),
        thresholds=MobileV2PromotionThresholds(
            min_requests=10,
            max_fallback_rate_percent=15,
            max_service_errors=1,
            max_parse_visibility_errors=0,
        ),
    )
    state = MobileV2SurfaceState(
        surface="feed",
        configured_state="pilot_enabled",
        state="pilot_enabled",
        enabled=True,
        reason="tenant_allowlisted",
        source="tenant_allowlist",
        endpoint_allowed=True,
        promotion_readiness=readiness,
    )

    payload = state.to_summary_payload(
        tenant_key="33",
        rollout_state="pilot_enabled",
    )

    assert payload["tenant_key"] == "33"
    assert payload["surface"] == "feed"
    assert payload["candidate_for_promotion"] is False
    assert payload["promotion_readiness"]["thresholds"]["min_requests"] == 10
    assert payload["promoted_since"] is None
    assert payload["health_status"] == "not_applicable"
    assert payload["pilot_outcome"] is None
    assert payload["evaluation_thresholds"] == {}
