from __future__ import annotations

from typing import Any


def build_platform_settings_console_summary_cards(
    *,
    environment_label: str,
    latest_changed_label: str,
    active_policies: int,
    review_ui_canonical_label: str,
) -> list[dict[str, Any]]:
    return [
        {
            "label": "Ambiente",
            "value": environment_label,
            "hint": "Ambiente em que o portal administrativo esta rodando.",
        },
        {
            "label": "Última alteração sensível",
            "value": latest_changed_label,
            "hint": "Ultima mudanca salva nas regras da plataforma.",
        },
        {
            "label": "Regras ativas",
            "value": str(active_policies),
            "hint": "Quantidade de regras que estao valendo agora para o Admin-CEO.",
        },
        {
            "label": "Liberacao da revisao",
            "value": review_ui_canonical_label,
            "hint": "Tela principal que hoje vale para a Mesa.",
        },
    ]


__all__ = ["build_platform_settings_console_summary_cards"]
