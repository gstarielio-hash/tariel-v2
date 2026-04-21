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
    clear_mobile_v2_organic_validation_session_for_tests,
    get_mobile_v2_organic_validation_summary,
    record_mobile_v2_organic_human_checkpoint,
    resolve_demo_mobile_organic_validation_targets,
    start_mobile_v2_organic_validation_session,
)
from app.v2.mobile_rollout import MOBILE_V2_CAPABILITIES_VERSION
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    record_mobile_v2_public_read,
)


def _configure_demo_human_coverage(ambiente_critico, monkeypatch) -> str:
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
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_WINDOW_MINUTES", "30")
    monkeypatch.setenv("TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MIN_REQUESTS_PER_SURFACE", "3")
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
            setor_industrial="Human Coverage Feed",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Human coverage feed target",
        )
        laudo_thread = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Human Coverage Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Human coverage thread target",
        )
        banco.add_all([laudo_feed, laudo_thread])
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_thread.id,
                remetente_id=ambiente_critico["ids"]["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem segura para coverage humana.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()
    return tenant_key


def _record_organic_reads(tenant_key: str, surface: str, count: int) -> int:
    session = organic_validation.get_mobile_v2_organic_validation_session()
    assert session is not None
    targets = resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)
    target_id = list(targets[surface])[0]
    for _ in range(count):
        record_mobile_v2_public_read(
            tenant_key=tenant_key,
            endpoint=surface,
            reason="promoted",
            source="surface_state_override",
            rollout_bucket=12,
            capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
            traffic_class="organic_validation",
            validation_session_id=session.session_id,
            target_ids=[target_id],
        )
    return target_id


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
                "+00:00",
                "Z",
            ),
            active=session.active,
            ended_at=session.ended_at,
            trigger_source=session.trigger_source,
            stop_source=session.stop_source,
            baselines=session.baselines,
        ),
    )


def test_candidate_permanece_false_sem_human_confirmed(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    tenant_key = _configure_demo_human_coverage(ambiente_critico, monkeypatch)
    start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")

    _record_organic_reads(tenant_key, "feed", 3)
    _record_organic_reads(tenant_key, "thread", 3)
    _force_window_elapsed(monkeypatch)

    summary = get_mobile_v2_organic_validation_summary()

    assert summary.outcome == "healthy"
    assert summary.candidate_ready_for_real_tenant is False
    assert summary.human_confirmed_required_coverage_met is False


def test_candidate_sobe_quando_human_confirmed_cobre_feed_e_thread(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    tenant_key = _configure_demo_human_coverage(ambiente_critico, monkeypatch)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    assert started.session is not None

    feed_target = _record_organic_reads(tenant_key, "feed", 3)
    thread_target = _record_organic_reads(tenant_key, "thread", 3)
    record_mobile_v2_organic_human_checkpoint(
        tenant_key=tenant_key,
        session_id=started.session.session_id,
        surface="feed",
        target_id=feed_target,
        checkpoint_kind="rendered",
        delivery_mode="v2",
    )
    record_mobile_v2_organic_human_checkpoint(
        tenant_key=tenant_key,
        session_id=started.session.session_id,
        surface="thread",
        target_id=thread_target,
        checkpoint_kind="rendered",
        delivery_mode="v2",
    )
    _force_window_elapsed(monkeypatch)

    summary = get_mobile_v2_organic_validation_summary()
    by_surface = {item.surface: item for item in summary.surface_summaries}

    assert summary.outcome == "candidate_ready_for_real_tenant"
    assert summary.candidate_ready_for_real_tenant is True
    assert summary.human_confirmed_required_coverage_met is True
    assert by_surface["feed"].candidate_ready_for_real_tenant is True
    assert by_surface["thread"].candidate_ready_for_real_tenant is True
    assert by_surface["feed"].human_surface_summary.human_confirmed_targets == (
        feed_target,
    )
    assert by_surface["thread"].human_surface_summary.human_confirmed_targets == (
        thread_target,
    )


def test_summary_humana_permanece_sem_conteudo_sensivel(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    tenant_key = _configure_demo_human_coverage(ambiente_critico, monkeypatch)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    assert started.session is not None

    feed_target = _record_organic_reads(tenant_key, "feed", 3)
    record_mobile_v2_organic_human_checkpoint(
        tenant_key=tenant_key,
        session_id=started.session.session_id,
        surface="feed",
        target_id=feed_target,
        checkpoint_kind="rendered",
        delivery_mode="v2",
    )

    payload = get_mobile_v2_organic_validation_summary().to_public_payload()

    assert payload["human_confirmed_count"] == 1
    assert isinstance(payload["human_confirmed_surface_summaries"], list)
    serialized = str(payload).lower()
    assert "conteudo" not in serialized
    assert "mensagem segura" not in serialized
