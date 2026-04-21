"""Rotas de feed mobile do canal mesa."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from app.domains.chat.app_context import logger
from app.domains.chat.core_helpers import resposta_json_ok
from app.domains.chat.mesa_common import (
    _construir_contexto_canonico_mobile_inspetor,
    _garantir_contrato_publico_mobile_v2_ativo,
    _parse_laudo_ids_feed,
)
from app.domains.chat.mesa_mobile_support import (
    carregar_feed_mesa_mobile_contextos,
    montar_feed_mesa_mobile,
    normalizar_cursor_atualizado_em,
)
from app.shared.database import Usuario, obter_banco
from app.shared.security import exigir_inspetor
from app.v2.adapters.android_case_feed import (
    adapt_inspector_case_view_projection_to_android_feed_item,
)
from app.v2.contracts.mobile import (
    build_mobile_inspector_feed_item_v2,
    build_mobile_inspector_feed_v2,
)
from app.v2.mobile_rollout import (
    observe_mobile_v2_legacy_fallback,
    observe_mobile_v2_public_contract_read,
    observe_mobile_v2_route_received,
)


async def feed_mesa_mobile(
    request: Request,
    laudo_ids: str = Query(default=""),
    cursor_atualizado_em: datetime | None = Query(default=None),
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    requested_laudo_ids = _parse_laudo_ids_feed(laudo_ids)
    observe_mobile_v2_route_received(
        request,
        usuario=usuario,
        endpoint="feed",
        route="/app/api/mobile/mesa/feed",
        delivery_path="legacy",
        target_ids=requested_laudo_ids,
    )
    observe_mobile_v2_legacy_fallback(
        request,
        usuario=usuario,
        legacy_route="/app/api/mobile/mesa/feed",
        target_ids=requested_laudo_ids,
    )
    return resposta_json_ok(
        montar_feed_mesa_mobile(
            banco,
            request=request,
            usuario=usuario,
            laudo_ids=requested_laudo_ids,
            cursor_atualizado_em=normalizar_cursor_atualizado_em(cursor_atualizado_em),
        )
    )


async def feed_mesa_mobile_public_v2(
    request: Request,
    laudo_ids: str = Query(default=""),
    cursor_atualizado_em: datetime | None = Query(default=None),
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    _garantir_contrato_publico_mobile_v2_ativo()
    source_channel = "android_mesa_feed_v2"
    requested_laudo_ids = _parse_laudo_ids_feed(laudo_ids)
    observe_mobile_v2_route_received(
        request,
        usuario=usuario,
        endpoint="feed",
        route="/app/api/mobile/v2/mesa/feed",
        delivery_path="v2",
        target_ids=requested_laudo_ids,
    )
    payload_legado, contextos = carregar_feed_mesa_mobile_contextos(
        banco,
        usuario=usuario,
        laudo_ids=requested_laudo_ids,
        cursor_atualizado_em=normalizar_cursor_atualizado_em(cursor_atualizado_em),
    )

    itens_publicos = []
    resultados_adapter: list[dict[str, Any]] = []
    case_compat_count = 0
    feed_compat_count = 0

    for contexto in contextos:
        laudo = contexto.laudo
        legacy_item = contexto.legacy_item
        resumo_legacy = (
            legacy_item.get("resumo")
            if isinstance(legacy_item.get("resumo"), dict)
            else {}
        )
        canonical_context = _construir_contexto_canonico_mobile_inspetor(
            banco=banco,
            usuario=usuario,
            laudo=laudo,
            legacy_public_state=str(legacy_item.get("estado") or "sem_relatorio"),
            allows_edit=bool(legacy_item.get("permite_edicao")),
            allows_reopen=bool(legacy_item.get("permite_reabrir")),
            laudo_card=legacy_item.get("laudo_card"),
            mensagens=contexto.mensagens,
            source_channel=source_channel,
        )
        resumo_payload = legacy_item.get("resumo")
        resumo_legacy = resumo_payload if isinstance(resumo_payload, dict) else {}
        public_item = build_mobile_inspector_feed_item_v2(
            projection=canonical_context["projection"],
            interactions=canonical_context["interaction_views"],
            source_channel=source_channel,
            visible_review_signals=canonical_context["visible_review_signals"],
            provenance_summary=canonical_context["provenance_summary"],
            case_metadata={
                "updated_at_iso": str(resumo_legacy.get("atualizado_em") or "")
            },
        )
        itens_publicos.append(public_item)

        feed_adapter = None
        divergences: list[str] = []
        try:
            feed_adapter = adapt_inspector_case_view_projection_to_android_feed_item(
                projection=canonical_context["projection"],
                interactions=canonical_context["interaction_views"],
                visible_review_signals=canonical_context["visible_review_signals"],
                expected_legacy_payload=legacy_item,
                case_metadata={
                    "updated_at_iso": str(resumo_legacy.get("atualizado_em") or "")
                },
            )
            case_compat_count += int(
                canonical_context["legacy_case_adapter"].compatibility.compatible
            )
            feed_compat_count += int(feed_adapter.compatibility.compatible)
            divergences = list(feed_adapter.compatibility.divergences)
        except Exception:
            logger.debug(
                "Falha ao comparar contrato publico mobile V2 do feed com o legado.",
                exc_info=True,
            )
            divergences = ["adapter_exception"]

        resultados_adapter.append(
            {
                "laudo_id": int(laudo.id),
                "case_snapshot": canonical_context["case_snapshot"].model_dump(mode="python"),
                "projection": canonical_context["projection"].model_dump(mode="python"),
                "interaction_views": [
                    item.model_dump(mode="python")
                    for item in canonical_context["interaction_views"]
                ],
                "visible_review_signals": canonical_context[
                    "visible_review_signals"
                ].model_dump(mode="python"),
                "legacy_case_adapter": canonical_context["legacy_case_adapter"].model_dump(
                    mode="python"
                ),
                "legacy_feed_adapter": (
                    feed_adapter.model_dump(mode="python")
                    if feed_adapter is not None
                    else None
                ),
                "public_contract_item": public_item.model_dump(mode="python"),
                "divergences": divergences,
                "provenance": (
                    canonical_context["provenance_summary"].model_dump(mode="python")
                    if canonical_context["provenance_summary"] is not None
                    else None
                ),
                "policy": (
                    canonical_context["policy_decision"].summary.model_dump(mode="python")
                    if canonical_context["policy_decision"] is not None
                    else None
                ),
                "document_facade": (
                    canonical_context["document_facade"].model_dump(mode="python")
                    if canonical_context["document_facade"] is not None
                    else None
                ),
                "document_shadow": (
                    canonical_context["shadow_result"].model_dump(mode="python")
                    if canonical_context["shadow_result"] is not None
                    else None
                ),
            }
        )

    public_contract = build_mobile_inspector_feed_v2(
        tenant_id=(
            itens_publicos[0].tenant_id
            if itens_publicos
            else str(getattr(usuario, "empresa_id", "") or "")
        ),
        source_channel=source_channel,
        requested_laudo_ids=list(payload_legado.get("laudo_ids") or []),
        cursor_current=str(payload_legado.get("cursor_atual") or ""),
        items=itens_publicos,
    )
    request.state.v2_android_public_contract_feed_results = resultados_adapter
    request.state.v2_android_public_contract_feed_summary = {
        "route": "/app/api/mobile/v2/mesa/feed",
        "contract_name": public_contract.contract_name,
        "total": len(resultados_adapter),
        "legacy_case_compatible": case_compat_count,
        "legacy_feed_compatible": feed_compat_count,
        "divergent": len(resultados_adapter) - feed_compat_count,
        "used_public_contract": True,
    }
    observe_mobile_v2_public_contract_read(
        request,
        usuario=usuario,
        endpoint="feed",
        route="/app/api/mobile/v2/mesa/feed",
        target_ids=list(payload_legado.get("laudo_ids") or []),
    )
    logger.info(
        "Mobile V2 public contract usado | route=%s | usuario_id=%s | tenant=%s | itens=%s | divergente=%s",
        "/app/api/mobile/v2/mesa/feed",
        getattr(usuario, "id", None),
        getattr(usuario, "empresa_id", None),
        len(resultados_adapter),
        len(resultados_adapter) - feed_compat_count,
    )
    return resposta_json_ok(public_contract.model_dump(mode="json"))


__all__ = [
    "feed_mesa_mobile",
    "feed_mesa_mobile_public_v2",
]
