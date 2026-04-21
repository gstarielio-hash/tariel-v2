from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from starlette.requests import Request

import app.domains.admin.services as admin_services
from app.domains.chat.laudo_service import obter_status_relatorio_resposta
from app.domains.mesa.contracts import (
    MensagemPacoteMesa,
    PacoteMesaLaudo,
    ResumoEvidenciasMesa,
    ResumoMensagensMesa,
    ResumoPendenciasMesa,
    RevisaoPacoteMesa,
)
from app.domains.revisor.mesa_api import obter_pacote_mesa_laudo
from app.shared.database import (
    EvidenceMesaStatus,
    EvidenceOperationalStatus,
    EvidenceValidation,
    Laudo,
    NivelAcesso,
    OperationalIrregularity,
    OperationalIrregularityStatus,
    StatusLaudo,
    StatusRevisao,
    Usuario,
)
from app.v2.acl.technical_case_core import build_technical_case_status_snapshot_for_user
from app.v2.billing import build_tenant_policy_capability_snapshot
from app.v2.contracts.projections import (
    build_inspector_case_view_projection,
    build_reviewdesk_case_view_projection,
)
from app.v2.policy import build_technical_case_policy_decision


def _build_inspector_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=17,
        empresa_id=33,
        nivel_acesso=NivelAcesso.INSPETOR.value,
    )


def _build_review_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=51,
        empresa_id=33,
        nivel_acesso=NivelAcesso.REVISOR.value,
    )


def _build_inspector_request(session_data: dict[str, object] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/app/api/laudo/status",
            "headers": [],
            "query_string": b"",
            "session": session_data or {},
            "state": {},
        }
    )


def _build_review_request(query_string: str = "") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/revisao/api/laudo/88/pacote",
            "headers": [],
            "query_string": query_string.encode(),
            "state": {},
        }
    )


def _build_review_package() -> PacoteMesaLaudo:
    agora = datetime.now(timezone.utc)
    return PacoteMesaLaudo(
        laudo_id=88,
        codigo_hash="abc123ef",
        tipo_template="padrao",
        setor_industrial="NR Teste",
        status_revisao=StatusRevisao.AGUARDANDO.value,
        status_conformidade=StatusLaudo.PENDENTE.value,
        criado_em=agora,
        atualizado_em=agora,
        tempo_em_campo_minutos=42,
        ultima_interacao_em=agora,
        inspetor_id=17,
        revisor_id=51,
        dados_formulario={"campo": "valor"},
        parecer_ia="Rascunho de apoio",
        resumo_mensagens=ResumoMensagensMesa(total=10, inspetor=4, ia=3, mesa=2, sistema_outros=1),
        resumo_evidencias=ResumoEvidenciasMesa(total=3, textuais=1, fotos=1, documentos=1),
        resumo_pendencias=ResumoPendenciasMesa(total=2, abertas=1, resolvidas=1),
        pendencias_abertas=[
            MensagemPacoteMesa(
                id=1,
                tipo="humano_eng",
                texto="Ajustar evidencia",
                criado_em=agora,
                remetente_id=51,
                lida=False,
            )
        ],
        pendencias_resolvidas_recentes=[
            MensagemPacoteMesa(
                id=2,
                tipo="humano_eng",
                texto="Ajuste resolvido",
                criado_em=agora,
                remetente_id=51,
                lida=True,
            )
        ],
        whispers_recentes=[
            MensagemPacoteMesa(
                id=3,
                tipo="humano_insp",
                texto="Campo respondeu",
                criado_em=agora,
                remetente_id=17,
                lida=False,
                referencia_mensagem_id=1,
            )
        ],
        revisoes_recentes=[
            RevisaoPacoteMesa(
                numero_versao=1,
                origem="ia",
                resumo="Primeira revisao",
                confianca_geral="alta",
                criado_em=agora,
            )
        ],
    )


def test_policy_engine_shape_e_defaults_conservadores_sem_laudo_ativo() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_inspector_user(),
        legacy_payload={"estado": "sem_relatorio", "laudo_id": None},
    )

    decision = build_technical_case_policy_decision(
        case_snapshot=snapshot,
        template_key=None,
    )

    dumped = decision.model_dump(mode="json")
    assert dumped["contract_name"] == "TechnicalCasePolicyDecisionV1"
    assert dumped["summary"]["contract_name"] == "PolicyDecisionSummaryV1"
    assert dumped["summary"]["review_required"] is False
    assert dumped["summary"]["review_mode"] == "none"
    assert dumped["summary"]["engineer_approval_required"] is False
    assert dumped["summary"]["document_materialization_allowed"] is False
    assert dumped["summary"]["document_issue_allowed"] is False
    assert dumped["summary"]["primary_policy_source_kind"] == "default"


def test_policy_engine_reflete_gate_minimo_para_caso_aprovado() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_inspector_user(),
        legacy_payload={
            "estado": "aprovado",
            "laudo_id": 88,
            "permite_reabrir": False,
            "laudo_card": {
                "id": 88,
                "status_revisao": StatusRevisao.APROVADO.value,
                "status_card": "aprovado",
            },
        },
    )

    decision = build_technical_case_policy_decision(
        case_snapshot=snapshot,
        template_key="padrao",
        laudo_type="padrao",
        document_type="padrao",
    )

    assert decision.summary.review_required is True
    assert decision.summary.review_mode == "mesa_required"
    assert decision.summary.engineer_approval_required is True
    assert decision.summary.document_materialization_allowed is True
    assert decision.summary.document_issue_allowed is True
    assert decision.summary.source_summary["document"]["policy_source_kind"] == "system"


def test_policy_engine_libera_mobile_autonomous_quando_report_pack_piloto_esta_pronto() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_inspector_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 88,
            "permite_reabrir": False,
            "laudo_card": {
                "id": 88,
                "status_revisao": StatusRevisao.RASCUNHO.value,
                "status_card": "aberto",
            },
        },
    )

    decision = build_technical_case_policy_decision(
        case_snapshot=snapshot,
        template_key="nr35_linha_vida",
        laudo_type="nr35_linha_vida",
        document_type="nr35_linha_vida",
        report_pack_draft={
            "template_key": "nr35_linha_vida",
            "quality_gates": {
                "autonomy_ready": True,
                "final_validation_mode": "mobile_autonomous",
            },
            "telemetry": {
                "entry_mode_effective": "evidence_first",
            },
        },
    )

    assert decision.summary.review_required is False
    assert decision.summary.review_mode == "mobile_autonomous"
    assert decision.summary.engineer_approval_required is False
    assert "autonomia mobile" in str(decision.review.rationale or "").lower()


def test_policy_engine_mobile_autonomous_respeita_allowlist_de_tenant(monkeypatch) -> None:
    monkeypatch.setenv("TARIEL_V2_MOBILE_AUTONOMY_TENANTS", "99")

    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_inspector_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 89,
            "permite_reabrir": False,
            "laudo_card": {
                "id": 89,
                "status_revisao": StatusRevisao.RASCUNHO.value,
                "status_card": "aberto",
            },
        },
    )

    decision = build_technical_case_policy_decision(
        case_snapshot=snapshot,
        template_key="cbmgo",
        laudo_type="cbmgo",
        document_type="cbmgo",
        report_pack_draft={
            "template_key": "cbmgo",
            "modeled": True,
            "quality_gates": {
                "autonomy_ready": True,
                "final_validation_mode": "mobile_autonomous",
            },
            "telemetry": {
                "entry_mode_effective": "evidence_first",
            },
        },
    )

    assert decision.summary.review_mode == "mobile_review_allowed"
    assert decision.summary.review_required is False
    assert decision.summary.tenant_entitlements["mobile_review_allowed"] is True
    assert decision.summary.tenant_entitlements["mobile_autonomous_allowed"] is False
    assert any(
        flag["code"] == "tenant_not_entitled_mobile_autonomy"
        for flag in decision.summary.red_flags
    )


def test_policy_engine_runtime_red_flags_promovem_caso_para_mesa(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="nr35_linha_vida",
            catalog_family_key="nr35_linha_vida",
            status_revisao=StatusRevisao.RASCUNHO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        banco.add(
            EvidenceValidation(
                laudo_id=laudo.id,
                empresa_id=usuario.empresa_id,
                family_key="nr35_linha_vida",
                evidence_key="slot:foto_placa",
                operational_status=EvidenceOperationalStatus.REPLACED.value,
                mesa_status=EvidenceMesaStatus.NEEDS_RECHECK.value,
            )
        )
        banco.add(
            OperationalIrregularity(
                laudo_id=laudo.id,
                empresa_id=usuario.empresa_id,
                family_key="nr35_linha_vida",
                irregularity_type="field_reopened",
                severity="warning",
                status=OperationalIrregularityStatus.OPEN.value,
                detected_by="mesa",
                block_key="inspecao_visual",
            )
        )
        banco.flush()

        snapshot = build_technical_case_status_snapshot_for_user(
            usuario=usuario,
            legacy_payload={
                "estado": "relatorio_ativo",
                "laudo_id": laudo.id,
                "permite_reabrir": False,
                "laudo_card": {
                    "id": laudo.id,
                    "status_revisao": StatusRevisao.RASCUNHO.value,
                    "status_card": "aberto",
                },
            },
            laudo=laudo,
        )

        decision = build_technical_case_policy_decision(
            banco=banco,
            case_snapshot=snapshot,
            template_key="nr35_linha_vida",
            laudo_type="nr35_linha_vida",
            document_type="nr35_linha_vida",
            report_pack_draft={
                "template_key": "nr35_linha_vida",
                "quality_gates": {
                    "autonomy_ready": True,
                    "final_validation_mode": "mobile_autonomous",
                },
                "telemetry": {
                    "entry_mode_effective": "evidence_first",
                },
            },
        )

    assert decision.summary.review_mode == "mesa_required"
    assert decision.summary.runtime_operational_context["open_return_to_inspector_count"] == 1
    assert decision.summary.runtime_operational_context["needs_recheck_count"] == 1
    assert any(
        item["code"] == "runtime_return_to_inspector_open"
        for item in decision.summary.red_flags
    )
    assert any(
        item["code"] == "runtime_evidence_needs_recheck"
        for item in decision.summary.red_flags
    )


def test_policy_engine_bloqueia_materializacao_e_emissao_quando_tenant_esta_bloqueado() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_inspector_user(),
        legacy_payload={
            "estado": "aprovado",
            "laudo_id": 88,
            "permite_reabrir": False,
            "laudo_card": {
                "id": 88,
                "status_revisao": StatusRevisao.APROVADO.value,
                "status_card": "aprovado",
            },
        },
    )
    tenant_policy_context = build_tenant_policy_capability_snapshot(
        tenant_id=33,
        plan_name="Intermediario",
        tenant_status="blocked",
        upload_doc_enabled=True,
        deep_research_enabled=False,
    )

    decision = build_technical_case_policy_decision(
        case_snapshot=snapshot,
        template_key="padrao",
        laudo_type="padrao",
        document_type="padrao",
        tenant_policy_context=tenant_policy_context,
    )

    assert decision.summary.review_required is True
    assert decision.summary.review_mode == "mesa_required"
    assert decision.summary.document_materialization_allowed is False
    assert decision.summary.document_issue_allowed is False
    assert decision.summary.primary_policy_source_kind == "tenant"
    assert decision.summary.source_summary["document"]["policy_source_kind"] == "tenant"
    assert "tenant_status=blocked" in str(decision.document.rationale or "")


def test_policy_engine_aplica_entitlement_por_tenant_com_downgrade_para_mobile_review(
    ambiente_critico,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TARIEL_V2_MOBILE_AUTONOMY_TEMPLATES", "nr35_linha_vida")

    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_inspector_user(),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 91,
            "permite_reabrir": False,
            "laudo_card": {
                "id": 91,
                "status_revisao": StatusRevisao.RASCUNHO.value,
                "status_card": "aberto",
            },
        },
    )

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_exibicao="NR35 · Linha de Vida",
            macro_categoria="NR35",
            status_catalogo="publicado",
            review_policy_json_text=json.dumps(
                {
                    "default_review_mode": "mobile_review_allowed",
                    "max_review_mode": "mobile_autonomous",
                    "tenant_entitlements": {
                        "requires_release_active": True,
                        "mobile_review_allowed_plans": ["intermediario"],
                        "mobile_autonomous_allowed_plans": ["ilimitado"],
                    },
                }
            ),
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr35_inspecao_linha_de_vida",
            release_status="active",
            criado_por_id=ids["admin_a"],
        )
        tenant_policy_context = build_tenant_policy_capability_snapshot(
            tenant_id=ids["empresa_a"],
            plan_name="Intermediario",
            tenant_status="active",
            upload_doc_enabled=True,
            deep_research_enabled=False,
        )

        decision = build_technical_case_policy_decision(
            banco=banco,
            case_snapshot=snapshot,
            template_key="nr35_linha_vida",
            family_key="nr35_inspecao_linha_de_vida",
            variant_key="premium_campo",
            laudo_type="nr35_linha_vida",
            document_type="nr35_linha_vida",
            tenant_policy_context=tenant_policy_context,
            report_pack_draft={
                "template_key": "nr35_linha_vida",
                "catalog_family_key": "nr35_inspecao_linha_de_vida",
                "quality_gates": {
                    "autonomy_ready": True,
                    "final_validation_mode": "mobile_autonomous",
                },
                "telemetry": {
                    "entry_mode_effective": "evidence_first",
                },
            },
        )

    assert decision.summary.review_mode == "mobile_review_allowed"
    assert decision.summary.review_required is False
    assert decision.summary.tenant_entitlements["mobile_review_allowed"] is True
    assert decision.summary.tenant_entitlements["mobile_autonomous_allowed"] is False
    assert any(
        flag["code"] == "tenant_not_entitled_mobile_autonomy"
        for flag in decision.summary.red_flags
    )


def test_policy_engine_release_governance_override_libera_mobile_review_sem_plano(
    ambiente_critico,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TARIEL_V2_MOBILE_AUTONOMY_TEMPLATES", "nr35_linha_vida")

    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=SimpleNamespace(
            id=17,
            empresa_id=ids["empresa_a"],
            nivel_acesso=NivelAcesso.INSPETOR.value,
        ),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 94,
            "permite_reabrir": False,
            "laudo_card": {
                "id": 94,
                "status_revisao": StatusRevisao.RASCUNHO.value,
                "status_card": "aberto",
            },
        },
    )

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr35_inspecao_linha_de_vida",
            nome_exibicao="NR35 · Linha de Vida",
            macro_categoria="NR35",
            status_catalogo="publicado",
            review_policy_json_text=json.dumps(
                {
                    "default_review_mode": "mobile_autonomous",
                    "max_review_mode": "mobile_autonomous",
                    "tenant_entitlements": {
                        "requires_release_active": True,
                        "mobile_review_allowed_plans": ["ilimitado"],
                        "mobile_autonomous_allowed_plans": ["ilimitado"],
                    },
                }
            ),
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr35_inspecao_linha_de_vida",
            release_status="active",
            force_review_mode="mobile_review_allowed",
            max_review_mode="mobile_review_allowed",
            mobile_review_override="allow",
            mobile_autonomous_override="deny",
            criado_por_id=ids["admin_a"],
        )
        tenant_policy_context = build_tenant_policy_capability_snapshot(
            tenant_id=ids["empresa_a"],
            plan_name="Intermediario",
            tenant_status="active",
            upload_doc_enabled=True,
            deep_research_enabled=False,
        )

        decision = build_technical_case_policy_decision(
            banco=banco,
            case_snapshot=snapshot,
            template_key="nr35_linha_vida",
            family_key="nr35_inspecao_linha_de_vida",
            variant_key="prime_site",
            laudo_type="nr35_linha_vida",
            document_type="nr35_linha_vida",
            tenant_policy_context=tenant_policy_context,
            report_pack_draft={
                "template_key": "nr35_linha_vida",
                "catalog_family_key": "nr35_inspecao_linha_de_vida",
                "quality_gates": {
                    "autonomy_ready": True,
                    "final_validation_mode": "mobile_autonomous",
                },
                "telemetry": {
                    "entry_mode_effective": "evidence_first",
                },
            },
        )

    assert decision.summary.review_mode == "mobile_review_allowed"
    assert decision.summary.review_required is False
    assert decision.summary.tenant_entitlements["mobile_review_allowed"] is True
    assert decision.summary.tenant_entitlements["mobile_autonomous_allowed"] is False
    assert decision.summary.tenant_entitlements["force_review_mode"] == "mobile_review_allowed"
    assert decision.summary.tenant_entitlements["effective_max_review_mode"] == "mobile_review_allowed"


def test_policy_engine_eleva_para_mesa_com_red_flags_de_release_e_evidencia(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=SimpleNamespace(
            id=17,
            empresa_id=ids["empresa_a"],
            nivel_acesso=NivelAcesso.INSPETOR.value,
        ),
        legacy_payload={
            "estado": "relatorio_ativo",
            "laudo_id": 92,
            "permite_reabrir": False,
            "laudo_card": {
                "id": 92,
                "status_revisao": StatusRevisao.RASCUNHO.value,
                "status_card": "aberto",
            },
        },
    )

    with SessionLocal() as banco:
        admin_services.upsert_familia_catalogo(
            banco,
            family_key="nr13_inspecao_caldeira",
            nome_exibicao="NR13 · Caldeira",
            macro_categoria="NR13",
            status_catalogo="publicado",
            review_policy_json_text=json.dumps(
                {
                    "default_review_mode": "mobile_review_allowed",
                    "block_on_missing_required_evidence": True,
                    "tenant_entitlements": {
                        "requires_release_active": True,
                    },
                }
            ),
            criado_por_id=ids["admin_a"],
        )
        admin_services.upsert_tenant_family_release(
            banco,
            tenant_id=ids["empresa_a"],
            family_key="nr13_inspecao_caldeira",
            release_status="paused",
            criado_por_id=ids["admin_a"],
        )
        tenant_policy_context = build_tenant_policy_capability_snapshot(
            tenant_id=ids["empresa_a"],
            plan_name="Intermediario",
            tenant_status="active",
            upload_doc_enabled=True,
            deep_research_enabled=False,
        )

        decision = build_technical_case_policy_decision(
            banco=banco,
            case_snapshot=snapshot,
            template_key="nr13",
            family_key="nr13_inspecao_caldeira",
            variant_key="premium_campo",
            laudo_type="nr13",
            document_type="nr13",
            tenant_policy_context=tenant_policy_context,
            report_pack_draft={
                "template_key": "nr13",
                "catalog_family_key": "nr13_inspecao_caldeira",
                "quality_gates": {
                    "autonomy_ready": False,
                    "final_validation_mode": "mobile_review_allowed",
                    "missing_evidence": [
                        {
                            "code": "placa_identificacao_ausente",
                            "message": "Falta a evidência da placa.",
                        }
                    ],
                },
                "telemetry": {
                    "entry_mode_effective": "evidence_first",
                },
            },
        )

    red_flag_codes = {flag["code"] for flag in decision.summary.red_flags}
    assert decision.summary.review_mode == "mesa_required"
    assert decision.summary.review_required is True
    assert decision.summary.tenant_entitlements["family_release_active"] is False
    assert {"tenant_family_release_inactive", "missing_required_evidence"} <= red_flag_codes


def test_projecoes_canonicas_carregam_policy_summary() -> None:
    snapshot = build_technical_case_status_snapshot_for_user(
        usuario=_build_review_user(),
        legacy_payload={
            "estado": "aguardando",
            "laudo_id": 88,
            "status_card": "aguardando",
            "permite_reabrir": False,
            "laudo_card": {"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
        },
    )
    decision = build_technical_case_policy_decision(
        case_snapshot=snapshot,
        template_key="padrao",
        laudo_type="padrao",
        document_type="padrao",
    )

    inspector_projection = build_inspector_case_view_projection(
        case_snapshot=snapshot,
        actor_id=17,
        actor_role="inspetor",
        source_channel="web_app",
        allows_edit=False,
        has_interaction=True,
        report_types={"padrao": "Inspecao Geral (Padrao)"},
        laudo_card={"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
        policy_decision=decision,
    )
    review_projection = build_reviewdesk_case_view_projection(
        case_snapshot=snapshot,
        pacote=_build_review_package(),
        actor_id=51,
        actor_role="revisor",
        source_channel="review_api",
        policy_decision=decision,
    )

    inspector_payload = inspector_projection.model_dump(mode="json")["payload"]
    review_payload = review_projection.model_dump(mode="json")["payload"]
    assert inspector_payload["policy_summary"]["contract_name"] == "PolicyDecisionSummaryV1"
    assert inspector_payload["review_required"] is True
    assert inspector_payload["review_mode"] == "mesa_required"
    assert inspector_payload["engineer_approval_required"] is True
    assert inspector_payload["materialization_allowed"] is True
    assert inspector_payload["issue_allowed"] is False
    assert review_payload["policy_summary"]["contract_name"] == "PolicyDecisionSummaryV1"
    assert review_payload["policy_source_summary"]["review"]["policy_source_kind"] == "default"
    assert review_payload["materialization_allowed"] is True


def test_status_relatorio_com_policy_engine_preserva_payload_publico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["inspetor_a"])
        assert usuario is not None

        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        sessao = {"laudo_ativo_id": laudo.id, "estado_relatorio": "aguardando"}

        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_INSPECTOR_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_POLICY_ENGINE", raising=False)
        payload_base, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=_build_inspector_request(dict(sessao)),
                usuario=usuario,
                banco=banco,
            )
        )

        request_policy = _build_inspector_request(dict(sessao))
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_INSPECTOR_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_POLICY_ENGINE", "1")
        payload_policy, _ = asyncio.run(
            obter_status_relatorio_resposta(
                request=request_policy,
                usuario=usuario,
                banco=banco,
            )
        )

    assert payload_policy == payload_base
    assert request_policy.state.v2_policy_decision_summary["contract_name"] == "PolicyDecisionSummaryV1"
    assert request_policy.state.v2_policy_decision_summary["review_mode"] == "mesa_required"
    assert request_policy.state.v2_inspector_projection_result["policy"]["review_required"] is True


def test_pacote_mesa_com_policy_engine_preserva_payload_publico(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        revisor = banco.get(Usuario, ids["revisor_a"])
        assert revisor is not None

        laudo = Laudo(
            empresa_id=revisor.empresa_id,
            usuario_id=ids["inspetor_a"],
            setor_industrial="NR Teste",
            tipo_template="padrao",
            status_revisao=StatusRevisao.AGUARDANDO.value,
            codigo_hash=uuid.uuid4().hex,
        )
        banco.add(laudo)
        banco.flush()

        request_base = _build_review_request()
        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_REVIEW_DESK_PROJECTION", raising=False)
        monkeypatch.delenv("TARIEL_V2_POLICY_ENGINE", raising=False)
        response_base = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_base,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_base = json.loads(response_base.body)

        request_policy = _build_review_request()
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_REVIEW_DESK_PROJECTION", "1")
        monkeypatch.setenv("TARIEL_V2_POLICY_ENGINE", "1")
        response_policy = asyncio.run(
            obter_pacote_mesa_laudo(
                laudo_id=laudo.id,
                request=request_policy,
                limite_whispers=80,
                limite_pendencias=80,
                limite_revisoes=10,
                usuario=revisor,
                banco=banco,
            )
        )
        payload_policy = json.loads(response_policy.body)

    assert payload_policy == payload_base
    assert request_policy.state.v2_policy_decision_summary["contract_name"] == "PolicyDecisionSummaryV1"
    assert request_policy.state.v2_policy_decision_summary["review_required"] is True
    assert request_policy.state.v2_reviewdesk_projection_result["policy"]["review_mode"] == "mesa_required"
