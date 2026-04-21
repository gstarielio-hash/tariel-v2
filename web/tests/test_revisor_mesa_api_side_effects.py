from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.domains.revisor.base import DadosRespostaChat, DadosSolicitacaoCoverageReturn
from app.domains.revisor.service_contracts import AvaliacaoLaudoResult, CoverageReturnRequestResult, RespostaChatResult
from app.domains.revisor import mesa_api


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=71,
        empresa_id=9,
        nome="Revisor Teste",
        nome_completo="Revisor Teste",
    )


def _build_request(*, api: bool = True) -> SimpleNamespace:
    headers = {"X-CSRF-Token": "csrf"} if api else {}
    return SimpleNamespace(
        headers=headers,
        scope={},
        method="POST",
        client=SimpleNamespace(host="testclient"),
    )


def test_avaliar_laudo_delega_side_effects_para_executor(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    monkeypatch.setattr(mesa_api, "_validar_csrf", lambda *_args, **_kwargs: True)

    def _fake_handle(command):
        capturado["command"] = command
        return AvaliacaoLaudoResult(
            laudo_id=66,
            acao="aprovar",
            status_revisao="aprovado",
            motivo="",
            modo_schemathesis=False,
            inspetor_id=12,
            mensagem_id=904,
            texto_notificacao_inspetor="ok",
        )

    async def _fake_side_effects(*, command, result):
        capturado["side_effect_command"] = command
        capturado["side_effect_result"] = result

    monkeypatch.setattr(mesa_api, "handle_review_decision_command", _fake_handle)
    monkeypatch.setattr(mesa_api, "run_review_decision_side_effects", _fake_side_effects)

    resposta = asyncio.run(
        mesa_api.avaliar_laudo(
            laudo_id=66,
            request=_build_request(api=True),
            acao="aprovar",
            motivo="",
            csrf_token="",
            usuario=_build_user(),
            banco=object(),
        )
    )

    assert resposta.status_code == 200
    assert capturado["side_effect_command"] is capturado["command"]
    assert capturado["side_effect_result"].laudo_id == 66


def test_responder_chat_campo_delega_side_effects_para_executor(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    monkeypatch.setattr(mesa_api, "_validar_csrf", lambda *_args, **_kwargs: True)

    def _fake_handle(command):
        capturado["command"] = command
        return RespostaChatResult(
            laudo_id=55,
            inspetor_id=21,
            mensagem_id=901,
            referencia_mensagem_id=33,
            texto_notificacao="texto teste",
        )

    async def _fake_side_effects(*, command, result):
        capturado["side_effect_command"] = command
        capturado["side_effect_result"] = result

    monkeypatch.setattr(mesa_api, "handle_review_reply_command", _fake_handle)
    monkeypatch.setattr(mesa_api, "run_review_reply_side_effects", _fake_side_effects)

    resposta = asyncio.run(
        mesa_api.responder_chat_campo(
            laudo_id=55,
            dados=DadosRespostaChat(texto="texto teste", referencia_mensagem_id=33),
            request=_build_request(api=True),
            usuario=_build_user(),
            banco=object(),
        )
    )

    assert resposta.status_code == 200
    assert capturado["side_effect_command"] is capturado["command"]
    assert capturado["side_effect_result"].mensagem_id == 901


def test_solicitar_refazer_item_coverage_delega_side_effects_para_executor(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    monkeypatch.setattr(mesa_api, "_validar_csrf", lambda *_args, **_kwargs: True)

    def _fake_handle(command):
        capturado["command"] = command
        return CoverageReturnRequestResult(
            laudo_id=55,
            inspetor_id=21,
            mensagem_id=990,
            evidence_key="slot:foto_placa",
            block_key="coverage_return:slot:foto_placa",
            texto_notificacao="refazer coverage",
            mensagem_payload={"id": 990},
        )

    async def _fake_side_effects(*, command, result):
        capturado["side_effect_command"] = command
        capturado["side_effect_result"] = result

    monkeypatch.setattr(mesa_api, "handle_review_coverage_return_command", _fake_handle)
    monkeypatch.setattr(mesa_api, "run_review_coverage_return_side_effects", _fake_side_effects)

    resposta = asyncio.run(
        mesa_api.solicitar_refazer_item_coverage(
            laudo_id=55,
            dados=DadosSolicitacaoCoverageReturn(
                evidence_key="slot:foto_placa",
                title="Foto da placa",
                kind="image_slot",
                required=True,
                summary="Foto borrada.",
                failure_reasons=["foto_borrada"],
            ),
            request=_build_request(api=True),
            usuario=_build_user(),
            banco=object(),
        )
    )

    assert resposta.status_code == 200
    assert capturado["side_effect_command"] is capturado["command"]
    assert capturado["side_effect_result"].mensagem_id == 990
