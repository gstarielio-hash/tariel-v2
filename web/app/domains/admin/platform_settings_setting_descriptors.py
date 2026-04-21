from __future__ import annotations

from typing import Any


def build_access_setting_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "key": "admin_reauth_max_age_minutes",
            "title": "Janela de reautenticação",
            "description": "Define a validade do step-up para ações críticas do Admin-CEO.",
        }
    ]


def build_support_setting_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "key": "support_exceptional_mode",
            "title": "Modo de suporte excepcional",
            "description": "Define o regime operacional permitido para suporte fora do fluxo administrativo padrão.",
        },
        {
            "key": "support_exceptional_approval_required",
            "title": "Aprovação formal",
            "description": "Exige aprovação explícita antes de ativar suporte excepcional para qualquer tenant.",
        },
        {
            "key": "support_exceptional_justification_required",
            "title": "Justificativa obrigatória",
            "description": "Impede abertura excepcional sem motivo auditável e rastreável.",
        },
        {
            "key": "support_exceptional_max_duration_minutes",
            "title": "Duração máxima",
            "description": "Janela máxima contínua em que um suporte excepcional pode permanecer ativo.",
        },
        {
            "key": "support_exceptional_scope_level",
            "title": "Escopo máximo permitido",
            "description": "Delimita até onde o suporte excepcional pode alcançar sem violar governança.",
        },
    ]


def build_rollout_setting_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "key": "review_ui_canonical",
            "title": "UI canônica da revisão",
            "description": "Fluxo oficial fixado no painel SSR legado do revisor.",
        }
    ]


def build_defaults_setting_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "key": "default_new_tenant_plan",
            "title": "Plano padrão do onboarding",
            "description": "Plano pré-selecionado ao provisionar uma nova empresa pelo Admin-CEO.",
        }
    ]


__all__ = [
    "build_access_setting_descriptors",
    "build_defaults_setting_descriptors",
    "build_rollout_setting_descriptors",
    "build_support_setting_descriptors",
]
