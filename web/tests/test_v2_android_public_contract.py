from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.chat.mesa import (
    feed_mesa_mobile_public_v2,
    listar_mensagens_mesa_laudo_mobile_public_v2,
)
from app.shared.database import (
    Laudo,
    MensagemLaudo,
    NivelAcesso,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.adapters.android_case_feed import (
    build_inspector_case_interaction_view_from_legacy_message,
    build_inspector_visible_review_signals,
)
from app.v2.adapters.android_case_thread import build_inspector_case_conversation_view
from app.v2.contracts.mobile import (
    build_mobile_inspector_feed_item_v2,
    build_mobile_inspector_feed_v2,
    build_mobile_inspector_thread_v2,
)
from app.v2.contracts.projections import build_inspector_case_view_projection
from tests.regras_rotas_criticas_support import SENHA_PADRAO


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def _build_request(
    path: str,
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
            "path": path,
            "headers": headers,
            "query_string": b"",
            "session": {},
            "state": {},
        }
    )


def _login_mobile_inspetor(client) -> dict[str, str]:
    resposta = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": "inspetor@empresa-a.test",
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def test_shape_do_contrato_publico_mobile_v2_feed_e_thread() -> None:
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
        source_channel="android_mesa_feed_v2",
        allows_edit=False,
        has_interaction=True,
        report_types={"padrao": "Inspeção Geral (Padrão)"},
        laudo_card=laudo_card,
    )
    mensagem_inspetor = SimpleNamespace(
        id=300,
        tipo=TipoMensagem.HUMANO_INSP.value,
        conteudo="Seguem os ajustes solicitados.",
        criado_em=datetime(2026, 3, 25, 10, 28, tzinfo=timezone.utc),
        remetente_id=17,
        lida=True,
        resolvida_em=None,
        client_message_id="mesa:public:v2:0001",
        anexos_mesa=[],
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
        anexos_mesa=[
            SimpleNamespace(
                id=9,
                laudo_id=88,
                nome_original="foto.jpg",
                mime_type="image/jpeg",
                categoria="imagem",
                tamanho_bytes=2048,
            )
        ],
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

    feed_item = build_mobile_inspector_feed_item_v2(
        projection=projection,
        interactions=interactions,
        source_channel="android_mesa_feed_v2",
        visible_review_signals=review_signals,
        provenance_summary=None,
        case_metadata={"updated_at_iso": interactions[-1].timestamp.isoformat()},
    )
    feed_contract = build_mobile_inspector_feed_v2(
        tenant_id=str(snapshot.tenant_id),
        source_channel="android_mesa_feed_v2",
        requested_laudo_ids=[88],
        cursor_current="2026-03-25T10:31:00+00:00",
        items=[feed_item],
    )
    thread_contract = build_mobile_inspector_thread_v2(
        projection=projection,
        conversation=conversation,
        source_channel="android_mesa_thread_v2",
        visible_review_signals=review_signals,
        provenance_summary=None,
    )

    assert feed_contract.contract_name == "MobileInspectorFeedV2"
    assert feed_contract.contract_version == "v2"
    assert feed_contract.items[0].contract_name == "MobileInspectorFeedItemV2"
    assert feed_contract.items[0].case_lifecycle_status == "aguardando_mesa"
    assert feed_contract.items[0].case_workflow_mode == "laudo_com_mesa"
    assert feed_contract.items[0].active_owner_role == "mesa"
    assert feed_contract.items[0].allowed_next_lifecycle_statuses == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert feed_contract.items[0].allowed_surface_actions == [
        "mesa_approve",
        "mesa_return",
    ]
    assert [
        item["target_status"]
        for item in feed_contract.items[0].allowed_lifecycle_transitions
    ] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert feed_contract.items[0].human_validation_required is True
    assert feed_contract.items[0].latest_interaction is not None
    assert feed_contract.items[0].latest_interaction.actor_role == "mesa"
    assert feed_contract.items[0].review_signals.review_visible_to_inspector is True
    assert feed_contract.items[0].feedback_policy.feedback_mode == "visible_feedback_only"
    assert feed_contract.items[0].collaboration.summary.open_feedback_count == 1
    assert feed_contract.items[0].collaboration.latest_feedback is not None
    assert feed_contract.items[0].collaboration.latest_feedback.actor_role == "mesa"
    assert thread_contract.contract_name == "MobileInspectorThreadV2"
    assert thread_contract.contract_version == "v2"
    assert thread_contract.case_lifecycle_status == "aguardando_mesa"
    assert thread_contract.case_workflow_mode == "laudo_com_mesa"
    assert thread_contract.active_owner_role == "mesa"
    assert thread_contract.allowed_next_lifecycle_statuses == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert thread_contract.allowed_surface_actions == [
        "mesa_approve",
        "mesa_return",
    ]
    assert [
        item["target_status"]
        for item in thread_contract.allowed_lifecycle_transitions
    ] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert thread_contract.human_validation_required is True
    assert thread_contract.items[0].contract_name == "MobileInspectorThreadMessageV2"
    assert thread_contract.feedback_policy.feedback_message_bodies_visible is True
    assert thread_contract.collaboration.summary.visible_feedback_count == 1
    assert thread_contract.collaboration.latest_feedback is not None
    assert thread_contract.collaboration.latest_feedback.message_id == 301
    assert thread_contract.attachment_policy.policy_name == "android_attachment_sync_policy"
    assert thread_contract.sync_policy.mode == "full"
    assert thread_contract.items[1].attachments[0].contract_name == "MobileInspectorAttachmentV2"
    assert thread_contract.items[1].attachments[0].download_url == "/app/api/laudo/88/mesa/anexos/9"
    assert {item.actor_role for item in thread_contract.items} == {"inspetor", "mesa"}

    dumped_feed = feed_contract.model_dump(mode="python")
    dumped_thread = thread_contract.model_dump(mode="python")
    assert "recent_reviews" not in dumped_feed
    assert "dados_formulario" not in dumped_feed
    assert "parecer_ia" not in dumped_thread
    assert "recent_reviews" not in dumped_thread


def test_contrato_publico_mobile_v2_oculta_feedback_da_mesa_quando_politica_fica_fechada() -> None:
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
        source_channel="android_mesa_feed_v2",
        allows_edit=True,
        has_interaction=True,
        report_types={"padrao": "Inspeção Geral (Padrão)"},
        laudo_card=laudo_card,
    )
    mensagem_inspetor = SimpleNamespace(
        id=300,
        tipo=TipoMensagem.HUMANO_INSP.value,
        conteudo="Mensagem visível do inspetor.",
        criado_em=datetime(2026, 3, 25, 10, 28, tzinfo=timezone.utc),
        remetente_id=17,
        lida=True,
        resolvida_em=None,
        client_message_id="mesa:public:v2:hidden:0001",
        anexos_mesa=[],
    )
    mensagem_mesa = SimpleNamespace(
        id=301,
        tipo=TipoMensagem.HUMANO_ENG.value,
        conteudo="Comentário ainda não liberado ao mobile.",
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

    feed_item = build_mobile_inspector_feed_item_v2(
        projection=projection,
        interactions=interactions,
        source_channel="android_mesa_feed_v2",
        visible_review_signals=review_signals,
        provenance_summary=None,
        case_metadata={"updated_at_iso": interactions[-1].timestamp.isoformat()},
    )
    thread_contract = build_mobile_inspector_thread_v2(
        projection=projection,
        conversation=conversation,
        source_channel="android_mesa_thread_v2",
        visible_review_signals=review_signals,
        provenance_summary=None,
    )

    assert feed_item.review_signals.review_visible_to_inspector is False
    assert feed_item.feedback_policy.feedback_mode == "hidden"
    assert feed_item.feedback_policy.feedback_message_bodies_visible is False
    assert feed_item.collaboration.summary.feedback_visible_to_inspector is False
    assert feed_item.collaboration.summary.visible_feedback_count == 0
    assert feed_item.collaboration.latest_feedback is None
    assert feed_item.total_visible_interactions == 1
    assert feed_item.unread_visible_interactions == 0
    assert feed_item.latest_interaction is not None
    assert feed_item.latest_interaction.actor_role == "inspetor"
    assert thread_contract.review_signals.visible_feedback_count == 0
    assert thread_contract.feedback_policy.latest_feedback_pointer_visible is False
    assert thread_contract.collaboration.summary.latest_feedback_message_id is None
    assert thread_contract.collaboration.summary.latest_feedback_preview == ""
    assert len(thread_contract.items) == 1
    assert {item.actor_role for item in thread_contract.items} == {"inspetor"}


def test_endpoints_publicos_mobile_v2_exigem_flag_e_preservam_legado(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    headers = _login_mobile_inspetor(client)

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Public Contract",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Primeira interação mobile V2",
        )
        banco.add(laudo)
        banco.flush()
        banco.add(
            MensagemLaudo(
                laudo_id=laudo.id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Retorno novo da mesa para contrato público.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        laudo.atualizado_em = datetime.now(timezone.utc)
        banco.commit()
        laudo_id = int(laudo.id)

    for flag in (
        "TARIEL_V2_ANDROID_PUBLIC_CONTRACT",
        "TARIEL_V2_ANDROID_FEED_ADAPTER",
        "TARIEL_V2_ANDROID_THREAD_ADAPTER",
    ):
        monkeypatch.delenv(flag, raising=False)

    resposta_feed_legado_base = client.get(
        "/app/api/mobile/mesa/feed",
        headers=headers,
        params={"laudo_ids": str(laudo_id)},
    )
    assert resposta_feed_legado_base.status_code == 200
    payload_feed_legado_base = resposta_feed_legado_base.json()

    resposta_thread_legado_base = client.get(
        f"/app/api/laudo/{laudo_id}/mesa/mensagens",
        headers=headers,
    )
    assert resposta_thread_legado_base.status_code == 200
    payload_thread_legado_base = resposta_thread_legado_base.json()

    resposta_feed_v2_desligado = client.get(
        "/app/api/mobile/v2/mesa/feed",
        headers=headers,
        params={"laudo_ids": str(laudo_id)},
    )
    resposta_thread_v2_desligado = client.get(
        f"/app/api/mobile/v2/laudo/{laudo_id}/mesa/mensagens",
        headers=headers,
    )
    assert resposta_feed_v2_desligado.status_code == 404
    assert resposta_thread_v2_desligado.status_code == 404

    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")

    resposta_feed_legado_apos_flag = client.get(
        "/app/api/mobile/mesa/feed",
        headers=headers,
        params={"laudo_ids": str(laudo_id)},
    )
    resposta_thread_legado_apos_flag = client.get(
        f"/app/api/laudo/{laudo_id}/mesa/mensagens",
        headers=headers,
    )
    assert resposta_feed_legado_apos_flag.status_code == 200
    assert resposta_thread_legado_apos_flag.status_code == 200
    assert resposta_feed_legado_apos_flag.json() == payload_feed_legado_base
    assert resposta_thread_legado_apos_flag.json() == payload_thread_legado_base
    assert "contract_name" not in resposta_feed_legado_apos_flag.json()
    assert "contract_name" not in resposta_thread_legado_apos_flag.json()

    resposta_feed_v2 = client.get(
        "/app/api/mobile/v2/mesa/feed",
        headers=headers,
        params={"laudo_ids": str(laudo_id)},
    )
    resposta_thread_v2 = client.get(
        f"/app/api/mobile/v2/laudo/{laudo_id}/mesa/mensagens",
        headers=headers,
    )
    assert resposta_feed_v2.status_code == 200
    assert resposta_thread_v2.status_code == 200

    payload_feed_v2 = resposta_feed_v2.json()
    payload_thread_v2 = resposta_thread_v2.json()
    assert payload_feed_v2["contract_name"] == "MobileInspectorFeedV2"
    assert payload_feed_v2["contract_version"] == "v2"
    assert payload_feed_v2["items"][0]["legacy_laudo_id"] == laudo_id
    assert payload_feed_v2["items"][0]["case_lifecycle_status"] == "aguardando_mesa"
    assert payload_feed_v2["items"][0]["case_workflow_mode"] == "laudo_com_mesa"
    assert payload_feed_v2["items"][0]["active_owner_role"] == "mesa"
    assert payload_feed_v2["items"][0]["allowed_next_lifecycle_statuses"] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert payload_feed_v2["items"][0]["allowed_surface_actions"] == [
        "mesa_approve",
        "mesa_return",
    ]
    assert payload_thread_v2["contract_name"] == "MobileInspectorThreadV2"
    assert payload_thread_v2["contract_version"] == "v2"
    assert payload_thread_v2["legacy_laudo_id"] == laudo_id
    assert payload_thread_v2["case_lifecycle_status"] == "aguardando_mesa"
    assert payload_thread_v2["case_workflow_mode"] == "laudo_com_mesa"
    assert payload_thread_v2["active_owner_role"] == "mesa"
    assert payload_thread_v2["allowed_next_lifecycle_statuses"] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert payload_thread_v2["allowed_surface_actions"] == [
        "mesa_approve",
        "mesa_return",
    ]
    assert payload_thread_v2["mobile_review_package"]["contract_name"] == "MobileInspectorReviewPackageV2"
    assert payload_thread_v2["mobile_review_package"]["allowed_decisions"] == []
    assert payload_thread_v2["mobile_review_package"]["supports_block_reopen"] is False
    assert "coverage_map" in payload_thread_v2["mobile_review_package"]
    assert "inspection_history" in payload_thread_v2["mobile_review_package"]
    assert "public_verification" in payload_thread_v2["mobile_review_package"]
    assert "anexo_pack" in payload_thread_v2["mobile_review_package"]
    assert "emissao_oficial" in payload_thread_v2["mobile_review_package"]
    assert payload_thread_v2["mobile_review_package"]["public_verification"]["qr_image_data_uri"].startswith(
        "data:image/png;base64,"
    )


def test_contrato_publico_mobile_v2_restringe_visibilidade_ao_inspetor_e_registra_telemetria(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    monkeypatch.setenv("TARIEL_V2_ANDROID_PUBLIC_CONTRACT", "1")

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Visibilidade Controlada",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem="Primeira interação da conversa V2",
        )
        banco.add(laudo)
        banco.flush()

        mensagens = [
            MensagemLaudo(
                laudo_id=laudo.id,
                remetente_id=usuario.id,
                tipo=TipoMensagem.USER.value,
                conteudo="Mensagem interna do user que não deve sair no mobile.",
                custo_api_reais=Decimal("0.0000"),
            ),
            MensagemLaudo(
                laudo_id=laudo.id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.IA.value,
                conteudo="Sugestão interna de IA que não deve sair no mobile.",
                custo_api_reais=Decimal("0.0000"),
            ),
            MensagemLaudo(
                laudo_id=laudo.id,
                remetente_id=usuario.id,
                tipo=TipoMensagem.HUMANO_INSP.value,
                conteudo="Resposta do inspetor visível ao Android.",
                custo_api_reais=Decimal("0.0000"),
            ),
            MensagemLaudo(
                laudo_id=laudo.id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Pendência da mesa visível ao inspetor.",
                custo_api_reais=Decimal("0.0000"),
            ),
        ]
        for mensagem in mensagens:
            banco.add(mensagem)
        laudo.atualizado_em = datetime.now(timezone.utc)
        banco.commit()

        request_feed = _build_request(
            "/app/api/mobile/v2/mesa/feed",
            auth_header="Bearer token-public-v2",
        )
        response_feed = asyncio.run(
            feed_mesa_mobile_public_v2(
                request=request_feed,
                laudo_ids=str(laudo.id),
                cursor_atualizado_em=None,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_feed = json.loads(response_feed.body)

        request_thread = _build_request(
            f"/app/api/mobile/v2/laudo/{laudo.id}/mesa/mensagens",
            auth_header="Bearer token-public-v2",
        )
        response_thread = asyncio.run(
            listar_mensagens_mesa_laudo_mobile_public_v2(
                laudo_id=laudo.id,
                request=request_thread,
                cursor=None,
                apos_id=None,
                limite=40,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_thread = json.loads(response_thread.body)

    assert payload_feed["contract_name"] == "MobileInspectorFeedV2"
    assert payload_feed["items"][0]["total_visible_interactions"] == 2
    assert payload_feed["items"][0]["latest_interaction"]["actor_role"] == "mesa"
    assert payload_thread["contract_name"] == "MobileInspectorThreadV2"
    assert len(payload_thread["items"]) == 2
    assert {item["actor_role"] for item in payload_thread["items"]} == {"inspetor", "mesa"}
    assert {item["legacy_message_type"] for item in payload_thread["items"]} == {
        TipoMensagem.HUMANO_INSP.value,
        TipoMensagem.HUMANO_ENG.value,
    }
    assert {item["item_kind"] for item in payload_thread["items"]} == {"whisper", "pendency"}
    assert {item["message_kind"] for item in payload_thread["items"]} == {
        "inspector_whisper",
        "mesa_pendency",
    }
    assert {item["pendency_state"] for item in payload_thread["items"]} == {
        "not_applicable",
        "open",
    }
    assert "parecer_ia" not in payload_thread
    assert "dados_formulario" not in payload_thread
    assert "recent_reviews" not in payload_feed["items"][0]
    assert payload_thread["mobile_review_package"]["contract_name"] == "MobileInspectorReviewPackageV2"
    assert "historico_refazer_inspetor" in payload_thread["mobile_review_package"]
    assert "inspection_history" in payload_thread["mobile_review_package"]
    assert "public_verification" in payload_thread["mobile_review_package"]
    assert request_feed.state.v2_android_public_contract_feed_summary["used_public_contract"] is True
    assert request_feed.state.v2_android_public_contract_feed_summary["legacy_case_compatible"] == 1
    assert (
        request_thread.state.v2_android_public_contract_thread_result["legacy_case_adapter"]["contract_name"]
        == "AndroidCaseViewAdapterResultV1"
    )
    assert request_thread.state.v2_android_public_contract_thread_summary["used_public_contract"] is True
