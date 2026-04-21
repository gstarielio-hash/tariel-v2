"""Helpers compartilhados para montar runtime V2 do caso tecnico."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.domains.chat.laudo_state_helpers import (
    laudo_permite_reabrir,
    laudo_tem_interacao,
    obter_contexto_modo_entrada_laudo,
    obter_estado_api_laudo,
    obter_status_card_laudo,
    serializar_card_laudo,
    serializar_contexto_case_lifecycle_legado,
)
from app.shared.database import Laudo, Usuario
from app.v2.acl import (
    build_technical_case_snapshot_for_user,
    build_technical_case_status_snapshot_for_user,
)
from app.v2.billing import build_tenant_policy_capability_snapshot
from app.v2.document import (
    attach_legacy_document_shadow,
    build_canonical_document_facade,
    build_legacy_document_pipeline_shadow_input,
    evaluate_legacy_document_pipeline_shadow,
)
from app.v2.policy import build_technical_case_policy_decision

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TechnicalCaseRuntimeBundle:
    legacy_payload: dict[str, Any]
    provenance_summary: Any | None = None
    case_snapshot: Any | None = None
    technical_case_snapshot: Any | None = None
    tenant_policy_context: Any | None = None
    policy_decision: Any | None = None
    document_facade: Any | None = None
    document_shadow_result: Any | None = None


def build_legacy_case_status_payload_from_laudo(
    *,
    banco: Session,
    laudo: Laudo | None,
    include_entry_mode_context: bool = False,
    include_case_lifecycle_context: bool = True,
) -> dict[str, Any]:
    if laudo is None:
        payload_sem_laudo: dict[str, Any] = {
            "estado": "sem_relatorio",
            "laudo_id": None,
            "status_card": "oculto",
            "permite_reabrir": False,
            "tem_interacao": False,
            "laudo_card": None,
        }
        if include_case_lifecycle_context:
            payload_sem_laudo.update(
                serializar_contexto_case_lifecycle_legado(
                    laudo=None,
                    legacy_payload=payload_sem_laudo,
                )
            )
        return payload_sem_laudo

    status_card = obter_status_card_laudo(banco, laudo)
    payload: dict[str, Any] = {
        "estado": obter_estado_api_laudo(banco, laudo),
        "laudo_id": int(laudo.id) if status_card != "oculto" else None,
        "status_card": status_card,
        "permite_reabrir": laudo_permite_reabrir(banco, laudo),
        "tem_interacao": laudo_tem_interacao(banco, int(laudo.id)),
        "laudo_card": serializar_card_laudo(banco, laudo) if status_card != "oculto" else None,
    }
    if include_entry_mode_context:
        payload.update(obter_contexto_modo_entrada_laudo(laudo))
    if include_case_lifecycle_context:
        payload.update(
            serializar_contexto_case_lifecycle_legado(
                laudo=laudo,
                legacy_payload=payload,
            )
        )
    return payload


def build_technical_case_context_bundle(
    *,
    banco: Session,
    usuario: Usuario,
    laudo: Laudo | None,
    legacy_payload: dict[str, Any],
    source_channel: str,
    template_key: Any = None,
    family_key: Any = None,
    variant_key: Any = None,
    laudo_type: Any = None,
    document_type: Any = None,
    provenance_summary: Any | None = None,
    current_review_status: Any = None,
    has_form_data: bool = False,
    has_ai_draft: bool = False,
    report_pack_draft: Any = None,
    include_full_snapshot: bool = False,
    include_policy_decision: bool = True,
    include_document_facade: bool = True,
    attach_document_shadow: bool = False,
    allow_partial_failures: bool = False,
) -> TechnicalCaseRuntimeBundle:
    bundle = TechnicalCaseRuntimeBundle(
        legacy_payload=dict(legacy_payload or {}),
        provenance_summary=provenance_summary,
    )
    case_snapshot = build_technical_case_status_snapshot_for_user(
        usuario=usuario,
        legacy_payload=bundle.legacy_payload,
        laudo=laudo,
        content_origin_summary=provenance_summary,
    )
    bundle.case_snapshot = case_snapshot

    if include_full_snapshot and laudo is not None and getattr(laudo, "id", None):
        bundle.technical_case_snapshot = build_technical_case_snapshot_for_user(
            usuario=usuario,
            legacy_payload=bundle.legacy_payload,
            laudo=laudo,
            source_channel=source_channel,
            content_origin_summary=provenance_summary,
            correlation_id=case_snapshot.correlation_id,
        )

    bundle.tenant_policy_context = build_tenant_policy_capability_snapshot(
        tenant=getattr(usuario, "empresa", None),
        tenant_id=getattr(usuario, "empresa_id", None),
        banco=banco,
    )

    def _build_policy_decision() -> Any:
        return build_technical_case_policy_decision(
            banco=banco,
            case_snapshot=case_snapshot,
            template_key=template_key,
            family_key=family_key,
            variant_key=variant_key,
            laudo_type=laudo_type,
            document_type=document_type,
            tenant_policy_context=bundle.tenant_policy_context,
            report_pack_draft=report_pack_draft,
        )

    if include_policy_decision:
        if allow_partial_failures:
            try:
                bundle.policy_decision = _build_policy_decision()
            except Exception:
                logger.debug("Falha ao derivar policy decision do caso tecnico V2.", exc_info=True)
                bundle.policy_decision = None
        else:
            bundle.policy_decision = _build_policy_decision()

    def _build_document_facade() -> Any:
        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=case_snapshot,
            source_channel=source_channel,
            template_key=template_key,
            policy_decision=bundle.policy_decision,
            tenant_policy_context=bundle.tenant_policy_context,
            provenance_summary=provenance_summary,
            current_review_status=current_review_status,
            has_form_data=has_form_data,
            has_ai_draft=has_ai_draft,
        )
        if attach_document_shadow:
            shadow_input = build_legacy_document_pipeline_shadow_input(
                facade=facade,
                provenance_summary=provenance_summary,
                banco=banco,
                laudo=laudo,
            )
            bundle.document_shadow_result = evaluate_legacy_document_pipeline_shadow(
                shadow_input=shadow_input,
            )
            facade = attach_legacy_document_shadow(
                facade=facade,
                shadow_result=bundle.document_shadow_result,
            )
        return facade

    if include_document_facade:
        if allow_partial_failures:
            try:
                bundle.document_facade = _build_document_facade()
            except Exception:
                logger.debug("Falha ao derivar facade documental do caso tecnico V2.", exc_info=True)
                bundle.document_facade = None
        else:
            bundle.document_facade = _build_document_facade()

    return bundle


def bind_technical_case_runtime_bundle_to_request(
    *,
    request: Request,
    bundle: TechnicalCaseRuntimeBundle,
) -> TechnicalCaseRuntimeBundle:
    if bundle.case_snapshot is not None:
        request.state.v2_case_core_snapshot = bundle.case_snapshot.model_dump(mode="python")
    if bundle.technical_case_snapshot is not None:
        request.state.v2_technical_case_snapshot = bundle.technical_case_snapshot.model_dump(
            mode="python"
        )
    if bundle.tenant_policy_context is not None:
        request.state.v2_tenant_policy_context = bundle.tenant_policy_context.model_dump(
            mode="python"
        )
    if bundle.policy_decision is not None:
        request.state.v2_policy_decision_summary = bundle.policy_decision.summary.model_dump(
            mode="python"
        )
    if bundle.document_facade is not None:
        request.state.v2_document_facade_summary = bundle.document_facade.document_readiness.model_dump(
            mode="python"
        )
    if bundle.document_shadow_result is not None:
        request.state.v2_document_shadow_summary = bundle.document_shadow_result.model_dump(
            mode="python"
        )
    return bundle


def build_technical_case_runtime_bundle(
    *,
    request: Request,
    banco: Session,
    usuario: Usuario,
    laudo: Laudo | None,
    legacy_payload: dict[str, Any],
    source_channel: str,
    template_key: Any = None,
    family_key: Any = None,
    variant_key: Any = None,
    laudo_type: Any = None,
    document_type: Any = None,
    provenance_summary: Any | None = None,
    current_review_status: Any = None,
    has_form_data: bool = False,
    has_ai_draft: bool = False,
    report_pack_draft: Any = None,
    include_full_snapshot: bool = False,
    include_policy_decision: bool = True,
    include_document_facade: bool = True,
    attach_document_shadow: bool = False,
    allow_partial_failures: bool = False,
) -> TechnicalCaseRuntimeBundle:
    bundle = build_technical_case_context_bundle(
        banco=banco,
        usuario=usuario,
        laudo=laudo,
        legacy_payload=legacy_payload,
        source_channel=source_channel,
        template_key=template_key,
        family_key=family_key,
        variant_key=variant_key,
        laudo_type=laudo_type,
        document_type=document_type,
        provenance_summary=provenance_summary,
        current_review_status=current_review_status,
        has_form_data=has_form_data,
        has_ai_draft=has_ai_draft,
        report_pack_draft=report_pack_draft,
        include_full_snapshot=include_full_snapshot,
        include_policy_decision=include_policy_decision,
        include_document_facade=include_document_facade,
        attach_document_shadow=attach_document_shadow,
        allow_partial_failures=allow_partial_failures,
    )
    return bind_technical_case_runtime_bundle_to_request(
        request=request,
        bundle=bundle,
    )


__all__ = [
    "TechnicalCaseRuntimeBundle",
    "bind_technical_case_runtime_bundle_to_request",
    "build_technical_case_context_bundle",
    "build_legacy_case_status_payload_from_laudo",
    "build_technical_case_runtime_bundle",
]
