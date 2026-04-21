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


def _nr13_vaso_guided_checklist() -> list[dict[str, str]]:
    return [
        {
            "id": "identificacao",
            "title": "Identificacao do vaso",
            "prompt": "registre o ativo, placa e prontuario principal",
            "evidence_hint": "placa e referencia principal",
        },
        {
            "id": "inspecao_visual",
            "title": "Inspecao visual",
            "prompt": "registre corrosao, vazamentos e condicao geral",
            "evidence_hint": "achados visuais principais",
        },
        {
            "id": "dispositivos_acessorios",
            "title": "Dispositivos e acessorios",
            "prompt": "registre dispositivos de seguranca e manometro",
            "evidence_hint": "valvula, manometro e conjunto de seguranca",
        },
        {
            "id": "registros_fotograficos",
            "title": "Registros fotograficos",
            "prompt": "anexe placa, dispositivo de seguranca e achado principal",
            "evidence_hint": "placa, dispositivo e detalhe do achado",
        },
        {
            "id": "conclusao",
            "title": "Conclusao",
            "prompt": "registre conclusao tecnica e encaminhamento",
            "evidence_hint": "status final e recomendacao",
        },
    ]


def _payload_nr13_vaso_pressao(*, com_corrosao: bool) -> dict[str, str]:
    return {
        "local_inspecao": "Casa de utilidades, linha de ar comprimido, bloco B",
        "placa_identificacao": "IMG_201 - placa parcialmente legivel com confirmacao no prontuario vinculado.",
        "prontuario": "DOC_201 - prontuario_vp204.pdf",
        "relatorio_anterior": "DOC_202 - relatorio_anterior_vp204.pdf",
        "dispositivos_de_seguranca": "Valvula de seguranca e instrumentos associados registrados durante a inspecao.",
        "manometro": "Manometro com visor legivel e leitura local acessivel.",
        "valvula_seguranca": "Valvula de seguranca visivelmente instalada e sem interferencias aparentes.",
        "corrosao": (
            "Ponto inicial de corrosao superficial proximo ao suporte inferior."
            if com_corrosao
            else "Sem corrosao aparente nas superficies visiveis do vaso."
        ),
        "vazamentos": (
            "Nao foram observados sinais aparentes de vazamento no momento da inspecao."
        ),
        "ha_nao_conformidades": "Sim" if com_corrosao else "Nao",
        "observacoes": (
            "Programar tratamento localizado da corrosao superficial e nova avaliacao."
            if com_corrosao
            else "Manter monitoramento periodico do vaso de pressao."
        ),
    }


def _criar_laudo_nr13_vaso_pressao(
    ambiente_critico,
    *,
    com_fotos: bool,
    com_corrosao: bool,
) -> int:
    SessionLocal = ambiente_critico["SessionLocal"]
    imagem_data_uri = _imagem_png_data_uri_teste()
    imagem_sha256 = hashlib.sha256(imagem_data_uri.encode("utf-8")).hexdigest()

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR13 Vaso de Pressao",
            primeira_mensagem="Inspecao NR13 do vaso VP-204.",
            tipo_template="nr13",
            catalog_family_key="nr13_inspecao_vaso_pressao",
            catalog_family_label="NR13 Vaso de Pressao",
            catalog_variant_key="premium_campo",
            catalog_variant_label="Premium Campo",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
            dados_formulario=_payload_nr13_vaso_pressao(com_corrosao=com_corrosao),
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
            "Vaso VP-204 identificado em campo com placa parcialmente legivel e prontuario associado."
        )
        msg_visual = add_user_message(
            "Foi registrado ponto inicial de corrosao superficial no suporte inferior."
            if com_corrosao
            else "Nao foram observados pontos de corrosao nem vazamentos aparentes no vaso."
        )
        msg_dispositivos = add_user_message(
            "Valvula de seguranca, manometro e acessorios principais foram registrados durante a inspecao."
        )
        msg_conclusao = add_user_message(
            "Caso consolidado para revisao de engenharia com prontuario e evidencias do vaso de pressao."
        )

        refs = [
            {
                "message_id": int(msg_identificacao.id),
                "step_id": "identificacao",
                "step_title": "Identificacao do vaso",
                "captured_at": msg_identificacao.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_visual.id),
                "step_id": "inspecao_visual",
                "step_title": "Inspecao visual",
                "captured_at": msg_visual.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_dispositivos.id),
                "step_id": "dispositivos_acessorios",
                "step_title": "Dispositivos e acessorios",
                "captured_at": msg_dispositivos.criado_em.isoformat(),
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
                ("Placa de identificacao", "Dispositivos de seguranca", "Achado principal"),
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
                        setor_industrial="NR13 Vaso de Pressao",
                        resumo=f"Foto {indice} do vaso de pressao",
                        descricao_contexto=f"Evidencia fotografica {indice} do vaso VP-204.",
                        correcao_inspetor="Registro fotografico confirmado pelo inspetor.",
                        imagem_url=f"/static/test/nr13_vaso_pressao_{indice}.png",
                        imagem_nome_original=f"nr13_vaso_pressao_{indice}.png",
                        imagem_mime_type="image/png",
                        imagem_sha256=imagem_sha256,
                        caminho_arquivo=f"/tmp/nr13_vaso_pressao_{indice}.png",
                    )
                )

        banco.add(
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer tecnico preliminar do vaso de pressao consolidado pela IA.",
            )
        )
        laudo.guided_inspection_draft_json = {
            "template_key": "nr13",
            "template_label": "NR13 Vaso de Pressao",
            "started_at": "2026-04-18T15:30:00.000Z",
            "current_step_index": 4,
            "completed_step_ids": [item["id"] for item in _nr13_vaso_guided_checklist()],
            "checklist": _nr13_vaso_guided_checklist(),
            "evidence_bundle_kind": "case_thread",
            "evidence_refs": refs,
            "mesa_handoff": None,
        }
        banco.commit()
        banco.refresh(laudo)
        return int(laudo.id)


def test_report_pack_nr13_vaso_pressao_modela_familia_com_candidato_canonico(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    laudo_id = _criar_laudo_nr13_vaso_pressao(
        ambiente_critico,
        com_fotos=True,
        com_corrosao=True,
    )

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        draft = build_report_pack_draft_for_laudo(banco=banco, laudo=laudo)

    assert draft is not None
    assert draft["modeled"] is True
    assert draft["template_key"] == "nr13"
    assert draft["family"] == "nr13_inspecao_vaso_pressao"
    assert draft["telemetry"]["modeled_strategy"] == "nr13_vaso_pressao_structured_model"
    assert draft["structured_data_candidate"]["schema_type"] == "laudo_output"
    assert draft["structured_data_candidate"]["family_key"] == "nr13_inspecao_vaso_pressao"
    assert draft["quality_gates"]["required_image_slots_complete"] is True
    assert draft["quality_gates"]["autonomy_ready"] is False
    assert draft["quality_gates"]["final_validation_mode"] == "mesa_required"
    assert any(
        item["item_codigo"] == "pontos_de_corrosao"
        and item["veredito_ia_normativo"] == "NC"
        for item in draft["items"]
    )
    assert any(
        item["item_codigo"] == "prontuario"
        and item["veredito_ia_normativo"] == "C"
        for item in draft["items"]
    )
    assert draft["pre_laudo_outline"]["ready_for_finalization"] is True


def test_gate_nr13_vaso_pressao_expoe_slots_pendentes_quando_faltam_fotos(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr13_vaso_pressao(
        ambiente_critico,
        com_fotos=False,
        com_corrosao=True,
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
    assert "nr13_vaso_pressao_image_slot_missing" in missing_codes


def test_finalizacao_nr13_vaso_pressao_permanece_em_mesa_mesmo_com_caso_completo(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr13_vaso_pressao(
        ambiente_critico,
        com_fotos=True,
        com_corrosao=False,
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
        assert laudo.report_pack_draft_json["family"] == "nr13_inspecao_vaso_pressao"
