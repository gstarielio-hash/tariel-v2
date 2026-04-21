from __future__ import annotations

from app.domains.admin.platform_settings_console_summary_cards import (
    build_platform_settings_console_summary_cards,
)


def test_build_platform_settings_console_summary_cards_preserva_ordem_e_rotulos() -> None:
    cards = build_platform_settings_console_summary_cards(
        environment_label="DEV",
        latest_changed_label="18/04/2026 16:00 UTC",
        active_policies=3,
        review_ui_canonical_label="SSR legado",
    )

    assert [card["label"] for card in cards] == [
        "Ambiente",
        "Última alteração sensível",
        "Regras ativas",
        "Liberacao da revisao",
    ]
    assert cards[0]["value"] == "DEV"
    assert cards[1]["value"] == "18/04/2026 16:00 UTC"
    assert cards[2]["value"] == "3"
    assert cards[3]["value"] == "SSR legado"
