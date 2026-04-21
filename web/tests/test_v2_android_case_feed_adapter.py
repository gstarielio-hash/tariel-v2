from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.chat.mesa import feed_mesa_mobile
from app.shared.database import (
    Laudo,
    LaudoRevisao,
    MensagemLaudo,
    NivelAcesso,
    StatusRevisao,
    TemplateLaudo,
    TipoMensagem,
    Usuario,
)
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.adapters.android_case_feed import (
    adapt_inspector_case_view_projection_to_android_feed_item,
    build_inspector_case_interaction_view_from_legacy_message,
    build_inspector_visible_review_signals,
)
from app.v2.contracts.projections import build_inspector_case_view_projection


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def _build_mobile_feed_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/app/api/mobile/mesa/feed",
            "headers": [],
            "query_string": b"",
            "state": {},
        }
    )


def test_shape_do_adapter_android_feed_e_payload_limitado_ao_inspetor() -> None:
    laudo_card = {
        "id": 88,
        "titulo": "Caldeira B-202",
        "preview": "Primeira mensagem",
        "pinado": False,
        "data_iso": "2026-03-25",
        "data_br": "25/03/2026",
        "hora_br": "10:30",
        "tipo_template": "padrao",
        "status_revisao": StatusRevisao.AGUARDANDO.value,
        "status_card": "aguardando",
        "status_card_label": "Aguardando",
        "permite_edicao": False,
        "permite_reabrir": False,
        "possui_historico": True,
    }
    legacy_feed_item = {
        "laudo_id": 88,
        "estado": "aguardando",
        "permite_edicao": False,
        "permite_reabrir": False,
        "laudo_card": laudo_card,
        "resumo": {
            "atualizado_em": "2026-03-25T10:31:00+00:00",
            "total_mensagens": 1,
            "mensagens_nao_lidas": 1,
            "pendencias_abertas": 1,
            "pendencias_resolvidas": 0,
            "ultima_mensagem_id": 301,
            "ultima_mensagem_em": "2026-03-25T10:31:00+00:00",
            "ultima_mensagem_preview": "Ajustar item 4",
            "ultima_mensagem_tipo": TipoMensagem.HUMANO_ENG.value,
            "ultima_mensagem_remetente_id": 7,
        },
    }
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "permite_reabrir": False,
            "tem_interacao": True,
            "laudo_card": laudo_card,
        },
    )
    projection = build_inspector_case_view_projection(
        case_snapshot=snapshot,
        actor_id=17,
        actor_role="inspetor",
        source_channel="android_mesa_feed",
        allows_edit=False,
        has_interaction=True,
        report_types={"padrao": "Inspeção Geral (Padrão)"},
        laudo_card=laudo_card,
    )
    mensagem_mesa = SimpleNamespace(
        id=301,
        tipo=TipoMensagem.HUMANO_ENG.value,
        conteudo="Ajustar item 4",
        criado_em=datetime(2026, 3, 25, 10, 31, tzinfo=timezone.utc),
        remetente_id=7,
        lida=False,
        resolvida_em=None,
        client_message_id=None,
        anexos_mesa=[],
    )
    interaction = build_inspector_case_interaction_view_from_legacy_message(
        tenant_id=str(snapshot.tenant_id),
        case_id=snapshot.case_ref.case_id,
        thread_id=snapshot.case_ref.thread_id,
        message=mensagem_mesa,
    )
    review_signals = build_inspector_visible_review_signals(
        interactions=[interaction],
        projection=projection,
    )

    adapted = adapt_inspector_case_view_projection_to_android_feed_item(
        projection=projection,
        interactions=[interaction],
        visible_review_signals=review_signals,
        expected_legacy_payload=legacy_feed_item,
        case_metadata={"updated_at_iso": legacy_feed_item["resumo"]["atualizado_em"]},
    )

    assert adapted.contract_name == "AndroidCaseFeedItemAdapterResultV1"
    assert adapted.compatibility.contract_name == "AndroidCaseFeedCompatibilitySummaryV1"
    assert adapted.compatibility.compatible is True
    assert set(adapted.payload.keys()) == {
        "laudo_id",
        "estado",
        "permite_edicao",
        "permite_reabrir",
        "laudo_card",
        "resumo",
    }
    assert "policy_summary" not in adapted.payload
    assert "origin_summary" not in adapted.payload
    assert "document_readiness" not in adapted.payload


def test_mobile_mesa_feed_com_adapter_preserva_payload_publico(
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
            primeira_mensagem="Primeira evidencia coletada",
        )
        banco.add(laudo)
        banco.flush()

        banco.add(
            MensagemLaudo(
                laudo_id=laudo.id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Retorno novo da mesa para sync.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        laudo.atualizado_em = datetime.now(timezone.utc)
        banco.commit()

        request_base = _build_mobile_feed_request()
        monkeypatch.delenv("TARIEL_V2_ANDROID_FEED_ADAPTER", raising=False)
        response_base = asyncio.run(
            feed_mesa_mobile(
                request=request_base,
                laudo_ids=str(laudo.id),
                cursor_atualizado_em=None,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_base = json.loads(response_base.body)

        request_adapter = _build_mobile_feed_request()
        monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ADAPTER", "1")
        response_adapter = asyncio.run(
            feed_mesa_mobile(
                request=request_adapter,
                laudo_ids=str(laudo.id),
                cursor_atualizado_em=None,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_adapter = json.loads(response_adapter.body)

    assert payload_adapter == payload_base
    assert request_adapter.state.v2_android_feed_adapter_summary["total"] == 1
    assert request_adapter.state.v2_android_feed_adapter_summary["compatible"] == 1
    assert (
        request_adapter.state.v2_android_feed_adapter_results[0]["android_feed_adapter"]["contract_name"]
        == "AndroidCaseFeedItemAdapterResultV1"
    )
    assert (
        request_adapter.state.v2_android_feed_adapter_results[0]["projection"]["contract_name"]
        == "InspectorCaseViewProjectionV1"
    )


def test_mobile_mesa_feed_adapter_mantem_visibilidade_controlada_do_inspetor(
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
            nome="Template Feed Mobile",
            codigo_template="padrao",
            versao=2,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="editor_rico",
            status_template="ativo",
            arquivo_pdf_base="/tmp/nao_usado_mobile_feed.pdf",
            mapeamento_campos_json={},
            documento_editor_json={"content": []},
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Android",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
            parecer_ia="Rascunho IA",
            primeira_mensagem="Coleta inicial mobile",
        )
        banco.add(template)
        banco.add(laudo)
        banco.flush()

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo.id,
                    remetente_id=usuario.id,
                    tipo=TipoMensagem.USER.value,
                    conteudo="Mensagem de chat comum que nao deve ir para o feed da mesa.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo.id,
                    remetente_id=usuario.id,
                    tipo=TipoMensagem.IA.value,
                    conteudo="Rascunho IA interno.",
                    custo_api_reais=Decimal("0.0000"),
                ),
                MensagemLaudo(
                    laudo_id=laudo.id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Pendencia aberta da mesa.",
                    custo_api_reais=Decimal("0.0000"),
                ),
            ]
        )
        banco.add(
            LaudoRevisao(
                laudo_id=laudo.id,
                numero_versao=1,
                origem="ia",
                resumo="Resumo interno da revisao.",
                conteudo="Conteudo interno da revisao.",
                confianca_geral="alta",
            )
        )
        laudo.atualizado_em = datetime.now(timezone.utc)
        banco.commit()

        request_adapter = _build_mobile_feed_request()
        monkeypatch.setenv("TARIEL_V2_ANDROID_FEED_ADAPTER", "1")
        monkeypatch.setenv("TARIEL_V2_PROVENANCE", "1")
        monkeypatch.setenv("TARIEL_V2_POLICY_ENGINE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_FACADE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_SHADOW", "1")
        response_adapter = asyncio.run(
            feed_mesa_mobile(
                request=request_adapter,
                laudo_ids=str(laudo.id),
                cursor_atualizado_em=None,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_adapter = json.loads(response_adapter.body)

    assert payload_adapter["itens"]
    item = payload_adapter["itens"][0]
    assert item["resumo"]["total_mensagens"] == 1
    assert item["resumo"]["pendencias_abertas"] == 1
    assert "origin_summary" not in item
    assert "policy_summary" not in item
    assert "document_readiness" not in item
    assert "recent_reviews" not in item
    resultado = request_adapter.state.v2_android_feed_adapter_results[0]
    assert resultado["projection"]["projection_audience"] == "inspetor"
    assert resultado["android_feed_adapter"]["compatibility"]["visibility_scope"] == "inspetor_mobile"
    assert resultado["document_facade"]["legacy_pipeline_shadow"]["contract_name"] == "LegacyDocumentPipelineShadowResultV1"
    assert {entrada["actor_role"] for entrada in resultado["interaction_views"]} <= {"inspetor", "mesa"}
    assert resultado["visible_review_signals"]["visible_feedback_count"] == 1


def test_adapter_android_feed_zera_sinais_e_ponteiros_quando_feedback_da_mesa_fica_oculto() -> None:
    laudo_card = {
        "id": 88,
        "titulo": "Caldeira B-202",
        "preview": "Primeira mensagem",
        "pinado": False,
        "data_iso": "2026-03-25",
        "data_br": "25/03/2026",
        "hora_br": "10:30",
        "tipo_template": "padrao",
        "status_revisao": StatusRevisao.RASCUNHO.value,
        "status_card": "rascunho",
        "status_card_label": "Rascunho",
        "permite_edicao": True,
        "permite_reabrir": False,
        "possui_historico": True,
    }
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "rascunho",
            "laudo_id": 88,
            "permite_reabrir": False,
            "tem_interacao": True,
            "laudo_card": laudo_card,
        },
    )
    projection = build_inspector_case_view_projection(
        case_snapshot=snapshot,
        actor_id=17,
        actor_role="inspetor",
        source_channel="android_mesa_feed",
        allows_edit=True,
        has_interaction=True,
        report_types={"padrao": "Inspeção Geral (Padrão)"},
        laudo_card=laudo_card,
    )
    mensagem_inspetor = SimpleNamespace(
        id=300,
        tipo=TipoMensagem.HUMANO_INSP.value,
        conteudo="Mensagem do inspetor ainda visível.",
        criado_em=datetime(2026, 3, 25, 10, 28, tzinfo=timezone.utc),
        remetente_id=17,
        lida=True,
        resolvida_em=None,
        client_message_id="mesa:hidden:feed:0001",
        anexos_mesa=[],
    )
    mensagem_mesa = SimpleNamespace(
        id=301,
        tipo=TipoMensagem.HUMANO_ENG.value,
        conteudo="Pendência da mesa ainda não liberada.",
        criado_em=datetime(2026, 3, 25, 10, 31, tzinfo=timezone.utc),
        remetente_id=7,
        lida=False,
        resolvida_em=None,
        client_message_id=None,
        anexos_mesa=[],
    )
    interactions = [
        build_inspector_case_interaction_view_from_legacy_message(
            tenant_id=str(snapshot.tenant_id),
            case_id=snapshot.case_ref.case_id,
            thread_id=snapshot.case_ref.thread_id,
            message=mensagem_inspetor,
        ),
        build_inspector_case_interaction_view_from_legacy_message(
            tenant_id=str(snapshot.tenant_id),
            case_id=snapshot.case_ref.case_id,
            thread_id=snapshot.case_ref.thread_id,
            message=mensagem_mesa,
        ),
    ]
    review_signals = build_inspector_visible_review_signals(
        interactions=interactions,
        projection=projection,
    )

    adapted = adapt_inspector_case_view_projection_to_android_feed_item(
        projection=projection,
        interactions=interactions,
        visible_review_signals=review_signals,
        case_metadata={"updated_at_iso": interactions[-1].timestamp.isoformat()},
    )

    assert adapted.compatibility.compatible is True
    assert adapted.payload["resumo"]["total_mensagens"] == 1
    assert adapted.payload["resumo"]["mensagens_nao_lidas"] == 0
    assert adapted.payload["resumo"]["pendencias_abertas"] == 0
    assert adapted.payload["resumo"]["pendencias_resolvidas"] == 0
    assert adapted.payload["resumo"]["ultima_mensagem_id"] == 300
    assert adapted.payload["resumo"]["ultima_mensagem_tipo"] == TipoMensagem.HUMANO_INSP.value
