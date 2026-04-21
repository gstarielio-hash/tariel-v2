"""Suporte mobile/sync da Mesa Avaliadora."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domains.chat.app_context import logger
from app.domains.chat.laudo_state_helpers import (
    laudo_permite_edicao_inspetor,
    laudo_permite_reabrir,
    laudo_possui_historico_visivel,
    obter_estado_api_laudo,
    serializar_contexto_case_lifecycle_legado,
    serializar_card_laudo,
)
from app.domains.chat.normalization import nome_template_humano
from app.domains.mesa.attachments import resumo_mensagem_mesa
from app.shared.database import Laudo, MensagemLaudo, TipoMensagem, Usuario
from app.v2.adapters.android_case_feed import (
    adapt_inspector_case_view_projection_to_android_feed_item,
    build_inspector_case_interaction_view_from_legacy_message,
    build_inspector_visible_review_signals,
)
from app.v2.case_runtime import build_technical_case_context_bundle
from app.v2.contracts.projections import build_inspector_case_view_projection
from app.v2.provenance import (
    build_inspector_content_origin_summary,
    load_message_origin_counters,
)
from app.v2.runtime import (
    actor_role_from_user,
    v2_android_feed_adapter_enabled,
    v2_document_facade_enabled,
    v2_document_shadow_enabled,
    v2_policy_engine_enabled,
    v2_provenance_enabled,
)

_PADRAO_CLIENT_MESSAGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,63}$")
_TIPOS_MESA = (
    TipoMensagem.HUMANO_INSP.value,
    TipoMensagem.HUMANO_ENG.value,
)


@dataclass(slots=True)
class MobileMesaFeedItemContext:
    laudo: Laudo
    legacy_item: dict[str, Any]
    mensagens: list[MensagemLaudo]


def normalizar_client_message_id(valor: object) -> str | None:
    client_message_id = str(valor or "").strip()
    if not client_message_id:
        return None
    if not _PADRAO_CLIENT_MESSAGE_ID.fullmatch(client_message_id):
        raise HTTPException(status_code=400, detail="client_message_id inválido.")
    return client_message_id


def obter_request_id(request: Request) -> str:
    for nome_header in ("X-Client-Request-Id", "X-Request-Id"):
        valor = str(request.headers.get(nome_header, "")).strip()
        if valor:
            return valor[:120]
    return uuid.uuid4().hex


def normalizar_cursor_atualizado_em(cursor: datetime | None) -> datetime | None:
    if cursor is None:
        return None
    if cursor.tzinfo is None:
        return cursor.replace(tzinfo=timezone.utc)
    return cursor.astimezone(timezone.utc)


def _normalizar_datetime_utc(valor: datetime | None) -> datetime | None:
    if valor is None:
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def carregar_mensagem_idempotente(
    banco: Session,
    *,
    laudo_id: int,
    remetente_id: int | None,
    client_message_id: str | None,
) -> MensagemLaudo | None:
    if not client_message_id:
        return None

    consulta = (
        select(MensagemLaudo)
        .where(
            MensagemLaudo.laudo_id == laudo_id,
            MensagemLaudo.remetente_id == remetente_id,
            MensagemLaudo.client_message_id == client_message_id,
        )
        .options(selectinload(MensagemLaudo.anexos_mesa))
    )
    return banco.scalar(consulta)


def carregar_mensagens_mesa_por_laudo_ids(
    banco: Session,
    laudo_ids: list[int],
) -> dict[int, list[MensagemLaudo]]:
    ids_validos = sorted({int(laudo_id) for laudo_id in laudo_ids if int(laudo_id or 0) > 0})
    if not ids_validos:
        return {}

    mensagens = list(
        banco.scalars(
            select(MensagemLaudo)
            .where(
                MensagemLaudo.laudo_id.in_(ids_validos),
                MensagemLaudo.tipo.in_(_TIPOS_MESA),
            )
            .options(selectinload(MensagemLaudo.anexos_mesa))
            .order_by(MensagemLaudo.laudo_id.asc(), MensagemLaudo.id.asc())
        ).all()
    )
    agrupadas: defaultdict[int, list[MensagemLaudo]] = defaultdict(list)
    for mensagem in mensagens:
        agrupadas[int(mensagem.laudo_id)].append(mensagem)
    return dict(agrupadas)


def serializar_resumo_mesa_laudo(
    laudo: Laudo,
    mensagens: list[MensagemLaudo],
) -> dict[str, Any]:
    pendencias_abertas = [
        mensagem
        for mensagem in mensagens
        if mensagem.tipo == TipoMensagem.HUMANO_ENG.value and mensagem.resolvida_em is None
    ]
    pendencias_resolvidas = [
        mensagem
        for mensagem in mensagens
        if mensagem.tipo == TipoMensagem.HUMANO_ENG.value and mensagem.resolvida_em is not None
    ]
    mensagens_nao_lidas = [
        mensagem
        for mensagem in mensagens
        if mensagem.tipo == TipoMensagem.HUMANO_ENG.value and not bool(mensagem.lida)
    ]
    ultima_mensagem = mensagens[-1] if mensagens else None
    atualizado_em = _normalizar_datetime_utc(laudo.atualizado_em or laudo.criado_em)
    payload: dict[str, Any] = {
        "atualizado_em": atualizado_em.isoformat() if atualizado_em else "",
        "total_mensagens": len(mensagens),
        "mensagens_nao_lidas": len(mensagens_nao_lidas),
        "pendencias_abertas": len(pendencias_abertas),
        "pendencias_resolvidas": len(pendencias_resolvidas),
        "ultima_mensagem_id": int(ultima_mensagem.id) if ultima_mensagem else None,
        "ultima_mensagem_em": ultima_mensagem.criado_em.isoformat() if ultima_mensagem and ultima_mensagem.criado_em else "",
        "ultima_mensagem_preview": resumo_mensagem_mesa(
            ultima_mensagem.conteudo,
            anexos=getattr(ultima_mensagem, "anexos_mesa", None),
        )
        if ultima_mensagem
        else "",
        "ultima_mensagem_tipo": str(ultima_mensagem.tipo or "") if ultima_mensagem else "",
        "ultima_mensagem_remetente_id": int(ultima_mensagem.remetente_id)
        if ultima_mensagem and ultima_mensagem.remetente_id
        else None,
    }
    if ultima_mensagem and ultima_mensagem.client_message_id:
        payload["ultima_mensagem_client_message_id"] = str(ultima_mensagem.client_message_id)
    return payload


def serializar_estado_resumo_mesa_laudo(
    banco: Session,
    *,
    laudo: Laudo,
    mensagens: list[MensagemLaudo],
) -> dict[str, Any]:
    payload = {
        "laudo_id": int(laudo.id),
        "estado": obter_estado_api_laudo(banco, laudo),
        "permite_edicao": laudo_permite_edicao_inspetor(laudo),
        "permite_reabrir": laudo_permite_reabrir(banco, laudo),
        "laudo_card": serializar_card_laudo(banco, laudo)
        if laudo_possui_historico_visivel(banco, laudo)
        else None,
        "resumo": serializar_resumo_mesa_laudo(laudo, mensagens),
    }
    payload.update(
        serializar_contexto_case_lifecycle_legado(
            laudo=laudo,
            legacy_payload=payload,
        )
    )
    return payload


def _carregar_feed_mesa_mobile_contextos(
    banco: Session,
    *,
    usuario: Usuario,
    laudo_ids: list[int],
    cursor_atualizado_em: datetime | None,
) -> tuple[dict[str, Any], list[MobileMesaFeedItemContext]]:
    ids_validos = sorted({int(laudo_id) for laudo_id in laudo_ids if int(laudo_id or 0) > 0})
    if not ids_validos:
        return (
            {
                "cursor_atual": "",
                "laudo_ids": [],
                "itens": [],
            },
            [],
        )

    laudos = list(
        banco.scalars(
            select(Laudo)
            .where(
                Laudo.empresa_id == usuario.empresa_id,
                Laudo.usuario_id == usuario.id,
                Laudo.id.in_(ids_validos),
            )
            .order_by(Laudo.id.asc())
        ).all()
    )
    if not laudos:
        return (
            {
                "cursor_atual": "",
                "laudo_ids": [],
                "itens": [],
            },
            [],
        )

    mensagens_por_laudo = carregar_mensagens_mesa_por_laudo_ids(
        banco,
        [int(laudo.id) for laudo in laudos],
    )
    cursor_normalizado = normalizar_cursor_atualizado_em(cursor_atualizado_em)
    referencias_monitoradas: list[datetime] = []
    for laudo in laudos:
        referencia = _normalizar_datetime_utc(laudo.atualizado_em or laudo.criado_em)
        if referencia is not None:
            referencias_monitoradas.append(referencia)

    cursor_atual = cursor_normalizado
    for referencia in referencias_monitoradas:
        if cursor_atual is None or referencia > cursor_atual:
            cursor_atual = referencia

    laudos_alterados = (
        laudos
        if cursor_normalizado is None
        else [
            laudo
            for laudo in laudos
            if (
                referencia := _normalizar_datetime_utc(
                    laudo.atualizado_em or laudo.criado_em,
                )
            )
            is not None
            and referencia > cursor_normalizado
        ]
    )
    contextos = [
        MobileMesaFeedItemContext(
            laudo=laudo,
            legacy_item=serializar_estado_resumo_mesa_laudo(
                banco,
                laudo=laudo,
                mensagens=mensagens_por_laudo.get(int(laudo.id), []),
            ),
            mensagens=mensagens_por_laudo.get(int(laudo.id), []),
        )
        for laudo in laudos_alterados
    ]

    return (
        {
            "cursor_atual": cursor_atual.isoformat() if cursor_atual else "",
            "laudo_ids": [int(laudo.id) for laudo in laudos],
            "itens": [contexto.legacy_item for contexto in contextos],
        },
        contextos,
    )


def carregar_feed_mesa_mobile_contextos(
    banco: Session,
    *,
    usuario: Usuario,
    laudo_ids: list[int],
    cursor_atualizado_em: datetime | None,
) -> tuple[dict[str, Any], list[MobileMesaFeedItemContext]]:
    return _carregar_feed_mesa_mobile_contextos(
        banco,
        usuario=usuario,
        laudo_ids=laudo_ids,
        cursor_atualizado_em=cursor_atualizado_em,
    )


def montar_feed_mesa_mobile(
    banco: Session,
    *,
    request: Request | None = None,
    usuario: Usuario,
    laudo_ids: list[int],
    cursor_atualizado_em: datetime | None,
) -> dict[str, Any]:
    payload_legado, contextos = _carregar_feed_mesa_mobile_contextos(
        banco,
        usuario=usuario,
        laudo_ids=laudo_ids,
        cursor_atualizado_em=cursor_atualizado_em,
    )
    if not v2_android_feed_adapter_enabled():
        return payload_legado

    resultados_adapter: list[dict[str, Any]] = []
    itens_publicos: list[dict[str, Any]] = []
    compat_count = 0

    for contexto in contextos:
        laudo = contexto.laudo
        legacy_item = contexto.legacy_item
        mensagens = contexto.mensagens
        provenance_summary = None
        policy_decision = None
        document_facade = None
        shadow_result = None

        try:
            resumo_payload = legacy_item.get("resumo")
            resumo_legacy = resumo_payload if isinstance(resumo_payload, dict) else {}
            laudo_card_payload = legacy_item.get("laudo_card")
            laudo_card = laudo_card_payload if isinstance(laudo_card_payload, dict) else {}
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

            legacy_payload = {
                "estado": str(legacy_item.get("estado") or "sem_relatorio"),
                "laudo_id": int(laudo.id),
                "status_card": laudo_card.get("status_card"),
                "permite_reabrir": bool(legacy_item.get("permite_reabrir")),
                "tem_interacao": bool(mensagens),
                "laudo_card": legacy_item.get("laudo_card"),
                "case_lifecycle_status": (
                    legacy_item.get("case_lifecycle_status")
                    or laudo_card.get("case_lifecycle_status")
                ),
                "case_workflow_mode": (
                    legacy_item.get("case_workflow_mode")
                    or laudo_card.get("case_workflow_mode")
                ),
                "active_owner_role": (
                    legacy_item.get("active_owner_role")
                    or laudo_card.get("active_owner_role")
                ),
                "allowed_next_lifecycle_statuses": (
                    legacy_item.get("allowed_next_lifecycle_statuses")
                    or laudo_card.get("allowed_next_lifecycle_statuses")
                ),
                "allowed_lifecycle_transitions": (
                    legacy_item.get("allowed_lifecycle_transitions")
                    or laudo_card.get("allowed_lifecycle_transitions")
                ),
                "allowed_surface_actions": (
                    legacy_item.get("allowed_surface_actions")
                    or laudo_card.get("allowed_surface_actions")
                ),
            }
            runtime_bundle = build_technical_case_context_bundle(
                banco=banco,
                usuario=usuario,
                laudo=laudo,
                legacy_payload=legacy_payload,
                source_channel="android_mesa_feed",
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
                source_channel="android_mesa_feed",
                allows_edit=bool(legacy_item.get("permite_edicao")),
                has_interaction=bool(legacy_payload["tem_interacao"]),
                report_types={
                    str(getattr(laudo, "tipo_template", None) or "padrao"): nome_template_humano(
                        str(getattr(laudo, "tipo_template", None) or "padrao")
                    )
                },
                laudo_card=legacy_item.get("laudo_card"),
                policy_decision=policy_decision,
                document_facade=document_facade,
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
            adapted = adapt_inspector_case_view_projection_to_android_feed_item(
                projection=inspector_projection,
                interactions=interaction_views,
                visible_review_signals=visible_review_signals,
                expected_legacy_payload=legacy_item,
                case_metadata={"updated_at_iso": str(resumo_legacy.get("atualizado_em") or "")},
            )

            if adapted.compatibility.compatible:
                compat_count += 1
                itens_publicos.append(adapted.payload)
            else:
                logger.debug(
                    "V2 android feed adapter divergiu | laudo_id=%s | divergences=%s",
                    laudo.id,
                    ",".join(adapted.compatibility.divergences),
                )
                itens_publicos.append(legacy_item)

            resultados_adapter.append(
                {
                    "laudo_id": int(laudo.id),
                    "case_snapshot": case_snapshot.model_dump(mode="python"),
                    "projection": inspector_projection.model_dump(mode="python"),
                    "interaction_views": [
                        item.model_dump(mode="python")
                        for item in interaction_views
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
                    "android_feed_adapter": adapted.model_dump(mode="python"),
                }
            )
        except Exception:
            logger.debug(
                "Falha ao derivar adapter canônico do feed mobile da mesa no V2.",
                exc_info=True,
            )
            itens_publicos.append(legacy_item)
            resultados_adapter.append(
                {
                    "laudo_id": int(laudo.id),
                    "case_snapshot": None,
                    "projection": None,
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
                    "android_feed_adapter": None,
                }
            )

    if request is not None:
        request.state.v2_android_feed_adapter_results = resultados_adapter
        request.state.v2_android_feed_adapter_summary = {
            "total": len(resultados_adapter),
            "compatible": compat_count,
            "divergent": len(resultados_adapter) - compat_count,
            "used_projection": compat_count,
        }

    resposta = dict(payload_legado)
    resposta["itens"] = itens_publicos
    return resposta


__all__ = [
    "carregar_feed_mesa_mobile_contextos",
    "carregar_mensagem_idempotente",
    "carregar_mensagens_mesa_por_laudo_ids",
    "montar_feed_mesa_mobile",
    "normalizar_client_message_id",
    "normalizar_cursor_atualizado_em",
    "obter_request_id",
    "serializar_estado_resumo_mesa_laudo",
    "serializar_resumo_mesa_laudo",
]
