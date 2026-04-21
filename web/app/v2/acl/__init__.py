"""ACLs incrementais do V2 sobre o legado."""

from __future__ import annotations

from app.v2.acl.technical_case_core import (
    TechnicalCaseLifecycleTransition,
    TechnicalCaseRef,
    TechnicalCaseSurfaceAction,
    TechnicalCaseStatusSnapshot,
    build_technical_case_ref_from_legacy_laudo,
    build_technical_case_status_snapshot_for_user,
    build_technical_case_status_snapshot_from_legacy,
    is_mobile_review_command_allowed,
    resolve_allowed_lifecycle_transitions,
    resolve_allowed_mobile_review_decisions,
    resolve_allowed_surface_actions,
    resolve_canonical_case_status_from_legacy,
    resolve_supports_mobile_block_reopen,
)
from app.v2.acl.technical_case_snapshot import (
    TechnicalCaseLegacyRefsV1,
    TechnicalCaseSnapshotV1,
    build_technical_case_snapshot_for_user,
    build_technical_case_snapshot_from_case_status,
    build_technical_case_snapshot_from_legacy,
)

__all__ = [
    "TechnicalCaseLegacyRefsV1",
    "TechnicalCaseLifecycleTransition",
    "TechnicalCaseRef",
    "TechnicalCaseSnapshotV1",
    "TechnicalCaseSurfaceAction",
    "TechnicalCaseStatusSnapshot",
    "build_technical_case_ref_from_legacy_laudo",
    "build_technical_case_snapshot_for_user",
    "build_technical_case_snapshot_from_case_status",
    "build_technical_case_snapshot_from_legacy",
    "build_technical_case_status_snapshot_for_user",
    "build_technical_case_status_snapshot_from_legacy",
    "is_mobile_review_command_allowed",
    "resolve_allowed_lifecycle_transitions",
    "resolve_allowed_mobile_review_decisions",
    "resolve_allowed_surface_actions",
    "resolve_canonical_case_status_from_legacy",
    "resolve_supports_mobile_block_reopen",
]
