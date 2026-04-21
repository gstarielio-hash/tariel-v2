"""Hooks de integracao da memoria operacional com fluxos reais do produto."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.chat.report_pack_helpers import (
    build_pre_laudo_summary,
    obter_pre_laudo_outline_report_pack,
)
from app.shared.database import (
    ApprovedCaseSnapshot,
    EvidenceMesaStatus,
    EvidenceOperationalStatus,
    EvidenceValidation,
    Laudo,
    LaudoRevisao,
    OperationalEvent,
    OperationalIrregularity,
    OperationalIrregularityStatus,
    OperationalResolutionMode,
    OperationalSeverity,
)
from app.shared.operational_memory import (
    abrir_irregularidade_operacional,
    registrar_evento_operacional,
    registrar_snapshot_aprovado,
    registrar_validacao_evidencia,
    resolver_irregularidade_operacional,
)
from app.shared.operational_memory_contracts import (
    ApprovedCaseSnapshotInput,
    EvidenceValidationInput,
    OperationalEventInput,
    OperationalIrregularityInput,
    OperationalIrregularityResolutionInput,
)

_OPEN_IRREGULARITY_STATUSES = (
    OperationalIrregularityStatus.OPEN.value,
    OperationalIrregularityStatus.ACKNOWLEDGED.value,
)
_RETURN_TO_INSPECTOR_TYPES = (
    "block_returned_to_inspector",
    "field_reopened",
)


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _texto_curto(valor: Any, *, limite: int = 240) -> str | None:
    texto = " ".join(str(valor or "").strip().split())
    if not texto:
        return None
    return texto[:limite]


def _payload_json(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {str(chave): _payload_json(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_payload_json(item) for item in valor]
    return valor


def _hash_payload(payload: dict[str, Any]) -> str:
    serializado = json.dumps(_payload_json(payload), sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _normalizar_datetime_utc(valor: datetime | None) -> datetime | None:
    if valor is None:
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _family_key(laudo: Laudo) -> str:
    return str(getattr(laudo, "catalog_family_key", None) or getattr(laudo, "tipo_template", "") or "").strip()


def _technical_tags_for_laudo(
    laudo: Laudo,
    *,
    document_outcome: str,
) -> list[str]:
    tags: list[str] = []
    for candidato in (
        _family_key(laudo),
        str(getattr(laudo, "tipo_template", "") or "").strip(),
        str(getattr(laudo, "catalog_variant_key", "") or "").strip(),
        str(document_outcome or "").strip(),
    ):
        if candidato and candidato not in tags:
            tags.append(candidato)

    report_pack = getattr(laudo, "report_pack_draft_json", None)
    if isinstance(report_pack, dict):
        if bool(report_pack.get("modeled")):
            tags.append("report_pack_modeled")
        if isinstance(report_pack.get("structured_data_candidate"), dict):
            tags.append("structured_candidate_ready")
        final_validation_mode = str(((report_pack.get("quality_gates") or {}).get("final_validation_mode")) or "").strip()
        if final_validation_mode:
            tags.append(f"review_mode:{final_validation_mode}")

    return tags


def _latest_revision_payload(banco: Session, *, laudo_id: int) -> dict[str, Any] | None:
    revisao = banco.scalar(
        select(LaudoRevisao)
        .where(LaudoRevisao.laudo_id == int(laudo_id))
        .order_by(LaudoRevisao.numero_versao.desc(), LaudoRevisao.id.desc())
        .limit(1)
    )
    if revisao is None:
        return None
    return {
        "numero_versao": int(revisao.numero_versao),
        "origem": str(revisao.origem or "").strip(),
        "resumo": _texto_curto(revisao.resumo),
        "conteudo": str(revisao.conteudo or "").strip(),
        "confianca_geral": _texto_curto(revisao.confianca_geral, limite=32),
        "criado_em": revisao.criado_em.isoformat() if revisao.criado_em else None,
    }


def _build_laudo_output_snapshot(banco: Session, *, laudo: Laudo) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "laudo_id": int(laudo.id),
        "codigo_hash": str(getattr(laudo, "codigo_hash", "") or "").strip(),
        "tipo_template": str(getattr(laudo, "tipo_template", "") or "").strip(),
        "family_key": _family_key(laudo),
        "family_label": _texto_curto(getattr(laudo, "catalog_family_label", None), limite=180),
        "variant_key": _texto_curto(getattr(laudo, "catalog_variant_key", None), limite=80),
        "variant_label": _texto_curto(getattr(laudo, "catalog_variant_label", None), limite=120),
        "status_revisao": str(getattr(laudo, "status_revisao", "") or "").strip(),
        "status_conformidade": str(getattr(laudo, "status_conformidade", "") or "").strip(),
        "parecer_ia": _texto_curto(getattr(laudo, "parecer_ia", None), limite=4000),
    }
    if isinstance(getattr(laudo, "dados_formulario", None), dict):
        snapshot["dados_formulario"] = dict(laudo.dados_formulario or {})
    if isinstance(getattr(laudo, "report_pack_draft_json", None), dict):
        snapshot["report_pack_draft"] = dict(laudo.report_pack_draft_json or {})
        pre_laudo_summary = build_pre_laudo_summary(
            obter_pre_laudo_outline_report_pack(getattr(laudo, "report_pack_draft_json", None))
        )
        if pre_laudo_summary is not None:
            snapshot["pre_laudo_summary"] = pre_laudo_summary
    latest_revision = _latest_revision_payload(banco, laudo_id=int(laudo.id))
    if latest_revision is not None:
        snapshot["latest_revision"] = latest_revision
    return snapshot


def _build_evidence_manifest(laudo: Laudo) -> list[dict[str, Any]]:
    report_pack = getattr(laudo, "report_pack_draft_json", None)
    if not isinstance(report_pack, dict):
        return []

    manifest: list[dict[str, Any]] = []
    image_slots = list(report_pack.get("image_slots") or [])
    for slot in image_slots:
        if not isinstance(slot, dict):
            continue
        slot_code = str(slot.get("slot") or "").strip()
        if not slot_code:
            continue
        manifest.append(
            {
                "evidence_key": f"slot:{slot_code}",
                "kind": "image_slot",
                "slot": slot_code,
                "title": _texto_curto(slot.get("title"), limite=160),
                "status": str(slot.get("status") or "").strip(),
                "required": bool(slot.get("required")),
                "replacement_evidence_key": _texto_curto(slot.get("resolved_evidence_id"), limite=160),
                "resolved_caption": _texto_curto(slot.get("resolved_caption")),
                "missing_evidence": list(slot.get("missing_evidence") or []),
            }
        )

    for item in list(report_pack.get("items") or []):
        if not isinstance(item, dict):
            continue
        item_code = str(item.get("item_codigo") or "").strip()
        if not item_code:
            continue
        manifest.append(
            {
                "evidence_key": f"item:{item_code}",
                "kind": "normative_item",
                "item_codigo": item_code,
                "status": str(item.get("veredito_ia_normativo") or "").strip(),
                "confidence_ia": _texto_curto(item.get("confidence_ia"), limite=32),
                "approved_for_emission": bool(item.get("approved_for_emission")),
                "learning_disposition": _texto_curto(item.get("learning_disposition"), limite=64),
                "missing_evidence": list(item.get("missing_evidence") or []),
            }
        )

    if manifest:
        return manifest

    missing_evidence = list(((report_pack.get("quality_gates") or {}).get("missing_evidence")) or [])
    return [
        {
            "evidence_key": "gate:summary",
            "kind": "gate_summary",
            "status": "ok" if not missing_evidence else "pending",
            "missing_evidence": missing_evidence,
        }
    ]


def _build_approved_case_snapshot_payload_base(
    banco: Session,
    *,
    laudo: Laudo,
    document_outcome: str,
    mesa_resolution_summary: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    laudo_output_snapshot = _build_laudo_output_snapshot(banco, laudo=laudo)
    evidence_manifest = _build_evidence_manifest(laudo)
    document_outcome_text = str(document_outcome or "").strip() or "approved"
    payload_base = {
        "laudo_output_snapshot": laudo_output_snapshot,
        "evidence_manifest": evidence_manifest,
        "mesa_resolution_summary": mesa_resolution_summary or {},
        "document_outcome": document_outcome_text,
    }
    return payload_base, laudo_output_snapshot, evidence_manifest


def load_latest_approved_case_snapshot_for_laudo(
    banco: Session,
    *,
    laudo: Laudo,
) -> ApprovedCaseSnapshot | None:
    return banco.scalar(
        select(ApprovedCaseSnapshot)
        .where(ApprovedCaseSnapshot.laudo_id == int(laudo.id))
        .order_by(ApprovedCaseSnapshot.approval_version.desc(), ApprovedCaseSnapshot.id.desc())
        .limit(1)
    )


def find_replayable_approved_case_snapshot_for_laudo(
    banco: Session,
    *,
    laudo: Laudo,
    approved_by_id: int | None,
    document_outcome: str,
    mesa_resolution_summary: dict[str, Any] | None = None,
) -> ApprovedCaseSnapshot | None:
    latest_snapshot = load_latest_approved_case_snapshot_for_laudo(banco, laudo=laudo)
    if latest_snapshot is None:
        return None

    reopen_anchor = _normalizar_datetime_utc(getattr(laudo, "reaberto_em", None))
    latest_approved_at = _normalizar_datetime_utc(getattr(latest_snapshot, "approved_at", None))

    if reopen_anchor is not None and (
        latest_approved_at is None or latest_approved_at < reopen_anchor
    ):
        return None
    if int(getattr(latest_snapshot, "approved_by_id", 0) or 0) != int(approved_by_id or 0):
        return None
    if str(getattr(latest_snapshot, "document_outcome", "") or "").strip() != (
        str(document_outcome or "").strip() or "approved"
    ):
        return None
    return latest_snapshot


def ensure_approved_case_snapshot_for_laudo(
    banco: Session,
    *,
    laudo: Laudo,
    approved_by_id: int | None,
    document_outcome: str,
    mesa_resolution_summary: dict[str, Any] | None = None,
) -> tuple[ApprovedCaseSnapshot, bool]:
    snapshot_existente = find_replayable_approved_case_snapshot_for_laudo(
        banco,
        laudo=laudo,
        approved_by_id=approved_by_id,
        document_outcome=document_outcome,
        mesa_resolution_summary=mesa_resolution_summary,
    )
    if snapshot_existente is not None:
        resolve_open_return_to_inspector_irregularities(
            banco,
            laudo_id=int(laudo.id),
            resolved_by_id=approved_by_id,
            resolution_mode=OperationalResolutionMode.EDITED_CASE_DATA.value,
            resolution_notes="Fluxo aprovado e consolidado na memoria operacional.",
        )
        return snapshot_existente, True

    payload_base, laudo_output_snapshot, evidence_manifest = _build_approved_case_snapshot_payload_base(
        banco,
        laudo=laudo,
        document_outcome=document_outcome,
        mesa_resolution_summary=mesa_resolution_summary,
    )
    snapshot = registrar_snapshot_aprovado(
        banco,
        ApprovedCaseSnapshotInput(
            laudo_id=int(laudo.id),
            approved_by_id=approved_by_id,
            laudo_output_snapshot=laudo_output_snapshot,
            evidence_manifest=evidence_manifest,
            mesa_resolution_summary=mesa_resolution_summary or {},
            document_outcome=str(document_outcome or "").strip() or "approved",
            technical_tags=_technical_tags_for_laudo(
                laudo,
                document_outcome=str(document_outcome or "").strip() or "approved",
            ),
            snapshot_hash=_hash_payload(payload_base),
        ),
    )
    resolve_open_return_to_inspector_irregularities(
        banco,
        laudo_id=int(laudo.id),
        resolved_by_id=approved_by_id,
        resolution_mode=OperationalResolutionMode.EDITED_CASE_DATA.value,
        resolution_notes="Fluxo aprovado e consolidado na memoria operacional.",
    )
    return snapshot, False


def record_approved_case_snapshot_for_laudo(
    banco: Session,
    *,
    laudo: Laudo,
    approved_by_id: int | None,
    document_outcome: str,
    mesa_resolution_summary: dict[str, Any] | None = None,
) -> ApprovedCaseSnapshot:
    snapshot, _idempotent_replay = ensure_approved_case_snapshot_for_laudo(
        banco,
        laudo=laudo,
        approved_by_id=approved_by_id,
        document_outcome=document_outcome,
        mesa_resolution_summary=mesa_resolution_summary,
    )
    return snapshot


def record_return_to_inspector_irregularity(
    banco: Session,
    *,
    laudo: Laudo,
    actor_user_id: int | None,
    event_type: str,
    block_key: str,
    details: dict[str, Any] | None = None,
    severity: str = OperationalSeverity.WARNING.value,
    evidence_key: str | None = None,
    source: str = "mesa",
) -> tuple[OperationalEvent, OperationalIrregularity]:
    event = registrar_evento_operacional(
        banco,
        OperationalEventInput(
            laudo_id=int(laudo.id),
            actor_user_id=actor_user_id,
            event_type=event_type,
            event_source=source,
            severity=severity,
            block_key=block_key,
            evidence_key=evidence_key,
            event_metadata=details or {},
        ),
    )
    irregularidade_existente = banco.scalar(
        select(OperationalIrregularity)
        .where(
            OperationalIrregularity.laudo_id == int(laudo.id),
            OperationalIrregularity.irregularity_type == str(event_type),
            OperationalIrregularity.block_key == str(block_key),
            OperationalIrregularity.status.in_(_OPEN_IRREGULARITY_STATUSES),
        )
        .order_by(OperationalIrregularity.id.desc())
        .limit(1)
    )
    if irregularidade_existente is not None:
        irregularidade_existente.source_event_id = event.id
        irregularidade_existente.detected_by_user_id = actor_user_id
        irregularidade_existente.details_json = details or None
        irregularidade_existente.evidence_key = evidence_key
        irregularidade_existente.atualizado_em = _agora_utc()
        banco.flush()
        return event, irregularidade_existente

    irregularidade = abrir_irregularidade_operacional(
        banco,
        OperationalIrregularityInput(
            laudo_id=int(laudo.id),
            irregularity_type=event_type,
            severity=severity,
            detected_by=source,
            detected_by_user_id=actor_user_id,
            source_event_id=event.id,
            block_key=block_key,
            evidence_key=evidence_key,
            details=details or {},
        ),
    )
    return event, irregularidade


def resolve_open_return_to_inspector_irregularities(
    banco: Session,
    *,
    laudo_id: int,
    resolved_by_id: int | None,
    resolution_mode: str,
    resolution_notes: str,
    block_key: str | None = None,
    evidence_key: str | None = None,
) -> list[int]:
    consulta = select(OperationalIrregularity).where(
        OperationalIrregularity.laudo_id == int(laudo_id),
        OperationalIrregularity.irregularity_type.in_(_RETURN_TO_INSPECTOR_TYPES),
        OperationalIrregularity.status.in_(_OPEN_IRREGULARITY_STATUSES),
    )
    if block_key is not None:
        consulta = consulta.where(OperationalIrregularity.block_key == str(block_key))
    if evidence_key is not None:
        consulta = consulta.where(OperationalIrregularity.evidence_key == str(evidence_key))

    registros = list(banco.scalars(consulta).all())
    resolvidos: list[int] = []
    for registro in registros:
        resolver_irregularidade_operacional(
            banco,
            irregularity_id=int(registro.id),
            payload=OperationalIrregularityResolutionInput(
                resolution_mode=resolution_mode,
                resolved_by_id=resolved_by_id,
                resolution_notes=resolution_notes,
            ),
        )
        resolvidos.append(int(registro.id))
    return resolvidos


def record_quality_gate_validations(
    banco: Session,
    *,
    laudo: Laudo,
    gate_result: dict[str, Any],
    actor_user_id: int | None = None,
) -> list[EvidenceValidation]:
    gate_payload = gate_result if isinstance(gate_result, dict) else {}
    report_pack = gate_payload.get("report_pack_draft") if isinstance(gate_payload.get("report_pack_draft"), dict) else {}
    quality_gates_payload = (
        report_pack.get("quality_gates")
        if isinstance(report_pack, dict)
        else None
    )
    quality_gates = quality_gates_payload if isinstance(quality_gates_payload, dict) else {}
    missing_evidence = list((quality_gates or {}).get("missing_evidence") or [])
    faltantes = list(gate_payload.get("faltantes") or [])
    touched_keys: set[str] = set()
    registros: list[EvidenceValidation] = []
    now = _agora_utc()

    image_slots_payload = report_pack.get("image_slots") if isinstance(report_pack, dict) else None
    image_slots = image_slots_payload if isinstance(image_slots_payload, list) else []
    for slot in image_slots:
        if not isinstance(slot, dict):
            continue
        slot_code = str(slot.get("slot") or "").strip()
        if not slot_code:
            continue
        evidence_key = f"slot:{slot_code}"
        touched_keys.add(evidence_key)
        resolved = str(slot.get("status") or "").strip() == "resolved"
        failure_reasons = [str(item).strip() for item in list(slot.get("missing_evidence") or []) if str(item).strip()]
        registros.append(
            registrar_validacao_evidencia(
                banco,
                EvidenceValidationInput(
                    laudo_id=int(laudo.id),
                    evidence_key=evidence_key,
                    component_type=slot_code,
                    view_angle=_texto_curto(slot.get("title"), limite=80),
                    quality_score=100 if resolved else 0,
                    coherence_score=100 if resolved else 0,
                    operational_status=(
                        EvidenceOperationalStatus.OK.value if resolved else EvidenceOperationalStatus.IRREGULAR.value
                    ),
                    mesa_status=EvidenceMesaStatus.NOT_REVIEWED.value,
                    failure_reasons=failure_reasons,
                    evidence_metadata={
                        "source": "report_pack_image_slot",
                        "slot": slot_code,
                        "title": _texto_curto(slot.get("title"), limite=160),
                        "required": bool(slot.get("required")),
                        "resolved_message_id": slot.get("resolved_message_id"),
                        "resolved_caption": _texto_curto(slot.get("resolved_caption")),
                    },
                    replacement_evidence_key=_texto_curto(slot.get("resolved_evidence_id"), limite=160),
                    validated_by_user_id=actor_user_id,
                    last_evaluated_at=now,
                ),
            )
        )

    for missing in missing_evidence:
        if not isinstance(missing, dict):
            continue
        kind = str(missing.get("kind") or "").strip() or "gate"
        if kind == "image_slot":
            continue
        ref = str(missing.get("item_codigo") or missing.get("slot") or missing.get("code") or "generic").strip()
        evidence_key = f"gate:{kind}:{ref}"
        touched_keys.add(evidence_key)
        registros.append(
            registrar_validacao_evidencia(
                banco,
                EvidenceValidationInput(
                    laudo_id=int(laudo.id),
                    evidence_key=evidence_key,
                    component_type=kind[:80],
                    quality_score=0,
                    coherence_score=0,
                    operational_status=EvidenceOperationalStatus.IRREGULAR.value,
                    mesa_status=EvidenceMesaStatus.NOT_REVIEWED.value,
                    failure_reasons=[str(missing.get("code") or ref).strip()],
                    evidence_metadata={
                        "source": "quality_gate_missing_evidence",
                        "kind": kind,
                        "message": _texto_curto(missing.get("message"), limite=280),
                        "reference": ref,
                    },
                    validated_by_user_id=actor_user_id,
                    last_evaluated_at=now,
                ),
            )
        )

    if not touched_keys:
        evidence_key = "gate:summary"
        touched_keys.add(evidence_key)
        failure_reasons = [
            str(item.get("id") or item.get("code") or "").strip()
            for item in faltantes
            if isinstance(item, dict) and str(item.get("id") or item.get("code") or "").strip()
        ]
        registros.append(
            registrar_validacao_evidencia(
                banco,
                EvidenceValidationInput(
                    laudo_id=int(laudo.id),
                    evidence_key=evidence_key,
                    component_type="quality_gate",
                    quality_score=100 if bool(gate_payload.get("aprovado")) else 0,
                    coherence_score=100 if bool(gate_payload.get("aprovado")) else 0,
                    operational_status=(
                        EvidenceOperationalStatus.OK.value
                        if bool(gate_payload.get("aprovado"))
                        else EvidenceOperationalStatus.IRREGULAR.value
                    ),
                    mesa_status=EvidenceMesaStatus.NOT_REVIEWED.value,
                    failure_reasons=failure_reasons,
                    evidence_metadata={
                        "source": "quality_gate_summary",
                        "codigo": str(gate_payload.get("codigo") or "").strip(),
                        "template": str(gate_payload.get("tipo_template") or "").strip(),
                        "mensagem": _texto_curto(gate_payload.get("mensagem"), limite=280),
                        "resumo": dict(gate_payload.get("resumo") or {}),
                    },
                    validated_by_user_id=actor_user_id,
                    last_evaluated_at=now,
                ),
            )
        )

    stale_gate_keys = list(
        banco.scalars(
            select(EvidenceValidation).where(
                EvidenceValidation.laudo_id == int(laudo.id),
                EvidenceValidation.evidence_key.like("gate:%"),
            )
        ).all()
    )
    for registro in stale_gate_keys:
        if str(registro.evidence_key or "") in touched_keys:
            continue
        registro.operational_status = EvidenceOperationalStatus.OK.value
        registro.mesa_status = EvidenceMesaStatus.NOT_REVIEWED.value
        registro.failure_reasons_json = None
        registro.last_evaluated_at = now
        registro.atualizado_em = now
    if stale_gate_keys:
        banco.flush()

    return registros


__all__ = [
    "ensure_approved_case_snapshot_for_laudo",
    "find_replayable_approved_case_snapshot_for_laudo",
    "load_latest_approved_case_snapshot_for_laudo",
    "record_approved_case_snapshot_for_laudo",
    "record_quality_gate_validations",
    "record_return_to_inspector_irregularity",
    "resolve_open_return_to_inspector_irregularities",
]
