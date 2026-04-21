"""Snapshot canonico rico do caso tecnico sobre o legado de laudo."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.database import NivelAcesso, StatusRevisao
from app.v2.acl.technical_case_core import (
    TechnicalCaseActiveOwnerRole,
    TechnicalCaseLifecycleTransition,
    TechnicalCaseLifecycleStatus,
    TechnicalCaseRef,
    TechnicalCaseSurfaceAction,
    TechnicalCaseStatusSnapshot,
    TechnicalCaseWorkflowMode,
    build_technical_case_status_snapshot_for_user,
    build_technical_case_status_snapshot_from_legacy,
)
from app.v2.contracts.envelopes import utc_now
from app.v2.contracts.provenance import ContentOriginSummary, OriginKind

TechnicalCaseState = Literal[
    "draft",
    "collecting_evidence",
    "ai_draft_ready",
    "needs_reviewer",
    "review_in_progress",
    "review_feedback_pending",
    "approved",
    "issued",
    "reopened",
    "archived",
]
TechnicalCaseReviewState = Literal[
    "not_requested",
    "pending_review",
    "in_review",
    "approved",
    "rejected",
    "sent_back_for_adjustment",
]
TechnicalCaseDocumentState = Literal[
    "not_started",
    "draft_document",
    "partially_filled",
    "awaiting_approval",
    "approved_for_issue",
    "issued",
    "reopened",
]
TechnicalCaseEngineerApprovalState = Literal[
    "not_required",
    "required",
    "awaiting_engineer",
    "approved",
    "rejected",
]
TechnicalCaseSensitivityLevel = Literal[
    "technical_raw",
    "technical_structured",
    "review_internal",
    "documentary_working",
    "documentary_final",
    "administrative",
    "billing_restricted",
]
TechnicalCaseVisibilityScope = Literal[
    "tenant_technical_full",
    "tenant_technical_summary",
    "tenant_documental_restricted",
    "tenant_admin_summary",
    "platform_admin_aggregate",
    "exceptional_scoped_access",
]
TechnicalCaseOrigin = Literal[
    "inspector_web",
    "review_web",
    "admin_cliente_web",
    "admin_geral_web",
    "android",
    "system",
]


class TechnicalCaseLegacyRefsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["TechnicalCaseLegacyRefsV1"] = "TechnicalCaseLegacyRefsV1"
    contract_version: str = "v1"
    legacy_laudo_id: int | None = None
    legacy_public_state: str | None = None
    legacy_status_card: str | None = None
    legacy_status_revisao: str | None = None
    legacy_reabertura_pendente: bool | None = None
    legacy_reaberto_em: datetime | None = None
    legacy_reviewer_id: int | None = None
    legacy_thread_ref: str | None = None
    legacy_document_ref: str | None = None
    legacy_document_version_number: int | None = None
    legacy_pdf_file_name: str | None = None


class TechnicalCaseSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["TechnicalCaseSnapshotV1"] = "TechnicalCaseSnapshotV1"
    contract_version: str = "v1"
    tenant_id: str
    case_ref: TechnicalCaseRef
    case_state: TechnicalCaseState
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
    case_origin: TechnicalCaseOrigin = "system"
    responsible_inspector_id: int | None = None
    responsible_reviewer_id: int | None = None
    current_review_state: TechnicalCaseReviewState
    current_document_state: TechnicalCaseDocumentState
    current_engineer_approval_state: TechnicalCaseEngineerApprovalState | None = None
    human_validation_required: bool = False
    main_thread_id: str | None = None
    active_laudo_id: int | None = None
    active_document_version_id: str | None = None
    latest_document_version_number: int | None = None
    review_cycle_id: str | None = None
    sensitivity_level: TechnicalCaseSensitivityLevel = "technical_structured"
    visibility_scope: TechnicalCaseVisibilityScope = "tenant_technical_full"
    policy_snapshot_ref: str | None = None
    legacy_refs: TechnicalCaseLegacyRefsV1
    divergence_flags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    source_channel: str | None = None
    origin_kind: OriginKind = "system"
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


def _normalize_optional_int(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_datetime(value: Any) -> datetime | None:
    return value if isinstance(value, datetime) else None


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


def _iter_revisoes(value: Any) -> Iterable[Any]:
    if value is None:
        return ()
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return value
    return tuple(value)


def _resolve_latest_revision(revisoes: Any) -> Any | None:
    ordered = sorted(
        _iter_revisoes(revisoes),
        key=lambda item: (
            _normalize_optional_int(getattr(item, "numero_versao", None)) or 0,
            _normalize_optional_int(getattr(item, "id", None)) or 0,
        ),
    )
    return ordered[-1] if ordered else None


def _build_document_version_ref(
    *,
    tenant_id: str,
    legacy_laudo_id: int | None,
    version_number: int | None,
) -> str | None:
    if legacy_laudo_id is None or version_number is None:
        return None
    return f"document-version:legacy-laudo:{tenant_id}:{legacy_laudo_id}:{version_number}"


def _resolve_case_origin(source_channel: Any) -> TechnicalCaseOrigin:
    channel = str(source_channel or "").strip().lower()
    if "admin_cliente" in channel or "cliente" in channel:
        return "admin_cliente_web"
    if "admin_geral" in channel or channel.startswith("admin") or "admin_ceo" in channel:
        return "admin_geral_web"
    if "review" in channel or "mesa" in channel or "revisor" in channel:
        return "review_web"
    if "android" in channel or "mobile" in channel:
        return "android"
    if "web" in channel or "app" in channel or "inspetor" in channel:
        return "inspector_web"
    return "system"


def _resolve_visibility_scope(
    *,
    actor_access_level: Any,
    case_origin: TechnicalCaseOrigin,
) -> TechnicalCaseVisibilityScope:
    nivel = _normalize_optional_int(actor_access_level)
    if case_origin == "admin_geral_web" or nivel == int(NivelAcesso.DIRETORIA):
        return "platform_admin_aggregate"
    if case_origin == "admin_cliente_web" or nivel == int(NivelAcesso.ADMIN_CLIENTE):
        return "tenant_admin_summary"
    if case_origin == "android":
        return "tenant_technical_summary"
    return "tenant_technical_full"


def _resolve_review_state(
    *,
    case_status_snapshot: TechnicalCaseStatusSnapshot,
    reviewer_id: int | None,
) -> TechnicalCaseReviewState:
    if not case_status_snapshot.has_active_report:
        return "not_requested"

    if isinstance(case_status_snapshot.legacy_review_status, StatusRevisao):
        legacy_review_status = case_status_snapshot.legacy_review_status.value
    else:
        try:
            legacy_review_status = StatusRevisao.normalizar(case_status_snapshot.legacy_review_status)
        except ValueError:
            legacy_review_status = str(case_status_snapshot.legacy_review_status or "").strip()
    if legacy_review_status == StatusRevisao.APROVADO.value:
        return "approved"
    if legacy_review_status == StatusRevisao.REJEITADO.value or bool(case_status_snapshot.allows_reopen):
        return "sent_back_for_adjustment"
    if legacy_review_status == StatusRevisao.AGUARDANDO.value:
        return "in_review" if reviewer_id is not None else "pending_review"
    return "not_requested"


def _resolve_document_state(
    *,
    case_status_snapshot: TechnicalCaseStatusSnapshot,
    review_state: TechnicalCaseReviewState,
    has_form_data: bool,
    has_ai_draft: bool,
    has_document_file: bool,
    has_revision_history: bool,
    reopened_at: datetime | None,
) -> TechnicalCaseDocumentState:
    if not case_status_snapshot.has_active_report:
        return "not_started"
    if reopened_at is not None:
        return "reopened"
    if has_document_file:
        return "issued"
    if review_state == "approved":
        return "approved_for_issue"
    if review_state in {"pending_review", "in_review"}:
        return "awaiting_approval"
    if has_form_data or has_ai_draft or has_revision_history:
        return "partially_filled"
    return "draft_document"


def _resolve_case_state(
    *,
    case_status_snapshot: TechnicalCaseStatusSnapshot,
    review_state: TechnicalCaseReviewState,
    has_form_data: bool,
    has_ai_draft: bool,
    has_document_file: bool,
    reopened_at: datetime | None,
) -> TechnicalCaseState:
    if reopened_at is not None:
        return "reopened"
    if has_document_file:
        return "issued"
    if review_state == "in_review":
        return "review_in_progress"
    if (
        case_status_snapshot.canonical_status == "collecting_evidence"
        and has_ai_draft
        and not has_form_data
    ):
        return "ai_draft_ready"
    return case_status_snapshot.canonical_status


def _resolve_engineer_approval_state(
    *,
    case_status_snapshot: TechnicalCaseStatusSnapshot,
    review_state: TechnicalCaseReviewState,
) -> TechnicalCaseEngineerApprovalState:
    if not case_status_snapshot.has_active_report:
        return "not_required"
    if review_state == "approved":
        return "approved"
    if review_state == "sent_back_for_adjustment":
        return "rejected"
    if review_state in {"pending_review", "in_review"}:
        return "awaiting_engineer"
    return "required"


def _resolve_sensitivity_level(
    *,
    visibility_scope: TechnicalCaseVisibilityScope,
    review_state: TechnicalCaseReviewState,
    document_state: TechnicalCaseDocumentState,
    has_form_data: bool,
    has_ai_draft: bool,
    has_revision_history: bool,
) -> TechnicalCaseSensitivityLevel:
    if visibility_scope in {"tenant_admin_summary", "platform_admin_aggregate"}:
        return "administrative"
    if document_state == "issued":
        return "documentary_final"
    if document_state in {"reopened", "approved_for_issue", "awaiting_approval"} or has_revision_history:
        return "documentary_working"
    if review_state in {"pending_review", "in_review", "approved", "sent_back_for_adjustment"}:
        return "review_internal"
    if has_form_data or has_ai_draft:
        return "technical_structured"
    return "technical_raw"


def _collect_divergence_flags(
    *,
    reviewer_id: int | None,
    latest_revision_number: int | None,
    has_document_file: bool,
    reopened_at: datetime | None,
    has_pending_reopen: bool,
) -> list[str]:
    flags: list[str] = []
    if reviewer_id is not None and has_pending_reopen:
        flags.append("legacy_review_cycle_still_implicit")
    if has_document_file and latest_revision_number is None:
        flags.append("legacy_document_issued_without_revision_history")
    if reopened_at is not None:
        flags.append("legacy_reopen_cycle_not_explicit")
    return flags


def build_technical_case_snapshot_from_case_status(
    *,
    case_status_snapshot: TechnicalCaseStatusSnapshot,
    laudo: Any,
    source_channel: str,
    actor_access_level: Any = None,
    policy_snapshot_ref: str | None = None,
    timestamp: datetime | None = None,
) -> TechnicalCaseSnapshotV1:
    case_ref = case_status_snapshot.case_ref
    legacy_laudo_id = case_ref.legacy_laudo_id
    if legacy_laudo_id is None:
        raise ValueError("Technical case snapshot exige legacy_laudo_id valido.")

    tenant_id = str(case_status_snapshot.tenant_id or "").strip()
    resolved_timestamp = timestamp or utc_now()
    reviewer_id = _normalize_optional_int(getattr(laudo, "revisado_por", None))
    responsible_inspector_id = _normalize_optional_int(getattr(laudo, "usuario_id", None))
    latest_revision = _resolve_latest_revision(getattr(laudo, "revisoes", None))
    latest_revision_number = _normalize_optional_int(getattr(latest_revision, "numero_versao", None))
    reopened_at = _normalize_datetime(getattr(laudo, "reaberto_em", None))
    has_pending_reopen = _normalize_datetime(getattr(laudo, "reabertura_pendente_em", None)) is not None
    has_form_data = _has_meaningful_content(getattr(laudo, "dados_formulario", None))
    has_ai_draft = _has_meaningful_content(getattr(laudo, "parecer_ia", None))
    has_document_file = bool(_normalize_optional_text(getattr(laudo, "nome_arquivo_pdf", None)))
    has_revision_history = latest_revision_number is not None
    case_origin = _resolve_case_origin(source_channel)
    visibility_scope = _resolve_visibility_scope(
        actor_access_level=actor_access_level,
        case_origin=case_origin,
    )
    review_state = _resolve_review_state(
        case_status_snapshot=case_status_snapshot,
        reviewer_id=reviewer_id,
    )
    document_state = _resolve_document_state(
        case_status_snapshot=case_status_snapshot,
        review_state=review_state,
        has_form_data=has_form_data,
        has_ai_draft=has_ai_draft,
        has_document_file=has_document_file,
        has_revision_history=has_revision_history,
        reopened_at=reopened_at,
    )
    case_state = _resolve_case_state(
        case_status_snapshot=case_status_snapshot,
        review_state=review_state,
        has_form_data=has_form_data,
        has_ai_draft=has_ai_draft,
        has_document_file=has_document_file,
        reopened_at=reopened_at,
    )
    engineer_approval_state = _resolve_engineer_approval_state(
        case_status_snapshot=case_status_snapshot,
        review_state=review_state,
    )
    sensitivity_level = _resolve_sensitivity_level(
        visibility_scope=visibility_scope,
        review_state=review_state,
        document_state=document_state,
        has_form_data=has_form_data,
        has_ai_draft=has_ai_draft,
        has_revision_history=has_revision_history,
    )
    active_document_version_id = _build_document_version_ref(
        tenant_id=tenant_id,
        legacy_laudo_id=legacy_laudo_id,
        version_number=latest_revision_number,
    )

    return TechnicalCaseSnapshotV1(
        tenant_id=tenant_id,
        case_ref=case_ref,
        case_state=case_state,
        case_lifecycle_status=case_status_snapshot.case_lifecycle_status,
        workflow_mode=case_status_snapshot.workflow_mode,
        active_owner_role=case_status_snapshot.active_owner_role,
        allowed_next_lifecycle_statuses=list(
            case_status_snapshot.allowed_next_lifecycle_statuses
        ),
        allowed_lifecycle_transitions=list(
            case_status_snapshot.allowed_lifecycle_transitions
        ),
        allowed_surface_actions=list(case_status_snapshot.allowed_surface_actions),
        case_origin=case_origin,
        responsible_inspector_id=responsible_inspector_id,
        responsible_reviewer_id=reviewer_id,
        current_review_state=review_state,
        current_document_state=document_state,
        current_engineer_approval_state=engineer_approval_state,
        human_validation_required=case_status_snapshot.human_validation_required,
        main_thread_id=case_ref.thread_id,
        active_laudo_id=legacy_laudo_id,
        active_document_version_id=active_document_version_id,
        latest_document_version_number=latest_revision_number,
        review_cycle_id=None,
        sensitivity_level=sensitivity_level,
        visibility_scope=visibility_scope,
        policy_snapshot_ref=_normalize_optional_text(policy_snapshot_ref),
        legacy_refs=TechnicalCaseLegacyRefsV1(
            legacy_laudo_id=legacy_laudo_id,
            legacy_public_state=case_status_snapshot.legacy_public_state,
            legacy_status_card=case_status_snapshot.legacy_status_card,
            legacy_status_revisao=case_status_snapshot.legacy_review_status,
            legacy_reabertura_pendente=has_pending_reopen,
            legacy_reaberto_em=reopened_at,
            legacy_reviewer_id=reviewer_id,
            legacy_thread_ref=f"mensagens_laudo:laudo_id:{legacy_laudo_id}",
            legacy_document_ref=(
                f"laudo_revisoes:laudo_id:{legacy_laudo_id}"
                if has_revision_history
                else (
                    f"laudos:nome_arquivo_pdf:{legacy_laudo_id}"
                    if has_document_file
                    else None
                )
            ),
            legacy_document_version_number=latest_revision_number,
            legacy_pdf_file_name=_normalize_optional_text(getattr(laudo, "nome_arquivo_pdf", None)),
        ),
        divergence_flags=_collect_divergence_flags(
            reviewer_id=reviewer_id,
            latest_revision_number=latest_revision_number,
            has_document_file=has_document_file,
            reopened_at=reopened_at,
            has_pending_reopen=has_pending_reopen,
        ),
        created_at=_normalize_datetime(getattr(laudo, "criado_em", None)) or resolved_timestamp,
        updated_at=(
            _normalize_datetime(getattr(laudo, "atualizado_em", None))
            or _normalize_datetime(getattr(laudo, "criado_em", None))
            or resolved_timestamp
        ),
        source_channel=_normalize_optional_text(source_channel),
        origin_kind=case_status_snapshot.origin_kind,
        correlation_id=case_status_snapshot.correlation_id,
        timestamp=resolved_timestamp,
    )


def build_technical_case_snapshot_from_legacy(
    *,
    tenant_id: Any,
    legacy_payload: dict[str, Any],
    laudo: Any,
    source_channel: str,
    actor_access_level: Any = None,
    content_origin_summary: ContentOriginSummary | None = None,
    correlation_id: str | None = None,
    policy_snapshot_ref: str | None = None,
    timestamp: datetime | None = None,
) -> TechnicalCaseSnapshotV1:
    case_status_snapshot = build_technical_case_status_snapshot_from_legacy(
        tenant_id=tenant_id,
        legacy_payload=legacy_payload,
        laudo=laudo,
        content_origin_summary=content_origin_summary,
        correlation_id=correlation_id,
        timestamp=timestamp,
    )
    return build_technical_case_snapshot_from_case_status(
        case_status_snapshot=case_status_snapshot,
        laudo=laudo,
        source_channel=source_channel,
        actor_access_level=actor_access_level,
        policy_snapshot_ref=policy_snapshot_ref,
        timestamp=timestamp,
    )


def build_technical_case_snapshot_for_user(
    *,
    usuario: Any,
    legacy_payload: dict[str, Any],
    laudo: Any,
    source_channel: str,
    content_origin_summary: ContentOriginSummary | None = None,
    correlation_id: str | None = None,
    policy_snapshot_ref: str | None = None,
    timestamp: datetime | None = None,
) -> TechnicalCaseSnapshotV1:
    case_status_snapshot = build_technical_case_status_snapshot_for_user(
        usuario=usuario,
        legacy_payload=legacy_payload,
        laudo=laudo,
        content_origin_summary=content_origin_summary,
        correlation_id=correlation_id,
        timestamp=timestamp,
    )
    return build_technical_case_snapshot_from_case_status(
        case_status_snapshot=case_status_snapshot,
        laudo=laudo,
        source_channel=source_channel,
        actor_access_level=getattr(usuario, "nivel_acesso", None),
        policy_snapshot_ref=policy_snapshot_ref,
        timestamp=timestamp,
    )


__all__ = [
    "TechnicalCaseLegacyRefsV1",
    "TechnicalCaseSnapshotV1",
    "build_technical_case_snapshot_for_user",
    "build_technical_case_snapshot_from_case_status",
    "build_technical_case_snapshot_from_legacy",
]
