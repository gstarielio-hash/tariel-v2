from __future__ import annotations

import app.domains.admin.runtime_settings_descriptors as runtime_settings_descriptors


def test_build_access_runtime_descriptors_reflete_provedores_e_operadores(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_settings_descriptors,
        "ADMIN_LOGIN_GOOGLE_ENABLED",
        True,
    )
    monkeypatch.setattr(
        runtime_settings_descriptors,
        "ADMIN_LOGIN_GOOGLE_ENTRYPOINT",
        "/admin/login/google",
    )
    monkeypatch.setattr(
        runtime_settings_descriptors,
        "ADMIN_LOGIN_MICROSOFT_ENABLED",
        False,
    )
    monkeypatch.setattr(
        runtime_settings_descriptors,
        "ADMIN_LOGIN_MICROSOFT_ENTRYPOINT",
        "",
    )

    descriptors = runtime_settings_descriptors.build_access_runtime_descriptors(
        operator_count=4
    )

    assert descriptors[0]["source_kind"] == "fixed"
    assert descriptors[1]["value_label"] == "Habilitado"
    assert descriptors[1]["reason"] == "Gateway configurado."
    assert descriptors[2]["value_label"] == "Desabilitado"
    assert descriptors[2]["reason"] == "Gateway ainda não configurado."
    assert descriptors[3]["technical_path"] == "/admin/api/operadores"
    assert descriptors[3]["value_label"] == "4"


def test_build_document_runtime_descriptors_reflete_gates(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_settings_descriptors,
        "document_soft_gate_observability_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        runtime_settings_descriptors,
        "document_hard_gate_observability_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        runtime_settings_descriptors,
        "document_hard_gate_durable_evidence_enabled",
        lambda: True,
    )

    descriptors = runtime_settings_descriptors.build_document_runtime_descriptors()

    assert descriptors[0]["technical_path"] == "/admin/api/document-soft-gate/summary"
    assert descriptors[0]["status_tone_key"] == "positive"
    assert descriptors[1]["technical_path"] == "/admin/api/document-hard-gate/summary"
    assert descriptors[1]["status_tone_key"] == "warning"
    assert descriptors[2]["technical_path"] == "/admin/api/document-hard-gate/durable-summary"
    assert descriptors[2]["value_label"] == "Habilitada"


def test_build_observability_runtime_descriptors_reflete_retencao() -> None:
    descriptors = runtime_settings_descriptors.build_observability_runtime_descriptors(
        {
            "replay_allowed_in_browser": True,
            "log_retention_days": 12,
            "perf_retention_days": 7,
            "artifact_retention_days": 3,
        }
    )

    assert descriptors[0]["technical_path"] == "/admin/api/observability/summary"
    assert descriptors[0]["status_tone_key"] == "positive"
    assert descriptors[1]["value_label"] == "12 dias"
    assert descriptors[2]["value_label"] == "7 dias"
    assert descriptors[3]["value_label"] == "3 dias"
