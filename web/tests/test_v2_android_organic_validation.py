from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import app.v2.mobile_organic_validation as organic_validation
from app.shared.database import (
    Empresa,
    Laudo,
    MensagemLaudo,
    StatusRevisao,
    TipoMensagem,
)
from app.v2.mobile_organic_validation import (
    MobileV2OrganicValidationSession,
    get_mobile_v2_organic_validation_summary,
    resolve_demo_mobile_organic_validation_targets,
    start_mobile_v2_organic_validation_session,
    stop_mobile_v2_organic_validation_session,
)
from app.v2.mobile_rollout import MOBILE_V2_CAPABILITIES_VERSION
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    record_mobile_v2_legacy_fallback,
    record_mobile_v2_public_read,
)


def _configure_demo_organic_validation(ambiente_critico, monkeypatch) -> str:
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
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_NOTE", "organic_validation_demo")
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
        laudo_feed = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Organic Validation Feed",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Organic feed target",
        )
        laudo_thread = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Organic Validation Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Organic thread target",
        )
        banco.add_all([laudo_feed, laudo_thread])
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_thread.id,
                remetente_id=ambiente_critico["ids"]["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem segura para validacao organica.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()
    return tenant_key


def _validation_session_payload(tenant_key: str, surface: str) -> tuple[str, list[int]]:
    session = organic_validation.get_mobile_v2_organic_validation_session()
    assert session is not None
    targets = resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)
    return session.session_id, list(targets.get(surface, ())[:1])


def _record_organic(
    *,
    tenant_key: str,
    surface: str,
    v2_served: int = 0,
    fallback_reasons: tuple[str, ...] = (),
) -> None:
    session_id, target_ids = _validation_session_payload(tenant_key, surface)
    for _ in range(v2_served):
        record_mobile_v2_public_read(
            tenant_key=tenant_key,
            endpoint=surface,
            reason="promoted",
            source="surface_state_override",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            traffic_class="organic_validation",
            validation_session_id=session_id,
            target_ids=target_ids,
        )
    for reason in fallback_reasons:
        record_mobile_v2_legacy_fallback(
            tenant_key=tenant_key,
            endpoint=surface,
            reason=reason,
            source="v2_read",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            traffic_class="legacy_fallback_from_validation",
            validation_session_id=session_id,
            target_ids=target_ids,
        )


def _record_probe(
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
            probe_label="pilot_probe",
            probe_source="demo_controlled",
        )
    for reason in fallback_reasons:
        record_mobile_v2_legacy_fallback(
            tenant_key=tenant_key,
            endpoint=surface,
            reason=reason,
            source="v2_read",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            probe_label="pilot_probe",
            probe_source="demo_controlled",
        )


def _force_window_elapsed(monkeypatch) -> None:
    session = organic_validation.get_mobile_v2_organic_validation_session()
    assert session is not None
    elapsed_start = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=2)
    monkeypatch.setattr(
        organic_validation,
        "_session_state",
        MobileV2OrganicValidationSession(
            tenant_key=session.tenant_key,
            tenant_label=session.tenant_label,
            session_id=session.session_id,
            surfaces=session.surfaces,
            started_at=elapsed_start.isoformat().replace("+00:00", "Z"),
            expires_at=(elapsed_start + timedelta(minutes=30)).isoformat().replace(
                "+00:00", "Z"
            ),
            active=session.active,
            ended_at=session.ended_at,
            trigger_source=session.trigger_source,
            stop_source=session.stop_source,
            baselines=session.baselines,
        ),
    )


def test_organic_validation_start_e_stop_controlados(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    tenant_key = _configure_demo_organic_validation(ambiente_critico, monkeypatch)

    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    stopped = stop_mobile_v2_organic_validation_session(remote_host="127.0.0.1")

    assert started.active is True
    assert started.session is not None
    assert started.session.tenant_key == tenant_key
    assert started.session.session_id.startswith("orgv_")
    assert started.outcome == "insufficient_evidence"
    assert stopped.active is False
    assert stopped.ended_at is not None
    assert stopped.candidate_ready_for_real_tenant is False


def test_organic_validation_bloqueia_host_nao_local(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_demo_organic_validation(ambiente_critico, monkeypatch)

    try:
        start_mobile_v2_organic_validation_session(remote_host="8.8.8.8")
    except PermissionError as exc:
        assert str(exc) == "organic_validation_requires_local_host"
    else:
        raise AssertionError("Era esperado bloqueio para host nao local.")


def test_organic_validation_ignora_probe_e_permanece_insufficient_evidence(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    tenant_key = _configure_demo_organic_validation(ambiente_critico, monkeypatch)
    start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")

    _record_probe(tenant_key=tenant_key, surface="feed", v2_served=5)
    _record_probe(tenant_key=tenant_key, surface="thread", v2_served=5)

    summary = get_mobile_v2_organic_validation_summary()

    assert summary.outcome == "insufficient_evidence"
    assert summary.organic_requests_v2 == 0
    assert summary.probe_vs_organic_evidence["probe_requests_v2_since_start"] == 10
    assert summary.probe_vs_organic_evidence["evidence_source"] == "probe_only"
    assert summary.candidate_ready_for_real_tenant is False


def test_organic_validation_fica_observing_com_uso_organico_parcial(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    tenant_key = _configure_demo_organic_validation(ambiente_critico, monkeypatch)
    start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")

    _record_organic(tenant_key=tenant_key, surface="feed", v2_served=3)
    _record_organic(tenant_key=tenant_key, surface="thread", v2_served=1)

    summary = get_mobile_v2_organic_validation_summary()
    by_surface = {item.surface: item for item in summary.surface_summaries}

    assert summary.outcome == "observing"
    assert by_surface["feed"].outcome == "healthy"
    assert by_surface["thread"].outcome == "observing"
    assert summary.surface_coverage_summary["covered_surfaces"] == ["feed"]
    assert summary.candidate_ready_for_real_tenant is False


def test_organic_validation_hold_e_rollback_recommended_aparecem_quando_necessario(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    tenant_key = _configure_demo_organic_validation(ambiente_critico, monkeypatch)
    start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")

    _record_organic(
        tenant_key=tenant_key,
        surface="feed",
        v2_served=3,
        fallback_reasons=("http_error",),
    )
    _record_organic(
        tenant_key=tenant_key,
        surface="thread",
        v2_served=3,
        fallback_reasons=("parse_error",),
    )

    summary = get_mobile_v2_organic_validation_summary()
    by_surface = {item.surface: item for item in summary.surface_summaries}

    assert by_surface["feed"].outcome == "hold_recommended"
    assert by_surface["thread"].outcome == "rollback_recommended"
    assert summary.outcome == "rollback_recommended"


def test_organic_validation_candidate_ready_so_quando_duas_superficies_e_janela_sao_atendidas(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    tenant_key = _configure_demo_organic_validation(ambiente_critico, monkeypatch)
    start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")

    _record_organic(tenant_key=tenant_key, surface="feed", v2_served=3)
    _record_organic(tenant_key=tenant_key, surface="thread", v2_served=3)

    before_elapsed = get_mobile_v2_organic_validation_summary()
    _force_window_elapsed(monkeypatch)
    after_elapsed = get_mobile_v2_organic_validation_summary()

    assert before_elapsed.outcome == "healthy"
    assert before_elapsed.candidate_ready_for_real_tenant is False
    assert after_elapsed.outcome == "healthy"
    assert after_elapsed.candidate_ready_for_real_tenant is False
    assert after_elapsed.human_confirmed_required_coverage_met is False
    assert after_elapsed.surface_coverage_summary["both_surfaces_covered"] is True
