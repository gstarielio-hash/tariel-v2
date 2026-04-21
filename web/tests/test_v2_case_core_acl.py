from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.database import NivelAcesso, StatusRevisao
from app.v2.acl.technical_case_core import (
    build_technical_case_ref_from_legacy_laudo,
    build_technical_case_status_snapshot_for_user,
    resolve_canonical_case_status_from_legacy,
)


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def test_case_ref_namespaced_do_laudo_legado() -> None:
    case_ref = build_technical_case_ref_from_legacy_laudo(
        tenant_id=33,
        legacy_laudo_id=88,
        correlation_id="corr-1",
    )

    dumped = case_ref.model_dump(mode="json")
    assert dumped["tenant_id"] == "33"
    assert dumped["legacy_laudo_id"] == 88
    assert dumped["case_id"] == "case:legacy-laudo:33:88"
    assert dumped["thread_id"] == "thread:legacy-laudo:33:88"
    assert dumped["document_id"] == "document:legacy-laudo:33:88"
    assert dumped["identity_namespace"] == "legacy_laudo"
    assert dumped["correlation_id"] == "corr-1"


@pytest.mark.parametrize(
    ("legacy_public_state", "legacy_review_status", "allows_reopen", "has_active_report", "expected"),
    [
        ("sem_relatorio", None, False, False, "draft"),
        ("relatorio_ativo", StatusRevisao.RASCUNHO.value, False, True, "collecting_evidence"),
        ("aguardando", StatusRevisao.AGUARDANDO.value, False, True, "needs_reviewer"),
        ("ajustes", StatusRevisao.REJEITADO.value, True, True, "review_feedback_pending"),
        ("aprovado", StatusRevisao.APROVADO.value, False, True, "approved"),
    ],
)
def test_status_canonico_do_caso_normaliza_estado_legado(
    legacy_public_state: str,
    legacy_review_status: str | None,
    allows_reopen: bool,
    has_active_report: bool,
    expected: str,
) -> None:
    assert (
        resolve_canonical_case_status_from_legacy(
            legacy_public_state=legacy_public_state,
            legacy_review_status=legacy_review_status,
            allows_reopen=allows_reopen,
            has_active_report=has_active_report,
        )
        == expected
    )


def test_snapshot_canonico_do_caso_reflete_status_legado_observado() -> None:
    legacy_payload = {
        "estado": "aguardando",
        "laudo_id": 55,
        "permite_reabrir": False,
        "laudo_card": {
            "id": 55,
            "status_revisao": StatusRevisao.AGUARDANDO.value,
            "status_card": "aguardando",
        },
    }

    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload=legacy_payload,
    )

    dumped = snapshot.model_dump(mode="json")
    assert dumped["tenant_id"] == "33"
    assert dumped["canonical_status"] == "needs_reviewer"
    assert dumped["legacy_public_state"] == "aguardando"
    assert dumped["legacy_status_card"] == "aguardando"
    assert dumped["legacy_review_status"] == StatusRevisao.AGUARDANDO.value
    assert dumped["allowed_surface_actions"] == ["mesa_approve", "mesa_return"]
    assert [item["target_status"] for item in dumped["allowed_lifecycle_transitions"]] == [
        "em_revisao_mesa",
        "devolvido_para_correcao",
        "aprovado",
    ]
    assert dumped["case_ref"]["case_id"] == "case:legacy-laudo:33:55"
    assert dumped["case_ref"]["thread_id"] == "thread:legacy-laudo:33:55"
    assert dumped["case_ref"]["document_id"] == "document:legacy-laudo:33:55"
