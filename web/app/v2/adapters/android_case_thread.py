"""Adapter da conversa detalhada canônica do Inspetor para o payload legado mobile da mesa."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.envelopes import utc_now
from app.v2.contracts.interactions import (
    InspectorCaseConversationViewV1,
    InspectorCaseInteractionViewV1,
    InspectorCaseThreadMessageV1,
    InspectorVisibleReviewSignalsV1,
)
from app.v2.contracts.projections import InspectorCaseViewProjectionV1


def _is_open_pendency(item: InspectorCaseInteractionViewV1 | InspectorCaseThreadMessageV1) -> bool:
    return str(item.pendency_state or "").strip().lower() == "open"


def _is_resolved_pendency(
    item: InspectorCaseInteractionViewV1 | InspectorCaseThreadMessageV1,
) -> bool:
    return str(item.pendency_state or "").strip().lower() == "resolved"


class AndroidCaseThreadAdapterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseThreadAdapterInputV1"
    contract_version: str = "v1"
    tenant_id: str
    actor_id: str
    actor_role: str
    source_channel: str
    case_id: str | None = None
    thread_id: str | None = None
    legacy_laudo_id: int | None = None
    legacy_laudo_context: dict[str, Any] = Field(default_factory=dict)
    provenance_summary: dict[str, Any] | None = None
    inspector_projection: InspectorCaseViewProjectionV1
    conversation: InspectorCaseConversationViewV1
    interactions: list[InspectorCaseInteractionViewV1] = Field(default_factory=list)
    visible_review_signals: InspectorVisibleReviewSignalsV1 | None = None
    case_metadata: dict[str, Any] = Field(default_factory=dict)
    expected_legacy_payload: dict[str, Any] | None = None
    timestamp: Any = Field(default_factory=utc_now)


class AndroidCaseThreadCompatibilitySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseThreadCompatibilitySummaryV1"
    contract_version: str = "v1"
    compatible: bool
    divergences: list[str] = Field(default_factory=list)
    visibility_scope: str = "inspetor_mobile"
    used_projection: bool = False
    message_count: int = 0
    compatible_message_count: int = 0
    timestamp: Any = Field(default_factory=utc_now)


class AndroidCaseThreadMessageAdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseThreadMessageAdapterResultV1"
    contract_version: str = "v1"
    message_id: int | None = None
    payload: dict[str, Any]
    compatibility: AndroidCaseThreadCompatibilitySummary


class AndroidCaseThreadAdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseThreadAdapterResultV1"
    contract_version: str = "v1"
    payload: dict[str, Any]
    message_results: list[AndroidCaseThreadMessageAdapterResult] = Field(default_factory=list)
    compatibility: AndroidCaseThreadCompatibilitySummary


def _sort_interactions(
    interactions: list[InspectorCaseInteractionViewV1],
) -> list[InspectorCaseInteractionViewV1]:
    return sorted(
        interactions,
        key=lambda item: (
            item.timestamp,
            int(item.message_id or 0),
        ),
    )


def build_inspector_case_thread_message_from_interaction(
    *,
    interaction: InspectorCaseInteractionViewV1,
    order_index: int,
    is_delta_item: bool,
) -> InspectorCaseThreadMessageV1:
    payload = interaction.model_dump(mode="python")
    payload.pop("contract_name", None)
    return InspectorCaseThreadMessageV1(
        **payload,
        order_index=order_index,
        cursor_id=interaction.message_id,
        is_delta_item=is_delta_item,
    )


def build_inspector_case_conversation_view(
    *,
    tenant_id: str,
    case_id: str | None,
    thread_id: str | None,
    page_interactions: list[InspectorCaseInteractionViewV1],
    all_interactions: list[InspectorCaseInteractionViewV1],
    sync_mode: str,
    cursor_after_id: int | None,
    next_cursor_id: int | None,
    cursor_last_message_id: int | None,
    has_more: bool,
) -> InspectorCaseConversationViewV1:
    ordered_page = _sort_interactions(page_interactions)
    ordered_all = _sort_interactions(all_interactions)
    thread_messages = [
        build_inspector_case_thread_message_from_interaction(
            interaction=interaction,
            order_index=index,
            is_delta_item=sync_mode == "delta",
        )
        for index, interaction in enumerate(ordered_page)
    ]
    latest_message = ordered_all[-1] if ordered_all else None
    return InspectorCaseConversationViewV1(
        tenant_id=tenant_id,
        case_id=case_id,
        thread_id=thread_id,
        items=thread_messages,
        total_visible_messages=len(ordered_all),
        unread_visible_messages=sum(
            1
            for item in ordered_all
            if item.actor_role == "mesa" and not item.is_read
        ),
        open_feedback_count=sum(
            1
            for item in ordered_all
            if item.actor_role == "mesa" and _is_open_pendency(item)
        ),
        resolved_feedback_count=sum(
            1
            for item in ordered_all
            if item.actor_role == "mesa" and _is_resolved_pendency(item)
        ),
        latest_message_id=latest_message.message_id if latest_message is not None else None,
        latest_message_at=latest_message.timestamp if latest_message is not None else None,
        latest_message_preview=latest_message.text_preview if latest_message is not None else "",
        latest_message_type=latest_message.legacy_message_type if latest_message is not None else "",
        latest_message_sender_id=latest_message.sender_id if latest_message is not None else None,
        latest_message_client_message_id=(
            latest_message.client_message_id if latest_message is not None else None
        ),
        has_more=bool(has_more),
        next_cursor_id=int(next_cursor_id) if next_cursor_id else None,
        cursor_after_id=int(cursor_after_id) if cursor_after_id else None,
        cursor_last_message_id=int(cursor_last_message_id) if cursor_last_message_id else None,
        sync_mode="delta" if sync_mode == "delta" else "full",
    )


def _legacy_thread_message_payload(
    *,
    message: InspectorCaseThreadMessageV1,
    legacy_laudo_id: int | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": message.message_id,
        "laudo_id": legacy_laudo_id,
        "tipo": message.legacy_message_type,
        "item_kind": message.item_kind,
        "message_kind": message.message_kind,
        "pendency_state": message.pendency_state,
        "texto": message.content_text,
        "remetente_id": message.sender_id,
        "data": message.display_date,
        "criado_em_iso": message.timestamp.isoformat() if message.timestamp else "",
        "lida": bool(message.is_read),
        "resolvida_em": message.resolved_at.isoformat() if message.resolved_at else "",
        "resolvida_em_label": message.resolved_at_label,
        "resolvida_por_nome": message.resolved_by_name,
        "entrega_status": message.delivery_status or "persisted",
    }
    if message.client_message_id:
        payload["client_message_id"] = message.client_message_id
    if message.reference_message_id:
        payload["referencia_mensagem_id"] = message.reference_message_id
    if message.operational_context:
        payload["operational_context"] = dict(message.operational_context)
    if message.attachments:
        payload["anexos"] = list(message.attachments)
    return payload


def _collect_divergences(
    expected: Any,
    actual: Any,
    *,
    prefix: str = "",
) -> list[str]:
    divergences: list[str] = []

    if isinstance(expected, dict) and isinstance(actual, dict):
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())
        if expected_keys != actual_keys:
            divergences.append(f"{prefix}.keys" if prefix else "keys")
        for key in sorted(expected_keys | actual_keys):
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key not in expected or key not in actual:
                divergences.append(next_prefix)
                continue
            divergences.extend(
                _collect_divergences(expected[key], actual[key], prefix=next_prefix)
            )
        return divergences

    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            divergences.append(f"{prefix}.length" if prefix else "length")
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            next_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            divergences.extend(
                _collect_divergences(expected_item, actual_item, prefix=next_prefix)
            )
        return divergences

    if expected != actual:
        divergences.append(prefix or "value")
    return divergences


def adapt_android_case_thread_message(
    *,
    message: InspectorCaseThreadMessageV1,
    legacy_laudo_id: int | None,
    expected_legacy_payload: dict[str, Any] | None = None,
) -> AndroidCaseThreadMessageAdapterResult:
    payload = _legacy_thread_message_payload(
        message=message,
        legacy_laudo_id=legacy_laudo_id,
    )
    divergences: list[str] = []

    if message.visibility_scope != "inspetor_mobile":
        divergences.append("visibility_scope")
    if message.actor_role not in {"inspetor", "mesa"}:
        divergences.append("actor_role")

    if expected_legacy_payload is not None:
        divergences.extend(
            _collect_divergences(
                expected_legacy_payload,
                payload,
            )
        )

    compatibility = AndroidCaseThreadCompatibilitySummary(
        compatible=not divergences,
        divergences=divergences,
        used_projection=not divergences,
        message_count=1,
        compatible_message_count=1 if not divergences else 0,
    )

    return AndroidCaseThreadMessageAdapterResult(
        message_id=message.message_id,
        payload=payload,
        compatibility=compatibility,
    )


def _legacy_mobile_thread_payload_from_projection(
    adapter_input: AndroidCaseThreadAdapterInput,
    *,
    message_results: list[AndroidCaseThreadMessageAdapterResult],
) -> dict[str, Any]:
    projection_payload = adapter_input.inspector_projection.payload
    conversation = adapter_input.conversation
    visible_items = [item.payload for item in message_results]
    latest_visible_message: dict[str, Any] | None = visible_items[-1] if visible_items else None
    latest_visible_interaction: dict[str, Any] | None = None
    if latest_visible_message is not None:
        latest_visible_interaction = {
            "message_id": latest_visible_message.get("id"),
            "timestamp": latest_visible_message.get("criado_em_iso"),
            "text_preview": latest_visible_message.get("texto") or "",
            "legacy_message_type": latest_visible_message.get("tipo") or "",
            "sender_id": latest_visible_message.get("remetente_id"),
            "client_message_id": latest_visible_message.get("client_message_id"),
        }
    resumo_payload: dict[str, Any] = {
        "atualizado_em": (
            str(adapter_input.case_metadata.get("updated_at_iso") or "")
            if (
                adapter_input.visible_review_signals is None
                or adapter_input.visible_review_signals.review_visible_to_inspector
            )
            else ""
        )
        or str((latest_visible_interaction or {}).get("timestamp") or ""),
        "total_mensagens": len(visible_items),
        "mensagens_nao_lidas": sum(
            1
            for item in visible_items
            if item.get("tipo") == "humano_eng" and not item.get("lida")
        ),
        "pendencias_abertas": sum(
            1
            for item in visible_items
            if str(item.get("pendency_state") or "").strip().lower() == "open"
        ),
        "pendencias_resolvidas": sum(
            1
            for item in visible_items
            if str(item.get("pendency_state") or "").strip().lower() == "resolved"
        ),
        "ultima_mensagem_id": (latest_visible_interaction or {}).get("message_id"),
        "ultima_mensagem_em": str((latest_visible_interaction or {}).get("timestamp") or ""),
        "ultima_mensagem_preview": str(
            (latest_visible_interaction or {}).get("text_preview") or ""
        ),
        "ultima_mensagem_tipo": str(
            (latest_visible_interaction or {}).get("legacy_message_type") or ""
        ),
        "ultima_mensagem_remetente_id": (latest_visible_interaction or {}).get(
            "sender_id"
        ),
    }
    payload: dict[str, Any] = {
        "laudo_id": adapter_input.legacy_laudo_id,
        "itens": visible_items,
        "cursor_proximo": conversation.next_cursor_id,
        "cursor_ultimo_id": conversation.cursor_last_message_id,
        "tem_mais": conversation.has_more,
        "estado": str(
            projection_payload.get("legacy_public_state")
            or adapter_input.legacy_laudo_context.get("estado")
            or "sem_relatorio"
        ),
        "permite_edicao": bool(projection_payload.get("allows_edit")),
        "permite_reabrir": bool(projection_payload.get("allows_reopen")),
        "laudo_card": projection_payload.get("laudo_card"),
        "resumo": resumo_payload,
        "sync": {
            "modo": conversation.sync_mode,
            "apos_id": conversation.cursor_after_id,
            "cursor_ultimo_id": conversation.cursor_last_message_id,
        },
    }

    if latest_visible_interaction is not None and latest_visible_interaction.get(
        "client_message_id"
    ):
        resumo_payload["ultima_mensagem_client_message_id"] = latest_visible_interaction[
            "client_message_id"
        ]

    if (
        adapter_input.visible_review_signals is not None
        and not adapter_input.visible_review_signals.review_visible_to_inspector
    ):
        resumo_payload["mensagens_nao_lidas"] = 0
        resumo_payload["pendencias_abertas"] = 0
        resumo_payload["pendencias_resolvidas"] = 0

    attachment_policy = adapter_input.legacy_laudo_context.get("attachment_policy")
    if isinstance(attachment_policy, dict):
        payload["attachment_policy"] = attachment_policy

    return payload


def adapt_android_case_thread(
    *,
    adapter_input: AndroidCaseThreadAdapterInput,
) -> AndroidCaseThreadAdapterResult:
    expected_items = []
    if (
        adapter_input.expected_legacy_payload is not None
        and isinstance(adapter_input.expected_legacy_payload.get("itens"), list)
    ):
        expected_items = list(adapter_input.expected_legacy_payload.get("itens") or [])

    review_visible = bool(
        adapter_input.visible_review_signals is None
        or adapter_input.visible_review_signals.review_visible_to_inspector
    )
    ordered_messages = [
        item
        for item in sorted(
            adapter_input.conversation.items,
            key=lambda item: (
                item.order_index,
                item.timestamp,
                int(item.message_id or 0),
            ),
        )
        if item.actor_role != "mesa"
        or (review_visible and item.review_feedback_visible)
    ]
    message_results = [
        adapt_android_case_thread_message(
            message=message,
            legacy_laudo_id=adapter_input.legacy_laudo_id,
            expected_legacy_payload=(
                expected_items[index] if index < len(expected_items) else None
            ),
        )
        for index, message in enumerate(ordered_messages)
    ]
    payload = _legacy_mobile_thread_payload_from_projection(
        adapter_input,
        message_results=message_results,
    )

    divergences: list[str] = []
    if adapter_input.actor_role != "inspetor":
        divergences.append("actor_role")

    if adapter_input.conversation.visibility_scope != "inspetor_mobile":
        divergences.append("conversation_visibility_scope")

    if any(item.visibility_scope != "inspetor_mobile" for item in adapter_input.interactions):
        divergences.append("interaction_visibility_scope")

    if any(not item.compatibility.compatible for item in message_results):
        divergences.append("itens")

    if adapter_input.expected_legacy_payload is not None:
        divergences.extend(
            _collect_divergences(
                adapter_input.expected_legacy_payload,
                payload,
            )
        )

    compatible_message_count = sum(
        1 for item in message_results if item.compatibility.compatible
    )
    compatibility = AndroidCaseThreadCompatibilitySummary(
        compatible=not divergences,
        divergences=divergences,
        used_projection=not divergences,
        message_count=len(message_results),
        compatible_message_count=compatible_message_count,
    )
    return AndroidCaseThreadAdapterResult(
        payload=payload,
        message_results=message_results,
        compatibility=compatibility,
    )


def adapt_inspector_case_view_projection_to_android_thread(
    *,
    projection: InspectorCaseViewProjectionV1,
    conversation: InspectorCaseConversationViewV1,
    interactions: list[InspectorCaseInteractionViewV1],
    visible_review_signals: InspectorVisibleReviewSignalsV1 | None = None,
    expected_legacy_payload: dict[str, Any] | None = None,
    legacy_laudo_context: dict[str, Any] | None = None,
    provenance_summary: dict[str, Any] | None = None,
    case_metadata: dict[str, Any] | None = None,
) -> AndroidCaseThreadAdapterResult:
    payload = projection.payload
    return adapt_android_case_thread(
        adapter_input=AndroidCaseThreadAdapterInput(
            tenant_id=str(projection.tenant_id),
            actor_id=str(projection.actor_id),
            actor_role=str(projection.actor_role),
            source_channel=str(projection.source_channel),
            case_id=str(projection.case_id or "") or None,
            thread_id=str(projection.thread_id or "") or None,
            legacy_laudo_id=int(payload.get("legacy_laudo_id") or 0) or None,
            legacy_laudo_context=dict(legacy_laudo_context or {}),
            provenance_summary=dict(provenance_summary or {}) or None,
            inspector_projection=projection,
            conversation=conversation,
            interactions=interactions,
            visible_review_signals=visible_review_signals,
            case_metadata=dict(case_metadata or {}),
            expected_legacy_payload=expected_legacy_payload,
        )
    )


__all__ = [
    "AndroidCaseThreadAdapterInput",
    "AndroidCaseThreadAdapterResult",
    "AndroidCaseThreadCompatibilitySummary",
    "AndroidCaseThreadMessageAdapterResult",
    "adapt_android_case_thread",
    "adapt_android_case_thread_message",
    "adapt_inspector_case_view_projection_to_android_thread",
    "build_inspector_case_conversation_view",
    "build_inspector_case_thread_message_from_interaction",
]
