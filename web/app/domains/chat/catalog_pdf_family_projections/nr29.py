from __future__ import annotations

from typing import Any

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

_NR29_FAMILY_KEY = "nr29_inspecao_operacao_portuaria"
_NR29_DOCUMENT_NOTE = "Documento vinculado ao contexto de norma regulamentadora de seguranca e saude no trabalho portuario."
_NR29_DEFAULT_METHOD = (
    "Inspecao de campo em operacao portuaria com checklist NR29, verificacao de equipamentos, fluxos de carga, acessos e controles operacionais do cais."
)


def _resolve_nr29_conclusion_status(
    *values: Any,
    review_status: Any,
    has_nonconformity: bool | None,
) -> str | None:
    for value in values:
        text = _normalize_signal_text(value)
        if not text:
            continue
        if any(token in text for token in ("nao conforme", "reprov", "bloqueio", "nao liberad")):
            return "nao_conforme"
        if any(token in text for token in ("ressalva", "restric", "ajuste", "pendencia")):
            return "ajuste"
        if any(token in text for token in ("liberad", "aprov", "conforme")):
            return "conforme"
        if "pendente" in text:
            return "pendente"
    fallback = _resolve_conclusion_status(review_status, has_nonconformity=has_nonconformity)
    if fallback == "bloqueio":
        return "nao_conforme"
    return fallback


def apply_nr29_projection(
    *,
    payload: dict[str, Any],
    existing_payload: dict[str, Any] | None,
    family_key: str,
    laudo: Laudo | None,
    location_hint: str | None,
    summary_hint: str | None,
    recommendation_hint: str | None,
    title_hint: str | None,
) -> None:
    if family_key != _NR29_FAMILY_KEY:
        return

    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.objeto_principal",
                "objeto_principal",
                "operacao_portuaria",
                "atividade_portuaria",
                "frente_operacional",
                "berco_operacao",
                "terminal",
            ],
        ),
        title_hint,
        getattr(laudo, "primeira_mensagem", None),
    )
    internal_code = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.codigo_interno", "codigo_interno", "operacao_id", "numero_operacao", "tag"],
    )
    main_reference_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.referencia_principal.referencias_texto",
                "referencia_principal",
                "foto_principal",
                "evidencia_principal",
            ],
        ),
        internal_code,
    )
    main_reference_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.referencia_principal.descricao", "descricao_referencia_principal", "referencia_principal_descricao"],
        ),
        "Referencia principal do cenario portuario validada com evidencia de campo." if main_reference_text else None,
        object_hint,
    )
    main_reference_obs = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["identificacao.referencia_principal.observacao", "observacao_referencia_principal"]),
        "Rastreabilidade principal confirmada para o servico." if main_reference_text else None,
    )
    nr29_location_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.localizacao", "local_inspecao", "localizacao", "terminal", "berco", "setor", "unidade"],
        ),
        location_hint,
    )
    delivery_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.tipo_entrega", "tipo_entrega", "modalidade_laudo"]),
        _value_by_path(payload, "case_context.modalidade_laudo"),
        "inspecao_tecnica",
    )
    execution_mode = _pick_first_text(
        _normalize_execution_mode(
            _pick_value_by_paths(
                existing_payload,
                payload,
                paths=["escopo_servico.modo_execucao", "modo_execucao", "tipo_execucao", "modalidade_execucao"],
            )
        ),
        "in_loco",
    )
    scope_summary = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.resumo_escopo", "resumo_escopo", "resumo_servico", "escopo"]),
        summary_hint,
    )
    method_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["execucao_servico.metodo_aplicado", "metodo_aplicado", "metodo_inspecao", "metodo", "roteiro_inspecao"],
        ),
        _NR29_DEFAULT_METHOD,
    )
    observed_conditions = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["execucao_servico.condicoes_observadas", "condicoes_observadas", "condicoes_gerais", "status_operacao"],
        ),
        summary_hint,
    )
    relevant_parameters = _build_labeled_summary(
        ("Tipo operacao", _pick_text_by_paths(existing_payload, payload, paths=["tipo_operacao", "operacao_tipo"])),
        ("Equipamento", _pick_text_by_paths(existing_payload, payload, paths=["equipamento_portuario", "equipamento_principal"])),
        ("Movimentacao carga", _pick_text_by_paths(existing_payload, payload, paths=["movimentacao_carga", "tipo_carga"])),
        ("Acesso cais", _pick_text_by_paths(existing_payload, payload, paths=["acesso_cais", "acesso_operacional"])),
        ("Sinalizacao", _pick_text_by_paths(existing_payload, payload, paths=["sinalizacao", "isolamento_area"])),
        ("Amarracao", _pick_text_by_paths(existing_payload, payload, paths=["amarracao", "atracacao"])),
        ("Comunicacao", _pick_text_by_paths(existing_payload, payload, paths=["comunicacao_operacional", "comunicacao"])),
        ("Condicoes piso", _pick_text_by_paths(existing_payload, payload, paths=["condicoes_piso", "piso_operacional"])),
    )

    execution_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["execucao_servico.evidencia_execucao.referencias_texto", "evidencia_execucao", "registro_execucao", "evidencia_principal"],
        ),
        main_reference_text,
    )
    execution_evidence_desc = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.evidencia_execucao.descricao", "descricao_evidencia_execucao"]),
        observed_conditions,
    )
    primary_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload, payload, paths=["evidencias_e_anexos.evidencia_principal.referencias_texto", "evidencia_principal", "foto_principal"]
        ),
        execution_evidence_text,
    )
    primary_evidence_desc = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.evidencia_principal.descricao", "descricao_evidencia_principal"]),
        observed_conditions,
    )
    complementary_evidence_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["evidencias_e_anexos.evidencia_complementar.referencias_texto", "evidencia_complementar", "evidencias_complementares"],
    )
    complementary_evidence_desc = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["evidencias_e_anexos.evidencia_complementar.descricao", "descricao_evidencia_complementar"],
    )

    pgr = _pick_text_by_paths(existing_payload, payload, paths=["pgr_portuario", "pgr"])
    apr = _pick_text_by_paths(existing_payload, payload, paths=["apr", "analise_preliminar_risco"])
    emergency_plan = _pick_text_by_paths(existing_payload, payload, paths=["plano_emergencia", "plano_resposta"])
    procedure = _pick_text_by_paths(existing_payload, payload, paths=["procedimento_operacional", "procedimentos_operacionais"])
    permit = _pick_text_by_paths(existing_payload, payload, paths=["pte", "permissao_trabalho_especial", "permissao_operacao"])
    art_number = _pick_text_by_paths(existing_payload, payload, paths=["art_numero", "art"])
    document_base_text = _pick_first_text(pgr, procedure, emergency_plan, permit)
    document_summary = _build_labeled_summary(
        ("PGR", pgr),
        ("APR", apr),
        ("Procedimento", procedure),
        ("Plano emergencia", emergency_plan),
        ("Permissao", permit),
        ("ART", art_number),
    )
    document_notes = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["documentacao_e_registros.observacoes_documentais", "observacoes_documentais"]),
        _NR29_DOCUMENT_NOTE,
    )

    explicit_attention = _pick_value_by_paths(
        existing_payload,
        payload,
        paths=["nao_conformidades_ou_lacunas.ha_pontos_de_atencao", "ha_pontos_de_atencao", "ha_nao_conformidades", "possui_restricoes"],
    )
    attention_description = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["nao_conformidades_ou_lacunas.descricao", "descricao_pontos_atencao", "descricao_nao_conformidades", "pontos_de_atencao", "restricoes"],
        ),
        recommendation_hint,
        summary_hint,
    )
    has_attention_points = _infer_nonconformity_flag(explicit_attention, attention_description, recommendation_hint)
    attention_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["nao_conformidades_ou_lacunas.evidencias.referencias_texto", "evidencia_ponto_atencao", "evidencia_nao_conformidade"],
        ),
        primary_evidence_text,
    )
    explicit_conclusion = _pick_text_by_paths(existing_payload, payload, paths=["conclusao.status", "status_conclusao", "status"])

    _set_path_if_blank(payload, "identificacao.objeto_principal", object_hint)
    _set_path_if_blank(payload, "identificacao.localizacao", nr29_location_hint)
    _set_path_if_blank(payload, "identificacao.codigo_interno", internal_code)
    _set_block_fields_if_blank(
        payload,
        block_path="identificacao.referencia_principal",
        description=main_reference_desc,
        references_text=main_reference_text,
        observation=main_reference_obs,
        available=bool(main_reference_desc or main_reference_text or main_reference_obs),
    )

    _set_path_if_blank(payload, "escopo_servico.tipo_entrega", delivery_type)
    _set_path_if_blank(payload, "escopo_servico.modo_execucao", execution_mode)
    _set_path_if_blank(payload, "escopo_servico.ativo_tipo", "operacao_portuaria")
    _set_path_if_blank(payload, "escopo_servico.resumo_escopo", scope_summary)

    _set_path_if_blank(payload, "execucao_servico.metodo_aplicado", method_text)
    _set_path_if_blank(payload, "execucao_servico.condicoes_observadas", observed_conditions)
    _set_path_if_blank(payload, "execucao_servico.parametros_relevantes", relevant_parameters)
    _set_block_fields_if_blank(
        payload,
        block_path="execucao_servico.evidencia_execucao",
        description=execution_evidence_desc,
        references_text=execution_evidence_text,
        available=bool(execution_evidence_desc or execution_evidence_text),
    )

    _set_block_fields_if_blank(
        payload,
        block_path="evidencias_e_anexos.evidencia_principal",
        description=primary_evidence_desc,
        references_text=primary_evidence_text,
        available=bool(primary_evidence_desc or primary_evidence_text),
    )
    _set_block_fields_if_blank(
        payload,
        block_path="evidencias_e_anexos.evidencia_complementar",
        description=complementary_evidence_desc,
        references_text=complementary_evidence_text,
        available=bool(complementary_evidence_desc or complementary_evidence_text),
    )
    _set_block_fields_if_blank(
        payload,
        block_path="evidencias_e_anexos.documento_base",
        description="Documento base principal considerado para a avaliacao NR29." if document_base_text else None,
        references_text=document_base_text,
        observation=document_notes,
        available=bool(document_base_text),
    )

    _set_path_if_blank(payload, "documentacao_e_registros.documentos_disponiveis", document_summary)
    _set_path_if_blank(
        payload,
        "documentacao_e_registros.documentos_emitidos",
        _pick_text_by_paths(existing_payload, payload, paths=["documentacao_e_registros.documentos_emitidos", "documentos_emitidos", "laudo_emitido"]),
    )
    _set_path_if_blank(payload, "documentacao_e_registros.observacoes_documentais", document_notes)

    _set_path_if_blank(payload, "nao_conformidades_ou_lacunas.ha_pontos_de_atencao", has_attention_points)
    _set_path_if_blank(
        payload,
        "nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto",
        "Sim" if has_attention_points is True else "Nao" if has_attention_points is False else None,
    )
    _set_path_if_blank(payload, "nao_conformidades_ou_lacunas.descricao", attention_description)
    _set_block_fields_if_blank(
        payload,
        block_path="nao_conformidades_ou_lacunas.evidencias",
        description=attention_description,
        references_text=attention_evidence_text,
        available=bool(attention_description or attention_evidence_text),
    )

    _set_path_if_blank(
        payload,
        "mesa_review.pendencias_resolvidas_texto",
        f"Base documental considerada na emissao: {document_summary}" if document_summary else None,
    )
    _set_path_if_blank(
        payload,
        "conclusao.status",
        _resolve_nr29_conclusion_status(
            explicit_conclusion,
            review_status=getattr(laudo, "status_revisao", None),
            has_nonconformity=has_attention_points,
        ),
    )


__all__ = ["apply_nr29_projection"]
