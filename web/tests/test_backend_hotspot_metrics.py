from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.domains.admin.services import registrar_novo_cliente
from app.domains.chat import chat_stream_routes
from app.domains.chat.schemas import DadosChat
from app.shared.backend_hotspot_metrics import (
    BACKEND_HOTSPOT_CONTRACT_NAME,
    BACKEND_HOTSPOT_CONTRACT_VERSION,
    clear_backend_hotspot_metrics_for_tests,
    get_backend_hotspot_operational_summary,
)
from app.shared.database import Empresa, Laudo, StatusRevisao, Usuario
from tests.regras_rotas_criticas_support import (
    _criar_laudo,
    _login_admin,
    _login_app_inspetor,
    _login_cliente,
    _login_revisor,
    _pdf_base_bytes_teste,
)


def _build_hotspot_request(path: str, *, method: str = "POST") -> Request:
    request = Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "client": ("testclient", 50000),
        }
    )
    request.state.request_id = "hotspot-request-id"
    request.state.correlation_id = "hotspot-correlation-id"
    request.state.trace_id = "hotspot-trace-id"
    return request


def test_backend_hotspot_metrics_agregam_onboarding_bootstrap_e_bloqueio_governado_mesa(
    ambiente_critico,
) -> None:
    clear_backend_hotspot_metrics_for_tests()
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    suffix = uuid.uuid4().int % 10**12
    with SessionLocal() as banco:
        empresa, senha_temporaria, _notice = registrar_novo_cliente(
            banco,
            nome=f"Empresa Observability {suffix}",
            cnpj=f"77{suffix:012d}",
            email_admin=f"admin.obs.{suffix}@empresa.test",
            plano="Ilimitado",
            provisionar_inspetor_inicial=True,
            inspetor_nome=f"Inspetor {suffix}",
            inspetor_email=f"inspetor.obs.{suffix}@empresa.test",
            provisionar_revisor_inicial=True,
            revisor_nome=f"Mesa {suffix}",
            revisor_email=f"mesa.obs.{suffix}@empresa.test",
            revisor_crea="123456/GO",
        )
        assert int(empresa.id) > 0
        assert senha_temporaria

    _login_cliente(client, "cliente@empresa-a.test")
    resposta_bootstrap = client.get("/cliente/api/bootstrap?surface=chat")
    assert resposta_bootstrap.status_code == 200

    with SessionLocal() as banco:
        empresa_a = banco.get(Empresa, ids["empresa_a"])
        assert empresa_a is not None
        empresa_a.admin_cliente_policy_json = {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "tenant_capability_reviewer_decision_enabled": False,
        }
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        banco.commit()

    _login_revisor(client, "revisor@empresa-a.test")
    resposta_export_pdf = client.get(f"/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf")
    assert resposta_export_pdf.status_code == 403

    payload = get_backend_hotspot_operational_summary()

    assert payload["totals"]["observations"] >= 3
    assert payload["totals"]["success"] >= 2
    assert payload["totals"]["blocked"] >= 1
    assert payload["totals"]["governed"] >= 1
    assert any(
        row["endpoint"] == "admin_tenant_onboarding" and row["success"] >= 1
        for row in payload["by_endpoint"]
    )
    assert any(
        row["endpoint"] == "cliente_bootstrap" and row["success"] >= 1
        for row in payload["by_endpoint"]
    )
    assert any(
        row["endpoint"] == "mesa_export_package_pdf" and row["blocked"] >= 1
        for row in payload["by_endpoint"]
    )
    assert any(
        row["surface"] == "mesa" and row["blocked"] >= 1
        for row in payload["by_surface"]
    )


def test_chat_route_and_admin_summary_endpoint_expoem_backend_hotspot_observability(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_backend_hotspot_metrics_for_tests()
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setattr(chat_stream_routes, "exigir_csrf", lambda _request: None)
    monkeypatch.setattr(
        chat_stream_routes,
        "prepare_chat_stream_route",
        lambda **_kwargs: (SimpleNamespace(), None),
    )
    monkeypatch.setattr(
        chat_stream_routes,
        "persist_chat_user_message",
        lambda **_kwargs: SimpleNamespace(
            eh_whisper_para_mesa=False,
            eh_comando_finalizar=False,
            texto_exibicao="Mensagem de teste",
            mensagem_usuario_id=901,
            laudo=SimpleNamespace(id=321),
            historico_dict=[],
            dados_imagem_validos=None,
            texto_documento="",
            tipo_template_finalizacao=None,
            headers={},
            laudo_id_atual=321,
            empresa_id_atual=ids["empresa_a"],
            usuario_id_atual=ids["inspetor_a"],
            usuario_nome_atual="Inspetor A",
            card_laudo_payload=None,
        ),
    )
    monkeypatch.setattr(chat_stream_routes, "obter_cliente_ia_ativo", lambda: object())
    monkeypatch.setattr(
        chat_stream_routes,
        "build_ai_stream_response",
        lambda **_kwargs: JSONResponse({"ok": True}),
    )

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        resposta = asyncio.run(
            chat_stream_routes.rota_chat(
                dados=DadosChat(mensagem="teste observability", historico=[]),
                request=_build_hotspot_request("/app/api/chat"),
                usuario=usuario,
                banco=banco,
            )
        )

    assert resposta.status_code == 200
    assert client.get("/admin/api/backend-hotspots/summary").status_code == 401

    _login_admin(client, "admin@empresa-a.test")
    resposta_summary = client.get("/admin/api/backend-hotspots/summary")
    assert resposta_summary.status_code == 200

    payload = resposta_summary.json()
    assert payload["contract_name"] == BACKEND_HOTSPOT_CONTRACT_NAME
    assert payload["contract_version"] == BACKEND_HOTSPOT_CONTRACT_VERSION
    assert payload["observability_enabled"] is True
    assert any(
        row["endpoint"] == "chat_stream" and row["success"] >= 1
        for row in payload["by_endpoint"]
    )
    assert any(
        item["endpoint"] == "chat_stream" and item["outcome"] == "ai_stream"
        for item in payload["recent_events"]
    )


def test_backend_hotspot_metrics_cobrem_paineis_e_operacoes_documentais_pesadas(
    ambiente_critico,
) -> None:
    clear_backend_hotspot_metrics_for_tests()
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    _login_admin(client, "admin@empresa-a.test")
    resposta_admin = client.get("/admin/painel")
    assert resposta_admin.status_code == 200

    csrf_revisor = _login_revisor(client, "revisor@empresa-a.test")
    resposta_revisao = client.get("/revisao/painel")
    assert resposta_revisao.status_code == 200

    csrf_inspetor = _login_app_inspetor(client, "inspetor@empresa-a.test")
    with SessionLocal() as banco:
        laudo_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        laudo = banco.get(Laudo, laudo_id)
        assert laudo is not None
        laudo.primeira_mensagem = "Inspecao eletrica em painel principal."
        laudo.parecer_ia = "Resumo do laudo para emissao de preview."
        laudo.dados_formulario = {
            "informacoes_gerais": {
                "responsavel_pela_inspecao": "Gabriel Santos",
                "data_inspecao": "15/04/2026",
                "local_inspecao": "Planta Norte",
            },
            "resumo_executivo": "Preview do inspetor para observabilidade.",
        }
        banco.commit()

    resposta_pdf = client.post(
        "/app/api/gerar_pdf",
        headers={"X-CSRF-Token": csrf_inspetor},
        json={
            "diagnostico": "Inspecao eletrica concluida.",
            "inspetor": "Gabriel Santos",
            "empresa": "Empresa A",
            "setor": "geral",
            "data": "15/04/2026",
            "laudo_id": laudo_id,
            "tipo_template": "padrao",
        },
    )
    assert resposta_pdf.status_code == 200
    assert "application/pdf" in (resposta_pdf.headers.get("content-type", "").lower())

    csrf_revisor = _login_revisor(client, "revisor@empresa-a.test")
    resposta_upload = client.post(
        "/revisao/api/templates-laudo/upload",
        headers={"X-CSRF-Token": csrf_revisor},
        data={
            "nome": "Template observability preview",
            "codigo_template": "cbmgo_cmar",
            "versao": "31",
        },
        files={
            "arquivo_base": ("observability_base.pdf", _pdf_base_bytes_teste(), "application/pdf"),
        },
    )
    assert resposta_upload.status_code == 201
    template_id = int(resposta_upload.json()["id"])

    resposta_preview = client.post(
        f"/revisao/api/templates-laudo/{template_id}/preview",
        headers={"X-CSRF-Token": csrf_revisor},
        json={
            "laudo_id": laudo_id,
            "dados_formulario": {
                "informacoes_gerais": {
                    "responsavel_pela_inspecao": "Gabriel Santos",
                    "data_inspecao": "15/04/2026",
                    "local_inspecao": "Planta Norte",
                },
                "resumo_executivo": "Preview da mesa para observabilidade.",
            },
        },
    )
    assert resposta_preview.status_code == 200
    assert "application/pdf" in (resposta_preview.headers.get("content-type", "").lower())

    _login_admin(client, "admin@empresa-a.test")
    resposta_summary = client.get("/admin/api/backend-hotspots/summary")
    assert resposta_summary.status_code == 200
    payload = resposta_summary.json()
    endpoints = {row["endpoint"]: row for row in payload["by_endpoint"]}
    assert endpoints["admin_dashboard_html"]["success"] >= 1
    assert endpoints["review_panel_html"]["success"] >= 1
    assert endpoints["inspector_pdf_generation"]["success"] >= 1
    assert endpoints["review_template_preview"]["success"] >= 1

    resposta_document_summary = client.get("/admin/api/document-operations/summary")
    assert resposta_document_summary.status_code == 200
    payload_document_summary = resposta_document_summary.json()
    assert payload_document_summary["backend_hotspots"]["contract_name"] == BACKEND_HOTSPOT_CONTRACT_NAME
    assert {
        row["endpoint"] for row in payload_document_summary["backend_hotspots"]["by_endpoint"]
    } >= {
        "admin_dashboard_html",
        "review_panel_html",
        "inspector_pdf_generation",
        "review_template_preview",
    }
