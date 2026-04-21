from __future__ import annotations

import app.domains.admin.runtime_rollout_descriptors as runtime_rollout_descriptors


def test_build_rollout_runtime_descriptors_reflete_mobile_e_report_pack(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_rollout_descriptors,
        "mobile_v2_rollout_observability_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        runtime_rollout_descriptors,
        "report_pack_rollout_observability_enabled",
        lambda: False,
    )

    descriptors = runtime_rollout_descriptors.build_rollout_runtime_descriptors()

    assert descriptors[0]["technical_path"] == "/admin/api/mobile-v2-rollout/summary"
    assert descriptors[0]["status_tone_key"] == "positive"
    assert descriptors[0]["value_label"] == "Habilitado"
    assert descriptors[1]["technical_path"] == "/admin/api/report-pack-rollout/summary"
    assert descriptors[1]["status_tone_key"] == "neutral"
    assert descriptors[1]["value_label"] == "Observação"
