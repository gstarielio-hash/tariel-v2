"""Resolucao incremental de binding de template para a facade documental do V2."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from app.domains.chat.catalog_pdf_templates import (
    ResolvedPdfTemplateRef,
    resolve_pdf_template_for_laudo,
)
from app.domains.chat.normalization import codigos_template_compativeis
from app.shared.database import Laudo, TemplateLaudo
from app.v2.acl.technical_case_core import TechnicalCaseStatusSnapshot
from app.v2.document.models import DocumentTemplateBindingRef


def _normalize_optional_int(value: Any) -> int | None:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return None
    return resolved if resolved > 0 else None


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _template_source_kind_from_mode(value: Any) -> str:
    modo_editor = str(value or "").strip().lower()
    if modo_editor == "legado_pdf":
        return "legacy_pdf"
    if modo_editor == "editor_rico":
        return "editor_rico"
    if modo_editor == "docx_word":
        return "docx_word"
    return "unknown"


def _template_source_kind_from_legacy(template: TemplateLaudo | None) -> str:
    return _template_source_kind_from_mode(getattr(template, "modo_editor", None))


def _bool_has_editor_document(template: TemplateLaudo | None) -> bool | None:
    if template is None:
        return None
    return bool(getattr(template, "documento_editor_json", None))


def _bool_has_pdf_base_path(value: Any) -> bool:
    caminho = str(value or "").strip()
    if not caminho:
        return False
    return os.path.isfile(caminho)


def _bool_has_pdf_base(template: TemplateLaudo | None) -> bool | None:
    if template is None:
        return None
    return _bool_has_pdf_base_path(getattr(template, "arquivo_pdf_base", None))


def _pick_active_template(
    banco: Session,
    *,
    tenant_id: int,
    template_key: str,
) -> TemplateLaudo | None:
    codigos = codigos_template_compativeis(template_key)
    if not codigos:
        return None

    candidatos = (
        banco.query(TemplateLaudo)
        .filter(
            TemplateLaudo.empresa_id == tenant_id,
            TemplateLaudo.ativo.is_(True),
            TemplateLaudo.codigo_template.in_(codigos),
        )
        .all()
    )
    if not candidatos:
        return None

    prioridade = {codigo: indice for indice, codigo in enumerate(codigos)}
    candidatos.sort(
        key=lambda item: (
            prioridade.get(str(item.codigo_template or "").strip().lower(), 999),
            -int(item.versao or 0),
            -int(item.id or 0),
        )
    )
    return candidatos[0]


def _resolve_catalog_template_ref(
    banco: Session,
    *,
    tenant_id: int,
    legacy_laudo_id: int,
) -> ResolvedPdfTemplateRef | None:
    laudo = banco.get(Laudo, legacy_laudo_id)
    if laudo is None:
        return None
    if _normalize_optional_int(getattr(laudo, "empresa_id", None)) != tenant_id:
        return None
    return resolve_pdf_template_for_laudo(
        banco=banco,
        empresa_id=tenant_id,
        laudo=laudo,
        allow_runtime_fallback=False,
        allow_current_binding_lookup=True,
    )


def _build_binding_from_resolved_template_ref(
    *,
    case_snapshot: TechnicalCaseStatusSnapshot,
    template_ref: ResolvedPdfTemplateRef,
    template_key: str | None,
    source_channel: str | None,
) -> DocumentTemplateBindingRef:
    case_ref = case_snapshot.case_ref
    return DocumentTemplateBindingRef(
        tenant_id=str(case_snapshot.tenant_id or "").strip(),
        case_id=case_ref.case_id,
        legacy_laudo_id=case_ref.legacy_laudo_id,
        document_id=case_ref.document_id,
        thread_id=case_ref.thread_id,
        template_id=_normalize_optional_int(template_ref.template_id),
        template_key=_normalize_optional_text(template_ref.codigo_template) or template_key,
        template_version=_normalize_optional_int(template_ref.versao),
        template_source_kind=_template_source_kind_from_mode(template_ref.modo_editor),
        binding_status="bound",
        legacy_template_status=_normalize_optional_text(template_ref.source_kind),
        legacy_template_mode=_normalize_optional_text(template_ref.modo_editor),
        legacy_pdf_base_available=_bool_has_pdf_base_path(template_ref.arquivo_pdf_base),
        legacy_editor_document_present=bool(template_ref.documento_editor_json),
        source_channel=source_channel,
    )


def resolve_document_template_binding(
    *,
    banco: Session | None,
    case_snapshot: TechnicalCaseStatusSnapshot,
    template_key: Any = None,
    source_channel: str | None = None,
) -> DocumentTemplateBindingRef:
    case_ref = case_snapshot.case_ref
    tenant_id = str(case_snapshot.tenant_id or "").strip()
    template_key_text = _normalize_optional_text(template_key)
    template: TemplateLaudo | None = None
    catalog_template_ref: ResolvedPdfTemplateRef | None = None

    tenant_id_int = _normalize_optional_int(case_snapshot.tenant_id)
    legacy_laudo_id = _normalize_optional_int(case_ref.legacy_laudo_id)
    if banco is not None and tenant_id_int is not None and legacy_laudo_id is not None:
        catalog_template_ref = _resolve_catalog_template_ref(
            banco,
            tenant_id=tenant_id_int,
            legacy_laudo_id=legacy_laudo_id,
        )
    if catalog_template_ref is not None:
        return _build_binding_from_resolved_template_ref(
            case_snapshot=case_snapshot,
            template_ref=catalog_template_ref,
            template_key=template_key_text,
            source_channel=source_channel,
        )
    if banco is not None and tenant_id_int is not None and template_key_text:
        template = _pick_active_template(banco, tenant_id=tenant_id_int, template_key=template_key_text)

    return DocumentTemplateBindingRef(
        tenant_id=tenant_id,
        case_id=case_ref.case_id,
        legacy_laudo_id=case_ref.legacy_laudo_id,
        document_id=case_ref.document_id,
        thread_id=case_ref.thread_id,
        template_id=_normalize_optional_int(getattr(template, "id", None)),
        template_key=template_key_text or _normalize_optional_text(getattr(template, "codigo_template", None)),
        template_version=_normalize_optional_int(getattr(template, "versao", None)),
        template_source_kind=_template_source_kind_from_legacy(template),
        binding_status="bound" if template is not None else "not_bound",
        legacy_template_status=_normalize_optional_text(getattr(template, "status_template", None)),
        legacy_template_mode=_normalize_optional_text(getattr(template, "modo_editor", None)),
        legacy_pdf_base_available=_bool_has_pdf_base(template),
        legacy_editor_document_present=_bool_has_editor_document(template),
        source_channel=source_channel,
    )


__all__ = ["resolve_document_template_binding"]
