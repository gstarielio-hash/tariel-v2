from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.chat.auth_mobile_support import montar_contexto_portal_inspetor
from app.domains.chat.auth_mobile_routes import api_listar_laudos_mobile_inspetor
import app.shared.official_issue_package as official_issue_package
from app.shared.database import (
    EmissaoOficialLaudo,
    Laudo,
    NivelAcesso,
    StatusRevisao,
    TemplateLaudo,
    Usuario,
)
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.adapters.android_case_view import adapt_inspector_case_view_projection_to_android_case
from app.v2.contracts.projections import build_inspector_case_view_projection


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def _build_mobile_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/app/api/mobile/laudos",
            "headers": [],
            "query_string": b"",
            "state": {},
        }
    )


def test_shape_do_adapter_android_e_payload_limitado_ao_inspetor() -> None:
    legacy_card = {
        "id": 88,
        "titulo": "Caldeira B-202",
        "preview": "Primeira mensagem",
        "pinado": False,
        "data_iso": "2026-03-25",
        "data_br": "25/03/2026",
        "hora_br": "10:30",
        "tipo_template": "padrao",
        "status_revisao": StatusRevisao.AGUARDANDO.value,
        "status_card": "aguardando",
        "status_card_label": "Aguardando",
        "permite_edicao": False,
        "permite_reabrir": False,
        "possui_historico": True,
    }
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "permite_reabrir": False,
            "tem_interacao": True,
            "laudo_card": legacy_card,
        },
    )
    projection = build_inspector_case_view_projection(
        case_snapshot=snapshot,
        actor_id=17,
        actor_role="inspetor",
        source_channel="android_api",
        allows_edit=False,
        has_interaction=True,
        report_types={"padrao": "Inspeção Geral (Padrão)"},
        laudo_card=legacy_card,
    )

    adapted = adapt_inspector_case_view_projection_to_android_case(
        projection=projection,
        expected_legacy_payload=legacy_card,
    )

    assert adapted.contract_name == "AndroidCaseViewAdapterResultV1"
    assert adapted.compatibility.contract_name == "AndroidCaseCompatibilitySummaryV1"
    assert adapted.compatibility.compatible is True
    assert set(adapted.payload.keys()) == {
        "id",
        "titulo",
        "preview",
        "pinado",
        "data_iso",
        "data_br",
        "hora_br",
        "tipo_template",
        "status_revisao",
        "status_card",
        "status_card_label",
        "permite_edicao",
        "permite_reabrir",
        "possui_historico",
    }
    assert "policy_summary" not in adapted.payload
    assert "origin_summary" not in adapted.payload
    assert "document_readiness" not in adapted.payload


def test_adapter_android_reconstroi_card_publico_legado() -> None:
    legacy_card = {
        "id": 41,
        "titulo": "Ponte Rolante PR-12",
        "preview": "Inspeção iniciada",
        "pinado": True,
        "data_iso": "2026-03-24",
        "data_br": "24/03/2026",
        "hora_br": "15:45",
        "tipo_template": "nr12maquinas",
        "status_revisao": StatusRevisao.RASCUNHO.value,
        "status_card": "aberto",
        "status_card_label": "Aberto",
        "permite_edicao": True,
        "permite_reabrir": False,
        "possui_historico": True,
    }
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 41,
            "permite_reabrir": False,
            "tem_interacao": True,
            "laudo_card": legacy_card,
        },
    )
    projection = build_inspector_case_view_projection(
        case_snapshot=snapshot,
        actor_id=17,
        actor_role="inspetor",
        source_channel="android_api",
        allows_edit=True,
        has_interaction=True,
        report_types={"nr12maquinas": "Ponte Rolante"},
        laudo_card=legacy_card,
    )

    adapted = adapt_inspector_case_view_projection_to_android_case(
        projection=projection,
        expected_legacy_payload=legacy_card,
    )

    assert adapted.compatibility.compatible is True
    assert adapted.compatibility.divergences == []
    assert adapted.payload == legacy_card


def test_mobile_laudos_com_android_adapter_preserva_payload_publico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
            primeira_mensagem="Primeira evidencia coletada",
        )
        banco.add(laudo)
        banco.flush()

        request_base = _build_mobile_request()
        monkeypatch.delenv("TARIEL_V2_ANDROID_CASE_ADAPTER", raising=False)
        monkeypatch.delenv("TARIEL_V2_PROVENANCE", raising=False)
        monkeypatch.delenv("TARIEL_V2_POLICY_ENGINE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_FACADE", raising=False)
        monkeypatch.delenv("TARIEL_V2_DOCUMENT_SHADOW", raising=False)
        response_base = asyncio.run(
            api_listar_laudos_mobile_inspetor(
                request=request_base,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_base = json.loads(response_base.body)

        request_adapter = _build_mobile_request()
        monkeypatch.setenv("TARIEL_V2_ANDROID_CASE_ADAPTER", "1")
        response_adapter = asyncio.run(
            api_listar_laudos_mobile_inspetor(
                request=request_adapter,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_adapter = json.loads(response_adapter.body)

    assert payload_adapter == payload_base
    assert request_adapter.state.v2_android_case_adapter_summary["total"] >= 1
    assert request_adapter.state.v2_android_case_adapter_summary["compatible"] >= 1
    assert request_adapter.state.v2_android_case_adapter_results[0]["android_adapter"]["contract_name"] == "AndroidCaseViewAdapterResultV1"
    assert request_adapter.state.v2_android_case_adapter_results[0]["projection"]["contract_name"] == "InspectorCaseViewProjectionV1"


def test_mobile_laudos_adapter_mantem_visibilidade_do_papel_inspetor(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        template = TemplateLaudo(
            empresa_id=usuario.empresa_id,
            criado_por_id=usuario.id,
            nome="Template Mobile",
            codigo_template="padrao",
            versao=2,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="editor_rico",
            status_template="ativo",
            arquivo_pdf_base="/tmp/nao_usado_mobile.pdf",
            mapeamento_campos_json={},
            documento_editor_json={"content": []},
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Android",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
            parecer_ia="Rascunho IA",
            primeira_mensagem="Coleta inicial mobile",
        )
        banco.add(template)
        banco.add(laudo)
        banco.flush()

        request_adapter = _build_mobile_request()
        monkeypatch.setenv("TARIEL_V2_ANDROID_CASE_ADAPTER", "1")
        monkeypatch.setenv("TARIEL_V2_PROVENANCE", "1")
        monkeypatch.setenv("TARIEL_V2_POLICY_ENGINE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_FACADE", "1")
        monkeypatch.setenv("TARIEL_V2_DOCUMENT_SHADOW", "1")
        response_adapter = asyncio.run(
            api_listar_laudos_mobile_inspetor(
                request=request_adapter,
                usuario=usuario,
                banco=banco,
            )
        )
        payload_adapter = json.loads(response_adapter.body)

    assert payload_adapter["ok"] is True
    item = payload_adapter["itens"][0]
    assert "policy_summary" not in item
    assert "origin_summary" not in item
    assert "document_readiness" not in item
    resultado = request_adapter.state.v2_android_case_adapter_results[0]
    assert resultado["projection"]["projection_audience"] == "inspetor"
    assert resultado["android_adapter"]["compatibility"]["visibility_scope"] == "inspetor_mobile"
    assert resultado["document_facade"]["legacy_pipeline_shadow"]["contract_name"] == "LegacyDocumentPipelineShadowResultV1"


def test_mobile_laudos_expoe_alerta_de_reemissao_do_pdf_oficial(
    ambiente_critico,
    monkeypatch,
    tmp_path,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    monkeypatch.setattr(official_issue_package, "WEB_ROOT", tmp_path)

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR35 Linha de Vida",
            tipo_template="nr35",
            status_revisao=StatusRevisao.APROVADO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"campo": "valor"},
            primeira_mensagem="PDF emitido divergente",
            nome_arquivo_pdf="nr35_emitido.pdf",
        )
        banco.add(laudo)
        banco.flush()

        frozen_path = tmp_path / "frozen" / "nr35_emitido.pdf"
        frozen_path.parent.mkdir(parents=True, exist_ok=True)
        frozen_path.write_bytes(b"pdf-frozen")

        current_path = (
            tmp_path
            / "storage"
            / "laudos_emitidos"
            / f"empresa_{usuario.empresa_id}"
            / f"laudo_{laudo.id}"
            / "v0004"
            / "nr35_emitido.pdf"
        )
        current_path.parent.mkdir(parents=True, exist_ok=True)
        current_path.write_bytes(b"pdf-current")

        emissao = EmissaoOficialLaudo(
            laudo_id=laudo.id,
            tenant_id=usuario.empresa_id,
            issue_number="EO-NR35-1",
            issue_state="issued",
            issued_at=datetime.now(timezone.utc),
            package_sha256="a" * 64,
            package_fingerprint_sha256="b" * 64,
            issue_context_json={
                "primary_pdf_artifact": {
                    "storage_path": str(frozen_path),
                    "storage_file_name": "nr35_emitido.pdf",
                    "storage_version": "v0003",
                    "storage_version_number": 3,
                    "source": "issue_context",
                }
            },
        )
        banco.add(emissao)
        banco.commit()

        request = _build_mobile_request()
        response = asyncio.run(
            api_listar_laudos_mobile_inspetor(
                request=request,
                usuario=usuario,
                banco=banco,
            )
        )
        payload = json.loads(response.body)

    assert payload["ok"] is True
    summary = payload["itens"][0]["official_issue_summary"]
    assert summary["label"] == "Reemissão recomendada"
    assert summary["detail"] == "PDF emitido divergente · Emitido v0003 · Atual v0004"
    assert summary["primary_pdf_diverged"] is True
    assert summary["issue_number"] == "EO-NR35-1"


def test_portal_inspetor_expoe_resumo_de_reemissao_no_contexto_ssr(
    ambiente_critico,
    monkeypatch,
    tmp_path,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    monkeypatch.setattr(official_issue_package, "WEB_ROOT", tmp_path)

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR12 Ponte Rolante",
            tipo_template="nr12maquinas",
            status_revisao=StatusRevisao.APROVADO.value,
            codigo_hash=uuid.uuid4().hex,
            dados_formulario={"cliente": "Metal Forte", "unidade": "Pátio A"},
            primeira_mensagem="Drift do PDF oficial no portal",
            nome_arquivo_pdf="nr12_emitido.pdf",
        )
        banco.add(laudo)
        banco.flush()

        frozen_path = tmp_path / "frozen" / "nr12_emitido.pdf"
        frozen_path.parent.mkdir(parents=True, exist_ok=True)
        frozen_path.write_bytes(b"pdf-frozen-portal")

        current_path = (
            tmp_path
            / "storage"
            / "laudos_emitidos"
            / f"empresa_{usuario.empresa_id}"
            / f"laudo_{laudo.id}"
            / "v0004"
            / "nr12_emitido.pdf"
        )
        current_path.parent.mkdir(parents=True, exist_ok=True)
        current_path.write_bytes(b"pdf-current-portal")

        emissao = EmissaoOficialLaudo(
            laudo_id=laudo.id,
            tenant_id=usuario.empresa_id,
            issue_number="EO-NR12-PORTAL-1",
            issue_state="issued",
            issued_at=datetime.now(timezone.utc),
            package_sha256="c" * 64,
            package_fingerprint_sha256="d" * 64,
            issue_context_json={
                "primary_pdf_artifact": {
                    "storage_path": str(frozen_path),
                    "storage_file_name": "nr12_emitido.pdf",
                    "storage_version": "v0003",
                    "storage_version_number": 3,
                    "source": "issue_context",
                }
            },
        )
        banco.add(emissao)
        banco.commit()

        contexto = montar_contexto_portal_inspetor(
            banco,
            usuario=usuario,
            laudos_recentes=[laudo],
        )

    governance_summary = contexto["portal_governance_summary"]
    assert governance_summary["visible"] is True
    assert governance_summary["reissue_recommended_count"] == 1
    assert governance_summary["label"] == "1 caso com reemissão recomendada"
    assert governance_summary["detail"] == "PDF oficial divergente detectado no ponto de entrada do inspetor."

    item = contexto["laudos_portal_cards"][0]
    official_issue_summary = item["official_issue_summary"]
    assert official_issue_summary["label"] == "Reemissão recomendada"
    assert official_issue_summary["detail"] == "PDF emitido divergente · Emitido v0003 · Atual v0004"
    assert official_issue_summary["primary_pdf_diverged"] is True
