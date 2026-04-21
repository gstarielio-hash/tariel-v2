from __future__ import annotations

from typing import Any

from app.domains.admin.portal_support import (
    ADMIN_LOGIN_GOOGLE_ENABLED,
    ADMIN_LOGIN_GOOGLE_ENTRYPOINT,
    ADMIN_LOGIN_MICROSOFT_ENABLED,
    ADMIN_LOGIN_MICROSOFT_ENTRYPOINT,
)
from app.v2.document import (
    document_hard_gate_observability_enabled,
    document_soft_gate_observability_enabled,
)
from app.v2.document.hard_gate_evidence import (
    document_hard_gate_durable_evidence_enabled,
)


def build_access_runtime_descriptors(*, operator_count: int) -> list[dict[str, Any]]:
    return [
        {
            "title": "MFA obrigatório do Admin-CEO",
            "description": "O acesso administrativo de plataforma exige TOTP antes da emissão de sessão.",
            "value_label": "Obrigatório",
            "status_tone_key": "positive",
            "source_kind": "fixed",
            "scope_label": "Somente Admin-CEO",
        },
        {
            "title": "Google corporativo",
            "description": "Entrada de identidade autorizada para operadores de plataforma previamente cadastrados.",
            "value_label": "Habilitado" if ADMIN_LOGIN_GOOGLE_ENABLED else "Desabilitado",
            "status_tone_key": "positive" if ADMIN_LOGIN_GOOGLE_ENABLED else "neutral",
            "source_kind": "environment",
            "scope_label": "Somente Admin-CEO",
            "reason": (
                "Gateway configurado."
                if ADMIN_LOGIN_GOOGLE_ENTRYPOINT
                else "Gateway ainda não configurado."
            ),
        },
        {
            "title": "Microsoft corporativo",
            "description": "Entrada corporativa alternativa para operadores autorizados do Admin-CEO.",
            "value_label": "Habilitado"
            if ADMIN_LOGIN_MICROSOFT_ENABLED
            else "Desabilitado",
            "status_tone_key": "positive"
            if ADMIN_LOGIN_MICROSOFT_ENABLED
            else "neutral",
            "source_kind": "environment",
            "scope_label": "Somente Admin-CEO",
            "reason": (
                "Gateway configurado."
                if ADMIN_LOGIN_MICROSOFT_ENTRYPOINT
                else "Gateway ainda não configurado."
            ),
        },
        {
            "title": "Operadores autorizados",
            "description": "Total de contas de plataforma autorizadas a acessar o portal Admin-CEO.",
            "value_label": str(operator_count),
            "status_tone_key": "neutral",
            "source_kind": "runtime",
            "scope_label": "Somente Admin-CEO",
            "technical_path": "/admin/api/operadores",
        },
    ]


def build_document_runtime_descriptors() -> list[dict[str, Any]]:
    soft_gate_enabled = document_soft_gate_observability_enabled()
    hard_gate_enabled = document_hard_gate_observability_enabled()
    durable_evidence_enabled = document_hard_gate_durable_evidence_enabled()
    return [
        {
            "title": "Soft gate documental",
            "description": "Observa sinais preventivos antes de mutações documentais sensíveis.",
            "value_label": "Habilitado" if soft_gate_enabled else "Observação",
            "status_tone_key": "positive" if soft_gate_enabled else "neutral",
            "source_kind": "environment",
            "scope_label": "Documento",
            "technical_path": "/admin/api/document-soft-gate/summary",
        },
        {
            "title": "Hard gate documental",
            "description": "Resume bloqueios efetivos e o estado operacional do enforcement documental.",
            "value_label": "Habilitado" if hard_gate_enabled else "Observação",
            "status_tone_key": "positive" if hard_gate_enabled else "warning",
            "source_kind": "environment",
            "scope_label": "Documento",
            "technical_path": "/admin/api/document-hard-gate/summary",
        },
        {
            "title": "Evidência durável",
            "description": "Mantém trilha persistente de bloqueios documentais para auditoria posterior.",
            "value_label": "Habilitada" if durable_evidence_enabled else "Desabilitada",
            "status_tone_key": "positive" if durable_evidence_enabled else "neutral",
            "source_kind": "environment",
            "scope_label": "Documento",
            "technical_path": "/admin/api/document-hard-gate/durable-summary",
        },
    ]


def build_observability_runtime_descriptors(
    privacy: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    privacy_payload = dict(privacy or {})
    return [
        {
            "title": "Replay em navegador",
            "description": "Indica se a observabilidade permite replay de navegação no browser.",
            "value_label": (
                "Habilitado"
                if bool(privacy_payload.get("replay_allowed_in_browser"))
                else "Desabilitado"
            ),
            "status_tone_key": (
                "positive"
                if bool(privacy_payload.get("replay_allowed_in_browser"))
                else "neutral"
            ),
            "source_kind": "environment",
            "scope_label": "Observabilidade",
            "technical_path": "/admin/api/observability/summary",
        },
        {
            "title": "Retenção de logs",
            "description": "Janela de retenção dos logs administrativos e operacionais minimizados.",
            "value_label": f"{int(privacy_payload.get('log_retention_days') or 0)} dias",
            "status_tone_key": "neutral",
            "source_kind": "environment",
            "scope_label": "Observabilidade",
        },
        {
            "title": "Retenção de performance",
            "description": "Janela de retenção de métricas e telemetria de performance da plataforma.",
            "value_label": f"{int(privacy_payload.get('perf_retention_days') or 0)} dias",
            "status_tone_key": "neutral",
            "source_kind": "environment",
            "scope_label": "Observabilidade",
        },
        {
            "title": "Retenção de artifacts",
            "description": "Janela de retenção de artifacts e bundles operacionais do runtime.",
            "value_label": f"{int(privacy_payload.get('artifact_retention_days') or 0)} dias",
            "status_tone_key": "neutral",
            "source_kind": "environment",
            "scope_label": "Observabilidade",
        },
    ]


__all__ = [
    "build_access_runtime_descriptors",
    "build_document_runtime_descriptors",
    "build_observability_runtime_descriptors",
]
