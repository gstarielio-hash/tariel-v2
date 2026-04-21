"""Governanca catalogada por familia e tenant para o policy engine do V2."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.shared.database import (
    AtivacaoCatalogoEmpresaLaudo,
    FamiliaLaudoCatalogo,
    TenantFamilyReleaseLaudo,
)
from app.shared.tenant_report_catalog import build_catalog_selection_token

_REVIEW_MODE_VALUES = {
    "mesa_required",
    "mobile_review_allowed",
    "mobile_autonomous",
}


def _normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raw_values = [item.strip() for item in values.split(",")]
    elif isinstance(values, (list, tuple, set)):
        raw_values = [str(item or "").strip() for item in values]
    else:
        raw_values = [str(values or "").strip()]
    return [item for item in raw_values if item]


def _normalize_review_mode(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if text in _REVIEW_MODE_VALUES:
        return text
    return None


def _family_keys_for_lookup(*, family_key: Any, template_key: Any) -> list[str]:
    candidates: list[str] = []
    for raw in (family_key, template_key):
        text = _normalize_text(raw)
        if not text:
            continue
        normalized = text.lower()
        if normalized not in candidates:
            candidates.append(normalized)
    return candidates


def load_case_policy_governance_context(
    banco: Session | None,
    *,
    tenant_id: Any,
    family_key: Any = None,
    variant_key: Any = None,
    template_key: Any = None,
) -> dict[str, Any]:
    resolved_family_key = _normalize_text(family_key)
    resolved_variant_key = _normalize_text(variant_key)
    resolved_template_key = _normalize_text(template_key)
    context: dict[str, Any] = {
        "family_key": resolved_family_key.lower() if resolved_family_key else None,
        "variant_key": resolved_variant_key.lower() if resolved_variant_key else None,
        "template_key": resolved_template_key.lower() if resolved_template_key else None,
        "family_label": None,
        "family_exists": False,
        "review_policy": {},
        "release_status": None,
        "release_active": None,
        "release_present": False,
        "release_policy": {},
        "release_force_review_mode": None,
        "release_max_review_mode": None,
        "release_mobile_review_override": None,
        "release_mobile_autonomous_override": None,
        "activation_active": False,
        "activation_selection_token": None,
        "allowed_templates": [],
        "allowed_variants": [],
        "default_review_mode": None,
        "max_review_mode": None,
        "tenant_entitlements_policy": {},
    }
    if banco is None:
        return context

    lookup_keys = _family_keys_for_lookup(
        family_key=resolved_family_key,
        template_key=resolved_template_key,
    )
    family = None
    if lookup_keys:
        family = banco.scalar(
            select(FamiliaLaudoCatalogo)
            .options(selectinload(FamiliaLaudoCatalogo.tenant_releases))
            .where(FamiliaLaudoCatalogo.family_key.in_(lookup_keys))
            .order_by(FamiliaLaudoCatalogo.id.asc())
        )

    if family is None:
        return context

    family_key_text = str(family.family_key or "").strip().lower()
    review_policy = (
        dict(family.review_policy_json)
        if isinstance(family.review_policy_json, dict)
        else {}
    )
    tenant_entitlements_policy = (
        dict(review_policy.get("tenant_entitlements") or {})
        if isinstance(review_policy.get("tenant_entitlements"), dict)
        else {}
    )

    release = None
    tenant_id_int = None
    try:
        tenant_id_int = int(tenant_id)
    except (TypeError, ValueError):
        tenant_id_int = None
    if tenant_id_int is not None:
        release = banco.scalar(
            select(TenantFamilyReleaseLaudo)
            .where(
                TenantFamilyReleaseLaudo.tenant_id == tenant_id_int,
                TenantFamilyReleaseLaudo.family_id == int(family.id),
            )
            .order_by(TenantFamilyReleaseLaudo.id.desc())
        )

    activation = None
    if tenant_id_int is not None:
        activation_query = select(AtivacaoCatalogoEmpresaLaudo).where(
            AtivacaoCatalogoEmpresaLaudo.empresa_id == tenant_id_int,
            AtivacaoCatalogoEmpresaLaudo.family_key == family_key_text,
            AtivacaoCatalogoEmpresaLaudo.ativo.is_(True),
        )
        if resolved_variant_key:
            activation_query = activation_query.where(
                AtivacaoCatalogoEmpresaLaudo.variant_key
                == str(resolved_variant_key).strip().lower()
            )
        activation = banco.scalar(
            activation_query.order_by(AtivacaoCatalogoEmpresaLaudo.id.desc())
        )

    activation_selection_token = None
    if family_key_text and resolved_variant_key:
        try:
            activation_selection_token = build_catalog_selection_token(
                family_key_text,
                resolved_variant_key.lower(),
            )
        except ValueError:
            activation_selection_token = None

    allowed_templates = (
        _normalize_list(getattr(release, "allowed_templates_json", None))
        if release is not None
        else []
    )
    allowed_variants = (
        _normalize_list(getattr(release, "allowed_variants_json", None))
        if release is not None
        else []
    )
    release_policy = (
        dict(getattr(release, "governance_policy_json", None) or {})
        if release is not None
        and isinstance(getattr(release, "governance_policy_json", None), dict)
        else {}
    )
    release_mobile_review_override = release_policy.get("mobile_review_override")
    if not isinstance(release_mobile_review_override, bool):
        release_mobile_review_override = None
    release_mobile_autonomous_override = release_policy.get(
        "mobile_autonomous_override"
    )
    if not isinstance(release_mobile_autonomous_override, bool):
        release_mobile_autonomous_override = None

    context.update(
        {
            "family_key": family_key_text,
            "family_label": _normalize_text(getattr(family, "nome_exibicao", None)),
            "family_exists": True,
            "review_policy": review_policy,
            "release_status": _normalize_text(getattr(release, "release_status", None)),
            "release_active": (
                str(getattr(release, "release_status", "") or "").strip().lower()
                == "active"
                if release is not None
                else None
            ),
            "release_present": release is not None,
            "release_policy": release_policy,
            "release_force_review_mode": _normalize_review_mode(
                release_policy.get("force_review_mode")
            ),
            "release_max_review_mode": _normalize_review_mode(
                release_policy.get("max_review_mode")
            ),
            "release_mobile_review_override": release_mobile_review_override,
            "release_mobile_autonomous_override": release_mobile_autonomous_override,
            "activation_active": activation is not None,
            "activation_selection_token": activation_selection_token,
            "allowed_templates": allowed_templates,
            "allowed_variants": allowed_variants,
            "default_review_mode": _normalize_review_mode(
                review_policy.get("default_review_mode")
            ),
            "max_review_mode": _normalize_review_mode(
                review_policy.get("max_review_mode")
            ),
            "tenant_entitlements_policy": tenant_entitlements_policy,
        }
    )
    return context


__all__ = ["load_case_policy_governance_context"]
