from __future__ import annotations

from typing import Any


def build_platform_settings_console_sections(
    *,
    access_items: list[dict[str, Any]],
    admin_reauth_max_age_minutes: int,
    support_items: list[dict[str, Any]],
    support_exceptional_mode: str,
    support_exceptional_mode_options: list[dict[str, str]],
    support_exceptional_approval_required: bool,
    support_exceptional_justification_required: bool,
    support_exceptional_max_duration_minutes: int,
    support_exceptional_scope_level: str,
    support_exceptional_scope_options: list[dict[str, str]],
    rollout_items: list[dict[str, Any]],
    review_ui_canonical: str,
    document_items: list[dict[str, Any]],
    observability_items: list[dict[str, Any]],
    defaults_items: list[dict[str, Any]],
    default_new_tenant_plan: str,
    default_new_tenant_plan_options: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "key": "access",
            "title": "Acesso e seguranca da plataforma",
            "description": "Controles de acesso do Admin-CEO, confirmacao extra e protecao das acoes mais sensiveis.",
            "badge": "Segurança",
            "items": access_items,
            "form": {
                "action": "/admin/configuracoes/acesso",
                "submit_label": "Salvar segurança",
                "requires_step_up": True,
                "fields": [
                    {
                        "name": "admin_reauth_max_age_minutes",
                        "label": "Janela de reautenticação",
                        "type": "number",
                        "value": admin_reauth_max_age_minutes,
                        "min": 1,
                        "max": 120,
                        "hint": "Tempo, em minutos, em que a confirmacao extra continua valendo para acoes criticas.",
                    },
                ],
            },
        },
        {
            "key": "support",
            "title": "Política de suporte excepcional",
            "description": "Regras para excecoes administrativas, com duracao, motivo e alcance maximos.",
            "badge": "Exceção",
            "items": support_items,
            "form": {
                "action": "/admin/configuracoes/suporte-excepcional",
                "submit_label": "Salvar política excepcional",
                "requires_step_up": True,
                "fields": [
                    {
                        "name": "support_exceptional_mode",
                        "label": "Modo operacional",
                        "type": "select",
                        "value": support_exceptional_mode,
                        "options": support_exceptional_mode_options,
                        "hint": "Defina se o suporte fica desligado, depende de aprovacao ou entra em modo de incidente controlado.",
                    },
                    {
                        "name": "support_exceptional_approval_required",
                        "label": "Exigir aprovação formal",
                        "type": "checkbox",
                        "value": support_exceptional_approval_required,
                        "hint": "Mantem a excecao condicionada a aprovacao registrada do Admin-CEO.",
                    },
                    {
                        "name": "support_exceptional_justification_required",
                        "label": "Exigir justificativa",
                        "type": "checkbox",
                        "value": support_exceptional_justification_required,
                        "hint": "Toda excecao precisa registrar o motivo na trilha administrativa.",
                    },
                    {
                        "name": "support_exceptional_max_duration_minutes",
                        "label": "Duração máxima",
                        "type": "number",
                        "value": support_exceptional_max_duration_minutes,
                        "min": 15,
                        "max": 1440,
                        "hint": "Tempo maximo continuo em minutos.",
                    },
                    {
                        "name": "support_exceptional_scope_level",
                        "label": "Escopo máximo",
                        "type": "select",
                        "value": support_exceptional_scope_level,
                        "options": support_exceptional_scope_options,
                        "hint": "Escolha ate onde o suporte excepcional pode chegar sem abrir conteudo bruto por padrao.",
                    },
                ],
            },
        },
        {
            "key": "rollout",
            "title": "Liberacao da revisao",
            "description": "Define qual tela de revisao vale como principal e acompanha como ela esta sendo usada.",
            "badge": "Liberacao",
            "items": rollout_items,
            "form": {
                "action": "/admin/configuracoes/rollout",
                "submit_label": "Salvar liberacao",
                "requires_step_up": True,
                "fields": [
                    {
                        "name": "review_ui_canonical",
                        "label": "Tela principal da revisao",
                        "type": "select",
                        "value": review_ui_canonical,
                        "options": [
                            {"value": "ssr", "label": "SSR legado"},
                        ],
                        "hint": "A revisao permanece no SSR legado para manter uma unica tela principal de operacao.",
                    },
                ],
            },
        },
        {
            "key": "document",
            "title": "Regras do documento",
            "description": "Resumo das travas do documento e do que precisa ficar guardado de forma duravel.",
            "badge": "Documento",
            "items": document_items,
            "read_only_note": "Resumo apenas para consulta. As travas reais do documento sao definidas pelo ambiente e pelas regras centrais.",
        },
        {
            "key": "observability",
            "title": "Historico e armazenamento",
            "description": "Regras de historico e tempo de armazenamento vindas do ambiente da plataforma.",
            "badge": "Historico",
            "items": observability_items,
            "read_only_note": "Resumo apenas para consulta. O tempo de armazenamento e o replay desta camada sao definidos fora do portal.",
        },
        {
            "key": "defaults",
            "title": "Padroes para novas empresas",
            "description": "Padroes aplicados quando uma nova empresa e criada no portal.",
            "badge": "Onboarding",
            "items": defaults_items,
            "form": {
                "action": "/admin/configuracoes/defaults",
                "submit_label": "Salvar padroes",
                "requires_step_up": True,
                "fields": [
                    {
                        "name": "default_new_tenant_plan",
                        "label": "Plano inicial da nova empresa",
                        "type": "select",
                        "value": default_new_tenant_plan,
                        "options": default_new_tenant_plan_options,
                        "hint": "Plano que ja vem preselecionado ao cadastrar uma nova empresa.",
                    },
                ],
            },
        },
    ]


__all__ = ["build_platform_settings_console_sections"]
