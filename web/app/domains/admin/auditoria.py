"""Helpers de auditoria do portal admin-geral."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.domains.cliente.auditoria import serializar_registro_auditoria
from app.domains.cliente.auditoria import registrar_auditoria_empresa
from app.shared.database import RegistroAuditoriaEmpresa

logger = logging.getLogger("tariel.admin.auditoria")


def registrar_auditoria_admin_empresa_segura(
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
    try:
        registrar_auditoria_empresa(
            banco,
            empresa_id=int(empresa_id),
            ator_usuario_id=int(ator_usuario_id) if ator_usuario_id is not None else None,
            alvo_usuario_id=int(alvo_usuario_id) if alvo_usuario_id is not None else None,
            portal="admin",
            acao=acao,
            resumo=resumo,
            detalhe=detalhe,
            payload=payload,
        )
    except Exception:
        logger.warning(
            "Falha ao registrar auditoria do admin-geral | empresa_id=%s | ator_usuario_id=%s | acao=%s",
            empresa_id,
            ator_usuario_id,
            acao,
            exc_info=True,
        )


def listar_auditoria_admin_empresa(
    banco: Session,
    *,
    empresa_id: int | None = None,
    limite: int = 20,
) -> list[RegistroAuditoriaEmpresa]:
    limite_normalizado = max(1, min(int(limite or 20), 100))
    consulta = (
        select(RegistroAuditoriaEmpresa)
        .options(
            selectinload(RegistroAuditoriaEmpresa.empresa),
            selectinload(RegistroAuditoriaEmpresa.ator_usuario),
            selectinload(RegistroAuditoriaEmpresa.alvo_usuario),
        )
        .where(RegistroAuditoriaEmpresa.portal == "admin")
        .order_by(RegistroAuditoriaEmpresa.criado_em.desc(), RegistroAuditoriaEmpresa.id.desc())
        .limit(limite_normalizado)
    )
    if empresa_id is not None:
        consulta = consulta.where(RegistroAuditoriaEmpresa.empresa_id == int(empresa_id))
    return list(banco.scalars(consulta).all())


def serializar_registro_auditoria_admin(registro: RegistroAuditoriaEmpresa) -> dict[str, Any]:
    payload = serializar_registro_auditoria(registro)
    empresa = getattr(registro, "empresa", None)
    payload["empresa_id"] = int(registro.empresa_id)
    payload["empresa_nome"] = getattr(empresa, "nome_fantasia", None) or f"Empresa #{registro.empresa_id}"
    return payload


__all__ = [
    "listar_auditoria_admin_empresa",
    "registrar_auditoria_admin_empresa_segura",
    "serializar_registro_auditoria_admin",
]
