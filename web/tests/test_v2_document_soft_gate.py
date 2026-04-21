from __future__ import annotations

from types import SimpleNamespace

from app.shared.database import StatusRevisao, TemplateLaudo, Usuario
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.billing import build_tenant_policy_capability_snapshot
from app.v2.contracts.provenance import ProvenanceEntry, build_content_origin_summary
from app.v2.document import (
    build_canonical_document_facade,
    build_document_soft_gate_route_context,
    build_document_soft_gate_trace,
)


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=1,
    )


def test_shape_da_trace_documental_soft_gate() -> None:
    provenance = build_content_origin_summary(
        entries=[
            ProvenanceEntry(
                origin_kind="legacy_unknown",
                source="package.form_data",
                confidence="legacy_unknown",
                signal_count=1,
            )
        ]
    )
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
        },
        content_origin_summary=provenance,
    )
    facade = build_canonical_document_facade(
        banco=None,
        case_snapshot=snapshot,
        source_channel="review_api",
        template_key="padrao",
        provenance_summary=provenance,
        current_review_status=StatusRevisao.AGUARDANDO.value,
        has_form_data=True,
        has_ai_draft=True,
    )
    trace = build_document_soft_gate_trace(
        case_snapshot=snapshot,
        document_facade=facade,
        route_context=build_document_soft_gate_route_context(
            route_name="obter_pacote_mesa_laudo",
            route_path="/revisao/api/laudo/88/pacote",
            http_method="GET",
            source_channel="review_api",
            operation_kind="review_package_read",
            side_effect_free=True,
            legacy_pipeline_name="legacy_review_package",
        ),
    )

    dumped = trace.model_dump(mode="json")
    assert dumped["contract_name"] == "DocumentSoftGateTraceV1"
    assert dumped["decision"]["contract_name"] == "DocumentSoftGateDecisionV1"
    assert dumped["route_context"]["contract_name"] == "DocumentSoftGateRouteContextV1"
    assert dumped["decision"]["materialization_would_be_blocked"] is True
    assert dumped["decision"]["issue_would_be_blocked"] is True
    blocker_codes = {item["blocker_code"] for item in dumped["decision"]["blockers"]}
    assert "template_not_bound" in blocker_codes
    assert "document_source_insufficient" in blocker_codes
    assert "review_requirement_not_satisfied" in blocker_codes


def test_soft_gate_permite_materializacao_e_emissao_quando_sinais_canonicos_estao_satisfeitos(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        template = TemplateLaudo(
            empresa_id=usuario.empresa_id,
            criado_por_id=usuario.id,
            nome="Template Padrao",
            codigo_template="padrao",
            versao=2,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            status_template="ativo",
            arquivo_pdf_base="/tmp/template_gate_soft.pdf",
            mapeamento_campos_json={},
            documento_editor_json=None,
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
        banco.add(template)
        banco.flush()

        provenance = build_content_origin_summary(
            entries=[
                ProvenanceEntry(
                    origin_kind="human",
                    source="package.message_summary",
                    confidence="confirmed",
                    signal_count=3,
                )
            ]
        )
        snapshot = build_technical_case_status_snapshot_for_user(
            usuario=usuario,
            legacy_payload={
                "estado": "aprovado",
                "laudo_id": 91,
                "permite_reabrir": False,
                "laudo_card": {"id": 91, "status_revisao": StatusRevisao.APROVADO.value},
            },
            content_origin_summary=provenance,
        )
        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=snapshot,
            source_channel="review_api",
            template_key="padrao",
            provenance_summary=provenance,
            current_review_status=StatusRevisao.APROVADO.value,
            has_form_data=True,
            has_ai_draft=False,
        )

    trace = build_document_soft_gate_trace(
        case_snapshot=snapshot,
        document_facade=facade,
        route_context=build_document_soft_gate_route_context(
            route_name="obter_pacote_mesa_laudo",
            route_path="/revisao/api/laudo/91/pacote",
            http_method="GET",
            source_channel="review_api",
            operation_kind="review_package_read",
            side_effect_free=True,
            legacy_pipeline_name="legacy_review_package",
        ),
    )

    assert trace.decision.materialization_would_be_blocked is False
    assert trace.decision.issue_would_be_blocked is False
    assert trace.decision.blockers == []


def test_soft_gate_bloqueia_materializacao_e_emissao_quando_tenant_esta_bloqueado(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        template = TemplateLaudo(
            empresa_id=usuario.empresa_id,
            criado_por_id=usuario.id,
            nome="Template Padrao",
            codigo_template="padrao",
            versao=3,
            ativo=True,
            base_recomendada_fixa=False,
            modo_editor="legado_pdf",
            status_template="ativo",
            arquivo_pdf_base="/tmp/template_gate_soft_blocked.pdf",
            mapeamento_campos_json={},
            documento_editor_json=None,
            assets_json=[],
            estilo_json={},
            observacoes=None,
        )
        banco.add(template)
        banco.flush()

        provenance = build_content_origin_summary(
            entries=[
                ProvenanceEntry(
                    origin_kind="human",
                    source="package.message_summary",
                    confidence="confirmed",
                    signal_count=2,
                )
            ]
        )
        snapshot = build_technical_case_status_snapshot_for_user(
            usuario=usuario,
            legacy_payload={
                "estado": "aprovado",
                "laudo_id": 92,
                "permite_reabrir": False,
                "laudo_card": {"id": 92, "status_revisao": StatusRevisao.APROVADO.value},
            },
            content_origin_summary=provenance,
        )
        facade = build_canonical_document_facade(
            banco=banco,
            case_snapshot=snapshot,
            source_channel="review_api",
            template_key="padrao",
            tenant_policy_context=build_tenant_policy_capability_snapshot(
                tenant_id=usuario.empresa_id,
                plan_name="Intermediario",
                tenant_status="blocked",
                upload_doc_enabled=True,
                deep_research_enabled=False,
            ),
            provenance_summary=provenance,
            current_review_status=StatusRevisao.APROVADO.value,
            has_form_data=True,
            has_ai_draft=False,
        )

    trace = build_document_soft_gate_trace(
        case_snapshot=snapshot,
        document_facade=facade,
        route_context=build_document_soft_gate_route_context(
            route_name="obter_pacote_mesa_laudo",
            route_path="/revisao/api/laudo/92/pacote",
            http_method="GET",
            source_channel="review_api",
            operation_kind="review_package_read",
            side_effect_free=True,
            legacy_pipeline_name="legacy_review_package",
        ),
    )

    blocker_codes = {item.blocker_code for item in trace.decision.blockers}
    assert trace.decision.materialization_would_be_blocked is True
    assert trace.decision.issue_would_be_blocked is True
    assert "materialization_disallowed_by_policy" in blocker_codes
    assert "issue_disallowed_by_policy" in blocker_codes
    assert trace.decision.policy_summary["policy_source_summary"]["document"]["policy_source_kind"] == "tenant"
