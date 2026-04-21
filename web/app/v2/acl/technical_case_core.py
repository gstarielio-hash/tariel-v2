"""ACL inicial do Technical Case Core sobre o legado de laudo."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.database import StatusRevisao
from app.v2.contracts.envelopes import utc_now
from app.v2.contracts.provenance import ContentOriginSummary, OriginKind

TechnicalCaseCanonicalStatus = Literal[
    "draft",
    "collecting_evidence",
    "needs_reviewer",
    "review_feedback_pending",
    "approved",
]
TechnicalCaseLifecycleStatus = Literal[
    "analise_livre",
    "pre_laudo",
    "laudo_em_coleta",
    "aguardando_mesa",
    "em_revisao_mesa",
    "devolvido_para_correcao",
    "aprovado",
    "emitido",
]
TechnicalCaseWorkflowMode = Literal[
    "analise_livre",
    "laudo_guiado",
    "laudo_com_mesa",
]
TechnicalCaseActiveOwnerRole = Literal["inspetor", "mesa", "none"]
TechnicalCaseLifecycleTransitionKind = Literal[
    "analysis",
    "advance",
    "review",
    "approval",
    "correction",
    "reopen",
    "issue",
]
TechnicalCasePreferredSurface = Literal["chat", "mesa", "mobile", "system"]
TechnicalCaseSurfaceAction = Literal[
    "chat_finalize",
    "chat_reopen",
    "mesa_approve",
    "mesa_return",
    "system_issue",
]
TechnicalCaseMobileReviewDecision = Literal[
    "enviar_para_mesa",
    "aprovar_no_mobile",
    "devolver_no_mobile",
]
TechnicalCaseMobileReviewCommand = Literal[
    "enviar_para_mesa",
    "aprovar_no_mobile",
    "devolver_no_mobile",
    "reabrir_bloco",
]

_MOBILE_REVIEW_ACTIONABLE_LIFECYCLE_STATUSES = frozenset(
    {
        "analise_livre",
        "pre_laudo",
        "laudo_em_coleta",
        "devolvido_para_correcao",
    }
)
_MOBILE_REVIEW_APPROVAL_MODES = frozenset(
    {
        "mobile_autonomous",
        "mobile_review_allowed",
    }
)

_CASE_LIFECYCLE_STATUS_LABELS: dict[str, str] = {
    "analise_livre": "Analise livre",
    "pre_laudo": "Pre-laudo",
    "laudo_em_coleta": "Em coleta",
    "aguardando_mesa": "Aguardando mesa",
    "em_revisao_mesa": "Mesa em revisao",
    "devolvido_para_correcao": "Devolvido para correcao",
    "aprovado": "Aprovado",
    "emitido": "Emitido",
}

_ACTIVE_OWNER_ROLE_LABELS: dict[str, str] = {
    "inspetor": "Responsavel: campo",
    "mesa": "Responsavel: mesa",
    "none": "Responsavel: conclusao",
}


class TechnicalCaseRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["TechnicalCaseRefV1"] = "TechnicalCaseRefV1"
    contract_version: str = "v1"
    tenant_id: str
    case_id: str | None = None
    legacy_laudo_id: int | None = None
    thread_id: str | None = None
    document_id: str | None = None
    identity_namespace: Literal["legacy_laudo"] = "legacy_laudo"
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class TechnicalCaseLifecycleTransition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_status: TechnicalCaseLifecycleStatus
    transition_kind: TechnicalCaseLifecycleTransitionKind = "advance"
    label: str
    owner_role: TechnicalCaseActiveOwnerRole = "inspetor"
    preferred_surface: TechnicalCasePreferredSurface = "chat"


class TechnicalCaseStatusSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["TechnicalCaseStatusSnapshotV1"] = "TechnicalCaseStatusSnapshotV1"
    contract_version: str = "v1"
    tenant_id: str
    case_ref: TechnicalCaseRef
    canonical_status: TechnicalCaseCanonicalStatus
    case_lifecycle_status: TechnicalCaseLifecycleStatus = "analise_livre"
    workflow_mode: TechnicalCaseWorkflowMode = "analise_livre"
    active_owner_role: TechnicalCaseActiveOwnerRole = "inspetor"
    allowed_next_lifecycle_statuses: list[TechnicalCaseLifecycleStatus] = Field(
        default_factory=list
    )
    allowed_lifecycle_transitions: list[TechnicalCaseLifecycleTransition] = Field(
        default_factory=list
    )
    allowed_surface_actions: list[TechnicalCaseSurfaceAction] = Field(
        default_factory=list
    )
    human_validation_required: bool = False
    legacy_public_state: str = "sem_relatorio"
    legacy_status_card: str | None = None
    legacy_review_status: str | None = None
    allows_reopen: bool | None = None
    has_active_report: bool = False
    origin_kind: OriginKind = "system"
    content_origin_summary: ContentOriginSummary | None = None
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


def _stringify_tenant_id(value: Any) -> str:
    return str(value or "").strip()


def _normalize_optional_int(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _has_meaningful_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return bool(value)
    return bool(value)


def _normalize_review_status(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, StatusRevisao):
        return value.value
    try:
        return StatusRevisao.normalizar(value)
    except ValueError:
        text = str(value or "").strip()
        return text or None


def _build_namespaced_ref(kind: str, tenant_id: str, legacy_laudo_id: int | None) -> str | None:
    if legacy_laudo_id is None:
        return None
    return f"{kind}:legacy-laudo:{tenant_id}:{legacy_laudo_id}"


def _normalize_entry_mode_effective(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text or None


def _normalize_review_mode(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text or None


def _has_guided_checklist(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    checklist = value.get("checklist")
    return isinstance(checklist, list) and bool(checklist)


def resolve_case_workflow_mode_from_legacy(
    *,
    legacy_review_status: Any = None,
    final_validation_mode: Any = None,
    allows_reopen: bool | None = None,
    has_active_report: bool | None = None,
    entry_mode_effective: Any = None,
    has_guided_checklist: bool = False,
) -> TechnicalCaseWorkflowMode:
    review_status = _normalize_review_status(legacy_review_status) or ""
    review_mode = _normalize_review_mode(final_validation_mode)
    active_report = bool(has_active_report)
    effective_mode = _normalize_entry_mode_effective(entry_mode_effective)

    if review_status in {
        StatusRevisao.AGUARDANDO.value,
        StatusRevisao.REJEITADO.value,
    }:
        return "laudo_com_mesa"
    if review_status == StatusRevisao.APROVADO.value:
        return "laudo_guiado" if review_mode == "mobile_autonomous" else "laudo_com_mesa"
    if bool(allows_reopen):
        return "laudo_guiado" if review_mode == "mobile_autonomous" else "laudo_com_mesa"
    if active_report and (
        has_guided_checklist
        or effective_mode == "evidence_first"
        or review_mode == "mobile_autonomous"
    ):
        return "laudo_guiado"
    return "analise_livre"


def resolve_case_lifecycle_status_from_legacy(
    *,
    legacy_public_state: Any = None,
    legacy_review_status: Any = None,
    allows_reopen: bool | None = None,
    has_active_report: bool | None = None,
    reviewer_id: Any = None,
    entry_mode_effective: Any = None,
    has_form_data: bool = False,
    has_ai_draft: bool = False,
    has_guided_checklist: bool = False,
    has_report_pack_draft: bool = False,
    has_message_history: bool = False,
    has_document_file: bool = False,
    reopened_at: Any = None,
) -> TechnicalCaseLifecycleStatus:
    public_state = str(legacy_public_state or "").strip().lower()
    review_status = _normalize_review_status(legacy_review_status) or ""
    active_report = bool(has_active_report)
    reviewer_present = _normalize_optional_int(reviewer_id) is not None
    effective_mode = _normalize_entry_mode_effective(entry_mode_effective)
    was_reopened = reopened_at is not None

    if not active_report or public_state == "sem_relatorio":
        return "analise_livre"
    if (
        was_reopened
        or review_status == StatusRevisao.REJEITADO.value
        or public_state == "ajustes"
    ):
        return "devolvido_para_correcao"
    if has_document_file:
        return "emitido"
    if review_status == StatusRevisao.APROVADO.value or public_state == "aprovado":
        return "aprovado"
    if review_status == StatusRevisao.AGUARDANDO.value or public_state == "aguardando":
        return "em_revisao_mesa" if reviewer_present else "aguardando_mesa"
    if has_guided_checklist or has_form_data or has_message_history or effective_mode == "evidence_first":
        return "laudo_em_coleta"
    if has_ai_draft or has_report_pack_draft:
        return "pre_laudo"
    return "pre_laudo"


def resolve_active_owner_role_from_lifecycle(
    lifecycle_status: TechnicalCaseLifecycleStatus,
) -> TechnicalCaseActiveOwnerRole:
    if lifecycle_status in {"aguardando_mesa", "em_revisao_mesa"}:
        return "mesa"
    if lifecycle_status in {"aprovado", "emitido"}:
        return "none"
    return "inspetor"


def resolve_allowed_next_lifecycle_statuses(
    *,
    lifecycle_status: TechnicalCaseLifecycleStatus,
    workflow_mode: TechnicalCaseWorkflowMode,
) -> list[TechnicalCaseLifecycleStatus]:
    base_matrix: dict[TechnicalCaseLifecycleStatus, list[TechnicalCaseLifecycleStatus]] = {
        "analise_livre": ["pre_laudo", "laudo_em_coleta"],
        "pre_laudo": ["analise_livre", "laudo_em_coleta"],
        "laudo_em_coleta": ["aguardando_mesa", "aprovado"],
        "aguardando_mesa": ["em_revisao_mesa", "devolvido_para_correcao", "aprovado"],
        "em_revisao_mesa": ["devolvido_para_correcao", "aprovado"],
        "devolvido_para_correcao": ["laudo_em_coleta", "aguardando_mesa"],
        "aprovado": ["emitido", "devolvido_para_correcao"],
        "emitido": ["devolvido_para_correcao"],
    }
    allowed = list(base_matrix.get(lifecycle_status, []))
    if workflow_mode == "laudo_com_mesa" and lifecycle_status == "laudo_em_coleta":
        return ["aguardando_mesa"]
    return allowed


def resolve_allowed_lifecycle_transitions(
    *,
    lifecycle_status: TechnicalCaseLifecycleStatus,
    workflow_mode: TechnicalCaseWorkflowMode,
) -> list[TechnicalCaseLifecycleTransition]:
    transitions: list[TechnicalCaseLifecycleTransition] = []
    for target_status in resolve_allowed_next_lifecycle_statuses(
        lifecycle_status=lifecycle_status,
        workflow_mode=workflow_mode,
    ):
        transition_kind: TechnicalCaseLifecycleTransitionKind = "advance"
        label = "Atualizar estado do caso"
        preferred_surface: TechnicalCasePreferredSurface = "chat"

        if lifecycle_status == "analise_livre" and target_status == "pre_laudo":
            transition_kind = "analysis"
            label = "Preparar pre-laudo"
        elif lifecycle_status == "analise_livre" and target_status == "laudo_em_coleta":
            transition_kind = "advance"
            label = "Iniciar laudo guiado"
        elif lifecycle_status == "pre_laudo" and target_status == "analise_livre":
            transition_kind = "analysis"
            label = "Voltar para analise livre"
        elif lifecycle_status == "pre_laudo" and target_status == "laudo_em_coleta":
            transition_kind = "advance"
            label = "Entrar em laudo guiado"
        elif lifecycle_status == "laudo_em_coleta" and target_status == "aguardando_mesa":
            transition_kind = "review"
            label = "Enviar para mesa"
        elif lifecycle_status == "laudo_em_coleta" and target_status == "aprovado":
            transition_kind = "approval"
            label = "Finalizar sem mesa"
        elif lifecycle_status == "aguardando_mesa" and target_status == "em_revisao_mesa":
            transition_kind = "review"
            label = "Assumir revisao da mesa"
            preferred_surface = "mesa"
        elif (
            lifecycle_status in {"aguardando_mesa", "em_revisao_mesa"}
            and target_status == "devolvido_para_correcao"
        ):
            transition_kind = "correction"
            label = "Devolver para correcao"
            preferred_surface = "mesa"
        elif (
            lifecycle_status in {"aguardando_mesa", "em_revisao_mesa"}
            and target_status == "aprovado"
        ):
            transition_kind = "approval"
            label = "Aprovar caso"
            preferred_surface = "mesa"
        elif (
            lifecycle_status == "devolvido_para_correcao"
            and target_status == "laudo_em_coleta"
        ):
            transition_kind = "advance"
            label = "Retomar laudo guiado"
        elif (
            lifecycle_status == "devolvido_para_correcao"
            and target_status == "aguardando_mesa"
        ):
            transition_kind = "review"
            label = "Reenviar para mesa"
        elif lifecycle_status == "aprovado" and target_status == "emitido":
            transition_kind = "issue"
            label = "Emitir PDF final"
            preferred_surface = "system"
        elif (
            lifecycle_status in {"aprovado", "emitido"}
            and target_status == "devolvido_para_correcao"
        ):
            transition_kind = "reopen"
            label = (
                "Reabrir caso emitido"
                if lifecycle_status == "emitido"
                else "Reabrir para correcao"
            )

        transitions.append(
            TechnicalCaseLifecycleTransition(
                target_status=target_status,
                transition_kind=transition_kind,
                label=label,
                owner_role=resolve_active_owner_role_from_lifecycle(target_status),
                preferred_surface=preferred_surface,
            )
        )
    return transitions


def resolve_allowed_surface_actions(
    *,
    lifecycle_status: TechnicalCaseLifecycleStatus,
    workflow_mode: TechnicalCaseWorkflowMode,
) -> list[TechnicalCaseSurfaceAction]:
    transitions = resolve_allowed_lifecycle_transitions(
        lifecycle_status=lifecycle_status,
        workflow_mode=workflow_mode,
    )
    target_statuses = {item.target_status for item in transitions}
    actions: list[TechnicalCaseSurfaceAction] = []

    if lifecycle_status in {"laudo_em_coleta", "devolvido_para_correcao"} and (
        "aguardando_mesa" in target_statuses or "aprovado" in target_statuses
    ):
        actions.append("chat_finalize")
    if lifecycle_status in {"aprovado", "emitido"} and "devolvido_para_correcao" in target_statuses:
        actions.append("chat_reopen")
    if lifecycle_status in {"aguardando_mesa", "em_revisao_mesa"} and "aprovado" in target_statuses:
        actions.append("mesa_approve")
    if lifecycle_status in {"aguardando_mesa", "em_revisao_mesa"} and "devolvido_para_correcao" in target_statuses:
        actions.append("mesa_return")
    if lifecycle_status == "aprovado" and "emitido" in target_statuses:
        actions.append("system_issue")
    return actions


def humanize_case_lifecycle_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return _CASE_LIFECYCLE_STATUS_LABELS.get(normalized, "")


def humanize_active_owner_role(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return _ACTIVE_OWNER_ROLE_LABELS.get(normalized, "")


def build_case_status_visual_label(
    *,
    lifecycle_status: Any,
    active_owner_role: Any,
) -> str:
    lifecycle_label = humanize_case_lifecycle_status(lifecycle_status)
    owner_label = humanize_active_owner_role(active_owner_role)
    if lifecycle_label and owner_label:
        return f"{lifecycle_label} / {owner_label}"
    return lifecycle_label or owner_label


def resolve_allowed_mobile_review_decisions(
    *,
    lifecycle_status: TechnicalCaseLifecycleStatus,
    allows_edit: bool = False,
    review_mode: Any = None,
    allow_approval_when_review_mode_unresolved: bool = False,
) -> list[TechnicalCaseMobileReviewDecision]:
    if not allows_edit or lifecycle_status not in _MOBILE_REVIEW_ACTIONABLE_LIFECYCLE_STATUSES:
        return []

    allowed: list[TechnicalCaseMobileReviewDecision] = [
        "enviar_para_mesa",
        "devolver_no_mobile",
    ]
    normalized_review_mode = _normalize_review_mode(review_mode)
    if normalized_review_mode in _MOBILE_REVIEW_APPROVAL_MODES or (
        allow_approval_when_review_mode_unresolved and normalized_review_mode is None
    ):
        allowed.insert(0, "aprovar_no_mobile")
    return allowed


def resolve_supports_mobile_block_reopen(
    *,
    lifecycle_status: TechnicalCaseLifecycleStatus,
    allows_edit: bool = False,
    has_block_review_items: bool = False,
) -> bool:
    return bool(
        allows_edit
        and has_block_review_items
        and lifecycle_status in _MOBILE_REVIEW_ACTIONABLE_LIFECYCLE_STATUSES
    )


def is_mobile_review_command_allowed(
    *,
    lifecycle_status: TechnicalCaseLifecycleStatus,
    allows_edit: bool = False,
    review_mode: Any = None,
    command: TechnicalCaseMobileReviewCommand,
    has_block_review_items: bool = False,
    allow_approval_when_review_mode_unresolved: bool = False,
) -> bool:
    if command == "reabrir_bloco":
        return resolve_supports_mobile_block_reopen(
            lifecycle_status=lifecycle_status,
            allows_edit=allows_edit,
            has_block_review_items=has_block_review_items,
        )
    return command in resolve_allowed_mobile_review_decisions(
        lifecycle_status=lifecycle_status,
        allows_edit=allows_edit,
        review_mode=review_mode,
        allow_approval_when_review_mode_unresolved=allow_approval_when_review_mode_unresolved,
    )


def build_technical_case_ref_from_legacy_laudo(
    *,
    tenant_id: Any,
    legacy_laudo_id: Any,
    correlation_id: str | None = None,
    timestamp: datetime | None = None,
) -> TechnicalCaseRef:
    tenant_text = _stringify_tenant_id(tenant_id)
    legacy_laudo_id_int = _normalize_optional_int(legacy_laudo_id)

    return TechnicalCaseRef(
        tenant_id=tenant_text,
        case_id=_build_namespaced_ref("case", tenant_text, legacy_laudo_id_int),
        legacy_laudo_id=legacy_laudo_id_int,
        thread_id=_build_namespaced_ref("thread", tenant_text, legacy_laudo_id_int),
        document_id=_build_namespaced_ref("document", tenant_text, legacy_laudo_id_int),
        correlation_id=correlation_id,
        timestamp=timestamp or utc_now(),
    )


def resolve_canonical_case_status_from_legacy(
    *,
    legacy_public_state: Any = None,
    legacy_review_status: Any = None,
    allows_reopen: bool | None = None,
    has_active_report: bool | None = None,
) -> TechnicalCaseCanonicalStatus:
    public_state = str(legacy_public_state or "").strip().lower()
    review_status = _normalize_review_status(legacy_review_status) or ""
    active_report = bool(has_active_report)

    if not active_report or public_state == "sem_relatorio":
        return "draft"
    if review_status == StatusRevisao.APROVADO.value or public_state == "aprovado":
        return "approved"
    if (
        review_status == StatusRevisao.REJEITADO.value
        or public_state == "ajustes"
        or bool(allows_reopen)
    ):
        return "review_feedback_pending"
    if review_status == StatusRevisao.AGUARDANDO.value or public_state == "aguardando":
        return "needs_reviewer"
    return "collecting_evidence"


def build_technical_case_status_snapshot_from_legacy(
    *,
    tenant_id: Any,
    legacy_payload: dict[str, Any],
    laudo: Any | None = None,
    content_origin_summary: ContentOriginSummary | None = None,
    correlation_id: str | None = None,
    timestamp: datetime | None = None,
) -> TechnicalCaseStatusSnapshot:
    tenant_text = _stringify_tenant_id(tenant_id)
    snapshot_timestamp = timestamp or utc_now()
    resolved_correlation_id = correlation_id or uuid.uuid4().hex

    laudo_card = legacy_payload.get("laudo_card")
    laudo_card_payload = laudo_card if isinstance(laudo_card, dict) else {}

    legacy_laudo_id = _normalize_optional_int(
        legacy_payload.get("laudo_id") or getattr(laudo, "id", None),
    )
    legacy_public_state = str(legacy_payload.get("estado") or "sem_relatorio")
    legacy_status_card = str(
        legacy_payload.get("status_card")
        or laudo_card_payload.get("status_card")
        or ""
    ).strip() or None
    legacy_review_status = _normalize_review_status(
        getattr(laudo, "status_revisao", None)
        or laudo_card_payload.get("status_revisao")
    )
    allows_reopen = legacy_payload.get("permite_reabrir")
    if allows_reopen is None and "permite_reabrir" in laudo_card_payload:
        allows_reopen = bool(laudo_card_payload.get("permite_reabrir"))
    has_active_report = bool(legacy_laudo_id)
    reviewer_id = _normalize_optional_int(getattr(laudo, "revisado_por", None))
    entry_mode_effective = _normalize_entry_mode_effective(
        getattr(laudo, "entry_mode_effective", None)
    )
    has_form_data = _has_meaningful_content(getattr(laudo, "dados_formulario", None))
    has_ai_draft = _has_meaningful_content(getattr(laudo, "parecer_ia", None))
    has_guided_checklist = _has_guided_checklist(
        getattr(laudo, "guided_inspection_draft_json", None)
    )
    has_message_history = bool(legacy_payload.get("has_message_history"))
    report_pack_draft = getattr(laudo, "report_pack_draft_json", None)
    has_report_pack_draft = _has_meaningful_content(report_pack_draft)
    report_pack_quality_gates = (
        report_pack_draft.get("quality_gates")
        if isinstance(report_pack_draft, dict)
        else None
    )
    final_validation_mode = _normalize_review_mode(
        report_pack_quality_gates.get("final_validation_mode")
        if isinstance(report_pack_quality_gates, dict)
        else None
    )
    has_document_file = bool(
        _normalize_optional_text(getattr(laudo, "nome_arquivo_pdf", None))
    )
    lifecycle_status = resolve_case_lifecycle_status_from_legacy(
        legacy_public_state=legacy_public_state,
        legacy_review_status=legacy_review_status,
        allows_reopen=bool(allows_reopen) if allows_reopen is not None else None,
        has_active_report=has_active_report,
        reviewer_id=reviewer_id,
        entry_mode_effective=entry_mode_effective,
        has_form_data=has_form_data,
        has_ai_draft=has_ai_draft,
        has_guided_checklist=has_guided_checklist,
        has_report_pack_draft=has_report_pack_draft,
        has_message_history=has_message_history,
        has_document_file=has_document_file,
        reopened_at=getattr(laudo, "reaberto_em", None),
    )
    workflow_mode = resolve_case_workflow_mode_from_legacy(
        legacy_review_status=legacy_review_status,
        final_validation_mode=final_validation_mode,
        allows_reopen=bool(allows_reopen) if allows_reopen is not None else None,
        has_active_report=has_active_report,
        entry_mode_effective=entry_mode_effective,
        has_guided_checklist=has_guided_checklist,
    )

    case_ref = build_technical_case_ref_from_legacy_laudo(
        tenant_id=tenant_text,
        legacy_laudo_id=legacy_laudo_id,
        correlation_id=resolved_correlation_id,
        timestamp=snapshot_timestamp,
    )
    allowed_next_lifecycle_statuses = resolve_allowed_next_lifecycle_statuses(
        lifecycle_status=lifecycle_status,
        workflow_mode=workflow_mode,
    )
    allowed_lifecycle_transitions = resolve_allowed_lifecycle_transitions(
        lifecycle_status=lifecycle_status,
        workflow_mode=workflow_mode,
    )

    return TechnicalCaseStatusSnapshot(
        tenant_id=tenant_text,
        case_ref=case_ref,
        canonical_status=resolve_canonical_case_status_from_legacy(
            legacy_public_state=legacy_public_state,
            legacy_review_status=legacy_review_status,
            allows_reopen=bool(allows_reopen) if allows_reopen is not None else None,
            has_active_report=has_active_report,
        ),
        case_lifecycle_status=lifecycle_status,
        workflow_mode=workflow_mode,
        active_owner_role=resolve_active_owner_role_from_lifecycle(lifecycle_status),
        allowed_next_lifecycle_statuses=allowed_next_lifecycle_statuses,
        allowed_lifecycle_transitions=allowed_lifecycle_transitions,
        allowed_surface_actions=resolve_allowed_surface_actions(
            lifecycle_status=lifecycle_status,
            workflow_mode=workflow_mode,
        ),
        human_validation_required=has_active_report,
        legacy_public_state=legacy_public_state,
        legacy_status_card=legacy_status_card,
        legacy_review_status=legacy_review_status,
        allows_reopen=bool(allows_reopen) if allows_reopen is not None else None,
        has_active_report=has_active_report,
        content_origin_summary=content_origin_summary,
        correlation_id=resolved_correlation_id,
        timestamp=snapshot_timestamp,
    )


def build_technical_case_status_snapshot_for_user(
    *,
    usuario: Any,
    legacy_payload: dict[str, Any],
    laudo: Any | None = None,
    content_origin_summary: ContentOriginSummary | None = None,
    correlation_id: str | None = None,
    timestamp: datetime | None = None,
) -> TechnicalCaseStatusSnapshot:
    return build_technical_case_status_snapshot_from_legacy(
        tenant_id=getattr(usuario, "empresa_id", ""),
        legacy_payload=legacy_payload,
        laudo=laudo,
        content_origin_summary=content_origin_summary,
        correlation_id=correlation_id,
        timestamp=timestamp,
    )


__all__ = [
    "TechnicalCaseActiveOwnerRole",
    "TechnicalCaseCanonicalStatus",
    "TechnicalCaseLifecycleTransition",
    "TechnicalCaseLifecycleTransitionKind",
    "TechnicalCaseLifecycleStatus",
    "TechnicalCaseMobileReviewCommand",
    "TechnicalCaseMobileReviewDecision",
    "TechnicalCasePreferredSurface",
    "TechnicalCaseRef",
    "TechnicalCaseSurfaceAction",
    "TechnicalCaseStatusSnapshot",
    "TechnicalCaseWorkflowMode",
    "build_technical_case_ref_from_legacy_laudo",
    "build_case_status_visual_label",
    "build_technical_case_status_snapshot_for_user",
    "build_technical_case_status_snapshot_from_legacy",
    "humanize_active_owner_role",
    "humanize_case_lifecycle_status",
    "is_mobile_review_command_allowed",
    "resolve_allowed_lifecycle_transitions",
    "resolve_active_owner_role_from_lifecycle",
    "resolve_allowed_next_lifecycle_statuses",
    "resolve_allowed_mobile_review_decisions",
    "resolve_allowed_surface_actions",
    "resolve_case_lifecycle_status_from_legacy",
    "resolve_case_workflow_mode_from_legacy",
    "resolve_canonical_case_status_from_legacy",
    "resolve_supports_mobile_block_reopen",
]
