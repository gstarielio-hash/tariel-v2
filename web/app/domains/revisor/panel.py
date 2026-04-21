from __future__ import annotations

import logging

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.domains.revisor.base import roteador_revisor, templates
from app.domains.revisor.panel_rollout import (
    resolve_review_panel_redirect_url,
    resolve_review_panel_surface,
)
from app.domains.revisor.panel_shadow import (
    build_review_panel_template_context,
    registrar_shadow_review_queue_dashboard,
)
from app.domains.revisor.panel_state import build_review_panel_state
from app.shared.backend_hotspot_metrics import observe_backend_hotspot
from app.shared.database import Usuario, obter_banco
from app.shared.security import exigir_revisor

logger = logging.getLogger("tariel.revisor.panel")


@roteador_revisor.get("/painel", response_class=HTMLResponse)
async def painel_revisor(
    request: Request,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    with observe_backend_hotspot(
        "review_panel_html",
        request=request,
        surface="mesa",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        route_path="/revisao/painel",
        method="GET",
    ) as hotspot:
        redirect_url = resolve_review_panel_redirect_url(request)
        if redirect_url:
            logger.warning("Redirect legado de revisão solicitado, mas a superfície oficial permanece no SSR.")

        requested_surface = resolve_review_panel_surface(request)
        if requested_surface != "ssr":
            logger.warning("Superficie de revisão inválida. Mantendo render SSR legado.")

        panel_state = build_review_panel_state(
            request=request,
            usuario=usuario,
            banco=banco,
        )
        queue_projection_shadow = None
        try:
            queue_projection_shadow = registrar_shadow_review_queue_dashboard(
                request=request,
                usuario=usuario,
                panel_state=panel_state,
            )
        except Exception:
            logger.debug("Falha ao registrar review queue projection em shadow mode.", exc_info=True)
            request.state.v2_review_queue_projection_error = "review_queue_projection_failed"

        try:
            template_context = build_review_panel_template_context(
                request=request,
                usuario=usuario,
                panel_state=panel_state,
                shadow_result=queue_projection_shadow,
            )
        except Exception:
            logger.debug("Falha ao promover review queue projection para o contexto SSR.", exc_info=True)
            request.state.v2_review_queue_projection_prefer_error = "review_queue_projection_prefer_failed"
            request.state.v2_review_queue_projection_preferred = False
            template_context = panel_state.to_template_context(
                request=request,
                usuario=usuario,
            )

        hotspot.outcome = "render_panel"
        hotspot.response_status_code = 200
        hotspot.detail.update(
            {
                "legacy_redirect_requested": bool(redirect_url),
                "requested_surface": requested_surface,
                "queue_projection_preferred": bool(
                    getattr(request.state, "v2_review_queue_projection_preferred", False)
                ),
            }
        )
        return templates.TemplateResponse(
            request,
            "painel_revisor.html",
            template_context,
        )


__all__ = ["painel_revisor"]
