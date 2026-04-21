from __future__ import annotations

import hashlib
import uuid

from app.domains.chat.templates_ai import MAPA_VERIFICACOES_CBMGO
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


def _cbmgo_guided_checklist() -> list[dict[str, str]]:
    return [
        {
            "id": "informacoes_gerais",
            "title": "Informacoes gerais da vistoria",
            "prompt": "registre responsavel, local, tipologia e data",
            "evidence_hint": "responsavel, local, tipologia e data",
        },
        {
            "id": "seguranca_estrutural",
            "title": "Seguranca estrutural",
            "prompt": "consolide achados estruturais e localizacao",
            "evidence_hint": "fissuras, corrosao e localizacao resumida",
        },
        {
            "id": "cmar",
            "title": "CMAR",
            "prompt": "resuma materiais empregados e divergencias",
            "evidence_hint": "piso, paredes, teto e cobertura",
        },
        {
            "id": "verificacao_documental",
            "title": "Verificacao documental",
            "prompt": "relacione plano, documentos e acessos",
            "evidence_hint": "documentos conferidos e lacunas",
        },
        {
            "id": "registros_fotograficos",
            "title": "Registros fotograficos",
            "prompt": "anexe vista geral, achado e apoio documental",
            "evidence_hint": "fachada, achado e documento",
        },
        {
            "id": "conclusao",
            "title": "Conclusao",
            "prompt": "resuma conclusao e prontidao do formulario",
            "evidence_hint": "resumo executivo e recomendacoes",
        },
    ]


def _cbmgo_dados_formulario_validos() -> dict[str, object]:
    payload: dict[str, object] = {
        "informacoes_gerais": {
            "responsavel_pela_inspecao": "Gabriel Santos",
            "data_inspecao": "2026-04-06",
            "local_inspecao": "Unidade 1 - Goiania/GO",
            "tipologia": "Industrial",
            "possui_cercon": "Sim",
            "responsavel_empresa_acompanhamento": "Carlos Lima",
        },
        "seguranca_estrutural": {},
        "cmar": {},
        "trrf_observacoes": "TRRF em linha com memorial e vistoria visual.",
        "verificacao_documental": {},
        "recomendacoes_gerais": {
            "outros": "Sem outras recomendacoes alem da manutencao rotineira.",
        },
        "coleta_assinaturas": {
            "responsavel_pela_inspecao": "Gabriel Santos",
            "responsavel_empresa_acompanhamento": "Carlos Lima",
        },
        "resumo_executivo": "Vistoria CBMGO sem nao conformidades objetivas e com evidencias suficientes para liberacao automatica controlada.",
    }
    for section_key, section_map in MAPA_VERIFICACOES_CBMGO.items():
        target = payload.setdefault(section_key, {})
        assert isinstance(target, dict)
        for item_key in section_map:
            target[item_key] = {
                "condicao": "C",
                "localizacao": "Setor principal",
                "observacao": "Sem nao conformidade visual relevante.",
            }
    return payload


def _criar_laudo_cbmgo_guiado(
    ambiente_critico,
) -> int:
    SessionLocal = ambiente_critico["SessionLocal"]
    imagem_data_uri = _imagem_png_data_uri_teste()
    imagem_sha256 = hashlib.sha256(imagem_data_uri.encode("utf-8")).hexdigest()

    with SessionLocal() as banco:
        usuario = banco.query(Usuario).filter(Usuario.email == "inspetor@empresa-a.test").one()
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="CBMGO Vistoria Bombeiro",
            primeira_mensagem="Inspecao CBMGO com coleta guiada e evidencias completas.",
            tipo_template="cbmgo",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            modo_resposta="detalhado",
            is_deep_research=False,
            entry_mode_preference="evidence_first",
            entry_mode_effective="evidence_first",
            entry_mode_reason="user_preference",
            dados_formulario=_cbmgo_dados_formulario_validos(),
        )
        banco.add(laudo)
        banco.flush()

        def add_inspector_message(texto: str) -> MensagemLaudo:
            mensagem = MensagemLaudo(
                laudo_id=int(laudo.id),
                remetente_id=usuario.id,
                tipo=TipoMensagem.HUMANO_INSP.value,
                conteudo=texto,
            )
            banco.add(mensagem)
            banco.flush()
            return mensagem

        msg_info = add_inspector_message(
            "Responsavel: Gabriel Santos; Local: Unidade 1 - Goiania/GO; Tipologia: Industrial; Data: 2026-04-06."
        )
        msg_estrutural = add_inspector_message(
            "Sem fissuras, corrosao, deformacoes ou recalques aparentes nos elementos inspecionados."
        )
        msg_cmar = add_inspector_message(
            "Piso, paredes, teto e cobertura compativeis com o memorial. Sem divergencias observadas."
        )
        msg_documental = add_inspector_message(
            "Plano de manutencao disponivel, coerente e com documentos pertinentes acessiveis."
        )
        msg_conclusao = add_inspector_message(
            "Conclusao: vistoria sem nao conformidades objetivas, com formulario estruturado consistente."
        )

        refs = [
            {
                "message_id": int(msg_info.id),
                "step_id": "informacoes_gerais",
                "step_title": "Informacoes gerais da vistoria",
                "captured_at": msg_info.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_estrutural.id),
                "step_id": "seguranca_estrutural",
                "step_title": "Seguranca estrutural",
                "captured_at": msg_estrutural.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_cmar.id),
                "step_id": "cmar",
                "step_title": "CMAR",
                "captured_at": msg_cmar.criado_em.isoformat(),
                "evidence_kind": "chat_message",
                "attachment_kind": "none",
            },
            {
                "message_id": int(msg_documental.id),
                "step_id": "verificacao_documental",
                "step_title": "Verificacao documental",
                "captured_at": msg_documental.criado_em.isoformat(),
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

        for indice, titulo in enumerate(
            ("Vista geral", "Achado estrutural", "Documento de apoio"),
            start=1,
        ):
            mensagem_foto = add_inspector_message("[imagem]")
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
                    setor_industrial="CBMGO Vistoria Bombeiro",
                    resumo=f"Foto {indice} da vistoria CBMGO",
                    descricao_contexto=f"Evidencia fotografica {indice} do caso CBMGO.",
                    correcao_inspetor="Registro fotografico confirmado pelo inspetor.",
                    imagem_url=f"/static/test/cbmgo_{indice}.png",
                    imagem_nome_original=f"cbmgo_{indice}.png",
                    imagem_mime_type="image/png",
                    imagem_sha256=imagem_sha256,
                    caminho_arquivo=f"/tmp/cbmgo_{indice}.png",
                )
            )

        laudo.guided_inspection_draft_json = {
            "template_key": "cbmgo",
            "template_label": "CBM-GO Vistoria Bombeiro",
            "started_at": "2026-04-06T23:50:00.000Z",
            "current_step_index": 5,
            "completed_step_ids": [item["id"] for item in _cbmgo_guided_checklist()],
            "checklist": _cbmgo_guided_checklist(),
            "evidence_bundle_kind": "case_thread",
            "evidence_refs": refs,
            "mesa_handoff": None,
        }
        banco.commit()
        banco.refresh(laudo)
        return int(laudo.id)


def test_finalizacao_cbmgo_mobile_autonomous_aprova_direto_sem_parecer_previo_da_ia(
    ambiente_critico,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    csrf = _login_app_inspetor(client, "inspetor@empresa-a.test")
    laudo_id = _criar_laudo_cbmgo_guiado(ambiente_critico)

    gate = client.get(
        f"/app/api/laudo/{laudo_id}/gate-qualidade",
        headers={"X-CSRF-Token": csrf},
    )
    assert gate.status_code == 200
    assert gate.json()["review_mode_sugerido"] == "mobile_autonomous"

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
    assert corpo["report_pack_draft"]["template_key"] == "cbmgo"
    assert corpo["report_pack_draft"]["quality_gates"]["autonomy_ready"] is True

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.APROVADO.value
        assert laudo.dados_formulario is not None
        assert (
            laudo.dados_formulario["seguranca_estrutural"]["item_01_fissuras_trincas"]["condicao"]
            == "C"
        )
