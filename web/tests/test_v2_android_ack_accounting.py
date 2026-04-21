from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.shared.database import Empresa, Laudo, MensagemLaudo, StatusRevisao, TipoMensagem
from app.v2.mobile_organic_validation import (
    clear_mobile_v2_organic_validation_session_for_tests,
    get_mobile_v2_organic_validation_summary,
    record_mobile_v2_organic_human_checkpoint,
    resolve_demo_mobile_organic_validation_targets,
    start_mobile_v2_organic_validation_session,
)
from app.v2.mobile_rollout_metrics import clear_mobile_v2_rollout_metrics_for_tests


def _configure_demo_ack_accounting(ambiente_critico, monkeypatch) -> str:
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
        laudo_thread = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Ack Accounting Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Ack accounting thread target",
        )
        banco.add(laudo_thread)
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_thread.id,
                remetente_id=ambiente_critico["ids"]["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem segura para contabilizacao.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()
    return tenant_key


def test_summary_expoe_eventos_recentes_de_ack_aceito_duplicado_e_rejeitado(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    tenant_key = _configure_demo_ack_accounting(ambiente_critico, monkeypatch)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    assert started.session is not None
    target_id = list(
        resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)["thread"]
    )[0]

    accepted = record_mobile_v2_organic_human_checkpoint(
        tenant_key=tenant_key,
        session_id=started.session.session_id,
        surface="thread",
        target_id=target_id,
        checkpoint_kind="rendered",
        delivery_mode="v2",
        operator_run_id="oprv_ack123456",
        capabilities_version="2026-03-26.09m",
        rollout_bucket=44,
    )
    duplicate = record_mobile_v2_organic_human_checkpoint(
        tenant_key=tenant_key,
        session_id=started.session.session_id,
        surface="thread",
        target_id=target_id,
        checkpoint_kind="rendered",
        delivery_mode="v2",
        operator_run_id="oprv_ack123456",
        capabilities_version="2026-03-26.09m",
        rollout_bucket=44,
    )

    with pytest.raises(RuntimeError) as exc:
        record_mobile_v2_organic_human_checkpoint(
            tenant_key=tenant_key,
            session_id="orgv_sessao_errada",
            surface="thread",
            target_id=target_id,
            checkpoint_kind="rendered",
            delivery_mode="v2",
            operator_run_id="oprv_ack123456",
            capabilities_version="2026-03-26.09m",
            rollout_bucket=44,
        )

    assert accepted["duplicate"] is False
    assert duplicate["duplicate"] is True
    assert str(exc.value) == "organic_validation_ack_session_mismatch"

    payload = get_mobile_v2_organic_validation_summary().to_public_payload()
    recent_events = payload["human_ack_recent_events"]

    assert [item["status"] for item in recent_events[:3]] == [
        "rejected",
        "duplicate",
        "accepted",
    ]
    assert recent_events[0]["rejection_reason"] == "organic_validation_ack_session_mismatch"
    assert recent_events[1]["operator_run_id"] == "oprv_ack123456"
    assert recent_events[2]["surface"] == "thread"
    assert recent_events[2]["target_id"] == target_id
    assert payload["human_confirmed_count"] == 1
