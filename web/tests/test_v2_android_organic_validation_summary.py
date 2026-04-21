from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.shared.database import Empresa, NivelAcesso, Usuario
from app.shared.security import obter_usuario_html
import main
from app.v2.mobile_organic_validation import (
    resolve_demo_mobile_organic_validation_targets,
    start_mobile_v2_organic_validation_session,
)
from app.v2.mobile_rollout import MOBILE_V2_CAPABILITIES_VERSION
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
    record_mobile_v2_public_read,
)


def _configure_demo_summary_rollout(ambiente_critico, monkeypatch) -> str:
    tenant_key = str(ambiente_critico["ids"]["empresa_a"])
    started_at = (
        datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=2)
    ).isoformat().replace("+00:00", "Z")

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ENABLED", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES", f"{tenant_key}=pilot_enabled")
    monkeypatch.setenv(
        "TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES",
        f"{tenant_key}:feed=promoted,{tenant_key}:thread=promoted",
    )
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", tenant_key)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROMOTED_SINCE", started_at)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT", started_at)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS", "24")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_SOURCE", "seed_dev_demo_company")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_NOTE", "organic_summary_demo")
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_WINDOW_MINUTES", "30")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MIN_REQUESTS_PER_SURFACE", "3")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_FALLBACK_RATE_PERCENT", "15")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_VISIBILITY_VIOLATIONS", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_PARSE_ERRORS", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_HTTP_FAILURES", "0")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_REQUIRE_FULL_WINDOW", "1")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_TARGET_LIMIT", "100")

    SessionLocal = ambiente_critico["SessionLocal"]
    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ambiente_critico["ids"]["empresa_a"])
        assert empresa is not None
        empresa.nome_fantasia = "Empresa Demo (DEV)"
        empresa.cnpj = "00000000000000"
        banco.commit()
    return tenant_key


def test_summary_expoe_validacao_organica_sem_dados_sensiveis(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    tenant_key = _configure_demo_summary_rollout(ambiente_critico, monkeypatch)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    session = started.session
    assert session is not None
    targets = resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)
    feed_target_ids = list(targets.get("feed", ())[:1])
    thread_target_ids = list(targets.get("thread", ())[:1])

    record_mobile_v2_public_read(
        tenant_key=tenant_key,
        endpoint="feed",
        reason="promoted",
        source="surface_state_override",
        rollout_bucket=12,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        traffic_class="organic_validation",
        validation_session_id=session.session_id,
        target_ids=feed_target_ids,
    )
    record_mobile_v2_public_read(
        tenant_key=tenant_key,
        endpoint="feed",
        reason="promoted",
        source="surface_state_override",
        rollout_bucket=12,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        probe_label="pilot_probe",
        probe_source="demo_controlled",
        target_ids=feed_target_ids,
    )
    record_mobile_v2_public_read(
        tenant_key=tenant_key,
        endpoint="thread",
        reason="promoted",
        source="surface_state_override",
        rollout_bucket=12,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        traffic_class="organic_validation",
        validation_session_id=session.session_id,
        target_ids=thread_target_ids,
    )

    summary = get_mobile_v2_rollout_operational_summary()
    tenant_row = next(
        row for row in summary["tenant_rollout_states"] if row["tenant_key"] == tenant_key
    )
    feed_row = next(
        row
        for row in summary["tenant_surface_states"]
        if row["tenant_key"] == tenant_key and row["surface"] == "feed"
    )
    first_promoted = summary["first_promoted_tenant"]

    assert summary["organic_validation_active"] is True
    assert summary["organic_validation_outcome"] == "observing"
    assert summary["probe_vs_organic_evidence"]["evidence_source"] == "mixed"
    assert summary["organic_validation_session"]["session_id"] == session.session_id
    assert tenant_row["organic_validation_active"] is True
    assert tenant_row["organic_validation_outcome"] == "observing"
    assert tenant_row["probe_vs_organic_evidence"]["probe_ignored_for_validation"] is True
    assert feed_row["organic_validation_requests_v2"] == 1
    assert feed_row["organic_validation_outcome"] == "observing"
    assert isinstance(feed_row["organic_validation_suggested_target_ids"], list)
    assert first_promoted["organic_validation_active"] is True
    assert first_promoted["candidate_ready_for_real_tenant"] is False
    serialized = str(summary).lower()
    assert "conteudo" not in serialized
    assert "mensagem" not in serialized


def test_rotas_admin_start_e_stop_da_validacao_organica(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_demo_summary_rollout(ambiente_critico, monkeypatch)
    client = ambiente_critico["client"]

    assert client.post("/admin/api/mobile-v2-rollout/organic-validation/start").status_code == 401

    main.app.dependency_overrides[obter_usuario_html] = lambda: Usuario(
        id=ambiente_critico["ids"]["admin_a"],
        empresa_id=ambiente_critico["ids"]["empresa_a"],
        nivel_acesso=NivelAcesso.DIRETORIA.value,
        email="admin@empresa-a.test",
    )
    try:
        start_response = client.post("/admin/api/mobile-v2-rollout/organic-validation/start")
        stop_response = client.post("/admin/api/mobile-v2-rollout/organic-validation/stop")
    finally:
        main.app.dependency_overrides.pop(obter_usuario_html, None)

    assert start_response.status_code == 200
    assert start_response.json()["organic_validation_active"] is True
    assert stop_response.status_code == 200
    assert stop_response.json()["organic_validation_active"] is False
    assert stop_response.json()["organic_validation_ended_at"] is not None
