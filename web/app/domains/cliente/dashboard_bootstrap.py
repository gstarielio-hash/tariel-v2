"""Shell do bootstrap do portal admin-cliente."""

from __future__ import annotations

import logging

from starlette.requests import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.admin.services import (
    filtro_usuarios_gerenciaveis_cliente,
    filtro_usuarios_operacionais_cliente,
)
from app.domains.cliente.auditoria import (
    listar_auditoria_empresa,
    resumir_auditoria_serializada,
    serializar_registro_auditoria,
)
from app.domains.cliente.dashboard_analytics import resumo_empresa_cliente
from app.domains.cliente.dashboard_bootstrap_shadow import (
    build_tenant_admin_projection_for_bootstrap,
    registrar_shadow_tenant_admin_bootstrap,
)
from app.domains.cliente.diagnostics import build_cliente_portal_context
from app.domains.cliente.dashboard_bootstrap_support import (
    ROLE_LABELS,
    listar_laudos_chat_usuario,
    listar_laudos_mesa_empresa,
    serializar_usuario_cliente,
)
from app.shared.backend_hotspot_metrics import observe_backend_hotspot
from app.shared.database import Usuario
from app.shared.tenant_entitlement_guard import tenant_access_policy_for_user
from app.shared.tenant_admin_policy import tenant_admin_surface_availability
from app.shared.tenant_report_catalog import build_tenant_template_option_snapshot

logger = logging.getLogger("tariel.cliente.bootstrap")


def _normalizar_superficie_bootstrap(surface: str | None) -> str | None:
    valor = str(surface or "").strip().lower()
    if valor in {"admin", "chat", "mesa"}:
        return valor
    return None


def bootstrap_cliente(
    banco: Session,
    usuario: Usuario,
    *,
    request: Request | None = None,
    surface: str | None = None,
) -> dict[str, object]:
    with observe_backend_hotspot(
        "cliente_bootstrap",
        request=request,
        surface="admin_cliente",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        route_path="/cliente/api/bootstrap" if request is not None else "service:bootstrap_cliente",
        method="GET" if request is not None else "SERVICE",
        detail={"requested_surface": _normalizar_superficie_bootstrap(surface) or "full"},
    ) as hotspot:
        surface_resolvida = _normalizar_superficie_bootstrap(surface)
        usuarios_tenant_admin = list(
            banco.scalars(
                select(Usuario)
                .where(
                    Usuario.empresa_id == usuario.empresa_id,
                    filtro_usuarios_gerenciaveis_cliente(),
                )
                .order_by(Usuario.nivel_acesso.desc(), Usuario.nome_completo.asc())
            ).all()
        )
        empresa_summary = resumo_empresa_cliente(banco, usuario)
        tenant_admin_projection, _case_snapshots = build_tenant_admin_projection_for_bootstrap(
            banco=banco,
            usuario=usuario,
            empresa_summary=empresa_summary,
            usuarios=usuarios_tenant_admin,
        )
        tenant_admin_payload = (
            tenant_admin_projection.payload
            if isinstance(getattr(tenant_admin_projection, "payload", None), dict)
            else {}
        )
        surface_availability = tenant_admin_surface_availability(
            tenant_admin_payload.get("visibility_policy")
        )
        if surface_resolvida in {"chat", "mesa"} and not surface_availability.get(surface_resolvida, False):
            surface_resolvida = "admin"

        incluir_admin = surface_resolvida in {None, "admin"}
        incluir_chat = surface_resolvida in {None, "chat"} and bool(surface_availability.get("chat"))
        incluir_mesa = surface_resolvida in {None, "mesa"} and bool(surface_availability.get("mesa"))
        payload = {
            "portal": build_cliente_portal_context(),
            "empresa": empresa_summary,
            "tenant_admin_projection": tenant_admin_projection.model_dump(mode="json"),
            "tenant_access_policy": tenant_access_policy_for_user(usuario),
        }

        if incluir_admin:
            auditoria_itens = [
                serializar_registro_auditoria(item)
                for item in listar_auditoria_empresa(banco, empresa_id=int(usuario.empresa_id))
            ]
            usuarios_publicos = list(
                banco.scalars(
                    select(Usuario)
                    .where(
                        Usuario.empresa_id == usuario.empresa_id,
                        filtro_usuarios_operacionais_cliente(),
                    )
                    .order_by(Usuario.nivel_acesso.desc(), Usuario.nome_completo.asc())
                ).all()
            )
            payload["usuarios"] = [serializar_usuario_cliente(item) for item in usuarios_publicos]
            payload["auditoria"] = {
                "itens": auditoria_itens,
                "resumo": resumir_auditoria_serializada(auditoria_itens),
            }

        if incluir_chat:
            template_snapshot = build_tenant_template_option_snapshot(banco, empresa_id=int(usuario.empresa_id))
            payload["chat"] = {
                "tipos_template": {
                    str(item["value"]): str(item["label"])
                    for item in list(template_snapshot.get("options") or [])
                },
                "tipo_template_options": list(template_snapshot.get("options") or []),
                "catalog_governed_mode": bool(template_snapshot.get("governed_mode")),
                "catalog_state": str(template_snapshot.get("catalog_state") or "legacy_open"),
                "catalog_permissions": dict(template_snapshot.get("permissions") or {}),
                "laudos": listar_laudos_chat_usuario(banco, usuario),
            }

        if incluir_mesa:
            payload["mesa"] = {
                "laudos": listar_laudos_mesa_empresa(banco, usuario),
            }

        if request is not None and surface_resolvida is None:
            try:
                registrar_shadow_tenant_admin_bootstrap(
                    request=request,
                    banco=banco,
                    usuario=usuario,
                    empresa_summary=empresa_summary,
                    usuarios=usuarios_tenant_admin,
                    payload_publico=payload,
                )
            except Exception:
                logger.debug("Falha ao registrar tenant admin view em shadow mode.", exc_info=True)
                request.state.v2_tenant_admin_projection_error = "tenant_admin_projection_failed"

        hotspot.outcome = surface_resolvida or "full"
        hotspot.response_status_code = 200
        hotspot.detail.update(
            {
                "sections": [
                    section
                    for section, enabled in (
                        ("admin", incluir_admin),
                        ("chat", incluir_chat),
                        ("mesa", incluir_mesa),
                    )
                    if enabled
                ],
                "tenant_admin_users": len(usuarios_tenant_admin),
            }
        )
        return payload


__all__ = [
    "ROLE_LABELS",
    "bootstrap_cliente",
    "listar_laudos_chat_usuario",
    "listar_laudos_mesa_empresa",
    "serializar_usuario_cliente",
]
