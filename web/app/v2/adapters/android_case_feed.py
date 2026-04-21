"""Adapter do feed canônico do Inspetor para o payload legado mobile da mesa."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domains.chat.pendencias_helpers import formatar_data_br, nome_resolvedor_pendencia
from app.domains.mesa.attachments import (
    resumo_mensagem_mesa,
    serializar_anexos_mesa,
    texto_mensagem_mesa_visivel,
)
from app.domains.mesa.operational_tasks import extract_operational_context
from app.domains.mesa.semantics import build_mesa_message_semantics
from app.shared.database import MensagemLaudo
from app.v2.contracts.envelopes import utc_now
from app.v2.contracts.interactions import (
    InspectorCaseInteractionViewV1,
    InspectorVisibleReviewSignalsV1,
)
from app.v2.contracts.projections import InspectorCaseViewProjectionV1
from nucleo.inspetor.referencias_mensagem import extrair_referencia_do_texto


def _is_open_pendency(item: InspectorCaseInteractionViewV1) -> bool:
    return str(item.pendency_state or "").strip().lower() == "open"


def _is_resolved_pendency(item: InspectorCaseInteractionViewV1) -> bool:
    return str(item.pendency_state or "").strip().lower() == "resolved"


class AndroidCaseFeedAdapterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseFeedAdapterInputV1"
    contract_version: str = "v1"
    tenant_id: str
    actor_id: str
    actor_role: str
    source_channel: str
    case_id: str | None = None
    thread_id: str | None = None
    legacy_laudo_id: int | None = None
    inspector_projection: InspectorCaseViewProjectionV1
    interactions: list[InspectorCaseInteractionViewV1] = Field(default_factory=list)
    visible_review_signals: InspectorVisibleReviewSignalsV1 | None = None
    case_metadata: dict[str, Any] = Field(default_factory=dict)
    expected_legacy_payload: dict[str, Any] | None = None
    timestamp: Any = Field(default_factory=utc_now)


class AndroidCaseFeedCompatibilitySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseFeedCompatibilitySummaryV1"
    contract_version: str = "v1"
    compatible: bool
    divergences: list[str] = Field(default_factory=list)
    visibility_scope: str = "inspetor_mobile"
    used_projection: bool = False
    timestamp: Any = Field(default_factory=utc_now)


class AndroidCaseFeedItemAdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseFeedItemAdapterResultV1"
    contract_version: str = "v1"
    payload: dict[str, Any]
    compatibility: AndroidCaseFeedCompatibilitySummary


def _message_timestamp(message: MensagemLaudo) -> datetime:
    created_at = getattr(message, "criado_em", None)
    if isinstance(created_at, datetime):
        return created_at
    return utc_now()


def build_inspector_case_interaction_view_from_legacy_message(
    *,
    tenant_id: str,
    case_id: str | None,
    thread_id: str | None,
    message: MensagemLaudo,
) -> InspectorCaseInteractionViewV1:
    reference_message_id, _text = extrair_referencia_do_texto(str(message.conteudo or ""))
    attachments = list(getattr(message, "anexos_mesa", None) or [])
    attachments_payload = serializar_anexos_mesa(attachments, portal="app")
    semantics = build_mesa_message_semantics(
        legacy_message_type=message.tipo,
        resolved_at=getattr(message, "resolvida_em", None),
        is_whisper=bool(getattr(message, "is_whisper", False)),
    )
    actor_role = "unknown"
    if semantics.message_kind in {"inspector_message", "inspector_whisper"}:
        actor_role = "inspetor"
    elif semantics.message_kind == "mesa_pendency":
        actor_role = "mesa"

    if attachments and str(message.conteudo or "").strip():
        content_kind = "mixed"
    elif attachments:
        content_kind = "attachment"
    else:
        content_kind = "text"

    review_feedback_visible = semantics.item_kind == "pendency" and actor_role == "mesa"
    pending_open = semantics.pendency_state == "open"
    pending_resolved = semantics.pendency_state == "resolved"

    return InspectorCaseInteractionViewV1(
        tenant_id=tenant_id,
        case_id=case_id,
        thread_id=thread_id,
        interaction_id=f"interaction:legacy-message:{tenant_id}:{int(message.id)}",
        message_id=int(message.id),
        actor_role=actor_role,
        actor_kind="human" if actor_role in {"inspetor", "mesa"} else "unknown",
        origin_kind="human" if actor_role in {"inspetor", "mesa"} else "system",
        content_kind=content_kind,
        legacy_message_type=str(message.tipo or ""),
        item_kind=semantics.item_kind,
        message_kind=semantics.message_kind,
        pendency_state=semantics.pendency_state,
        text_preview=resumo_mensagem_mesa(
            str(message.conteudo or ""),
            anexos=attachments,
        ),
        content_text=texto_mensagem_mesa_visivel(
            str(message.conteudo or ""),
            anexos=attachments,
        ),
        timestamp=_message_timestamp(message),
        display_date=formatar_data_br(getattr(message, "criado_em", None)),
        sender_id=int(message.remetente_id) if getattr(message, "remetente_id", None) else None,
        client_message_id=str(message.client_message_id) if getattr(message, "client_message_id", None) else None,
        reference_message_id=reference_message_id,
        operational_context=extract_operational_context(message),
        resolved_at=getattr(message, "resolvida_em", None),
        resolved_at_label=(
            formatar_data_br(getattr(message, "resolvida_em", None), incluir_ano=True)
            if getattr(message, "resolvida_em", None)
            else ""
        ),
        resolved_by_name=(
            nome_resolvedor_pendencia(message)
            if getattr(message, "resolvida_por_id", None)
            else ""
        ),
        is_read=bool(getattr(message, "lida", False)),
        has_attachments=bool(attachments),
        attachments=attachments_payload,
        delivery_status="persisted",
        review_feedback_visible=review_feedback_visible,
        review_marker_visible=review_feedback_visible,
        highlight_marker=pending_open,
        redirect_target_message_id=reference_message_id or int(message.id),
        pending_open=pending_open,
        pending_resolved=pending_resolved,
    )


def filter_mobile_visible_interactions(
    *,
    interactions: list[InspectorCaseInteractionViewV1],
    review_visible_to_inspector: bool,
) -> list[InspectorCaseInteractionViewV1]:
    return [
        item
        for item in interactions
        if item.actor_role != "mesa"
        or (review_visible_to_inspector and item.review_feedback_visible)
    ]


def build_inspector_visible_review_signals(
    *,
    interactions: list[InspectorCaseInteractionViewV1],
    projection: InspectorCaseViewProjectionV1,
) -> InspectorVisibleReviewSignalsV1:
    review_visible = bool(projection.payload.get("review_visible_to_inspector"))
    visible_interactions = filter_mobile_visible_interactions(
        interactions=interactions,
        review_visible_to_inspector=review_visible,
    )
    visible_feedback = [
        item
        for item in visible_interactions
        if item.actor_role == "mesa" and item.review_feedback_visible
    ]
    latest_feedback = visible_feedback[-1] if visible_feedback else None
    return InspectorVisibleReviewSignalsV1(
        review_visible_to_inspector=review_visible,
        total_visible_interactions=len(visible_interactions),
        visible_feedback_count=len(visible_feedback),
        open_feedback_count=sum(1 for item in visible_feedback if _is_open_pendency(item)),
        resolved_feedback_count=sum(
            1 for item in visible_feedback if _is_resolved_pendency(item)
        ),
        latest_feedback_message_id=latest_feedback.message_id if latest_feedback is not None else None,
        latest_feedback_at=latest_feedback.timestamp if latest_feedback is not None else None,
    )


def _resolve_updated_at_iso(
    adapter_input: AndroidCaseFeedAdapterInput,
    *,
    visible_interactions: list[InspectorCaseInteractionViewV1],
) -> str:
    if (
        adapter_input.visible_review_signals is None
        or adapter_input.visible_review_signals.review_visible_to_inspector
    ):
        value = str(adapter_input.case_metadata.get("updated_at_iso") or "").strip()
        if value:
            return value
    if visible_interactions:
        return visible_interactions[-1].timestamp.isoformat()
    projection_timestamp = getattr(adapter_input.inspector_projection, "timestamp", None)
    if isinstance(projection_timestamp, datetime):
        return projection_timestamp.isoformat()
    return ""


def _legacy_mobile_feed_payload_from_projection(
    adapter_input: AndroidCaseFeedAdapterInput,
) -> dict[str, Any]:
    projection_payload = adapter_input.inspector_projection.payload
    laudo_card = projection_payload.get("laudo_card")
    laudo_card_context = laudo_card if isinstance(laudo_card, dict) else {}
    expected_payload = (
        adapter_input.expected_legacy_payload
        if isinstance(adapter_input.expected_legacy_payload, dict)
        else {}
    )
    review_visible = bool(
        adapter_input.visible_review_signals is None
        or adapter_input.visible_review_signals.review_visible_to_inspector
    )
    interactions = filter_mobile_visible_interactions(
        interactions=sorted(
            adapter_input.interactions,
            key=lambda item: (
                item.timestamp,
                int(item.message_id or 0),
            ),
        ),
        review_visible_to_inspector=review_visible,
    )
    last_interaction = interactions[-1] if interactions else None
    review_signals = adapter_input.visible_review_signals

    resumo_payload: dict[str, Any] = {
        "atualizado_em": _resolve_updated_at_iso(
            adapter_input,
            visible_interactions=interactions,
        ),
        "total_mensagens": len(interactions),
        "mensagens_nao_lidas": sum(
            1
            for item in interactions
            if item.actor_role == "mesa" and not item.is_read
        ),
        "pendencias_abertas": sum(
            1
            for item in interactions
            if item.actor_role == "mesa" and _is_open_pendency(item)
        ),
        "pendencias_resolvidas": sum(
            1
            for item in interactions
            if item.actor_role == "mesa" and _is_resolved_pendency(item)
        ),
        "ultima_mensagem_id": last_interaction.message_id if last_interaction is not None else None,
        "ultima_mensagem_em": last_interaction.timestamp.isoformat() if last_interaction is not None else "",
        "ultima_mensagem_preview": last_interaction.text_preview if last_interaction is not None else "",
        "ultima_mensagem_tipo": last_interaction.legacy_message_type if last_interaction is not None else "",
        "ultima_mensagem_remetente_id": last_interaction.sender_id if last_interaction is not None else None,
    }
    if last_interaction is not None and last_interaction.client_message_id:
        resumo_payload["ultima_mensagem_client_message_id"] = last_interaction.client_message_id

    payload = {
        "laudo_id": adapter_input.legacy_laudo_id,
        "estado": str(projection_payload.get("legacy_public_state") or "sem_relatorio"),
        "permite_edicao": bool(projection_payload.get("allows_edit")),
        "permite_reabrir": bool(projection_payload.get("allows_reopen")),
        "laudo_card": laudo_card,
        "resumo": resumo_payload,
    }
    lifecycle_top_level_keys = {
        "case_lifecycle_status",
        "case_workflow_mode",
        "active_owner_role",
        "allowed_next_lifecycle_statuses",
        "allowed_lifecycle_transitions",
        "allowed_surface_actions",
    }
    if not expected_payload or lifecycle_top_level_keys.intersection(expected_payload):
        payload.update(
            {
                "case_lifecycle_status": (
                    projection_payload.get("case_lifecycle_status")
                    or laudo_card_context.get("case_lifecycle_status")
                ),
                "case_workflow_mode": (
                    projection_payload.get("case_workflow_mode")
                    or laudo_card_context.get("case_workflow_mode")
                ),
                "active_owner_role": (
                    projection_payload.get("active_owner_role")
                    or laudo_card_context.get("active_owner_role")
                ),
                "allowed_next_lifecycle_statuses": (
                    projection_payload.get("allowed_next_lifecycle_statuses")
                    or laudo_card_context.get("allowed_next_lifecycle_statuses")
                    or []
                ),
                "allowed_lifecycle_transitions": (
                    projection_payload.get("allowed_lifecycle_transitions")
                    or laudo_card_context.get("allowed_lifecycle_transitions")
                    or []
                ),
                "allowed_surface_actions": (
                    projection_payload.get("allowed_surface_actions")
                    or laudo_card_context.get("allowed_surface_actions")
                    or []
                ),
            }
        )

    resumo_payload_raw = payload.get("resumo")
    resumo_update_payload = (
        dict(resumo_payload_raw) if isinstance(resumo_payload_raw, dict) else None
    )
    if (
        resumo_update_payload is not None
        and review_signals is not None
        and not review_signals.review_visible_to_inspector
    ):
        resumo_update_payload["mensagens_nao_lidas"] = 0
        resumo_update_payload["pendencias_abertas"] = 0
        resumo_update_payload["pendencias_resolvidas"] = 0
        payload["resumo"] = resumo_update_payload

    return payload


def adapt_android_case_feed_item(
    *,
    adapter_input: AndroidCaseFeedAdapterInput,
) -> AndroidCaseFeedItemAdapterResult:
    payload = _legacy_mobile_feed_payload_from_projection(adapter_input)
    divergences: list[str] = []

    if adapter_input.actor_role != "inspetor":
        divergences.append("actor_role")

    if any(item.visibility_scope != "inspetor_mobile" for item in adapter_input.interactions):
        divergences.append("visibility_scope")

    if adapter_input.expected_legacy_payload is not None:
        expected_keys = set(adapter_input.expected_legacy_payload.keys())
        actual_keys = set(payload.keys())
        if expected_keys != actual_keys:
            divergences.append("payload_keys")
        for key in sorted(expected_keys | actual_keys):
            if adapter_input.expected_legacy_payload.get(key) != payload.get(key):
                divergences.append(key)

    compatibility = AndroidCaseFeedCompatibilitySummary(
        compatible=not divergences,
        divergences=divergences,
        used_projection=not divergences,
    )

    return AndroidCaseFeedItemAdapterResult(
        payload=payload,
        compatibility=compatibility,
    )


def adapt_inspector_case_view_projection_to_android_feed_item(
    *,
    projection: InspectorCaseViewProjectionV1,
    interactions: list[InspectorCaseInteractionViewV1],
    visible_review_signals: InspectorVisibleReviewSignalsV1 | None = None,
    expected_legacy_payload: dict[str, Any] | None = None,
    case_metadata: dict[str, Any] | None = None,
) -> AndroidCaseFeedItemAdapterResult:
    payload = projection.payload
    return adapt_android_case_feed_item(
        adapter_input=AndroidCaseFeedAdapterInput(
            tenant_id=str(projection.tenant_id),
            actor_id=str(projection.actor_id),
            actor_role=str(projection.actor_role),
            source_channel=str(projection.source_channel),
            case_id=str(projection.case_id or "") or None,
            thread_id=str(projection.thread_id or "") or None,
            legacy_laudo_id=int(payload.get("legacy_laudo_id") or 0) or None,
            inspector_projection=projection,
            interactions=interactions,
            visible_review_signals=visible_review_signals,
            case_metadata=dict(case_metadata or {}),
            expected_legacy_payload=expected_legacy_payload,
        )
    )


__all__ = [
    "AndroidCaseFeedAdapterInput",
    "AndroidCaseFeedCompatibilitySummary",
    "AndroidCaseFeedItemAdapterResult",
    "adapt_android_case_feed_item",
    "adapt_inspector_case_view_projection_to_android_feed_item",
    "filter_mobile_visible_interactions",
    "build_inspector_case_interaction_view_from_legacy_message",
    "build_inspector_visible_review_signals",
]
