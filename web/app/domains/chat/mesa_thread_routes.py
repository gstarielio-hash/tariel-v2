"""Rotas de thread e resumo do canal mesa."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from app.domains.chat.app_context import logger
from app.domains.chat.core_helpers import resposta_json_ok
from app.domains.chat.laudo_access_helpers import obter_laudo_do_inspetor
from app.domains.chat.mesa_common import (
    _carregar_thread_mesa_mobile_estado,
    _construir_contexto_canonico_mobile_inspetor,
    _garantir_contrato_publico_mobile_v2_ativo,
    _resolver_source_channel,
)
from app.domains.chat.mesa_mobile_support import (
    carregar_mensagens_mesa_por_laudo_ids,
    serializar_estado_resumo_mesa_laudo,
)
from app.domains.chat.normalization import nome_template_humano
from app.domains.chat.request_parsing_helpers import InteiroOpcionalNullish
from app.domains.chat.session_helpers import aplicar_contexto_laudo_selecionado
from app.shared.database import Usuario, obter_banco
from app.shared.security import exigir_inspetor
from app.v2.adapters.android_case_feed import (
    build_inspector_case_interaction_view_from_legacy_message,
    build_inspector_visible_review_signals,
)
from app.v2.adapters.android_case_thread import (
    adapt_inspector_case_view_projection_to_android_thread,
    build_inspector_case_conversation_view,
)
from app.v2.case_runtime import build_technical_case_context_bundle
from app.v2.contracts.mobile import build_mobile_inspector_thread_v2
from app.v2.contracts.projections import build_inspector_case_view_projection
from app.v2.mobile_rollout import (
    observe_mobile_v2_legacy_fallback,
    observe_mobile_v2_public_contract_read,
)
from app.v2.provenance import (
    build_inspector_content_origin_summary,
    load_message_origin_counters,
)
from app.v2.runtime import (
    actor_role_from_user,
    v2_android_thread_adapter_enabled,
    v2_document_facade_enabled,
    v2_document_shadow_enabled,
    v2_policy_engine_enabled,
    v2_provenance_enabled,
)


async def listar_mensagens_mesa_laudo(
    laudo_id: int,
    request: Request,
    cursor: Annotated[InteiroOpcionalNullish, Query()] = None,
    apos_id: Annotated[InteiroOpcionalNullish, Query()] = None,
    limite: int = Query(default=40, ge=10, le=120),
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    thread_state = _carregar_thread_mesa_mobile_estado(
        laudo_id=laudo_id,
        laudo=laudo,
        request=request,
        usuario=usuario,
        banco=banco,
        cursor=cursor,
        apos_id=apos_id,
        limite=limite,
        persistir_contexto_sessao=True,
    )
    mensagens_pagina = thread_state["mensagens_pagina"]
    mensagens_resumo = thread_state["mensagens_resumo"]
    estado_resumo = thread_state["estado_resumo"]
    cursor_proximo = thread_state["cursor_proximo"]
    tem_mais = thread_state["tem_mais"]
    payload_legado = thread_state["payload_legado"]
    observe_mobile_v2_legacy_fallback(
        request,
        usuario=usuario,
        legacy_route="/app/api/laudo/{laudo_id}/mesa/mensagens",
        target_ids=[int(laudo.id)],
    )
    if not v2_android_thread_adapter_enabled():
        return resposta_json_ok(payload_legado)

    provenance_summary = None
    policy_decision = None
    document_facade = None
    shadow_result = None

    try:
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

        laudo_card = (
            payload_legado.get("laudo_card")
            if isinstance(payload_legado.get("laudo_card"), dict)
            else {}
        )
        legacy_payload = {
            "estado": str(payload_legado.get("estado") or "sem_relatorio"),
            "laudo_id": int(laudo.id),
            "status_card": laudo_card.get("status_card"),
            "permite_reabrir": bool(payload_legado.get("permite_reabrir")),
            "tem_interacao": bool(mensagens_resumo),
            "laudo_card": payload_legado.get("laudo_card"),
            "case_lifecycle_status": (
                payload_legado.get("case_lifecycle_status")
                or laudo_card.get("case_lifecycle_status")
            ),
            "case_workflow_mode": (
                payload_legado.get("case_workflow_mode")
                or laudo_card.get("case_workflow_mode")
            ),
            "active_owner_role": (
                payload_legado.get("active_owner_role")
                or laudo_card.get("active_owner_role")
            ),
            "allowed_next_lifecycle_statuses": (
                payload_legado.get("allowed_next_lifecycle_statuses")
                or laudo_card.get("allowed_next_lifecycle_statuses")
            ),
            "allowed_lifecycle_transitions": (
                payload_legado.get("allowed_lifecycle_transitions")
                or laudo_card.get("allowed_lifecycle_transitions")
            ),
            "allowed_surface_actions": (
                payload_legado.get("allowed_surface_actions")
                or laudo_card.get("allowed_surface_actions")
            ),
        }
        source_channel = _resolver_source_channel(
            request,
            mobile_channel="android_mesa_thread",
            web_channel="inspetor_mesa_thread",
        )
        runtime_bundle = build_technical_case_context_bundle(
            banco=banco,
            usuario=usuario,
            laudo=laudo,
            legacy_payload=legacy_payload,
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

        inspector_projection = build_inspector_case_view_projection(
            case_snapshot=case_snapshot,
            actor_id=usuario.id,
            actor_role=actor_role_from_user(usuario),
            source_channel=source_channel,
            allows_edit=bool(payload_legado.get("permite_edicao")),
            has_interaction=bool(mensagens_resumo),
            report_types={
                str(getattr(laudo, "tipo_template", None) or "padrao"): nome_template_humano(
                    str(getattr(laudo, "tipo_template", None) or "padrao")
                )
            },
            laudo_card=payload_legado.get("laudo_card"),
            policy_decision=policy_decision,
            document_facade=document_facade,
        )
        all_interaction_views = [
            build_inspector_case_interaction_view_from_legacy_message(
                tenant_id=case_snapshot.tenant_id,
                case_id=case_snapshot.case_ref.case_id,
                thread_id=case_snapshot.case_ref.thread_id,
                message=mensagem,
            )
            for mensagem in mensagens_resumo
        ]
        page_interaction_views = [
            build_inspector_case_interaction_view_from_legacy_message(
                tenant_id=case_snapshot.tenant_id,
                case_id=case_snapshot.case_ref.case_id,
                thread_id=case_snapshot.case_ref.thread_id,
                message=mensagem,
            )
            for mensagem in mensagens_pagina
        ]
        visible_review_signals = build_inspector_visible_review_signals(
            interactions=all_interaction_views,
            projection=inspector_projection,
        )
        conversation = build_inspector_case_conversation_view(
            tenant_id=case_snapshot.tenant_id,
            case_id=case_snapshot.case_ref.case_id,
            thread_id=case_snapshot.case_ref.thread_id,
            page_interactions=page_interaction_views,
            all_interactions=all_interaction_views,
            sync_mode="delta" if apos_id else "full",
            cursor_after_id=int(apos_id) if apos_id else None,
            next_cursor_id=int(cursor_proximo) if cursor_proximo else None,
            cursor_last_message_id=estado_resumo["resumo"]["ultima_mensagem_id"],
            has_more=tem_mais,
        )
        adapted = adapt_inspector_case_view_projection_to_android_thread(
            projection=inspector_projection,
            conversation=conversation,
            interactions=all_interaction_views,
            visible_review_signals=visible_review_signals,
            expected_legacy_payload=payload_legado,
            legacy_laudo_context={
                "estado": payload_legado.get("estado"),
                "permite_edicao": payload_legado.get("permite_edicao"),
                "permite_reabrir": payload_legado.get("permite_reabrir"),
                "laudo_card": payload_legado.get("laudo_card"),
                "attachment_policy": payload_legado.get("attachment_policy"),
            },
            provenance_summary=(
                provenance_summary.model_dump(mode="python")
                if provenance_summary is not None
                else None
            ),
            case_metadata={"updated_at_iso": str(estado_resumo["resumo"].get("atualizado_em") or "")},
        )

        request.state.v2_android_thread_adapter_result = {
            "laudo_id": int(laudo.id),
            "case_snapshot": case_snapshot.model_dump(mode="python"),
            "projection": inspector_projection.model_dump(mode="python"),
            "conversation": conversation.model_dump(mode="python"),
            "interaction_views": [
                item.model_dump(mode="python")
                for item in all_interaction_views
            ],
            "visible_review_signals": visible_review_signals.model_dump(mode="python"),
            "compatible": adapted.compatibility.compatible,
            "divergences": adapted.compatibility.divergences,
            "used_projection": adapted.compatibility.compatible,
            "provenance": (
                provenance_summary.model_dump(mode="python")
                if provenance_summary is not None
                else None
            ),
            "policy": (
                policy_decision.summary.model_dump(mode="python")
                if policy_decision is not None
                else None
            ),
            "document_facade": (
                document_facade.model_dump(mode="python")
                if document_facade is not None
                else None
            ),
            "document_shadow": (
                shadow_result.model_dump(mode="python")
                if shadow_result is not None
                else None
            ),
            "android_thread_adapter": adapted.model_dump(mode="python"),
        }
        request.state.v2_android_thread_adapter_summary = {
            "laudo_id": int(laudo.id),
            "total_messages": adapted.compatibility.message_count,
            "compatible_messages": adapted.compatibility.compatible_message_count,
            "compatible": adapted.compatibility.compatible,
            "divergences": list(adapted.compatibility.divergences),
            "used_projection": adapted.compatibility.compatible,
        }

        if adapted.compatibility.compatible:
            return resposta_json_ok(adapted.payload)

        logger.debug(
            "V2 android thread adapter divergiu | laudo_id=%s | divergences=%s",
            laudo.id,
            ",".join(adapted.compatibility.divergences),
        )
    except Exception:
        logger.debug(
            "Falha ao derivar adapter canônico da conversa detalhada mobile da mesa no V2.",
            exc_info=True,
        )
        request.state.v2_android_thread_adapter_result = {
            "laudo_id": int(laudo.id),
            "case_snapshot": None,
            "projection": None,
            "conversation": None,
            "interaction_views": [],
            "visible_review_signals": None,
            "compatible": False,
            "divergences": ["adapter_exception"],
            "used_projection": False,
            "provenance": (
                provenance_summary.model_dump(mode="python")
                if provenance_summary is not None
                else None
            ),
            "policy": (
                policy_decision.summary.model_dump(mode="python")
                if policy_decision is not None
                else None
            ),
            "document_facade": (
                document_facade.model_dump(mode="python")
                if document_facade is not None
                else None
            ),
            "document_shadow": (
                shadow_result.model_dump(mode="python")
                if shadow_result is not None
                else None
            ),
            "android_thread_adapter": None,
        }
        request.state.v2_android_thread_adapter_summary = {
            "laudo_id": int(laudo.id),
            "total_messages": len(payload_legado["itens"]),
            "compatible_messages": 0,
            "compatible": False,
            "divergences": ["adapter_exception"],
            "used_projection": False,
        }

    return resposta_json_ok(payload_legado)


async def obter_resumo_mesa_laudo(
    laudo_id: int,
    request: Request,
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)
    mensagens = carregar_mensagens_mesa_por_laudo_ids(banco, [laudo_id]).get(laudo_id, [])
    return resposta_json_ok(
        serializar_estado_resumo_mesa_laudo(
            banco,
            laudo=laudo,
            mensagens=mensagens,
        )
    )


async def listar_mensagens_mesa_laudo_mobile_public_v2(
    laudo_id: int,
    request: Request,
    cursor: Annotated[InteiroOpcionalNullish, Query()] = None,
    apos_id: Annotated[InteiroOpcionalNullish, Query()] = None,
    limite: int = Query(default=40, ge=10, le=120),
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    _garantir_contrato_publico_mobile_v2_ativo()
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    thread_state = _carregar_thread_mesa_mobile_estado(
        laudo_id=laudo_id,
        laudo=laudo,
        request=request,
        usuario=usuario,
        banco=banco,
        cursor=cursor,
        apos_id=apos_id,
        limite=limite,
        persistir_contexto_sessao=False,
    )
    payload_legado = thread_state["payload_legado"]
    estado_resumo = thread_state["estado_resumo"]
    mensagens_pagina = thread_state["mensagens_pagina"]
    mensagens_resumo = thread_state["mensagens_resumo"]
    source_channel = "android_mesa_thread_v2"

    canonical_context = _construir_contexto_canonico_mobile_inspetor(
        banco=banco,
        usuario=usuario,
        laudo=laudo,
        legacy_public_state=str(payload_legado.get("estado") or "sem_relatorio"),
        allows_edit=bool(payload_legado.get("permite_edicao")),
        allows_reopen=bool(payload_legado.get("permite_reabrir")),
        laudo_card=payload_legado.get("laudo_card"),
        mensagens=mensagens_resumo,
        source_channel=source_channel,
    )
    page_interaction_views = [
        build_inspector_case_interaction_view_from_legacy_message(
            tenant_id=canonical_context["case_snapshot"].tenant_id,
            case_id=canonical_context["case_snapshot"].case_ref.case_id,
            thread_id=canonical_context["case_snapshot"].case_ref.thread_id,
            message=mensagem,
        )
        for mensagem in mensagens_pagina
    ]
    conversation = build_inspector_case_conversation_view(
        tenant_id=canonical_context["case_snapshot"].tenant_id,
        case_id=canonical_context["case_snapshot"].case_ref.case_id,
        thread_id=canonical_context["case_snapshot"].case_ref.thread_id,
        page_interactions=page_interaction_views,
        all_interactions=canonical_context["interaction_views"],
        sync_mode="delta" if apos_id else "full",
        cursor_after_id=int(apos_id) if apos_id else None,
        next_cursor_id=(
            int(thread_state["cursor_proximo"])
            if thread_state["cursor_proximo"]
            else None
        ),
        cursor_last_message_id=estado_resumo["resumo"]["ultima_mensagem_id"],
        has_more=thread_state["tem_mais"],
    )
    public_contract = build_mobile_inspector_thread_v2(
        projection=canonical_context["projection"],
        conversation=conversation,
        source_channel=source_channel,
        visible_review_signals=canonical_context["visible_review_signals"],
        provenance_summary=canonical_context["provenance_summary"],
        mobile_review_package=canonical_context["mobile_review_package"],
    )

    thread_adapter = None
    divergences: list[str] = []
    try:
        thread_adapter = adapt_inspector_case_view_projection_to_android_thread(
            projection=canonical_context["projection"],
            conversation=conversation,
            interactions=canonical_context["interaction_views"],
            visible_review_signals=canonical_context["visible_review_signals"],
            expected_legacy_payload=payload_legado,
            legacy_laudo_context={
                "estado": payload_legado.get("estado"),
                "permite_edicao": payload_legado.get("permite_edicao"),
                "permite_reabrir": payload_legado.get("permite_reabrir"),
                "laudo_card": payload_legado.get("laudo_card"),
                "attachment_policy": payload_legado.get("attachment_policy"),
            },
            provenance_summary=(
                canonical_context["provenance_summary"].model_dump(mode="python")
                if canonical_context["provenance_summary"] is not None
                else None
            ),
            case_metadata={
                "updated_at_iso": str(
                    estado_resumo["resumo"].get("atualizado_em") or ""
                )
            },
        )
        divergences = list(thread_adapter.compatibility.divergences)
    except Exception:
        logger.debug(
            "Falha ao comparar contrato publico mobile V2 da thread com o legado.",
            exc_info=True,
        )
        divergences = ["adapter_exception"]

    request.state.v2_android_public_contract_thread_result = {
        "laudo_id": int(laudo.id),
        "case_snapshot": canonical_context["case_snapshot"].model_dump(mode="python"),
        "projection": canonical_context["projection"].model_dump(mode="python"),
        "conversation": conversation.model_dump(mode="python"),
        "interaction_views": [
            item.model_dump(mode="python")
            for item in canonical_context["interaction_views"]
        ],
        "visible_review_signals": canonical_context["visible_review_signals"].model_dump(
            mode="python"
        ),
        "legacy_case_adapter": canonical_context["legacy_case_adapter"].model_dump(
            mode="python"
        ),
        "legacy_thread_adapter": (
            thread_adapter.model_dump(mode="python")
            if thread_adapter is not None
            else None
        ),
        "public_contract": public_contract.model_dump(mode="python"),
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
    request.state.v2_android_public_contract_thread_summary = {
        "route": "/app/api/mobile/v2/laudo/{laudo_id}/mesa/mensagens",
        "contract_name": public_contract.contract_name,
        "legacy_case_compatible": canonical_context["legacy_case_adapter"].compatibility.compatible,
        "legacy_thread_compatible": (
            thread_adapter.compatibility.compatible
            if thread_adapter is not None
            else False
        ),
        "total_messages": len(public_contract.items),
        "divergences": divergences,
        "used_public_contract": True,
    }
    observe_mobile_v2_public_contract_read(
        request,
        usuario=usuario,
        endpoint="thread",
        route="/app/api/mobile/v2/laudo/{laudo_id}/mesa/mensagens",
        target_ids=[int(laudo.id)],
    )
    logger.info(
        "Mobile V2 public contract usado | route=%s | usuario_id=%s | tenant=%s | laudo_id=%s | mensagens=%s | divergencias=%s",
        "/app/api/mobile/v2/laudo/{laudo_id}/mesa/mensagens",
        getattr(usuario, "id", None),
        getattr(usuario, "empresa_id", None),
        int(laudo.id),
        len(public_contract.items),
        ",".join(divergences) or "none",
    )
    return resposta_json_ok(public_contract.model_dump(mode="json"))


__all__ = [
    "listar_mensagens_mesa_laudo",
    "obter_resumo_mesa_laudo",
    "listar_mensagens_mesa_laudo_mobile_public_v2",
]
