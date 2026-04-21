"""Governança do catálogo comercial de laudos por tenant."""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domains.chat.normalization import ALIASES_TEMPLATE, TIPOS_TEMPLATE_VALIDOS, normalizar_tipo_template
from app.shared.catalog_commercial_governance import (
    summarize_offer_commercial_governance,
    summarize_release_contract_governance,
)
from app.shared.db.models_auth import Empresa
from app.shared.db.models_review_governance import (
    AtivacaoCatalogoEmpresaLaudo,
    FamiliaLaudoCatalogo,
    OfertaComercialFamiliaLaudo,
    TenantFamilyReleaseLaudo,
)

CATALOGO_TOKEN_PREFIX = "catalog"

_LEGACY_TEMPLATE_GROUPS = {
    "avcb": "Bombeiros e Incêndio",
    "cbmgo": "Bombeiros e Incêndio",
    "loto": "Instalações Elétricas",
    "nr11_movimentacao": "Máquinas e Processos",
    "nr12maquinas": "Máquinas e Processos",
    "nr13": "Máquinas e Processos",
    "nr13_calibracao": "Máquinas e Processos",
    "nr13_teste_hidrostatico": "Máquinas e Processos",
    "nr13_ultrassom": "Máquinas e Processos",
    "nr20_instalacoes": "Processos com Inflamáveis",
    "nr33_espaco_confinado": "Espaço Confinado",
    "nr35_linha_vida": "Trabalho em Altura",
    "nr35_montagem": "Trabalho em Altura",
    "nr35_ponto_ancoragem": "Trabalho em Altura",
    "nr35_projeto": "Trabalho em Altura",
    "pie": "Instalações Elétricas",
    "rti": "Instalações Elétricas",
    "spda": "Instalações Elétricas",
    "padrao": "Flexível",
}
_LEGACY_TEMPLATE_ORDER = (
    "avcb",
    "cbmgo",
    "rti",
    "pie",
    "spda",
    "loto",
    "nr11_movimentacao",
    "nr12maquinas",
    "nr13",
    "nr13_ultrassom",
    "nr13_calibracao",
    "nr13_teste_hidrostatico",
    "nr20_instalacoes",
    "nr33_espaco_confinado",
    "nr35_linha_vida",
    "nr35_ponto_ancoragem",
    "nr35_projeto",
    "nr35_montagem",
    "padrao",
)
_RUNTIME_PREFIX_RULES: tuple[tuple[str, str], ...] = (
    ("nr35_ponto_ancoragem", "nr35_ponto_ancoragem"),
    ("nr35_projeto", "nr35_projeto"),
    ("nr35_montagem", "nr35_montagem"),
    ("nr13", "nr13"),
    ("nr33", "nr33_espaco_confinado"),
    ("nr20", "nr20_instalacoes"),
    ("nr11", "nr11_movimentacao"),
    ("nr10", "rti"),
    ("loto", "loto"),
    ("rti", "rti"),
    ("nr12", "nr12maquinas"),
    ("nr35", "nr35_linha_vida"),
    ("cbmgo", "cbmgo"),
    ("avcb", "avcb"),
    ("spda", "spda"),
    ("pie", "pie"),
)
_REVIEW_MODE_LABELS = {
    "mesa_required": "Mesa obrigatória",
    "mobile_review_allowed": "Mobile com revisão",
    "mobile_autonomous": "Mobile autônomo",
}
_RELEASE_STATUS_LABELS = {
    "draft": "Rascunho",
    "active": "Liberado",
    "paused": "Pausado",
    "expired": "Expirado",
}
_ACTIVATION_BLOCK_REASON_LABELS = {
    "offer_not_released": "Oferta comercial não liberada para o tenant.",
    "release_inactive": "A liberação da família está inativa para o tenant.",
    "template_not_released": "Template fora da liberação ativa do tenant.",
    "variant_not_released": "Variante comercial fora da liberação ativa do tenant.",
}


def _normalizar_chave_catalogo(valor: Any, *, max_len: int) -> str:
    texto = str(valor or "").strip().lower()
    texto = (
        texto.replace("á", "a")
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
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return texto[:max_len]


def build_catalog_selection_token(family_key: str, variant_key: str) -> str:
    family_norm = _normalizar_chave_catalogo(family_key, max_len=120)
    variant_norm = _normalizar_chave_catalogo(variant_key, max_len=80)
    if not family_norm or not variant_norm:
        raise ValueError("Family key e variant key são obrigatórios para o token do catálogo.")
    return f"{CATALOGO_TOKEN_PREFIX}:{family_norm}:{variant_norm}"


def parse_catalog_selection_token(value: Any) -> tuple[str, str] | None:
    bruto = str(value or "").strip().lower()
    if not bruto.startswith(f"{CATALOGO_TOKEN_PREFIX}:"):
        return None
    partes = bruto.split(":")
    if len(partes) != 3:
        return None
    family_key = _normalizar_chave_catalogo(partes[1], max_len=120)
    variant_key = _normalizar_chave_catalogo(partes[2], max_len=80)
    if not family_key or not variant_key:
        return None
    return family_key, variant_key


def resolve_runtime_template_code(
    *,
    family_key: Any,
    template_code: Any = None,
    variant_key: Any = None,
) -> str | None:
    candidatos = [
        _normalizar_chave_catalogo(template_code, max_len=80),
        _normalizar_chave_catalogo(family_key, max_len=120),
        _normalizar_chave_catalogo(variant_key, max_len=80),
    ]
    for candidato in candidatos:
        if not candidato:
            continue
        if candidato in ALIASES_TEMPLATE:
            return normalizar_tipo_template(candidato)

    for candidato in candidatos:
        if not candidato:
            continue
        for prefixo, runtime in _RUNTIME_PREFIX_RULES:
            if candidato.startswith(prefixo):
                return runtime
    return None


def _family_group_label(familia: FamiliaLaudoCatalogo, oferta: OfertaComercialFamiliaLaudo | None = None) -> str:
    macro = str(getattr(familia, "macro_categoria", "") or "").strip()
    pacote = str(getattr(oferta, "pacote_comercial", "") or "").strip()
    return macro or pacote or "Catálogo oficial"


def _review_mode_meta(value: Any) -> dict[str, str]:
    key = _normalizar_chave_catalogo(value, max_len=40)
    if key not in _REVIEW_MODE_LABELS:
        return {"key": "inherit", "label": "Herdar"}
    return {"key": key, "label": _REVIEW_MODE_LABELS[key]}


def _release_status_meta(value: Any) -> dict[str, str]:
    key = str(value or "").strip().lower() or "draft"
    return {"key": key, "label": _RELEASE_STATUS_LABELS.get(key, key)}


def _activation_block_reason_meta(reason: Any) -> dict[str, str] | None:
    key = str(reason or "").strip().lower()
    if not key:
        return None
    return {"key": key, "label": _ACTIVATION_BLOCK_REASON_LABELS.get(key, key)}


def _offer_lifecycle_status(oferta: OfertaComercialFamiliaLaudo | None) -> str:
    lifecycle = str(getattr(oferta, "lifecycle_status", "") or "").strip().lower()
    if lifecycle:
        return lifecycle
    return "active" if bool(getattr(oferta, "ativo_comercial", False)) else "draft"


def _offer_is_catalog_active(oferta: OfertaComercialFamiliaLaudo | None) -> bool:
    return _offer_lifecycle_status(oferta) == "active"


def catalog_offer_variants(
    familia: FamiliaLaudoCatalogo,
    oferta: OfertaComercialFamiliaLaudo | None,
) -> list[dict[str, Any]]:
    raw_variants = list(getattr(oferta, "variantes_json", None) or []) if oferta is not None else []
    variants = [item for item in raw_variants if isinstance(item, dict)]
    if variants:
        return variants

    family_key = str(getattr(familia, "family_key", "") or "").strip().lower()
    template_default_code = _normalizar_chave_catalogo(
        getattr(oferta, "template_default_code", None),
        max_len=80,
    )
    runtime_template_code = resolve_runtime_template_code(
        family_key=family_key,
        template_code=template_default_code,
        variant_key="padrao",
    )
    if not template_default_code and not runtime_template_code:
        return []

    offer_name = (
        str(getattr(oferta, "nome_oferta", "") or "").strip()
        or str(getattr(familia, "nome_exibicao", "") or "").strip()
        or family_key
    )
    variant_key = template_default_code or "padrao"
    return [
        {
            "variant_key": variant_key,
            "nome_exibicao": "Modelo principal",
            "template_code": template_default_code or None,
            "uso_recomendado": f"Modelo principal da oferta {offer_name}.",
            "ordem": 1,
            "synthetic_fallback": True,
        }
    ]


def _override_meta(value: Any) -> dict[str, str]:
    if isinstance(value, bool):
        return {"key": "allow" if value else "deny", "label": "Permitir explicitamente" if value else "Bloquear explicitamente"}
    return {"key": "inherit", "label": "Herdar política da família"}


def _family_review_governance_summary(familia: FamiliaLaudoCatalogo) -> dict[str, Any]:
    payload = (
        dict(getattr(familia, "review_policy_json", None) or {})
        if isinstance(getattr(familia, "review_policy_json", None), dict)
        else {}
    )
    tenant_entitlements = (
        dict(payload.get("tenant_entitlements") or {})
        if isinstance(payload.get("tenant_entitlements"), dict)
        else {}
    )
    red_flags = list(payload.get("red_flags") or [])
    return {
        "default_review_mode": _review_mode_meta(payload.get("default_review_mode")),
        "max_review_mode": _review_mode_meta(payload.get("max_review_mode")),
        "red_flags_count": len([item for item in red_flags if isinstance(item, dict)]),
        "requires_release_active": bool(tenant_entitlements.get("requires_release_active")),
    }


def _tenant_plan_snapshot(banco: Session, empresa: Empresa | None) -> dict[str, Any]:
    if empresa is None:
        return {}
    limites = empresa.obter_limites(banco)
    return {
        "usuarios_max": getattr(limites, "usuarios_max", None),
        "laudos_mes": getattr(limites, "laudos_mes", None),
        "upload_doc": bool(getattr(limites, "upload_doc", False)),
        "deep_research": bool(getattr(limites, "deep_research", False)),
        "integracoes_max": getattr(limites, "integracoes_max", None),
        "retencao_dias": getattr(limites, "retencao_dias", None),
    }


def _tenant_release_summary(
    release: TenantFamilyReleaseLaudo | None,
    *,
    offer: OfertaComercialFamiliaLaudo | None = None,
    plan_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = (
        dict(getattr(release, "governance_policy_json", None) or {})
        if release is not None
        and isinstance(getattr(release, "governance_policy_json", None), dict)
        else {}
    )
    commercial = summarize_release_contract_governance(
        payload,
        offer_flags_payload=getattr(offer, "flags_json", None) if offer is not None else None,
        offer_lifecycle_status=str(getattr(offer, "lifecycle_status", "") or "").strip().lower() or None,
        plan_snapshot=plan_snapshot,
    )
    return {
        "exists": release is not None,
        "release_status": _release_status_meta(getattr(release, "release_status", None)),
        "default_template_code": str(getattr(release, "default_template_code", "") or "").strip() or None,
        "allowed_templates": list(getattr(release, "allowed_templates_json", None) or []) if release is not None else [],
        "allowed_variants": list(getattr(release, "allowed_variants_json", None) or []) if release is not None else [],
        "allowed_modes": list(getattr(release, "allowed_modes_json", None) or []) if release is not None else [],
        "allowed_offers": list(getattr(release, "allowed_offers_json", None) or []) if release is not None else [],
        "observacoes": str(getattr(release, "observacoes", "") or "").strip() or None,
        "force_review_mode": _review_mode_meta(payload.get("force_review_mode")),
        "max_review_mode": _review_mode_meta(payload.get("max_review_mode")),
        "mobile_review_override": _override_meta(payload.get("mobile_review_override")),
        "mobile_autonomous_override": _override_meta(payload.get("mobile_autonomous_override")),
        "release_channel_override": commercial["release_channel_override"],
        "effective_release_channel": commercial["effective_release_channel"],
        "contract_entitlements_override": commercial["contract_entitlements_override"],
        "effective_contract_entitlements": commercial["effective_contract_entitlements"],
        "has_governance_overrides": any(
            item in payload for item in (
                "force_review_mode",
                "max_review_mode",
                "mobile_review_override",
                "mobile_autonomous_override",
                "release_channel_override",
                "contract_entitlements",
            )
        ),
    }


def _legacy_template_options() -> list[dict[str, Any]]:
    opcoes: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for codigo in _LEGACY_TEMPLATE_ORDER:
        runtime = normalizar_tipo_template(codigo)
        if runtime in vistos:
            continue
        vistos.add(runtime)
        opcoes.append(
            {
                "value": runtime,
                "label": TIPOS_TEMPLATE_VALIDOS.get(runtime, runtime),
                "family_key": None,
                "family_label": None,
                "variant_key": None,
                "variant_label": TIPOS_TEMPLATE_VALIDOS.get(runtime, runtime),
                "offer_name": None,
                "group_label": _LEGACY_TEMPLATE_GROUPS.get(runtime, "Modelos técnicos"),
                "runtime_template_code": runtime,
                "runtime_template_label": TIPOS_TEMPLATE_VALIDOS.get(runtime, runtime),
                "selection_token": None,
                "governed": False,
            }
        )
    return opcoes


def _tenant_catalog_permissions(*, managed_by_admin_ceo: bool) -> dict[str, Any]:
    return {
        "managed_by_admin_ceo": bool(managed_by_admin_ceo),
        "allow_catalog_edit": False,
        "allow_template_edit": False,
        "allow_branding_edit": True,
    }


def _normalize_slug_list(
    values: Any,
    *,
    max_len: int,
) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        raw_values = [item.strip() for item in values.split(",")]
    elif isinstance(values, (list, tuple, set)):
        raw_values = [str(item or "").strip() for item in values]
    else:
        raw_values = [str(values or "").strip()]
    normalized = {
        _normalizar_chave_catalogo(item, max_len=max_len)
        for item in raw_values
        if str(item or "").strip()
    }
    return {item for item in normalized if item}


def _normalize_selection_token_list(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        raw_values = [item.strip() for item in values.split(",")]
    elif isinstance(values, (list, tuple, set)):
        raw_values = [str(item or "").strip() for item in values]
    else:
        raw_values = [str(values or "").strip()]
    return {str(item or "").strip().lower() for item in raw_values if str(item or "").strip()}


def _activation_record_key(item: AtivacaoCatalogoEmpresaLaudo) -> tuple[str, str] | None:
    family_key = str(getattr(item, "family_key", "") or "").strip().lower()
    variant_key = str(getattr(item, "variant_key", "") or "").strip().lower()
    if not family_key or not variant_key:
        return None
    return family_key, variant_key


def _activation_selection_token(item: AtivacaoCatalogoEmpresaLaudo) -> str | None:
    chave = _activation_record_key(item)
    if chave is None:
        return None
    try:
        return build_catalog_selection_token(*chave)
    except ValueError:
        return None


def _activation_offer_candidates(item: AtivacaoCatalogoEmpresaLaudo) -> set[str]:
    candidates: set[str] = set()
    oferta = getattr(item, "oferta", None)
    for raw in (
        getattr(oferta, "offer_key", None),
        getattr(oferta, "nome_oferta", None),
        getattr(item, "offer_name", None),
    ):
        normalized = _normalizar_chave_catalogo(raw, max_len=120)
        if normalized:
            candidates.add(normalized)
    return candidates


def _release_lookup_by_family(
    banco: Session,
    *,
    empresa_id: int,
) -> dict[int, TenantFamilyReleaseLaudo]:
    releases = list(
        banco.scalars(
            select(TenantFamilyReleaseLaudo)
            .options(selectinload(TenantFamilyReleaseLaudo.familia))
            .where(TenantFamilyReleaseLaudo.tenant_id == int(empresa_id))
        ).all()
    )
    return {
        int(item.family_id): item
        for item in releases
        if int(getattr(item, "family_id", 0) or 0) > 0
    }


def _activation_effective_state(
    item: AtivacaoCatalogoEmpresaLaudo,
    *,
    release: TenantFamilyReleaseLaudo | None,
) -> tuple[bool, str | None]:
    if release is None:
        return True, None

    release_status = str(getattr(release, "release_status", "") or "").strip().lower() or "draft"
    if release_status != "active":
        return False, "release_inactive"

    allowed_variants = _normalize_selection_token_list(getattr(release, "allowed_variants_json", None))
    selection_token = _activation_selection_token(item)
    if allowed_variants and (not selection_token or selection_token not in allowed_variants):
        return False, "variant_not_released"

    allowed_templates = _normalize_slug_list(getattr(release, "allowed_templates_json", None), max_len=80)
    runtime_template_code = _normalizar_chave_catalogo(getattr(item, "runtime_template_code", None), max_len=80)
    if allowed_templates and runtime_template_code not in allowed_templates:
        return False, "template_not_released"

    allowed_offers = _normalize_slug_list(getattr(release, "allowed_offers_json", None), max_len=120)
    if allowed_offers and _activation_offer_candidates(item).isdisjoint(allowed_offers):
        return False, "offer_not_released"

    return True, None


def _tenant_catalog_management_state(
    banco: Session,
    *,
    empresa_id: int,
) -> dict[str, Any]:
    raw_activations = list(
        banco.scalars(
            select(AtivacaoCatalogoEmpresaLaudo)
            .options(
                selectinload(AtivacaoCatalogoEmpresaLaudo.familia),
                selectinload(AtivacaoCatalogoEmpresaLaudo.oferta),
            )
            .where(
                AtivacaoCatalogoEmpresaLaudo.empresa_id == int(empresa_id),
                AtivacaoCatalogoEmpresaLaudo.ativo.is_(True),
            )
            .order_by(
                AtivacaoCatalogoEmpresaLaudo.family_key.asc(),
                AtivacaoCatalogoEmpresaLaudo.variant_ordem.asc(),
                AtivacaoCatalogoEmpresaLaudo.variant_label.asc(),
                AtivacaoCatalogoEmpresaLaudo.id.asc(),
            )
        ).all()
    )
    release_lookup = _release_lookup_by_family(banco, empresa_id=int(empresa_id))
    effective_activations: list[AtivacaoCatalogoEmpresaLaudo] = []
    raw_lookup: dict[tuple[str, str], AtivacaoCatalogoEmpresaLaudo] = {}
    effective_lookup: dict[tuple[str, str], AtivacaoCatalogoEmpresaLaudo] = {}
    blocked_reasons_by_key: dict[tuple[str, str], str] = {}
    blocked_reasons_by_token: dict[str, str] = {}

    for item in raw_activations:
        record_key = _activation_record_key(item)
        if record_key is None:
            continue
        raw_lookup[record_key] = item
        release = release_lookup.get(int(getattr(item, "family_id", 0) or 0))
        effective, reason = _activation_effective_state(item, release=release)
        if effective:
            effective_lookup[record_key] = item
            effective_activations.append(item)
            continue
        if reason:
            blocked_reasons_by_key[record_key] = reason
            selection_token = _activation_selection_token(item)
            if selection_token:
                blocked_reasons_by_token[selection_token] = reason

    has_activation_records = (
        banco.scalar(
            select(AtivacaoCatalogoEmpresaLaudo.id)
            .where(AtivacaoCatalogoEmpresaLaudo.empresa_id == int(empresa_id))
            .limit(1)
        )
        is not None
    )
    has_release_records = bool(release_lookup)
    managed_by_admin_ceo = bool(has_activation_records or has_release_records)
    catalog_state = (
        "managed_active"
        if effective_activations
        else "managed_empty"
        if managed_by_admin_ceo
        else "legacy_open"
    )
    return {
        "managed_by_admin_ceo": managed_by_admin_ceo,
        "catalog_state": catalog_state,
        "permissions": _tenant_catalog_permissions(managed_by_admin_ceo=managed_by_admin_ceo),
        "has_activation_records": has_activation_records,
        "has_release_records": has_release_records,
        "raw_lookup": raw_lookup,
        "effective_lookup": effective_lookup,
        "effective_activations": effective_activations,
        "blocked_reasons_by_key": blocked_reasons_by_key,
        "blocked_reasons_by_token": blocked_reasons_by_token,
    }


def list_active_tenant_catalog_activations(
    banco: Session,
    *,
    empresa_id: int,
) -> list[AtivacaoCatalogoEmpresaLaudo]:
    state = _tenant_catalog_management_state(banco, empresa_id=int(empresa_id))
    return list(state["effective_activations"])


def build_tenant_template_option_snapshot(
    banco: Session,
    *,
    empresa_id: int,
) -> dict[str, Any]:
    management_state = _tenant_catalog_management_state(banco, empresa_id=int(empresa_id))
    ativacoes = list(management_state["effective_activations"])
    if not ativacoes:
        if management_state["managed_by_admin_ceo"]:
            return {
                "governed_mode": True,
                "managed_by_admin_ceo": True,
                "catalog_state": management_state["catalog_state"],
                "permissions": dict(management_state["permissions"]),
                "options": [],
                "activation_count": 0,
                "runtime_codes": [],
            }
        opcoes = _legacy_template_options()
        return {
            "governed_mode": False,
            "managed_by_admin_ceo": False,
            "catalog_state": management_state["catalog_state"],
            "permissions": dict(management_state["permissions"]),
            "options": opcoes,
            "activation_count": 0,
            "runtime_codes": [item["runtime_template_code"] for item in opcoes],
        }

    opcoes = [
        {
            "value": build_catalog_selection_token(item.family_key, item.variant_key),
            "label": f"{item.family_label} · {item.variant_label}",
            "family_key": item.family_key,
            "family_label": item.family_label,
            "variant_key": item.variant_key,
            "variant_label": item.variant_label,
            "offer_name": item.offer_name,
            "group_label": item.group_label,
            "runtime_template_code": item.runtime_template_code,
            "runtime_template_label": TIPOS_TEMPLATE_VALIDOS.get(
                item.runtime_template_code,
                item.runtime_template_code,
            ),
            "selection_token": build_catalog_selection_token(item.family_key, item.variant_key),
            "governed": True,
        }
        for item in ativacoes
    ]
    runtime_codes = sorted(
        {str(item.runtime_template_code or "").strip().lower() for item in ativacoes if str(item.runtime_template_code or "").strip()}
    )
    return {
        "governed_mode": True,
        "managed_by_admin_ceo": True,
        "catalog_state": management_state["catalog_state"],
        "permissions": dict(management_state["permissions"]),
        "options": opcoes,
        "activation_count": len(opcoes),
        "runtime_codes": runtime_codes,
    }


def build_admin_tenant_catalog_snapshot(
    banco: Session,
    *,
    empresa_id: int,
) -> dict[str, Any]:
    empresa = banco.get(Empresa, int(empresa_id))
    plan_snapshot = _tenant_plan_snapshot(banco, empresa)
    ofertas = list(
        banco.scalars(
            select(FamiliaLaudoCatalogo)
            .options(
                selectinload(FamiliaLaudoCatalogo.oferta_comercial),
                selectinload(FamiliaLaudoCatalogo.tenant_releases),
            )
            .where(FamiliaLaudoCatalogo.status_catalogo == "publicado")
            .order_by(FamiliaLaudoCatalogo.macro_categoria.asc(), FamiliaLaudoCatalogo.nome_exibicao.asc())
        ).all()
    )
    management_state = _tenant_catalog_management_state(banco, empresa_id=int(empresa_id))
    ativacoes = list(management_state["effective_activations"])
    ativacoes_por_chave = dict(management_state["effective_lookup"])
    ativacoes_registradas_por_chave = dict(management_state["raw_lookup"])
    blocked_reasons_by_key = dict(management_state["blocked_reasons_by_key"])

    familias: list[dict[str, Any]] = []
    total_variantes_disponiveis = 0
    total_variantes_operacionais = 0
    for familia in ofertas:
        oferta = getattr(familia, "oferta_comercial", None)
        if oferta is None or not _offer_is_catalog_active(oferta):
            continue
        tenant_release = next(
            (
                item
                for item in list(getattr(familia, "tenant_releases", None) or [])
                if int(getattr(item, "tenant_id", 0) or 0) == int(empresa_id)
            ),
            None,
        )
        variantes = []
        for variante in catalog_offer_variants(familia, oferta):
            if not isinstance(variante, dict):
                continue
            variant_key = _normalizar_chave_catalogo(variante.get("variant_key"), max_len=80)
            if not variant_key:
                continue
            family_key = str(getattr(familia, "family_key", "") or "").strip().lower()
            token = build_catalog_selection_token(family_key, variant_key)
            runtime_template_code = resolve_runtime_template_code(
                family_key=family_key,
                template_code=variante.get("template_code"),
                variant_key=variant_key,
            )
            ativacao = ativacoes_por_chave.get((family_key, variant_key))
            ativacao_registrada = ativacoes_registradas_por_chave.get((family_key, variant_key))
            blocked_reason = blocked_reasons_by_key.get((family_key, variant_key))
            operacional = bool(runtime_template_code)
            total_variantes_disponiveis += 1
            if operacional:
                total_variantes_operacionais += 1
            variantes.append(
                {
                    "selection_token": token,
                    "variant_key": variant_key,
                    "variant_label": str(variante.get("nome_exibicao") or variant_key).strip() or variant_key,
                    "template_code": str(variante.get("template_code") or "").strip() or None,
                    "uso_recomendado": str(variante.get("uso_recomendado") or "").strip() or None,
                    "ordem": int(variante.get("ordem") or 0),
                    "runtime_template_code": runtime_template_code,
                    "runtime_template_label": TIPOS_TEMPLATE_VALIDOS.get(runtime_template_code or "", "Não operacional"),
                    "is_active": ativacao is not None,
                    "has_activation_record": ativacao_registrada is not None,
                    "is_operational": operacional,
                    "is_selectable_for_tenant": operacional and blocked_reason is None,
                    "availability_state": (
                        "active"
                        if ativacao is not None
                        else "blocked"
                        if blocked_reason is not None
                        else "available"
                        if operacional
                        else "unmapped"
                    ),
                    "availability_reason": _activation_block_reason_meta(blocked_reason),
                }
            )
        if not variantes:
            continue
        def _variant_sort_key(item: dict[str, Any]) -> tuple[int, str]:
            raw_ordem = item.get("ordem")
            return (
                int(raw_ordem) if isinstance(raw_ordem, (int, str)) else 0,
                str(item.get("variant_label") or "").lower(),
            )

        variantes.sort(key=_variant_sort_key)
        offer_governance = summarize_offer_commercial_governance(
            getattr(oferta, "flags_json", None),
            offer_lifecycle_status=str(getattr(oferta, "lifecycle_status", "") or "").strip().lower() or None,
        )
        familias.append(
            {
                "family_id": int(familia.id),
                "family_key": str(familia.family_key),
                "family_label": str(familia.nome_exibicao),
                "family_description": str(getattr(familia, "descricao", "") or "").strip() or None,
                "group_label": _family_group_label(familia, oferta),
                "offer_id": int(oferta.id),
                "offer_key": str(getattr(oferta, "offer_key", "") or "").strip() or None,
                "offer_name": str(getattr(oferta, "nome_oferta", "") or "").strip() or str(familia.nome_exibicao),
                "offer_package": str(getattr(oferta, "pacote_comercial", "") or "").strip() or None,
                "offer_deadline_days": int(getattr(oferta, "prazo_padrao_dias", 0) or 0) or None,
                "offer_release_channel": offer_governance["release_channel"],
                "offer_bundle": offer_governance["commercial_bundle"],
                "offer_contract_entitlements": offer_governance["contract_entitlements"],
                "material_real_status": str(getattr(oferta, "material_real_status", "") or "").strip() or None,
                "review_governance": _family_review_governance_summary(familia),
                "tenant_release": _tenant_release_summary(
                    tenant_release,
                    offer=oferta,
                    plan_snapshot=plan_snapshot,
                ),
                "variantes": variantes,
                "active_variants_count": sum(1 for item in variantes if bool(item["is_active"])),
            }
        )

    familias.sort(key=lambda item: (str(item["group_label"]).lower(), str(item["family_label"]).lower()))
    return {
        "families": familias,
        "active_activation_count": len(ativacoes),
        "active_family_count": sum(1 for item in familias if int(item["active_variants_count"]) > 0),
        "governed_mode": bool(management_state["managed_by_admin_ceo"]),
        "managed_by_admin_ceo": bool(management_state["managed_by_admin_ceo"]),
        "catalog_state": str(management_state["catalog_state"]),
        "permissions": dict(management_state["permissions"]),
        "available_variant_count": total_variantes_disponiveis,
        "operational_variant_count": total_variantes_operacionais,
    }


def sync_tenant_catalog_activations(
    banco: Session,
    *,
    empresa_id: int,
    selection_tokens: list[str] | tuple[str, ...],
    admin_id: int | None = None,
) -> dict[str, Any]:
    snapshot = build_admin_tenant_catalog_snapshot(banco, empresa_id=int(empresa_id))
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for familia in snapshot["families"]:
        for variante in familia["variantes"]:
            lookup[(str(familia["family_key"]).lower(), str(variante["variant_key"]).lower())] = {
                "family_id": int(familia["family_id"]),
                "family_key": str(familia["family_key"]).lower(),
                "family_label": str(familia["family_label"]),
                "group_label": str(familia["group_label"]),
                "offer_id": int(familia["offer_id"]),
                "offer_name": str(familia["offer_name"]),
                "variant_key": str(variante["variant_key"]).lower(),
                "variant_label": str(variante["variant_label"]),
                "runtime_template_code": variante["runtime_template_code"],
                "ordem": int(variante["ordem"]),
                "is_selectable_for_tenant": bool(variante.get("is_selectable_for_tenant")),
                "availability_state": str(variante.get("availability_state") or ""),
                "availability_reason": (
                    str((variante.get("availability_reason") or {}).get("label") or "").strip()
                ),
            }

    tokens_normalizados: list[tuple[str, str]] = []
    vistos: set[tuple[str, str]] = set()
    for bruto in selection_tokens:
        parsed = parse_catalog_selection_token(bruto)
        if parsed is None:
            raise ValueError("Seleção de variante comercial inválida.")
        if parsed in vistos:
            continue
        vistos.add(parsed)
        tokens_normalizados.append(parsed)

    for chave in tokens_normalizados:
        item = lookup.get(chave)
        if item is None:
            raise ValueError("A variante escolhida não está disponível no catálogo oficial.")
        if not bool(item["is_selectable_for_tenant"]):
            detalhe = str(item.get("availability_reason") or "").strip()
            if detalhe:
                raise ValueError(detalhe)
            raise ValueError("A variante escolhida não está liberada para este tenant.")
        if not item["runtime_template_code"]:
            raise ValueError("A variante escolhida ainda não possui runtime operacional no produto.")

    existentes = list(
        banco.scalars(
            select(AtivacaoCatalogoEmpresaLaudo).where(
                AtivacaoCatalogoEmpresaLaudo.empresa_id == int(empresa_id)
            )
        ).all()
    )
    existentes_por_chave = {
        (str(item.family_key or "").strip().lower(), str(item.variant_key or "").strip().lower()): item
        for item in existentes
    }

    ativadas: list[str] = []
    reativadas: list[str] = []
    desativadas: list[str] = []
    selecionadas = set(tokens_normalizados)

    for chave, item in lookup.items():
        registro = existentes_por_chave.get(chave)
        if chave in selecionadas:
            if registro is None:
                registro = AtivacaoCatalogoEmpresaLaudo(
                    empresa_id=int(empresa_id),
                    family_id=item["family_id"],
                    oferta_id=item["offer_id"],
                    family_key=item["family_key"],
                    family_label=item["family_label"],
                    group_label=item["group_label"],
                    offer_name=item["offer_name"],
                    variant_key=item["variant_key"],
                    variant_label=item["variant_label"],
                    variant_ordem=item["ordem"],
                    runtime_template_code=item["runtime_template_code"],
                    criado_por_id=int(admin_id) if admin_id is not None else None,
                    ativo=True,
                )
                banco.add(registro)
                ativadas.append(build_catalog_selection_token(*chave))
            else:
                reativando = not bool(registro.ativo)
                registro.family_label = item["family_label"]
                registro.group_label = item["group_label"]
                registro.family_id = item["family_id"]
                registro.oferta_id = item["offer_id"]
                registro.offer_name = item["offer_name"]
                registro.variant_label = item["variant_label"]
                registro.variant_ordem = item["ordem"]
                registro.runtime_template_code = item["runtime_template_code"]
                registro.ativo = True
                admin_id_int = (
                    int(admin_id)
                    if isinstance(admin_id, (int, str)) and int(admin_id) > 0
                    else 0
                )
                if admin_id_int > 0:
                    registro.criado_por_id = admin_id_int
                if reativando:
                    reativadas.append(build_catalog_selection_token(*chave))

    for chave, registro in existentes_por_chave.items():
        if chave in selecionadas or not bool(registro.ativo):
            continue
        registro.ativo = False
        desativadas.append(build_catalog_selection_token(*chave))

    management_state = _tenant_catalog_management_state(banco, empresa_id=int(empresa_id))
    return {
        "activated": ativadas,
        "reactivated": reativadas,
        "deactivated": desativadas,
        "selected_count": len(selecionadas),
        "governed_mode": bool(management_state["managed_by_admin_ceo"]),
        "catalog_state": str(management_state["catalog_state"]),
    }


def resolve_tenant_template_request(
    banco: Session,
    *,
    empresa_id: int,
    requested_value: Any,
) -> dict[str, Any]:
    bruto = str(requested_value or "").strip().lower() or "padrao"
    management_state = _tenant_catalog_management_state(banco, empresa_id=int(empresa_id))
    ativacoes = list(management_state["effective_activations"])
    if not ativacoes:
        if management_state["managed_by_admin_ceo"]:
            raise PermissionError("Este tenant não possui templates liberados pelo Admin-CEO no momento.")
        if bruto not in ALIASES_TEMPLATE:
            raise ValueError("Tipo de relatório inválido.")
        runtime = normalizar_tipo_template(bruto)
        return {
            "governed_mode": False,
            "catalog_state": management_state["catalog_state"],
            "requested_value": bruto,
            "runtime_template_code": runtime,
            "family_key": None,
            "family_label": None,
            "variant_key": None,
            "variant_label": None,
            "offer_name": None,
            "selection_token": None,
            "compatibility_mode": False,
        }

    ativacao_por_token = {
        build_catalog_selection_token(item.family_key, item.variant_key): item
        for item in ativacoes
    }
    ativacoes_por_runtime: dict[str, list[AtivacaoCatalogoEmpresaLaudo]] = defaultdict(list)
    for item in ativacoes:
        ativacoes_por_runtime[str(item.runtime_template_code or "").strip().lower()].append(item)

    ativacao = ativacao_por_token.get(bruto)
    compatibility_mode = False
    if ativacao is None:
        if bruto not in ALIASES_TEMPLATE:
            raise ValueError("Tipo de relatório inválido.")
        runtime = normalizar_tipo_template(bruto)
        candidatas = ativacoes_por_runtime.get(runtime, [])
        if not candidatas:
            raise PermissionError("Este template não está habilitado para o tenant.")
        if len(candidatas) > 1:
            raise PermissionError("Este tenant exige a escolha explícita da variante comercial.")
        ativacao = candidatas[0]
        compatibility_mode = True

    return {
        "governed_mode": True,
        "catalog_state": management_state["catalog_state"],
        "requested_value": bruto,
        "runtime_template_code": str(ativacao.runtime_template_code or "padrao").strip().lower() or "padrao",
        "family_key": str(ativacao.family_key or "").strip() or None,
        "family_label": str(ativacao.family_label or "").strip() or None,
        "variant_key": str(ativacao.variant_key or "").strip() or None,
        "variant_label": str(ativacao.variant_label or "").strip() or None,
        "offer_name": str(ativacao.offer_name or "").strip() or None,
        "selection_token": build_catalog_selection_token(ativacao.family_key, ativacao.variant_key),
        "compatibility_mode": compatibility_mode,
    }


__all__ = [
    "CATALOGO_TOKEN_PREFIX",
    "build_admin_tenant_catalog_snapshot",
    "build_catalog_selection_token",
    "build_tenant_template_option_snapshot",
    "catalog_offer_variants",
    "list_active_tenant_catalog_activations",
    "parse_catalog_selection_token",
    "resolve_runtime_template_code",
    "resolve_tenant_template_request",
    "sync_tenant_catalog_activations",
]
