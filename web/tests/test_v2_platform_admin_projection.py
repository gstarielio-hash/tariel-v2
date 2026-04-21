from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi.responses import HTMLResponse
from starlette.requests import Request

import app.domains.admin.routes as admin_routes
from app.domains.admin.routes import painel_faturamento
from app.shared.database import Empresa, Laudo, NivelAcesso, RegistroAuditoriaEmpresa, StatusRevisao, Usuario
from app.v2.contracts.platform_admin import build_platform_admin_view_projection


def _build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=99,
        empresa_id=0,
        nivel_acesso=NivelAcesso.DIRETORIA.value,
    )


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/admin/painel",
            "headers": [],
            "query_string": b"",
            "session": {},
            "state": {},
        }
    )


def test_shape_da_projecao_canonica_do_admin_geral() -> None:
    projection = build_platform_admin_view_projection(
        tenant_summaries=[
            SimpleNamespace(
                id=1,
                nome_fantasia="Empresa A",
                plano_ativo="Ilimitado",
                status_bloqueio=False,
                mensagens_processadas=14,
            ),
            SimpleNamespace(
                id=2,
                nome_fantasia="Empresa B",
                plano_ativo="Inicial",
                status_bloqueio=True,
                mensagens_processadas=3,
            ),
        ],
        total_inspections=44,
        total_api_revenue_brl="125.90",
        chart_labels=["Seg", "Ter"],
        chart_values=[7, 9],
        recent_admin_actions=5,
        actor_id=99,
        actor_role="diretoria",
        source_channel="admin_dashboard",
    )

    dumped = projection.model_dump(mode="json")
    assert dumped["contract_name"] == "PlatformAdminViewProjectionV1"
    assert dumped["projection_audience"] == "platform_admin_web"
    assert dumped["payload"]["technical_visibility"] == "none_by_default"
    assert dumped["payload"]["plan_summary"]["active_plans"] == 2
    assert dumped["payload"]["consumption_summary"]["active_tenants"] == 1
    assert dumped["payload"]["consumption_summary"]["alert_count"] == 1
    assert dumped["payload"]["platform_alerts"] == ["tenant_blocked:2"]
    assert dumped["payload"]["audit_summary"]["recent_admin_actions"] == 5


def test_painel_admin_passa_pelo_piloto_platform_admin_sem_mudar_html(
    ambiente_critico,
    monkeypatch,
) -> None:
    SessionLocal = ambiente_critico["SessionLocal"]
    ids = ambiente_critico["ids"]

    monkeypatch.setattr(
        admin_routes,
        "_render_template",
        lambda request, template, context: HTMLResponse(
            f"dashboard:{context['dados'].get('qtd_clientes', 0)}:{context['dados'].get('total_inspecoes', 0)}"
        ),
    )

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, ids["admin_a"])
        empresa_b = banco.get(Empresa, ids["empresa_b"])
        assert usuario is not None
        assert empresa_b is not None

        empresa_b.status_bloqueio = True
        banco.add(
            Laudo(
                empresa_id=ids["empresa_a"],
                usuario_id=ids["inspetor_a"],
                setor_industrial="NR Teste",
                tipo_template="padrao",
                status_revisao=StatusRevisao.RASCUNHO.value,
                codigo_hash="admin-geral-laudo-a",
            )
        )
        banco.add(
            Laudo(
                empresa_id=ids["empresa_b"],
                usuario_id=ids["inspetor_b"],
                setor_industrial="NR Teste",
                tipo_template="padrao",
                status_revisao=StatusRevisao.AGUARDANDO.value,
                codigo_hash="admin-geral-laudo-b",
            )
        )
        banco.add(
            RegistroAuditoriaEmpresa(
                empresa_id=ids["empresa_a"],
                ator_usuario_id=usuario.id,
                portal="cliente",
                acao="plano_alterado",
                resumo="Plano alterado para acompanhamento administrativo.",
            )
        )
        banco.commit()

        request_base = _build_request()
        monkeypatch.delenv("TARIEL_V2_PLATFORM_ADMIN_PROJECTION", raising=False)
        response_base = asyncio.run(
            painel_faturamento(
                request=request_base,
                banco=banco,
                usuario=usuario,
            )
        )

        request_flags = _build_request()
        monkeypatch.setenv("TARIEL_V2_PLATFORM_ADMIN_PROJECTION", "1")
        response_flags = asyncio.run(
            painel_faturamento(
                request=request_flags,
                banco=banco,
                usuario=usuario,
            )
        )

    assert response_flags.body == response_base.body
    assert request_flags.state.v2_platform_admin_projection_result["compatible"] is True
    assert request_flags.state.v2_platform_admin_projection_result["used_projection"] is True
    projection = request_flags.state.v2_platform_admin_projection_result["projection"]
    assert projection["contract_name"] == "PlatformAdminViewProjectionV1"
    assert projection["payload"]["technical_visibility"] == "none_by_default"
    assert projection["payload"]["consumption_summary"]["active_tenants"] == 1
    assert projection["payload"]["audit_summary"]["recent_admin_actions"] >= 1
    assert f"tenant_blocked:{ids['empresa_b']}" in projection["payload"]["platform_alerts"]
