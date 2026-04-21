from __future__ import annotations

from app.domains.admin.platform_settings_console_sections import (
    build_platform_settings_console_sections,
)


def test_build_platform_settings_console_sections_monta_formularios_e_notas() -> None:
    sections = build_platform_settings_console_sections(
        access_items=[{"title": "Acesso"}],
        admin_reauth_max_age_minutes=25,
        support_items=[{"title": "Suporte"}],
        support_exceptional_mode="incident_controlled",
        support_exceptional_mode_options=[
            {"value": "disabled", "label": "Desligado"},
            {"value": "incident_controlled", "label": "Incidente controlado"},
        ],
        support_exceptional_approval_required=True,
        support_exceptional_justification_required=True,
        support_exceptional_max_duration_minutes=180,
        support_exceptional_scope_level="tenant_metadata_only",
        support_exceptional_scope_options=[
            {"value": "tenant_metadata_only", "label": "Somente metadados"},
        ],
        rollout_items=[{"title": "Rollout"}],
        review_ui_canonical="ssr",
        document_items=[{"title": "Documento"}],
        observability_items=[{"title": "Observabilidade"}],
        defaults_items=[{"title": "Defaults"}],
        default_new_tenant_plan="basico",
        default_new_tenant_plan_options=[{"value": "basico", "label": "basico"}],
    )

    assert [section["key"] for section in sections] == [
        "access",
        "support",
        "rollout",
        "document",
        "observability",
        "defaults",
    ]
    assert sections[0]["form"]["fields"][0]["value"] == 25
    assert sections[1]["form"]["fields"][0]["options"][1]["value"] == "incident_controlled"
    assert sections[1]["form"]["fields"][3]["value"] == 180
    assert sections[2]["form"]["fields"][0]["value"] == "ssr"
    assert "read_only_note" in sections[3]
    assert "read_only_note" in sections[4]
    assert sections[5]["form"]["fields"][0]["value"] == "basico"
