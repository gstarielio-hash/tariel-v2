"""Shell do fluxo principal de chat e stream do inspetor."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.routing import APIRouter
from sqlalchemy.orm import Session

from app.domains.chat.chat_stream_support import (
    persist_chat_user_message,
    prepare_chat_stream_route,
)
from app.domains.chat.chat_stream_transport import (
    build_ai_stream_response,
    build_whisper_stream_response,
)
from app.domains.chat.free_chat_report import build_free_chat_report_response
from app.domains.chat.ia_runtime import obter_cliente_ia_ativo
from app.domains.chat.report_finalize_stream_shadow import processar_finalizacao_stream_documental
from app.domains.chat.schemas import DadosChat
from app.domains.chat.session_helpers import exigir_csrf
from app.shared.database import Usuario, obter_banco
from app.shared.backend_hotspot_metrics import observe_backend_hotspot
from app.shared.security import exigir_inspetor
from nucleo.inspetor.comandos_chat import analisar_pedido_relatorio_chat_livre

roteador_chat_stream = APIRouter()


async def rota_chat(
    dados: DadosChat,
    request: Request,
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    with observe_backend_hotspot(
        "chat_stream",
        request=request,
        surface="inspetor",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        route_path="/app/api/chat",
        method="POST",
        detail={
            "has_laudo_id": bool(getattr(dados, "laudo_id", None)),
            "has_guided_draft": bool(getattr(dados, "guided_inspection_draft", None)),
        },
    ) as hotspot:
        exigir_csrf(request)
        prepared, early_response = prepare_chat_stream_route(
            dados=dados,
            request=request,
            usuario=usuario,
            banco=banco,
        )
        if early_response is not None:
            hotspot.outcome = "early_response"
            hotspot.response_status_code = getattr(early_response, "status_code", 200)
            return early_response
        if prepared is None:
            hotspot.outcome = "prepared_missing"
            raise HTTPException(status_code=500, detail="Fluxo de chat inconsistente.")

        stream_context = persist_chat_user_message(
            dados=dados,
            request=request,
            usuario=usuario,
            banco=banco,
            prepared=prepared,
        )
        hotspot.tenant_id = getattr(stream_context, "empresa_id_atual", None)
        hotspot.user_id = getattr(stream_context, "usuario_id_atual", None)
        hotspot.laudo_id = getattr(stream_context, "laudo_id_atual", None)
        hotspot.case_id = getattr(stream_context, "laudo_id_atual", None)

        if stream_context.eh_whisper_para_mesa:
            hotspot.outcome = "whisper_mesa"
            hotspot.response_status_code = 200
            return build_whisper_stream_response(stream_context=stream_context)

        if stream_context.eh_comando_finalizar:
            hotspot.outcome = "report_finalize_stream"
            hotspot.response_status_code = 200
            return await processar_finalizacao_stream_documental(
                request=request,
                usuario=usuario,
                banco=banco,
                laudo=stream_context.laudo,
                historico_dict=stream_context.historico_dict,
                dados_imagem_validos=stream_context.dados_imagem_validos,
                texto_documento=stream_context.texto_documento,
                tipo_template_finalizacao=stream_context.tipo_template_finalizacao or "padrao",
                headers=stream_context.headers,
            )

        if analisar_pedido_relatorio_chat_livre(stream_context.texto_exibicao):
            hotspot.outcome = "free_chat_report"
            hotspot.response_status_code = 200
            return build_free_chat_report_response(
                banco=banco,
                laudo=stream_context.laudo,
                usuario=usuario,
                request_message_id=stream_context.mensagem_usuario_id,
            )

        cliente_ia_ativo = obter_cliente_ia_ativo()
        hotspot.outcome = "ai_stream"
        hotspot.response_status_code = 200
        return build_ai_stream_response(
            stream_context=stream_context,
            dados=dados,
            cliente_ia_ativo=cliente_ia_ativo,
        )


roteador_chat_stream.add_api_route(
    "/api/chat",
    rota_chat,
    methods=["POST"],
    responses={
        200: {
            "description": "Resposta do chat em JSON ou fluxo SSE.",
            "content": {
                "application/json": {},
                "text/event-stream": {},
            },
        },
        400: {"description": "Payload do chat inválido para a operação solicitada."},
    },
)


__all__ = [
    "rota_chat",
    "roteador_chat_stream",
]
