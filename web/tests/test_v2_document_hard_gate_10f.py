from __future__ import annotations

import asyncio
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.chat.chat_stream_routes import rota_chat
from app.domains.chat.schemas import DadosChat
from app.shared.database import Laudo, MensagemLaudo, StatusRevisao, TemplateLaudo, TipoMensagem, Usuario
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.document import (
    build_canonical_document_facade,
    build_document_hard_gate_decision,
    build_document_soft_gate_route_context,
    build_document_soft_gate_trace,
    clear_document_hard_gate_metrics_for_tests,
    get_document_hard_gate_operational_summary,
)
from tests.regras_rotas_criticas_support import _criar_laudo, _salvar_pdf_temporario_teste


def _build_stream_finalize_trace() -> object:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=SimpleNamespace(id=17, empresa_id=33, nivel_acesso=1),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 144,
            "permite_reabrir": False,
            "laudo_card": {"id": 144, "status_revisao": StatusRevisao.RASCUNHO.value},
        },
    )
    facade = build_canonical_document_facade(
        banco=None,
        case_snapshot=snapshot,
        source_channel="web_app_chat",
        template_key="padrao",
        current_review_status=StatusRevisao.RASCUNHO.value,
        has_form_data=True,
        has_ai_draft=False,
    )
    return build_document_soft_gate_trace(
        case_snapshot=snapshot,
        document_facade=facade,
        route_context=build_document_soft_gate_route_context(
            route_name="rota_chat_report_finalize_stream",
            route_path="/app/api/chat",
            http_method="POST",
            source_channel="web_app_chat",
            operation_kind="report_finalize_stream",
            side_effect_free=False,
            legacy_pipeline_name="legacy_report_finalize_stream",
        ),
    )


def _preparar_laudo_finalizavel_stream(
    banco,
    *,
    empresa_id: int,
    usuario_id: int,
    tipo_template: str = "padrao",
) -> int:
    laudo_id = _criar_laudo(
        banco,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        status_revisao=StatusRevisao.RASCUNHO.value,
        tipo_template=tipo_template,
    )
    laudo = banco.get(Laudo, laudo_id)
    assert laudo is not None
    laudo.primeira_mensagem = "Inspeção inicial em equipamento crítico."
    banco.add_all(
        [
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="Foram coletadas evidências suficientes para o laudo.",
            ),
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.USER.value,
                conteudo="[imagem]",
            ),
            MensagemLaudo(
                laudo_id=laudo_id,
                remetente_id=usuario_id,
                tipo=TipoMensagem.IA.value,
                conteudo="Parecer preliminar com apoio documental.",
            ),
        ]
    )
    banco.commit()
    return laudo_id


def _criar_template_ativo_stream(
    banco,
    *,
    empresa_id: int,
    criado_por_id: int,
    codigo_template: str = "padrao",
) -> None:
    banco.add(
        TemplateLaudo(
            empresa_id=empresa_id,
            criado_por_id=criado_por_id,
            nome=f"Template {codigo_template} stream",
            codigo_template=codigo_template,
            versao=1,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            status_template="ativo",
            arquivo_pdf_base=_salvar_pdf_temporario_teste(f"stream_{codigo_template}"),
            mapeamento_campos_json={},
            documento_editor_json=None,
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
    )
    banco.commit()


def _summary_blocker(payload: dict, blocker_code: str) -> dict:
    for item in payload["by_blocker_code"]:
        if item["blocker_code"] == blocker_code:
            return item
    raise AssertionError(f"Blocker {blocker_code} não encontrado no summary.")


def _build_chat_request(laudo_id: int, csrf: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/app/api/chat",
            "headers": [(b"x-csrf-token", csrf.encode())],
            "query_string": b"",
            "session": {
                "csrf_token_inspetor": csrf,
                "laudo_ativo_id": int(laudo_id),
                "estado_relatorio": "relatorio_ativo",
            },
            "state": {},
            "client": ("testclient", 50120),
        }
    )


def test_hard_gate_report_finalize_stream_permanece_shadow_only_mesmo_com_enforce_flag(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", "33")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "report_finalize_stream")

    decision = build_document_hard_gate_decision(
        soft_gate_trace=_build_stream_finalize_trace(),
        remote_host="testclient",
    )

    assert decision.operation_kind == "report_finalize_stream"
    assert decision.mode == "shadow_only"
    assert decision.shadow_only is True
    assert decision.enforce_enabled is False
    assert decision.would_block is True
    assert decision.did_block is False
    assert decision.route_name == "rota_chat_report_finalize_stream"
    assert decision.route_path == "/app/api/chat"
    assert decision.source_channel == "web_app_chat"
    assert all(item.enforcement_scope == "shadow_only" for item in decision.blockers)


def test_hard_gate_report_finalize_stream_shadow_only_nao_bloqueia_finalizacao_via_sse(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()
    csrf = "csrf-report-finalize-stream-shadow"

    with SessionLocal() as banco:
        laudo_id = _preparar_laudo_finalizavel_stream(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            tipo_template="padrao",
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "report_finalize_stream")

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        resposta = asyncio.run(
            rota_chat(
                dados=DadosChat(
                    mensagem="COMANDO_SISTEMA FINALIZARLAUDOAGORA TIPO padrao",
                    historico=[],
                    laudo_id=laudo_id,
                ),
                request=_build_chat_request(laudo_id, csrf),
                usuario=usuario,
                banco=banco,
            )
        )

    assert resposta.status_code == 200
    assert resposta.media_type == "text/event-stream"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value

    summary = get_document_hard_gate_operational_summary()
    assert any(
        item["operation_kind"] == "report_finalize_stream"
        and item["evaluations"] >= 1
        and item["did_block"] == 0
        for item in summary["by_operation_kind"]
    )
    assert summary["totals"]["would_block"] >= 1
    assert summary["totals"]["did_block"] == 0
    assert summary["totals"]["shadow_only"] >= 1
    assert _summary_blocker(summary, "template_not_bound")["shadow_only"] >= 1

    recent_decision = summary["recent_results"][0]["decision"]
    assert recent_decision["operation_kind"] == "report_finalize_stream"
    assert recent_decision["route_name"] == "rota_chat_report_finalize_stream"
    assert recent_decision["route_path"] == "/app/api/chat"
    assert recent_decision["source_channel"] == "web_app_chat"
    assert recent_decision["did_block"] is False


def test_hard_gate_report_finalize_stream_com_template_ativo_reduz_blockers_sem_bloquear(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_hard_gate_metrics_for_tests()
    csrf = "csrf-report-finalize-stream-template-ok"

    with SessionLocal() as banco:
        _criar_template_ativo_stream(
            banco,
            empresa_id=ids["empresa_a"],
            criado_por_id=ids["inspetor_a"],
            codigo_template="padrao",
        )
        laudo_id = _preparar_laudo_finalizavel_stream(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            tipo_template="padrao",
        )

    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", str(ids["empresa_a"]))
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "report_finalize_stream")

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        resposta = asyncio.run(
            rota_chat(
                dados=DadosChat(
                    mensagem="COMANDO_SISTEMA FINALIZARLAUDOAGORA TIPO padrao",
                    historico=[],
                    laudo_id=laudo_id,
                ),
                request=_build_chat_request(laudo_id, csrf),
                usuario=usuario,
                banco=banco,
            )
        )

    assert resposta.status_code == 200
    assert resposta.media_type == "text/event-stream"

    with SessionLocal() as banco:
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        assert laudo.status_revisao == StatusRevisao.AGUARDANDO.value

    summary = get_document_hard_gate_operational_summary()
    assert summary["totals"]["did_block"] == 0

    recent_decision = summary["recent_results"][0]["decision"]
    blocker_codes = {item["blocker_code"] for item in recent_decision["blockers"]}
    assert recent_decision["operation_kind"] == "report_finalize_stream"
    assert recent_decision["route_name"] == "rota_chat_report_finalize_stream"
    assert "template_not_bound" not in blocker_codes
    assert "template_source_unknown" not in blocker_codes
