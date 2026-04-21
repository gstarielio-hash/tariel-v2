from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import main
from app.shared.database import NivelAcesso, Usuario
from app.shared.security import obter_usuario_html
from app.v2.mobile_rollout import (
    MOBILE_V2_CAPABILITIES_VERSION,
    resolve_mobile_v2_rollout_state_for_tenant_key,
)
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
    record_mobile_v2_capabilities_check,
    record_mobile_v2_legacy_fallback,
    record_mobile_v2_public_read,
)


def _record_clean_pilot_feed(*, tenant_key: str, requests: int) -> None:
    for _ in range(requests):
        record_mobile_v2_capabilities_check(
            tenant_key=tenant_key,
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            reason="tenant_allowlisted",
            source="tenant_allowlist",
            feed_enabled=True,
            feed_reason="pilot_enabled",
            thread_enabled=True,
            thread_reason="pilot_enabled",
        )
        record_mobile_v2_public_read(
            tenant_key=tenant_key,
            endpoint="feed",
            reason="pilot_enabled",
            source="tenant_allowlist",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        )


def test_rollout_state_marca_candidate_for_promotion_quando_feed_esta_estavel(monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST", "33")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PROMOTION_MIN_REQUESTS", "3")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PROMOTION_MAX_FALLBACK_RATE_PERCENT", "20")

    _record_clean_pilot_feed(tenant_key="33", requests=3)

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")

    assert rollout.rollout_state == "pilot_enabled"
    assert rollout.feed.state == "candidate_for_promotion"
    assert rollout.feed.promotion_readiness.candidate_for_promotion is True
    assert rollout.feed.promotion_readiness.observed_requests == 3
    assert rollout.thread.state == "pilot_enabled"


def test_rollout_state_bloqueia_promocao_quando_parse_ou_visibilidade_falham(monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST", "33")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PROMOTION_MIN_REQUESTS", "2")

    _record_clean_pilot_feed(tenant_key="33", requests=2)
    record_mobile_v2_legacy_fallback(
        tenant_key="33",
        endpoint="feed",
        reason="visibility_violation",
        source="v2_read",
        rollout_bucket=12,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
    )

    rollout = resolve_mobile_v2_rollout_state_for_tenant_key("33")

    assert rollout.feed.state == "pilot_enabled"
    assert rollout.feed.promotion_readiness.candidate_for_promotion is False
    assert "parse_or_visibility_errors_detected" in rollout.feed.promotion_readiness.reasons


def test_summary_operacional_expoe_estado_por_tenant_superficie_sem_dados_sensiveis(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", "33=pilot_enabled")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES",
        "33:thread=rollback_forced",
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PROMOTION_MIN_REQUESTS", "2")

    _record_clean_pilot_feed(tenant_key="33", requests=2)
    payload = get_mobile_v2_rollout_operational_summary()

    assert payload["promotion_thresholds"]["min_requests"] == 2
    assert "mobile_v2_closure_summary" in payload
    assert any(
        item["tenant_key"] == "33" and item["rollout_state"] == "pilot_enabled"
        for item in payload["tenant_rollout_states"]
    )
    assert any(
        item["tenant_key"] == "33"
        and item["surface"] == "feed"
        and item["surface_state"] == "candidate_for_promotion"
        and item["candidate_for_promotion"] is True
        for item in payload["tenant_surface_states"]
    )
    assert any(
        item["tenant_key"] == "33"
        and item["surface"] == "thread"
        and item["surface_state"] == "rollback_forced"
        and item["rollback_forced"] is True
        for item in payload["tenant_surface_states"]
    )
    serialized = str(payload).lower()
    assert "conteudo" not in serialized
    assert "mensagem" not in serialized

    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]
    main.app.dependency_overrides[obter_usuario_html] = lambda: Usuario(
        id=ids["admin_a"],
        empresa_id=ids["empresa_a"],
        nivel_acesso=NivelAcesso.DIRETORIA.value,
        email="admin@empresa-a.test",
    )
    resposta = client.get("/admin/api/mobile-v2-rollout/summary")
    main.app.dependency_overrides.pop(obter_usuario_html, None)

    assert resposta.status_code == 200
    payload_http = resposta.json()
    assert "tenant_rollout_states" in payload_http
    assert "tenant_surface_states" in payload_http
    assert "mobile_v2_closure_summary" in payload_http


def test_closure_summary_usa_evidencia_duravel_da_lane_oficial_quando_estado_vivo_esta_volatil(
    monkeypatch,
    tmp_path: Path,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0)
    artifact_dir = tmp_path / "mobile_artifact"
    artifact_dir.mkdir()
    (artifact_dir / "final_report.md").write_text(
        "\n".join(
            [
                "pilot_outcome_after: candidate_for_real_tenant",
                "organic_validation_outcome_after: observing",
                "candidate_ready_for_real_tenant_after: False",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    state_file = tmp_path / "mobile_pilot_lane_status.json"
    state_file.write_text(
        """
{
  "generatedAt": "__GENERATED_AT__",
  "status": "ok",
  "result": "success_human_confirmed",
  "operatorRunOutcome": "completed_successfully",
  "operatorRunReason": "required_surfaces_completed",
  "feedCovered": true,
  "threadCovered": true,
  "environmentFailureSignals": [],
  "artifactDir": "__ARTIFACT_DIR__"
}
        """
        .replace("__ARTIFACT_DIR__", str(artifact_dir))
        .replace("__GENERATED_AT__", generated_at.isoformat().replace("+00:00", "Z")),
        encoding="utf-8",
    )

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", "33")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", "33=promoted")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")
    monkeypatch.setenv("TARIEL_MOBILE_ACCEPTANCE_STATE_FILE", str(state_file))
    monkeypatch.setenv("TARIEL_MOBILE_ACCEPTANCE_MAX_AGE_HOURS", "168")

    payload = get_mobile_v2_rollout_operational_summary()

    assert payload["mobile_v2_closure_summary"]["mobile_v2_architecture_status"] == (
        "closed_with_guardrails"
    )
    assert payload["mobile_v2_closure_summary"]["mobile_v2_architecture_reason"] == (
        "durable_mobile_acceptance_evidence"
    )
    assert payload["mobile_v2_durable_acceptance_evidence"]["valid_for_closure"] is True
