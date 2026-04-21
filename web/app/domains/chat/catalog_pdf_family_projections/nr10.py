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


def _infer_nr10_asset_type(*values: Any) -> str | None:
    joined = " ".join(str(value or "").strip() for value in values if str(value or "").strip())
    text = _normalize_signal_text(joined)
    if "subest" in text:
        return "subestacao"
    if "cabine" in text:
        return "cabine_eletrica"
    if "painel" in text:
        return "painel_eletrico"
    if "qgbt" in text or "quadro" in text:
        return "quadro_eletrico"
    if "circuit" in text:
        return "circuito_eletrico"
    if "aterr" in text:
        return "sistema_aterramento"
    return "instalacoes_eletricas" if text else None


def _resolve_nr10_documental_conclusion_status(
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


def _resolve_nr10_check_condition(*values: Any, default: str | None = None) -> str | None:
    for value in values:
        if isinstance(value, bool):
            return "conforme" if value else "ajuste"
        text = _normalize_signal_text(value)
        if not text:
            continue
        if any(
            token in text
            for token in (
                "nao identificado",
                "nao aplicada",
                "nao aplicado",
                "nao dispon",
                "nao apresentado",
                "ausent",
                "pendenc",
                "ajuste",
                "reaperto",
                "incomplet",
                "correc",
                "falha",
                "diverg",
                "restric",
            )
        ):
            return "ajuste"
        if any(
            token in text
            for token in (
                "conforme",
                "adequad",
                "confirm",
                "verificad",
                "integr",
                "preservad",
                "aplicad",
                "bloquead",
                "etiquet",
                "energia zero",
                "condicao segura",
                "disponivel",
                "acessivel",
            )
        ):
            return "conforme"
    return default


def _set_nr10_check_item(
    payload: dict[str, Any],
    *,
    item_key: str,
    condition: str | None,
    observation: str | None,
) -> None:
    _set_path_if_blank(payload, f"checklist_componentes.{item_key}.condicao", condition)
    _set_path_if_blank(payload, f"checklist_componentes.{item_key}.observacao", observation)


def apply_nr10_projection(
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
    if family_key != "nr10_inspecao_instalacoes_eletricas":
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
                "objeto_inspecao.identificacao",
                "painel_principal",
                "painel",
                "quadro_principal_nome",
                "quadro_principal",
                "cabine_eletrica",
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
            "painel_tag",
            "quadro_tag",
        ],
    )
    main_reference_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "identificacao.referencia_principal.referencias_texto",
            "referencia_principal",
            "referencia_principal_ref",
            "foto_referencia_principal",
            "foto_painel_principal",
            "foto_quadro_principal",
            "quadro_principal_ref",
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
        paths=[
            "identificacao.referencia_principal.observacao",
            "observacao_referencia_principal",
        ],
    )
    delivery_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "escopo_servico.tipo_entrega",
                "tipo_entrega",
                "modalidade_laudo",
            ],
        ),
        _value_by_path(payload, "case_context.modalidade_laudo"),
    )
    execution_mode = _normalize_execution_mode(
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
    asset_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "escopo_servico.ativo_tipo",
                "ativo_tipo",
                "tipo_ativo",
                "tipo_instalacao",
                "objeto_tipo",
            ],
        ),
        _infer_nr10_asset_type(object_hint, internal_code, title_hint),
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
        summary_hint,
    )

    method_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "execucao_servico.metodo_aplicado",
            "metodo_aplicado",
            "metodo_inspecao",
            "metodo",
            "roteiro_inspecao",
            "checklist_aplicado",
        ],
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
                "riscos_observados",
                "parecer_preliminar",
            ],
        ),
        summary_hint,
    )
    relevant_parameters = _build_labeled_summary(
        (
            "Quadro principal",
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["quadro_principal", "painel_principal", "quadro", "painel"],
            ),
        ),
        (
            "Circuitos criticos",
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["circuitos_criticos", "circuitos_prioritarios"],
            ),
        ),
        ("Aterramento", _pick_text_by_paths(existing_payload, payload, paths=["aterramento", "sistema_aterramento"])),
        (
            "Protecao",
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["protecao_eletrica", "dispositivos_protecao", "protecao"],
            ),
        ),
        ("Termografia", _pick_text_by_paths(existing_payload, payload, paths=["termografia", "resultado_termografia"])),
    )

    execution_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.evidencia_execucao.referencias_texto",
                "evidencia_execucao",
                "registro_execucao",
                "registro_termografico",
                "foto_execucao",
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
        observed_conditions,
    )
    primary_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "evidencias_e_anexos.evidencia_principal.referencias_texto",
                "evidencia_principal",
                "foto_principal",
                "registro_principal",
            ],
        ),
        execution_evidence_text,
    )
    primary_evidence_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["evidencias_e_anexos.evidencia_principal.descricao", "descricao_evidencia_principal"],
        ),
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
        ],
    )
    complementary_evidence_desc = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["evidencias_e_anexos.evidencia_complementar.descricao", "descricao_evidencia_complementar"],
    )

    pie_text = _pick_text_by_paths(existing_payload, payload, paths=["pie", "prontuario_instalacoes", "prontuario_eletrico"])
    prontuario_text = _pick_text_by_paths(existing_payload, payload, paths=["prontuario", "documentacao_base.prontuario"])
    diagram_text = _pick_text_by_paths(existing_payload, payload, paths=["diagrama_unifilar", "diagrama_eletrico", "documentacao_base.diagrama"])
    rti_text = _pick_text_by_paths(existing_payload, payload, paths=["rti", "relatorio_termografico"])
    relatorio_text = _pick_text_by_paths(existing_payload, payload, paths=["relatorio_anterior", "historico_relatorio"])
    document_base_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.documento_base.referencias_texto", "documento_base"]),
        pie_text,
        prontuario_text,
        diagram_text,
        rti_text,
        relatorio_text,
    )
    document_summary = _build_labeled_summary(
        ("PIE", pie_text),
        ("Prontuario", prontuario_text),
        ("Diagrama", diagram_text),
        ("RTI", rti_text),
        ("Relatorio anterior", relatorio_text),
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
                "anomalias",
                "riscos_observados",
            ],
        ),
        recommendation_hint,
        summary_hint,
    )
    has_attention_points = _infer_nonconformity_flag(explicit_attention, attention_description, recommendation_hint)
    if has_attention_points is None and attention_description:
        has_attention_points = True
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
        description="Documento base principal considerado para a avaliacao NR10." if document_base_text else None,
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
        _resolve_conclusion_status(getattr(laudo, "status_revisao", None), has_nonconformity=has_attention_points),
    )


def apply_nr10_loto_projection(
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
    if family_key != "nr10_implantacao_loto":
        return

    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.objeto_principal",
                "objeto_principal",
                "ativo_principal",
                "equipamento",
                "maquina",
                "frente_trabalho",
                "painel_principal",
                "objeto_inspecao.identificacao",
            ],
        ),
        title_hint,
        getattr(laudo, "primeira_mensagem", None),
    )
    nr10_location_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.localizacao", "local_inspecao", "localizacao", "setor", "unidade", "area"],
        ),
        location_hint,
    )
    internal_code = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.codigo_interno", "codigo_interno", "tag_patrimonial", "codigo_tag", "tag"],
    )
    main_reference_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.referencia_principal.referencias_texto",
                "referencia_principal",
                "foto_principal",
                "documento_base",
                "procedimento_loto",
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
        "Ativo, frente ou painel ancorado ao procedimento LOTO aplicado." if main_reference_text else None,
        object_hint,
    )
    main_reference_obs = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.referencia_principal.observacao", "observacao_referencia_principal"],
        ),
        "Rastreabilidade entre ativo, procedimento e evidencia principal preservada." if main_reference_text else None,
    )
    delivery_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.tipo_entrega", "tipo_entrega", "modalidade_laudo"],
        ),
        _value_by_path(payload, "case_context.modalidade_laudo"),
        "implantacao_loto",
    )
    execution_mode = _normalize_execution_mode(
        _pick_value_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.modo_execucao", "modo_execucao", "tipo_execucao", "modalidade_execucao"],
        )
    )
    if execution_mode in {None, "documental"}:
        execution_mode = "in_loco"
    asset_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.ativo_tipo", "ativo_tipo", "tipo_ativo", "tipo_instalacao", "objeto_tipo"],
        ),
        _infer_nr10_asset_type(object_hint, internal_code, title_hint),
        "sistema_bloqueio_energias",
    )
    scope_summary = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.resumo_escopo", "resumo_escopo", "resumo_servico", "escopo"],
        ),
        summary_hint,
    )

    energy_sources = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "procedimentos_de_controle.fontes_de_energia",
            "fontes_de_energia",
            "fontes_energia",
            "matriz_energias",
            "energias_perigosas",
        ],
    )
    lock_points = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "procedimentos_de_controle.pontos_de_bloqueio",
            "pontos_de_bloqueio",
            "ponto_bloqueio",
            "dispositivos_bloqueio",
        ],
    )
    lock_devices = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "procedimentos_de_controle.dispositivos_e_sinalizacao",
            "dispositivos_e_sinalizacao",
            "sinalizacao",
            "etiquetagem",
            "cadeados",
        ],
    )
    zero_energy = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "procedimentos_de_controle.verificacao_energia_zero",
            "verificacao_energia_zero",
            "teste_partida",
            "condicao_segura",
        ],
    )
    controlled_sequence = _build_labeled_summary(
        (
            "Seccionamento",
            _pick_text_by_paths(existing_payload, payload, paths=["seccionamento", "sequencia_desenergizacao"]),
        ),
        (
            "Impedimento de reenergizacao",
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["impedimento_reenergizacao", "travamento", "bloqueio_religamento"],
            ),
        ),
        (
            "Protecao de elementos energizados",
            _pick_text_by_paths(existing_payload, payload, paths=["protecao_elementos_energizados", "isolacao_partes_vivas"]),
        ),
        (
            "Reenergizacao controlada",
            _pick_text_by_paths(existing_payload, payload, paths=["sequencia_reenergizacao", "liberacao_controlada"]),
        ),
    )

    method_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.metodo_aplicado",
                "metodo_aplicado",
                "metodo_inspecao",
                "procedimento_aplicado",
                "checklist_aplicado",
                "apr",
            ],
        ),
        "Aplicacao da sequencia de desenergizacao, impedimento de reenergizacao, etiquetagem e confirmacao de energia zero conforme NR10.",
    )
    observed_conditions = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.condicoes_observadas",
                "condicoes_observadas",
                "condicoes_gerais",
                "observacoes",
                "status_implantacao",
            ],
        ),
        summary_hint,
    )
    relevant_parameters = _build_labeled_summary(
        ("Fontes de energia", energy_sources),
        ("Pontos de bloqueio", lock_points),
        ("Dispositivos e sinalizacao", lock_devices),
        ("Energia zero", zero_energy),
        ("Sequencia controlada", controlled_sequence),
    )
    execution_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.evidencia_execucao.referencias_texto",
                "evidencia_execucao",
                "registro_execucao",
                "cadeado_principal",
                "etiqueta_principal",
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
        observed_conditions,
    )
    primary_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "evidencias_e_anexos.evidencia_principal.referencias_texto",
                "evidencia_principal",
                "cadeado_principal",
                "foto_bloqueio_principal",
            ],
        ),
        execution_evidence_text,
    )
    primary_evidence_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["evidencias_e_anexos.evidencia_principal.descricao", "descricao_evidencia_principal"],
        ),
        "Registro principal do bloqueio e do impedimento de reenergizacao." if primary_evidence_text else None,
    )
    complementary_evidence_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "evidencias_e_anexos.evidencia_complementar.referencias_texto",
            "evidencia_complementar",
            "evidencias_complementares",
            "foto_complementar",
        ],
    )
    complementary_evidence_desc = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["evidencias_e_anexos.evidencia_complementar.descricao", "descricao_evidencia_complementar"],
    )
    procedure_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "evidencias_e_anexos.documento_base.referencias_texto",
            "documento_base",
            "procedimento_loto",
            "procedimento_base",
        ],
    )
    apr_text = _pick_text_by_paths(existing_payload, payload, paths=["apr", "analise_preliminar_risco"])
    energy_matrix_text = _pick_text_by_paths(existing_payload, payload, paths=["matriz_energias", "lista_energias_perigosas"])
    authorization_text = _pick_text_by_paths(existing_payload, payload, paths=["lista_autorizados", "registro_treinamento"])
    checklist_text = _pick_text_by_paths(existing_payload, payload, paths=["checklist_loto", "checklist_aplicado"])
    document_base_text = _pick_first_text(procedure_text, apr_text, energy_matrix_text, checklist_text, primary_evidence_text)
    document_summary = _build_labeled_summary(
        ("Procedimento", procedure_text),
        ("APR", apr_text),
        ("Matriz de energias", energy_matrix_text),
        ("Checklist", checklist_text),
        ("Autorizacao/Treinamento", authorization_text),
    )
    document_notes = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["documentacao_e_registros.observacoes_documentais", "observacoes_documentais"],
        ),
        recommendation_hint,
        document_summary,
    )

    explicit_attention = _pick_value_by_paths(
        existing_payload,
        payload,
        paths=[
            "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
            "ha_pontos_de_atencao",
            "ha_nao_conformidades",
            "possui_pendencias",
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
                "pendencias",
                "observacoes",
            ],
        ),
        recommendation_hint,
        summary_hint,
    )
    has_attention_points = _infer_nonconformity_flag(explicit_attention, attention_description, recommendation_hint)
    if has_attention_points is None and attention_description:
        has_attention_points = True
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
        primary_evidence_text,
    )
    explicit_conclusion = _pick_text_by_paths(existing_payload, payload, paths=["conclusao.status", "status_conclusao", "status"])

    _set_path_if_blank(payload, "identificacao.objeto_principal", object_hint)
    _set_path_if_blank(payload, "identificacao.localizacao", nr10_location_hint)
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

    _set_nr10_check_item(
        payload,
        item_key="fontes_de_energia",
        condition=_resolve_nr10_check_condition(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.fontes_de_energia.condicao"]),
            energy_sources,
            default="conforme" if energy_sources else None,
        ),
        observation=_pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.fontes_de_energia.observacao"]),
            energy_sources,
        ),
    )
    _set_nr10_check_item(
        payload,
        item_key="pontos_de_bloqueio",
        condition=_resolve_nr10_check_condition(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.pontos_de_bloqueio.condicao"]),
            lock_points,
            default="conforme" if lock_points else None,
        ),
        observation=_pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.pontos_de_bloqueio.observacao"]),
            lock_points,
        ),
    )
    _set_nr10_check_item(
        payload,
        item_key="dispositivos_e_sinalizacao",
        condition=(
            "ajuste"
            if has_attention_points and "sinaliz" in _normalize_signal_text(attention_description)
            else _resolve_nr10_check_condition(
                _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.dispositivos_e_sinalizacao.condicao"]),
                attention_description if has_attention_points else None,
                lock_devices,
                default="conforme" if lock_devices else None,
            )
        ),
        observation=_pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.dispositivos_e_sinalizacao.observacao"]),
            lock_devices,
            attention_description if has_attention_points else None,
        ),
    )
    _set_nr10_check_item(
        payload,
        item_key="verificacao_energia_zero",
        condition=_resolve_nr10_check_condition(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.verificacao_energia_zero.condicao"]),
            zero_energy,
            default="conforme" if zero_energy else None,
        ),
        observation=_pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.verificacao_energia_zero.observacao"]),
            zero_energy,
        ),
    )
    _set_nr10_check_item(
        payload,
        item_key="sequenciamento_e_reenergizacao_controlada",
        condition=_resolve_nr10_check_condition(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["checklist_componentes.sequenciamento_e_reenergizacao_controlada.condicao"],
            ),
            controlled_sequence,
            default="conforme" if controlled_sequence or (lock_points and zero_energy) else None,
        ),
        observation=_pick_first_text(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["checklist_componentes.sequenciamento_e_reenergizacao_controlada.observacao"],
            ),
            controlled_sequence,
        ),
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
        description="Procedimento ou documento base que ancora a sequencia LOTO aplicada." if document_base_text else None,
        references_text=document_base_text,
        observation=document_notes,
        available=bool(document_base_text),
    )

    _set_path_if_blank(payload, "documentacao_e_registros.documentos_disponiveis", document_summary)
    _set_path_if_blank(
        payload,
        "documentacao_e_registros.documentos_emitidos",
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["documentacao_e_registros.documentos_emitidos", "documentos_emitidos", "registro_implantacao"],
        ),
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
        f"Base tecnica LOTO considerada: {document_summary}" if document_summary else None,
    )
    _set_path_if_blank(
        payload,
        "conclusao.status",
        _resolve_nr10_documental_conclusion_status(
            explicit_conclusion,
            review_status=getattr(laudo, "status_revisao", None),
            has_nonconformity=has_attention_points,
        ),
    )


def apply_nr10_spda_projection(
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
    if family_key != "nr10_inspecao_spda":
        return

    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.objeto_principal",
                "objeto_principal",
                "sistema_principal",
                "estrutura_principal",
                "cobertura",
                "spda_principal",
            ],
        ),
        title_hint,
        getattr(laudo, "primeira_mensagem", None),
    )
    nr10_location_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.localizacao", "local_inspecao", "localizacao", "setor", "unidade", "area"],
        ),
        location_hint,
    )
    internal_code = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.codigo_interno", "codigo_interno", "tag_patrimonial", "codigo_tag", "tag"],
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
            paths=[
                "identificacao.referencia_principal.descricao",
                "descricao_referencia_principal",
                "referencia_principal_descricao",
            ],
        ),
        "Frente principal do SPDA, cobertura ou estrutura inspecionada." if main_reference_text else None,
        object_hint,
    )
    main_reference_obs = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.referencia_principal.observacao", "observacao_referencia_principal"],
        ),
        "Rastreabilidade do sistema SPDA preservada pela evidencia principal." if main_reference_text else None,
    )
    delivery_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.tipo_entrega", "tipo_entrega", "modalidade_laudo"],
        ),
        _value_by_path(payload, "case_context.modalidade_laudo"),
        "inspecao_tecnica",
    )
    execution_mode = _normalize_execution_mode(
        _pick_value_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.modo_execucao", "modo_execucao", "tipo_execucao", "modalidade_execucao"],
        )
    )
    if execution_mode in {None, "documental"}:
        execution_mode = "in_loco"
    asset_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.ativo_tipo", "ativo_tipo", "tipo_ativo", "tipo_instalacao", "objeto_tipo"],
        ),
        "spda_edificacao",
    )
    scope_summary = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.resumo_escopo", "resumo_escopo", "resumo_servico", "escopo"],
        ),
        summary_hint,
    )

    captation_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["sistema_spda.captacao", "captacao", "subsistema_captacao"],
    )
    down_conductors_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["sistema_spda.descidas", "descidas", "subsistema_descidas"],
    )
    grounding_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "sistema_spda.aterramento_e_equipotencializacao",
            "aterramento_e_equipotencializacao",
            "aterramento",
            "equipotencializacao",
        ],
    )
    measurement_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "sistema_spda.medicoes_ou_testes",
            "medicoes_ou_testes",
            "medicao_aterramento",
            "laudo_medicao",
            "relatorio_medicao",
        ],
    )

    method_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.metodo_aplicado",
                "metodo_aplicado",
                "metodo_inspecao",
                "procedimento_aplicado",
                "roteiro_vistoria",
            ],
        ),
        "Vistoria do SPDA com leitura de captacao, descidas, aterramento/equipotencializacao e confronto com registros de medicao disponiveis.",
    )
    observed_conditions = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.condicoes_observadas",
                "condicoes_observadas",
                "condicoes_gerais",
                "observacoes",
                "status_sistema",
            ],
        ),
        summary_hint,
    )
    relevant_parameters = _build_labeled_summary(
        ("Captacao", captation_text),
        ("Descidas", down_conductors_text),
        ("Aterramento/equipotencializacao", grounding_text),
        ("Medicoes/testes", measurement_text),
    )
    execution_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.evidencia_execucao.referencias_texto",
                "evidencia_execucao",
                "registro_execucao",
                "foto_descida",
                "foto_barramento",
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
        observed_conditions,
    )
    primary_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "evidencias_e_anexos.evidencia_principal.referencias_texto",
                "evidencia_principal",
                "foto_ponto_atencao",
                "foto_descida",
            ],
        ),
        execution_evidence_text,
    )
    primary_evidence_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["evidencias_e_anexos.evidencia_principal.descricao", "descricao_evidencia_principal"],
        ),
        "Registro principal do ponto mais sensivel identificado no SPDA." if primary_evidence_text else None,
    )
    complementary_evidence_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "evidencias_e_anexos.evidencia_complementar.referencias_texto",
            "evidencia_complementar",
            "evidencias_complementares",
            "foto_complementar",
        ],
    )
    complementary_evidence_desc = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["evidencias_e_anexos.evidencia_complementar.descricao", "descricao_evidencia_complementar"],
    )
    measurement_report_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["laudo_medicao", "medicao_aterramento", "relatorio_medicao", "documento_base"],
    )
    project_text = _pick_text_by_paths(existing_payload, payload, paths=["projeto_spda", "croqui_spda", "croqui_cobertura"])
    history_text = _pick_text_by_paths(existing_payload, payload, paths=["historico_spda", "relatorio_anterior"])
    document_base_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.documento_base.referencias_texto"]),
        measurement_report_text,
        project_text,
        history_text,
        primary_evidence_text,
    )
    document_summary = _build_labeled_summary(
        ("Medicao/relatorio", measurement_report_text),
        ("Projeto/croqui", project_text),
        ("Historico anterior", history_text),
    )
    document_notes = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["documentacao_e_registros.observacoes_documentais", "observacoes_documentais"],
        ),
        recommendation_hint,
        document_summary,
    )

    explicit_attention = _pick_value_by_paths(
        existing_payload,
        payload,
        paths=[
            "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
            "ha_pontos_de_atencao",
            "ha_nao_conformidades",
            "possui_pendencias",
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
                "pendencias",
                "observacoes",
            ],
        ),
        recommendation_hint,
        summary_hint,
    )
    has_attention_points = _infer_nonconformity_flag(explicit_attention, attention_description, recommendation_hint)
    if has_attention_points is None and attention_description:
        has_attention_points = True
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
    explicit_conclusion = _pick_text_by_paths(existing_payload, payload, paths=["conclusao.status", "status_conclusao", "status"])

    _set_path_if_blank(payload, "identificacao.objeto_principal", object_hint)
    _set_path_if_blank(payload, "identificacao.localizacao", nr10_location_hint)
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

    _set_nr10_check_item(
        payload,
        item_key="captacao",
        condition=_resolve_nr10_check_condition(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.captacao.condicao"]),
            captation_text,
            default="conforme" if captation_text else None,
        ),
        observation=_pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.captacao.observacao"]),
            captation_text,
        ),
    )
    _set_nr10_check_item(
        payload,
        item_key="descidas",
        condition=_resolve_nr10_check_condition(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.descidas.condicao"]),
            attention_description if has_attention_points else None,
            down_conductors_text,
            default="conforme" if down_conductors_text else None,
        ),
        observation=_pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.descidas.observacao"]),
            down_conductors_text,
            attention_description if has_attention_points else None,
        ),
    )
    _set_nr10_check_item(
        payload,
        item_key="aterramento_e_equipotencializacao",
        condition=_resolve_nr10_check_condition(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["checklist_componentes.aterramento_e_equipotencializacao.condicao"],
            ),
            grounding_text,
            default="conforme" if grounding_text else None,
        ),
        observation=_pick_first_text(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["checklist_componentes.aterramento_e_equipotencializacao.observacao"],
            ),
            grounding_text,
        ),
    )
    _set_nr10_check_item(
        payload,
        item_key="medicoes_ou_testes",
        condition=_resolve_nr10_check_condition(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.medicoes_ou_testes.condicao"]),
            measurement_text,
            default="conforme" if measurement_text else None,
        ),
        observation=_pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["checklist_componentes.medicoes_ou_testes.observacao"]),
            measurement_text,
        ),
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
        description="Relatorio, medicao ou documento base utilizado para sustentar a inspeção do SPDA." if document_base_text else None,
        references_text=document_base_text,
        observation=document_notes,
        available=bool(document_base_text),
    )

    _set_path_if_blank(payload, "documentacao_e_registros.documentos_disponiveis", document_summary)
    _set_path_if_blank(
        payload,
        "documentacao_e_registros.documentos_emitidos",
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["documentacao_e_registros.documentos_emitidos", "documentos_emitidos", "laudo_emitido"],
        ),
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
        f"Base documental SPDA considerada: {document_summary}" if document_summary else None,
    )
    _set_path_if_blank(
        payload,
        "conclusao.status",
        _resolve_nr10_documental_conclusion_status(
            explicit_conclusion,
            review_status=getattr(laudo, "status_revisao", None),
            has_nonconformity=has_attention_points,
        ),
    )


def apply_nr10_prontuario_projection(
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
    if family_key != "nr10_prontuario_instalacoes_eletricas":
        return

    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.objeto_principal",
                "objeto_principal",
                "prontuario_objeto",
                "instalacao_principal",
                "sistema_principal",
                "painel_principal",
                "quadro_principal",
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
            "numero_prontuario",
            "tag_patrimonial",
            "codigo_tag",
            "tag",
        ],
    )
    main_reference_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.referencia_principal.referencias_texto",
                "referencia_principal",
                "indice_prontuario",
                "documento_indice",
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
        "Documento indice e referencia principal do prontuario eletrico." if main_reference_text else None,
        object_hint,
    )
    main_reference_obs = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.referencia_principal.observacao", "observacao_referencia_principal"],
        ),
        "Rastreabilidade principal confirmada para o prontuario." if main_reference_text else None,
    )
    nr10_location_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.localizacao", "local_inspecao", "localizacao", "setor", "unidade"],
        ),
        location_hint,
    )
    delivery_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.tipo_entrega", "tipo_entrega", "modalidade_laudo"]),
        _value_by_path(payload, "case_context.modalidade_laudo"),
        "pacote_documental",
    )
    raw_execution_mode = _normalize_execution_mode(
        _pick_value_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.modo_execucao", "modo_execucao", "tipo_execucao", "modalidade_execucao"],
        )
    )
    if raw_execution_mode in {None, "documental"}:
        execution_mode = "analise_documental"
    else:
        execution_mode = _pick_first_text(raw_execution_mode, "analise_documental") or "analise_documental"
    asset_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.ativo_tipo", "ativo_tipo", "tipo_ativo"]),
        "instalacoes_eletricas",
    )
    scope_summary = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.resumo_escopo", "resumo_escopo", "resumo_servico", "escopo"],
        ),
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
                "criterio_consolidacao",
            ],
        ),
        "Consolidacao documental do prontuario NR10 com organizacao de indice, diagramas, inventario e registros tecnicos.",
    )
    observed_conditions = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "execucao_servico.condicoes_observadas",
                "condicoes_observadas",
                "condicoes_gerais",
                "status_documentacao",
                "resumo_documental",
            ],
        ),
        summary_hint,
    )
    pie_text = _pick_text_by_paths(existing_payload, payload, paths=["pie", "prontuario_eletrico", "documentacao_base.pie"])
    prontuario_text = _pick_text_by_paths(existing_payload, payload, paths=["prontuario", "indice_prontuario", "documentacao_base.prontuario"])
    diagram_text = _pick_text_by_paths(existing_payload, payload, paths=["diagrama_unifilar", "diagrama_eletrico", "documentacao_base.diagrama"])
    memorial_text = _pick_text_by_paths(existing_payload, payload, paths=["memorial_descritivo", "documentacao_base.memorial"])
    inventory_text = _pick_text_by_paths(existing_payload, payload, paths=["inventario_instalacoes", "inventario_eletrico"])
    procedure_text = _pick_text_by_paths(existing_payload, payload, paths=["procedimento_trabalho", "procedimento_operacional", "procedimentos_trabalho"])
    specification_text = _pick_text_by_paths(existing_payload, payload, paths=["especificacoes_sistema", "especificacao_sistema"])
    art_number = _pick_text_by_paths(existing_payload, payload, paths=["art_numero", "art"])
    relevant_parameters = _build_labeled_summary(
        ("Prontuario", prontuario_text),
        ("PIE", pie_text),
        ("Diagrama", diagram_text),
        ("Inventario", inventory_text),
        ("Procedimento", procedure_text),
        ("Memorial", memorial_text),
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
        _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.evidencia_execucao.descricao", "descricao_evidencia_execucao"]),
        observed_conditions,
    )
    primary_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["evidencias_e_anexos.evidencia_principal.referencias_texto", "evidencia_principal", "documento_principal"],
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
    document_base_text = _pick_first_text(prontuario_text, pie_text, diagram_text, inventory_text, primary_evidence_text)
    document_summary = _build_labeled_summary(
        ("Prontuario", prontuario_text),
        ("PIE", pie_text),
        ("Diagrama", diagram_text),
        ("Inventario", inventory_text),
        ("Procedimento", procedure_text),
        ("Memorial", memorial_text),
        ("Especificacao", specification_text),
        ("ART", art_number),
    )
    document_notes = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["documentacao_e_registros.observacoes_documentais", "observacoes_documentais"]),
        recommendation_hint,
        document_summary,
    )

    explicit_attention = _pick_value_by_paths(
        existing_payload,
        payload,
        paths=[
            "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
            "ha_pontos_de_atencao",
            "ha_nao_conformidades",
            "possui_pendencias_documentais",
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
                "pendencias_documentais",
                "pontos_de_atencao",
            ],
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
    _set_path_if_blank(payload, "identificacao.localizacao", nr10_location_hint)
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
        description="Documento base principal considerado para a consolidacao do prontuario NR10." if document_base_text else None,
        references_text=document_base_text,
        observation=document_notes,
        available=bool(document_base_text),
    )

    _set_path_if_blank(payload, "documentacao_e_registros.documentos_disponiveis", document_summary)
    _set_path_if_blank(
        payload,
        "documentacao_e_registros.documentos_emitidos",
        _pick_text_by_paths(existing_payload, payload, paths=["documentacao_e_registros.documentos_emitidos", "documentos_emitidos", "pacote_emitido"]),
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
        _resolve_nr10_documental_conclusion_status(
            explicit_conclusion,
            review_status=getattr(laudo, "status_revisao", None),
            has_nonconformity=has_attention_points,
        ),
    )


__all__ = [
    "apply_nr10_projection",
    "apply_nr10_loto_projection",
    "apply_nr10_prontuario_projection",
    "apply_nr10_spda_projection",
]
