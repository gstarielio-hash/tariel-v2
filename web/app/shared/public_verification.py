"""Payloads e utilitarios de verificacao publica por hash."""

from __future__ import annotations

import base64
import io
import os
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.database import ApprovedCaseSnapshot, EmissaoOficialLaudo, Laudo, StatusRevisao
from app.v2.acl.technical_case_core import build_case_status_visual_label


@lru_cache(maxsize=256)
def build_public_verification_qr_png_bytes(payload: str) -> bytes | None:
    qr_payload = str(payload or "").strip()
    if not qr_payload:
        return None
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except Exception:
        return None

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    if hasattr(image, "get_image"):
        image = image.get_image()

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


@lru_cache(maxsize=256)
def build_public_verification_qr_data_uri(payload: str) -> str | None:
    image_bytes = build_public_verification_qr_png_bytes(payload)
    if not image_bytes:
        return None
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _normalized_host() -> str | None:
    host = str(os.getenv("APP_HOST_PUBLICO") or "").strip().rstrip("/")
    if not host:
        return None
    if host.startswith("http://") or host.startswith("https://"):
        return host
    scheme = "http" if host.startswith(("localhost", "127.0.0.1")) else "https"
    return f"{scheme}://{host}"


def _serialize_official_issue_record(record: EmissaoOficialLaudo | None) -> dict[str, Any] | None:
    if record is None:
        return None
    context = record.issue_context_json if isinstance(record.issue_context_json, dict) else {}
    signatory_payload = context.get("signatory_snapshot")
    signatory_snapshot = (
        signatory_payload if isinstance(signatory_payload, dict) else {}
    )
    state = str(getattr(record, "issue_state", "") or "").strip().lower() or "issued"
    state_label = {
        "issued": "Emitido",
        "superseded": "Substituído",
        "revoked": "Revogado",
    }.get(state, state)
    primary_pdf_payload = (
        dict(context.get("primary_pdf_artifact") or {})
        if isinstance(context.get("primary_pdf_artifact"), dict)
        else {}
    )
    return {
        "issue_number": str(getattr(record, "issue_number", "") or "").strip() or None,
        "issue_state": state,
        "issue_state_label": state_label,
        "issued_at": getattr(record, "issued_at", None),
        "signatory_name": str(signatory_snapshot.get("nome") or "").strip() or None,
        "signatory_registration": str(signatory_snapshot.get("registro_profissional") or "").strip() or None,
        "package_sha256": str(getattr(record, "package_sha256", "") or "").strip() or None,
        "primary_pdf_sha256": str(primary_pdf_payload.get("sha256") or "").strip() or None,
        "reissue_of_issue_number": str(context.get("reissue_of_issue_number") or "").strip() or None,
        "reissue_reason_codes": [
            str(item).strip()
            for item in list(context.get("reissue_reason_codes") or [])
            if str(item).strip()
        ],
        "reissue_reason_summary": str(context.get("reissue_reason_summary") or "").strip() or None,
        "superseded_by_issue_number": str(context.get("superseded_by_issue_number") or "").strip() or None,
    }


def _clean_text(value: Any) -> str | None:
    text = " ".join(str(value or "").strip().split())
    return text or None


def _build_public_official_issue_lineage_summary(payload: dict[str, Any] | None) -> str | None:
    source = payload if isinstance(payload, dict) else {}
    reissue_of_issue_number = _clean_text(source.get("reissue_of_issue_number"))
    reissue_reason_summary = _clean_text(source.get("reissue_reason_summary"))
    if not reissue_of_issue_number:
        return None
    if reissue_reason_summary:
        return f"Esta emissão substitui {reissue_of_issue_number}. {reissue_reason_summary}"
    return f"Esta emissão substitui {reissue_of_issue_number}."


def _build_public_catalog_binding_trace(
    *,
    laudo: Laudo,
    latest_snapshot: ApprovedCaseSnapshot | None = None,
    latest_official_issue: EmissaoOficialLaudo | None = None,
) -> dict[str, Any]:
    context = (
        dict(getattr(latest_official_issue, "issue_context_json", None) or {})
        if latest_official_issue is not None and isinstance(getattr(latest_official_issue, "issue_context_json", None), dict)
        else {}
    )
    persisted_trace = dict(context.get("catalog_binding_trace") or {}) if isinstance(context.get("catalog_binding_trace"), dict) else {}
    if persisted_trace:
        return persisted_trace

    snapshot_payload = (
        dict(getattr(latest_snapshot, "laudo_output_snapshot", None) or {})
        if latest_snapshot is not None and isinstance(getattr(latest_snapshot, "laudo_output_snapshot", None), dict)
        else {}
    )
    template_snapshot = (
        dict(getattr(laudo, "pdf_template_snapshot_json", None) or {})
        if isinstance(getattr(laudo, "pdf_template_snapshot_json", None), dict)
        else {}
    )
    template_ref_payload = (
        dict(template_snapshot.get("template_ref") or {})
        if isinstance(template_snapshot.get("template_ref"), dict)
        else dict(template_snapshot or {})
    )
    approved_at = getattr(latest_snapshot, "approved_at", None)
    trace: dict[str, Any] = {
        "selection_token": _clean_text(getattr(laudo, "catalog_selection_token", None)),
        "runtime_template_code": _clean_text(getattr(laudo, "tipo_template", None)),
        "family_key": _clean_text(
            getattr(laudo, "catalog_family_key", None) or snapshot_payload.get("family_key")
        ),
        "family_label": _clean_text(
            getattr(laudo, "catalog_family_label", None) or snapshot_payload.get("family_label")
        ),
        "variant_key": _clean_text(
            getattr(laudo, "catalog_variant_key", None) or snapshot_payload.get("variant_key")
        ),
        "variant_label": _clean_text(
            getattr(laudo, "catalog_variant_label", None) or snapshot_payload.get("variant_label")
        ),
        "approved_snapshot_id": int(getattr(latest_snapshot, "id", 0) or 0) or None,
        "approval_version": int(getattr(latest_snapshot, "approval_version", 0) or 0) or None,
        "approved_at": approved_at.isoformat() if approved_at is not None else None,
        "approved_snapshot_hash": _clean_text(getattr(latest_snapshot, "snapshot_hash", None)),
        "approved_snapshot_codigo_hash": _clean_text(snapshot_payload.get("codigo_hash")),
    }
    if template_ref_payload:
        trace["template_ref"] = {
            "source_kind": _clean_text(template_ref_payload.get("source_kind")),
            "template_id": int(template_ref_payload.get("template_id") or 0) or None,
            "codigo_template": _clean_text(template_ref_payload.get("codigo_template")),
            "versao": int(template_ref_payload.get("versao") or 0) or None,
            "modo_editor": _clean_text(template_ref_payload.get("modo_editor")),
        }
    return trace


def _enum_value_text(value: Any) -> str | None:
    raw_value = getattr(value, "value", value)
    text = str(raw_value or "").strip()
    return text or None


def _build_public_case_status_fields(
    banco: Session | None,
    *,
    laudo: Laudo,
) -> dict[str, str | None]:
    case_lifecycle_status: str | None = None
    active_owner_role: str | None = None

    if banco is not None:
        try:
            from app.domains.chat.laudo_state_helpers import resolver_snapshot_leitura_caso_tecnico

            case_snapshot = resolver_snapshot_leitura_caso_tecnico(banco, laudo)
        except Exception:
            case_snapshot = None

        if case_snapshot is not None:
            case_lifecycle_status = str(case_snapshot.case_lifecycle_status or "").strip() or None
            active_owner_role = str(case_snapshot.active_owner_role or "").strip() or None

    if not case_lifecycle_status or not active_owner_role:
        review_status = _enum_value_text(getattr(laudo, "status_revisao", None)) or ""
        reviewer_id = getattr(laudo, "revisado_por", None)
        has_document_file = bool(_clean_text(getattr(laudo, "nome_arquivo_pdf", None)))
        was_reopened = getattr(laudo, "reaberto_em", None) is not None

        if was_reopened or review_status == StatusRevisao.REJEITADO.value:
            case_lifecycle_status = "devolvido_para_correcao"
        elif has_document_file:
            case_lifecycle_status = "emitido"
        elif review_status == StatusRevisao.APROVADO.value:
            case_lifecycle_status = "aprovado"
        elif review_status == StatusRevisao.AGUARDANDO.value:
            case_lifecycle_status = "em_revisao_mesa" if reviewer_id else "aguardando_mesa"
        elif int(getattr(laudo, "id", 0) or 0) > 0:
            case_lifecycle_status = "laudo_em_coleta"
        else:
            case_lifecycle_status = "analise_livre"

        if case_lifecycle_status in {"aguardando_mesa", "em_revisao_mesa"}:
            active_owner_role = "mesa"
        elif case_lifecycle_status in {"aprovado", "emitido"}:
            active_owner_role = "none"
        else:
            active_owner_role = "inspetor"

    return {
        "case_lifecycle_status": case_lifecycle_status,
        "active_owner_role": active_owner_role,
        "status_visual_label": build_case_status_visual_label(
            lifecycle_status=case_lifecycle_status,
            active_owner_role=active_owner_role,
        ) or None,
    }


def build_public_verification_url(
    *,
    codigo_hash: str,
    base_url: str | None = None,
) -> str:
    codigo_hash_normalized = str(codigo_hash or "").strip()
    path = f"/app/public/laudo/verificar/{codigo_hash_normalized}"
    base = str(base_url or "").strip().rstrip("/")
    if base:
        return f"{base}{path}"
    host = _normalized_host()
    if host:
        return f"{host}{path}"
    return path


def build_public_verification_payload(
    banco: Session | None = None,
    *,
    laudo: Laudo,
    latest_snapshot: ApprovedCaseSnapshot | None = None,
    latest_official_issue: EmissaoOficialLaudo | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    company = getattr(getattr(laudo, "empresa", None), "nome_fantasia", None) or getattr(
        getattr(laudo, "empresa", None), "razao_social", None
    )
    verification_url = build_public_verification_url(
        codigo_hash=str(getattr(laudo, "codigo_hash", "") or ""),
        base_url=base_url,
    )
    qr_image_data_uri = build_public_verification_qr_data_uri(verification_url)
    snapshot_payload = (
        latest_snapshot.laudo_output_snapshot
        if latest_snapshot is not None and isinstance(latest_snapshot.laudo_output_snapshot, dict)
        else {}
    )
    if latest_official_issue is None and banco is not None:
        latest_official_issue = banco.scalar(
            select(EmissaoOficialLaudo)
            .where(
                EmissaoOficialLaudo.laudo_id == int(laudo.id),
                EmissaoOficialLaudo.issue_state == "issued",
            )
            .order_by(EmissaoOficialLaudo.issued_at.desc(), EmissaoOficialLaudo.id.desc())
            .limit(1)
        )
    official_issue_payload = _serialize_official_issue_record(latest_official_issue)
    official_issue_primary_pdf_comparison = None
    if latest_official_issue is not None:
        from app.shared.official_issue_package import build_official_issue_primary_pdf_comparison

        official_issue_primary_pdf_comparison = build_official_issue_primary_pdf_comparison(
            laudo,
            record=latest_official_issue,
        )
    catalog_binding_trace = _build_public_catalog_binding_trace(
        laudo=laudo,
        latest_snapshot=latest_snapshot,
        latest_official_issue=latest_official_issue,
    )
    template_ref_payload = (
        dict(catalog_binding_trace.get("template_ref") or {})
        if isinstance(catalog_binding_trace.get("template_ref"), dict)
        else {}
    )
    case_status_fields = _build_public_case_status_fields(banco, laudo=laudo)
    return {
        "codigo_hash": str(getattr(laudo, "codigo_hash", "") or ""),
        "hash_short": str(getattr(laudo, "codigo_hash", "") or "")[-6:],
        "laudo_id": int(getattr(laudo, "id", 0) or 0) or None,
        "empresa_nome": str(company or "").strip() or None,
        "tipo_template": str(
            catalog_binding_trace.get("runtime_template_code") or getattr(laudo, "tipo_template", "") or ""
        ).strip()
        or None,
        "family_key": str(
            catalog_binding_trace.get("family_key") or getattr(laudo, "catalog_family_key", "") or ""
        ).strip()
        or None,
        "family_label": str(
            catalog_binding_trace.get("family_label") or getattr(laudo, "catalog_family_label", "") or ""
        ).strip()
        or None,
        "variant_key": str(
            catalog_binding_trace.get("variant_key") or getattr(laudo, "catalog_variant_key", "") or ""
        ).strip()
        or None,
        "variant_label": str(
            catalog_binding_trace.get("variant_label") or getattr(laudo, "catalog_variant_label", "") or ""
        ).strip()
        or None,
        "selection_token": str(
            catalog_binding_trace.get("selection_token") or getattr(laudo, "catalog_selection_token", "") or ""
        ).strip()
        or None,
        "template_code": str(template_ref_payload.get("codigo_template") or "").strip() or None,
        "case_lifecycle_status": case_status_fields["case_lifecycle_status"],
        "active_owner_role": case_status_fields["active_owner_role"],
        "status_visual_label": case_status_fields["status_visual_label"],
        "status_revisao": _enum_value_text(getattr(laudo, "status_revisao", None)),
        "status_conformidade": _enum_value_text(getattr(laudo, "status_conformidade", None)),
        "criado_em": getattr(laudo, "criado_em", None),
        "atualizado_em": getattr(laudo, "atualizado_em", None),
        "approved_at": getattr(latest_snapshot, "approved_at", None),
        "approval_version": int(getattr(latest_snapshot, "approval_version", 0) or 0) or None,
        "document_outcome": str(getattr(latest_snapshot, "document_outcome", "") or "").strip() or None,
        "source_status_revisao": _enum_value_text(getattr(latest_snapshot, "source_status_revisao", None)),
        "qr_payload": verification_url,
        "qr_image_data_uri": qr_image_data_uri,
        "verification_url": verification_url,
        "verified": True,
        "approved_snapshot_hash": str(snapshot_payload.get("codigo_hash") or "") or None,
        "official_issue_number": str((official_issue_payload or {}).get("issue_number") or "") or None,
        "official_issue_state": str((official_issue_payload or {}).get("issue_state") or "") or None,
        "official_issue_state_label": str((official_issue_payload or {}).get("issue_state_label") or "") or None,
        "official_issue_issued_at": (official_issue_payload or {}).get("issued_at"),
        "official_issue_signatory_name": str((official_issue_payload or {}).get("signatory_name") or "") or None,
        "official_issue_signatory_registration": str((official_issue_payload or {}).get("signatory_registration") or "") or None,
        "official_issue_package_sha256": str((official_issue_payload or {}).get("package_sha256") or "") or None,
        "official_issue_primary_pdf_sha256": str((official_issue_payload or {}).get("primary_pdf_sha256") or "") or None,
        "official_issue_reissue_of_issue_number": str(
            (official_issue_payload or {}).get("reissue_of_issue_number") or ""
        )
        or None,
        "official_issue_reissue_reason_codes": list(
            (official_issue_payload or {}).get("reissue_reason_codes") or []
        ),
        "official_issue_reissue_reason_summary": str(
            (official_issue_payload or {}).get("reissue_reason_summary") or ""
        )
        or None,
        "official_issue_superseded_by_issue_number": str(
            (official_issue_payload or {}).get("superseded_by_issue_number") or ""
        )
        or None,
        "official_issue_current_pdf_sha256": str(
            (official_issue_primary_pdf_comparison or {}).get("current_sha256") or ""
        )
        or None,
        "official_issue_current_pdf_storage_version": str(
            (official_issue_primary_pdf_comparison or {}).get("current_storage_version") or ""
        )
        or None,
        "official_issue_primary_pdf_diverged": bool((official_issue_primary_pdf_comparison or {}).get("diverged")),
        "official_issue_primary_pdf_comparison_status": str(
            (official_issue_primary_pdf_comparison or {}).get("status") or ""
        )
        or None,
        "catalog_binding_trace": catalog_binding_trace,
        "official_issue_document_integrity_summary": (
            (
                "Documento atual diverge do emitido."
                f" Atual: {official_issue_primary_pdf_comparison.get('current_storage_version') or 'sem versão'}."
            )
            if official_issue_primary_pdf_comparison is not None
            and bool(official_issue_primary_pdf_comparison.get("diverged"))
            else (
                "Documento atual alinhado ao emitido."
                f" Atual: {official_issue_primary_pdf_comparison.get('current_storage_version') or 'sem versão'}."
            )
            if official_issue_primary_pdf_comparison is not None
            and str(official_issue_primary_pdf_comparison.get("status") or "") == "aligned"
            else None
        ),
        "official_issue_lineage_summary": _build_public_official_issue_lineage_summary(official_issue_payload),
    }


def load_public_verification_payload(
    banco: Session,
    *,
    codigo_hash: str,
    base_url: str | None = None,
) -> dict[str, Any] | None:
    codigo_hash_normalized = str(codigo_hash or "").strip()
    if not codigo_hash_normalized:
        return None
    laudo = banco.scalar(
        select(Laudo).where(Laudo.codigo_hash == codigo_hash_normalized).limit(1)
    )
    if laudo is None:
        return None
    latest_snapshot = banco.scalar(
        select(ApprovedCaseSnapshot)
        .where(ApprovedCaseSnapshot.laudo_id == int(laudo.id))
        .order_by(ApprovedCaseSnapshot.approval_version.desc(), ApprovedCaseSnapshot.id.desc())
        .limit(1)
    )
    latest_official_issue = banco.scalar(
        select(EmissaoOficialLaudo)
        .where(
            EmissaoOficialLaudo.laudo_id == int(laudo.id),
            EmissaoOficialLaudo.issue_state == "issued",
        )
        .order_by(EmissaoOficialLaudo.issued_at.desc(), EmissaoOficialLaudo.id.desc())
        .limit(1)
    )
    return build_public_verification_payload(
        banco,
        laudo=laudo,
        latest_snapshot=latest_snapshot,
        latest_official_issue=latest_official_issue,
        base_url=base_url,
    )


__all__ = [
    "build_public_verification_payload",
    "build_public_verification_qr_data_uri",
    "build_public_verification_qr_png_bytes",
    "build_public_verification_url",
    "load_public_verification_payload",
]
