"""Suporte HTTP e de sessao do portal administrativo."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets
from typing import Any, Optional, TypeGuard
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.paths import TEMPLATES_DIR
from app.core.perf_support import contexto_template_perf
from app.core.settings import env_bool, env_int, env_str, get_settings
from app.domains.admin.mfa import build_totp_otpauth_uri
from app.shared.database import NivelAcesso, Usuario
from app.shared.security import (
    PORTAL_ADMIN,
    atualizar_meta_sessao,
    criar_sessao,
    definir_sessao_portal,
    encerrar_sessao,
    limpar_sessao_portal,
    obter_dados_sessao_portal,
    obter_meta_sessao,
    obter_token_autenticacao_request,
    usuario_tem_acesso_portal,
    usuario_tem_bloqueio_ativo,
    usuario_tem_escopo_plataforma,
)

logger = logging.getLogger("tariel.admin")

_settings = get_settings()
EM_PRODUCAO = _settings.em_producao

URL_LOGIN = "/admin/login"
URL_PAINEL = "/admin/painel"
URL_CLIENTES = "/admin/clientes"
URL_NOVO_CLIENTE = "/admin/novo-cliente"

_PLANOS_MAPEADOS = {
    "piloto": "Piloto",
    "inicial": "Piloto",
    "starter": "Piloto",
    "pro": "Pro",
    "intermediario": "Pro",
    "intermediário": "Pro",
    "professional": "Pro",
    "ilimitado": "Ilimitado",
    "enterprise": "Ilimitado",
    "premium": "Ilimitado",
}

_NIVEIS_ADMIN = frozenset({NivelAcesso.DIRETORIA.value})
_CHAVE_FLASH = "_admin_flash_messages"
CHAVE_CSRF_ADMIN = "csrf_token_admin"
PORTAL_TROCA_SENHA_ADMIN = PORTAL_ADMIN
CHAVE_TROCA_SENHA_UID = "troca_senha_uid"
CHAVE_TROCA_SENHA_PORTAL = "troca_senha_portal"
CHAVE_TROCA_SENHA_LEMBRAR = "troca_senha_lembrar"
CHAVE_IDENTITY_STATE = "admin_identity_state"
CHAVE_IDENTITY_PROVIDER = "admin_identity_provider"
CHAVE_MFA_PENDING_UID = "admin_mfa_pending_uid"
CHAVE_MFA_PENDING_PROVIDER = "admin_mfa_pending_provider"
CHAVE_MFA_PENDING_LEMBRAR = "admin_mfa_pending_lembrar"
CHAVE_MFA_PENDING_RETURN_TO = "admin_mfa_pending_return_to"
CHAVE_REAUTH_RETURN_TO = "admin_reauth_return_to"
ADMIN_LOGIN_GOOGLE_ENABLED = env_bool("ADMIN_LOGIN_GOOGLE_ENABLED", False)
ADMIN_LOGIN_MICROSOFT_ENABLED = env_bool("ADMIN_LOGIN_MICROSOFT_ENABLED", False)
ADMIN_LOGIN_GOOGLE_ENTRYPOINT = env_str("ADMIN_LOGIN_GOOGLE_ENTRYPOINT", "")
ADMIN_LOGIN_MICROSOFT_ENTRYPOINT = env_str("ADMIN_LOGIN_MICROSOFT_ENTRYPOINT", "")
ADMIN_TOTP_ENABLED = env_bool("ADMIN_TOTP_ENABLED", True)
ADMIN_REAUTH_MAX_AGE_MINUTES = max(env_int("ADMIN_REAUTH_MAX_AGE_MINUTES", 10), 1)
ADMIN_SESSION_MFA_LEVEL = "totp"
ADMIN_SESSION_MFA_DISABLED_LEVEL = "disabled"
_PLATFORM_SETTING_REAUTH_WINDOW_KEY = "admin_reauth_max_age_minutes"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
TEMPLATE_ADMIN_LOGIN = "admin/login.html"
TEMPLATE_ADMIN_TROCA_SENHA = "admin/trocar_senha.html"
TEMPLATE_ADMIN_MFA = "admin/admin_mfa.html"


def _normalizar_texto(valor: str, *, max_len: int | None = None) -> str:
    texto = (valor or "").strip()
    if max_len is not None:
        return texto[:max_len]
    return texto


def _normalizar_email(email: str) -> str:
    return _normalizar_texto(email, max_len=254).lower()


def _normalizar_plano(valor: str) -> str:
    chave = _normalizar_texto(valor).lower()
    return _PLANOS_MAPEADOS.get(chave, _normalizar_texto(valor))


def _normalizar_tipo_flash(tipo: str) -> str:
    return "success" if str(tipo).strip().lower() == "success" else "error"


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_admin_reauth_max_age_minutes() -> int:
    try:
        from app.shared.database import ConfiguracaoPlataforma, SessaoLocal

        with SessaoLocal() as banco:
            configuracao = banco.get(ConfiguracaoPlataforma, _PLATFORM_SETTING_REAUTH_WINDOW_KEY)
            if configuracao is not None:
                try:
                    return max(int(configuracao.valor_json), 1)
                except (TypeError, ValueError):
                    logger.warning(
                        "Configuração inválida para janela de reautenticação do Admin-CEO. Usando fallback de ambiente."
                    )
    except Exception:
        logger.debug("Falha ao resolver janela persistida de reautenticação do Admin-CEO.", exc_info=True)

    return max(ADMIN_REAUTH_MAX_AGE_MINUTES, 1)


def admin_totp_enabled() -> bool:
    return bool(ADMIN_TOTP_ENABLED)


def admin_session_mfa_level() -> str:
    return ADMIN_SESSION_MFA_LEVEL if admin_totp_enabled() else ADMIN_SESSION_MFA_DISABLED_LEVEL


def _normalizar_datetime_utc(valor: datetime | None) -> datetime | None:
    if not isinstance(valor, datetime):
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _device_id_request(request: Request) -> str:
    header_device = str(request.headers.get("x-device-id", "") or "").strip()
    if header_device:
        return header_device[:120]

    user_agent = str(request.headers.get("user-agent", "") or "").strip()
    ip = getattr(getattr(request, "client", None), "host", "") or ""
    digest = hashlib.sha256(f"{user_agent}|{ip}".encode("utf-8")).hexdigest()
    return digest[:32]


def _normalizar_credencial_onboarding_flash(payload: Any) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None

    referencia = _normalizar_texto(str(payload.get("referencia", "")), max_len=180)
    empresa_nome = _normalizar_texto(str(payload.get("empresa_nome", "")), max_len=200)
    login = _normalizar_texto(str(payload.get("login", "")), max_len=254)
    senha = _normalizar_texto(str(payload.get("senha", "")), max_len=180)
    portal_login_url = _normalizar_texto(str(payload.get("portal_login_url", "")), max_len=240)
    portal_label = _normalizar_texto(str(payload.get("portal_label", "")), max_len=120)
    orientacao = _normalizar_texto(str(payload.get("orientacao", "")), max_len=220)

    if not login or not senha:
        return None

    return {
        "referencia": referencia or "Credencial inicial",
        "empresa_nome": empresa_nome,
        "login": login,
        "senha": senha,
        "portal_login_url": portal_login_url or "/cliente/login",
        "portal_label": portal_label or "Portal da empresa",
        "orientacao": orientacao or "Compartilhe a senha por canal seguro e exija a troca no primeiro acesso.",
    }


def _adicionar_flash(
    request: Request,
    texto: str,
    *,
    tipo: str = "success",
    credencial_onboarding: dict[str, Any] | None = None,
) -> None:
    mensagem = _normalizar_texto(texto, max_len=700)
    if not mensagem:
        return

    credencial_norm = _normalizar_credencial_onboarding_flash(credencial_onboarding)

    fila = request.session.get(_CHAVE_FLASH, [])
    if not isinstance(fila, list):
        fila = []
    item = {
        "tipo": _normalizar_tipo_flash(tipo),
        "texto": mensagem,
    }
    if credencial_norm is not None:
        item["credencial_onboarding"] = credencial_norm

    fila.append(item)
    request.session[_CHAVE_FLASH] = fila[-8:]


def _consumir_flash(request: Request) -> list[dict[str, Any]]:
    mensagens_brutas = request.session.pop(_CHAVE_FLASH, [])
    if not isinstance(mensagens_brutas, list):
        return []

    mensagens: list[dict[str, Any]] = []
    for item in mensagens_brutas:
        if not isinstance(item, dict):
            continue
        texto = _normalizar_texto(str(item.get("texto", "")), max_len=700)
        if not texto:
            continue
        mensagem: dict[str, Any] = {
            "tipo": _normalizar_tipo_flash(str(item.get("tipo", "error"))),
            "texto": texto,
        }
        credencial_onboarding = _normalizar_credencial_onboarding_flash(item.get("credencial_onboarding"))
        if credencial_onboarding is not None:
            mensagem["credencial_onboarding"] = credencial_onboarding
        mensagens.append(mensagem)
    return mensagens


def _flash_senha_temporaria(
    request: Request,
    *,
    referencia: str,
    senha: str,
    login: str = "",
    portal_login_url: str = "",
    portal_label: str = "",
) -> None:
    ref = _normalizar_texto(referencia, max_len=180)
    senha_temp = _normalizar_texto(senha, max_len=180)
    if not ref or not senha_temp:
        return

    login_norm = _normalizar_texto(login, max_len=254)
    portal_login_url_norm = _normalizar_texto(portal_login_url, max_len=240)
    portal_label_norm = _normalizar_texto(portal_label, max_len=120)

    _adicionar_flash(
        request,
        f"Senha temporária para {ref}: {senha_temp}. Compartilhe em canal seguro e oriente a troca no primeiro acesso.",
        tipo="success",
        credencial_onboarding={
            "referencia": ref,
            "login": login_norm,
            "senha": senha_temp,
            "portal_login_url": portal_login_url_norm,
            "portal_label": portal_label_norm,
        }
        if login_norm
        else None,
    )


def _flash_primeiro_acesso_empresa(request: Request, *, empresa: str, email: str) -> None:
    empresa_norm = _normalizar_texto(empresa, max_len=180)
    email_norm = _normalizar_email(email)
    if not empresa_norm or not email_norm:
        return

    _adicionar_flash(
        request,
        (
            f"Primeiro acesso da empresa preparado para {empresa_norm}. "
            f"O responsavel entra pelo Portal da empresa com o e-mail {email_norm} "
            "e define uma nova senha no primeiro login."
        ),
        tipo="success",
    )


def _usuario_nome(usuario: Usuario) -> str:
    return getattr(usuario, "nome_completo", None) or getattr(usuario, "nome", None) or f"Admin #{usuario.id}"


def _normalizar_identity_provider(provider: str | None) -> str:
    valor = str(provider or "").strip().lower()
    if valor in {"google", "microsoft"}:
        return valor
    return ""


def _identity_provider_enabled(provider: str | None) -> bool:
    provider_norm = _normalizar_identity_provider(provider)
    if provider_norm == "google":
        return ADMIN_LOGIN_GOOGLE_ENABLED
    if provider_norm == "microsoft":
        return ADMIN_LOGIN_MICROSOFT_ENABLED
    return False


def _identity_provider_visible(provider: str | None) -> bool:
    return _identity_provider_enabled(provider) and bool(_identity_provider_entrypoint(provider))


def _identity_provider_entrypoint(provider: str | None) -> str:
    provider_norm = _normalizar_identity_provider(provider)
    if provider_norm == "google":
        return ADMIN_LOGIN_GOOGLE_ENTRYPOINT
    if provider_norm == "microsoft":
        return ADMIN_LOGIN_MICROSOFT_ENTRYPOINT
    return ""


def _identity_provider_state(request: Request, *, provider: str) -> str:
    state = secrets.token_urlsafe(32)
    request.session[CHAVE_IDENTITY_STATE] = state
    request.session[CHAVE_IDENTITY_PROVIDER] = _normalizar_identity_provider(provider)
    return state


def _identity_provider_state_valid(request: Request, *, provider: str, state: str) -> bool:
    provider_norm = _normalizar_identity_provider(provider)
    state_norm = str(state or "").strip()
    if not provider_norm or not state_norm:
        return False

    session_provider = _normalizar_identity_provider(request.session.get(CHAVE_IDENTITY_PROVIDER))
    session_state = str(request.session.get(CHAVE_IDENTITY_STATE, "") or "").strip()
    csrf_state = str(request.session.get(CHAVE_CSRF_ADMIN, "") or "").strip()
    if session_provider == provider_norm and session_state and secrets.compare_digest(session_state, state_norm):
        return True
    if csrf_state and secrets.compare_digest(csrf_state, state_norm):
        return True
    return False


def _identity_provider_state_clear(request: Request) -> None:
    request.session.pop(CHAVE_IDENTITY_STATE, None)
    request.session.pop(CHAVE_IDENTITY_PROVIDER, None)


def _verificar_acesso_admin(usuario: Optional[Usuario]) -> TypeGuard[Usuario]:
    return (
        usuario is not None
        and int(getattr(usuario, "nivel_acesso", 0) or 0) in _NIVEIS_ADMIN
        and usuario_tem_escopo_plataforma(usuario)
        and str(getattr(usuario, "account_status", "active") or "active").strip().lower() == "active"
        and usuario_tem_acesso_portal(usuario, PORTAL_ADMIN)
    )


def _usuario_esta_bloqueado(usuario: Usuario) -> bool:
    try:
        return usuario_tem_bloqueio_ativo(usuario)
    except Exception:
        logger.warning(
            "Falha ao verificar bloqueio dinâmico do usuário | usuario_id=%s",
            getattr(usuario, "id", None),
            exc_info=True,
        )
        return True


def _garantir_csrf_na_sessao(request: Request) -> str:
    token = request.session.get(CHAVE_CSRF_ADMIN)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CHAVE_CSRF_ADMIN] = token
    return token


def _validar_csrf(request: Request, token_form: str = "") -> bool:
    token_sessao = request.session.get(CHAVE_CSRF_ADMIN, "")
    if not token_sessao:
        return False

    token_candidato = request.headers.get("X-CSRF-Token", "") or token_form
    return bool(token_candidato and secrets.compare_digest(token_sessao, token_candidato))


def _contexto_base(request: Request, **extra: Any) -> dict[str, Any]:
    sucesso = _normalizar_texto(request.query_params.get("sucesso", ""), max_len=300)
    erro = _normalizar_texto(request.query_params.get("erro", ""), max_len=300)
    mensagens_flash = _consumir_flash(request)
    if sucesso:
        mensagens_flash.append({"tipo": "success", "texto": sucesso})
    if erro:
        mensagens_flash.append({"tipo": "error", "texto": erro})

    contexto = {
        "request": request,
        "csrf_token": _garantir_csrf_na_sessao(request),
        "csp_nonce": getattr(request.state, "csp_nonce", ""),
        "em_producao": EM_PRODUCAO,
        "sucesso": sucesso,
        "erro": erro,
        "mensagens_flash": mensagens_flash,
        **contexto_template_perf(),
    }
    contexto.update(extra)
    return contexto


def _aplicar_headers_no_cache(response: HTMLResponse | RedirectResponse) -> None:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


def _render_template(
    request: Request,
    nome_template: str,
    contexto: dict[str, Any] | None = None,
    *,
    status_code: int = 200,
) -> HTMLResponse:
    resposta = templates.TemplateResponse(
        request,
        nome_template,
        _contexto_base(request, **(contexto or {})),
        status_code=status_code,
    )
    _aplicar_headers_no_cache(resposta)
    return resposta


def _render_login(request: Request, *, erro: str = "", status_code: int = 200) -> HTMLResponse:
    identidade_provedores: list[dict[str, str]] = []
    if _identity_provider_visible("google"):
        identidade_provedores.append(
            {
                "slug": "google",
                "label": "Continuar com Google",
                "start_url": "/admin/login/identity/google",
                "feedback": (
                    "A identidade Google só será aceita para operadores já autorizados no portal Admin-CEO."
                ),
            }
        )
    if _identity_provider_visible("microsoft"):
        identidade_provedores.append(
            {
                "slug": "microsoft",
                "label": "Continuar com Microsoft",
                "start_url": "/admin/login/identity/microsoft",
                "feedback": (
                    "A identidade Microsoft só será aceita para operadores já autorizados no portal Admin-CEO."
                ),
            }
        )

    return _render_template(
        request,
        TEMPLATE_ADMIN_LOGIN,
        {
            "erro": erro,
            "mfa_required": True,
            "identity_providers": identidade_provedores,
            "identity_providers_enabled": bool(identidade_provedores),
        },
        status_code=status_code,
    )


def _redirect_login() -> RedirectResponse:
    resposta = RedirectResponse(url=URL_LOGIN, status_code=303)
    _aplicar_headers_no_cache(resposta)
    return resposta


def _redirect_com_mensagem(url: str, *, sucesso: str = "", erro: str = "") -> RedirectResponse:
    if sucesso or erro:
        parsed = urlsplit(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if sucesso:
            query["sucesso"] = sucesso
        elif erro:
            query["erro"] = erro
        destino = urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(query, doseq=True, quote_via=quote),
                parsed.fragment,
            )
        )
    else:
        destino = url

    resposta = RedirectResponse(url=destino, status_code=303)
    _aplicar_headers_no_cache(resposta)
    return resposta


def _redirect_ok(url: str, mensagem: str) -> RedirectResponse:
    return _redirect_com_mensagem(url, sucesso=mensagem)


def _redirect_err(url: str, mensagem: str) -> RedirectResponse:
    return _redirect_com_mensagem(url, erro=mensagem)


def _limpar_sessao_admin(request: Request) -> None:
    token = obter_dados_sessao_portal(request.session, portal=PORTAL_ADMIN).get("token")
    if token:
        encerrar_sessao(token)

    limpar_sessao_portal(request.session, portal=PORTAL_ADMIN)
    request.session.pop(CHAVE_CSRF_ADMIN, None)


def _registrar_fluxo_mfa_pendente(
    request: Request,
    *,
    usuario_id: int,
    provider: str,
    lembrar: bool,
    return_to: str = URL_PAINEL,
) -> None:
    request.session[CHAVE_MFA_PENDING_UID] = int(usuario_id)
    request.session[CHAVE_MFA_PENDING_PROVIDER] = _normalizar_identity_provider(provider) or "password"
    request.session[CHAVE_MFA_PENDING_LEMBRAR] = bool(lembrar)
    request.session[CHAVE_MFA_PENDING_RETURN_TO] = str(return_to or URL_PAINEL)
    request.session[CHAVE_CSRF_ADMIN] = secrets.token_urlsafe(32)


def _limpar_fluxo_mfa_pendente(request: Request) -> None:
    request.session.pop(CHAVE_MFA_PENDING_UID, None)
    request.session.pop(CHAVE_MFA_PENDING_PROVIDER, None)
    request.session.pop(CHAVE_MFA_PENDING_LEMBRAR, None)
    request.session.pop(CHAVE_MFA_PENDING_RETURN_TO, None)


def _usuario_mfa_pendente(request: Request, banco: Session) -> Usuario | None:
    usuario_id = request.session.get(CHAVE_MFA_PENDING_UID)
    try:
        usuario_id_int = int(usuario_id)
    except (TypeError, ValueError):
        _limpar_fluxo_mfa_pendente(request)
        return None

    usuario = banco.get(Usuario, usuario_id_int)
    if not _verificar_acesso_admin(usuario):
        _limpar_fluxo_mfa_pendente(request)
        return None
    if _usuario_esta_bloqueado(usuario):
        _limpar_fluxo_mfa_pendente(request)
        return None
    return usuario


def _registrar_sessao_admin(
    request: Request,
    usuario: Usuario,
    *,
    lembrar: bool = False,
    mfa_level: str | None = None,
    reauth_at: datetime | None = None,
) -> None:
    token_anterior = obter_dados_sessao_portal(request.session, portal=PORTAL_ADMIN).get("token")
    if token_anterior:
        encerrar_sessao(token_anterior)

    momento_reauth = _normalizar_datetime_utc(reauth_at) or _agora_utc()
    mfa_level_norm = (
        str(mfa_level).strip().lower()
        if isinstance(mfa_level, str) and str(mfa_level).strip()
        else admin_session_mfa_level()
    )
    token_novo = criar_sessao(
        usuario.id,
        lembrar=lembrar,
        ip=getattr(getattr(request, "client", None), "host", None),
        user_agent=request.headers.get("user-agent", ""),
        portal=PORTAL_ADMIN,
        account_scope="platform",
        device_id=_device_id_request(request),
        mfa_level=mfa_level_norm,
        reauth_at=momento_reauth,
    )

    definir_sessao_portal(
        request.session,
        portal=PORTAL_ADMIN,
        token=token_novo,
        usuario_id=int(usuario.id),
        empresa_id=None,
        nivel_acesso=int(usuario.nivel_acesso),
        nome=_usuario_nome(usuario),
    )

    # Rotaciona o token CSRF no login.
    request.session[CHAVE_CSRF_ADMIN] = secrets.token_urlsafe(32)
    _limpar_fluxo_mfa_pendente(request)
    request.session.pop(CHAVE_REAUTH_RETURN_TO, None)


def _sessao_admin_reauth_expirada(request: Request) -> bool:
    if not admin_totp_enabled():
        return False
    token = obter_token_autenticacao_request(request)
    meta = obter_meta_sessao(token)
    if meta is None:
        return True
    reauth_at = _normalizar_datetime_utc(getattr(meta, "reauth_at", None))
    if reauth_at is None:
        return True
    return (_agora_utc() - reauth_at) > timedelta(minutes=get_admin_reauth_max_age_minutes())


def _registrar_reauth_admin(request: Request) -> None:
    token = obter_token_autenticacao_request(request)
    if token:
        atualizar_meta_sessao(token, reauth_at=_agora_utc(), mfa_level=admin_session_mfa_level())


def _redirect_step_up_admin(request: Request, *, return_to: str, mensagem: str) -> RedirectResponse:
    request.session[CHAVE_REAUTH_RETURN_TO] = str(return_to or URL_PAINEL)
    return _redirect_err("/admin/reauth", mensagem)


def _iniciar_fluxo_troca_senha(request: Request, *, usuario_id: int, lembrar: bool) -> None:
    _limpar_sessao_admin(request)
    request.session[CHAVE_CSRF_ADMIN] = secrets.token_urlsafe(32)
    request.session[CHAVE_TROCA_SENHA_UID] = int(usuario_id)
    request.session[CHAVE_TROCA_SENHA_PORTAL] = PORTAL_TROCA_SENHA_ADMIN
    request.session[CHAVE_TROCA_SENHA_LEMBRAR] = bool(lembrar)


def _limpar_fluxo_troca_senha(request: Request) -> None:
    request.session.pop(CHAVE_TROCA_SENHA_UID, None)
    request.session.pop(CHAVE_TROCA_SENHA_PORTAL, None)
    request.session.pop(CHAVE_TROCA_SENHA_LEMBRAR, None)


def _usuario_pendente_troca_senha(request: Request, banco: Session) -> Usuario | None:
    if request.session.get(CHAVE_TROCA_SENHA_PORTAL) != PORTAL_TROCA_SENHA_ADMIN:
        return None

    usuario_id = request.session.get(CHAVE_TROCA_SENHA_UID)
    try:
        usuario_id_int = int(usuario_id)
    except (TypeError, ValueError):
        _limpar_fluxo_troca_senha(request)
        return None

    usuario = banco.get(Usuario, usuario_id_int)
    if not usuario:
        _limpar_fluxo_troca_senha(request)
        return None
    if not _verificar_acesso_admin(usuario):
        _limpar_fluxo_troca_senha(request)
        return None
    if not bool(getattr(usuario, "senha_temporaria_ativa", False)):
        _limpar_fluxo_troca_senha(request)
        return None
    if _usuario_esta_bloqueado(usuario):
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
        TEMPLATE_ADMIN_TROCA_SENHA,
        {
            "erro": erro,
            "titulo_pagina": "Troca Obrigatória de Senha",
            "subtitulo_pagina": "Defina sua nova senha para liberar o acesso ao painel administrativo.",
            "acao_form": "/admin/trocar-senha",
            "rota_login": URL_LOGIN,
        },
        status_code=status_code,
    )


def _render_admin_mfa(
    request: Request,
    *,
    usuario: Usuario,
    modo: str,
    erro: str = "",
    status_code: int = 200,
    return_to: str = URL_PAINEL,
    expor_segredo: bool = False,
) -> HTMLResponse:
    pode_expor_segredo = (
        modo == "setup"
        and expor_segredo
        and not bool(getattr(usuario, "mfa_enrolled_at", None))
    )
    secret = (
        str(getattr(usuario, "mfa_secret_b32", "") or "").strip().upper()
        if pode_expor_segredo
        else ""
    )
    if modo == "setup":
        titulo = "Configurar MFA do Admin-CEO"
        subtitulo = "Cadastre o TOTP antes de concluir o acesso administrativo."
    elif modo == "reauth":
        titulo = "Reautenticar ação crítica"
        subtitulo = "Confirme o TOTP para liberar a ação administrativa sensível."
    else:
        titulo = "Confirmar MFA do Admin-CEO"
        subtitulo = "Confirme o código TOTP para concluir o acesso administrativo."
    return _render_template(
        request,
        TEMPLATE_ADMIN_MFA,
        {
            "erro": erro,
            "modo_mfa": modo,
            "mfa_titulo": titulo,
            "mfa_subtitulo": subtitulo,
            "mfa_secret_b32": secret,
            "mfa_secret_grouped": " ".join(secret[i : i + 4] for i in range(0, len(secret), 4)),
            "mfa_otpauth_uri": (
                build_totp_otpauth_uri(secret, account_name=str(usuario.email or "").lower())
                if secret
                else ""
            ),
            "return_to": str(return_to or URL_PAINEL),
        },
        status_code=status_code,
    )


__all__ = [
    "ADMIN_TOTP_ENABLED",
    "ADMIN_REAUTH_MAX_AGE_MINUTES",
    "admin_session_mfa_level",
    "admin_totp_enabled",
    "get_admin_reauth_max_age_minutes",
    "URL_LOGIN",
    "URL_PAINEL",
    "URL_CLIENTES",
    "URL_NOVO_CLIENTE",
    "TEMPLATE_ADMIN_LOGIN",
    "TEMPLATE_ADMIN_TROCA_SENHA",
    "TEMPLATE_ADMIN_MFA",
    "_normalizar_texto",
    "_normalizar_email",
    "_normalizar_plano",
    "_flash_senha_temporaria",
    "_flash_primeiro_acesso_empresa",
    "_verificar_acesso_admin",
    "_usuario_esta_bloqueado",
    "_validar_csrf",
    "_render_template",
    "_render_login",
    "_redirect_login",
    "_redirect_ok",
    "_redirect_err",
    "_limpar_sessao_admin",
    "_limpar_fluxo_mfa_pendente",
    "_redirect_step_up_admin",
    "_registrar_fluxo_mfa_pendente",
    "_registrar_reauth_admin",
    "_registrar_sessao_admin",
    "_identity_provider_enabled",
    "_identity_provider_entrypoint",
    "_identity_provider_state",
    "_identity_provider_state_clear",
    "_identity_provider_state_valid",
    "_identity_provider_visible",
    "_normalizar_identity_provider",
    "_iniciar_fluxo_troca_senha",
    "_limpar_fluxo_troca_senha",
    "_render_admin_mfa",
    "_sessao_admin_reauth_expirada",
    "_usuario_mfa_pendente",
    "_usuario_pendente_troca_senha",
    "_validar_nova_senha",
    "_render_troca_senha",
]
