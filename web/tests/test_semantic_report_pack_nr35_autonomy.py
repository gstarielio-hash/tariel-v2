from __future__ import annotations

import hashlib
import uuid

from app.shared.database import (
    AprendizadoVisualIa,
    Laudo,
    MensagemLaudo,
    StatusRevisao,
    TipoMensagem,
    Usuario,
)
from tests.regras_rotas_criticas_support import (
    _imagem_png_data_uri_teste,
    _login_app_inspetor,
)


def _nr35_guided_checklist() -> list[dict[str, str]]:
    return [
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
        {
            "id": "objeto_inspecao",
            "title": "Objeto da inspecao",
            "prompt": "descreva a linha de vida",
            "evidence_hint": "tipo e escopo resumido",
        },
        {
            "id": "componentes_inspecionados",
            "title": "Componentes inspecionados",
            "prompt": "marque C, NC ou NA",
            "evidence_hint": "fixacao, cabo, esticador, sapatilha, olhal e grampos",
        },
        {
            "id": "registros_fotograficos",
            "title": "Registros fotograficos",
            "prompt": "anexe fotos principais",
            "evidence_hint": "vista geral, ponto superior e ponto inferior",
        },
        {
            "id": "conclusao",
            "title": "Conclusao e proxima inspecao",
            "prompt": "defina o status final",
            "evidence_hint": "status, justificativa e proxima inspecao",
        },
    ]


def _criar_laudo_nr35_guiado(
    ambiente_critico,
    *,
    com_fotos: bool,
) -> int:
    SessionLocal = ambiente_critico["SessionLocal"]
    imagem_data_uri = _imagem_png_data_uri_teste()
    imagem_sha256 = hashlib.sha256(imagem_data_uri.encode("utf-8")).hexdigest()

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR35 Linha de Vida",
            primeira_mensagem="Inspecao NR35 da linha de vida com evidencias tecnicas completas.",
            tipo_template="nr35_linha_vida",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
        )
        banco.add(laudo)
        banco.flush()

        def add_user_message(texto: str) -> MensagemLaudo:
            mensagem = MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.USER.value,
                conteudo=texto,
            )
            banco.add(mensagem)
            banco.flush()
            return mensagem

        msg_identificacao = add_user_message(
            "Unidade: Orizona - GO; Local: Orizona - GO; Laudo inspecao: AT-IN-OZ-001-01-26; Fabricante: MC-CRMR-0032."
        )
        msg_contexto = add_user_message(
            "Contratante: Caramuru Alimentos S/A; Contratada: ATY Service LTDA; "
            "Engenheiro: Wellington Pedro dos Santos; Inspetor: Marcel Renato "
            "Silva; Data: 2026-01-29."
        )
        msg_objeto = add_user_message(
            "Linha de vida vertical da escada de acesso ao elevador 01. Escopo da inspecao: diagnostico geral do ativo."
        )
        msg_componentes = add_user_message(
            "fixacao dos pontos: C; cabo de aco: C; esticador: C; sapatilha: C; olhal: C; grampos: C."
        )
        msg_conclusao = add_user_message(
            "Status: Aprovado. Observacoes finais: linha de vida em conformidade visual no momento da vistoria."
        )

        refs = [
            {
                "message_id": int(msg_identificacao.id),
                "step_id": "identificacao_laudo",
                "step_title": "Identificacao do ativo e do laudo",
                "captured_at": msg_identificacao.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_contexto.id),
                "step_id": "contexto_vistoria",
                "step_title": "Contexto da vistoria",
                "captured_at": msg_contexto.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_objeto.id),
                "step_id": "objeto_inspecao",
                "step_title": "Objeto da inspecao",
                "captured_at": msg_objeto.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_componentes.id),
                "step_id": "componentes_inspecionados",
                "step_title": "Componentes inspecionados",
                "captured_at": msg_componentes.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_conclusao.id),
                "step_id": "conclusao",
                "step_title": "Conclusao e proxima inspecao",
                "captured_at": msg_conclusao.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
        ]

        if com_fotos:
            for indice, titulo in enumerate(
                ("Vista geral", "Ponto superior", "Ponto inferior"),
                start=1,
            ):
                mensagem_foto = add_user_message("[imagem]")
                refs.append(
                    {
                        "message_id": int(mensagem_foto.id),
                        "step_id": "registros_fotograficos",
                        "step_title": titulo,
                        "captured_at": mensagem_foto.criado_em.isoformat(),
                        "evidence_kind": "chat_message",
                        "attachment_kind": "image",
                    }
                )
                banco.add(
                    AprendizadoVisualIa(
                        empresa_id=usuario.empresa_id,
                        laudo_id=int(laudo.id),
                        mensagem_referencia_id=int(mensagem_foto.id),
                        criado_por_id=usuario.id,
                        setor_industrial="NR35 Linha de Vida",
                        resumo=f"Foto {indice} da linha de vida",
                        descricao_contexto=f"Evidencia fotografica {indice} do caso piloto.",
                        correcao_inspetor="Registro fotografico confirmado pelo inspetor.",
                        imagem_url=f"/static/test/nr35_{indice}.png",
                        imagem_nome_original=f"nr35_{indice}.png",
                        imagem_mime_type="image/png",
                        imagem_sha256=imagem_sha256,
                        caminho_arquivo=f"/tmp/nr35_{indice}.png",
                    )
                )

        banco.add(
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer tecnico preliminar consolidado pela IA.",
            )
        )
        laudo.guided_inspection_draft_json = {
            "template_key": "nr35_linha_vida",
            "template_label": "NR35 Linha de Vida",
            "started_at": "2026-04-06T23:40:00.000Z",
            "current_step_index": 5,
            "completed_step_ids": [item["id"] for item in _nr35_guided_checklist()],
            "checklist": _nr35_guided_checklist(),
            "evidence_bundle_kind": "case_thread",
            "evidence_refs": refs,
            "mesa_handoff": None,
        }
        banco.commit()
        banco.refresh(laudo)
        return int(laudo.id)


def test_gate_nr35_expoe_image_slots_pendentes_antes_da_finalizacao(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr35_guiado(ambiente_critico, com_fotos=False)

    resposta = client.get(
        f"/app/api/laudo/{laudo_id}/gate-qualidade",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["report_pack_draft"]["modeled"] is True
    assert corpo["review_mode_sugerido"] == "mesa_required"
    assert (
        corpo["report_pack_draft"]["quality_gates"]["required_image_slots_complete"]
        is False
    )
    pendentes = [
        slot
        for slot in corpo["report_pack_draft"]["image_slots"]
        if slot["status"] == "pending"
    ]
    assert len(pendentes) == 3
    missing_codes = {
        item["code"]
        for item in corpo["report_pack_draft"]["quality_gates"]["missing_evidence"]
    }
    assert "nr35_image_slot_missing" in missing_codes
    assert corpo["report_pack_draft"]["pre_laudo_outline"]["status"] == "needs_completion"
    assert corpo["report_pack_draft"]["pre_laudo_outline"]["ready_for_structured_form"] is True
    assert corpo["report_pack_draft"]["pre_laudo_outline"]["ready_for_finalization"] is False
    assert corpo["report_pack_draft"]["pre_laudo_document"]["artifact_snapshot"][
        "has_family_schema"
    ] is True
    assert any(
        item["title"] == "Identificacao"
        for item in corpo["report_pack_draft"]["pre_laudo_document"]["document_sections"]
    )
    assert any(
        "foto obrigatória" in pergunta.lower()
        for pergunta in corpo["report_pack_draft"]["pre_laudo_outline"]["next_questions"]
    )


def test_finalizacao_nr35_mobile_autonomous_aprova_direto(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr35_guiado(ambiente_critico, com_fotos=True)

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["review_mode_final"] == "mobile_autonomous"
    assert "aprovado automaticamente" in corpo["message"].lower()
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
    assert corpo["report_pack_draft"]["quality_gates"]["final_validation_mode"] == (
        "mobile_autonomous"
    )
    assert corpo["report_pack_draft"]["pre_laudo_outline"]["status"] == (
        "ready_for_finalization"
    )
    assert corpo["report_pack_draft"]["pre_laudo_outline"]["ready_for_finalization"] is True
    assert corpo["pre_laudo_summary"]["status"] == "ready_for_finalization"
    assert corpo["pre_laudo_summary"]["ready_for_finalization"] is True
    assert any(
        item["status"] == "ready"
        for item in corpo["report_pack_draft"]["pre_laudo_document"]["document_flow"]
    )
    assert any(
        item["title"] == "Conclusao"
        for item in corpo["report_pack_draft"]["pre_laudo_document"]["document_sections"]
    )

    status = client.get("/app/api/laudo/status", headers={"X-CSRF-Token": csrf})
    assert status.status_code == 200
    assert status.json()["estado"] == "aprovado"
    assert status.json()["report_pack_draft"]["quality_gates"]["autonomy_ready"] is True
    assert status.json()["pre_laudo_summary"]["status"] == "ready_for_finalization"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.APROVADO.value
        assert laudo.dados_formulario is not None
        assert (
            laudo.dados_formulario["componentes_inspecionados"]["fixacao_dos_pontos"]["condicao"]
            == "C"
        )
        assert (
            laudo.dados_formulario["conclusao"]["status"] == "Aprovado"
        )
