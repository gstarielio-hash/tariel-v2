from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.chat.mesa import listar_mensagens_mesa_laudo
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
    build_inspector_case_interaction_view_from_legacy_message,
    build_inspector_visible_review_signals,
)
from app.v2.adapters.android_case_thread import (
    adapt_inspector_case_view_projection_to_android_thread,
    build_inspector_case_conversation_view,
)
from app.v2.contracts.projections import build_inspector_case_view_projection


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def _build_mobile_thread_request(
    laudo_id: int,
    *,
    auth_header: str | None = None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if auth_header:
        headers.append((b"authorization", auth_header.encode("utf-8")))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": f"/app/api/laudo/{laudo_id}/mesa/mensagens",
            "headers": headers,
            "query_string": b"",
            "session": {},
            "state": {},
        }
    )


def test_shape_do_adapter_android_thread_e_payload_limitado_ao_inspetor() -> None:
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
        source_channel="android_mesa_thread",
        allows_edit=False,
        has_interaction=True,
        report_types={"padrao": "Inspeção Geral (Padrão)"},
        laudo_card=laudo_card,
    )
    mensagem_inspetor = SimpleNamespace(
        id=300,
        laudo_id=88,
        tipo=TipoMensagem.HUMANO_INSP.value,
        conteudo="Seguem os ajustes solicitados.",
        criado_em=datetime(2026, 3, 25, 10, 28, tzinfo=timezone.utc),
        remetente_id=17,
        lida=True,
        resolvida_em=None,
        client_message_id="mesa:thread:0001",
        anexos_mesa=[],
    )
    mensagem_mesa = SimpleNamespace(
        id=301,
        laudo_id=88,
        tipo=TipoMensagem.HUMANO_ENG.value,
        conteudo="Ajustar item 4",
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
    conversation = build_inspector_case_conversation_view(
        tenant_id=str(snapshot.tenant_id),
        case_id=snapshot.case_ref.case_id,
        thread_id=snapshot.case_ref.thread_id,
        page_interactions=interactions,
        all_interactions=interactions,
        sync_mode="full",
        cursor_after_id=None,
        next_cursor_id=None,
        cursor_last_message_id=301,
        has_more=False,
    )
    review_signals = build_inspector_visible_review_signals(
        interactions=interactions,
        projection=projection,
    )
    legacy_payload = {
        "laudo_id": 88,
        "itens": [
            {
                "id": interactions[0].message_id,
                "laudo_id": 88,
                "tipo": interactions[0].legacy_message_type,
                "item_kind": interactions[0].item_kind,
                "message_kind": interactions[0].message_kind,
                "pendency_state": interactions[0].pendency_state,
                "texto": interactions[0].content_text,
                "remetente_id": interactions[0].sender_id,
                "data": interactions[0].display_date,
                "criado_em_iso": interactions[0].timestamp.isoformat(),
                "lida": interactions[0].is_read,
                "resolvida_em": "",
                "resolvida_em_label": "",
                "resolvida_por_nome": "",
                "entrega_status": "persisted",
                "client_message_id": interactions[0].client_message_id,
            },
            {
                "id": interactions[1].message_id,
                "laudo_id": 88,
                "tipo": interactions[1].legacy_message_type,
                "item_kind": interactions[1].item_kind,
                "message_kind": interactions[1].message_kind,
                "pendency_state": interactions[1].pendency_state,
                "texto": interactions[1].content_text,
                "remetente_id": interactions[1].sender_id,
                "data": interactions[1].display_date,
                "criado_em_iso": interactions[1].timestamp.isoformat(),
                "lida": interactions[1].is_read,
                "resolvida_em": "",
                "resolvida_em_label": "",
                "resolvida_por_nome": "",
                "entrega_status": "persisted",
            },
        ],
        "cursor_proximo": None,
        "cursor_ultimo_id": 301,
        "tem_mais": False,
        "estado": "aguardando",
        "permite_edicao": False,
        "permite_reabrir": False,
        "laudo_card": laudo_card,
        "resumo": {
            "atualizado_em": interactions[1].timestamp.isoformat(),
            "total_mensagens": 2,
            "mensagens_nao_lidas": 1,
            "pendencias_abertas": 1,
            "pendencias_resolvidas": 0,
            "ultima_mensagem_id": 301,
            "ultima_mensagem_em": interactions[1].timestamp.isoformat(),
            "ultima_mensagem_preview": interactions[1].text_preview,
            "ultima_mensagem_tipo": interactions[1].legacy_message_type,
            "ultima_mensagem_remetente_id": interactions[1].sender_id,
        },
        "sync": {
            "modo": "full",
            "apos_id": None,
            "cursor_ultimo_id": 301,
        },
    }

    adapted = adapt_inspector_case_view_projection_to_android_thread(
        projection=projection,
        conversation=conversation,
        interactions=interactions,
        visible_review_signals=review_signals,
        expected_legacy_payload=legacy_payload,
        legacy_laudo_context={
            "estado": "aguardando",
            "permite_edicao": False,
            "permite_reabrir": False,
            "laudo_card": laudo_card,
        },
        case_metadata={"updated_at_iso": interactions[1].timestamp.isoformat()},
    )

    assert adapted.contract_name == "AndroidCaseThreadAdapterResultV1"
    assert adapted.compatibility.contract_name == "AndroidCaseThreadCompatibilitySummaryV1"
    assert adapted.compatibility.compatible is True
    assert set(adapted.payload.keys()) == {
        "laudo_id",
        "itens",
        "cursor_proximo",
        "cursor_ultimo_id",
        "tem_mais",
        "estado",
        "permite_edicao",
        "permite_reabrir",
        "laudo_card",
        "resumo",
        "sync",
    }
    assert "policy_summary" not in adapted.payload
    assert "origin_summary" not in adapted.payload
    assert "document_readiness" not in adapted.payload
    assert "policy_summary" not in adapted.payload["itens"][0]
    assert "origin_summary" not in adapted.payload["itens"][0]


def test_mobile_mesa_thread_com_adapter_preserva_payload_publico(
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

        banco.add_all(
            [
                MensagemLaudo(
                    laudo_id=laudo.id,
                    remetente_id=usuario.id,
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo="Resposta inicial do inspetor.",
                    custo_api_reais=Decimal("0.0000"),
                    client_message_id="mesa:thread:test:0001",
                ),
                MensagemLaudo(
                    laudo_id=laudo.id,
                    remetente_id=ids["revisor_a"],
                    tipo=TipoMensagem.HUMANO_ENG.value,
                    conteudo="Retorno novo da mesa para sync.",
                    custo_api_reais=Decimal("0.0000"),
                ),
            ]
        )
        laudo.atualizado_em = datetime.now(timezone.utc)
        banco.commit()

        request_base = _build_mobile_thread_request(laudo.id)
        monkeypatch.delenv("TARIEL_V2_ANDROID_THREAD_ADAPTER", raising=False)
        response_base = asyncio.run(
            listar_mensagens_mesa_laudo(
                laudo_id=laudo.id,
                request=request_base,
                limite=40,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_base = json.loads(response_base.body)

        request_adapter = _build_mobile_thread_request(
            laudo.id,
            auth_header="Bearer token-123",
        )
        monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ADAPTER", "1")
        response_adapter = asyncio.run(
            listar_mensagens_mesa_laudo(
                laudo_id=laudo.id,
                request=request_adapter,
                limite=40,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_adapter = json.loads(response_adapter.body)

    assert payload_adapter == payload_base
    assert request_adapter.state.v2_android_thread_adapter_summary["compatible"] is True
    assert request_adapter.state.v2_android_thread_adapter_summary["total_messages"] == 2
    assert (
        request_adapter.state.v2_android_thread_adapter_result["android_thread_adapter"]["contract_name"]
        == "AndroidCaseThreadAdapterResultV1"
    )
    assert (
        request_adapter.state.v2_android_thread_adapter_result["projection"]["contract_name"]
        == "InspectorCaseViewProjectionV1"
    )


def test_mobile_mesa_thread_adapter_mantem_visibilidade_controlada_do_inspetor(
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
            nome="Template Thread Mobile",
            codigo_template="padrao",
            versao=2,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="editor_rico",
            status_template="ativo",
            arquivo_pdf_base="/tmp/nao_usado_mobile_thread.pdf",
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
                    conteudo="Mensagem de chat comum que nao deve ir para a conversa da mesa.",
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
                    remetente_id=usuario.id,
                    tipo=TipoMensagem.HUMANO_INSP.value,
                    conteudo="Resposta visivel do inspetor.",
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

        request_adapter = _build_mobile_thread_request(
            laudo.id,
            auth_header="Bearer token-123",
        )
        monkeypatch.setenv("TARIEL_V2_ANDROID_THREAD_ADAPTER", "1")
        monkeypatch.setenv("TARIEL_V2_PROVENANCE", "1")
        monkeypatch.setenv("TARIEL_V2_POLICY_ENGINE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_FACADE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_SHADOW", "1")
        response_adapter = asyncio.run(
            listar_mensagens_mesa_laudo(
                laudo_id=laudo.id,
                request=request_adapter,
                limite=40,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_adapter = json.loads(response_adapter.body)

    assert len(payload_adapter["itens"]) == 2
    assert {item["tipo"] for item in payload_adapter["itens"]} == {
        TipoMensagem.HUMANO_INSP.value,
        TipoMensagem.HUMANO_ENG.value,
    }
    assert payload_adapter["resumo"]["total_mensagens"] == 2
    assert payload_adapter["resumo"]["pendencias_abertas"] == 1
    assert "origin_summary" not in payload_adapter
    assert "policy_summary" not in payload_adapter
    assert "document_readiness" not in payload_adapter
    assert "recent_reviews" not in payload_adapter
    resultado = request_adapter.state.v2_android_thread_adapter_result
    assert resultado["projection"]["projection_audience"] == "inspetor"
    assert (
        resultado["android_thread_adapter"]["compatibility"]["visibility_scope"]
        == "inspetor_mobile"
    )
    assert (
        resultado["document_facade"]["legacy_pipeline_shadow"]["contract_name"]
        == "LegacyDocumentPipelineShadowResultV1"
    )
    assert {entrada["actor_role"] for entrada in resultado["interaction_views"]} <= {
        "inspetor",
        "mesa",
    }
    assert resultado["visible_review_signals"]["visible_feedback_count"] == 1


def test_adapter_android_thread_remove_mensagem_da_mesa_quando_feedback_fica_oculto() -> None:
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
        source_channel="android_mesa_thread",
        allows_edit=True,
        has_interaction=True,
        report_types={"padrao": "Inspeção Geral (Padrão)"},
        laudo_card=laudo_card,
    )
    mensagem_inspetor = SimpleNamespace(
        id=300,
        laudo_id=88,
        tipo=TipoMensagem.HUMANO_INSP.value,
        conteudo="Resposta visível do inspetor.",
        criado_em=datetime(2026, 3, 25, 10, 28, tzinfo=timezone.utc),
        remetente_id=17,
        lida=True,
        resolvida_em=None,
        client_message_id="mesa:hidden:thread:0001",
        anexos_mesa=[],
    )
    mensagem_mesa = SimpleNamespace(
        id=301,
        laudo_id=88,
        tipo=TipoMensagem.HUMANO_ENG.value,
        conteudo="Comentário da mesa ainda oculto para o mobile.",
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
    conversation = build_inspector_case_conversation_view(
        tenant_id=str(snapshot.tenant_id),
        case_id=snapshot.case_ref.case_id,
        thread_id=snapshot.case_ref.thread_id,
        page_interactions=interactions,
        all_interactions=interactions,
        sync_mode="full",
        cursor_after_id=None,
        next_cursor_id=None,
        cursor_last_message_id=301,
        has_more=False,
    )
    review_signals = build_inspector_visible_review_signals(
        interactions=interactions,
        projection=projection,
    )

    adapted = adapt_inspector_case_view_projection_to_android_thread(
        projection=projection,
        conversation=conversation,
        interactions=interactions,
        visible_review_signals=review_signals,
        legacy_laudo_context={
            "estado": "rascunho",
            "permite_edicao": True,
            "permite_reabrir": False,
            "laudo_card": laudo_card,
        },
        case_metadata={"updated_at_iso": interactions[-1].timestamp.isoformat()},
    )

    assert adapted.compatibility.compatible is True
    assert len(adapted.payload["itens"]) == 1
    assert adapted.payload["itens"][0]["id"] == 300
    assert adapted.payload["resumo"]["total_mensagens"] == 1
    assert adapted.payload["resumo"]["mensagens_nao_lidas"] == 0
    assert adapted.payload["resumo"]["pendencias_abertas"] == 0
    assert adapted.payload["resumo"]["pendencias_resolvidas"] == 0
    assert adapted.payload["resumo"]["ultima_mensagem_id"] == 300
