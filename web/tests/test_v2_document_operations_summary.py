from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import main

from app.domains.admin.document_operations_summary import (
    build_document_operations_operational_summary,
)
from app.core.perf_support import registrar_operacao, resetar_perf
from app.core.settings import get_settings
from app.domains.admin.routes import api_document_operations_summary
from app.shared.backend_hotspot_metrics import clear_backend_hotspot_metrics_for_tests
from app.shared.database import Laudo, NivelAcesso, StatusRevisao, Usuario
from app.shared.security import obter_usuario_html
from app.v2.report_pack_rollout_metrics import (
    clear_report_pack_rollout_metrics_for_tests,
    record_report_pack_gate_observation,
)
from starlette.requests import Request
from tests.regras_rotas_criticas_support import _criar_laudo


def _build_admin_request(remote_host: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/admin/api/document-operations/summary",
            "headers": [],
            "query_string": b"",
            "state": {},
            "client": (remote_host, 50006),
        }
    )


def test_admin_summary_document_operations_permanece_local_only_e_agrega_perf(
    ambiente_critico,
    monkeypatch,
) -> None:
    client = ambiente_critico["client"]
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setenv("AMBIENTE", "dev")
    monkeypatch.setenv("PERF_MODE", "1")
    monkeypatch.setenv("TARIEL_V2_REPORT_PACK_ROLLOUT_OBSERVABILITY", "1")
    get_settings.cache_clear()
    resetar_perf()
    clear_backend_hotspot_metrics_for_tests()
    clear_report_pack_rollout_metrics_for_tests()

    try:
        registrar_operacao(
            "ocr",
            "ocr_extract_pdf",
            duration_ms=82.5,
            detail={"pages": 3},
        )
        registrar_operacao(
            "pdf",
            "document_render_final",
            duration_ms=145.2,
            detail={"laudo_id": 123},
        )
        report_pack_case = type("ReportPackCase", (), {})()
        report_pack_case.id = 321
        report_pack_case.empresa_id = ids["empresa_a"]
        report_pack_case.tipo_template = "nr35_linha_vida"
        report_pack_case.entry_mode_preference = "chat_first"
        report_pack_case.entry_mode_effective = "evidence_first"
        report_pack_case.dados_formulario = {
            "componentes_inspecionados": {
                "fixacao_dos_pontos": {"condicao": "NC"},
            }
        }
        report_pack_draft = {
            "template_key": "nr35_linha_vida",
            "family": "nr35_periodica_linha_vida",
            "structured_data_candidate": {
                "componentes_inspecionados": {
                    "fixacao_dos_pontos": {"condicao": "C"},
                }
            },
            "quality_gates": {
                "missing_evidence": [{"code": "nr35_image_slot_missing"}],
                "autonomy_ready": False,
                "final_validation_mode": "mesa_required",
                "max_conflict_score": 82,
            },
            "telemetry": {
                "entry_mode_preference": "chat_first",
                "entry_mode_effective": "evidence_first",
            },
        }
        record_report_pack_gate_observation(
            laudo=report_pack_case,
            report_pack_draft=report_pack_draft,
            approved=False,
            review_mode_sugerido="mesa_required",
        )

        with SessionLocal() as banco:
            resposta_remote = asyncio.run(
                api_document_operations_summary(
                    request=_build_admin_request("10.10.10.10"),
                    banco=banco,
                    usuario=Usuario(
                        id=ids["admin_a"],
                        empresa_id=ids["empresa_a"],
                        nivel_acesso=NivelAcesso.DIRETORIA.value,
                        email="admin@empresa-a.test",
                    ),
                )
            )
            assert resposta_remote.status_code == 403

        assert client.get("/admin/api/document-operations/summary").status_code == 401

        main.app.dependency_overrides[obter_usuario_html] = lambda: Usuario(
            id=ids["admin_a"],
            empresa_id=ids["empresa_a"],
            nivel_acesso=NivelAcesso.DIRETORIA.value,
            email="admin@empresa-a.test",
        )
        try:
            resposta = client.get("/admin/api/document-operations/summary")
        finally:
            main.app.dependency_overrides.pop(obter_usuario_html, None)

        assert resposta.status_code == 200
        payload = resposta.json()
        assert payload["contract_name"] == "DocumentOperationsSummaryV1"
        assert payload["feature_flags"]["perf_mode_enabled"] is True
        assert payload["feature_flags"]["report_pack_rollout_enabled"] is True
        assert payload["ai_costs"]["total_inspections"] >= 0
        assert payload["report_pack_rollout"]["contract_name"] == "ReportPackRolloutObservabilityV1"
        assert payload["report_pack_rollout"]["totals"]["gate_checks"] >= 1
        assert payload["backend_hotspots"]["contract_name"] == "BackendCriticalPathObservabilityV1"
        assert any(
            item["category"] == "ocr" and item["count"] >= 1
            for item in payload["heavy_operations"]["by_category"]
        )
        assert any(
            item["category"] == "pdf" and item["count"] >= 1
            for item in payload["heavy_operations"]["by_category"]
        )
    finally:
        clear_report_pack_rollout_metrics_for_tests()
        resetar_perf()
        get_settings.cache_clear()


def test_document_operations_summary_expoe_lifecycle_dos_laudos(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    timestamp = datetime(2026, 4, 18, 16, 0, tzinfo=timezone.utc)

    with SessionLocal() as banco:
        before = build_document_operations_operational_summary(banco)["case_lifecycle"]

        draft_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
            tipo_template="nr10_prontuario_instalacoes_eletricas",
        )
        awaiting_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
            tipo_template="nr20_prontuario_instalacoes_inflamaveis",
        )
        approved_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.APROVADO.value,
            tipo_template="nr13_inspecao_caldeira",
        )
        returned_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.REJEITADO.value,
            tipo_template="nr35_ponto_ancoragem",
        )

        draft_laudo = banco.get(Laudo, draft_id)
        awaiting_laudo = banco.get(Laudo, awaiting_id)
        approved_laudo = banco.get(Laudo, approved_id)
        returned_laudo = banco.get(Laudo, returned_id)
        assert draft_laudo is not None
        assert awaiting_laudo is not None
        assert approved_laudo is not None
        assert returned_laudo is not None

        draft_laudo.reaberto_em = timestamp
        awaiting_laudo.reabertura_pendente_em = timestamp
        awaiting_laudo.encerrado_pelo_inspetor_em = timestamp
        approved_laudo.encerrado_pelo_inspetor_em = timestamp
        returned_laudo.reabertura_pendente_em = timestamp
        banco.commit()

        payload = build_document_operations_operational_summary(banco)

    lifecycle = payload["case_lifecycle"]
    totals = lifecycle["totals"]

    assert lifecycle["contract_name"] == "TechnicalCaseLifecycleSummaryV1"
    assert totals["total_cases"] >= before["totals"]["total_cases"] + 4
    assert totals["inspector_collecting"] >= before["totals"]["inspector_collecting"] + 1
    assert totals["awaiting_mesa_review"] >= before["totals"]["awaiting_mesa_review"] + 1
    assert totals["approved"] >= before["totals"]["approved"] + 1
    assert totals["returned_to_inspector"] >= before["totals"]["returned_to_inspector"] + 1
    assert totals["pending_reopen"] >= before["totals"]["pending_reopen"] + 2
    assert totals["manual_reopens"] >= before["totals"]["manual_reopens"] + 1
    assert totals["inspector_finalized"] >= before["totals"]["inspector_finalized"] + 2
    assert any(
        item["status"] == "aguardando" and item["count"] >= totals["awaiting_mesa_review"]
        for item in lifecycle["status_distribution"]
    )
    assert any(
        item["template_key"] == "nr20_prontuario_instalacoes_inflamaveis"
        and item["count"] >= 1
        for item in lifecycle["top_pending_reopen_templates"]
    )
