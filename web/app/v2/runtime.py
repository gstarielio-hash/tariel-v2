"""Runtime incremental do V2 com flags e helpers leves."""

from __future__ import annotations

from typing import Any

from app.core.settings import env_bool, env_str
from app.shared.database import NivelAcesso

V2_ENVELOPES_FLAG = "TARIEL_V2_ENVELOPES"
V2_CASE_CORE_ACL_FLAG = "TARIEL_V2_CASE_CORE_ACL"
V2_INSPECTOR_PROJECTION_FLAG = "TARIEL_V2_INSPECTOR_PROJECTION"
V2_REVIEW_DESK_PROJECTION_FLAG = "TARIEL_V2_REVIEW_DESK_PROJECTION"
V2_REVIEW_DESK_PROJECTION_PREFER_FLAG = "TARIEL_V2_REVIEW_DESK_PROJECTION_PREFER"
V2_REVIEW_QUEUE_PROJECTION_FLAG = "TARIEL_V2_REVIEW_QUEUE_PROJECTION"
V2_REVIEW_QUEUE_PROJECTION_PREFER_FLAG = "TARIEL_V2_REVIEW_QUEUE_PROJECTION_PREFER"
V2_PROVENANCE_FLAG = "TARIEL_V2_PROVENANCE"
V2_POLICY_ENGINE_FLAG = "TARIEL_V2_POLICY_ENGINE"
V2_DOCUMENT_FACADE_FLAG = "TARIEL_V2_DOCUMENT_FACADE"
V2_DOCUMENT_SHADOW_FLAG = "TARIEL_V2_DOCUMENT_SHADOW"
V2_DOCUMENT_SOFT_GATE_FLAG = "TARIEL_V2_DOCUMENT_SOFT_GATE"
V2_DOCUMENT_HARD_GATE_FLAG = "TARIEL_V2_DOCUMENT_HARD_GATE"
V2_TENANT_ADMIN_PROJECTION_FLAG = "TARIEL_V2_TENANT_ADMIN_PROJECTION"
V2_PLATFORM_ADMIN_PROJECTION_FLAG = "TARIEL_V2_PLATFORM_ADMIN_PROJECTION"
V2_DOCUMENT_HARD_GATE_ENFORCE_FLAG = "TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE"
V2_DOCUMENT_HARD_GATE_TENANTS_FLAG = "TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS"
V2_DOCUMENT_HARD_GATE_OPERATIONS_FLAG = "TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS"
V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES_FLAG = "TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES"
V2_ANDROID_CASE_ADAPTER_FLAG = "TARIEL_V2_ANDROID_CASE_ADAPTER"
V2_ANDROID_FEED_ADAPTER_FLAG = "TARIEL_V2_ANDROID_FEED_ADAPTER"
V2_ANDROID_THREAD_ADAPTER_FLAG = "TARIEL_V2_ANDROID_THREAD_ADAPTER"
V2_ANDROID_PUBLIC_CONTRACT_FLAG = "TARIEL_V2_ANDROID_PUBLIC_CONTRACT"
V2_MOBILE_AUTONOMY_TEMPLATES_FLAG = "TARIEL_V2_MOBILE_AUTONOMY_TEMPLATES"
V2_MOBILE_AUTONOMY_TENANTS_FLAG = "TARIEL_V2_MOBILE_AUTONOMY_TENANTS"


def v2_envelopes_enabled() -> bool:
    return env_bool(V2_ENVELOPES_FLAG, False)


def v2_case_core_acl_enabled() -> bool:
    return env_bool(V2_CASE_CORE_ACL_FLAG, False)


def v2_inspector_projection_enabled() -> bool:
    return env_bool(V2_INSPECTOR_PROJECTION_FLAG, False)


def v2_review_desk_projection_enabled() -> bool:
    return env_bool(V2_REVIEW_DESK_PROJECTION_FLAG, False)


def v2_review_desk_projection_prefer_enabled() -> bool:
    return v2_review_desk_projection_enabled() and env_bool(
        V2_REVIEW_DESK_PROJECTION_PREFER_FLAG,
        False,
    )


def v2_review_queue_projection_enabled() -> bool:
    return env_bool(V2_REVIEW_QUEUE_PROJECTION_FLAG, False)


def v2_review_queue_projection_prefer_enabled() -> bool:
    return v2_review_queue_projection_enabled() and env_bool(
        V2_REVIEW_QUEUE_PROJECTION_PREFER_FLAG,
        False,
    )


def v2_provenance_enabled() -> bool:
    return env_bool(V2_PROVENANCE_FLAG, False)


def v2_policy_engine_enabled() -> bool:
    return env_bool(V2_POLICY_ENGINE_FLAG, False)


def v2_document_facade_enabled() -> bool:
    return env_bool(V2_DOCUMENT_FACADE_FLAG, False)


def v2_document_shadow_enabled() -> bool:
    return env_bool(V2_DOCUMENT_SHADOW_FLAG, False)


def v2_document_soft_gate_enabled() -> bool:
    return env_bool(V2_DOCUMENT_SOFT_GATE_FLAG, False)


def _env_csv(nome: str) -> tuple[str, ...]:
    return tuple(
        item
        for item in (
            str(parte or "").strip()
            for parte in env_str(nome, "").split(",")
        )
        if item
    )


def v2_document_hard_gate_enabled() -> bool:
    return env_bool(V2_DOCUMENT_HARD_GATE_FLAG, False)


def v2_tenant_admin_projection_enabled() -> bool:
    return env_bool(V2_TENANT_ADMIN_PROJECTION_FLAG, False)


def v2_platform_admin_projection_enabled() -> bool:
    return env_bool(V2_PLATFORM_ADMIN_PROJECTION_FLAG, False)


def v2_document_hard_gate_enforce_enabled() -> bool:
    return env_bool(V2_DOCUMENT_HARD_GATE_ENFORCE_FLAG, False)


def v2_document_hard_gate_tenant_allowlist() -> tuple[str, ...]:
    return _env_csv(V2_DOCUMENT_HARD_GATE_TENANTS_FLAG)


def v2_document_hard_gate_operation_allowlist() -> tuple[str, ...]:
    return _env_csv(V2_DOCUMENT_HARD_GATE_OPERATIONS_FLAG)


def v2_document_hard_gate_template_code_allowlist() -> tuple[str, ...]:
    return _env_csv(V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES_FLAG)


def v2_android_case_adapter_enabled() -> bool:
    return env_bool(V2_ANDROID_CASE_ADAPTER_FLAG, False)


def v2_android_feed_adapter_enabled() -> bool:
    return env_bool(V2_ANDROID_FEED_ADAPTER_FLAG, False)


def v2_android_thread_adapter_enabled() -> bool:
    return env_bool(V2_ANDROID_THREAD_ADAPTER_FLAG, False)


def v2_android_public_contract_enabled() -> bool:
    return env_bool(V2_ANDROID_PUBLIC_CONTRACT_FLAG, False)


def v2_mobile_autonomy_template_allowlist() -> tuple[str, ...]:
    configured = _env_csv(V2_MOBILE_AUTONOMY_TEMPLATES_FLAG)
    return configured or ("nr35_linha_vida", "cbmgo")


def v2_mobile_autonomy_tenant_allowlist() -> tuple[str, ...]:
    return _env_csv(V2_MOBILE_AUTONOMY_TENANTS_FLAG)


def actor_role_from_user(usuario: Any) -> str:
    nivel = getattr(usuario, "nivel_acesso", None)
    if not isinstance(nivel, (int, float, str, bytes, bytearray)):
        return "unknown"

    try:
        nivel_int = int(nivel)
    except (TypeError, ValueError):
        return "unknown"

    mapa = {
        int(NivelAcesso.INSPETOR): "inspetor",
        int(NivelAcesso.REVISOR): "revisor",
        int(NivelAcesso.ADMIN_CLIENTE): "admin_cliente",
        int(NivelAcesso.DIRETORIA): "diretoria",
    }
    return mapa.get(nivel_int, "unknown")


__all__ = [
    "V2_CASE_CORE_ACL_FLAG",
    "V2_ANDROID_CASE_ADAPTER_FLAG",
    "V2_ANDROID_FEED_ADAPTER_FLAG",
    "V2_ANDROID_PUBLIC_CONTRACT_FLAG",
    "V2_ANDROID_THREAD_ADAPTER_FLAG",
    "V2_DOCUMENT_FACADE_FLAG",
    "V2_DOCUMENT_HARD_GATE_ENFORCE_FLAG",
    "V2_DOCUMENT_HARD_GATE_FLAG",
    "V2_DOCUMENT_HARD_GATE_OPERATIONS_FLAG",
    "V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES_FLAG",
    "V2_DOCUMENT_HARD_GATE_TENANTS_FLAG",
    "V2_DOCUMENT_SHADOW_FLAG",
    "V2_DOCUMENT_SOFT_GATE_FLAG",
    "V2_MOBILE_AUTONOMY_TEMPLATES_FLAG",
    "V2_MOBILE_AUTONOMY_TENANTS_FLAG",
    "V2_ENVELOPES_FLAG",
    "V2_INSPECTOR_PROJECTION_FLAG",
    "V2_POLICY_ENGINE_FLAG",
    "V2_PLATFORM_ADMIN_PROJECTION_FLAG",
    "V2_PROVENANCE_FLAG",
    "V2_REVIEW_DESK_PROJECTION_PREFER_FLAG",
    "V2_REVIEW_QUEUE_PROJECTION_FLAG",
    "V2_REVIEW_DESK_PROJECTION_FLAG",
    "V2_REVIEW_QUEUE_PROJECTION_PREFER_FLAG",
    "V2_TENANT_ADMIN_PROJECTION_FLAG",
    "actor_role_from_user",
    "v2_android_case_adapter_enabled",
    "v2_android_feed_adapter_enabled",
    "v2_android_public_contract_enabled",
    "v2_android_thread_adapter_enabled",
    "v2_case_core_acl_enabled",
    "v2_document_facade_enabled",
    "v2_document_hard_gate_enabled",
    "v2_document_hard_gate_enforce_enabled",
    "v2_document_hard_gate_operation_allowlist",
    "v2_document_hard_gate_template_code_allowlist",
    "v2_document_hard_gate_tenant_allowlist",
    "v2_document_shadow_enabled",
    "v2_document_soft_gate_enabled",
    "v2_envelopes_enabled",
    "v2_inspector_projection_enabled",
    "v2_mobile_autonomy_template_allowlist",
    "v2_mobile_autonomy_tenant_allowlist",
    "v2_platform_admin_projection_enabled",
    "v2_policy_engine_enabled",
    "v2_provenance_enabled",
    "v2_review_desk_projection_prefer_enabled",
    "v2_review_queue_projection_enabled",
    "v2_review_queue_projection_prefer_enabled",
    "v2_review_desk_projection_enabled",
    "v2_tenant_admin_projection_enabled",
]
