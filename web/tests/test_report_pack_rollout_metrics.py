from __future__ import annotations

from app.shared.database import Laudo
from app.v2.report_pack_rollout_metrics import (
    clear_report_pack_rollout_metrics_for_tests,
    get_report_pack_rollout_operational_summary,
    record_report_pack_finalization_observation,
    record_report_pack_gate_observation,
    record_report_pack_review_decision,
)


def test_report_pack_rollout_metrics_agregam_gate_finalizacao_e_divergencia() -> None:
    clear_report_pack_rollout_metrics_for_tests()

    laudo = Laudo(
        id=77,
        empresa_id=33,
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

    summary = get_report_pack_rollout_operational_summary()

    assert summary["totals"]["gate_checks"] == 1
    assert summary["totals"]["gate_blocked"] == 1
    assert summary["totals"]["finalizations"] == 1
    assert summary["totals"]["routed_to_mesa"] == 1
    assert summary["totals"]["review_decisions"] == 1
    assert summary["totals"]["review_approved"] == 1
    assert summary["totals"]["mode_switches"] == 1
    assert summary["totals"]["divergence_events"] == 2
    assert summary["totals"]["divergence_fields_total"] >= 2

    nr35_row = next(
        row
        for row in summary["by_template_mode"]
        if row["template_key"] == "nr35_linha_vida"
        and row["entry_mode_effective"] == "evidence_first"
    )
    assert nr35_row["gate_checks"] == 1
    assert nr35_row["finalizations"] == 1
    assert nr35_row["review_decisions"] == 1

    preference_row = next(
        row
        for row in summary["by_preference_effective"]
        if row["entry_mode_preference"] == "chat_first"
        and row["entry_mode_effective"] == "evidence_first"
    )
    assert preference_row["count"] == 3

    assert summary["recent_events"][0]["kind"] == "review_decision"
