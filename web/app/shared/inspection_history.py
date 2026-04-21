"""Helpers para clone da ultima inspecao e diff entre emissoes."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.database import ApprovedCaseSnapshot, Laudo

_IDENTITY_PRIORITY_TOKENS = (
    "tag",
    "placa",
    "serial",
    "patrimonio",
    "patrimonio_ativo",
    "codigo",
    "ativo",
    "equipamento",
    "modelo",
    "fabricante",
    "identificacao",
)
_STABLE_SCOPE_TOKENS = (
    "cliente",
    "unidade",
    "local",
    "localizacao",
    "setor",
    "area",
    "ativo",
    "equipamento",
    "identificacao",
    "tag",
    "placa",
    "serial",
    "patrimonio",
    "codigo",
    "modelo",
    "fabricante",
    "nome_inspecao",
    "objetivo",
)
_DYNAMIC_EXCLUDE_TOKENS = (
    "conclus",
    "recomend",
    "nao_conform",
    "irregular",
    "evidenc",
    "foto",
    "imagem",
    "anexo",
    "documento",
    "parecer",
    "status",
    "resultado",
    "veredito",
    "aprov",
    "mesa",
    "assinatura",
    "aprendizado",
    "learning",
)
_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")


def _normalize_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def _normalize_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "sim" if value else "nao"
    text = " ".join(str(value).strip().split())
    return text[:240]


def _tokenize_text(value: Any) -> list[str]:
    normalized = _normalize_key(value)
    if not normalized:
        return []
    tokens: list[str] = []
    for item in _TOKEN_SPLIT_RE.split(normalized):
        if len(item) < 3:
            continue
        if item.isdigit() and len(item) < 4:
            continue
        tokens.append(item)
    return tokens


def _path_contains_any(path_tokens: Iterable[str], candidates: Iterable[str]) -> bool:
    normalized_path = tuple(_normalize_key(token) for token in path_tokens)
    for token in normalized_path:
        if not token:
            continue
        for candidate in candidates:
            candidate_norm = _normalize_key(candidate)
            if candidate_norm and candidate_norm in token:
                return True
    return False


def _should_exclude_path(path_tokens: Iterable[str]) -> bool:
    return _path_contains_any(path_tokens, _DYNAMIC_EXCLUDE_TOKENS)


def _path_is_stable_scope(path_tokens: Iterable[str]) -> bool:
    return _path_contains_any(path_tokens, _STABLE_SCOPE_TOKENS)


def _flatten_compare_payload(
    value: Any,
    *,
    path_tokens: tuple[str, ...] = (),
) -> dict[str, str]:
    if _should_exclude_path(path_tokens):
        return {}

    if isinstance(value, dict):
        flattened: dict[str, str] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            flattened.update(
                _flatten_compare_payload(
                    raw_value,
                    path_tokens=(*path_tokens, key),
                )
            )
        return flattened

    if isinstance(value, list):
        return {}

    if not _path_is_stable_scope(path_tokens):
        return {}

    scalar = _normalize_scalar(value)
    if not scalar:
        return {}
    return {".".join(path_tokens): scalar}


def _sanitize_clone_payload(
    value: Any,
    *,
    path_tokens: tuple[str, ...] = (),
) -> Any:
    if _should_exclude_path(path_tokens):
        return None

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            child = _sanitize_clone_payload(
                raw_value,
                path_tokens=(*path_tokens, key),
            )
            if child in (None, {}, []):
                continue
            if _path_is_stable_scope((*path_tokens, key)) or isinstance(child, dict):
                sanitized[key] = child
        return sanitized or None

    if isinstance(value, list):
        return None

    if not _path_is_stable_scope(path_tokens):
        return None
    scalar = _normalize_scalar(value)
    return value if scalar else None


def _extract_snapshot_form_payload(snapshot: ApprovedCaseSnapshot) -> dict[str, Any]:
    payload = snapshot.laudo_output_snapshot if isinstance(snapshot.laudo_output_snapshot, dict) else {}
    form_data = payload.get("dados_formulario")
    return dict(form_data) if isinstance(form_data, dict) else {}


def build_human_override_summary(laudo: Laudo) -> dict[str, Any] | None:
    report_pack = (
        dict(getattr(laudo, "report_pack_draft_json", None) or {})
        if isinstance(getattr(laudo, "report_pack_draft_json", None), dict)
        else {}
    )
    quality_gates_payload = report_pack.get("quality_gates")
    quality_gates = (
        quality_gates_payload if isinstance(quality_gates_payload, dict) else {}
    )
    latest = quality_gates.get("human_override")
    if not isinstance(latest, dict):
        return None

    history = [
        dict(item)
        for item in list(quality_gates.get("human_override_history") or [])
        if isinstance(item, dict)
    ]
    latest_payload = {
        "scope": str(latest.get("scope") or "quality_gate").strip() or "quality_gate",
        "applied_at": latest.get("applied_at"),
        "actor_user_id": int(latest.get("actor_user_id") or 0) or None,
        "actor_name": _summarize_value(latest.get("actor_name")),
        "reason": _summarize_value(latest.get("reason")),
        "matched_override_cases": [
            str(item).strip()
            for item in list(latest.get("matched_override_cases") or [])
            if str(item).strip()
        ],
        "matched_override_case_labels": [
            _summarize_value(item)
            for item in list(latest.get("matched_override_case_labels") or [])
            if _summarize_value(item)
        ],
        "overrideable_item_ids": [
            str(item).strip()
            for item in list(latest.get("overrideable_item_ids") or [])
            if str(item).strip()
        ],
        "final_validation_mode": _summarize_value(latest.get("final_validation_mode")),
        "responsibility_notice": _summarize_value(latest.get("responsibility_notice")),
    }

    return {
        "count": len(history) or 1,
        "latest": latest_payload,
        "history": history[-5:],
    }


def _build_identity_signature(payload: dict[str, Any] | None) -> dict[str, set[str]]:
    flattened = _flatten_compare_payload(payload or {})
    important: set[str] = set()
    contextual: set[str] = set()
    for path, value in flattened.items():
        tokens = set(_tokenize_text(value))
        if not tokens:
            continue
        path_tokens = tuple(path.split("."))
        if _path_contains_any(path_tokens, _IDENTITY_PRIORITY_TOKENS):
            important.update(tokens)
        else:
            contextual.update(tokens)
    return {
        "important": important,
        "contextual": contextual,
    }


def _score_snapshot_match(
    *,
    current_payload: dict[str, Any] | None,
    snapshot_payload: dict[str, Any] | None,
    technical_tags: list[str] | None = None,
) -> tuple[int, str]:
    current_signature = _build_identity_signature(current_payload)
    if not current_signature["important"] and not current_signature["contextual"]:
        return (0, "family_recency")

    snapshot_signature = _build_identity_signature(snapshot_payload)
    snapshot_signature["important"].update(_tokenize_text(" ".join(technical_tags or [])))

    important_overlap = current_signature["important"] & snapshot_signature["important"]
    contextual_overlap = (
        (current_signature["important"] | current_signature["contextual"])
        & (snapshot_signature["important"] | snapshot_signature["contextual"])
    )
    score = len(important_overlap) * 12 + len(contextual_overlap) * 3
    if important_overlap:
        return (score, "asset_identity")
    if contextual_overlap:
        return (score, "contextual_identity")
    return (0, "family_recency")


def _serialize_snapshot_reference(
    snapshot: ApprovedCaseSnapshot,
    *,
    matched_by: str,
    match_score: int,
) -> dict[str, Any]:
    payload = snapshot.laudo_output_snapshot if isinstance(snapshot.laudo_output_snapshot, dict) else {}
    return {
        "snapshot_id": int(snapshot.id),
        "source_laudo_id": int(snapshot.laudo_id),
        "source_codigo_hash": str(payload.get("codigo_hash") or "") or None,
        "approved_at": snapshot.approved_at,
        "approval_version": int(snapshot.approval_version or 0),
        "document_outcome": str(snapshot.document_outcome or "").strip() or None,
        "matched_by": matched_by,
        "match_score": int(match_score),
    }


def _merge_nested_payloads(
    base: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any] | None:
    base_payload = dict(base or {})
    override_payload = dict(override or {})
    if not base_payload and not override_payload:
        return None

    merged = dict(base_payload)
    for key, value in override_payload.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_nested_payloads(merged.get(key), value) or {}
        else:
            merged[key] = value
    return merged


def _humanize_path(path: str) -> str:
    parts = [part.replace("_", " ").strip() for part in str(path or "").split(".") if part]
    if not parts:
        return "Campo"
    return " / ".join(part[:1].upper() + part[1:] for part in parts)


def _summarize_value(value: str | None) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:96]


def _resolve_diff_block_key(path: str) -> str:
    parts = [part for part in str(path or "").split(".") if part]
    if not parts:
        return "geral"
    return parts[0]


def _summarize_block_change_counts(
    *,
    changed_count: int,
    added_count: int,
    removed_count: int,
) -> str:
    parts: list[str] = []
    if changed_count:
        parts.append(f"{changed_count} alterado(s)")
    if added_count:
        parts.append(f"{added_count} novo(s)")
    if removed_count:
        parts.append(f"{removed_count} removido(s)")
    if not parts:
        return "Sem delta relevante."
    return " | ".join(parts)


def _build_block_diff_highlights(
    highlights: list[dict[str, Any]],
    *,
    limit_blocks: int = 4,
    limit_fields_per_block: int = 3,
    limit_identity_fields: int = 4,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    grouped: dict[str, dict[str, Any]] = {}
    identity_items: list[dict[str, Any]] = []

    for item in highlights:
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        block_key = _resolve_diff_block_key(path)
        block = grouped.setdefault(
            block_key,
            {
                "block_key": block_key,
                "title": _humanize_path(block_key),
                "changed_count": 0,
                "added_count": 0,
                "removed_count": 0,
                "identity_change_count": 0,
                "fields": [],
            },
        )
        change_type = str(item.get("change_type") or "changed").strip().lower()
        if change_type == "added":
            block["added_count"] += 1
        elif change_type == "removed":
            block["removed_count"] += 1
        else:
            block["changed_count"] += 1

        if len(block["fields"]) < max(1, int(limit_fields_per_block)):
            block["fields"].append(item)

        path_tokens = tuple(path.split("."))
        if _path_contains_any(path_tokens, _IDENTITY_PRIORITY_TOKENS):
            block["identity_change_count"] += 1
            if len(identity_items) < max(1, int(limit_identity_fields)):
                identity_items.append(item)

    block_highlights = list(grouped.values())
    for item in block_highlights:
        item["total_changes"] = (
            int(item.get("changed_count") or 0)
            + int(item.get("added_count") or 0)
            + int(item.get("removed_count") or 0)
        )
        item["summary"] = _summarize_block_change_counts(
            changed_count=int(item.get("changed_count") or 0),
            added_count=int(item.get("added_count") or 0),
            removed_count=int(item.get("removed_count") or 0),
        )

    block_highlights.sort(
        key=lambda item: (
            -int(item.get("identity_change_count") or 0),
            -int(item.get("total_changes") or 0),
            str(item.get("title") or "").lower(),
        )
    )
    identity_count = sum(int(item.get("identity_change_count") or 0) for item in block_highlights)
    return (
        block_highlights[: max(1, int(limit_blocks))],
        identity_items,
        identity_count,
    )


def _build_diff_highlights(
    *,
    current_payload: dict[str, Any] | None,
    snapshot_payload: dict[str, Any] | None,
    limit: int = 5,
) -> dict[str, Any]:
    current_map = _flatten_compare_payload(current_payload or {})
    snapshot_map = _flatten_compare_payload(snapshot_payload or {})
    paths = sorted(set(current_map) | set(snapshot_map))

    highlights: list[dict[str, Any]] = []
    changed_count = 0
    added_count = 0
    removed_count = 0

    for path in paths:
        current_value = current_map.get(path)
        previous_value = snapshot_map.get(path)
        if current_value == previous_value:
            continue
        if previous_value is None and current_value is not None:
            change_type = "added"
            added_count += 1
        elif current_value is None and previous_value is not None:
            change_type = "removed"
            removed_count += 1
        else:
            change_type = "changed"
            changed_count += 1
        highlights.append(
            {
                "path": path,
                "label": _humanize_path(path),
                "change_type": change_type,
                "previous_value": _summarize_value(previous_value),
                "current_value": _summarize_value(current_value),
            }
        )

    priority = {"changed": 0, "added": 1, "removed": 2}
    highlights.sort(
        key=lambda item: (
            priority.get(str(item.get("change_type") or ""), 9),
            0
            if _path_contains_any(
                tuple(str(item.get("path") or "").split(".")),
                _IDENTITY_PRIORITY_TOKENS,
            )
            else 1,
            str(item.get("label") or "").lower(),
        )
    )
    total_changes = changed_count + added_count + removed_count
    block_highlights, identity_highlights, identity_change_count = _build_block_diff_highlights(
        highlights,
    )

    summary_parts: list[str] = []
    if changed_count:
        summary_parts.append(f"{changed_count} mudanca(s)")
    if added_count:
        summary_parts.append(f"{added_count} novo(s)")
    if removed_count:
        summary_parts.append(f"{removed_count} removido(s)")

    return {
        "changed_count": changed_count,
        "added_count": added_count,
        "removed_count": removed_count,
        "total_changes": total_changes,
        "identity_change_count": identity_change_count,
        "current_fields_count": len(current_map),
        "reference_fields_count": len(snapshot_map),
        "summary": (
            "Sem diferencas relevantes nos campos estaveis."
            if not summary_parts
            else " | ".join(summary_parts)
        ),
        "highlights": highlights[: max(1, int(limit))],
        "identity_highlights": identity_highlights,
        "block_highlights": block_highlights,
    }


def resolve_latest_reference_snapshot(
    banco: Session,
    *,
    empresa_id: int,
    family_key: str,
    current_payload: dict[str, Any] | None = None,
    exclude_laudo_id: int | None = None,
    candidate_limit: int = 24,
) -> dict[str, Any] | None:
    family_key_normalized = str(family_key or "").strip()
    if not family_key_normalized:
        return None

    query = (
        select(ApprovedCaseSnapshot)
        .where(
            ApprovedCaseSnapshot.empresa_id == int(empresa_id),
            ApprovedCaseSnapshot.family_key == family_key_normalized,
        )
        .order_by(ApprovedCaseSnapshot.approved_at.desc(), ApprovedCaseSnapshot.id.desc())
        .limit(max(1, int(candidate_limit)))
    )
    candidates = list(banco.scalars(query).all())
    if exclude_laudo_id is not None:
        candidates = [item for item in candidates if int(item.laudo_id) != int(exclude_laudo_id)]
    if not candidates:
        return None

    best_snapshot = candidates[0]
    best_score = -1
    best_match_type = "family_recency"

    for snapshot in candidates:
        snapshot_payload = _extract_snapshot_form_payload(snapshot)
        technical_tags = list(snapshot.technical_tags_json or []) if isinstance(snapshot.technical_tags_json, list) else []
        score, match_type = _score_snapshot_match(
            current_payload=current_payload,
            snapshot_payload=snapshot_payload,
            technical_tags=technical_tags,
        )
        if score > best_score:
            best_snapshot = snapshot
            best_score = score
            best_match_type = match_type

    return {
        "snapshot": best_snapshot,
        "matched_by": best_match_type,
        "match_score": max(best_score, 0),
    }


def build_clone_from_last_inspection_seed(
    banco: Session,
    *,
    empresa_id: int,
    family_key: str,
    current_payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    resolved = resolve_latest_reference_snapshot(
        banco,
        empresa_id=empresa_id,
        family_key=family_key,
        current_payload=current_payload,
    )
    if resolved is None:
        return None

    snapshot = resolved["snapshot"]
    snapshot_payload = _extract_snapshot_form_payload(snapshot)
    prefill_payload = _sanitize_clone_payload(snapshot_payload) or {}
    merged_prefill = _merge_nested_payloads(prefill_payload, current_payload) or {}
    prefilled_fields = _flatten_compare_payload(prefill_payload)
    if not merged_prefill and not prefilled_fields:
        return None

    result = _serialize_snapshot_reference(
        snapshot,
        matched_by=str(resolved["matched_by"]),
        match_score=int(resolved["match_score"]),
    )
    result.update(
        {
            "prefill_data": merged_prefill,
            "prefilled_field_count": len(prefilled_fields),
            "prefilled_fields_preview": [
                _humanize_path(path)
                for path in list(prefilled_fields.keys())[:5]
            ],
        }
    )
    return result


def build_inspection_history_summary(
    banco: Session,
    *,
    laudo: Laudo,
    current_payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    family_key = str(getattr(laudo, "catalog_family_key", None) or getattr(laudo, "tipo_template", "") or "").strip()
    if not family_key:
        return None
    human_override_summary = build_human_override_summary(laudo)

    payload_atual = current_payload
    if payload_atual is None and isinstance(getattr(laudo, "dados_formulario", None), dict):
        payload_atual = dict(laudo.dados_formulario or {})

    resolved = resolve_latest_reference_snapshot(
        banco,
        empresa_id=int(laudo.empresa_id),
        family_key=family_key,
        current_payload=payload_atual,
        exclude_laudo_id=int(getattr(laudo, "id", 0) or 0) or None,
    )
    if resolved is None:
        if human_override_summary is None:
            return None
        return {
            "human_override_summary": human_override_summary.get("latest"),
            "human_override_history": human_override_summary.get("history"),
            "human_override_count": int(human_override_summary.get("count") or 0),
        }

    snapshot = resolved["snapshot"]
    snapshot_payload = _extract_snapshot_form_payload(snapshot)
    diff = _build_diff_highlights(
        current_payload=payload_atual,
        snapshot_payload=snapshot_payload,
    )
    result = _serialize_snapshot_reference(
        snapshot,
        matched_by=str(resolved["matched_by"]),
        match_score=int(resolved["match_score"]),
    )
    result["prefilled_field_count"] = len(_flatten_compare_payload(_sanitize_clone_payload(snapshot_payload) or {}))
    result["diff"] = diff
    if human_override_summary is not None:
        result["human_override_summary"] = human_override_summary.get("latest")
        result["human_override_history"] = human_override_summary.get("history")
        result["human_override_count"] = int(human_override_summary.get("count") or 0)
    return result


__all__ = [
    "build_clone_from_last_inspection_seed",
    "build_human_override_summary",
    "build_inspection_history_summary",
]
