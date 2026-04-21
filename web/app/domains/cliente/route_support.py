"""Suporte HTTP e utilitarios do portal admin-cliente."""

from __future__ import annotations

import json
import secrets
from json import JSONDecodeError
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.paths import TEMPLATES_DIR
from app.domains.cliente.auditoria import registrar_auditoria_empresa
from app.domains.chat.laudo_state_helpers import serializar_card_laudo
from app.domains.cliente.common import CHAVE_CSRF_CLIENTE, contexto_base_cliente
from app.domains.cliente.dashboard import serializar_usuario_cliente as _serializar_usuario_cliente
from app.shared.database import Empresa, Laudo, NivelAcesso, Usuario
from app.shared.security import (
    PORTAL_ADMIN,
    PORTAL_CLIENTE,
    PORTAL_INSPETOR,
    PORTAL_REVISOR,
    criar_sessao,
    definir_sessao_portal,
    encerrar_sessao,
    nivel_acesso_sessao_portal,
    limpar_sessao_portal,
    obter_dados_sessao_portal,
    usuario_tem_acesso_portal,
    usuario_tem_bloqueio_ativo,
    usuario_portal_switch_links,
    usuario_portais_habilitados,
)
from app.shared.tenant_access import obter_empresa_usuario
from app.shared.tenant_admin_policy import (
    summarize_tenant_admin_policy,
    tenant_admin_surface_availability,
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

URL_LOGIN = "/cliente/login"
URL_LOGIN_INSPETOR = "/app/login"
URL_LOGIN_REVISOR = "/revisao/login"
URL_PAINEL = "/cliente/painel"
URL_EQUIPE = "/cliente/equipe"
URL_CHAT = "/cliente/chat"
URL_MESA = "/cliente/mesa"
CLIENTE_SURFACE_ROUTES = {
    "admin": URL_PAINEL,
    "chat": URL_CHAT,
    "mesa": URL_MESA,
}
CLIENTE_SURFACE_SECTION_DEFAULTS = {
    "admin": "overview",
    "chat": "overview",
    "mesa": "overview",
}
CLIENTE_SURFACE_SECTION_OPTIONS = {
    "admin": {"overview", "capacity", "team", "support"},
    "chat": {"overview", "new", "queue", "case"},
    "mesa": {"overview", "queue", "pending", "reply"},
}
CLIENTE_SURFACE_SECTION_ALIASES = {
    "admin": {
        "planos": "capacity",
        "equipe": "team",
        "governanca": "support",
    },
    "chat": {},
    "mesa": {},
}
PORTAL_TROCA_SENHA_CLIENTE = "cliente"
CHAVE_TROCA_SENHA_UID = "troca_senha_uid"
CHAVE_TROCA_SENHA_PORTAL = "troca_senha_portal"
CHAVE_TROCA_SENHA_LEMBRAR = "troca_senha_lembrar"
CHAVE_CREDENCIAL_ONBOARDING = "_cliente_credencial_onboarding"
_PORTAL_LOGIN_ROUTES = {
    PORTAL_CLIENTE: URL_LOGIN,
    PORTAL_INSPETOR: URL_LOGIN_INSPETOR,
    PORTAL_REVISOR: URL_LOGIN_REVISOR,
}
_ONBOARDING_PORTAL_LABELS = {
    PORTAL_CLIENTE: "Admin-Cliente",
    PORTAL_INSPETOR: "Inspetor web/mobile",
    PORTAL_REVISOR: "Mesa Avaliadora",
}


def _aplicar_headers_no_cache(response: HTMLResponse | RedirectResponse) -> None:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


def _render_template(request: Request, nome_template: str, contexto: dict[str, Any], *, status_code: int = 200) -> HTMLResponse:
    resposta = templates.TemplateResponse(
        request,
        nome_template,
        {**contexto_base_cliente(request), **contexto},
        status_code=status_code,
    )
    _aplicar_headers_no_cache(resposta)
    return resposta


def _render_login_cliente(
    request: Request,
    *,
    erro: str = "",
    email: str = "",
    primeiro_acesso: bool = False,
    status_code: int = 200,
) -> HTMLResponse:
    return _render_template(
        request,
        "login_cliente.html",
        {
            "erro": erro,
            "email_prefill": str(email or "").strip().lower(),
            "primeiro_acesso": bool(primeiro_acesso),
        },
        status_code=status_code,
    )


def _redirect_login_cliente() -> RedirectResponse:
    resposta = RedirectResponse(url=URL_LOGIN, status_code=status.HTTP_303_SEE_OTHER)
    _aplicar_headers_no_cache(resposta)
    return resposta


def _normalizar_tab_cliente(valor: str | None) -> str:
    tab = str(valor or "").strip().lower()
    if tab in CLIENTE_SURFACE_ROUTES:
        return tab
    return "admin"


def _normalizar_secao_cliente(tab: str, valor: str | None) -> str:
    tab_resolvida = _normalizar_tab_cliente(tab)
    secao = str(valor or "").strip().lower()
    secao = CLIENTE_SURFACE_SECTION_ALIASES.get(tab_resolvida, {}).get(secao, secao)
    if secao in CLIENTE_SURFACE_SECTION_OPTIONS.get(tab_resolvida, set()):
        return secao
    return CLIENTE_SURFACE_SECTION_DEFAULTS.get(tab_resolvida, "overview")


def _mensagem_portal_correto(usuario: Usuario) -> str:
    if usuario_tem_acesso_portal(usuario, PORTAL_ADMIN):
        return "Esta credencial pertence ao portal da Tariel em /admin/login."

    destinos = []
    for portal in usuario_portais_habilitados(usuario):
        if portal == PORTAL_REVISOR:
            destinos.append("/revisao/login")
        elif portal == PORTAL_INSPETOR:
            destinos.append("/app/login")

    if not destinos:
        nivel = int(usuario.nivel_acesso or 0)
        if nivel == int(NivelAcesso.INSPETOR):
            return "Esta credencial deve acessar /app/login."
        if nivel == int(NivelAcesso.REVISOR):
            return "Esta credencial deve acessar /revisao/login."
        return "Acesso negado para este portal."

    if len(destinos) == 1:
        destino_unico = destinos[0]
        if destino_unico == "/app/login":
            return "Este usuário deve acessar /app/login."
        if destino_unico == "/revisao/login":
            return "Este usuário deve acessar /revisao/login."
        return f"Esta credencial deve acessar {destino_unico}."
    return "Esta credencial pode acessar " + ", ".join(destinos[:-1]) + f" e {destinos[-1]}."


def _normalizar_credencial_onboarding_cliente(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    try:
        usuario_id = int(payload.get("usuario_id") or 0)
    except (TypeError, ValueError):
        usuario_id = 0

    referencia = str(payload.get("referencia") or "").strip()[:180]
    empresa_nome = str(payload.get("empresa_nome") or "").strip()[:200]
    usuario_nome = str(payload.get("usuario_nome") or "").strip()[:180]
    papel = str(payload.get("papel") or "").strip()[:120]
    login = str(payload.get("login") or "").strip()[:254]
    senha = str(payload.get("senha") or "").strip()[:180]
    orientacao = str(payload.get("orientacao") or "").strip()[:260]

    if usuario_id <= 0 or not login or not senha:
        return None

    portais_brutos = payload.get("portais")
    portais: list[dict[str, str]] = []
    if isinstance(portais_brutos, list):
        for item in portais_brutos:
            if not isinstance(item, dict):
                continue
            portal = str(item.get("portal") or "").strip().lower()[:40]
            label = str(item.get("label") or "").strip()[:120]
            login_url = str(item.get("login_url") or "").strip()[:240]
            if not portal or not login_url:
                continue
            portais.append(
                {
                    "portal": portal,
                    "label": label or portal,
                    "login_url": login_url,
                }
            )

    if not portais:
        return None

    return {
        "usuario_id": usuario_id,
        "referencia": referencia or "Credencial operacional",
        "empresa_nome": empresa_nome,
        "usuario_nome": usuario_nome or f"Usuário #{usuario_id}",
        "papel": papel or "Usuário operacional",
        "login": login,
        "senha": senha,
        "orientacao": orientacao or "Compartilhe a senha por canal seguro e exija a troca obrigatória no primeiro acesso.",
        "portais": portais,
    }


def _rotas_login_usuario_cliente(usuario: Usuario) -> list[dict[str, str]]:
    serializado = _serializar_usuario_cliente(usuario)
    portais = list(serializado.get("allowed_portals") or [])
    itens: list[dict[str, str]] = []
    for portal in portais:
        portal_norm = str(portal or "").strip().lower()
        login_url = _PORTAL_LOGIN_ROUTES.get(portal_norm)
        if not login_url:
            continue
        itens.append(
            {
                "portal": portal_norm,
                "label": _ONBOARDING_PORTAL_LABELS.get(portal_norm, portal_norm),
                "login_url": login_url,
            }
        )
    return itens


def _registrar_credencial_onboarding_cliente(
    request: Request,
    *,
    usuario: Usuario,
    senha_temporaria: str,
    referencia: str,
) -> dict[str, Any]:
    serializado = _serializar_usuario_cliente(usuario)
    portais = _rotas_login_usuario_cliente(usuario)
    onboarding = _normalizar_credencial_onboarding_cliente(
        {
            "usuario_id": int(usuario.id),
            "referencia": referencia,
            "empresa_nome": str(getattr(getattr(usuario, "empresa", None), "nome_fantasia", "") or ""),
            "usuario_nome": str(serializado.get("nome") or ""),
            "papel": str(serializado.get("papel") or ""),
            "login": str(serializado.get("email") or ""),
            "senha": str(senha_temporaria or ""),
            "orientacao": (
                "Use o login abaixo em um dos portais liberados. "
                "No primeiro acesso, o usuário terá de trocar a senha temporária antes de continuar."
            ),
            "portais": portais,
        }
    )
    if onboarding is None:
        raise ValueError("Não foi possível montar a credencial de onboarding do usuário operacional.")

    fila = request.session.get(CHAVE_CREDENCIAL_ONBOARDING, {})
    if not isinstance(fila, dict):
        fila = {}
    fila[str(int(usuario.id))] = onboarding
    while len(fila) > 8:
        chave_mais_antiga = next(iter(fila))
        fila.pop(chave_mais_antiga, None)
    request.session[CHAVE_CREDENCIAL_ONBOARDING] = fila
    return onboarding


def _consumir_credencial_onboarding_cliente(request: Request, *, usuario_id: int) -> dict[str, Any] | None:
    fila = request.session.get(CHAVE_CREDENCIAL_ONBOARDING, {})
    if not isinstance(fila, dict):
        request.session.pop(CHAVE_CREDENCIAL_ONBOARDING, None)
        return None

    item = fila.pop(str(int(usuario_id)), None)
    if fila:
        request.session[CHAVE_CREDENCIAL_ONBOARDING] = fila
    else:
        request.session.pop(CHAVE_CREDENCIAL_ONBOARDING, None)
    return _normalizar_credencial_onboarding_cliente(item)


def _nome_usuario_cliente(usuario: Usuario) -> str:
    return str(_serializar_usuario_cliente(usuario).get("nome") or f"Cliente #{usuario.id}")


def _limpar_sessao_cliente(request: Request) -> None:
    token = obter_dados_sessao_portal(request.session, portal=PORTAL_CLIENTE).get("token")
    if token:
        encerrar_sessao(token)
    limpar_sessao_portal(request.session, portal=PORTAL_CLIENTE)
    request.session.pop(CHAVE_CSRF_CLIENTE, None)
    request.session.pop("csrf_token", None)
    _limpar_fluxo_troca_senha(request)


def _registrar_sessao_cliente(request: Request, usuario: Usuario, *, lembrar: bool) -> None:
    token = criar_sessao(int(usuario.id), lembrar=lembrar)
    definir_sessao_portal(
        request.session,
        portal=PORTAL_CLIENTE,
        token=token,
        usuario_id=int(usuario.id),
        empresa_id=int(usuario.empresa_id),
        nivel_acesso=nivel_acesso_sessao_portal(PORTAL_CLIENTE) or int(usuario.nivel_acesso),
        nome=_nome_usuario_cliente(usuario),
    )
    token_csrf = secrets.token_urlsafe(32)
    request.session[CHAVE_CSRF_CLIENTE] = token_csrf
    request.session["csrf_token"] = token_csrf


def _iniciar_fluxo_troca_senha(request: Request, *, usuario_id: int, lembrar: bool) -> None:
    _limpar_sessao_cliente(request)
    token_csrf = secrets.token_urlsafe(32)
    request.session[CHAVE_CSRF_CLIENTE] = token_csrf
    request.session["csrf_token"] = token_csrf
    request.session[CHAVE_TROCA_SENHA_UID] = int(usuario_id)
    request.session[CHAVE_TROCA_SENHA_PORTAL] = PORTAL_TROCA_SENHA_CLIENTE
    request.session[CHAVE_TROCA_SENHA_LEMBRAR] = bool(lembrar)


def _limpar_fluxo_troca_senha(request: Request) -> None:
    request.session.pop(CHAVE_TROCA_SENHA_UID, None)
    request.session.pop(CHAVE_TROCA_SENHA_PORTAL, None)
    request.session.pop(CHAVE_TROCA_SENHA_LEMBRAR, None)


def _usuario_pendente_troca_senha(request: Request, banco: Session) -> Usuario | None:
    if request.session.get(CHAVE_TROCA_SENHA_PORTAL) != PORTAL_TROCA_SENHA_CLIENTE:
        return None

    usuario_id = request.session.get(CHAVE_TROCA_SENHA_UID)
    try:
        usuario_id_int = int(usuario_id)
    except (TypeError, ValueError):
        _limpar_fluxo_troca_senha(request)
        return None

    usuario = banco.get(Usuario, usuario_id_int)
    if not usuario or not usuario_tem_acesso_portal(usuario, PORTAL_CLIENTE):
        _limpar_fluxo_troca_senha(request)
        return None
    if not bool(getattr(usuario, "senha_temporaria_ativa", False)):
        _limpar_fluxo_troca_senha(request)
        return None
    if usuario_tem_bloqueio_ativo(usuario):
        _limpar_fluxo_troca_senha(request)
        return None
    return usuario


def _validar_nova_senha(senha_atual: str, nova_senha: str, confirmar_senha: str) -> str:
    senha_atual = senha_atual or ""
    nova_senha = nova_senha or ""
    confirmar_senha = confirmar_senha or ""

    if not senha_atual or not nova_senha or not confirmar_senha:
        return "Preencha senha atual, nova senha e confirmação."
    if nova_senha != confirmar_senha:
        return "A confirmação da nova senha não confere."
    if len(nova_senha) < 8:
        return "A nova senha deve ter no mínimo 8 caracteres."
    if nova_senha == senha_atual:
        return "A nova senha deve ser diferente da senha temporária."
    return ""


def _render_troca_senha(request: Request, *, erro: str = "", status_code: int = 200) -> HTMLResponse:
    return _render_template(
        request,
        "trocar_senha.html",
        {
            "erro": erro,
            "titulo_pagina": "Troca Obrigatória de Senha",
            "subtitulo_pagina": "Defina sua nova senha para liberar o acesso ao portal da empresa.",
            "acao_form": "/cliente/trocar-senha",
            "rota_login": URL_LOGIN,
        },
        status_code=status_code,
    )


def _render_portal_cliente(
    request: Request,
    *,
    usuario: Usuario,
    empresa: Empresa,
    tab_inicial: str = "admin",
    secao_inicial: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    tenant_admin_policy = summarize_tenant_admin_policy(
        getattr(empresa, "admin_cliente_policy_json", None)
    )
    surface_availability = tenant_admin_surface_availability(tenant_admin_policy)
    tab_resolvida = _normalizar_tab_cliente(tab_inicial)
    if not surface_availability.get(tab_resolvida, False):
        tab_resolvida = "admin"
    secao_param = secao_inicial or request.query_params.get("sec") or request.query_params.get("secao")
    secao_resolvida = _normalizar_secao_cliente(tab_resolvida, secao_param)
    return _render_template(
        request,
        "cliente_portal.html",
        {
            "usuario": usuario,
            "empresa": empresa,
            "cliente_tab_inicial": tab_resolvida,
            "cliente_admin_section_inicial": secao_resolvida if tab_resolvida == "admin" else CLIENTE_SURFACE_SECTION_DEFAULTS["admin"],
            "cliente_chat_section_inicial": secao_resolvida if tab_resolvida == "chat" else CLIENTE_SURFACE_SECTION_DEFAULTS["chat"],
            "cliente_mesa_section_inicial": secao_resolvida if tab_resolvida == "mesa" else CLIENTE_SURFACE_SECTION_DEFAULTS["mesa"],
            "cliente_surface_availability": surface_availability,
            "cliente_surface_routes": CLIENTE_SURFACE_ROUTES,
            "portal_switch_links": usuario_portal_switch_links(
                usuario,
                portal_atual=PORTAL_CLIENTE,
            ),
            "tenant_admin_policy": tenant_admin_policy,
        },
        status_code=status_code,
    )


def _empresa_usuario(banco: Session, usuario: Usuario) -> Empresa:
    return obter_empresa_usuario(banco, usuario)


def _traduzir_erro_servico_cliente(exc: ValueError) -> HTTPException:
    detalhe = str(exc).strip() or "Operação inválida."
    detalhe_lower = detalhe.lower()

    if "não encontrado" in detalhe_lower or "nao encontrado" in detalhe_lower:
        status_code = status.HTTP_404_NOT_FOUND
    elif (
        "já cadastrado" in detalhe_lower
        or "ja cadastrado" in detalhe_lower
        or "já em uso" in detalhe_lower
        or "ja em uso" in detalhe_lower
        or "limite de usuários" in detalhe_lower
        or "limite de usuarios" in detalhe_lower
        or "limite operacional" in detalhe_lower
        or "conflito" in detalhe_lower
    ):
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_400_BAD_REQUEST

    return HTTPException(status_code=status_code, detail=detalhe)


def _rebase_urls_anexos_cliente(payload: Any, *, laudo_id: int) -> Any:
    if isinstance(payload, dict):
        anexos = payload.get("anexos")
        if isinstance(anexos, list):
            for anexo in anexos:
                if not isinstance(anexo, dict):
                    continue
                try:
                    anexo_id = int(anexo.get("id") or 0)
                except (TypeError, ValueError):
                    anexo_id = 0
                if anexo_id > 0:
                    anexo["url"] = f"/cliente/api/mesa/laudos/{int(laudo_id)}/anexos/{anexo_id}"

        for valor in payload.values():
            _rebase_urls_anexos_cliente(valor, laudo_id=laudo_id)
        return payload

    if isinstance(payload, list):
        for item in payload:
            _rebase_urls_anexos_cliente(item, laudo_id=laudo_id)

    return payload


def _payload_json_resposta(resposta: Any) -> dict[str, Any]:
    if not isinstance(resposta, JSONResponse):
        return {}
    try:
        bruto = resposta.body.decode("utf-8")
        payload = json.loads(bruto or "{}")
    except (AttributeError, UnicodeDecodeError, JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _resumir_texto_auditoria(texto: str, *, limite: int = 160) -> str:
    valor = " ".join(str(texto or "").split())
    if len(valor) <= limite:
        return valor
    return f"{valor[: limite - 3].rstrip()}..."


def _titulo_laudo_cliente(banco: Session, *, empresa_id: int, laudo_id: int) -> str:
    laudo = banco.get(Laudo, int(laudo_id))
    if laudo is None or int(getattr(laudo, "empresa_id", 0) or 0) != int(empresa_id):
        return f"Laudo #{laudo_id}"
    payload = serializar_card_laudo(banco, laudo)
    return str(payload.get("titulo") or f"Laudo #{laudo_id}")


def _registrar_auditoria_cliente_segura(
    banco: Session,
    *,
    empresa_id: int,
    ator_usuario_id: int | None,
    acao: str,
    resumo: str,
    detalhe: str = "",
    alvo_usuario_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    registrar_auditoria_empresa(
        banco,
        empresa_id=empresa_id,
        ator_usuario_id=ator_usuario_id,
        acao=acao,
        resumo=resumo,
        detalhe=detalhe,
        alvo_usuario_id=alvo_usuario_id,
        payload=payload,
    )


__all__ = [
    "CLIENTE_SURFACE_ROUTES",
    "URL_LOGIN",
    "URL_LOGIN_INSPETOR",
    "URL_LOGIN_REVISOR",
    "URL_CHAT",
    "URL_MESA",
    "URL_PAINEL",
    "CHAVE_TROCA_SENHA_LEMBRAR",
    "_consumir_credencial_onboarding_cliente",
    "_empresa_usuario",
    "_iniciar_fluxo_troca_senha",
    "_limpar_fluxo_troca_senha",
    "_limpar_sessao_cliente",
    "_mensagem_portal_correto",
    "_nome_usuario_cliente",
    "_payload_json_resposta",
    "_registrar_credencial_onboarding_cliente",
    "_rebase_urls_anexos_cliente",
    "_redirect_login_cliente",
    "_registrar_auditoria_cliente_segura",
    "_registrar_sessao_cliente",
    "_render_login_cliente",
    "_render_portal_cliente",
    "_render_template",
    "_render_troca_senha",
    "_normalizar_tab_cliente",
    "_resumir_texto_auditoria",
    "_titulo_laudo_cliente",
    "_traduzir_erro_servico_cliente",
    "_usuario_pendente_troca_senha",
    "_validar_nova_senha",
]
