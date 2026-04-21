"""Helpers compartilhados do canal mesa no domínio do inspetor."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domains.chat.attachment_policy import (
    build_mobile_attachment_policy_payload,
)
from app.domains.chat.mensagem_helpers import serializar_mensagem_mesa
from app.domains.chat.mesa_mobile_support import (
    carregar_mensagens_mesa_por_laudo_ids,
    serializar_estado_resumo_mesa_laudo,
)
from app.domains.chat.normalization import nome_template_humano
from app.domains.chat.session_helpers import aplicar_contexto_laudo_selecionado
from app.domains.mesa.service import montar_pacote_mesa_laudo
from app.shared.database import MensagemLaudo, TipoMensagem, Usuario
from app.v2.adapters.android_case_feed import (
    build_inspector_case_interaction_view_from_legacy_message,
    build_inspector_visible_review_signals,
)
from app.v2.adapters.android_case_view import (
    adapt_inspector_case_view_projection_to_android_case,
)
from app.v2.case_runtime import build_technical_case_context_bundle
from app.v2.contracts.mobile import build_mobile_inspector_review_package_v2
from app.v2.contracts.projections import build_inspector_case_view_projection
from app.v2.provenance import (
    build_inspector_content_origin_summary,
    load_message_origin_counters,
)
from app.v2.runtime import (
    actor_role_from_user,
    v2_android_public_contract_enabled,
    v2_document_facade_enabled,
    v2_document_shadow_enabled,
    v2_policy_engine_enabled,
    v2_provenance_enabled,
)


def _request_usa_token_bearer(request: Request) -> bool:
    return str(request.headers.get("authorization") or "").strip().lower().startswith("bearer ")


def _resolver_source_channel(
    request: Request,
    *,
    mobile_channel: str,
    web_channel: str,
) -> str:
    return mobile_channel if _request_usa_token_bearer(request) else web_channel


def _garantir_contrato_publico_mobile_v2_ativo() -> None:
    if not v2_android_public_contract_enabled():
        raise HTTPException(status_code=404, detail="Recurso não encontrado.")


def _carregar_thread_mesa_mobile_estado(
    *,
    laudo_id: int,
    laudo,
    request: Request,
    usuario: Usuario,
    banco: Session,
    cursor: int | None,
    apos_id: int | None,
    limite: int,
    persistir_contexto_sessao: bool,
) -> dict[str, Any]:
    contexto = None
    if persistir_contexto_sessao:
        contexto = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)
    if cursor and apos_id:
        raise HTTPException(status_code=400, detail="Use cursor ou apos_id, nunca ambos.")

    consulta = (
        select(MensagemLaudo)
        .where(
            MensagemLaudo.laudo_id == laudo_id,
            MensagemLaudo.tipo.in_(
                (
                    TipoMensagem.HUMANO_INSP.value,
                    TipoMensagem.HUMANO_ENG.value,
                )
            ),
        )
        .options(selectinload(MensagemLaudo.anexos_mesa))
    )
    if apos_id:
        consulta = consulta.where(MensagemLaudo.id > apos_id)
    elif cursor:
        consulta = consulta.where(MensagemLaudo.id < cursor)

    if apos_id:
        mensagens_asc = list(
            banco.scalars(
                consulta.order_by(MensagemLaudo.id.asc()).limit(limite + 1)
            ).all()
        )
        tem_mais = len(mensagens_asc) > limite
        mensagens_pagina = mensagens_asc[:limite]
        cursor_proximo = mensagens_pagina[-1].id if tem_mais and mensagens_pagina else None
    else:
        mensagens_desc = list(
            banco.scalars(
                consulta.order_by(MensagemLaudo.id.desc()).limit(limite + 1)
            ).all()
        )
        tem_mais = len(mensagens_desc) > limite
        mensagens_pagina = list(reversed(mensagens_desc[:limite]))
        cursor_proximo = mensagens_pagina[0].id if tem_mais and mensagens_pagina else None

    mensagens_resumo = carregar_mensagens_mesa_por_laudo_ids(banco, [laudo_id]).get(laudo_id, [])
    estado_resumo = serializar_estado_resumo_mesa_laudo(
        banco,
        laudo=laudo,
        mensagens=mensagens_resumo,
    )
    attachment_policy = build_mobile_attachment_policy_payload(
        usuario=usuario,
        banco=banco,
    )
    payload_legado = {
        "laudo_id": laudo_id,
        "itens": [serializar_mensagem_mesa(item) for item in mensagens_pagina],
        "cursor_proximo": int(cursor_proximo) if cursor_proximo else None,
        "cursor_ultimo_id": estado_resumo["resumo"]["ultima_mensagem_id"],
        "tem_mais": tem_mais,
        "estado": (
            contexto["estado"]
            if isinstance(contexto, dict)
            else estado_resumo["estado"]
        ),
        "permite_edicao": (
            contexto["permite_edicao"]
            if isinstance(contexto, dict)
            else estado_resumo["permite_edicao"]
        ),
        "permite_reabrir": (
            contexto["permite_reabrir"]
            if isinstance(contexto, dict)
            else estado_resumo["permite_reabrir"]
        ),
        "laudo_card": (
            contexto["laudo_card"]
            if isinstance(contexto, dict) and "laudo_card" in contexto
            else estado_resumo["laudo_card"]
        ),
        "attachment_policy": attachment_policy,
        "resumo": estado_resumo["resumo"],
        "sync": {
            "modo": "delta" if apos_id else "full",
            "apos_id": int(apos_id) if apos_id else None,
            "cursor_ultimo_id": estado_resumo["resumo"]["ultima_mensagem_id"],
        },
    }
    return {
        "payload_legado": payload_legado,
        "mensagens_pagina": mensagens_pagina,
        "mensagens_resumo": mensagens_resumo,
        "estado_resumo": estado_resumo,
        "cursor_proximo": cursor_proximo,
        "tem_mais": tem_mais,
    }


def _construir_contexto_canonico_mobile_inspetor(
    *,
    banco: Session,
    usuario: Usuario,
    laudo,
    legacy_public_state: str,
    allows_edit: bool,
    allows_reopen: bool,
    laudo_card: dict[str, Any] | None,
    mensagens: list[MensagemLaudo],
    source_channel: str,
) -> dict[str, Any]:
    provenance_summary = None
    policy_decision = None
    document_facade = None
    mobile_review_package = None
    shadow_result = None

    if v2_provenance_enabled():
        message_counters = load_message_origin_counters(
            banco,
            laudo_id=int(getattr(laudo, "id", 0) or 0) or None,
        )
        provenance_summary = build_inspector_content_origin_summary(
            laudo=laudo,
            message_counters=message_counters,
            has_active_report=True,
        )

    runtime_bundle = build_technical_case_context_bundle(
        banco=banco,
        usuario=usuario,
        laudo=laudo,
        legacy_payload={
            "estado": str(legacy_public_state or "sem_relatorio"),
            "laudo_id": int(laudo.id),
            "status_card": (
                laudo_card.get("status_card") if isinstance(laudo_card, dict) else None
            ),
            "permite_reabrir": bool(allows_reopen),
            "tem_interacao": bool(mensagens),
            "laudo_card": laudo_card,
            "case_lifecycle_status": (
                laudo_card.get("case_lifecycle_status") if isinstance(laudo_card, dict) else None
            ),
            "case_workflow_mode": (
                laudo_card.get("case_workflow_mode") if isinstance(laudo_card, dict) else None
            ),
            "active_owner_role": (
                laudo_card.get("active_owner_role") if isinstance(laudo_card, dict) else None
            ),
            "allowed_next_lifecycle_statuses": (
                laudo_card.get("allowed_next_lifecycle_statuses")
                if isinstance(laudo_card, dict)
                else None
            ),
            "allowed_lifecycle_transitions": (
                laudo_card.get("allowed_lifecycle_transitions")
                if isinstance(laudo_card, dict)
                else None
            ),
            "allowed_surface_actions": (
                laudo_card.get("allowed_surface_actions")
                if isinstance(laudo_card, dict)
                else None
            ),
        },
        source_channel=source_channel,
        template_key=getattr(laudo, "tipo_template", None),
        family_key=getattr(laudo, "catalog_family_key", None),
        variant_key=getattr(laudo, "catalog_variant_key", None),
        laudo_type=getattr(laudo, "tipo_template", None),
        document_type=getattr(laudo, "tipo_template", None),
        provenance_summary=provenance_summary,
        current_review_status=getattr(laudo, "status_revisao", None),
        has_form_data=bool(getattr(laudo, "dados_formulario", None)),
        has_ai_draft=bool(str(getattr(laudo, "parecer_ia", "") or "").strip()),
        report_pack_draft=getattr(laudo, "report_pack_draft_json", None),
        include_policy_decision=v2_policy_engine_enabled(),
        include_document_facade=v2_document_facade_enabled(),
        attach_document_shadow=v2_document_shadow_enabled(),
    )
    case_snapshot = runtime_bundle.case_snapshot
    assert case_snapshot is not None
    policy_decision = runtime_bundle.policy_decision
    document_facade = runtime_bundle.document_facade
    shadow_result = runtime_bundle.document_shadow_result

    try:
        pacote_mesa = montar_pacote_mesa_laudo(banco, laudo=laudo)
    except Exception:
        pacote_mesa = None

    inspector_projection = build_inspector_case_view_projection(
        case_snapshot=case_snapshot,
        actor_id=usuario.id,
        actor_role=actor_role_from_user(usuario),
        source_channel=source_channel,
        allows_edit=bool(allows_edit),
        has_interaction=bool(mensagens),
        report_types={
            str(getattr(laudo, "tipo_template", None) or "padrao"): nome_template_humano(
                str(getattr(laudo, "tipo_template", None) or "padrao")
            )
        },
        laudo_card=laudo_card,
        policy_decision=policy_decision,
        document_facade=document_facade,
    )
    mobile_review_package = build_mobile_inspector_review_package_v2(
        projection=inspector_projection,
        pacote_mesa=pacote_mesa,
    )
    interaction_views = [
        build_inspector_case_interaction_view_from_legacy_message(
            tenant_id=case_snapshot.tenant_id,
            case_id=case_snapshot.case_ref.case_id,
            thread_id=case_snapshot.case_ref.thread_id,
            message=mensagem,
        )
        for mensagem in mensagens
    ]
    visible_review_signals = build_inspector_visible_review_signals(
        interactions=interaction_views,
        projection=inspector_projection,
    )
    legacy_case_adapter = adapt_inspector_case_view_projection_to_android_case(
        projection=inspector_projection,
        expected_legacy_payload=laudo_card if isinstance(laudo_card, dict) else None,
    )
    return {
        "case_snapshot": case_snapshot,
        "projection": inspector_projection,
        "interaction_views": interaction_views,
        "visible_review_signals": visible_review_signals,
        "provenance_summary": provenance_summary,
        "policy_decision": policy_decision,
        "document_facade": document_facade,
        "mobile_review_package": mobile_review_package,
        "shadow_result": shadow_result,
        "legacy_case_adapter": legacy_case_adapter,
    }


def _parse_laudo_ids_feed(laudo_ids: str) -> list[int]:
    ids: list[int] = []
    for parte in str(laudo_ids or "").split(","):
        valor = parte.strip()
        if not valor:
            continue
        try:
            laudo_id = int(valor)
        except ValueError as erro:
            raise HTTPException(status_code=400, detail="laudo_ids inválido.") from erro
        if laudo_id > 0 and laudo_id not in ids:
            ids.append(laudo_id)
    return ids


__all__ = [
    "_request_usa_token_bearer",
    "_resolver_source_channel",
    "_garantir_contrato_publico_mobile_v2_ativo",
    "_carregar_thread_mesa_mobile_estado",
    "_construir_contexto_canonico_mobile_inspetor",
    "_parse_laudo_ids_feed",
]
