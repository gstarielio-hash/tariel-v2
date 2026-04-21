"""Adapters incrementais do V2 para convivencia com o legado."""

from __future__ import annotations

from app.v2.adapters.android_case_feed import (
    AndroidCaseFeedAdapterInput,
    AndroidCaseFeedCompatibilitySummary,
    AndroidCaseFeedItemAdapterResult,
    adapt_inspector_case_view_projection_to_android_feed_item,
)
from app.v2.adapters.android_case_thread import (
    AndroidCaseThreadAdapterInput,
    AndroidCaseThreadAdapterResult,
    AndroidCaseThreadCompatibilitySummary,
    AndroidCaseThreadMessageAdapterResult,
    adapt_inspector_case_view_projection_to_android_thread,
)
from app.v2.adapters.android_case_view import (
    AndroidCaseCompatibilitySummary,
    AndroidCaseViewAdapterInput,
    AndroidCaseViewAdapterResult,
    adapt_inspector_case_view_projection_to_android_case,
)
from app.v2.adapters.inspector_status import (
    InspectorLegacyStatusAdapterResult,
    adapt_inspector_case_view_projection_to_legacy_status,
)
from app.v2.adapters.reviewdesk_package import (
    ReviewDeskLegacyPackageAdapterResult,
    adapt_reviewdesk_case_view_projection_to_legacy_package,
)

__all__ = [
    "AndroidCaseFeedAdapterInput",
    "AndroidCaseFeedCompatibilitySummary",
    "AndroidCaseFeedItemAdapterResult",
    "AndroidCaseThreadAdapterInput",
    "AndroidCaseThreadAdapterResult",
    "AndroidCaseThreadCompatibilitySummary",
    "AndroidCaseThreadMessageAdapterResult",
    "AndroidCaseCompatibilitySummary",
    "AndroidCaseViewAdapterInput",
    "AndroidCaseViewAdapterResult",
    "InspectorLegacyStatusAdapterResult",
    "ReviewDeskLegacyPackageAdapterResult",
    "adapt_inspector_case_view_projection_to_android_feed_item",
    "adapt_inspector_case_view_projection_to_android_thread",
    "adapt_inspector_case_view_projection_to_android_case",
    "adapt_inspector_case_view_projection_to_legacy_status",
    "adapt_reviewdesk_case_view_projection_to_legacy_package",
]
