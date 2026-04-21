"""Builders runtime compartilhados dos report packs semanticos."""

from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Any

from pydantic import ValidationError

from app.domains.chat.normalization import (
    nome_template_humano,
    normalizar_tipo_template,
    resolver_familia_padrao_template,
)
from app.domains.chat.report_pack_pre_laudo import (
    _build_analysis_basis,
    _extract_message_text,
    _looks_like_document_message,
    _looks_like_photo_message,
)
from app.domains.chat.schemas import GuidedInspectionDraftPayload
from app.domains.chat.templates_ai import (
    MAPA_VERIFICACOES_CBMGO,
    TITULOS_SECOES_CBMGO,
    obter_schema_template_ia,
)
from app.shared.database import Laudo, MensagemLaudo
from nucleo.inspetor.confianca_ia import estimar_conflict_score_normativo

_REPORT_PACK_CONTRACT_NAME = "SemanticReportPackDraftV1"
_REPORT_PACK_VERSION = "v1"
_CBMGO_FAMILY = "cbmgo_vistoria_bombeiro"
_CBMGO_IMAGE_SLOTS = (
    ("foto_fachada_ou_vista_geral", "Vista geral ou fachada"),
    ("foto_achado_estrutural", "Achado estrutural relevante"),
    ("foto_documento_apoio", "Documento ou evidência de apoio"),
)
_CBMGO_SECTION_CRITICALITY = {
    "seguranca_estrutural": "alta",
    "cmar": "media",
    "verificacao_documental": "alta",
    "recomendacoes_gerais": "alta",
}
_CBMGO_HIGH_RISK_ITEMS = {
    "recomendacoes_gerais.item_01_interdicao",
    "recomendacoes_gerais.item_03_intervencao_imediata",
}


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", normalized)


def _normalize_guided_draft(raw_value: Any) -> dict[str, Any] | None:
    if raw_value is None:
        return None
    try:
        payload = GuidedInspectionDraftPayload.model_validate(raw_value)
    except ValidationError:
        return None
    return payload.model_dump(mode="python")


def _copy_dict_payload(raw_value: Any) -> dict[str, Any] | None:
    if not isinstance(raw_value, dict):
        return None
    return deepcopy(raw_value)


def _looks_like_catalog_structured_payload(laudo: Laudo) -> bool:
    payload = getattr(laudo, "dados_formulario", None)
    if not isinstance(payload, dict):
        return False
    schema_type = str(payload.get("schema_type") or "").strip().lower()
    payload_family_key = str(payload.get("family_key") or "").strip().lower()
    laudo_family_key = str(getattr(laudo, "catalog_family_key", "") or "").strip().lower()
    return bool(schema_type == "laudo_output" or payload_family_key or laudo_family_key)


def _count_catalog_thread_evidence(
    *,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
) -> dict[str, int]:
    text_count = 0
    image_count = 0
    document_count = 0
    evidence_count = 0
    for message in user_messages:
        is_text = bool(_extract_message_text(message))
        is_image = _looks_like_photo_message(message, visual_message_ids)
        is_document = _looks_like_document_message(message)
        if is_text:
            text_count += 1
        if is_image:
            image_count += 1
        if is_document:
            document_count += 1
        evidence_count += int(is_text) + int(is_image) + int(is_document)
    return {
        "text_count": text_count,
        "image_count": image_count,
        "document_count": document_count,
        "evidence_count": evidence_count,
    }


def _validated_structured_payload(
    *,
    laudo: Laudo,
    template_key: str,
) -> dict[str, Any] | None:
    schema = obter_schema_template_ia(template_key)
    raw_payload = getattr(laudo, "dados_formulario", None)
    if schema is None or not isinstance(raw_payload, dict):
        return None
    try:
        validated = schema.model_validate(raw_payload)
    except ValidationError:
        return None
    return validated.model_dump(mode="python")


def _build_image_slots_from_refs(
    *,
    image_slots: tuple[tuple[str, str], ...],
    guided_draft: dict[str, Any] | None,
    user_messages: list[MensagemLaudo] | None = None,
    visual_message_ids: set[int] | None = None,
) -> list[dict[str, Any]]:
    photo_refs = [
        ref
        for ref in list((guided_draft or {}).get("evidence_refs") or [])
        if str(ref.get("step_id") or "").strip() == "registros_fotograficos"
        and str(ref.get("attachment_kind") or "").strip() in {"image", "mixed"}
    ]
    resolved_message_ids = {
        int(ref.get("message_id") or 0)
        for ref in photo_refs
        if int(ref.get("message_id") or 0) > 0
    }
    for message in user_messages or []:
        message_id = int(getattr(message, "id", 0) or 0)
        if message_id <= 0 or message_id in resolved_message_ids:
            continue
        if not _looks_like_photo_message(message, visual_message_ids or set()):
            continue
        photo_refs.append(
            {
                "message_id": message_id,
                "step_id": "registros_fotograficos",
                "step_title": f"Registro fotografico {len(photo_refs) + 1}",
                "attachment_kind": "image",
            }
        )
        resolved_message_ids.add(message_id)
    resolved_slots: list[dict[str, Any]] = []
    for index, (slot_code, slot_title) in enumerate(image_slots):
        resolved = photo_refs[index] if index < len(photo_refs) else None
        resolved_slots.append(
            {
                "slot": slot_code,
                "title": slot_title,
                "required": True,
                "status": "resolved" if resolved else "pending",
                "step_id": "registros_fotograficos",
                "resolved_message_id": int(resolved.get("message_id") or 0) if resolved else None,
                "resolved_evidence_id": (
                    f"msg:{int(resolved.get('message_id') or 0)}" if resolved else None
                ),
                "resolved_caption": str(resolved.get("step_title") or "").strip() if resolved else "",
                "missing_evidence": [] if resolved else ["foto_obrigatoria_ausente"],
            }
        )
    return resolved_slots


def _build_catalog_backed_report_pack_draft(
    *,
    laudo: Laudo,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
    visual_attachment_by_message_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    template_key = normalizar_tipo_template(getattr(laudo, "tipo_template", "padrao"))
    family_binding = resolver_familia_padrao_template(template_key)
    guided_draft = _normalize_guided_draft(getattr(laudo, "guided_inspection_draft_json", None))
    checklist = list((guided_draft or {}).get("checklist") or [])
    checklist_ids = [
        str(item.get("id") or "").strip()
        for item in checklist
        if str(item.get("id") or "").strip()
    ]
    completed_step_ids = {
        str(item).strip()
        for item in list((guided_draft or {}).get("completed_step_ids") or [])
        if str(item).strip()
    }
    checklist_complete = not checklist_ids or set(checklist_ids).issubset(completed_step_ids)
    payload = _copy_dict_payload(getattr(laudo, "dados_formulario", None))
    family_key = str(
        getattr(laudo, "catalog_family_key", None)
        or (payload or {}).get("family_key")
        or family_binding.get("family_key")
        or getattr(laudo, "tipo_template", "")
        or "padrao"
    ).strip().lower() or "padrao"
    family_label = (
        str(getattr(laudo, "catalog_family_label", "") or "").strip()
        or str((payload or {}).get("family_label") or "").strip()
        or str(family_binding.get("family_label") or "").strip()
        or nome_template_humano(template_key)
    )
    evidence_counts = _count_catalog_thread_evidence(
        user_messages=user_messages,
        visual_message_ids=visual_message_ids,
    )
    image_step_present = "registros_fotograficos" in set(checklist_ids)
    required_image_slots_complete = (
        not image_step_present or int(evidence_counts["image_count"]) > 0
    )
    missing_evidence: list[dict[str, Any]] = []
    if payload is None:
        missing_evidence.append(
            {
                "code": "catalog_structured_form_missing",
                "kind": "structured_form",
                "message": "O payload estruturado catalogado ainda nao foi materializado para esta familia.",
            }
        )
    if checklist_ids and not checklist_complete:
        missing_evidence.append(
            {
                "code": "guided_checklist_incomplete",
                "kind": "checklist",
                "message": "O checklist guiado desta familia ainda nao foi concluido.",
            }
        )
    if image_step_present and not required_image_slots_complete:
        missing_evidence.append(
            {
                "code": "catalog_guided_image_missing",
                "kind": "image_slot",
                "message": "A etapa guiada de registros fotograficos ainda nao possui evidencia visual suficiente.",
            }
        )
    if int(evidence_counts["evidence_count"]) <= 0:
        missing_evidence.append(
            {
                "code": "catalog_case_thread_empty",
                "kind": "evidence",
                "message": "Nao ha evidencias suficientes no case thread para sustentar o pacote incremental.",
            }
        )

    return {
        "contract_name": _REPORT_PACK_CONTRACT_NAME,
        "contract_version": _REPORT_PACK_VERSION,
        "modeled": True,
        "template_key": template_key,
        "template_label": family_label,
        "family": family_key,
        "pack_version": _REPORT_PACK_VERSION,
        "evidence_bundle_kind": "case_thread",
        "evidence_summary": {
            "user_message_count": len(user_messages),
            "evidence_count": int(evidence_counts["evidence_count"]),
            "image_count": int(evidence_counts["image_count"]),
            "document_count": int(evidence_counts["document_count"]),
            "text_count": int(evidence_counts["text_count"]),
        },
        "guided_context": {
            "checklist_ids": checklist_ids,
            "completed_step_ids": sorted(completed_step_ids),
            "has_guided_draft": bool(guided_draft),
        },
        "items": [],
        "image_slots": [],
        "quality_gates": {
            "checklist_complete": checklist_complete,
            "required_image_slots_complete": required_image_slots_complete,
            "critical_items_complete": payload is not None,
            "missing_evidence": missing_evidence,
            "max_conflict_score": 0 if not missing_evidence else 100,
            "requires_normative_curation": False,
            "learning_eligible": False,
            "autonomy_ready": False,
            "final_validation_mode": "mesa_required",
        },
        "structured_data_candidate": payload,
        "telemetry": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or ""),
            "entry_mode_effective": str(getattr(laudo, "entry_mode_effective", "") or ""),
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or ""),
            "guided_evidence_gap_count": len(missing_evidence),
            "mode_switch_observed": (
                str(getattr(laudo, "entry_mode_preference", "") or "")
                != str(getattr(laudo, "entry_mode_effective", "") or "")
            ),
            "modeled_strategy": "catalog_structured_payload_fallback",
        },
        "analysis_basis": _build_analysis_basis(
            laudo=laudo,
            user_messages=user_messages,
            visual_message_ids=visual_message_ids,
            visual_attachment_by_message_id=visual_attachment_by_message_id,
            final_validation_mode="mesa_required",
        ),
    }


def _cbmgo_item_criticality(section_key: str, item_key: str) -> str:
    item_path = f"{section_key}.{item_key}"
    if item_path in _CBMGO_HIGH_RISK_ITEMS:
        return "alta"
    return _CBMGO_SECTION_CRITICALITY.get(section_key, "media")


def _build_cbmgo_items(
    structured_payload: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    items: list[dict[str, Any]] = []
    missing_item_codes: list[str] = []
    nonconformity_codes: list[str] = []
    critical_nonconformity_codes: list[str] = []

    for section_key, section_map in MAPA_VERIFICACOES_CBMGO.items():
        section_payload = structured_payload.get(section_key) if isinstance(structured_payload, dict) else None
        for item_key, description in section_map.items():
            item_payload = section_payload.get(item_key) if isinstance(section_payload, dict) else None
            condicao = (
                str(item_payload.get("condicao") or "").strip()
                if isinstance(item_payload, dict)
                else ""
            )
            observacao = (
                str(item_payload.get("observacao") or "").strip()
                if isinstance(item_payload, dict)
                else ""
            )
            localizacao = (
                str(item_payload.get("localizacao") or "").strip()
                if isinstance(item_payload, dict)
                else ""
            )
            criticidade = _cbmgo_item_criticality(section_key, item_key)
            contradictory_markers = int(
                condicao == "NC" and "conforme" in _normalize_text(f"{localizacao} {observacao}")
            )
            conflict = estimar_conflict_score_normativo(
                texto=f"{localizacao} {observacao}".strip(),
                missing_evidence_count=0 if condicao else 1,
                contradictory_markers=contradictory_markers,
            )
            item_code = f"{section_key}.{item_key}"
            if not condicao:
                missing_item_codes.append(item_code)
            elif condicao == "NC":
                nonconformity_codes.append(item_code)
                if criticidade == "alta":
                    critical_nonconformity_codes.append(item_code)

            items.append(
                {
                    "item_codigo": item_code,
                    "titulo": description,
                    "secao": section_key,
                    "secao_titulo": TITULOS_SECOES_CBMGO.get(section_key, section_key),
                    "criticidade": criticidade,
                    "veredito_ia_normativo": condicao or "pendente",
                    "confidence_ia": "alta" if condicao else "baixa",
                    "norma_refs": ["CBMGO report pack piloto v1"],
                    "rule_version": _REPORT_PACK_VERSION,
                    "evidence_refs": [],
                    "human_review_required": condicao == "NC" or not condicao,
                    "missing_evidence": [] if condicao else ["status_normativo_nao_confirmado"],
                    "observacoes": " | ".join(part for part in (localizacao, observacao) if part)[:280],
                    "conflict_score": int(conflict.get("score") or 0),
                    "conflict_severity": str(conflict.get("severity") or "low"),
                    "approved_for_emission": condicao in {"C", "N/A"},
                    "override_reason": None,
                    "override_class": None,
                    "learning_disposition": (
                        "blocked_nonconformity"
                        if condicao == "NC"
                        else "eligible"
                        if condicao
                        else "blocked_missing_evidence"
                    ),
                    "curation_required": bool(
                        conflict.get("requires_human_review") or condicao == "NC" or not condicao
                    ),
                }
            )

    return items, missing_item_codes, nonconformity_codes, critical_nonconformity_codes


def _build_cbmgo_report_pack_draft(
    *,
    laudo: Laudo,
    guided_draft: dict[str, Any] | None,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
    visual_attachment_by_message_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    checklist = list((guided_draft or {}).get("checklist") or [])
    checklist_ids = [
        str(item.get("id") or "").strip()
        for item in checklist
        if str(item.get("id") or "").strip()
    ]
    completed_step_ids = set((guided_draft or {}).get("completed_step_ids") or [])
    checklist_complete = (
        bool(checklist_ids) and set(checklist_ids).issubset(completed_step_ids)
    ) or bool(_validated_structured_payload(laudo=laudo, template_key="cbmgo"))
    structured_payload = _validated_structured_payload(laudo=laudo, template_key="cbmgo")
    image_slots = _build_image_slots_from_refs(
        image_slots=_CBMGO_IMAGE_SLOTS,
        guided_draft=guided_draft,
        user_messages=user_messages,
        visual_message_ids=visual_message_ids,
    )
    unresolved_slots = [slot["slot"] for slot in image_slots if slot["status"] != "resolved"]
    (
        item_rows,
        missing_item_codes,
        nonconformity_codes,
        critical_nonconformity_codes,
    ) = _build_cbmgo_items(structured_payload)
    max_conflict_score = max(
        [int(item.get("conflict_score") or 0) for item in item_rows] or [0]
    )
    entry_mode_effective = str(getattr(laudo, "entry_mode_effective", "") or "").strip()
    structured_form_ready = structured_payload is not None
    autonomy_ready = (
        structured_form_ready
        and checklist_complete
        and not unresolved_slots
        and not nonconformity_codes
        and max_conflict_score < 70
        and entry_mode_effective == "evidence_first"
    )
    missing_evidence: list[dict[str, Any]] = []
    if not checklist_complete:
        missing_evidence.append(
            {
                "code": "guided_checklist_incomplete",
                "kind": "checklist",
                "message": "O checklist guiado da familia CBMGO ainda nao foi concluido.",
            }
        )
    if not structured_form_ready:
        missing_evidence.append(
            {
                "code": "cbmgo_structured_form_missing",
                "kind": "structured_form",
                "message": "O formulario estruturado CBMGO ainda nao foi materializado no caso.",
            }
        )
    for slot_code in unresolved_slots:
        missing_evidence.append(
            {
                "code": "cbmgo_image_slot_missing",
                "kind": "image_slot",
                "slot": slot_code,
                "message": f"Falta evidencia fotografica obrigatoria para {slot_code}.",
            }
        )
    for item_code in missing_item_codes:
        missing_evidence.append(
            {
                "code": "cbmgo_item_status_missing",
                "kind": "normative_item",
                "item_codigo": item_code,
                "message": f"Falta status normativo do item {item_code}.",
            }
        )

    final_validation_mode = "mobile_autonomous" if autonomy_ready else "mesa_required"
    return {
        "contract_name": _REPORT_PACK_CONTRACT_NAME,
        "contract_version": _REPORT_PACK_VERSION,
        "modeled": True,
        "template_key": "cbmgo",
        "template_label": nome_template_humano("cbmgo"),
        "family": _CBMGO_FAMILY,
        "pack_version": _REPORT_PACK_VERSION,
        "evidence_bundle_kind": "case_thread",
        "evidence_summary": {
            "user_message_count": len(user_messages),
            "evidence_count": len(user_messages),
            "image_count": len([slot for slot in image_slots if slot["status"] == "resolved"]),
        },
        "guided_context": {
            "checklist_ids": checklist_ids,
            "completed_step_ids": sorted(completed_step_ids),
            "has_guided_draft": bool(guided_draft),
        },
        "items": item_rows,
        "image_slots": image_slots,
        "quality_gates": {
            "checklist_complete": checklist_complete,
            "required_image_slots_complete": not unresolved_slots,
            "critical_items_complete": structured_form_ready and not missing_item_codes,
            "missing_evidence": missing_evidence,
            "max_conflict_score": max_conflict_score,
            "requires_normative_curation": bool(critical_nonconformity_codes) or max_conflict_score >= 70,
            "learning_eligible": autonomy_ready,
            "autonomy_ready": autonomy_ready,
            "final_validation_mode": final_validation_mode,
        },
        "structured_data_candidate": structured_payload,
        "telemetry": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or ""),
            "entry_mode_effective": entry_mode_effective,
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or ""),
            "guided_evidence_gap_count": len(missing_evidence),
            "mode_switch_observed": (
                str(getattr(laudo, "entry_mode_preference", "") or "")
                != str(getattr(laudo, "entry_mode_effective", "") or "")
            ),
            "nonconformity_count": len(nonconformity_codes),
            "critical_nonconformity_count": len(critical_nonconformity_codes),
        },
        "analysis_basis": _build_analysis_basis(
            laudo=laudo,
            user_messages=user_messages,
            visual_message_ids=visual_message_ids,
            visual_attachment_by_message_id=visual_attachment_by_message_id,
            image_slots=image_slots,
            final_validation_mode=final_validation_mode,
        ),
    }


__all__ = [
    "_CBMGO_FAMILY",
    "_REPORT_PACK_CONTRACT_NAME",
    "_REPORT_PACK_VERSION",
    "_build_catalog_backed_report_pack_draft",
    "_build_cbmgo_report_pack_draft",
    "_build_image_slots_from_refs",
    "_copy_dict_payload",
    "_looks_like_catalog_structured_payload",
    "_normalize_guided_draft",
    "_normalize_text",
]
