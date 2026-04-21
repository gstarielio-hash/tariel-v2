from __future__ import annotations

from types import SimpleNamespace

from starlette.requests import Request

from app.shared.database import NivelAcesso
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.contracts.envelopes import BaseEnvelope
from app.v2.contracts.projections import build_inspector_case_status_projection_for_user
from app.v2.runtime import V2_CASE_CORE_ACL_FLAG, V2_ENVELOPES_FLAG
from app.v2.shadow import run_inspector_case_status_shadow


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/app/api/laudo/status",
            "headers": [],
            "query_string": b"",
            "state": {},
        }
    )


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def test_base_envelope_expoe_campos_obrigatorios() -> None:
    envelope = BaseEnvelope(
        envelope_kind="projection",
        contract_name="DummyContractV1",
        tenant_id="33",
        case_id="101",
        thread_id="201",
        document_id="301",
        actor_id="17",
        actor_role="inspetor",
        correlation_id="corr-1",
        causation_id="cause-1",
        idempotency_key="idem-1",
        source_channel="web_app",
        origin_kind="human",
        sensitivity="technical",
        visibility_scope="actor",
        payload={"ok": True},
    )

    dumped = envelope.model_dump(mode="json")
    assert dumped["contract_name"] == "DummyContractV1"
    assert dumped["contract_version"] == "v1"
    assert dumped["tenant_id"] == "33"
    assert dumped["case_id"] == "101"
    assert dumped["thread_id"] == "201"
    assert dumped["document_id"] == "301"
    assert dumped["actor_id"] == "17"
    assert dumped["actor_role"] == "inspetor"
    assert dumped["correlation_id"] == "corr-1"
    assert dumped["causation_id"] == "cause-1"
    assert dumped["idempotency_key"] == "idem-1"
    assert dumped["source_channel"] == "web_app"
    assert dumped["origin_kind"] == "human"
    assert dumped["sensitivity"] == "technical"
    assert dumped["visibility_scope"] == "actor"
    assert dumped["payload"] == {"ok": True}
    assert dumped["timestamp"]


def test_contrato_piloto_serializa_projection_envelope() -> None:
    envelope = build_inspector_case_status_projection_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 88,
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": "rascunho"},
        },
    )

    dumped = envelope.model_dump(mode="json")
    assert dumped["contract_name"] == "InspectorCaseStatusProjectionV1"
    assert dumped["projection_name"] == "InspectorCaseStatusProjectionV1"
    assert dumped["projection_audience"] == "inspetor"
    assert dumped["projection_type"] == "operational_read_model"
    assert dumped["tenant_id"] == "33"
    assert dumped["case_id"] == "88"
    assert dumped["thread_id"] is None
    assert dumped["document_id"] is None
    assert dumped["actor_id"] == "17"
    assert dumped["actor_role"] == "inspetor"
    assert dumped["source_channel"] == "web_app"
    assert dumped["origin_kind"] == "system"
    assert dumped["payload"]["legacy_laudo_id"] == 88
    assert dumped["payload"]["state"] == "relatorio_ativo"
    assert dumped["payload"]["state_source"] == "legacy_public_state"
    assert dumped["payload"]["legacy_public_state"] == "relatorio_ativo"
    assert dumped["payload"]["has_active_report"] is True


def test_contrato_piloto_serializa_projection_envelope_via_acl() -> None:
    legacy_payload = {
        "estado": "aguardando",
        "laudo_id": 88,
        "permite_reabrir": False,
        "laudo_card": {"id": 88, "status_revisao": "Aguardando Aval"},
    }
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload=legacy_payload,
    )

    envelope = build_inspector_case_status_projection_for_user(
        usuario=_build_user(),
        legacy_payload=legacy_payload,
        case_snapshot=snapshot,
    )

    dumped = envelope.model_dump(mode="json")
    assert dumped["case_id"] == "case:legacy-laudo:33:88"
    assert dumped["thread_id"] == "thread:legacy-laudo:33:88"
    assert dumped["document_id"] == "document:legacy-laudo:33:88"
    assert dumped["payload"]["state"] == "needs_reviewer"
    assert dumped["payload"]["state_source"] == "technical_case_acl"
    assert dumped["payload"]["legacy_public_state"] == "aguardando"
    assert dumped["payload"]["legacy_review_status"] == "Aguardando Aval"


def test_shadow_mode_ignora_piloto_quando_flag_esta_desligada(monkeypatch) -> None:
    monkeypatch.delenv(V2_ENVELOPES_FLAG, raising=False)
    monkeypatch.delenv(V2_CASE_CORE_ACL_FLAG, raising=False)
    request = _build_request()

    result = run_inspector_case_status_shadow(
        request=request,
        usuario=_build_user(),
        legacy_payload={"estado": "sem_relatorio", "laudo_id": None, "laudo_card": None},
    )

    assert result is None
    assert not hasattr(request.state, "v2_shadow_projection_result")


def test_shadow_mode_monta_projection_em_paralelo_quando_flag_esta_ativa(monkeypatch) -> None:
    monkeypatch.setenv(V2_ENVELOPES_FLAG, "1")
    monkeypatch.delenv(V2_CASE_CORE_ACL_FLAG, raising=False)
    request = _build_request()

    result = run_inspector_case_status_shadow(
        request=request,
        usuario=_build_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 41,
            "permite_reabrir": True,
            "laudo_card": {"id": 41},
        },
    )

    assert result is not None
    assert result.compatible is True
    assert result.contract_name == "InspectorCaseStatusProjectionV1"
    assert result.projection["payload"]["legacy_laudo_id"] == 41
    assert result.projection["payload"]["state"] == "relatorio_ativo"
    assert request.state.v2_shadow_projection_result["compatible"] is True


def test_shadow_mode_com_acl_usa_case_snapshot_canonico(monkeypatch) -> None:
    monkeypatch.setenv(V2_ENVELOPES_FLAG, "1")
    monkeypatch.setenv(V2_CASE_CORE_ACL_FLAG, "1")
    request = _build_request()

    result = run_inspector_case_status_shadow(
        request=request,
        usuario=_build_user(),
        legacy_payload={
            "estado": "ajustes",
            "laudo_id": 41,
            "permite_reabrir": True,
            "laudo_card": {"id": 41, "status_revisao": "Rejeitado"},
        },
    )

    assert result is not None
    assert result.compatible is True
    assert result.projection["case_id"] == "case:legacy-laudo:33:41"
    assert result.projection["thread_id"] == "thread:legacy-laudo:33:41"
    assert result.projection["document_id"] == "document:legacy-laudo:33:41"
    assert result.projection["payload"]["state"] == "review_feedback_pending"
    assert result.projection["payload"]["state_source"] == "technical_case_acl"
    assert result.case_snapshot is not None
    assert result.case_snapshot["case_ref"]["case_id"] == "case:legacy-laudo:33:41"
    assert request.state.v2_shadow_projection_result["compatible"] is True
