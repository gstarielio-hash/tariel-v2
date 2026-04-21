from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.domains.chat.laudo_service as laudo_service
import app.domains.revisor.service_messaging as service_messaging
from app.domains.mesa.service import montar_pacote_mesa_laudo
from app.shared.database import (
    ApprovedCaseSnapshot,
    Base,
    Empresa,
    EvidenceValidation,
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    OperationalEvent,
    OperationalIrregularity,
    StatusLaudo,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)
from app.shared.inspection_history import (
    build_clone_from_last_inspection_seed,
    build_inspection_history_summary,
)
from app.shared.operational_memory import (
    abrir_irregularidade_operacional,
    build_family_operational_memory_summary,
    registrar_evento_operacional,
    registrar_snapshot_aprovado,
    registrar_validacao_evidencia,
    resolver_irregularidade_operacional,
)
from app.shared.operational_memory_contracts import (
    ApprovedCaseSnapshotInput,
    EvidenceValidationInput,
    OperationalEventInput,
    OperationalIrregularityInput,
    OperationalIrregularityResolutionInput,
)


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)


def _seed_case_context(banco: Session) -> dict[str, int | str]:
    empresa = Empresa(nome_fantasia="Empresa Wave 1", cnpj="12345678000197")
    banco.add(empresa)
    banco.flush()

    inspetor = Usuario(
        empresa_id=empresa.id,
        nome_completo="Inspetor Wave 1",
        email="inspetor-wave1@tariel.test",
        senha_hash="hash",
        nivel_acesso=int(NivelAcesso.INSPETOR),
    )
    revisor = Usuario(
        empresa_id=empresa.id,
        nome_completo="Revisor Wave 1",
        email="revisor-wave1@tariel.test",
        senha_hash="hash",
        nivel_acesso=int(NivelAcesso.REVISOR),
    )
    banco.add_all([inspetor, revisor])
    banco.flush()

    laudo = Laudo(
        empresa_id=empresa.id,
        usuario_id=inspetor.id,
        setor_industrial="Industrial",
        tipo_template="nr13_inspecao_caldeira",
        catalog_family_key="nr13_inspecao_caldeira",
        catalog_family_label="NR13 Inspecao Caldeira",
        status_conformidade=StatusLaudo.CONFORME.value,
        status_revisao=StatusRevisao.APROVADO.value,
        codigo_hash="wave1hash001",
    )
    banco.add(laudo)
    banco.flush()

    return {
        "empresa_id": empresa.id,
        "inspetor_id": inspetor.id,
        "revisor_id": revisor.id,
        "laudo_id": laudo.id,
        "family_key": "nr13_inspecao_caldeira",
    }


def test_operational_memory_wave1_persiste_snapshot_evento_validacao_e_irregularidade() -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as banco:
        contexto = _seed_case_context(banco)

        snapshot = registrar_snapshot_aprovado(
            banco,
            ApprovedCaseSnapshotInput(
                laudo_id=int(contexto["laudo_id"]),
                approved_by_id=int(contexto["revisor_id"]),
                laudo_output_snapshot={"conclusao": {"status": "conforme"}},
                evidence_manifest=[{"evidence_key": "foto-001", "accepted": True}],
                mesa_resolution_summary={"decision": "approved"},
                technical_tags=["caldeira", "placa_ok"],
            ),
        )
        evento = registrar_evento_operacional(
            banco,
            OperationalEventInput(
                laudo_id=int(contexto["laudo_id"]),
                event_type="foto_borrada",
                event_source="quality_gate",
                severity="aviso",
                evidence_key="foto-001",
                event_metadata={"reason": "blur_detected"},
            ),
        )
        validacao = registrar_validacao_evidencia(
            banco,
            EvidenceValidationInput(
                laudo_id=int(contexto["laudo_id"]),
                evidence_key="foto-001",
                component_type="placa_identificacao",
                view_angle="close_up",
                quality_score=44,
                coherence_score=92,
                operational_status="operacional_irregular",
                mesa_status="pendente",
                failure_reasons=["borrada"],
            ),
        )
        irregularidade = abrir_irregularidade_operacional(
            banco,
            OperationalIrregularityInput(
                laudo_id=int(contexto["laudo_id"]),
                irregularity_type="image_blurry",
                severity="warning",
                detected_by="mesa",
                detected_by_user_id=int(contexto["revisor_id"]),
                source_event_id=evento.id,
                validation_id=validacao.id,
                evidence_key="foto-001",
                details={"required_action": "retirar nova foto"},
            ),
        )

        validacao_atualizada = registrar_validacao_evidencia(
            banco,
            EvidenceValidationInput(
                laudo_id=int(contexto["laudo_id"]),
                evidence_key="foto-001",
                component_type="placa_identificacao",
                view_angle="close_up",
                quality_score=95,
                coherence_score=98,
                operational_status="operacional_ok",
                mesa_status="aceita_mesa",
                failure_reasons=[],
                replacement_evidence_key="foto-001b",
                validated_by_user_id=int(contexto["revisor_id"]),
            ),
        )
        irregularidade_resolvida = resolver_irregularidade_operacional(
            banco,
            irregularity_id=irregularidade.id,
            payload=OperationalIrregularityResolutionInput(
                resolution_mode="nova_foto",
                resolved_by_id=int(contexto["revisor_id"]),
                resolution_notes="Nova captura aceita pela Mesa.",
            ),
        )

        resumo = build_family_operational_memory_summary(
            banco,
            empresa_id=int(contexto["empresa_id"]),
            family_key=str(contexto["family_key"]),
        )

        assert snapshot.approval_version == 1
        assert snapshot.family_key == "nr13_inspecao_caldeira"
        assert evento.event_type == "image_blurry"
        assert validacao_atualizada.operational_status == "ok"
        assert validacao_atualizada.mesa_status == "accepted"
        assert irregularidade_resolvida.status == "resolved"
        assert resumo.approved_snapshot_count == 1
        assert resumo.operational_event_count == 1
        assert resumo.validated_evidence_count == 1
        assert resumo.open_irregularity_count == 0
        assert resumo.top_event_types[0].item_key == "image_blurry"
        assert resumo.top_event_types[0].count == 1


def test_operational_memory_wave1_auto_incrementa_snapshot_por_laudo() -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as banco:
        contexto = _seed_case_context(banco)

        primeiro = registrar_snapshot_aprovado(
            banco,
            ApprovedCaseSnapshotInput(
                laudo_id=int(contexto["laudo_id"]),
                laudo_output_snapshot={"versao": 1},
            ),
        )
        segundo = registrar_snapshot_aprovado(
            banco,
            ApprovedCaseSnapshotInput(
                laudo_id=int(contexto["laudo_id"]),
                laudo_output_snapshot={"versao": 2},
            ),
        )

        assert primeiro.approval_version == 1
        assert segundo.approval_version == 2


def test_operational_memory_wave1_clone_e_diff_usam_snapshot_aprovado_anterior() -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as banco:
        contexto = _seed_case_context(banco)

        registrar_snapshot_aprovado(
            banco,
            ApprovedCaseSnapshotInput(
                laudo_id=int(contexto["laudo_id"]),
                approved_by_id=int(contexto["revisor_id"]),
                laudo_output_snapshot={
                    "codigo_hash": "basehash001",
                    "dados_formulario": {
                        "cliente": "Empresa Wave 1",
                        "local_inspecao": "Casa de caldeiras",
                        "identificacao": {
                            "tag": "CAL-01",
                            "serial": "SER-9911",
                        },
                        "conclusao": {
                            "status": "conforme",
                        },
                    },
                },
                technical_tags=["caldeira", "cal-01"],
            ),
        )

        clone_seed = build_clone_from_last_inspection_seed(
            banco,
            empresa_id=int(contexto["empresa_id"]),
            family_key=str(contexto["family_key"]),
            current_payload={
                "cliente": "Empresa Wave 1",
                "identificacao": {"tag": "CAL-01"},
            },
        )

        novo_laudo = Laudo(
            empresa_id=int(contexto["empresa_id"]),
            usuario_id=int(contexto["inspetor_id"]),
            setor_industrial="Industrial",
            tipo_template="nr13_inspecao_caldeira",
            catalog_family_key="nr13_inspecao_caldeira",
            catalog_family_label="NR13 Inspecao Caldeira",
            status_conformidade=StatusLaudo.PENDENTE.value,
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash="wave1hash002",
            dados_formulario={
                "cliente": "Empresa Wave 1",
                "local_inspecao": "Casa de caldeiras bloco B",
                "identificacao": {
                    "tag": "CAL-01",
                    "serial": "SER-9911A",
                },
                "conclusao": {
                    "status": "ajuste",
                },
            },
        )
        banco.add(novo_laudo)
        banco.flush()

        historico = build_inspection_history_summary(
            banco,
            laudo=novo_laudo,
        )

        assert clone_seed is not None
        assert clone_seed["matched_by"] == "asset_identity"
        assert clone_seed["source_codigo_hash"] == "basehash001"
        assert clone_seed["prefilled_field_count"] >= 3
        assert clone_seed["prefill_data"]["identificacao"]["serial"] == "SER-9911"
        assert "conclusao" not in clone_seed["prefill_data"]

        assert historico is not None
        assert historico["source_codigo_hash"] == "basehash001"
        assert historico["diff"]["changed_count"] >= 2
        assert historico["diff"]["identity_change_count"] >= 1
        assert any(
            item["path"] == "identificacao.serial"
            for item in historico["diff"]["highlights"]
        )
        assert any(
            item["block_key"] == "identificacao"
            for item in historico["diff"]["block_highlights"]
        )


def test_operational_memory_wave1_contracts_normalizam_aliases() -> None:
    evento = OperationalEventInput(laudo_id=1, event_type="foto_escura", event_source="ia", severity="critico")
    validacao = EvidenceValidationInput(
        laudo_id=1,
        evidence_key="foto-1",
        operational_status="operacional_irregular",
        mesa_status="aceita_mesa",
        failure_reasons=["borrada", "borrada", " "],
    )
    resolucao = OperationalIrregularityResolutionInput(resolution_mode="falso_positivo")

    assert evento.event_type == "image_dark"
    assert evento.event_source == "chat_ia"
    assert evento.severity == "blocker"
    assert validacao.operational_status == "irregular"
    assert validacao.mesa_status == "accepted"
    assert validacao.failure_reasons == ["borrada"]
    assert resolucao.resolution_mode == "dismissed_false_positive"


def test_operational_memory_wave1_aprovacao_da_mesa_registra_snapshot(monkeypatch) -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as banco:
        contexto = _seed_case_context(banco)
        laudo = banco.get(Laudo, int(contexto["laudo_id"]))
        assert laudo is not None
        laudo.status_revisao = StatusRevisao.AGUARDANDO.value
        laudo.dados_formulario = {"conclusao": {"status": "conforme"}}
        laudo.report_pack_draft_json = {
            "modeled": True,
            "quality_gates": {"final_validation_mode": "mesa_required"},
            "pre_laudo_outline": {
                "status": "needs_completion",
                "analysis_summary": "Base inicial do caso consolidada no mobile.",
                "ready_for_structured_form": True,
                "ready_for_finalization": False,
                "final_validation_mode": "mesa_required",
                "filled_field_count": 5,
                "missing_field_count": 2,
                "missing_highlights": [
                    {
                        "path": "conclusao.status",
                        "label": "Conclusao / Status",
                    }
                ],
                "next_questions": [
                    "Qual é a conclusão final do caso: aprovado, reprovado ou pendente?"
                ],
            },
            "image_slots": [
                {
                    "slot": "foto_placa",
                    "title": "Foto da placa",
                    "status": "resolved",
                    "required": True,
                    "resolved_evidence_id": "msg:501",
                    "resolved_caption": "Placa de identificacao",
                    "missing_evidence": [],
                }
            ],
        }
        banco.flush()

        monkeypatch.setattr(service_messaging, "record_report_pack_review_decision", lambda **_kwargs: None)

        resultado = service_messaging.avaliar_laudo_revisor(
            banco,
            laudo_id=int(contexto["laudo_id"]),
            empresa_id=int(contexto["empresa_id"]),
            revisor_id=int(contexto["revisor_id"]),
            revisor_nome="Revisor Wave 1",
            acao="aprovar",
            motivo="",
            resposta_api=True,
            modo_schemathesis=False,
        )

        snapshots = banco.query(ApprovedCaseSnapshot).filter(ApprovedCaseSnapshot.laudo_id == int(contexto["laudo_id"])).all()

        assert resultado.status_revisao == StatusRevisao.APROVADO.value
        assert len(snapshots) == 1
        assert snapshots[0].document_outcome == "approved_by_mesa"
        assert snapshots[0].approval_version == 1
        assert snapshots[0].laudo_output_snapshot["pre_laudo_summary"]["status"] == "needs_completion"
        assert (
            snapshots[0].laudo_output_snapshot["pre_laudo_summary"]["next_questions"][0]
            == "Qual é a conclusão final do caso: aprovado, reprovado ou pendente?"
        )


def test_operational_memory_wave1_pendencia_reaberta_abre_irregularidade_e_resolucao_fecha() -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as banco:
        contexto = _seed_case_context(banco)
        laudo = banco.get(Laudo, int(contexto["laudo_id"]))
        assert laudo is not None
        laudo.status_revisao = StatusRevisao.AGUARDANDO.value
        mensagem = MensagemLaudo(
            laudo_id=int(contexto["laudo_id"]),
            remetente_id=int(contexto["revisor_id"]),
            tipo=TipoMensagem.HUMANO_ENG.value,
            conteudo="Refazer bloco de evidencias fotograficas.",
            lida=True,
        )
        banco.add(mensagem)
        banco.flush()

        resultado_reabertura = service_messaging.atualizar_pendencia_mesa_revisor_status(
            banco,
            laudo_id=int(contexto["laudo_id"]),
            empresa_id=int(contexto["empresa_id"]),
            mensagem_id=int(mensagem.id),
            lida=False,
            revisor_id=int(contexto["revisor_id"]),
        )
        irregularidade = banco.query(OperationalIrregularity).filter(OperationalIrregularity.laudo_id == int(contexto["laudo_id"])).one()
        evento = banco.query(OperationalEvent).filter(OperationalEvent.laudo_id == int(contexto["laudo_id"])).one()

        resultado_resolucao = service_messaging.atualizar_pendencia_mesa_revisor_status(
            banco,
            laudo_id=int(contexto["laudo_id"]),
            empresa_id=int(contexto["empresa_id"]),
            mensagem_id=int(mensagem.id),
            lida=True,
            revisor_id=int(contexto["revisor_id"]),
        )
        banco.refresh(irregularidade)

        assert resultado_reabertura.lida is False
        assert evento.event_type == "field_reopened"
        assert irregularidade.irregularity_type == "field_reopened"
        assert irregularidade.status == "resolved"
        assert resultado_resolucao.lida is True


def test_operational_memory_wave1_gate_qualidade_persiste_validacoes(monkeypatch) -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as banco:
        contexto = _seed_case_context(banco)
        laudo = banco.get(Laudo, int(contexto["laudo_id"]))
        assert laudo is not None
        usuario = SimpleNamespace(id=int(contexto["inspetor_id"]))

        monkeypatch.setattr(laudo_service, "obter_laudo_do_inspetor", lambda *_args, **_kwargs: laudo)

        resultado_inicial = {
            "codigo": "GATE_QUALIDADE_REPROVADO",
            "aprovado": False,
            "mensagem": "Falta evidencia obrigatoria.",
            "tipo_template": "nr13_inspecao_caldeira",
            "resumo": {"fotos": 0, "evidencias": 1},
            "faltantes": [{"id": "fotos_essenciais"}],
            "report_pack_draft": {
                "modeled": True,
                "image_slots": [
                    {
                        "slot": "foto_placa",
                        "title": "Foto da placa",
                        "status": "pending",
                        "required": True,
                        "missing_evidence": ["foto_obrigatoria_ausente"],
                    }
                ],
                "quality_gates": {
                    "missing_evidence": [
                        {
                            "code": "nr13_documento_base_missing",
                            "kind": "structured_form",
                            "message": "Documento base ainda nao foi materializado.",
                        }
                    ]
                },
            },
        }
        monkeypatch.setattr(laudo_service, "avaliar_gate_qualidade_laudo", lambda *_args, **_kwargs: resultado_inicial)

        payload, status_code = laudo_service.obter_gate_qualidade_laudo_resposta(
            laudo_id=int(contexto["laudo_id"]),
            usuario=usuario,
            banco=banco,
        )

        slot_validacao = banco.query(EvidenceValidation).filter(EvidenceValidation.evidence_key == "slot:foto_placa").one()
        gate_validacao = (
            banco.query(EvidenceValidation)
            .filter(EvidenceValidation.evidence_key == "gate:structured_form:nr13_documento_base_missing")
            .one()
        )

        assert status_code == 422
        assert payload["codigo"] == "GATE_QUALIDADE_REPROVADO"
        assert slot_validacao.operational_status == "irregular"
        assert gate_validacao.operational_status == "irregular"

        resultado_aprovado = {
            "codigo": "GATE_QUALIDADE_OK",
            "aprovado": True,
            "mensagem": "Gate aprovado.",
            "tipo_template": "nr13_inspecao_caldeira",
            "resumo": {"fotos": 1, "evidencias": 3},
            "faltantes": [],
            "report_pack_draft": {
                "modeled": True,
                "image_slots": [
                    {
                        "slot": "foto_placa",
                        "title": "Foto da placa",
                        "status": "resolved",
                        "required": True,
                        "resolved_evidence_id": "msg:700",
                        "resolved_message_id": 700,
                        "resolved_caption": "Placa em foco",
                        "missing_evidence": [],
                    }
                ],
                "quality_gates": {"missing_evidence": []},
            },
        }
        monkeypatch.setattr(laudo_service, "avaliar_gate_qualidade_laudo", lambda *_args, **_kwargs: resultado_aprovado)

        _payload_ok, status_code_ok = laudo_service.obter_gate_qualidade_laudo_resposta(
            laudo_id=int(contexto["laudo_id"]),
            usuario=usuario,
            banco=banco,
        )
        banco.refresh(slot_validacao)
        banco.refresh(gate_validacao)

        assert status_code_ok == 200
        assert slot_validacao.operational_status == "ok"
        assert slot_validacao.replacement_evidence_key == "msg:700"
        assert gate_validacao.operational_status == "ok"


def test_operational_memory_wave1_pacote_mesa_expoe_cobertura_historico_e_memoria() -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as banco:
        contexto = _seed_case_context(banco)
        laudo = banco.get(Laudo, int(contexto["laudo_id"]))
        assert laudo is not None
        laudo.dados_formulario = {
            "schema_type": "laudo_output",
            "family_key": "nr13_inspecao_caldeira",
            "identificacao": {
                "identificacao_equipamento": "Caldeira 01",
                "localizacao": "Casa de maquinas",
                "placa_identificacao": {
                    "descricao": "Placa visivel e legivel.",
                },
            },
            "inspecao_visual": {
                "condicao_geral": "Equipamento em operacao.",
                "pontos_de_corrosao": {
                    "descricao": "Oxidacao leve na regiao inferior.",
                },
            },
            "documentacao_e_registros": {
                "prontuario": {
                    "disponivel": False,
                    "referencias_texto": "Nao apresentado no momento da inspecao.",
                },
            },
            "conclusao": {
                "status": "ajuste",
                "conclusao_tecnica": "Necessita ajuste documental antes da liberacao final.",
            },
        }
        laudo.report_pack_draft_json = {
            "modeled": True,
            "image_slots": [
                {
                    "slot": "foto_placa",
                    "title": "Foto da placa",
                    "status": "resolved",
                    "required": True,
                    "resolved_evidence_id": "msg:800",
                    "resolved_caption": "Placa em foco",
                    "missing_evidence": [],
                },
                {
                    "slot": "foto_vista_geral",
                    "title": "Vista geral",
                    "status": "pending",
                    "required": True,
                    "missing_evidence": ["angulo_obrigatorio_faltando"],
                },
            ],
            "quality_gates": {
                "final_validation_mode": "mesa_required",
                "human_override": {
                    "scope": "quality_gate",
                    "applied_at": "2026-04-13T17:45:00+00:00",
                    "actor_user_id": int(contexto["inspetor_id"]),
                    "actor_name": "Inspetor Wave 1",
                    "reason": "A decisão humana manteve a conclusão com base em evidência textual rastreável.",
                },
                "human_override_history": [
                    {
                        "scope": "quality_gate",
                        "applied_at": "2026-04-13T17:45:00+00:00",
                        "actor_user_id": int(contexto["inspetor_id"]),
                        "actor_name": "Inspetor Wave 1",
                        "reason": "A decisão humana manteve a conclusão com base em evidência textual rastreável.",
                    }
                ],
                "missing_evidence": [
                    {
                        "code": "nr13_documento_base_missing",
                        "kind": "structured_form",
                        "message": "Documento base ainda nao foi materializado.",
                    }
                ],
            },
        }

        registrar_snapshot_aprovado(
            banco,
            ApprovedCaseSnapshotInput(
                laudo_id=int(contexto["laudo_id"]),
                approved_by_id=int(contexto["revisor_id"]),
                laudo_output_snapshot={"conclusao": {"status": "conforme"}},
            ),
        )
        registrar_evento_operacional(
            banco,
            OperationalEventInput(
                laudo_id=int(contexto["laudo_id"]),
                event_type="field_reopened",
                event_source="mesa",
                severity="warning",
                block_key="inspecao_visual",
            ),
        )
        registrar_validacao_evidencia(
            banco,
            EvidenceValidationInput(
                laudo_id=int(contexto["laudo_id"]),
                evidence_key="slot:foto_placa",
                component_type="placa_identificacao",
                view_angle="close_up",
                quality_score=98,
                coherence_score=96,
                operational_status="operacional_ok",
                mesa_status="aceita_mesa",
                replacement_evidence_key="msg:800",
            ),
        )
        registrar_validacao_evidencia(
            banco,
            EvidenceValidationInput(
                laudo_id=int(contexto["laudo_id"]),
                evidence_key="gate:structured_form:nr13_documento_base_missing",
                operational_status="operacional_irregular",
                mesa_status="pendente",
                failure_reasons=["documento base ausente"],
            ),
        )
        abrir_irregularidade_operacional(
            banco,
            OperationalIrregularityInput(
                laudo_id=int(contexto["laudo_id"]),
                irregularity_type="field_reopened",
                severity="warning",
                detected_by="mesa",
                detected_by_user_id=int(contexto["revisor_id"]),
                block_key="inspecao_visual",
                details={"required_action": "Refazer bloco fotografico"},
            ),
        )

        pacote = montar_pacote_mesa_laudo(banco, laudo=laudo)

        assert pacote.coverage_map is not None
        assert pacote.case_status == "approved"
        assert pacote.case_lifecycle_status == "aprovado"
        assert pacote.active_owner_role == "none"
        assert pacote.status_visual_label == "Aprovado / Responsavel: conclusao"
        assert pacote.coverage_map.total_required == 3
        assert pacote.coverage_map.total_accepted == 1
        assert pacote.coverage_map.total_irregular == 1
        assert pacote.coverage_map.total_missing == 1
        assert {
            item.evidence_key
            for item in pacote.coverage_map.items
            if item.status in {"missing", "irregular"}
        } == {
            "slot:foto_vista_geral",
            "gate:structured_form:nr13_documento_base_missing",
        }
        assert pacote.historico_refazer_inspetor[0].irregularity_type == "field_reopened"
        assert pacote.historico_refazer_inspetor[0].summary == "Refazer bloco fotografico"
        assert pacote.memoria_operacional_familia is not None
        assert pacote.memoria_operacional_familia.family_key == "nr13_inspecao_caldeira"
        assert pacote.memoria_operacional_familia.approved_snapshot_count == 1
        assert pacote.human_override_summary is not None
        assert pacote.human_override_summary["latest"]["actor_name"] == "Inspetor Wave 1"
        assert pacote.revisao_por_bloco is not None
        assert pacote.revisao_por_bloco.returned_blocks == 1
        assert pacote.revisao_por_bloco.attention_blocks >= 1
        blocos = {item.block_key: item for item in pacote.revisao_por_bloco.items}
        assert blocos["inspecao_visual"].review_status == "returned"
        assert blocos["inspecao_visual"].open_return_count == 1
        assert blocos["documentacao_e_registros"].review_status == "attention"
        assert blocos["documentacao_e_registros"].coverage_alert_count == 1


def test_montar_pacote_mesa_cria_item_gate_quando_validacao_nao_tem_base_previa() -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as banco:
        contexto = _seed_case_context(banco)
        laudo = banco.get(Laudo, int(contexto["laudo_id"]))
        assert laudo is not None

        registrar_validacao_evidencia(
            banco,
            EvidenceValidationInput(
                laudo_id=int(contexto["laudo_id"]),
                evidence_key="gate:structured_form:nr13_documento_base_missing",
                operational_status="operacional_irregular",
                mesa_status="pendente",
                failure_reasons=["documento base ausente"],
            ),
        )

        pacote = montar_pacote_mesa_laudo(banco, laudo=laudo)

        assert pacote.coverage_map is not None
        assert pacote.coverage_map.total_required == 1
        assert pacote.coverage_map.total_irregular == 1
        assert pacote.coverage_map.total_missing == 0
        item = next(
            item
            for item in pacote.coverage_map.items
            if item.evidence_key == "gate:structured_form:nr13_documento_base_missing"
        )
        assert item.kind == "gate_requirement"
        assert item.required is True
        assert item.status == "irregular"
        assert item.source_status == "pending"


def test_operational_memory_wave1_solicitacao_refazer_coverage_cria_pendencia_estruturada() -> None:
    SessionLocal = _session_factory()

    with SessionLocal() as banco:
        contexto = _seed_case_context(banco)
        laudo = banco.get(Laudo, int(contexto["laudo_id"]))
        assert laudo is not None
        laudo.status_revisao = StatusRevisao.AGUARDANDO.value

        resultado = service_messaging.solicitar_refazer_item_coverage_revisor(
            banco,
            laudo_id=int(contexto["laudo_id"]),
            empresa_id=int(contexto["empresa_id"]),
            revisor_id=int(contexto["revisor_id"]),
            revisor_nome="Revisor Wave 1",
            evidence_key="slot:foto_placa",
            title="Foto da placa",
            kind="image_slot",
            required=True,
            source_status="missing",
            operational_status="irregular",
            mesa_status="not_reviewed",
            component_type="placa_identificacao",
            view_angle="close_up",
            severity="warning",
            summary="Foto borrada para o ativo correto.",
            required_action="Reenviar imagem nitida da placa.",
            failure_reasons=["foto_borrada"],
        )

        mensagem = banco.get(MensagemLaudo, resultado.mensagem_id)
        irregularidade = (
            banco.query(OperationalIrregularity)
            .filter(OperationalIrregularity.laudo_id == int(contexto["laudo_id"]))
            .one()
        )

        assert mensagem is not None
        assert mensagem.tipo == TipoMensagem.HUMANO_ENG.value
        assert isinstance(mensagem.metadata_json, dict)
        assert mensagem.metadata_json["task_kind"] == "coverage_return_request"
        assert mensagem.metadata_json["evidence_key"] == "slot:foto_placa"
        assert resultado.mensagem_payload is not None
        assert resultado.mensagem_payload["operational_context"]["task_kind"] == "coverage_return_request"
        assert irregularidade.evidence_key == "slot:foto_placa"
        assert irregularidade.irregularity_type == "block_returned_to_inspector"
