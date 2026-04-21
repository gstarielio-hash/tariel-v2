"""Base incremental de envelopes canônicos do V2."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.provenance import OriginKind


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BaseEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    envelope_kind: str
    contract_name: str
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    thread_id: str | None = None
    document_id: str | None = None
    actor_id: str
    actor_role: str
    correlation_id: str
    causation_id: str | None = None
    idempotency_key: str | None = None
    source_channel: str
    origin_kind: OriginKind = "system"
    sensitivity: str = "technical"
    visibility_scope: str = "actor"
    timestamp: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)


class CommandEnvelope(BaseEnvelope):
    envelope_kind: Literal["command"] = "command"


class DomainEventEnvelope(BaseEnvelope):
    envelope_kind: Literal["domain_event"] = "domain_event"


class CollaborationEventEnvelope(BaseEnvelope):
    envelope_kind: Literal["collaboration_event"] = "collaboration_event"


class ProjectionEnvelope(BaseEnvelope):
    envelope_kind: Literal["projection"] = "projection"
    projection_name: str
    projection_audience: str
    projection_type: str


__all__ = [
    "BaseEnvelope",
    "CollaborationEventEnvelope",
    "CommandEnvelope",
    "DomainEventEnvelope",
    "OriginKind",
    "ProjectionEnvelope",
    "utc_now",
]
