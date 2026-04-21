from __future__ import annotations

import main

from app.shared.database import Laudo, NivelAcesso, Usuario
from app.shared.security import obter_usuario_html
from app.v2.report_pack_rollout_metrics import (
    clear_report_pack_rollout_metrics_for_tests,
    record_report_pack_finalization_observation,
    record_report_pack_gate_observation,
    record_report_pack_review_decision,
)


def _sample_report_pack_case(*, tenant_id: int) -> Laudo:
    laudo = Laudo(
        id=77,
        empresa_id=tenant_id,
        tipo_template="nr35_linha_vida",
        entry_mode_preference="chat_first",
        entry_mode_effective="evidence_first",
        dados_formulario={
            "componentes_inspecionados": {
                "fixacao_dos_pontos": {"condicao": "NC"},
            },
            "conclusao": {"status": "Aprovado"},
        },
    )
    laudo.report_pack_draft_json = {
        "template_key": "nr35_linha_vida",
        "family": "nr35_periodica_linha_vida",
        "structured_data_candidate": {
            "componentes_inspecionados": {
                "fixacao_dos_pontos": {"condicao": "C"},
            },
            "conclusao": {"status": "Aprovado"},
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
    return laudo


def test_admin_summary_endpoint_do_report_pack_rollout_respeita_flag_e_expoe_metricas(
    ambiente_critico,
    monkeypatch,
) -> None:
    clear_report_pack_rollout_metrics_for_tests()
    client = ambiente_critico["client"]
    ids = ambiente_critico["ids"]

    assert client.get("/admin/api/report-pack-rollout/summary").status_code == 401

    main.app.dependency_overrides[obter_usuario_html] = lambda: Usuario(
        id=ids["admin_a"],
        empresa_id=ids["empresa_a"],
        nivel_acesso=NivelAcesso.DIRETORIA.value,
        email="admin@empresa-a.test",
    )
    try:
        monkeypatch.setenv("TARIEL_V2_REPORT_PACK_ROLLOUT_OBSERVABILITY", "0")
        resposta_disabled = client.get("/admin/api/report-pack-rollout/summary")
        assert resposta_disabled.status_code == 404

        monkeypatch.setenv("TARIEL_V2_REPORT_PACK_ROLLOUT_OBSERVABILITY", "1")
        laudo = _sample_report_pack_case(tenant_id=ids["empresa_a"])

        record_report_pack_gate_observation(
            laudo=laudo,
            report_pack_draft=laudo.report_pack_draft_json,
            approved=False,
            review_mode_sugerido="mesa_required",
        )
        record_report_pack_finalization_observation(
            laudo=laudo,
            report_pack_draft=laudo.report_pack_draft_json,
            final_validation_mode="mesa_required",
            status_revisao="Aguardando Aval",
        )
        record_report_pack_review_decision(
            laudo=laudo,
            action="aprovar",
            status_revisao="Aprovado",
        )

        resposta = client.get("/admin/api/report-pack-rollout/summary")
    finally:
        main.app.dependency_overrides.pop(obter_usuario_html, None)
        clear_report_pack_rollout_metrics_for_tests()

    assert resposta.status_code == 200
    payload = resposta.json()
    assert payload["contract_name"] == "ReportPackRolloutObservabilityV1"
    assert payload["contract_version"] == "v1"
    assert payload["observability_enabled"] is True
    assert payload["totals"]["gate_checks"] == 1
    assert payload["totals"]["finalizations"] == 1
    assert payload["totals"]["review_decisions"] == 1
    assert any(
        item["tenant_id"] == str(ids["empresa_a"]) and item["gate_checks"] == 1
        for item in payload["by_tenant"]
    )
    assert any(
        item["template_key"] == "nr35_linha_vida" and item["review_decisions"] == 1
        for item in payload["by_template_mode"]
    )
