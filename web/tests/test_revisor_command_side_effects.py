from __future__ import annotations

import asyncio
from types import SimpleNamespace

import app.domains.revisor.command_side_effects as command_side_effects
from app.domains.revisor.command_handlers import (
    ReviewDecisionCommand,
    ReviewPendencyStatusCommand,
    ReviewReplyCommand,
    ReviewReplyAttachmentCommand,
    ReviewWhisperReplyCommand,
)
from app.domains.revisor.service_contracts import (
    AvaliacaoLaudoResult,
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


def test_run_review_decision_side_effects_notifica_e_audita(monkeypatch) -> None:
    chamadas: dict[str, list[dict[str, object]]] = {"notify": [], "audit": []}

    async def _fake_notify(**kwargs):
        chamadas["notify"].append(kwargs)

    def _fake_audit(**kwargs):
        chamadas["audit"].append(kwargs)

    monkeypatch.setattr(command_side_effects, "notificar_inspetor_sse", _fake_notify)
    monkeypatch.setattr(command_side_effects, "_registrar_auditoria_revisor_segura", _fake_audit)

    asyncio.run(
        command_side_effects.run_review_decision_side_effects(
            command=ReviewDecisionCommand(
                request=_build_request(),
                banco=object(),
                usuario=_build_user(),
                laudo_id=55,
                acao="aprovar",
                motivo="",
                resposta_api=True,
                modo_schemathesis=False,
            ),
            result=AvaliacaoLaudoResult(
                laudo_id=55,
                acao="aprovar",
                status_revisao="aprovado",
                motivo="",
                modo_schemathesis=False,
                inspetor_id=21,
                mensagem_id=901,
                texto_notificacao_inspetor="ok",
            ),
        )
    )

    assert chamadas["notify"][0]["inspetor_id"] == 21
    assert chamadas["notify"][0]["mensagem_id"] == 901
    assert chamadas["audit"][0]["acao"] == "mesa_laudo_avaliado"
    assert chamadas["audit"][0]["payload"]["status_revisao"] == "aprovado"


def test_run_review_decision_side_effects_pula_schemathesis(monkeypatch) -> None:
    chamadas = {"notify": 0, "audit": 0}

    async def _fake_notify(**_kwargs):
        chamadas["notify"] += 1

    def _fake_audit(**_kwargs):
        chamadas["audit"] += 1

    monkeypatch.setattr(command_side_effects, "notificar_inspetor_sse", _fake_notify)
    monkeypatch.setattr(command_side_effects, "_registrar_auditoria_revisor_segura", _fake_audit)

    asyncio.run(
        command_side_effects.run_review_decision_side_effects(
            command=ReviewDecisionCommand(
                request=_build_request(),
                banco=object(),
                usuario=_build_user(),
                laudo_id=55,
                acao="aprovar",
                motivo="",
                resposta_api=True,
                modo_schemathesis=True,
            ),
            result=AvaliacaoLaudoResult(
                laudo_id=55,
                acao="aprovar",
                status_revisao="aprovado",
                motivo="",
                modo_schemathesis=True,
            ),
        )
    )

    assert chamadas == {"notify": 0, "audit": 0}


def test_run_review_reply_side_effects_notifica_payload_mensagem(monkeypatch) -> None:
    chamadas: dict[str, list[dict[str, object]]] = {"notify": [], "audit": []}

    async def _fake_notify(**kwargs):
        chamadas["notify"].append(kwargs)

    def _fake_audit(**kwargs):
        chamadas["audit"].append(kwargs)

    monkeypatch.setattr(command_side_effects, "notificar_inspetor_sse", _fake_notify)
    monkeypatch.setattr(command_side_effects, "_registrar_auditoria_revisor_segura", _fake_audit)

    asyncio.run(
        command_side_effects.run_review_reply_side_effects(
            command=ReviewReplyCommand(
                banco=object(),
                usuario=_build_user(),
                laudo_id=55,
                texto="texto teste",
                referencia_mensagem_id=33,
            ),
            result=RespostaChatResult(
                laudo_id=55,
                inspetor_id=21,
                mensagem_id=901,
                referencia_mensagem_id=33,
                texto_notificacao="texto teste",
                mensagem_payload={"id": 901, "texto": "texto teste"},
            ),
        )
    )

    assert chamadas["notify"][0]["referencia_mensagem_id"] == 33
    assert chamadas["notify"][0]["mensagem"] == {"id": 901, "texto": "texto teste"}
    assert chamadas["audit"][0]["acao"] == "mesa_resposta_enviada"


def test_run_review_reply_attachment_side_effects_notifica_e_audita(monkeypatch) -> None:
    chamadas: dict[str, list[dict[str, object]]] = {"notify": [], "audit": []}

    async def _fake_notify(**kwargs):
        chamadas["notify"].append(kwargs)

    def _fake_audit(**kwargs):
        chamadas["audit"].append(kwargs)

    monkeypatch.setattr(command_side_effects, "notificar_inspetor_sse", _fake_notify)
    monkeypatch.setattr(command_side_effects, "_registrar_auditoria_revisor_segura", _fake_audit)

    asyncio.run(
        command_side_effects.run_review_reply_attachment_side_effects(
            command=ReviewReplyAttachmentCommand(
                banco=object(),
                usuario=_build_user(),
                laudo_id=55,
                nome_arquivo="anexo.pdf",
                mime_type="application/pdf",
                conteudo_arquivo=b"pdf",
                texto="segue anexo",
                referencia_mensagem_id=44,
            ),
            result=RespostaChatAnexoResult(
                laudo_id=55,
                inspetor_id=21,
                mensagem_id=902,
                referencia_mensagem_id=44,
                texto_notificacao="anexo teste",
                mensagem_payload={"id": 902},
            ),
        )
    )

    assert chamadas["notify"][0]["referencia_mensagem_id"] == 44
    assert chamadas["notify"][0]["mensagem"] == {"id": 902}
    assert chamadas["audit"][0]["acao"] == "mesa_resposta_com_anexo"
    assert chamadas["audit"][0]["payload"]["nome_arquivo"] == "anexo.pdf"


def test_run_review_whisper_reply_side_effects_publica_ws_sse_e_audita(monkeypatch) -> None:
    chamadas: dict[str, list[dict[str, object]]] = {"ws": [], "sse": [], "audit": [], "log": []}

    async def _fake_ws(**kwargs):
        chamadas["ws"].append(kwargs)

    async def _fake_sse(**kwargs):
        chamadas["sse"].append(kwargs)

    def _fake_audit(**kwargs):
        chamadas["audit"].append(kwargs)

    monkeypatch.setattr(command_side_effects, "notificar_whisper_resposta_revisor", _fake_ws)
    monkeypatch.setattr(command_side_effects, "notificar_inspetor_sse", _fake_sse)
    monkeypatch.setattr(command_side_effects, "_registrar_auditoria_revisor_segura", _fake_audit)
    monkeypatch.setattr(
        command_side_effects,
        "logger",
        SimpleNamespace(info=lambda *args, **kwargs: chamadas["log"].append({"args": args, "kwargs": kwargs})),
    )

    asyncio.run(
        command_side_effects.run_review_whisper_reply_side_effects(
            command=ReviewWhisperReplyCommand(
                banco=object(),
                usuario=_build_user(),
                laudo_id=77,
                mensagem="whisper",
                destinatario_id=18,
                referencia_mensagem_id=11,
            ),
            result=WhisperRespostaResult(
                laudo_id=77,
                destinatario_id=18,
                mensagem_id=903,
                referencia_mensagem_id=11,
                preview="whisper",
            ),
        )
    )

    assert chamadas["ws"][0]["destinatario_id"] == 18
    assert chamadas["sse"][0]["tipo"] == "whisper_eng"
    assert chamadas["audit"][0]["acao"] == "mesa_whisper_enviado"
    assert len(chamadas["log"]) == 1


def test_run_review_pendency_status_side_effects_notifica_e_audita(monkeypatch) -> None:
    chamadas: dict[str, list[dict[str, object]]] = {"notify": [], "audit": []}

    async def _fake_notify(**kwargs):
        chamadas["notify"].append(kwargs)

    def _fake_audit(**kwargs):
        chamadas["audit"].append(kwargs)

    monkeypatch.setattr(command_side_effects, "notificar_inspetor_sse", _fake_notify)
    monkeypatch.setattr(command_side_effects, "_registrar_auditoria_revisor_segura", _fake_audit)

    asyncio.run(
        command_side_effects.run_review_pendency_status_side_effects(
            command=ReviewPendencyStatusCommand(
                banco=object(),
                usuario=_build_user(),
                laudo_id=88,
                mensagem_id=321,
                lida=True,
            ),
            result=PendenciaMesaResult(
                laudo_id=88,
                mensagem_id=321,
                lida=True,
                resolvida_por_id=71,
                resolvida_por_nome="Revisor Teste",
                resolvida_em="2026-04-02T10:00:00+00:00",
                pendencias_abertas=0,
                inspetor_id=21,
                texto_notificacao="Pendência resolvida",
            ),
        )
    )

    assert chamadas["notify"][0]["tipo"] == "pendencia_mesa"
    assert chamadas["audit"][0]["acao"] == "mesa_pendencia_atualizada"
    assert chamadas["audit"][0]["payload"]["pendencias_abertas"] == 0
