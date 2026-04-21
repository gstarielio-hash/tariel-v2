from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from app.domains.admin.platform_settings_console_summary_cards import (
    build_platform_settings_console_summary_cards,
)


def _normalize_datetime_platform_settings_console(
    value: datetime | None,
) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _latest_changed_label(rows: Iterable[Any]) -> str:
    latest: datetime | None = None
    for row in rows:
        candidate = _normalize_datetime_platform_settings_console(
            getattr(row, "atualizado_em", None) or getattr(row, "criado_em", None)
        )
        if candidate is None:
            continue
        if latest is None or candidate > latest:
            latest = candidate
    return latest.strftime("%d/%m/%Y %H:%M UTC") if latest else "Sem mudanças sensíveis"


def _count_active_policies(
    *,
    privacy: dict[str, Any] | None,
    document_hard_gate_enabled: bool,
    durable_evidence_enabled: bool,
    support_exceptional_mode: str,
) -> int:
    privacy_payload = dict(privacy or {})
    active_policies = 0
    if bool(privacy_payload.get("replay_allowed_in_browser")):
        active_policies += 1
    if document_hard_gate_enabled:
        active_policies += 1
    if durable_evidence_enabled:
        active_policies += 1
    if support_exceptional_mode != "disabled":
        active_policies += 1
    return active_policies


def build_platform_settings_console_overview(
    *,
    rows: Iterable[Any],
    privacy: dict[str, Any] | None,
    environment_label: str,
    review_ui_canonical_label: str,
    support_exceptional_mode: str,
    document_hard_gate_enabled: bool,
    durable_evidence_enabled: bool,
) -> list[dict[str, Any]]:
    return build_platform_settings_console_summary_cards(
        environment_label=environment_label,
        latest_changed_label=_latest_changed_label(rows),
        active_policies=_count_active_policies(
            privacy=privacy,
            document_hard_gate_enabled=document_hard_gate_enabled,
            durable_evidence_enabled=durable_evidence_enabled,
            support_exceptional_mode=support_exceptional_mode,
        ),
        review_ui_canonical_label=review_ui_canonical_label,
    )


__all__ = ["build_platform_settings_console_overview"]
