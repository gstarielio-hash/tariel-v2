"""Adapter incremental da projeção canônica do admin-geral para o dashboard legado."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.platform_admin import build_platform_admin_view_projection


class PlatformAdminDashboardShadowResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: Literal["PlatformAdminDashboardShadowResultV1"] = "PlatformAdminDashboardShadowResultV1"
    contract_version: str = "v1"
    compatible: bool
    divergences: list[str] = Field(default_factory=list)
    used_projection: bool = True
    delivery_mode: Literal["shadow_only"] = "shadow_only"
    observed_tenant_count: int = 0
    projection: dict[str, Any]


def _normalize_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def build_platform_admin_dashboard_shadow_result(
    *,
    tenant_summaries: Iterable[Any],
    total_inspections: int,
    total_api_revenue_brl: Any,
    chart_labels: Iterable[Any],
    chart_values: Iterable[Any],
    recent_admin_actions: int,
    actor_id: Any,
    actor_role: str,
    source_channel: str,
    legacy_dashboard_data: dict[str, Any],
    correlation_id: str | None = None,
    timestamp: datetime | None = None,
) -> PlatformAdminDashboardShadowResult:
    tenants = list(tenant_summaries)
    projection = build_platform_admin_view_projection(
        tenant_summaries=tenants,
        total_inspections=total_inspections,
        total_api_revenue_brl=total_api_revenue_brl,
        chart_labels=chart_labels,
        chart_values=chart_values,
        recent_admin_actions=recent_admin_actions,
        actor_id=actor_id,
        actor_role=actor_role,
        source_channel=source_channel,
        correlation_id=correlation_id,
        timestamp=timestamp,
    )
    projection_payload = projection.payload
    consumption_summary = projection_payload.get("consumption_summary", {})
    divergences: list[str] = []
    if _normalize_int(legacy_dashboard_data.get("qtd_clientes")) != len(
        projection_payload.get("tenant_list_summary", [])
    ):
        divergences.append("tenant_count")
    if _normalize_int(legacy_dashboard_data.get("total_inspecoes")) != _normalize_int(
        consumption_summary.get("total_inspections")
    ):
        divergences.append("total_inspections")
    if sum(1 for item in tenants if not bool(getattr(item, "status_bloqueio", False))) != _normalize_int(
        consumption_summary.get("active_tenants")
    ):
        divergences.append("active_tenants")
    if [str(item) for item in legacy_dashboard_data.get("labels_grafico", [])] != list(
        consumption_summary.get("chart_labels", [])
    ):
        divergences.append("chart_labels")
    if [_normalize_int(item) for item in legacy_dashboard_data.get("valores_grafico", [])] != list(
        consumption_summary.get("chart_values", [])
    ):
        divergences.append("chart_values")

    return PlatformAdminDashboardShadowResult(
        compatible=not divergences,
        divergences=divergences,
        observed_tenant_count=len(tenants),
        projection=projection.model_dump(mode="json"),
    )


__all__ = [
    "PlatformAdminDashboardShadowResult",
    "build_platform_admin_dashboard_shadow_result",
]
