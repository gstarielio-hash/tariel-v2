from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.domains.revisor.command_handlers as command_handlers
from app.domains.revisor.command_handlers import (
    ReviewCoverageReturnCommand,
    ReviewDecisionCommand,
    ReviewPendencyStatusCommand,
    ReviewReplyAttachmentCommand,
    ReviewReplyCommand,
    ReviewWhisperReplyCommand,
    handle_review_coverage_return_command,
    handle_review_decision_command,
    handle_review_pendency_status_command,
    handle_review_reply_attachment_command,
    handle_review_reply_command,
    handle_review_whisper_reply_command,
)
from app.domains.revisor.service_contracts import (
    AvaliacaoLaudoResult,
    CoverageReturnRequestResult,
    PendenciaMesaResult,
    RespostaChatAnexoResult,
    RespostaChatResult,
    WhisperRespostaResult,
)


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=71,
        empresa_id=9,
        nome="Revisor Teste",
        nome_completo="Revisor Teste",
    )


def _build_request() -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(),
        headers={},
        scope={},
        method="POST",
        client=SimpleNamespace(host="testclient"),
    )


def test_handle_review_reply_command_delega_para_servico(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    esperado = RespostaChatResult(
        laudo_id=55,
        inspetor_id=21,
        mensagem_id=901,
        referencia_mensagem_id=33,
        texto_notificacao="texto teste",
    )

    def _fake(*args, **kwargs):
        capturado["args"] = args
        capturado["kwargs"] = kwargs
        return esperado

    monkeypatch.setattr(command_handlers, "registrar_resposta_chat_revisor", _fake)

    resultado = handle_review_reply_command(
        ReviewReplyCommand(
            banco=object(),
            usuario=_build_user(),
            laudo_id=55,
            texto="texto teste",
            referencia_mensagem_id=33,
        )
    )

    assert resultado == esperado
    assert capturado["kwargs"]["laudo_id"] == 55
    assert capturado["kwargs"]["empresa_id"] == 9
    assert capturado["kwargs"]["revisor_id"] == 71
    assert capturado["kwargs"]["revisor_nome"] == "Revisor Teste"


def test_handle_review_reply_attachment_command_delega_para_servico(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    esperado = RespostaChatAnexoResult(
        laudo_id=55,
        inspetor_id=21,
        mensagem_id=902,
        referencia_mensagem_id=44,
        texto_notificacao="anexo teste",
        mensagem_payload={"id": 902},
    )

    def _fake(*args, **kwargs):
        capturado["kwargs"] = kwargs
        return esperado

    monkeypatch.setattr(command_handlers, "registrar_resposta_chat_com_anexo_revisor", _fake)

    resultado = handle_review_reply_attachment_command(
        ReviewReplyAttachmentCommand(
            banco=object(),
            usuario=_build_user(),
            laudo_id=55,
            nome_arquivo="teste.pdf",
            mime_type="application/pdf",
            conteudo_arquivo=b"pdf",
            texto="anexo teste",
            referencia_mensagem_id=44,
        )
    )

    assert resultado == esperado
    assert capturado["kwargs"]["nome_arquivo"] == "teste.pdf"
    assert capturado["kwargs"]["mime_type"] == "application/pdf"
    assert capturado["kwargs"]["empresa_id"] == 9


def test_handle_review_whisper_reply_command_delega_para_servico(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    esperado = WhisperRespostaResult(
        laudo_id=77,
        destinatario_id=18,
        mensagem_id=903,
        referencia_mensagem_id=11,
        preview="whisper",
    )

    def _fake(*args, **kwargs):
        capturado["kwargs"] = kwargs
        return esperado

    monkeypatch.setattr(command_handlers, "registrar_whisper_resposta_revisor", _fake)

    resultado = handle_review_whisper_reply_command(
        ReviewWhisperReplyCommand(
            banco=object(),
            usuario=_build_user(),
            laudo_id=77,
            mensagem="whisper",
            destinatario_id=18,
            referencia_mensagem_id=11,
        )
    )

    assert resultado == esperado
    assert capturado["kwargs"]["destinatario_id"] == 18
    assert capturado["kwargs"]["empresa_id"] == 9


def test_handle_review_pendency_status_command_delega_para_servico(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    esperado = PendenciaMesaResult(
        laudo_id=88,
        mensagem_id=321,
        lida=True,
        resolvida_por_id=71,
        resolvida_por_nome="Revisor Teste",
        resolvida_em="2026-04-02T10:00:00+00:00",
        pendencias_abertas=0,
        inspetor_id=21,
        texto_notificacao="Pendência resolvida",
    )

    def _fake(*args, **kwargs):
        capturado["kwargs"] = kwargs
        return esperado

    monkeypatch.setattr(command_handlers, "atualizar_pendencia_mesa_revisor_status", _fake)

    resultado = handle_review_pendency_status_command(
        ReviewPendencyStatusCommand(
            banco=object(),
            usuario=_build_user(),
            laudo_id=88,
            mensagem_id=321,
            lida=True,
        )
    )

    assert resultado == esperado
    assert capturado["kwargs"]["mensagem_id"] == 321
    assert capturado["kwargs"]["revisor_id"] == 71


def test_handle_review_coverage_return_command_delega_para_servico(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    esperado = CoverageReturnRequestResult(
        laudo_id=88,
        inspetor_id=21,
        mensagem_id=654,
        evidence_key="slot:foto_placa",
        block_key="coverage_return:slot:foto_placa",
        texto_notificacao="refazer coverage",
        mensagem_payload={"id": 654},
    )

    def _fake(*args, **kwargs):
        capturado["kwargs"] = kwargs
        return esperado

    monkeypatch.setattr(command_handlers, "solicitar_refazer_item_coverage_revisor", _fake)

    resultado = handle_review_coverage_return_command(
        ReviewCoverageReturnCommand(
            banco=object(),
            usuario=_build_user(),
            laudo_id=88,
            evidence_key="slot:foto_placa",
            title="Foto da placa",
            kind="image_slot",
            required=True,
            source_status="missing",
            operational_status="irregular",
            mesa_status="not_reviewed",
            component_type="placa_identificacao",
            view_angle="close_up",
            severity="warning",
            summary="Foto borrada.",
            required_action="Reenviar foto nitida.",
            failure_reasons=["foto_borrada"],
        )
    )

    assert resultado == esperado
    assert capturado["kwargs"]["laudo_id"] == 88
    assert capturado["kwargs"]["empresa_id"] == 9
    assert capturado["kwargs"]["revisor_id"] == 71
    assert capturado["kwargs"]["evidence_key"] == "slot:foto_placa"


def test_handle_review_decision_command_delega_para_servico_quando_gate_desligado(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    esperado = AvaliacaoLaudoResult(
        laudo_id=66,
        acao="aprovar",
        status_revisao="aprovado",
        motivo="",
        modo_schemathesis=False,
        inspetor_id=12,
        mensagem_id=904,
        texto_notificacao_inspetor="ok",
    )

    monkeypatch.setattr(command_handlers, "v2_document_hard_gate_enabled", lambda: False)
    monkeypatch.setattr(command_handlers, "v2_document_soft_gate_enabled", lambda: False)

    def _fake(*args, **kwargs):
        capturado["kwargs"] = kwargs
        return esperado

    monkeypatch.setattr(command_handlers, "avaliar_laudo_revisor", _fake)

    resultado = handle_review_decision_command(
        ReviewDecisionCommand(
            request=_build_request(),
            banco=object(),
            usuario=_build_user(),
            laudo_id=66,
            acao="aprovar",
            motivo="",
            resposta_api=True,
            modo_schemathesis=False,
        )
    )

    assert resultado == esperado
    assert capturado["kwargs"]["laudo_id"] == 66
    assert capturado["kwargs"]["revisor_nome"] == "Revisor Teste"
    assert capturado["kwargs"]["acao"] == "aprovar"


def test_handle_review_decision_command_bloqueia_quando_hard_gate_bloqueia(monkeypatch) -> None:
    gate_result = SimpleNamespace(
        decision=SimpleNamespace(did_block=True),
        blocked_response_status=422,
    )

    monkeypatch.setattr(
        command_handlers,
        "_avaliar_gate_documental_decisao_revisor",
        lambda **_kwargs: (None, gate_result),
    )
    monkeypatch.setattr(
        command_handlers,
        "build_document_hard_gate_block_detail",
        lambda _result: {"erro": "bloqueado"},
    )

    with pytest.raises(HTTPException) as excinfo:
        handle_review_decision_command(
            ReviewDecisionCommand(
                request=_build_request(),
                banco=object(),
                usuario=_build_user(),
                laudo_id=66,
                acao="aprovar",
                motivo="",
                resposta_api=True,
                modo_schemathesis=False,
            )
        )

    assert excinfo.value.status_code == 422
    assert excinfo.value.detail == {"erro": "bloqueado"}
