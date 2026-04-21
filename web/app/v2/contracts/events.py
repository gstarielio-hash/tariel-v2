"""Eventos canônicos incrementais do V2."""

from __future__ import annotations

from typing import Literal

from app.v2.contracts.envelopes import CollaborationEventEnvelope, DomainEventEnvelope


class TechnicalCaseCreatedDomainEventV1(DomainEventEnvelope):
    contract_name: Literal["TechnicalCaseCreatedDomainEventV1"] = "TechnicalCaseCreatedDomainEventV1"


class CommentPublishedCollaborationEventV1(CollaborationEventEnvelope):
    contract_name: Literal["CommentPublishedCollaborationEventV1"] = "CommentPublishedCollaborationEventV1"


__all__ = [
    "CollaborationEventEnvelope",
    "CommentPublishedCollaborationEventV1",
    "DomainEventEnvelope",
    "TechnicalCaseCreatedDomainEventV1",
]
