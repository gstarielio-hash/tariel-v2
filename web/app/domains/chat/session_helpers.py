"""Helpers de sessão/CSRF/estado para o domínio Chat/Inspetor."""

from __future__ import annotations

import os
import secrets
from typing import Any, Optional

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.core.perf_support import contexto_template_perf
from app.domains.chat.laudo_state_helpers import (
    CacheResumoLaudoRequest,
    criar_cache_resumo_laudos,
    laudo_permite_edicao_inspetor,
    laudo_permite_reabrir,
    laudo_tem_interacao,
    obter_contexto_modo_entrada_laudo,
    obter_estado_api_laudo,
    obter_status_card_laudo,
    serializar_contexto_case_lifecycle_legado,
)
from app.domains.chat.normalization import TIPOS_TEMPLATE_VALIDOS
from app.shared.security import obter_token_bearer_request, token_esta_ativo
from app.shared.database import Laudo, Usuario
from app.shared.tenant_report_catalog import build_tenant_template_option_snapshot

CHAVE_CSRF_INSPETOR = "csrf_token_inspetor"
CHAVE_CONTEXTO_INICIAL_LAUDO = "laudos_contexto_inicial"
VERSAO_APP = os.getenv("APP_BUILD_ID", "dev").strip() or "dev"
AMBIENTE_APP = os.getenv("AMBIENTE", "producao").strip().lower() or "producao"


def _versao_assets(request: Request) -> str:
    if AMBIENTE_APP == "producao":
        return VERSAO_APP

    nonce = getattr(request.state, "csp_nonce", "").strip()
    if not nonce:
        return VERSAO_APP

    return f"{VERSAO_APP}-{nonce[:8]}"


def build_inspector_template_catalog_payload(
    banco: Session,
    *,
    empresa_id: Any,
) -> dict[str, Any]:
    try:
        empresa_id_int = int(empresa_id or 0)
    except (TypeError, ValueError):
        empresa_id_int = 0

    if empresa_id_int <= 0:
        return {
            "tipos_relatorio": dict(TIPOS_TEMPLATE_VALIDOS),
            "tipo_template_options": [],
            "catalog_governed_mode": False,
            "catalog_state": "legacy_open",
            "catalog_permissions": {},
        }

    template_snapshot = build_tenant_template_option_snapshot(
        banco,
        empresa_id=empresa_id_int,
    )
    runtime_codes = [
        str(item or "").strip().lower()
        for item in list(template_snapshot.get("runtime_codes") or [])
        if str(item or "").strip()
    ]
    if bool(template_snapshot.get("governed_mode")):
        tipos_relatorio = {
            runtime_code: TIPOS_TEMPLATE_VALIDOS.get(runtime_code, runtime_code)
            for runtime_code in runtime_codes
        }
    else:
        tipos_relatorio = dict(TIPOS_TEMPLATE_VALIDOS)

    return {
        "tipos_relatorio": tipos_relatorio,
        "tipo_template_options": list(template_snapshot.get("options") or []),
        "catalog_governed_mode": bool(template_snapshot.get("governed_mode")),
        "catalog_state": str(template_snapshot.get("catalog_state") or "legacy_open"),
        "catalog_permissions": dict(template_snapshot.get("permissions") or {}),
    }


def contexto_base(request: Request) -> dict[str, Any]:
    if CHAVE_CSRF_INSPETOR not in request.session:
        request.session[CHAVE_CSRF_INSPETOR] = secrets.token_urlsafe(32)

    return {
        "request": request,
        "csrf_token": request.session[CHAVE_CSRF_INSPETOR],
        "csp_nonce": getattr(request.state, "csp_nonce", ""),
        "v_app": _versao_assets(request),
        **contexto_template_perf(),
    }


def validar_csrf(request: Request, token_form: str = "") -> bool:
    token_bearer = obter_token_bearer_request(request)
    if token_bearer:
        return token_esta_ativo(token_bearer)

    token_sessao = request.session.get(CHAVE_CSRF_INSPETOR) or request.session.get("csrf_token", "")
    if not token_sessao:
        return False

    token_candidato = request.headers.get("X-CSRF-Token", "") or token_form
    return bool(token_candidato and secrets.compare_digest(token_sessao, token_candidato))


def exigir_csrf(request: Request, token_form: str = "") -> None:
    if not validar_csrf(request, token_form):
        raise HTTPException(status_code=403, detail="Token CSRF inválido.")


def laudo_id_sessao(request: Request) -> Optional[int]:
    valor = request.session.get("laudo_ativo_id")
    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def laudo_id_query(request: Request) -> Optional[int]:
    valor = request.query_params.get("laudo")
    try:
        laudo_id = int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None

    return laudo_id if laudo_id and laudo_id > 0 else None


def _contextos_iniciais_laudo(request: Request) -> dict[str, dict[str, str]]:
    bruto = request.session.get(CHAVE_CONTEXTO_INICIAL_LAUDO)
    if not isinstance(bruto, dict):
        return {}

    payload: dict[str, dict[str, str]] = {}
    for chave, valor in bruto.items():
        if not isinstance(valor, dict):
            continue
        contexto = {
            str(campo): str(conteudo).strip()
            for campo, conteudo in valor.items()
            if str(campo).strip() and str(conteudo).strip()
        }
        if contexto:
            payload[str(chave)] = contexto
    return payload


def definir_contexto_inicial_laudo_sessao(
    request: Request,
    *,
    laudo_id: int | None,
    contexto: dict[str, str] | None,
) -> None:
    try:
        laudo_id_normalizado = int(laudo_id or 0)
    except (TypeError, ValueError):
        laudo_id_normalizado = 0
    if laudo_id_normalizado <= 0:
        return

    contextos = _contextos_iniciais_laudo(request)
    chave = str(laudo_id_normalizado)
    contexto_limpo = {
        str(campo): str(valor).strip()
        for campo, valor in (contexto or {}).items()
        if str(campo).strip() and str(valor).strip()
    }
    if contexto_limpo:
        contextos[chave] = contexto_limpo
    else:
        contextos.pop(chave, None)
    request.session[CHAVE_CONTEXTO_INICIAL_LAUDO] = contextos


def obter_contexto_inicial_laudo_sessao(
    request: Request | None,
    *,
    laudo_id: int | None,
) -> dict[str, str]:
    if request is None:
        return {}

    try:
        laudo_id_normalizado = int(laudo_id or 0)
    except (TypeError, ValueError):
        laudo_id_normalizado = 0
    if laudo_id_normalizado <= 0:
        return {}

    return dict(_contextos_iniciais_laudo(request).get(str(laudo_id_normalizado), {}))


def limpar_contexto_laudo_ativo(request: Request) -> None:
    request.session.pop("laudo_ativo_id", None)
    request.session["estado_relatorio"] = "sem_relatorio"


def aplicar_contexto_laudo_selecionado(
    request: Request,
    banco: Session,
    laudo: Laudo | None,
    usuario: Usuario | None,
) -> dict[str, Any]:
    if not laudo:
        limpar_contexto_laudo_ativo(request)
        return {
            "estado": "sem_relatorio",
            "laudo_id": None,
            "status_card": "oculto",
            "permite_edicao": False,
            "permite_reabrir": False,
        }

    request.session["laudo_ativo_id"] = int(laudo.id)
    if usuario is None:
        raise HTTPException(status_code=500, detail="Usuário inválido para contexto do laudo.")
    payload = estado_relatorio_sanitizado(request, banco, usuario, mutar_sessao=True)
    return payload


def resolver_contexto_principal_inspetor(
    request: Request,
    banco: Session,
    usuario: Usuario,
    *,
    resumo_cache: CacheResumoLaudoRequest | None = None,
) -> dict[str, Any]:
    cache = resumo_cache or criar_cache_resumo_laudos()
    laudo_id_candidato = laudo_id_query(request)
    laudo_query_presente = request.query_params.get("laudo") is not None
    home_explicito = request.query_params.get("home") == "1"
    fonte_laudo_ativo = "session"

    if laudo_id_candidato:
        laudo = (
            banco.query(Laudo)
            .filter(
                Laudo.id == laudo_id_candidato,
                Laudo.empresa_id == usuario.empresa_id,
                Laudo.usuario_id == usuario.id,
            )
            .first()
        )
        if laudo is not None:
            estado_relatorio = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)
            fonte_laudo_ativo = "query_param"
        else:
            estado_relatorio = estado_relatorio_sanitizado(
                request,
                banco,
                usuario,
                resumo_cache=cache,
            )
    elif not laudo_query_presente and not home_explicito:
        limpar_contexto_laudo_ativo(request)
        estado_relatorio = estado_relatorio_sanitizado(
            request,
            banco,
            usuario,
            resumo_cache=cache,
        )
        fonte_laudo_ativo = "root_home"
    else:
        estado_relatorio = estado_relatorio_sanitizado(
            request,
            banco,
            usuario,
            resumo_cache=cache,
        )

    home_forcado_inicial = (home_explicito and fonte_laudo_ativo != "query_param") or (
        not laudo_query_presente and not home_explicito
    )

    return {
        "estado_relatorio": estado_relatorio,
        "home_forcado_inicial": home_forcado_inicial,
        "fonte_laudo_ativo": fonte_laudo_ativo,
    }


def estado_relatorio_sanitizado(
    request: Request,
    banco: Session,
    usuario: Usuario,
    *,
    mutar_sessao: bool = True,
    resumo_cache: CacheResumoLaudoRequest | None = None,
) -> dict[str, Any]:
    cache = resumo_cache or criar_cache_resumo_laudos()
    estado = request.session.get("estado_relatorio", "sem_relatorio")
    laudo_id = laudo_id_sessao(request)
    template_catalog_payload = build_inspector_template_catalog_payload(
        banco,
        empresa_id=getattr(usuario, "empresa_id", None),
    )

    if not laudo_id:
        if mutar_sessao:
            limpar_contexto_laudo_ativo(request)
        return {
            "estado": "sem_relatorio",
            "laudo_id": None,
            "status_card": "oculto",
            "permite_edicao": False,
            "permite_reabrir": False,
            "entry_mode_preference": None,
            "entry_mode_effective": None,
            "entry_mode_reason": None,
            **template_catalog_payload,
            **serializar_contexto_case_lifecycle_legado(
                laudo=None,
                tenant_id=getattr(usuario, "empresa_id", ""),
                legacy_payload={
                    "estado": "sem_relatorio",
                    "laudo_id": None,
                    "status_card": "oculto",
                    "permite_reabrir": False,
                },
            ),
        }

    laudo = (
        banco.query(Laudo)
        .filter(
            Laudo.id == laudo_id,
            Laudo.empresa_id == usuario.empresa_id,
            Laudo.usuario_id == usuario.id,
        )
        .first()
    )

    if not laudo:
        if mutar_sessao:
            limpar_contexto_laudo_ativo(request)
        return {
            "estado": "sem_relatorio",
            "laudo_id": None,
            "status_card": "oculto",
            "permite_edicao": False,
            "permite_reabrir": False,
            "entry_mode_preference": None,
            "entry_mode_effective": None,
            "entry_mode_reason": None,
            **template_catalog_payload,
            **serializar_contexto_case_lifecycle_legado(
                laudo=None,
                tenant_id=getattr(usuario, "empresa_id", ""),
                legacy_payload={
                    "estado": "sem_relatorio",
                    "laudo_id": None,
                    "status_card": "oculto",
                    "permite_reabrir": False,
                },
            ),
        }

    estado = obter_estado_api_laudo(banco, laudo, cache=cache)
    status_card = obter_status_card_laudo(banco, laudo, cache=cache)

    if mutar_sessao:
        request.session["estado_relatorio"] = estado

    payload = {
        "estado": estado,
        "laudo_id": laudo.id if status_card != "oculto" else None,
        "status_card": status_card,
        "permite_edicao": laudo_permite_edicao_inspetor(laudo),
        "permite_reabrir": laudo_permite_reabrir(banco, laudo, cache=cache),
        "tem_interacao": laudo_tem_interacao(banco, laudo.id, cache=cache),
        **obter_contexto_modo_entrada_laudo(laudo),
        **template_catalog_payload,
    }
    payload.update(
        serializar_contexto_case_lifecycle_legado(
            laudo=laudo,
            legacy_payload=payload,
        )
    )
    return payload


__all__ = [
    "CHAVE_CSRF_INSPETOR",
    "CHAVE_CONTEXTO_INICIAL_LAUDO",
    "VERSAO_APP",
    "contexto_base",
    "definir_contexto_inicial_laudo_sessao",
    "build_inspector_template_catalog_payload",
    "validar_csrf",
    "exigir_csrf",
    "laudo_id_query",
    "laudo_id_sessao",
    "limpar_contexto_laudo_ativo",
    "obter_contexto_inicial_laudo_sessao",
    "aplicar_contexto_laudo_selecionado",
    "resolver_contexto_principal_inspetor",
    "estado_relatorio_sanitizado",
    "laudo_tem_interacao",
]
