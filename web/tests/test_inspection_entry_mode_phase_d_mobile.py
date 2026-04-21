from __future__ import annotations

import uuid

import app.domains.chat.routes as rotas_inspetor
from app.shared.database import Laudo, MensagemLaudo, StatusRevisao, TipoMensagem, Usuario
from tests.regras_rotas_criticas_support import SENHA_PADRAO, _login_app_inspetor


def _login_mobile_inspetor(client, email: str) -> dict[str, str]:
    resposta = client.post(
        "/app/api/mobile/auth/login",
        json={
            "email": email,
            "senha": SENHA_PADRAO,
            "lembrar": True,
        },
    )
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def _guided_inspection_payload() -> dict[str, object]:
    return {
        "guided_inspection_draft": {
            "template_key": "nr35_linha_vida",
            "template_label": "NR35 Linha de Vida",
            "started_at": "2026-04-06T22:30:00.000Z",
            "current_step_index": 1,
            "completed_step_ids": ["identificacao_laudo"],
            "checklist": [
                {
                    "id": "identificacao_laudo",
                    "title": "Identificacao do ativo e do laudo",
                    "prompt": "registre unidade, local e tag",
                    "evidence_hint": "codigo do ativo e local resumido",
                },
                {
                    "id": "contexto_vistoria",
                    "title": "Contexto da vistoria",
                    "prompt": "confirme responsaveis e data",
                    "evidence_hint": "nomes, data e acompanhamento",
                },
            ],
        }
    }


def _guided_inspection_payload_nr11() -> dict[str, object]:
    return {
        "guided_inspection_draft": {
            "template_key": "nr11_movimentacao",
            "template_label": "NR11 Movimentacao e Armazenagem",
            "started_at": "2026-04-06T22:30:00.000Z",
            "current_step_index": 1,
            "completed_step_ids": ["identificacao_operacao"],
            "checklist": [
                {
                    "id": "identificacao_operacao",
                    "title": "Identificacao da operacao",
                    "prompt": "registre equipamento, carga e setor",
                    "evidence_hint": "equipamento, carga e setor",
                },
                {
                    "id": "levantamento_campo",
                    "title": "Levantamento em campo",
                    "prompt": "descreva fluxo e condicoes do ambiente",
                    "evidence_hint": "fluxo, layout e condicoes do ambiente",
                },
            ],
        }
    }


def test_mobile_persiste_draft_guiado_canonico_e_round_trip_no_caso(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    headers = _login_mobile_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="linha de vida",
            primeira_mensagem="Coleta iniciada no mobile.",
            tipo_template="nr35",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
        )
        banco.add(laudo)
        banco.commit()
        banco.refresh(laudo)
        laudo_id = int(laudo.id)

    resposta_salvar = client.put(
        f"/app/api/mobile/laudo/{laudo_id}/guided-inspection-draft",
        headers=headers,
        json=_guided_inspection_payload(),
    )

    assert resposta_salvar.status_code == 200
    assert resposta_salvar.json()["ok"] is True
    assert resposta_salvar.json()["laudo_id"] == laudo_id
    assert (
        resposta_salvar.json()["guided_inspection_draft"]["template_key"]
        == "nr35_linha_vida"
    )
    assert resposta_salvar.json()["pre_laudo_summary"]["status"] == "needs_completion"
    assert resposta_salvar.json()["pre_laudo_summary"]["ready_for_structured_form"] is True
    assert resposta_salvar.json()["pre_laudo_summary"]["ready_for_finalization"] is False

    resposta_mensagens = client.get(
        f"/app/api/laudo/{laudo_id}/mensagens",
        headers=headers,
    )
    assert resposta_mensagens.status_code == 200
    assert (
        resposta_mensagens.json()["guided_inspection_draft"]["current_step_index"]
        == 1
    )
    assert resposta_mensagens.json()["guided_inspection_draft"]["checklist"][1][
        "id"
    ] == "contexto_vistoria"
    assert resposta_mensagens.json()["pre_laudo_summary"]["status"] == "needs_completion"
    assert any(
        "foto obrigatória" in pergunta.lower()
        or "conclua a etapa guiada" in pergunta.lower()
        for pergunta in resposta_mensagens.json()["pre_laudo_summary"]["next_questions"]
    )

    resposta_status = client.get("/app/api/laudo/status", headers=headers)
    assert resposta_status.status_code == 200
    assert resposta_status.json()["laudo_id"] == laudo_id
    assert (
        resposta_status.json()["guided_inspection_draft"]["completed_step_ids"]
        == ["identificacao_laudo"]
    )
    assert resposta_status.json()["pre_laudo_summary"]["status"] == "needs_completion"
    assert resposta_status.json()["pre_laudo_summary"]["missing_field_count"] >= 1

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.guided_inspection_draft_json is not None
        assert laudo.guided_inspection_draft_json["template_key"] == "nr35_linha_vida"
        assert laudo.guided_inspection_draft_json["current_step_index"] == 1
        assert laudo.catalog_family_key == "nr35_inspecao_linha_de_vida"
        assert laudo.catalog_family_label == "NR35 Inspecao de Linha de Vida"


def test_mobile_guided_draft_novo_vincula_family_key_padrao_quando_nao_ha_catalogo_explicito(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    headers = _login_mobile_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="movimentacao",
            primeira_mensagem="Coleta NR11 iniciada no mobile.",
            tipo_template="padrao",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
        )
        banco.add(laudo)
        banco.commit()
        banco.refresh(laudo)
        laudo_id = int(laudo.id)

    resposta_salvar = client.put(
        f"/app/api/mobile/laudo/{laudo_id}/guided-inspection-draft",
        headers=headers,
        json=_guided_inspection_payload_nr11(),
    )

    assert resposta_salvar.status_code == 200
    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.tipo_template == "nr11_movimentacao"
        assert laudo.catalog_family_key == "nr11_inspecao_movimentacao_armazenagem"
        assert laudo.catalog_family_label == "NR11 Inspecao de Movimentacao e Armazenagem"


def test_mobile_rejeita_persistencia_do_draft_guiado_fora_do_rascunho(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    headers = _login_mobile_inspetor(client, "inspetor@empresa-a.test")

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="linha de vida",
            primeira_mensagem="Caso fechado para emissao.",
            tipo_template="nr35",
            status_revisao=StatusRevisao.APROVADO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="existing_case_state",
        )
        banco.add(laudo)
        banco.commit()
        banco.refresh(laudo)
        laudo_id = int(laudo.id)

    resposta = client.put(
        f"/app/api/mobile/laudo/{laudo_id}/guided-inspection-draft",
        headers=headers,
        json=_guided_inspection_payload(),
    )

    assert resposta.status_code == 400
    assert "rascunho" in resposta.json()["detail"].lower()


def test_chat_guiado_vincula_evidencia_ao_bundle_do_caso_e_registra_mesa(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    prompt_capturado: dict[str, str] = {}

    class ClienteIAStub:
        def gerar_resposta_stream(self, mensagem: str, *_args, **_kwargs):
            prompt_capturado["mensagem"] = mensagem
            yield "Resposta guiada inicial.\n"

    cliente_original = rotas_inspetor.cliente_ia
    rotas_inspetor.cliente_ia = ClienteIAStub()
    try:
        resposta_chat = client.post(
            "/app/api/chat",
            headers={"X-CSRF-Token": csrf},
            json={
                "mensagem": "Coleta guiada com foto e contexto do caso.",
                "historico": [],
                "entry_mode_preference": "evidence_first",
                "guided_inspection_draft": {
                    "template_key": "nr35_linha_vida",
                    "template_label": "NR35 Linha de Vida",
                    "started_at": "2026-04-06T22:30:00.000Z",
                    "current_step_index": 1,
                    "completed_step_ids": ["identificacao_laudo"],
                    "checklist": [
                        {
                            "id": "identificacao_laudo",
                            "title": "Identificacao do ativo e do laudo",
                            "prompt": "registre unidade, local e tag",
                            "evidence_hint": "codigo do ativo e local resumido",
                        },
                        {
                            "id": "contexto_vistoria",
                            "title": "Contexto da vistoria",
                            "prompt": "confirme responsaveis e data",
                            "evidence_hint": "nomes, data e acompanhamento",
                        },
                    ],
                },
                "guided_inspection_context": {
                    "template_key": "nr35_linha_vida",
                    "step_id": "contexto_vistoria",
                    "step_title": "Contexto da vistoria",
                    "attachment_kind": "image",
                },
            },
        )
    finally:
        rotas_inspetor.cliente_ia = cliente_original

    assert resposta_chat.status_code == 200

    resposta_status = client.get("/app/api/laudo/status", headers={"X-CSRF-Token": csrf})
    assert resposta_status.status_code == 200
    laudo_id = int(resposta_status.json()["laudo_id"])

    resposta_mensagens = client.get(
        f"/app/api/laudo/{laudo_id}/mensagens",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta_mensagens.status_code == 200
    draft = resposta_mensagens.json()["guided_inspection_draft"]
    assert draft["evidence_bundle_kind"] == "case_thread"
    assert draft["completed_step_ids"] == [
        "identificacao_laudo",
        "contexto_vistoria",
    ]
    assert draft["current_step_index"] == 1
    assert draft["evidence_refs"][0]["step_id"] == "contexto_vistoria"
    assert draft["evidence_refs"][0]["attachment_kind"] == "image"
    assert draft["mesa_handoff"]["review_mode"] == "mesa_required"
    assert draft["mesa_handoff"]["reason_code"] == "policy_review_mode"
    assert "[pre_laudo_operacional]" in prompt_capturado["mensagem"]
    assert "Contexto da vistoria" in prompt_capturado["mensagem"]
    assert resposta_mensagens.json()["pre_laudo_summary"]["status"] in prompt_capturado["mensagem"]
    for pergunta in resposta_mensagens.json()["pre_laudo_summary"]["next_questions"]:
        assert pergunta in prompt_capturado["mensagem"]

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.guided_inspection_draft_json is not None
        mensagem_usuario = (
            banco.query(MensagemLaudo)
            .filter(
                MensagemLaudo.laudo_id == laudo_id,
                MensagemLaudo.tipo == TipoMensagem.USER.value,
            )
            .order_by(MensagemLaudo.id.asc())
            .first()
        )
        assert mensagem_usuario is not None
        assert (
            laudo.guided_inspection_draft_json["evidence_refs"][0]["message_id"]
            == int(mensagem_usuario.id)
        )
        assert laudo.guided_inspection_draft_json["completed_step_ids"] == [
            "identificacao_laudo",
            "contexto_vistoria",
        ]
