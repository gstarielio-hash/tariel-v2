from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from app.core.paths import resolve_family_schemas_dir
from app.domains.chat.catalog_pdf_templates import (
    _build_labeled_summary,
    _infer_nonconformity_flag,
    _normalize_execution_mode,
    _normalize_signal_text,
    _pick_first_text,
    _pick_text_by_paths,
    _pick_value_by_paths,
    _resolve_conclusion_status,
    _set_block_fields_if_blank,
    _set_path_if_blank,
    _value_by_path,
)
from app.shared.database import Laudo

DEFAULT_OBJECT_PATHS: tuple[str, ...] = (
    "identificacao.objeto_principal",
    "objeto_principal",
    "programa",
    "laudo",
    "relatorio",
    "inspecao",
    "setor",
    "unidade",
    "area",
    "edificacao",
    "posto_trabalho",
    "processo",
)
DEFAULT_LOCATION_PATHS: tuple[str, ...] = (
    "identificacao.localizacao",
    "local_inspecao",
    "localizacao",
    "setor",
    "unidade",
    "planta",
    "area",
    "posto_trabalho",
)
DEFAULT_REFERENCE_PATHS: tuple[str, ...] = (
    "identificacao.referencia_principal.referencias_texto",
    "referencia_principal",
    "documento_base",
    "evidencia_principal",
    "foto_principal",
)
DEFAULT_CODE_PATHS: tuple[str, ...] = (
    "identificacao.codigo_interno",
    "codigo_interno",
    "codigo_programa",
    "numero_documento",
    "numero_laudo",
    "tag",
)
DEFAULT_DELIVERY_PATHS: tuple[str, ...] = (
    "escopo_servico.tipo_entrega",
    "tipo_entrega",
    "modalidade_laudo",
)
DEFAULT_EXECUTION_MODE_PATHS: tuple[str, ...] = (
    "escopo_servico.modo_execucao",
    "modo_execucao",
    "tipo_execucao",
    "modalidade_execucao",
)
DEFAULT_ASSET_TYPE_PATHS: tuple[str, ...] = (
    "escopo_servico.ativo_tipo",
    "ativo_tipo",
    "tipo_ativo",
)
DEFAULT_SCOPE_PATHS: tuple[str, ...] = (
    "escopo_servico.resumo_escopo",
    "resumo_escopo",
    "resumo_servico",
    "escopo",
)
DEFAULT_METHOD_PATHS: tuple[str, ...] = (
    "execucao_servico.metodo_aplicado",
    "metodo_aplicado",
    "metodo_inspecao",
    "metodo",
    "abordagem_tecnica",
)
DEFAULT_CONDITION_PATHS: tuple[str, ...] = (
    "execucao_servico.condicoes_observadas",
    "condicoes_observadas",
    "condicoes_gerais",
    "status_documentacao",
    "status_documental",
    "contexto_atual",
)
DEFAULT_EXECUTION_EVIDENCE_PATHS: tuple[str, ...] = (
    "execucao_servico.evidencia_execucao.referencias_texto",
    "evidencia_execucao",
    "registro_execucao",
    "evidencia_principal",
)
DEFAULT_COMPLEMENTARY_EVIDENCE_PATHS: tuple[str, ...] = (
    "evidencia_complementar",
    "evidencias_complementares",
    "registro_complementar",
)
DEFAULT_DOCUMENT_SUMMARY_PATHS: tuple[str, ...] = (
    "documentacao_e_registros.documentos_disponiveis",
    "documentos_disponiveis",
    "documentacao_disponivel",
    "documento_base",
    "pacote_documental",
)
DEFAULT_DOCUMENT_NOTES_PATHS: tuple[str, ...] = (
    "documentacao_e_registros.observacoes_documentais",
    "observacoes_documentais",
)
DEFAULT_ATTENTION_FLAG_PATHS: tuple[str, ...] = (
    "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
    "ha_pontos_de_atencao",
    "ha_nao_conformidades",
    "possui_restricoes",
)
DEFAULT_ATTENTION_DESCRIPTION_PATHS: tuple[str, ...] = (
    "nao_conformidades_ou_lacunas.descricao",
    "descricao_pontos_atencao",
    "descricao_nao_conformidades",
    "restricoes",
    "pendencias",
    "observacoes",
    "status_documentacao",
)
DEFAULT_STATUS_PATHS: tuple[str, ...] = (
    "conclusao.status",
    "status_conclusao",
    "status_documentacao",
    "status_documental",
    "status",
    "resultado",
)


def _merge_paths(extra_paths: list[str] | tuple[str, ...] | None, default_paths: tuple[str, ...]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for collection in (default_paths, extra_paths or []):
        for path in collection:
            key = str(path or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(key)
    return merged


def _family_schemas_dir() -> Path:
    return resolve_family_schemas_dir()


@lru_cache(maxsize=128)
def _load_family_example(family_key: str) -> dict[str, Any]:
    path = _family_schemas_dir() / f"{family_key}.laudo_output_exemplo.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _example_value(family_key: str, path: str) -> Any:
    return _value_by_path(_load_family_example(family_key), path)


def _resolve_wave3_conclusion_status(
    *values: Any,
    review_status: Any,
    has_nonconformity: bool | None,
    example_status: Any,
) -> str | None:
    for value in values:
        text = _normalize_signal_text(value)
        if not text:
            continue
        if any(token in text for token in ("nao conforme", "reprov", "bloqueio", "nao liberad")):
            return "nao_conforme"
        if any(token in text for token in ("ressalva", "restric", "ajuste", "pendenc")):
            return "ajuste"
        if any(token in text for token in ("conforme", "aprov", "liberad", "vigente", "atendido")):
            return "conforme"
        if "pendente" in text:
            return "pendente"

    fallback = _resolve_conclusion_status(review_status, has_nonconformity=has_nonconformity)
    if fallback:
        return fallback

    example_text = _normalize_signal_text(example_status)
    if example_text in {"ajuste", "conforme", "nao_conforme", "pendente"}:
        return example_text
    return None


def apply_wave3_generic_projection(
    *,
    payload: dict[str, Any],
    existing_payload: dict[str, Any] | None,
    family_key: str,
    laudo: Laudo | None,
    location_hint: str | None,
    summary_hint: str | None,
    recommendation_hint: str | None,
    title_hint: str | None,
    registry: dict[str, dict[str, Any]],
) -> None:
    meta = registry.get(family_key)
    if meta is None:
        return

    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("object_paths"), DEFAULT_OBJECT_PATHS),
        ),
        title_hint,
        getattr(laudo, "primeira_mensagem", None),
        _example_value(family_key, "identificacao.objeto_principal"),
    )
    internal_code = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("code_paths"), DEFAULT_CODE_PATHS),
        ),
        _example_value(family_key, "identificacao.codigo_interno"),
    )
    main_reference_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("reference_paths"), DEFAULT_REFERENCE_PATHS),
        ),
        internal_code,
        _example_value(family_key, "identificacao.referencia_principal.referencias_texto"),
    )
    main_reference_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.referencia_principal.descricao", "descricao_referencia_principal"],
        ),
        _example_value(family_key, "identificacao.referencia_principal.descricao"),
        object_hint,
    )
    main_reference_obs = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.referencia_principal.observacao", "observacao_referencia_principal"],
        ),
        _example_value(family_key, "identificacao.referencia_principal.observacao"),
    )
    resolved_location = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("location_paths"), DEFAULT_LOCATION_PATHS),
        ),
        location_hint,
        _example_value(family_key, "identificacao.localizacao"),
    )
    delivery_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("delivery_paths"), DEFAULT_DELIVERY_PATHS),
        ),
        _example_value(family_key, "escopo_servico.tipo_entrega"),
    )
    execution_mode = _pick_first_text(
        _normalize_execution_mode(
            _pick_value_by_paths(
                existing_payload,
                payload,
                paths=_merge_paths(meta.get("execution_mode_paths"), DEFAULT_EXECUTION_MODE_PATHS),
            )
        ),
        _example_value(family_key, "escopo_servico.modo_execucao"),
    )
    asset_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("asset_type_paths"), DEFAULT_ASSET_TYPE_PATHS),
        ),
        _example_value(family_key, "escopo_servico.ativo_tipo"),
    )
    scope_summary = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("scope_paths"), DEFAULT_SCOPE_PATHS),
        ),
        summary_hint,
        _example_value(family_key, "escopo_servico.resumo_escopo"),
    )
    method_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("method_paths"), DEFAULT_METHOD_PATHS),
        ),
        _example_value(family_key, "execucao_servico.metodo_aplicado"),
    )
    observed_conditions = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("condition_paths"), DEFAULT_CONDITION_PATHS),
        ),
        summary_hint,
        _example_value(family_key, "execucao_servico.condicoes_observadas"),
    )

    parameter_fields = []
    for label, paths in meta.get("parameter_fields") or []:
        parameter_fields.append(
            (
                label,
                _pick_text_by_paths(existing_payload, payload, paths=list(paths)),
            )
        )
    relevant_parameters = _pick_first_text(
        _build_labeled_summary(*parameter_fields),
        _example_value(family_key, "execucao_servico.parametros_relevantes"),
    )

    execution_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("execution_evidence_paths"), DEFAULT_EXECUTION_EVIDENCE_PATHS),
        ),
        main_reference_text,
        _example_value(family_key, "execucao_servico.evidencia_execucao.referencias_texto"),
    )
    execution_evidence_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["execucao_servico.evidencia_execucao.descricao", "descricao_evidencia_execucao"],
        ),
        observed_conditions,
        _example_value(family_key, "execucao_servico.evidencia_execucao.descricao"),
    )
    complementary_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("complementary_evidence_paths"), DEFAULT_COMPLEMENTARY_EVIDENCE_PATHS),
        ),
        _example_value(family_key, "nao_conformidades_ou_lacunas.evidencias.referencias_texto"),
    )

    document_fields = []
    for label, paths in meta.get("document_fields") or []:
        document_fields.append(
            (
                label,
                _pick_text_by_paths(existing_payload, payload, paths=list(paths)),
            )
        )
    document_summary = _pick_first_text(
        _build_labeled_summary(*document_fields),
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("document_summary_paths"), DEFAULT_DOCUMENT_SUMMARY_PATHS),
        ),
        _example_value(family_key, "documentacao_e_registros.documentos_disponiveis"),
    )
    document_notes = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("document_notes_paths"), DEFAULT_DOCUMENT_NOTES_PATHS),
        ),
        _example_value(family_key, "documentacao_e_registros.observacoes_documentais"),
    )
    documents_emitted = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["documentacao_e_registros.documentos_emitidos", "documentos_emitidos"],
        ),
        _example_value(family_key, "documentacao_e_registros.documentos_emitidos"),
    )

    explicit_attention = _pick_value_by_paths(
        existing_payload,
        payload,
        paths=_merge_paths(meta.get("attention_flag_paths"), DEFAULT_ATTENTION_FLAG_PATHS),
    )
    attention_description = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=_merge_paths(meta.get("attention_description_paths"), DEFAULT_ATTENTION_DESCRIPTION_PATHS),
        ),
        recommendation_hint,
        _example_value(family_key, "nao_conformidades_ou_lacunas.descricao"),
    )
    has_attention_points = _infer_nonconformity_flag(
        explicit_attention,
        attention_description,
        recommendation_hint,
    )
    if has_attention_points is None:
        example_attention = _pick_value_by_paths(
            _load_family_example(family_key),
            paths=["nao_conformidades_ou_lacunas.ha_pontos_de_atencao"],
        )
        has_attention_points = _infer_nonconformity_flag(example_attention)

    attention_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "nao_conformidades_ou_lacunas.evidencias.referencias_texto",
                "evidencia_ponto_atencao",
                "evidencia_nao_conformidade",
            ],
        ),
        complementary_evidence_text,
        execution_evidence_text,
        _example_value(family_key, "nao_conformidades_ou_lacunas.evidencias.referencias_texto"),
    )
    explicit_conclusion = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=_merge_paths(meta.get("status_paths"), DEFAULT_STATUS_PATHS),
    )
    conclusion_status = _resolve_wave3_conclusion_status(
        explicit_conclusion,
        attention_description,
        review_status=getattr(laudo, "status_revisao", None),
        has_nonconformity=has_attention_points,
        example_status=_example_value(family_key, "conclusao.status"),
    )
    recommendation_text = _pick_first_text(
        recommendation_hint,
        attention_description,
        _example_value(family_key, "recomendacoes.texto"),
    )
    conclusion_text = _pick_first_text(
        summary_hint,
        _example_value(family_key, "conclusao.conclusao_tecnica"),
    )
    justification_text = _pick_first_text(
        summary_hint,
        _example_value(family_key, "conclusao.justificativa"),
    )

    _set_path_if_blank(payload, "identificacao.objeto_principal", object_hint)
    _set_path_if_blank(payload, "identificacao.localizacao", resolved_location)
    _set_path_if_blank(payload, "identificacao.codigo_interno", internal_code)
    _set_block_fields_if_blank(
        payload,
        block_path="identificacao.referencia_principal",
        description=main_reference_desc,
        references_text=main_reference_text,
        available=bool(main_reference_text),
        observation=main_reference_obs,
    )

    _set_path_if_blank(payload, "escopo_servico.tipo_entrega", delivery_type)
    _set_path_if_blank(payload, "escopo_servico.modo_execucao", execution_mode)
    _set_path_if_blank(payload, "escopo_servico.ativo_tipo", asset_type)
    _set_path_if_blank(payload, "escopo_servico.resumo_escopo", scope_summary)

    _set_path_if_blank(payload, "execucao_servico.metodo_aplicado", method_text)
    _set_path_if_blank(payload, "execucao_servico.condicoes_observadas", observed_conditions)
    _set_path_if_blank(payload, "execucao_servico.parametros_relevantes", relevant_parameters)
    _set_block_fields_if_blank(
        payload,
        block_path="execucao_servico.evidencia_execucao",
        description=execution_evidence_desc,
        references_text=execution_evidence_text,
        available=bool(execution_evidence_text),
        observation=observed_conditions,
    )

    _set_path_if_blank(payload, "documentacao_e_registros.documentos_disponiveis", document_summary)
    _set_path_if_blank(payload, "documentacao_e_registros.documentos_emitidos", documents_emitted)
    _set_path_if_blank(payload, "documentacao_e_registros.observacoes_documentais", document_notes)

    if has_attention_points is not None:
        _set_path_if_blank(
            payload,
            "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
            has_attention_points,
        )
        _set_path_if_blank(
            payload,
            "nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto",
            "Sim" if has_attention_points else "Nao",
        )
    _set_path_if_blank(payload, "nao_conformidades_ou_lacunas.descricao", attention_description)
    _set_block_fields_if_blank(
        payload,
        block_path="nao_conformidades_ou_lacunas.evidencias",
        description=_example_value(family_key, "nao_conformidades_ou_lacunas.evidencias.descricao"),
        references_text=attention_evidence_text,
        available=bool(attention_evidence_text),
        observation=_example_value(family_key, "nao_conformidades_ou_lacunas.evidencias.observacao"),
    )

    _set_path_if_blank(payload, "recomendacoes.texto", recommendation_text)
    _set_path_if_blank(payload, "conclusao.status", conclusion_status)
    _set_path_if_blank(payload, "conclusao.conclusao_tecnica", conclusion_text)
    _set_path_if_blank(payload, "conclusao.justificativa", justification_text)


__all__ = ["apply_wave3_generic_projection"]
