from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.shared.database import (
    Empresa,
    Laudo,
    MensagemLaudo,
    StatusRevisao,
    TipoMensagem,
)
from app.v2.mobile_organic_validation import (
    clear_mobile_v2_organic_validation_session_for_tests,
    get_mobile_v2_organic_validation_summary,
    record_mobile_v2_organic_human_checkpoint,
    resolve_demo_mobile_organic_validation_targets,
    start_mobile_v2_organic_validation_session,
)
from app.v2.mobile_rollout_metrics import clear_mobile_v2_rollout_metrics_for_tests
from tests.regras_rotas_criticas_support import SENHA_PADRAO


def _configure_demo_human_validation(ambiente_critico, monkeypatch) -> str:
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
            setor_industrial="Human Ack Feed",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Human ack feed target",
        )
        laudo_thread = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Human Ack Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Human ack thread target",
        )
        banco.add_all([laudo_feed, laudo_thread])
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_thread.id,
                remetente_id=ambiente_critico["ids"]["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem segura para human ack.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()
    return tenant_key


def _login_mobile_inspetor(client) -> dict[str, str]:
    resposta = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def test_ack_rejeitado_sem_sessao_ativa(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    tenant_key = _configure_demo_human_validation(ambiente_critico, monkeypatch)
    client = ambiente_critico["client"]
    headers = _login_mobile_inspetor(client)
    targets = resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)

    resposta = client.post(
        "/app/api/mobile/v2/organic-validation/ack",
        headers=headers,
        json={
            "session_id": "orgv_inactive0001",
            "surface": "feed",
            "target_id": list(targets["feed"])[0],
            "checkpoint_kind": "rendered",
            "delivery_mode": "v2",
        },
    )

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "organic_validation_ack_session_inactive"


def test_ack_aceito_via_endpoint_e_deduplicado(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    tenant_key = _configure_demo_human_validation(ambiente_critico, monkeypatch)
    client = ambiente_critico["client"]
    headers = _login_mobile_inspetor(client)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    assert started.session is not None
    targets = resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)
    target_id = list(targets["thread"])[0]

    payload = {
        "session_id": started.session.session_id,
        "surface": "thread",
        "target_id": target_id,
        "checkpoint_kind": "rendered",
        "delivery_mode": "v2",
    }
    primeira = client.post(
        "/app/api/mobile/v2/organic-validation/ack",
        headers={
            **headers,
            "X-Tariel-Mobile-V2-Capabilities-Version": "2026-03-26.09j",
            "X-Tariel-Mobile-V2-Rollout-Bucket": "12",
        },
        json=payload,
    )
    segunda = client.post(
        "/app/api/mobile/v2/organic-validation/ack",
        headers=headers,
        json=payload,
    )

    assert primeira.status_code == 200
    assert primeira.json()["duplicate"] is False
    assert primeira.json()["checkpoint"]["surface"] == "thread"
    assert primeira.json()["checkpoint"]["target_id"] == target_id
    assert segunda.status_code == 200
    assert segunda.json()["duplicate"] is True

    summary = get_mobile_v2_organic_validation_summary()
    assert summary.human_confirmed_count == 1
    thread_summary = next(
        item
        for item in summary.human_confirmed_surface_summaries
        if item.surface == "thread"
    )
    assert thread_summary.human_confirmed_targets == (target_id,)


def test_ack_rejeitado_para_tenant_nao_elegivel(ambiente_critico, monkeypatch) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    clear_mobile_v2_organic_validation_session_for_tests()
    tenant_key = _configure_demo_human_validation(ambiente_critico, monkeypatch)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    assert started.session is not None
    targets = resolve_demo_mobile_organic_validation_targets(tenant_key=tenant_key)

    with pytest.raises(PermissionError) as exc:
        record_mobile_v2_organic_human_checkpoint(
            tenant_key=str(ambiente_critico["ids"]["empresa_b"]),
            session_id=started.session.session_id,
            surface="feed",
            target_id=list(targets["feed"])[0],
            checkpoint_kind="rendered",
            delivery_mode="v2",
        )

    assert str(exc.value) == "organic_validation_ack_tenant_not_eligible"
