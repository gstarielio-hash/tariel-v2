"""Helpers de auditoria do portal admin-cliente."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.shared.database import RegistroAuditoriaEmpresa, agora_utc

logger = logging.getLogger("tariel.cliente.auditoria")

_AUDITORIA_CATEGORIA_LABELS = {
    "access": "Acesso",
    "commercial": "Comercial",
    "team": "Equipe",
    "support": "Suporte",
    "chat": "Chat",
    "mesa": "Mesa",
    "general": "Geral",
}
_AUDITORIA_SCOPE_LABELS = {
    "admin": "Painel",
    "chat": "Chat",
    "mesa": "Mesa",
    "timeline": "Timeline completa",
}


def classificar_auditoria_empresa(acao: str) -> dict[str, str]:
    normalized = str(acao or "").strip().lower()
    if normalized.startswith("chat_"):
        categoria = "chat"
        scope = "chat"
    elif normalized.startswith("mesa_"):
        categoria = "mesa"
        scope = "mesa"
    elif normalized.startswith("plano_"):
        categoria = "commercial"
        scope = "admin"
    elif normalized.startswith("usuario_"):
        categoria = "team"
        scope = "admin"
    elif normalized.startswith("senha_"):
        categoria = "access"
        scope = "admin"
    elif normalized.startswith("suporte_"):
        categoria = "support"
        scope = "admin"
    else:
        categoria = "general"
        scope = "admin"
    return {
        "categoria": categoria,
        "categoria_label": _AUDITORIA_CATEGORIA_LABELS.get(categoria, "Geral"),
        "scope": scope,
        "scope_label": _AUDITORIA_SCOPE_LABELS.get(scope, "Painel"),
    }


def resumir_auditoria_serializada(itens: list[dict[str, Any]]) -> dict[str, Any]:
    categories = {key: 0 for key in _AUDITORIA_CATEGORIA_LABELS}
    scopes = {key: 0 for key in _AUDITORIA_SCOPE_LABELS if key != "timeline"}
    for item in itens:
        categoria = str(item.get("categoria") or "general")
        scope = str(item.get("scope") or "admin")
        categories[categoria] = int(categories.get(categoria, 0)) + 1
        scopes[scope] = int(scopes.get(scope, 0)) + 1
    return {
        "total": len(itens),
        "categories": categories,
        "scopes": scopes,
    }


def registrar_auditoria_empresa(
    banco: Session,
    *,
    empresa_id: int,
    ator_usuario_id: int | None,
    acao: str,
    resumo: str,
    detalhe: str = "",
    alvo_usuario_id: int | None = None,
    portal: str = "cliente",
    payload: dict[str, Any] | None = None,
) -> RegistroAuditoriaEmpresa:
    timestamp = agora_utc()
    registro = RegistroAuditoriaEmpresa(
        empresa_id=int(empresa_id),
        ator_usuario_id=int(ator_usuario_id) if ator_usuario_id else None,
        alvo_usuario_id=int(alvo_usuario_id) if alvo_usuario_id else None,
        portal=str(portal or "cliente")[:30],
        acao=str(acao or "acao").strip()[:80],
        resumo=str(resumo or "Ação registrada").strip()[:220],
        detalhe=(str(detalhe or "").strip() or None),
        payload_json=payload or None,
        criado_em=timestamp,
        atualizado_em=timestamp,
    )
    banco.add(registro)
    banco.flush()
    banco.refresh(registro)
    return registro


def listar_auditoria_empresa(
    banco: Session,
    *,
    empresa_id: int,
    portal: str = "cliente",
    limite: int = 12,
    scope: str | None = None,
) -> list[RegistroAuditoriaEmpresa]:
    limite_normalizado = max(1, min(int(limite or 12), 50))
    filtro_scope = str(scope or "").strip().lower()
    limite_consulta = max(limite_normalizado, min(limite_normalizado * 8, 200))
    consulta = (
        select(RegistroAuditoriaEmpresa)
        .options(
            selectinload(RegistroAuditoriaEmpresa.ator_usuario),
            selectinload(RegistroAuditoriaEmpresa.alvo_usuario),
        )
        .where(
            RegistroAuditoriaEmpresa.empresa_id == int(empresa_id),
            RegistroAuditoriaEmpresa.portal == str(portal or "cliente"),
        )
        .order_by(RegistroAuditoriaEmpresa.criado_em.desc(), RegistroAuditoriaEmpresa.id.desc())
        .limit(limite_consulta)
    )
    registros = list(banco.scalars(consulta).all())
    if filtro_scope in {"admin", "chat", "mesa", "support"}:
        registros = [
            item
            for item in registros
            if (
                classificar_auditoria_empresa(getattr(item, "acao", "")).get("scope") == filtro_scope
                if filtro_scope in {"admin", "chat", "mesa"}
                else classificar_auditoria_empresa(getattr(item, "acao", "")).get("categoria") == "support"
            )
        ]
    return registros[:limite_normalizado]


def serializar_registro_auditoria(registro: RegistroAuditoriaEmpresa) -> dict[str, Any]:
    criado_em = getattr(registro, "criado_em", None)
    ator = getattr(registro, "ator_usuario", None)
    alvo = getattr(registro, "alvo_usuario", None)
    classificacao = classificar_auditoria_empresa(getattr(registro, "acao", ""))

    return {
        "id": int(registro.id),
        "acao": str(registro.acao or ""),
        "portal": str(registro.portal or "cliente"),
        "categoria": classificacao["categoria"],
        "categoria_label": classificacao["categoria_label"],
        "scope": classificacao["scope"],
        "scope_label": classificacao["scope_label"],
        "resumo": str(registro.resumo or ""),
        "detalhe": str(registro.detalhe or ""),
        "payload": registro.payload_json or {},
        "criado_em": criado_em.isoformat() if criado_em else "",
        "criado_em_label": (criado_em.astimezone().strftime("%d/%m/%Y %H:%M") if criado_em else "Agora"),
        "ator_usuario_id": int(registro.ator_usuario_id) if registro.ator_usuario_id else None,
        "ator_nome": getattr(ator, "nome", None) or getattr(ator, "nome_completo", None) or "Sistema",
        "alvo_usuario_id": int(registro.alvo_usuario_id) if registro.alvo_usuario_id else None,
        "alvo_nome": getattr(alvo, "nome", None) or getattr(alvo, "nome_completo", None) or "",
    }
