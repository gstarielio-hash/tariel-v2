from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.admin.admin_platform_identity_services import (
    _resolver_empresa_plataforma,
    _tenant_cliente_clause,
)
from app.domains.admin.tenant_user_services import _normalizar_texto_curto
from app.shared.database import (
    AprendizadoVisualIa,
    AtivacaoCatalogoEmpresaLaudo,
    DispositivoPushMobile,
    Empresa,
    Laudo,
    RegistroAuditoriaEmpresa,
    SignatarioGovernadoLaudo,
    TemplateLaudo,
    TenantFamilyReleaseLaudo,
    Usuario,
    commit_ou_rollback_integridade,
)
from app.shared.security import encerrar_todas_sessoes_usuario


logger = logging.getLogger("tariel.saas")

UI_AUDIT_TENANT_PREFIX = "Tariel UI Audit "


def _remover_dependencias_empresa(db: Session, empresa_id: int) -> None:
    db.query(AtivacaoCatalogoEmpresaLaudo).filter(
        AtivacaoCatalogoEmpresaLaudo.empresa_id == empresa_id
    ).delete(synchronize_session=False)
    db.query(TenantFamilyReleaseLaudo).filter(
        TenantFamilyReleaseLaudo.tenant_id == empresa_id
    ).delete(synchronize_session=False)
    db.query(SignatarioGovernadoLaudo).filter(
        SignatarioGovernadoLaudo.tenant_id == empresa_id
    ).delete(synchronize_session=False)
    db.query(DispositivoPushMobile).filter(
        DispositivoPushMobile.empresa_id == empresa_id
    ).delete(synchronize_session=False)
    db.query(AprendizadoVisualIa).filter(
        AprendizadoVisualIa.empresa_id == empresa_id
    ).delete(synchronize_session=False)
    db.query(TemplateLaudo).filter(
        TemplateLaudo.empresa_id == empresa_id
    ).delete(synchronize_session=False)
    db.query(RegistroAuditoriaEmpresa).filter(
        RegistroAuditoriaEmpresa.empresa_id == empresa_id
    ).delete(synchronize_session=False)
    db.query(Laudo).filter(
        Laudo.empresa_id == empresa_id
    ).delete(synchronize_session=False)
    db.query(Usuario).filter(
        Usuario.empresa_id == empresa_id
    ).delete(synchronize_session=False)


def remover_empresas_temporarias_auditoria_ui(
    db: Session,
    *,
    actor_user: Usuario,
    company_ids: list[int] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    ids_filtrados = sorted({int(item) for item in list(company_ids or []) if int(item) > 0})
    justificativa = _normalizar_texto_curto(
        reason or "Limpeza operacional de tenants temporários de auditoria UI.",
        campo="Justificativa",
        max_len=300,
    )

    stmt = (
        select(Empresa)
        .where(
            _tenant_cliente_clause(),
            Empresa.nome_fantasia.like(f"{UI_AUDIT_TENANT_PREFIX}%"),
        )
        .order_by(Empresa.id.asc())
    )
    if ids_filtrados:
        stmt = stmt.where(Empresa.id.in_(ids_filtrados))

    empresas = list(db.scalars(stmt).all())
    if not empresas:
        raise ValueError("Nenhuma empresa temporária de auditoria UI foi encontrada para limpeza.")

    resumo_empresas: list[dict[str, Any]] = []
    usuarios_ids_encerrar: list[int] = []
    ids_encontrados = {int(empresa.id) for empresa in empresas}
    ids_nao_encontrados = [item for item in ids_filtrados if item not in ids_encontrados]

    for empresa in empresas:
        nome_empresa = str(getattr(empresa, "nome_fantasia", "") or "").strip()
        if not nome_empresa.startswith(UI_AUDIT_TENANT_PREFIX):
            raise ValueError("A limpeza recusou uma empresa fora do prefixo temporário permitido.")
        if bool(getattr(empresa, "escopo_plataforma", False)):
            raise ValueError("A limpeza recusou uma empresa da plataforma.")

        empresa_id = int(empresa.id)
        usuarios_empresa = list(
            db.scalars(select(Usuario).where(Usuario.empresa_id == empresa_id).order_by(Usuario.id.asc())).all()
        )
        total_laudos = int(db.scalar(select(func.count(Laudo.id)).where(Laudo.empresa_id == empresa_id)) or 0)
        usuarios_ids_encerrar.extend(int(usuario.id) for usuario in usuarios_empresa)
        resumo_empresas.append(
            {
                "empresa_id": empresa_id,
                "nome_fantasia": nome_empresa,
                "cnpj": str(getattr(empresa, "cnpj", "") or ""),
                "usuarios_total": len(usuarios_empresa),
                "laudos_total": total_laudos,
            }
        )

    sessoes_encerradas = sum(
        encerrar_todas_sessoes_usuario(usuario_id) for usuario_id in sorted(set(usuarios_ids_encerrar))
    )

    empresa_plataforma = _resolver_empresa_plataforma(db, usuario=actor_user)
    if empresa_plataforma is None:
        raise ValueError("Tenant de plataforma não encontrado para auditar a limpeza.")

    db.add(
        RegistroAuditoriaEmpresa(
            empresa_id=int(empresa_plataforma.id),
            ator_usuario_id=int(actor_user.id),
            portal="admin",
            acao="ui_audit_tenants_purged",
            resumo="Empresas temporárias de auditoria UI removidas.",
            detalhe="Limpeza definitiva aplicada a tenants criados apenas para validação operacional em produção.",
            payload_json={
                "reason": justificativa,
                "tenant_prefix": UI_AUDIT_TENANT_PREFIX,
                "requested_company_ids": ids_filtrados,
                "missing_company_ids": ids_nao_encontrados,
                "companies": resumo_empresas,
                "sessions_invalidated": int(sessoes_encerradas),
            },
        )
    )

    for empresa in empresas:
        empresa_id = int(empresa.id)
        _remover_dependencias_empresa(db, empresa_id)
        db.delete(empresa)

    commit_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível remover as empresas temporárias de auditoria UI.",
    )
    return {
        "tenant_prefix": UI_AUDIT_TENANT_PREFIX,
        "requested_company_ids": ids_filtrados,
        "missing_company_ids": ids_nao_encontrados,
        "companies_deleted": len(resumo_empresas),
        "sessions_invalidated": int(sessoes_encerradas),
        "companies": resumo_empresas,
    }


def remover_empresas_cliente_por_ids(
    db: Session,
    *,
    actor_user: Usuario,
    company_ids: list[int] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    ids_filtrados = sorted({int(item) for item in list(company_ids or []) if int(item) > 0})
    if not ids_filtrados:
        raise ValueError("Informe ao menos um ID de empresa cliente para remover.")

    justificativa = _normalizar_texto_curto(
        reason or "Limpeza operacional de empresas cliente temporárias.",
        campo="Justificativa",
        max_len=300,
    )

    empresas = list(
        db.scalars(
            select(Empresa)
            .where(
                _tenant_cliente_clause(),
                Empresa.id.in_(ids_filtrados),
            )
            .order_by(Empresa.id.asc())
        ).all()
    )
    if not empresas:
        raise ValueError("Nenhuma empresa cliente válida foi encontrada para remoção.")

    ids_encontrados = {int(empresa.id) for empresa in empresas}
    ids_nao_encontrados = [item for item in ids_filtrados if item not in ids_encontrados]
    if ids_nao_encontrados:
        raise ValueError(
            "Algumas empresas informadas não foram encontradas como clientes válidos: "
            + ", ".join(str(item) for item in ids_nao_encontrados)
            + "."
        )

    resumo_empresas: list[dict[str, Any]] = []
    usuarios_ids_encerrar: list[int] = []

    for empresa in empresas:
        if bool(getattr(empresa, "escopo_plataforma", False)):
            raise ValueError("A limpeza recusou uma empresa da plataforma.")

        empresa_id = int(empresa.id)
        usuarios_empresa = list(
            db.scalars(select(Usuario).where(Usuario.empresa_id == empresa_id).order_by(Usuario.id.asc())).all()
        )
        total_laudos = int(db.scalar(select(func.count(Laudo.id)).where(Laudo.empresa_id == empresa_id)) or 0)
        usuarios_ids_encerrar.extend(int(usuario.id) for usuario in usuarios_empresa)
        resumo_empresas.append(
            {
                "empresa_id": empresa_id,
                "nome_fantasia": str(getattr(empresa, "nome_fantasia", "") or "").strip(),
                "cnpj": str(getattr(empresa, "cnpj", "") or ""),
                "usuarios_total": len(usuarios_empresa),
                "laudos_total": total_laudos,
            }
        )

    sessoes_encerradas = sum(
        encerrar_todas_sessoes_usuario(usuario_id) for usuario_id in sorted(set(usuarios_ids_encerrar))
    )

    empresa_plataforma = _resolver_empresa_plataforma(db, usuario=actor_user)
    if empresa_plataforma is None:
        raise ValueError("Tenant de plataforma não encontrado para auditar a limpeza.")

    db.add(
        RegistroAuditoriaEmpresa(
            empresa_id=int(empresa_plataforma.id),
            ator_usuario_id=int(actor_user.id),
            portal="admin",
            acao="client_tenants_purged",
            resumo="Empresas cliente removidas.",
            detalhe="Limpeza definitiva aplicada a empresas cliente selecionadas explicitamente no Admin-CEO.",
            payload_json={
                "reason": justificativa,
                "requested_company_ids": ids_filtrados,
                "companies": resumo_empresas,
                "sessions_invalidated": int(sessoes_encerradas),
            },
        )
    )

    for empresa in empresas:
        empresa_id = int(empresa.id)
        _remover_dependencias_empresa(db, empresa_id)
        db.delete(empresa)

    commit_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível remover as empresas cliente selecionadas.",
    )
    return {
        "requested_company_ids": ids_filtrados,
        "companies_deleted": len(resumo_empresas),
        "sessions_invalidated": int(sessoes_encerradas),
        "companies": resumo_empresas,
    }
