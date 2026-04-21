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


def _nr10_prontuario_guided_checklist() -> list[dict[str, str]]:
    return [
        {
            "id": "identificacao",
            "title": "Identificacao do prontuario",
            "prompt": "registre objeto, codigo interno e referencia principal",
            "evidence_hint": "indice e referencia principal",
        },
        {
            "id": "documentacao_principal",
            "title": "Documentacao principal",
            "prompt": "registre prontuario, diagrama, inventario, PIE e ART",
            "evidence_hint": "documentos base do prontuario eletrico",
        },
        {
            "id": "registros_fotograficos",
            "title": "Registros fotograficos",
            "prompt": "anexe referencia principal e documento base",
            "evidence_hint": "referencia do caso e documento ancora",
        },
        {
            "id": "conclusao",
            "title": "Conclusao",
            "prompt": "registre consolidacao tecnica e pendencias",
            "evidence_hint": "status final e ressalvas",
        },
    ]


def _payload_nr10_prontuario(*, com_ressalva: bool) -> dict[str, str]:
    return {
        "localizacao": "Area de prensas - painel QGBT-07",
        "objeto_principal": "Prontuario eletrico do painel QGBT-07",
        "codigo_interno": "PRT-QGBT-07",
        "numero_prontuario": "PRT-QGBT-07",
        "referencia_principal": "DOC_301 - indice_prontuario_qgbt07.pdf",
        "modo_execucao": "analise documental",
        "metodo_aplicado": "Consolidacao documental do prontuario NR10 com validacao do indice, diagramas e inventario de circuitos.",
        "status_documentacao": "Documentacao principal consolidada com pendencia na ART da ultima revisao.",
        "prontuario": "DOC_301 - indice_prontuario_qgbt07.pdf",
        "inventario_instalacoes": "DOC_302 - inventario_circuitos_qgbt07.xlsx",
        "diagrama_unifilar": "DOC_303 - diagrama_qgbt07_rev04.pdf",
        "pie": "DOC_304 - pie_prensas_rev02.pdf",
        "procedimento_trabalho": "DOC_305 - procedimento_intervencao_qgbt07.pdf",
        "memorial_descritivo": "DOC_306 - memorial_qgbt07.pdf",
        "art_numero": "ART 2026-00411",
        "evidencia_principal": "DOC_303 - diagrama_qgbt07_rev04.pdf",
        "descricao_pontos_atencao": (
            "Pendencia de anexar a ART de atualizacao do diagrama unifilar revisado."
            if com_ressalva
            else "Sem pendencias documentais relevantes para o fechamento do prontuario."
        ),
        "conclusao": {"status": "Liberado com ressalvas" if com_ressalva else "Liberado"},
        "observacoes": (
            "Anexar a ART da revisao do diagrama, atualizar o indice e reemitir o prontuario."
            if com_ressalva
            else "Prontuario consolidado com rastreabilidade documental suficiente."
        ),
    }


def _criar_laudo_nr10_prontuario(
    ambiente_critico,
    *,
    quantidade_fotos: int,
    com_ressalva: bool,
) -> int:
    SessionLocal = ambiente_critico["SessionLocal"]
    imagem_data_uri = _imagem_png_data_uri_teste()
    imagem_sha256 = hashlib.sha256(imagem_data_uri.encode("utf-8")).hexdigest()

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR10 Prontuario",
            primeira_mensagem="Consolidacao do prontuario eletrico do painel QGBT-07 da area de prensas.",
            tipo_template="nr10",
            catalog_family_key="nr10_prontuario_instalacoes_eletricas",
            catalog_family_label="NR10 Prontuario Instalacoes Eletricas",
            catalog_variant_key="prime_documental",
            catalog_variant_label="Prime documental",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
            dados_formulario=_payload_nr10_prontuario(com_ressalva=com_ressalva),
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
            "Prontuario do painel QGBT-07 identificado com indice principal e referencia documental vinculada."
        )
        msg_documentacao = add_user_message(
            "Prontuario, diagrama unifilar, inventario de circuitos, PIE e ART foram consolidados no pacote documental."
        )
        msg_conclusao = add_user_message(
            "Prontuario eletrico consolidado para revisao documental da Mesa com rastreabilidade suficiente."
        )

        refs = [
            {
                "message_id": int(msg_identificacao.id),
                "step_id": "identificacao",
                "step_title": "Identificacao do prontuario",
                "captured_at": msg_identificacao.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_documentacao.id),
                "step_id": "documentacao_principal",
                "step_title": "Documentacao principal",
                "captured_at": msg_documentacao.criado_em.isoformat(),
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

        for indice in range(max(0, int(quantidade_fotos))):
            mensagem_foto = add_user_message("[imagem]")
            refs.append(
                {
                    "message_id": int(mensagem_foto.id),
                    "step_id": "registros_fotograficos",
                    "step_title": (
                        "Referencia principal" if indice == 0 else "Documento base"
                    ),
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
                    setor_industrial="NR10 Prontuario",
                    resumo=f"Foto {indice + 1} do prontuario NR10",
                    descricao_contexto=f"Evidencia fotografica {indice + 1} do prontuario QGBT-07.",
                    correcao_inspetor="Registro fotografico confirmado pelo inspetor.",
                    imagem_url=f"/static/test/nr10_prontuario_{indice + 1}.png",
                    imagem_nome_original=f"nr10_prontuario_{indice + 1}.png",
                    imagem_mime_type="image/png",
                    imagem_sha256=imagem_sha256,
                    caminho_arquivo=f"/tmp/nr10_prontuario_{indice + 1}.png",
                )
            )

        banco.add(
            MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer tecnico preliminar do prontuario NR10 consolidado pela IA.",
            )
        )
        laudo.guided_inspection_draft_json = {
            "template_key": "pie",
            "template_label": "NR10 Prontuario",
            "started_at": "2026-04-18T16:40:00.000Z",
            "current_step_index": 3,
            "completed_step_ids": [item["id"] for item in _nr10_prontuario_guided_checklist()],
            "checklist": _nr10_prontuario_guided_checklist(),
            "evidence_bundle_kind": "case_thread",
            "evidence_refs": refs,
            "mesa_handoff": None,
        }
        banco.commit()
        banco.refresh(laudo)
        return int(laudo.id)


def test_report_pack_nr10_prontuario_modela_familia_com_candidato_canonico(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    laudo_id = _criar_laudo_nr10_prontuario(
        ambiente_critico,
        quantidade_fotos=2,
        com_ressalva=True,
    )

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        draft = build_report_pack_draft_for_laudo(banco=banco, laudo=laudo)

    assert draft is not None
    assert draft["modeled"] is True
    assert draft["template_key"] == "pie"
    assert draft["family"] == "nr10_prontuario_instalacoes_eletricas"
    assert draft["telemetry"]["modeled_strategy"] == "nr10_prontuario_structured_model"
    assert draft["structured_data_candidate"]["schema_type"] == "laudo_output"
    assert draft["structured_data_candidate"]["family_key"] == "nr10_prontuario_instalacoes_eletricas"
    assert draft["quality_gates"]["required_image_slots_complete"] is True
    assert draft["quality_gates"]["autonomy_ready"] is False
    assert draft["quality_gates"]["final_validation_mode"] == "mesa_required"
    assert any(
        item["item_codigo"] == "diagrama_unifilar"
        and item["veredito_ia_normativo"] == "C"
        for item in draft["items"]
    )
    assert any(
        item["item_codigo"] == "pie"
        and item["veredito_ia_normativo"] == "C"
        for item in draft["items"]
    )
    assert draft["pre_laudo_outline"]["ready_for_finalization"] is True


def test_gate_nr10_prontuario_expoe_slot_pendente_quando_falta_foto(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr10_prontuario(
        ambiente_critico,
        quantidade_fotos=1,
        com_ressalva=True,
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
    assert len(pendentes) == 1
    missing_codes = {
        item["code"]
        for item in corpo["report_pack_draft"]["quality_gates"]["missing_evidence"]
    }
    assert "nr10_prontuario_image_slot_missing" in missing_codes


def test_finalizacao_nr10_prontuario_permanece_em_mesa_mesmo_com_caso_completo(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_nr10_prontuario(
        ambiente_critico,
        quantidade_fotos=2,
        com_ressalva=True,
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
        assert laudo.report_pack_draft_json["family"] == "nr10_prontuario_instalacoes_eletricas"
