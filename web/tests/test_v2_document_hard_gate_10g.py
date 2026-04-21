from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi.responses import StreamingResponse
from starlette.requests import Request

from app.domains.admin.routes import api_document_hard_gate_durable_summary
from app.domains.chat import chat_stream_routes
from app.domains.chat.chat_stream_routes import rota_chat
from app.domains.chat.schemas import DadosChat
from app.shared.database import Laudo, MensagemLaudo, NivelAcesso, StatusRevisao, TemplateLaudo, TipoMensagem, Usuario
from app.v2.document import clear_document_hard_gate_metrics_for_tests, get_document_hard_gate_operational_summary
from app.v2.document.hard_gate_evidence import (
    clear_document_hard_gate_durable_evidence_for_tests,
    get_document_hard_gate_durable_summary,
)
from tests.regras_rotas_criticas_support import _criar_laudo, _salvar_pdf_temporario_teste


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


def _build_chat_request(laudo_id: int, csrf: str, *, remote_host: str = "testclient") -> Request:
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
            "client": (remote_host, 50120),
        }
    )


def _build_admin_request(remote_host: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/admin/api/document-hard-gate/durable-summary",
            "headers": [],
            "query_string": b"",
            "state": {},
            "client": (remote_host, 50005),
        }
    )


async def _read_stream(response: StreamingResponse) -> str:
    partes: list[str] = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            partes.append(chunk.decode())
        else:
            partes.append(str(chunk))
    return "".join(partes)


def test_rota_chat_delega_finalizacao_stream_para_servico_isolado(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = "csrf-report-finalize-stream-isolado"

    with SessionLocal() as banco:
        laudo_id = _preparar_laudo_finalizavel_stream(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
        )

    chamadas: list[dict[str, object]] = []

    async def _stub_processar_finalizacao_stream_documental(**kwargs):
        chamadas.append(kwargs)

        async def _fake_stream():
            yield "data: {\"texto\":\"ok\"}\n\n"
            yield "data: [FIM]\n\n"

        return StreamingResponse(_fake_stream(), media_type="text/event-stream")

    monkeypatch.setattr(
        chat_stream_routes,
        "processar_finalizacao_stream_documental",
        _stub_processar_finalizacao_stream_documental,
    )

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
    assert len(chamadas) == 1
    assert chamadas[0]["tipo_template_finalizacao"] == "padrao"
    assert chamadas[0]["laudo"].id == laudo_id
    assert chamadas[0]["headers"]["Cache-Control"] == "no-cache, no-store, must-revalidate"


def test_report_finalize_stream_shadow_persiste_evidencia_duravel_e_expoe_summary_local_only(
    ambiente_critico,
    monkeypatch,
    tmp_path,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    csrf = "csrf-report-finalize-stream-durable"
    evidence_root = tmp_path / "durable_evidence"
    clear_document_hard_gate_metrics_for_tests()
    clear_document_hard_gate_durable_evidence_for_tests(root=evidence_root)

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
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR", str(evidence_root))

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        admin = banco.get(Usuario, ids["admin_a"])
        assert usuario is not None
        assert admin is not None
        request = _build_chat_request(laudo_id, csrf)
        resposta = asyncio.run(
            rota_chat(
                dados=DadosChat(
                    mensagem="COMANDO_SISTEMA FINALIZARLAUDOAGORA TIPO padrao",
                    historico=[],
                    laudo_id=laudo_id,
                ),
                request=request,
                usuario=usuario,
                banco=banco,
            )
        )
        sse_body = asyncio.run(_read_stream(resposta))
        local_summary_response = asyncio.run(
            api_document_hard_gate_durable_summary(
                request=_build_admin_request("testclient"),
                usuario=admin,
            )
        )
        remote_summary_response = asyncio.run(
            api_document_hard_gate_durable_summary(
                request=_build_admin_request("10.10.10.10"),
                usuario=Usuario(
                    id=ids["admin_a"],
                    empresa_id=ids["empresa_a"],
                    nivel_acesso=NivelAcesso.DIRETORIA.value,
                    email="admin@empresa-a.test",
                ),
            )
        )

    assert resposta.status_code == 200
    assert resposta.media_type == "text/event-stream"
    assert "data: [FIM]" in sse_body

    observation = request.state.v2_report_finalize_stream_shadow_observation
    artifact_path = Path(request.state.v2_report_finalize_stream_shadow_artifact_path)
    assert observation["enabled"] is True
    assert observation["hard_gate_observed"] is True
    assert observation["response_media_type"] == "text/event-stream"
    assert observation["did_block"] is False
    assert observation["artifact_path"] == str(artifact_path)
    assert artifact_path.exists()

    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    blocker_codes = {item["blocker_code"] for item in artifact_payload["blockers"]}
    assert artifact_payload["operation_kind"] == "report_finalize_stream"
    assert artifact_payload["tenant_id"] == str(ids["empresa_a"])
    assert artifact_payload["legacy_laudo_id"] == laudo_id
    assert artifact_payload["route_context"]["route_name"] == "rota_chat_report_finalize_stream"
    assert artifact_payload["route_context"]["route_path"] == "/app/api/chat"
    assert artifact_payload["route_context"]["source_channel"] == "web_app_chat"
    assert artifact_payload["response"]["sse_preserved"] is True
    assert artifact_payload["functional_outcome"] == "stream_finalize_completed_shadow_only"
    assert artifact_payload["did_block"] is False
    assert artifact_payload["mode"] == "shadow_only"
    assert artifact_payload["would_block"] is False
    assert "template_not_bound" not in blocker_codes
    assert "template_source_unknown" not in blocker_codes

    summary = get_document_hard_gate_operational_summary()
    assert summary["totals"]["did_block"] == 0
    assert summary["totals"]["shadow_only"] >= 1
    assert any(
        item["operation_kind"] == "report_finalize_stream" and item["evaluations"] >= 1
        for item in summary["by_operation_kind"]
    )

    durable_summary = get_document_hard_gate_durable_summary(root=evidence_root)
    assert durable_summary["totals"]["evaluations"] == 1
    assert durable_summary["totals"]["did_block"] == 0
    assert durable_summary["totals"]["shadow_only"] == 1
    assert durable_summary["by_operation_kind"][0]["operation_kind"] == "report_finalize_stream"
    assert durable_summary["recent_entries"][0]["artifact_path"] == str(artifact_path)

    assert remote_summary_response.status_code == 403
    assert local_summary_response.status_code == 200
    local_payload = json.loads(local_summary_response.body)
    assert local_payload["totals"]["evaluations"] == 1
    assert local_payload["recent_entries"][0]["artifact_path"] == str(artifact_path)
