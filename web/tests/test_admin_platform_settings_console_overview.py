from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.domains.admin.platform_settings_console_overview import (
    build_platform_settings_console_overview,
)


def test_build_platform_settings_console_overview_resume_ambiente_e_politicas() -> None:
    cards = build_platform_settings_console_overview(
        rows=[
            SimpleNamespace(
                criado_em=datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc),
                atualizado_em=None,
            ),
            SimpleNamespace(
                criado_em=datetime(2026, 4, 18, 13, 0, tzinfo=timezone.utc),
                atualizado_em=datetime(2026, 4, 18, 14, 30, tzinfo=timezone.utc),
            ),
        ],
        privacy={"replay_allowed_in_browser": True},
        environment_label="DEV",
        review_ui_canonical_label="SSR legado",
        support_exceptional_mode="incident_controlled",
        document_hard_gate_enabled=True,
        durable_evidence_enabled=False,
    )

    assert cards[0]["value"] == "DEV"
    assert cards[1]["value"] == "18/04/2026 14:30 UTC"
    assert cards[2]["value"] == "3"
    assert cards[3]["value"] == "SSR legado"
