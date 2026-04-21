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

_NR33_SERVICE_META: dict[str, dict[str, str]] = {
    "nr33_avaliacao_espaco_confinado": {
        "service_label": "avaliacao espaco confinado",
        "scope_summary": (
            "Execucao do servico avaliacao espaco confinado no contexto da norma seguranca e saude "
            "nos trabalhos em espacos confinados, com consolidacao de evidencias, registros de campo "
            "ou base documental e conclusao tecnica auditavel."
        ),
        "method_text": (
            "Metodo padrao Tariel para avaliacao espaco confinado, com registro estruturado do "
            "escopo, dados de execucao, anexos principais e pontos de atencao."
        ),
        "document_base": "Pacote tecnico de referencia para avaliacao espaco confinado.",
        "documents_emitted": "Pacote tecnico de nr33 - avaliacao espaco confinado consolidado para entrega.",
        "recommendation": (
            "Manter rastreabilidade do servico avaliacao espaco confinado e registrar formalmente "
            "qualquer ajuste, complemento documental ou revalidacao futura."
        ),
        "conclusion": (
            "O servico nr33 - avaliacao espaco confinado foi consolidado com rastreabilidade "
            "suficiente, evidencias principais vinculadas e conclusao tecnica formalizada."
        ),
    },
    "nr33_permissao_entrada_trabalho": {
        "service_label": "permissao entrada trabalho",
        "scope_summary": (
            "Execucao do servico permissao entrada trabalho no contexto da norma seguranca e saude "
            "nos trabalhos em espacos confinados, com consolidacao de evidencias, registros de campo "
            "ou base documental e conclusao tecnica auditavel."
        ),
        "method_text": (
            "Metodo padrao Tariel para permissao entrada trabalho, com registro estruturado do "
            "escopo, dados de execucao, anexos principais e pontos de atencao."
        ),
        "document_base": "Pacote tecnico de referencia para permissao entrada trabalho.",
        "documents_emitted": "Pacote tecnico de nr33 - permissao entrada trabalho consolidado para entrega.",
        "recommendation": (
            "Manter rastreabilidade do servico permissao entrada trabalho e registrar formalmente "
            "qualquer ajuste, complemento documental ou revalidacao futura."
        ),
        "conclusion": (
            "O servico nr33 - permissao entrada trabalho foi consolidado com rastreabilidade "
            "suficiente, evidencias principais vinculadas e conclusao tecnica formalizada."
        ),
    },
}

_NR33_DEFAULT_JUSTIFICATION = (
    "A conclusao considera o escopo registrado, o metodo aplicado, a documentacao disponivel, "
    "a evidencia principal e os pontos de atencao ou sua ausencia declarada."
)
_NR33_DEFAULT_EXECUTION_OBSERVATION = (
    "Servico executado dentro do escopo previsto, com registros suficientes para revisao da Mesa e consolidacao do documento final."
)
_NR33_DEFAULT_REFERENCE_DESCRIPTION = "Referencia principal do objeto identificada com apoio de evidencia visual e documento associado."
_NR33_DEFAULT_REFERENCE_OBSERVATION = "Rastreabilidade principal confirmada para o servico."
_NR33_DEFAULT_DOCUMENT_NOTE = "Documento vinculado ao contexto de seguranca e saude nos trabalhos em espacos confinados."


def _resolve_nr33_conclusion_status(
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
        if any(token in text for token in ("restric", "ressalva", "ajuste")):
            return "ajuste"
        if any(token in text for token in ("liberad", "aprov", "conforme")):
            return "conforme"
        if "pendente" in text:
            return "pendente"

    fallback = _resolve_conclusion_status(review_status, has_nonconformity=has_nonconformity)
    if fallback == "bloqueio":
        return "nao_conforme"
    return fallback


def apply_nr33_projection(
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
    meta = _NR33_SERVICE_META.get(family_key)
    if meta is None:
        return

    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.objeto_principal",
                "objeto_principal",
                "espaco_confinado",
                "espaco_confinado_identificacao",
                "descricao_espaco",
                "atividade_principal",
                "servico_principal",
                "titulo_servico",
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
            "numero_pet",
            "pet_numero",
            "numero_permissao",
            "numero_avaliacao",
            "codigo_espaco",
            "codigo_local",
            "tag_patrimonial",
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
                "referencia_principal_ref",
                "foto_entrada",
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
        _NR33_DEFAULT_REFERENCE_DESCRIPTION if main_reference_text else None,
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
        _NR33_DEFAULT_REFERENCE_OBSERVATION if main_reference_text else None,
    )
    nr33_location_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.localizacao",
                "local_inspecao",
                "localizacao",
                "unidade",
                "setor",
                "informacoes_gerais.local",
                "informacoes_gerais.unidade",
            ],
        ),
        location_hint,
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
    execution_mode = _pick_first_text(
        _normalize_execution_mode(
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
        ),
        "in_loco",
    )
    asset_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.ativo_tipo", "ativo_tipo", "tipo_ativo"],
        ),
        "NR33",
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

    supervisor_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["supervisor_entrada", "supervisor", "responsavel_liberacao"],
    )
    watcher_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["vigia", "observador", "monitor_entrada"],
    )
    lockout_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["bloqueios", "isolamentos", "isolamento_energias"],
    )
    atmosphere_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=[
            "atmosfera_liberacao",
            "atmosfera_inicial",
            "leitura_atmosferica",
            "medicao_atmosferica",
        ],
    )

    if family_key == "nr33_avaliacao_espaco_confinado":
        classification_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["classificacao_espaco", "categoria_espaco", "tipo_espaco"],
        )
        ventilation_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["ventilacao", "ventilacao_prevista", "exaustao"],
        )
        rescue_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["plano_resgate", "resgate", "equipe_resgate"],
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
            ("Classificacao", classification_text),
            ("Atmosfera", atmosphere_text),
            ("Ventilacao", ventilation_text),
            ("Bloqueios", lockout_text),
            ("Supervisor", supervisor_text),
            ("Vigia", watcher_text),
            ("Resgate", rescue_text),
        )
        document_base_text = _pick_first_text(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["evidencias_e_anexos.documento_base.referencias_texto", "documento_base", "avaliacao_previa"],
            ),
            _pick_text_by_paths(existing_payload, payload, paths=["apr", "procedimento", "registro_medicoes"]),
            meta["document_base"],
        )
        document_summary = _build_labeled_summary(
            ("Documento base", document_base_text),
            ("APR", _pick_text_by_paths(existing_payload, payload, paths=["apr"])),
            ("Procedimento", _pick_text_by_paths(existing_payload, payload, paths=["procedimento"])),
            ("Medicoes", _pick_text_by_paths(existing_payload, payload, paths=["registro_medicoes", "medicao_atmosferica"])),
        )
    else:
        pet_number_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["numero_pet", "pet_numero", "numero_permissao"],
        )
        validity_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["validade_pet", "vigencia_pet", "validade_permissao"],
        )
        team_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["equipe_autorizada", "executante", "trabalhadores_autorizados"],
        )
        epi_epc_text = _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["epi_epc", "epis_epcs", "protecoes_coletivas"],
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
            ("PET", pet_number_text),
            ("Validade", validity_text),
            ("Supervisor", supervisor_text),
            ("Vigia", watcher_text),
            ("Atmosfera", atmosphere_text),
            ("Bloqueios", lockout_text),
            ("EPI/EPC", epi_epc_text),
            ("Equipe", team_text),
        )
        document_base_text = _pick_first_text(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["evidencias_e_anexos.documento_base.referencias_texto", "documento_base", "pet_documento"],
            ),
            _pick_text_by_paths(existing_payload, payload, paths=["apr", "procedimento"]),
            meta["document_base"],
        )
        document_summary = _build_labeled_summary(
            ("PET", _pick_first_text(pet_number_text, _pick_text_by_paths(existing_payload, payload, paths=["pet_documento"]))),
            ("APR", _pick_text_by_paths(existing_payload, payload, paths=["apr"])),
            ("Procedimento", _pick_text_by_paths(existing_payload, payload, paths=["procedimento"])),
            ("Bloqueios", lockout_text),
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
        _NR33_DEFAULT_EXECUTION_OBSERVATION,
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
        paths=["evidencias_e_anexos.evidencia_complementar.referencias_texto", "evidencia_complementar", "evidencias_complementares"],
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
        _NR33_DEFAULT_DOCUMENT_NOTE,
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
        _pick_text_by_paths(existing_payload, payload, paths=["recomendacoes.texto", "recomendacao", "recomendacoes", "observacoes"]),
        recommendation_hint,
        meta["recommendation"],
    )
    conclusion_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["conclusao.conclusao_tecnica", "conclusao_tecnica"]),
        meta["conclusion"],
    )
    conclusion_justification = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["conclusao.justificativa", "justificativa"]),
        _NR33_DEFAULT_JUSTIFICATION,
    )
    summary_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["resumo_executivo"]),
        summary_hint,
        (
            f"Foi executado o servico nr33 - {meta['service_label']} com registro "
            "estruturado do objeto principal, evidencias vinculadas, "
            "documentacao de apoio e conclusao tecnica consolidada para a Mesa."
        ),
    )

    attention_evidence_text = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["nao_conformidades_ou_lacunas.evidencias.referencias_texto", "evidencia_ponto_atencao", "evidencia_nao_conformidade"],
        ),
        primary_evidence_text,
    )

    _set_path_if_blank(payload, "resumo_executivo", summary_text)

    _set_path_if_blank(payload, "identificacao.objeto_principal", object_hint)
    _set_path_if_blank(payload, "identificacao.localizacao", nr33_location_hint)
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
        _resolve_nr33_conclusion_status(
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


__all__ = ["apply_nr33_projection"]
