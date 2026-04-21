from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.mesa.contracts import (
    AnexoPackItemPacoteMesa,
    AnexoPackPacoteMesa,
    CoverageMapItemPacoteMesa,
    CoverageMapPacoteMesa,
    EmissaoOficialAtualPacoteMesa,
    EmissaoOficialBlockerPacoteMesa,
    EmissaoOficialPacoteMesa,
    HistoricoRefazerInspetorItemPacoteMesa,
    HistoricoInspecaoDiffItemPacoteMesa,
    HistoricoInspecaoDiffPacoteMesa,
    HistoricoInspecaoPacoteMesa,
    MemoriaOperacionalFamiliaPacoteMesa,
    MemoriaOperacionalFrequenciaPacoteMesa,
    MensagemPacoteMesa,
    PacoteMesaLaudo,
    RevisaoPorBlocoItemPacoteMesa,
    RevisaoPorBlocoPacoteMesa,
    ResumoEvidenciasMesa,
    ResumoMensagensMesa,
    ResumoPendenciasMesa,
    RevisaoPacoteMesa,
    SignatarioGovernadoPacoteMesa,
    VerificacaoPublicaPacoteMesa,
)
from app.domains.cliente.portal_bridge import obter_laudo_completo_cliente
from app.domains.revisor.document_boundary import (
    ReviewDeskDocumentBoundaryResult,
    merge_reviewdesk_boundary_into_complete_payload,
)
from app.domains.revisor.mesa_api import obter_laudo_completo, obter_pacote_mesa_laudo
from app.shared.database import Laudo, NivelAcesso, StatusLaudo, StatusRevisao, Usuario
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.adapters.reviewdesk_package import adapt_reviewdesk_case_view_projection_to_legacy_package
from app.v2.contracts.projections import build_reviewdesk_case_view_projection


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=51,
        empresa_id=33,
        nivel_acesso=NivelAcesso.REVISOR.value,
    )


def _build_request(
    query_string: str = "",
    *,
    path: str = "/revisao/api/laudo/88/pacote",
) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": query_string.encode(),
            "state": {},
        }
    )


def _build_pacote() -> PacoteMesaLaudo:
    agora = datetime.now(timezone.utc)
    return PacoteMesaLaudo(
        laudo_id=88,
        codigo_hash="abc123ef",
        tipo_template="padrao",
        setor_industrial="NR Teste",
        status_revisao=StatusRevisao.AGUARDANDO.value,
        status_conformidade=StatusLaudo.PENDENTE.value,
        case_status="needs_reviewer",
        case_lifecycle_status="aguardando_mesa",
        case_workflow_mode="laudo_com_mesa",
        active_owner_role="mesa",
        allowed_next_lifecycle_statuses=[
            "em_revisao_mesa",
            "devolvido_para_correcao",
            "aprovado",
        ],
        allowed_surface_actions=["mesa_approve", "mesa_return"],
        status_visual_label="Aguardando mesa / Responsavel: mesa",
        criado_em=agora,
        atualizado_em=agora,
        tempo_em_campo_minutos=42,
        ultima_interacao_em=agora,
        inspetor_id=17,
        revisor_id=51,
        dados_formulario={"campo": "valor"},
        parecer_ia="Rascunho de apoio",
        resumo_mensagens=ResumoMensagensMesa(total=10, inspetor=4, ia=3, mesa=2, sistema_outros=1),
        resumo_evidencias=ResumoEvidenciasMesa(total=3, textuais=1, fotos=1, documentos=1),
        resumo_pendencias=ResumoPendenciasMesa(total=2, abertas=1, resolvidas=1),
        revisao_por_bloco=RevisaoPorBlocoPacoteMesa(
            total_blocks=3,
            ready_blocks=1,
            attention_blocks=1,
            returned_blocks=1,
            items=[
                RevisaoPorBlocoItemPacoteMesa(
                    block_key="identificacao",
                    title="Identificacao",
                    document_status="filled",
                    review_status="ready",
                    summary="Placa e localizacao registradas.",
                    filled_fields=3,
                    total_fields=3,
                    coverage_total=1,
                ),
                RevisaoPorBlocoItemPacoteMesa(
                    block_key="documentacao_e_registros",
                    title="Documentacao e registros",
                    document_status="partial",
                    review_status="attention",
                    summary="Prontuario nao apresentado.",
                    filled_fields=1,
                    total_fields=3,
                    coverage_total=1,
                    coverage_alert_count=1,
                    recommended_action="Anexar documento base valido.",
                ),
                RevisaoPorBlocoItemPacoteMesa(
                    block_key="inspecao_visual",
                    title="Inspecao visual",
                    document_status="filled",
                    review_status="returned",
                    summary="Nova captura de evidencia solicitada.",
                    filled_fields=2,
                    total_fields=2,
                    coverage_total=1,
                    open_return_count=1,
                    open_pendency_count=1,
                    latest_return_at=agora,
                    recommended_action="Reenviar foto nova e nitida.",
                ),
            ],
        ),
        coverage_map=CoverageMapPacoteMesa(
            total_required=3,
            total_collected=2,
            total_accepted=1,
            total_missing=1,
            total_irregular=0,
            final_validation_mode="mesa_required",
            items=[
                CoverageMapItemPacoteMesa(
                    evidence_key="slot:foto_placa",
                    title="Foto da placa",
                    kind="image_slot",
                    status="accepted",
                    required=True,
                    source_status="resolved",
                    operational_status="ok",
                )
            ],
        ),
        historico_inspecao=HistoricoInspecaoPacoteMesa(
            snapshot_id=5,
            source_laudo_id=44,
            source_codigo_hash="prev001",
            approved_at=agora,
            approval_version=2,
            document_outcome="approved",
            matched_by="asset_identity",
            match_score=18,
            prefilled_field_count=4,
            diff=HistoricoInspecaoDiffPacoteMesa(
                changed_count=2,
                added_count=1,
                removed_count=0,
                current_fields_count=6,
                reference_fields_count=5,
                summary="2 mudancas | 1 novo",
                highlights=[
                    HistoricoInspecaoDiffItemPacoteMesa(
                        path="identificacao.serial",
                        label="Identificacao / Serial",
                        change_type="changed",
                        previous_value="SER-001",
                        current_value="SER-002",
                    )
                ],
            ),
        ),
        verificacao_publica=VerificacaoPublicaPacoteMesa(
            codigo_hash="abc123ef",
            hash_short="123ef",
            verification_url="/app/public/laudo/verificar/abc123ef",
            qr_payload="/app/public/laudo/verificar/abc123ef",
            qr_image_data_uri="data:image/png;base64,ZmFrZQ==",
            empresa_nome="Empresa Demo",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            status_visual_label="Aguardando mesa / Responsavel: mesa",
            status_conformidade=StatusLaudo.PENDENTE.value,
            approved_at=agora,
            approval_version=2,
            document_outcome="approved",
        ),
        anexo_pack=AnexoPackPacoteMesa(
            total_items=4,
            total_required=2,
            total_present=4,
            missing_required_count=0,
            document_count=2,
            image_count=1,
            virtual_count=1,
            ready_for_issue=True,
            items=[
                AnexoPackItemPacoteMesa(
                    item_key="pdf_principal",
                    label="PDF principal emitido",
                    category="pdf",
                    required=True,
                    present=True,
                    source="laudo_runtime",
                )
            ],
        ),
        emissao_oficial=EmissaoOficialPacoteMesa(
            issue_status="ready_for_issue",
            issue_status_label="Pronto para emissão oficial",
            ready_for_issue=True,
            compatible_signatory_count=2,
            eligible_signatory_count=1,
            blocker_count=1,
            signature_status="ready",
            signature_status_label="Signatário governado pronto",
            verification_url="/app/public/laudo/verificar/abc123ef",
            pdf_present=True,
            public_verification_present=True,
            signatories=[
                SignatarioGovernadoPacoteMesa(
                    id=11,
                    nome="Eng. Tariel",
                    funcao="Responsável técnico",
                    registro_profissional="CREA 1234",
                    status="ready",
                    status_label="Pronto para emissão",
                    ativo=True,
                )
            ],
            blockers=[
                EmissaoOficialBlockerPacoteMesa(
                    code="example_warning",
                    title="Aviso residual",
                    message="Apenas para validar a serialização do contrato.",
                    blocking=False,
                )
            ],
            current_issue=EmissaoOficialAtualPacoteMesa(
                id=901,
                issue_number="TAR-20260417-0001",
                issue_state="issued",
                issue_state_label="Emitido oficialmente",
                primary_pdf_sha256="a" * 64,
                primary_pdf_storage_version="v0003",
                primary_pdf_storage_version_number=3,
                current_primary_pdf_sha256="b" * 64,
                current_primary_pdf_storage_version="v0004",
                current_primary_pdf_storage_version_number=4,
                primary_pdf_diverged=True,
                primary_pdf_comparison_status="diverged",
                reissue_of_issue_id=880,
                reissue_of_issue_number="TAR-20260410-0008",
                reissue_reason_codes=["primary_pdf_diverged"],
                reissue_reason_summary="Reemissão motivada por divergência do PDF principal.",
            ),
        ),
        historico_refazer_inspetor=[
            HistoricoRefazerInspetorItemPacoteMesa(
                id=7,
                irregularity_type="block_returned_to_inspector",
                severity="warning",
                status="resolved",
                detected_by="mesa",
                block_key="evidencias",
                evidence_key="slot:foto_placa",
                summary="Nova foto solicitada",
                resolution_mode="recaptured_evidence",
                detected_at=agora,
                resolved_at=agora,
                detected_by_user_name="Mesa",
                resolved_by_user_name="Mesa",
            )
        ],
        memoria_operacional_familia=MemoriaOperacionalFamiliaPacoteMesa(
            family_key="nr13_inspecao_caldeira",
            approved_snapshot_count=12,
            operational_event_count=34,
            validated_evidence_count=56,
            open_irregularity_count=2,
            latest_approved_at=agora,
            latest_event_at=agora,
            top_event_types=[MemoriaOperacionalFrequenciaPacoteMesa(item_key="field_reopened", count=5)],
            top_open_irregularities=[MemoriaOperacionalFrequenciaPacoteMesa(item_key="document_missing", count=2)],
        ),
        pendencias_abertas=[
            MensagemPacoteMesa(
                id=1,
                tipo="humano_eng",
                texto="Ajustar evidência",
                criado_em=agora,
                remetente_id=51,
                lida=False,
            )
        ],
        pendencias_resolvidas_recentes=[
            MensagemPacoteMesa(
                id=2,
                tipo="humano_eng",
                texto="Ajuste resolvido",
                criado_em=agora,
                remetente_id=51,
                lida=True,
            )
        ],
        whispers_recentes=[
            MensagemPacoteMesa(
                id=3,
                tipo="humano_insp",
                texto="Campo respondeu",
                criado_em=agora,
                remetente_id=17,
                lida=False,
                referencia_mensagem_id=1,
            )
        ],
        revisoes_recentes=[
            RevisaoPacoteMesa(
                numero_versao=1,
                origem="ia",
                resumo="Primeira revisão",
                confianca_geral="alta",
                criado_em=agora,
            )
        ],
    )


def test_shape_da_projecao_canonica_da_mesa() -> None:
    pacote = _build_pacote()
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "status_card": "aguardando",
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
        },
    )

    projection = build_reviewdesk_case_view_projection(
        case_snapshot=snapshot,
        pacote=pacote,
        actor_id=51,
        actor_role="revisor",
        source_channel="review_api",
    )

    dumped = projection.model_dump(mode="json")
    assert dumped["contract_name"] == "ReviewDeskCaseViewProjectionV1"
    assert dumped["case_id"] == "case:legacy-laudo:33:88"
    assert dumped["thread_id"] == "thread:legacy-laudo:33:88"
    assert dumped["document_id"] == "document:legacy-laudo:33:88"
    assert dumped["projection_audience"] == "mesa"
    assert dumped["payload"]["case_status"] == "needs_reviewer"
    assert dumped["payload"]["case_lifecycle_status"] == "aguardando_mesa"
    assert dumped["payload"]["case_workflow_mode"] == "laudo_com_mesa"
    assert dumped["payload"]["active_owner_role"] == "mesa"
    assert dumped["payload"]["allowed_next_lifecycle_statuses"] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert dumped["payload"]["human_validation_required"] is True
    assert dumped["payload"]["review_status"] == "pending_review"
    assert dumped["payload"]["document_status"] == "draft_document"
    assert dumped["payload"]["pending_open_count"] == 1
    assert dumped["payload"]["recent_whispers_count"] == 1
    assert dumped["payload"]["requires_reviewer_action"] is True
    assert dumped["payload"]["summary_pending"]["abertas"] == 1
    assert dumped["payload"]["revisao_por_bloco"]["returned_blocks"] == 1
    assert dumped["payload"]["revisao_por_bloco"]["items"][0]["block_key"] == "identificacao"
    assert dumped["payload"]["coverage_map"]["total_required"] == 3
    assert dumped["payload"]["inspection_history"]["source_codigo_hash"] == "prev001"
    assert dumped["payload"]["public_verification"]["verification_url"] == "/app/public/laudo/verificar/abc123ef"
    assert dumped["payload"]["public_verification"]["qr_image_data_uri"].startswith("data:image/png;base64,")
    assert dumped["payload"]["public_verification"]["status_visual_label"] == "Aguardando mesa / Responsavel: mesa"
    assert dumped["payload"]["anexo_pack"]["ready_for_issue"] is True
    assert dumped["payload"]["emissao_oficial"]["issue_status"] == "ready_for_issue"
    assert dumped["payload"]["emissao_oficial"]["current_issue"]["primary_pdf_diverged"] is True
    assert dumped["payload"]["emissao_oficial"]["current_issue"]["reissue_of_issue_number"] == "TAR-20260410-0008"
    assert dumped["payload"]["emissao_oficial"]["current_issue"]["reissue_reason_codes"] == ["primary_pdf_diverged"]
    assert dumped["payload"]["emissao_oficial"]["current_issue"]["current_primary_pdf_storage_version"] == "v0004"
    assert dumped["payload"]["historico_refazer_inspetor"][0]["irregularity_type"] == "block_returned_to_inspector"
    assert dumped["payload"]["memoria_operacional_familia"]["approved_snapshot_count"] == 12
    assert dumped["payload"]["collaboration"]["summary"]["open_pendency_count"] == 1
    assert dumped["payload"]["collaboration"]["summary"]["resolved_pendency_count"] == 1
    assert dumped["payload"]["collaboration"]["summary"]["recent_whisper_count"] == 1
    assert dumped["payload"]["collaboration"]["summary"]["unread_whisper_count"] == 1
    assert dumped["payload"]["collaboration"]["summary"]["requires_reviewer_attention"] is True
    assert dumped["payload"]["collaboration"]["open_pendencies"][0]["item_kind"] == "pendency"
    assert dumped["payload"]["collaboration"]["open_pendencies"][0]["message_kind"] == "mesa_pendency"
    assert dumped["payload"]["collaboration"]["open_pendencies"][0]["pendency_state"] == "open"
    assert dumped["payload"]["collaboration"]["recent_whispers"][0]["item_kind"] == "whisper"
    assert dumped["payload"]["collaboration"]["recent_whispers"][0]["message_kind"] == "inspector_whisper"
    assert dumped["payload"]["collaboration"]["recent_whispers"][0]["pendency_state"] == "not_applicable"
    assert dumped["payload"]["collaboration"]["recent_reviews"][0]["version"] == 1


def test_adapter_da_projecao_reconstroi_payload_legado_do_pacote() -> None:
    pacote = _build_pacote()
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "status_card": "aguardando",
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
        },
    )
    projection = build_reviewdesk_case_view_projection(
        case_snapshot=snapshot,
        pacote=pacote,
        actor_id=51,
        actor_role="revisor",
        source_channel="review_api",
    )

    adapted = adapt_reviewdesk_case_view_projection_to_legacy_package(
        projection=projection,
        expected_legacy_payload=pacote.model_dump(mode="json"),
    )

    assert adapted.compatible is True
    assert adapted.divergences == []
    assert adapted.payload["laudo_id"] == pacote.laudo_id
    assert adapted.payload["case_status"] == "needs_reviewer"
    assert adapted.payload["case_lifecycle_status"] == "aguardando_mesa"
    assert adapted.payload["active_owner_role"] == "mesa"
    assert adapted.payload["status_visual_label"] == "Aguardando mesa / Responsavel: mesa"
    assert adapted.payload["revisao_por_bloco"]["attention_blocks"] == 1
    assert adapted.payload["coverage_map"]["total_accepted"] == 1
    assert adapted.payload["anexo_pack"]["total_items"] == 4
    assert adapted.payload["emissao_oficial"]["eligible_signatory_count"] == 1
    assert adapted.payload["emissao_oficial"]["current_issue"]["primary_pdf_diverged"] is True
    assert adapted.payload["emissao_oficial"]["current_issue"]["reissue_of_issue_number"] == "TAR-20260410-0008"
    assert adapted.payload["emissao_oficial"]["current_issue"]["reissue_reason_codes"] == ["primary_pdf_diverged"]
    assert adapted.payload["historico_refazer_inspetor"][0]["status"] == "resolved"
    assert adapted.payload["memoria_operacional_familia"]["family_key"] == "nr13_inspecao_caldeira"
    assert adapted.payload["collaboration"]["summary"]["open_pendency_count"] == 1
    assert adapted.payload["collaboration"]["summary"]["recent_whisper_count"] == 1


def test_merge_do_completo_prefere_summary_do_boundary_quando_projection_compativel() -> None:
    legacy_payload = {
        "id": 88,
        "hash": "legacy0",
        "setor": "Legado",
        "status": StatusRevisao.RASCUNHO.value,
        "case_status": "legacy_case",
        "case_lifecycle_status": "legacy_lifecycle",
        "case_workflow_mode": "legacy_mode",
        "active_owner_role": "mesa",
        "allowed_next_lifecycle_statuses": [],
        "allowed_surface_actions": [],
        "tipo_template": "padrao",
        "criado_em": "01/01/2026 09:00",
        "historico": [],
        "whispers": [],
        "aprendizados_visuais": [],
        "historico_paginado": {"incluir_historico": False, "cursor_proximo": None, "tem_mais": False, "limite": 60},
    }
    boundary_result = ReviewDeskDocumentBoundaryResult(
        pacote_carregado=SimpleNamespace(),
        payload_publico={
            "laudo_id": 88,
            "codigo_hash": "abc123ef",
            "setor_industrial": "NR Teste",
            "status_revisao": StatusRevisao.AGUARDANDO.value,
            "case_status": "needs_reviewer",
            "case_lifecycle_status": "aguardando_mesa",
            "case_workflow_mode": "laudo_com_mesa",
            "active_owner_role": "mesa",
            "allowed_next_lifecycle_statuses": ["aprovado"],
            "allowed_surface_actions": ["review_approve"],
            "tipo_template": "padrao",
            "criado_em": "2026-04-15T12:30:00+00:00",
            "reviewer_case_view": {"contract_name": "ReviewDeskCaseViewProjectionV1"},
            "reviewer_case_view_preferred": True,
        },
        projection_compatible=True,
    )

    payload = merge_reviewdesk_boundary_into_complete_payload(
        legacy_payload=legacy_payload,
        boundary_result=boundary_result,
    )

    assert payload["id"] == 88
    assert payload["hash"] == "c123ef"
    assert payload["setor"] == "NR Teste"
    assert payload["status"] == StatusRevisao.AGUARDANDO.value
    assert payload["case_lifecycle_status"] == "aguardando_mesa"
    assert payload["active_owner_role"] == "mesa"
    assert payload["allowed_surface_actions"] == ["review_approve"]
    esperado_criado_em = (
        datetime.fromisoformat("2026-04-15T12:30:00+00:00").astimezone().strftime("%d/%m/%Y %H:%M")
    )
    assert payload["criado_em"] == esperado_criado_em
    assert payload["reviewer_case_view_preferred"] is True
    assert payload["reviewer_case_view"]["contract_name"] == "ReviewDeskCaseViewProjectionV1"


def test_merge_do_completo_mantem_view_sem_promover_quando_projection_diverge() -> None:
    legacy_payload = {
        "id": 77,
        "hash": "legacy7",
        "setor": "Legado",
        "status": StatusRevisao.RASCUNHO.value,
        "historico": [],
        "whispers": [],
        "aprendizados_visuais": [],
        "historico_paginado": {"incluir_historico": False, "cursor_proximo": None, "tem_mais": False, "limite": 60},
    }
    boundary_result = ReviewDeskDocumentBoundaryResult(
        pacote_carregado=SimpleNamespace(),
        payload_publico={
            "laudo_id": 77,
            "codigo_hash": "zzz999aa",
            "setor_industrial": "NR Teste",
            "status_revisao": StatusRevisao.AGUARDANDO.value,
            "reviewer_case_view": {"contract_name": "ReviewDeskCaseViewProjectionV1"},
            "reviewer_case_view_preferred": False,
        },
        projection_compatible=False,
        projection_divergences=["status_revisao"],
    )

    payload = merge_reviewdesk_boundary_into_complete_payload(
        legacy_payload=legacy_payload,
        boundary_result=boundary_result,
    )

    assert payload["reviewer_case_view_preferred"] is False
    assert payload["reviewer_case_view"]["contract_name"] == "ReviewDeskCaseViewProjectionV1"


def test_endpoint_pacote_da_mesa_passa_pela_projecao_quando_flag_ativa(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo = Laudo(
            empresa_id=revisor.empresa_id,
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        request_base = _build_request()
        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_ENVELOPES", raising=False)
        monkeypatch.delenv("TARIEL_V2_REVIEW_DESK_PROJECTION", raising=False)
        response_base = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_base,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_base = json.loads(response_base.body)

        request_projection = _build_request()
        monkeypatch.setenv("TARIEL_V2_REVIEW_DESK_PROJECTION", "1")
        response_projection = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_projection,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_projection = json.loads(response_projection.body)

    payload_base_sem_view = {k: v for k, v in payload_base.items() if k != "reviewer_case_view"}
    payload_projection_sem_view = {k: v for k, v in payload_projection.items() if k != "reviewer_case_view"}

    assert payload_projection_sem_view == payload_base_sem_view
    assert payload_projection["reviewer_case_view"]["contract_name"] == "ReviewDeskCaseViewProjectionV1"
    assert payload_base["reviewer_case_view"]["contract_name"] == "ReviewDeskCaseViewProjectionV1"
    assert payload_base["collaboration"]["summary"]["open_pendency_count"] == 0
    assert payload_projection["collaboration"]["summary"]["requires_reviewer_attention"] is True
    assert request_projection.state.v2_reviewdesk_projection_result["compatible"] is True
    assert request_projection.state.v2_reviewdesk_projection_result["used_projection"] is True
    assert (
        request_projection.state.v2_reviewdesk_projection_result["projection"]["contract_name"]
        == "ReviewDeskCaseViewProjectionV1"
    )
    assert request_projection.state.v2_case_core_snapshot["canonical_status"] == "needs_reviewer"
    assert request_projection.state.v2_case_core_snapshot["case_lifecycle_status"] == "aguardando_mesa"
    assert request_projection.state.v2_case_core_snapshot["workflow_mode"] == "laudo_com_mesa"
    assert request_projection.state.v2_technical_case_snapshot["case_state"] == "needs_reviewer"
    assert request_projection.state.v2_technical_case_snapshot["case_lifecycle_status"] == "aguardando_mesa"
    assert request_projection.state.v2_technical_case_snapshot["current_review_state"] == "pending_review"


def test_endpoint_pacote_da_mesa_preserva_owner_canonico_quando_caso_volta_ao_inspetor(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo = Laudo(
            empresa_id=revisor.empresa_id,
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.REJEITADO.value,
            codigo_hash=uuid.uuid4().hex,
            revisado_por=revisor.id,
            motivo_rejeicao="Refazer a evidencia.",
        )
        banco.add(laudo)
        banco.flush()

        request_projection = _build_request(path=f"/revisao/api/laudo/{laudo.id}/pacote")
        monkeypatch.setenv("TARIEL_V2_REVIEW_DESK_PROJECTION", "1")
        response_projection = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_projection,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_projection = json.loads(response_projection.body)

    assert payload_projection["case_lifecycle_status"] == "devolvido_para_correcao"
    assert payload_projection["active_owner_role"] == "inspetor"
    assert payload_projection["allowed_surface_actions"] == ["chat_finalize"]
    assert payload_projection["revisor_id"] is None
    assert payload_projection["reviewer_case_view"]["payload"]["active_owner_role"] == "inspetor"
    assert request_projection.state.v2_reviewdesk_projection_result["compatible"] is True


def test_endpoint_laudo_completo_embute_reviewer_case_view_por_padrao_canonico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo = Laudo(
            empresa_id=revisor.empresa_id,
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        request = _build_request(
            "incluir_historico=true",
            path=f"/revisao/api/laudo/{laudo.id}/completo",
        )
        monkeypatch.delenv("TARIEL_V2_REVIEW_DESK_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_REVIEW_DESK_PROJECTION_PREFER", raising=False)

        response = asyncio.run(
            obter_laudo_completo(
                laudo_id=laudo.id,
                request=request,
                incluir_historico=True,
                cursor=None,
                limite=60,
                usuario=revisor,
                banco=banco,
            )
        )
        payload = json.loads(response.body)

    assert payload["reviewer_case_view_preferred"] is True
    assert payload["reviewer_case_view"]["contract_name"] == "ReviewDeskCaseViewProjectionV1"
    assert payload["reviewer_case_view"]["payload"]["legacy_laudo_id"] == laudo.id
    assert payload["reviewer_case_view"]["payload"]["review_status"] == "pending_review"
    assert request.state.v2_reviewdesk_projection_preferred is True
    assert request.state.v2_reviewdesk_projection_result["compatible"] is True


def test_endpoint_laudo_completo_embute_reviewer_case_view_mesmo_sem_flag_de_preferencia(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo = Laudo(
            empresa_id=revisor.empresa_id,
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        request = _build_request(
            "incluir_historico=true",
            path=f"/revisao/api/laudo/{laudo.id}/completo",
        )
        monkeypatch.setenv("TARIEL_V2_REVIEW_DESK_PROJECTION", "1")
        monkeypatch.delenv("TARIEL_V2_REVIEW_DESK_PROJECTION_PREFER", raising=False)

        response = asyncio.run(
            obter_laudo_completo(
                laudo_id=laudo.id,
                request=request,
                incluir_historico=True,
                cursor=None,
                limite=60,
                usuario=revisor,
                banco=banco,
            )
        )
        payload = json.loads(response.body)

    assert payload["reviewer_case_view_preferred"] is True
    assert payload["reviewer_case_view"]["contract_name"] == "ReviewDeskCaseViewProjectionV1"
    assert request.state.v2_reviewdesk_projection_preferred is True


def test_portal_bridge_cliente_repassa_request_no_completo_da_mesa(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        admin_cliente = banco.get(Usuario, ids["admin_cliente_a"])
        assert admin_cliente is not None

        laudo = Laudo(
            empresa_id=admin_cliente.empresa_id,
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        request = _build_request(
            "incluir_historico=true",
            path=f"/cliente/api/mesa/laudos/{laudo.id}/completo",
        )
        monkeypatch.setenv("TARIEL_V2_REVIEW_DESK_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_REVIEW_DESK_PROJECTION_PREFER", "1")

        response = asyncio.run(
            obter_laudo_completo_cliente(
                laudo_id=laudo.id,
                request=request,
                incluir_historico=True,
                cursor=None,
                limite=60,
                usuario=admin_cliente,
                banco=banco,
            )
        )
        payload = json.loads(response.body)

    assert payload["reviewer_case_view_preferred"] is True
    assert payload["reviewer_case_view"]["payload"]["legacy_laudo_id"] == laudo.id
