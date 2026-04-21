from __future__ import annotations

import hashlib
import uuid

from app.domains.chat.report_pack_helpers import build_report_pack_draft_for_laudo
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


def _nr35_anchor_guided_checklist() -> list[dict[str, str]]:
    return [
        {
            "id": "identificacao",
            "title": "Identificacao do ponto",
            "prompt": "registre local e tag do ponto",
            "evidence_hint": "objeto principal e codigo interno",
        },
        {
            "id": "avaliacao_tecnica",
            "title": "Avaliacao tecnica do ponto",
            "prompt": "registre fixacao, chumbador, corrosao, deformacao e trincas",
            "evidence_hint": "condicao estrutural resumida",
        },
        {
            "id": "registros_fotograficos",
            "title": "Registros fotograficos",
            "prompt": "anexe as imagens principais",
            "evidence_hint": "vista geral, base e detalhe do achado principal",
        },
        {
            "id": "conclusao",
            "title": "Conclusao",
            "prompt": "registre os pontos de atencao e a conduta final",
            "evidence_hint": "descricao tecnica e recomendacao",
        },
    ]


def _payload_nr35_anchor(*, com_achado: bool) -> dict[str, str]:
    corrosao = (
        "Corrosao superficial no olhal com perda localizada de pintura."
        if com_achado
        else "Sem corrosao aparente no olhal ou na base metalica."
    )
    descricao_pontos_atencao = (
        "Corrosao superficial no olhal e necessidade de limpeza com protecao anticorrosiva."
        if com_achado
        else ""
    )
    observacoes = (
        "Executar limpeza, protecao anticorrosiva e reinspecionar o ponto apos o tratamento."
        if com_achado
        else "Ponto mantido em monitoramento visual de rotina, sem necessidade de bloqueio imediato."
    )
    return {
        "local_inspecao": "Cobertura bloco C - ponto ANC-12",
        "objeto_principal": "Ponto de ancoragem ANC-12",
        "codigo_interno": "ANC-12",
        "referencia_principal": "IMG_801 - visao geral do ponto ANC-12",
        "modo_execucao": "in loco",
        "metodo_inspecao": "Inspecao visual com verificacao de fixacao, corrosao e deformacoes aparentes.",
        "tipo_ancoragem": "Olhal quimico em base metalica",
        "fixacao": "Fixacao com chumbador quimico e base metalica.",
        "chumbador": "Chumbador com torque conferido em campo.",
        "corrosao": corrosao,
        "deformacao": "Sem deformacao permanente aparente.",
        "trinca": "Nao foram observadas trincas na base ou no olhal.",
        "carga_nominal": "15 kN",
        "evidencia_principal": "IMG_802 - detalhe do olhal",
        "evidencia_complementar": "IMG_803 - chumbador e base metalica",
        "certificado_ancoragem": "DOC_081 - certificado_ancoragem_anc12.pdf",
        "memorial_calculo": "DOC_082 - memorial_anc12.pdf",
        "art_numero": "ART 2026-00155",
        "descricao_pontos_atencao": descricao_pontos_atencao,
        "observacoes": observacoes,
    }


def _criar_laudo_nr35_anchor(
    ambiente_critico,
    *,
    com_fotos: bool,
    com_achado: bool,
) -> int:
    SessionLocal = ambiente_critico["SessionLocal"]
    imagem_data_uri = _imagem_png_data_uri_teste()
    imagem_sha256 = hashlib.sha256(imagem_data_uri.encode("utf-8")).hexdigest()

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR35 Ponto de Ancoragem",
            primeira_mensagem="Inspecao NR35 do ponto de ancoragem ANC-12.",
            tipo_template="nr35_ponto_ancoragem",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
            dados_formulario=_payload_nr35_anchor(com_achado=com_achado),
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
            "Ponto de ancoragem ANC-12 na cobertura do bloco C, com referencia principal IMG_801."
        )
        msg_avaliacao = add_user_message(
            "Fixacao integra, chumbador com torque conferido, deformacao ausente e sem trincas aparentes."
        )
        msg_conclusao = add_user_message(
            "Caso consolidado para revisao de engenharia com registros fotograficos e documentacao de apoio."
        )

        refs = [
            {
                "message_id": int(msg_identificacao.id),
                "step_id": "identificacao",
                "step_title": "Identificacao do ponto",
                "captured_at": msg_identificacao.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_avaliacao.id),
                "step_id": "avaliacao_tecnica",
                "step_title": "Avaliacao tecnica do ponto",
                "captured_at": msg_avaliacao.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_conclusao.id),
                "step_id": "conclusao",
                "step_title": "Conclusao",
                "captured_at": msg_conclusao.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
        ]

        if com_fotos:
            for indice, titulo in enumerate(
                ("Vista geral", "Base e fixacao", "Detalhe do achado principal"),
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
                        setor_industrial="NR35 Ponto de Ancoragem",
                        resumo=f"Foto {indice} do ponto de ancoragem",
                        descricao_contexto=f"Evidencia fotografica {indice} do ponto ANC-12.",
                        correcao_inspetor="Registro fotografico confirmado pelo inspetor.",
                        imagem_url=f"/static/test/nr35_anchor_{indice}.png",
                        imagem_nome_original=f"nr35_anchor_{indice}.png",
                        imagem_mime_type="image/png",
                        imagem_sha256=imagem_sha256,
                        caminho_arquivo=f"/tmp/nr35_anchor_{indice}.png",
                    )
                )

        banco.add(
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer tecnico preliminar do ponto de ancoragem.",
            )
        )
        laudo.guided_inspection_draft_json = {
            "template_key": "nr35_ponto_ancoragem",
            "template_label": "NR35 Ponto de Ancoragem",
            "started_at": "2026-04-18T13:00:00.000Z",
            "current_step_index": 3,
            "completed_step_ids": [item["id"] for item in _nr35_anchor_guided_checklist()],
            "checklist": _nr35_anchor_guided_checklist(),
            "evidence_bundle_kind": "case_thread",
            "evidence_refs": refs,
            "mesa_handoff": None,
        }
        banco.commit()
        banco.refresh(laudo)
        return int(laudo.id)


def test_report_pack_nr35_anchor_modela_familia_com_candidato_canonico(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    laudo_id = _criar_laudo_nr35_anchor(
        ambiente_critico,
        com_fotos=True,
        com_achado=True,
    )

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        draft = build_report_pack_draft_for_laudo(banco=banco, laudo=laudo)

    assert draft is not None
    assert draft["modeled"] is True
    assert draft["template_key"] == "nr35_ponto_ancoragem"
    assert draft["family"] == "nr35_inspecao_ponto_ancoragem"
    assert draft["telemetry"]["modeled_strategy"] == "nr35_anchor_structured_model"
    assert draft["structured_data_candidate"]["schema_type"] == "laudo_output"
    assert draft["structured_data_candidate"]["family_key"] == "nr35_inspecao_ponto_ancoragem"
    assert draft["quality_gates"]["required_image_slots_complete"] is True
    assert draft["quality_gates"]["autonomy_ready"] is False
    assert draft["quality_gates"]["final_validation_mode"] == "mesa_required"
    assert any(
        item["item_codigo"] == "corrosao" and item["veredito_ia_normativo"] == "NC"
        for item in draft["items"]
    )
    assert any(
        item["item_codigo"] == "trinca" and item["veredito_ia_normativo"] == "C"
        for item in draft["items"]
    )
    assert draft["pre_laudo_outline"]["ready_for_finalization"] is True


def test_gate_nr35_anchor_expoe_slots_pendentes_quando_faltam_fotos(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr35_anchor(
        ambiente_critico,
        com_fotos=False,
        com_achado=True,
    )

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
    assert "nr35_anchor_image_slot_missing" in missing_codes


def test_finalizacao_nr35_anchor_permanece_em_mesa_mesmo_com_caso_completo(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr35_anchor(
        ambiente_critico,
        com_fotos=True,
        com_achado=False,
    )

    resposta = client.post(
        f"/app/api/laudo/{laudo_id}/finalizar",
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["review_mode_final"] == "mesa_required"
    assert "mesa" in corpo["message"].lower()
    assert corpo["estado"] == "aguardando"
    assert corpo["report_pack_draft"]["quality_gates"]["autonomy_ready"] is False
    assert corpo["report_pack_draft"]["quality_gates"]["final_validation_mode"] == (
        "mesa_required"
    )
    assert corpo["pre_laudo_summary"]["ready_for_finalization"] is True

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value
        assert laudo.report_pack_draft_json is not None
        assert laudo.report_pack_draft_json["family"] == "nr35_inspecao_ponto_ancoragem"
