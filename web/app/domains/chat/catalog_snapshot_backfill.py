"""Backfill seguro para snapshots imutaveis de laudos governados."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domains.chat.catalog_pdf_templates import capture_catalog_snapshot_for_laudo
from app.shared.database import Laudo
from app.shared.tenant_report_catalog import (
    build_catalog_selection_token,
    parse_catalog_selection_token,
)
from nucleo.template_laudos import normalizar_codigo_template


_BACKFILL_CAPTURE_REASON = "backfill_current_state"
_BACKFILL_CAPTURE_ACTOR = "script:backfill_laudo_catalog_snapshots"


def _normalize_catalog_key(value: Any, *, max_len: int) -> str | None:
    raw_text = str(value or "").strip()
    if not raw_text:
        return None
    normalized = normalizar_codigo_template(raw_text)[:max_len]
    return normalized or None


def infer_catalog_identity_for_backfill(laudo: Laudo) -> dict[str, str | None]:
    selection_token = str(getattr(laudo, "catalog_selection_token", "") or "").strip().lower() or None
    family_key = _normalize_catalog_key(getattr(laudo, "catalog_family_key", None), max_len=120)
    variant_key = _normalize_catalog_key(getattr(laudo, "catalog_variant_key", None), max_len=80)

    parsed_token = parse_catalog_selection_token(selection_token)
    if parsed_token is not None:
        family_key = family_key or parsed_token[0]
        variant_key = variant_key or parsed_token[1]

    if selection_token is None and family_key and variant_key:
        selection_token = build_catalog_selection_token(family_key, variant_key)

    return {
        "selection_token": selection_token,
        "family_key": family_key,
        "variant_key": variant_key,
    }


def laudo_requires_snapshot_backfill(laudo: Laudo) -> bool:
    identity = infer_catalog_identity_for_backfill(laudo)
    has_catalog_identity = bool(identity["family_key"] or identity["selection_token"])
    if not has_catalog_identity:
        return False
    return not (
        isinstance(getattr(laudo, "catalog_snapshot_json", None), dict)
        and isinstance(getattr(laudo, "pdf_template_snapshot_json", None), dict)
    )


def backfill_laudo_catalog_snapshots(
    banco: Session,
    *,
    empresa_id: int | None = None,
    laudo_ids: list[int] | tuple[int, ...] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    capture_actor: str = _BACKFILL_CAPTURE_ACTOR,
) -> dict[str, Any]:
    query = (
        select(Laudo)
        .where(
            or_(
                Laudo.catalog_snapshot_json.is_(None),
                Laudo.pdf_template_snapshot_json.is_(None),
            )
        )
        .order_by(Laudo.id.asc())
    )
    if empresa_id is not None:
        query = query.where(Laudo.empresa_id == int(empresa_id))
    if laudo_ids:
        normalized_ids = sorted({int(item) for item in laudo_ids if int(item) > 0})
        if normalized_ids:
            query = query.where(Laudo.id.in_(normalized_ids))
    if limit is not None and int(limit) > 0:
        query = query.limit(int(limit))

    laudos = list(banco.scalars(query))
    summary: dict[str, Any] = {
        "dry_run": bool(dry_run),
        "evaluated": 0,
        "eligible": 0,
        "updated": 0,
        "skipped_complete": 0,
        "skipped_without_catalog_identity": 0,
        "updated_ids": [],
        "eligible_ids": [],
    }

    for laudo in laudos:
        summary["evaluated"] += 1
        if not laudo_requires_snapshot_backfill(laudo):
            if isinstance(getattr(laudo, "catalog_snapshot_json", None), dict) and isinstance(
                getattr(laudo, "pdf_template_snapshot_json", None),
                dict,
            ):
                summary["skipped_complete"] += 1
            else:
                summary["skipped_without_catalog_identity"] += 1
            continue

        identity = infer_catalog_identity_for_backfill(laudo)
        if not identity["family_key"]:
            summary["skipped_without_catalog_identity"] += 1
            continue

        summary["eligible"] += 1
        summary["eligible_ids"].append(int(laudo.id))

        if dry_run:
            continue

        if identity["selection_token"] and not getattr(laudo, "catalog_selection_token", None):
            laudo.catalog_selection_token = identity["selection_token"]
        if identity["family_key"] and not getattr(laudo, "catalog_family_key", None):
            laudo.catalog_family_key = identity["family_key"]
        if identity["variant_key"] and not getattr(laudo, "catalog_variant_key", None):
            laudo.catalog_variant_key = identity["variant_key"]

        capture_catalog_snapshot_for_laudo(
            banco=banco,
            laudo=laudo,
            capture_reason=_BACKFILL_CAPTURE_REASON,
            capture_actor=capture_actor,
        )
        banco.flush()
        summary["updated"] += 1
        summary["updated_ids"].append(int(laudo.id))

    return summary


__all__ = [
    "backfill_laudo_catalog_snapshots",
    "infer_catalog_identity_for_backfill",
    "laudo_requires_snapshot_backfill",
]
