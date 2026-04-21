from __future__ import annotations

import asyncio

import main

from app.domains.admin.routes import api_document_soft_gate_summary
from app.shared.database import NivelAcesso, StatusRevisao, TemplateLaudo, Usuario
from app.shared.security import obter_usuario_html
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.contracts.provenance import ProvenanceEntry, build_content_origin_summary
from app.v2.document import (
    clear_document_soft_gate_metrics_for_tests,
    build_canonical_document_facade,
    build_document_soft_gate_route_context,
    build_document_soft_gate_trace,
    record_document_soft_gate_trace,
)
from starlette.requests import Request


def _build_admin_request(remote_host: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/admin/api/document-soft-gate/summary",
            "headers": [],
            "query_string": b"",
            "state": {},
            "client": (remote_host, 50002),
        }
    )


def test_admin_summary_do_soft_gate_permanece_local_only(ambiente_critico, monkeypatch) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_soft_gate_metrics_for_tests()
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_SOFT_GATE", "1")

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_a"])
        inspetor = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        assert inspetor is not None

        banco.add(
            TemplateLaudo(
                empresa_id=inspetor.empresa_id,
                criado_por_id=inspetor.id,
                nome="Template Padrao",
                codigo_template="padrao",
                versao=1,
                ativo=True,
                base_recomendada_fixa=False,
                modo_editor="legado_pdf",
                status_template="ativo",
                arquivo_pdf_base="/tmp/template_soft_gate_summary.pdf",
                mapeamento_campos_json={},
                documento_editor_json=None,
                assets_json=[],
                estilo_json={},
                observacoes=None,
            )
        )
        banco.flush()

        provenance = build_content_origin_summary(
            entries=[
                ProvenanceEntry(
                    origin_kind="human",
                    source="package.message_summary",
                    confidence="confirmed",
                    signal_count=2,
                )
            ]
        )
        snapshot = build_technical_case_status_snapshot_for_user(
            usuario=inspetor,
            legacy_payload={
                "estado": "aprovado",
                "laudo_id": 123,
                "permite_reabrir": False,
                "laudo_card": {"id": 123, "status_revisao": StatusRevisao.APROVADO.value},
            },
            content_origin_summary=provenance,
        )
        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=snapshot,
            source_channel="review_api",
            template_key="padrao",
            provenance_summary=provenance,
            current_review_status=StatusRevisao.APROVADO.value,
            has_form_data=True,
            has_ai_draft=False,
        )

    record_document_soft_gate_trace(
        build_document_soft_gate_trace(
            case_snapshot=snapshot,
            document_facade=facade,
            route_context=build_document_soft_gate_route_context(
                route_name="obter_pacote_mesa_laudo",
                route_path="/revisao/api/laudo/123/pacote",
                http_method="GET",
                source_channel="review_api",
                operation_kind="review_package_read",
                side_effect_free=True,
                legacy_pipeline_name="legacy_review_package",
            ),
        )
    )

    resposta_remote = asyncio.run(
        api_document_soft_gate_summary(
            request=_build_admin_request("10.10.10.10"),
            usuario=Usuario(
                id=ids["admin_a"],
                empresa_id=ids["empresa_a"],
                nivel_acesso=NivelAcesso.DIRETORIA.value,
                email="admin@empresa-a.test",
            ),
        )
    )
    assert resposta_remote.status_code == 403

    client = ambiente_critico["client"]
    assert client.get("/admin/api/document-soft-gate/summary").status_code == 401

    main.app.dependency_overrides[obter_usuario_html] = lambda: Usuario(
        id=ids["admin_a"],
        empresa_id=ids["empresa_a"],
        nivel_acesso=NivelAcesso.DIRETORIA.value,
        email="admin@empresa-a.test",
    )
    try:
        resposta = client.get("/admin/api/document-soft-gate/summary")
    finally:
        main.app.dependency_overrides.pop(obter_usuario_html, None)

    assert resposta.status_code == 200
    payload = resposta.json()
    assert payload["contract_name"] == "DocumentSoftGateSummaryV1"
    assert payload["feature_flag"] == "TARIEL_V2_DOCUMENT_SOFT_GATE"
    assert payload["totals"]["decisions"] >= 1
    assert any(
        item["operation_kind"] == "review_package_read" and item["decisions"] >= 1
        for item in payload["by_operation_kind"]
    )
