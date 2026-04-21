"""Facade documental incremental do V2."""

from __future__ import annotations

from app.v2.document.facade import build_canonical_document_facade
from app.v2.document.gate_metrics import (
    clear_document_soft_gate_metrics_for_tests,
    document_soft_gate_observability_enabled,
    ensure_document_soft_gate_local_access,
    get_document_soft_gate_operational_summary,
    record_document_soft_gate_trace,
)
from app.v2.document.hard_gate import (
    build_document_hard_gate_block_detail,
    build_document_hard_gate_decision,
    build_document_hard_gate_enforcement_result,
    document_hard_gate_observability_flags,
)
from app.v2.document.hard_gate_metrics import (
    clear_document_hard_gate_metrics_for_tests,
    document_hard_gate_observability_enabled,
    ensure_document_hard_gate_local_access,
    get_document_hard_gate_operational_summary,
    record_document_hard_gate_result,
)
from app.v2.document.hard_gate_models import (
    DocumentHardGateBlockerV1,
    DocumentHardGateDecisionV1,
    DocumentHardGateEnforcementResultV1,
    DocumentHardGateSummaryV1,
)
from app.v2.document.gate_models import (
    DocumentSoftGateBlockerV1,
    DocumentSoftGateDecisionV1,
    DocumentSoftGateRouteContextV1,
    DocumentSoftGateSummaryV1,
    DocumentSoftGateTraceV1,
)
from app.v2.document.gates import (
    build_document_soft_gate_route_context,
    build_document_soft_gate_trace,
)
from app.v2.document.legacy_adapter import (
    attach_legacy_document_shadow,
    build_legacy_document_pipeline_shadow_input,
    evaluate_legacy_document_pipeline_shadow,
)
from app.v2.document.models import (
    CanonicalDocumentFacadeV1,
    DocumentBlockerSummary,
    DocumentMaterializationReadinessV1,
    DocumentPolicyViewSummary,
    DocumentTemplateBindingRef,
    LegacyDocumentPipelineShadowInput,
    LegacyDocumentPipelineShadowResult,
    LegacyDocumentReadinessComparison,
)
from app.v2.document.template_binding import resolve_document_template_binding

__all__ = [
    "CanonicalDocumentFacadeV1",
    "DocumentBlockerSummary",
    "DocumentHardGateBlockerV1",
    "DocumentHardGateDecisionV1",
    "DocumentHardGateEnforcementResultV1",
    "DocumentHardGateSummaryV1",
    "DocumentMaterializationReadinessV1",
    "DocumentPolicyViewSummary",
    "DocumentSoftGateBlockerV1",
    "DocumentSoftGateDecisionV1",
    "DocumentSoftGateRouteContextV1",
    "DocumentSoftGateSummaryV1",
    "DocumentSoftGateTraceV1",
    "DocumentTemplateBindingRef",
    "LegacyDocumentPipelineShadowInput",
    "LegacyDocumentPipelineShadowResult",
    "LegacyDocumentReadinessComparison",
    "attach_legacy_document_shadow",
    "build_canonical_document_facade",
    "build_document_hard_gate_block_detail",
    "build_document_hard_gate_decision",
    "build_document_hard_gate_enforcement_result",
    "build_document_soft_gate_route_context",
    "build_document_soft_gate_trace",
    "build_legacy_document_pipeline_shadow_input",
    "clear_document_hard_gate_metrics_for_tests",
    "clear_document_soft_gate_metrics_for_tests",
    "document_hard_gate_observability_enabled",
    "document_hard_gate_observability_flags",
    "document_soft_gate_observability_enabled",
    "ensure_document_hard_gate_local_access",
    "ensure_document_soft_gate_local_access",
    "evaluate_legacy_document_pipeline_shadow",
    "get_document_hard_gate_operational_summary",
    "get_document_soft_gate_operational_summary",
    "record_document_hard_gate_result",
    "record_document_soft_gate_trace",
    "resolve_document_template_binding",
]
