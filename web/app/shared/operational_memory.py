"""Servicos internos da Wave 1 da memoria operacional governada."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.shared.database import (
    ApprovedCaseSnapshot,
    EvidenceOperationalStatus,
    EvidenceValidation,
    Laudo,
    OperationalEvent,
    OperationalIrregularity,
    OperationalIrregularityStatus,
    OperationalResolutionMode,
)
from app.shared.operational_memory_contracts import (
    ApprovedCaseSnapshotInput,
    EvidenceValidationInput,
    FamilyOperationalFrequencyItem,
    FamilyOperationalMemorySummary,
    OperationalEventInput,
    OperationalIrregularityInput,
    OperationalIrregularityResolutionInput,
)


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalizar_data_utc(valor: datetime | None) -> datetime:
    if valor is None:
        return _agora_utc()
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _compactar_json(valor: Any) -> Any:
    if isinstance(valor, dict):
        if not valor:
            return None
        return {str(chave): item for chave, item in valor.items()}
    if isinstance(valor, list):
        return valor or None
    return valor


def _resolver_contexto_laudo(banco: Session, *, laudo_id: int) -> tuple[Laudo, str]:
    laudo = banco.get(Laudo, int(laudo_id))
    if laudo is None:
        raise ValueError("Laudo nao encontrado para memoria operacional.")

    family_key = str(laudo.catalog_family_key or laudo.tipo_template or "").strip()
    if not family_key:
        raise ValueError("Laudo sem family_key ou tipo_template para memoria operacional.")

    return laudo, family_key


def registrar_snapshot_aprovado(banco: Session, payload: ApprovedCaseSnapshotInput) -> ApprovedCaseSnapshot:
    laudo, family_key = _resolver_contexto_laudo(banco, laudo_id=payload.laudo_id)
    approved_at = _normalizar_data_utc(payload.approved_at)
    approval_version = payload.approval_version

    if approval_version is None:
        ultimo = banco.scalar(
            select(func.max(ApprovedCaseSnapshot.approval_version)).where(ApprovedCaseSnapshot.laudo_id == laudo.id)
        )
        approval_version = int(ultimo or 0) + 1

    registro = ApprovedCaseSnapshot(
        laudo_id=laudo.id,
        empresa_id=laudo.empresa_id,
        family_key=family_key,
        approval_version=int(approval_version),
        approved_at=approved_at,
        approved_by_id=payload.approved_by_id,
        source_status_revisao=str(laudo.status_revisao or "").strip() or None,
        source_status_conformidade=str(laudo.status_conformidade or "").strip() or None,
        document_outcome=payload.document_outcome,
        laudo_output_snapshot=payload.laudo_output_snapshot,
        evidence_manifest_json=_compactar_json(payload.evidence_manifest),
        mesa_resolution_summary_json=_compactar_json(payload.mesa_resolution_summary),
        technical_tags_json=_compactar_json(payload.technical_tags),
        snapshot_hash=payload.snapshot_hash,
        criado_em=approved_at,
        atualizado_em=approved_at,
    )
    banco.add(registro)
    banco.flush()
    return registro


def registrar_evento_operacional(banco: Session, payload: OperationalEventInput) -> OperationalEvent:
    laudo, family_key = _resolver_contexto_laudo(banco, laudo_id=payload.laudo_id)
    occurred_at = _normalizar_data_utc(payload.occurred_at)

    registro = OperationalEvent(
        laudo_id=laudo.id,
        empresa_id=laudo.empresa_id,
        family_key=family_key,
        snapshot_id=payload.snapshot_id,
        actor_user_id=payload.actor_user_id,
        event_type=payload.event_type,
        event_source=payload.event_source,
        severity=payload.severity,
        block_key=payload.block_key,
        evidence_key=payload.evidence_key,
        event_metadata_json=_compactar_json(payload.event_metadata),
        criado_em=occurred_at,
        atualizado_em=occurred_at,
    )
    banco.add(registro)
    banco.flush()
    return registro


def registrar_validacao_evidencia(banco: Session, payload: EvidenceValidationInput) -> EvidenceValidation:
    laudo, family_key = _resolver_contexto_laudo(banco, laudo_id=payload.laudo_id)
    last_evaluated_at = _normalizar_data_utc(payload.last_evaluated_at)

    registro = banco.scalar(
        select(EvidenceValidation).where(
            EvidenceValidation.laudo_id == laudo.id,
            EvidenceValidation.evidence_key == payload.evidence_key,
        )
    )
    if registro is None:
        registro = EvidenceValidation(
            laudo_id=laudo.id,
            empresa_id=laudo.empresa_id,
            family_key=family_key,
            evidence_key=payload.evidence_key,
            criado_em=last_evaluated_at,
        )
        banco.add(registro)

    registro.component_type = payload.component_type
    registro.view_angle = payload.view_angle
    registro.quality_score = payload.quality_score
    registro.coherence_score = payload.coherence_score
    registro.operational_status = payload.operational_status
    registro.mesa_status = payload.mesa_status
    registro.failure_reasons_json = _compactar_json(payload.failure_reasons)
    registro.evidence_metadata_json = _compactar_json(payload.evidence_metadata)
    registro.replacement_evidence_key = payload.replacement_evidence_key
    registro.validated_by_user_id = payload.validated_by_user_id
    registro.last_evaluated_at = last_evaluated_at
    registro.atualizado_em = last_evaluated_at
    banco.flush()
    return registro


def abrir_irregularidade_operacional(
    banco: Session,
    payload: OperationalIrregularityInput,
) -> OperationalIrregularity:
    laudo, family_key = _resolver_contexto_laudo(banco, laudo_id=payload.laudo_id)
    detected_at = _normalizar_data_utc(payload.detected_at)

    registro = OperationalIrregularity(
        laudo_id=laudo.id,
        empresa_id=laudo.empresa_id,
        family_key=family_key,
        source_event_id=payload.source_event_id,
        validation_id=payload.validation_id,
        detected_by_user_id=payload.detected_by_user_id,
        irregularity_type=payload.irregularity_type,
        severity=payload.severity,
        status=OperationalIrregularityStatus.OPEN.value,
        detected_by=payload.detected_by,
        block_key=payload.block_key,
        evidence_key=payload.evidence_key,
        details_json=_compactar_json(payload.details),
        criado_em=detected_at,
        atualizado_em=detected_at,
    )
    banco.add(registro)
    banco.flush()
    return registro


def resolver_irregularidade_operacional(
    banco: Session,
    *,
    irregularity_id: int,
    payload: OperationalIrregularityResolutionInput,
) -> OperationalIrregularity:
    registro = banco.get(OperationalIrregularity, int(irregularity_id))
    if registro is None:
        raise ValueError("Irregularidade operacional nao encontrada.")

    resolved_at = _normalizar_data_utc(payload.resolved_at)
    registro.resolution_mode = payload.resolution_mode
    registro.resolution_notes = payload.resolution_notes
    registro.resolved_by_id = payload.resolved_by_id
    registro.resolved_at = resolved_at
    registro.status = (
        OperationalIrregularityStatus.DISMISSED.value
        if payload.resolution_mode == OperationalResolutionMode.DISMISSED_FALSE_POSITIVE.value
        else OperationalIrregularityStatus.RESOLVED.value
    )
    registro.atualizado_em = resolved_at
    banco.flush()
    return registro


def build_family_operational_memory_summary(
    banco: Session,
    *,
    empresa_id: int,
    family_key: str,
    limit: int = 5,
) -> FamilyOperationalMemorySummary:
    family_key_limpo = str(family_key or "").strip()
    if not family_key_limpo:
        raise ValueError("family_key e obrigatorio.")

    approved_snapshot_count = int(
        banco.scalar(
            select(func.count(ApprovedCaseSnapshot.id)).where(
                ApprovedCaseSnapshot.empresa_id == int(empresa_id),
                ApprovedCaseSnapshot.family_key == family_key_limpo,
            )
        )
        or 0
    )
    operational_event_count = int(
        banco.scalar(
            select(func.count(OperationalEvent.id)).where(
                OperationalEvent.empresa_id == int(empresa_id),
                OperationalEvent.family_key == family_key_limpo,
            )
        )
        or 0
    )
    validated_evidence_count = int(
        banco.scalar(
            select(func.count(EvidenceValidation.id)).where(
                EvidenceValidation.empresa_id == int(empresa_id),
                EvidenceValidation.family_key == family_key_limpo,
                EvidenceValidation.operational_status == EvidenceOperationalStatus.OK.value,
            )
        )
        or 0
    )
    open_irregularity_count = int(
        banco.scalar(
            select(func.count(OperationalIrregularity.id)).where(
                OperationalIrregularity.empresa_id == int(empresa_id),
                OperationalIrregularity.family_key == family_key_limpo,
                OperationalIrregularity.status.in_(
                    (
                        OperationalIrregularityStatus.OPEN.value,
                        OperationalIrregularityStatus.ACKNOWLEDGED.value,
                    )
                ),
            )
        )
        or 0
    )

    latest_approved_at = banco.scalar(
        select(func.max(ApprovedCaseSnapshot.approved_at)).where(
            ApprovedCaseSnapshot.empresa_id == int(empresa_id),
            ApprovedCaseSnapshot.family_key == family_key_limpo,
        )
    )
    latest_event_at = banco.scalar(
        select(func.max(OperationalEvent.criado_em)).where(
            OperationalEvent.empresa_id == int(empresa_id),
            OperationalEvent.family_key == family_key_limpo,
        )
    )

    top_event_rows = banco.execute(
        select(OperationalEvent.event_type, func.count(OperationalEvent.id).label("total"))
        .where(
            OperationalEvent.empresa_id == int(empresa_id),
            OperationalEvent.family_key == family_key_limpo,
        )
        .group_by(OperationalEvent.event_type)
        .order_by(func.count(OperationalEvent.id).desc(), OperationalEvent.event_type.asc())
        .limit(max(1, int(limit)))
    ).all()
    top_irregularity_rows = banco.execute(
        select(OperationalIrregularity.irregularity_type, func.count(OperationalIrregularity.id).label("total"))
        .where(
            OperationalIrregularity.empresa_id == int(empresa_id),
            OperationalIrregularity.family_key == family_key_limpo,
            OperationalIrregularity.status.in_(
                (
                    OperationalIrregularityStatus.OPEN.value,
                    OperationalIrregularityStatus.ACKNOWLEDGED.value,
                )
            ),
        )
        .group_by(OperationalIrregularity.irregularity_type)
        .order_by(func.count(OperationalIrregularity.id).desc(), OperationalIrregularity.irregularity_type.asc())
        .limit(max(1, int(limit)))
    ).all()

    return FamilyOperationalMemorySummary(
        empresa_id=int(empresa_id),
        family_key=family_key_limpo,
        approved_snapshot_count=approved_snapshot_count,
        operational_event_count=operational_event_count,
        validated_evidence_count=validated_evidence_count,
        open_irregularity_count=open_irregularity_count,
        latest_approved_at=latest_approved_at,
        latest_event_at=latest_event_at,
        top_event_types=[
            FamilyOperationalFrequencyItem(item_key=str(row[0]), count=int(row[1] or 0)) for row in top_event_rows
        ],
        top_open_irregularities=[
            FamilyOperationalFrequencyItem(item_key=str(row[0]), count=int(row[1] or 0))
            for row in top_irregularity_rows
        ],
    )


__all__ = [
    "abrir_irregularidade_operacional",
    "build_family_operational_memory_summary",
    "registrar_evento_operacional",
    "registrar_snapshot_aprovado",
    "registrar_validacao_evidencia",
    "resolver_irregularidade_operacional",
]
