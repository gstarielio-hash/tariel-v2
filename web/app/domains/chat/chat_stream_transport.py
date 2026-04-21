"""Transporte SSE do fluxo principal de chat do inspetor."""

from __future__ import annotations

import asyncio
import json
from contextvars import copy_context
from typing import Any

from fastapi.responses import StreamingResponse

from app.domains.chat.app_context import logger
from app.domains.chat.chat_runtime import (
    PREFIXO_CITACOES,
    PREFIXO_METADATA,
    PREFIXO_MODO_HUMANO,
    TIMEOUT_FILA_STREAM_SEGUNDOS,
    executor_stream,
)
from app.domains.chat.chat_runtime_support import salvar_mensagem_ia
from app.domains.chat.core_helpers import evento_sse
from app.domains.chat.mensagem_helpers import notificar_mesa_whisper
from app.domains.chat.chat_stream_support import ChatPersistedMessageContext
from nucleo.inspetor.confianca_ia import analisar_confianca_resposta_ia


def build_whisper_stream_response(
    *,
    stream_context: ChatPersistedMessageContext,
) -> StreamingResponse:
    async def gerador_humano():
        payload_inicial: dict[str, Any] = {"laudo_id": stream_context.laudo_id_atual}
        if stream_context.card_laudo_payload:
            payload_inicial["laudo_card"] = stream_context.card_laudo_payload
        yield evento_sse(payload_inicial)

        await notificar_mesa_whisper(
            empresa_id=stream_context.empresa_id_atual,
            laudo_id=stream_context.laudo_id_atual,
            inspetor_id=stream_context.usuario_id_atual,
            inspetor_nome=stream_context.usuario_nome_atual,
            preview=stream_context.texto_exibicao,
        )

        yield evento_sse(
            {
                "tipo": "humano_insp",
                "tipo_humano": "humano_insp",
                "texto": stream_context.texto_exibicao,
                "remetente": "inspetor",
                "destinatario": "engenharia",
                "laudo_id": stream_context.laudo_id_atual,
                "mensagem_id": stream_context.mensagem_usuario_id,
                "referencia_mensagem_id": stream_context.referencia_mensagem_id,
            }
        )
        yield "data: [FIM]\n\n"

    return StreamingResponse(
        gerador_humano(),
        media_type="text/event-stream",
        headers=stream_context.headers,
    )


def build_ai_stream_response(
    *,
    stream_context: ChatPersistedMessageContext,
    dados,
    cliente_ia_ativo,
) -> StreamingResponse:
    async def gerador_async():
        loop = asyncio.get_running_loop()
        fila: asyncio.Queue[str | None] = asyncio.Queue()
        resposta_completa: list[str] = []
        metadados_custo: dict[str, Any] = {}
        citacoes_deep: list[dict[str, Any]] = []
        confianca_ia_payload: dict[str, Any] = {}

        def executar_stream() -> None:
            try:
                gerador_stream = cliente_ia_ativo.gerar_resposta_stream(
                    stream_context.mensagem_para_ia,
                    stream_context.dados_imagem_validos or None,
                    dados.setor,
                    empresa_id=stream_context.empresa_id_atual,
                    historico=stream_context.historico_dict,
                    modo=dados.modo,
                    texto_documento=stream_context.texto_documento or None,
                    nome_documento=stream_context.nome_documento or None,
                )

                for pedaco in gerador_stream:
                    asyncio.run_coroutine_threadsafe(fila.put(pedaco), loop)
            except Exception:
                logger.error("Erro no stream da IA.", exc_info=True)
                asyncio.run_coroutine_threadsafe(
                    fila.put("\n\n**[Erro]** Falha interna."),
                    loop,
                )
            finally:
                asyncio.run_coroutine_threadsafe(fila.put(None), loop)

        payload_inicial: dict[str, Any] = {"laudo_id": stream_context.laudo_id_atual}
        if stream_context.card_laudo_payload:
            payload_inicial["laudo_card"] = stream_context.card_laudo_payload
        yield evento_sse(payload_inicial)
        contexto_execucao = copy_context()
        future = loop.run_in_executor(executor_stream, contexto_execucao.run, executar_stream)

        try:
            while True:
                try:
                    pedaco = await asyncio.wait_for(
                        fila.get(),
                        timeout=TIMEOUT_FILA_STREAM_SEGUNDOS,
                    )
                except asyncio.TimeoutError:
                    yield evento_sse({"texto": "\n\n**[Timeout]** A IA demorou muito."})
                    break

                if pedaco is None:
                    break

                if pedaco.startswith(PREFIXO_METADATA):
                    try:
                        metadados_custo = json.loads(pedaco[len(PREFIXO_METADATA) :])
                    except Exception:
                        metadados_custo = {}
                    continue

                if pedaco.startswith(PREFIXO_CITACOES):
                    try:
                        citacoes_deep = json.loads(pedaco[len(PREFIXO_CITACOES) :])
                        if not isinstance(citacoes_deep, list):
                            citacoes_deep = []
                    except Exception:
                        citacoes_deep = []

                    if citacoes_deep:
                        yield evento_sse({"citacoes": citacoes_deep})
                    continue

                if pedaco.startswith(PREFIXO_MODO_HUMANO):
                    continue

                resposta_completa.append(pedaco)
                yield evento_sse({"texto": pedaco})

            texto_final_stream = "".join(resposta_completa)
            if texto_final_stream.strip():
                confianca_ia_payload = analisar_confianca_resposta_ia(texto_final_stream)
                if confianca_ia_payload:
                    yield evento_sse({"confianca_ia": confianca_ia_payload})

            yield "data: [FIM]\n\n"
        except asyncio.CancelledError:
            future.cancel()
            raise
        finally:
            await salvar_mensagem_ia(
                laudo_id=stream_context.laudo_id_atual,
                usuario_id=stream_context.usuario_id_atual,
                empresa_id=stream_context.empresa_id_atual,
                texto_final="".join(resposta_completa),
                metadados=metadados_custo,
                is_deep=stream_context.eh_deep,
                citacoes=citacoes_deep if stream_context.eh_deep else None,
                confianca_ia=confianca_ia_payload or None,
            )

    return StreamingResponse(
        gerador_async(),
        media_type="text/event-stream",
        headers=stream_context.headers,
    )


__all__ = [
    "build_ai_stream_response",
    "build_whisper_stream_response",
]
