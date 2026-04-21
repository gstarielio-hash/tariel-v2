from __future__ import annotations

import uuid

from starlette.requests import Request

import app.v2.case_runtime as case_runtime
from app.shared.database import Laudo, StatusRevisao, Usuario
from app.v2.case_runtime import (
    bind_technical_case_runtime_bundle_to_request,
    build_legacy_case_status_payload_from_laudo,
    build_technical_case_context_bundle,
)


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/app/api/laudo/status",
            "headers": [],
            "query_string": b"",
            "session": {},
            "state": {},
        }
    )


def _criar_laudo(
    *,
    usuario: Usuario,
    banco,
) -> Laudo:
    laudo = Laudo(
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        setor_industrial="NR Teste",
        tipo_template="padrao",
        status_revisao=StatusRevisao.AGUARDANDO.value,
        codigo_hash=uuid.uuid4().hex,
        dados_formulario={"campo": "valor"},
        parecer_ia="Rascunho tecnico",
        report_pack_draft_json={
            "quality_gates": {
                "final_validation_mode": "mesa_required",
                "missing_evidence": [],
            }
        },
    )
    banco.add(laudo)
    banco.flush()
    return laudo


def test_context_bundle_puro_consolida_snapshot_policy_e_documento(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        laudo = _criar_laudo(usuario=usuario, banco=banco)
        legacy_payload = build_legacy_case_status_payload_from_laudo(
            banco=banco,
            laudo=laudo,
            include_entry_mode_context=True,
        )

        bundle = build_technical_case_context_bundle(
            banco=banco,
            usuario=usuario,
            laudo=laudo,
            legacy_payload=legacy_payload,
            source_channel="web_app",
            template_key=getattr(laudo, "tipo_template", None),
            family_key=getattr(laudo, "catalog_family_key", None),
            variant_key=getattr(laudo, "catalog_variant_key", None),
            laudo_type=getattr(laudo, "tipo_template", None),
            document_type=getattr(laudo, "tipo_template", None),
            current_review_status=getattr(laudo, "status_revisao", None),
            has_form_data=bool(getattr(laudo, "dados_formulario", None)),
            has_ai_draft=bool(str(getattr(laudo, "parecer_ia", "") or "").strip()),
            report_pack_draft=getattr(laudo, "report_pack_draft_json", None),
            include_full_snapshot=True,
            include_policy_decision=True,
            include_document_facade=True,
            attach_document_shadow=True,
        )

    assert bundle.case_snapshot is not None
    assert bundle.case_snapshot.contract_name == "TechnicalCaseStatusSnapshotV1"
    assert bundle.case_snapshot.case_ref.case_id == f"case:legacy-laudo:{ids['empresa_a']}:{laudo.id}"
    assert bundle.technical_case_snapshot is not None
    assert bundle.technical_case_snapshot.contract_name == "TechnicalCaseSnapshotV1"
    assert bundle.tenant_policy_context is not None
    assert bundle.tenant_policy_context.tenant_id == str(ids["empresa_a"])
    assert bundle.policy_decision is not None
    assert bundle.policy_decision.summary.contract_name == "PolicyDecisionSummaryV1"
    assert bundle.document_facade is not None
    assert (
        bundle.document_facade.document_readiness.contract_name
        == "DocumentMaterializationReadinessV1"
    )
    assert bundle.document_shadow_result is not None
    assert bundle.document_shadow_result.contract_name == "LegacyDocumentPipelineShadowResultV1"


def test_bind_runtime_bundle_to_request_publica_summaries_canonicas(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        laudo = _criar_laudo(usuario=usuario, banco=banco)
        bundle = build_technical_case_context_bundle(
            banco=banco,
            usuario=usuario,
            laudo=laudo,
            legacy_payload=build_legacy_case_status_payload_from_laudo(
                banco=banco,
                laudo=laudo,
            ),
            source_channel="web_app",
            template_key=getattr(laudo, "tipo_template", None),
            family_key=getattr(laudo, "catalog_family_key", None),
            variant_key=getattr(laudo, "catalog_variant_key", None),
            laudo_type=getattr(laudo, "tipo_template", None),
            document_type=getattr(laudo, "tipo_template", None),
            current_review_status=getattr(laudo, "status_revisao", None),
            has_form_data=bool(getattr(laudo, "dados_formulario", None)),
            has_ai_draft=bool(str(getattr(laudo, "parecer_ia", "") or "").strip()),
            report_pack_draft=getattr(laudo, "report_pack_draft_json", None),
            include_full_snapshot=True,
            include_policy_decision=True,
            include_document_facade=True,
            attach_document_shadow=True,
        )

    request = _build_request()
    returned = bind_technical_case_runtime_bundle_to_request(
        request=request,
        bundle=bundle,
    )

    assert returned is bundle
    assert request.state.v2_case_core_snapshot["contract_name"] == "TechnicalCaseStatusSnapshotV1"
    assert request.state.v2_case_core_snapshot["case_ref"]["case_id"] == (
        f"case:legacy-laudo:{ids['empresa_a']}:{laudo.id}"
    )
    assert request.state.v2_technical_case_snapshot["contract_name"] == "TechnicalCaseSnapshotV1"
    assert request.state.v2_tenant_policy_context["tenant_id"] == str(ids["empresa_a"])
    assert request.state.v2_policy_decision_summary["contract_name"] == "PolicyDecisionSummaryV1"
    assert request.state.v2_document_facade_summary["contract_name"] == "DocumentMaterializationReadinessV1"
    assert request.state.v2_document_shadow_summary["contract_name"] == "LegacyDocumentPipelineShadowResultV1"


def test_context_bundle_allow_partial_failures_degrada_facade_sem_explodir(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None
        laudo = _criar_laudo(usuario=usuario, banco=banco)

        def _falhar_facade(*args, **kwargs):
            raise RuntimeError("facade_broken_for_test")

        monkeypatch.setattr(case_runtime, "build_canonical_document_facade", _falhar_facade)
        bundle = build_technical_case_context_bundle(
            banco=banco,
            usuario=usuario,
            laudo=laudo,
            legacy_payload=build_legacy_case_status_payload_from_laudo(
                banco=banco,
                laudo=laudo,
            ),
            source_channel="web_app",
            template_key=getattr(laudo, "tipo_template", None),
            family_key=getattr(laudo, "catalog_family_key", None),
            variant_key=getattr(laudo, "catalog_variant_key", None),
            laudo_type=getattr(laudo, "tipo_template", None),
            document_type=getattr(laudo, "tipo_template", None),
            current_review_status=getattr(laudo, "status_revisao", None),
            has_form_data=bool(getattr(laudo, "dados_formulario", None)),
            has_ai_draft=bool(str(getattr(laudo, "parecer_ia", "") or "").strip()),
            report_pack_draft=getattr(laudo, "report_pack_draft_json", None),
            include_policy_decision=True,
            include_document_facade=True,
            attach_document_shadow=True,
            allow_partial_failures=True,
        )

    assert bundle.case_snapshot is not None
    assert bundle.policy_decision is not None
    assert bundle.document_facade is None
    assert bundle.document_shadow_result is None
