# ==========================================
# TARIEL CONTROL TOWER — SECURITY_PORTAL_STATE.PY
# Responsabilidade: Helpers de portal, RBAC e chaves de sessão HTTP
# ==========================================

from __future__ import annotations

from typing import Any

from fastapi import Request

import app.shared.database as banco_dados
from app.shared.tenant_admin_policy import (
    tenant_admin_effective_user_portal_grants,
    tenant_admin_user_occupies_operational_slot,
    tenant_admin_user_portal_label,
)

CHAVE_SESSION_TOKEN = "session_token"
CHAVE_USUARIO_ID = "usuario_id"
CHAVE_EMPRESA_ID = "empresa_id"
CHAVE_NIVEL_ACESSO = "nivel_acesso"
CHAVE_NOME = "nome"

PORTAL_INSPETOR = "inspetor"
PORTAL_REVISOR = "revisor"
PORTAL_CLIENTE = "cliente"
PORTAL_ADMIN = "admin"

_CHAVES_SESSAO_POR_PORTAL: dict[str, dict[str, str]] = {
    PORTAL_INSPETOR: {
        "token": "session_token_inspetor",
        "usuario_id": "usuario_id_inspetor",
        "empresa_id": "empresa_id_inspetor",
        "nivel_acesso": "nivel_acesso_inspetor",
        "nome": "nome_inspetor",
    },
    PORTAL_REVISOR: {
        "token": "session_token_revisor",
        "usuario_id": "usuario_id_revisor",
        "empresa_id": "empresa_id_revisor",
        "nivel_acesso": "nivel_acesso_revisor",
        "nome": "nome_revisor",
    },
    PORTAL_ADMIN: {
        "token": "session_token_admin",
        "usuario_id": "usuario_id_admin",
        "empresa_id": "empresa_id_admin",
        "nivel_acesso": "nivel_acesso_admin",
        "nome": "nome_admin",
    },
    PORTAL_CLIENTE: {
        "token": "session_token_cliente",
        "usuario_id": "usuario_id_cliente",
        "empresa_id": "empresa_id_cliente",
        "nivel_acesso": "nivel_acesso_cliente",
        "nome": "nome_cliente",
    },
}

_NIVEIS_PERMITIDOS_APP = frozenset({banco_dados.NivelAcesso.INSPETOR.value})
_NIVEIS_PERMITIDOS_REVISAO = frozenset({banco_dados.NivelAcesso.REVISOR.value})
_NIVEIS_PERMITIDOS_CLIENTE = frozenset({banco_dados.NivelAcesso.ADMIN_CLIENTE.value})
_NIVEIS_PERMITIDOS_ADMIN = frozenset({banco_dados.NivelAcesso.DIRETORIA.value})

_NIVEIS_PERMITIDOS_POR_PORTAL: dict[str, frozenset[int]] = {
    PORTAL_INSPETOR: _NIVEIS_PERMITIDOS_APP,
    PORTAL_REVISOR: _NIVEIS_PERMITIDOS_REVISAO,
    PORTAL_CLIENTE: _NIVEIS_PERMITIDOS_CLIENTE,
    PORTAL_ADMIN: _NIVEIS_PERMITIDOS_ADMIN,
}

_NIVEL_SESSAO_POR_PORTAL: dict[str, int] = {
    PORTAL_INSPETOR: int(banco_dados.NivelAcesso.INSPETOR.value),
    PORTAL_REVISOR: int(banco_dados.NivelAcesso.REVISOR.value),
    PORTAL_CLIENTE: int(banco_dados.NivelAcesso.ADMIN_CLIENTE.value),
    PORTAL_ADMIN: int(banco_dados.NivelAcesso.DIRETORIA.value),
}

_DESTINO_HTTP_POR_PORTAL: dict[str, str] = {
    PORTAL_INSPETOR: "/app/",
    PORTAL_REVISOR: "/revisao/painel",
    PORTAL_CLIENTE: "/cliente/painel",
    PORTAL_ADMIN: "/admin/painel",
}


def empresa_tem_escopo_plataforma(empresa: banco_dados.Empresa | None) -> bool:
    return bool(getattr(empresa, "escopo_plataforma", False))


def usuario_admin_portal_autorizado(usuario: banco_dados.Usuario | None) -> bool:
    if usuario is None:
        return False

    try:
        nivel_int = int(getattr(usuario, "nivel_acesso", 0) or 0)
    except (TypeError, ValueError):
        nivel_int = 0

    if nivel_int != int(banco_dados.NivelAcesso.DIRETORIA.value):
        return False

    allowed_portals = getattr(usuario, "allowed_portals", ())
    if allowed_portals:
        portal_permitido = PORTAL_ADMIN in {str(item or "").strip().lower() for item in allowed_portals}
    else:
        portal_permitido = True

    flag = getattr(usuario, "portal_admin_autorizado", None)
    if flag is None:
        return bool(portal_permitido)

    return bool(flag) and bool(portal_permitido)


def usuario_tem_escopo_plataforma(usuario: banco_dados.Usuario | None) -> bool:
    if usuario is None:
        return False

    empresa = getattr(usuario, "empresa", None)
    if empresa_tem_escopo_plataforma(empresa):
        return True

    if str(getattr(usuario, "account_scope", "tenant") or "tenant").strip().lower() == "platform":
        return True

    return usuario_admin_portal_autorizado(usuario) and empresa is None


def normalizar_portal_sessao(portal: str | None) -> str | None:
    valor = str(portal or "").strip().lower()
    if valor in _CHAVES_SESSAO_POR_PORTAL:
        return valor
    return None


def portal_por_caminho(caminho: str | None) -> str | None:
    rota = str(caminho or "").strip().lower()
    if rota.startswith("/app"):
        return PORTAL_INSPETOR
    if rota.startswith("/revisao"):
        return PORTAL_REVISOR
    if rota.startswith("/cliente"):
        return PORTAL_CLIENTE
    if rota.startswith("/admin"):
        return PORTAL_ADMIN
    return None


def destino_http_portal(portal: str | None) -> str | None:
    portal_normalizado = normalizar_portal_sessao(portal)
    if not portal_normalizado:
        return None
    return _DESTINO_HTTP_POR_PORTAL.get(portal_normalizado)


def obter_token_bearer_request(request: Request | None) -> str | None:
    if request is None:
        return None

    cabecalho = str(request.headers.get("authorization", "") or "").strip()
    if not cabecalho:
        return None

    esquema, _, token = cabecalho.partition(" ")
    if esquema.strip().lower() != "bearer":
        return None

    token_normalizado = token.strip()
    return token_normalizado or None


def _chaves_sessao_do_portal(portal: str | None) -> dict[str, str] | None:
    portal_normalizado = normalizar_portal_sessao(portal)
    if not portal_normalizado:
        return None
    return _CHAVES_SESSAO_POR_PORTAL.get(portal_normalizado)


def _nivel_compativel_com_portal(portal: str | None, nivel_acesso: Any) -> bool:
    try:
        nivel_int = int(nivel_acesso)
    except (TypeError, ValueError):
        return False

    nivel_esperado = nivel_acesso_sessao_portal(portal)
    if nivel_esperado is not None:
        return nivel_int == nivel_esperado

    return True


def niveis_permitidos_portal(portal: str | None) -> frozenset[int]:
    portal_normalizado = normalizar_portal_sessao(portal)
    if not portal_normalizado:
        return frozenset()
    return _NIVEIS_PERMITIDOS_POR_PORTAL.get(portal_normalizado, frozenset())


def usuario_tem_niveis_permitidos(
    usuario: banco_dados.Usuario | None,
    niveis_permitidos: set[int] | frozenset[int],
) -> bool:
    if usuario is None:
        return False
    try:
        nivel_int = int(usuario.nivel_acesso)
    except (TypeError, ValueError):
        return False
    return nivel_int in {int(nivel) for nivel in niveis_permitidos}


def usuario_tem_nivel(usuario: banco_dados.Usuario | None, nivel: int) -> bool:
    return usuario_tem_niveis_permitidos(usuario, {int(nivel)})


def nivel_acesso_sessao_portal(portal: str | None) -> int | None:
    portal_normalizado = normalizar_portal_sessao(portal)
    if not portal_normalizado:
        return None
    return _NIVEL_SESSAO_POR_PORTAL.get(portal_normalizado)


def usuario_portais_habilitados(usuario: banco_dados.Usuario | None) -> tuple[str, ...]:
    if usuario is None:
        return tuple()

    policy = getattr(getattr(usuario, "empresa", None), "admin_cliente_policy_json", None)
    try:
        effective_portals = tenant_admin_effective_user_portal_grants(
            policy,
            access_level=getattr(usuario, "nivel_acesso", None),
            stored_portals=getattr(usuario, "allowed_portals", ()),
        )
    except Exception:
        effective_portals = []

    normalized = tuple(
        portal
        for portal in dict.fromkeys(
            str(item or "").strip().lower() for item in list(effective_portals or [])
        )
        if portal in {PORTAL_CLIENTE, PORTAL_INSPETOR, PORTAL_REVISOR}
    )
    return normalized


def usuario_ocupa_slot_operacional(usuario: banco_dados.Usuario | None) -> bool:
    if usuario is None:
        return False
    policy = getattr(getattr(usuario, "empresa", None), "admin_cliente_policy_json", None)
    try:
        return tenant_admin_user_occupies_operational_slot(
            policy,
            access_level=getattr(usuario, "nivel_acesso", None),
            stored_portals=getattr(usuario, "allowed_portals", ()),
        )
    except Exception:
        return False


def usuario_tem_acesso_portal(usuario: banco_dados.Usuario | None, portal: str | None) -> bool:
    portal_normalizado = normalizar_portal_sessao(portal)
    if portal_normalizado is None or usuario is None:
        return False

    if portal_normalizado == PORTAL_ADMIN:
        return usuario_admin_portal_autorizado(usuario)

    return portal_normalizado in set(usuario_portais_habilitados(usuario))


def usuario_portal_switch_links(
    usuario: banco_dados.Usuario | None,
    *,
    portal_atual: str | None = None,
) -> list[dict[str, str]]:
    if usuario is None:
        return []

    atual = normalizar_portal_sessao(portal_atual)
    links: list[dict[str, str]] = []
    for portal in usuario_portais_habilitados(usuario):
        if portal == atual:
            continue
        destino = destino_http_portal(portal)
        if not destino:
            continue
        links.append(
            {
                "portal": portal,
                "label": tenant_admin_user_portal_label(portal),
                "url": destino,
            }
        )
    return links


def obter_dados_sessao_portal(
    sessao: Any,
    *,
    portal: str | None = None,
    caminho: str | None = None,
) -> dict[str, Any]:
    portal_alvo = normalizar_portal_sessao(portal) or portal_por_caminho(caminho)
    chaves = _chaves_sessao_do_portal(portal_alvo)

    token = sessao.get(CHAVE_SESSION_TOKEN)
    usuario_id = sessao.get(CHAVE_USUARIO_ID)
    empresa_id = sessao.get(CHAVE_EMPRESA_ID)
    nivel_acesso = sessao.get(CHAVE_NIVEL_ACESSO)
    nome = sessao.get(CHAVE_NOME)

    if chaves:
        token_portal = sessao.get(chaves["token"])
        usuario_id_portal = sessao.get(chaves["usuario_id"])
        empresa_id_portal = sessao.get(chaves["empresa_id"])
        nivel_portal = sessao.get(chaves["nivel_acesso"])
        nome_portal = sessao.get(chaves["nome"])

        if token_portal:
            token = token_portal
            usuario_id = usuario_id_portal or usuario_id
            empresa_id = empresa_id_portal or empresa_id
            nivel_acesso = nivel_portal or nivel_acesso
            nome = nome_portal or nome
        elif not _nivel_compativel_com_portal(portal_alvo, nivel_acesso):
            token = None
            usuario_id = None
            empresa_id = None
            nivel_acesso = None
            nome = None

    return {
        "portal": portal_alvo,
        "token": token,
        "usuario_id": usuario_id,
        "empresa_id": empresa_id,
        "nivel_acesso": nivel_acesso,
        "nome": nome,
    }


def definir_sessao_portal(
    sessao: Any,
    *,
    portal: str,
    token: str,
    usuario_id: int,
    empresa_id: int | None,
    nivel_acesso: int,
    nome: str,
) -> None:
    portal_normalizado = normalizar_portal_sessao(portal)
    chaves = _chaves_sessao_do_portal(portal_normalizado)
    if not chaves:
        raise ValueError("Portal invalido para definicao de sessao.")

    sessao[chaves["token"]] = token
    sessao[chaves["usuario_id"]] = int(usuario_id)
    sessao[chaves["empresa_id"]] = int(empresa_id) if empresa_id is not None else None
    sessao[chaves["nivel_acesso"]] = int(nivel_acesso)
    sessao[chaves["nome"]] = str(nome or "").strip()

    sessao[CHAVE_SESSION_TOKEN] = token
    sessao[CHAVE_USUARIO_ID] = int(usuario_id)
    sessao[CHAVE_EMPRESA_ID] = int(empresa_id) if empresa_id is not None else None
    sessao[CHAVE_NIVEL_ACESSO] = int(nivel_acesso)
    sessao[CHAVE_NOME] = str(nome or "").strip()


def limpar_sessao_portal(sessao: Any, *, portal: str) -> None:
    chaves = _chaves_sessao_do_portal(portal)
    if not chaves:
        return

    token_portal = sessao.get(chaves["token"])
    token_global = sessao.get(CHAVE_SESSION_TOKEN)

    for chave in chaves.values():
        sessao.pop(chave, None)

    deve_limpar_global = bool(token_portal and token_global == token_portal)
    if not deve_limpar_global and not token_portal and token_global:
        try:
            nivel_global = int(sessao.get(CHAVE_NIVEL_ACESSO))
        except (TypeError, ValueError):
            nivel_global = None

        if nivel_global is not None and _nivel_compativel_com_portal(portal, nivel_global):
            deve_limpar_global = True

    if deve_limpar_global:
        for chave in (CHAVE_SESSION_TOKEN, CHAVE_USUARIO_ID, CHAVE_EMPRESA_ID, CHAVE_NIVEL_ACESSO, CHAVE_NOME):
            sessao.pop(chave, None)


def _limpar_chaves_sessao_request(request: Request, *, portal: str | None = None) -> None:
    portal_normalizado = normalizar_portal_sessao(portal) or portal_por_caminho(request.url.path)
    if portal_normalizado:
        limpar_sessao_portal(request.session, portal=portal_normalizado)
        return

    for chave in (CHAVE_SESSION_TOKEN, CHAVE_USUARIO_ID, CHAVE_EMPRESA_ID, CHAVE_NIVEL_ACESSO, CHAVE_NOME):
        request.session.pop(chave, None)


def usuario_tem_bloqueio_ativo(usuario: banco_dados.Usuario) -> bool:
    if not getattr(usuario, "ativo", True):
        return True

    bloqueio_temporario_ativo = False
    if hasattr(usuario, "esta_bloqueado") and callable(usuario.esta_bloqueado):
        try:
            bloqueio_temporario_ativo = bool(usuario.esta_bloqueado())
        except Exception:
            pass

    status_bloqueio = bool(getattr(usuario, "status_bloqueio", False))
    bloqueado_ate = getattr(usuario, "bloqueado_ate", None)

    if status_bloqueio:
        if bloqueado_ate is None:
            return True
        if bloqueio_temporario_ativo:
            return True
    elif bloqueio_temporario_ativo:
        return True

    empresa = getattr(usuario, "empresa", None)

    # Operadores da plataforma vivem em tenant técnico dedicado e não herdam
    # bloqueio operacional do tenant cliente.
    herda_bloqueio_empresa = not usuario_tem_escopo_plataforma(usuario)
    if herda_bloqueio_empresa and empresa and getattr(empresa, "status_bloqueio", False):
        return True

    return False


__all__ = [
    "CHAVE_EMPRESA_ID",
    "CHAVE_NIVEL_ACESSO",
    "CHAVE_NOME",
    "CHAVE_SESSION_TOKEN",
    "CHAVE_USUARIO_ID",
    "PORTAL_ADMIN",
    "PORTAL_CLIENTE",
    "PORTAL_INSPETOR",
    "PORTAL_REVISOR",
    "_limpar_chaves_sessao_request",
    "definir_sessao_portal",
    "empresa_tem_escopo_plataforma",
    "limpar_sessao_portal",
    "niveis_permitidos_portal",
    "normalizar_portal_sessao",
    "obter_dados_sessao_portal",
    "obter_token_bearer_request",
    "destino_http_portal",
    "portal_por_caminho",
    "usuario_portal_switch_links",
    "usuario_admin_portal_autorizado",
    "usuario_tem_acesso_portal",
    "usuario_tem_bloqueio_ativo",
    "usuario_tem_nivel",
    "usuario_tem_niveis_permitidos",
    "usuario_tem_escopo_plataforma",
]
