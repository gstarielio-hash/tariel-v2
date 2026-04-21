from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.shared.database import Empresa, Laudo, MensagemLaudo, StatusRevisao, TipoMensagem
from app.v2.mobile_organic_validation import (
    clear_mobile_v2_organic_validation_session_for_tests,
    resolve_demo_mobile_organic_validation_targets,
    start_mobile_v2_organic_validation_session,
)
from app.v2.mobile_rollout import MOBILE_V2_CAPABILITIES_VERSION
from app.v2.mobile_rollout_metrics import (
    clear_mobile_v2_rollout_metrics_for_tests,
    get_mobile_v2_rollout_operational_summary,
    record_mobile_v2_public_read,
)


def _configure_demo_served_accounting(ambiente_critico, monkeypatch) -> str:
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
            setor_industrial="Served Accounting Feed",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Served accounting feed target",
        )
        laudo_thread = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Served Accounting Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Served accounting thread target",
        )
        banco.add_all([laudo_feed, laudo_thread])
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_thread.id,
                remetente_id=ambiente_critico["ids"]["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem segura para served accounting.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()
    return tenant_key


def test_recent_events_expoem_surface_v2_servida_com_sessao_e_target(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    tenant_key = _configure_demo_served_accounting(ambiente_critico, monkeypatch)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    assert started.session is not None
    targets = resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)
    feed_target = list(targets["feed"])[0]
    thread_target = list(targets["thread"])[0]

    record_mobile_v2_public_read(
        tenant_key=tenant_key,
        endpoint="feed",
        reason="promoted",
        source="surface_state_override",
        rollout_bucket=44,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        traffic_class="organic_validation",
        validation_session_id=started.session.session_id,
        target_ids=[feed_target],
    )
    record_mobile_v2_public_read(
        tenant_key=tenant_key,
        endpoint="thread",
        reason="promoted",
        source="surface_state_override",
        rollout_bucket=44,
        capabilities_version=MOBILE_V2_CAPABILITIES_VERSION,
        traffic_class="organic_validation",
        validation_session_id=started.session.session_id,
        target_ids=[thread_target],
    )

    summary = get_mobile_v2_rollout_operational_summary()
    recent_events = summary["recent_events"]
    thread_event = next(
        item
        for item in recent_events
        if item["kind"] == "v2_served" and item["endpoint"] == "thread"
    )
    feed_event = next(
        item
        for item in recent_events
        if item["kind"] == "v2_served" and item["endpoint"] == "feed"
    )

    assert feed_event["traffic_class"] == "organic_validation"
    assert feed_event["validation_session_id"] == started.session.session_id
    assert feed_event["target_ids"] == [str(feed_target)]
    assert thread_event["traffic_class"] == "organic_validation"
    assert thread_event["validation_session_id"] == started.session.session_id
    assert thread_event["target_ids"] == [str(thread_target)]
