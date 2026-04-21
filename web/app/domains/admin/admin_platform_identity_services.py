from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.admin.tenant_user_services import _normalizar_email, _normalizar_texto_curto
from app.shared.database import Empresa, NivelAcesso, RegistroAuditoriaEmpresa, Usuario

logger = logging.getLogger("tariel.saas")

_ADMIN_IDENTITY_STATUS_ALLOWED = frozenset({"active", "password_reset_required"})
_ADMIN_IDENTITY_STATUS_LABELS = {
    "invited": "Convite pendente",
    "active": "Ativo",
    "suspended": "Suspenso",
    "blocked": "Bloqueado",
    "password_reset_required": "Reset obrigatório",
}


@dataclass(slots=True)
class AdminIdentityAuthorizationResult:
    authorized: bool
    user: Usuario | None
    audit_company_id: int | None
    reason: str
    message: str


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _admin_identity_status(valor: str | None) -> str:
    status = str(valor or "active").strip().lower() or "active"
    if status in _ADMIN_IDENTITY_STATUS_LABELS:
        return status
    return "active"


def _admin_identity_status_allows_access(valor: str | None) -> bool:
    return _admin_identity_status(valor) in _ADMIN_IDENTITY_STATUS_ALLOWED


def _usuario_admin_portal_explicitly_authorized(usuario: Usuario | None) -> bool:
    if usuario is None or int(getattr(usuario, "nivel_acesso", 0) or 0) != int(NivelAcesso.DIRETORIA):
        return False

    flag = getattr(usuario, "portal_admin_autorizado", None)
    if flag is None:
        return True
    return bool(flag)


def _usuario_platform_account_active(usuario: Usuario | None) -> bool:
    if usuario is None:
        return False
    scope = str(getattr(usuario, "account_scope", "tenant") or "tenant").strip().lower()
    status = str(getattr(usuario, "account_status", "active") or "active").strip().lower()
    return scope == "platform" and status == "active"


def _usuario_allowed_portals(usuario: Usuario | None) -> set[str]:
    if usuario is None:
        return set()
    bruto = getattr(usuario, "allowed_portals", ())
    return {str(item or "").strip().lower() for item in bruto if str(item or "").strip()}


def _usuario_allows_identity_provider(usuario: Usuario | None, provider: str) -> bool:
    if usuario is None:
        return False
    provider_norm = str(provider or "").strip().lower()
    if provider_norm == "google":
        return bool(getattr(usuario, "can_google_login", False))
    if provider_norm == "microsoft":
        return bool(getattr(usuario, "can_microsoft_login", False))
    if provider_norm == "password":
        return bool(getattr(usuario, "can_password_login", True))
    return False


def _tenant_cliente_clause():
    return Empresa.escopo_plataforma.is_not(True)


def _resolver_empresa_plataforma(db: Session, *, usuario: Usuario | None = None) -> Empresa | None:
    if usuario is not None:
        empresa_usuario = getattr(usuario, "empresa", None)
        if empresa_usuario is not None and bool(getattr(empresa_usuario, "escopo_plataforma", False)):
            return empresa_usuario
        empresa_id = getattr(usuario, "empresa_id", None)
        if empresa_id:
            empresa_carregada = db.get(Empresa, int(empresa_id))
            if empresa_carregada is not None and bool(getattr(empresa_carregada, "escopo_plataforma", False)):
                return empresa_carregada

    return db.scalar(
        select(Empresa)
        .where(Empresa.escopo_plataforma.is_(True))
        .order_by(Empresa.id.asc())
    )


def registrar_auditoria_identidade_admin(
    db: Session,
    *,
    acao: str,
    resumo: str,
    detalhe: str = "",
    provider: str,
    email: str,
    reason: str,
    usuario: Usuario | None = None,
    actor_user_id: int | None = None,
    subject: str = "",
    payload_extra: dict[str, Any] | None = None,
) -> RegistroAuditoriaEmpresa | None:
    empresa_auditoria = _resolver_empresa_plataforma(db, usuario=usuario)
    if empresa_auditoria is None:
        logger.warning(
            "Auditoria de identidade admin sem tenant plataforma resolvido | acao=%s email=%s",
            acao,
            email,
        )
        return None

    email_bruto = str(email or "").strip().lower()
    try:
        email_auditoria = _normalizar_email(email_bruto)
    except ValueError:
        email_auditoria = email_bruto[:254] or "desconhecido"

    payload = {
        "provider": str(provider or "").strip().lower(),
        "email": email_auditoria,
        "reason": str(reason or "").strip().lower(),
        "subject_present": bool(str(subject or "").strip()),
    }
    if payload_extra:
        payload.update(payload_extra)

    registro = RegistroAuditoriaEmpresa(
        empresa_id=int(empresa_auditoria.id),
        ator_usuario_id=actor_user_id if actor_user_id else getattr(usuario, "id", None),
        alvo_usuario_id=getattr(usuario, "id", None),
        portal="admin",
        acao=str(acao or "").strip()[:80] or "admin_identity_event",
        resumo=str(resumo or "").strip()[:220] or "Evento de identidade do Admin-CEO.",
        detalhe=str(detalhe or "").strip() or None,
        payload_json=payload,
    )
    db.add(registro)
    return registro


def autenticar_identidade_admin(
    db: Session,
    *,
    provider: str,
    email: str,
    subject: str,
) -> AdminIdentityAuthorizationResult:
    provider_norm = str(provider or "").strip().lower()
    email_norm = _normalizar_email(email)
    subject_norm = _normalizar_texto_curto(subject, campo="Subject", max_len=255)

    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == email_norm))
    empresa_auditoria = _resolver_empresa_plataforma(db, usuario=usuario)
    audit_company_id = int(empresa_auditoria.id) if empresa_auditoria is not None else None

    if usuario is None:
        return AdminIdentityAuthorizationResult(
            authorized=False,
            user=None,
            audit_company_id=audit_company_id,
            reason="identity_not_found",
            message="Sua identidade foi confirmada, mas este e-mail não está autorizado para o portal Admin-CEO.",
        )

    if int(getattr(usuario, "nivel_acesso", 0) or 0) != int(NivelAcesso.DIRETORIA):
        return AdminIdentityAuthorizationResult(
            authorized=False,
            user=usuario,
            audit_company_id=audit_company_id,
            reason="role_not_allowed",
            message="Sua identidade foi confirmada, mas este e-mail não está autorizado para o portal Admin-CEO.",
        )

    if not _usuario_platform_account_active(usuario):
        return AdminIdentityAuthorizationResult(
            authorized=False,
            user=usuario,
            audit_company_id=audit_company_id,
            reason="account_not_platform_active",
            message="Sua identidade administrativa existe, mas a conta de plataforma não está ativa.",
        )

    if not _usuario_admin_portal_explicitly_authorized(usuario):
        return AdminIdentityAuthorizationResult(
            authorized=False,
            user=usuario,
            audit_company_id=audit_company_id,
            reason="portal_not_authorized",
            message="Sua identidade foi confirmada, mas este e-mail não está autorizado para o portal Admin-CEO.",
        )

    if "admin" not in _usuario_allowed_portals(usuario):
        return AdminIdentityAuthorizationResult(
            authorized=False,
            user=usuario,
            audit_company_id=audit_company_id,
            reason="admin_portal_missing",
            message="Sua identidade foi confirmada, mas o acesso ao portal Admin-CEO não está liberado para esta conta.",
        )

    if not _usuario_allows_identity_provider(usuario, provider_norm):
        return AdminIdentityAuthorizationResult(
            authorized=False,
            user=usuario,
            audit_company_id=audit_company_id,
            reason="identity_method_disabled",
            message="Sua identidade foi confirmada, mas este método de login não está liberado para o Admin-CEO.",
        )

    status = _admin_identity_status(getattr(usuario, "admin_identity_status", None))
    if not _admin_identity_status_allows_access(status):
        return AdminIdentityAuthorizationResult(
            authorized=False,
            user=usuario,
            audit_company_id=audit_company_id,
            reason=f"identity_{status}",
            message=(
                "Sua identidade administrativa existe, mas está sem autorização ativa para o portal Admin-CEO."
            ),
        )

    provider_atual = str(getattr(usuario, "admin_identity_provider", "") or "").strip().lower()
    subject_atual = str(getattr(usuario, "admin_identity_subject", "") or "").strip()
    if provider_atual and provider_atual != provider_norm:
        return AdminIdentityAuthorizationResult(
            authorized=False,
            user=usuario,
            audit_company_id=audit_company_id,
            reason="provider_mismatch",
            message="Sua identidade foi confirmada, mas o provedor não corresponde ao vínculo autorizado do Admin-CEO.",
        )
    if subject_atual and subject_atual != subject_norm:
        return AdminIdentityAuthorizationResult(
            authorized=False,
            user=usuario,
            audit_company_id=audit_company_id,
            reason="subject_mismatch",
            message="Sua identidade foi confirmada, mas o vínculo autorizado do Admin-CEO não corresponde a este login.",
        )

    usuario.admin_identity_provider = provider_norm
    usuario.admin_identity_subject = subject_norm
    usuario.admin_identity_verified_em = _agora_utc()
    if not getattr(usuario, "portal_admin_autorizado", False):
        usuario.portal_admin_autorizado = True

    return AdminIdentityAuthorizationResult(
        authorized=True,
        user=usuario,
        audit_company_id=audit_company_id,
        reason="authorized",
        message="Identidade autorizada para o Admin-CEO.",
    )


def listar_operadores_plataforma(db: Session) -> list[dict[str, Any]]:
    operadores = list(
        db.scalars(
            select(Usuario)
            .where(
                Usuario.account_scope == "platform",
                Usuario.nivel_acesso == int(NivelAcesso.DIRETORIA),
            )
            .order_by(func.lower(Usuario.nome_completo).asc(), Usuario.id.asc())
        ).all()
    )
    return [
        {
            "user_id": int(usuario.id),
            "nome": str(usuario.nome_completo or ""),
            "email": str(usuario.email or "").lower(),
            "account_status": str(getattr(usuario, "account_status", "active") or "active"),
            "platform_role": str(getattr(usuario, "platform_role", "") or "").upper() or "PLATFORM_ADMIN",
            "allowed_portals": sorted(_usuario_allowed_portals(usuario)),
            "mfa_required": bool(getattr(usuario, "mfa_required", False)),
            "mfa_enrolled": bool(getattr(usuario, "mfa_enrolled_at", None)),
            "password_login": bool(getattr(usuario, "can_password_login", True)),
            "google_login": bool(getattr(usuario, "can_google_login", False)),
            "microsoft_login": bool(getattr(usuario, "can_microsoft_login", False)),
            "identity_status": _admin_identity_status(getattr(usuario, "admin_identity_status", None)),
        }
        for usuario in operadores
    ]
