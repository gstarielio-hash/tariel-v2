from __future__ import annotations

from types import SimpleNamespace

from app.v2.billing import (
    build_platform_billing_metering_summary,
    build_tenant_billing_metering_snapshot,
    build_tenant_policy_capability_snapshot,
)


def test_tenant_billing_metering_snapshot_normaliza_campos_comerciais() -> None:
    snapshot = build_tenant_billing_metering_snapshot(
        plan_name=" Intermediario ",
        usage_status="",
        usage_percent="82",
        recommended_plan="  Ilimitado  ",
    )

    assert snapshot.model_dump(mode="python") == {
        "plan_name": "Intermediario",
        "usage_status": "unknown",
        "usage_percent": None,
        "recommended_plan": "Ilimitado",
    }


def test_platform_billing_metering_summary_agrega_planos_alertas_e_consumo() -> None:
    summary = build_platform_billing_metering_summary(
        tenant_summaries=[
            SimpleNamespace(
                id=1,
                nome_fantasia="Empresa A",
                plano_ativo="Ilimitado",
                status_bloqueio=False,
                mensagens_processadas=14,
            ),
            {
                "tenant_id": 2,
                "tenant_name": "Empresa B",
                "blocked": True,
                "usage_counter": 3,
            },
        ],
        total_inspections=44,
        total_api_revenue_brl="125.90",
        chart_labels=["Seg", "Ter"],
        chart_values=[7, 9],
    )

    dumped = summary.model_dump(mode="python")
    assert dumped["active_plans"] == 1
    assert dumped["plan_breakdown"] == {"Ilimitado": 1}
    assert dumped["active_tenants"] == 1
    assert dumped["blocked_tenants"] == 1
    assert dumped["alert_count"] == 2
    assert dumped["total_usage_counter"] == 17
    assert dumped["platform_alerts"] == [
        "tenant_without_plan:2",
        "tenant_blocked:2",
    ]


def test_tenant_policy_capability_snapshot_derive_plano_status_e_recomendacao() -> None:
    snapshot = build_tenant_policy_capability_snapshot(
        tenant_id=33,
        plan_name=" Inicial ",
        tenant_status="active",
        laudos_mes_limit=50,
        laudos_mes_used=43,
        upload_doc_enabled=False,
        deep_research_enabled=False,
    )

    assert snapshot.model_dump(mode="python") == {
        "tenant_id": "33",
        "tenant_status": "active",
        "plan_name": "Inicial",
        "usage_status": "atencao",
        "usage_percent": 86,
        "recommended_plan": "Intermediario",
        "laudos_mes_limit": 50,
        "laudos_mes_used": 43,
        "upload_doc_enabled": False,
        "deep_research_enabled": False,
    }
