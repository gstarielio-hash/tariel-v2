"""Pacotes compartilhados de anexos e emissão oficial governada."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.paths import WEB_ROOT
from app.domains.chat.laudo_state_helpers import resolver_snapshot_leitura_caso_tecnico
from app.shared.database import (
    AnexoMesa,
    ApprovedCaseSnapshot,
    EmissaoOficialLaudo,
    Laudo,
    SignatarioGovernadoLaudo,
    Usuario,
)
from app.shared.public_verification import build_public_verification_payload
from app.v2.acl.technical_case_core import build_case_status_visual_label

_DOCUMENT_LIKE_REQUIREMENT_KINDS = {"document", "documento", "pack", "attachment", "pdf"}
_SIGNATORY_EXPIRING_SOON_WINDOW = timedelta(days=30)
_FILENAME_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_STORAGE_VERSION_RE = re.compile(r"^v(?P<number>\d{4})$")
_ELIGIBLE_SIGNATORY_STATUSES = {"ready", "expiring_soon"}
_OFFICIAL_ISSUE_FINGERPRINT_SOURCES = {
    "canonical_document",
    "laudo_runtime",
    "report_pack_runtime",
    "ai_draft",
    "mesa_attachment",
}
_ISSUE_STATE_LABELS = {
    "issued": "Emitido",
    "superseded": "Substituído",
    "revoked": "Revogado",
}
_OFFICIAL_ISSUE_REISSUE_REASON_LABELS = {
    "approval_snapshot_updated": "nova aprovação governada",
    "primary_pdf_diverged": "divergência do PDF principal",
    "signatory_changed": "troca de signatário",
    "package_manifest_changed": "mudança no pacote governado",
}


class OfficialIssueConflictError(RuntimeError):
    """Raised when the active official issue changed during a reissue attempt."""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_dt(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _clean_text(value: Any, *, limit: int | None = None) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    if limit is not None and len(text) > limit:
        return f"{text[: max(0, limit - 3)].rstrip()}..."
    return text


def _enum_value_text(value: Any, *, limit: int | None = None) -> str | None:
    raw_value = getattr(value, "value", value)
    return _clean_text(raw_value, limit=limit)


def _sha256_json_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _sha256_file(path: str | None) -> str | None:
    normalized_path = str(path or "").strip()
    if not normalized_path or not os.path.isfile(normalized_path):
        return None
    digest = hashlib.sha256()
    with open(normalized_path, "rb") as arquivo:
        for chunk in iter(lambda: arquivo.read(1024 * 1024), b""):
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _humanize_slug(value: Any) -> str:
    text = str(value or "").strip().replace("-", "_")
    if not text:
        return ""
    return " ".join(part.capitalize() for part in text.split("_") if part)


def _safe_file_name(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    if text:
        text = os.path.basename(text)
    if not text:
        text = fallback
    sanitized = _FILENAME_SANITIZE_RE.sub("_", text).strip("._")
    return sanitized or fallback


def _normalize_key_list(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    else:
        values = list(value or [])
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_text(item)
        if not text:
            continue
        normalized = text.strip().lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _join_human_list(items: list[str]) -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} e {values[1]}"
    return f"{', '.join(values[:-1])} e {values[-1]}"


def _serialize_official_issue_case_snapshot(case_snapshot: Any) -> dict[str, Any]:
    case_status = str(getattr(case_snapshot, "canonical_status", "") or "")
    case_lifecycle_status = str(getattr(case_snapshot, "case_lifecycle_status", "") or "")
    case_workflow_mode = str(getattr(case_snapshot, "workflow_mode", "") or "")
    active_owner_role = str(getattr(case_snapshot, "active_owner_role", "") or "")
    allowed_next_lifecycle_statuses = [
        str(item or "").strip()
        for item in list(getattr(case_snapshot, "allowed_next_lifecycle_statuses", []) or [])
        if str(item or "").strip()
    ]
    allowed_surface_actions = [
        str(item or "").strip()
        for item in list(getattr(case_snapshot, "allowed_surface_actions", []) or [])
        if str(item or "").strip()
    ]
    return {
        "case_status": case_status,
        "case_lifecycle_status": case_lifecycle_status,
        "case_workflow_mode": case_workflow_mode,
        "active_owner_role": active_owner_role,
        "allowed_next_lifecycle_statuses": allowed_next_lifecycle_statuses,
        "allowed_surface_actions": allowed_surface_actions,
        "status_visual_label": build_case_status_visual_label(
            lifecycle_status=case_lifecycle_status,
            active_owner_role=active_owner_role,
        ),
    }


def _case_ready_for_official_issue(case_fields: dict[str, Any]) -> bool:
    return (
        str(case_fields.get("case_lifecycle_status") or "") in {"aprovado", "emitido"}
        and str(case_fields.get("active_owner_role") or "") == "none"
    )


def _document_like_requirements(report_pack_draft: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(report_pack_draft, dict):
        return []
    quality_gates = report_pack_draft.get("quality_gates")
    if not isinstance(quality_gates, dict):
        return []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(list(quality_gates.get("missing_evidence") or []), start=1):
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        if kind not in _DOCUMENT_LIKE_REQUIREMENT_KINDS:
            continue
        code = _clean_text(item.get("code")) or f"requirement_{index}"
        key = f"requirement:{code.lower().replace(' ', '_')}"
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "item_key": key,
                "label": _clean_text(item.get("message"), limit=180) or _humanize_slug(code),
                "category": "required_document",
                "required": True,
                "present": False,
                "source": "report_pack_quality_gate",
                "summary": _clean_text(item.get("message"), limit=280),
                "file_name": None,
                "archive_path": None,
            }
        )
    return result


def load_latest_approved_case_snapshot(
    banco: Session,
    *,
    laudo: Laudo,
) -> ApprovedCaseSnapshot | None:
    return banco.scalar(
        select(ApprovedCaseSnapshot)
        .where(ApprovedCaseSnapshot.laudo_id == int(laudo.id))
        .order_by(ApprovedCaseSnapshot.approval_version.desc(), ApprovedCaseSnapshot.id.desc())
        .limit(1)
    )


def load_active_official_issue_record(
    banco: Session,
    *,
    laudo: Laudo,
) -> EmissaoOficialLaudo | None:
    return banco.scalar(
        select(EmissaoOficialLaudo)
        .where(
            EmissaoOficialLaudo.laudo_id == int(laudo.id),
            EmissaoOficialLaudo.issue_state == "issued",
        )
        .order_by(EmissaoOficialLaudo.issued_at.desc(), EmissaoOficialLaudo.id.desc())
        .limit(1)
    )


def _issue_state_label(value: Any) -> str:
    key = str(value or "").strip().lower()
    return _ISSUE_STATE_LABELS.get(key, _humanize_slug(key) or "Emitido")


def _signatory_snapshot_payload(signatory: SignatarioGovernadoLaudo | None) -> dict[str, Any] | None:
    if signatory is None:
        return None
    status, status_label = _signatory_effective_status(signatory)
    valid_until = _normalize_dt(getattr(signatory, "valid_until", None))
    return {
        "id": int(signatory.id),
        "nome": _clean_text(signatory.nome, limit=160),
        "funcao": _clean_text(signatory.funcao, limit=120),
        "registro_profissional": _clean_text(signatory.registro_profissional, limit=80),
        "valid_until": valid_until.isoformat() if valid_until is not None else None,
        "status": status,
        "status_label": status_label,
    }


def _issued_by_snapshot_payload(usuario: Usuario | None) -> dict[str, Any] | None:
    if usuario is None:
        return None
    return {
        "id": int(usuario.id),
        "nome": _clean_text(getattr(usuario, "nome", None) or getattr(usuario, "nome_completo", None), limit=160),
        "email": _clean_text(getattr(usuario, "email", None), limit=180),
    }


def _load_user(banco: Session, user_id: int | None) -> Usuario | None:
    if user_id is None:
        return None
    return banco.get(Usuario, user_id)


def _artifact_sort_key(item: dict[str, object]) -> str:
    return str(item.get("archive_path") or "")


def _issue_context_primary_pdf_artifact(record: EmissaoOficialLaudo) -> dict[str, Any] | None:
    payload = record.issue_context_json if isinstance(record.issue_context_json, dict) else {}
    artifact = payload.get("primary_pdf_artifact")
    if isinstance(artifact, dict):
        return artifact
    return None


def _parse_storage_version_number(value: Any) -> int | None:
    match = _STORAGE_VERSION_RE.match(str(value or "").strip())
    if match is None:
        return None
    return int(match.group("number"))


def _normalize_primary_pdf_artifact_payload(
    payload: dict[str, Any] | None,
    *,
    laudo: Laudo,
    source_fallback: str,
) -> dict[str, Any] | None:
    source_payload = payload if isinstance(payload, dict) else {}
    file_name = _clean_text(source_payload.get("file_name"), limit=220) or resolve_official_issue_primary_pdf_archive_name(laudo)
    archive_path = _clean_text(source_payload.get("archive_path"), limit=260) or f"documentos/{file_name}"
    storage_path = _clean_text(source_payload.get("storage_path"), limit=600)
    storage_file_name = _clean_text(source_payload.get("storage_file_name"), limit=220)
    if storage_path and not storage_file_name:
        storage_file_name = _clean_text(os.path.basename(storage_path), limit=220)
    sha256 = _clean_text(source_payload.get("sha256"), limit=64)

    storage_version = _clean_text(source_payload.get("storage_version"), limit=32)
    storage_version_number = int(source_payload.get("storage_version_number") or 0) or None
    if storage_version_number is None and storage_version:
        storage_version_number = _parse_storage_version_number(storage_version)
    if storage_path:
        storage_parent_name = Path(storage_path).parent.name
        if not storage_version:
            normalized_storage_version = _clean_text(storage_parent_name, limit=32)
            if _parse_storage_version_number(normalized_storage_version) is not None:
                storage_version = normalized_storage_version
        if storage_version_number is None:
            storage_version_number = _parse_storage_version_number(storage_parent_name)
        if sha256 is None:
            sha256 = _sha256_file(storage_path)

    return {
        "file_name": file_name,
        "archive_path": archive_path,
        "storage_file_name": storage_file_name,
        "storage_path": storage_path,
        "storage_version": storage_version,
        "storage_version_number": storage_version_number,
        "storage_ready": bool(storage_path),
        "present_on_disk": bool(storage_path and os.path.isfile(storage_path)),
        "sha256": sha256,
        "source": _clean_text(source_payload.get("source"), limit=80) or source_fallback,
    }


def resolve_official_issue_primary_pdf_artifact(
    laudo: Laudo,
    *,
    record: EmissaoOficialLaudo | None = None,
) -> dict[str, Any] | None:
    if record is not None:
        persisted_payload = _issue_context_primary_pdf_artifact(record)
        if persisted_payload:
            return _normalize_primary_pdf_artifact_payload(
                persisted_payload,
                laudo=laudo,
                source_fallback="issue_context",
            )

    storage_file_name = os.path.basename(str(getattr(laudo, "nome_arquivo_pdf", "") or "").strip())
    tenant_id = int(getattr(laudo, "empresa_id", 0) or 0)
    laudo_id = int(getattr(laudo, "id", 0) or 0)
    if storage_file_name and tenant_id > 0 and laudo_id > 0:
        storage_root = WEB_ROOT / "storage" / "laudos_emitidos" / f"empresa_{tenant_id}" / f"laudo_{laudo_id}"
        candidates: list[tuple[int, str, Path]] = []
        if storage_root.is_dir():
            for child in storage_root.iterdir():
                if not child.is_dir():
                    continue
                version_number = _parse_storage_version_number(child.name)
                if version_number is None:
                    continue
                candidate_path = child / storage_file_name
                if candidate_path.is_file():
                    candidates.append((version_number, child.name, candidate_path))
        if candidates:
            version_number, version_label, candidate_path = max(candidates, key=lambda item: (item[0], item[1]))
            return _normalize_primary_pdf_artifact_payload(
                {
                    "storage_file_name": storage_file_name,
                    "storage_path": str(candidate_path),
                    "storage_version": version_label,
                    "storage_version_number": version_number,
                    "source": "storage_scan",
                },
                laudo=laudo,
                source_fallback="storage_scan",
            )

    if _clean_text(getattr(laudo, "nome_arquivo_pdf", None)):
        return _normalize_primary_pdf_artifact_payload(
            {"source": "laudo_runtime"},
            laudo=laudo,
            source_fallback="laudo_runtime",
        )
    return None


def build_official_issue_primary_pdf_comparison(
    laudo: Laudo,
    *,
    record: EmissaoOficialLaudo | None = None,
) -> dict[str, Any] | None:
    frozen_artifact = resolve_official_issue_primary_pdf_artifact(laudo, record=record)
    if frozen_artifact is None:
        return None

    current_artifact = resolve_official_issue_primary_pdf_artifact(laudo)
    frozen_sha256 = _clean_text(frozen_artifact.get("sha256"), limit=64)
    current_sha256 = _clean_text((current_artifact or {}).get("sha256"), limit=64)
    comparable = bool(frozen_sha256 and current_sha256)
    diverged = bool(comparable and frozen_sha256 != current_sha256)

    if comparable:
        status = "diverged" if diverged else "aligned"
    elif current_artifact is None:
        status = "current_missing"
    elif bool(current_artifact.get("storage_ready")):
        status = "current_unhashed"
    else:
        status = "unknown"

    return {
        "status": status,
        "comparable": comparable,
        "diverged": diverged,
        "frozen_artifact": frozen_artifact,
        "current_artifact": current_artifact,
        "frozen_sha256": frozen_sha256,
        "current_sha256": current_sha256,
        "current_storage_version": _clean_text((current_artifact or {}).get("storage_version"), limit=32),
        "current_storage_version_number": int((current_artifact or {}).get("storage_version_number") or 0) or None,
    }


def _build_official_issue_reissue_reason_codes(
    *,
    active_record: EmissaoOficialLaudo | None,
    signatory: SignatarioGovernadoLaudo,
    approval_snapshot_id: int | None,
    package_fingerprint_sha256: str,
) -> list[str]:
    if active_record is None:
        return []

    codes: list[str] = []
    current_snapshot_id = int(getattr(active_record, "approval_snapshot_id", 0) or 0) or None
    if current_snapshot_id != int(approval_snapshot_id or 0) or (current_snapshot_id is None) != (approval_snapshot_id is None):
        codes.append("approval_snapshot_updated")

    current_signatory_id = int(getattr(active_record, "signatory_id", 0) or 0) or None
    if current_signatory_id != int(getattr(signatory, "id", 0) or 0):
        codes.append("signatory_changed")

    primary_pdf_comparison = (
        build_official_issue_primary_pdf_comparison(active_record.laudo, record=active_record)
        if getattr(active_record, "laudo", None) is not None
        else None
    )
    if bool((primary_pdf_comparison or {}).get("diverged")):
        codes.append("primary_pdf_diverged")

    fingerprint_changed = str(getattr(active_record, "package_fingerprint_sha256", "") or "").strip() != str(
        package_fingerprint_sha256 or ""
    ).strip()
    if fingerprint_changed and not codes:
        codes.append("package_manifest_changed")

    return _normalize_key_list(codes)


def _build_official_issue_reissue_reason_summary(reason_codes: list[str]) -> str | None:
    labels = [
        str(_OFFICIAL_ISSUE_REISSUE_REASON_LABELS.get(code) or _humanize_slug(code)).strip()
        for code in _normalize_key_list(reason_codes)
    ]
    labels = [item for item in labels if item]
    if not labels:
        return None
    return f"Reemissão motivada por {_join_human_list(labels)}."


def _validate_expected_active_official_issue(
    *,
    active_record: EmissaoOficialLaudo | None,
    expected_active_issue_id: int | None,
    expected_active_issue_number: str | None,
) -> None:
    if expected_active_issue_id is None and not _clean_text(expected_active_issue_number, limit=80):
        return

    if active_record is None:
        raise OfficialIssueConflictError(
            "A emissão oficial ativa mudou antes da reemissão. Recarregue o caso e tente novamente."
        )

    expected_issue_id = int(expected_active_issue_id or 0) or None
    if expected_issue_id is not None and int(getattr(active_record, "id", 0) or 0) != expected_issue_id:
        raise OfficialIssueConflictError(
            "A emissão oficial ativa mudou antes da reemissão. Recarregue o caso e tente novamente."
        )

    expected_issue_number = _clean_text(expected_active_issue_number, limit=80)
    if expected_issue_number and _clean_text(getattr(active_record, "issue_number", None), limit=80) != expected_issue_number:
        raise OfficialIssueConflictError(
            "A emissão oficial ativa mudou antes da reemissão. Recarregue o caso e tente novamente."
        )


def _issue_context_signatory_snapshot(record: EmissaoOficialLaudo) -> dict[str, Any] | None:
    payload = record.issue_context_json if isinstance(record.issue_context_json, dict) else {}
    snapshot = payload.get("signatory_snapshot")
    if isinstance(snapshot, dict):
        return snapshot
    return _signatory_snapshot_payload(record.signatory)


def _issue_context_issued_by_snapshot(record: EmissaoOficialLaudo) -> dict[str, Any] | None:
    payload = record.issue_context_json if isinstance(record.issue_context_json, dict) else {}
    snapshot = payload.get("issued_by_snapshot")
    if isinstance(snapshot, dict):
        return snapshot
    return _issued_by_snapshot_payload(record.issued_by_user)


def build_official_issue_catalog_binding_trace(
    *,
    laudo: Laudo,
    latest_snapshot: ApprovedCaseSnapshot | None = None,
) -> dict[str, Any]:
    catalog_snapshot = (
        dict(getattr(laudo, "catalog_snapshot_json", None) or {})
        if isinstance(getattr(laudo, "catalog_snapshot_json", None), dict)
        else {}
    )
    pdf_template_snapshot = (
        dict(getattr(laudo, "pdf_template_snapshot_json", None) or {})
        if isinstance(getattr(laudo, "pdf_template_snapshot_json", None), dict)
        else {}
    )
    template_ref_payload = (
        dict(pdf_template_snapshot.get("template_ref") or {})
        if isinstance(pdf_template_snapshot.get("template_ref"), dict)
        else dict(pdf_template_snapshot or {})
    )
    latest_snapshot_payload = (
        dict(getattr(latest_snapshot, "laudo_output_snapshot", None) or {})
        if latest_snapshot is not None and isinstance(getattr(latest_snapshot, "laudo_output_snapshot", None), dict)
        else {}
    )
    family_snapshot = dict(catalog_snapshot.get("family") or {}) if isinstance(catalog_snapshot.get("family"), dict) else {}
    variant_snapshot = (
        dict(catalog_snapshot.get("variant") or {}) if isinstance(catalog_snapshot.get("variant"), dict) else {}
    )
    offer_snapshot = dict(catalog_snapshot.get("offer") or {}) if isinstance(catalog_snapshot.get("offer"), dict) else {}
    tenant_release_snapshot = (
        dict(catalog_snapshot.get("tenant_release") or {})
        if isinstance(catalog_snapshot.get("tenant_release"), dict)
        else {}
    )

    approved_at = _normalize_dt(getattr(latest_snapshot, "approved_at", None))
    trace: dict[str, Any] = {
        "selection_token": _clean_text(getattr(laudo, "catalog_selection_token", None), limit=240),
        "runtime_template_code": _clean_text(getattr(laudo, "tipo_template", None), limit=80),
        "family_key": _clean_text(
            getattr(laudo, "catalog_family_key", None) or latest_snapshot_payload.get("family_key") or family_snapshot.get("key"),
            limit=120,
        ),
        "family_label": _clean_text(
            getattr(laudo, "catalog_family_label", None) or latest_snapshot_payload.get("family_label") or family_snapshot.get("label"),
            limit=180,
        ),
        "variant_key": _clean_text(
            getattr(laudo, "catalog_variant_key", None) or latest_snapshot_payload.get("variant_key") or variant_snapshot.get("key"),
            limit=80,
        ),
        "variant_label": _clean_text(
            getattr(laudo, "catalog_variant_label", None)
            or latest_snapshot_payload.get("variant_label")
            or variant_snapshot.get("label"),
            limit=120,
        ),
        "offer_name": _clean_text(offer_snapshot.get("name"), limit=180),
        "tenant_release_status": _clean_text(tenant_release_snapshot.get("status"), limit=32),
        "catalog_snapshot_captured_at": _clean_text(catalog_snapshot.get("captured_at"), limit=80),
        "catalog_snapshot_capture_reason": _clean_text(catalog_snapshot.get("capture_reason"), limit=80),
        "catalog_snapshot_sha256": _sha256_json_payload(catalog_snapshot),
        "pdf_template_snapshot_sha256": _sha256_json_payload(pdf_template_snapshot),
        "approved_snapshot_id": int(getattr(latest_snapshot, "id", 0) or 0) or None,
        "approval_version": int(getattr(latest_snapshot, "approval_version", 0) or 0) or None,
        "approved_at": approved_at.isoformat() if approved_at is not None else None,
        "approved_snapshot_hash": _clean_text(getattr(latest_snapshot, "snapshot_hash", None), limit=64),
        "approved_snapshot_codigo_hash": _clean_text(latest_snapshot_payload.get("codigo_hash"), limit=64),
    }
    if template_ref_payload:
        trace["template_ref"] = {
            "source_kind": _clean_text(template_ref_payload.get("source_kind"), limit=80),
            "template_id": int(template_ref_payload.get("template_id") or 0) or None,
            "codigo_template": _clean_text(template_ref_payload.get("codigo_template"), limit=120),
            "versao": int(template_ref_payload.get("versao") or 0) or None,
            "modo_editor": _clean_text(template_ref_payload.get("modo_editor"), limit=40),
            "has_pdf_base": bool(_clean_text(template_ref_payload.get("arquivo_pdf_base"))),
            "asset_count": len(list(template_ref_payload.get("assets_json") or [])),
        }
    return trace


def serialize_official_issue_record(record: EmissaoOficialLaudo | None) -> dict[str, Any] | None:
    if record is None:
        return None
    signatory_snapshot = _issue_context_signatory_snapshot(record) or {}
    issued_by_snapshot = _issue_context_issued_by_snapshot(record) or {}
    payload = record.issue_context_json if isinstance(record.issue_context_json, dict) else {}
    reissue_reason_codes = _normalize_key_list(payload.get("reissue_reason_codes"))
    primary_pdf_comparison = (
        build_official_issue_primary_pdf_comparison(record.laudo, record=record)
        if getattr(record, "laudo", None) is not None
        else None
    )
    primary_pdf_artifact = (primary_pdf_comparison or {}).get("frozen_artifact")
    return {
        "id": int(record.id),
        "issue_number": _clean_text(record.issue_number, limit=80),
        "issue_state": str(record.issue_state or "issued"),
        "issue_state_label": _issue_state_label(record.issue_state),
        "issued_at": _normalize_dt(getattr(record, "issued_at", None)),
        "superseded_at": _normalize_dt(getattr(record, "superseded_at", None)),
        "package_sha256": _clean_text(record.package_sha256, limit=64),
        "package_fingerprint_sha256": _clean_text(record.package_fingerprint_sha256, limit=64),
        "package_filename": _clean_text(record.package_filename, limit=220),
        "package_storage_path": _clean_text(record.package_storage_path, limit=600),
        "package_storage_ready": bool(_clean_text(record.package_storage_path)),
        "package_size_bytes": int(getattr(record, "package_size_bytes", 0) or 0) or None,
        "verification_hash": _clean_text(record.verification_hash, limit=64),
        "verification_url": _clean_text(record.public_verification_url, limit=400),
        "approval_snapshot_id": int(getattr(record, "approval_snapshot_id", 0) or 0) or None,
        "approval_version": int(payload.get("approval_version") or 0) or None,
        "signatory_name": _clean_text(signatory_snapshot.get("nome"), limit=160),
        "signatory_function": _clean_text(signatory_snapshot.get("funcao"), limit=120),
        "signatory_registration": _clean_text(signatory_snapshot.get("registro_profissional"), limit=80),
        "issued_by_name": _clean_text(issued_by_snapshot.get("nome"), limit=160),
        "primary_pdf_archive_path": _clean_text((primary_pdf_artifact or {}).get("archive_path"), limit=260),
        "primary_pdf_storage_path": _clean_text((primary_pdf_artifact or {}).get("storage_path"), limit=600),
        "primary_pdf_storage_ready": bool((primary_pdf_artifact or {}).get("storage_ready")),
        "primary_pdf_storage_version": _clean_text((primary_pdf_artifact or {}).get("storage_version"), limit=32),
        "primary_pdf_storage_version_number": int((primary_pdf_artifact or {}).get("storage_version_number") or 0)
        or None,
        "primary_pdf_sha256": _clean_text((primary_pdf_artifact or {}).get("sha256"), limit=64),
        "current_primary_pdf_sha256": _clean_text((primary_pdf_comparison or {}).get("current_sha256"), limit=64),
        "current_primary_pdf_storage_version": _clean_text(
            (primary_pdf_comparison or {}).get("current_storage_version"),
            limit=32,
        ),
        "current_primary_pdf_storage_version_number": int(
            (primary_pdf_comparison or {}).get("current_storage_version_number") or 0
        )
        or None,
        "primary_pdf_diverged": bool((primary_pdf_comparison or {}).get("diverged")),
        "primary_pdf_comparison_status": _clean_text((primary_pdf_comparison or {}).get("status"), limit=32),
        "reissue_of_issue_id": int(payload.get("reissue_of_issue_id") or 0) or None,
        "reissue_of_issue_number": _clean_text(payload.get("reissue_of_issue_number"), limit=80),
        "reissue_reason_codes": reissue_reason_codes,
        "reissue_reason_summary": _clean_text(
            payload.get("reissue_reason_summary") or _build_official_issue_reissue_reason_summary(reissue_reason_codes),
            limit=280,
        ),
        "superseded_by_issue_id": int(getattr(record, "superseded_by_issue_id", 0) or 0) or None,
        "superseded_by_issue_number": _clean_text(payload.get("superseded_by_issue_number"), limit=80),
        "superseded_reason_codes": _normalize_key_list(payload.get("superseded_reason_codes")),
        "superseded_reason_summary": _clean_text(payload.get("superseded_reason_summary"), limit=280),
    }


def build_official_issue_fingerprint(
    *,
    laudo: Laudo,
    signatory_id: int,
    approval_snapshot_id: int | None,
    manifest_payload: dict[str, Any],
) -> str:
    artifacts_payload = []
    for item in list(manifest_payload.get("artifacts") or []):
        if not isinstance(item, dict):
            continue
        archive_path = _clean_text(item.get("archive_path"))
        if not archive_path:
            continue
        source = _clean_text(item.get("source"))
        if source not in _OFFICIAL_ISSUE_FINGERPRINT_SOURCES:
            continue
        artifacts_payload.append(
            {
                "archive_path": archive_path,
                "source": source,
                "present": bool(item.get("present")),
                "sha256": _clean_text(item.get("sha256"), limit=64),
            }
        )
    artifacts_payload.sort(key=_artifact_sort_key)
    payload = {
        "laudo_id": int(getattr(laudo, "id", 0) or 0),
        "empresa_id": int(getattr(laudo, "empresa_id", 0) or 0),
        "codigo_hash": _clean_text(getattr(laudo, "codigo_hash", None), limit=64),
        "family_key": _clean_text(getattr(laudo, "catalog_family_key", None), limit=120),
        "case_status": _clean_text(manifest_payload.get("case_status"), limit=40),
        "case_lifecycle_status": _clean_text(manifest_payload.get("case_lifecycle_status"), limit=40),
        "case_workflow_mode": _clean_text(manifest_payload.get("case_workflow_mode"), limit=40),
        "active_owner_role": _clean_text(manifest_payload.get("active_owner_role"), limit=24),
        "allowed_next_lifecycle_statuses": _normalize_key_list(
            manifest_payload.get("allowed_next_lifecycle_statuses")
        ),
        "allowed_surface_actions": _normalize_key_list(manifest_payload.get("allowed_surface_actions")),
        "status_visual_label": _clean_text(manifest_payload.get("status_visual_label"), limit=120),
        "status_conformidade": _enum_value_text(getattr(laudo, "status_conformidade", None), limit=40),
        "approval_snapshot_id": int(approval_snapshot_id or 0) or None,
        "signatory_id": int(signatory_id),
        "artifacts": artifacts_payload,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def resolve_signatory_for_official_issue(
    banco: Session,
    *,
    laudo: Laudo,
    signatory_id: int | None = None,
) -> tuple[SignatarioGovernadoLaudo, dict[str, Any]]:
    summary = build_governed_signatory_summary(banco, laudo=laudo)
    eligible = [
        item
        for item in list(summary.get("signatories") or [])
        if str(item.get("status") or "").strip().lower() in _ELIGIBLE_SIGNATORY_STATUSES
    ]
    if signatory_id is not None:
        selected = next((item for item in eligible if int(item.get("id") or 0) == int(signatory_id)), None)
        if selected is None:
            raise ValueError("O signatário escolhido não está elegível para esta emissão oficial.")
        signatory = banco.get(SignatarioGovernadoLaudo, int(signatory_id))
        if signatory is None or int(getattr(signatory, "tenant_id", 0) or 0) != int(getattr(laudo, "empresa_id", 0) or 0):
            raise ValueError("Signatário governado não encontrado para este tenant.")
        return signatory, selected

    if len(eligible) == 1:
        selected = eligible[0]
        signatory = banco.get(SignatarioGovernadoLaudo, int(selected["id"]))
        if signatory is None:
            raise ValueError("Signatário governado não encontrado para esta emissão.")
        return signatory, selected

    if not eligible:
        raise ValueError("Não existe signatário governado elegível para esta emissão oficial.")
    raise ValueError("Selecione um signatário governado elegível antes de emitir oficialmente.")


def persist_official_issue_record(
    banco: Session,
    *,
    laudo: Laudo,
    signatory: SignatarioGovernadoLaudo,
    issued_by_user_id: int | None,
    package_sha256: str,
    package_fingerprint_sha256: str,
    package_filename: str | None,
    package_storage_path: str | None,
    package_size_bytes: int | None,
    manifest_payload: dict[str, Any] | None,
    primary_pdf_artifact: dict[str, Any] | None,
    verification_url: str | None,
    expected_active_issue_id: int | None = None,
    expected_active_issue_number: str | None = None,
) -> tuple[EmissaoOficialLaudo, bool]:
    latest_snapshot = load_latest_approved_case_snapshot(banco, laudo=laudo)
    active_record = load_active_official_issue_record(banco, laudo=laudo)
    _validate_expected_active_official_issue(
        active_record=active_record,
        expected_active_issue_id=expected_active_issue_id,
        expected_active_issue_number=expected_active_issue_number,
    )
    snapshot_id = int(getattr(latest_snapshot, "id", 0) or 0) or None
    catalog_binding_trace = (
        dict((manifest_payload or {}).get("catalog_binding_trace") or {})
        if isinstance((manifest_payload or {}).get("catalog_binding_trace"), dict)
        else build_official_issue_catalog_binding_trace(laudo=laudo, latest_snapshot=latest_snapshot)
    )
    normalized_primary_pdf_artifact = _normalize_primary_pdf_artifact_payload(
        primary_pdf_artifact,
        laudo=laudo,
        source_fallback="laudo_runtime",
    )
    reissue_reason_codes = _build_official_issue_reissue_reason_codes(
        active_record=active_record,
        signatory=signatory,
        approval_snapshot_id=snapshot_id,
        package_fingerprint_sha256=package_fingerprint_sha256,
    )
    reissue_reason_summary = _build_official_issue_reissue_reason_summary(reissue_reason_codes)

    if (
        active_record is not None
        and str(getattr(active_record, "package_fingerprint_sha256", "") or "").strip() == package_fingerprint_sha256
        and int(getattr(active_record, "signatory_id", 0) or 0) == int(signatory.id)
        and int(getattr(active_record, "approval_snapshot_id", 0) or 0) == int(snapshot_id or 0)
    ):
        if normalized_primary_pdf_artifact is not None:
            issue_context_payload = (
                dict(getattr(active_record, "issue_context_json", None) or {})
                if isinstance(getattr(active_record, "issue_context_json", None), dict)
                else {}
            )
            if issue_context_payload.get("primary_pdf_artifact") != normalized_primary_pdf_artifact:
                issue_context_payload["primary_pdf_artifact"] = normalized_primary_pdf_artifact
                active_record.issue_context_json = issue_context_payload
                banco.flush()
        return active_record, True

    issued_by_user = _load_user(banco, issued_by_user_id)
    now = _now_utc()
    record = EmissaoOficialLaudo(
        laudo_id=int(laudo.id),
        tenant_id=int(getattr(laudo, "empresa_id", 0) or 0),
        approval_snapshot_id=snapshot_id,
        signatory_id=int(signatory.id),
        issued_by_user_id=int(issued_by_user_id or 0) or None,
        superseded_by_issue_id=None,
        issue_number=f"pending-{uuid.uuid4().hex}",
        issue_state="issued",
        issued_at=now,
        superseded_at=None,
        verification_hash=_clean_text(getattr(laudo, "codigo_hash", None), limit=64),
        public_verification_url=_clean_text(verification_url, limit=400),
        package_sha256=str(package_sha256).strip(),
        package_fingerprint_sha256=str(package_fingerprint_sha256).strip(),
        package_filename=_clean_text(package_filename, limit=220),
        package_storage_path=_clean_text(package_storage_path, limit=600),
        package_size_bytes=int(package_size_bytes or 0) or None,
        manifest_json=manifest_payload if isinstance(manifest_payload, dict) else None,
        issue_context_json={
            "approval_version": int(getattr(latest_snapshot, "approval_version", 0) or 0) or None,
            "signatory_snapshot": _signatory_snapshot_payload(signatory),
            "issued_by_snapshot": _issued_by_snapshot_payload(issued_by_user),
            "catalog_binding_trace": catalog_binding_trace,
            "primary_pdf_artifact": normalized_primary_pdf_artifact,
            "reissue_of_issue_id": int(getattr(active_record, "id", 0) or 0) or None,
            "reissue_of_issue_number": _clean_text(getattr(active_record, "issue_number", None), limit=80),
            "reissue_reason_codes": reissue_reason_codes,
            "reissue_reason_summary": reissue_reason_summary,
        },
    )
    banco.add(record)
    banco.flush()

    record.issue_number = f"TAR-{now.strftime('%Y%m%d')}-{int(record.tenant_id):04d}-{int(record.id):06d}"
    if active_record is not None and int(active_record.id) != int(record.id):
        active_record.issue_state = "superseded"
        active_record.superseded_at = now
        active_record.superseded_by_issue_id = int(record.id)
        active_issue_context_payload = (
            dict(getattr(active_record, "issue_context_json", None) or {})
            if isinstance(getattr(active_record, "issue_context_json", None), dict)
            else {}
        )
        active_issue_context_payload["superseded_by_issue_id"] = int(record.id)
        active_issue_context_payload["superseded_by_issue_number"] = record.issue_number
        active_issue_context_payload["superseded_reason_codes"] = reissue_reason_codes
        active_issue_context_payload["superseded_reason_summary"] = reissue_reason_summary
        active_record.issue_context_json = active_issue_context_payload
    banco.flush()
    return record, False


def build_anexo_pack_summary(
    banco: Session,
    *,
    laudo: Laudo,
) -> dict[str, Any]:
    report_pack_draft = laudo.report_pack_draft_json if isinstance(laudo.report_pack_draft_json, dict) else {}
    verification_payload = build_public_verification_payload(banco, laudo=laudo)
    attachments = (
        banco.execute(
            select(AnexoMesa)
            .where(AnexoMesa.laudo_id == int(laudo.id))
            .order_by(AnexoMesa.criado_em.asc(), AnexoMesa.id.asc())
        )
        .scalars()
        .all()
    )
    pdf_file_name = resolve_official_issue_primary_pdf_archive_name(laudo)

    items: list[dict[str, Any]] = [
        {
            "item_key": "pdf_principal",
            "label": "PDF principal emitido",
            "category": "pdf",
            "required": True,
            "present": bool(_clean_text(getattr(laudo, "nome_arquivo_pdf", None))),
            "source": "laudo_runtime",
            "summary": _clean_text(getattr(laudo, "nome_arquivo_pdf", None), limit=180),
            "mime_type": "application/pdf",
            "size_bytes": None,
            "file_name": pdf_file_name,
            "archive_path": f"documentos/{pdf_file_name}",
        },
        {
            "item_key": "verificacao_publica",
            "label": "Verificação pública por hash",
            "category": "verification",
            "required": True,
            "present": bool(_clean_text(verification_payload.get("verification_url"))),
            "source": "public_verification",
            "summary": _clean_text(verification_payload.get("verification_url"), limit=280),
            "mime_type": None,
            "size_bytes": None,
            "file_name": "verificacao_publica.json",
            "archive_path": "metadados/verificacao_publica.json",
        },
    ]
    items.extend(_document_like_requirements(report_pack_draft))

    for attachment in attachments:
        items.append(
            {
                "item_key": f"mesa_attachment:{int(attachment.id)}",
                "label": _clean_text(attachment.nome_original, limit=180) or f"Anexo #{int(attachment.id)}",
                "category": "image" if str(attachment.categoria or "") == "imagem" else "document",
                "required": False,
                "present": True,
                "source": "mesa_attachment",
                "summary": _clean_text(attachment.nome_original, limit=280),
                "mime_type": _clean_text(attachment.mime_type, limit=120),
                "size_bytes": int(getattr(attachment, "tamanho_bytes", 0) or 0),
                "file_name": _safe_file_name(
                    attachment.nome_original or attachment.nome_arquivo,
                    fallback=f"anexo_mesa_{int(attachment.id)}",
                ),
                "archive_path": (
                    "anexos_mesa/"
                    f"{int(attachment.id)}_"
                    f"{_safe_file_name(attachment.nome_original or attachment.nome_arquivo, fallback=f'anexo_mesa_{int(attachment.id)}')}"
                ),
            }
        )

    total_required = sum(1 for item in items if item["required"])
    total_present = sum(1 for item in items if item["present"])
    missing_required = [item for item in items if item["required"] and not item["present"]]
    ready_for_issue = not missing_required

    document_count = sum(
        1 for item in items if item["present"] and item["category"] in {"document", "pdf", "required_document"}
    )
    image_count = sum(1 for item in items if item["present"] and item["category"] == "image")
    virtual_count = sum(1 for item in items if item["category"] in {"verification"})
    delivery_manifest = {
        "bundle_kind": "tariel_pdf_delivery_bundle",
        "delivery_path": "document_view_model_to_editor_to_render",
        "public_payload_mode": "human_validated_pdf",
        "ai_trace_visibility": "internal_audit_only",
        "human_validation_required": True,
        "required_item_keys": [str(item["item_key"]) for item in items if item["required"]],
        "missing_required_item_keys": [
            str(item["item_key"]) for item in items if item["required"] and not item["present"]
        ],
        "present_archive_paths": [
            str(item["archive_path"]) for item in items if item["present"] and item.get("archive_path")
        ],
        "artifact_count": sum(1 for item in items if item["present"]),
        "ready_for_issue": ready_for_issue,
    }

    return {
        "total_items": len(items),
        "total_required": total_required,
        "total_present": total_present,
        "missing_required_count": len(missing_required),
        "document_count": document_count,
        "image_count": image_count,
        "virtual_count": virtual_count,
        "ready_for_issue": ready_for_issue,
        "missing_items": [str(item["label"]) for item in missing_required],
        "items": items,
        "pdf_present": bool(items[0]["present"]),
        "public_verification_present": bool(items[1]["present"]),
        "delivery_manifest": delivery_manifest,
    }


def _trail_status_payload(
    *,
    status: str,
    title: str,
    summary: str,
    recorded_at: datetime | None,
    blocking: bool = False,
) -> dict[str, Any]:
    labels = {
        "ready": "Pronto",
        "attention": "Atenção",
        "blocked": "Bloqueado",
    }
    return {
        "title": title,
        "status": status,
        "status_label": labels.get(status, _humanize_slug(status)),
        "summary": summary,
        "blocking": bool(blocking),
        "recorded_at": recorded_at,
    }


def _build_official_issue_audit_trail(
    *,
    case_fields: dict[str, Any],
    anexo_summary: dict[str, Any],
    signatory_summary: dict[str, Any],
    verification_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    base_recorded_at = (
        _normalize_dt(verification_payload.get("approved_at"))
        or _normalize_dt(verification_payload.get("updated_at"))
        or _normalize_dt(verification_payload.get("created_at"))
    )
    signature_status = str(signatory_summary.get("signature_status") or "").strip().lower()
    status_visual_label = str(case_fields.get("status_visual_label") or "").strip()
    review_ready = _case_ready_for_official_issue(case_fields)

    if review_ready:
        review_event = _trail_status_payload(
            status="ready",
            title="Aprovação governada",
            summary=(
                f"O caso está em {status_visual_label} e liberado para emissão oficial."
                if status_visual_label
                else "A Mesa confirmou o laudo para emissão oficial."
            ),
            recorded_at=base_recorded_at,
        )
    else:
        review_event = _trail_status_payload(
            status="blocked",
            title="Aprovação governada",
            summary=(
                f"O caso está em {status_visual_label} e a emissão oficial continua bloqueada até a aprovação final da Mesa."
                if status_visual_label
                else "A emissão oficial continua bloqueada até a aprovação final da Mesa."
            ),
            recorded_at=base_recorded_at,
            blocking=True,
        )

    pdf_event = _trail_status_payload(
        status="ready" if bool(anexo_summary.get("pdf_present")) else "blocked",
        title="PDF principal",
        summary=(
            "O PDF principal já foi materializado para compor o pacote final."
            if bool(anexo_summary.get("pdf_present"))
            else "O PDF principal ainda não foi materializado."
        ),
        recorded_at=base_recorded_at,
        blocking=not bool(anexo_summary.get("pdf_present")),
    )

    verification_ready = bool(anexo_summary.get("public_verification_present"))
    verification_event = _trail_status_payload(
        status="ready" if verification_ready else "blocked",
        title="Verificação pública",
        summary=(
            "Hash, URL e QR de conferência pública estão prontos."
            if verification_ready
            else "O hash público ainda não está disponível para rastreabilidade externa."
        ),
        recorded_at=base_recorded_at,
        blocking=not verification_ready,
    )

    annex_ready = int(anexo_summary.get("missing_required_count") or 0) <= 0
    annex_event = _trail_status_payload(
        status="ready" if annex_ready else "blocked",
        title="Anexo pack",
        summary=(
            "Todos os anexos obrigatórios foram consolidados para a emissão."
            if annex_ready
            else "Ainda existem anexos obrigatórios pendentes para a emissão oficial."
        ),
        recorded_at=base_recorded_at,
        blocking=not annex_ready,
    )

    if signature_status == "ready":
        signatory_event = _trail_status_payload(
            status="ready",
            title="Signatários governados",
            summary="Há signatário governado elegível para a família deste laudo.",
            recorded_at=base_recorded_at,
        )
    elif signature_status == "attention":
        signatory_event = _trail_status_payload(
            status="attention",
            title="Signatários governados",
            summary="Existe signatário elegível, mas com validade próxima.",
            recorded_at=base_recorded_at,
        )
    else:
        signatory_event = _trail_status_payload(
            status="blocked",
            title="Signatários governados",
            summary="Não existe signatário elegível configurado para esta emissão.",
            recorded_at=base_recorded_at,
            blocking=True,
        )

    return [
        {"event_key": "review_approval", **review_event},
        {"event_key": "primary_pdf", **pdf_event},
        {"event_key": "public_verification", **verification_event},
        {"event_key": "annex_pack", **annex_event},
        {"event_key": "governed_signatory", **signatory_event},
    ]


def _signatory_effective_status(signatory: SignatarioGovernadoLaudo) -> tuple[str, str]:
    if not bool(getattr(signatory, "ativo", False)):
        return "inactive", "Inativo"
    valid_until = _normalize_dt(getattr(signatory, "valid_until", None))
    if valid_until is not None and valid_until < _now_utc():
        return "expired", "Validade expirada"
    if valid_until is not None and valid_until <= (_now_utc() + _SIGNATORY_EXPIRING_SOON_WINDOW):
        return "expiring_soon", "Validade próxima"
    return "ready", "Pronto para emissão"


def build_governed_signatory_summary(
    banco: Session,
    *,
    laudo: Laudo,
) -> dict[str, Any]:
    family_key = str(getattr(laudo, "catalog_family_key", "") or getattr(laudo, "tipo_template", "") or "").strip().lower()
    signatories = (
        banco.execute(
            select(SignatarioGovernadoLaudo)
            .where(SignatarioGovernadoLaudo.tenant_id == int(laudo.empresa_id))
            .order_by(SignatarioGovernadoLaudo.ativo.desc(), SignatarioGovernadoLaudo.nome.asc())
        )
        .scalars()
        .all()
    )

    compatible_items: list[dict[str, Any]] = []
    eligible_count = 0
    expiring_count = 0
    for signatory in signatories:
        allowed_family_keys = _normalize_key_list(getattr(signatory, "allowed_family_keys_json", None))
        compatible = not allowed_family_keys or family_key in allowed_family_keys
        if not compatible:
            continue
        status, status_label = _signatory_effective_status(signatory)
        if status == "ready":
            eligible_count += 1
        elif status == "expiring_soon":
            eligible_count += 1
            expiring_count += 1
        compatible_items.append(
            {
                "id": int(signatory.id),
                "nome": _clean_text(signatory.nome, limit=160) or f"Signatário #{int(signatory.id)}",
                "funcao": _clean_text(signatory.funcao, limit=120) or "Responsável técnico",
                "registro_profissional": _clean_text(signatory.registro_profissional, limit=80),
                "valid_until": _normalize_dt(getattr(signatory, "valid_until", None)),
                "status": status,
                "status_label": status_label,
                "ativo": bool(getattr(signatory, "ativo", False)),
                "allowed_family_keys": allowed_family_keys,
                "observacoes": _clean_text(getattr(signatory, "observacoes", None), limit=280),
            }
        )

    if not compatible_items:
        signature_status = "not_configured"
        signature_status_label = "Sem signatário governado"
    elif eligible_count <= 0:
        signature_status = "blocked"
        signature_status_label = "Sem signatário elegível"
    elif expiring_count > 0:
        signature_status = "attention"
        signature_status_label = "Signatário com validade próxima"
    else:
        signature_status = "ready"
        signature_status_label = "Signatário governado pronto"

    return {
        "compatible_signatory_count": len(compatible_items),
        "eligible_signatory_count": eligible_count,
        "signature_status": signature_status,
        "signature_status_label": signature_status_label,
        "signatories": compatible_items,
    }


def build_official_issue_summary(
    banco: Session,
    *,
    laudo: Laudo,
    anexo_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    anexo_summary = anexo_pack or build_anexo_pack_summary(banco, laudo=laudo)
    signatory_summary = build_governed_signatory_summary(banco, laudo=laudo)
    verification_payload = build_public_verification_payload(banco, laudo=laudo)
    case_fields = _serialize_official_issue_case_snapshot(
        resolver_snapshot_leitura_caso_tecnico(banco, laudo)
    )
    review_ready = _case_ready_for_official_issue(case_fields)
    blockers: list[dict[str, Any]] = []

    if not review_ready:
        blockers.append(
            {
                "code": "review_not_approved",
                "title": "Aprovação final pendente",
                "message": (
                    f"A emissão oficial só fica pronta depois da aprovação governada do laudo. Estado atual: {case_fields['status_visual_label']}."
                    if case_fields["status_visual_label"]
                    else "A emissão oficial só fica pronta depois da aprovação governada do laudo."
                ),
                "blocking": True,
            }
        )
    if not bool(anexo_summary.get("pdf_present")):
        blockers.append(
            {
                "code": "missing_pdf",
                "title": "PDF principal ausente",
                "message": "O PDF principal ainda não foi materializado para a emissão oficial.",
                "blocking": True,
            }
        )
    if not bool(anexo_summary.get("public_verification_present")):
        blockers.append(
            {
                "code": "missing_public_verification",
                "title": "Verificação pública ausente",
                "message": "O hash e a URL pública de conferência ainda não estão prontos para a emissão.",
                "blocking": True,
            }
        )
    if int(anexo_summary.get("missing_required_count") or 0) > 0:
        blockers.append(
            {
                "code": "annex_pack_incomplete",
                "title": "Anexo pack incompleto",
                "message": "Ainda existem anexos obrigatórios pendentes antes da emissão oficial.",
                "blocking": True,
            }
        )
    if int(signatory_summary.get("eligible_signatory_count") or 0) <= 0:
        blockers.append(
            {
                "code": "no_eligible_signatory",
                "title": "Sem signatário elegível",
                "message": "Configure ao menos um signatário ativo e válido compatível com a família deste laudo.",
                "blocking": True,
            }
        )

    ready_for_issue = not blockers
    issue_status = "ready_for_issue"
    issue_status_label = "Pronto para emissão oficial"
    if not ready_for_issue:
        if not review_ready:
            issue_status = "awaiting_approval"
            issue_status_label = "Aguardando aprovação final"
        else:
            issue_status = "governance_blocked"
            issue_status_label = "Bloqueado por governança"

    latest_snapshot = load_latest_approved_case_snapshot(banco, laudo=laudo)
    current_record = load_active_official_issue_record(banco, laudo=laudo)
    current_issue = serialize_official_issue_record(current_record)
    already_issued = current_issue is not None
    snapshot_reissue_recommended = bool(
        current_record is not None
        and latest_snapshot is not None
        and int(getattr(current_record, "approval_snapshot_id", 0) or 0) != int(latest_snapshot.id)
    )
    current_primary_pdf_comparison = (
        build_official_issue_primary_pdf_comparison(laudo, record=current_record)
        if current_record is not None
        else None
    )
    document_reissue_recommended = bool((current_primary_pdf_comparison or {}).get("diverged"))
    reissue_recommended = bool(snapshot_reissue_recommended or document_reissue_recommended)

    audit_trail = _build_official_issue_audit_trail(
        case_fields=case_fields,
        anexo_summary=anexo_summary,
        signatory_summary=signatory_summary,
        verification_payload=verification_payload,
    )
    if current_issue is not None:
        reissue_origin_number = _clean_text(current_issue.get("reissue_of_issue_number"), limit=80)
        reissue_reason_summary = _clean_text(current_issue.get("reissue_reason_summary"), limit=280)
        if not review_ready:
            current_event = _trail_status_payload(
                status="attention",
                title="Emissão oficial ativa",
                summary=(
                    f"A emissão {current_issue['issue_number']} permanece congelada no histórico, "
                    f"mas o caso atual está em {case_fields['status_visual_label']} e exige nova aprovação antes de nova emissão."
                    if case_fields["status_visual_label"]
                    else (
                        f"A emissão {current_issue['issue_number']} permanece congelada no histórico, "
                        "mas o caso atual exige nova aprovação antes de nova emissão."
                    )
                ),
                recorded_at=_normalize_dt(current_issue.get("issued_at")),
            )
        elif reissue_recommended:
            issue_status = "reissue_recommended"
            issue_status_label = "Reemissão recomendada"
            current_event = _trail_status_payload(
                status="attention",
                title="Emissão oficial ativa",
                summary=(
                    (
                        f"A emissão {current_issue['issue_number']} permanece registrada, "
                        "mas uma nova aprovação e a divergência do PDF atual pedem reemissão do pacote oficial."
                    )
                    if snapshot_reissue_recommended and document_reissue_recommended
                    else (
                        f"A emissão {current_issue['issue_number']} permanece registrada, "
                        "mas uma nova aprovação pede reemissão do pacote oficial."
                    )
                    if snapshot_reissue_recommended
                    else (
                        f"A emissão {current_issue['issue_number']} permanece registrada, "
                        "mas o PDF atual do caso divergiu do documento emitido e pede reemissão do pacote oficial."
                    )
                ),
                recorded_at=_normalize_dt(current_issue.get("issued_at")),
            )
        else:
            issue_status = "issued_officially"
            issue_status_label = "Emitido oficialmente"
            current_event = _trail_status_payload(
                status="ready",
                title="Emissão oficial ativa",
                summary=(
                    f"A emissão {current_issue['issue_number']} substituiu {reissue_origin_number} "
                    f"e está congelada e válida no storage oficial. {reissue_reason_summary}"
                    if reissue_origin_number and reissue_reason_summary
                    else (
                        f"A emissão {current_issue['issue_number']} substituiu {reissue_origin_number} "
                        "e está congelada e válida no storage oficial."
                    )
                    if reissue_origin_number
                    else f"A emissão {current_issue['issue_number']} está congelada e válida no storage oficial."
                ),
                recorded_at=_normalize_dt(current_issue.get("issued_at")),
            )
        audit_trail.insert(0, {"event_key": "official_issue_record", **current_event})
        if current_primary_pdf_comparison is not None and bool(current_primary_pdf_comparison.get("comparable")):
            document_integrity_event = _trail_status_payload(
                status="attention" if bool(current_primary_pdf_comparison.get("diverged")) else "ready",
                title="Integridade do documento emitido",
                summary=(
                    (
                        "O PDF atual do caso divergiu do documento congelado na emissão oficial."
                        f" Emitido: {current_primary_pdf_comparison['frozen_artifact'].get('storage_version') or 'sem versão'}"
                        f" · Atual: {current_primary_pdf_comparison.get('current_storage_version') or 'sem versão'}."
                    )
                    if bool(current_primary_pdf_comparison.get("diverged"))
                    else (
                        "O PDF atual do caso permanece alinhado ao documento congelado na emissão oficial."
                        f" Versão atual: {current_primary_pdf_comparison.get('current_storage_version') or 'sem versão'}."
                    )
                ),
                recorded_at=_normalize_dt(current_issue.get("issued_at")),
            )
            audit_trail.insert(1, {"event_key": "official_issue_document_integrity", **document_integrity_event})

    return {
        **case_fields,
        "issue_status": issue_status,
        "issue_status_label": issue_status_label,
        "ready_for_issue": ready_for_issue,
        "requires_human_signature": True,
        "compatible_signatory_count": int(signatory_summary.get("compatible_signatory_count") or 0),
        "eligible_signatory_count": int(signatory_summary.get("eligible_signatory_count") or 0),
        "blocker_count": len(blockers),
        "signature_status": signatory_summary.get("signature_status"),
        "signature_status_label": signatory_summary.get("signature_status_label"),
        "verification_url": _clean_text(verification_payload.get("verification_url"), limit=400),
        "pdf_present": bool(anexo_summary.get("pdf_present")),
        "public_verification_present": bool(anexo_summary.get("public_verification_present")),
        "signatories": list(signatory_summary.get("signatories") or []),
        "blockers": blockers,
        "audit_trail": audit_trail,
        "delivery_manifest": dict(anexo_summary.get("delivery_manifest") or {}),
        "already_issued": already_issued,
        "reissue_recommended": reissue_recommended,
        "issue_action_label": "Reemitir oficialmente" if already_issued else "Emitir oficialmente",
        "issue_action_enabled": ready_for_issue and int(signatory_summary.get("eligible_signatory_count") or 0) > 0,
        "current_issue": current_issue,
    }


def build_official_issue_package(
    banco: Session,
    *,
    laudo: Laudo,
) -> tuple[dict[str, Any], dict[str, Any]]:
    anexo_pack = build_anexo_pack_summary(banco, laudo=laudo)
    emissao_oficial = build_official_issue_summary(
        banco,
        laudo=laudo,
        anexo_pack=anexo_pack,
    )
    return anexo_pack, emissao_oficial


def resolve_official_issue_primary_pdf_archive_name(laudo: Laudo) -> str:
    return _safe_file_name(
        getattr(laudo, "nome_arquivo_pdf", None),
        fallback=f"laudo_{str(getattr(laudo, 'codigo_hash', '') or 'tariel')[:12]}.pdf",
    )


__all__ = [
    "OfficialIssueConflictError",
    "build_anexo_pack_summary",
    "build_governed_signatory_summary",
    "build_official_issue_fingerprint",
    "build_official_issue_package",
    "build_official_issue_catalog_binding_trace",
    "build_official_issue_primary_pdf_comparison",
    "build_official_issue_summary",
    "load_active_official_issue_record",
    "load_latest_approved_case_snapshot",
    "persist_official_issue_record",
    "resolve_official_issue_primary_pdf_artifact",
    "resolve_official_issue_primary_pdf_archive_name",
    "resolve_signatory_for_official_issue",
    "serialize_official_issue_record",
]
