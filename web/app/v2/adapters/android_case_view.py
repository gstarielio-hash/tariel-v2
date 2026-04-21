"""Adapter da projeção canônica do Inspetor para o payload legado do Android."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.v2.contracts.envelopes import utc_now
from app.v2.contracts.projections import InspectorCaseViewProjectionV1


class AndroidCaseViewAdapterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseViewAdapterInputV1"
    contract_version: str = "v1"
    tenant_id: str
    actor_id: str
    actor_role: str
    projection: InspectorCaseViewProjectionV1
    expected_legacy_payload: dict[str, Any] | None = None
    timestamp: Any = Field(default_factory=utc_now)


class AndroidCaseCompatibilitySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseCompatibilitySummaryV1"
    contract_version: str = "v1"
    compatible: bool
    divergences: list[str] = Field(default_factory=list)
    visibility_scope: str = "inspetor_mobile"
    used_projection: bool = False
    timestamp: Any = Field(default_factory=utc_now)


class AndroidCaseViewAdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_name: str = "AndroidCaseViewAdapterResultV1"
    contract_version: str = "v1"
    payload: dict[str, Any]
    compatibility: AndroidCaseCompatibilitySummary


def _legacy_mobile_payload_from_projection(projection: InspectorCaseViewProjectionV1) -> dict[str, Any]:
    payload = projection.payload
    laudo_card = dict(payload.get("laudo_card") or {})
    report_types = dict(payload.get("report_types") or {})

    return {
        "id": laudo_card.get("id", payload.get("legacy_laudo_id")),
        "titulo": str(laudo_card.get("titulo") or ""),
        "preview": str(laudo_card.get("preview") or ""),
        "pinado": bool(laudo_card.get("pinado")),
        "data_iso": str(laudo_card.get("data_iso") or ""),
        "data_br": str(laudo_card.get("data_br") or ""),
        "hora_br": str(laudo_card.get("hora_br") or ""),
        "tipo_template": str(
            laudo_card.get("tipo_template")
            or next(iter(report_types.keys()), "padrao")
        ),
        "status_revisao": str(laudo_card.get("status_revisao") or payload.get("legacy_review_status") or ""),
        "status_card": str(laudo_card.get("status_card") or payload.get("legacy_status_card") or "oculto"),
        "status_card_label": str(laudo_card.get("status_card_label") or "Laudo"),
        "permite_edicao": bool(laudo_card.get("permite_edicao", payload.get("allows_edit"))),
        "permite_reabrir": bool(laudo_card.get("permite_reabrir", payload.get("allows_reopen"))),
        "possui_historico": bool(laudo_card.get("possui_historico", payload.get("has_active_report"))),
    }


def _merge_expected_legacy_passthrough(
    *,
    payload: dict[str, Any],
    expected_legacy_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if not expected_legacy_payload:
        return payload

    merged = dict(payload)
    for key, value in expected_legacy_payload.items():
        if key not in merged:
            merged[key] = value
    return merged


def adapt_android_case_view(
    *,
    adapter_input: AndroidCaseViewAdapterInput,
) -> AndroidCaseViewAdapterResult:
    payload = _merge_expected_legacy_passthrough(
        payload=_legacy_mobile_payload_from_projection(adapter_input.projection),
        expected_legacy_payload=adapter_input.expected_legacy_payload,
    )
    divergences: list[str] = []

    if adapter_input.actor_role != "inspetor":
        divergences.append("actor_role")

    if adapter_input.expected_legacy_payload is not None:
        for key, value in payload.items():
            if adapter_input.expected_legacy_payload.get(key) != value:
                divergences.append(key)

    compatibility = AndroidCaseCompatibilitySummary(
        compatible=not divergences,
        divergences=divergences,
        used_projection=not divergences,
    )

    return AndroidCaseViewAdapterResult(
        payload=payload,
        compatibility=compatibility,
    )


def adapt_inspector_case_view_projection_to_android_case(
    *,
    projection: InspectorCaseViewProjectionV1,
    expected_legacy_payload: dict[str, Any] | None = None,
) -> AndroidCaseViewAdapterResult:
    return adapt_android_case_view(
        adapter_input=AndroidCaseViewAdapterInput(
            tenant_id=str(projection.tenant_id),
            actor_id=str(projection.actor_id),
            actor_role=str(projection.actor_role),
            projection=projection,
            expected_legacy_payload=expected_legacy_payload,
        )
    )


__all__ = [
    "AndroidCaseCompatibilitySummary",
    "AndroidCaseViewAdapterInput",
    "AndroidCaseViewAdapterResult",
    "adapt_android_case_view",
    "adapt_inspector_case_view_projection_to_android_case",
]
