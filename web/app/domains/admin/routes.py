"""
rotas_admin.py — Tariel.ia
Rotas do portal Admin-CEO

Responsabilidades:
- autenticação do painel admin central
- dashboard do admin-ceo
 - gestão SaaS de empresas assinantes
 - cadastro da empresa e do primeiro admin-cliente
- troca de plano, bloqueio e gestão de inspetores
"""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.admin.client_routes import (
    registrar_novo_cliente,
    resetar_senha_inspetor,
    roteador_admin_clientes,
)
from app.domains.admin.document_operations_summary import (
    build_document_operations_operational_summary,
)
from app.domains.admin.observability_summary import (
    build_admin_observability_operational_summary,
)
from app.domains.admin.production_ops_summary import (
    build_admin_production_operations_summary,
)
from app.shared.backend_hotspot_metrics import (
    backend_hotspot_observability_enabled,
    get_backend_hotspot_operational_summary,
    observe_backend_hotspot,
)
from app.domains.admin.auditoria import (
    listar_auditoria_admin_empresa,
    serializar_registro_auditoria_admin,
)
from app.domains.admin.portal_support import (
    CHAVE_REAUTH_RETURN_TO,
    URL_LOGIN,
    URL_PAINEL,
    admin_session_mfa_level,
    admin_totp_enabled,
    _identity_provider_enabled,
    _identity_provider_entrypoint,
    _identity_provider_state,
    _identity_provider_state_clear,
    _identity_provider_state_valid,
    _iniciar_fluxo_troca_senha,
    _limpar_fluxo_troca_senha,
    _limpar_fluxo_mfa_pendente,
    _limpar_sessao_admin,
    _normalizar_email,
    _normalizar_identity_provider,
    _redirect_login,
    _redirect_err,
    _redirect_ok,
    _redirect_step_up_admin,
    _registrar_sessao_admin,
    _registrar_fluxo_mfa_pendente,
    _registrar_reauth_admin,
    _render_login,
    _render_admin_mfa,
    _render_template,
    _render_troca_senha,
    _sessao_admin_reauth_expirada,
    _usuario_esta_bloqueado,
    _usuario_mfa_pendente,
    _usuario_pendente_troca_senha,
    _validar_csrf,
    _validar_nova_senha,
    _verificar_acesso_admin,
    get_admin_reauth_max_age_minutes,
)
from app.domains.admin.mfa import generate_totp_secret, verify_totp
from app.domains.admin.services import (
    apply_platform_settings_update,
    autenticar_identidade_admin,
    build_admin_platform_settings_console,
    buscar_metricas_ia_painel,
    listar_operadores_plataforma,
    registrar_auditoria_identidade_admin,
    remover_empresas_cliente_por_ids,
    remover_empresas_temporarias_auditoria_ui,
)
from app.shared.database import (
    RegistroAuditoriaEmpresa,
    Usuario,
    commit_ou_rollback_operacional,
    obter_banco,
)
from app.shared.security import (
    PORTAL_ADMIN,
    criar_hash_senha,
    obter_dados_sessao_portal,
    obter_usuario_html,
    token_esta_ativo,
    verificar_senha,
    verificar_senha_com_upgrade,
)
from app.v2.adapters.platform_admin_dashboard import build_platform_admin_dashboard_shadow_result
from app.v2.contracts.envelopes import utc_now
from app.v2.document import (
    document_hard_gate_observability_enabled,
    ensure_document_hard_gate_local_access,
    get_document_hard_gate_operational_summary,
    document_soft_gate_observability_enabled,
    ensure_document_soft_gate_local_access,
    get_document_soft_gate_operational_summary,
)
from app.v2.document.hard_gate_evidence import (
    document_hard_gate_durable_evidence_enabled,
    get_document_hard_gate_durable_summary,
)
from app.v2.mobile_rollout_metrics import (
    get_mobile_v2_rollout_operational_summary,
    mobile_v2_rollout_observability_enabled,
)
from app.v2.mobile_organic_validation import (
    start_mobile_v2_organic_validation_session,
    stop_mobile_v2_organic_validation_session,
)
from app.v2.mobile_operator_run import (
    finish_mobile_v2_operator_validation_run,
    get_mobile_v2_operator_validation_status,
    start_mobile_v2_operator_validation_run,
)
from app.v2.mobile_probe import execute_demo_mobile_v2_pilot_probe
from app.v2.report_pack_rollout_metrics import (
    get_report_pack_rollout_operational_summary,
    report_pack_rollout_observability_enabled,
)
from app.v2.runtime import actor_role_from_user, v2_platform_admin_projection_enabled

logger = logging.getLogger("tariel.admin")

roteador_admin = APIRouter()
_ADMIN_CLIENT_ROUTE_COMPAT = (
    registrar_novo_cliente,
    resetar_senha_inspetor,
)
_ADMIN_IDENTITY_UNAUTHORIZED_MESSAGE = (
    "Sua identidade foi confirmada, mas este e-mail não está autorizado para o portal "
    "Admin-CEO. Área restrita ao Admin-CEO. Para admins-cliente, use /cliente/login."
)


def _metodo_login_local_habilitado(usuario: Usuario) -> bool:
    return bool(getattr(usuario, "can_password_login", True))


def _conta_plataforma_ativa(usuario: Usuario) -> bool:
    return str(getattr(usuario, "account_scope", "tenant") or "tenant").strip().lower() == "platform" and str(
        getattr(usuario, "account_status", "active") or "active"
    ).strip().lower() == "active"


def _finalizar_login_admin(
    *,
    request: Request,
    banco: Session,
    usuario: Usuario,
    provider: str,
    lembrar: bool,
    subject: str = "",
    mfa_level: str | None = None,
) -> RedirectResponse:
    mfa_required = bool(getattr(usuario, "mfa_required", False))
    mfa_level_resolvido = (
        str(mfa_level).strip().lower()
        if isinstance(mfa_level, str) and str(mfa_level).strip()
        else (admin_session_mfa_level() if mfa_required else None)
    )
    if mfa_level_resolvido == "totp":
        detalhe_login = "Sessão administrativa emitida após autenticação e MFA."
    elif mfa_level_resolvido == "disabled":
        detalhe_login = "Sessão administrativa emitida após autenticação. MFA TOTP desabilitado por ambiente."
    else:
        detalhe_login = "Sessão administrativa emitida após autenticação."
    if hasattr(usuario, "registrar_login_sucesso"):
        try:
            usuario.registrar_login_sucesso(ip=request.client.host if request.client else None)
        except Exception:
            logger.warning("Falha ao registrar sucesso de login admin | usuario_id=%s", usuario.id, exc_info=True)

    registrar_auditoria_identidade_admin(
        banco,
        acao="admin_login_authenticated",
        resumo=f"Login {provider} concluído no Admin-CEO",
        detalhe=detalhe_login,
        provider=provider,
        email=str(usuario.email or "").lower(),
        reason="login_completed",
        usuario=usuario,
        actor_user_id=usuario.id,
        subject=subject,
        payload_extra={
            "mfa_required": mfa_required,
            "mfa_level": mfa_level_resolvido,
            "mfa_enabled": admin_totp_enabled(),
        },
    )
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao concluir login administrativo com MFA.",
    )
    _registrar_sessao_admin(request, usuario, lembrar=lembrar, mfa_level=mfa_level_resolvido)
    return RedirectResponse(url=URL_PAINEL, status_code=303)


def _admin_mfa_obrigatorio(usuario: Usuario) -> bool:
    return admin_totp_enabled() and bool(getattr(usuario, "mfa_required", False))


def _configuracoes_return_to() -> str:
    return "/admin/configuracoes"


def _exigir_step_up_configuracoes(request: Request, *, mensagem: str) -> RedirectResponse | None:
    if not _sessao_admin_reauth_expirada(request):
        return None
    return _redirect_step_up_admin(
        request,
        return_to=_configuracoes_return_to(),
        mensagem=mensagem,
    )


# =========================================================
# AUTENTICAÇÃO / ACESSO
# =========================================================


@roteador_admin.get("/login", response_class=HTMLResponse)
async def tela_login(
    request: Request,
    banco: Session = Depends(obter_banco),
):
    dados_sessao = obter_dados_sessao_portal(request.session, portal=PORTAL_ADMIN)
    token = dados_sessao.get("token")
    usuario_id = dados_sessao.get("usuario_id")

    if token and usuario_id and token_esta_ativo(token):
        usuario = banco.get(Usuario, usuario_id)
        if usuario and _verificar_acesso_admin(usuario):
            return RedirectResponse(url=URL_PAINEL, status_code=303)

    if token or usuario_id:
        _limpar_sessao_admin(request)
    _limpar_fluxo_mfa_pendente(request)
    request.session.pop(CHAVE_REAUTH_RETURN_TO, None)

    return _render_login(request)


@roteador_admin.get("/trocar-senha", response_class=HTMLResponse)
async def tela_troca_senha_admin(
    request: Request,
    banco: Session = Depends(obter_banco),
):
    if not _usuario_pendente_troca_senha(request, banco):
        return _redirect_login()
    return _render_troca_senha(request)


@roteador_admin.get("/mfa/setup", response_class=HTMLResponse)
async def tela_mfa_setup_admin(
    request: Request,
    banco: Session = Depends(obter_banco),
):
    usuario = _usuario_mfa_pendente(request, banco)
    if not usuario:
        return _redirect_login()
    if not admin_totp_enabled():
        provider = str(request.session.get("admin_mfa_pending_provider", "password") or "password")
        lembrar = bool(request.session.get("admin_mfa_pending_lembrar", False))
        return _finalizar_login_admin(
            request=request,
            banco=banco,
            usuario=usuario,
            provider=provider,
            lembrar=lembrar,
            mfa_level=admin_session_mfa_level(),
        )
    if bool(getattr(usuario, "mfa_enrolled_at", None)):
        return RedirectResponse(url="/admin/mfa/challenge", status_code=303)
    if not bool(getattr(usuario, "mfa_secret_b32", None)):
        usuario.mfa_secret_b32 = generate_totp_secret()
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao preparar segredo MFA do Admin-CEO.",
        )
    return _render_admin_mfa(request, usuario=usuario, modo="setup", expor_segredo=True)


@roteador_admin.post("/mfa/setup")
async def processar_mfa_setup_admin(
    request: Request,
    codigo: str = Form(default=""),
    csrf_token: str = Form(default=""),
    banco: Session = Depends(obter_banco),
):
    usuario = _usuario_mfa_pendente(request, banco)
    if not usuario:
        return _redirect_login()
    if not admin_totp_enabled():
        provider = str(request.session.get("admin_mfa_pending_provider", "password") or "password")
        lembrar = bool(request.session.get("admin_mfa_pending_lembrar", False))
        return _finalizar_login_admin(
            request=request,
            banco=banco,
            usuario=usuario,
            provider=provider,
            lembrar=lembrar,
            mfa_level=admin_session_mfa_level(),
        )
    if bool(getattr(usuario, "mfa_enrolled_at", None)):
        return RedirectResponse(url="/admin/mfa/challenge", status_code=303)
    if not _validar_csrf(request, csrf_token):
        return _render_admin_mfa(
            request,
            usuario=usuario,
            modo="setup",
            erro="Requisição inválida.",
            status_code=400,
            expor_segredo=False,
        )

    segredo = str(getattr(usuario, "mfa_secret_b32", "") or "").strip().upper()
    if not segredo:
        return RedirectResponse(url="/admin/mfa/setup", status_code=303)
    if not verify_totp(segredo, codigo):
        return _render_admin_mfa(
            request,
            usuario=usuario,
            modo="setup",
            erro="Código TOTP inválido.",
            status_code=401,
            expor_segredo=False,
        )

    usuario.mfa_required = True
    usuario.mfa_enrolled_at = utc_now()
    provider = str(request.session.get("admin_mfa_pending_provider", "password") or "password")
    lembrar = bool(request.session.get("admin_mfa_pending_lembrar", False))

    registrar_auditoria_identidade_admin(
        banco,
        acao="admin_mfa_enrolled",
        resumo="MFA cadastrado para operador da plataforma",
        detalhe="Cadastro TOTP concluído durante o acesso ao Admin-CEO.",
        provider=provider,
        email=str(usuario.email or "").lower(),
        reason="mfa_setup_completed",
        usuario=usuario,
        actor_user_id=usuario.id,
    )
    return _finalizar_login_admin(
        request=request,
        banco=banco,
        usuario=usuario,
        provider=provider,
        lembrar=lembrar,
    )


@roteador_admin.get("/mfa/challenge", response_class=HTMLResponse)
async def tela_mfa_challenge_admin(
    request: Request,
    banco: Session = Depends(obter_banco),
):
    usuario = _usuario_mfa_pendente(request, banco)
    if not usuario:
        return _redirect_login()
    if not admin_totp_enabled():
        provider = str(request.session.get("admin_mfa_pending_provider", "password") or "password")
        lembrar = bool(request.session.get("admin_mfa_pending_lembrar", False))
        return _finalizar_login_admin(
            request=request,
            banco=banco,
            usuario=usuario,
            provider=provider,
            lembrar=lembrar,
            mfa_level=admin_session_mfa_level(),
        )
    if not bool(getattr(usuario, "mfa_secret_b32", None)) or not bool(getattr(usuario, "mfa_enrolled_at", None)):
        return RedirectResponse(url="/admin/mfa/setup", status_code=303)
    return _render_admin_mfa(request, usuario=usuario, modo="challenge")


@roteador_admin.post("/mfa/challenge")
async def processar_mfa_challenge_admin(
    request: Request,
    codigo: str = Form(default=""),
    csrf_token: str = Form(default=""),
    banco: Session = Depends(obter_banco),
):
    usuario = _usuario_mfa_pendente(request, banco)
    if not usuario:
        return _redirect_login()
    if not admin_totp_enabled():
        provider = str(request.session.get("admin_mfa_pending_provider", "password") or "password")
        lembrar = bool(request.session.get("admin_mfa_pending_lembrar", False))
        return _finalizar_login_admin(
            request=request,
            banco=banco,
            usuario=usuario,
            provider=provider,
            lembrar=lembrar,
            mfa_level=admin_session_mfa_level(),
        )
    if not _validar_csrf(request, csrf_token):
        return _render_admin_mfa(request, usuario=usuario, modo="challenge", erro="Requisição inválida.", status_code=400)

    segredo = str(getattr(usuario, "mfa_secret_b32", "") or "").strip().upper()
    if not segredo:
        return RedirectResponse(url="/admin/mfa/setup", status_code=303)
    if not verify_totp(segredo, codigo):
        return _render_admin_mfa(
            request,
            usuario=usuario,
            modo="challenge",
            erro="Código TOTP inválido.",
            status_code=401,
        )

    provider = str(request.session.get("admin_mfa_pending_provider", "password") or "password")
    lembrar = bool(request.session.get("admin_mfa_pending_lembrar", False))
    return _finalizar_login_admin(
        request=request,
        banco=banco,
        usuario=usuario,
        provider=provider,
        lembrar=lembrar,
    )


@roteador_admin.get("/reauth", response_class=HTMLResponse)
async def tela_reauth_admin(
    request: Request,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    return_to = str(request.session.get(CHAVE_REAUTH_RETURN_TO, "") or URL_PAINEL)
    if not admin_totp_enabled():
        _registrar_reauth_admin(request)
        request.session.pop(CHAVE_REAUTH_RETURN_TO, None)
        return RedirectResponse(url=return_to, status_code=303)
    return _render_admin_mfa(request, usuario=usuario, modo="reauth", return_to=return_to)


@roteador_admin.post("/reauth")
async def processar_reauth_admin(
    request: Request,
    codigo: str = Form(default=""),
    csrf_token: str = Form(default=""),
    return_to: str = Form(default=URL_PAINEL),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    if not admin_totp_enabled():
        _registrar_reauth_admin(request)
        request.session.pop(CHAVE_REAUTH_RETURN_TO, None)
        return RedirectResponse(url=str(return_to or URL_PAINEL), status_code=303)
    if not _validar_csrf(request, csrf_token):
        return _render_admin_mfa(request, usuario=usuario, modo="reauth", erro="Requisição inválida.", status_code=400, return_to=return_to)

    segredo = str(getattr(usuario, "mfa_secret_b32", "") or "").strip().upper()
    if not segredo or not verify_totp(segredo, codigo):
        return _render_admin_mfa(
            request,
            usuario=usuario,
            modo="reauth",
            erro="Código TOTP inválido.",
            status_code=401,
            return_to=return_to,
        )

    _registrar_reauth_admin(request)
    registrar_auditoria_identidade_admin(
        banco,
        acao="admin_step_up_completed",
        resumo="Reautenticação do Admin-CEO concluída",
        detalhe=f"Step-up válido por {get_admin_reauth_max_age_minutes()} minutos para ações críticas.",
        provider="reauth",
        email=str(usuario.email or "").lower(),
        reason="step_up_completed",
        usuario=usuario,
        actor_user_id=usuario.id,
    )
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao registrar reautenticação do Admin-CEO.",
    )
    request.session.pop(CHAVE_REAUTH_RETURN_TO, None)
    return RedirectResponse(url=str(return_to or URL_PAINEL), status_code=303)


@roteador_admin.get("/login/identity/{provider}")
async def iniciar_login_identidade_admin(
    request: Request,
    provider: str,
):
    provider_norm = _normalizar_identity_provider(provider)
    if not provider_norm or not _identity_provider_enabled(provider_norm):
        return _render_login(
            request,
            erro="Provedor de identidade não disponível para o Admin-CEO.",
            status_code=404,
        )

    state = _identity_provider_state(request, provider=provider_norm)
    gateway_url = _identity_provider_entrypoint(provider_norm)
    if not gateway_url:
        return _render_login(
            request,
            erro=(
                "A identidade corporativa está habilitada, mas o gateway ainda não foi configurado "
                "para concluir o login do Admin-CEO."
            ),
            status_code=503,
        )

    callback_url = str(request.url_for("callback_login_identidade_admin", provider=provider_norm))
    query = urlencode({"state": state, "redirect_uri": callback_url})
    separator = "&" if "?" in gateway_url else "?"
    return RedirectResponse(url=f"{gateway_url}{separator}{query}", status_code=303)


@roteador_admin.get("/login/identity/{provider}/callback", name="callback_login_identidade_admin")
async def callback_login_identidade_admin(
    request: Request,
    provider: str,
    state: str = "",
    email: str = "",
    subject: str = "",
    error: str = "",
    banco: Session = Depends(obter_banco),
):
    provider_norm = _normalizar_identity_provider(provider)
    if not provider_norm or not _identity_provider_enabled(provider_norm):
        return _render_login(
            request,
            erro="Provedor de identidade não disponível para o Admin-CEO.",
            status_code=404,
        )

    if not _identity_provider_state_valid(request, provider=provider_norm, state=state):
        _identity_provider_state_clear(request)
        return _render_login(
            request,
            erro="Fluxo de identidade inválido ou expirado. Inicie o login novamente.",
            status_code=400,
        )

    if error:
        registrar_auditoria_identidade_admin(
            banco,
            acao="admin_identity_denied",
            resumo=f"Login {provider_norm} negado no Admin-CEO",
            detalhe="O gateway de identidade devolveu erro antes da autorização local.",
            provider=provider_norm,
            email=email or "desconhecido",
            reason=str(error or "").strip().lower()[:60] or "identity_gateway_error",
            subject=subject,
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao registrar auditoria de erro no callback de identidade admin.",
        )
        _identity_provider_state_clear(request)
        return _render_login(
            request,
            erro="A identidade corporativa não pôde ser confirmada. Tente novamente ou contate a operação da plataforma.",
            status_code=403,
        )

    try:
        resultado = autenticar_identidade_admin(
            banco,
            provider=provider_norm,
            email=email,
            subject=subject,
        )
    except ValueError:
        _identity_provider_state_clear(request)
        return _render_login(
            request,
            erro="A resposta do provedor de identidade veio incompleta. Refaça o login corporativo.",
            status_code=400,
        )

    if not resultado.authorized or resultado.user is None:
        registrar_auditoria_identidade_admin(
            banco,
            acao="admin_identity_denied",
            resumo=f"Login {provider_norm} negado no Admin-CEO",
            detalhe=resultado.message,
            provider=provider_norm,
            email=email or "desconhecido",
            reason=resultado.reason,
            usuario=resultado.user,
            subject=subject,
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao registrar auditoria de negação no callback de identidade admin.",
        )
        _identity_provider_state_clear(request)
        return _render_login(
            request,
            erro=resultado.message,
            status_code=403,
        )

    usuario = resultado.user
    registrar_auditoria_identidade_admin(
        banco,
        acao="admin_identity_authenticated",
        resumo=f"Login {provider_norm} autorizado no Admin-CEO",
        detalhe="Identidade corporativa validada sem autoprovisionamento.",
        provider=provider_norm,
        email=email,
        reason=resultado.reason,
        usuario=usuario,
        actor_user_id=usuario.id,
        subject=subject,
    )
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao concluir callback de identidade admin.",
    )

    _identity_provider_state_clear(request)
    if not _admin_mfa_obrigatorio(usuario):
        return _finalizar_login_admin(
            request=request,
            banco=banco,
            usuario=usuario,
            provider=provider_norm,
            lembrar=False,
            subject=subject,
        )
    _registrar_fluxo_mfa_pendente(
        request,
        usuario_id=usuario.id,
        provider=provider_norm,
        lembrar=False,
    )
    logger.info("Identidade admin validada, aguardando MFA | usuario_id=%s | provider=%s", usuario.id, provider_norm)
    if bool(getattr(usuario, "mfa_enrolled_at", None)) and bool(getattr(usuario, "mfa_secret_b32", None)):
        return RedirectResponse(url="/admin/mfa/challenge", status_code=303)
    return RedirectResponse(url="/admin/mfa/setup", status_code=303)


@roteador_admin.post("/trocar-senha")
async def processar_troca_senha_admin(
    request: Request,
    senha_atual: str = Form(default=""),
    nova_senha: str = Form(default=""),
    confirmar_senha: str = Form(default=""),
    csrf_token: str = Form(default=""),
    banco: Session = Depends(obter_banco),
):
    if not _validar_csrf(request, csrf_token):
        return _render_troca_senha(request, erro="Requisição inválida.", status_code=400)

    usuario = _usuario_pendente_troca_senha(request, banco)
    if not usuario:
        return _redirect_login()

    erro_validacao = _validar_nova_senha(senha_atual, nova_senha, confirmar_senha)
    if erro_validacao:
        return _render_troca_senha(request, erro=erro_validacao, status_code=400)

    if not verificar_senha(senha_atual, usuario.senha_hash):
        return _render_troca_senha(request, erro="Senha temporária inválida.", status_code=401)

    usuario.senha_hash = criar_hash_senha(nova_senha)
    usuario.senha_temporaria_ativa = False
    if hasattr(usuario, "registrar_login_sucesso"):
        try:
            usuario.registrar_login_sucesso(ip=request.client.host if request.client else None)
        except Exception:
            logger.warning(
                "Falha ao registrar login após troca obrigatória de senha | usuario_id=%s",
                usuario.id,
                exc_info=True,
            )
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao confirmar troca obrigatoria de senha do admin.",
    )

    lembrar_troca = bool(request.session.get("troca_senha_lembrar", False))
    _limpar_fluxo_troca_senha(request)
    if not _admin_mfa_obrigatorio(usuario):
        return _finalizar_login_admin(
            request=request,
            banco=banco,
            usuario=usuario,
            provider="password",
            lembrar=lembrar_troca,
        )
    _registrar_fluxo_mfa_pendente(
        request,
        usuario_id=usuario.id,
        provider="password",
        lembrar=lembrar_troca,
    )

    logger.info("Troca obrigatória de senha concluída, aguardando MFA | usuario_id=%s", usuario.id)
    if bool(getattr(usuario, "mfa_enrolled_at", None)) and bool(getattr(usuario, "mfa_secret_b32", None)):
        return RedirectResponse(url="/admin/mfa/challenge", status_code=303)
    return RedirectResponse(url="/admin/mfa/setup", status_code=303)


@roteador_admin.post("/login")
async def processar_login(
    request: Request,
    email: str = Form(default=""),
    senha: str = Form(default=""),
    lembrar: str = Form(default=""),
    csrf_token: str = Form(default=""),
    banco: Session = Depends(obter_banco),
):
    email_normalizado = _normalizar_email(email)
    senha = senha or ""

    if not email_normalizado or not senha:
        return _render_login(
            request,
            erro="Preencha e-mail e senha.",
            status_code=400,
        )

    if not _validar_csrf(request, csrf_token):
        return _render_login(
            request,
            erro="Requisição inválida.",
            status_code=400,
        )

    usuario = banco.scalar(select(Usuario).where(Usuario.email == email_normalizado))
    senha_valida = False
    hash_atualizado: str | None = None
    if usuario:
        senha_valida, hash_atualizado = verificar_senha_com_upgrade(senha, usuario.senha_hash)

    if not usuario or not senha_valida:
        if usuario and hasattr(usuario, "incrementar_tentativa_falha"):
            try:
                usuario.incrementar_tentativa_falha()
                banco.flush()
            except Exception:
                banco.rollback()
                logger.warning(
                    "Falha ao atualizar tentativas de login | usuario_id=%s",
                    getattr(usuario, "id", None),
                    exc_info=True,
                )

        registrar_auditoria_identidade_admin(
            banco,
            acao="admin_identity_denied",
            resumo="Login local negado no Admin-CEO",
            detalhe="Credenciais inválidas para o acesso administrativo.",
            provider="password",
            email=email_normalizado,
            reason="invalid_credentials",
            usuario=usuario,
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao registrar auditoria de credenciais inválidas do admin.",
        )

        return _render_login(
            request,
            erro="Credenciais inválidas.",
            status_code=401,
        )

    if not _verificar_acesso_admin(usuario):
        registrar_auditoria_identidade_admin(
            banco,
            acao="admin_identity_denied",
            resumo="Login local negado no Admin-CEO",
            detalhe=_ADMIN_IDENTITY_UNAUTHORIZED_MESSAGE,
            provider="password",
            email=email_normalizado,
            reason="portal_not_authorized",
            usuario=usuario,
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao registrar auditoria de negação no login local do admin.",
        )
        return _render_login(
            request,
            erro=_ADMIN_IDENTITY_UNAUTHORIZED_MESSAGE,
            status_code=403,
        )

    if not _conta_plataforma_ativa(usuario):
        registrar_auditoria_identidade_admin(
            banco,
            acao="admin_identity_denied",
            resumo="Login local negado no Admin-CEO",
            detalhe="A conta de plataforma não está ativa para este operador.",
            provider="password",
            email=email_normalizado,
            reason="account_not_platform_active",
            usuario=usuario,
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao registrar auditoria de conta de plataforma inativa.",
        )
        return _render_login(
            request,
            erro="Sua conta de plataforma não está ativa para o Admin-CEO.",
            status_code=403,
        )

    if not _metodo_login_local_habilitado(usuario):
        registrar_auditoria_identidade_admin(
            banco,
            acao="admin_identity_denied",
            resumo="Login local negado no Admin-CEO",
            detalhe="O método senha não está liberado para este operador da plataforma.",
            provider="password",
            email=email_normalizado,
            reason="password_login_disabled",
            usuario=usuario,
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao registrar auditoria de método local desabilitado.",
        )
        return _render_login(
            request,
            erro="Sua conta está autorizada, mas o login por senha não está habilitado para o Admin-CEO.",
            status_code=403,
        )

    if not bool(getattr(usuario, "identidade_admin_ativa", True)):
        registrar_auditoria_identidade_admin(
            banco,
            acao="admin_identity_denied",
            resumo="Login local negado no Admin-CEO",
            detalhe="A identidade administrativa existe, mas está sem autorização ativa para o portal Admin-CEO.",
            provider="password",
            email=email_normalizado,
            reason=str(getattr(usuario, "identidade_admin_status", "inactive")),
            usuario=usuario,
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao registrar auditoria de identidade inativa no login local do admin.",
        )
        return _render_login(
            request,
            erro="Sua identidade administrativa existe, mas está sem autorização ativa para o portal Admin-CEO.",
            status_code=403,
        )

    if _usuario_esta_bloqueado(usuario):
        registrar_auditoria_identidade_admin(
            banco,
            acao="admin_identity_denied",
            resumo="Login local negado no Admin-CEO",
            detalhe="Conta administrativa bloqueada para o portal Admin-CEO.",
            provider="password",
            email=email_normalizado,
            reason="account_blocked",
            usuario=usuario,
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao registrar auditoria de bloqueio no login local do admin.",
        )
        return _render_login(
            request,
            erro="Conta bloqueada. Contate o suporte.",
            status_code=403,
        )

    if bool(getattr(usuario, "senha_temporaria_ativa", False)):
        _iniciar_fluxo_troca_senha(request, usuario_id=usuario.id, lembrar=False)
        return RedirectResponse(url="/admin/trocar-senha", status_code=303)

    if hash_atualizado:
        usuario.senha_hash = hash_atualizado

    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao confirmar login do admin.",
    )
    if not _admin_mfa_obrigatorio(usuario):
        return _finalizar_login_admin(
            request=request,
            banco=banco,
            usuario=usuario,
            provider="password",
            lembrar=str(lembrar or "").strip().lower() in {"1", "true", "on", "yes"},
        )
    _registrar_fluxo_mfa_pendente(
        request,
        usuario_id=usuario.id,
        provider="password",
        lembrar=str(lembrar or "").strip().lower() in {"1", "true", "on", "yes"},
    )

    logger.info("Senha admin validada, aguardando MFA | usuario_id=%s | email=%s", usuario.id, email_normalizado)
    if bool(getattr(usuario, "mfa_enrolled_at", None)) and bool(getattr(usuario, "mfa_secret_b32", None)):
        return RedirectResponse(url="/admin/mfa/challenge", status_code=303)
    return RedirectResponse(url="/admin/mfa/setup", status_code=303)


@roteador_admin.post("/logout")
async def fazer_logout(
    request: Request,
    csrf_token: str = Form(default=""),
):
    if not _validar_csrf(request, csrf_token):
        return _redirect_login()

    _limpar_sessao_admin(request)
    _limpar_fluxo_mfa_pendente(request)
    request.session.pop(CHAVE_REAUTH_RETURN_TO, None)
    return RedirectResponse(url=URL_LOGIN, status_code=303)


# =========================================================
# DASHBOARD
# =========================================================


def _registrar_shadow_platform_admin_dashboard(
    *,
    request: Request,
    banco: Session,
    usuario: Usuario,
    dados_dashboard: dict[str, object],
) -> None:
    if not v2_platform_admin_projection_enabled():
        return

    clientes = dados_dashboard.get("clientes")
    tenants = clientes if isinstance(clientes, list) else []
    recent_admin_actions = int(
        banco.scalar(
            select(func.count(RegistroAuditoriaEmpresa.id)).where(
                RegistroAuditoriaEmpresa.criado_em >= (utc_now() - timedelta(days=30)),
            )
        )
        or 0
    )
    total_inspections_raw = dados_dashboard.get("total_inspecoes")
    chart_labels_raw = dados_dashboard.get("labels_grafico")
    chart_values_raw = dados_dashboard.get("valores_grafico")
    resultado = build_platform_admin_dashboard_shadow_result(
        tenant_summaries=tenants,
        total_inspections=(
            int(total_inspections_raw) if isinstance(total_inspections_raw, (int, str)) else 0
        ),
        total_api_revenue_brl=dados_dashboard.get("receita_ia_total"),
        chart_labels=list(chart_labels_raw) if isinstance(chart_labels_raw, list) else [],
        chart_values=list(chart_values_raw) if isinstance(chart_values_raw, list) else [],
        recent_admin_actions=recent_admin_actions,
        actor_id=usuario.id,
        actor_role=actor_role_from_user(usuario),
        source_channel="admin_dashboard",
        legacy_dashboard_data=dados_dashboard,
    )
    request.state.v2_platform_admin_projection_result = resultado.model_dump(mode="python")


@roteador_admin.get("/painel", response_class=HTMLResponse)
async def painel_faturamento(
    request: Request,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    with observe_backend_hotspot(
        "admin_dashboard_html",
        request=request,
        surface="adminceo",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        route_path="/admin/painel",
        method="GET",
    ) as hotspot:
        if not _verificar_acesso_admin(usuario):
            resposta = _redirect_login()
            hotspot.outcome = "redirect_login"
            hotspot.response_status_code = getattr(resposta, "status_code", 303)
            return resposta

        try:
            dados = buscar_metricas_ia_painel(banco)
        except Exception:
            logger.error(
                "Falha ao buscar métricas do painel admin | usuario_id=%s",
                usuario.id if usuario else None,
                exc_info=True,
            )
            dados = {}
            hotspot.status = "error"
            hotspot.error_class = "infra"
            hotspot.error_code = "admin_dashboard_metrics_failed"
            hotspot.detail["metrics_fallback"] = True

        if usuario is not None and isinstance(dados, dict):
            try:
                _registrar_shadow_platform_admin_dashboard(
                    request=request,
                    banco=banco,
                    usuario=usuario,
                    dados_dashboard=dados,
                )
            except Exception:
                logger.debug("Falha ao registrar platform admin view em shadow mode.", exc_info=True)
                request.state.v2_platform_admin_projection_error = "platform_admin_projection_failed"

        hotspot.outcome = "render_dashboard"
        hotspot.response_status_code = 200
        return _render_template(
            request,
            "admin/dashboard.html",
            {
                "dados": dados,
                "usuario": usuario,
            },
        )


@roteador_admin.get("/auditoria", response_class=HTMLResponse)
async def pagina_auditoria_admin(
    request: Request,
    empresa_id: int | None = None,
    limite: int = 30,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    itens = [
        serializar_registro_auditoria_admin(item)
        for item in listar_auditoria_admin_empresa(
            banco,
            empresa_id=empresa_id,
            limite=limite,
        )
    ]
    return _render_template(
        request,
        "admin/admin_auditoria.html",
        {
            "usuario": usuario,
            "itens": itens,
            "empresa_id_filtro": empresa_id,
            "limite_filtro": max(1, min(int(limite or 30), 100)),
        },
    )


@roteador_admin.get("/configuracoes", response_class=HTMLResponse)
async def pagina_configuracoes_admin(
    request: Request,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    console = build_admin_platform_settings_console(banco)
    return _render_template(
        request,
        "admin/admin_configuracoes.html",
        {
            "usuario": usuario,
            **console,
        },
    )


@roteador_admin.post("/configuracoes/acesso")
async def atualizar_configuracoes_acesso_admin(
    request: Request,
    csrf_token: str = Form(default=""),
    admin_reauth_max_age_minutes: str = Form(default=""),
    motivo_alteracao: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(_configuracoes_return_to(), "Requisição inválida.")
    step_up = _exigir_step_up_configuracoes(
        request,
        mensagem="Reautenticação necessária para alterar a política de acesso do Admin-CEO.",
    )
    if step_up is not None:
        return step_up

    try:
        apply_platform_settings_update(
            banco,
            actor_user=usuario,
            group_key="access",
            reason=motivo_alteracao,
            updates={"admin_reauth_max_age_minutes": admin_reauth_max_age_minutes},
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao salvar a política de acesso da plataforma.",
        )
    except ValueError as erro:
        return _redirect_err(_configuracoes_return_to(), str(erro))
    return _redirect_ok(_configuracoes_return_to(), "Política de acesso atualizada.")


@roteador_admin.post("/configuracoes/suporte-excepcional")
async def atualizar_configuracoes_suporte_excepcional_admin(
    request: Request,
    csrf_token: str = Form(default=""),
    support_exceptional_mode: str = Form(default=""),
    support_exceptional_approval_required: str = Form(default=""),
    support_exceptional_justification_required: str = Form(default=""),
    support_exceptional_max_duration_minutes: str = Form(default=""),
    support_exceptional_scope_level: str = Form(default=""),
    motivo_alteracao: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(_configuracoes_return_to(), "Requisição inválida.")
    step_up = _exigir_step_up_configuracoes(
        request,
        mensagem="Reautenticação necessária para alterar suporte excepcional.",
    )
    if step_up is not None:
        return step_up

    try:
        apply_platform_settings_update(
            banco,
            actor_user=usuario,
            group_key="support",
            reason=motivo_alteracao,
            updates={
                "support_exceptional_mode": support_exceptional_mode,
                "support_exceptional_approval_required": support_exceptional_approval_required == "1",
                "support_exceptional_justification_required": support_exceptional_justification_required == "1",
                "support_exceptional_max_duration_minutes": support_exceptional_max_duration_minutes,
                "support_exceptional_scope_level": support_exceptional_scope_level,
            },
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao salvar a política de suporte excepcional.",
        )
    except ValueError as erro:
        return _redirect_err(_configuracoes_return_to(), str(erro))
    return _redirect_ok(_configuracoes_return_to(), "Política de suporte excepcional atualizada.")


@roteador_admin.post("/configuracoes/rollout")
async def atualizar_configuracoes_rollout_admin(
    request: Request,
    csrf_token: str = Form(default=""),
    review_ui_canonical: str = Form(default=""),
    motivo_alteracao: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(_configuracoes_return_to(), "Requisição inválida.")
    step_up = _exigir_step_up_configuracoes(
        request,
        mensagem="Reautenticação necessária para alterar o rollout operacional da revisão.",
    )
    if step_up is not None:
        return step_up

    try:
        apply_platform_settings_update(
            banco,
            actor_user=usuario,
            group_key="rollout",
            reason=motivo_alteracao,
            updates={"review_ui_canonical": review_ui_canonical},
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao salvar o rollout operacional.",
        )
    except ValueError as erro:
        return _redirect_err(_configuracoes_return_to(), str(erro))
    return _redirect_ok(_configuracoes_return_to(), "Rollout operacional atualizado.")


@roteador_admin.post("/configuracoes/defaults")
async def atualizar_configuracoes_defaults_admin(
    request: Request,
    csrf_token: str = Form(default=""),
    default_new_tenant_plan: str = Form(default=""),
    motivo_alteracao: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(_configuracoes_return_to(), "Requisição inválida.")
    step_up = _exigir_step_up_configuracoes(
        request,
        mensagem="Reautenticação necessária para alterar defaults globais da plataforma.",
    )
    if step_up is not None:
        return step_up

    try:
        apply_platform_settings_update(
            banco,
            actor_user=usuario,
            group_key="defaults",
            reason=motivo_alteracao,
            updates={"default_new_tenant_plan": default_new_tenant_plan},
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao salvar os defaults globais da plataforma.",
        )
    except ValueError as erro:
        return _redirect_err(_configuracoes_return_to(), str(erro))
    return _redirect_ok(_configuracoes_return_to(), "Defaults globais atualizados.")


@roteador_admin.post("/configuracoes/manutencao/limpar-auditoria-ui")
async def limpar_empresas_temporarias_auditoria_ui_admin(
    request: Request,
    csrf_token: str = Form(default=""),
    company_ids: str = Form(default=""),
    confirmation_phrase: str = Form(default=""),
    motivo_operacao: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(_configuracoes_return_to(), "Requisição inválida.")
    step_up = _exigir_step_up_configuracoes(
        request,
        mensagem="Reautenticação necessária para remover tenants temporários de auditoria UI.",
    )
    if step_up is not None:
        return step_up

    confirmacao = str(confirmation_phrase or "").strip()
    if confirmacao != "EXCLUIR TARIEL UI AUDIT":
        return _redirect_err(
            _configuracoes_return_to(),
            "Confirmação inválida para a limpeza dos tenants temporários.",
        )

    ids: list[int] = []
    bruto = str(company_ids or "").strip()
    if bruto:
        try:
            ids = sorted({int(item) for item in bruto.split(",") if str(item).strip()})
        except ValueError:
            return _redirect_err(
                _configuracoes_return_to(),
                "Informe IDs válidos separados por vírgula para a limpeza temporária.",
            )

    try:
        resultado = remover_empresas_temporarias_auditoria_ui(
            banco,
            actor_user=usuario,
            company_ids=ids,
            reason=motivo_operacao,
        )
    except ValueError as erro:
        return _redirect_err(_configuracoes_return_to(), str(erro))

    return _redirect_ok(
        _configuracoes_return_to(),
        (
            f"{int(resultado['companies_deleted'])} empresa(s) temporária(s) removida(s) "
            f"e {int(resultado['sessions_invalidated'])} sessão(ões) encerrada(s)."
        ),
    )


@roteador_admin.post("/configuracoes/manutencao/remover-tenants-cliente")
async def remover_tenants_cliente_admin(
    request: Request,
    csrf_token: str = Form(default=""),
    company_ids: str = Form(default=""),
    confirmation_phrase: str = Form(default=""),
    motivo_operacao: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(_configuracoes_return_to(), "Requisição inválida.")
    step_up = _exigir_step_up_configuracoes(
        request,
        mensagem="Reautenticação necessária para remover empresas cliente do ambiente.",
    )
    if step_up is not None:
        return step_up

    confirmacao = str(confirmation_phrase or "").strip()
    if confirmacao != "EXCLUIR EMPRESAS CLIENTE":
        return _redirect_err(
            _configuracoes_return_to(),
            "Confirmação inválida para a remoção das empresas cliente.",
        )

    try:
        ids = sorted({int(item) for item in str(company_ids or "").split(",") if str(item).strip()})
    except ValueError:
        return _redirect_err(
            _configuracoes_return_to(),
            "Informe IDs válidos separados por vírgula para remover empresas cliente.",
        )

    try:
        resultado = remover_empresas_cliente_por_ids(
            banco,
            actor_user=usuario,
            company_ids=ids,
            reason=motivo_operacao,
        )
    except ValueError as erro:
        return _redirect_err(_configuracoes_return_to(), str(erro))

    return _redirect_ok(
        _configuracoes_return_to(),
        (
            f"{int(resultado['companies_deleted'])} empresa(s) cliente removida(s) "
            f"e {int(resultado['sessions_invalidated'])} sessão(ões) encerrada(s)."
        ),
    )


@roteador_admin.get("/api/auditoria")
async def api_auditoria_admin(
    empresa_id: int | None = None,
    limite: int = 30,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Nao autenticado."},
        )

    itens = [
        serializar_registro_auditoria_admin(item)
        for item in listar_auditoria_admin_empresa(
            banco,
            empresa_id=empresa_id,
            limite=limite,
        )
    ]
    return JSONResponse({"itens": itens})


@roteador_admin.get("/api/operadores")
async def api_operadores_plataforma(
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(status_code=401, content={"detail": "Nao autenticado."})
    return JSONResponse({"itens": listar_operadores_plataforma(banco)})


@roteador_admin.get("/api/observability/summary")
async def api_observability_summary(
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Nao autenticado."},
        )

    return JSONResponse(build_admin_observability_operational_summary())


@roteador_admin.get("/api/production-ops/summary")
async def api_production_ops_summary(
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Nao autenticado."},
        )

    return JSONResponse(build_admin_production_operations_summary())


@roteador_admin.get("/api/metricas-grafico")
async def api_metricas_grafico(
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    try:
        dados = buscar_metricas_ia_painel(banco)
    except Exception:
        logger.error(
            "Falha ao buscar métricas do gráfico admin | usuario_id=%s",
            usuario.id if usuario else None,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro ao carregar métricas."},
        )

    labels = [str(item) for item in dados.get("labels_grafico", [])]
    valores = [int(item) for item in dados.get("valores_grafico", [])]
    return JSONResponse(
        content={
            "labels": labels,
            "valores": valores,
        }
    )


@roteador_admin.get("/api/mobile-v2-rollout/summary")
async def api_mobile_v2_rollout_summary(
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    if not mobile_v2_rollout_observability_enabled():
        return JSONResponse(
            status_code=404,
            content={"detail": "Recurso não encontrado."},
        )

    return JSONResponse(content=get_mobile_v2_rollout_operational_summary())


@roteador_admin.get("/api/report-pack-rollout/summary")
async def api_report_pack_rollout_summary(
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    if not report_pack_rollout_observability_enabled():
        return JSONResponse(
            status_code=404,
            content={"detail": "Recurso não encontrado."},
        )

    return JSONResponse(content=get_report_pack_rollout_operational_summary())


@roteador_admin.get("/api/backend-hotspots/summary")
async def api_backend_hotspots_summary(
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    if not backend_hotspot_observability_enabled():
        return JSONResponse(
            status_code=404,
            content={"detail": "Recurso não encontrado."},
        )

    return JSONResponse(content=get_backend_hotspot_operational_summary())


@roteador_admin.get("/api/document-soft-gate/summary")
async def api_document_soft_gate_summary(
    request: Request,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    if not document_soft_gate_observability_enabled():
        return JSONResponse(
            status_code=404,
            content={"detail": "Recurso não encontrado."},
        )

    try:
        ensure_document_soft_gate_local_access(
            getattr(getattr(request, "client", None), "host", None),
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ação disponível apenas em contexto local controlado."},
        )

    return JSONResponse(content=get_document_soft_gate_operational_summary())


@roteador_admin.get("/api/document-hard-gate/summary")
async def api_document_hard_gate_summary(
    request: Request,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    if not document_hard_gate_observability_enabled():
        return JSONResponse(
            status_code=404,
            content={"detail": "Recurso não encontrado."},
        )

    try:
        ensure_document_hard_gate_local_access(
            getattr(getattr(request, "client", None), "host", None),
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ação disponível apenas em contexto local controlado."},
        )

    return JSONResponse(content=get_document_hard_gate_operational_summary())


@roteador_admin.get("/api/document-hard-gate/durable-summary")
async def api_document_hard_gate_durable_summary(
    request: Request,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    if not document_hard_gate_durable_evidence_enabled():
        return JSONResponse(
            status_code=404,
            content={"detail": "Recurso não encontrado."},
        )

    try:
        ensure_document_hard_gate_local_access(
            getattr(getattr(request, "client", None), "host", None),
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ação disponível apenas em contexto local controlado."},
        )

    return JSONResponse(content=get_document_hard_gate_durable_summary())


@roteador_admin.get("/api/document-operations/summary")
async def api_document_operations_summary(
    request: Request,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    try:
        ensure_document_hard_gate_local_access(
            getattr(getattr(request, "client", None), "host", None),
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ação disponível apenas em contexto local controlado."},
        )

    return JSONResponse(content=build_document_operations_operational_summary(banco))


@roteador_admin.post("/api/mobile-v2-rollout/probe/run")
async def api_mobile_v2_rollout_probe_run(
    request: Request,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    resultado = await execute_demo_mobile_v2_pilot_probe(
        remote_host=getattr(getattr(request, "client", None), "host", None),
        trigger_source="admin_api",
    )
    status_code = 200 if resultado.ok else 409
    if resultado.status == "disabled":
        status_code = 404
    return JSONResponse(status_code=status_code, content=resultado.to_public_payload())


@roteador_admin.post("/api/mobile-v2-rollout/organic-validation/start")
async def api_mobile_v2_rollout_organic_validation_start(
    request: Request,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    try:
        resumo = start_mobile_v2_organic_validation_session(
            remote_host=getattr(getattr(request, "client", None), "host", None),
            trigger_source="admin_api",
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ação disponível apenas em contexto local controlado."},
        )
    except RuntimeError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=resumo.to_public_payload())


@roteador_admin.post("/api/mobile-v2-rollout/organic-validation/stop")
async def api_mobile_v2_rollout_organic_validation_stop(
    request: Request,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    try:
        resumo = stop_mobile_v2_organic_validation_session(
            remote_host=getattr(getattr(request, "client", None), "host", None),
            trigger_source="admin_api",
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ação disponível apenas em contexto local controlado."},
        )
    except RuntimeError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=resumo.to_public_payload())


@roteador_admin.post("/api/mobile-v2-rollout/operator-run/start")
async def api_mobile_v2_rollout_operator_run_start(
    request: Request,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    try:
        status = start_mobile_v2_operator_validation_run(
            remote_host=getattr(getattr(request, "client", None), "host", None),
            trigger_source="admin_api",
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ação disponível apenas em contexto local controlado."},
        )
    except RuntimeError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    status_code = (
        409 if status.operator_run_outcome == "blocked_no_targets" else 200
    )
    return JSONResponse(status_code=status_code, content=status.to_public_payload())


@roteador_admin.get("/api/mobile-v2-rollout/operator-run/status")
async def api_mobile_v2_rollout_operator_run_status(
    request: Request,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    try:
        status = get_mobile_v2_operator_validation_status(
            remote_host=getattr(getattr(request, "client", None), "host", None),
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ação disponível apenas em contexto local controlado."},
        )

    return JSONResponse(status_code=200, content=status.to_public_payload())


@roteador_admin.post("/api/mobile-v2-rollout/operator-run/finish")
async def api_mobile_v2_rollout_operator_run_finish(
    request: Request,
    abort: bool = False,
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return JSONResponse(
            status_code=401,
            content={"detail": "Não autenticado."},
        )

    try:
        status = finish_mobile_v2_operator_validation_run(
            remote_host=getattr(getattr(request, "client", None), "host", None),
            trigger_source="admin_api",
            abort=abort,
        )
    except PermissionError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Ação disponível apenas em contexto local controlado."},
        )
    except RuntimeError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=status.to_public_payload())


roteador_admin.include_router(roteador_admin_clientes)
