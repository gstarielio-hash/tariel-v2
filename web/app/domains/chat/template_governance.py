"""Governanca compartilhada de template para fluxos guiados do inspetor."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.chat.normalization import normalizar_tipo_template, resolver_familia_padrao_template
from app.shared.database import Laudo, Usuario
from app.shared.tenant_report_catalog import (
    build_catalog_selection_token,
    parse_catalog_selection_token,
    resolve_tenant_template_request,
)
from nucleo.template_laudos import normalizar_codigo_template


def _texto_limpo(valor: Any) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    return texto


def _snapshot_dict(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return dict(value)


def _catalog_key_limpa(valor: Any, *, limite: int) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    return normalizar_codigo_template(texto)[:limite] or None


def resolve_guided_template_governance(
    banco: Session,
    *,
    usuario: Usuario,
    template_key: Any,
    laudo: Laudo | None = None,
) -> dict[str, Any]:
    template_key_normalizado = normalizar_tipo_template(str(template_key or "padrao"))
    selection_token_atual = _texto_limpo(getattr(laudo, "catalog_selection_token", None))

    if selection_token_atual:
        runtime_atual = normalizar_tipo_template(
            str(getattr(laudo, "tipo_template", None) or template_key_normalizado)
        )
        if runtime_atual != template_key_normalizado:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Este laudo ja esta vinculado a um template governado pelo Admin-CEO "
                    "e nao pode trocar de binding durante a coleta."
                ),
            )
        return {
            "governed_mode": True,
            "catalog_state": "case_bound",
            "requested_value": template_key_normalizado,
            "runtime_template_code": runtime_atual,
            "family_key": _texto_limpo(getattr(laudo, "catalog_family_key", None)),
            "family_label": _texto_limpo(getattr(laudo, "catalog_family_label", None)),
            "variant_key": _texto_limpo(getattr(laudo, "catalog_variant_key", None)),
            "variant_label": _texto_limpo(getattr(laudo, "catalog_variant_label", None)),
            "offer_name": None,
            "selection_token": selection_token_atual,
            "compatibility_mode": False,
            "case_bound": True,
        }

    try:
        resolucao_template = resolve_tenant_template_request(
            banco,
            empresa_id=int(usuario.empresa_id),
            requested_value=template_key_normalizado,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return {
        **resolucao_template,
        "case_bound": False,
    }


def apply_template_governance_to_laudo(
    *,
    laudo: Laudo,
    resolucao_template: dict[str, Any],
) -> None:
    runtime_template_code = (
        str(resolucao_template.get("runtime_template_code") or "padrao").strip().lower()
        or "padrao"
    )
    laudo.tipo_template = runtime_template_code

    family_binding = resolver_familia_padrao_template(runtime_template_code)
    family_key = (
        _texto_limpo(resolucao_template.get("family_key"))
        or _texto_limpo(family_binding.get("family_key"))
    )
    family_label = (
        _texto_limpo(resolucao_template.get("family_label"))
        or _texto_limpo(family_binding.get("family_label"))
    )
    selection_token = _texto_limpo(resolucao_template.get("selection_token"))

    laudo.catalog_selection_token = selection_token
    laudo.catalog_family_key = family_key
    laudo.catalog_family_label = family_label
    laudo.catalog_variant_key = _texto_limpo(resolucao_template.get("variant_key"))
    laudo.catalog_variant_label = _texto_limpo(resolucao_template.get("variant_label"))


def resolve_case_bound_runtime_template(
    *,
    laudo: Laudo | None,
    requested_template_key: Any,
) -> dict[str, Any]:
    requested_template_code = normalizar_tipo_template(
        str(requested_template_key or getattr(laudo, "tipo_template", None) or "padrao")
    )
    current_template_code = normalizar_tipo_template(
        str(getattr(laudo, "tipo_template", None) or requested_template_code or "padrao")
    )
    selection_token = _texto_limpo(getattr(laudo, "catalog_selection_token", None))
    binding_locked = bool(selection_token)
    effective_template_code = current_template_code if binding_locked else requested_template_code

    return {
        "requested_template_code": requested_template_code,
        "effective_template_code": effective_template_code,
        "binding_locked": binding_locked,
        "case_bound": binding_locked,
        "selection_token": selection_token,
        "overrode_requested_template": binding_locked and effective_template_code != requested_template_code,
    }


def reaffirm_case_bound_template_governance(
    *,
    laudo: Laudo,
) -> dict[str, Any]:
    catalog_snapshot = _snapshot_dict(getattr(laudo, "catalog_snapshot_json", None)) or {}
    pdf_template_snapshot = _snapshot_dict(getattr(laudo, "pdf_template_snapshot_json", None)) or {}
    pdf_template_ref = _snapshot_dict(pdf_template_snapshot.get("template_ref")) or pdf_template_snapshot
    snapshot_family = _snapshot_dict(catalog_snapshot.get("family")) or {}
    snapshot_variant = _snapshot_dict(catalog_snapshot.get("variant")) or {}

    current_selection_token = _texto_limpo(getattr(laudo, "catalog_selection_token", None))
    snapshot_selection_token = _texto_limpo(catalog_snapshot.get("selection_token"))
    selection_token = current_selection_token or snapshot_selection_token
    parsed_selection = parse_catalog_selection_token(selection_token) if selection_token else None
    parsed_family_key = parsed_selection[0] if parsed_selection is not None else None
    parsed_variant_key = parsed_selection[1] if parsed_selection is not None else None

    snapshot_runtime_template = _texto_limpo(catalog_snapshot.get("runtime_template_code"))
    snapshot_pdf_template_code = _texto_limpo(pdf_template_ref.get("codigo_template"))
    runtime_template_code = normalizar_tipo_template(
        snapshot_runtime_template
        or snapshot_pdf_template_code
        or getattr(laudo, "tipo_template", None)
        or "padrao"
    )
    family_binding = resolver_familia_padrao_template(runtime_template_code)

    family_key = (
        _catalog_key_limpa(parsed_family_key, limite=120)
        or _catalog_key_limpa(snapshot_family.get("key"), limite=120)
        or _catalog_key_limpa(pdf_template_ref.get("family_key"), limite=120)
        or _catalog_key_limpa(getattr(laudo, "catalog_family_key", None), limite=120)
        or _catalog_key_limpa(family_binding.get("family_key"), limite=120)
    )
    variant_key = (
        _catalog_key_limpa(parsed_variant_key, limite=80)
        or _catalog_key_limpa(snapshot_variant.get("key"), limite=80)
        or _catalog_key_limpa(getattr(laudo, "catalog_variant_key", None), limite=80)
    )
    if selection_token is None and family_key and variant_key:
        try:
            selection_token = build_catalog_selection_token(family_key, variant_key)
        except ValueError:
            selection_token = None

    governed_binding = bool(
        selection_token
        or snapshot_selection_token
        or snapshot_runtime_template
        or snapshot_pdf_template_code
        or family_key
    )
    if not governed_binding:
        return {
            "governed_binding": False,
            "changed": False,
            "runtime_template_code": runtime_template_code,
            "selection_token": None,
            "family_key": None,
            "variant_key": None,
        }

    family_label = (
        _texto_limpo(snapshot_family.get("label"))
        or _texto_limpo(getattr(laudo, "catalog_family_label", None))
        or _texto_limpo(family_binding.get("family_label"))
    )
    variant_label = (
        _texto_limpo(snapshot_variant.get("label"))
        or _texto_limpo(getattr(laudo, "catalog_variant_label", None))
    )

    changed = False
    desired_values = {
        "tipo_template": runtime_template_code,
        "catalog_selection_token": selection_token,
        "catalog_family_key": family_key,
        "catalog_family_label": family_label,
        "catalog_variant_key": variant_key,
        "catalog_variant_label": variant_label,
    }
    for field_name, expected_value in desired_values.items():
        current_value = getattr(laudo, field_name, None)
        if current_value != expected_value:
            setattr(laudo, field_name, expected_value)
            changed = True

    return {
        "governed_binding": True,
        "changed": changed,
        "runtime_template_code": runtime_template_code,
        "selection_token": selection_token,
        "family_key": family_key,
        "variant_key": variant_key,
    }


__all__ = [
    "apply_template_governance_to_laudo",
    "reaffirm_case_bound_template_governance",
    "resolve_case_bound_runtime_template",
    "resolve_guided_template_governance",
]
