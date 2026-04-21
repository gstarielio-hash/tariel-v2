"""Resolucao catalog-aware de templates PDF por familia governada."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.paths import resolve_family_schemas_dir
from app.domains.chat.catalog_document_view_model import (
    build_catalog_document_view_model,
    build_universal_document_editor,
)
from app.domains.chat.catalog_document_contract import (
    build_document_contract_payload,
    build_document_control_payload,
    build_document_delivery_package_payload,
    build_runtime_brand_assets,
    build_tenant_branding_payload,
)
from app.domains.chat.normalization import normalizar_tipo_template
from app.domains.chat.template_helpers import selecionar_template_ativo_para_tipo
from app.shared.tenant_report_catalog import build_catalog_selection_token
from app.shared.database import (
    FamiliaLaudoCatalogo,
    Laudo,
    TemplateLaudo,
    TenantFamilyReleaseLaudo,
)
from nucleo.template_editor_word import (
    MODO_EDITOR_RICO,
    documento_editor_padrao,
    estilo_editor_padrao,
    normalizar_documento_editor,
    normalizar_estilo_editor,
    normalizar_modo_editor,
)
from nucleo.template_laudos import normalizar_codigo_template
from nucleo.template_laudos import normalizar_mapeamento_campos


@dataclass(slots=True)
class ResolvedPdfTemplateRef:
    source_kind: str
    family_key: str | None
    template_id: int | None
    codigo_template: str
    versao: int
    modo_editor: str
    arquivo_pdf_base: str
    documento_editor_json: dict[str, Any]
    estilo_json: dict[str, Any]
    assets_json: list[dict[str, Any]]
    mapeamento_campos_json: dict[str, Any] = field(default_factory=dict)


RENDER_MODE_TEMPLATE_PREVIEW_BLANK = "template_preview_blank"
RENDER_MODE_CLIENT_PDF_FILLED = "client_pdf_filled"
RENDER_MODE_ADMIN_PDF = "admin_pdf"

_VALID_RENDER_MODES = {
    RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    RENDER_MODE_CLIENT_PDF_FILLED,
    RENDER_MODE_ADMIN_PDF,
}

_CATALOG_SNAPSHOT_VERSION = 1
_PDF_TEMPLATE_SNAPSHOT_VERSION = 1

_BLANK_PREVIEW_KEEP_PREFIXES: tuple[str, ...] = (
    "schema_type",
    "schema_version",
    "family_key",
    "template_code",
    "document_contract",
    "document_control.document_code",
    "document_control.revision",
    "document_control.title",
    "document_control.master_template_id",
    "document_control.master_template_label",
    "document_projection",
    "render_mode",
    "tokens.documento_codigo",
    "tokens.documento_revisao",
    "tokens.documento_titulo",
    "tokens.documento_tipo_mestre",
    "tokens.revisao_template",
)

_BLANK_PREVIEW_DROP_PREFIXES: tuple[str, ...] = (
    "analysis_basis",
    "mesa_review",
    "telemetry",
    "binding",
    "debug",
    "governanca",
    "governance",
    "contract",
)

def _family_schemas_dir() -> Path:
    return resolve_family_schemas_dir()


def _family_artifact_file_path(family_key: str, artifact_suffix: str) -> Path:
    family_key_norm = normalizar_codigo_template(str(family_key or "").strip().lower())[:120]
    return (_family_schemas_dir() / f"{family_key_norm}{artifact_suffix}").resolve()


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _load_family_template_seed(family_key: str) -> dict[str, Any] | None:
    return _read_json_file(_family_artifact_file_path(family_key, ".template_master_seed.json"))


def _load_family_output_seed(family_key: str) -> dict[str, Any] | None:
    return _read_json_file(_family_artifact_file_path(family_key, ".laudo_output_seed.json"))


def _load_family_output_example(family_key: str) -> dict[str, Any] | None:
    return _read_json_file(_family_artifact_file_path(family_key, ".laudo_output_exemplo.json"))


def _load_family_schema_definition(family_key: str) -> dict[str, Any] | None:
    return _read_json_file(_family_artifact_file_path(family_key, ".json"))


def _sha256_json(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _utc_timestamp_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _snapshot_dict(value: Any) -> dict[str, Any] | None:
    return deepcopy(value) if isinstance(value, dict) else None


def _serialize_template_ref_snapshot(
    template_ref: ResolvedPdfTemplateRef,
    *,
    capture_reason: str = "creation",
    capture_actor: str | None = None,
) -> dict[str, Any]:
    capture_reason_text = str(capture_reason or "creation").strip().lower() or "creation"
    return {
        "version": _PDF_TEMPLATE_SNAPSHOT_VERSION,
        "captured_at": _utc_timestamp_iso(),
        "capture_reason": capture_reason_text,
        "capture_actor": str(capture_actor or "").strip() or None,
        "backfill": capture_reason_text.startswith("backfill"),
        "template_ref": {
            "source_kind": str(template_ref.source_kind or "").strip(),
            "family_key": _normalize_catalog_family_key(template_ref.family_key),
            "template_id": int(template_ref.template_id or 0) or None,
            "codigo_template": _normalize_template_code(template_ref.codigo_template) or "template",
            "versao": max(1, int(template_ref.versao or 1)),
            "modo_editor": normalizar_modo_editor(template_ref.modo_editor),
            "arquivo_pdf_base": str(template_ref.arquivo_pdf_base or "").strip(),
            "documento_editor_json": normalizar_documento_editor(template_ref.documento_editor_json),
            "estilo_json": normalizar_estilo_editor(template_ref.estilo_json),
            "assets_json": list(template_ref.assets_json or []),
            "mapeamento_campos_json": normalizar_mapeamento_campos(template_ref.mapeamento_campos_json),
        },
    }


def _build_template_ref_from_snapshot(snapshot_payload: Any) -> ResolvedPdfTemplateRef | None:
    snapshot = _snapshot_dict(snapshot_payload)
    if snapshot is None:
        return None
    template_ref_payload = _snapshot_dict(snapshot.get("template_ref")) or snapshot
    template_code = _normalize_template_code(template_ref_payload.get("codigo_template"))
    if not template_code:
        return None
    return ResolvedPdfTemplateRef(
        source_kind=str(template_ref_payload.get("source_kind") or "snapshot").strip() or "snapshot",
        family_key=_normalize_catalog_family_key(template_ref_payload.get("family_key")),
        template_id=int(template_ref_payload.get("template_id") or 0) or None,
        codigo_template=template_code,
        versao=max(1, int(template_ref_payload.get("versao") or 1)),
        modo_editor=normalizar_modo_editor(template_ref_payload.get("modo_editor") or MODO_EDITOR_RICO),
        arquivo_pdf_base=str(template_ref_payload.get("arquivo_pdf_base") or "").strip(),
        documento_editor_json=normalizar_documento_editor(template_ref_payload.get("documento_editor_json")),
        estilo_json=normalizar_estilo_editor(template_ref_payload.get("estilo_json")),
        assets_json=list(template_ref_payload.get("assets_json") or []),
        mapeamento_campos_json=normalizar_mapeamento_campos(template_ref_payload.get("mapeamento_campos_json")),
    )


def _extract_catalog_snapshot(laudo: Laudo | None) -> dict[str, Any] | None:
    return _snapshot_dict(getattr(laudo, "catalog_snapshot_json", None))


def _has_governed_catalog_binding(
    laudo: Laudo | None,
    *,
    snapshot: dict[str, Any] | None = None,
) -> bool:
    selection_token = str(getattr(laudo, "catalog_selection_token", "") or "").strip()
    if selection_token:
        return True
    catalog_snapshot = snapshot if snapshot is not None else _extract_catalog_snapshot(laudo)
    if not isinstance(catalog_snapshot, dict):
        return False
    return bool(str(catalog_snapshot.get("selection_token") or "").strip())


def _catalog_snapshot_artifact(laudo: Laudo | None, artifact_key: str) -> dict[str, Any] | None:
    snapshot = _extract_catalog_snapshot(laudo)
    artifacts = _snapshot_dict(snapshot.get("artifacts")) if snapshot is not None else None
    if artifacts is None:
        return None
    return _snapshot_dict(artifacts.get(artifact_key))


def _load_family_artifacts_for_laudo(
    *,
    laudo: Laudo | None,
    family_key: str,
) -> dict[str, dict[str, Any]]:
    return {
        "family_schema": (
            _catalog_snapshot_artifact(laudo, "family_schema")
            or _load_family_schema_definition(family_key)
            or {}
        ),
        "template_master_seed": (
            _catalog_snapshot_artifact(laudo, "template_master_seed")
            or _load_family_template_seed(family_key)
            or {}
        ),
        "laudo_output_seed": (
            _catalog_snapshot_artifact(laudo, "laudo_output_seed")
            or _load_family_output_seed(family_key)
            or {}
        ),
        "laudo_output_exemplo": (
            _catalog_snapshot_artifact(laudo, "laudo_output_exemplo")
            or _load_family_output_example(family_key)
            or {}
        ),
    }


def capture_catalog_snapshot_for_laudo(
    *,
    banco: Session,
    laudo: Laudo,
    template_ref: ResolvedPdfTemplateRef | None = None,
    capture_reason: str = "creation",
    capture_actor: str | None = None,
) -> None:
    if laudo is None or getattr(laudo, "id", None) is None:
        return

    capture_reason_text = str(capture_reason or "creation").strip().lower() or "creation"
    capture_actor_text = str(capture_actor or "").strip() or None
    is_backfill_capture = capture_reason_text.startswith("backfill")

    resolved_template_ref = template_ref or resolve_pdf_template_for_laudo(
        banco=banco,
        empresa_id=int(getattr(laudo, "empresa_id", 0) or 0),
        laudo=laudo,
        allow_runtime_fallback=True,
        allow_current_binding_lookup=True,
    )
    if resolved_template_ref is not None:
        laudo.pdf_template_snapshot_json = _serialize_template_ref_snapshot(
            resolved_template_ref,
            capture_reason=capture_reason_text,
            capture_actor=capture_actor_text,
        )

    family_key = _normalize_catalog_family_key(
        getattr(laudo, "catalog_family_key", None)
        or (resolved_template_ref.family_key if resolved_template_ref is not None else None)
    )
    if not family_key:
        return

    if not getattr(laudo, "catalog_family_key", None):
        laudo.catalog_family_key = family_key

    selection_token = str(getattr(laudo, "catalog_selection_token", "") or "").strip()
    variant_key = _normalize_template_code(getattr(laudo, "catalog_variant_key", None))
    if not selection_token and family_key and variant_key:
        try:
            selection_token = build_catalog_selection_token(family_key, variant_key)
        except ValueError:
            selection_token = ""
    laudo.catalog_selection_token = selection_token or None

    artifacts = _load_family_artifacts_for_laudo(laudo=None, family_key=family_key)
    family_schema = _snapshot_dict(artifacts.get("family_schema")) or {}
    template_master_seed = _snapshot_dict(artifacts.get("template_master_seed")) or {}
    laudo_output_seed = _snapshot_dict(artifacts.get("laudo_output_seed")) or {}
    laudo_output_example = _snapshot_dict(artifacts.get("laudo_output_exemplo")) or {}

    familia = banco.scalar(
        select(FamiliaLaudoCatalogo)
        .options(selectinload(FamiliaLaudoCatalogo.oferta_comercial))
        .where(FamiliaLaudoCatalogo.family_key == family_key)
    )
    oferta = getattr(familia, "oferta_comercial", None) if familia is not None else None
    tenant_release = None
    if familia is not None:
        tenant_release = banco.scalar(
            select(TenantFamilyReleaseLaudo).where(
                TenantFamilyReleaseLaudo.tenant_id == int(getattr(laudo, "empresa_id", 0) or 0),
                TenantFamilyReleaseLaudo.family_id == int(getattr(familia, "id", 0) or 0),
            )
        )

    laudo.catalog_snapshot_json = {
        "version": _CATALOG_SNAPSHOT_VERSION,
        "captured_at": _utc_timestamp_iso(),
        "capture_reason": capture_reason_text,
        "capture_actor": capture_actor_text,
        "backfill": is_backfill_capture,
        "selection_token": selection_token or None,
        "runtime_template_code": str(getattr(laudo, "tipo_template", "") or "").strip().lower() or None,
        "family": {
            "id": int(getattr(familia, "id", 0) or 0) or None,
            "key": family_key,
            "label": str(
                getattr(laudo, "catalog_family_label", None)
                or getattr(familia, "nome_exibicao", None)
                or family_schema.get("nome_exibicao")
                or family_key
            ).strip(),
            "macro_category": str(
                getattr(familia, "macro_categoria", None)
                or family_schema.get("macro_categoria")
                or ""
            ).strip()
            or None,
            "description": str(
                getattr(familia, "descricao", None)
                or family_schema.get("descricao")
                or ""
            ).strip()
            or None,
        },
        "variant": {
            "key": variant_key,
            "label": str(getattr(laudo, "catalog_variant_label", None) or "").strip() or None,
        },
        "offer": {
            "id": int(getattr(oferta, "id", 0) or 0) or None,
            "key": str(getattr(oferta, "offer_key", "") or "").strip() or None,
            "name": str(
                getattr(laudo, "catalog_variant_label", None)
                or getattr(oferta, "nome_oferta", None)
                or ""
            ).strip()
            or None,
            "package": str(getattr(oferta, "pacote_comercial", "") or "").strip() or None,
        },
        "tenant_release": {
            "id": int(getattr(tenant_release, "id", 0) or 0) or None,
            "status": str(getattr(tenant_release, "release_status", "") or "").strip() or None,
            "default_template_code": str(getattr(tenant_release, "default_template_code", "") or "").strip() or None,
            "allowed_templates": list(getattr(tenant_release, "allowed_templates_json", None) or []),
            "allowed_variants": list(getattr(tenant_release, "allowed_variants_json", None) or []),
            "allowed_modes": list(getattr(tenant_release, "allowed_modes_json", None) or []),
            "allowed_offers": list(getattr(tenant_release, "allowed_offers_json", None) or []),
            "governance_policy_json": deepcopy(getattr(tenant_release, "governance_policy_json", None) or {}),
        },
        "artifacts": {
            "family_schema": family_schema,
            "template_master_seed": template_master_seed,
            "laudo_output_seed": laudo_output_seed,
            "laudo_output_exemplo": laudo_output_example,
        },
        "artifact_hashes": {
            "family_schema": _sha256_json(family_schema),
            "template_master_seed": _sha256_json(template_master_seed),
            "laudo_output_seed": _sha256_json(laudo_output_seed),
            "laudo_output_exemplo": _sha256_json(laudo_output_example),
        },
    }

    family_label = str(
        ((laudo.catalog_snapshot_json.get("family") or {}).get("label"))
        or family_key
    ).strip()
    if family_label and not str(getattr(laudo, "catalog_family_label", "") or "").strip():
        laudo.catalog_family_label = family_label


def _normalize_catalog_family_key(value: Any) -> str | None:
    raw_value = str(value or "").strip().lower()
    if not raw_value:
        return None
    family_key = normalizar_codigo_template(raw_value)[:120]
    return family_key or None


def _normalize_template_code(value: Any) -> str | None:
    raw_value = str(value or "").strip().lower()
    if not raw_value:
        return None
    code = normalizar_codigo_template(raw_value)
    return code or None


def normalize_catalog_render_mode(value: Any) -> str:
    render_mode = str(value or "").strip().lower()
    if render_mode in _VALID_RENDER_MODES:
        return render_mode
    return RENDER_MODE_CLIENT_PDF_FILLED


def _path_matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    normalized = str(path or "").strip(".")
    if not normalized:
        return False
    return any(
        normalized == prefix or normalized.startswith(f"{prefix}.")
        for prefix in prefixes
    )


def _blank_like(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _blank_like(child) for key, child in value.items()}
    if isinstance(value, list):
        return []
    if isinstance(value, tuple):
        return []
    return None


def _blank_preview_payload_fragment(value: Any, *, path: str = "") -> Any:
    if _path_matches_prefix(path, _BLANK_PREVIEW_KEEP_PREFIXES):
        return deepcopy(value)
    if _path_matches_prefix(path, _BLANK_PREVIEW_DROP_PREFIXES):
        return _blank_like(value)
    if isinstance(value, dict):
        return {
            key: _blank_preview_payload_fragment(
                child,
                path=f"{path}.{key}" if path else str(key),
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return []
    return None


def _simplify_slot(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    label = str(item.get("label") or item.get("slot_id") or "").strip()
    binding_path = str(item.get("binding_path") or "").strip()
    if not label or not binding_path:
        return None
    return {
        "slot_id": str(item.get("slot_id") or "").strip(),
        "label": label,
        "binding_path": binding_path,
        "purpose": str(item.get("purpose") or "").strip(),
        "required": bool(item.get("required")),
        "min_items": max(0, int(item.get("min_items") or 0)),
        "accepted_types": [str(kind).strip() for kind in list(item.get("accepted_types") or []) if str(kind).strip()],
    }


def _extract_slots(payload: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    policy = payload.get("evidence_policy") if isinstance(payload, dict) else None
    items = policy.get(key) if isinstance(policy, dict) else []
    slots: list[dict[str, Any]] = []
    for item in list(items or []):
        slot = _simplify_slot(item)
        if slot is not None:
            slots.append(slot)
    return slots


def _macro_category_from_family_key(family_key: str) -> str | None:
    match = re.match(r"^(nr\d+)", str(family_key or "").strip().lower())
    if not match:
        return None
    return match.group(1).upper()


def _build_projection_field_semantics(
    family_schema: dict[str, Any] | None = None,
) -> dict[str, str]:
    semantics = {
        "document_control.document_code": "template_static",
        "document_control.revision": "template_static",
        "document_control.title": "template_static",
        "document_contract.label": "template_static",
        "document_projection.macro_category": "template_static",
        "tenant_branding.display_name": "instance_fill",
        "tenant_branding.legal_name": "instance_fill",
        "tenant_branding.cnpj": "instance_fill",
        "tenant_branding.contact_name": "instance_fill",
        "case_context.unidade_nome": "instance_fill",
        "case_context.data_execucao": "instance_fill",
        "case_context.data_emissao": "computed_on_emit",
        "tokens.engenheiro_responsavel": "instance_fill",
        "identificacao": "instance_fill",
        "objeto_inspecao": "instance_fill",
        "informacoes_gerais": "instance_fill",
        "execucao_servico": "instance_fill",
        "checklist_componentes": "instance_fill",
        "evidencias_e_anexos": "instance_fill",
        "documentacao_e_registros": "instance_fill",
        "nao_conformidades": "instance_fill",
        "nao_conformidades_ou_lacunas": "instance_fill",
        "recomendacoes": "instance_fill",
        "conclusao": "computed_on_emit",
        "mesa_review": "internal_only",
        "family_key": "internal_only",
    }
    blueprint = (
        dict((family_schema or {}).get("document_blueprint") or {})
        if isinstance((family_schema or {}).get("document_blueprint"), dict)
        else {}
    )
    field_semantics = blueprint.get("field_semantics")
    if isinstance(field_semantics, dict):
        for path, semantic in field_semantics.items():
            path_text = str(path or "").strip()
            semantic_text = str(semantic or "").strip().lower()
            if path_text and semantic_text:
                semantics[path_text] = semantic_text
    return semantics


def _build_document_projection_payload(
    *,
    family_key: str,
    family_schema: dict[str, Any] | None,
    document_contract: dict[str, Any],
    document_control: dict[str, Any],
    render_mode: str,
) -> dict[str, Any]:
    blueprint = (
        dict((family_schema or {}).get("document_blueprint") or {})
        if isinstance((family_schema or {}).get("document_blueprint"), dict)
        else {}
    )
    family_description = str(
        (family_schema or {}).get("descricao")
        or document_contract.get("summary")
        or ""
    ).strip()
    blueprint_opening_statement = str(blueprint.get("opening_statement") or "").strip()
    if render_mode == RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        opening_statement = (
            blueprint_opening_statement
            or f"Template documental governado para emissao tecnica da familia {document_control.get('title') or family_key}."
        )
    else:
        opening_statement = (
            blueprint_opening_statement
            or family_description
            or "Documento tecnico estruturado para consolidacao de escopo, evidencias e conclusao."
        )
    return {
        "render_mode": render_mode,
        "audience": "admin" if render_mode == RENDER_MODE_ADMIN_PDF else "client",
        "family_label": str(
            (family_schema or {}).get("nome_exibicao")
            or document_control.get("title")
            or family_key
        ).strip(),
        "family_description": family_description,
        "macro_category": str(
            (family_schema or {}).get("macro_categoria")
            or _macro_category_from_family_key(family_key)
            or ""
        ).strip(),
        "master_template_id": str(document_contract.get("id") or "").strip(),
        "master_template_label": str(document_contract.get("label") or "").strip(),
        "usage_classification": (
            "Template pre-pronto"
            if render_mode == RENDER_MODE_TEMPLATE_PREVIEW_BLANK
            else "Versao administrativa"
            if render_mode == RENDER_MODE_ADMIN_PDF
            else "Documento tecnico emitido"
        ),
        "opening_statement": opening_statement,
        "preview_seal": "Template pre-pronto" if render_mode == RENDER_MODE_TEMPLATE_PREVIEW_BLANK else "",
        "section_order": list(blueprint.get("section_order") or document_contract.get("section_order") or []),
        "required_slots": _extract_slots(family_schema, "required_slots"),
        "optional_slots": _extract_slots(family_schema, "optional_slots"),
        "field_semantics": _build_projection_field_semantics(family_schema),
        "signature_roles": list(blueprint.get("signature_roles") or []),
        "blank_row_targets": dict(blueprint.get("blank_row_targets") or {}),
        "section_intros": dict(blueprint.get("section_intros") or {}),
    }


def _materialize_blank_template_preview_payload(payload: dict[str, Any]) -> dict[str, Any]:
    blank_payload = _blank_preview_payload_fragment(payload)
    if not isinstance(blank_payload, dict):
        return {}

    document_projection_payload = blank_payload.get("document_projection")
    document_projection = (
        document_projection_payload if isinstance(document_projection_payload, dict) else {}
    )
    document_control_payload = blank_payload.get("document_control")
    document_control = (
        document_control_payload if isinstance(document_control_payload, dict) else {}
    )
    tokens_payload = blank_payload.get("tokens")
    if isinstance(tokens_payload, dict):
        tokens = tokens_payload
    else:
        tokens = {}
        blank_payload["tokens"] = tokens
    tokens["revisao_template"] = str(
        tokens.get("revisao_template")
        or document_control.get("revision")
        or ""
    ).strip()
    tokens["documento_codigo"] = str(
        tokens.get("documento_codigo")
        or document_control.get("document_code")
        or ""
    ).strip()
    tokens["documento_revisao"] = str(
        tokens.get("documento_revisao")
        or document_control.get("revision")
        or ""
    ).strip()
    tokens["documento_titulo"] = str(
        tokens.get("documento_titulo")
        or document_control.get("title")
        or ""
    ).strip()
    tokens["documento_tipo_mestre"] = str(
        tokens.get("documento_tipo_mestre")
        or document_projection.get("master_template_label")
        or ""
    ).strip()

    tenant_branding_payload = blank_payload.get("tenant_branding")
    if isinstance(tenant_branding_payload, dict):
        tenant_branding = tenant_branding_payload
    else:
        tenant_branding = {}
        blank_payload["tenant_branding"] = tenant_branding
    tenant_branding["display_name"] = ""
    tenant_branding["legal_name"] = ""
    tenant_branding["cnpj"] = ""
    tenant_branding["location_label"] = ""
    tenant_branding["contact_name"] = ""
    tenant_branding["logo_asset"] = None
    tenant_branding["logo_asset_id"] = ""
    tenant_branding["signature_status"] = ""

    document_control["issue_date"] = ""
    blank_payload["resumo_executivo"] = None
    return blank_payload


def _build_template_ref_from_db(
    template: TemplateLaudo,
    *,
    family_key: str | None,
) -> ResolvedPdfTemplateRef:
    return ResolvedPdfTemplateRef(
        source_kind="tenant_template",
        family_key=family_key,
        template_id=int(getattr(template, "id", 0) or 0) or None,
        codigo_template=_normalize_template_code(getattr(template, "codigo_template", None)) or "template",
        versao=max(1, int(getattr(template, "versao", 0) or 1)),
        modo_editor=normalizar_modo_editor(getattr(template, "modo_editor", None)),
        arquivo_pdf_base=str(getattr(template, "arquivo_pdf_base", "") or "").strip(),
        documento_editor_json=normalizar_documento_editor(getattr(template, "documento_editor_json", None)),
        estilo_json=normalizar_estilo_editor(getattr(template, "estilo_json", None)),
        assets_json=list(getattr(template, "assets_json", None) or []),
        mapeamento_campos_json=normalizar_mapeamento_campos(getattr(template, "mapeamento_campos_json", None)),
    )


def _build_template_ref_from_seed(
    *,
    family_key: str,
    template_seed: dict[str, Any],
) -> ResolvedPdfTemplateRef | None:
    if not isinstance(template_seed, dict) or not template_seed:
        return None
    template_code = _normalize_template_code(
        template_seed.get("template_code") or template_seed.get("codigo_template") or family_key
    )
    if not template_code:
        return None
    return ResolvedPdfTemplateRef(
        source_kind="catalog_canonical_seed",
        family_key=family_key,
        template_id=None,
        codigo_template=template_code,
        versao=max(1, int(template_seed.get("versao") or template_seed.get("schema_version") or 1)),
        modo_editor=normalizar_modo_editor(template_seed.get("modo_editor") or MODO_EDITOR_RICO),
        arquivo_pdf_base="",
        documento_editor_json=normalizar_documento_editor(
            template_seed.get("documento_editor_json") or documento_editor_padrao()
        ),
        estilo_json=normalizar_estilo_editor(
            template_seed.get("estilo_json") or estilo_editor_padrao()
        ),
        assets_json=list(template_seed.get("assets_json") or []),
        mapeamento_campos_json=normalizar_mapeamento_campos(template_seed.get("mapeamento_campos_json")),
    )


def _catalog_specific_template_codes(
    banco: Session,
    *,
    empresa_id: int,
    laudo: Laudo,
    template_seed: dict[str, Any] | None,
) -> list[str]:
    family_key = _normalize_catalog_family_key(getattr(laudo, "catalog_family_key", None))
    variant_key = _normalize_template_code(getattr(laudo, "catalog_variant_key", None))
    candidate_codes: list[str] = []
    seen: set[str] = set()

    def _push(value: Any) -> None:
        code = _normalize_template_code(value)
        if not code or code in seen:
            return
        seen.add(code)
        candidate_codes.append(code)

    if family_key:
        familia = banco.scalar(
            select(FamiliaLaudoCatalogo)
            .options(selectinload(FamiliaLaudoCatalogo.oferta_comercial))
            .where(FamiliaLaudoCatalogo.family_key == family_key)
        )
        if familia is not None:
            release = banco.scalar(
                select(TenantFamilyReleaseLaudo).where(
                    TenantFamilyReleaseLaudo.tenant_id == int(empresa_id),
                    TenantFamilyReleaseLaudo.family_id == int(familia.id),
                    TenantFamilyReleaseLaudo.release_status == "active",
                )
            )
            _push(getattr(release, "default_template_code", None))
            _push(getattr(getattr(familia, "oferta_comercial", None), "template_default_code", None))

    _push((template_seed or {}).get("template_code"))
    _push(family_key)
    _push(variant_key)
    return candidate_codes


def _pick_active_template_by_codes(
    banco: Session,
    *,
    empresa_id: int,
    candidate_codes: list[str],
) -> TemplateLaudo | None:
    if not candidate_codes:
        return None

    candidates = (
        banco.query(TemplateLaudo)
        .filter(
            TemplateLaudo.empresa_id == int(empresa_id),
            TemplateLaudo.ativo.is_(True),
            TemplateLaudo.codigo_template.in_(candidate_codes),
        )
        .all()
    )
    if not candidates:
        return None

    priority = {code: index for index, code in enumerate(candidate_codes)}
    candidates.sort(
        key=lambda item: (
            priority.get(_normalize_template_code(getattr(item, "codigo_template", None)) or "", 999),
            -int(getattr(item, "versao", 0) or 0),
            -int(getattr(item, "id", 0) or 0),
        )
    )
    return candidates[0]


def resolve_pdf_template_for_laudo(
    *,
    banco: Session,
    empresa_id: int,
    laudo: Laudo | None,
    allow_runtime_fallback: bool,
    allow_current_binding_lookup: bool = True,
) -> ResolvedPdfTemplateRef | None:
    if laudo is None:
        return None

    snapshot_template_ref = _build_template_ref_from_snapshot(
        getattr(laudo, "pdf_template_snapshot_json", None)
    )
    if snapshot_template_ref is not None:
        return snapshot_template_ref

    snapshot = _extract_catalog_snapshot(laudo)
    governed_binding = _has_governed_catalog_binding(laudo, snapshot=snapshot)
    snapshot_family = (
        _normalize_catalog_family_key(((snapshot or {}).get("family") or {}).get("key"))
        if snapshot is not None
        else None
    )
    family_key = _normalize_catalog_family_key(
        getattr(laudo, "catalog_family_key", None) or snapshot_family
    )
    if family_key:
        artifacts = _load_family_artifacts_for_laudo(laudo=laudo, family_key=family_key)
        template_seed = artifacts.get("template_master_seed") or {}
        if allow_current_binding_lookup:
            specific_codes = _catalog_specific_template_codes(
                banco,
                empresa_id=int(empresa_id),
                laudo=laudo,
                template_seed=template_seed or {},
            )
            active_template = _pick_active_template_by_codes(
                banco,
                empresa_id=int(empresa_id),
                candidate_codes=specific_codes,
            )
            if active_template is not None:
                return _build_template_ref_from_db(active_template, family_key=family_key)

        template_from_seed = _build_template_ref_from_seed(
            family_key=family_key,
            template_seed=template_seed or {},
        )
        if template_from_seed is not None:
            return template_from_seed

    if not allow_runtime_fallback or governed_binding:
        return None

    fallback_template = selecionar_template_ativo_para_tipo(
        banco,
        empresa_id=int(empresa_id),
        tipo_template=normalizar_tipo_template(getattr(laudo, "tipo_template", None) or "padrao"),
    )
    if fallback_template is None:
        return None
    return _build_template_ref_from_db(fallback_template, family_key=family_key)


def _deep_merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    for key, value in overlay.items():
        if value is None:
            continue
        current = base.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            _deep_merge_dict(current, value)
            continue
        if isinstance(value, list):
            base[key] = deepcopy(value)
            continue
        base[key] = value
    return base


def _deep_fill_missing_dict(base: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    for key, value in fallback.items():
        if value is None:
            continue
        current = base.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            _deep_fill_missing_dict(current, value)
            continue
        if key in base:
            continue
        base[key] = deepcopy(value) if isinstance(value, (dict, list)) else value
    return base


def _looks_like_canonical_payload(payload: dict[str, Any] | None, *, family_key: str) -> bool:
    if not isinstance(payload, dict):
        return False
    payload_family = _normalize_catalog_family_key(payload.get("family_key"))
    schema_type = str(payload.get("schema_type") or "").strip().lower()
    return bool(
        schema_type == "laudo_output"
        or payload_family == family_key
        or isinstance(payload.get("case_context"), dict)
    )


def _value_by_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        key = str(segment or "").strip()
        if not key:
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _path_exists(payload: dict[str, Any], path: str) -> bool:
    current: Any = payload
    segments = [str(segment or "").strip() for segment in path.split(".") if str(segment or "").strip()]
    for segment in segments[:-1]:
        if not isinstance(current, dict) or segment not in current:
            return False
        current = current.get(segment)
    return isinstance(current, dict) and bool(segments) and segments[-1] in current


def _set_path_if_blank(payload: dict[str, Any], path: str, value: Any) -> None:
    if value in (None, "") or not _path_exists(payload, path):
        return
    current = payload
    segments = [str(segment or "").strip() for segment in path.split(".") if str(segment or "").strip()]
    for segment in segments[:-1]:
        current = current[segment]
        if not isinstance(current, dict):
            return
    leaf = segments[-1]
    existing = current.get(leaf)
    if existing not in (None, "", []):
        return
    current[leaf] = value


def _delete_path(payload: dict[str, Any], path: str) -> None:
    current: Any = payload
    segments = [str(segment or "").strip() for segment in path.split(".") if str(segment or "").strip()]
    if not segments:
        return
    for segment in segments[:-1]:
        if not isinstance(current, dict):
            return
        current = current.get(segment)
    if not isinstance(current, dict):
        return
    current.pop(segments[-1], None)


def _has_meaningful_payload_content(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_meaningful_payload_content(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_meaningful_payload_content(item) for item in value)
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _prune_empty_client_pdf_blocks(payload: dict[str, Any]) -> None:
    for path in ("registros_fotograficos",):
        block = _value_by_path(payload, path)
        if isinstance(block, dict) and not _has_meaningful_payload_content(block):
            _delete_path(payload, path)


def _normalize_date_text(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.strftime("%Y-%m-%d")
    return text


def _pick_first_text(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _pick_text_by_paths(*sources: dict[str, Any] | None, paths: list[str]) -> str | None:
    for path in paths:
        for source in sources:
            if not isinstance(source, dict):
                continue
            value = _value_by_path(source, path)
            if isinstance(value, dict):
                for key in ("descricao", "texto", "observacao", "referencias_texto", "valor"):
                    text = _pick_first_text(value.get(key))
                    if text:
                        return text
                continue
            if isinstance(value, list):
                parts = [str(item or "").strip() for item in value if str(item or "").strip()]
                if parts:
                    return "; ".join(parts)
                continue
            text = _pick_first_text(value)
            if text:
                return text
    return None


def _pick_value_by_paths(*sources: dict[str, Any] | None, paths: list[str]) -> Any:
    for path in paths:
        for source in sources:
            if not isinstance(source, dict):
                continue
            value = _value_by_path(source, path)
            if value is None or value == "":
                continue
            return value
    return None


def _normalize_signal_text(value: Any) -> str:
    text = _pick_first_text(value) or ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    text = _normalize_signal_text(value)
    if not text:
        return None
    if text in {"sim", "true", "yes", "ok", "presente", "disponivel", "existente", "em_operacao"}:
        return True
    if text in {"nao", "false", "no", "ausente", "indisponivel", "nao_apresentado", "fora_de_operacao"}:
        return False
    if any(token in text for token in ("nao apresentado", "nao observ", "ausente", "indisponivel")):
        return False
    if any(token in text for token in ("disponivel", "apresentado", "presente", "registrado", "legivel")):
        return True
    return None


def _normalize_operation_state(value: Any) -> str | None:
    bool_value = _coerce_bool(value)
    if bool_value is True:
        return "em_operacao"
    if bool_value is False:
        return "fora_de_operacao"
    text = _normalize_signal_text(value)
    if not text:
        return None
    if any(token in text for token in ("em operacao", "operando", "operacional", "funcionando", "ativo")):
        return "em_operacao"
    if any(token in text for token in ("fora de operacao", "parado", "desligado", "inoperante")):
        return "fora_de_operacao"
    return _pick_first_text(value)


def _normalize_reference_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item or "").strip() for item in value if str(item or "").strip()]
    text = _pick_first_text(value)
    if not text:
        return []
    if _normalize_signal_text(text).startswith("nao "):
        return []
    parts = [segment.strip() for segment in re.split(r"[;\n,]+", text) if segment.strip()]
    return parts


def _set_block_fields_if_blank(
    payload: dict[str, Any],
    *,
    block_path: str,
    description: str | None = None,
    references_text: str | None = None,
    available: bool | None = None,
    observation: str | None = None,
) -> None:
    _set_path_if_blank(payload, f"{block_path}.descricao", description)
    _set_path_if_blank(payload, f"{block_path}.referencias_texto", references_text)
    if observation is not None:
        _set_path_if_blank(payload, f"{block_path}.observacao", observation)
    if references_text:
        _set_path_if_blank(payload, f"{block_path}.referencias", _normalize_reference_list(references_text))
    if available is not None:
        _set_path_if_blank(payload, f"{block_path}.disponivel", available)


def _infer_nonconformity_flag(*values: Any) -> bool | None:
    for value in values:
        explicit = _coerce_bool(value)
        if explicit is not None:
            return explicit

    negative_found = False
    for value in values:
        text = _normalize_signal_text(value)
        if not text:
            continue
        negative_patterns = (
            "sem nao conform",
            "nenhuma nao conform",
            "sem anomalia",
            "sem corros",
            "sem vazament",
            "sem fuligem",
            "sem fissura",
            "sem trinca",
            "nao foram observ",
            "nao observad",
        )
        if any(pattern in text for pattern in negative_patterns):
            negative_found = True
            continue

        positive_patterns = (
            "nao conform",
            "corros",
            "vazament",
            "fuligem",
            "trinca",
            "fissura",
            "aqueciment",
            "sobreaquec",
            "desgaste",
            "anomalia",
            "irregular",
            "lacuna",
            "ressalva",
            "ajuste",
            "pendenc",
            "restric",
            "ausent",
            "incomplet",
        )
        if any(pattern in text for pattern in positive_patterns):
            return True

    if negative_found:
        return False
    return None


def _resolve_conclusion_status(review_status: Any, *, has_nonconformity: bool | None) -> str | None:
    review_key = _normalize_signal_text(review_status)
    if "rejeitad" in review_key:
        return "bloqueio"
    if has_nonconformity is True:
        return "ajuste"
    if has_nonconformity is False:
        return "conforme"
    if "rascunho" in review_key or "aguardando" in review_key:
        return "pendente"
    if "aprovado" in review_key:
        return "conforme"
    return None


def _default_catalog_materialization_date(laudo: Laudo | None) -> str | None:
    for attr_name in ("encerrado_pelo_inspetor_em", "atualizado_em", "criado_em"):
        value = getattr(laudo, attr_name, None) if laudo is not None else None
        if isinstance(value, datetime):
            return value.date().isoformat()
    return None


def _build_document_summary(
    *,
    prontuario_text: str | None,
    certificado_text: str | None,
    relatorio_text: str | None,
) -> str | None:
    parts = []
    if prontuario_text:
        parts.append(f"Prontuario: {prontuario_text}")
    if certificado_text:
        parts.append(f"Certificado: {certificado_text}")
    if relatorio_text:
        parts.append(f"Relatorio anterior: {relatorio_text}")
    return "; ".join(parts) or None


def _build_labeled_summary(*items: tuple[str, Any]) -> str | None:
    parts: list[str] = []
    for label, value in items:
        text = _pick_first_text(value)
        if text:
            parts.append(f"{label}: {text}")
    return "; ".join(parts) or None


def _extract_analysis_basis(
    *,
    laudo: Laudo | None,
    source_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if isinstance(source_payload, dict) and isinstance(source_payload.get("analysis_basis"), dict):
        return deepcopy(source_payload.get("analysis_basis"))
    report_pack = getattr(laudo, "report_pack_draft_json", None)
    if isinstance(report_pack, dict) and isinstance(report_pack.get("analysis_basis"), dict):
        return deepcopy(report_pack.get("analysis_basis"))
    return None


def _analysis_basis_internal_summary(analysis_basis: dict[str, Any] | None) -> str | None:
    if not isinstance(analysis_basis, dict):
        return None
    return _pick_first_text(
        analysis_basis.get("coverage_summary"),
        analysis_basis.get("context_summary"),
        analysis_basis.get("ai_draft_excerpt"),
    )


def _normalize_execution_mode(value: Any) -> str | None:
    text = _normalize_signal_text(value)
    if not text:
        return None
    if any(token in text for token in ("analise e modelagem", "analise/modelagem", "modelagem", "engenharia")):
        return "analise_e_modelagem"
    if any(token in text for token in ("in loco", "campo", "presencial", "site", "local")):
        return "in_loco"
    if any(token in text for token in ("hibrid", "misto", "combinado")):
        return "hibrido"
    if any(token in text for token in ("documental", "documento", "remoto", "escritorio", "gabinete")):
        return "documental"
    return _pick_first_text(value)

def build_catalog_pdf_payload(
    *,
    laudo: Laudo | None,
    template_ref: ResolvedPdfTemplateRef,
    source_payload: dict[str, Any] | None = None,
    diagnostico: str = "",
    inspetor: str = "",
    empresa: str = "",
    data: str = "",
    render_mode: str = RENDER_MODE_CLIENT_PDF_FILLED,
) -> dict[str, Any]:
    render_mode_norm = normalize_catalog_render_mode(render_mode)
    family_key = _normalize_catalog_family_key(
        template_ref.family_key or getattr(laudo, "catalog_family_key", None)
    )
    if not family_key:
        raw_payload = getattr(laudo, "dados_formulario", None)
        return raw_payload if isinstance(raw_payload, dict) else {}

    artifacts = _load_family_artifacts_for_laudo(laudo=laudo, family_key=family_key)
    payload = deepcopy(artifacts.get("laudo_output_seed") or {})
    family_schema = artifacts.get("family_schema") or {}
    existing_payload = source_payload if isinstance(source_payload, dict) else getattr(laudo, "dados_formulario", None)
    analysis_basis = _extract_analysis_basis(
        laudo=laudo,
        source_payload=existing_payload if isinstance(existing_payload, dict) else None,
    )
    if isinstance(existing_payload, dict):
        if _looks_like_canonical_payload(existing_payload, family_key=family_key):
            _deep_merge_dict(payload, existing_payload)
        else:
            tokens = existing_payload.get("tokens") if isinstance(existing_payload.get("tokens"), dict) else {}
            if tokens:
                payload_tokens = payload.setdefault("tokens", {})
                if isinstance(payload_tokens, dict):
                    _deep_merge_dict(payload_tokens, tokens)
            if isinstance(existing_payload.get("case_context"), dict):
                payload_case_context = payload.setdefault("case_context", {})
                if isinstance(payload_case_context, dict):
                    _deep_merge_dict(payload_case_context, existing_payload["case_context"])
            _set_path_if_blank(payload, "resumo_executivo", existing_payload.get("resumo_executivo"))

    tokens = payload.setdefault("tokens", {})
    if not isinstance(tokens, dict):
        tokens = {}
        payload["tokens"] = tokens

    case_context = payload.setdefault("case_context", {})
    if not isinstance(case_context, dict):
        case_context = {}
        payload["case_context"] = case_context

    mesa_review = payload.setdefault("mesa_review", {})
    if not isinstance(mesa_review, dict):
        mesa_review = {}
        payload["mesa_review"] = mesa_review

    location_hint = _pick_first_text(
        _value_by_path(existing_payload or {}, "informacoes_gerais.local_inspecao"),
        _value_by_path(existing_payload or {}, "local_inspecao"),
        _value_by_path(existing_payload or {}, "unidade"),
        _value_by_path(existing_payload or {}, "planta"),
        _value_by_path(existing_payload or {}, "setor"),
        getattr(laudo, "catalog_variant_label", None),
    )
    summary_hint = _pick_first_text(
        _value_by_path(existing_payload or {}, "resumo_executivo"),
        _analysis_basis_internal_summary(analysis_basis),
        getattr(laudo, "parecer_ia", None),
        diagnostico,
        getattr(laudo, "primeira_mensagem", None),
    )
    recommendation_hint = _pick_first_text(
        _value_by_path(existing_payload or {}, "trrf_observacoes"),
        _value_by_path(existing_payload or {}, "observacoes"),
        diagnostico,
    )
    title_hint = _pick_first_text(
        getattr(laudo, "catalog_family_label", None),
        getattr(laudo, "setor_industrial", None),
    )
    company_name = _pick_first_text(
        tokens.get("cliente_nome"),
        case_context.get("empresa_nome"),
        empresa,
    )
    unit_name = _pick_first_text(
        tokens.get("unidade_nome"),
        case_context.get("unidade_nome"),
        location_hint,
    )
    inspection_date = _normalize_date_text(
        _pick_first_text(case_context.get("data_inspecao"), data)
    )
    emission_date = _normalize_date_text(
        _pick_first_text(case_context.get("data_emissao"), data)
    )
    tenant_branding = build_tenant_branding_payload(
        empresa_entity=getattr(laudo, "empresa", None) if laudo is not None else None,
        empresa_nome=company_name,
        source_payload=existing_payload if isinstance(existing_payload, dict) else None,
    )
    document_contract = build_document_contract_payload(
        family_key=family_key,
        family_label=_pick_first_text(getattr(laudo, "catalog_family_label", None), title_hint, family_key),
        template_code=_normalize_template_code(template_ref.codigo_template) or template_ref.codigo_template,
    )
    document_control = build_document_control_payload(
        family_key=family_key,
        family_label=_pick_first_text(getattr(laudo, "catalog_family_label", None), title_hint, family_key),
        template_code=_normalize_template_code(template_ref.codigo_template) or template_ref.codigo_template,
        version=max(1, int(template_ref.versao or 1)),
        laudo=laudo,
        source_payload=existing_payload if isinstance(existing_payload, dict) else None,
        issue_date=emission_date,
        master_template_id=str(document_contract.get("id") or ""),
        master_template_label=str(document_contract.get("label") or ""),
    )

    payload["schema_type"] = "laudo_output"
    payload["schema_version"] = int(payload.get("schema_version") or 1)
    payload["family_key"] = family_key
    payload["template_code"] = _normalize_template_code(template_ref.codigo_template) or template_ref.codigo_template
    payload["document_contract"] = document_contract
    payload["document_control"] = document_control
    payload["delivery_package"] = build_document_delivery_package_payload(
        document_contract=document_contract,
        document_control=document_control,
        render_mode=render_mode_norm,
    )
    payload["tenant_branding"] = tenant_branding
    payload["render_mode"] = render_mode_norm
    payload["document_projection"] = _build_document_projection_payload(
        family_key=family_key,
        family_schema=family_schema,
        document_contract=document_contract,
        document_control=document_control,
        render_mode=render_mode_norm,
    )
    if analysis_basis is not None:
        payload["analysis_basis"] = analysis_basis
        payload["delivery_package"]["analysis_basis_available"] = True
        payload["delivery_package"]["analysis_basis_visibility"] = "internal_audit_only"
        payload["document_projection"]["analysis_basis_summary"] = _analysis_basis_internal_summary(analysis_basis)
    else:
        payload["delivery_package"]["analysis_basis_available"] = False

    tokens["cliente_nome"] = _pick_first_text(tokens.get("cliente_nome"), tenant_branding.get("display_name"), company_name)
    tokens["cliente_razao_social"] = _pick_first_text(tokens.get("cliente_razao_social"), tenant_branding.get("legal_name"))
    tokens["cliente_cnpj"] = _pick_first_text(tokens.get("cliente_cnpj"), tenant_branding.get("cnpj"))
    tokens["cliente_localizacao"] = _pick_first_text(tokens.get("cliente_localizacao"), tenant_branding.get("location_label"))
    tokens["cliente_responsavel"] = _pick_first_text(tokens.get("cliente_responsavel"), tenant_branding.get("contact_name"))
    tokens["cliente_logo_asset_id"] = _pick_first_text(tokens.get("cliente_logo_asset_id"), tenant_branding.get("logo_asset_id"))
    tokens["confidencialidade_documento"] = _pick_first_text(tokens.get("confidencialidade_documento"), tenant_branding.get("confidentiality_notice"))
    tokens["status_assinatura"] = _pick_first_text(tokens.get("status_assinatura"), tenant_branding.get("signature_status"))
    tokens["unidade_nome"] = _pick_first_text(tokens.get("unidade_nome"), unit_name)
    tokens["engenheiro_responsavel"] = _pick_first_text(tokens.get("engenheiro_responsavel"), inspetor)
    tokens["revisao_template"] = _pick_first_text(tokens.get("revisao_template"), f"v{template_ref.versao}")
    tokens["documento_codigo"] = _pick_first_text(tokens.get("documento_codigo"), document_control.get("document_code"))
    tokens["documento_revisao"] = _pick_first_text(tokens.get("documento_revisao"), document_control.get("revision"))
    tokens["documento_titulo"] = _pick_first_text(tokens.get("documento_titulo"), document_control.get("title"))
    tokens["documento_tipo_mestre"] = _pick_first_text(tokens.get("documento_tipo_mestre"), document_contract.get("label"))
    if tokens.get("crea_art") is None:
        tokens["crea_art"] = None

    case_context["laudo_id"] = _pick_first_text(case_context.get("laudo_id"), getattr(laudo, "id", None))
    case_context["empresa_nome"] = _pick_first_text(
        case_context.get("empresa_nome"),
        tenant_branding.get("display_name"),
        company_name,
    )
    case_context["unidade_nome"] = _pick_first_text(case_context.get("unidade_nome"), unit_name)
    case_context["data_inspecao"] = _pick_first_text(case_context.get("data_inspecao"), inspection_date)
    case_context["data_emissao"] = _pick_first_text(case_context.get("data_emissao"), emission_date)
    case_context["document_code"] = _pick_first_text(case_context.get("document_code"), document_control.get("document_code"))
    case_context["status_mesa"] = _pick_first_text(
        case_context.get("status_mesa"),
        getattr(laudo, "status_revisao", None),
    )

    mesa_review["status"] = _pick_first_text(
        mesa_review.get("status"),
        getattr(laudo, "status_revisao", None),
    )
    if mesa_review.get("family_lock") is None:
        mesa_review["family_lock"] = True
    if mesa_review.get("scope_mismatch") is None:
        mesa_review["scope_mismatch"] = False
    if not isinstance(mesa_review.get("bloqueios"), list):
        mesa_review["bloqueios"] = []
    _set_path_if_blank(
        payload,
        "mesa_review.bloqueios_texto",
        _pick_first_text(getattr(laudo, "motivo_rejeicao", None), "Sem bloqueios pendentes para emissão."),
    )
    _set_path_if_blank(payload, "mesa_review.observacoes_mesa", getattr(laudo, "motivo_rejeicao", None))

    _set_path_if_blank(payload, "resumo_executivo", summary_hint)
    _set_path_if_blank(payload, "recomendacoes.texto", recommendation_hint)
    _set_path_if_blank(payload, "conclusao.conclusao_tecnica", summary_hint)
    _set_path_if_blank(payload, "conclusao.justificativa", summary_hint)
    from app.domains.chat.catalog_pdf_family_projections import apply_catalog_family_projections

    apply_catalog_family_projections(
        payload=payload,
        existing_payload=existing_payload if isinstance(existing_payload, dict) else None,
        family_key=family_key,
        laudo=laudo,
        location_hint=location_hint,
        summary_hint=summary_hint,
        recommendation_hint=recommendation_hint,
        title_hint=title_hint,
    )

    if render_mode_norm == RENDER_MODE_CLIENT_PDF_FILLED:
        _prune_empty_client_pdf_blocks(payload)

    _set_path_if_blank(payload, "identificacao.localizacao", location_hint)
    _set_path_if_blank(payload, "informacoes_gerais.local", location_hint)
    _set_path_if_blank(payload, "informacoes_gerais.local_inspecao", location_hint)
    _set_path_if_blank(payload, "objeto_inspecao.localizacao", location_hint)
    _set_path_if_blank(payload, "identificacao.identificacao_do_vaso", title_hint)
    _set_path_if_blank(payload, "identificacao.identificacao_do_equipamento", title_hint)
    _set_path_if_blank(payload, "objeto_inspecao.identificacao", title_hint)
    _set_path_if_blank(payload, "case_context.data_execucao", inspection_date)

    if render_mode_norm == RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        return _materialize_blank_template_preview_payload(payload)
    return payload


def materialize_runtime_document_editor_json(
    *,
    template_ref: ResolvedPdfTemplateRef,
    payload: dict[str, Any] | None,
    render_mode: str | None = None,
) -> dict[str, Any]:
    document = normalizar_documento_editor(getattr(template_ref, "documento_editor_json", None))
    render_mode_norm = normalize_catalog_render_mode(
        render_mode
        or (
            (payload or {}).get("render_mode")
            if isinstance(payload, dict)
            else None
        )
    )
    if (
        _editor_document_looks_like_runtime_placeholder(document)
        or render_mode_norm != RENDER_MODE_CLIENT_PDF_FILLED
        or str(getattr(template_ref, "source_kind", "") or "").startswith("catalog_")
    ):
        view_model = _build_runtime_document_view_model(
            payload=payload,
            render_mode=render_mode_norm,
        )
        universal_document = build_universal_document_editor(view_model)
        if universal_document is not None:
            document = normalizar_documento_editor(universal_document)

    branding = payload.get("tenant_branding") if isinstance(payload, dict) else None
    if render_mode_norm == RENDER_MODE_TEMPLATE_PREVIEW_BLANK:
        return document
    logo_asset_id = str((branding or {}).get("logo_asset_id") or "").strip()
    if not logo_asset_id:
        return document

    content = (
        document.setdefault("doc", {}).setdefault("content", [])
        if isinstance(document.get("doc"), dict)
        else []
    )
    if not isinstance(content, list):
        return document

    for node in content:
        if not isinstance(node, dict) or str(node.get("type") or "") != "image":
            continue
        attrs_payload = node.get("attrs")
        attrs = attrs_payload if isinstance(attrs_payload, dict) else {}
        if str(attrs.get("asset_id") or "").strip() == logo_asset_id:
            return document

    brand_line: list[dict[str, Any]] = []
    display_name = str((branding or {}).get("display_name") or "").strip()
    cnpj = str((branding or {}).get("cnpj") or "").strip()
    confidentiality = str((branding or {}).get("confidentiality_notice") or "").strip()
    if display_name:
        brand_line.append({"type": "text", "text": display_name})
    if display_name and cnpj:
        brand_line.append({"type": "text", "text": " | "})
    if cnpj:
        brand_line.append({"type": "text", "text": cnpj})
    if confidentiality:
        if brand_line:
            brand_line.append({"type": "text", "text": " | "})
        brand_line.append({"type": "text", "text": confidentiality})

    intro_nodes: list[dict[str, Any]] = [
        {
            "type": "image",
            "attrs": {
                "asset_id": logo_asset_id,
                "src": f"asset://{logo_asset_id}",
                "alt": f"Logo {display_name or 'cliente'}",
                "width": 160,
            },
        }
    ]
    if brand_line:
        intro_nodes.append(
            {
                "type": "paragraph",
                "attrs": {"className": "doc-small"},
                "content": brand_line,
            }
        )
    intro_nodes.append({"type": "horizontalRule"})
    content[:0] = intro_nodes
    return document


def materialize_runtime_style_json_for_pdf_template(
    *,
    template_ref: ResolvedPdfTemplateRef,
    payload: dict[str, Any] | None,
    render_mode: str | None = None,
) -> dict[str, Any]:
    estilo = normalizar_estilo_editor(getattr(template_ref, "estilo_json", None))
    render_mode_norm = normalize_catalog_render_mode(
        render_mode
        or (
            (payload or {}).get("render_mode")
            if isinstance(payload, dict)
            else None
        )
    )
    projection = payload.get("document_projection") if isinstance(payload, dict) else None
    document_control = payload.get("document_control") if isinstance(payload, dict) else None
    if (
        str(getattr(template_ref, "source_kind", "") or "") == "tenant_template"
        and render_mode_norm == RENDER_MODE_CLIENT_PDF_FILLED
        and (
            normalizar_modo_editor(getattr(template_ref, "modo_editor", None)) == MODO_EDITOR_RICO
            or has_viable_legacy_preview_overlay_for_pdf_template(template_ref=template_ref)
        )
    ):
        return estilo

    family_label = str(
        ((projection or {}).get("family_label"))
        or ((document_control or {}).get("title"))
        or getattr(template_ref, "family_key", "")
        or "Documento Tecnico Tariel"
    ).strip()
    macro_category = str((projection or {}).get("macro_category") or "").strip()
    document_code = str((document_control or {}).get("document_code") or "").strip()
    revision = str((document_control or {}).get("revision") or "").strip()
    usage_classification = str((projection or {}).get("usage_classification") or "").strip()

    header_parts = ["Tariel"]
    if macro_category:
        header_parts.append(macro_category)
    if family_label:
        header_parts.append(family_label)
    estilo["cabecalho_texto"] = " | ".join(part for part in header_parts if part)

    footer_parts = []
    if document_code:
        footer_parts.append(document_code)
    if revision:
        footer_parts.append(f"Revisao {revision}")
    if usage_classification:
        footer_parts.append(usage_classification)
    estilo["rodape_texto"] = " | ".join(part for part in footer_parts if part)
    estilo["pagina"] = {
        "size": "A4",
        "orientation": "portrait",
        "margens_mm": {"top": 22, "right": 16, "bottom": 20, "left": 16},
    }
    estilo["tipografia"] = {
        "font_family": "Georgia, 'Times New Roman', serif",
        "font_size_px": 11,
        "line_height": 1.52,
    }
    estilo["tema"] = {
        "primaria": "#17324d",
        "secundaria": "#607284",
        "acento": "#9f6f2f",
        "suave": "#f3f6f8",
        "borda": "#ccd6de",
    }
    estilo["marca_dagua"] = {"texto": "", "opacity": 0.08, "font_size_px": 72, "rotate_deg": -32}
    return estilo


def resolve_runtime_assets_for_pdf_template(
    *,
    template_ref: ResolvedPdfTemplateRef,
    payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    return build_runtime_brand_assets(
        template_assets_json=template_ref.assets_json,
        payload=payload if isinstance(payload, dict) else {},
    )


def resolve_runtime_field_mapping_for_pdf_template(
    *,
    template_ref: ResolvedPdfTemplateRef,
) -> dict[str, Any]:
    return normalizar_mapeamento_campos(getattr(template_ref, "mapeamento_campos_json", None))


def _document_content(document: dict[str, Any] | None) -> list[Any]:
    if not isinstance(document, dict):
        return []
    doc = document.get("doc")
    if not isinstance(doc, dict):
        return []
    content = doc.get("content")
    return list(content) if isinstance(content, list) else []


def _editor_document_looks_like_runtime_placeholder(document: dict[str, Any] | None) -> bool:
    document_content = _document_content(document)
    default_content = _document_content(documento_editor_padrao())
    text_dump = json.dumps(document_content or [], ensure_ascii=False).lower()
    return (
        document_content == default_content
        or "template tecnico tariel.ia".lower() in text_dump
        or "preencher automaticamente" in text_dump
    )


def _count_field_mapping_slots(mapping_payload: dict[str, Any] | None) -> int:
    mapping = mapping_payload if isinstance(mapping_payload, dict) else {}
    total = 0
    for page in list(mapping.get("pages") or []):
        if not isinstance(page, dict):
            continue
        for field_item in list(page.get("fields") or []):
            if isinstance(field_item, dict) and str(field_item.get("key") or "").strip():
                total += 1
    return total


def _build_runtime_document_view_model(
    *,
    payload: dict[str, Any] | None,
    render_mode: str,
) -> dict[str, Any]:
    return build_catalog_document_view_model(
        payload if isinstance(payload, dict) else {},
        audience="admin" if render_mode == RENDER_MODE_ADMIN_PDF else "client",
        render_mode=render_mode,
    )


def has_viable_legacy_preview_overlay_for_pdf_template(
    *,
    template_ref: ResolvedPdfTemplateRef,
) -> bool:
    if normalizar_modo_editor(getattr(template_ref, "modo_editor", None)) == MODO_EDITOR_RICO:
        return False
    if not str(getattr(template_ref, "arquivo_pdf_base", "") or "").strip():
        return False
    mapping = resolve_runtime_field_mapping_for_pdf_template(template_ref=template_ref)
    return _count_field_mapping_slots(mapping) > 0


def should_use_rich_runtime_preview_for_pdf_template(
    *,
    template_ref: ResolvedPdfTemplateRef,
    payload: dict[str, Any] | None,
    render_mode: str | None = None,
) -> bool:
    if normalizar_modo_editor(getattr(template_ref, "modo_editor", None)) == MODO_EDITOR_RICO:
        return True
    if has_viable_legacy_preview_overlay_for_pdf_template(template_ref=template_ref):
        return False

    document = normalizar_documento_editor(getattr(template_ref, "documento_editor_json", None))
    if not _editor_document_looks_like_runtime_placeholder(document):
        return True

    render_mode_norm = normalize_catalog_render_mode(
        render_mode
        or (
            (payload or {}).get("render_mode")
            if isinstance(payload, dict)
            else None
        )
    )
    view_model = _build_runtime_document_view_model(
        payload=payload,
        render_mode=render_mode_norm,
    )
    return bool(view_model.get("modeled"))


def materialize_catalog_payload_for_laudo(
    *,
    laudo: Laudo | None,
    source_payload: dict[str, Any] | None = None,
    diagnostico: str = "",
    inspetor: str = "",
    empresa: str = "",
    data: str = "",
) -> dict[str, Any] | None:
    family_key = _normalize_catalog_family_key(
        getattr(laudo, "catalog_family_key", None)
        or (((_extract_catalog_snapshot(laudo) or {}).get("family") or {}).get("key"))
    )
    if not family_key:
        existing_payload = source_payload if isinstance(source_payload, dict) else getattr(laudo, "dados_formulario", None)
        return existing_payload if isinstance(existing_payload, dict) else None

    artifacts = _load_family_artifacts_for_laudo(laudo=laudo, family_key=family_key)
    output_seed = artifacts.get("laudo_output_seed")
    if not isinstance(output_seed, dict) or not output_seed:
        existing_payload = source_payload if isinstance(source_payload, dict) else getattr(laudo, "dados_formulario", None)
        return existing_payload if isinstance(existing_payload, dict) else None

    template_ref = _build_template_ref_from_snapshot(getattr(laudo, "pdf_template_snapshot_json", None))
    template_seed = artifacts.get("template_master_seed") or {}
    if template_ref is None:
        template_ref = _build_template_ref_from_seed(
            family_key=family_key,
            template_seed=template_seed,
        )
    if template_ref is None:
        template_code = _normalize_template_code(template_seed.get("template_code")) or family_key
        template_ref = ResolvedPdfTemplateRef(
            source_kind="catalog_runtime_materialization",
            family_key=family_key,
            template_id=None,
            codigo_template=template_code,
            versao=max(1, int(template_seed.get("versao") or template_seed.get("schema_version") or 1)),
            modo_editor=normalizar_modo_editor(template_seed.get("modo_editor") or MODO_EDITOR_RICO),
            arquivo_pdf_base="",
            documento_editor_json={},
            estilo_json={},
            assets_json=[],
            mapeamento_campos_json={},
        )

    effective_date = data or _default_catalog_materialization_date(laudo) or ""
    payload = build_catalog_pdf_payload(
        laudo=laudo,
        template_ref=template_ref,
        source_payload=source_payload,
        diagnostico=diagnostico,
        inspetor=inspetor,
        empresa=empresa,
        data=effective_date,
        render_mode=RENDER_MODE_CLIENT_PDF_FILLED,
    )
    existing_payload = (
        source_payload if isinstance(source_payload, dict) else getattr(laudo, "dados_formulario", None)
    )
    if isinstance(existing_payload, dict):
        _deep_fill_missing_dict(payload, existing_payload)
    if isinstance(laudo, Laudo):
        laudo.dados_formulario = payload
    return payload


__all__ = [
    "ResolvedPdfTemplateRef",
    "RENDER_MODE_ADMIN_PDF",
    "RENDER_MODE_CLIENT_PDF_FILLED",
    "RENDER_MODE_TEMPLATE_PREVIEW_BLANK",
    "build_catalog_pdf_payload",
    "capture_catalog_snapshot_for_laudo",
    "materialize_runtime_document_editor_json",
    "materialize_runtime_style_json_for_pdf_template",
    "materialize_catalog_payload_for_laudo",
    "normalize_catalog_render_mode",
    "has_viable_legacy_preview_overlay_for_pdf_template",
    "resolve_runtime_assets_for_pdf_template",
    "resolve_runtime_field_mapping_for_pdf_template",
    "should_use_rich_runtime_preview_for_pdf_template",
    "resolve_pdf_template_for_laudo",
]
