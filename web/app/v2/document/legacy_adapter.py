"""Integracao shadow segura entre a facade documental canonica e o pipeline legado."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domains.chat.catalog_pdf_templates import (
    RENDER_MODE_CLIENT_PDF_FILLED,
    build_catalog_pdf_payload,
    has_viable_legacy_preview_overlay_for_pdf_template,
    resolve_pdf_template_for_laudo,
    should_use_rich_runtime_preview_for_pdf_template,
)
from app.v2.contracts.provenance import ContentOriginSummary
from app.v2.document.models import (
    CanonicalDocumentFacadeV1,
    DocumentBlockerSummary,
    LegacyDocumentPipelineShadowInput,
    LegacyDocumentPipelineShadowResult,
    LegacyDocumentReadinessComparison,
)


def build_legacy_document_pipeline_shadow_input(
    *,
    facade: CanonicalDocumentFacadeV1,
    provenance_summary: ContentOriginSummary | None = None,
    banco: Session | None = None,
    laudo: Any | None = None,
) -> LegacyDocumentPipelineShadowInput:
    runtime_preview_summary = _resolve_runtime_preview_summary(
        facade=facade,
        banco=banco,
        laudo=laudo,
    )
    return LegacyDocumentPipelineShadowInput(
        tenant_id=facade.tenant_id,
        case_id=facade.case_id,
        legacy_laudo_id=facade.legacy_laudo_id,
        document_id=facade.document_id,
        thread_id=facade.thread_id,
        source_channel=facade.source_channel,
        template_binding=facade.template_binding,
        document_policy=facade.document_policy,
        document_readiness=facade.document_readiness,
        provenance_summary=(
            provenance_summary.model_dump(mode="python")
            if provenance_summary is not None
            else facade.document_readiness.provenance_summary
        ),
        legacy_preview_overlay_viable=runtime_preview_summary.get("legacy_preview_overlay_viable"),
        rich_runtime_preview_viable=runtime_preview_summary.get("rich_runtime_preview_viable"),
        resolved_template_family_key=runtime_preview_summary.get("resolved_template_family_key"),
        resolved_template_source_kind=runtime_preview_summary.get("resolved_template_source_kind"),
    )


def _build_blocker(
    *,
    blocker_code: str,
    blocker_kind: str,
    message: str,
    blocking: bool,
    source: str,
) -> DocumentBlockerSummary:
    return DocumentBlockerSummary(
        blocker_code=blocker_code,
        blocker_kind=blocker_kind,  # type: ignore[arg-type]
        message=message,
        blocking=blocking,
        source=source,
    )


def _normalize_optional_int(value: Any) -> int | None:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return None
    return resolved if resolved > 0 else None


def _resolve_runtime_preview_summary(
    *,
    facade: CanonicalDocumentFacadeV1,
    banco: Session | None,
    laudo: Any | None,
) -> dict[str, Any]:
    if banco is None or laudo is None:
        return {}

    tenant_id = _normalize_optional_int(facade.tenant_id or getattr(laudo, "empresa_id", None))
    legacy_laudo_id = _normalize_optional_int(
        facade.legacy_laudo_id or getattr(laudo, "id", None)
    )
    if tenant_id is None or legacy_laudo_id is None:
        return {}

    resolved_template = resolve_pdf_template_for_laudo(
        banco=banco,
        empresa_id=tenant_id,
        laudo=laudo,
        allow_runtime_fallback=False,
        allow_current_binding_lookup=True,
    )
    if resolved_template is None:
        return {}

    runtime_payload = (
        build_catalog_pdf_payload(
            laudo=laudo,
            template_ref=resolved_template,
            render_mode=RENDER_MODE_CLIENT_PDF_FILLED,
        )
        if resolved_template.family_key
        else (
            getattr(laudo, "dados_formulario", None)
            if isinstance(getattr(laudo, "dados_formulario", None), dict)
            else {}
        )
    )
    overlay_viable = has_viable_legacy_preview_overlay_for_pdf_template(
        template_ref=resolved_template,
    )
    rich_runtime_viable = should_use_rich_runtime_preview_for_pdf_template(
        template_ref=resolved_template,
        payload=runtime_payload or {},
        render_mode=RENDER_MODE_CLIENT_PDF_FILLED,
    )
    return {
        "legacy_preview_overlay_viable": overlay_viable,
        "rich_runtime_preview_viable": rich_runtime_viable,
        "resolved_template_family_key": str(resolved_template.family_key or "").strip() or None,
        "resolved_template_source_kind": str(resolved_template.source_kind or "").strip() or None,
    }


def _resolve_shadow_pipeline(
    shadow_input: LegacyDocumentPipelineShadowInput,
) -> tuple[str, list[DocumentBlockerSummary], dict[str, Any], bool]:
    binding = shadow_input.template_binding
    readiness = shadow_input.document_readiness

    has_active_report = bool(shadow_input.legacy_laudo_id)
    has_form_data = bool(readiness.has_form_data)
    blockers: list[DocumentBlockerSummary] = []
    resolution = {
        "binding_status": binding.binding_status,
        "template_id": binding.template_id,
        "template_key": binding.template_key,
        "template_version": binding.template_version,
        "template_source_kind": binding.template_source_kind,
        "legacy_template_mode": binding.legacy_template_mode,
        "legacy_template_status": binding.legacy_template_status,
        "legacy_pdf_base_available": binding.legacy_pdf_base_available,
        "legacy_editor_document_present": binding.legacy_editor_document_present,
        "has_form_data": has_form_data,
        "legacy_preview_overlay_viable": shadow_input.legacy_preview_overlay_viable,
        "rich_runtime_preview_viable": shadow_input.rich_runtime_preview_viable,
        "resolved_template_family_key": shadow_input.resolved_template_family_key,
        "resolved_template_source_kind": shadow_input.resolved_template_source_kind,
    }

    if not has_active_report:
        blockers.append(
            _build_blocker(
                blocker_code="legacy_no_active_report",
                blocker_kind="data",
                message="O pipeline legado nao tem laudo ativo para avaliar materializacao.",
                blocking=True,
                source="document_shadow",
            )
        )
        resolution["selection_reason"] = "no_active_report"
        return ("not_available", blockers, resolution, False)

    if binding.binding_status == "bound" and has_form_data:
        if binding.template_source_kind == "editor_rico":
            if bool(binding.legacy_editor_document_present):
                resolution["selection_reason"] = "bound_editor_rico_template"
                return ("editor_rico_preview", blockers, resolution, True)
            blockers.append(
                _build_blocker(
                    blocker_code="legacy_editor_document_missing",
                    blocker_kind="template",
                    message="O template legado em editor rico nao possui documento estruturado para preview.",
                    blocking=False,
                    source="document_shadow",
                )
            )
            resolution["selection_reason"] = "editor_rico_missing_document"
            return ("legacy_pdf_fallback", blockers, resolution, True)

        if binding.template_source_kind == "legacy_pdf":
            overlay_viable = shadow_input.legacy_preview_overlay_viable
            rich_runtime_viable = shadow_input.rich_runtime_preview_viable
            if rich_runtime_viable is True:
                resolution["selection_reason"] = "legacy_pdf_promoted_to_editor_rico"
                resolution["runtime_render_strategy"] = "legacy_promoted_to_editor_rico"
                return ("editor_rico_preview", blockers, resolution, True)
            if overlay_viable is True:
                resolution["selection_reason"] = "bound_pdf_template"
                return ("legacy_pdf_preview", blockers, resolution, True)
            if overlay_viable is False:
                if bool(binding.legacy_pdf_base_available):
                    blockers.append(
                        _build_blocker(
                            blocker_code="legacy_pdf_overlay_missing",
                            blocker_kind="template",
                            message="O template legado vinculado nao possui overlay viavel para preview seguro.",
                            blocking=False,
                            source="document_shadow",
                        )
                    )
                    resolution["selection_reason"] = "pdf_overlay_missing"
                else:
                    blockers.append(
                        _build_blocker(
                            blocker_code="legacy_pdf_base_missing",
                            blocker_kind="template",
                            message="O template legado vinculado nao possui PDF-base disponivel para preview.",
                            blocking=False,
                            source="document_shadow",
                        )
                    )
                    resolution["selection_reason"] = "pdf_base_missing"
                return ("legacy_pdf_fallback", blockers, resolution, True)
            if bool(binding.legacy_pdf_base_available):
                resolution["selection_reason"] = "bound_pdf_template"
                return ("legacy_pdf_preview", blockers, resolution, True)
            blockers.append(
                _build_blocker(
                    blocker_code="legacy_pdf_base_missing",
                    blocker_kind="template",
                    message="O template legado vinculado nao possui PDF-base disponivel para preview.",
                    blocking=False,
                    source="document_shadow",
                )
            )
            resolution["selection_reason"] = "pdf_base_missing"
            return ("legacy_pdf_fallback", blockers, resolution, True)

        blockers.append(
            _build_blocker(
                blocker_code="legacy_template_mode_unknown",
                blocker_kind="template",
                message="O template legado vinculado nao possui modo de editor reconhecido para preview seguro.",
                blocking=False,
                source="document_shadow",
            )
        )
        resolution["selection_reason"] = "unknown_template_mode"
        return ("legacy_pdf_fallback", blockers, resolution, True)

    if binding.binding_status == "bound" and not has_form_data:
        blockers.append(
            _build_blocker(
                blocker_code="legacy_template_requires_form_data",
                blocker_kind="data",
                message="O caminho legado por template so e selecionado quando ha dados de formulario materializados.",
                blocking=False,
                source="document_shadow",
            )
        )
        resolution["selection_reason"] = "bound_template_without_form_data"
        return ("legacy_pdf_fallback", blockers, resolution, True)

    resolution["selection_reason"] = "no_template_binding"
    return ("legacy_pdf_fallback", blockers, resolution, True)


def evaluate_legacy_document_pipeline_shadow(
    *,
    shadow_input: LegacyDocumentPipelineShadowInput,
) -> LegacyDocumentPipelineShadowResult:
    pipeline_name, blockers, template_resolution, materialization_allowed = _resolve_shadow_pipeline(shadow_input)
    readiness = shadow_input.document_readiness
    binding = shadow_input.template_binding

    legacy_issue_allowed = bool(materialization_allowed) and bool(readiness.issue_allowed) and (
        str(readiness.current_document_status or "") == "approved_for_issue"
    )
    canonical_blocking = any(item.blocking for item in readiness.blockers)
    legacy_blocking = any(item.blocking for item in blockers)

    divergences: list[str] = []
    template_binding_agrees = (binding.binding_status == "bound") == (
        pipeline_name in {"editor_rico_preview", "legacy_pdf_preview"}
    )
    if not template_binding_agrees:
        divergences.append("template_binding_vs_legacy_pipeline")
    if bool(readiness.materialization_allowed) != bool(materialization_allowed):
        divergences.append("materialization_allowed")
    if bool(readiness.issue_allowed) != bool(legacy_issue_allowed):
        divergences.append("issue_allowed")
    blockers_match = canonical_blocking == legacy_blocking
    if not blockers_match:
        divergences.append("blocking_state")

    if not divergences:
        compatibility_state = "aligned"
    elif pipeline_name == "not_available":
        compatibility_state = "partial"
    else:
        compatibility_state = "diverged"

    comparison_quality = "high"
    if pipeline_name == "legacy_pdf_fallback" or any(
        item.blocker_code
        in {
            "legacy_template_requires_form_data",
            "legacy_pdf_base_missing",
            "legacy_pdf_overlay_missing",
            "legacy_editor_document_missing",
        }
        for item in blockers
    ):
        comparison_quality = "partial"
    if pipeline_name == "not_available":
        comparison_quality = "low"

    comparison = LegacyDocumentReadinessComparison(
        canonical_materialization_allowed=bool(readiness.materialization_allowed),
        legacy_materialization_allowed=bool(materialization_allowed),
        canonical_issue_allowed=bool(readiness.issue_allowed),
        legacy_issue_allowed=bool(legacy_issue_allowed),
        template_binding_agrees=template_binding_agrees,
        blockers_match=blockers_match,
        divergences=divergences,
        compatibility_state=compatibility_state,  # type: ignore[arg-type]
        comparison_quality=comparison_quality,  # type: ignore[arg-type]
    )

    return LegacyDocumentPipelineShadowResult(
        tenant_id=shadow_input.tenant_id,
        case_id=shadow_input.case_id,
        legacy_laudo_id=shadow_input.legacy_laudo_id,
        document_id=shadow_input.document_id,
        thread_id=shadow_input.thread_id,
        pipeline_name=pipeline_name,
        template_resolution=template_resolution,
        materialization_allowed=bool(materialization_allowed),
        issue_allowed=bool(legacy_issue_allowed),
        blockers=blockers,
        comparison=comparison,
    )


def attach_legacy_document_shadow(
    *,
    facade: CanonicalDocumentFacadeV1,
    shadow_result: LegacyDocumentPipelineShadowResult,
) -> CanonicalDocumentFacadeV1:
    return facade.model_copy(update={"legacy_pipeline_shadow": shadow_result})


__all__ = [
    "LegacyDocumentPipelineShadowInput",
    "LegacyDocumentPipelineShadowResult",
    "LegacyDocumentReadinessComparison",
    "attach_legacy_document_shadow",
    "build_legacy_document_pipeline_shadow_input",
    "evaluate_legacy_document_pipeline_shadow",
]
