"""Shell das rotas da mesa avaliadora no domínio do inspetor."""

from __future__ import annotations

from fastapi.routing import APIRouter

from app.domains.chat.mesa_feed_routes import (
    feed_mesa_mobile,
    feed_mesa_mobile_public_v2,
)
from app.domains.chat.mesa_message_routes import (
    baixar_anexo_mesa_laudo,
    enviar_mensagem_mesa_laudo,
    enviar_mensagem_mesa_laudo_com_anexo,
)
from app.domains.chat.mesa_thread_routes import (
    listar_mensagens_mesa_laudo,
    listar_mensagens_mesa_laudo_mobile_public_v2,
    obter_resumo_mesa_laudo,
)

roteador_mesa = APIRouter()
RESPOSTA_LAUDO_NAO_ENCONTRADO = {404: {"description": "Laudo não encontrado."}}

listar_mensagens_mesa = listar_mensagens_mesa_laudo
enviar_mensagem_mesa = enviar_mensagem_mesa_laudo

roteador_mesa.add_api_route(
    "/api/laudo/{laudo_id}/mesa/mensagens",
    listar_mensagens_mesa_laudo,
    methods=["GET"],
    responses=RESPOSTA_LAUDO_NAO_ENCONTRADO,
)
roteador_mesa.add_api_route(
    "/api/laudo/{laudo_id}/mesa/resumo",
    obter_resumo_mesa_laudo,
    methods=["GET"],
    responses=RESPOSTA_LAUDO_NAO_ENCONTRADO,
)
roteador_mesa.add_api_route(
    "/api/laudo/{laudo_id}/mesa/mensagem",
    enviar_mensagem_mesa_laudo,
    methods=["POST"],
    responses={
        **RESPOSTA_LAUDO_NAO_ENCONTRADO,
        201: {"description": "Mensagem enviada para a mesa."},
        400: {"description": "Mensagem inválida para o canal da mesa."},
    },
)
roteador_mesa.add_api_route(
    "/api/laudo/{laudo_id}/mesa/anexo",
    enviar_mensagem_mesa_laudo_com_anexo,
    methods=["POST"],
    responses={
        **RESPOSTA_LAUDO_NAO_ENCONTRADO,
        201: {"description": "Anexo enviado para a mesa."},
        400: {"description": "Corpo multipart inválido."},
        413: {"description": "Anexo acima do limite permitido."},
        415: {"description": "Tipo de arquivo não suportado."},
    },
)
roteador_mesa.add_api_route(
    "/api/mobile/mesa/feed",
    feed_mesa_mobile,
    methods=["GET"],
    responses={400: {"description": "Parâmetros inválidos para o feed da mesa."}},
)
roteador_mesa.add_api_route(
    "/api/mobile/v2/mesa/feed",
    feed_mesa_mobile_public_v2,
    methods=["GET"],
    responses={
        400: {"description": "Parâmetros inválidos para o feed V2 da mesa."},
        404: {"description": "Contrato publico mobile V2 desativado."},
    },
)
roteador_mesa.add_api_route(
    "/api/mobile/v2/laudo/{laudo_id}/mesa/mensagens",
    listar_mensagens_mesa_laudo_mobile_public_v2,
    methods=["GET"],
    responses={
        **RESPOSTA_LAUDO_NAO_ENCONTRADO,
        404: {"description": "Contrato publico mobile V2 desativado."},
    },
)
roteador_mesa.add_api_route(
    "/api/laudo/{laudo_id}/mesa/anexos/{anexo_id}",
    baixar_anexo_mesa_laudo,
    methods=["GET"],
    responses={
        **RESPOSTA_LAUDO_NAO_ENCONTRADO,
        200: {
            "description": "Download do anexo da mesa.",
            "content": {
                "application/pdf": {},
                "image/png": {},
                "image/jpeg": {},
                "image/webp": {},
                "application/octet-stream": {},
            },
        },
    },
)

__all__ = [
    "roteador_mesa",
    "listar_mensagens_mesa_laudo",
    "listar_mensagens_mesa",
    "enviar_mensagem_mesa_laudo",
    "enviar_mensagem_mesa",
    "enviar_mensagem_mesa_laudo_com_anexo",
    "obter_resumo_mesa_laudo",
    "feed_mesa_mobile",
    "feed_mesa_mobile_public_v2",
    "listar_mensagens_mesa_laudo_mobile_public_v2",
    "baixar_anexo_mesa_laudo",
]
