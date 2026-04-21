from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.admin.tenant_plan_services import construir_preview_troca_plano
from app.domains.admin.tenant_user_services import (
    _buscar_empresa,
    _contar_slots_operacionais_empresa,
    _contar_usuarios_empresa,
    filtro_usuarios_gerenciaveis_cliente,
)
from app.shared.database import (
    NivelAcesso,
    Usuario,
    commit_ou_rollback_integridade,
    flush_ou_rollback_integridade,
)
from app.shared.security import encerrar_todas_sessoes_usuario
from app.shared.tenant_admin_policy import (
    sanitize_tenant_admin_policy,
    summarize_tenant_admin_policy,
    tenant_admin_default_admin_cliente_portal_grants,
)


logger = logging.getLogger("tariel.saas")


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalizar_politica_admin_cliente_empresa(
    *,
    case_visibility_mode: str = "",
    case_action_mode: str = "",
    operating_model: str = "",
    mobile_web_inspector_enabled: str | bool = "",
    mobile_web_review_enabled: str | bool = "",
    operational_user_cross_portal_enabled: str | bool = "",
    operational_user_admin_portal_enabled: str | bool = "",
) -> dict[str, Any]:
    return sanitize_tenant_admin_policy(
        {
            "case_visibility_mode": case_visibility_mode,
            "case_action_mode": case_action_mode,
            "operating_model": operating_model,
            "shared_mobile_operator_web_inspector_enabled": mobile_web_inspector_enabled,
            "shared_mobile_operator_web_review_enabled": mobile_web_review_enabled,
            "operational_user_cross_portal_enabled": operational_user_cross_portal_enabled,
            "operational_user_admin_portal_enabled": operational_user_admin_portal_enabled,
        }
    )


def _listar_ids_usuarios_operacionais_empresa(db: Session, empresa_id: int) -> list[int]:
    return [
        int(usuario_id)
        for usuario_id in db.scalars(
            select(Usuario.id).where(
                Usuario.empresa_id == int(empresa_id),
                filtro_usuarios_gerenciaveis_cliente(),
            )
        ).all()
    ]


def alternar_bloqueio(
    db: Session,
    empresa_id: int,
    *,
    motivo: str = "",
    confirmar_desbloqueio: bool = False,
) -> dict[str, Any]:
    empresa = _buscar_empresa(db, empresa_id)
    bloqueada = bool(getattr(empresa, "status_bloqueio", False))
    motivo_norm = str(motivo or "").strip()
    if motivo_norm:
        motivo_norm = motivo_norm[:300]

    if bloqueada:
        if not confirmar_desbloqueio:
            raise ValueError("Confirme o desbloqueio da empresa.")
        empresa.status_bloqueio = False
        empresa.bloqueado_em = None
        commit_ou_rollback_integridade(
            db,
            logger_operacao=logger,
            mensagem_erro="Não foi possível desbloquear a empresa.",
        )
        return {
            "blocked": False,
            "reason": str(getattr(empresa, "motivo_bloqueio", "") or ""),
            "sessions_invalidated": 0,
        }

    if not motivo_norm:
        raise ValueError("Informe o motivo do bloqueio.")

    empresa.status_bloqueio = True
    empresa.bloqueado_em = _agora_utc()
    empresa.motivo_bloqueio = motivo_norm
    commit_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível alterar o bloqueio da empresa.",
    )

    usuarios_ids = _listar_ids_usuarios_operacionais_empresa(db, empresa_id)
    sessoes_encerradas = sum(encerrar_todas_sessoes_usuario(usuario_id) for usuario_id in usuarios_ids)
    return {
        "blocked": True,
        "reason": motivo_norm,
        "sessions_invalidated": int(sessoes_encerradas),
    }


def atualizar_politica_admin_cliente_empresa(
    db: Session,
    *,
    empresa_id: int,
    case_visibility_mode: str = "",
    case_action_mode: str = "",
    operating_model: str = "",
    mobile_web_inspector_enabled: str | bool = "",
    mobile_web_review_enabled: str | bool = "",
    operational_user_cross_portal_enabled: str | bool = "",
    operational_user_admin_portal_enabled: str | bool = "",
) -> dict[str, Any]:
    empresa = _buscar_empresa(db, empresa_id)
    politica = _normalizar_politica_admin_cliente_empresa(
        case_visibility_mode=case_visibility_mode,
        case_action_mode=case_action_mode,
        operating_model=operating_model,
        mobile_web_inspector_enabled=mobile_web_inspector_enabled,
        mobile_web_review_enabled=mobile_web_review_enabled,
        operational_user_cross_portal_enabled=operational_user_cross_portal_enabled,
        operational_user_admin_portal_enabled=operational_user_admin_portal_enabled,
    )
    empresa.admin_cliente_policy_json = politica
    if str(politica.get("operating_model") or "").strip().lower() == "mobile_single_operator":
        admins_cliente = list(
            db.scalars(
                select(Usuario)
                .where(
                    Usuario.empresa_id == int(empresa.id),
                    Usuario.nivel_acesso == int(NivelAcesso.ADMIN_CLIENTE),
                )
                .order_by(Usuario.id.asc())
            ).all()
        )
        if len(admins_cliente) == 1 and _contar_slots_operacionais_empresa(db, empresa=empresa) == 0:
            admin_principal = admins_cliente[0]
            admin_principal.allowed_portals_json = tenant_admin_default_admin_cliente_portal_grants(
                politica
            )
    commit_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível atualizar a política operacional do admin-cliente.",
    )
    return summarize_tenant_admin_policy(empresa.admin_cliente_policy_json)


def alterar_plano(db: Session, empresa_id: int, novo_plano: str) -> dict[str, Any]:
    empresa = _buscar_empresa(db, empresa_id)
    total_usuarios = _contar_usuarios_empresa(db, empresa_id)
    uso_atual = int(getattr(empresa, "mensagens_processadas", 0) or 0)
    preview = construir_preview_troca_plano(
        db,
        empresa=empresa,
        novo_plano=novo_plano,
        usuarios_total=total_usuarios,
        uso_atual=uso_atual,
    )

    empresa.plano_ativo = preview["plano_novo"]
    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível alterar o plano da empresa.",
    )
    return preview
