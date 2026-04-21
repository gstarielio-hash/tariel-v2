"""Adapter da projeção canônica do Inspetor para o payload legado de status."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.projections import InspectorCaseViewProjectionV1


class InspectorLegacyStatusAdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any]
    compatible: bool
    divergences: list[str] = Field(default_factory=list)


def _payload_from_projection(projection: InspectorCaseViewProjectionV1) -> dict[str, Any]:
    payload = projection.payload
    return {
        "estado": payload["legacy_public_state"],
        "laudo_id": payload["legacy_laudo_id"],
        "status_card": payload["legacy_status_card"] or "oculto",
        "permite_edicao": bool(payload["allows_edit"]),
        "permite_reabrir": bool(payload["allows_reopen"]),
        "tem_interacao": bool(payload["has_interaction"]),
        "case_lifecycle_status": payload["case_lifecycle_status"],
        "case_workflow_mode": payload["case_workflow_mode"],
        "active_owner_role": payload["active_owner_role"],
        "allowed_next_lifecycle_statuses": list(
            payload["allowed_next_lifecycle_statuses"]
        ),
        "allowed_lifecycle_transitions": list(
            payload.get("allowed_lifecycle_transitions") or []
        ),
        "allowed_surface_actions": list(payload.get("allowed_surface_actions") or []),
        "tipos_relatorio": dict(payload["report_types"]),
        "public_verification": payload.get("public_verification"),
        "emissao_oficial": payload.get("emissao_oficial"),
        "laudo_card": payload["laudo_card"],
    }


def adapt_inspector_case_view_projection_to_legacy_status(
    *,
    projection: InspectorCaseViewProjectionV1,
    expected_legacy_payload: dict[str, Any] | None = None,
) -> InspectorLegacyStatusAdapterResult:
    payload = _payload_from_projection(projection)
    divergences: list[str] = []

    if expected_legacy_payload is not None:
        expected_report_types = expected_legacy_payload.get("tipos_relatorio")
        if isinstance(expected_report_types, tuple):
            payload["tipos_relatorio"] = tuple(payload["tipos_relatorio"])
        elif isinstance(expected_report_types, list):
            payload["tipos_relatorio"] = list(payload["tipos_relatorio"])
        elif isinstance(expected_report_types, dict):
            payload["tipos_relatorio"] = dict(payload["tipos_relatorio"])

        for key, value in payload.items():
            if key not in expected_legacy_payload:
                continue
            if expected_legacy_payload.get(key) != value:
                divergences.append(key)

    return InspectorLegacyStatusAdapterResult(
        payload=payload,
        compatible=not divergences,
        divergences=divergences,
    )


__all__ = [
    "InspectorLegacyStatusAdapterResult",
    "adapt_inspector_case_view_projection_to_legacy_status",
]
