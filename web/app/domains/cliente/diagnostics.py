"""Diagnostico operacional e metadados de suporte do portal admin-cliente."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.domains.chat.app_context import PADRAO_SUPORTE_WHATSAPP
from app.domains.cliente.common import AMBIENTE_APP
from app.shared.database import Usuario
from app.shared.tenant_admin_policy import summarize_tenant_admin_operational_package
from app.v2.contracts.envelopes import utc_now


def _dict_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _dict_list_payload(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def support_whatsapp_cliente() -> str:
    return str(PADRAO_SUPORTE_WHATSAPP or "").strip() or "5516999999999"


def ambiente_cliente() -> str:
    return str(AMBIENTE_APP or "").strip() or "producao"


def build_cliente_portal_context() -> dict[str, str]:
    return {
        "suporte_whatsapp": support_whatsapp_cliente(),
        "ambiente": ambiente_cliente(),
        "diagnostico_url": "/cliente/api/diagnostico",
        "support_report_url": "/cliente/api/suporte/report",
    }


def build_cliente_portal_diagnostic_payload(
    banco: Session,
    usuario: Usuario,
    *,
    request: Request | None = None,
) -> dict[str, Any]:
    from app.domains.cliente.dashboard_bootstrap import bootstrap_cliente

    bootstrap = bootstrap_cliente(banco, usuario, request=None)
    usuarios = _dict_list_payload(bootstrap.get("usuarios"))
    empresa = _dict_payload(bootstrap.get("empresa"))
    portal_context = build_cliente_portal_context()
    tenant_admin_projection = _dict_payload(bootstrap.get("tenant_admin_projection"))
    tenant_admin_payload = _dict_payload(tenant_admin_projection.get("payload"))
    visibility_policy = _dict_payload(tenant_admin_payload.get("visibility_policy"))
    auditoria = _dict_payload(bootstrap.get("auditoria")) or {"itens": []}

    usuarios_ativos = sum(1 for item in usuarios if bool(item.get("ativo")))
    primeiros_acessos = sum(1 for item in usuarios if bool(item.get("senha_temporaria_ativa")))
    bloqueados = sum(1 for item in usuarios if not bool(item.get("ativo")))
    chat = _dict_payload(bootstrap.get("chat"))
    mesa = _dict_payload(bootstrap.get("mesa"))
    visibility_slots_in_use = visibility_policy.get("operational_identity_slots_in_use")
    chat_laudos_payload = chat.get("laudos")
    chat_laudos: list[Any] = list(chat_laudos_payload) if isinstance(chat_laudos_payload, list) else []
    chat_tipos_template_payload = chat.get("tipos_template")
    chat_tipos_template: list[Any] = (
        list(chat_tipos_template_payload) if isinstance(chat_tipos_template_payload, list) else []
    )
    mesa_laudos_payload = mesa.get("laudos")
    mesa_laudos: list[Any] = list(mesa_laudos_payload) if isinstance(mesa_laudos_payload, list) else []
    operational_package = summarize_tenant_admin_operational_package(
        visibility_policy,
        operational_users_in_use=(
            visibility_slots_in_use
            if isinstance(visibility_slots_in_use, int)
            else len(usuarios)
        ),
    )

    payload: dict[str, Any] = {
        "contract_name": "TenantAdminOperationalDiagnosticV1",
        "generated_at": utc_now().isoformat(),
        "portal": "cliente",
        "actor": {
            "usuario_id": int(getattr(usuario, "id", 0) or 0),
            "empresa_id": int(getattr(usuario, "empresa_id", 0) or 0),
            "papel": "admin_cliente",
            "email": str(getattr(usuario, "email", "") or ""),
        },
        "contexto_portal": portal_context,
        "visibility_policy": visibility_policy,
        "operational_package": operational_package,
        "empresa": empresa,
        "usuarios": {
            "total": len(usuarios),
            "ativos": int(usuarios_ativos),
            "bloqueados": int(bloqueados),
            "primeiros_acessos_pendentes": int(primeiros_acessos),
            "itens": usuarios,
        },
        "chat": {
            "total_laudos_visiveis": len(chat_laudos),
            "tipos_template": list(chat_tipos_template),
            "laudos": list(chat_laudos),
        },
        "mesa": {
            "total_laudos_visiveis": len(mesa_laudos),
            "laudos": list(mesa_laudos),
        },
        "auditoria": auditoria,
        "fronteiras": {
            "admin_scope": "tenant_admin_only",
            "chat_scope": "company_scoped",
            "mesa_scope": "company_scoped",
            "revisao_scope": "blocked_outside_reviewer_portal",
            "bridge_policy": "explicit_portal_bridge_only",
        },
    }
    if request is not None:
        payload["request"] = {
            "base_url": str(request.base_url).rstrip("/"),
            "path": str(request.url.path or ""),
        }
    return payload


__all__ = [
    "ambiente_cliente",
    "build_cliente_portal_context",
    "build_cliente_portal_diagnostic_payload",
    "support_whatsapp_cliente",
]
