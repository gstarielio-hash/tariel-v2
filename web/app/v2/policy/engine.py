"""Derivacao incremental do policy engine do V2."""

from __future__ import annotations

from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.database import (
    EvidenceMesaStatus,
    EvidenceOperationalStatus,
    EvidenceValidation,
    OperationalIrregularity,
    OperationalIrregularityStatus,
    OperationalSeverity,
)
from app.v2.acl.technical_case_core import TechnicalCaseStatusSnapshot
from app.v2.billing import TenantPolicyCapabilitySnapshot
from app.v2.policy.governance import load_case_policy_governance_context
from app.v2.policy.models import (
    DocumentMaterializationDecision,
    PolicyDecisionSummary,
    ReviewRequirementDecision,
    ReviewMode,
    TechnicalCasePolicyDecision,
)
from app.v2.policy.tenant_rules import (
    build_default_review_policy_source,
    build_document_gate_policy_source,
)
from app.v2.runtime import (
    v2_mobile_autonomy_template_allowlist,
    v2_mobile_autonomy_tenant_allowlist,
)

_REVIEW_MODE_ORDER = {
    "mobile_autonomous": 0,
    "mobile_review_allowed": 1,
    "mesa_required": 2,
}
_OPEN_IRREGULARITY_STATUSES = (
    OperationalIrregularityStatus.OPEN.value,
    OperationalIrregularityStatus.ACKNOWLEDGED.value,
)
_RETURN_TO_INSPECTOR_TYPES = {
    "block_returned_to_inspector",
    "field_reopened",
}


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _payload_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _payload_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _resolve_mobile_autonomy_context(
    *,
    tenant_id: str | None,
    template_key: str | None,
    report_pack_draft: dict[str, Any] | None,
) -> dict[str, Any]:
    draft = report_pack_draft if isinstance(report_pack_draft, dict) else {}
    quality_gates = _payload_dict(draft.get("quality_gates"))
    telemetry = _payload_dict(draft.get("telemetry"))
    resolved_template = (
        _normalize_optional_text(template_key)
        or _normalize_optional_text(draft.get("template_key"))
        or ""
    )
    allowlisted = resolved_template in {
        _normalize_optional_text(item) or "" for item in v2_mobile_autonomy_template_allowlist()
    }
    tenant_allowlist = {
        _normalize_optional_text(item) or "" for item in v2_mobile_autonomy_tenant_allowlist()
    }
    tenant_allowed = not tenant_allowlist or (_normalize_optional_text(tenant_id) or "") in tenant_allowlist
    autonomy_ready = bool(quality_gates.get("autonomy_ready"))
    evidence_first = (
        _normalize_optional_text(telemetry.get("entry_mode_effective")) == "evidence_first"
    )
    return {
        "template_key": resolved_template,
        "allowlisted": allowlisted,
        "tenant_allowed": tenant_allowed,
        "autonomy_ready": autonomy_ready,
        "evidence_first": evidence_first,
        "missing_evidence": list(quality_gates.get("missing_evidence") or []),
        "final_validation_mode": _normalize_optional_text(
            quality_gates.get("final_validation_mode")
        ),
        "family_key": _normalize_optional_text(
            draft.get("catalog_family_key") or draft.get("family_key")
        ),
    }


def _normalize_text_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raw_values = [item.strip() for item in values.split(",")]
    elif isinstance(values, (list, tuple, set)):
        raw_values = [str(item or "").strip() for item in values]
    else:
        raw_values = [str(values or "").strip()]
    return [item for item in raw_values if item]


def _normalize_review_mode(value: Any, *, fallback: str = "mesa_required") -> ReviewMode:
    text = str(value or "").strip().lower()
    if text in _REVIEW_MODE_ORDER:
        return text  # type: ignore[return-value]
    return fallback  # type: ignore[return-value]


def _effective_max_review_mode(governance_context: dict[str, Any]) -> ReviewMode:
    candidates = [
        _normalize_review_mode(governance_context.get("max_review_mode") or "mobile_autonomous"),
    ]
    release_max = governance_context.get("release_max_review_mode")
    if release_max:
        candidates.append(_normalize_review_mode(release_max))
    return sorted(candidates, key=lambda item: _REVIEW_MODE_ORDER[item], reverse=True)[0]


def _downgrade_review_mode(
    review_mode: ReviewMode,
    *,
    mobile_review_allowed: bool,
    mobile_autonomous_allowed: bool,
) -> ReviewMode:
    if review_mode == "mobile_autonomous" and not mobile_autonomous_allowed:
        return "mobile_review_allowed" if mobile_review_allowed else "mesa_required"
    if review_mode == "mobile_review_allowed" and not mobile_review_allowed:
        return "mesa_required"
    return review_mode


def _resolve_requested_review_mode(
    *,
    autonomy_context: dict[str, Any],
    governance_context: dict[str, Any],
) -> ReviewMode:
    forced_mode = governance_context.get("release_force_review_mode")
    requested_mode = _normalize_review_mode(
        forced_mode
        or autonomy_context.get("final_validation_mode")
        or governance_context.get("default_review_mode")
        or "mesa_required"
    )
    if requested_mode == "mobile_autonomous" and (
        not bool(autonomy_context.get("autonomy_ready"))
        or not bool(autonomy_context.get("evidence_first"))
    ):
        return "mobile_review_allowed"
    return requested_mode


def _is_template_allowed_by_release(
    *,
    template_key: str | None,
    governance_context: dict[str, Any],
) -> bool:
    allowed_templates = _normalize_text_list(governance_context.get("allowed_templates"))
    if not allowed_templates:
        return True
    normalized_template = str(template_key or "").strip().lower()
    return normalized_template in {item.lower() for item in allowed_templates}


def _is_variant_allowed_by_release(governance_context: dict[str, Any]) -> bool:
    allowed_variants = _normalize_text_list(governance_context.get("allowed_variants"))
    if not allowed_variants:
        return True
    selection_token = str(governance_context.get("activation_selection_token") or "").strip().lower()
    variant_key = str(governance_context.get("variant_key") or "").strip().lower()
    normalized_allowed = {item.lower() for item in allowed_variants}
    return bool(selection_token and selection_token in normalized_allowed) or bool(
        variant_key and variant_key in normalized_allowed
    )


def _plan_is_allowed(
    *,
    tenant_policy_context: TenantPolicyCapabilitySnapshot | None,
    plans: list[str],
) -> bool:
    if not plans:
        return True
    plan_name = str(getattr(tenant_policy_context, "plan_name", "") or "").strip().lower()
    return plan_name in {item.lower() for item in plans}


def _build_family_policy_summary(
    governance_context: dict[str, Any],
) -> dict[str, Any]:
    review_policy = _payload_dict(governance_context.get("review_policy"))
    return {
        "family_key": governance_context.get("family_key"),
        "family_label": governance_context.get("family_label"),
        "requires_family_lock": bool(review_policy.get("requires_family_lock")),
        "block_on_scope_mismatch": bool(review_policy.get("block_on_scope_mismatch")),
        "block_on_missing_required_evidence": bool(
            review_policy.get("block_on_missing_required_evidence")
        ),
        "block_on_critical_field_absent": bool(
            review_policy.get("block_on_critical_field_absent")
        ),
        "default_review_mode": governance_context.get("default_review_mode"),
        "max_review_mode": governance_context.get("max_review_mode"),
        "release_force_review_mode": governance_context.get("release_force_review_mode"),
        "release_max_review_mode": governance_context.get("release_max_review_mode"),
        "release_status": governance_context.get("release_status"),
        "activation_active": bool(governance_context.get("activation_active")),
        "blocking_conditions_count": len(
            _normalize_text_list(review_policy.get("blocking_conditions"))
        ),
        "non_blocking_conditions_count": len(
            _normalize_text_list(review_policy.get("non_blocking_conditions"))
        ),
    }


def _build_tenant_entitlements(
    *,
    tenant_policy_context: TenantPolicyCapabilitySnapshot | None,
    governance_context: dict[str, Any],
    autonomy_context: dict[str, Any],
    template_key: str | None,
) -> dict[str, Any]:
    policy = _payload_dict(governance_context.get("tenant_entitlements_policy"))
    tenant_blocked = _is_tenant_blocked(tenant_policy_context)
    release_present = bool(governance_context.get("release_present"))
    release_active = governance_context.get("release_active")
    requires_release_active = bool(policy.get("requires_release_active")) and release_present
    template_allowed = _is_template_allowed_by_release(
        template_key=template_key,
        governance_context=governance_context,
    )
    variant_allowed = _is_variant_allowed_by_release(governance_context)

    review_plans = _normalize_text_list(
        policy.get("mobile_review_allowed_plans")
        or policy.get("mobile_review_plans")
    )
    autonomy_plans = _normalize_text_list(
        policy.get("mobile_autonomous_allowed_plans")
        or policy.get("mobile_autonomous_plans")
    )
    requires_upload_doc_for_autonomy = bool(
        policy.get("requires_upload_doc_for_mobile_autonomous")
    )
    structural_mobile_review_allowed = (
        not tenant_blocked
        and template_allowed
        and variant_allowed
        and (not requires_release_active or bool(release_active))
    )
    review_plan_allowed = _plan_is_allowed(
        tenant_policy_context=tenant_policy_context,
        plans=review_plans,
    )
    autonomy_structural_allowed = (
        structural_mobile_review_allowed
        and bool(autonomy_context.get("allowlisted"))
        and bool(autonomy_context.get("tenant_allowed"))
        and bool(autonomy_context.get("autonomy_ready"))
        and bool(autonomy_context.get("evidence_first"))
        and (
            not requires_upload_doc_for_autonomy
            or bool(getattr(tenant_policy_context, "upload_doc_enabled", False))
        )
    )
    autonomy_plan_allowed = _plan_is_allowed(
        tenant_policy_context=tenant_policy_context,
        plans=autonomy_plans,
    )

    release_mobile_review_override = governance_context.get("release_mobile_review_override")
    release_mobile_autonomy_override = governance_context.get(
        "release_mobile_autonomous_override"
    )

    mobile_review_allowed = structural_mobile_review_allowed and review_plan_allowed
    if isinstance(release_mobile_review_override, bool):
        mobile_review_allowed = (
            structural_mobile_review_allowed and release_mobile_review_override
        )
    elif release_mobile_autonomy_override is True:
        mobile_review_allowed = structural_mobile_review_allowed

    mobile_autonomous_allowed = (
        mobile_review_allowed
        and autonomy_structural_allowed
        and autonomy_plan_allowed
    )
    if isinstance(release_mobile_autonomy_override, bool):
        mobile_autonomous_allowed = (
            mobile_review_allowed
            and autonomy_structural_allowed
            and release_mobile_autonomy_override
        )

    max_review_mode = _effective_max_review_mode(governance_context)
    if _REVIEW_MODE_ORDER[max_review_mode] >= _REVIEW_MODE_ORDER["mesa_required"]:
        mobile_review_allowed = False
        mobile_autonomous_allowed = False
    elif _REVIEW_MODE_ORDER[max_review_mode] >= _REVIEW_MODE_ORDER["mobile_review_allowed"]:
        mobile_autonomous_allowed = False

    allowed_review_modes = ["mesa_required"]
    if mobile_review_allowed:
        allowed_review_modes.append("mobile_review_allowed")
    if mobile_autonomous_allowed:
        allowed_review_modes.append("mobile_autonomous")

    return {
        "tenant_id": getattr(tenant_policy_context, "tenant_id", None),
        "tenant_status": getattr(tenant_policy_context, "tenant_status", None),
        "plan_name": getattr(tenant_policy_context, "plan_name", None),
        "usage_status": getattr(tenant_policy_context, "usage_status", None),
        "family_release_present": release_present,
        "family_release_active": release_active,
        "catalog_activation_active": bool(governance_context.get("activation_active")),
        "template_allowed_by_release": template_allowed,
        "variant_allowed_by_release": variant_allowed,
        "mobile_review_allowed": mobile_review_allowed,
        "mobile_autonomous_allowed": mobile_autonomous_allowed,
        "allowed_review_modes": allowed_review_modes,
        "requires_release_active": requires_release_active,
        "requires_upload_doc_for_mobile_autonomous": requires_upload_doc_for_autonomy,
        "effective_max_review_mode": max_review_mode,
        "force_review_mode": governance_context.get("release_force_review_mode"),
        "release_mobile_review_override": release_mobile_review_override,
        "release_mobile_autonomous_override": release_mobile_autonomy_override,
    }


def _build_runtime_operational_context(
    *,
    banco: Session | None,
    case_snapshot: TechnicalCaseStatusSnapshot,
) -> dict[str, Any]:
    laudo_id = getattr(case_snapshot.case_ref, "legacy_laudo_id", None)
    if banco is None or laudo_id is None:
        return {}

    validations = list(
        banco.scalars(
            select(EvidenceValidation)
            .where(EvidenceValidation.laudo_id == int(laudo_id))
            .order_by(EvidenceValidation.last_evaluated_at.desc(), EvidenceValidation.id.desc())
        ).all()
    )
    irregularities = list(
        banco.scalars(
            select(OperationalIrregularity)
            .where(
                OperationalIrregularity.laudo_id == int(laudo_id),
                OperationalIrregularity.status.in_(_OPEN_IRREGULARITY_STATUSES),
            )
            .order_by(OperationalIrregularity.criado_em.desc(), OperationalIrregularity.id.desc())
        ).all()
    )

    pending_recheck = [
        item
        for item in validations
        if str(item.mesa_status or "").strip().lower() == EvidenceMesaStatus.NEEDS_RECHECK.value
    ]
    irregular_validations = [
        item
        for item in validations
        if str(item.operational_status or "").strip().lower()
        in {EvidenceOperationalStatus.IRREGULAR.value, EvidenceOperationalStatus.REPLACED.value}
    ]
    open_returns = [
        item
        for item in irregularities
        if str(item.irregularity_type or "").strip().lower() in _RETURN_TO_INSPECTOR_TYPES
    ]
    blocking_irregularities = [
        item
        for item in irregularities
        if str(item.severity or "").strip().lower() == OperationalSeverity.BLOCKER.value
        or str(item.irregularity_type or "").strip().lower() not in _RETURN_TO_INSPECTOR_TYPES
    ]

    latest_validation = validations[0] if validations else None
    latest_irregularity = irregularities[0] if irregularities else None
    return {
        "open_irregularity_count": len(irregularities),
        "open_return_to_inspector_count": len(open_returns),
        "blocking_irregularity_count": len(blocking_irregularities),
        "needs_recheck_count": len(pending_recheck),
        "irregular_evidence_count": len(irregular_validations),
        "latest_validation_evidence_key": (
            str(latest_validation.evidence_key or "").strip() or None
            if latest_validation is not None
            else None
        ),
        "latest_irregularity_type": (
            str(latest_irregularity.irregularity_type or "").strip() or None
            if latest_irregularity is not None
            else None
        ),
        "latest_irregularity_evidence_key": (
            str(latest_irregularity.evidence_key or "").strip() or None
            if latest_irregularity is not None
            else None
        ),
    }


def _build_red_flags(
    *,
    governance_context: dict[str, Any],
    tenant_entitlements: dict[str, Any],
    autonomy_context: dict[str, Any],
    runtime_operational_context: dict[str, Any],
    template_key: str | None,
) -> list[dict[str, Any]]:
    review_policy = _payload_dict(governance_context.get("review_policy"))
    red_flags: list[dict[str, Any]] = []
    missing_evidence = list(autonomy_context.get("missing_evidence") or [])

    def _append_flag(
        *,
        code: str,
        title: str,
        message: str,
        severity: str = "high",
        blocking: bool = True,
        source: str = "family_policy",
    ) -> None:
        red_flags.append(
            {
                "code": code,
                "title": title,
                "message": message,
                "severity": severity,
                "blocking": blocking,
                "source": source,
                "force_review_mode": "mesa_required" if blocking else None,
            }
        )

    if bool(review_policy.get("requires_family_lock")) and not bool(
        governance_context.get("family_key")
    ):
        _append_flag(
            code="family_lock_missing",
            title="Familia governada ausente",
            message="O caso nao esta vinculado a uma familia governada valida para esta operacao.",
        )

    draft_family_key = _normalize_optional_text(autonomy_context.get("family_key"))
    if (
        bool(review_policy.get("block_on_scope_mismatch"))
        and draft_family_key
        and governance_context.get("family_key")
        and draft_family_key.lower() != str(governance_context.get("family_key")).lower()
    ):
        _append_flag(
            code="family_scope_mismatch",
            title="Escopo divergente da familia",
            message="O draft incremental aponta para uma familia diferente da familia governada do caso.",
        )

    if bool(review_policy.get("block_on_missing_required_evidence")) and missing_evidence:
        _append_flag(
            code="missing_required_evidence",
            title="Evidencia obrigatoria pendente",
            message="Ainda existem evidencias obrigatorias faltantes no quality gate do caso.",
        )

    if int(runtime_operational_context.get("open_return_to_inspector_count") or 0) > 0:
        _append_flag(
            code="runtime_return_to_inspector_open",
            title="Refazer operacional ainda aberto",
            message="O caso ainda possui blocos devolvidos ao inspetor sem resolucao operacional consolidada.",
            source="runtime_operational",
        )

    if int(runtime_operational_context.get("needs_recheck_count") or 0) > 0:
        _append_flag(
            code="runtime_evidence_needs_recheck",
            title="Evidencia aguardando rechecagem",
            message="Existe evidencia substituida ou sinalizada que ainda exige nova revalidacao antes da decisao final.",
            source="runtime_operational",
        )

    if int(runtime_operational_context.get("blocking_irregularity_count") or 0) > 0:
        _append_flag(
            code="runtime_blocking_irregularity_open",
            title="Irregularidade operacional bloqueante",
            message="Uma ou mais irregularidades operacionais abertas ainda bloqueiam o fechamento governado do caso.",
            source="runtime_operational",
        )

    if (
        governance_context.get("release_present")
        and governance_context.get("release_active") is False
    ):
        _append_flag(
            code="tenant_family_release_inactive",
            title="Liberacao do tenant inativa",
            message="A familia existe no catalogo, mas a liberacao por tenant nao esta ativa para este caso.",
            source="tenant_release",
        )

    if not bool(tenant_entitlements.get("template_allowed_by_release", True)):
        _append_flag(
            code="template_not_released_for_tenant",
            title="Template fora da liberacao",
            message=(
                f"O template {template_key or 'selecionado'} nao esta liberado para este tenant "
                "na familia atual."
            ),
            source="tenant_release",
        )

    if not bool(tenant_entitlements.get("variant_allowed_by_release", True)):
        _append_flag(
            code="variant_not_released_for_tenant",
            title="Variante fora da liberacao",
            message="A variante comercial atual nao esta liberada para este tenant na familia governada.",
            source="tenant_release",
        )

    requested_mode = _normalize_review_mode(
        autonomy_context.get("final_validation_mode") or "mesa_required"
    )
    if requested_mode != "mesa_required" and not bool(
        tenant_entitlements.get("mobile_review_allowed")
    ):
        _append_flag(
            code="tenant_not_entitled_mobile_review",
            title="Revisao mobile nao autorizada",
            message="A politica comercial/governada do tenant nao libera decisao mobile para este caso.",
            source="tenant_entitlement",
        )
    elif requested_mode == "mobile_autonomous" and not bool(
        tenant_entitlements.get("mobile_autonomous_allowed")
    ):
        _append_flag(
            code="tenant_not_entitled_mobile_autonomy",
            title="Autonomia mobile nao autorizada",
            message="O tenant nao possui entitlement suficiente para concluir este caso em modo autonomo.",
            severity="medium",
            blocking=False,
            source="tenant_entitlement",
        )

    for raw_flag in _payload_list(review_policy.get("red_flags")):
        if not isinstance(raw_flag, dict):
            continue
        title = _normalize_optional_text(raw_flag.get("title"))
        message = _normalize_optional_text(raw_flag.get("message"))
        code = _normalize_optional_text(raw_flag.get("code"))
        if not title or not message:
            continue
        blocking = bool(raw_flag.get("blocking", True))
        when_missing_evidence = bool(raw_flag.get("when_missing_required_evidence"))
        if when_missing_evidence and not missing_evidence:
            continue
        _append_flag(
            code=code or title.lower().replace(" ", "_"),
            title=title,
            message=message,
            severity=str(raw_flag.get("severity") or "high"),
            blocking=blocking,
            source=str(raw_flag.get("source") or "family_policy"),
        )

    return red_flags


def _resolve_review_mode(
    case_snapshot: TechnicalCaseStatusSnapshot,
    *,
    autonomy_context: dict[str, Any],
    governance_context: dict[str, Any],
    tenant_entitlements: dict[str, Any],
    red_flags: list[dict[str, Any]],
) -> ReviewMode:
    if not case_snapshot.has_active_report:
        return "none"
    if any(bool(item.get("blocking")) for item in red_flags):
        return "mesa_required"
    requested_mode = _resolve_requested_review_mode(
        autonomy_context=autonomy_context,
        governance_context=governance_context,
    )
    return _downgrade_review_mode(
        requested_mode,
        mobile_review_allowed=bool(tenant_entitlements.get("mobile_review_allowed")),
        mobile_autonomous_allowed=bool(
            tenant_entitlements.get("mobile_autonomous_allowed")
        ),
    )


def _is_tenant_blocked(tenant_policy_context: TenantPolicyCapabilitySnapshot | None) -> bool:
    if tenant_policy_context is None:
        return False
    return str(tenant_policy_context.tenant_status or "").strip().lower() == "blocked"


def _build_tenant_policy_suffix(
    tenant_policy_context: TenantPolicyCapabilitySnapshot | None,
) -> str | None:
    if tenant_policy_context is None:
        return None

    parts = [
        f"tenant_status={tenant_policy_context.tenant_status}",
        f"plan_name={tenant_policy_context.plan_name}",
        f"usage_status={tenant_policy_context.usage_status}",
        f"upload_doc_enabled={tenant_policy_context.upload_doc_enabled}",
        f"deep_research_enabled={tenant_policy_context.deep_research_enabled}",
    ]
    if tenant_policy_context.recommended_plan:
        parts.append(f"recommended_plan={tenant_policy_context.recommended_plan}")
    return "; ".join(parts)


def build_technical_case_policy_decision(
    *,
    banco: Session | None = None,
    case_snapshot: TechnicalCaseStatusSnapshot,
    template_key: Any = None,
    family_key: Any = None,
    variant_key: Any = None,
    laudo_type: Any = None,
    document_type: Any = None,
    tenant_policy_context: TenantPolicyCapabilitySnapshot | None = None,
    report_pack_draft: dict[str, Any] | None = None,
) -> TechnicalCasePolicyDecision:
    tenant_id = str(case_snapshot.tenant_id or "").strip()
    governance_tenant_id = (
        str(getattr(tenant_policy_context, "tenant_id", "") or "").strip() or tenant_id
    )
    case_id = case_snapshot.case_ref.case_id
    resolved_template_key = _normalize_optional_text(template_key)
    resolved_laudo_type = _normalize_optional_text(laudo_type) or resolved_template_key
    resolved_document_type = _normalize_optional_text(document_type) or resolved_template_key
    governance_context = load_case_policy_governance_context(
        banco,
        tenant_id=governance_tenant_id,
        family_key=family_key,
        variant_key=variant_key,
        template_key=resolved_template_key,
    )
    autonomy_context = _resolve_mobile_autonomy_context(
        tenant_id=case_snapshot.tenant_id,
        template_key=resolved_template_key,
        report_pack_draft=report_pack_draft,
    )
    runtime_operational_context = _build_runtime_operational_context(
        banco=banco,
        case_snapshot=case_snapshot,
    )
    tenant_entitlements = _build_tenant_entitlements(
        tenant_policy_context=tenant_policy_context,
        governance_context=governance_context,
        autonomy_context=autonomy_context,
        template_key=resolved_template_key,
    )
    red_flags = _build_red_flags(
        governance_context=governance_context,
        tenant_entitlements=tenant_entitlements,
        autonomy_context=autonomy_context,
        runtime_operational_context=runtime_operational_context,
        template_key=resolved_template_key,
    )
    family_policy_summary = _build_family_policy_summary(governance_context)

    review_mode = _resolve_review_mode(
        case_snapshot,
        autonomy_context=autonomy_context,
        governance_context=governance_context,
        tenant_entitlements=tenant_entitlements,
        red_flags=red_flags,
    )
    review_required = bool(case_snapshot.has_active_report) and review_mode not in {
        "mobile_autonomous",
        "mobile_review_allowed",
    }
    engineer_approval_required = bool(case_snapshot.has_active_report) and review_mode not in {
        "mobile_autonomous",
        "mobile_review_allowed",
    }
    document_materialization_allowed = bool(case_snapshot.has_active_report)
    document_issue_allowed = case_snapshot.canonical_status == "approved"
    tenant_blocked = _is_tenant_blocked(tenant_policy_context)

    if tenant_blocked:
        document_materialization_allowed = False
        document_issue_allowed = False

    review_source = build_default_review_policy_source(
        tenant_id=tenant_id,
        template_key=resolved_template_key,
        tenant_policy_context=tenant_policy_context,
    )
    document_source = build_document_gate_policy_source(
        tenant_id=tenant_id,
        template_key=resolved_template_key,
        tenant_policy_context=tenant_policy_context,
    )
    tenant_policy_suffix = _build_tenant_policy_suffix(tenant_policy_context)

    if not case_snapshot.has_active_report:
        review_rationale = "Sem laudo ativo, a politica minima de revisao nao se aplica."
        document_rationale = "Sem laudo ativo, nao ha materializacao documental nem emissao."
    elif tenant_blocked:
        review_rationale = (
            "A revisao humana segue obrigatoria para o caso ativo, mas o tenant bloqueado impede avancos documentais formais."
        )
        document_rationale = (
            "Tenant bloqueado desabilita materializacao e emissao ate a restricao comercial ser removida."
        )
    elif review_mode == "mobile_autonomous":
        review_rationale = (
            "Report pack incremental da familia allowlisted satisfez os hard gates e liberou autonomia mobile para este caso."
        )
        document_rationale = (
            "Materializacao documental segue permitida e a emissao final depende apenas do fechamento do caso no fluxo autonomo."
        )
    elif review_mode == "mobile_review_allowed":
        review_rationale = (
            "Policy ativa permite revisao e decisao governada no proprio mobile, com escalonamento opcional para a Mesa."
        )
        document_rationale = (
            "Materializacao documental segue permitida e a emissao final depende do comando explicito de aprovacao no fluxo movel."
        )
    else:
        review_rationale = (
            "Fluxo legado ativo exige revisao humana antes do fechamento formal do caso."
        )
        document_rationale = (
            "Materializacao documental segue permitida para o caso ativo, e a emissao continua condicionada ao estado aprovado."
        )

    if document_issue_allowed and not tenant_blocked:
        document_rationale = (
            "Estado canonico aprovado e tenant elegivel permitem emissao potencial sob o gate humano vigente."
        )
    if red_flags:
        review_rationale = (
            f"{review_rationale} [red_flags={len(red_flags)}]"
            if review_rationale
            else f"Red flags ativas={len(red_flags)}."
        )
    if tenant_policy_suffix:
        review_rationale = f"{review_rationale} [{tenant_policy_suffix}]"
        document_rationale = f"{document_rationale} [{tenant_policy_suffix}]"

    primary_source = (
        document_source
        if document_source.policy_source_kind == "tenant"
        else review_source
    )

    review_decision = ReviewRequirementDecision(
        tenant_id=tenant_id,
        case_id=case_id,
        template_key=resolved_template_key,
        laudo_type=resolved_laudo_type,
        review_required=review_required,
        review_mode=review_mode,
        engineer_approval_required=engineer_approval_required,
        policy_source=review_source,
        rationale=review_rationale,
        family_policy_summary=family_policy_summary,
        tenant_entitlements=tenant_entitlements,
        runtime_operational_context=runtime_operational_context,
        red_flags=red_flags,
    )

    document_decision = DocumentMaterializationDecision(
        tenant_id=tenant_id,
        case_id=case_id,
        template_key=resolved_template_key,
        document_type=resolved_document_type,
        document_materialization_allowed=document_materialization_allowed,
        document_issue_allowed=document_issue_allowed,
        policy_source=document_source,
        rationale=document_rationale,
    )

    summary = PolicyDecisionSummary(
        tenant_id=tenant_id,
        case_id=case_id,
        template_key=resolved_template_key,
        laudo_type=resolved_laudo_type,
        document_type=resolved_document_type,
        review_required=review_required,
        review_mode=review_mode,
        engineer_approval_required=engineer_approval_required,
        document_materialization_allowed=document_materialization_allowed,
        document_issue_allowed=document_issue_allowed,
        primary_policy_source_kind=primary_source.policy_source_kind,
        primary_policy_source_id=primary_source.policy_source_id,
        source_summary={
            "review": review_source.model_dump(mode="python"),
            "document": document_source.model_dump(mode="python"),
        },
        rationale=" | ".join(
            part
            for part in (review_rationale, document_rationale)
            if str(part or "").strip()
        ),
        family_policy_summary=family_policy_summary,
        tenant_entitlements=tenant_entitlements,
        runtime_operational_context=runtime_operational_context,
        red_flags=red_flags,
    )

    return TechnicalCasePolicyDecision(
        tenant_id=tenant_id,
        case_id=case_id,
        template_key=resolved_template_key,
        laudo_type=resolved_laudo_type,
        document_type=resolved_document_type,
        review=review_decision,
        document=document_decision,
        summary=summary,
    )


__all__ = ["build_technical_case_policy_decision"]
