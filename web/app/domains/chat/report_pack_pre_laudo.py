"""Pre-laudo e análise de evidências para report packs incrementais."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.paths import resolve_family_schemas_dir
from app.domains.chat.media_helpers import mensagem_representa_documento
from app.domains.chat.normalization import (
    nome_template_humano,
    normalizar_tipo_template,
    resolver_familia_padrao_template,
)
from app.shared.database import Laudo, MensagemLaudo

_PRE_LAUDO_FAMILY_CANONICAL_ALIASES = {
    "nr35_periodica_linha_vida": "nr35_inspecao_linha_de_vida",
    "nr35_linha_vida": "nr35_inspecao_linha_de_vida",
    "rti": "nr10_inspecao_instalacoes_eletricas",
    "pie": "nr10_prontuario_instalacoes_eletricas",
    "nr11_movimentacao": "nr11_inspecao_movimentacao_armazenagem",
    "nr12maquinas": "nr12_inspecao_maquina_equipamento",
    "nr13": "nr13_inspecao_caldeira",
    "nr13_ultrassom": "nr13_calculo_espessura_minima_vaso_pressao",
    "nr13_teste_hidrostatico": "nr13_teste_hidrostatico",
    "nr20_instalacoes": "nr20_inspecao_instalacoes_inflamaveis",
    "nr33_espaco_confinado": "nr33_avaliacao_espaco_confinado",
    "nr35_ponto_ancoragem": "nr35_inspecao_ponto_ancoragem",
}
_PRE_LAUDO_META_SECTION_KEYS = {
    "schema_type",
    "schema_version",
    "family_key",
    "template_code",
    "tokens",
    "case_context",
    "mesa_review",
}
_PRE_LAUDO_IGNORED_PATH_PREFIXES: tuple[str, ...] = (
    "schema_type",
    "schema_version",
    "family_key",
    "family_label",
    "template_code",
    "template_label",
    "contract_name",
    "contract_version",
    "pack_version",
    "analysis_basis",
    "document_projection",
    "document_contract",
    "document_control",
    "delivery_package",
    "tokens",
    "case_context",
    "tenant_branding",
    "mesa_review",
    "render_mode",
)


def _looks_like_photo_message(message: MensagemLaudo, visual_message_ids: set[int]) -> bool:
    content = str(getattr(message, "conteudo", "") or "").strip().lower()
    if int(getattr(message, "id", 0) or 0) in visual_message_ids:
        return True
    return content in {"[imagem]", "imagem enviada", "[foto]"}


def _looks_like_document_message(message: MensagemLaudo) -> bool:
    return mensagem_representa_documento(str(getattr(message, "conteudo", "") or ""))


def _extract_message_text(message: MensagemLaudo) -> str:
    text = str(getattr(message, "conteudo", "") or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"[imagem]", "imagem enviada", "[foto]"}:
        return ""
    if mensagem_representa_documento(text):
        return ""
    if "solicitou encerramento" in lowered:
        return ""
    return text


def _message_payload(message: MensagemLaudo) -> dict[str, Any]:
    created_at = getattr(message, "criado_em", None)
    return {
        "message_id": int(getattr(message, "id", 0) or 0),
        "created_at": created_at.isoformat() if created_at is not None else None,
        "text": _extract_message_text(message),
    }


def _truncate_text(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return ""
    if len(text) <= max(0, int(limit)):
        return text
    return f"{text[: max(0, int(limit) - 3)].rstrip()}..."


def _pick_first_nonempty_text(*values: Any, limit: int = 180) -> str:
    for value in values:
        text = _truncate_text(value, limit=limit)
        if text:
            return text
    return ""


def _filename_from_reference(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    sanitized = text.split("?", 1)[0].split("#", 1)[0].strip()
    if not sanitized:
        return ""
    return Path(sanitized).name.strip()


def _join_summary_items(values: list[str], *, max_items: int, limit: int) -> str:
    clean_values = [_truncate_text(value, limit=limit) for value in values if _truncate_text(value, limit=limit)]
    if not clean_values:
        return ""
    return " | ".join(clean_values[: max(1, int(max_items))])


def _normalize_family_key(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized:
        artifact_path = (resolve_family_schemas_dir() / f"{normalized}.json").resolve()
        if artifact_path.exists():
            return normalized
    if normalized:
        binding = resolver_familia_padrao_template(normalized)
        family_key = str(binding.get("family_key") or "").strip().lower()
        if family_key:
            return family_key
    return _PRE_LAUDO_FAMILY_CANONICAL_ALIASES.get(normalized, normalized)


@lru_cache(maxsize=128)
def _read_family_artifact_payload(family_key: str, suffix: str) -> dict[str, Any] | None:
    family_key_norm = _normalize_family_key(family_key)
    if not family_key_norm:
        return None
    path = (resolve_family_schemas_dir() / f"{family_key_norm}{suffix}").resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _family_artifact_snapshot(family_key: str) -> dict[str, bool]:
    family_key_norm = _normalize_family_key(family_key)
    return {
        "has_family_schema": _read_family_artifact_payload(family_key_norm, ".json") is not None,
        "has_template_seed": (
            _read_family_artifact_payload(family_key_norm, ".template_master_seed.json") is not None
        ),
        "has_laudo_output_seed": (
            _read_family_artifact_payload(family_key_norm, ".laudo_output_seed.json") is not None
        ),
        "has_laudo_output_exemplo": (
            _read_family_artifact_payload(family_key_norm, ".laudo_output_exemplo.json") is not None
        ),
    }


def _resolve_report_pack_family_key(*, draft: dict[str, Any], laudo: Laudo) -> str:
    return _normalize_family_key(
        draft.get("family")
        or draft.get("family_key")
        or getattr(laudo, "catalog_family_key", None)
        or getattr(laudo, "tipo_template", None)
    )


def _is_blank_candidate_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return not any(not _is_blank_candidate_value(item) for item in value)
    if isinstance(value, dict):
        return not any(not _is_blank_candidate_value(item) for item in value.values())
    return False


def _should_ignore_candidate_path(path: str) -> bool:
    normalized = str(path or "").strip(".")
    if not normalized:
        return False
    return any(
        normalized == prefix or normalized.startswith(f"{prefix}.")
        for prefix in _PRE_LAUDO_IGNORED_PATH_PREFIXES
    )


def _humanize_candidate_path(path: str) -> str:
    parts: list[str] = []
    for item in str(path or "").replace("[", ".").replace("]", "").split("."):
        token = item.strip()
        if not token or token.isdigit():
            continue
        parts.append(token.replace("_", " ").strip().capitalize())
    return " / ".join(parts) or "Campo estruturado"


def _collect_seed_field_status(
    seed_value: Any,
    candidate_value: Any,
    *,
    path: str = "",
    filled: list[str] | None = None,
    missing: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    filled_paths = filled if filled is not None else []
    missing_paths = missing if missing is not None else []
    normalized_path = str(path or "").strip(".")
    if normalized_path and _should_ignore_candidate_path(normalized_path):
        return filled_paths, missing_paths

    if isinstance(seed_value, dict):
        if not seed_value and normalized_path:
            if _is_blank_candidate_value(candidate_value):
                missing_paths.append(normalized_path)
            else:
                filled_paths.append(normalized_path)
            return filled_paths, missing_paths
        candidate_dict = candidate_value if isinstance(candidate_value, dict) else {}
        for key, child in seed_value.items():
            child_path = f"{normalized_path}.{key}" if normalized_path else str(key)
            _collect_seed_field_status(
                child,
                candidate_dict.get(key),
                path=child_path,
                filled=filled_paths,
                missing=missing_paths,
            )
        return filled_paths, missing_paths

    if isinstance(seed_value, list):
        if normalized_path:
            if _is_blank_candidate_value(candidate_value):
                missing_paths.append(normalized_path)
            else:
                filled_paths.append(normalized_path)
        return filled_paths, missing_paths

    if not normalized_path:
        return filled_paths, missing_paths
    if _is_blank_candidate_value(candidate_value):
        missing_paths.append(normalized_path)
    else:
        filled_paths.append(normalized_path)
    return filled_paths, missing_paths


def _build_document_flow_entries(family_key: str) -> list[dict[str, Any]]:
    snapshot = _family_artifact_snapshot(family_key)
    definitions = (
        ("family_schema", "Base da família", snapshot["has_family_schema"]),
        ("template_seed", "Modelo base", snapshot["has_template_seed"]),
        ("laudo_output_seed", "Documento base", snapshot["has_laudo_output_seed"]),
        ("laudo_output_exemplo", "Exemplo de documento", snapshot["has_laudo_output_exemplo"]),
    )
    entries: list[dict[str, Any]] = []
    for key, title, ready in definitions:
        entries.append(
            {
                "key": key,
                "title": title,
                "status": "ready" if ready else "pending",
                "status_label": "Pronto" if ready else "Pendente",
                "summary": (
                    f"{title} pronto no catálogo Admin-CEO."
                    if ready
                    else f"{title} ainda não foi preparado no catálogo Admin-CEO."
                ),
            }
        )
    return entries


def _normalize_slot_payload(slot: dict[str, Any], *, required: bool) -> dict[str, Any]:
    return {
        "slot_id": str(slot.get("slot_id") or "").strip(),
        "label": _truncate_text(slot.get("label"), limit=120) or "Slot de evidência",
        "required": required,
        "accepted_types": [
            str(item).strip()
            for item in list(slot.get("accepted_types") or [])
            if str(item).strip()
        ][:4],
        "binding_path": str(slot.get("binding_path") or "").strip() or None,
        "purpose": _truncate_text(slot.get("purpose"), limit=180) or None,
    }


def _normalize_checklist_group_payload(group: dict[str, Any]) -> dict[str, Any]:
    items = [
        {
            "item_id": str(item.get("item_id") or "").strip(),
            "label": _truncate_text(item.get("label"), limit=120) or "Checklist",
            "critical": bool(item.get("critical")),
        }
        for item in list(group.get("items") or [])
        if isinstance(item, dict) and str(item.get("item_id") or "").strip()
    ]
    return {
        "group_id": str(group.get("group_id") or "").strip(),
        "title": _truncate_text(group.get("title"), limit=120) or "Grupo do checklist",
        "required": bool(group.get("required")),
        "items": items[:6],
    }


def _build_pre_laudo_document_sections(
    *,
    laudo_output_seed: dict[str, Any] | None,
    structured_candidate: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(laudo_output_seed, dict):
        return []
    sections: list[dict[str, Any]] = []
    candidate = structured_candidate if isinstance(structured_candidate, dict) else {}
    for key, seed_section in laudo_output_seed.items():
        if key in _PRE_LAUDO_META_SECTION_KEYS:
            continue
        section_title = _humanize_candidate_path(key)
        candidate_section = candidate.get(key)
        filled_paths, missing_paths = _collect_seed_field_status(
            seed_section,
            candidate_section,
            path=str(key),
        )
        filled_count = len(filled_paths)
        missing_count = len(missing_paths)
        total_fields = filled_count + missing_count
        if total_fields <= 0:
            continue
        if missing_count == 0:
            status = "ready"
            summary = f"{filled_count}/{total_fields} campos preenchidos."
        elif filled_count > 0:
            status = "attention"
            summary = f"{filled_count}/{total_fields} campos preenchidos; revisão parcial."
        else:
            status = "pending"
            summary = f"0/{total_fields} campos preenchidos."
        sections.append(
            {
                "section_key": key,
                "title": section_title,
                "status": status,
                "status_label": (
                    "Pronto" if status == "ready" else "Em andamento" if status == "attention" else "Pendente"
                ),
                "summary": summary,
                "filled_field_count": filled_count,
                "missing_field_count": missing_count,
                "total_field_count": total_fields,
                "highlights": [
                    {"path": path, "label": _humanize_candidate_path(path)}
                    for path in (missing_paths[:2] or filled_paths[:2])
                ],
            }
        )
    return sections


def _build_pre_laudo_executive_sections(
    *,
    artifact_snapshot: dict[str, bool],
    evidence_policy: dict[str, Any],
    pre_laudo_summary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    minimum_evidence = dict(evidence_policy.get("minimum_evidence") or {})
    required_slots = [
        _normalize_slot_payload(item, required=True)
        for item in list(evidence_policy.get("required_slots") or [])
        if isinstance(item, dict)
    ]
    status = str((pre_laudo_summary or {}).get("status") or "needs_completion").strip()
    final_validation_mode = str((pre_laudo_summary or {}).get("final_validation_mode") or "").strip()
    return [
        {
            "key": "casca_profissional",
            "title": "Casca profissional",
            "status": (
                "ready"
                if artifact_snapshot.get("has_family_schema")
                and artifact_snapshot.get("has_template_seed")
                and artifact_snapshot.get("has_laudo_output_seed")
                else "pending"
            ),
            "summary": "Base, modelo e documento governados no catálogo Admin-CEO.",
            "bullets": [
                "Base da família pronta." if artifact_snapshot.get("has_family_schema") else "Base da família ausente.",
                "Modelo base pronto." if artifact_snapshot.get("has_template_seed") else "Modelo base ausente.",
                "Documento base pronto." if artifact_snapshot.get("has_laudo_output_seed") else "Documento base ausente.",
            ],
        },
        {
            "key": "metodologia_e_evidencias",
            "title": "Metodologia e evidências",
            "status": "ready" if required_slots else "pending",
            "summary": (
                f"Mínimo esperado: {int(minimum_evidence.get('fotos') or 0)} foto(s), "
                f"{int(minimum_evidence.get('documentos') or 0)} documento(s) e "
                f"{int(minimum_evidence.get('textos') or 0)} texto(s)."
            ),
            "bullets": [
                item["label"] for item in required_slots[:3]
            ] or ["Definir slots críticos de evidência."],
        },
        {
            "key": "conclusao_e_emissao",
            "title": "Conclusão e emissão",
            "status": "ready" if status == "ready_for_finalization" else "attention",
            "summary": (
                "Pré-laudo consistente para consolidação e emissão."
                if status == "ready_for_finalization"
                else "Ainda existem pendências antes da finalização."
            ),
            "bullets": [
                f"Validação final: {final_validation_mode or 'governada'}.",
                "Rastreabilidade obrigatória do chat ao PDF.",
                "Conclusão técnica precisa estar fechada para emissão.",
            ],
        },
    ]


def _build_pre_laudo_document(
    *,
    draft: dict[str, Any],
    laudo: Laudo,
) -> dict[str, Any]:
    pre_laudo_summary = build_pre_laudo_summary(
        obter_pre_laudo_outline_report_pack(draft)
    ) or {}
    family_key = _resolve_report_pack_family_key(draft=draft, laudo=laudo)
    family_schema = _read_family_artifact_payload(family_key, ".json") or {}
    laudo_output_seed = _read_family_artifact_payload(family_key, ".laudo_output_seed.json") or {}
    laudo_output_example = _read_family_artifact_payload(family_key, ".laudo_output_exemplo.json") or {}
    evidence_policy = dict(family_schema.get("evidence_policy") or {})
    structured_candidate = (
        dict(draft.get("structured_data_candidate") or {})
        if isinstance(draft.get("structured_data_candidate"), dict)
        else None
    )
    document_sections = _build_pre_laudo_document_sections(
        laudo_output_seed=laudo_output_seed,
        structured_candidate=structured_candidate,
    )
    artifact_snapshot = _family_artifact_snapshot(family_key)
    highlighted_sections = [
        item for item in document_sections if item.get("status") != "ready"
    ][:4]
    return {
        "contract_name": "MobilePreLaudoDocumentV1",
        "contract_version": "v1",
        "family_key": family_key or None,
        "family_label": _truncate_text(
            family_schema.get("nome_exibicao")
            or getattr(laudo, "catalog_family_label", None)
            or draft.get("template_label"),
            limit=120,
        )
        or None,
        "template_key": str(draft.get("template_key") or "").strip() or None,
        "template_label": _truncate_text(draft.get("template_label"), limit=120) or None,
        "artifact_snapshot": artifact_snapshot,
        "document_flow": _build_document_flow_entries(family_key),
        "minimum_evidence": {
            "fotos": int((evidence_policy.get("minimum_evidence") or {}).get("fotos") or 0),
            "documentos": int((evidence_policy.get("minimum_evidence") or {}).get("documentos") or 0),
            "textos": int((evidence_policy.get("minimum_evidence") or {}).get("textos") or 0),
        },
        "required_slots": [
            _normalize_slot_payload(item, required=True)
            for item in list(evidence_policy.get("required_slots") or [])
            if isinstance(item, dict)
        ][:6],
        "optional_slots": [
            _normalize_slot_payload(item, required=False)
            for item in list(evidence_policy.get("optional_slots") or [])
            if isinstance(item, dict)
        ][:5],
        "checklist_groups": [
            _normalize_checklist_group_payload(item)
            for item in list(evidence_policy.get("checklist_groups") or [])
            if isinstance(item, dict)
        ][:5],
        "review_required": [
            _truncate_text(item, limit=160)
            for item in list(evidence_policy.get("review_required") or [])[:4]
            if _truncate_text(item, limit=160)
        ],
        "executive_sections": _build_pre_laudo_executive_sections(
            artifact_snapshot=artifact_snapshot,
            evidence_policy=evidence_policy,
            pre_laudo_summary=pre_laudo_summary,
        ),
        "document_sections": document_sections,
        "highlighted_sections": highlighted_sections,
        "next_questions": list(pre_laudo_summary.get("next_questions") or [])[:3],
        "analysis_basis_summary": {
            "coverage_summary": _truncate_text(
                (draft.get("analysis_basis") or {}).get("coverage_summary"),
                limit=220,
            )
            or None,
            "photo_summary": _truncate_text(
                (draft.get("analysis_basis") or {}).get("photo_summary"),
                limit=220,
            )
            or None,
            "document_summary": _truncate_text(
                (draft.get("analysis_basis") or {}).get("document_summary"),
                limit=220,
            )
            or None,
            "context_summary": _truncate_text(
                (draft.get("analysis_basis") or {}).get("context_summary"),
                limit=220,
            )
            or None,
        },
        "example_available": bool(laudo_output_example),
    }


def _build_analysis_basis(
    *,
    laudo: Laudo,
    user_messages: list[MensagemLaudo],
    visual_message_ids: set[int],
    visual_attachment_by_message_id: dict[int, dict[str, Any]] | None = None,
    image_slots: list[dict[str, Any]] | None = None,
    final_validation_mode: str | None = None,
) -> dict[str, Any]:
    slot_by_message_id: dict[int, dict[str, Any]] = {}
    for slot in list(image_slots or []):
        if not isinstance(slot, dict):
            continue
        message_id = int(slot.get("resolved_message_id") or 0)
        if message_id <= 0:
            continue
        slot_by_message_id[message_id] = slot

    photo_evidence: list[dict[str, Any]] = []
    document_evidence: list[dict[str, Any]] = []
    context_messages: list[dict[str, Any]] = []

    for message in user_messages:
        message_id = int(getattr(message, "id", 0) or 0)
        message_created_at = getattr(message, "criado_em", None)
        created_at = (
            message_created_at.isoformat()
            if message_created_at is not None
            else None
        )
        if _looks_like_photo_message(message, visual_message_ids):
            slot = slot_by_message_id.get(message_id) or {}
            attachment = (
                visual_attachment_by_message_id.get(message_id)
                if isinstance(visual_attachment_by_message_id, dict)
                else {}
            ) or {}
            original_name = _pick_first_nonempty_text(
                attachment.get("imagem_nome_original"),
                _filename_from_reference(attachment.get("caminho_arquivo")),
                _filename_from_reference(attachment.get("imagem_url")),
                limit=160,
            )
            reference = _pick_first_nonempty_text(
                attachment.get("reference"),
                original_name,
                f"msg:{message_id}" if message_id > 0 else None,
                limit=180,
            )
            label = _truncate_text(
                slot.get("title")
                or slot.get("resolved_caption")
                or original_name
                or f"Registro fotografico {len(photo_evidence) + 1}",
                limit=80,
            )
            caption = _truncate_text(
                slot.get("resolved_caption")
                or original_name
                or slot.get("title")
                or label,
                limit=140,
            )
            photo_evidence.append(
                {
                    "message_id": message_id,
                    "created_at": created_at,
                    "reference": reference or (f"msg:{message_id}" if message_id > 0 else None),
                    "label": label or f"Registro fotografico {len(photo_evidence) + 1}",
                    "caption": caption or None,
                    "slot": str(slot.get("slot") or "").strip() or None,
                    "original_name": original_name or None,
                    "image_url": _pick_first_nonempty_text(attachment.get("imagem_url"), limit=240) or None,
                }
            )
            continue

        if _looks_like_document_message(message):
            summary = _truncate_text(getattr(message, "conteudo", None), limit=180)
            document_evidence.append(
                {
                    "message_id": message_id,
                    "created_at": created_at,
                    "reference": f"msg:{message_id}" if message_id > 0 else None,
                    "summary": summary or None,
                }
            )
            continue

        text = _truncate_text(_extract_message_text(message), limit=220)
        if not text:
            continue
        context_messages.append(
            {
                "message_id": message_id,
                "created_at": created_at,
                "text": text,
            }
        )

    context_summary = _join_summary_items(
        [str(item.get("text") or "") for item in context_messages],
        max_items=3,
        limit=120,
    )
    photo_summary = "; ".join(
        part
        for part in [
            _truncate_text(
                (
                    f"{item.get('label')}: {item.get('caption')}"
                    if item.get("label") and item.get("caption")
                    else item.get("label")
                    or item.get("caption")
                ),
                limit=120,
            )
            for item in photo_evidence[:3]
        ]
        if part
    )
    document_summary = "; ".join(
        _truncate_text(item.get("summary"), limit=120)
        for item in document_evidence[:2]
        if _truncate_text(item.get("summary"), limit=120)
    )
    opening_context = _truncate_text(getattr(laudo, "primeira_mensagem", None), limit=220) or None
    ai_summary = _truncate_text(getattr(laudo, "parecer_ia", None), limit=220) or None

    summary_parts: list[str] = [
        f"{len(photo_evidence)} foto(s)" if photo_evidence else "",
        f"{len(context_messages)} mensagem(ns) de contexto" if context_messages else "",
        f"{len(document_evidence)} documento(s) complementar(es)" if document_evidence else "",
    ]
    coverage_summary = ", ".join(part for part in summary_parts if part) or "Sem base de evidencia consolidada."
    if opening_context:
        coverage_summary = f"{coverage_summary} Contexto inicial: {opening_context}"
    elif context_summary:
        coverage_summary = f"{coverage_summary} Contexto resumido: {context_summary}"

    source_message_ids = [
        message_id
        for message_id in [
            *[int(item.get("message_id") or 0) for item in context_messages],
            *[int(item.get("message_id") or 0) for item in photo_evidence],
            *[int(item.get("message_id") or 0) for item in document_evidence],
        ]
        if message_id > 0
    ]

    return {
        "coverage_summary": coverage_summary,
        "opening_context": opening_context,
        "context_summary": context_summary or None,
        "photo_summary": photo_summary or None,
        "document_summary": document_summary or None,
        "ai_draft_excerpt": ai_summary,
        "photo_evidence": photo_evidence,
        "document_evidence": document_evidence,
        "context_messages": context_messages[:5],
        "source_message_ids": source_message_ids,
        "workflow_signals": {
            "entry_mode_preference": str(getattr(laudo, "entry_mode_preference", "") or "").strip() or None,
            "entry_mode_effective": str(getattr(laudo, "entry_mode_effective", "") or "").strip() or None,
            "entry_mode_reason": str(getattr(laudo, "entry_mode_reason", "") or "").strip() or None,
            "final_validation_mode": str(final_validation_mode or "").strip() or None,
        },
    }


def _collect_candidate_field_status(
    value: Any,
    *,
    path: str = "",
    filled: list[str] | None = None,
    missing: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    filled_paths = filled if filled is not None else []
    missing_paths = missing if missing is not None else []
    normalized_path = str(path or "").strip(".")
    if normalized_path and _should_ignore_candidate_path(normalized_path):
        return filled_paths, missing_paths

    if isinstance(value, dict):
        if not value and normalized_path:
            missing_paths.append(normalized_path)
            return filled_paths, missing_paths
        for key, child in value.items():
            child_path = f"{normalized_path}.{key}" if normalized_path else str(key)
            _collect_candidate_field_status(
                child,
                path=child_path,
                filled=filled_paths,
                missing=missing_paths,
            )
        return filled_paths, missing_paths

    if isinstance(value, list):
        if normalized_path:
            if _is_blank_candidate_value(value):
                missing_paths.append(normalized_path)
            else:
                filled_paths.append(normalized_path)
        return filled_paths, missing_paths

    if not normalized_path:
        return filled_paths, missing_paths
    if _is_blank_candidate_value(value):
        missing_paths.append(normalized_path)
    else:
        filled_paths.append(normalized_path)
    return filled_paths, missing_paths


def _build_pre_laudo_questions(
    *,
    quality_gates: dict[str, Any],
    missing_paths: list[str],
) -> list[str]:
    prompts: list[str] = []
    seen: set[str] = set()

    def _push(text: str) -> None:
        prompt = _truncate_text(text, limit=220)
        if not prompt:
            return
        key = prompt.casefold()
        if key in seen:
            return
        seen.add(key)
        prompts.append(prompt)

    for item in list(quality_gates.get("missing_evidence") or []):
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        slot = str(item.get("slot") or "").strip()
        item_code = str(item.get("item_codigo") or "").strip()
        message = str(item.get("message") or "").strip()
        if kind == "image_slot" and slot:
            _push(f"Envie a foto obrigatória de {slot.replace('_', ' ')}.")
            continue
        if kind == "normative_item" and item_code:
            _push(f"Qual é o status normativo de {item_code.replace('_', ' ')}: C, NC ou N/A?")
            continue
        if kind == "conclusion":
            _push("Qual é a conclusão final do caso: aprovado, reprovado ou pendente?")
            continue
        if kind == "checklist":
            _push("Conclua a etapa guiada pendente antes de seguir para o laudo final.")
            continue
        if kind == "structured_form":
            _push("Complete os campos estruturados mínimos do template antes da finalização.")
            continue
        if kind == "document":
            _push("Anexe o documento controlado exigido para sustentar o laudo.")
            continue
        if message:
            _push(message)

    for path in missing_paths[:3]:
        _push(f"Preencha o campo {_humanize_candidate_path(path).lower()}.")

    return prompts[:5]


def _build_pre_laudo_outline(draft: dict[str, Any]) -> dict[str, Any]:
    structured_candidate = draft.get("structured_data_candidate")
    quality_gates = dict(draft.get("quality_gates") or {})
    analysis_basis = dict(draft.get("analysis_basis") or {})
    filled_paths: list[str] = []
    missing_paths: list[str] = []
    if isinstance(structured_candidate, dict):
        filled_paths, missing_paths = _collect_candidate_field_status(structured_candidate)

    final_validation_mode = str(quality_gates.get("final_validation_mode") or "").strip() or "mesa_required"
    missing_evidence = list(quality_gates.get("missing_evidence") or [])
    if not isinstance(structured_candidate, dict):
        status = "awaiting_structured_candidate"
    elif not missing_evidence:
        status = "ready_for_finalization"
    elif missing_paths or missing_evidence:
        status = "needs_completion"
    else:
        status = "ready_for_finalization"

    return {
        "status": status,
        "analysis_summary": _truncate_text(
            analysis_basis.get("coverage_summary") or analysis_basis.get("context_summary"),
            limit=220,
        )
        or None,
        "ready_for_structured_form": isinstance(structured_candidate, dict),
        "ready_for_finalization": status == "ready_for_finalization",
        "final_validation_mode": final_validation_mode,
        "filled_field_count": len(filled_paths),
        "missing_field_count": len(missing_paths),
        "filled_highlights": [
            {"path": path, "label": _humanize_candidate_path(path)}
            for path in filled_paths[:6]
        ],
        "missing_highlights": [
            {"path": path, "label": _humanize_candidate_path(path)}
            for path in missing_paths[:6]
        ],
        "next_questions": _build_pre_laudo_questions(
            quality_gates=quality_gates,
            missing_paths=missing_paths,
        ),
    }


def _attach_pre_laudo_views(
    *,
    draft: dict[str, Any] | None,
    laudo: Laudo,
) -> dict[str, Any] | None:
    if not isinstance(draft, dict):
        return draft
    draft["pre_laudo_outline"] = _build_pre_laudo_outline(draft)
    draft["pre_laudo_document"] = _build_pre_laudo_document(
        draft=draft,
        laudo=laudo,
    )
    return draft


def obter_pre_laudo_outline_report_pack(
    report_pack_draft: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(report_pack_draft, dict):
        return None
    outline = report_pack_draft.get("pre_laudo_outline")
    return dict(outline) if isinstance(outline, dict) else None


def build_pre_laudo_summary(
    pre_laudo_outline: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(pre_laudo_outline, dict):
        return None
    return {
        "status": str(pre_laudo_outline.get("status") or "").strip() or "needs_completion",
        "analysis_summary": _truncate_text(pre_laudo_outline.get("analysis_summary"), limit=220) or None,
        "ready_for_structured_form": bool(pre_laudo_outline.get("ready_for_structured_form")),
        "ready_for_finalization": bool(pre_laudo_outline.get("ready_for_finalization")),
        "final_validation_mode": str(pre_laudo_outline.get("final_validation_mode") or "").strip() or None,
        "filled_field_count": int(pre_laudo_outline.get("filled_field_count") or 0),
        "missing_field_count": int(pre_laudo_outline.get("missing_field_count") or 0),
        "missing_highlights": [
            {
                "path": str(item.get("path") or "").strip(),
                "label": _truncate_text(item.get("label"), limit=120) or None,
            }
            for item in list(pre_laudo_outline.get("missing_highlights") or [])[:3]
            if isinstance(item, dict) and str(item.get("path") or "").strip()
        ],
        "next_questions": [
            _truncate_text(item, limit=220)
            for item in list(pre_laudo_outline.get("next_questions") or [])[:3]
            if _truncate_text(item, limit=220)
        ],
    }


def _read_context_value(raw_context: Any, field_name: str) -> Any:
    if isinstance(raw_context, dict):
        return raw_context.get(field_name)
    return getattr(raw_context, field_name, None)


def build_pre_laudo_prompt_context(
    pre_laudo_summary: dict[str, Any] | None,
    *,
    template_key: str | None = None,
    guided_context: Any = None,
    analysis_basis: dict[str, Any] | None = None,
) -> str:
    if not isinstance(pre_laudo_summary, dict):
        return ""

    status = str(pre_laudo_summary.get("status") or "").strip() or "needs_completion"
    ready_for_finalization = bool(pre_laudo_summary.get("ready_for_finalization"))
    final_validation_mode = (
        str(pre_laudo_summary.get("final_validation_mode") or "").strip() or None
    )
    analysis_summary = _truncate_text(
        pre_laudo_summary.get("analysis_summary"),
        limit=220,
    )
    missing_field_count = int(pre_laudo_summary.get("missing_field_count") or 0)
    filled_field_count = int(pre_laudo_summary.get("filled_field_count") or 0)
    missing_labels = [
        _truncate_text(item.get("label"), limit=120)
        for item in list(pre_laudo_summary.get("missing_highlights") or [])[:3]
        if isinstance(item, dict) and _truncate_text(item.get("label"), limit=120)
    ]
    next_questions = [
        _truncate_text(item, limit=220)
        for item in list(pre_laudo_summary.get("next_questions") or [])[:3]
        if _truncate_text(item, limit=220)
    ]
    analysis_basis_dict = dict(analysis_basis or {}) if isinstance(analysis_basis, dict) else {}
    photo_summary = _truncate_text(analysis_basis_dict.get("photo_summary"), limit=220)
    document_summary = _truncate_text(
        analysis_basis_dict.get("document_summary"),
        limit=220,
    )
    context_summary = _truncate_text(
        analysis_basis_dict.get("context_summary"),
        limit=220,
    )

    template_key_normalized = normalizar_tipo_template(template_key or "")
    template_label = (
        nome_template_humano(template_key_normalized)
        if template_key_normalized
        else ""
    )
    step_id = str(_read_context_value(guided_context, "step_id") or "").strip()
    step_title = str(_read_context_value(guided_context, "step_title") or "").strip()
    attachment_kind = (
        str(_read_context_value(guided_context, "attachment_kind") or "").strip().lower()
    )

    status_label = {
        "awaiting_structured_candidate": "base reunida, mas ainda sem candidato estruturado",
        "needs_completion": "coleta em andamento com pendencias para fechar o pre-laudo",
        "ready_for_finalization": "pre-laudo consistente para consolidacao/finalizacao",
    }.get(status, status.replace("_", " "))
    attachment_label = {
        "none": "sem anexo novo",
        "image": "imagem/foto",
        "document": "documento",
        "mixed": "imagem e documento",
    }.get(attachment_kind, attachment_kind or None)

    lines = [
        "[pre_laudo_operacional]",
        (
            "Use este estado interno para conduzir o preenchimento do pre-laudo. "
            "Nao invente campos ausentes e nao declare o caso pronto para PDF "
            "enquanto ready_for_finalization for falso."
        ),
        f"- Status interno: {status}",
        f"- Leitura operacional: {status_label}",
        f"- Ready for finalization: {'true' if ready_for_finalization else 'false'}",
    ]
    if template_label:
        lines.append(f"- Template em curso: {template_label}")
    if final_validation_mode:
        lines.append(f"- Modo de validacao final: {final_validation_mode}")
    if step_title:
        step_line = f"- Etapa guiada atual: {step_title}"
        if step_id:
            step_line = f"{step_line} ({step_id})"
        lines.append(step_line)
    if attachment_label:
        lines.append(f"- Evidencia recebida nesta etapa: {attachment_label}")
    if analysis_summary:
        lines.append(f"- Resumo atual da base: {analysis_summary}")
    if photo_summary:
        lines.append(f"- Fotos ja vinculadas: {photo_summary}")
    if document_summary:
        lines.append(f"- Documento complementar: {document_summary}")
    if context_summary and context_summary != analysis_summary:
        lines.append(f"- Contexto textual resumido: {context_summary}")
    lines.append(f"- Campos preenchidos: {filled_field_count}")
    lines.append(f"- Campos faltantes: {missing_field_count}")
    if missing_labels:
        lines.append(f"- Pendencias prioritarias: {'; '.join(missing_labels)}")
    if next_questions:
        lines.append("- Perguntas seguintes sugeridas:")
        for index, question in enumerate(next_questions, start=1):
            lines.append(f"  {index}. {question}")
    elif ready_for_finalization:
        lines.append(
            "- Proxima acao sugerida: consolidar o caso e confirmar se o usuario deseja finalizar."
        )
    else:
        lines.append(
            "- Proxima acao sugerida: faca 1 ou 2 perguntas objetivas cobrindo primeiro a maior lacuna."
        )
    lines.append("[/pre_laudo_operacional]")
    return "\n".join(lines)


__all__ = [
    "_attach_pre_laudo_views",
    "_build_analysis_basis",
    "_extract_message_text",
    "_filename_from_reference",
    "_looks_like_document_message",
    "_looks_like_photo_message",
    "_message_payload",
    "_pick_first_nonempty_text",
    "_truncate_text",
    "build_pre_laudo_prompt_context",
    "build_pre_laudo_summary",
    "obter_pre_laudo_outline_report_pack",
]
