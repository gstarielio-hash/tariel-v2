from __future__ import annotations

from types import SimpleNamespace

from app.shared.database import StatusRevisao
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.document import (
    build_canonical_document_facade,
    build_document_hard_gate_decision,
    build_document_hard_gate_enforcement_result,
    build_document_soft_gate_route_context,
    build_document_soft_gate_trace,
)


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=1,
    )


def _build_soft_gate_trace() -> object:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 88,
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.RASCUNHO.value},
        },
    )
    facade = build_canonical_document_facade(
        banco=None,
        case_snapshot=snapshot,
        source_channel="web_app",
        template_key="padrao",
        current_review_status=StatusRevisao.RASCUNHO.value,
        has_form_data=True,
        has_ai_draft=False,
    )
    return build_document_soft_gate_trace(
        case_snapshot=snapshot,
        document_facade=facade,
        route_context=build_document_soft_gate_route_context(
            route_name="finalizar_relatorio_resposta",
            route_path="/app/api/laudo/88/finalizar",
            http_method="POST",
            source_channel="web_app",
            operation_kind="report_finalize",
            side_effect_free=False,
            legacy_pipeline_name="legacy_report_finalize",
        ),
    )


def test_hard_gate_desligado_fica_em_modo_disabled(monkeypatch) -> None:
    monkeypatch.delenv("TARIEL_V2_DOCUMENT_HARD_GATE", raising=False)
    monkeypatch.delenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", raising=False)
    monkeypatch.delenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", raising=False)
    monkeypatch.delenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", raising=False)

    decision = build_document_hard_gate_decision(
        soft_gate_trace=_build_soft_gate_trace(),
        remote_host="testclient",
    )

    assert decision.hard_gate_enabled is False
    assert decision.mode == "disabled"
    assert decision.would_block is True
    assert decision.did_block is False


def test_hard_gate_shadow_only_quando_enforce_nao_esta_efetivamente_habilitado(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.delenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", raising=False)
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", "33")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "report_finalize")

    decision = build_document_hard_gate_decision(
        soft_gate_trace=_build_soft_gate_trace(),
        remote_host="testclient",
    )
    result = build_document_hard_gate_enforcement_result(decision=decision)

    assert decision.hard_gate_enabled is True
    assert decision.shadow_only is True
    assert decision.enforce_enabled is False
    assert decision.would_block is True
    assert decision.did_block is False
    assert result.blocked_response_status is None


def test_hard_gate_enforce_pede_allowlist_de_tenant_e_operacao(monkeypatch) -> None:
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE", "1")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS", "99")
    monkeypatch.setenv("TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS", "review_issue")

    decision = build_document_hard_gate_decision(
        soft_gate_trace=_build_soft_gate_trace(),
        remote_host="testclient",
    )

    assert decision.enforce_requested is True
    assert decision.tenant_allowlisted is False
    assert decision.operation_allowlisted is False
    assert decision.enforce_enabled is False
    assert decision.mode == "shadow_only"
    assert decision.did_block is False
