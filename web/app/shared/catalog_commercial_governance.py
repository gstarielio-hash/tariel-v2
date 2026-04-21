from __future__ import annotations

import re
from typing import Any

RELEASE_CHANNEL_LABELS = {
    "pilot": ("Piloto", "testing"),
    "limited_release": ("Liberacao controlada", "review"),
    "general_release": ("Liberacao ampla", "active"),
}

RELEASE_CHANNEL_ORDER = {
    "pilot": 1,
    "limited_release": 2,
    "general_release": 3,
}

CONTRACT_FEATURE_LABELS = {
    "advanced_preview": "Preview premium",
    "anexo_pack": "Anexo pack",
    "family_memory": "Memoria por familia",
    "governed_signatories": "Responsaveis pela assinatura",
    "mobile_autonomous": "Aplicativo com autonomia",
    "mobile_review": "Aplicativo com apoio da analise",
    "official_issue": "Emissao oficial",
    "operational_memory": "Memoria operacional",
    "priority_support": "Suporte prioritario",
    "public_verification": "Verificacao publica",
}

PLATFORM_FEATURE_LABELS = {
    "deep_research": "Pesquisa aprofundada",
    "upload_doc": "Upload documental",
}

CONTRACT_LIMIT_LABELS = {
    "monthly_issues": "Emissoes/mes",
    "max_active_variants": "Versoes ativas do servico",
    "max_admin_clients": "Administradores da empresa",
    "max_inspectors": "Equipe de campo",
    "max_integrations": "Integracoes",
    "max_reviewers": "Equipe de analise",
    "retention_days": "Retencao (dias)",
    "total_users": "Usuarios totais",
}


def _dict_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _slug(value: Any, *, max_len: int = 120) -> str:
    text = str(value or "").strip().lower()
    text = (
        text.replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:max_len]


def _clean_text(value: Any, *, max_len: int) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return None
    return text[:max_len]


def _clean_string_list(value: Any, *, max_len: int = 160, max_items: int = 8) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        raw_items = list(value)
    else:
        text = str(value or "").strip()
        if not text:
            return None
        raw_items = [line.strip() for line in text.splitlines()]

    items: list[str] = []
    seen: set[str] = set()
    for raw in raw_items:
        cleaned = _clean_text(raw, max_len=max_len)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(cleaned)
        if len(items) >= max_items:
            break
    return items or None


def _clean_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def normalize_release_channel(value: Any, *, allow_empty: bool = True) -> str | None:
    text = str(value or "").strip().lower()
    aliases = {
        "": None if allow_empty else "pilot",
        "inherit": None if allow_empty else "pilot",
        "pilot": "pilot",
        "teste": "pilot",
        "testing": "pilot",
        "limited_release": "limited_release",
        "limited": "limited_release",
        "limitado": "limited_release",
        "general_release": "general_release",
        "general": "general_release",
        "geral": "general_release",
        "active": "general_release",
    }
    if text not in aliases:
        raise ValueError("Release channel invalido.")
    return aliases[text]


def release_channel_meta(value: Any, *, fallback: str | None = None) -> dict[str, str]:
    key = normalize_release_channel(value, allow_empty=True) or normalize_release_channel(fallback, allow_empty=False)
    assert key is not None
    label, tone = RELEASE_CHANNEL_LABELS[key]
    return {"key": key, "label": label, "tone": tone}


def _normalize_feature_key(value: Any) -> str | None:
    text = _slug(value, max_len=80)
    aliases = {
        "advanced_preview": "advanced_preview",
        "anexo_pack": "anexo_pack",
        "attachments_pack": "anexo_pack",
        "family_memory": "family_memory",
        "governed_signatories": "governed_signatories",
        "signatories": "governed_signatories",
        "mobile_autonomous": "mobile_autonomous",
        "mobile_review": "mobile_review",
        "official_issue": "official_issue",
        "operational_memory": "operational_memory",
        "priority_support": "priority_support",
        "public_verification": "public_verification",
    }
    return aliases.get(text) or (text if text else None)


def _feature_meta(value: Any, *, platform: bool = False) -> dict[str, str]:
    key = _slug(value, max_len=80)
    labels = PLATFORM_FEATURE_LABELS if platform else CONTRACT_FEATURE_LABELS
    label = labels.get(key) or key.replace("_", " ").title()
    return {"key": key, "label": label}


def sanitize_commercial_bundle(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    key = _slug(
        payload.get("bundle_key")
        or payload.get("package_key")
        or payload.get("key")
        or payload.get("pacote")
        or payload.get("bundle_label")
        or payload.get("label"),
        max_len=80,
    )
    label = _clean_text(
        payload.get("bundle_label")
        or payload.get("package_name")
        or payload.get("label")
        or payload.get("nome"),
        max_len=120,
    )
    if not key and not label:
        return None
    highlights = _clean_string_list(
        payload.get("highlights") or payload.get("destaques"),
        max_len=120,
        max_items=6,
    )
    return {
        "bundle_key": key or _slug(label, max_len=80),
        "bundle_label": label or key.replace("_", " ").title(),
        "summary": _clean_text(payload.get("summary") or payload.get("descricao"), max_len=240),
        "audience": _clean_text(payload.get("audience") or payload.get("publico"), max_len=120),
        "highlights": highlights or [],
    }


def sanitize_contract_entitlements(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    raw_features = (
        payload.get("included_features")
        or payload.get("features")
        or payload.get("recursos")
        or []
    )
    features = _clean_string_list(raw_features, max_len=80, max_items=10) or []
    feature_keys: list[str] = []
    seen_features: set[str] = set()
    for item in features:
        normalized = _normalize_feature_key(item)
        if not normalized or normalized in seen_features:
            continue
        seen_features.add(normalized)
        feature_keys.append(normalized)

    raw_limits = _dict_payload(payload.get("limits")) or _dict_payload(payload)
    limits = {
        "monthly_issues": _clean_int(
            raw_limits.get("monthly_issues")
            or raw_limits.get("issuance_limit_monthly")
            or raw_limits.get("monthly_issue_limit")
        ),
        "max_admin_clients": _clean_int(
            raw_limits.get("max_admin_clients")
            or raw_limits.get("max_admins_cliente")
            or raw_limits.get("max_admin_client")
        ),
        "max_inspectors": _clean_int(raw_limits.get("max_inspectors") or raw_limits.get("max_inspetores")),
        "max_reviewers": _clean_int(raw_limits.get("max_reviewers") or raw_limits.get("max_revisores")),
        "max_active_variants": _clean_int(
            raw_limits.get("max_active_variants")
            or raw_limits.get("max_variants")
            or raw_limits.get("max_variantes_ativas")
        ),
        "max_integrations": _clean_int(
            raw_limits.get("max_integrations")
            or raw_limits.get("integrations_max")
            or raw_limits.get("max_integracoes")
        ),
    }
    normalized_limits = {key: value for key, value in limits.items() if value is not None}
    if not feature_keys and not normalized_limits:
        return None
    return {
        "included_features": feature_keys,
        "limits": normalized_limits,
    }


def sanitize_plan_snapshot(payload: Any) -> dict[str, Any]:
    source = dict(payload or {}) if isinstance(payload, dict) else {}
    return {
        "laudos_mes": _clean_int(source.get("laudos_mes")),
        "usuarios_max": _clean_int(source.get("usuarios_max")),
        "integracoes_max": _clean_int(source.get("integracoes_max")),
        "retencao_dias": _clean_int(source.get("retencao_dias")),
        "upload_doc": bool(source.get("upload_doc")),
        "deep_research": bool(source.get("deep_research")),
    }


def merge_offer_commercial_flags(
    base_flags: Any,
    *,
    release_channel: str | None,
    commercial_bundle: dict[str, Any] | None,
    contract_entitlements: dict[str, Any] | None,
) -> dict[str, Any] | None:
    payload = dict(base_flags or {}) if isinstance(base_flags, dict) else {}
    payload = {
        key: value
        for key, value in payload.items()
        if key not in {"release_channel", "commercial_bundle", "contract_entitlements"}
    }
    if release_channel:
        payload["release_channel"] = release_channel
    if commercial_bundle:
        payload["commercial_bundle"] = commercial_bundle
    if contract_entitlements:
        payload["contract_entitlements"] = contract_entitlements
    return payload or None


def merge_release_contract_policy(
    base_policy: Any,
    *,
    release_channel_override: str | None,
    contract_entitlements: dict[str, Any] | None,
) -> dict[str, Any] | None:
    payload = dict(base_policy or {}) if isinstance(base_policy, dict) else {}
    payload = {
        key: value
        for key, value in payload.items()
        if key not in {"release_channel_override", "contract_entitlements"}
    }
    if release_channel_override:
        payload["release_channel_override"] = release_channel_override
    if contract_entitlements:
        payload["contract_entitlements"] = contract_entitlements
    return payload or None


def summarize_offer_commercial_governance(
    flags_payload: Any,
    *,
    offer_lifecycle_status: str | None = None,
) -> dict[str, Any]:
    payload = dict(flags_payload or {}) if isinstance(flags_payload, dict) else {}
    explicit_channel = normalize_release_channel(payload.get("release_channel"), allow_empty=True)
    inferred_channel = explicit_channel
    lifecycle = str(offer_lifecycle_status or "").strip().lower()
    if inferred_channel is None:
        if lifecycle == "active":
            inferred_channel = "general_release"
        elif lifecycle == "testing":
            inferred_channel = "limited_release"
        else:
            inferred_channel = "pilot"
    bundle = sanitize_commercial_bundle(payload.get("commercial_bundle"))
    contract = sanitize_contract_entitlements(payload.get("contract_entitlements"))
    return {
        "release_channel": release_channel_meta(inferred_channel),
        "explicit_release_channel": release_channel_meta(explicit_channel or inferred_channel),
        "commercial_bundle": bundle,
        "contract_entitlements": summarize_contract_entitlements(contract),
    }


def summarize_release_contract_governance(
    governance_payload: Any,
    *,
    offer_flags_payload: Any = None,
    offer_lifecycle_status: str | None = None,
    plan_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(governance_payload or {}) if isinstance(governance_payload, dict) else {}
    offer_payload = dict(offer_flags_payload or {}) if isinstance(offer_flags_payload, dict) else {}
    offer_summary = summarize_offer_commercial_governance(
        offer_payload,
        offer_lifecycle_status=offer_lifecycle_status,
    )
    override_channel = normalize_release_channel(payload.get("release_channel_override"), allow_empty=True)
    effective_channel_key = offer_summary["release_channel"]["key"]
    if override_channel:
        effective_channel_key = min(
            (effective_channel_key, override_channel),
            key=lambda item: RELEASE_CHANNEL_ORDER.get(item, 99),
        )
    offer_contract = sanitize_contract_entitlements(offer_payload.get("contract_entitlements"))
    release_contract = sanitize_contract_entitlements(payload.get("contract_entitlements"))
    effective_contract = _merge_contract_entitlements(offer_contract, release_contract)
    return {
        "release_channel_override": (
            release_channel_meta(override_channel)
            if override_channel
            else {"key": "inherit", "label": "Herdar", "tone": "idle"}
        ),
        "effective_release_channel": release_channel_meta(effective_channel_key),
        "contract_entitlements_override": summarize_contract_entitlements(release_contract),
        "effective_contract_entitlements": summarize_contract_entitlements(
            effective_contract,
            plan_snapshot=plan_snapshot,
        ),
    }


def summarize_contract_entitlements(
    payload: Any,
    *,
    plan_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = sanitize_contract_entitlements(payload)
    plan = sanitize_plan_snapshot(plan_snapshot)
    platform_features = [
        _feature_meta(key, platform=True)
        for key in PLATFORM_FEATURE_LABELS
        if bool(plan.get(key))
    ]
    included_features = [
        _feature_meta(item)
        for item in list((contract or {}).get("included_features") or [])
    ]
    effective_features_lookup = {
        item["key"]: item
        for item in [*platform_features, *included_features]
    }
    effective_limits_raw = {
        "total_users": plan.get("usuarios_max"),
        "monthly_issues": _min_limit(plan.get("laudos_mes"), ((contract or {}).get("limits") or {}).get("monthly_issues")),
        "max_integrations": _min_limit(plan.get("integracoes_max"), ((contract or {}).get("limits") or {}).get("max_integrations")),
        "retention_days": plan.get("retencao_dias"),
        "max_admin_clients": ((contract or {}).get("limits") or {}).get("max_admin_clients"),
        "max_inspectors": ((contract or {}).get("limits") or {}).get("max_inspectors"),
        "max_reviewers": ((contract or {}).get("limits") or {}).get("max_reviewers"),
        "max_active_variants": ((contract or {}).get("limits") or {}).get("max_active_variants"),
    }
    effective_limits = {
        key: value for key, value in effective_limits_raw.items() if value is not None
    }
    limit_items = [
        {
            "key": key,
            "label": CONTRACT_LIMIT_LABELS.get(key, key.replace("_", " ").title()),
            "value": int(value),
        }
        for key, value in effective_limits.items()
    ]
    return {
        "has_data": bool(contract or platform_features or effective_limits),
        "included_features": included_features,
        "platform_features": platform_features,
        "effective_features": list(effective_features_lookup.values()),
        "limits": limit_items,
        "limit_count": len(limit_items),
    }


def _merge_contract_entitlements(
    base_payload: dict[str, Any] | None,
    override_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    base = sanitize_contract_entitlements(base_payload)
    override = sanitize_contract_entitlements(override_payload)
    if base is None and override is None:
        return None
    features = (
        list(override.get("included_features") or [])
        if override and list(override.get("included_features") or [])
        else list((base or {}).get("included_features") or [])
    )
    merged_limits: dict[str, int] = {}
    all_limit_keys = {
        *list((base or {}).get("limits", {}).keys()),
        *list((override or {}).get("limits", {}).keys()),
    }
    for key in all_limit_keys:
        merged_limit = _min_limit(
            ((base or {}).get("limits") or {}).get(key),
            ((override or {}).get("limits") or {}).get(key),
        )
        if merged_limit is not None:
            merged_limits[key] = merged_limit
    merged_payload = {
        "included_features": features,
        "limits": merged_limits,
    }
    return sanitize_contract_entitlements(merged_payload)


def _min_limit(left: Any, right: Any) -> int | None:
    left_int = _clean_int(left)
    right_int = _clean_int(right)
    if left_int is None:
        return right_int
    if right_int is None:
        return left_int
    return min(left_int, right_int)
