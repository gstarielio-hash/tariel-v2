from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

from app.shared.database import (
    Empresa,
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    StatusRevisao,
    TipoMensagem,
)
from app.v2.mobile_organic_validation import (
    resolve_mobile_v2_organic_request_classification,
    start_mobile_v2_organic_validation_session,
    stop_mobile_v2_organic_validation_session,
)
from app.v2.mobile_rollout import resolve_mobile_v2_capabilities_for_user
from app.v2.mobile_rollout_metrics import clear_mobile_v2_rollout_metrics_for_tests


def _configure_demo_signal(ambiente_critico, monkeypatch) -> str:
    tenant_key = str(ambiente_critico["ids"]["empresa_a"])
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
            setor_industrial="Organic Signal Feed",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Organic signal feed target",
        )
        laudo_thread = Laudo(
            empresa_id=ambiente_critico["ids"]["empresa_a"],
            usuario_id=ambiente_critico["ids"]["inspetor_a"],
            setor_industrial="Organic Signal Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Organic signal thread target",
        )
        banco.add_all([laudo_feed, laudo_thread])
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_thread.id,
                remetente_id=ambiente_critico["ids"]["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem segura para sinal organico.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        banco.commit()
    return tenant_key


def _build_user(*, empresa_id: int, user_id: int = 17) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        empresa_id=empresa_id,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def test_capabilities_expoe_session_id_e_targets_da_validacao_organica(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_demo_signal(ambiente_critico, monkeypatch)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    session = started.session
    assert session is not None

    capabilities = resolve_mobile_v2_capabilities_for_user(
        _build_user(empresa_id=ambiente_critico["ids"]["empresa_a"])
    )

    assert capabilities.organic_validation_active is True
    assert capabilities.organic_validation_session_id == session.session_id
    assert set(capabilities.organic_validation_surfaces) == {"feed", "thread"}
    assert capabilities.organic_validation_targets_ready is True
    assert {item["surface"] for item in capabilities.organic_validation_target_suggestions} == {
        "feed",
        "thread",
    }


def test_capabilities_nao_expoem_sinal_organico_para_tenant_fora_do_demo(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    _configure_demo_signal(ambiente_critico, monkeypatch)
    start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")

    capabilities = resolve_mobile_v2_capabilities_for_user(
        _build_user(empresa_id=ambiente_critico["ids"]["empresa_b"], user_id=29)
    )

    assert capabilities.organic_validation_active is False
    assert capabilities.organic_validation_session_id is None
    assert capabilities.organic_validation_surfaces == ()
    assert capabilities.organic_validation_target_suggestions == ()


def test_classificacao_aceita_session_id_ativo_e_rejeita_sessao_encerrada(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_mobile_v2_rollout_metrics_for_tests()
    tenant_key = _configure_demo_signal(ambiente_critico, monkeypatch)
    started = start_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    session = started.session
    assert session is not None

    active_classification = resolve_mobile_v2_organic_request_classification(
        tenant_key=tenant_key,
        endpoint="feed",
        usage_mode="organic_validation",
        validation_session_id=session.session_id,
        is_probe=False,
        is_fallback=False,
    )
    assert active_classification.traffic_class == "organic_validation"
    assert active_classification.counts_for_validation is True

    stopped = stop_mobile_v2_organic_validation_session(remote_host="127.0.0.1")
    assert stopped.active is False
    stale_classification = resolve_mobile_v2_organic_request_classification(
        tenant_key=tenant_key,
        endpoint="feed",
        usage_mode="organic_validation",
        validation_session_id=session.session_id,
        is_probe=False,
        is_fallback=False,
    )
    assert stale_classification.traffic_class == "organic_general"
    assert stale_classification.counts_for_validation is False
