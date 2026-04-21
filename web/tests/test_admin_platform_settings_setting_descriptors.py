from __future__ import annotations

from app.domains.admin.platform_settings_setting_descriptors import (
    build_access_setting_descriptors,
    build_defaults_setting_descriptors,
    build_rollout_setting_descriptors,
    build_support_setting_descriptors,
)


def test_platform_setting_descriptors_preservam_ordem_esperada() -> None:
    assert [item["key"] for item in build_access_setting_descriptors()] == [
        "admin_reauth_max_age_minutes"
    ]
    assert [item["key"] for item in build_support_setting_descriptors()] == [
        "support_exceptional_mode",
        "support_exceptional_approval_required",
        "support_exceptional_justification_required",
        "support_exceptional_max_duration_minutes",
        "support_exceptional_scope_level",
    ]
    assert [item["key"] for item in build_rollout_setting_descriptors()] == [
        "review_ui_canonical"
    ]
    assert [item["key"] for item in build_defaults_setting_descriptors()] == [
        "default_new_tenant_plan"
    ]
