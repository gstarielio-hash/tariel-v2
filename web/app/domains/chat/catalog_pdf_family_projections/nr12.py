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


def _infer_nr12_asset_type(*values: Any) -> str | None:
    joined = " ".join(str(value or "").strip() for value in values if str(value or "").strip())
    text = _normalize_signal_text(joined)
    if "ponte rolante" in text or "talha" in text:
        return "ponte_rolante"
    if "prensa" in text and "hidraul" in text:
        return "prensa_hidraulica"
    if "prensa" in text:
        return "prensa"
    if "injetor" in text:
        return "injetora"
    if "torno" in text:
        return "torno"
    if "esteira" in text or "transportador" in text:
        return "esteira_transportadora"
    if "maquina" in text:
        return "maquina"
    if "equipamento" in text:
        return "equipamento"
    return "maquina_equipamento" if text else None


def _humanize_nr12_asset_type(*values: Any) -> str | None:
    text = _normalize_signal_text(" ".join(str(value or "").strip() for value in values if str(value or "").strip()))
    if not text:
        return None
    if "ponte rolante" in text or "talha" in text:
        return "Ponte rolante"
    if "prensa" in text and "hidraul" in text:
        return "Prensa hidraulica"
    if "prensa" in text:
        return "Prensa"
    if "injetor" in text:
        return "Injetora"
    if "torno" in text:
        return "Torno"
    if "esteira" in text or "transportador" in text or "fita" in text:
        return "Transportador continuo de materiais"
    if "maquina" in text:
        return "Maquina"
    if "equipamento" in text:
        return "Equipamento"
    return _pick_first_text(*values)


def _normalize_nr12_component_condition(*values: Any) -> str | None:
    text = _normalize_signal_text(" ".join(str(value or "").strip() for value in values if str(value or "").strip()))
    if not text:
        return None
    if "nao aplic" in text or text in {"n/a", "na"}:
        return "N/A"
    negative_patterns = (
        "ausencia",
        "expost",
        "irregular",
        "inoper",
        "nao conforme",
        "sem prote",
        "sem guarda",
        "nao bloque",
        "sem bloquear",
        "abre sem",
        "fiacao aparente",
        "cabeamento inadequ",
        "acesso perig",
        "insuficiente",
    )
    if any(pattern in text for pattern in negative_patterns):
        return "NC"
    positive_patterns = (
        "presente",
        "integra",
        "adequad",
        "segur",
        "funcional",
        "conforme",
        "operacional",
    )
    if any(pattern in text for pattern in positive_patterns):
        return "C"
    return None


def _resolve_nr12_operational_status(*values: Any) -> str | None:
    for value in values:
        text = _normalize_signal_text(value)
        if not text:
            continue
        if "bloqueio" in text:
            return "bloqueio"
        if any(token in text for token in ("ajuste", "adequacao", "nao conforme", "reprov", "pendencia")):
            return "adequacao_requerida"
        if any(token in text for token in ("conforme", "aprovado")):
            return "liberado_com_controle"
    return None


def apply_nr12_projection(
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
    if family_key != "nr12_inspecao_maquina_equipamento":
        return

    nr12_location_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.localizacao",
                "local_inspecao",
                "informacoes_gerais.local",
                "informacoes_gerais.unidade",
                "unidade",
            ],
        ),
        location_hint,
    )
    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.objeto_principal",
                "objeto_principal",
                "nome_equipamento",
                "equipamento",
                "maquina",
                "maquina_principal",
                "objeto_inspecao.identificacao",
                "prensa",
                "ponte_rolante",
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
            "codigo_tag",
            "tag",
            "asset_tag",
            "patrimonio",
            "serial_equipamento",
            "numero_maquina",
        ],
    )
    main_reference_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "identificacao.referencia_principal.referencias_texto",
            "referencia_principal",
            "referencia_principal_ref",
            "foto_maquina",
            "foto_equipamento",
            "foto_frontal",
        ],
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
        object_hint,
    )
    main_reference_obs = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.referencia_principal.observacao", "observacao_referencia_principal"],
    )
    unit_name = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.unidade_operacional", "informacoes_gerais.unidade", "unidade_operacional", "unidade"],
    )
    local_document = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.local_documento", "informacoes_gerais.local_documento", "informacoes_gerais.local", "local", "local_inspecao"],
    )
    inspection_type = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["case_context.tipo_inspecao", "identificacao.tipo_inspecao", "informacoes_gerais.tipo_inspecao", "tipo_inspecao"],
    )

    delivery_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.tipo_entrega", "tipo_entrega", "modalidade_laudo"]),
        _value_by_path(payload, "case_context.modalidade_laudo"),
    )
    execution_mode = _normalize_execution_mode(
        _pick_value_by_paths(existing_payload, payload, paths=["escopo_servico.modo_execucao", "modo_execucao", "tipo_execucao", "modalidade_execucao"])
    )
    asset_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.ativo_tipo", "ativo_tipo", "tipo_ativo", "tipo_maquina", "objeto_tipo"]),
        _infer_nr12_asset_type(object_hint, internal_code, title_hint),
    )
    scope_summary = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.resumo_escopo", "resumo_escopo", "resumo_servico", "escopo"]),
        summary_hint,
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
                "roteiro_inspecao",
                "checklist_aplicado",
                "checklist_nr12",
            ],
        ),
        "Inspecao visual e funcional com checklist NR12." if object_hint else None,
    )
    observed_conditions = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.condicoes_observadas",
                "condicoes_observadas",
                "condicoes_gerais",
                "condicao_geral",
                "condicao_operacional",
                "estado_geral",
                "parecer_preliminar",
            ],
        ),
        summary_hint,
    )
    guards_text = _pick_text_by_paths(
        existing_payload, payload, paths=["guardas_protecoes", "protecao_maquina", "protecoes", "protecao_lateral", "protecao_frontal"]
    )
    emergency_stop_text = _pick_text_by_paths(existing_payload, payload, paths=["parada_emergencia", "botoeira_emergencia", "emergencia"])
    interlocks_text = _pick_text_by_paths(existing_payload, payload, paths=["intertravamentos", "intertravamento_porta", "intertravamento"])
    risk_zone_text = _pick_text_by_paths(existing_payload, payload, paths=["zona_risco", "acessos_perigosos", "ponto_perigoso"])
    signage_text = _pick_text_by_paths(
        existing_payload, payload, paths=["sinalizacao", "sinalizacao_seguranca", "sinalizacao_segurança", "comunicacao_visual"]
    )
    enclosure_text = _pick_text_by_paths(existing_payload, payload, paths=["enclausuramento", "isolamento_area"])
    loto_text = _pick_text_by_paths(existing_payload, payload, paths=["procedimento_bloqueio", "bloqueio_etiquetagem", "loto"])
    relevant_parameters = _build_labeled_summary(
        ("Protecoes", guards_text),
        ("Parada de emergencia", emergency_stop_text),
        ("Intertravamentos", interlocks_text),
        ("Zona de risco", risk_zone_text),
        ("Enclausuramento", enclosure_text),
        ("Bloqueio/LOTO", loto_text),
    )

    execution_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.evidencia_execucao.referencias_texto",
                "evidencia_execucao",
                "registro_execucao",
                "foto_teste_funcional",
                "checklist_nr12",
            ],
        ),
        main_reference_text,
    )
    execution_evidence_desc = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.evidencia_execucao.descricao", "descricao_evidencia_execucao"]),
        observed_conditions,
    )
    primary_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["evidencias_e_anexos.evidencia_principal.referencias_texto", "evidencia_principal", "foto_principal", "registro_principal"],
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
        paths=["evidencias_e_anexos.evidencia_complementar.referencias_texto", "evidencia_complementar", "evidencias_complementares", "foto_complementar"],
    )
    complementary_evidence_desc = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["evidencias_e_anexos.evidencia_complementar.descricao", "descricao_evidencia_complementar"],
    )

    manual_text = _pick_text_by_paths(existing_payload, payload, paths=["manual_maquina", "manual_equipamento", "manual"])
    inventory_text = _pick_text_by_paths(existing_payload, payload, paths=["inventario_maquinas", "inventario_nr12", "inventario"])
    checklist_text = _pick_text_by_paths(existing_payload, payload, paths=["checklist_nr12", "checklist_inspecao", "checklist"])
    risk_analysis_text = _pick_text_by_paths(existing_payload, payload, paths=["apreciacao_risco", "analise_risco"])
    procedure_text = _pick_text_by_paths(existing_payload, payload, paths=["procedimento_bloqueio", "bloqueio_etiquetagem", "loto"])
    report_code = _pick_text_by_paths(existing_payload, payload, paths=["relatorio_codigo", "identificacao.relatorio_codigo", "numero_relatorio"])
    report_number = _pick_text_by_paths(existing_payload, payload, paths=["numero_laudo", "identificacao.numero_laudo", "informacoes_gerais.numero_laudo"])
    report_date = _pick_text_by_paths(existing_payload, payload, paths=["data_laudo", "identificacao.data_laudo", "informacoes_gerais.data_laudo"])
    inspection_month = _pick_text_by_paths(
        existing_payload, payload, paths=["mes_inspecao", "identificacao.mes_inspecao", "informacoes_gerais.mes_inspecao"]
    )
    contractor_name = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["contratante", "identificacao.contratante", "informacoes_gerais.contratante"],
    )
    executor_name = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["executante", "identificacao.executante", "informacoes_gerais.executante", "contratada"],
    )
    responsible_engineer = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["responsavel_tecnico", "identificacao.responsavel_tecnico", "informacoes_gerais.responsavel_tecnico", "engenheiro_responsavel"],
    )
    inspector_name = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["inspetor", "identificacao.inspetor", "informacoes_gerais.inspetor", "inspetor_lider"],
    )
    machine_function = _pick_text_by_paths(existing_payload, payload, paths=["funcao_equipamento", "identificacao.funcao_equipamento", "funcao"])
    manufacturer_text = _pick_text_by_paths(existing_payload, payload, paths=["fabricante", "identificacao.fabricante"])
    serial_text = _pick_text_by_paths(existing_payload, payload, paths=["numero_serie", "identificacao.numero_serie", "serial_equipamento"])
    model_text = _pick_text_by_paths(existing_payload, payload, paths=["modelo", "identificacao.modelo"])
    tag_text = _pick_text_by_paths(existing_payload, payload, paths=["tag", "identificacao.tag", "tag_patrimonial"])
    voltage_text = _pick_text_by_paths(existing_payload, payload, paths=["voltagem", "identificacao.voltagem"])
    command_text = _pick_text_by_paths(existing_payload, payload, paths=["comando", "identificacao.comando"])
    operators_text = _pick_text_by_paths(
        existing_payload, payload, paths=["operadores_por_turno", "identificacao.operadores_por_turno", "numero_operadores_turno"]
    )
    art_number = _pick_text_by_paths(existing_payload, payload, paths=["art_numero", "identificacao.art_numero", "informacoes_gerais.art_numero", "art"])
    objective_text = _pick_text_by_paths(existing_payload, payload, paths=["objetivo", "objetivo_inspecao", "objetivo_e_base_normativa.objetivo"])
    normative_base = _pick_text_by_paths(
        existing_payload, payload, paths=["normas_aplicaveis", "objetivo_e_base_normativa.normas_aplicaveis", "base_normativa"]
    )
    generalities_text = _pick_text_by_paths(
        existing_payload, payload, paths=["generalidades", "objetivo_e_base_normativa.generalidades", "premissas"]
    )
    scope_description = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["objeto_inspecao.descricao_escopo", "descricao_escopo", "escopo_inspecao", "resumo_escopo"],
        ),
        scope_summary,
    )
    machine_category = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["objeto_inspecao.categoria_maquina", "categoria_maquina", "tipo_maquina"]),
        _humanize_nr12_asset_type(asset_type, object_hint, title_hint),
    )
    process_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["objeto_inspecao.processo_associado", "processo_associado"]),
        machine_function,
    )
    methodology_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["metodologia_e_criterios.metodologia", "metodologia", "metodologia_inspecao"]),
        method_text,
    )
    checklist_reference = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["metodologia_e_criterios.checklist_referencia", "checklist_referencia"]),
        checklist_text,
    )
    risk_criteria = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["metodologia_e_criterios.criterios_risco", "criterios_risco"]),
        "Grafico de Risco NBR 14153 e classificacao HRN por grupo" if risk_analysis_text else None,
    )
    risk_graph = _pick_text_by_paths(
        existing_payload, payload, paths=["analise_risco.grafico_risco_categoria", "grafico_risco_categoria", "categoria_grafico_risco"]
    )
    risk_before = _pick_text_by_paths(
        existing_payload, payload, paths=["analise_risco.grau_risco_antes", "grau_risco_antes", "risco_antes"]
    )
    risk_after = _pick_text_by_paths(
        existing_payload, payload, paths=["analise_risco.grau_risco_apos", "grau_risco_apos", "risco_apos"]
    )
    risk_summary = _pick_text_by_paths(existing_payload, payload, paths=["analise_risco.resumo_risco", "resumo_risco"])
    document_base_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.documento_base.referencias_texto", "documento_base"]),
        manual_text,
        inventory_text,
        checklist_text,
        risk_analysis_text,
        procedure_text,
    )
    document_summary = _build_labeled_summary(
        ("Manual", manual_text),
        ("Inventario", inventory_text),
        ("Checklist NR12", checklist_text),
        ("Apreciacao de risco", risk_analysis_text),
        ("Procedimento LOTO", procedure_text),
    )
    document_notes = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["documentacao_e_registros.observacoes_documentais", "observacoes_documentais"]),
        document_summary,
    )

    explicit_attention = _pick_value_by_paths(
        existing_payload,
        payload,
        paths=[
            "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
            "ha_pontos_de_atencao",
            "nao_conformidades.ha_nao_conformidades",
            "ha_nao_conformidades",
            "possui_nao_conformidades",
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
                "nao_conformidades",
                "pontos_de_atencao",
                "falhas_de_seguranca",
                "desvios_nr12",
            ],
        ),
        recommendation_hint,
        summary_hint,
    )
    has_attention_points = _infer_nonconformity_flag(explicit_attention, attention_description, recommendation_hint)
    if has_attention_points is None:
        machine_signal_text = _normalize_signal_text(
            _build_labeled_summary(
                ("Pontos", attention_description),
                ("Protecoes", guards_text),
                ("Parada", emergency_stop_text),
                ("Intertravamentos", interlocks_text),
                ("Zona", risk_zone_text),
                ("Enclausuramento", enclosure_text),
            )
        )
        if any(
            pattern in machine_signal_text
            for pattern in (
                "inoper",
                "falha",
                "sem prote",
                "sem guarda",
                "ausencia de prote",
                "ausencia de guarda",
                "nao atua",
                "nao bloque",
                "acesso perig",
                "zona de risco expost",
                "sem enclausur",
                "intertravamento ausente",
                "intertravamento inoperante",
                "parada de emergencia inoperante",
            )
        ):
            has_attention_points = True
        elif any(
            pattern in machine_signal_text
            for pattern in (
                "sem anomalia",
                "sem desvio",
                "sem ponto de atencao",
                "sem risco",
                "protecao integra",
                "intertravamento funcional",
                "parada de emergencia funcional",
            )
        ):
            has_attention_points = False
    attention_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["nao_conformidades_ou_lacunas.evidencias.referencias_texto", "evidencia_ponto_atencao", "evidencia_nao_conformidade"],
        ),
        primary_evidence_text,
    )
    recommendation_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["recomendacoes.texto", "recomendacoes", "observacoes", "observacoes_finais"]),
        recommendation_hint,
    )
    final_statement = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["conclusao.parecer_final", "parecer_final"]),
        (
            "Necessita adequacao NR12 antes do fechamento definitivo."
            if has_attention_points
            else "Escopo inspecionado sem desvios criticos para o pacote emitido."
        ),
    )
    conclusion_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["conclusao.conclusao_tecnica", "parecer_tecnico", "parecer_conclusivo"]),
        summary_hint,
    )
    justification_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["conclusao.justificativa", "justificativa_conclusao"]),
        _build_labeled_summary(("Risco antes", risk_before), ("Pontos de atencao", attention_description)),
    )
    next_action_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["conclusao.proxima_acao", "proxima_acao"]),
        recommendation_text,
    )

    _set_path_if_blank(payload, "identificacao.objeto_principal", object_hint)
    _set_path_if_blank(payload, "identificacao.localizacao", nr12_location_hint)
    _set_path_if_blank(payload, "identificacao.unidade_operacional", unit_name)
    _set_path_if_blank(payload, "identificacao.local_documento", _pick_first_text(local_document, nr12_location_hint))
    _set_path_if_blank(payload, "identificacao.codigo_interno", internal_code)
    _set_path_if_blank(payload, "identificacao.relatorio_codigo", report_code)
    _set_path_if_blank(payload, "identificacao.numero_laudo", report_number)
    _set_path_if_blank(payload, "identificacao.data_laudo", report_date)
    _set_path_if_blank(payload, "identificacao.mes_inspecao", inspection_month)
    _set_path_if_blank(payload, "identificacao.tipo_inspecao", inspection_type)
    _set_path_if_blank(payload, "identificacao.contratante", contractor_name)
    _set_path_if_blank(payload, "identificacao.executante", executor_name)
    _set_path_if_blank(payload, "identificacao.responsavel_tecnico", responsible_engineer)
    _set_path_if_blank(payload, "identificacao.inspetor", inspector_name)
    _set_path_if_blank(payload, "identificacao.funcao_equipamento", machine_function)
    _set_path_if_blank(payload, "identificacao.fabricante", manufacturer_text)
    _set_path_if_blank(payload, "identificacao.numero_serie", serial_text)
    _set_path_if_blank(payload, "identificacao.modelo", model_text)
    _set_path_if_blank(payload, "identificacao.tag", tag_text)
    _set_path_if_blank(payload, "identificacao.voltagem", voltage_text)
    _set_path_if_blank(payload, "identificacao.comando", command_text)
    _set_path_if_blank(payload, "identificacao.operadores_por_turno", operators_text)
    _set_path_if_blank(payload, "identificacao.art_numero", art_number)
    _set_block_fields_if_blank(
        payload,
        block_path="identificacao.referencia_principal",
        description=main_reference_desc,
        references_text=main_reference_text,
        observation=main_reference_obs,
        available=bool(main_reference_desc or main_reference_text or main_reference_obs),
    )

    _set_path_if_blank(payload, "case_context.local_documento", _pick_first_text(local_document, nr12_location_hint))
    _set_path_if_blank(payload, "case_context.tipo_inspecao", inspection_type)
    _set_path_if_blank(payload, "objetivo_e_base_normativa.objetivo", objective_text)
    _set_path_if_blank(payload, "objetivo_e_base_normativa.normas_aplicaveis", normative_base)
    _set_path_if_blank(payload, "objetivo_e_base_normativa.generalidades", generalities_text)
    _set_path_if_blank(payload, "objeto_inspecao.descricao_escopo", scope_description)
    _set_path_if_blank(payload, "objeto_inspecao.categoria_maquina", machine_category)
    _set_path_if_blank(payload, "objeto_inspecao.processo_associado", process_text)
    _set_path_if_blank(payload, "escopo_servico.tipo_entrega", delivery_type)
    _set_path_if_blank(payload, "escopo_servico.modo_execucao", execution_mode)
    _set_path_if_blank(payload, "escopo_servico.ativo_tipo", asset_type)
    _set_path_if_blank(payload, "escopo_servico.resumo_escopo", scope_summary)

    _set_path_if_blank(payload, "execucao_servico.metodo_aplicado", method_text)
    _set_path_if_blank(payload, "execucao_servico.condicoes_observadas", observed_conditions)
    _set_path_if_blank(payload, "execucao_servico.parametros_relevantes", relevant_parameters)
    _set_path_if_blank(payload, "metodologia_e_criterios.metodologia", methodology_text)
    _set_path_if_blank(payload, "metodologia_e_criterios.checklist_referencia", checklist_reference)
    _set_path_if_blank(payload, "metodologia_e_criterios.criterios_risco", risk_criteria)
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
        description="Documento base principal considerado para a avaliacao NR12." if document_base_text else None,
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
    _set_path_if_blank(payload, "documentacao_e_registros.manual_maquina", manual_text)
    _set_path_if_blank(payload, "documentacao_e_registros.inventario_nr12", inventory_text)
    _set_path_if_blank(payload, "documentacao_e_registros.checklist_nr12", checklist_text)
    _set_path_if_blank(payload, "documentacao_e_registros.apreciacao_risco", risk_analysis_text)
    _set_path_if_blank(payload, "documentacao_e_registros.procedimento_loto", procedure_text)
    _set_path_if_blank(payload, "documentacao_e_registros.observacoes_documentais", document_notes)
    _set_path_if_blank(payload, "analise_risco.grafico_risco_categoria", risk_graph)
    _set_path_if_blank(payload, "analise_risco.grau_risco_antes", risk_before)
    _set_path_if_blank(payload, "analise_risco.grau_risco_apos", risk_after)
    _set_path_if_blank(payload, "analise_risco.resumo_risco", risk_summary)

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
    _set_path_if_blank(payload, "recomendacoes.texto", recommendation_text)
    _set_path_if_blank(
        payload,
        "conclusao.status",
        _resolve_conclusion_status(getattr(laudo, "status_revisao", None), has_nonconformity=has_attention_points),
    )
    _set_path_if_blank(
        payload,
        "conclusao.status_operacional",
        _resolve_nr12_operational_status(
            _resolve_conclusion_status(getattr(laudo, "status_revisao", None), has_nonconformity=has_attention_points),
            final_statement,
            attention_description,
        ),
    )
    _set_path_if_blank(payload, "conclusao.parecer_final", final_statement)
    _set_path_if_blank(payload, "conclusao.conclusao_tecnica", conclusion_text)
    _set_path_if_blank(payload, "conclusao.justificativa", justification_text)
    _set_path_if_blank(payload, "conclusao.proxima_acao", next_action_text)

    _set_path_if_blank(
        payload,
        "checklist_componentes.protecao_fixa_e_movel.condicao",
        _normalize_nr12_component_condition(guards_text, risk_zone_text, attention_description),
    )
    _set_path_if_blank(payload, "checklist_componentes.protecao_fixa_e_movel.observacao", guards_text)
    _set_path_if_blank(
        payload,
        "checklist_componentes.comandos_e_intertravamentos.condicao",
        _normalize_nr12_component_condition(interlocks_text, guards_text),
    )
    _set_path_if_blank(
        payload,
        "checklist_componentes.comandos_e_intertravamentos.observacao",
        _pick_first_text(interlocks_text, guards_text),
    )
    _set_path_if_blank(
        payload,
        "checklist_componentes.parada_de_emergencia.condicao",
        _normalize_nr12_component_condition(emergency_stop_text),
    )
    _set_path_if_blank(payload, "checklist_componentes.parada_de_emergencia.observacao", emergency_stop_text)
    _set_path_if_blank(
        payload,
        "checklist_componentes.sinalizacao_e_identificacao.condicao",
        _normalize_nr12_component_condition(signage_text, attention_description),
    )
    _set_path_if_blank(
        payload,
        "checklist_componentes.sinalizacao_e_identificacao.observacao",
        _pick_first_text(signage_text, recommendation_text),
    )
    _set_path_if_blank(
        payload,
        "checklist_componentes.zona_de_risco_e_acesso.condicao",
        _normalize_nr12_component_condition(risk_zone_text, guards_text),
    )
    _set_path_if_blank(payload, "checklist_componentes.zona_de_risco_e_acesso.observacao", risk_zone_text)

    checklist_group_specs = (
        (
            "arranjos_fisicos_instalacoes",
            [
                "grupos_checklist.arranjos_fisicos_instalacoes.status",
                "checklist_grupos.arranjos_fisicos_instalacoes.status",
            ],
            [
                "grupos_checklist.arranjos_fisicos_instalacoes.comentarios",
                "grupos_checklist.arranjos_fisicos_instalacoes.observacoes",
                "checklist_grupos.arranjos_fisicos_instalacoes.comentarios",
            ],
            [
                "grupos_checklist.arranjos_fisicos_instalacoes.risco_nivel",
                "checklist_grupos.arranjos_fisicos_instalacoes.risco_nivel",
            ],
        ),
        (
            "instalacoes_eletricas_partida_parada",
            [
                "grupos_checklist.instalacoes_eletricas_partida_parada.status",
                "checklist_grupos.instalacoes_eletricas_partida_parada.status",
            ],
            [
                "grupos_checklist.instalacoes_eletricas_partida_parada.comentarios",
                "grupos_checklist.instalacoes_eletricas_partida_parada.observacoes",
                "checklist_grupos.instalacoes_eletricas_partida_parada.comentarios",
            ],
            [
                "grupos_checklist.instalacoes_eletricas_partida_parada.risco_nivel",
                "checklist_grupos.instalacoes_eletricas_partida_parada.risco_nivel",
            ],
        ),
        (
            "sistemas_seguranca_transportadores",
            [
                "grupos_checklist.sistemas_seguranca_transportadores.status",
                "checklist_grupos.sistemas_seguranca_transportadores.status",
            ],
            [
                "grupos_checklist.sistemas_seguranca_transportadores.comentarios",
                "grupos_checklist.sistemas_seguranca_transportadores.observacoes",
                "checklist_grupos.sistemas_seguranca_transportadores.comentarios",
            ],
            [
                "grupos_checklist.sistemas_seguranca_transportadores.risco_nivel",
                "checklist_grupos.sistemas_seguranca_transportadores.risco_nivel",
            ],
        ),
        (
            "aspectos_ergonomicos",
            [
                "grupos_checklist.aspectos_ergonomicos.status",
                "checklist_grupos.aspectos_ergonomicos.status",
            ],
            [
                "grupos_checklist.aspectos_ergonomicos.comentarios",
                "grupos_checklist.aspectos_ergonomicos.observacoes",
                "checklist_grupos.aspectos_ergonomicos.comentarios",
            ],
            [
                "grupos_checklist.aspectos_ergonomicos.risco_nivel",
                "checklist_grupos.aspectos_ergonomicos.risco_nivel",
            ],
        ),
        (
            "riscos_adicionais_manutencao_sinalizacao",
            [
                "grupos_checklist.riscos_adicionais_manutencao_sinalizacao.status",
                "checklist_grupos.riscos_adicionais_manutencao_sinalizacao.status",
            ],
            [
                "grupos_checklist.riscos_adicionais_manutencao_sinalizacao.comentarios",
                "grupos_checklist.riscos_adicionais_manutencao_sinalizacao.observacoes",
                "checklist_grupos.riscos_adicionais_manutencao_sinalizacao.comentarios",
            ],
            [
                "grupos_checklist.riscos_adicionais_manutencao_sinalizacao.risco_nivel",
                "checklist_grupos.riscos_adicionais_manutencao_sinalizacao.risco_nivel",
            ],
        ),
        (
            "manuais_procedimentos_capacitacao",
            [
                "grupos_checklist.manuais_procedimentos_capacitacao.status",
                "checklist_grupos.manuais_procedimentos_capacitacao.status",
            ],
            [
                "grupos_checklist.manuais_procedimentos_capacitacao.comentarios",
                "grupos_checklist.manuais_procedimentos_capacitacao.observacoes",
                "checklist_grupos.manuais_procedimentos_capacitacao.comentarios",
            ],
            [
                "grupos_checklist.manuais_procedimentos_capacitacao.risco_nivel",
                "checklist_grupos.manuais_procedimentos_capacitacao.risco_nivel",
            ],
        ),
    )
    for group_key, status_paths, comment_paths, risk_paths in checklist_group_specs:
        _set_path_if_blank(payload, f"checklist_grupos.{group_key}.status", _pick_text_by_paths(existing_payload, payload, paths=status_paths))
        _set_path_if_blank(
            payload,
            f"checklist_grupos.{group_key}.comentarios",
            _pick_text_by_paths(existing_payload, payload, paths=comment_paths),
        )
        _set_path_if_blank(payload, f"checklist_grupos.{group_key}.risco_nivel", _pick_text_by_paths(existing_payload, payload, paths=risk_paths))


def apply_nr12_risk_projection(
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
    if family_key != "nr12_apreciacao_risco_maquina":
        return

    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.objeto_principal",
                "objeto_principal",
                "nome_equipamento",
                "equipamento",
                "maquina",
                "maquina_principal",
                "objeto_inspecao.identificacao",
                "prensa",
                "ponte_rolante",
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
            "codigo_tag",
            "tag",
            "asset_tag",
            "patrimonio",
            "serial_equipamento",
            "numero_maquina",
        ],
    )
    main_reference_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "identificacao.referencia_principal.referencias_texto",
            "referencia_principal",
            "referencia_principal_ref",
            "foto_maquina",
            "foto_equipamento",
            "croqui",
            "fluxograma",
        ],
    )
    main_reference_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.referencia_principal.descricao", "descricao_referencia_principal", "referencia_principal_descricao"],
        ),
        object_hint,
    )
    main_reference_obs = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.referencia_principal.observacao", "observacao_referencia_principal"],
    )

    delivery_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.tipo_entrega", "tipo_entrega", "modalidade_laudo"]),
        _value_by_path(payload, "case_context.modalidade_laudo"),
    )
    execution_mode = _pick_first_text(
        _normalize_execution_mode(
            _pick_value_by_paths(existing_payload, payload, paths=["escopo_servico.modo_execucao", "modo_execucao", "tipo_execucao", "modalidade_execucao"])
        ),
        "analise_e_modelagem",
    )
    asset_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.ativo_tipo", "ativo_tipo", "tipo_ativo", "tipo_maquina", "objeto_tipo"]),
        _infer_nr12_asset_type(object_hint, internal_code, title_hint),
    )
    scope_summary = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.resumo_escopo", "resumo_escopo", "resumo_servico", "escopo"]),
        summary_hint,
    )

    danger_text = _pick_text_by_paths(existing_payload, payload, paths=["perigo_identificado", "perigo", "descricao_perigo"])
    risk_zone_text = _pick_text_by_paths(existing_payload, payload, paths=["zona_risco", "acessos_perigosos", "ponto_perigoso"])
    risk_category_text = _pick_text_by_paths(existing_payload, payload, paths=["categoria_risco", "classificacao_risco", "nivel_risco"])
    severity_text = _pick_text_by_paths(existing_payload, payload, paths=["severidade", "grau_severidade"])
    probability_text = _pick_text_by_paths(existing_payload, payload, paths=["probabilidade", "ocorrencia", "frequencia"])
    existing_controls_text = _pick_text_by_paths(
        existing_payload, payload, paths=["medidas_existentes", "controles_existentes", "guardas_protecoes", "intertravamentos", "parada_emergencia"]
    )
    recommended_action_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["medidas_recomendadas", "acao_recomendada", "recomendacoes.texto", "proxima_acao", "observacoes"],
        ),
        recommendation_hint,
    )

    method_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.metodo_aplicado",
                "metodo_aplicado",
                "metodo_analise",
                "metodo_inspecao",
                "analise_risco_metodo",
                "matriz_metodo",
            ],
        ),
        "Apreciacao de risco com levantamento de perigos, matriz de risco e referencias NR12.",
    )
    observed_conditions = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.condicoes_observadas",
                "condicoes_observadas",
                "condicoes_gerais",
                "condicao_geral",
                "cenario_operacional",
                "parecer_preliminar",
            ],
        ),
        summary_hint,
    )
    relevant_parameters = _build_labeled_summary(
        ("Perigo", danger_text),
        ("Zona de risco", risk_zone_text),
        ("Categoria", risk_category_text),
        ("Severidade", severity_text),
        ("Probabilidade", probability_text),
        ("Controles existentes", existing_controls_text),
    )

    risk_assessment_doc = _pick_text_by_paths(existing_payload, payload, paths=["apreciacao_risco", "analise_risco", "matriz_risco"])
    checklist_text = _pick_text_by_paths(existing_payload, payload, paths=["checklist_nr12", "checklist_inspecao", "checklist"])
    manual_text = _pick_text_by_paths(existing_payload, payload, paths=["manual_maquina", "manual_equipamento", "manual"])
    inventory_text = _pick_text_by_paths(existing_payload, payload, paths=["inventario_maquinas", "inventario_nr12", "inventario"])

    execution_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.evidencia_execucao.referencias_texto",
                "evidencia_execucao",
                "registro_execucao",
                "apreciacao_risco",
                "analise_risco",
                "matriz_risco",
            ],
        ),
        risk_assessment_doc,
        main_reference_text,
    )
    execution_evidence_desc = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.evidencia_execucao.descricao", "descricao_evidencia_execucao"]),
        observed_conditions,
    )
    primary_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["evidencias_e_anexos.evidencia_principal.referencias_texto", "evidencia_principal", "foto_principal", "registro_principal"],
        ),
        risk_assessment_doc,
        execution_evidence_text,
    )
    primary_evidence_desc = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.evidencia_principal.descricao", "descricao_evidencia_principal"]),
        observed_conditions,
    )
    complementary_evidence_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "evidencias_e_anexos.evidencia_complementar.referencias_texto",
            "evidencia_complementar",
            "evidencias_complementares",
            "foto_complementar",
            "croqui",
            "fluxograma",
        ],
    )
    complementary_evidence_desc = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["evidencias_e_anexos.evidencia_complementar.descricao", "descricao_evidencia_complementar"],
    )

    document_base_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.documento_base.referencias_texto", "documento_base"]),
        risk_assessment_doc,
        checklist_text,
        manual_text,
        inventory_text,
    )
    document_summary = _build_labeled_summary(
        ("Apreciacao de risco", risk_assessment_doc),
        ("Checklist NR12", checklist_text),
        ("Manual", manual_text),
        ("Inventario", inventory_text),
    )
    document_notes = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["documentacao_e_registros.observacoes_documentais", "observacoes_documentais"]),
        document_summary,
    )

    explicit_attention = _pick_value_by_paths(
        existing_payload,
        payload,
        paths=[
            "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
            "ha_pontos_de_atencao",
            "nao_conformidades.ha_nao_conformidades",
            "ha_nao_conformidades",
            "possui_nao_conformidades",
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
                "nao_conformidades",
                "pontos_de_atencao",
                "perigo_identificado",
                "zona_risco",
            ],
        ),
        recommendation_hint,
        summary_hint,
    )
    has_attention_points = _infer_nonconformity_flag(explicit_attention, attention_description, recommendation_hint)
    if has_attention_points is None:
        risk_signal_text = _normalize_signal_text(
            _build_labeled_summary(
                ("Descricao", attention_description),
                ("Categoria", risk_category_text),
                ("Severidade", severity_text),
                ("Probabilidade", probability_text),
                ("Perigo", danger_text),
                ("Zona", risk_zone_text),
            )
        )
        if any(
            pattern in risk_signal_text
            for pattern in (
                "alto",
                "critico",
                "grave",
                "nao aceit",
                "inaceit",
                "aprision",
                "esmag",
                "corte",
                "acesso perig",
                "zona de risco",
                "sem prote",
                "exposicao",
            )
        ):
            has_attention_points = True
        elif any(
            pattern in risk_signal_text
            for pattern in (
                "baixo",
                "aceitavel",
                "controlado",
                "sem ponto de atencao",
                "sem desvio",
                "sem risco relevante",
            )
        ):
            has_attention_points = False
    attention_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["nao_conformidades_ou_lacunas.evidencias.referencias_texto", "evidencia_ponto_atencao", "evidencia_nao_conformidade"],
        ),
        primary_evidence_text,
    )

    _set_path_if_blank(payload, "identificacao.objeto_principal", object_hint)
    _set_path_if_blank(payload, "identificacao.localizacao", location_hint)
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
        description="Documento base principal considerado para a apreciacao de risco NR12." if document_base_text else None,
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

    risk_matrix_primary_item = {
        "perigo": danger_text,
        "cenario": risk_zone_text,
        "categoria": risk_category_text,
        "severidade": severity_text,
        "probabilidade": probability_text,
        "controle": existing_controls_text,
        "medida_existente": existing_controls_text,
        "acao_recomendada": recommended_action_text,
    }
    if any(value not in (None, "") for value in risk_matrix_primary_item.values()):
        _set_path_if_blank(payload, "analise_de_risco", [risk_matrix_primary_item])
        document_projection = payload.get("document_projection")
        if isinstance(document_projection, dict):
            existing_risk_primary = document_projection.get("risk_primary")
            if not isinstance(existing_risk_primary, dict) or not any(value not in (None, "") for value in existing_risk_primary.values()):
                document_projection["risk_primary"] = dict(risk_matrix_primary_item)

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
    _set_path_if_blank(payload, "recomendacoes.texto", recommended_action_text)
    _set_path_if_blank(
        payload,
        "conclusao.status",
        _resolve_conclusion_status(getattr(laudo, "status_revisao", None), has_nonconformity=has_attention_points),
    )


__all__ = ["apply_nr12_projection", "apply_nr12_risk_projection"]
