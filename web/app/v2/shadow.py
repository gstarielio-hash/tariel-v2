"""Shadow mode incremental para contratos do V2."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field

from app.domains.chat.app_context import logger
from app.v2.acl.technical_case_core import (
    TechnicalCaseStatusSnapshot,
    build_technical_case_status_snapshot_for_user,
)
from app.v2.contracts.projections import build_inspector_case_status_projection_for_user
from app.v2.runtime import v2_case_core_acl_enabled, v2_envelopes_enabled


class ShadowProjectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str
    contract_version: str
    compatible: bool
    divergences: list[str] = Field(default_factory=list)
    projection: dict[str, Any]
    case_snapshot: dict[str, Any] | None = None


def run_inspector_case_status_shadow(
    *,
    request: Request,
    usuario: Any,
    legacy_payload: dict[str, Any],
    case_snapshot: TechnicalCaseStatusSnapshot | None = None,
) -> ShadowProjectionResult | None:
    if not v2_envelopes_enabled():
        return None

    use_case_acl = v2_case_core_acl_enabled()
    resolved_snapshot = case_snapshot
    if use_case_acl and resolved_snapshot is None:
        resolved_snapshot = build_technical_case_status_snapshot_for_user(
            usuario=usuario,
            legacy_payload=legacy_payload,
        )

    projection = build_inspector_case_status_projection_for_user(
        usuario=usuario,
        legacy_payload=legacy_payload,
        case_snapshot=resolved_snapshot if use_case_acl else None,
        source_channel="web_app",
    )

    projection_payload = projection.payload
    divergences: list[str] = []
    if projection_payload.get("legacy_laudo_id") != legacy_payload.get("laudo_id"):
        divergences.append("legacy_laudo_id")
    if bool(projection_payload.get("has_active_report")) != bool(legacy_payload.get("laudo_id")):
        divergences.append("has_active_report")
    if use_case_acl and resolved_snapshot is not None:
        if resolved_snapshot.legacy_public_state != legacy_payload.get("estado"):
            divergences.append("legacy_public_state")
        if projection_payload.get("state") != resolved_snapshot.canonical_status:
            divergences.append("canonical_state")
        if projection.case_id != resolved_snapshot.case_ref.case_id:
            divergences.append("case_id")
    elif projection_payload.get("state") != legacy_payload.get("estado"):
        divergences.append("state")

    result = ShadowProjectionResult(
        contract_name=projection.contract_name,
        contract_version=projection.contract_version,
        compatible=not divergences,
        divergences=divergences,
        projection=projection.model_dump(mode="json"),
        case_snapshot=(
            resolved_snapshot.model_dump(mode="json")
            if resolved_snapshot is not None
            else None
        ),
    )

    request.state.v2_shadow_projection_result = result.model_dump(mode="python")
    if resolved_snapshot is not None:
        request.state.v2_case_core_snapshot = resolved_snapshot.model_dump(mode="python")

    if divergences:
        logger.debug(
            "V2 shadow divergiu | contract=%s | divergences=%s | case_acl=%s",
            projection.contract_name,
            ",".join(divergences),
            use_case_acl,
        )

    return result


__all__ = [
    "ShadowProjectionResult",
    "run_inspector_case_status_shadow",
]
