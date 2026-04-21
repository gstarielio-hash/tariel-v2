"""Contratos de aplicacao da Wave 1 da memoria operacional governada."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.db.contracts import (
    EvidenceMesaStatus,
    EvidenceOperationalStatus,
    OperationalEventSource,
    OperationalEventType,
    OperationalResolutionMode,
    OperationalSeverity,
)


def _normalizar_datetime_utc(valor: datetime | None) -> datetime | None:
    if valor is None:
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _normalizar_lista_textos(valores: list[str]) -> list[str]:
    vistos: set[str] = set()
    resultado: list[str] = []
    for valor in valores:
        texto = str(valor or "").strip()
        if not texto:
            continue
        chave = texto.lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(texto)
    return resultado


class ApprovedCaseSnapshotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    laudo_id: int = Field(..., ge=1)
    approved_by_id: int | None = Field(default=None, ge=1)
    approval_version: int | None = Field(default=None, ge=1)
    approved_at: datetime | None = None
    laudo_output_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence_manifest: list[dict[str, Any]] = Field(default_factory=list)
    mesa_resolution_summary: dict[str, Any] = Field(default_factory=dict)
    document_outcome: str | None = Field(default=None, max_length=80)
    technical_tags: list[str] = Field(default_factory=list)
    snapshot_hash: str | None = Field(default=None, max_length=64)

    @field_validator("approved_at")
    @classmethod
    def _validar_approved_at(cls, valor: datetime | None) -> datetime | None:
        return _normalizar_datetime_utc(valor)

    @field_validator("laudo_output_snapshot")
    @classmethod
    def _validar_laudo_output_snapshot(cls, valor: dict[str, Any]) -> dict[str, Any]:
        if not valor:
            raise ValueError("laudo_output_snapshot e obrigatorio.")
        return valor

    @field_validator("technical_tags")
    @classmethod
    def _validar_tags(cls, valor: list[str]) -> list[str]:
        return _normalizar_lista_textos(valor)


class OperationalEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    laudo_id: int = Field(..., ge=1)
    event_type: str = Field(..., min_length=3, max_length=64)
    event_source: str = Field(default=OperationalEventSource.SYSTEM_QUALITY_GATE.value, min_length=2, max_length=32)
    severity: str = Field(default=OperationalSeverity.INFO.value, min_length=3, max_length=16)
    actor_user_id: int | None = Field(default=None, ge=1)
    snapshot_id: int | None = Field(default=None, ge=1)
    block_key: str | None = Field(default=None, max_length=120)
    evidence_key: str | None = Field(default=None, max_length=160)
    event_metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None

    @field_validator("event_type")
    @classmethod
    def _validar_event_type(cls, valor: str) -> str:
        return OperationalEventType.normalizar(valor)

    @field_validator("event_source")
    @classmethod
    def _validar_event_source(cls, valor: str) -> str:
        return OperationalEventSource.normalizar(valor)

    @field_validator("severity")
    @classmethod
    def _validar_severity(cls, valor: str) -> str:
        return OperationalSeverity.normalizar(valor)

    @field_validator("occurred_at")
    @classmethod
    def _validar_occurred_at(cls, valor: datetime | None) -> datetime | None:
        return _normalizar_datetime_utc(valor)


class EvidenceValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    laudo_id: int = Field(..., ge=1)
    evidence_key: str = Field(..., min_length=1, max_length=160)
    component_type: str | None = Field(default=None, max_length=80)
    view_angle: str | None = Field(default=None, max_length=80)
    quality_score: int | None = Field(default=None, ge=0, le=100)
    coherence_score: int | None = Field(default=None, ge=0, le=100)
    operational_status: str = Field(default=EvidenceOperationalStatus.PENDING.value, min_length=2, max_length=24)
    mesa_status: str = Field(default=EvidenceMesaStatus.NOT_REVIEWED.value, min_length=2, max_length=24)
    failure_reasons: list[str] = Field(default_factory=list)
    evidence_metadata: dict[str, Any] = Field(default_factory=dict)
    replacement_evidence_key: str | None = Field(default=None, max_length=160)
    validated_by_user_id: int | None = Field(default=None, ge=1)
    last_evaluated_at: datetime | None = None

    @field_validator("operational_status")
    @classmethod
    def _validar_operational_status(cls, valor: str) -> str:
        return EvidenceOperationalStatus.normalizar(valor)

    @field_validator("mesa_status")
    @classmethod
    def _validar_mesa_status(cls, valor: str) -> str:
        return EvidenceMesaStatus.normalizar(valor)

    @field_validator("failure_reasons")
    @classmethod
    def _validar_failure_reasons(cls, valor: list[str]) -> list[str]:
        return _normalizar_lista_textos(valor)

    @field_validator("last_evaluated_at")
    @classmethod
    def _validar_last_evaluated_at(cls, valor: datetime | None) -> datetime | None:
        return _normalizar_datetime_utc(valor)


class OperationalIrregularityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    laudo_id: int = Field(..., ge=1)
    irregularity_type: str = Field(..., min_length=3, max_length=64)
    severity: str = Field(default=OperationalSeverity.WARNING.value, min_length=3, max_length=16)
    detected_by: str = Field(default=OperationalEventSource.SYSTEM_QUALITY_GATE.value, min_length=2, max_length=32)
    detected_by_user_id: int | None = Field(default=None, ge=1)
    source_event_id: int | None = Field(default=None, ge=1)
    validation_id: int | None = Field(default=None, ge=1)
    block_key: str | None = Field(default=None, max_length=120)
    evidence_key: str | None = Field(default=None, max_length=160)
    details: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime | None = None

    @field_validator("irregularity_type")
    @classmethod
    def _validar_irregularity_type(cls, valor: str) -> str:
        return OperationalEventType.normalizar(valor)

    @field_validator("severity")
    @classmethod
    def _validar_severity(cls, valor: str) -> str:
        return OperationalSeverity.normalizar(valor)

    @field_validator("detected_by")
    @classmethod
    def _validar_detected_by(cls, valor: str) -> str:
        return OperationalEventSource.normalizar(valor)

    @field_validator("detected_at")
    @classmethod
    def _validar_detected_at(cls, valor: datetime | None) -> datetime | None:
        return _normalizar_datetime_utc(valor)


class OperationalIrregularityResolutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_mode: str = Field(..., min_length=3, max_length=40)
    resolved_by_id: int | None = Field(default=None, ge=1)
    resolution_notes: str | None = Field(default=None, max_length=2000)
    resolved_at: datetime | None = None

    @field_validator("resolution_mode")
    @classmethod
    def _validar_resolution_mode(cls, valor: str) -> str:
        return OperationalResolutionMode.normalizar(valor)

    @field_validator("resolved_at")
    @classmethod
    def _validar_resolved_at(cls, valor: datetime | None) -> datetime | None:
        return _normalizar_datetime_utc(valor)


class FamilyOperationalFrequencyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_key: str = Field(..., min_length=1, max_length=160)
    count: int = Field(..., ge=0)


class FamilyOperationalMemorySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    empresa_id: int = Field(..., ge=1)
    family_key: str = Field(..., min_length=1, max_length=120)
    approved_snapshot_count: int = Field(default=0, ge=0)
    operational_event_count: int = Field(default=0, ge=0)
    validated_evidence_count: int = Field(default=0, ge=0)
    open_irregularity_count: int = Field(default=0, ge=0)
    latest_approved_at: datetime | None = None
    latest_event_at: datetime | None = None
    top_event_types: list[FamilyOperationalFrequencyItem] = Field(default_factory=list)
    top_open_irregularities: list[FamilyOperationalFrequencyItem] = Field(default_factory=list)


__all__ = [
    "ApprovedCaseSnapshotInput",
    "EvidenceValidationInput",
    "FamilyOperationalFrequencyItem",
    "FamilyOperationalMemorySummary",
    "OperationalEventInput",
    "OperationalIrregularityInput",
    "OperationalIrregularityResolutionInput",
]
