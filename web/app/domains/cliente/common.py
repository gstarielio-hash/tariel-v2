from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.perf_support import contexto_template_perf
from app.shared.database import Usuario, obter_banco
from app.shared.security import exigir_admin_cliente
from app.shared.tenant_access import obter_empresa_usuario
from app.shared.tenant_admin_policy import (
    summarize_tenant_admin_policy,
    tenant_admin_can_take_case_actions,
    tenant_admin_can_view_cases,
)

CHAVE_CSRF_CLIENTE = "csrf_token_cliente"
VERSAO_APP = os.getenv("APP_BUILD_ID", "dev").strip() or "dev"
AMBIENTE_APP = os.getenv("AMBIENTE", "producao").strip().lower() or "producao"


def _versao_assets(request: Request) -> str:
    if AMBIENTE_APP == "producao":
        return VERSAO_APP

    nonce = getattr(request.state, "csp_nonce", "").strip()
    if not nonce:
        return VERSAO_APP

    return f"{VERSAO_APP}-{nonce[:8]}"


def garantir_csrf_cliente(request: Request) -> str:
    token = request.session.get(CHAVE_CSRF_CLIENTE)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CHAVE_CSRF_CLIENTE] = token
    request.session["csrf_token"] = token
    return token


def contexto_base_cliente(request: Request) -> dict[str, Any]:
    return {
        "request": request,
        "csrf_token": garantir_csrf_cliente(request),
        "csp_nonce": getattr(request.state, "csp_nonce", ""),
        "v_app": _versao_assets(request),
        **contexto_template_perf(),
    }


def validar_csrf_cliente(request: Request, token_form: str = "") -> bool:
    token_sessao = request.session.get(CHAVE_CSRF_CLIENTE) or request.session.get("csrf_token", "")
    if not token_sessao:
        return False

    token_candidato = request.headers.get("X-CSRF-Token", "") or token_form
    return bool(token_candidato and secrets.compare_digest(token_sessao, token_candidato))


def exigir_csrf_cliente(request: Request, token_form: str = "") -> None:
    if not validar_csrf_cliente(request, token_form):
        raise HTTPException(status_code=403, detail="Token CSRF inválido.")


def obter_politica_operacional_admin_cliente(
    banco: Session,
    usuario: Usuario,
) -> dict[str, Any]:
    empresa = obter_empresa_usuario(banco, usuario)
    return summarize_tenant_admin_policy(getattr(empresa, "admin_cliente_policy_json", None))


def exigir_admin_cliente_com_visibilidade_casos(
    usuario: Usuario = Depends(exigir_admin_cliente),
    banco: Session = Depends(obter_banco),
) -> Usuario:
    politica = obter_politica_operacional_admin_cliente(banco, usuario)
    if not tenant_admin_can_view_cases(politica):
        raise HTTPException(
            status_code=403,
            detail="Esta empresa usa o portal admin-cliente apenas com resumos agregados.",
        )
    return usuario


def exigir_admin_cliente_com_acoes_casos(
    usuario: Usuario = Depends(exigir_admin_cliente),
    banco: Session = Depends(obter_banco),
) -> Usuario:
    politica = obter_politica_operacional_admin_cliente(banco, usuario)
    if not tenant_admin_can_view_cases(politica):
        raise HTTPException(
            status_code=403,
            detail="Esta empresa usa o portal admin-cliente apenas com resumos agregados.",
        )
    if not tenant_admin_can_take_case_actions(politica):
        raise HTTPException(
            status_code=403,
            detail="Esta empresa permite ao admin-cliente apenas acompanhamento, sem agir nos casos.",
        )
    return usuario


__all__ = [
    "CHAVE_CSRF_CLIENTE",
    "contexto_base_cliente",
    "exigir_admin_cliente_com_acoes_casos",
    "exigir_admin_cliente_com_visibilidade_casos",
    "garantir_csrf_cliente",
    "obter_politica_operacional_admin_cliente",
    "validar_csrf_cliente",
    "exigir_csrf_cliente",
]
