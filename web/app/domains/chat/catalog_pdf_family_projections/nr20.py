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

_NR20_SERVICE_META: dict[str, dict[str, str]] = {
    "nr20_inspecao_instalacoes_inflamaveis": {
        "service_label": "inspecao instalacoes inflamaveis",
        "scope_summary": (
            "Execucao do servico inspecao instalacoes inflamaveis no contexto da norma seguranca "
            "e saude no trabalho com inflamaveis e combustiveis, com consolidacao de evidencias, "
            "registros de campo ou base documental e conclusao tecnica auditavel."
        ),
        "method_text": (
            "Metodo padrao Tariel para inspecao instalacoes inflamaveis, com registro estruturado do "
            "escopo, dados de execucao, anexos principais e pontos de atencao."
        ),
        "document_base": "Pacote tecnico de referencia para inspecao instalacoes inflamaveis.",
        "documents_emitted": "Pacote tecnico de nr20 - inspecao instalacoes inflamaveis consolidado para entrega.",
        "recommendation": (
            "Manter rastreabilidade do servico inspecao instalacoes inflamaveis e registrar "
            "formalmente qualquer ajuste, complemento documental ou revalidacao futura."
        ),
        "conclusion": (
            "O servico nr20 - inspecao instalacoes inflamaveis foi consolidado com rastreabilidade "
            "suficiente, evidencias principais vinculadas e conclusao tecnica formalizada."
        ),
        "delivery_type": "inspecao_tecnica",
        "execution_mode": "in_loco",
        "document_note": "Documento vinculado ao contexto de seguranca e saude no trabalho com inflamaveis e combustiveis.",
    },
    "nr20_prontuario_instalacoes_inflamaveis": {
        "service_label": "prontuario instalacoes inflamaveis",
        "scope_summary": (
            "Execucao do servico prontuario instalacoes inflamaveis no contexto da norma seguranca "
            "e saude no trabalho com inflamaveis e combustiveis, com consolidacao de evidencias, "
            "registros de campo ou base documental e conclusao tecnica auditavel."
        ),
        "method_text": (
            "Metodo padrao Tariel para prontuario instalacoes inflamaveis, com registro estruturado do "
            "escopo, dados de execucao, anexos principais e pontos de atencao."
        ),
        "document_base": "Pacote tecnico de referencia para prontuario instalacoes inflamaveis.",
        "documents_emitted": "Pacote tecnico de nr20 - prontuario instalacoes inflamaveis consolidado para entrega.",
        "recommendation": (
            "Manter rastreabilidade do servico prontuario instalacoes inflamaveis e registrar "
            "formalmente qualquer ajuste, complemento documental ou revalidacao futura."
        ),
        "conclusion": (
            "O servico nr20 - prontuario instalacoes inflamaveis foi consolidado com rastreabilidade "
            "suficiente, evidencias principais vinculadas e conclusao tecnica formalizada."
        ),
        "delivery_type": "pacote_documental",
        "execution_mode": "analise_documental",
        "document_note": "Documento vinculado ao contexto de seguranca e saude no trabalho com inflamaveis e combustiveis.",
    },
}

_NR20_DEFAULT_JUSTIFICATION = (
    "A conclusao considera o escopo registrado, o metodo aplicado, a documentacao disponivel, "
    "a evidencia principal e os pontos de atencao ou sua ausencia declarada."
)
_NR20_DEFAULT_EXECUTION_OBSERVATION = (
    "Servico executado dentro do escopo previsto, com registros suficientes para revisao da Mesa e consolidacao do documento final."
)
_NR20_DEFAULT_REFERENCE_DESCRIPTION = "Referencia principal do objeto identificada com apoio de evidencia visual e documento associado."
_NR20_DEFAULT_REFERENCE_OBSERVATION = "Rastreabilidade principal confirmada para o servico."


def _resolve_nr20_conclusion_status(
    *values: Any,
    review_status: Any,
    has_nonconformity: bool | None,
) -> str | None:
    for value in values:
        text = _normalize_signal_text(value)
        if not text:
            continue
        if any(token in text for token in ("nao liberad", "reprov", "nao conforme")):
            return "nao_conforme"
        if any(token in text for token in ("restric", "ressalva", "ajuste", "pendencia controlada")):
            return "ajuste"
        if any(token in text for token in ("liberad", "aprov", "conforme")):
            return "conforme"
        if "pendente" in text:
            return "pendente"

    fallback = _resolve_conclusion_status(review_status, has_nonconformity=has_nonconformity)
    if fallback == "bloqueio":
        return "nao_conforme"
    return fallback


def apply_nr20_projection(
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
    meta = _NR20_SERVICE_META.get(family_key)
    if meta is None:
        return

    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.objeto_principal",
                "objeto_principal",
                "instalacao_principal",
                "tanque_principal",
                "sistema_principal",
                "area_classificada",
                "prontuario_objeto",
                "unidade_processo",
            ],
        ),
        title_hint,
        getattr(laudo, "primeira_mensagem", None),
    )
    internal_code = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "identificacao.codigo_interno",
            "codigo_interno",
            "tag_patrimonial",
            "tag",
            "numero_prontuario",
            "codigo_area",
            "numero_relatorio",
            "numero_inspecao",
        ],
    )
    main_reference_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.referencia_principal.referencias_texto",
                "referencia_principal",
                "referencia_principal_ref",
                "foto_principal",
                "evidencia_execucao",
                "evidencia_principal",
            ],
        ),
        internal_code,
    )
    main_reference_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.referencia_principal.descricao",
                "descricao_referencia_principal",
                "referencia_principal_descricao",
            ],
        ),
        _NR20_DEFAULT_REFERENCE_DESCRIPTION if main_reference_text else None,
        object_hint,
    )
    main_reference_obs = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.referencia_principal.observacao",
                "observacao_referencia_principal",
            ],
        ),
        _NR20_DEFAULT_REFERENCE_OBSERVATION if main_reference_text else None,
    )
    nr20_location_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.localizacao",
                "local_inspecao",
                "localizacao",
                "area_classificada",
                "setor",
                "unidade",
                "informacoes_gerais.local",
                "informacoes_gerais.unidade",
            ],
        ),
        location_hint,
    )

    raw_execution_mode = _normalize_execution_mode(
        _pick_value_by_paths(
            existing_payload,
            payload,
            paths=[
                "escopo_servico.modo_execucao",
                "modo_execucao",
                "tipo_execucao",
                "modalidade_execucao",
            ],
        )
    )
    if family_key == "nr20_prontuario_instalacoes_inflamaveis" and raw_execution_mode in {None, "documental"}:
        execution_mode = "analise_documental"
    else:
        execution_mode = _pick_first_text(raw_execution_mode, meta["execution_mode"]) or "analise_documental"

    delivery_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.tipo_entrega", "tipo_entrega", "modalidade_laudo"],
        ),
        _value_by_path(payload, "case_context.modalidade_laudo"),
        meta["delivery_type"],
    )
    asset_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.ativo_tipo", "ativo_tipo", "tipo_ativo"],
        ),
        "NR20",
    )
    scope_summary = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "escopo_servico.resumo_escopo",
                "resumo_escopo",
                "resumo_servico",
                "escopo",
            ],
        ),
        meta["scope_summary"],
    )

    classification_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["classificacao_area", "classe_instalacao", "classe_area"],
    )
    containment_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["bacia_contencao", "contencao", "drenagem_contingencia"],
    )
    grounding_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["aterramento", "bonding", "equipotencializacao"],
    )
    signaling_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["sinalizacao", "placas", "identificacao_risco"],
    )
    firefighting_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["combate_incendio", "extintores", "sistema_combatedor"],
    )

    if family_key == "nr20_inspecao_instalacoes_inflamaveis":
        method_text = _pick_first_text(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=[
                    "execucao_servico.metodo_aplicado",
                    "metodo_aplicado",
                    "metodo_inspecao",
                    "metodo",
                ],
            ),
            meta["method_text"],
        )
        relevant_parameters = _build_labeled_summary(
            ("Classificacao", classification_text),
            ("Contencao", containment_text),
            ("Aterramento", grounding_text),
            ("Sinalizacao", signaling_text),
            ("Combate a incendio", firefighting_text),
            (
                "Detector de gas",
                _pick_text_by_paths(existing_payload, payload, paths=["detector_gas", "monitoramento_gases"]),
            ),
        )
        document_base_text = _pick_first_text(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=[
                    "evidencias_e_anexos.documento_base.referencias_texto",
                    "documento_base",
                    "prontuario_nr20",
                    "plano_inspecao",
                ],
            ),
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["procedimento_operacional", "art_numero", "planta_classificada"],
            ),
            meta["document_base"],
        )
        document_summary = _build_labeled_summary(
            ("Prontuario NR20", _pick_text_by_paths(existing_payload, payload, paths=["prontuario_nr20"])),
            ("Plano de inspecao", _pick_text_by_paths(existing_payload, payload, paths=["plano_inspecao"])),
            ("Procedimento", _pick_text_by_paths(existing_payload, payload, paths=["procedimento_operacional"])),
            ("ART", _pick_text_by_paths(existing_payload, payload, paths=["art_numero", "art"])),
            ("Planta classificada", _pick_text_by_paths(existing_payload, payload, paths=["planta_classificada"])),
        )
    else:
        inventory_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["inventario_instalacoes", "inventario", "relacao_equipamentos"],
        )
        risk_analysis_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["analise_riscos", "analise_risco", "estudo_risco"],
        )
        procedures_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["procedimentos_operacionais", "procedimento_operacional", "procedimentos"],
        )
        emergency_plan_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["plano_resposta_emergencia", "plano_emergencia", "resposta_emergencia"],
        )
        training_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["matriz_treinamentos", "treinamentos", "qualificacao_equipes"],
        )
        method_text = _pick_first_text(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=[
                    "execucao_servico.metodo_aplicado",
                    "metodo_aplicado",
                    "metodo_inspecao",
                    "metodo",
                ],
            ),
            meta["method_text"],
        )
        relevant_parameters = _build_labeled_summary(
            ("Inventario", inventory_text),
            ("Analise de riscos", risk_analysis_text),
            ("Procedimentos", procedures_text),
            ("Plano de emergencia", emergency_plan_text),
            ("Treinamentos", training_text),
            ("Classificacao", classification_text),
        )
        document_base_text = _pick_first_text(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=[
                    "evidencias_e_anexos.documento_base.referencias_texto",
                    "documento_base",
                    "prontuario_nr20",
                    "inventario_instalacoes",
                ],
            ),
            _pick_text_by_paths(existing_payload, payload, paths=["analise_riscos", "plano_resposta_emergencia"]),
            meta["document_base"],
        )
        document_summary = _build_labeled_summary(
            ("Prontuario NR20", _pick_text_by_paths(existing_payload, payload, paths=["prontuario_nr20"])),
            ("Inventario", inventory_text),
            ("Analise de riscos", risk_analysis_text),
            ("Plano de emergencia", emergency_plan_text),
            ("Treinamentos", training_text),
        )

    observed_conditions = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.condicoes_observadas",
                "condicoes_observadas",
                "condicoes_gerais",
                "resumo_executivo",
            ],
        ),
        getattr(laudo, "parecer_ia", None),
        summary_hint,
        _NR20_DEFAULT_EXECUTION_OBSERVATION,
    )
    execution_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.evidencia_execucao.referencias_texto",
                "evidencia_execucao",
                "registro_execucao",
                "evidencia_principal",
            ],
        ),
        main_reference_text,
    )
    execution_evidence_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["execucao_servico.evidencia_execucao.descricao", "descricao_evidencia_execucao"],
        ),
        "Evidencia da execucao principal do servico." if execution_evidence_text else None,
        observed_conditions,
    )
    primary_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["evidencias_e_anexos.evidencia_principal.referencias_texto", "evidencia_principal"],
        ),
        execution_evidence_text,
    )
    primary_evidence_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["evidencias_e_anexos.evidencia_principal.descricao", "descricao_evidencia_principal"],
        ),
        "Evidencia principal que suporta a conclusao tecnica." if primary_evidence_text else None,
        observed_conditions,
    )
    complementary_evidence_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "evidencias_e_anexos.evidencia_complementar.referencias_texto",
            "evidencia_complementar",
            "evidencias_complementares",
        ],
    )
    complementary_evidence_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["evidencias_e_anexos.evidencia_complementar.descricao", "descricao_evidencia_complementar"],
        ),
        "Evidencia complementar para contextualizacao do servico." if complementary_evidence_text else None,
    )
    document_notes = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["documentacao_e_registros.observacoes_documentais", "observacoes_documentais"],
        ),
        meta["document_note"],
    )

    explicit_attention = _pick_value_by_paths(
        existing_payload,
        payload,
        paths=[
            "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
            "ha_pontos_de_atencao",
            "nao_conformidades.ha_nao_conformidades",
            "ha_nao_conformidades",
            "possui_restricoes",
        ],
    )
    attention_description = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "nao_conformidades_ou_lacunas.descricao",
                "descricao_pontos_atencao",
                "descricao_nao_conformidades",
                "restricoes",
                "pendencias",
                "nao_conformidades",
            ],
        ),
        recommendation_hint,
    )
    explicit_conclusion_status = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["conclusao.status", "status_conclusao", "status_servico", "status"],
    )
    has_attention_points = _infer_nonconformity_flag(
        explicit_attention,
        attention_description,
        explicit_conclusion_status,
    )
    if has_attention_points is None and explicit_conclusion_status:
        normalized_status = _normalize_signal_text(explicit_conclusion_status)
        if any(token in normalized_status for token in ("nao liberad", "reprov", "restric", "ajuste")):
            has_attention_points = True
        elif any(token in normalized_status for token in ("liberad", "conforme", "aprov")):
            has_attention_points = False

    recommendation_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["recomendacoes.texto", "recomendacao", "recomendacoes", "observacoes"],
        ),
        recommendation_hint,
        meta["recommendation"],
    )
    conclusion_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["conclusao.conclusao_tecnica", "conclusao_tecnica"],
        ),
        meta["conclusion"],
    )
    conclusion_justification = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["conclusao.justificativa", "justificativa"]),
        _NR20_DEFAULT_JUSTIFICATION,
    )
    summary_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["resumo_executivo"]),
        summary_hint,
        (
            f"Foi executado o servico nr20 - {meta['service_label']} com registro "
            "estruturado do objeto principal, evidencias vinculadas, "
            "documentacao de apoio e conclusao tecnica consolidada para a Mesa."
        ),
    )
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
        primary_evidence_text,
    )

    _set_path_if_blank(payload, "resumo_executivo", summary_text)

    _set_path_if_blank(payload, "identificacao.objeto_principal", object_hint)
    _set_path_if_blank(payload, "identificacao.localizacao", nr20_location_hint)
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
        observation="Registros principais consolidados." if execution_evidence_text else None,
        available=bool(execution_evidence_desc or execution_evidence_text),
    )

    _set_block_fields_if_blank(
        payload,
        block_path="evidencias_e_anexos.evidencia_principal",
        description=primary_evidence_desc,
        references_text=primary_evidence_text,
        observation="Material principal vinculado ao caso." if primary_evidence_text else None,
        available=bool(primary_evidence_desc or primary_evidence_text),
    )
    _set_block_fields_if_blank(
        payload,
        block_path="evidencias_e_anexos.evidencia_complementar",
        description=complementary_evidence_desc,
        references_text=complementary_evidence_text,
        observation="Registro complementar sem impacto critico." if complementary_evidence_text else None,
        available=bool(complementary_evidence_desc or complementary_evidence_text),
    )
    _set_block_fields_if_blank(
        payload,
        block_path="evidencias_e_anexos.documento_base",
        description="Documento base ou ancora principal do servico." if document_base_text else None,
        references_text=document_base_text,
        observation="Documento vinculado ao pacote final." if document_base_text else None,
        available=bool(document_base_text),
    )

    _set_path_if_blank(payload, "documentacao_e_registros.documentos_disponiveis", document_summary)
    _set_path_if_blank(payload, "documentacao_e_registros.documentos_emitidos", meta["documents_emitted"])
    _set_path_if_blank(payload, "documentacao_e_registros.observacoes_documentais", document_notes)

    _set_path_if_blank(payload, "nao_conformidades_ou_lacunas.ha_pontos_de_atencao", has_attention_points)
    _set_path_if_blank(
        payload,
        "nao_conformidades_ou_lacunas.ha_pontos_de_atencao_texto",
        "Sim" if has_attention_points is True else "Nao" if has_attention_points is False else None,
    )
    _set_path_if_blank(
        payload,
        "nao_conformidades_ou_lacunas.descricao",
        attention_description
        or ("Nao foram identificados pontos de atencao relevantes no fechamento deste servico." if has_attention_points is False else None),
    )
    _set_block_fields_if_blank(
        payload,
        block_path="nao_conformidades_ou_lacunas.evidencias",
        description=attention_description or ("Registro relacionado aos pontos de atencao ou a ausencia declarada deles." if attention_evidence_text else None),
        references_text=attention_evidence_text,
        observation="Evidencia vinculada ao fechamento da analise." if attention_evidence_text else None,
        available=bool(attention_description or attention_evidence_text),
    )

    _set_path_if_blank(payload, "recomendacoes.texto", recommendation_text)
    _set_path_if_blank(payload, "conclusao.conclusao_tecnica", conclusion_text)
    _set_path_if_blank(payload, "conclusao.justificativa", conclusion_justification)
    _set_path_if_blank(
        payload,
        "conclusao.status",
        _resolve_nr20_conclusion_status(
            explicit_conclusion_status,
            review_status=getattr(laudo, "status_revisao", None),
            has_nonconformity=has_attention_points,
        ),
    )
    _set_path_if_blank(
        payload,
        "mesa_review.pendencias_resolvidas_texto",
        f"Base documental considerada na emissao: {document_summary}" if document_summary else None,
    )


__all__ = ["apply_nr20_projection"]
