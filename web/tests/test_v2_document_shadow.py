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
from app.shared.database import Laudo, NivelAcesso, StatusRevisao, TemplateLaudo, Usuario
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.document import (
    build_canonical_document_facade,
    build_legacy_document_pipeline_shadow_input,
    evaluate_legacy_document_pipeline_shadow,
)


def _build_inspector_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
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
        status_conformidade="pendente",
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
        pendencias_resolvidas_recentes=[],
        whispers_recentes=[],
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


def test_shape_do_shadow_input_e_resultado_documental() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_inspector_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 88,
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.RASCUNHO.value},
        },
    )

    facade = build_canonical_document_facade(
        banco=None,
        case_snapshot=snapshot,
        source_channel="web_app",
        template_key="padrao",
        current_review_status=StatusRevisao.RASCUNHO.value,
        has_form_data=False,
        has_ai_draft=False,
    )

    shadow_input = build_legacy_document_pipeline_shadow_input(facade=facade)
    shadow_result = evaluate_legacy_document_pipeline_shadow(shadow_input=shadow_input)

    dumped_input = shadow_input.model_dump(mode="json")
    dumped_result = shadow_result.model_dump(mode="json")
    assert dumped_input["contract_name"] == "LegacyDocumentPipelineShadowInputV1"
    assert dumped_result["contract_name"] == "LegacyDocumentPipelineShadowResultV1"
    assert dumped_result["comparison"]["contract_name"] == "LegacyDocumentReadinessComparisonV1"
    assert dumped_result["pipeline_name"] == "legacy_pdf_fallback"


def test_shadow_adapter_escolhe_preview_editor_rico_quando_template_e_formulario_existem(
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
            nome="Template Editor Rico",
            codigo_template="padrao",
            versao=3,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="editor_rico",
            status_template="ativo",
            arquivo_pdf_base="/tmp/nao_usado.pdf",
            mapeamento_campos_json={},
            documento_editor_json={"content": []},
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
        banco.add(template)
        banco.flush()

        snapshot = build_technical_case_status_snapshot_for_user(
            usuario=usuario,
            legacy_payload={
                "estado": "aguardando",
                "laudo_id": 91,
                "permite_reabrir": False,
                "laudo_card": {"id": 91, "status_revisao": StatusRevisao.AGUARDANDO.value},
            },
        )
        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=snapshot,
            source_channel="web_app",
            template_key="padrao",
            current_review_status=StatusRevisao.AGUARDANDO.value,
            has_form_data=True,
            has_ai_draft=False,
        )

    shadow_result = evaluate_legacy_document_pipeline_shadow(
        shadow_input=build_legacy_document_pipeline_shadow_input(facade=facade),
    )

    assert shadow_result.pipeline_name == "editor_rico_preview"
    assert shadow_result.materialization_allowed is True
    assert shadow_result.template_resolution["template_source_kind"] == "editor_rico"


def test_shadow_adapter_cai_para_fallback_quando_template_bound_sem_formulario(
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
            nome="Template Editor Rico",
            codigo_template="padrao",
            versao=3,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="editor_rico",
            status_template="ativo",
            arquivo_pdf_base="/tmp/nao_usado.pdf",
            mapeamento_campos_json={},
            documento_editor_json={"content": []},
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
                "laudo_id": 92,
                "permite_reabrir": False,
                "laudo_card": {"id": 92, "status_revisao": StatusRevisao.RASCUNHO.value},
            },
        )
        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=snapshot,
            source_channel="web_app",
            template_key="padrao",
            current_review_status=StatusRevisao.RASCUNHO.value,
            has_form_data=False,
            has_ai_draft=False,
        )

    shadow_result = evaluate_legacy_document_pipeline_shadow(
        shadow_input=build_legacy_document_pipeline_shadow_input(facade=facade),
    )
    blocker_codes = {item.blocker_code for item in shadow_result.blockers}

    assert shadow_result.pipeline_name == "legacy_pdf_fallback"
    assert "legacy_template_requires_form_data" in blocker_codes
    assert "template_binding_vs_legacy_pipeline" in shadow_result.comparison.divergences


def test_shadow_adapter_promove_template_legado_fraco_catalogado_para_preview_editor_rico(
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
            nome="Template NR13 Legado Fraco",
            codigo_template="nr13_vaso_pressao",
            versao=4,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            status_template="ativo",
            arquivo_pdf_base="/tmp/nr13_legado_fraco.pdf",
            mapeamento_campos_json={},
            documento_editor_json={},
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR 13",
            tipo_template="nr13",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            catalog_family_key="nr13_inspecao_vaso_pressao",
            dados_formulario={
                "identificacao": {"identificacao_do_vaso": "Vaso vertical VP-204"},
                "conclusao": {
                    "status": "ajuste",
                    "conclusao_tecnica": "Equipamento apto com acompanhamento.",
                },
            },
        )
        banco.add(template)
        banco.add(laudo)
        banco.flush()

        snapshot = build_technical_case_status_snapshot_for_user(
            usuario=usuario,
            legacy_payload={
                "estado": "aguardando",
                "laudo_id": laudo.id,
                "permite_reabrir": False,
                "laudo_card": {"id": laudo.id, "status_revisao": StatusRevisao.AGUARDANDO.value},
            },
            laudo=laudo,
        )
        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=snapshot,
            source_channel="web_app",
            template_key="nr13",
            current_review_status=StatusRevisao.AGUARDANDO.value,
            has_form_data=True,
            has_ai_draft=False,
        )
        shadow_result = evaluate_legacy_document_pipeline_shadow(
            shadow_input=build_legacy_document_pipeline_shadow_input(
                facade=facade,
                banco=banco,
                laudo=laudo,
            ),
        )

    assert shadow_result.pipeline_name == "editor_rico_preview"
    assert shadow_result.materialization_allowed is True
    assert shadow_result.template_resolution["selection_reason"] == "legacy_pdf_promoted_to_editor_rico"
    assert shadow_result.template_resolution["runtime_render_strategy"] == "legacy_promoted_to_editor_rico"
    assert shadow_result.template_resolution["legacy_preview_overlay_viable"] is False
    assert shadow_result.template_resolution["rich_runtime_preview_viable"] is True
    assert shadow_result.template_resolution["resolved_template_family_key"] == "nr13_inspecao_vaso_pressao"


def test_status_relatorio_com_document_shadow_preserva_payload_publico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        template = TemplateLaudo(
            empresa_id=usuario.empresa_id,
            criado_por_id=usuario.id,
            nome="Template Editor Rico",
            codigo_template="padrao",
            versao=3,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="editor_rico",
            status_template="ativo",
            arquivo_pdf_base="/tmp/nao_usado.pdf",
            mapeamento_campos_json={},
            documento_editor_json={"content": []},
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
        )
        banco.add(template)
        banco.add(laudo)
        banco.flush()

        sessao = {"laudo_ativo_id": laudo.id, "estado_relatorio": "aguardando"}

        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_INSPECTOR_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_FACADE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_SHADOW", raising=False)
        payload_base, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_inspector_request(dict(sessao)),
                usuario=usuario,
                banco=banco,
            )
        )

        request_shadow = _build_inspector_request(dict(sessao))
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_INSPECTOR_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_FACADE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_SHADOW", "1")
        payload_shadow, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=request_shadow,
                usuario=usuario,
                banco=banco,
            )
        )

    assert payload_shadow == payload_base
    assert request_shadow.state.v2_document_shadow_summary["contract_name"] == "LegacyDocumentPipelineShadowResultV1"
    assert request_shadow.state.v2_document_shadow_summary["pipeline_name"] == "editor_rico_preview"
    projection_payload = request_shadow.state.v2_inspector_projection_result["projection"]["payload"]
    assert projection_payload["legacy_pipeline_name"] == "editor_rico_preview"
    assert request_shadow.state.v2_inspector_projection_result["document_shadow"]["contract_name"] == "LegacyDocumentPipelineShadowResultV1"


def test_status_relatorio_com_document_shadow_promovido_preserva_payload_publico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        template = TemplateLaudo(
            empresa_id=usuario.empresa_id,
            criado_por_id=usuario.id,
            nome="Template NR13 Legado Fraco",
            codigo_template="nr13_vaso_pressao",
            versao=4,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            status_template="ativo",
            arquivo_pdf_base="/tmp/nr13_legado_fraco.pdf",
            mapeamento_campos_json={},
            documento_editor_json={},
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR 13",
            tipo_template="nr13",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            catalog_family_key="nr13_inspecao_vaso_pressao",
            dados_formulario={
                "identificacao": {"identificacao_do_vaso": "Vaso vertical VP-204"},
                "conclusao": {
                    "status": "ajuste",
                    "conclusao_tecnica": "Equipamento apto com acompanhamento.",
                },
            },
        )
        banco.add(template)
        banco.add(laudo)
        banco.flush()

        sessao = {"laudo_ativo_id": laudo.id, "estado_relatorio": "aguardando"}

        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_INSPECTOR_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_FACADE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_SHADOW", raising=False)
        payload_base, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_inspector_request(dict(sessao)),
                usuario=usuario,
                banco=banco,
            )
        )

        request_shadow = _build_inspector_request(dict(sessao))
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_INSPECTOR_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_FACADE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_SHADOW", "1")
        payload_shadow, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=request_shadow,
                usuario=usuario,
                banco=banco,
            )
        )

    assert payload_shadow == payload_base
    assert request_shadow.state.v2_document_shadow_summary["pipeline_name"] == "editor_rico_preview"
    assert request_shadow.state.v2_document_shadow_summary["template_resolution"]["runtime_render_strategy"] == (
        "legacy_promoted_to_editor_rico"
    )
    projection_payload = request_shadow.state.v2_inspector_projection_result["projection"]["payload"]
    assert projection_payload["legacy_pipeline_name"] == "editor_rico_preview"


def test_pacote_mesa_com_document_shadow_preserva_payload_publico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        template = TemplateLaudo(
            empresa_id=revisor.empresa_id,
            criado_por_id=ids["admin_cliente_a"],
            nome="Template Editor Rico",
            codigo_template="padrao",
            versao=3,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="editor_rico",
            status_template="ativo",
            arquivo_pdf_base="/tmp/nao_usado.pdf",
            mapeamento_campos_json={},
            documento_editor_json={"content": []},
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
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
        banco.add(template)
        banco.add(laudo)
        banco.flush()

        request_base = _build_review_request()
        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_REVIEW_DESK_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_FACADE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_SHADOW", raising=False)
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

        request_shadow = _build_review_request()
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_REVIEW_DESK_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_FACADE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_SHADOW", "1")
        response_shadow = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_shadow,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_shadow = json.loads(response_shadow.body)

    assert payload_shadow == payload_base
    assert request_shadow.state.v2_document_shadow_summary["contract_name"] == "LegacyDocumentPipelineShadowResultV1"
    assert request_shadow.state.v2_document_shadow_summary["pipeline_name"] == "editor_rico_preview"
    projection_payload = request_shadow.state.v2_reviewdesk_projection_result["projection"]["payload"]
    assert projection_payload["legacy_pipeline_name"] == "editor_rico_preview"
    assert request_shadow.state.v2_reviewdesk_projection_result["document_shadow"]["contract_name"] == "LegacyDocumentPipelineShadowResultV1"
