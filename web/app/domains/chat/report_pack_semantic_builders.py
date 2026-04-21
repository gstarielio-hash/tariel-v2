"""Builders semanticos do draft incremental de report packs."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from app.domains.chat.catalog_pdf_templates import materialize_catalog_payload_for_laudo
from app.domains.chat.report_pack_documentary_builders import (
    _build_nr10_prontuario_items,
    _build_nr13_caldeira_items,
    _build_nr13_vaso_pressao_items,
    _build_nr20_prontuario_items,
)
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
    _message_payload,
)
from app.domains.chat.report_pack_runtime_builders import (
    _REPORT_PACK_CONTRACT_NAME,
    _REPORT_PACK_VERSION,
    _build_image_slots_from_refs,
    _copy_dict_payload,
    _normalize_guided_draft,
    _normalize_text,
)
from app.domains.chat.templates_ai import MAPA_COMPONENTES_NR35_LINHA_VIDA
from app.shared.database import Laudo, MensagemLaudo
from nucleo.inspetor.confianca_ia import estimar_conflict_score_normativo

_NR35_FAMILY = "nr35_periodica_linha_vida"
_NR35_ANCHOR_FAMILY = "nr35_inspecao_ponto_ancoragem"
_NR13_VASO_PRESSAO_FAMILY = "nr13_inspecao_vaso_pressao"
_NR13_CALDEIRA_FAMILY = "nr13_inspecao_caldeira"
_NR10_PRONTUARIO_FAMILY = "nr10_prontuario_instalacoes_eletricas"
_NR20_PRONTUARIO_FAMILY = "nr20_prontuario_instalacoes_inflamaveis"
_NR35_IMAGE_SLOTS = (
    ("foto_visao_geral", "Vista geral da linha de vida"),
    ("foto_ponto_superior", "Ponto superior"),
    ("foto_ponto_inferior", "Ponto inferior"),
)
_NR35_ANCHOR_IMAGE_SLOTS = (
    ("foto_visao_geral", "Vista geral do ponto de ancoragem"),
    ("foto_fixacao_base", "Base e fixacao do ponto de ancoragem"),
    ("foto_achado_principal", "Detalhe do achado principal"),
)
_NR13_CALDEIRA_IMAGE_SLOTS = (
    ("foto_placa_identificacao", "Placa de identificacao"),
    ("foto_painel_comandos", "Painel e comandos"),
    ("foto_achado_principal", "Achado principal"),
)
_NR13_VASO_PRESSAO_IMAGE_SLOTS = (
    ("foto_placa_identificacao", "Placa de identificacao"),
    ("foto_dispositivos_seguranca", "Dispositivos de seguranca"),
    ("foto_achado_principal", "Achado principal"),
)
_NR20_PRONTUARIO_IMAGE_SLOTS = (
    ("foto_referencia_principal", "Referencia principal"),
    ("foto_documento_base", "Documento base"),
)
_NR10_PRONTUARIO_IMAGE_SLOTS = (
    ("foto_referencia_principal", "Referencia principal"),
    ("foto_documento_base", "Documento base"),
)
_NR35_COMPONENT_SPECS = (
    ("fixacao_dos_pontos", "Fixacao dos pontos", "alta"),
    ("condicao_cabo_aco", "Condicao do cabo de aco", "alta"),
    ("condicao_esticador", "Condicao do esticador", "media"),
    ("condicao_sapatilha", "Condicao da sapatilha", "media"),
    ("condicao_olhal", "Condicao do olhal", "media"),
    ("condicao_grampos", "Condicao dos grampos", "alta"),
)
_NR35_ANCHOR_COMPONENT_SPECS = (
    ("fixacao", "Fixacao e base metalica", "alta"),
    ("chumbador", "Chumbador e torque aparente", "alta"),
    ("corrosao", "Corrosao visivel", "alta"),
    ("deformacao", "Deformacao aparente", "alta"),
    ("trinca", "Trincas e fissuras aparentes", "alta"),
)
_VERDICT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("N/A", ("nao se aplica", "não se aplica", r"\bn/?a\b", r"\bna\b")),
    ("NC", ("nao conforme", "não conforme", "reprovado", r"\bnc\b")),
    ("C", ("conforme", "aprovado", r"\bc\b")),
)


def _find_message_by_id(messages: list[MensagemLaudo], message_id: int) -> MensagemLaudo | None:
    for message in messages:
        if int(getattr(message, "id", 0) or 0) == int(message_id):
            return message
    return None


def _step_texts_from_guided_draft(
    *,
    guided_draft: dict[str, Any] | None,
    user_messages: list[MensagemLaudo],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    if not guided_draft:
        return result
    for ref in list(guided_draft.get("evidence_refs") or []):
        try:
            message_id = int(ref.get("message_id") or 0)
        except (TypeError, ValueError):
            continue
        if message_id <= 0:
            continue
        message = _find_message_by_id(user_messages, message_id)
        if message is None:
            continue
        step_id = str(ref.get("step_id") or "").strip()
        if not step_id:
            continue
        payload = _message_payload(message)
        payload["attachment_kind"] = str(ref.get("attachment_kind") or "none").strip() or "none"
        payload["step_title"] = str(ref.get("step_title") or "").strip()
        result.setdefault(step_id, []).append(payload)
    return result


def _infer_verdict_from_text(text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    for verdict, patterns in _VERDICT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, normalized):
                return verdict
    return None


def _component_aliases(component_key: str) -> tuple[str, ...]:
    aliases = {
        "fixacao_dos_pontos": ("fixacao dos pontos", "fixacao", "pontos de ancoragem"),
        "condicao_cabo_aco": ("cabo de aco", "cabo", "linha de vida"),
        "condicao_esticador": ("esticador", "tensionamento"),
        "condicao_sapatilha": ("sapatilha",),
        "condicao_olhal": ("olhal",),
        "condicao_grampos": ("grampos", "grampo"),
    }
    return aliases.get(component_key, (component_key.replace("_", " "),))


def _parse_component_item(step_entries: list[dict[str, Any]], component_key: str) -> dict[str, Any]:
    aliases = _component_aliases(component_key)
    best_text = ""
    verdict = None
    for entry in step_entries:
        text = str(entry.get("text") or "").strip()
        normalized = _normalize_text(text)
        if not normalized:
            continue
        if not any(alias in normalized for alias in aliases):
            continue
        for line in normalized.splitlines() or [normalized]:
            if any(alias in line for alias in aliases):
                verdict = _infer_verdict_from_text(line)
                if verdict:
                    best_text = text
                    break
        if verdict:
            break
    conflict = estimar_conflict_score_normativo(
        texto=best_text,
        missing_evidence_count=0 if verdict else 1,
        contradictory_markers=0,
    )
    missing_evidence = [] if verdict else ["status_normativo_nao_confirmado"]
    return {
        "item_codigo": component_key,
        "titulo": MAPA_COMPONENTES_NR35_LINHA_VIDA.get(component_key, component_key.replace("_", " ")),
        "criticidade": next(
            (criticality for key, _title, criticality in _NR35_COMPONENT_SPECS if key == component_key),
            "media",
        ),
        "veredito_ia_normativo": verdict or "pendente",
        "confidence_ia": "alta" if verdict else "baixa",
        "norma_refs": ["NR35 report pack piloto v1"],
        "rule_version": _REPORT_PACK_VERSION,
        "evidence_refs": [entry["message_id"] for entry in step_entries if entry.get("text")],
        "human_review_required": not bool(verdict),
        "missing_evidence": missing_evidence,
        "observacoes": best_text[:280] if best_text else "",
        "conflict_score": int(conflict.get("score") or 0),
        "conflict_severity": str(conflict.get("severity") or "low"),
        "approved_for_emission": bool(verdict),
        "override_reason": None,
        "override_class": None,
        "learning_disposition": "eligible" if verdict else "blocked_missing_evidence",
        "curation_required": bool(conflict.get("requires_human_review") or not verdict),
    }


def _extract_first_match(texts: list[str], patterns: tuple[str, ...]) -> str:
    for text in texts:
        normalized = _normalize_text(text)
        if not normalized:
            continue
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return str(match.group(1) or "").strip(" .,:;-")
    return ""


def _extract_nr35_conclusion_status(texts: list[str]) -> str:
    for text in texts:
        normalized = _normalize_text(text)
        if "aprovado" in normalized:
            return "Aprovado"
        if "reprovado" in normalized:
            return "Reprovado"
        if "pendente" in normalized:
            return "Pendente"
    return "Não informado"


def _materialize_catalog_candidate_without_mutation(
    *,
    laudo: Laudo,
    source_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    proxy = Laudo(
        empresa_id=int(getattr(laudo, "empresa_id", 0) or 0),
        usuario_id=getattr(laudo, "usuario_id", None),
        setor_industrial=str(getattr(laudo, "setor_industrial", "") or ""),
        tipo_template=str(getattr(laudo, "tipo_template", "padrao") or "padrao"),
        codigo_hash=str(getattr(laudo, "codigo_hash", "") or ""),
    )
    proxy.id = getattr(laudo, "id", None)
    proxy.catalog_family_key = (
        getattr(laudo, "catalog_family_key", None)
        or resolver_familia_padrao_template(getattr(laudo, "tipo_template", None)).get("family_key")
    )
    proxy.catalog_family_label = getattr(laudo, "catalog_family_label", None)
    proxy.catalog_variant_key = getattr(laudo, "catalog_variant_key", None)
    proxy.catalog_variant_label = getattr(laudo, "catalog_variant_label", None)
    proxy.status_revisao = getattr(laudo, "status_revisao", None)
    proxy.parecer_ia = getattr(laudo, "parecer_ia", None)
    proxy.primeira_mensagem = getattr(laudo, "primeira_mensagem", None)
    proxy.motivo_rejeicao = getattr(laudo, "motivo_rejeicao", None)
    proxy.pdf_template_snapshot_json = deepcopy(getattr(laudo, "pdf_template_snapshot_json", None))
    proxy.report_pack_draft_json = deepcopy(getattr(laudo, "report_pack_draft_json", None))
    proxy.dados_formulario = deepcopy(source_payload)
    candidate = materialize_catalog_payload_for_laudo(
        laudo=proxy,
        source_payload=deepcopy(source_payload),
    )
    return candidate if isinstance(candidate, dict) else None


def _nr35_anchor_source_payload(laudo: Laudo) -> dict[str, Any]:
    payload = _copy_dict_payload(getattr(laudo, "dados_formulario", None)) or {}
    if any(str(payload.get(field_key) or "").strip() for field_key, _title, _criticality in _NR35_ANCHOR_COMPONENT_SPECS):
        return payload
    return {}


def _nr35_anchor_field_verdict(field_key: str, text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    absence_patterns = (
        r"\bsem\b",
        r"\bnao ha\b",
        r"\bnao foram observad",
        r"\bnao foi observad",
        r"\binexistente\b",
        r"\btorque conferid",
        r"\bintegra\b",
        r"\bintegro\b",
        r"\bconforme\b",
        r"\badequad",
        r"\bregular\b",
    )
    if field_key in {"corrosao", "deformacao", "trinca"}:
        if any(re.search(pattern, normalized) for pattern in absence_patterns):
            return "C"
        return "NC"

    negative_patterns = (
        r"\bcorros",
        r"\btrinca",
        r"\bfissura",
        r"\bdeforma",
        r"\bsolt",
        r"\bfolga",
        r"\bafroux",
        r"\bdesgast",
        r"\boxid",
        r"\binadequad",
        r"\bnao conforme\b",
        r"\bausent",
    )
    if any(re.search(pattern, normalized) for pattern in negative_patterns):
        return "NC"
    return "C"


def _build_nr35_anchor_items(
    payload: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    items: list[dict[str, Any]] = []
    missing_item_codes: list[str] = []
    nonconformity_codes: list[str] = []
    critical_nonconformity_codes: list[str] = []

    for field_key, title, criticality in _NR35_ANCHOR_COMPONENT_SPECS:
        text = str((payload or {}).get(field_key) or "").strip()
        verdict = _nr35_anchor_field_verdict(field_key, text)
        conflict = estimar_conflict_score_normativo(
            texto=text,
            missing_evidence_count=0 if verdict else 1,
            contradictory_markers=0,
        )
        if not verdict:
            missing_item_codes.append(field_key)
        elif verdict == "NC":
            nonconformity_codes.append(field_key)
            if criticality == "alta":
                critical_nonconformity_codes.append(field_key)

        items.append(
            {
                "item_codigo": field_key,
                "titulo": title,
                "criticidade": criticality,
                "veredito_ia_normativo": verdict or "pendente",
                "confidence_ia": "alta" if verdict else "baixa",
                "norma_refs": ["NR35 ponto de ancoragem report pack v1"],
                "rule_version": _REPORT_PACK_VERSION,
                "evidence_refs": [],
                "human_review_required": verdict in {None, "NC"},
                "missing_evidence": [] if verdict else ["status_normativo_nao_confirmado"],
                "observacoes": text[:280] if text else "",
                "conflict_score": int(conflict.get("score") or 0),
                "conflict_severity": str(conflict.get("severity") or "low"),
                "approved_for_emission": verdict in {"C", "N/A"},
                "override_reason": None,
                "override_class": None,
                "learning_disposition": (
                    "blocked_nonconformity"
                    if verdict == "NC"
                    else "eligible"
                    if verdict
                    else "blocked_missing_evidence"
                ),
                "curation_required": bool(
                    conflict.get("requires_human_review") or verdict in {None, "NC"}
                ),
            }
        )

    return items, missing_item_codes, nonconformity_codes, critical_nonconformity_codes


def _build_nr35_anchor_report_pack_draft(
    *,
    laudo: Laudo,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
    visual_attachment_by_message_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
    raw_payload = _nr35_anchor_source_payload(laudo)
    structured_candidate = _materialize_catalog_candidate_without_mutation(
        laudo=laudo,
        source_payload=raw_payload or _copy_dict_payload(getattr(laudo, "dados_formulario", None)),
    )
    image_slots = _build_image_slots_from_refs(
        image_slots=_NR35_ANCHOR_IMAGE_SLOTS,
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
    ) = _build_nr35_anchor_items(raw_payload)
    max_conflict_score = max(
        [int(item.get("conflict_score") or 0) for item in item_rows] or [0]
    )
    missing_evidence: list[dict[str, Any]] = []
    if not checklist_complete:
        missing_evidence.append(
            {
                "code": "guided_checklist_incomplete",
                "kind": "checklist",
                "message": "O checklist guiado da familia NR35 ponto de ancoragem ainda nao foi concluido.",
            }
        )
    if not structured_candidate:
        missing_evidence.append(
            {
                "code": "nr35_anchor_structured_form_missing",
                "kind": "structured_form",
                "message": "O payload estruturado do ponto de ancoragem ainda nao foi materializado para o caso.",
            }
        )
    for slot_code in unresolved_slots:
        missing_evidence.append(
            {
                "code": "nr35_anchor_image_slot_missing",
                "kind": "image_slot",
                "slot": slot_code,
                "message": f"Falta evidencia fotografica obrigatoria para {slot_code}.",
            }
        )
    for item_code in missing_item_codes:
        missing_evidence.append(
            {
                "code": "nr35_anchor_item_status_missing",
                "kind": "normative_item",
                "item_codigo": item_code,
                "message": f"Falta leitura normativa do campo {item_code}.",
            }
        )

    final_validation_mode = "mesa_required"
    return {
        "contract_name": _REPORT_PACK_CONTRACT_NAME,
        "contract_version": _REPORT_PACK_VERSION,
        "modeled": True,
        "template_key": "nr35_ponto_ancoragem",
        "template_label": nome_template_humano("nr35_ponto_ancoragem"),
        "family": _NR35_ANCHOR_FAMILY,
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
            "critical_items_complete": bool(structured_candidate) and not missing_item_codes,
            "missing_evidence": missing_evidence,
            "max_conflict_score": max_conflict_score,
            "requires_normative_curation": bool(critical_nonconformity_codes) or max_conflict_score >= 70,
            "learning_eligible": False,
            "autonomy_ready": False,
            "final_validation_mode": final_validation_mode,
        },
        "structured_data_candidate": structured_candidate,
        "telemetry": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or ""),
            "entry_mode_effective": str(getattr(laudo, "entry_mode_effective", "") or ""),
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or ""),
            "guided_evidence_gap_count": len(missing_evidence),
            "mode_switch_observed": (
                str(getattr(laudo, "entry_mode_preference", "") or "")
                != str(getattr(laudo, "entry_mode_effective", "") or "")
            ),
            "modeled_strategy": "nr35_anchor_structured_model",
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


def _build_nr13_vaso_pressao_report_pack_draft(
    *,
    laudo: Laudo,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
    visual_attachment_by_message_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
    source_payload = _copy_dict_payload(getattr(laudo, "dados_formulario", None))
    structured_candidate = _materialize_catalog_candidate_without_mutation(
        laudo=laudo,
        source_payload=source_payload,
    )
    image_slots = _build_image_slots_from_refs(
        image_slots=_NR13_VASO_PRESSAO_IMAGE_SLOTS,
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
    ) = _build_nr13_vaso_pressao_items(
        structured_candidate,
        report_pack_version=_REPORT_PACK_VERSION,
    )
    max_conflict_score = max(
        [int(item.get("conflict_score") or 0) for item in item_rows] or [0]
    )

    missing_evidence: list[dict[str, Any]] = []
    if not checklist_complete:
        missing_evidence.append(
            {
                "code": "guided_checklist_incomplete",
                "kind": "checklist",
                "message": "O checklist guiado da familia NR13 vaso de pressao ainda nao foi concluido.",
            }
        )
    if not structured_candidate:
        missing_evidence.append(
            {
                "code": "nr13_vaso_pressao_structured_form_missing",
                "kind": "structured_form",
                "message": "O payload estruturado do vaso de pressao ainda nao foi materializado para o caso.",
            }
        )
    for slot_code in unresolved_slots:
        missing_evidence.append(
            {
                "code": "nr13_vaso_pressao_image_slot_missing",
                "kind": "image_slot",
                "slot": slot_code,
                "message": f"Falta evidencia fotografica obrigatoria para {slot_code}.",
            }
        )
    for item_code in missing_item_codes:
        missing_evidence.append(
            {
                "code": "nr13_vaso_pressao_item_status_missing",
                "kind": "normative_item",
                "item_codigo": item_code,
                "message": f"Falta leitura normativa do item {item_code}.",
            }
        )

    final_validation_mode = "mesa_required"
    return {
        "contract_name": _REPORT_PACK_CONTRACT_NAME,
        "contract_version": _REPORT_PACK_VERSION,
        "modeled": True,
        "template_key": "nr13",
        "template_label": nome_template_humano("nr13"),
        "family": _NR13_VASO_PRESSAO_FAMILY,
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
            "critical_items_complete": bool(structured_candidate) and not missing_item_codes,
            "missing_evidence": missing_evidence,
            "max_conflict_score": max_conflict_score,
            "requires_normative_curation": bool(critical_nonconformity_codes) or max_conflict_score >= 70,
            "learning_eligible": False,
            "autonomy_ready": False,
            "final_validation_mode": final_validation_mode,
        },
        "structured_data_candidate": structured_candidate,
        "telemetry": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or ""),
            "entry_mode_effective": str(getattr(laudo, "entry_mode_effective", "") or ""),
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or ""),
            "guided_evidence_gap_count": len(missing_evidence),
            "mode_switch_observed": (
                str(getattr(laudo, "entry_mode_preference", "") or "")
                != str(getattr(laudo, "entry_mode_effective", "") or "")
            ),
            "modeled_strategy": "nr13_vaso_pressao_structured_model",
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


def _build_nr13_caldeira_report_pack_draft(
    *,
    laudo: Laudo,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
    visual_attachment_by_message_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
    source_payload = _copy_dict_payload(getattr(laudo, "dados_formulario", None))
    structured_candidate = _materialize_catalog_candidate_without_mutation(
        laudo=laudo,
        source_payload=source_payload,
    )
    image_slots = _build_image_slots_from_refs(
        image_slots=_NR13_CALDEIRA_IMAGE_SLOTS,
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
    ) = _build_nr13_caldeira_items(
        structured_candidate,
        report_pack_version=_REPORT_PACK_VERSION,
    )
    max_conflict_score = max(
        [int(item.get("conflict_score") or 0) for item in item_rows] or [0]
    )

    missing_evidence: list[dict[str, Any]] = []
    if not checklist_complete:
        missing_evidence.append(
            {
                "code": "guided_checklist_incomplete",
                "kind": "checklist",
                "message": "O checklist guiado da familia NR13 caldeira ainda nao foi concluido.",
            }
        )
    if not structured_candidate:
        missing_evidence.append(
            {
                "code": "nr13_caldeira_structured_form_missing",
                "kind": "structured_form",
                "message": "O payload estruturado da caldeira ainda nao foi materializado para o caso.",
            }
        )
    for slot_code in unresolved_slots:
        missing_evidence.append(
            {
                "code": "nr13_caldeira_image_slot_missing",
                "kind": "image_slot",
                "slot": slot_code,
                "message": f"Falta evidencia fotografica obrigatoria para {slot_code}.",
            }
        )
    for item_code in missing_item_codes:
        missing_evidence.append(
            {
                "code": "nr13_caldeira_item_status_missing",
                "kind": "normative_item",
                "item_codigo": item_code,
                "message": f"Falta leitura normativa do item {item_code}.",
            }
        )

    final_validation_mode = "mesa_required"
    return {
        "contract_name": _REPORT_PACK_CONTRACT_NAME,
        "contract_version": _REPORT_PACK_VERSION,
        "modeled": True,
        "template_key": "nr13",
        "template_label": nome_template_humano("nr13"),
        "family": _NR13_CALDEIRA_FAMILY,
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
            "critical_items_complete": bool(structured_candidate) and not missing_item_codes,
            "missing_evidence": missing_evidence,
            "max_conflict_score": max_conflict_score,
            "requires_normative_curation": bool(critical_nonconformity_codes) or max_conflict_score >= 70,
            "learning_eligible": False,
            "autonomy_ready": False,
            "final_validation_mode": final_validation_mode,
        },
        "structured_data_candidate": structured_candidate,
        "telemetry": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or ""),
            "entry_mode_effective": str(getattr(laudo, "entry_mode_effective", "") or ""),
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or ""),
            "guided_evidence_gap_count": len(missing_evidence),
            "mode_switch_observed": (
                str(getattr(laudo, "entry_mode_preference", "") or "")
                != str(getattr(laudo, "entry_mode_effective", "") or "")
            ),
            "modeled_strategy": "nr13_caldeira_structured_model",
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


def _build_nr35_structured_candidate(
    *,
    step_entries: dict[str, list[dict[str, Any]]],
    image_slots: list[dict[str, Any]],
    component_items: list[dict[str, Any]],
) -> dict[str, Any]:
    identificacao_texts = [item.get("text") or "" for item in step_entries.get("identificacao_laudo", [])]
    contexto_texts = [item.get("text") or "" for item in step_entries.get("contexto_vistoria", [])]
    objeto_texts = [item.get("text") or "" for item in step_entries.get("objeto_inspecao", [])]
    conclusao_texts = [item.get("text") or "" for item in step_entries.get("conclusao", [])]

    status_conclusao = _extract_nr35_conclusion_status(conclusao_texts)
    observacao_conclusao = " ".join(text for text in conclusao_texts if text).strip()[:400]
    registros_fotograficos = [
        {
            "titulo": str(slot.get("title") or slot.get("slot") or "").strip(),
            "legenda": str(slot.get("resolved_caption") or "").strip(),
            "referencia_anexo": str(slot.get("resolved_evidence_id") or "").strip(),
        }
        for slot in image_slots
        if slot.get("status") == "resolved"
    ]
    resumo = (
        f"Draft incremental {nome_template_humano('nr35_linha_vida')} com "
        f"{len([item for item in component_items if item.get('veredito_ia_normativo') != 'pendente'])} "
        "componentes normativos identificados."
    )

    return {
        "informacoes_gerais": {
            "unidade": _extract_first_match(
                identificacao_texts,
                (
                    r"(?:unidade|filial)\s*[:=-]\s*([a-z0-9 /_-]+)",
                    r"(?:local|cidade)\s*[:=-]\s*([a-z0-9 /_-]+)",
                ),
            ),
            "local": _extract_first_match(
                identificacao_texts + contexto_texts,
                (
                    r"(?:local|cidade|uf)\s*[:=-]\s*([a-z0-9 /_-]+)",
                ),
            ),
            "contratante": _extract_first_match(
                contexto_texts,
                (r"contratante\s*[:=-]\s*([a-z0-9 /_.-]+)",),
            ),
            "contratada": _extract_first_match(
                contexto_texts,
                (r"contratada\s*[:=-]\s*([a-z0-9 /_.-]+)",),
            ),
            "engenheiro_responsavel": _extract_first_match(
                contexto_texts,
                (r"engenheiro(?: responsavel)?\s*[:=-]\s*([a-z0-9 /_.-]+)",),
            ),
            "inspetor_lider": _extract_first_match(
                contexto_texts,
                (r"inspetor(?: lider)?\s*[:=-]\s*([a-z0-9 /_.-]+)",),
            ),
            "numero_laudo_fabricante": _extract_first_match(
                identificacao_texts,
                (
                    r"(?:laudo fabricante|fabricante)\s*[:=-]\s*([a-z0-9 /_.-]+)",
                    r"(?:ref(?:erencia)? fabricante)\s*[:=-]\s*([a-z0-9 /_.-]+)",
                ),
            ),
            "numero_laudo_inspecao": _extract_first_match(
                identificacao_texts,
                (
                    r"(?:laudo inspecao|numero do laudo|laudo)\s*[:=-]\s*([a-z0-9 /_.-]+)",
                ),
            ),
            "art_numero": _extract_first_match(
                contexto_texts + identificacao_texts,
                (r"\bart\s*[:=-]?\s*([a-z0-9 /_.-]+)",),
            ),
            "data_vistoria": _extract_first_match(
                contexto_texts,
                (r"(?:data|vistoria)\s*[:=-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",),
            ),
        },
        "objeto_inspecao": {
            "identificacao_linha_vida": (
                " ".join(text for text in identificacao_texts if text).strip()[:240]
            ),
            "tipo_linha_vida": (
                "Vertical"
                if any("vertical" in _normalize_text(text) for text in objeto_texts)
                else "Horizontal"
                if any("horizontal" in _normalize_text(text) for text in objeto_texts)
                else "Ponto de Ancoragem"
                if any("ancoragem" in _normalize_text(text) for text in objeto_texts)
                else "Não identificado"
            ),
            "escopo_inspecao": " ".join(text for text in objeto_texts if text).strip()[:300],
        },
        "componentes_inspecionados": {
            item["item_codigo"]: {
                "condicao": (
                    item["veredito_ia_normativo"]
                    if item["veredito_ia_normativo"] in {"C", "NC", "N/A"}
                    else "N/A"
                ),
                "observacao": str(item.get("observacoes") or "").strip(),
            }
            for item in component_items
        },
        "registros_fotograficos": registros_fotograficos,
        "conclusao": {
            "status": status_conclusao,
            "proxima_inspecao_periodica": "",
            "observacoes": observacao_conclusao,
        },
        "resumo_executivo": resumo,
    }


def _build_nr20_prontuario_report_pack_draft(
    *,
    laudo: Laudo,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
    visual_attachment_by_message_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
    source_payload = _copy_dict_payload(getattr(laudo, "dados_formulario", None))
    structured_candidate = _materialize_catalog_candidate_without_mutation(
        laudo=laudo,
        source_payload=source_payload,
    )
    image_slots = _build_image_slots_from_refs(
        image_slots=_NR20_PRONTUARIO_IMAGE_SLOTS,
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
    ) = _build_nr20_prontuario_items(
        raw_payload=source_payload,
        structured_payload=structured_candidate,
        report_pack_version=_REPORT_PACK_VERSION,
    )
    max_conflict_score = max(
        [int(item.get("conflict_score") or 0) for item in item_rows] or [0]
    )

    missing_evidence: list[dict[str, Any]] = []
    if not checklist_complete:
        missing_evidence.append(
            {
                "code": "guided_checklist_incomplete",
                "kind": "checklist",
                "message": "O checklist guiado da familia NR20 prontuario ainda nao foi concluido.",
            }
        )
    if not structured_candidate:
        missing_evidence.append(
            {
                "code": "nr20_prontuario_structured_form_missing",
                "kind": "structured_form",
                "message": "O payload estruturado do prontuario NR20 ainda nao foi materializado para o caso.",
            }
        )
    for slot_code in unresolved_slots:
        missing_evidence.append(
            {
                "code": "nr20_prontuario_image_slot_missing",
                "kind": "image_slot",
                "slot": slot_code,
                "message": f"Falta evidencia fotografica obrigatoria para {slot_code}.",
            }
        )
    for item_code in missing_item_codes:
        missing_evidence.append(
            {
                "code": "nr20_prontuario_item_status_missing",
                "kind": "normative_item",
                "item_codigo": item_code,
                "message": f"Falta leitura documental do item {item_code}.",
            }
        )

    template_key = normalizar_tipo_template(getattr(laudo, "tipo_template", "padrao"))
    final_validation_mode = "mesa_required"
    return {
        "contract_name": _REPORT_PACK_CONTRACT_NAME,
        "contract_version": _REPORT_PACK_VERSION,
        "modeled": True,
        "template_key": template_key,
        "template_label": nome_template_humano(template_key),
        "family": _NR20_PRONTUARIO_FAMILY,
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
            "critical_items_complete": bool(structured_candidate) and not missing_item_codes,
            "missing_evidence": missing_evidence,
            "max_conflict_score": max_conflict_score,
            "requires_normative_curation": bool(critical_nonconformity_codes) or max_conflict_score >= 70,
            "learning_eligible": False,
            "autonomy_ready": False,
            "final_validation_mode": final_validation_mode,
        },
        "structured_data_candidate": structured_candidate,
        "telemetry": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or ""),
            "entry_mode_effective": str(getattr(laudo, "entry_mode_effective", "") or ""),
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or ""),
            "guided_evidence_gap_count": len(missing_evidence),
            "mode_switch_observed": (
                str(getattr(laudo, "entry_mode_preference", "") or "")
                != str(getattr(laudo, "entry_mode_effective", "") or "")
            ),
            "modeled_strategy": "nr20_prontuario_structured_model",
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


def _build_nr10_prontuario_report_pack_draft(
    *,
    laudo: Laudo,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
    visual_attachment_by_message_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
    source_payload = _copy_dict_payload(getattr(laudo, "dados_formulario", None))
    structured_candidate = _materialize_catalog_candidate_without_mutation(
        laudo=laudo,
        source_payload=source_payload,
    )
    image_slots = _build_image_slots_from_refs(
        image_slots=_NR10_PRONTUARIO_IMAGE_SLOTS,
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
    ) = _build_nr10_prontuario_items(
        raw_payload=source_payload,
        structured_payload=structured_candidate,
        report_pack_version=_REPORT_PACK_VERSION,
    )
    max_conflict_score = max(
        [int(item.get("conflict_score") or 0) for item in item_rows] or [0]
    )

    missing_evidence: list[dict[str, Any]] = []
    if not checklist_complete:
        missing_evidence.append(
            {
                "code": "guided_checklist_incomplete",
                "kind": "checklist",
                "message": "O checklist guiado da familia NR10 prontuario ainda nao foi concluido.",
            }
        )
    if not structured_candidate:
        missing_evidence.append(
            {
                "code": "nr10_prontuario_structured_form_missing",
                "kind": "structured_form",
                "message": "O payload estruturado do prontuario NR10 ainda nao foi materializado para o caso.",
            }
        )
    for slot_code in unresolved_slots:
        missing_evidence.append(
            {
                "code": "nr10_prontuario_image_slot_missing",
                "kind": "image_slot",
                "slot": slot_code,
                "message": f"Falta evidencia fotografica obrigatoria para {slot_code}.",
            }
        )
    for item_code in missing_item_codes:
        missing_evidence.append(
            {
                "code": "nr10_prontuario_item_status_missing",
                "kind": "normative_item",
                "item_codigo": item_code,
                "message": f"Falta leitura documental do item {item_code}.",
            }
        )

    final_validation_mode = "mesa_required"
    return {
        "contract_name": _REPORT_PACK_CONTRACT_NAME,
        "contract_version": _REPORT_PACK_VERSION,
        "modeled": True,
        "template_key": "pie",
        "template_label": nome_template_humano("pie"),
        "family": _NR10_PRONTUARIO_FAMILY,
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
            "critical_items_complete": bool(structured_candidate) and not missing_item_codes,
            "missing_evidence": missing_evidence,
            "max_conflict_score": max_conflict_score,
            "requires_normative_curation": bool(critical_nonconformity_codes) or max_conflict_score >= 70,
            "learning_eligible": False,
            "autonomy_ready": False,
            "final_validation_mode": final_validation_mode,
        },
        "structured_data_candidate": structured_candidate,
        "telemetry": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or ""),
            "entry_mode_effective": str(getattr(laudo, "entry_mode_effective", "") or ""),
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or ""),
            "guided_evidence_gap_count": len(missing_evidence),
            "mode_switch_observed": (
                str(getattr(laudo, "entry_mode_preference", "") or "")
                != str(getattr(laudo, "entry_mode_effective", "") or "")
            ),
            "modeled_strategy": "nr10_prontuario_structured_model",
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


def _build_nr35_report_pack_draft(
    *,
    laudo: Laudo,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
    visual_attachment_by_message_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    guided_draft = _normalize_guided_draft(getattr(laudo, "guided_inspection_draft_json", None))
    checklist = list((guided_draft or {}).get("checklist") or [])
    checklist_ids = [str(item.get("id") or "").strip() for item in checklist if str(item.get("id") or "").strip()]
    completed_step_ids = set((guided_draft or {}).get("completed_step_ids") or [])
    step_entries = _step_texts_from_guided_draft(
        guided_draft=guided_draft,
        user_messages=user_messages,
    )
    image_slots = _build_image_slots_from_refs(
        image_slots=_NR35_IMAGE_SLOTS,
        guided_draft=guided_draft,
        user_messages=user_messages,
        visual_message_ids=visual_message_ids,
    )
    photo_refs = [slot for slot in image_slots if slot["status"] == "resolved"]

    component_entries = step_entries.get("componentes_inspecionados", [])
    component_items = [
        _parse_component_item(component_entries, component_key)
        for component_key, _title, _criticality in _NR35_COMPONENT_SPECS
    ]
    component_missing = [
        item["item_codigo"]
        for item in component_items
        if item.get("veredito_ia_normativo") == "pendente"
    ]
    unresolved_slots = [slot["slot"] for slot in image_slots if slot["status"] != "resolved"]
    checklist_complete = bool(checklist_ids) and set(checklist_ids).issubset(completed_step_ids)
    conclusion_status = _extract_nr35_conclusion_status(
        [item.get("text") or "" for item in step_entries.get("conclusao", [])]
    )
    entry_mode_effective = str(getattr(laudo, "entry_mode_effective", "") or "").strip()
    conflict_scores = [int(item.get("conflict_score") or 0) for item in component_items]
    max_conflict_score = max(conflict_scores or [0])
    requires_normative_curation = any(
        bool(item.get("curation_required")) for item in component_items
    )
    autonomy_ready = (
        checklist_complete
        and not component_missing
        and not unresolved_slots
        and conclusion_status in {"Aprovado", "Reprovado"}
        and max_conflict_score < 70
        and entry_mode_effective == "evidence_first"
    )
    final_validation_mode = "mobile_autonomous" if autonomy_ready else "mesa_required"
    structured_candidate = _build_nr35_structured_candidate(
        step_entries=step_entries,
        image_slots=image_slots,
        component_items=component_items,
    )
    evidence_count = sum(
        1
        for message in user_messages
        if _extract_message_text(message)
        or _looks_like_photo_message(message, visual_message_ids)
        or _looks_like_document_message(message)
    )
    missing_evidence: list[dict[str, Any]] = []
    if not checklist_complete:
        missing_evidence.append(
            {
                "code": "guided_checklist_incomplete",
                "kind": "checklist",
                "message": "O checklist guiado da familia NR35 ainda nao foi concluido.",
            }
        )
    for component_key in component_missing:
        missing_evidence.append(
            {
                "code": "nr35_component_status_missing",
                "kind": "normative_item",
                "item_codigo": component_key,
                "message": f"Falta status normativo do componente {component_key}.",
            }
        )
    for slot_code in unresolved_slots:
        missing_evidence.append(
            {
                "code": "nr35_image_slot_missing",
                "kind": "image_slot",
                "slot": slot_code,
                "message": f"Falta evidencia fotografica obrigatoria para {slot_code}.",
            }
        )
    if conclusion_status not in {"Aprovado", "Reprovado"}:
        missing_evidence.append(
            {
                "code": "nr35_conclusion_status_pending",
                "kind": "conclusion",
                "message": "A conclusao final ainda nao definiu aprovado ou reprovado.",
            }
        )

    return {
        "contract_name": _REPORT_PACK_CONTRACT_NAME,
        "contract_version": _REPORT_PACK_VERSION,
        "modeled": True,
        "template_key": "nr35_linha_vida",
        "template_label": nome_template_humano("nr35_linha_vida"),
        "family": _NR35_FAMILY,
        "pack_version": _REPORT_PACK_VERSION,
        "evidence_bundle_kind": "case_thread",
        "evidence_summary": {
            "user_message_count": len(user_messages),
            "evidence_count": evidence_count,
            "image_count": len(photo_refs),
        },
        "guided_context": {
            "checklist_ids": checklist_ids,
            "completed_step_ids": sorted(completed_step_ids),
            "has_guided_draft": bool(guided_draft),
        },
        "items": component_items,
        "image_slots": image_slots,
        "quality_gates": {
            "checklist_complete": checklist_complete,
            "required_image_slots_complete": not unresolved_slots,
            "critical_items_complete": not component_missing,
            "missing_evidence": missing_evidence,
            "max_conflict_score": max_conflict_score,
            "requires_normative_curation": requires_normative_curation,
            "learning_eligible": autonomy_ready and not requires_normative_curation,
            "autonomy_ready": autonomy_ready,
            "final_validation_mode": final_validation_mode,
        },
        "structured_data_candidate": structured_candidate,
        "telemetry": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or ""),
            "entry_mode_effective": entry_mode_effective,
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or ""),
            "guided_evidence_gap_count": len(missing_evidence),
            "mode_switch_observed": (
                str(getattr(laudo, "entry_mode_preference", "") or "")
                != str(getattr(laudo, "entry_mode_effective", "") or "")
            ),
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


def build_unmodeled_report_pack_draft(
    *,
    laudo: Laudo,
    template_key: str,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
) -> dict[str, Any]:
    return {
        "contract_name": _REPORT_PACK_CONTRACT_NAME,
        "contract_version": _REPORT_PACK_VERSION,
        "modeled": False,
        "template_key": template_key,
        "template_label": nome_template_humano(template_key),
        "family": template_key,
        "pack_version": _REPORT_PACK_VERSION,
        "evidence_bundle_kind": "case_thread",
        "evidence_summary": {
            "user_message_count": len(user_messages),
            "evidence_count": len(user_messages),
            "image_count": len(visual_message_ids),
        },
        "items": [],
        "image_slots": [],
        "quality_gates": {
            "checklist_complete": False,
            "required_image_slots_complete": False,
            "critical_items_complete": False,
            "missing_evidence": [
                {
                    "code": "report_pack_not_modeled",
                    "kind": "pack",
                    "message": "Esta familia ainda nao possui report pack incremental modelado.",
                }
            ],
            "max_conflict_score": 100,
            "requires_normative_curation": True,
            "learning_eligible": False,
            "autonomy_ready": False,
            "final_validation_mode": "mesa_required",
        },
        "structured_data_candidate": None,
        "telemetry": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or ""),
            "entry_mode_effective": str(getattr(laudo, "entry_mode_effective", "") or ""),
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or ""),
            "guided_evidence_gap_count": 1,
            "mode_switch_observed": (
                str(getattr(laudo, "entry_mode_preference", "") or "")
                != str(getattr(laudo, "entry_mode_effective", "") or "")
            ),
        },
        "analysis_basis": _build_analysis_basis(
            laudo=laudo,
            user_messages=user_messages,
            visual_message_ids=visual_message_ids,
            final_validation_mode="mesa_required",
        ),
    }


__all__ = [
    "_NR10_PRONTUARIO_FAMILY",
    "_NR13_CALDEIRA_FAMILY",
    "_NR13_VASO_PRESSAO_FAMILY",
    "_NR20_PRONTUARIO_FAMILY",
    "_build_nr10_prontuario_report_pack_draft",
    "_build_nr13_caldeira_report_pack_draft",
    "_build_nr13_vaso_pressao_report_pack_draft",
    "_build_nr35_anchor_report_pack_draft",
    "_build_nr35_report_pack_draft",
    "_build_nr20_prontuario_report_pack_draft",
    "build_unmodeled_report_pack_draft",
]
