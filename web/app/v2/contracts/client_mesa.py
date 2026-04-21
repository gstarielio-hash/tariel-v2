"""Projecao canonica do snapshot da mesa no portal admin-cliente."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.envelopes import ProjectionEnvelope, utc_now


class ClientMesaTenantSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    company_name: str
    active_plan: str
    blocked: bool = False
    health_label: str = ""
    health_tone: str = ""
    health_text: str = ""
    total_reports: int = 0


class ClientMesaReviewerSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = 0
    active: int = 0
    blocked: int = 0
    with_recent_sessions: int = 0
    first_access_pending: int = 0


class ClientMesaReviewStatusTotalsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drafts: int = 0
    waiting_review: int = 0
    approved: int = 0
    rejected: int = 0
    other_statuses: int = 0


class ClientMesaReviewerPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    email: str
    portal_label: str = ""
    active: bool = True
    blocked: bool = False
    temporary_password_active: bool = False
    last_login_at: datetime | None = None
    last_login_label: str = ""
    last_activity_at: datetime | None = None
    last_activity_label: str = ""
    session_count: int = 0


class ClientMesaAuditItemPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    portal: str = ""
    action: str = ""
    category: str = ""
    scope: str = ""
    summary: str = ""
    detail: str = ""
    actor_name: str = ""
    target_name: str = ""
    created_at: datetime | None = None
    created_at_label: str = ""


class ClientMesaDashboardProjectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_summary: ClientMesaTenantSummaryPayload
    reviewer_summary: ClientMesaReviewerSummaryPayload
    review_status_totals: ClientMesaReviewStatusTotalsPayload
    reviewers: list[ClientMesaReviewerPayload] = Field(default_factory=list)
    recent_audit: list[ClientMesaAuditItemPayload] = Field(default_factory=list)
    audit_summary: dict[str, Any] = Field(default_factory=dict)
    review_queue_projection: dict[str, Any] = Field(default_factory=dict)


class ClientMesaDashboardProjectionV1(ProjectionEnvelope):
    contract_name: Literal["ClientMesaDashboardProjectionV1"] = "ClientMesaDashboardProjectionV1"
    projection_name: Literal["ClientMesaDashboardProjectionV1"] = "ClientMesaDashboardProjectionV1"
    projection_audience: Literal["tenant_admin_web"] = "tenant_admin_web"
    projection_type: Literal["client_mesa_dashboard_projection"] = "client_mesa_dashboard_projection"


def build_client_mesa_dashboard_projection(
    *,
    tenant_id: Any,
    company_id: int,
    company_name: str,
    active_plan: str,
    blocked: bool,
    health_label: str,
    health_tone: str,
    health_text: str,
    total_reports: int,
    reviewer_summary: dict[str, Any],
    review_status_totals: dict[str, Any],
    reviewers: list[dict[str, Any]],
    recent_audit: list[dict[str, Any]],
    audit_summary: dict[str, Any],
    review_queue_projection: dict[str, Any],
    actor_id: Any,
    actor_role: str,
    source_channel: str,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> ClientMesaDashboardProjectionV1:
    tenant_id_text = str(tenant_id or "").strip()
    now = timestamp or utc_now()

    payload = ClientMesaDashboardProjectionPayload(
        tenant_summary=ClientMesaTenantSummaryPayload(
            company_id=int(company_id),
            company_name=str(company_name or ""),
            active_plan=str(active_plan or ""),
            blocked=bool(blocked),
            health_label=str(health_label or ""),
            health_tone=str(health_tone or ""),
            health_text=str(health_text or ""),
            total_reports=max(0, int(total_reports or 0)),
        ),
        reviewer_summary=ClientMesaReviewerSummaryPayload.model_validate(reviewer_summary or {}),
        review_status_totals=ClientMesaReviewStatusTotalsPayload.model_validate(review_status_totals or {}),
        reviewers=[
            ClientMesaReviewerPayload.model_validate(item)
            for item in list(reviewers or [])
            if isinstance(item, dict)
        ],
        recent_audit=[
            ClientMesaAuditItemPayload.model_validate(item)
            for item in list(recent_audit or [])
            if isinstance(item, dict)
        ],
        audit_summary=dict(audit_summary or {}),
        review_queue_projection=dict(review_queue_projection or {}),
    )

    return ClientMesaDashboardProjectionV1(
        tenant_id=tenant_id_text,
        actor_id=str(actor_id or ""),
        actor_role=str(actor_role or "").strip() or "admin_cliente",
        correlation_id=correlation_id or uuid.uuid4().hex,
        causation_id=causation_id,
        idempotency_key=idempotency_key or f"client-mesa-dashboard:{tenant_id_text or 'unknown'}",
        source_channel=str(source_channel or "admin_cliente_mesa_snapshot"),
        sensitivity="administrative",
        visibility_scope="tenant_admin_summary",
        timestamp=now,
        payload=payload.model_dump(mode="python"),
    )


__all__ = [
    "ClientMesaDashboardProjectionPayload",
    "ClientMesaDashboardProjectionV1",
    "build_client_mesa_dashboard_projection",
]
