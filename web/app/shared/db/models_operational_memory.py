from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates

from app.shared.db.contracts import (
    EvidenceMesaStatus,
    EvidenceOperationalStatus,
    OperationalEventSource,
    OperationalEventType,
    OperationalIrregularityStatus,
    OperationalResolutionMode,
    OperationalSeverity,
)
from app.shared.db.models_base import Base, MixinAuditoria, agora_utc

_EVENT_TYPES_VALIDOS = ", ".join(repr(item.value) for item in OperationalEventType)
_EVENT_SOURCES_VALIDOS = ", ".join(repr(item.value) for item in OperationalEventSource)
_SEVERIDADES_VALIDAS = ", ".join(repr(item.value) for item in OperationalSeverity)
_EVIDENCE_OPERATIONAL_STATUS_VALIDOS = ", ".join(repr(item.value) for item in EvidenceOperationalStatus)
_EVIDENCE_MESA_STATUS_VALIDOS = ", ".join(repr(item.value) for item in EvidenceMesaStatus)
_IRREGULARITY_STATUS_VALIDOS = ", ".join(repr(item.value) for item in OperationalIrregularityStatus)
_RESOLUTION_MODE_VALIDOS = ", ".join(repr(item.value) for item in OperationalResolutionMode)


class ApprovedCaseSnapshot(MixinAuditoria, Base):
    __tablename__ = "laudo_approved_case_snapshots"
    __table_args__ = (
        CheckConstraint("approval_version >= 1", name="ck_approved_case_snapshot_version"),
        UniqueConstraint("laudo_id", "approval_version", name="uq_approved_case_snapshot_laudo_version"),
        Index("ix_approved_case_snapshot_laudo", "laudo_id", "approved_at"),
        Index("ix_approved_case_snapshot_empresa_familia", "empresa_id", "family_key"),
        Index("ix_approved_case_snapshot_family_approved", "family_key", "approved_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    laudo_id = Column(Integer, ForeignKey("laudos.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    family_key = Column(String(120), nullable=False, index=True)
    approval_version = Column(Integer, nullable=False, default=1)
    approved_at = Column(DateTime(timezone=True), nullable=False, default=agora_utc)
    approved_by_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    source_status_revisao = Column(String(40), nullable=True)
    source_status_conformidade = Column(String(40), nullable=True)
    document_outcome = Column(String(80), nullable=True)
    laudo_output_snapshot = Column(JSON, nullable=False)
    evidence_manifest_json = Column(JSON, nullable=True)
    mesa_resolution_summary_json = Column(JSON, nullable=True)
    technical_tags_json = Column(JSON, nullable=True)
    snapshot_hash = Column(String(64), nullable=True)

    laudo = relationship("Laudo", foreign_keys=[laudo_id])
    empresa = relationship("Empresa", foreign_keys=[empresa_id])
    approved_by = relationship("Usuario", foreign_keys=[approved_by_id])


class OperationalEvent(MixinAuditoria, Base):
    __tablename__ = "laudo_operational_events"
    __table_args__ = (
        CheckConstraint(f"event_type IN ({_EVENT_TYPES_VALIDOS})", name="ck_operational_event_type"),
        CheckConstraint(f"event_source IN ({_EVENT_SOURCES_VALIDOS})", name="ck_operational_event_source"),
        CheckConstraint(f"severity IN ({_SEVERIDADES_VALIDAS})", name="ck_operational_event_severity"),
        CheckConstraint(
            f"(resolution_mode IS NULL OR resolution_mode IN ({_RESOLUTION_MODE_VALIDOS}))",
            name="ck_operational_event_resolution_mode",
        ),
        Index("ix_operational_event_laudo_criado", "laudo_id", "criado_em"),
        Index("ix_operational_event_empresa_familia_tipo", "empresa_id", "family_key", "event_type"),
        Index("ix_operational_event_snapshot", "snapshot_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    laudo_id = Column(Integer, ForeignKey("laudos.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    family_key = Column(String(120), nullable=False, index=True)
    snapshot_id = Column(
        Integer,
        ForeignKey("laudo_approved_case_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False)
    event_source = Column(String(32), nullable=False, default=OperationalEventSource.SYSTEM_QUALITY_GATE.value)
    severity = Column(String(16), nullable=False, default=OperationalSeverity.INFO.value)
    block_key = Column(String(120), nullable=True)
    evidence_key = Column(String(160), nullable=True)
    event_metadata_json = Column(JSON, nullable=True)
    resolution_mode = Column(String(40), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)

    laudo = relationship("Laudo", foreign_keys=[laudo_id])
    empresa = relationship("Empresa", foreign_keys=[empresa_id])
    snapshot = relationship("ApprovedCaseSnapshot", foreign_keys=[snapshot_id])
    actor_user = relationship("Usuario", foreign_keys=[actor_user_id])
    resolved_by = relationship("Usuario", foreign_keys=[resolved_by_id])

    @validates("event_type")
    def _validar_event_type(self, _key: str, valor: Any) -> str:
        return OperationalEventType.normalizar(valor)

    @validates("event_source")
    def _validar_event_source(self, _key: str, valor: Any) -> str:
        return OperationalEventSource.normalizar(valor)

    @validates("severity")
    def _validar_severidade(self, _key: str, valor: Any) -> str:
        return OperationalSeverity.normalizar(valor)

    @validates("resolution_mode")
    def _validar_resolution_mode(self, _key: str, valor: Any) -> str | None:
        if valor is None or str(valor).strip() == "":
            return None
        return OperationalResolutionMode.normalizar(valor)


class EvidenceValidation(MixinAuditoria, Base):
    __tablename__ = "laudo_evidence_validations"
    __table_args__ = (
        CheckConstraint(
            "(quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100))",
            name="ck_evidence_validation_quality_score",
        ),
        CheckConstraint(
            "(coherence_score IS NULL OR (coherence_score >= 0 AND coherence_score <= 100))",
            name="ck_evidence_validation_coherence_score",
        ),
        CheckConstraint(
            f"operational_status IN ({_EVIDENCE_OPERATIONAL_STATUS_VALIDOS})",
            name="ck_evidence_validation_operational_status",
        ),
        CheckConstraint(f"mesa_status IN ({_EVIDENCE_MESA_STATUS_VALIDOS})", name="ck_evidence_validation_mesa_status"),
        UniqueConstraint("laudo_id", "evidence_key", name="uq_evidence_validation_laudo_evidence"),
        Index("ix_evidence_validation_empresa_familia", "empresa_id", "family_key"),
        Index("ix_evidence_validation_component_angle", "family_key", "component_type", "view_angle"),
    )

    id = Column(Integer, primary_key=True, index=True)
    laudo_id = Column(Integer, ForeignKey("laudos.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    family_key = Column(String(120), nullable=False, index=True)
    evidence_key = Column(String(160), nullable=False)
    component_type = Column(String(80), nullable=True)
    view_angle = Column(String(80), nullable=True)
    quality_score = Column(Integer, nullable=True)
    coherence_score = Column(Integer, nullable=True)
    operational_status = Column(String(24), nullable=False, default=EvidenceOperationalStatus.PENDING.value)
    mesa_status = Column(String(24), nullable=False, default=EvidenceMesaStatus.NOT_REVIEWED.value)
    failure_reasons_json = Column(JSON, nullable=True)
    evidence_metadata_json = Column(JSON, nullable=True)
    replacement_evidence_key = Column(String(160), nullable=True)
    validated_by_user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=False, default=agora_utc)

    laudo = relationship("Laudo", foreign_keys=[laudo_id])
    empresa = relationship("Empresa", foreign_keys=[empresa_id])
    validated_by = relationship("Usuario", foreign_keys=[validated_by_user_id])

    @validates("operational_status")
    def _validar_operational_status(self, _key: str, valor: Any) -> str:
        return EvidenceOperationalStatus.normalizar(valor)

    @validates("mesa_status")
    def _validar_mesa_status(self, _key: str, valor: Any) -> str:
        return EvidenceMesaStatus.normalizar(valor)


class OperationalIrregularity(MixinAuditoria, Base):
    __tablename__ = "laudo_operational_irregularities"
    __table_args__ = (
        CheckConstraint(f"irregularity_type IN ({_EVENT_TYPES_VALIDOS})", name="ck_operational_irregularity_type"),
        CheckConstraint(f"severity IN ({_SEVERIDADES_VALIDAS})", name="ck_operational_irregularity_severity"),
        CheckConstraint(f"status IN ({_IRREGULARITY_STATUS_VALIDOS})", name="ck_operational_irregularity_status"),
        CheckConstraint(f"detected_by IN ({_EVENT_SOURCES_VALIDOS})", name="ck_operational_irregularity_detected_by"),
        CheckConstraint(
            f"(resolution_mode IS NULL OR resolution_mode IN ({_RESOLUTION_MODE_VALIDOS}))",
            name="ck_operational_irregularity_resolution_mode",
        ),
        Index("ix_operational_irregularity_laudo_status", "laudo_id", "status", "criado_em"),
        Index("ix_operational_irregularity_empresa_familia_status", "empresa_id", "family_key", "status"),
        Index("ix_operational_irregularity_event_validation", "source_event_id", "validation_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    laudo_id = Column(Integer, ForeignKey("laudos.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    family_key = Column(String(120), nullable=False, index=True)
    source_event_id = Column(Integer, ForeignKey("laudo_operational_events.id", ondelete="SET NULL"), nullable=True)
    validation_id = Column(Integer, ForeignKey("laudo_evidence_validations.id", ondelete="SET NULL"), nullable=True)
    detected_by_user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    resolved_by_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    irregularity_type = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False, default=OperationalSeverity.WARNING.value)
    status = Column(String(24), nullable=False, default=OperationalIrregularityStatus.OPEN.value)
    detected_by = Column(String(32), nullable=False, default=OperationalEventSource.SYSTEM_QUALITY_GATE.value)
    block_key = Column(String(120), nullable=True)
    evidence_key = Column(String(160), nullable=True)
    details_json = Column(JSON, nullable=True)
    resolution_mode = Column(String(40), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    laudo = relationship("Laudo", foreign_keys=[laudo_id])
    empresa = relationship("Empresa", foreign_keys=[empresa_id])
    source_event = relationship("OperationalEvent", foreign_keys=[source_event_id])
    validation = relationship("EvidenceValidation", foreign_keys=[validation_id])
    detected_by_user = relationship("Usuario", foreign_keys=[detected_by_user_id])
    resolved_by = relationship("Usuario", foreign_keys=[resolved_by_id])

    @validates("irregularity_type")
    def _validar_irregularity_type(self, _key: str, valor: Any) -> str:
        return OperationalEventType.normalizar(valor)

    @validates("severity")
    def _validar_severidade(self, _key: str, valor: Any) -> str:
        return OperationalSeverity.normalizar(valor)

    @validates("status")
    def _validar_status(self, _key: str, valor: Any) -> str:
        return OperationalIrregularityStatus.normalizar(valor)

    @validates("detected_by")
    def _validar_detected_by(self, _key: str, valor: Any) -> str:
        return OperationalEventSource.normalizar(valor)

    @validates("resolution_mode")
    def _validar_resolution_mode(self, _key: str, valor: Any) -> str | None:
        if valor is None or str(valor).strip() == "":
            return None
        return OperationalResolutionMode.normalizar(valor)


__all__ = [
    "ApprovedCaseSnapshot",
    "EvidenceValidation",
    "OperationalEvent",
    "OperationalIrregularity",
]
