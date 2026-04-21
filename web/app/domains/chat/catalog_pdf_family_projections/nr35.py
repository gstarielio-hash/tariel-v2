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


def _infer_nr35_asset_type(*values: Any) -> str | None:
    joined = " ".join(str(value or "").strip() for value in values if str(value or "").strip())
    text = _normalize_signal_text(joined)
    if "ancor" in text:
        return "ponto_ancoragem"
    if "vertical" in text:
        return "linha_de_vida_vertical"
    if "horizontal" in text:
        return "linha_de_vida_horizontal"
    if "linha de vida" in text or "linha_vida" in text:
        return "linha_de_vida"
    return "trabalho_em_altura" if text else None


def _humanize_nr35_system_type(*values: Any) -> str | None:
    joined = " ".join(str(value or "").strip() for value in values if str(value or "").strip())
    text = _normalize_signal_text(joined)
    if not text:
        return None
    if "ancor" in text:
        return "Ponto de ancoragem"
    if "vertical" in text:
        return "Linha de vida vertical"
    if "horizontal" in text:
        return "Linha de vida horizontal"
    if "linha de vida" in text or "linha_vida" in text:
        return "Linha de vida"
    return _pick_first_text(*values)


def _normalize_nr35_component_condition(value: Any) -> str | None:
    raw_value = value
    if isinstance(value, dict):
        raw_value = value.get("condicao") or value.get("status") or value.get("veredito") or value.get("valor")
    text = _normalize_signal_text(raw_value)
    if not text:
        return None
    if text in {"c", "conforme", "ok", "aprovado"} or text.startswith("c "):
        return "C"
    if text in {"nc", "nao conforme", "reprovado", "ajuste"} or "nao conforme" in text or text.startswith("nc "):
        return "NC"
    if text in {"n/a", "na", "nao aplicavel", "nao se aplica"}:
        return "N/A"
    return _pick_first_text(raw_value)


def _extract_nr35_photo_records(*sources: dict[str, Any] | None) -> list[dict[str, str]]:
    for source in sources:
        if not isinstance(source, dict):
            continue
        records = _value_by_path(source, "registros_fotograficos")
        if not isinstance(records, list):
            continue
        normalized_records: list[dict[str, str]] = []
        for item in records:
            if not isinstance(item, dict):
                continue
            title = _pick_first_text(item.get("titulo"), item.get("title"))
            caption = _pick_first_text(item.get("legenda"), item.get("caption"))
            reference = _pick_first_text(item.get("referencia_anexo"), item.get("referencia"), item.get("resolved_evidence_id"))
            if not any((title, caption, reference)):
                continue
            normalized_records.append({"titulo": title or "", "legenda": caption or "", "referencia": reference or ""})
        if normalized_records:
            return normalized_records
    return []


def _format_nr35_component_signal(condition: str | None, observation: str | None) -> str | None:
    if condition and observation:
        return f"{condition} ({observation})"
    return condition or observation


def _resolve_nr35_conclusion_status(
    *values: Any,
    review_status: Any,
    has_nonconformity: bool | None,
) -> str | None:
    def _normalize_nr35_final_status(value: Any) -> str | None:
        text = _normalize_signal_text(value)
        if not text:
            return None
        if (
            "reprov" in text
            or "bloqueio" in text
            or "nao conforme" in text
            or "nao_conforme" in text
            or "ajuste" in text
        ):
            return "Reprovado"
        if "pendente" in text or "nao informado" in text:
            return "Pendente"
        if "aprov" in text or text in {"c", "ok", "conforme"}:
            return "Aprovado"
        return None

    for value in values:
        normalized_status = _normalize_nr35_final_status(value)
        if normalized_status:
            return normalized_status
    return _normalize_nr35_final_status(_resolve_conclusion_status(review_status, has_nonconformity=has_nonconformity))


def _resolve_nr35_operational_status(*values: Any, has_nonconformity: bool | None = None) -> str | None:
    for value in values:
        text = _normalize_signal_text(value)
        if not text:
            continue
        if "bloqueio" in text or "interdit" in text or "nao liberar" in text:
            return "bloqueio"
        if "reprov" in text and "ajuste" not in text:
            return "bloqueio"
        if any(token in text for token in ("ajuste", "adequac", "correc", "ressalv", "restric", "reinspec", "revalid", "nao conforme")):
            return "ajuste"
        if "pendente" in text or "avaliacao" in text:
            return "avaliacao_complementar"
        if "aprov" in text or text in {"c", "ok", "conforme", "liberado"}:
            return "conforme"
    if has_nonconformity is True:
        return "ajuste"
    if has_nonconformity is False:
        return "conforme"
    return None


def apply_nr35_projection(
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
    if family_key not in {"nr35_inspecao_linha_de_vida", "nr35_inspecao_ponto_ancoragem"}:
        return

    photo_records = _extract_nr35_photo_records(existing_payload, payload)
    photo_reference_items: list[str] = []
    photo_description_items: list[str] = []
    for record in photo_records:
        title = _pick_first_text(record.get("titulo"))
        caption = _pick_first_text(record.get("legenda"))
        reference = _pick_first_text(record.get("referencia"))
        if reference and title:
            photo_reference_items.append(f"{title}: {reference}")
        elif reference:
            photo_reference_items.append(reference)
        elif title:
            photo_reference_items.append(title)
        if title and caption:
            photo_description_items.append(f"{title} - {caption}")
        elif caption:
            photo_description_items.append(caption)
        elif title:
            photo_description_items.append(title)
    photo_reference_text = "; ".join(photo_reference_items) or None
    photo_description_text = "; ".join(photo_description_items) or None

    object_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=[
                "identificacao.objeto_principal",
                "objeto_principal",
                "objeto_inspecao.identificacao_linha_vida",
                "objeto_inspecao.identificacao",
                "linha_de_vida",
                "ponto_ancoragem",
                "ativo_principal",
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
            "informacoes_gerais.numero_laudo_inspecao",
            "numero_laudo_inspecao",
            "tag_patrimonial",
            "tag",
            "codigo_tag",
            "asset_tag",
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
                "foto_referencia_principal",
                "foto_principal",
            ],
        ),
        photo_reference_text,
    )
    main_reference_desc = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.referencia_principal.descricao", "descricao_referencia_principal", "referencia_principal_descricao"],
        ),
        photo_description_text,
        object_hint,
    )
    main_reference_obs = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.referencia_principal.observacao", "observacao_referencia_principal"],
    )
    nr35_location_hint = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["identificacao.localizacao", "local_inspecao", "informacoes_gerais.local", "informacoes_gerais.unidade", "unidade"],
        ),
        location_hint,
    )
    document_location = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.local_documento", "informacoes_gerais.local_documento", "informacoes_gerais.local", "local"],
    )
    unit_name = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.unidade_operacional", "informacoes_gerais.unidade_operacional", "informacoes_gerais.unidade", "unidade"],
    )
    inspection_type = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["case_context.tipo_inspecao", "identificacao.tipo_inspecao", "informacoes_gerais.tipo_inspecao", "tipo_inspecao"],
        ),
        "Inspecao Periodica",
    )

    delivery_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.tipo_entrega", "tipo_entrega", "modalidade_laudo"]),
        _value_by_path(payload, "case_context.modalidade_laudo"),
        "inspecao_tecnica",
    )
    execution_mode = _pick_first_text(
        _normalize_execution_mode(
            _pick_value_by_paths(existing_payload, payload, paths=["escopo_servico.modo_execucao", "modo_execucao", "tipo_execucao", "modalidade_execucao"])
        ),
        "in_loco",
    )
    asset_type_override = _pick_text_by_paths(existing_payload, payload, paths=["escopo_servico.ativo_tipo", "ativo_tipo"])
    asset_type_text = _pick_text_by_paths(
        existing_payload, payload, paths=["tipo_ativo", "tipo_linha_vida", "objeto_inspecao.tipo_linha_vida", "tipo_ancoragem"]
    )
    asset_type = _pick_first_text(asset_type_override, _infer_nr35_asset_type(asset_type_text, object_hint, family_key))
    scope_summary = _pick_first_text(
        _pick_text_by_paths(
            existing_payload,
            payload,
            paths=["escopo_servico.resumo_escopo", "objeto_inspecao.escopo_inspecao", "escopo_inspecao", "resumo_escopo", "resumo_servico", "escopo"],
        ),
        summary_hint,
    )

    document_report_number = _pick_text_by_paths(
        existing_payload, payload, paths=["informacoes_gerais.numero_laudo_inspecao", "numero_laudo_inspecao", "laudo_inspecao"]
    )
    manufacturer_report_number = _pick_text_by_paths(
        existing_payload, payload, paths=["informacoes_gerais.numero_laudo_fabricante", "numero_laudo_fabricante", "laudo_fabricante", "fabricante"]
    )
    art_number = _pick_text_by_paths(existing_payload, payload, paths=["informacoes_gerais.art_numero", "art_numero", "art"])
    document_code = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["identificacao.documento_codigo", "documento_codigo"]),
        document_report_number,
        internal_code,
    )
    contractor_name = _pick_text_by_paths(existing_payload, payload, paths=["identificacao.contratante", "informacoes_gerais.contratante", "contratante"])
    contractor_service_name = _pick_text_by_paths(existing_payload, payload, paths=["identificacao.contratada", "informacoes_gerais.contratada", "contratada"])
    responsible_engineer = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["identificacao.engenheiro_responsavel", "informacoes_gerais.engenheiro_responsavel", "engenheiro_responsavel"],
    )
    inspector_lead = _pick_text_by_paths(
        existing_payload, payload, paths=["identificacao.inspetor_lider", "informacoes_gerais.inspetor_lider", "inspetor_lider"]
    )
    inspection_date = _pick_text_by_paths(existing_payload, payload, paths=["identificacao.data_vistoria", "informacoes_gerais.data_vistoria", "data_vistoria"])
    next_inspection = _pick_text_by_paths(existing_payload, payload, paths=["conclusao.proxima_inspecao_periodica", "proxima_inspecao_periodica"])
    explicit_conclusion_status = _pick_text_by_paths(existing_payload, payload, paths=["conclusao.status", "status_conclusao", "status"])
    conclusion_note = _pick_text_by_paths(existing_payload, payload, paths=["conclusao.observacoes", "observacoes_finais", "observacoes"])
    linked_art = _pick_first_text(_pick_text_by_paths(existing_payload, payload, paths=["identificacao.vinculado_art", "vinculado_art"]), art_number)
    system_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["identificacao.tipo_sistema", "tipo_sistema"]),
        _humanize_nr35_system_type(asset_type_text, object_hint, family_key),
    )
    line_type = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["objeto_inspecao.tipo_linha_de_vida", "tipo_linha_vida"]),
        asset_type_text,
    )
    scope_description = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["objeto_inspecao.descricao_escopo", "descricao_escopo", "objeto_inspecao.escopo_inspecao"]),
        scope_summary,
    )
    use_classification = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["objeto_inspecao.classificacao_uso", "classificacao_uso"],
    )
    methodology_text = _pick_first_text(
        _pick_text_by_paths(existing_payload, payload, paths=["metodologia_e_recursos.metodologia", "metodologia", "metodologia_inspecao"]),
        None,
    )
    instruments_text = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["metodologia_e_recursos.instrumentos_utilizados", "instrumentos_utilizados", "instrumentos"],
    )
    important_notice = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["metodologia_e_recursos.aviso_importante", "aviso_importante"],
    )
    photo_register_note = _pick_text_by_paths(
        existing_payload,
        payload,
        paths=["registros_fotograficos_catalogados.observacao", "registros_fotograficos_observacao"],
    )

    if family_key == "nr35_inspecao_linha_de_vida":
        component_specs = (
            ("fixacao_dos_pontos", "Fixacao", ["componentes_inspecionados.fixacao_dos_pontos", "fixacao_dos_pontos"]),
            ("condicao_cabo_aco", "Cabo de aco", ["componentes_inspecionados.condicao_cabo_aco", "condicao_cabo_aco", "cabo_aco"]),
            ("condicao_esticador", "Esticador", ["componentes_inspecionados.condicao_esticador", "condicao_esticador", "esticador"]),
            ("condicao_sapatilha", "Sapatilha", ["componentes_inspecionados.condicao_sapatilha", "condicao_sapatilha", "sapatilha"]),
            ("condicao_olhal", "Olhal", ["componentes_inspecionados.condicao_olhal", "condicao_olhal", "olhal"]),
            ("condicao_grampos", "Grampos", ["componentes_inspecionados.condicao_grampos", "condicao_grampos", "grampos"]),
        )
        component_notes: list[tuple[str, str | None]] = []
        component_details: list[tuple[str, str | None, str | None]] = []
        has_nc_component = False
        all_components_closed = True

        for field_key, label, paths in component_specs:
            raw_component = _pick_value_by_paths(existing_payload, payload, paths=paths)
            component_condition = _normalize_nr35_component_condition(raw_component)
            if component_condition is None:
                all_components_closed = False
            elif component_condition == "NC":
                has_nc_component = True
            component_observation = None
            if isinstance(raw_component, dict):
                component_observation = _pick_first_text(
                    raw_component.get("observacao"), raw_component.get("descricao"), raw_component.get("texto"), raw_component.get("localizacao")
                )
            if component_observation is None:
                component_observation = _pick_text_by_paths(existing_payload, payload, paths=[f"{path}.observacao" for path in paths if "." in path])
            component_notes.append((label, _format_nr35_component_signal(component_condition, component_observation)))
            component_details.append((field_key, component_condition, component_observation))
        component_summary = "; ".join(label for _, label, _ in component_specs)

        method_text = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.metodo_aplicado", "metodo_aplicado", "metodo_inspecao", "metodo"]),
            "Inspecao visual em altura com checklist NR35 e registro fotografico guiado.",
        )
        observed_conditions = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.condicoes_observadas", "condicoes_observadas", "resumo_executivo"]),
            conclusion_note,
            summary_hint,
        )
        relevant_parameters = _build_labeled_summary(("Tipo", asset_type_text), *component_notes)
        execution_evidence_text = _pick_first_text(
            _pick_text_by_paths(
                existing_payload, payload, paths=["execucao_servico.evidencia_execucao.referencias_texto", "evidencia_execucao", "registro_execucao"]
            ),
            photo_reference_text,
            main_reference_text,
        )
        execution_evidence_desc = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.evidencia_execucao.descricao", "descricao_evidencia_execucao"]),
            photo_description_text,
            observed_conditions,
        )
        primary_evidence_text = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.evidencia_principal.referencias_texto", "evidencia_principal"]),
            main_reference_text,
        )
        primary_evidence_desc = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.evidencia_principal.descricao", "descricao_evidencia_principal"]),
            main_reference_desc,
            observed_conditions,
        )
        complementary_evidence_text = _pick_first_text(
            _pick_text_by_paths(
                existing_payload,
                payload,
                paths=["evidencias_e_anexos.evidencia_complementar.referencias_texto", "evidencia_complementar", "evidencias_complementares"],
            ),
            "; ".join(photo_reference_items[1:]) if len(photo_reference_items) > 1 else None,
        )
        complementary_evidence_desc = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.evidencia_complementar.descricao", "descricao_evidencia_complementar"]),
            "; ".join(photo_description_items[1:]) if len(photo_description_items) > 1 else None,
        )
        document_base_text = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.documento_base.referencias_texto", "documento_base"]),
            document_report_number,
            manufacturer_report_number,
            art_number,
        )
        document_summary = _build_labeled_summary(
            ("Laudo inspecao", document_report_number),
            ("Laudo fabricante", manufacturer_report_number),
            ("ART", art_number),
            ("Proxima inspecao", next_inspection),
        )
        document_notes = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["documentacao_e_registros.observacoes_documentais", "observacoes_documentais"]),
            document_summary,
        )
        nc_descriptions = [f"{label}: {signal}" for label, signal in component_notes if signal and signal.startswith("NC")]
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
                ],
            ),
            "; ".join(nc_descriptions) or None,
            conclusion_note,
            recommendation_hint,
            summary_hint,
        )
        explicit_attention = _pick_value_by_paths(
            existing_payload,
            payload,
            paths=[
                "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
                "ha_pontos_de_atencao",
                "nao_conformidades.ha_nao_conformidades",
                "ha_nao_conformidades",
            ],
        )
        has_attention_points = _infer_nonconformity_flag(explicit_attention, attention_description, conclusion_note)
        if has_attention_points is None and has_nc_component:
            has_attention_points = True
        if has_attention_points is None and all_components_closed and explicit_conclusion_status:
            normalized_status = _normalize_signal_text(explicit_conclusion_status)
            if "aprov" in normalized_status:
                has_attention_points = False
            elif "reprov" in normalized_status:
                has_attention_points = True
    else:
        anchor_type_text = _pick_text_by_paths(
            existing_payload, payload, paths=["tipo_ancoragem", "objeto_inspecao.tipo_linha_vida", "tipo_ativo", "ativo_tipo"]
        )
        fixation_text = _pick_text_by_paths(existing_payload, payload, paths=["fixacao", "fixacao_dos_pontos", "ponto_fixacao"])
        anchor_bolt_text = _pick_text_by_paths(existing_payload, payload, paths=["chumbador", "chumbadores", "fixador"])
        corrosion_text = _pick_text_by_paths(existing_payload, payload, paths=["corrosao", "oxidacao"])
        deformation_text = _pick_text_by_paths(existing_payload, payload, paths=["deformacao", "amassamento"])
        crack_text = _pick_text_by_paths(existing_payload, payload, paths=["trinca", "fissura"])
        load_text = _pick_text_by_paths(existing_payload, payload, paths=["carga_nominal", "capacidade_nominal"])
        certificate_text = _pick_text_by_paths(existing_payload, payload, paths=["certificado_ancoragem", "certificado"])
        memorial_text = _pick_text_by_paths(existing_payload, payload, paths=["memorial_calculo", "memorial"])
        manual_text = _pick_text_by_paths(existing_payload, payload, paths=["manual", "manual_fabricante"])

        method_text = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.metodo_aplicado", "metodo_aplicado", "metodo_inspecao", "metodo"]),
            "Inspecao visual e funcional do ponto de ancoragem com verificacao de fixacao e integridade aparente.",
        )
        observed_conditions = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.condicoes_observadas", "condicoes_observadas", "resumo_executivo"]),
            _build_labeled_summary(("Corrosao", corrosion_text), ("Deformacao", deformation_text), ("Trinca", crack_text)),
            summary_hint,
        )
        relevant_parameters = _build_labeled_summary(
            ("Tipo", anchor_type_text),
            ("Fixacao", fixation_text),
            ("Chumbador", anchor_bolt_text),
            ("Corrosao", corrosion_text),
            ("Deformacao", deformation_text),
            ("Trinca", crack_text),
            ("Carga nominal", load_text),
        )
        execution_evidence_text = _pick_first_text(
            _pick_text_by_paths(
                existing_payload, payload, paths=["execucao_servico.evidencia_execucao.referencias_texto", "evidencia_execucao", "registro_execucao"]
            ),
            main_reference_text,
        )
        execution_evidence_desc = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["execucao_servico.evidencia_execucao.descricao", "descricao_evidencia_execucao"]),
            observed_conditions,
        )
        primary_evidence_text = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.evidencia_principal.referencias_texto", "evidencia_principal"]),
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
            existing_payload, payload, paths=["evidencias_e_anexos.evidencia_complementar.descricao", "descricao_evidencia_complementar"]
        )
        document_base_text = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["evidencias_e_anexos.documento_base.referencias_texto", "documento_base"]),
            certificate_text,
            memorial_text,
            art_number,
        )
        document_summary = _build_labeled_summary(("Certificado", certificate_text), ("Memorial", memorial_text), ("ART", art_number), ("Manual", manual_text))
        document_notes = _pick_first_text(
            _pick_text_by_paths(existing_payload, payload, paths=["documentacao_e_registros.observacoes_documentais", "observacoes_documentais"]),
            document_summary,
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
                ],
            ),
            recommendation_hint,
            observed_conditions,
            summary_hint,
        )
        explicit_attention = _pick_value_by_paths(
            existing_payload,
            payload,
            paths=[
                "nao_conformidades_ou_lacunas.ha_pontos_de_atencao",
                "ha_pontos_de_atencao",
                "nao_conformidades.ha_nao_conformidades",
                "ha_nao_conformidades",
            ],
        )
        has_attention_points = _infer_nonconformity_flag(
            explicit_attention, attention_description, corrosion_text, deformation_text, crack_text, recommendation_hint
        )
        if has_attention_points is None and explicit_conclusion_status:
            normalized_status = _normalize_signal_text(explicit_conclusion_status)
            if "aprov" in normalized_status:
                has_attention_points = False
            elif "reprov" in normalized_status:
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
    _set_path_if_blank(payload, "identificacao.localizacao", nr35_location_hint)
    _set_path_if_blank(payload, "identificacao.unidade_operacional", unit_name)
    _set_path_if_blank(payload, "identificacao.local_documento", document_location)
    _set_path_if_blank(payload, "identificacao.codigo_interno", internal_code)
    _set_path_if_blank(payload, "identificacao.documento_codigo", document_code)
    _set_path_if_blank(payload, "identificacao.tipo_ativo", asset_type_text)
    _set_path_if_blank(payload, "identificacao.tipo_inspecao", inspection_type)
    _set_path_if_blank(payload, "identificacao.tipo_sistema", system_type)
    _set_path_if_blank(payload, "identificacao.contratante", contractor_name)
    _set_path_if_blank(payload, "identificacao.contratada", contractor_service_name)
    _set_path_if_blank(payload, "identificacao.engenheiro_responsavel", responsible_engineer)
    _set_path_if_blank(payload, "identificacao.inspetor_lider", inspector_lead)
    _set_path_if_blank(payload, "identificacao.numero_laudo_inspecao", document_report_number)
    _set_path_if_blank(payload, "identificacao.numero_laudo_fabricante", manufacturer_report_number)
    _set_path_if_blank(payload, "identificacao.art_numero", art_number)
    _set_path_if_blank(payload, "identificacao.vinculado_art", linked_art)
    _set_path_if_blank(payload, "identificacao.data_vistoria", inspection_date)
    _set_block_fields_if_blank(
        payload,
        block_path="identificacao.referencia_principal",
        description=main_reference_desc,
        references_text=main_reference_text,
        observation=main_reference_obs,
        available=bool(main_reference_desc or main_reference_text or main_reference_obs),
    )

    _set_path_if_blank(payload, "case_context.local_documento", document_location)
    _set_path_if_blank(payload, "case_context.tipo_inspecao", inspection_type)
    _set_path_if_blank(payload, "objeto_inspecao.descricao_escopo", scope_description)
    _set_path_if_blank(payload, "objeto_inspecao.tipo_linha_de_vida", line_type)
    _set_path_if_blank(payload, "objeto_inspecao.resumo_componentes_avaliados", component_summary if family_key == "nr35_inspecao_linha_de_vida" else None)
    _set_path_if_blank(payload, "objeto_inspecao.classificacao_uso", use_classification)
    _set_path_if_blank(payload, "escopo_servico.tipo_entrega", delivery_type)
    _set_path_if_blank(payload, "escopo_servico.modo_execucao", execution_mode)
    _set_path_if_blank(payload, "escopo_servico.ativo_tipo", asset_type)
    _set_path_if_blank(payload, "escopo_servico.resumo_escopo", scope_summary)

    _set_path_if_blank(payload, "execucao_servico.metodo_aplicado", method_text)
    _set_path_if_blank(payload, "execucao_servico.condicoes_observadas", observed_conditions)
    _set_path_if_blank(payload, "execucao_servico.parametros_relevantes", relevant_parameters)
    _set_path_if_blank(payload, "metodologia_e_recursos.metodologia", methodology_text or method_text)
    _set_path_if_blank(payload, "metodologia_e_recursos.instrumentos_utilizados", instruments_text)
    _set_path_if_blank(payload, "metodologia_e_recursos.aviso_importante", important_notice)
    _set_path_if_blank(payload, "registros_fotograficos.referencias_texto", photo_reference_text)
    _set_path_if_blank(payload, "registros_fotograficos.descricao", photo_description_text)
    _set_path_if_blank(payload, "registros_fotograficos.observacao", photo_register_note)
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
        description="Documento base principal considerado para a avaliacao NR35." if document_base_text else None,
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
    _set_path_if_blank(payload, "documentacao_e_registros.proxima_inspecao_planejada", next_inspection)
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
    resolved_conclusion_status = _resolve_nr35_conclusion_status(
        explicit_conclusion_status,
        conclusion_note,
        review_status=getattr(laudo, "status_revisao", None),
        has_nonconformity=has_attention_points,
    )
    resolved_operational_status = _resolve_nr35_operational_status(
        explicit_conclusion_status,
        conclusion_note,
        recommendation_hint,
        summary_hint,
        has_nonconformity=has_attention_points,
    )
    if resolved_conclusion_status:
        conclusion_block = payload.get("conclusao")
        if not isinstance(conclusion_block, dict):
            conclusion_block = {}
            payload["conclusao"] = conclusion_block
        conclusion_block["status"] = resolved_conclusion_status
    if resolved_operational_status:
        conclusion_block = payload.get("conclusao")
        if not isinstance(conclusion_block, dict):
            conclusion_block = {}
            payload["conclusao"] = conclusion_block
        if conclusion_block.get("status_operacional") in (None, "", []):
            conclusion_block["status_operacional"] = resolved_operational_status
    _set_path_if_blank(payload, "conclusao.proxima_inspecao_periodica", next_inspection)
    _set_path_if_blank(payload, "conclusao.observacoes", conclusion_note)

    if family_key == "nr35_inspecao_linha_de_vida":
        for field_key, component_condition, component_observation in component_details:
            _set_path_if_blank(payload, f"checklist_componentes.{field_key}.condicao", component_condition)
            _set_path_if_blank(payload, f"checklist_componentes.{field_key}.observacao", component_observation)


__all__ = ["apply_nr35_projection"]
