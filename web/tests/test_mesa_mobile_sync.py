from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.shared.database import (
    EvidenceMesaStatus,
    EvidenceOperationalStatus,
    EvidenceValidation,
    Laudo,
    MensagemLaudo,
    OperationalIrregularity,
    StatusRevisao,
    TipoMensagem,
)
from tests.regras_rotas_criticas_support import SENHA_PADRAO, _criar_laudo, _login_app_inspetor
from tests.test_semantic_report_pack_nr35_autonomy import _criar_laudo_nr35_guiado


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
    token = resposta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_mesa_mobile_idempotencia_reaproveita_mesma_mensagem(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    payload = {
        "texto": "Validação mobile com idempotência.",
        "client_message_id": "mesa:pytest:idempotencia:0001",
    }
    primeira = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf},
        json=payload,
    )
    assert primeira.status_code == 201
    corpo_primeira = primeira.json()
    assert corpo_primeira["idempotent_replay"] is False
    assert corpo_primeira["mensagem"]["client_message_id"] == payload["client_message_id"]

    segunda = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf},
        json=payload,
    )
    assert segunda.status_code == 200
    corpo_segunda = segunda.json()
    assert corpo_segunda["idempotent_replay"] is True
    assert corpo_segunda["mensagem"]["id"] == corpo_primeira["mensagem"]["id"]
    assert corpo_segunda["request_id"]

    with SessionLocal() as banco:
        mensagens = (
            banco.query(MensagemLaudo)
            .filter(
                MensagemLaudo.laudo_id == laudo_id,
                MensagemLaudo.client_message_id == payload["client_message_id"],
            )
            .all()
        )
        assert len(mensagens) == 1


def test_mesa_mobile_delta_e_resumo_refletem_novas_mensagens(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    primeira = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/mensagem",
        headers={"X-CSRF-Token": csrf},
        json={"texto": "Primeira mensagem da mesa sync."},
    )
    assert primeira.status_code == 201
    cursor_ultimo_id = int(primeira.json()["mensagem"]["id"])

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Retorno novo da mesa para sync.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        laudo.atualizado_em = datetime.now(timezone.utc)
        banco.commit()

    resposta_delta = client.get(
        f"/app/api/laudo/{laudo_id}/mesa/mensagens",
        params={"apos_id": cursor_ultimo_id},
    )
    assert resposta_delta.status_code == 200
    corpo = resposta_delta.json()
    assert corpo["sync"]["modo"] == "delta"
    assert corpo["attachment_policy"]["policy_name"] == "android_attachment_sync_policy"
    assert len(corpo["itens"]) == 1
    assert corpo["itens"][0]["texto"] == "Retorno novo da mesa para sync."
    assert corpo["cursor_ultimo_id"] == corpo["resumo"]["ultima_mensagem_id"]
    assert corpo["resumo"]["total_mensagens"] == 2
    assert corpo["resumo"]["pendencias_abertas"] == 1
    assert corpo["resumo"]["mensagens_nao_lidas"] == 1

    resposta_resumo = client.get(f"/app/api/laudo/{laudo_id}/mesa/resumo")
    assert resposta_resumo.status_code == 200
    resumo = resposta_resumo.json()["resumo"]
    assert resumo["ultima_mensagem_preview"] == "Retorno novo da mesa para sync."
    assert resumo["ultima_mensagem_tipo"] == TipoMensagem.HUMANO_ENG.value


def test_feed_mobile_mesa_retorna_apenas_laudos_alterados_desde_cursor(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    headers = _login_mobile_inspetor(client)

    with SessionLocal() as banco:
        laudo_a = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo_b = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_a,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem inicial da mesa no laudo A.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        laudo_modelo_a = banco.get(Laudo, laudo_a)
        assert laudo_modelo_a is not None
        laudo_modelo_a.atualizado_em = datetime.now(timezone.utc)
        banco.commit()

    primeira = client.get(
        "/app/api/mobile/mesa/feed",
        headers=headers,
        params={"laudo_ids": f"{laudo_a},{laudo_b}"},
    )
    assert primeira.status_code == 200
    corpo_primeira = primeira.json()
    assert set(corpo_primeira["laudo_ids"]) == {laudo_a, laudo_b}
    assert {item["laudo_id"] for item in corpo_primeira["itens"]} == {laudo_a, laudo_b}
    cursor = corpo_primeira["cursor_atual"]
    assert cursor

    with SessionLocal() as banco:
        laudo_modelo_b = banco.get(Laudo, laudo_b)
        assert laudo_modelo_b is not None
        banco.add(
            MensagemLaudo(
                laudo_id=laudo_b,
                remetente_id=ids["revisor_a"],
                tipo=TipoMensagem.HUMANO_ENG.value,
                conteudo="Mensagem nova da mesa no laudo B.",
                custo_api_reais=Decimal("0.0000"),
            )
        )
        laudo_modelo_b.atualizado_em = datetime.now(timezone.utc)
        banco.commit()

    segunda = client.get(
        "/app/api/mobile/mesa/feed",
        headers=headers,
        params={
            "laudo_ids": f"{laudo_a},{laudo_b}",
            "cursor_atualizado_em": cursor,
        },
    )
    assert segunda.status_code == 200
    corpo_segunda = segunda.json()
    assert len(corpo_segunda["itens"]) == 1
    assert corpo_segunda["itens"][0]["laudo_id"] == laudo_b
    assert corpo_segunda["itens"][0]["resumo"]["ultima_mensagem_preview"] == "Mensagem nova da mesa no laudo B."


def test_mesa_mobile_resposta_com_imagem_resolve_refazer_operacional_referenciado(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        mensagem_mesa = MensagemLaudo(
            laudo_id=laudo_id,
            remetente_id=ids["revisor_a"],
            tipo=TipoMensagem.HUMANO_ENG.value,
            conteudo="Refazer foto da placa.",
            custo_api_reais=Decimal("0.0000"),
            metadata_json={
                "task_kind": "coverage_return_request",
                "evidence_key": "slot:foto_placa",
                "block_key": "coverage_return:slot:foto_placa",
                "title": "Foto da placa",
                "kind": "image_slot",
                "required": True,
                "summary": "Foto borrada.",
                "required_action": "Reenviar imagem nitida da placa.",
                "expected_reply_mode": "image_required",
                "expected_reply_mode_label": "imagem obrigatória",
                "failure_reasons": ["foto_borrada"],
            },
        )
        banco.add(mensagem_mesa)
        banco.commit()
        mensagem_id = int(mensagem_mesa.id)

    resposta_thread = client.get(f"/app/api/laudo/{laudo_id}/mesa/mensagens")
    assert resposta_thread.status_code == 200
    itens = resposta_thread.json()["itens"]
    assert itens[0]["operational_context"]["task_kind"] == "coverage_return_request"

    resposta_envio = client.post(
        f"/app/api/laudo/{laudo_id}/mesa/anexo",
        headers={"X-CSRF-Token": csrf},
        data={
            "texto": "Nova captura anexada.",
            "referencia_mensagem_id": str(mensagem_id),
        },
        files={"arquivo": ("placa.jpg", b"fake-jpg", "image/jpeg")},
    )
    assert resposta_envio.status_code == 201
    corpo = resposta_envio.json()
    assert corpo["resumo"]["pendencias_abertas"] == 0

    with SessionLocal() as banco:
        mensagem_atualizada = banco.get(MensagemLaudo, mensagem_id)
        assert mensagem_atualizada is not None
        assert bool(mensagem_atualizada.lida) is True
        assert mensagem_atualizada.resolvida_em is not None
        validacao = (
            banco.query(EvidenceValidation)
            .filter(
                EvidenceValidation.laudo_id == laudo_id,
                EvidenceValidation.evidence_key == "slot:foto_placa",
            )
            .one()
        )
        assert validacao.operational_status == "replaced"
        assert validacao.mesa_status == "needs_recheck"
        assert str(validacao.replacement_evidence_key or "").startswith("msg:")


def test_mobile_review_command_aprovar_no_mobile_fecha_caso_autonomo(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    headers = _login_mobile_inspetor(client)
    laudo_id = _criar_laudo_nr35_guiado(ambiente_critico, com_fotos=True)

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers,
        json={"command": "aprovar_no_mobile"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ok"] is True
    assert corpo["command"] == "aprovar_no_mobile"
    assert corpo["review_mode_final"] == "mobile_autonomous"
    assert corpo["estado"] == "aprovado"
    assert corpo["case_lifecycle_status"] == "aprovado"
    assert corpo["case_workflow_mode"] == "laudo_guiado"
    assert corpo["active_owner_role"] == "none"
    assert corpo["allowed_next_lifecycle_statuses"] == [
        "emitido",
        "devolvido_para_correcao",
    ]
    assert corpo["laudo_card"]["case_lifecycle_status"] == "aprovado"
    assert corpo["laudo_card"]["case_workflow_mode"] == "laudo_guiado"
    assert corpo["laudo_card"]["active_owner_role"] == "none"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.APROVADO.value


def test_mobile_review_command_enviar_para_mesa_forca_handoff(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    headers = _login_mobile_inspetor(client)
    laudo_id = _criar_laudo_nr35_guiado(ambiente_critico, com_fotos=True)

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers,
        json={"command": "enviar_para_mesa"},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ok"] is True
    assert corpo["command"] == "enviar_para_mesa"
    assert corpo["review_mode_final"] == "mesa_required"
    assert corpo["estado"] == "aguardando"
    assert corpo["case_lifecycle_status"] == "aguardando_mesa"
    assert corpo["case_workflow_mode"] == "laudo_com_mesa"
    assert corpo["active_owner_role"] == "mesa"
    assert corpo["allowed_next_lifecycle_statuses"] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert corpo["laudo_card"]["case_lifecycle_status"] == "aguardando_mesa"
    assert corpo["laudo_card"]["case_workflow_mode"] == "laudo_com_mesa"
    assert corpo["laudo_card"]["active_owner_role"] == "mesa"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value


def test_mobile_review_command_rejeita_devolucao_fora_do_stage_editavel(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    headers = _login_mobile_inspetor(client)

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers,
        json={
            "command": "devolver_no_mobile",
            "block_key": "identificacao",
            "reason": "Nao deveria permitir devolucao nesse stage.",
        },
    )

    assert resposta.status_code == 422
    corpo = resposta.json()["detail"]
    assert corpo["code"] == "mobile_review_command_not_allowed"
    assert corpo["case_lifecycle_status"] == "aguardando_mesa"
    assert corpo["case_workflow_mode"] == "laudo_com_mesa"
    assert corpo["active_owner_role"] == "mesa"
    assert corpo["allows_edit"] is False
    assert corpo["allowed_next_lifecycle_statuses"] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert corpo["allowed_commands"] == []


def test_mobile_review_command_devolver_no_mobile_abre_irregularidade_e_evidencia(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    headers = _login_mobile_inspetor(client)

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers,
        json={
            "command": "devolver_no_mobile",
            "block_key": "identificacao",
            "evidence_key": "slot:foto_placa",
            "title": "Foto da placa",
            "reason": "Foto borrada e sem leitura da tag.",
            "summary": "Revisão mobile devolveu a evidência da placa.",
            "required_action": "Capturar nova foto frontal da placa.",
            "failure_reasons": ["foto_borrada", "tag_ilegivel"],
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["command"] == "devolver_no_mobile"

    with SessionLocal() as banco:
        irregularidade = (
            banco.query(OperationalIrregularity)
            .filter(
                OperationalIrregularity.laudo_id == laudo_id,
                OperationalIrregularity.irregularity_type == "block_returned_to_inspector",
                OperationalIrregularity.block_key == "identificacao",
            )
            .one()
        )
        assert irregularidade.status == "open"
        validacao = (
            banco.query(EvidenceValidation)
            .filter(
                EvidenceValidation.laudo_id == laudo_id,
                EvidenceValidation.evidence_key == "slot:foto_placa",
            )
            .one()
        )
        assert validacao.operational_status == EvidenceOperationalStatus.IRREGULAR.value
        assert validacao.mesa_status == EvidenceMesaStatus.NEEDS_RECHECK.value


def test_mobile_review_command_reabrir_bloco_registra_field_reopened(ambiente_critico) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    headers = _login_mobile_inspetor(client)

    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/mobile-review-command",
        headers=headers,
        json={
            "command": "reabrir_bloco",
            "block_key": "conclusao",
            "title": "Conclusão",
            "reason": "Conclusão precisa de revalidação local.",
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["command"] == "reabrir_bloco"

    with SessionLocal() as banco:
        irregularidade = (
            banco.query(OperationalIrregularity)
            .filter(
                OperationalIrregularity.laudo_id == laudo_id,
                OperationalIrregularity.irregularity_type == "field_reopened",
                OperationalIrregularity.block_key == "conclusao",
            )
            .one()
        )
        assert irregularidade.status == "open"
