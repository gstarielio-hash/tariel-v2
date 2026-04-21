"""Adapter incremental de billing/metering sem ler conteudo tecnico bruto."""

from __future__ import annotations

from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.shared.database import LIMITES_PADRAO, PlanoEmpresa


class TenantBillingMeteringSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_name: str
    usage_status: str
    usage_percent: int | None = None
    recommended_plan: str | None = None


class TenantPolicyCapabilitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = None
    tenant_status: str
    plan_name: str
    usage_status: str
    usage_percent: int | None = None
    recommended_plan: str | None = None
    laudos_mes_limit: int | None = None
    laudos_mes_used: int | None = None
    upload_doc_enabled: bool = False
    deep_research_enabled: bool = False


class PlatformBillingMeteringTenantSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    tenant_status: str
    tenant_name: str | None = None
    active_plan: str | None = None
    usage_counter: int = 0


class PlatformBillingMeteringSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_list_summary: list[PlatformBillingMeteringTenantSummary] = Field(default_factory=list)
    active_plans: int = 0
    plan_breakdown: dict[str, int] = Field(default_factory=dict)
    active_tenants: int = 0
    blocked_tenants: int = 0
    alert_count: int = 0
    total_usage_counter: int = 0
    total_inspections: int = 0
    total_api_revenue_brl: str = "0"
    chart_labels: list[str] = Field(default_factory=list)
    chart_values: list[int] = Field(default_factory=list)
    platform_alerts: list[str] = Field(default_factory=list)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _normalize_optional_int(value: Any) -> int | None:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _normalize_bool(value: Any) -> bool:
    return bool(value)


def _scalar_from_tenant(item: Any, *names: str) -> Any:
    for name in names:
        if hasattr(item, name):
            value = getattr(item, name)
            if value is not None:
                return value
        if isinstance(item, dict) and name in item and item.get(name) is not None:
            return item.get(name)
    return None


def _tenant_status(item: Any) -> str:
    return "blocked" if bool(_scalar_from_tenant(item, "status_bloqueio", "blocked")) else "active"


def _normalize_plan_name(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return PlanoEmpresa.INICIAL.value
    try:
        return PlanoEmpresa.normalizar(text)
    except ValueError:
        return text


def _resolve_limits_snapshot(
    *,
    tenant: Any,
    banco: Any,
    plan_name: str,
) -> dict[str, Any]:
    if tenant is not None and banco is not None and hasattr(tenant, "obter_limites"):
        try:
            limits = tenant.obter_limites(banco)
        except Exception:
            limits = None
        if limits is not None:
            return {
                "laudos_mes": getattr(limits, "laudos_mes", None),
                "upload_doc": bool(getattr(limits, "upload_doc", False)),
                "deep_research": bool(getattr(limits, "deep_research", False)),
            }

    fallback = LIMITES_PADRAO.get(plan_name, LIMITES_PADRAO[PlanoEmpresa.INICIAL.value])
    return {
        "laudos_mes": fallback.get("laudos_mes"),
        "upload_doc": bool(fallback.get("upload_doc", False)),
        "deep_research": bool(fallback.get("deep_research", False)),
    }


def _derive_usage_percent(*, laudos_mes_used: int | None, laudos_mes_limit: int | None) -> int | None:
    if laudos_mes_used is None:
        return None
    if not isinstance(laudos_mes_limit, int) or laudos_mes_limit <= 0:
        return None
    percentual = int(round((max(laudos_mes_used, 0) / laudos_mes_limit) * 100))
    return max(0, min(percentual, 100))


def _next_plan_name(plan_name: str) -> str | None:
    planos = [
        PlanoEmpresa.INICIAL.value,
        PlanoEmpresa.INTERMEDIARIO.value,
        PlanoEmpresa.ILIMITADO.value,
    ]
    try:
        indice = planos.index(_normalize_plan_name(plan_name))
    except ValueError:
        return None
    proximo = indice + 1
    if proximo >= len(planos):
        return None
    return planos[proximo]


def _resolve_usage_status(
    *,
    tenant_status: str,
    usage_status: Any,
    usage_percent: int | None,
) -> str:
    if tenant_status == "blocked":
        return "blocked"

    normalized = _normalize_text(usage_status).lower()
    if normalized:
        return normalized

    if usage_percent is None:
        return "unknown"
    if usage_percent >= 100:
        return "critico"
    if usage_percent >= 85:
        return "atencao"
    if usage_percent >= 70:
        return "monitorar"
    return "estavel"


def build_tenant_billing_metering_snapshot(
    *,
    plan_name: Any,
    usage_status: Any,
    usage_percent: int | None,
    recommended_plan: Any,
) -> TenantBillingMeteringSnapshot:
    return TenantBillingMeteringSnapshot(
        plan_name=_normalize_text(plan_name),
        usage_status=_normalize_text(usage_status) or "unknown",
        usage_percent=usage_percent if isinstance(usage_percent, int) else None,
        recommended_plan=(_normalize_text(recommended_plan) or None),
    )


def build_tenant_policy_capability_snapshot(
    *,
    tenant: Any = None,
    banco: Any = None,
    tenant_id: Any = None,
    plan_name: Any = None,
    tenant_status: Any = None,
    usage_status: Any = None,
    usage_percent: Any = None,
    recommended_plan: Any = None,
    laudos_mes_limit: Any = None,
    laudos_mes_used: Any = None,
    upload_doc_enabled: Any = None,
    deep_research_enabled: Any = None,
) -> TenantPolicyCapabilitySnapshot:
    tenant_id_text = _normalize_text(
        tenant_id if tenant_id is not None else _scalar_from_tenant(tenant, "id", "tenant_id")
    ) or None
    resolved_plan_name = _normalize_plan_name(
        plan_name if plan_name is not None else _scalar_from_tenant(tenant, "plano_ativo", "active_plan")
    )
    resolved_tenant_status = (
        _normalize_text(tenant_status).lower()
        if tenant_status is not None
        else _tenant_status(tenant)
    ) or "active"
    resolved_limits = _resolve_limits_snapshot(
        tenant=tenant,
        banco=banco,
        plan_name=resolved_plan_name,
    )
    resolved_laudos_mes_limit = (
        _normalize_optional_int(laudos_mes_limit)
        if laudos_mes_limit is not None
        else _normalize_optional_int(resolved_limits.get("laudos_mes"))
    )
    resolved_laudos_mes_used = _normalize_optional_int(laudos_mes_used)
    resolved_usage_percent = _normalize_optional_int(usage_percent)
    if resolved_usage_percent is None:
        resolved_usage_percent = _derive_usage_percent(
            laudos_mes_used=resolved_laudos_mes_used,
            laudos_mes_limit=resolved_laudos_mes_limit,
        )
    resolved_usage_status = _resolve_usage_status(
        tenant_status=resolved_tenant_status,
        usage_status=usage_status,
        usage_percent=resolved_usage_percent,
    )
    resolved_recommended_plan = _normalize_text(recommended_plan) or None
    if resolved_recommended_plan is None and resolved_usage_status in {"critico", "atencao", "monitorar"}:
        resolved_recommended_plan = _next_plan_name(resolved_plan_name)

    return TenantPolicyCapabilitySnapshot(
        tenant_id=tenant_id_text,
        tenant_status=resolved_tenant_status,
        plan_name=resolved_plan_name,
        usage_status=resolved_usage_status,
        usage_percent=resolved_usage_percent,
        recommended_plan=resolved_recommended_plan,
        laudos_mes_limit=resolved_laudos_mes_limit,
        laudos_mes_used=resolved_laudos_mes_used,
        upload_doc_enabled=(
            _normalize_bool(upload_doc_enabled)
            if upload_doc_enabled is not None
            else bool(resolved_limits.get("upload_doc", False))
        ),
        deep_research_enabled=(
            _normalize_bool(deep_research_enabled)
            if deep_research_enabled is not None
            else bool(resolved_limits.get("deep_research", False))
        ),
    )


def build_platform_billing_metering_summary(
    *,
    tenant_summaries: Iterable[Any],
    total_inspections: int,
    total_api_revenue_brl: Any,
    chart_labels: Iterable[Any],
    chart_values: Iterable[Any],
) -> PlatformBillingMeteringSummary:
    normalized_tenants = [
        PlatformBillingMeteringTenantSummary(
            tenant_id=_normalize_text(_scalar_from_tenant(item, "id", "tenant_id")),
            tenant_status=_tenant_status(item),
            tenant_name=(_normalize_text(_scalar_from_tenant(item, "nome_fantasia", "tenant_name")) or None),
            active_plan=(_normalize_text(_scalar_from_tenant(item, "plano_ativo", "active_plan")) or None),
            usage_counter=_normalize_int(_scalar_from_tenant(item, "mensagens_processadas", "usage_counter")),
        )
        for item in tenant_summaries
    ]

    plan_breakdown: dict[str, int] = {}
    platform_alerts: list[str] = []
    for item in normalized_tenants:
        if item.active_plan:
            plan_breakdown[item.active_plan] = plan_breakdown.get(item.active_plan, 0) + 1
        else:
            platform_alerts.append(f"tenant_without_plan:{item.tenant_id}")
        if item.tenant_status == "blocked":
            platform_alerts.append(f"tenant_blocked:{item.tenant_id}")

    return PlatformBillingMeteringSummary(
        tenant_list_summary=normalized_tenants,
        active_plans=sum(plan_breakdown.values()),
        plan_breakdown=plan_breakdown,
        active_tenants=sum(1 for item in normalized_tenants if item.tenant_status == "active"),
        blocked_tenants=sum(1 for item in normalized_tenants if item.tenant_status == "blocked"),
        alert_count=len(platform_alerts),
        total_usage_counter=sum(item.usage_counter for item in normalized_tenants),
        total_inspections=_normalize_int(total_inspections),
        total_api_revenue_brl=_normalize_text(total_api_revenue_brl) or "0",
        chart_labels=[_normalize_text(item) for item in chart_labels],
        chart_values=[_normalize_int(item) for item in chart_values],
        platform_alerts=platform_alerts,
    )


__all__ = [
    "PlatformBillingMeteringSummary",
    "PlatformBillingMeteringTenantSummary",
    "TenantBillingMeteringSnapshot",
    "TenantPolicyCapabilitySnapshot",
    "build_platform_billing_metering_summary",
    "build_tenant_billing_metering_snapshot",
    "build_tenant_policy_capability_snapshot",
]
