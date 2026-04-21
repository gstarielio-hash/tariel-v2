"""Adapter da projeção canônica da Mesa para o payload legado do pacote."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.v2.acl.technical_case_core import build_case_status_visual_label
from app.v2.contracts.projections import ReviewDeskCaseViewProjectionV1


class ReviewDeskLegacyPackageAdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any]
    compatible: bool
    divergences: list[str] = Field(default_factory=list)


def _payload_from_projection(projection: ReviewDeskCaseViewProjectionV1) -> dict[str, Any]:
    payload = projection.model_dump(mode="json")["payload"]
    return {
        "laudo_id": payload["legacy_laudo_id"],
        "codigo_hash": payload["codigo_hash"],
        "tipo_template": payload["tipo_template"],
        "setor_industrial": payload["setor_industrial"],
        "status_revisao": payload["legacy_review_status"],
        "case_status": payload["case_status"],
        "case_lifecycle_status": payload["case_lifecycle_status"],
        "case_workflow_mode": payload["case_workflow_mode"],
        "active_owner_role": payload["active_owner_role"],
        "allowed_next_lifecycle_statuses": payload["allowed_next_lifecycle_statuses"],
        "allowed_surface_actions": payload["allowed_surface_actions"],
        "status_visual_label": build_case_status_visual_label(
            lifecycle_status=payload["case_lifecycle_status"],
            active_owner_role=payload["active_owner_role"],
        ),
        "status_conformidade": payload["status_conformidade"],
        "criado_em": payload["created_at"],
        "atualizado_em": payload["updated_at"],
        "tempo_em_campo_minutos": payload["field_time_minutes"],
        "ultima_interacao_em": payload["last_interaction_at"],
        "inspetor_id": payload["inspector_id"],
        "revisor_id": payload["reviewer_id"],
        "dados_formulario": payload["dados_formulario"],
        "parecer_ia": payload["parecer_ia"],
        "resumo_mensagens": payload["summary_messages"],
        "resumo_evidencias": payload["summary_evidence"],
        "resumo_pendencias": payload["summary_pending"],
        "revisao_por_bloco": payload.get("revisao_por_bloco"),
        "coverage_map": payload.get("coverage_map"),
        "historico_inspecao": payload.get("inspection_history"),
        "verificacao_publica": payload.get("public_verification"),
        "anexo_pack": payload.get("anexo_pack"),
        "emissao_oficial": payload.get("emissao_oficial"),
        "historico_refazer_inspetor": payload.get("historico_refazer_inspetor") or [],
        "memoria_operacional_familia": payload.get("memoria_operacional_familia"),
        "pendencias_abertas": payload["open_pendencies"],
        "pendencias_resolvidas_recentes": payload["recent_resolved_pendencies"],
        "whispers_recentes": payload["recent_whispers"],
        "revisoes_recentes": payload["recent_reviews"],
        "collaboration": payload["collaboration"],
    }


def adapt_reviewdesk_case_view_projection_to_legacy_package(
    *,
    projection: ReviewDeskCaseViewProjectionV1,
    expected_legacy_payload: dict[str, Any] | None = None,
) -> ReviewDeskLegacyPackageAdapterResult:
    payload = _payload_from_projection(projection)
    divergences: list[str] = []

    if expected_legacy_payload is not None:
        for key, value in payload.items():
            if key not in expected_legacy_payload:
                continue
            if expected_legacy_payload.get(key) != value:
                divergences.append(key)

    return ReviewDeskLegacyPackageAdapterResult(
        payload=payload,
        compatible=not divergences,
        divergences=divergences,
    )


__all__ = [
    "ReviewDeskLegacyPackageAdapterResult",
    "adapt_reviewdesk_case_view_projection_to_legacy_package",
]
