from __future__ import annotations

import asyncio
import json
import uuid

from starlette.requests import Request

from app.domains.chat.catalog_pdf_templates import ResolvedPdfTemplateRef
from app.domains.chat.chat_aux_routes import rota_pdf
from app.domains.chat.media_helpers import safe_remove_file
from app.domains.chat.schemas import DadosPDF
from app.domains.revisor.mesa_api import obter_pacote_mesa_laudo
from app.shared.database import Laudo, StatusRevisao, Usuario
from app.v2.document import (
    clear_document_soft_gate_metrics_for_tests,
    get_document_soft_gate_operational_summary,
)
from nucleo.gerador_laudos import GeradorLaudos


def _build_review_request(query_string: str = "") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/revisao/api/laudo/88/pacote",
            "headers": [],
            "query_string": query_string.encode(),
            "state": {},
            "client": ("testclient", 50000),
        }
    )


def _build_pdf_request(*, laudo_id: int | None) -> Request:
    headers = [(b"x-csrf-token", b"csrf-soft-gate")]
    session = {"csrf_token_inspetor": "csrf-soft-gate"}
    if laudo_id is not None:
        session["laudo_ativo_id"] = int(laudo_id)
        session["estado_relatorio"] = "relatorio_ativo"
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/app/api/gerar_pdf",
            "headers": headers,
            "query_string": b"",
            "session": session,
            "state": {},
            "client": ("testclient", 50001),
        }
    )


def test_pacote_mesa_com_soft_gate_preserva_payload_publico_e_expoe_request_state(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_soft_gate_metrics_for_tests()

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo = Laudo(
            empresa_id=revisor.empresa_id,
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
            parecer_ia="Rascunho IA",
        )
        banco.add(laudo)
        banco.flush()

        request_base = _build_review_request()
        monkeypatch.delenv("TARIEL_V2_PROVENANCE", raising=False)
        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_POLICY_ENGINE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_FACADE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_SOFT_GATE", raising=False)
        response_base = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_base,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_base = json.loads(response_base.body)

        request_soft = _build_review_request()
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_SOFT_GATE", "1")
        response_soft = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_soft,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_soft = json.loads(response_soft.body)

    assert payload_soft == payload_base
    assert request_soft.state.v2_document_soft_gate_decision["contract_name"] == "DocumentSoftGateDecisionV1"
    assert request_soft.state.v2_document_soft_gate_trace["route_context"]["operation_kind"] == "review_package_read"
    assert request_soft.state.v2_document_facade_summary["contract_name"] == "DocumentMaterializationReadinessV1"

    summary = get_document_soft_gate_operational_summary()
    assert summary["totals"]["decisions"] >= 1
    assert any(
        item["operation_kind"] == "review_package_read" and item["decisions"] >= 1
        for item in summary["by_operation_kind"]
    )


def test_rota_pdf_com_soft_gate_preserva_retorno_publico_e_registra_decisao(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    clear_document_soft_gate_metrics_for_tests()

    def _fake_gerar_pdf_inspecao(*, caminho_saida: str, **_kwargs) -> None:
        with open(caminho_saida, "wb") as arquivo_saida:
            arquivo_saida.write(b"%PDF-1.4\n%soft-gate\n")

    monkeypatch.setattr(
        GeradorLaudos,
        "gerar_pdf_inspecao",
        staticmethod(_fake_gerar_pdf_inspecao),
    )

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
        )
        banco.add(laudo)
        banco.flush()

        dados_pdf = DadosPDF(
            diagnostico="Diagnostico soft gate.",
            inspetor="Inspetor A",
            empresa="Empresa A",
            setor="geral",
            data="27/03/2026",
            laudo_id=laudo.id,
            tipo_template="padrao",
        )

        request_base = _build_pdf_request(laudo_id=laudo.id)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_SOFT_GATE", raising=False)
        response_base = asyncio.run(
            rota_pdf(
                request=request_base,
                dados=dados_pdf,
                usuario=usuario,
                banco=banco,
            )
        )

        request_soft = _build_pdf_request(laudo_id=laudo.id)
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_SOFT_GATE", "1")
        response_soft = asyncio.run(
            rota_pdf(
                request=request_soft,
                dados=dados_pdf,
                usuario=usuario,
                banco=banco,
            )
        )

    try:
        assert response_base.media_type == "application/pdf"
        assert response_soft.media_type == "application/pdf"
        assert "laudo_art_wf.pdf" in str(response_base.headers.get("content-disposition", "")).lower()
        assert "laudo_art_wf.pdf" in str(response_soft.headers.get("content-disposition", "")).lower()
        assert request_soft.state.v2_document_soft_gate_decision["contract_name"] == "DocumentSoftGateDecisionV1"
        assert request_soft.state.v2_document_soft_gate_trace["route_context"]["operation_kind"] == "preview_pdf"
        assert request_soft.state.v2_document_soft_gate_trace["route_context"]["legacy_pipeline_name"] in {
            "legacy_pdf_preview",
            "legacy_pdf_fallback",
        }

        summary = get_document_soft_gate_operational_summary()
        assert any(
            item["operation_kind"] == "preview_pdf" and item["decisions"] >= 1
            for item in summary["by_operation_kind"]
        )
    finally:
        safe_remove_file(str(getattr(response_base, "path", "") or ""))
        safe_remove_file(str(getattr(response_soft, "path", "") or ""))


def test_rota_pdf_preview_legado_repassa_mapeamento_resolvido(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    captured: dict[str, object] = {}

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo_a": "Valor legado", "campo_b": "Outro valor"},
        )
        banco.add(laudo)
        banco.flush()

        dados_pdf = DadosPDF(
            diagnostico="Diagnostico overlay legado.",
            inspetor="Inspetor A",
            empresa="Empresa A",
            setor="geral",
            data="27/03/2026",
            laudo_id=laudo.id,
            tipo_template="padrao",
        )

        def _fake_resolve_template(**_kwargs) -> ResolvedPdfTemplateRef:
            return ResolvedPdfTemplateRef(
                source_kind="tenant_template",
                family_key=None,
                template_id=901,
                codigo_template="padrao_legado",
                versao=4,
                modo_editor="legado_pdf",
                arquivo_pdf_base="/tmp/padrao_legado.pdf",
                documento_editor_json={},
                estilo_json={},
                assets_json=[],
                mapeamento_campos_json={
                    "pages": [
                        {
                            "page": 1,
                            "fields": [
                                {"key": "campo_a", "x": 12, "y": 18, "w": 48, "h": 5},
                                {"key": "campo_b", "x": 12, "y": 25, "w": 48, "h": 5},
                            ],
                        }
                    ]
                },
            )

        def _fake_preview(*, caminho_pdf_base: str, mapeamento_campos: dict[str, object], dados_formulario: dict[str, object]) -> bytes:
            captured["caminho_pdf_base"] = caminho_pdf_base
            captured["mapeamento_campos"] = mapeamento_campos
            captured["dados_formulario"] = dados_formulario
            return b"%PDF-1.4\n%legacy-mapped\n"

        monkeypatch.setattr("app.domains.chat.chat_aux_routes.resolve_pdf_template_for_laudo", _fake_resolve_template)
        monkeypatch.setattr("app.domains.chat.chat_aux_routes.gerar_preview_pdf_template", _fake_preview)

        response = asyncio.run(
            rota_pdf(
                request=_build_pdf_request(laudo_id=laudo.id),
                dados=dados_pdf,
                usuario=usuario,
                banco=banco,
            )
        )

    try:
        assert response.media_type == "application/pdf"
        with open(str(getattr(response, "path", "") or ""), "rb") as arquivo_saida:
            assert arquivo_saida.read().startswith(b"%PDF-1.4")
        assert captured["caminho_pdf_base"] == "/tmp/padrao_legado.pdf"
        assert captured["dados_formulario"] == {"campo_a": "Valor legado", "campo_b": "Outro valor"}
        mapping = captured["mapeamento_campos"]
        assert isinstance(mapping, dict)
        assert mapping["pages"][0]["fields"][0]["key"] == "campo_a"
        assert mapping["pages"][0]["fields"][1]["key"] == "campo_b"
    finally:
        safe_remove_file(str(getattr(response, "path", "") or ""))


def test_rota_pdf_promove_template_legado_fraco_para_preview_editor_rico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    captured: dict[str, object] = {}

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="nr13",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={
                "identificacao": {"identificacao_do_vaso": "Vaso vertical VP-204"},
                "conclusao": {"status": "ajuste", "conclusao_tecnica": "Equipamento apto com acompanhamento."},
            },
        )
        banco.add(laudo)
        banco.flush()

        dados_pdf = DadosPDF(
            diagnostico="Diagnostico overlay fraco.",
            inspetor="Inspetor A",
            empresa="Empresa A",
            setor="geral",
            data="27/03/2026",
            laudo_id=laudo.id,
            tipo_template="nr13",
        )

        def _fake_resolve_template(**_kwargs) -> ResolvedPdfTemplateRef:
            return ResolvedPdfTemplateRef(
                source_kind="tenant_template",
                family_key="nr13_inspecao_vaso_pressao",
                template_id=902,
                codigo_template="nr13_legado_fraco",
                versao=4,
                modo_editor="legado_pdf",
                arquivo_pdf_base="/tmp/nr13_legado_fraco.pdf",
                documento_editor_json={},
                estilo_json={},
                assets_json=[],
                mapeamento_campos_json={},
            )

        async def _fake_render_editor_rico(**kwargs) -> bytes:
            captured["documento_editor_json"] = kwargs["documento_editor_json"]
            captured["estilo_json"] = kwargs["estilo_json"]
            captured["dados_formulario"] = kwargs["dados_formulario"]
            return b"%PDF-1.4\n%rich-promoted\n"

        def _legacy_preview_should_not_run(**_kwargs) -> bytes:
            raise AssertionError("overlay legado nao deveria ser usado")

        monkeypatch.setattr("app.domains.chat.chat_aux_routes.resolve_pdf_template_for_laudo", _fake_resolve_template)
        monkeypatch.setattr("app.domains.chat.chat.gerar_pdf_editor_rico_bytes", _fake_render_editor_rico)
        monkeypatch.setattr("app.domains.chat.chat_aux_routes.gerar_preview_pdf_template", _legacy_preview_should_not_run)
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_SOFT_GATE", "1")

        request = _build_pdf_request(laudo_id=laudo.id)
        response = asyncio.run(
            rota_pdf(
                request=request,
                dados=dados_pdf,
                usuario=usuario,
                banco=banco,
            )
        )

    try:
        assert response.media_type == "application/pdf"
        with open(str(getattr(response, "path", "") or ""), "rb") as arquivo_saida:
            assert arquivo_saida.read().startswith(b"%PDF-1.4")
        serialized_document = json.dumps(captured["documento_editor_json"], ensure_ascii=False)
        assert "Resumo Executivo" in serialized_document
        assert "Conclusao Tecnica" in serialized_document
        style = captured["estilo_json"]
        assert isinstance(style, dict)
        assert "Tariel" in str(style.get("cabecalho_texto") or "")
        assert "Revisao" in str(style.get("rodape_texto") or "")
        assert request.state.v2_document_soft_gate_trace["route_context"]["legacy_pipeline_name"] == "editor_rico_preview"
        assert request.state.v2_document_soft_gate_trace["route_context"]["legacy_compatibility_state"] == (
            "legacy_template_promoted_to_editor_rico"
        )
    finally:
        safe_remove_file(str(getattr(response, "path", "") or ""))
