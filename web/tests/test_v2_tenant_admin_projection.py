from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from starlette.requests import Request

from app.domains.cliente.dashboard_bootstrap import bootstrap_cliente
from app.shared.database import Empresa, Laudo, NivelAcesso, StatusRevisao, Usuario
from app.v2.acl.technical_case_snapshot import build_technical_case_snapshot_for_user
from app.v2.contracts.tenant_admin import build_tenant_admin_view_projection
from tests.regras_rotas_criticas_support import _criar_laudo


def _build_user(*, nivel_acesso: int = NivelAcesso.ADMIN_CLIENTE.value) -> SimpleNamespace:
    return SimpleNamespace(
        id=81,
        empresa_id=33,
        nivel_acesso=nivel_acesso,
    )


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/cliente/api/bootstrap",
            "headers": [],
            "query_string": b"",
            "state": {},
        }
    )


def test_shape_da_projecao_canonica_do_tenant_admin() -> None:
    agora = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)
    laudo_em_revisao = SimpleNamespace(
        id=88,
        empresa_id=33,
        usuario_id=17,
        revisado_por=51,
        status_revisao=StatusRevisao.AGUARDANDO.value,
        reabertura_pendente_em=None,
        reaberto_em=None,
        dados_formulario={"campo": "valor"},
        parecer_ia="Rascunho IA",
        nome_arquivo_pdf=None,
        criado_em=agora,
        atualizado_em=agora,
        revisoes=[SimpleNamespace(id=1, numero_versao=1)],
    )
    laudo_emitido = SimpleNamespace(
        id=91,
        empresa_id=33,
        usuario_id=17,
        revisado_por=51,
        status_revisao=StatusRevisao.APROVADO.value,
        reabertura_pendente_em=None,
        reaberto_em=None,
        dados_formulario={"campo": "valor"},
        parecer_ia="Rascunho IA",
        nome_arquivo_pdf="laudo_91.pdf",
        criado_em=agora,
        atualizado_em=agora,
        revisoes=[],
    )
    snapshots = [
        build_technical_case_snapshot_for_user(
            usuario=_build_user(),
            legacy_payload={
                "estado": "aguardando",
                "laudo_id": 88,
                "status_card": "aguardando",
                "permite_reabrir": False,
                "laudo_card": {"id": 88, "status_revisao": StatusRevisao.AGUARDANDO.value},
            },
            laudo=laudo_em_revisao,
            source_channel="admin_cliente_bootstrap",
        ),
        build_technical_case_snapshot_for_user(
            usuario=_build_user(),
            legacy_payload={
                "estado": "aprovado",
                "laudo_id": 91,
                "status_card": "aprovado",
                "permite_reabrir": False,
                "laudo_card": {"id": 91, "status_revisao": StatusRevisao.APROVADO.value},
            },
            laudo=laudo_emitido,
            source_channel="admin_cliente_bootstrap",
        ),
    ]

    projection = build_tenant_admin_view_projection(
        tenant_id=33,
        tenant_name="Empresa A",
        tenant_status="active",
        case_snapshots=snapshots,
        plan_name="Ilimitado",
        usage_status="estavel",
        usage_percent=40,
        recommended_plan=None,
        total_users=3,
        active_users=3,
        inspectors=1,
        reviewers=1,
        admin_clients=1,
        actor_id=81,
        actor_role="admin_cliente",
        source_channel="admin_cliente_bootstrap",
    )

    dumped = projection.model_dump(mode="json")
    assert dumped["contract_name"] == "TenantAdminViewProjectionV1"
    assert dumped["projection_audience"] == "tenant_admin_web"
    assert dumped["payload"]["tenant_summary"]["tenant_id"] == "33"
    assert dumped["payload"]["case_counts"]["total_cases"] == 2
    assert dumped["payload"]["case_counts"]["open_cases"] == 1
    assert dumped["payload"]["review_counts"]["in_review"] == 1
    assert dumped["payload"]["document_counts"]["issued_documents"] == 1
    assert dumped["payload"]["visibility_policy"]["management_projection_authoritative"] is True
    assert dumped["payload"]["visibility_policy"]["technical_access_mode"] == "surface_scoped_operational"
    assert dumped["payload"]["visibility_policy"]["per_case_visibility_configurable"] is True
    assert dumped["payload"]["visibility_policy"]["per_case_action_configurable"] is True
    assert (
        dumped["payload"]["visibility_policy"]["per_case_governance_owner"]
        == "admin_ceo_contract_setup"
    )
    assert dumped["payload"]["visibility_policy"]["commercial_operating_model"] == "standard"
    assert dumped["payload"]["visibility_policy"]["mobile_primary"] is False
    assert dumped["payload"]["visibility_policy"]["commercial_package_scope"] == "tenant_isolated_contract"
    assert dumped["payload"]["visibility_policy"]["cross_surface_session_strategy"] == "governed_links_and_grants"
    assert dumped["payload"]["visibility_policy"]["cross_surface_session_unified"] is False
    assert dumped["payload"]["visibility_policy"]["support_exceptional_protocol"] == "approval_scoped_temporary_audited"
    assert dumped["payload"]["visibility_policy"]["exceptional_support_access"] == "approval_required"
    assert dumped["payload"]["visibility_policy"]["technical_case_retention_min_days"] == 365
    assert dumped["payload"]["visibility_policy"]["issued_document_retention_min_days"] == 1825
    assert dumped["payload"]["visibility_policy"]["audit_retention_min_days"] == 1825
    assert dumped["payload"]["visibility_policy"]["human_signoff_required"] is True
    assert dumped["payload"]["visibility_policy"]["ai_assistance_audit_required"] is True
    assert "human_override_reason" in dumped["payload"]["visibility_policy"]["mandatory_audit_fields"]
    assert dumped["payload"]["visibility_policy"]["audit_scope"] == "tenant_operational_timeline"
    assert dumped["payload"]["allowed_document_refs"] == ["document:legacy-laudo:33:91"]


def test_projecao_tenant_admin_oculta_refs_caso_a_caso_quando_tenant_usa_so_resumos() -> None:
    agora = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)
    laudo_emitido = SimpleNamespace(
        id=91,
        empresa_id=33,
        usuario_id=17,
        revisado_por=51,
        status_revisao=StatusRevisao.APROVADO.value,
        reabertura_pendente_em=None,
        reaberto_em=None,
        dados_formulario={"campo": "valor"},
        parecer_ia="Rascunho IA",
        nome_arquivo_pdf="laudo_91.pdf",
        criado_em=agora,
        atualizado_em=agora,
        revisoes=[],
    )
    snapshot = build_technical_case_snapshot_for_user(
        usuario=_build_user(),
        legacy_payload={
            "estado": "aprovado",
            "laudo_id": 91,
            "status_card": "aprovado",
            "permite_reabrir": False,
            "laudo_card": {"id": 91, "status_revisao": StatusRevisao.APROVADO.value},
        },
        laudo=laudo_emitido,
        source_channel="admin_cliente_bootstrap",
    )

    projection = build_tenant_admin_view_projection(
        tenant_id=33,
        tenant_name="Empresa A",
        tenant_status="active",
        case_snapshots=[snapshot],
        plan_name="Ilimitado",
        usage_status="estavel",
        usage_percent=40,
        recommended_plan=None,
        total_users=3,
        active_users=3,
        inspectors=1,
        reviewers=1,
        admin_clients=1,
        actor_id=81,
        actor_role="admin_cliente",
        source_channel="admin_cliente_bootstrap",
        visibility_policy={
            "admin_client_case_visibility_mode": "summary_only",
            "admin_client_case_action_mode": "read_only",
            "case_list_visible": False,
            "case_actions_enabled": False,
        },
    )

    dumped = projection.model_dump(mode="json")
    assert dumped["payload"]["case_counts"]["total_cases"] == 1
    assert dumped["payload"]["observed_case_ids"] == []
    assert dumped["payload"]["allowed_document_refs"] == []
    assert (
        dumped["payload"]["visibility_policy"]["admin_client_case_visibility_mode"]
        == "summary_only"
    )
    assert dumped["payload"]["visibility_policy"]["case_list_visible"] is False


def test_projecao_tenant_admin_explica_pacote_mobile_single_operator() -> None:
    projection = build_tenant_admin_view_projection(
        tenant_id=33,
        tenant_name="Empresa A",
        tenant_status="active",
        case_snapshots=[],
        plan_name="Ilimitado",
        usage_status="estavel",
        usage_percent=40,
        recommended_plan=None,
        total_users=2,
        active_users=2,
        inspectors=0,
        reviewers=0,
        admin_clients=1,
        actor_id=81,
        actor_role="admin_cliente",
        source_channel="admin_cliente_bootstrap",
        visibility_policy={
            "commercial_operating_model": "mobile_single_operator",
            "mobile_primary": True,
            "contract_operational_user_limit": 1,
            "shared_mobile_operator_enabled": True,
            "shared_mobile_operator_web_inspector_enabled": True,
            "shared_mobile_operator_web_review_enabled": True,
            "shared_mobile_operator_surface_set": ["mobile", "inspetor_web", "mesa_web"],
        },
    )

    dumped = projection.model_dump(mode="json")
    visibility_policy = dumped["payload"]["visibility_policy"]
    assert visibility_policy["commercial_operating_model"] == "mobile_single_operator"
    assert visibility_policy["mobile_primary"] is True
    assert visibility_policy["contract_operational_user_limit"] == 1
    assert visibility_policy["shared_mobile_operator_web_inspector_enabled"] is True
    assert visibility_policy["shared_mobile_operator_web_review_enabled"] is True
    assert visibility_policy["cross_surface_session_strategy"] == "governed_links_and_grants"
    assert visibility_policy["cross_surface_session_unified"] is False


def test_bootstrap_cliente_passa_pelo_piloto_tenant_admin_sem_mudar_payload(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None

        _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.RASCUNHO.value,
        )
        _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo_em_revisao_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.AGUARDANDO.value,
        )
        laudo_emitido_id = _criar_laudo(
            banco,
            empresa_id=ids["empresa_a"],
            usuario_id=ids["inspetor_a"],
            status_revisao=StatusRevisao.APROVADO.value,
        )
        laudo_em_revisao = banco.get(Laudo, laudo_em_revisao_id)
        laudo_emitido = banco.get(Laudo, laudo_emitido_id)
        assert laudo_em_revisao is not None
        assert laudo_emitido is not None
        laudo_em_revisao.revisado_por = ids["revisor_a"]
        laudo_emitido.nome_arquivo_pdf = "laudo_emitido.pdf"
        banco.commit()

        request_base = _build_request()
        monkeypatch.delenv("TARIEL_V2_CASE_CORE_ACL", raising=False)
        monkeypatch.delenv("TARIEL_V2_TENANT_ADMIN_PROJECTION", raising=False)
        payload_base = bootstrap_cliente(banco, usuario, request=request_base)

        request_flags = _build_request()
        monkeypatch.setenv("TARIEL_V2_CASE_CORE_ACL", "1")
        monkeypatch.setenv("TARIEL_V2_TENANT_ADMIN_PROJECTION", "1")
        payload_flags = bootstrap_cliente(banco, usuario, request=request_flags)

    assert payload_flags == payload_base
    assert payload_base["tenant_admin_projection"]["contract_name"] == "TenantAdminViewProjectionV1"
    assert payload_base["tenant_admin_projection"]["payload"]["user_summary"]["total_users"] >= 1
    assert (
        payload_base["tenant_admin_projection"]["payload"]["visibility_policy"]["raw_evidence_access"]
        == "not_granted_by_projection"
    )
    assert (
        payload_base["tenant_admin_projection"]["payload"]["visibility_policy"]["technical_access_mode"]
        == "surface_scoped_operational"
    )
    assert (
        payload_base["tenant_admin_projection"]["payload"]["visibility_policy"][
            "per_case_visibility_configurable"
        ]
        is True
    )
    assert (
        payload_base["tenant_admin_projection"]["payload"]["visibility_policy"][
            "per_case_action_configurable"
        ]
        is True
    )
    assert request_flags.state.v2_tenant_admin_projection_result["compatible"] is True
    assert request_flags.state.v2_tenant_admin_projection_result["used_projection"] is True
    projection = request_flags.state.v2_tenant_admin_projection_result["projection"]
    assert projection["contract_name"] == "TenantAdminViewProjectionV1"
    assert projection["payload"]["case_counts"]["total_cases"] >= 4
    assert projection["payload"]["review_counts"]["pending_review"] >= 1
    assert projection["payload"]["review_counts"]["in_review"] >= 1
    assert projection["payload"]["document_counts"]["issued_documents"] >= 1


def test_bootstrap_cliente_aceita_recorte_por_superficie_sem_perder_resumos_globais(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None

        payload_admin = bootstrap_cliente(banco, usuario, surface="admin")
        payload_chat = bootstrap_cliente(banco, usuario, surface="chat")
        payload_mesa = bootstrap_cliente(banco, usuario, surface="mesa")

    assert payload_admin["empresa"]["nome_fantasia"] == "Empresa A"
    assert "usuarios" in payload_admin
    assert "auditoria" in payload_admin
    assert "chat" not in payload_admin
    assert "mesa" not in payload_admin
    assert payload_admin["tenant_admin_projection"]["contract_name"] == "TenantAdminViewProjectionV1"

    assert payload_chat["empresa"]["nome_fantasia"] == "Empresa A"
    assert "chat" in payload_chat
    assert "usuarios" not in payload_chat
    assert "auditoria" not in payload_chat
    assert "mesa" not in payload_chat
    assert payload_chat["tenant_admin_projection"]["payload"]["tenant_summary"]["tenant_name"] == "Empresa A"

    assert payload_mesa["empresa"]["nome_fantasia"] == "Empresa A"
    assert "mesa" in payload_mesa
    assert "usuarios" not in payload_mesa
    assert "auditoria" not in payload_mesa
    assert "chat" not in payload_mesa
    assert payload_mesa["tenant_admin_projection"]["payload"]["tenant_summary"]["tenant_name"] == "Empresa A"


def test_bootstrap_cliente_reflete_politica_operacional_do_tenant(ambiente_critico) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "summary_only",
            "case_action_mode": "read_only",
        }
        banco.commit()

        payload = bootstrap_cliente(banco, usuario, surface="chat")

    visibility_policy = payload["tenant_admin_projection"]["payload"]["visibility_policy"]
    assert payload["empresa"]["nome_fantasia"] == "Empresa A"
    assert "usuarios" in payload
    assert "auditoria" in payload
    assert "chat" not in payload
    assert "mesa" not in payload
    assert visibility_policy["admin_client_case_visibility_mode"] == "summary_only"
    assert visibility_policy["admin_client_case_action_mode"] == "read_only"
    assert visibility_policy["case_list_visible"] is False
    assert visibility_policy["case_actions_enabled"] is False
    assert payload["tenant_admin_projection"]["payload"]["observed_case_ids"] == []


def test_bootstrap_cliente_reflete_pacote_mobile_single_operator_com_flags_web(
    ambiente_critico,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_cliente_a"])
        assert usuario is not None
        empresa = banco.get(Empresa, ids["empresa_a"])
        assert empresa is not None
        empresa.admin_cliente_policy_json = {
            "case_visibility_mode": "case_list",
            "case_action_mode": "case_actions",
            "operating_model": "mobile_single_operator",
            "shared_mobile_operator_web_inspector_enabled": True,
            "shared_mobile_operator_web_review_enabled": False,
        }
        banco.commit()

        payload = bootstrap_cliente(banco, usuario, surface="admin")

    visibility_policy = payload["tenant_admin_projection"]["payload"]["visibility_policy"]
    assert visibility_policy["commercial_operating_model"] == "mobile_single_operator"
    assert visibility_policy["mobile_primary"] is True
    assert visibility_policy["contract_operational_user_limit"] == 1
    assert visibility_policy["shared_mobile_operator_web_inspector_enabled"] is True
    assert visibility_policy["shared_mobile_operator_web_review_enabled"] is False
    assert visibility_policy["shared_mobile_operator_surface_set"] == ["mobile", "inspetor_web"]
