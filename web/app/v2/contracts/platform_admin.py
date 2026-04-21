"""Projecao canonica incremental para o portal admin-geral."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.billing import build_platform_billing_metering_summary
from app.v2.contracts.envelopes import ProjectionEnvelope, utc_now


class PlatformAdminTenantSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    tenant_status: str
    tenant_name: str | None = None
    active_plan: str | None = None
    usage_counter: int = 0


class PlatformAdminPlanSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_plans: int = 0
    plan_breakdown: dict[str, int] = Field(default_factory=dict)


class PlatformAdminConsumptionSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_tenants: int = 0
    alert_count: int = 0
    total_inspections: int = 0
    total_api_revenue_brl: str = "0"
    chart_labels: list[str] = Field(default_factory=list)
    chart_values: list[int] = Field(default_factory=list)


class PlatformAdminAuditSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recent_admin_actions: int = 0
    audited_tenants: int = 0


class PlatformAdminViewProjectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_list_summary: list[PlatformAdminTenantSummaryPayload] = Field(default_factory=list)
    plan_summary: PlatformAdminPlanSummaryPayload
    consumption_summary: PlatformAdminConsumptionSummaryPayload
    platform_alerts: list[str] = Field(default_factory=list)
    audit_summary: PlatformAdminAuditSummaryPayload
    technical_visibility: Literal["none_by_default"] = "none_by_default"


class PlatformAdminViewProjectionV1(ProjectionEnvelope):
    contract_name: Literal["PlatformAdminViewProjectionV1"] = "PlatformAdminViewProjectionV1"
    projection_name: Literal["PlatformAdminViewProjectionV1"] = "PlatformAdminViewProjectionV1"
    projection_audience: Literal["platform_admin_web"] = "platform_admin_web"
    projection_type: Literal["platform_admin_projection"] = "platform_admin_projection"


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def build_platform_admin_view_projection(
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
    platform_scope_id: Any = "platform",
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> PlatformAdminViewProjectionV1:
    now = timestamp or utc_now()
    metering_summary = build_platform_billing_metering_summary(
        tenant_summaries=tenant_summaries,
        total_inspections=total_inspections,
        total_api_revenue_brl=total_api_revenue_brl,
        chart_labels=chart_labels,
        chart_values=chart_values,
    )

    payload = PlatformAdminViewProjectionPayload(
        tenant_list_summary=[
            PlatformAdminTenantSummaryPayload(**item.model_dump(mode="python"))
            for item in metering_summary.tenant_list_summary
        ],
        plan_summary=PlatformAdminPlanSummaryPayload(
            active_plans=metering_summary.active_plans,
            plan_breakdown=dict(metering_summary.plan_breakdown),
        ),
        consumption_summary=PlatformAdminConsumptionSummaryPayload(
            active_tenants=metering_summary.active_tenants,
            alert_count=metering_summary.alert_count,
            total_inspections=metering_summary.total_inspections,
            total_api_revenue_brl=metering_summary.total_api_revenue_brl,
            chart_labels=list(metering_summary.chart_labels),
            chart_values=list(metering_summary.chart_values),
        ),
        platform_alerts=list(metering_summary.platform_alerts),
        audit_summary=PlatformAdminAuditSummaryPayload(
            recent_admin_actions=_normalize_int(recent_admin_actions),
            audited_tenants=len(metering_summary.tenant_list_summary),
        ),
    )

    return PlatformAdminViewProjectionV1(
        tenant_id=_normalize_text(platform_scope_id) or "platform",
        actor_id=str(actor_id),
        actor_role=_normalize_text(actor_role) or "diretoria",
        correlation_id=correlation_id or uuid.uuid4().hex,
        causation_id=causation_id,
        idempotency_key=idempotency_key or "platform-admin-view:platform",
        source_channel=_normalize_text(source_channel) or "admin_dashboard",
        origin_kind="system",
        sensitivity="administrative",
        visibility_scope="platform_admin_aggregate",
        timestamp=now,
        payload=payload.model_dump(mode="python"),
    )


__all__ = [
    "PlatformAdminAuditSummaryPayload",
    "PlatformAdminConsumptionSummaryPayload",
    "PlatformAdminPlanSummaryPayload",
    "PlatformAdminTenantSummaryPayload",
    "PlatformAdminViewProjectionPayload",
    "PlatformAdminViewProjectionV1",
    "build_platform_admin_view_projection",
]
