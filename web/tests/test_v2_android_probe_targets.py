from __future__ import annotations

import uuid
from decimal import Decimal

from app.shared.database import Empresa, Laudo, MensagemLaudo, StatusRevisao, TipoMensagem
from app.v2.mobile_probe import resolve_demo_mobile_probe_targets


def _prepare_demo_tenant(ambiente_critico, *, with_thread_messages: bool = True) -> dict[str, int]:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    with SessionLocal() as banco:
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.nome_fantasia = "Empresa Demo (DEV)"
        empresa.cnpj = "00000000000000"

        laudo_feed = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="Probe Feed",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Probe feed",
        )
        laudo_thread = Laudo(
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            setor_industrial="Probe Thread",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Probe thread",
        )
        banco.add_all([laudo_feed, laudo_thread])
        banco.flush()

        if with_thread_messages:
            banco.add(
                MensagemLaudo(
                    laudo_id=laudo_thread.id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Mensagem segura para thread probe.",
                    custo_api_reais=Decimal("0.0000"),
                )
            )
        banco.commit()
        return {
            "feed_laudo_id": int(laudo_feed.id),
            "thread_laudo_id": int(laudo_thread.id),
        }


def test_resolve_demo_mobile_probe_targets_descobre_alvos_seguros_do_tenant_demo(
    ambiente_critico,
    monkeypatch,
) -> None:
    created = _prepare_demo_tenant(ambiente_critico)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", str(ambiente_critico["ids"]["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_PROBE_TARGET_LIMIT", "3")

    targets = resolve_demo_mobile_probe_targets()

    assert targets.ready is True
    assert targets.tenant_key == str(ambiente_critico["ids"]["empresa_a"])
    assert targets.tenant_label == "Empresa Demo (DEV)"
    assert targets.inspector_user_id == ambiente_critico["ids"]["inspetor_a"]
    assert created["feed_laudo_id"] in targets.feed_laudo_ids
    assert created["thread_laudo_id"] in targets.thread_laudo_ids
    assert targets.detail == "probe_targets_resolved"


def test_resolve_demo_mobile_probe_targets_bloqueia_quando_thread_nao_tem_alvo_elegivel(
    ambiente_critico,
    monkeypatch,
) -> None:
    created = _prepare_demo_tenant(ambiente_critico, with_thread_messages=False)
    monkeypatch.setenv("TARIEL_V2_ANDROID_PILOT_TENANT_KEY", str(ambiente_critico["ids"]["empresa_a"]))

    targets = resolve_demo_mobile_probe_targets()

    assert targets.ready is False
    assert created["feed_laudo_id"] in targets.feed_laudo_ids
    assert created["thread_laudo_id"] not in targets.thread_laudo_ids
    assert targets.detail == "probe_targets_missing"
