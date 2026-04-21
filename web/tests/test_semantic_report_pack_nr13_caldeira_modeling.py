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


def _nr13_caldeira_guided_checklist() -> list[dict[str, str]]:
    return [
        {
            "id": "identificacao",
            "title": "Identificacao da caldeira",
            "prompt": "registre local, tag e referencia principal",
            "evidence_hint": "placa e objeto principal",
        },
        {
            "id": "inspecao_visual",
            "title": "Inspecao visual",
            "prompt": "registre condicao geral, fuligem e isolamento",
            "evidence_hint": "achados principais da vistoria",
        },
        {
            "id": "dispositivos_controles",
            "title": "Dispositivos e controles",
            "prompt": "registre painel, valvula, manometro e indicador de nivel",
            "evidence_hint": "instrumentacao e comandos",
        },
        {
            "id": "registros_fotograficos",
            "title": "Registros fotograficos",
            "prompt": "anexe placa, painel e achado principal",
            "evidence_hint": "placa, painel e nao conformidade",
        },
        {
            "id": "conclusao",
            "title": "Conclusao",
            "prompt": "registre conclusao tecnica e recomendacao",
            "evidence_hint": "status final e encaminhamento",
        },
    ]


def _payload_nr13_caldeira(*, com_achado: bool) -> dict[str, str]:
    return {
        "local_inspecao": "Casa de caldeiras, unidade norte",
        "painel_comandos": "Painel frontal e comandos principais registrados durante a inspecao.",
        "dispositivos_de_seguranca": "Valvula de seguranca e instrumentos principais observados sem bloqueio aparente.",
        "indicador_nivel": "Indicador de nivel visivel na frente operacional.",
        "pontos_fuligem": (
            "Marca leve de fuligem em trecho aparente da exaustao."
            if com_achado
            else "Sem vazamento ou fuligem aparente no trecho da exaustao."
        ),
        "isolamento_termico": (
            "Desgaste localizado do revestimento externo do isolamento termico."
            if com_achado
            else "Isolamento termico integro, sem desgaste relevante."
        ),
        "queimador": "Frente do sistema termico registrada sem improvisacao aparente.",
        "certificado": "Nao apresentado",
        "relatorio_anterior": "DOC_022 - relatorio_anterior_2025.pdf",
        "prontuario": "DOC_021 - prontuario_caldeira_cal01.pdf",
        "placa_identificacao": "IMG_101 - placa parcialmente legivel com confirmacao no prontuario.",
        "ha_nao_conformidades": "Sim" if com_achado else "Nao",
        "observacoes": (
            "Programar recomposicao do revestimento externo do isolamento termico."
            if com_achado
            else "Manter a rotina de monitoramento visual da caldeira."
        ),
    }


def _criar_laudo_nr13_caldeira(
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
            setor_industrial="NR13 Caldeira",
            primeira_mensagem="Inspecao NR13 da caldeira CAL-01.",
            tipo_template="nr13",
            catalog_family_key="nr13_inspecao_caldeira",
            catalog_family_label="NR13 Caldeira",
            catalog_variant_key="premium_campo",
            catalog_variant_label="Premium Campo",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
            dados_formulario=_payload_nr13_caldeira(com_achado=com_achado),
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
            "Caldeira CAL-01 na casa de caldeiras da unidade norte, com placa parcialmente legivel e prontuario vinculado."
        )
        msg_visual = add_user_message(
            "Foi registrada a condicao geral da caldeira, incluindo fuligem na exaustao e revestimento do isolamento termico."
            if com_achado
            else "Condicao geral registrada sem fuligem aparente e com isolamento termico preservado."
        )
        msg_dispositivos = add_user_message(
            "Painel frontal, dispositivos de seguranca e indicador de nivel foram registrados durante a inspecao."
        )
        msg_conclusao = add_user_message(
            "Caso consolidado para revisao de engenharia com prontuario, painel, instrumentos e recomendacao tecnica."
        )

        refs = [
            {
                "message_id": int(msg_identificacao.id),
                "step_id": "identificacao",
                "step_title": "Identificacao da caldeira",
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
                "step_id": "dispositivos_controles",
                "step_title": "Dispositivos e controles",
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
                ("Placa de identificacao", "Painel e comandos", "Achado principal"),
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
                        setor_industrial="NR13 Caldeira",
                        resumo=f"Foto {indice} da caldeira",
                        descricao_contexto=f"Evidencia fotografica {indice} da caldeira CAL-01.",
                        correcao_inspetor="Registro fotografico confirmado pelo inspetor.",
                        imagem_url=f"/static/test/nr13_caldeira_{indice}.png",
                        imagem_nome_original=f"nr13_caldeira_{indice}.png",
                        imagem_mime_type="image/png",
                        imagem_sha256=imagem_sha256,
                        caminho_arquivo=f"/tmp/nr13_caldeira_{indice}.png",
                    )
                )

        banco.add(
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer tecnico preliminar da caldeira consolidado pela IA.",
            )
        )
        laudo.guided_inspection_draft_json = {
            "template_key": "nr13",
            "template_label": "NR13 Caldeira",
            "started_at": "2026-04-18T14:00:00.000Z",
            "current_step_index": 4,
            "completed_step_ids": [item["id"] for item in _nr13_caldeira_guided_checklist()],
            "checklist": _nr13_caldeira_guided_checklist(),
            "evidence_bundle_kind": "case_thread",
            "evidence_refs": refs,
            "mesa_handoff": None,
        }
        banco.commit()
        banco.refresh(laudo)
        return int(laudo.id)


def test_report_pack_nr13_caldeira_modela_familia_com_candidato_canonico(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    laudo_id = _criar_laudo_nr13_caldeira(
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
    assert draft["template_key"] == "nr13"
    assert draft["family"] == "nr13_inspecao_caldeira"
    assert draft["telemetry"]["modeled_strategy"] == "nr13_caldeira_structured_model"
    assert draft["structured_data_candidate"]["schema_type"] == "laudo_output"
    assert draft["structured_data_candidate"]["family_key"] == "nr13_inspecao_caldeira"
    assert draft["quality_gates"]["required_image_slots_complete"] is True
    assert draft["quality_gates"]["autonomy_ready"] is False
    assert draft["quality_gates"]["final_validation_mode"] == "mesa_required"
    assert any(
        item["item_codigo"] == "pontos_de_vazamento_ou_fuligem"
        and item["veredito_ia_normativo"] == "NC"
        for item in draft["items"]
    )
    assert any(
        item["item_codigo"] == "prontuario"
        and item["veredito_ia_normativo"] == "C"
        for item in draft["items"]
    )
    assert draft["pre_laudo_outline"]["ready_for_finalization"] is True


def test_gate_nr13_caldeira_expoe_slots_pendentes_quando_faltam_fotos(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr13_caldeira(
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
    assert "nr13_caldeira_image_slot_missing" in missing_codes


def test_finalizacao_nr13_caldeira_permanece_em_mesa_mesmo_com_caso_completo(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr13_caldeira(
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
        assert laudo.report_pack_draft_json["family"] == "nr13_inspecao_caldeira"
