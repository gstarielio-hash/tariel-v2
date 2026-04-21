from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.chat.laudo_service import obter_status_relatorio_resposta
from app.domains.mesa.contracts import (
    MensagemPacoteMesa,
    PacoteMesaLaudo,
    ResumoEvidenciasMesa,
    ResumoMensagensMesa,
    ResumoPendenciasMesa,
    RevisaoPacoteMesa,
)
from app.domains.revisor.mesa_api import obter_pacote_mesa_laudo
from app.shared.database import Laudo, NivelAcesso, StatusLaudo, StatusRevisao, TemplateLaudo, Usuario
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.contracts.provenance import ProvenanceEntry, build_content_origin_summary
from app.v2.document import build_canonical_document_facade


def _build_inspector_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def _build_review_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=51,
        empresa_id=33,
        nivel_acesso=NivelAcesso.REVISOR.value,
    )


def _build_inspector_request(session_data: dict[str, object] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/app/api/laudo/status",
            "headers": [],
            "query_string": b"",
            "session": session_data or {},
            "state": {},
        }
    )


def _build_review_request(query_string: str = "") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/revisao/api/laudo/88/pacote",
            "headers": [],
            "query_string": query_string.encode(),
            "state": {},
        }
    )


def _build_review_package() -> PacoteMesaLaudo:
    agora = datetime.now(timezone.utc)
    return PacoteMesaLaudo(
        laudo_id=88,
        codigo_hash="abc123ef",
        tipo_template="padrao",
        setor_industrial="NR Teste",
        status_revisao=StatusRevisao.AGUARDANDO.value,
        status_conformidade=StatusLaudo.PENDENTE.value,
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
        pendencias_abertas=[
            MensagemPacoteMesa(
                id=1,
                tipo="humano_eng",
                texto="Ajustar evidencia",
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
                resumo="Primeira revisao",
                confianca_geral="alta",
                criado_em=agora,
            )
        ],
    )


def test_shape_da_facade_documental_minima() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_inspector_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
        },
    )

    facade = build_canonical_document_facade(
        banco=None,
        case_snapshot=snapshot,
        source_channel="web_app",
        template_key="padrao",
        current_review_status=StatusRevisao.AGUARDANDO.value,
        has_form_data=True,
        has_ai_draft=True,
    )

    dumped = facade.model_dump(mode="json")
    assert dumped["contract_name"] == "CanonicalDocumentFacadeV1"
    assert dumped["template_binding"]["contract_name"] == "DocumentTemplateBindingRefV1"
    assert dumped["document_policy"]["contract_name"] == "DocumentPolicyViewSummaryV1"
    assert dumped["document_readiness"]["contract_name"] == "DocumentMaterializationReadinessV1"
    assert dumped["document_governance"]["contract_name"] == "DocumentGovernanceSummaryV1"
    assert dumped["document_readiness"]["current_case_status"] == "needs_reviewer"
    assert dumped["document_readiness"]["current_document_status"] == "partially_filled"
    assert dumped["document_readiness"]["readiness_state"] == "blocked"
    assert dumped["document_readiness"]["template_source_kind"] == "unknown"
    assert dumped["document_governance"]["template_editability_status"] == "unknown"
    assert dumped["document_governance"]["ai_transparency_status"] == "not_applicable"


def test_blockers_seguros_quando_faltam_dados_documentais() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_inspector_user(),
        legacy_payload={"estado": "sem_relatorio", "laudo_id": None},
    )

    facade = build_canonical_document_facade(
        banco=None,
        case_snapshot=snapshot,
        source_channel="web_app",
        template_key=None,
        current_review_status=None,
        has_form_data=False,
        has_ai_draft=False,
    )

    blocker_codes = {item.blocker_code for item in facade.document_readiness.blockers}
    assert facade.document_readiness.readiness_state == "not_applicable"
    assert "no_active_report" in blocker_codes
    assert "template_not_bound" in blocker_codes
    assert "materialization_disallowed_by_policy" in blocker_codes


def test_facade_documental_resolve_template_ativo_quando_existe(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        template = TemplateLaudo(
            empresa_id=usuario.empresa_id,
            criado_por_id=usuario.id,
            nome="Template Padrao",
            codigo_template="padrao",
            versao=2,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            status_template="ativo",
            arquivo_pdf_base="/tmp/template_padrao.pdf",
            mapeamento_campos_json={},
            documento_editor_json=None,
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
        banco.add(template)
        banco.flush()

        snapshot = build_technical_case_status_snapshot_for_user(
            usuario=usuario,
            legacy_payload={
                "estado": "relatorio_ativo",
                "laudo_id": 101,
                "permite_reabrir": False,
                "laudo_card": {"id": 101, "status_revisao": StatusRevisao.RASCUNHO.value},
            },
        )

        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=snapshot,
            source_channel="web_app",
            template_key="padrao",
            current_review_status=StatusRevisao.RASCUNHO.value,
            has_form_data=True,
            has_ai_draft=False,
        )

    assert facade.template_binding.binding_status == "bound"
    assert facade.template_binding.template_id == template.id
    assert facade.template_binding.template_source_kind == "legacy_pdf"
    assert facade.document_readiness.readiness_state == "ready_for_materialization"
    assert facade.document_governance.template_editability_status == "legacy_pdf_transition"


def test_facade_documental_resolve_seed_canonico_quando_laudo_catalogado_nao_tem_template_tenant_ativo(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
            catalog_family_key="nr10_inspecao_instalacoes_eletricas",
        )
        banco.add(laudo)
        banco.flush()

        snapshot = build_technical_case_status_snapshot_for_user(
            usuario=usuario,
            legacy_payload={
                "estado": "relatorio_ativo",
                "laudo_id": laudo.id,
                "permite_reabrir": False,
                "laudo_card": {"id": laudo.id, "status_revisao": StatusRevisao.RASCUNHO.value},
            },
            laudo=laudo,
        )

        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=snapshot,
            source_channel="web_app",
            template_key="padrao",
            current_review_status=StatusRevisao.RASCUNHO.value,
            has_form_data=True,
            has_ai_draft=False,
        )

    blocker_codes = {item.blocker_code for item in facade.document_readiness.blockers}
    assert facade.template_binding.binding_status == "bound"
    assert facade.template_binding.template_id is None
    assert facade.template_binding.template_key == "nr10_inspecao_instalacoes_eletricas"
    assert facade.template_binding.template_source_kind == "editor_rico"
    assert facade.template_binding.legacy_template_status == "catalog_canonical_seed"
    assert facade.template_binding.legacy_template_mode == "editor_rico"
    assert facade.template_binding.legacy_editor_document_present is True
    assert "template_not_bound" not in blocker_codes
    assert facade.document_readiness.readiness_state == "ready_for_materialization"
    assert facade.document_governance.template_editability_status == "editable_source_available"


def test_governanca_documental_explica_ia_aprovacao_humana_e_origem_parcial() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_review_user(),
        legacy_payload={
            "estado": "aprovado",
            "laudo_id": 144,
            "permite_reabrir": False,
            "laudo_card": {"id": 144, "status_revisao": StatusRevisao.APROVADO.value},
        },
    )
    provenance = build_content_origin_summary(
        entries=[
            ProvenanceEntry(
                origin_kind="ai_generated",
                source="ai:draft",
                confidence="confirmed",
            ),
            ProvenanceEntry(
                origin_kind="legacy_unknown",
                source="legacy:report",
                confidence="legacy_unknown",
            ),
        ]
    )

    facade = build_canonical_document_facade(
        banco=None,
        case_snapshot=snapshot,
        source_channel="review_web",
        template_key="padrao",
        provenance_summary=provenance,
        current_review_status=StatusRevisao.APROVADO.value,
        has_form_data=True,
        has_ai_draft=True,
    )

    assert facade.document_governance.has_ai_content is True
    assert facade.document_governance.ai_transparency_status == "pending_legal_definition"
    assert facade.document_governance.provenance_quality == "partial"
    assert facade.document_governance.provenance_has_legacy_unknown_content is True
    assert facade.document_governance.human_approval_state == "required_satisfied"


def test_status_relatorio_com_document_facade_preserva_payload_publico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
            parecer_ia="Rascunho IA",
        )
        banco.add(laudo)
        banco.flush()

        sessao = {"laudo_ativo_id": laudo.id, "estado_relatorio": "aguardando"}

        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_INSPECTOR_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_POLICY_ENGINE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_FACADE", raising=False)
        payload_base, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_inspector_request(dict(sessao)),
                usuario=usuario,
                banco=banco,
            )
        )

        request_document = _build_inspector_request(dict(sessao))
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_INSPECTOR_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_POLICY_ENGINE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_FACADE", "1")
        payload_document, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=request_document,
                usuario=usuario,
                banco=banco,
            )
        )

    assert payload_document == payload_base
    assert request_document.state.v2_document_facade_summary["contract_name"] == "DocumentMaterializationReadinessV1"
    projection_payload = request_document.state.v2_inspector_projection_result["projection"]["payload"]
    assert projection_payload["document_readiness"]["contract_name"] == "DocumentMaterializationReadinessV1"
    assert request_document.state.v2_inspector_projection_result["document_facade"]["contract_name"] == "CanonicalDocumentFacadeV1"


def test_pacote_mesa_com_document_facade_preserva_payload_publico(
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
            dados_formulario={"campo": "valor"},
            parecer_ia="Rascunho IA",
        )
        banco.add(laudo)
        banco.flush()

        request_base = _build_review_request()
        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_REVIEW_DESK_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_POLICY_ENGINE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_FACADE", raising=False)
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

        request_document = _build_review_request()
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_REVIEW_DESK_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_POLICY_ENGINE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_FACADE", "1")
        response_document = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_document,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_document = json.loads(response_document.body)

    assert payload_document == payload_base
    assert request_document.state.v2_document_facade_summary["contract_name"] == "DocumentMaterializationReadinessV1"
    projection_payload = request_document.state.v2_reviewdesk_projection_result["projection"]["payload"]
    assert projection_payload["document_readiness"]["contract_name"] == "DocumentMaterializationReadinessV1"
    assert request_document.state.v2_reviewdesk_projection_result["document_facade"]["contract_name"] == "CanonicalDocumentFacadeV1"
