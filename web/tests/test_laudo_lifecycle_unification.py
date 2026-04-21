from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.domains.chat.laudo_state_helpers import (
    aplicar_feedback_mesa_ao_laudo,
    aplicar_decisao_mesa_ao_laudo,
    aplicar_finalizacao_inspetor_ao_laudo,
    aplicar_reabertura_manual_ao_laudo,
    laudo_deve_sinalizar_reabertura_pendente_apos_feedback_mesa,
    laudo_permite_transicao_decisao_mesa,
    laudo_permite_transicao_finalizacao_inspetor,
    obter_detalhe_bloqueio_avaliacao_mesa,
    obter_detalhe_bloqueio_edicao_inspetor,
    resolver_alvo_reabertura_manual_laudo,
    resolver_autoridade_lifecycle_laudo,
)
from app.shared.database import StatusRevisao
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_from_legacy
from tests.regras_rotas_criticas_support import (
    _criar_laudo,
    _login_app_inspetor,
    _login_revisor,
)


def _laudo_stub(
    *,
    status_revisao: str,
    pending_reopen: bool = False,
    reaberto_em: datetime | None = None,
    revisado_por: int | None = None,
    dados_formulario: dict[str, object] | None = None,
    report_pack_draft_json: dict[str, object] | None = None,
    nome_arquivo_pdf: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=101,
        empresa_id=17,
        status_revisao=status_revisao,
        reabertura_pendente_em=(
            datetime.now(timezone.utc) if pending_reopen else None
        ),
        reaberto_em=reaberto_em,
        revisado_por=revisado_por,
        dados_formulario=dados_formulario,
        report_pack_draft_json=report_pack_draft_json,
        nome_arquivo_pdf=nome_arquivo_pdf,
        entry_mode_effective="evidence_first" if dados_formulario else None,
        parecer_ia=None,
        guided_inspection_draft_json=None,
        primeira_mensagem="Historico visivel",
        setor_industrial="Industrial",
        tipo_template="nr13_inspecao_caldeira",
        pinado=False,
        criado_em=datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
        encerrado_pelo_inspetor_em=None,
        atualizado_em=None,
        motivo_rejeicao=None,
    )


def _snapshot_stub(
    laudo: SimpleNamespace,
    *,
    estado: str,
    status_card: str,
    permite_reabrir: bool,
):
    return build_technical_case_status_snapshot_from_legacy(
        tenant_id=getattr(laudo, "empresa_id", ""),
        legacy_payload={
            "estado": estado,
            "laudo_id": int(getattr(laudo, "id", 0) or 0) or None,
            "status_card": status_card,
            "permite_reabrir": permite_reabrir,
        },
        laudo=laudo,
    )


def test_autoridade_lifecycle_unificada_define_regras_base() -> None:
    rascunho = resolver_autoridade_lifecycle_laudo(
        _laudo_stub(status_revisao=StatusRevisao.RASCUNHO.value)
    )
    aguardando = resolver_autoridade_lifecycle_laudo(
        _laudo_stub(status_revisao=StatusRevisao.AGUARDANDO.value)
    )
    ajustes = resolver_autoridade_lifecycle_laudo(
        _laudo_stub(
            status_revisao=StatusRevisao.AGUARDANDO.value,
            pending_reopen=True,
        )
    )

    assert rascunho.allows_inspector_edit is True
    assert rascunho.allows_mesa_review is False
    assert aguardando.allows_inspector_edit is False
    assert aguardando.allows_mesa_review is True
    assert (
        aguardando.inspector_block_detail(surface="chat")
        == "Laudo aguardando avaliação não pode receber novas mensagens."
    )
    assert (
        aguardando.inspector_block_detail(surface="mesa_reply")
        == "Laudo aguardando avaliação não aceita novas mensagens até ser reaberto."
    )
    assert (
        ajustes.inspector_block_detail(surface="chat")
        == "Laudo com ajustes da mesa precisa ser reaberto antes de continuar."
    )
    assert (
        ajustes.inspector_block_detail(surface="mesa_reply")
        == "Laudo com ajustes da mesa precisa ser reaberto antes de responder."
    )


def test_aplicar_feedback_mesa_sinaliza_reabertura_pendente_quando_exigido(
    monkeypatch,
) -> None:
    laudo = _laudo_stub(status_revisao=StatusRevisao.AGUARDANDO.value)
    timestamp = datetime(2026, 4, 18, 15, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(
        "app.domains.chat.laudo_state_helpers.resolver_autoridade_mutacao_caso_tecnico",
        lambda *_args, **_kwargs: SimpleNamespace(
            should_signal_pending_reopen_from_mesa_feedback=lambda: True
        ),
    )

    returned = aplicar_feedback_mesa_ao_laudo(
        banco=object(),
        laudo=laudo,
        occurred_at=timestamp,
    )

    assert returned == timestamp
    assert laudo.reabertura_pendente_em == timestamp
    assert laudo.atualizado_em == timestamp


def test_aplicar_feedback_mesa_so_toca_timestamp_quando_nao_reabre(
    monkeypatch,
) -> None:
    laudo = _laudo_stub(status_revisao=StatusRevisao.AGUARDANDO.value)
    timestamp = datetime(2026, 4, 18, 15, 35, tzinfo=timezone.utc)

    monkeypatch.setattr(
        "app.domains.chat.laudo_state_helpers.resolver_autoridade_mutacao_caso_tecnico",
        lambda *_args, **_kwargs: SimpleNamespace(
            should_signal_pending_reopen_from_mesa_feedback=lambda: False
        ),
    )

    returned = aplicar_feedback_mesa_ao_laudo(
        banco=object(),
        laudo=laudo,
        occurred_at=timestamp,
    )

    assert returned == timestamp
    assert laudo.reabertura_pendente_em is None
    assert laudo.atualizado_em == timestamp


def test_rotas_inspetor_consumem_mesma_autoridade_de_lifecycle(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta_chat = client.post(
        "/app/api/chat",
        headers={"X-CSRF-Token": csrf},
        json={
            "mensagem": "Nova mensagem bloqueada pelo lifecycle.",
            "laudo_id": laudo_id,
            "historico": [],
        },
    )
    assert resposta_chat.status_code == 400
    assert (
        resposta_chat.json()["detail"]
        == obter_detalhe_bloqueio_edicao_inspetor(
            _laudo_stub(status_revisao=StatusRevisao.AGUARDANDO.value),
            surface="chat",
        )
    )

    resposta_mesa = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf},
        json={"texto": "Tentativa de responder a mesa fora da fase editavel."},
    )
    assert resposta_mesa.status_code == 400
    assert (
        resposta_mesa.json()["detail"]
        == obter_detalhe_bloqueio_edicao_inspetor(
            _laudo_stub(status_revisao=StatusRevisao.AGUARDANDO.value),
            surface="mesa_reply",
        )
    )


def test_mesa_consume_mesma_autoridade_de_lifecycle_para_avaliar(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_revisor(client, "revisor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        f"/revisao/api/laudo/{laudo_id}/avaliar",
        data={"acao": "aprovar", "motivo": "", "csrf_token": csrf},
    )

    assert resposta.status_code == 400
    assert (
        resposta.json()["detail"]
        == obter_detalhe_bloqueio_avaliacao_mesa(
            _laudo_stub(status_revisao=StatusRevisao.RASCUNHO.value)
        )
    )


def test_autoridade_mutacao_resolve_targets_criticos_do_caso(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.domains.chat.laudo_state_helpers.laudo_tem_interacao",
        lambda *_args, **_kwargs: True,
    )

    collecting_autonomous = _laudo_stub(
        status_revisao=StatusRevisao.RASCUNHO.value,
        dados_formulario={"identificacao": {"tag": "A-01"}},
        report_pack_draft_json={
            "quality_gates": {
                "final_validation_mode": "mobile_autonomous",
            }
        },
    )
    awaiting_mesa = _laudo_stub(
        status_revisao=StatusRevisao.AGUARDANDO.value,
    )
    correction_pending = _laudo_stub(
        status_revisao=StatusRevisao.AGUARDANDO.value,
        pending_reopen=True,
    )
    issued_case = _laudo_stub(
        status_revisao=StatusRevisao.APROVADO.value,
        nome_arquivo_pdf="laudo-final.pdf",
    )

    assert laudo_permite_transicao_finalizacao_inspetor(
        None,
        collecting_autonomous,
        target_status="aprovado",
    ) is True
    assert laudo_permite_transicao_decisao_mesa(
        None,
        awaiting_mesa,
        target_status="aprovado",
    ) is True
    assert (
        laudo_deve_sinalizar_reabertura_pendente_apos_feedback_mesa(
            None,
            awaiting_mesa,
        )
        is True
    )
    assert (
        resolver_alvo_reabertura_manual_laudo(None, correction_pending)
        == "laudo_em_coleta"
    )
    assert (
        resolver_alvo_reabertura_manual_laudo(None, issued_case)
        == "devolvido_para_correcao"
    )


def test_helpers_compartilhados_mantem_lifecycle_canonico_em_sincronia() -> None:
    reopen_anchor = datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)
    finalize_at = datetime(2026, 4, 15, 12, 30, tzinfo=timezone.utc)
    mesa_at = datetime(2026, 4, 15, 12, 45, tzinfo=timezone.utc)
    reopen_at = datetime(2026, 4, 15, 13, 0, tzinfo=timezone.utc)

    laudo_reenviado = _laudo_stub(
        status_revisao=StatusRevisao.RASCUNHO.value,
        reaberto_em=reopen_anchor,
        dados_formulario={"identificacao": {"tag": "A-01"}},
        report_pack_draft_json={
            "quality_gates": {
                "final_validation_mode": "mesa_required",
            }
        },
    )
    aplicar_finalizacao_inspetor_ao_laudo(
        laudo_reenviado,
        target_status="aguardando_mesa",
        occurred_at=finalize_at,
    )
    snapshot_reenviado = _snapshot_stub(
        laudo_reenviado,
        estado="aguardando",
        status_card="aguardando",
        permite_reabrir=False,
    )
    assert laudo_reenviado.reaberto_em is None
    assert laudo_reenviado.atualizado_em == finalize_at
    assert snapshot_reenviado.case_lifecycle_status == "aguardando_mesa"

    laudo_aprovado = _laudo_stub(
        status_revisao=StatusRevisao.AGUARDANDO.value,
        reaberto_em=reopen_anchor,
    )
    aplicar_decisao_mesa_ao_laudo(
        laudo_aprovado,
        target_status="aprovado",
        reviewer_id=9,
        occurred_at=mesa_at,
    )
    snapshot_aprovado = _snapshot_stub(
        laudo_aprovado,
        estado="aprovado",
        status_card="aprovado",
        permite_reabrir=True,
    )
    assert snapshot_aprovado.case_lifecycle_status == "aprovado"
    assert laudo_aprovado.reabertura_pendente_em is None
    assert laudo_aprovado.reaberto_em is None
    assert laudo_aprovado.atualizado_em == mesa_at

    laudo_devolvido = _laudo_stub(
        status_revisao=StatusRevisao.AGUARDANDO.value,
    )
    aplicar_decisao_mesa_ao_laudo(
        laudo_devolvido,
        target_status="devolvido_para_correcao",
        reviewer_id=11,
        rejection_reason="Complementar a foto da placa.",
        occurred_at=mesa_at,
    )
    snapshot_devolvido = _snapshot_stub(
        laudo_devolvido,
        estado="ajustes",
        status_card="ajustes",
        permite_reabrir=True,
    )
    assert snapshot_devolvido.case_lifecycle_status == "devolvido_para_correcao"
    assert laudo_devolvido.motivo_rejeicao == "Complementar a foto da placa."
    assert laudo_devolvido.atualizado_em == mesa_at

    laudo_reaberto = _laudo_stub(
        status_revisao=StatusRevisao.REJEITADO.value,
        pending_reopen=True,
    )
    aplicar_reabertura_manual_ao_laudo(
        laudo_reaberto,
        target_status="laudo_em_coleta",
        reopened_at=reopen_at,
    )
    snapshot_reaberto = _snapshot_stub(
        laudo_reaberto,
        estado="relatorio_ativo",
        status_card="aberto",
        permite_reabrir=False,
    )
    assert snapshot_reaberto.case_lifecycle_status == "devolvido_para_correcao"
    assert laudo_reaberto.status_revisao == StatusRevisao.RASCUNHO.value
    assert laudo_reaberto.reabertura_pendente_em is None
    assert laudo_reaberto.atualizado_em == reopen_at
