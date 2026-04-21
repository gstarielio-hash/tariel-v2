"""Regras baseline e refs de origem do policy engine incremental."""

from __future__ import annotations

from app.v2.billing import TenantPolicyCapabilitySnapshot
from app.v2.policy.models import PolicySourceRef


def _build_tenant_policy_source_id(policy: TenantPolicyCapabilitySnapshot) -> str:
    plan_name = str(policy.plan_name or "").strip().lower().replace(" ", "_")
    tenant_status = str(policy.tenant_status or "").strip().lower() or "active"
    return f"tenant_plan:{plan_name or 'unknown'}:{tenant_status}"


def _build_tenant_policy_summary(
    *,
    policy: TenantPolicyCapabilitySnapshot,
    area: str,
) -> str:
    parts = [
        f"Politica de {area} derivada do tenant no plano {policy.plan_name}.",
        f"tenant_status={policy.tenant_status}",
        f"usage_status={policy.usage_status}",
        f"upload_doc_enabled={policy.upload_doc_enabled}",
        f"deep_research_enabled={policy.deep_research_enabled}",
    ]
    if policy.recommended_plan:
        parts.append(f"recommended_plan={policy.recommended_plan}")
    return " ".join(parts)


def build_default_review_policy_source(
    *,
    tenant_id: str,
    template_key: str | None,
    tenant_policy_context: TenantPolicyCapabilitySnapshot | None = None,
) -> PolicySourceRef:
    if tenant_policy_context is not None:
        return PolicySourceRef(
            policy_source_kind="tenant",
            policy_source_id=_build_tenant_policy_source_id(tenant_policy_context),
            tenant_id=tenant_id,
            template_key=template_key,
            summary=_build_tenant_policy_summary(
                policy=tenant_policy_context,
                area="revisao",
            ),
        )
    return PolicySourceRef(
        policy_source_kind="default",
        policy_source_id="legacy_review_flow_v1",
        tenant_id=tenant_id,
        template_key=template_key,
        summary="Baseline conservador herdado do fluxo atual de revisao humana.",
    )


def build_document_gate_policy_source(
    *,
    tenant_id: str,
    template_key: str | None,
    tenant_policy_context: TenantPolicyCapabilitySnapshot | None = None,
) -> PolicySourceRef:
    if tenant_policy_context is not None:
        return PolicySourceRef(
            policy_source_kind="tenant",
            policy_source_id=_build_tenant_policy_source_id(tenant_policy_context),
            tenant_id=tenant_id,
            template_key=template_key,
            summary=_build_tenant_policy_summary(
                policy=tenant_policy_context,
                area="documento",
            ),
        )
    return PolicySourceRef(
        policy_source_kind="system",
        policy_source_id="legacy_document_gate_v1",
        tenant_id=tenant_id,
        template_key=template_key,
        summary="Gate minimo derivado do estado canonico do caso e do laudo legado.",
    )


__all__ = [
    "build_default_review_policy_source",
    "build_document_gate_policy_source",
]
