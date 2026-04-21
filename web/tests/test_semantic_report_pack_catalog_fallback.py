from __future__ import annotations

import uuid

from app.domains.chat.gate_helpers import avaliar_gate_qualidade_laudo
from app.domains.chat.report_pack_helpers import (
    build_pre_laudo_prompt_context,
    build_report_pack_draft_for_laudo,
)
from app.shared.database import (
    AprendizadoVisualIa,
    Laudo,
    MensagemLaudo,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)


def _payload_catalogado_nr33() -> dict[str, object]:
    return {
        "schema_type": "laudo_output",
        "family_key": "nr33_avaliacao_espaco_confinado",
        "family_label": "NR33 Avaliacao de Espaco Confinado",
        "identificacao": {
            "objeto_principal": "Tanque TQ-11",
            "localizacao": "Casa de bombas",
        },
        "evidencias_e_anexos": {
            "evidencia_principal": {
                "referencias_texto": "IMG_014 - acesso principal do tanque",
            },
        },
        "conclusao": {
            "status": "ajuste",
        },
    }


def _criar_laudo_catalogado_nr33(
    ambiente_critico,
    *,
    quantidade_fotos: int = 2,
    photo_names: list[str] | None = None,
) -> int:
    SessionLocal = ambiente_critico["SessionLocal"]
    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR33 Espaco Confinado",
            primeira_mensagem="Inspecao NR33 com payload catalogado materializado.",
            tipo_template="nr33_espaco_confinado",
            catalog_family_key="nr33_avaliacao_espaco_confinado",
            catalog_family_label="NR33 Avaliacao de Espaco Confinado",
            catalog_variant_key="premium_campo",
            catalog_variant_label="Premium Campo",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="chat_first",
            entry_mode_effective="chat_first",
            entry_mode_reason="user_preference",
            dados_formulario=_payload_catalogado_nr33(),
        )
        banco.add(laudo)
        banco.flush()

        mensagens = [
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.USER.value,
                conteudo="Tanque TQ-11 avaliado em campo com foco em acesso, ventilacao e resgate.",
            ),
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.USER.value,
                conteudo="Foram observados pontos de atencao na liberacao e na ventilacao do espaco confinado.",
            ),
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.USER.value,
                conteudo="Documento enviado: pet_tq11.pdf",
            ),
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer preliminar: caso com evidencias suficientes para consolidacao documental.",
            ),
        ]
        photo_count = len(photo_names) if photo_names is not None else max(0, int(quantidade_fotos))
        photo_messages = [
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.USER.value,
                conteudo="[imagem]",
            )
            for _ in range(photo_count)
        ]
        mensagens.extend(photo_messages)
        banco.add_all(mensagens)
        banco.flush()

        if photo_names:
            for index, message in enumerate(photo_messages):
                filename = str(photo_names[index] or "").strip() or f"registro_{index + 1}.jpg"
                banco.add(
                    AprendizadoVisualIa(
                        empresa_id=int(usuario.empresa_id),
                        laudo_id=int(laudo.id),
                        mensagem_referencia_id=int(message.id),
                        criado_por_id=int(usuario.id),
                        setor_industrial=str(laudo.setor_industrial or "geral"),
                        resumo=f"Evidencia visual {index + 1}",
                        correcao_inspetor="Registro fotografico vinculado ao caso de teste.",
                        imagem_url=f"/static/uploads/aprendizados_ia/{int(usuario.empresa_id)}/{int(laudo.id)}/{filename}",
                        imagem_nome_original=filename,
                        imagem_mime_type="image/jpeg",
                        caminho_arquivo=f"/tmp/vision-fixtures/{filename}",
                    )
                )

        banco.commit()
        return int(laudo.id)


def _criar_laudo_guia_com_familia_padrao(
    ambiente_critico,
    *,
    tipo_template: str,
    setor_industrial: str,
) -> int:
    SessionLocal = ambiente_critico["SessionLocal"]
    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial=setor_industrial,
            primeira_mensagem=f"Caso guiado {tipo_template} iniciado no mobile.",
            tipo_template=tipo_template,
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
            guided_inspection_draft_json={
                "template_key": tipo_template,
                "template_label": tipo_template,
                "started_at": "2026-04-06T22:30:00.000Z",
                "current_step_index": 1,
                "completed_step_ids": ["identificacao"],
                "checklist": [
                    {
                        "id": "identificacao",
                        "title": "Identificacao",
                        "prompt": "registre o ativo",
                        "evidence_hint": "ativo e contexto",
                    },
                    {
                        "id": "registros_fotograficos",
                        "title": "Registros fotograficos",
                        "prompt": "registre fotos principais",
                        "evidence_hint": "vista geral e detalhe",
                    },
                ],
            },
        )
        banco.add(laudo)
        banco.flush()
        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=int(laudo.id),
                    remetente_id=usuario.id,
                    tipo=TipoMensagem.USER.value,
                    conteudo="Ativo identificado e contexto tecnico registrado em campo.",
                ),
                MensagemLaudo(
                    laudo_id=int(laudo.id),
                    remetente_id=usuario.id,
                    tipo=TipoMensagem.USER.value,
                    conteudo="[imagem]",
                ),
            ]
        )
        banco.commit()
        return int(laudo.id)


def test_report_pack_catalogado_materializado_usa_fallback_estruturado(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    laudo_id = _criar_laudo_catalogado_nr33(ambiente_critico)

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None

        draft = build_report_pack_draft_for_laudo(banco=banco, laudo=laudo)

    assert draft is not None
    assert draft["modeled"] is True
    assert draft["template_key"] == "nr33_espaco_confinado"
    assert draft["family"] == "nr33_avaliacao_espaco_confinado"
    assert draft["structured_data_candidate"] == _payload_catalogado_nr33()
    assert draft["telemetry"]["modeled_strategy"] == "catalog_structured_payload_fallback"
    assert draft["quality_gates"]["missing_evidence"] == []
    assert "2 foto(s)" in str(draft["analysis_basis"]["coverage_summary"])
    assert len(draft["analysis_basis"]["photo_evidence"]) == 2
    assert len(draft["analysis_basis"]["document_evidence"]) == 1
    assert draft["analysis_basis"]["context_messages"][0]["text"].startswith(
        "Tanque TQ-11 avaliado"
    )
    assert draft["pre_laudo_outline"]["status"] == "ready_for_finalization"
    assert draft["pre_laudo_outline"]["ready_for_structured_form"] is True
    assert draft["pre_laudo_outline"]["ready_for_finalization"] is True
    assert draft["pre_laudo_document"]["artifact_snapshot"]["has_family_schema"] is True
    assert draft["pre_laudo_document"]["artifact_snapshot"]["has_laudo_output_seed"] is True
    assert draft["pre_laudo_document"]["required_slots"][0]["label"]
    assert any(
        item["title"] == "Base da família"
        for item in draft["pre_laudo_document"]["document_flow"]
    )
    assert any(
        item["title"] == "Identificacao"
        for item in draft["pre_laudo_document"]["document_sections"]
    )
    assert draft["pre_laudo_outline"]["filled_field_count"] > 0
    assert draft["pre_laudo_outline"]["missing_field_count"] == 0
    assert all(
        item.get("code") != "report_pack_not_modeled"
        for item in draft["quality_gates"]["missing_evidence"]
    )


def test_report_pack_guidado_sem_catalogo_explicito_usa_familia_padrao_do_template(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    laudo_id = _criar_laudo_guia_com_familia_padrao(
        ambiente_critico,
        tipo_template="nr33_espaco_confinado",
        setor_industrial="NR33 Espaco Confinado",
    )

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None

        draft = build_report_pack_draft_for_laudo(banco=banco, laudo=laudo)

    assert draft is not None
    assert draft["modeled"] is True
    assert draft["template_key"] == "nr33_espaco_confinado"
    assert draft["family"] == "nr33_avaliacao_espaco_confinado"
    assert draft["telemetry"]["modeled_strategy"] == "catalog_structured_payload_fallback"
    assert draft["pre_laudo_document"]["artifact_snapshot"]["has_family_schema"] is True
    assert draft["pre_laudo_document"]["artifact_snapshot"]["has_template_seed"] is True
    assert draft["pre_laudo_document"]["artifact_snapshot"]["has_laudo_output_seed"] is True


def test_report_pack_guidado_loto_sem_catalogo_explicito_usa_familia_dedicada(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    laudo_id = _criar_laudo_guia_com_familia_padrao(
        ambiente_critico,
        tipo_template="loto",
        setor_industrial="NR10 LOTO",
    )

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None

        draft = build_report_pack_draft_for_laudo(banco=banco, laudo=laudo)

    assert draft is not None
    assert draft["modeled"] is True
    assert draft["template_key"] == "loto"
    assert draft["family"] == "nr10_implantacao_loto"
    assert draft["pre_laudo_document"]["artifact_snapshot"]["has_family_schema"] is True
    assert draft["pre_laudo_document"]["artifact_snapshot"]["has_template_seed"] is True
    assert draft["pre_laudo_document"]["artifact_snapshot"]["has_laudo_output_seed"] is True


def test_gate_qualidade_catalogado_aproveita_report_pack_estruturado(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    laudo_id = _criar_laudo_catalogado_nr33(ambiente_critico)

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None

        resultado = avaliar_gate_qualidade_laudo(banco, laudo)

    assert resultado["aprovado"] is True
    assert resultado["report_pack_draft"]["modeled"] is True
    assert resultado["report_pack_draft"]["quality_gates"]["missing_evidence"] == []
    assert not any(
        item["id"] == "report_pack_not_modeled"
        for item in resultado["itens"]
    )
    report_pack_item = next(
        item for item in resultado["itens"] if item["id"] == "report_pack_incremental"
    )
    assert report_pack_item["status"] == "ok"


def test_gate_qualidade_catalogado_expoe_override_humano_para_foto_faltante(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    laudo_id = _criar_laudo_catalogado_nr33(
        ambiente_critico,
        quantidade_fotos=1,
    )

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None

        resultado = avaliar_gate_qualidade_laudo(banco, laudo)

    assert resultado["aprovado"] is False
    policy = resultado["human_override_policy"]
    assert policy["available"] is True
    assert (
        "evidencia_complementar_substituida_por_registro_textual_com_rastreabilidade"
        in policy["matched_override_cases"]
    )
    assert any(
        item["id"] == "fotos_essenciais"
        for item in policy["overrideable_items"]
    )


def test_report_pack_catalogado_preserva_nome_original_das_fotos_vinculadas(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    expected_names = [
        "livre_01_painel_visao_geral.jpg",
        "livre_02_painel_nao_conforme.jpg",
    ]
    laudo_id = _criar_laudo_catalogado_nr33(
        ambiente_critico,
        photo_names=expected_names,
    )

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None

        draft = build_report_pack_draft_for_laudo(banco=banco, laudo=laudo)

    assert draft is not None
    photo_evidence = draft["analysis_basis"]["photo_evidence"]
    assert [item["reference"] for item in photo_evidence] == expected_names
    assert [item["original_name"] for item in photo_evidence] == expected_names
    assert photo_evidence[0]["caption"] == expected_names[0]


def test_pre_laudo_prompt_context_resume_pendencias_e_perguntas() -> None:
    contexto = build_pre_laudo_prompt_context(
        {
            "status": "needs_completion",
            "analysis_summary": "2 fotos e 1 documento ja vinculados ao caso.",
            "ready_for_finalization": False,
            "final_validation_mode": "mesa_required",
            "filled_field_count": 6,
            "missing_field_count": 2,
            "missing_highlights": [
                {"path": "identificacao.tag", "label": "Identificacao do vaso"},
                {"path": "conclusao.status", "label": "Conclusao final"},
            ],
            "next_questions": [
                "Confirme a TAG do ativo inspecionado.",
                "Qual e a conclusao final do caso: aprovado, reprovado ou pendente?",
            ],
        },
        template_key="nr13",
        guided_context={
            "step_id": "contexto_vistoria",
            "step_title": "Contexto da vistoria",
            "attachment_kind": "image",
        },
    )

    assert "[pre_laudo_operacional]" in contexto
    assert "needs_completion" in contexto
    assert "NR-13 Inspecoes e Integridade" in contexto
    assert "Contexto da vistoria" in contexto
    assert "Identificacao do vaso" in contexto
    assert "Qual e a conclusao final do caso" in contexto
