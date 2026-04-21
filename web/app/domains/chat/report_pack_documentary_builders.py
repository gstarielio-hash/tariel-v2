"""Builders documentais usados pelos report packs semanticos."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from nucleo.inspetor.confianca_ia import estimar_conflict_score_normativo

_NR13_CALDEIRA_COMPONENT_SPECS = (
    ("placa_identificacao", "Placa de identificacao", "media"),
    ("prontuario", "Prontuario vinculado", "alta"),
    ("painel_e_comandos", "Painel e comandos", "alta"),
    ("dispositivos_de_seguranca", "Dispositivos de seguranca", "alta"),
    ("indicador_nivel", "Indicador de nivel", "media"),
    ("pontos_de_vazamento_ou_fuligem", "Vazamento ou fuligem", "alta"),
    ("isolamento_termico", "Isolamento termico", "media"),
)
_NR13_VASO_PRESSAO_COMPONENT_SPECS = (
    ("placa_identificacao", "Placa de identificacao", "media"),
    ("prontuario", "Prontuario vinculado", "alta"),
    ("dispositivos_de_seguranca", "Dispositivos de seguranca", "alta"),
    ("manometro", "Manometro", "media"),
    ("pontos_de_corrosao", "Pontos de corrosao", "alta"),
    ("vazamentos", "Vazamentos aparentes", "alta"),
)
_NR20_PRONTUARIO_COMPONENT_SPECS = (
    ("referencia_principal", "Referencia principal", "alta"),
    ("prontuario_nr20", "Prontuario NR20", "alta"),
    ("inventario_instalacoes", "Inventario de instalacoes", "alta"),
    ("analise_riscos", "Analise de riscos", "alta"),
    ("plano_resposta_emergencia", "Plano de resposta a emergencia", "media"),
    ("matriz_treinamentos", "Matriz de treinamentos", "media"),
)
_NR10_PRONTUARIO_COMPONENT_SPECS = (
    ("referencia_principal", "Referencia principal", "alta"),
    ("prontuario", "Prontuario eletrico", "alta"),
    ("diagrama_unifilar", "Diagrama unifilar", "alta"),
    ("inventario_instalacoes", "Inventario de instalacoes", "alta"),
    ("pie", "PIE", "alta"),
    ("art_numero", "ART", "media"),
)


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", normalized)


def _extract_nested_text(payload: dict[str, Any] | None, *path: str) -> str:
    current: Any = payload or {}
    for segment in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(segment)
    if isinstance(current, dict):
        for candidate_key in (
            "descricao",
            "referencias_texto",
            "observacao",
            "texto",
            "status",
            "conclusao_tecnica",
        ):
            text = str(current.get(candidate_key) or "").strip()
            if text:
                return text
        return ""
    return str(current or "").strip()


def _pick_text_from_payloads(
    *,
    raw_payload: dict[str, Any] | None,
    structured_payload: dict[str, Any] | None,
    raw_keys: tuple[str, ...] = (),
    structured_paths: tuple[tuple[str, ...], ...] = (),
) -> str:
    for key in raw_keys:
        text = str((raw_payload or {}).get(key) or "").strip()
        if text:
            return text
    for path in structured_paths:
        text = _extract_nested_text(structured_payload, *path)
        if text:
            return text
    return ""


def _documentary_field_verdict(text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    negative_patterns = (
        r"\bnao apresentad",
        r"\bausent",
        r"\bindisponivel\b",
        r"\bpendente\b",
        r"\bfalta anexar\b",
        r"\bnao localizado\b",
        r"\brevisao pendente\b",
    )
    if any(re.search(pattern, normalized) for pattern in negative_patterns):
        return "NC"
    return "C"


def _nr13_vaso_pressao_item_text(payload: dict[str, Any] | None, field_key: str) -> str:
    field_paths: dict[str, tuple[tuple[str, ...], ...]] = {
        "placa_identificacao": (
            ("identificacao", "placa_identificacao"),
            ("identificacao", "placa_identificacao", "descricao"),
        ),
        "prontuario": (
            ("documentacao_e_registros", "prontuario"),
            ("documentacao_e_registros", "registros_disponiveis_no_local"),
        ),
        "dispositivos_de_seguranca": (
            ("dispositivos_e_acessorios", "dispositivos_de_seguranca"),
            ("dispositivos_e_acessorios", "leitura_dos_dispositivos_de_seguranca"),
        ),
        "manometro": (("dispositivos_e_acessorios", "manometro"),),
        "pontos_de_corrosao": (("inspecao_visual", "pontos_de_corrosao"),),
        "vazamentos": (("inspecao_visual", "vazamentos"),),
    }
    for path in field_paths.get(field_key, ()):
        text = _extract_nested_text(payload, *path)
        if text:
            return text
    return ""


def _nr13_vaso_pressao_field_verdict(field_key: str, text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    positive_absence_patterns = (
        r"\bsem vazamento\b",
        r"\bnao observad",
        r"\bnao apresentado\b",
        r"\bnao aplicavel\b",
        r"\blegivel\b",
        r"\bacessivel\b",
        r"\badequad",
        r"\binstalad",
        r"\bpresente\b",
    )
    negative_patterns = {
        "placa_identificacao": (
            r"\bnao apresentad",
            r"\bausent",
            r"\bilegivel\b",
        ),
        "prontuario": (
            r"\bnao apresentad",
            r"\bausent",
            r"\bindisponivel\b",
        ),
        "dispositivos_de_seguranca": (
            r"\bfalha\b",
            r"\binoperante\b",
            r"\bausent",
            r"\bsem acessibilidade\b",
            r"\bnao instalado\b",
        ),
        "manometro": (
            r"\bfalha\b",
            r"\binoperante\b",
            r"\bausent",
            r"\bnao legivel\b",
        ),
        "pontos_de_corrosao": (
            r"\bcorros",
            r"\boxid",
            r"\bdesgaste\b",
        ),
        "vazamentos": (
            r"\bvazamento\b",
            r"\bvazand",
            r"\bperda de fluido\b",
        ),
    }

    if field_key == "pontos_de_corrosao":
        if re.search(r"\bsem corros", normalized) or re.search(r"\bnao observad", normalized):
            return "C"
    if field_key == "vazamentos":
        if any(re.search(pattern, normalized) for pattern in positive_absence_patterns):
            return "C"
    if any(re.search(pattern, normalized) for pattern in negative_patterns.get(field_key, ())):
        return "NC"
    return "C"


def _build_nr13_vaso_pressao_items(
    structured_payload: dict[str, Any] | None,
    *,
    report_pack_version: str,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    items: list[dict[str, Any]] = []
    missing_item_codes: list[str] = []
    nonconformity_codes: list[str] = []
    critical_nonconformity_codes: list[str] = []

    for field_key, title, criticality in _NR13_VASO_PRESSAO_COMPONENT_SPECS:
        text = _nr13_vaso_pressao_item_text(structured_payload, field_key)
        verdict = _nr13_vaso_pressao_field_verdict(field_key, text)
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
                "norma_refs": ["NR13 vaso de pressao report pack v1"],
                "rule_version": report_pack_version,
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


def _nr13_caldeira_item_text(payload: dict[str, Any] | None, field_key: str) -> str:
    field_paths: dict[str, tuple[tuple[str, ...], ...]] = {
        "placa_identificacao": (
            ("identificacao", "placa_identificacao"),
            ("identificacao", "placa_identificacao", "descricao"),
        ),
        "prontuario": (
            ("documentacao_e_registros", "prontuario"),
            ("documentacao_e_registros", "registros_disponiveis_no_local"),
        ),
        "painel_e_comandos": (
            ("dispositivos_e_controles", "painel_e_comandos"),
            ("dispositivos_e_controles", "leitura_dos_comandos_e_indicadores"),
        ),
        "dispositivos_de_seguranca": (
            ("dispositivos_e_controles", "dispositivos_de_seguranca"),
            ("dispositivos_e_controles", "leitura_dos_dispositivos_de_seguranca"),
        ),
        "indicador_nivel": (("dispositivos_e_controles", "indicador_nivel"),),
        "pontos_de_vazamento_ou_fuligem": (("inspecao_visual", "pontos_de_vazamento_ou_fuligem"),),
        "isolamento_termico": (("inspecao_visual", "isolamento_termico"),),
    }
    for path in field_paths.get(field_key, ()):
        text = _extract_nested_text(payload, *path)
        if text:
            return text
    return ""


def _nr13_caldeira_field_verdict(field_key: str, text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    positive_absence_patterns = (
        r"\bsem vazamento\b",
        r"\bsem fuligem\b",
        r"\bsem evidencia\b",
        r"\bsem improvisacao\b",
        r"\bsem dano estrutural\b",
        r"\bsem desalinhamento\b",
        r"\bintegridade aparente preservada\b",
        r"\bdisponivel\b",
        r"\blegivel\b",
        r"\bacessivel\b",
    )
    negative_patterns = {
        "placa_identificacao": (
            r"\bnao apresentad",
            r"\bausent",
            r"\bilegivel\b",
        ),
        "prontuario": (
            r"\bnao apresentad",
            r"\bausent",
            r"\bindisponivel\b",
        ),
        "painel_e_comandos": (
            r"\bfalha\b",
            r"\binoperante\b",
            r"\bimprovis",
            r"\bausent",
        ),
        "dispositivos_de_seguranca": (
            r"\bfalha\b",
            r"\binoperante\b",
            r"\bimprovis",
            r"\bausent",
            r"\bsem acessibilidade\b",
        ),
        "indicador_nivel": (
            r"\bfalha\b",
            r"\binoperante\b",
            r"\bausent",
            r"\bnao legivel\b",
        ),
        "pontos_de_vazamento_ou_fuligem": (
            r"\bfuligem\b",
            r"\bvazamento\b",
            r"\bmarcas leves\b",
            r"\bmarcas de\b",
        ),
        "isolamento_termico": (
            r"\bdesgaste\b",
            r"\bdanific",
            r"\bavariad",
            r"\brompid",
            r"\bdegrad",
        ),
    }

    if any(re.search(pattern, normalized) for pattern in positive_absence_patterns):
        if field_key in {"pontos_de_vazamento_ou_fuligem", "isolamento_termico"}:
            return "C"
    if any(re.search(pattern, normalized) for pattern in negative_patterns.get(field_key, ())):
        return "NC"
    return "C"


def _build_nr13_caldeira_items(
    structured_payload: dict[str, Any] | None,
    *,
    report_pack_version: str,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    items: list[dict[str, Any]] = []
    missing_item_codes: list[str] = []
    nonconformity_codes: list[str] = []
    critical_nonconformity_codes: list[str] = []

    for field_key, title, criticality in _NR13_CALDEIRA_COMPONENT_SPECS:
        text = _nr13_caldeira_item_text(structured_payload, field_key)
        verdict = _nr13_caldeira_field_verdict(field_key, text)
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
                "norma_refs": ["NR13 caldeira report pack v1"],
                "rule_version": report_pack_version,
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


def _nr20_prontuario_item_text(
    *,
    raw_payload: dict[str, Any] | None,
    structured_payload: dict[str, Any] | None,
    field_key: str,
) -> str:
    field_mappings: dict[str, dict[str, Any]] = {
        "referencia_principal": {
            "raw_keys": ("referencia_principal", "evidencia_principal"),
            "structured_paths": (
                ("identificacao", "referencia_principal"),
                ("evidencias_e_anexos", "evidencia_principal"),
            ),
        },
        "prontuario_nr20": {
            "raw_keys": ("prontuario_nr20", "documento_base"),
            "structured_paths": (
                ("evidencias_e_anexos", "documento_base"),
                ("documentacao_e_registros", "documentos_disponiveis"),
            ),
        },
        "inventario_instalacoes": {
            "raw_keys": ("inventario_instalacoes",),
            "structured_paths": (
                ("execucao_servico", "parametros_relevantes"),
                ("documentacao_e_registros", "documentos_disponiveis"),
            ),
        },
        "analise_riscos": {
            "raw_keys": ("analise_riscos", "analise_risco", "estudo_risco"),
            "structured_paths": (
                ("execucao_servico", "parametros_relevantes"),
                ("documentacao_e_registros", "documentos_disponiveis"),
            ),
        },
        "plano_resposta_emergencia": {
            "raw_keys": ("plano_resposta_emergencia", "plano_emergencia"),
            "structured_paths": (
                ("execucao_servico", "parametros_relevantes"),
                ("documentacao_e_registros", "documentos_disponiveis"),
            ),
        },
        "matriz_treinamentos": {
            "raw_keys": ("matriz_treinamentos", "treinamentos"),
            "structured_paths": (
                ("execucao_servico", "parametros_relevantes"),
                ("documentacao_e_registros", "documentos_disponiveis"),
            ),
        },
    }
    mapping = field_mappings.get(field_key, {})
    return _pick_text_from_payloads(
        raw_payload=raw_payload,
        structured_payload=structured_payload,
        raw_keys=tuple(mapping.get("raw_keys") or ()),
        structured_paths=tuple(mapping.get("structured_paths") or ()),
    )


def _build_nr20_prontuario_items(
    *,
    raw_payload: dict[str, Any] | None,
    structured_payload: dict[str, Any] | None,
    report_pack_version: str,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    items: list[dict[str, Any]] = []
    missing_item_codes: list[str] = []
    nonconformity_codes: list[str] = []
    critical_nonconformity_codes: list[str] = []

    for field_key, title, criticality in _NR20_PRONTUARIO_COMPONENT_SPECS:
        text = _nr20_prontuario_item_text(
            raw_payload=raw_payload,
            structured_payload=structured_payload,
            field_key=field_key,
        )
        verdict = _documentary_field_verdict(text)
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
                "norma_refs": ["NR20 prontuario report pack v1"],
                "rule_version": report_pack_version,
                "evidence_refs": [],
                "human_review_required": verdict in {None, "NC"},
                "missing_evidence": [] if verdict else ["documento_obrigatorio_nao_confirmado"],
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


def _nr10_prontuario_item_text(
    *,
    raw_payload: dict[str, Any] | None,
    structured_payload: dict[str, Any] | None,
    field_key: str,
) -> str:
    field_mappings: dict[str, dict[str, Any]] = {
        "referencia_principal": {
            "raw_keys": ("referencia_principal", "evidencia_principal"),
            "structured_paths": (
                ("identificacao", "referencia_principal"),
                ("evidencias_e_anexos", "evidencia_principal"),
            ),
        },
        "prontuario": {
            "raw_keys": ("prontuario",),
            "structured_paths": (
                ("evidencias_e_anexos", "documento_base"),
                ("documentacao_e_registros", "documentos_disponiveis"),
            ),
        },
        "diagrama_unifilar": {
            "raw_keys": ("diagrama_unifilar", "diagrama_eletrico"),
            "structured_paths": (("documentacao_e_registros", "documentos_disponiveis"),),
        },
        "inventario_instalacoes": {
            "raw_keys": ("inventario_instalacoes",),
            "structured_paths": (
                ("documentacao_e_registros", "documentos_disponiveis"),
                ("execucao_servico", "parametros_relevantes"),
            ),
        },
        "pie": {
            "raw_keys": ("pie", "prontuario_instalacoes", "prontuario_eletrico"),
            "structured_paths": (
                ("documentacao_e_registros", "documentos_disponiveis"),
                ("evidencias_e_anexos", "documento_base"),
            ),
        },
        "art_numero": {
            "raw_keys": ("art_numero", "art"),
            "structured_paths": (("documentacao_e_registros", "documentos_disponiveis"),),
        },
    }
    mapping = field_mappings.get(field_key, {})
    return _pick_text_from_payloads(
        raw_payload=raw_payload,
        structured_payload=structured_payload,
        raw_keys=tuple(mapping.get("raw_keys") or ()),
        structured_paths=tuple(mapping.get("structured_paths") or ()),
    )


def _build_nr10_prontuario_items(
    *,
    raw_payload: dict[str, Any] | None,
    structured_payload: dict[str, Any] | None,
    report_pack_version: str,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    items: list[dict[str, Any]] = []
    missing_item_codes: list[str] = []
    nonconformity_codes: list[str] = []
    critical_nonconformity_codes: list[str] = []

    for field_key, title, criticality in _NR10_PRONTUARIO_COMPONENT_SPECS:
        text = _nr10_prontuario_item_text(
            raw_payload=raw_payload,
            structured_payload=structured_payload,
            field_key=field_key,
        )
        verdict = _documentary_field_verdict(text)
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
                "norma_refs": ["NR10 prontuario report pack v1"],
                "rule_version": report_pack_version,
                "evidence_refs": [],
                "human_review_required": verdict in {None, "NC"},
                "missing_evidence": [] if verdict else ["documento_obrigatorio_nao_confirmado"],
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
