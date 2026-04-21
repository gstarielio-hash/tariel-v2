from __future__ import annotations

import json
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, RefResolver

from app.v2.contracts.platform_admin import build_platform_admin_view_projection
from app.v2.contracts.tenant_admin import build_tenant_admin_view_projection

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message="jsonschema.RefResolver is deprecated.*",
)


def _v2_schemas_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "Tarie 2" / "schemas"


def _load_schema(name: str) -> tuple[dict, RefResolver]:
    schemas_dir = _v2_schemas_dir()
    if not schemas_dir.is_dir():
        pytest.skip(f"Pacote externo de schemas V2 ausente: {schemas_dir}")
    schema_path = schemas_dir / name
    if not schema_path.is_file():
        pytest.skip(f"Schema V2 externo ausente: {schema_path}")
    schema = json.loads((schemas_dir / name).read_text(encoding="utf-8"))
    store: dict[str, dict] = {}
    for path in schemas_dir.glob("*.json"):
        loaded = json.loads(path.read_text(encoding="utf-8"))
        schema_id = loaded.get("$id")
        if isinstance(schema_id, str) and schema_id:
            store[schema_id] = loaded
        store[f"{schemas_dir.as_uri()}/{path.name}"] = loaded
    resolver = RefResolver(
        base_uri=f"{schemas_dir.as_uri()}/",
        referrer=schema,
        store=store,
    )
    return schema, resolver


def _validate_payload(schema_name: str, payload: dict) -> None:
    schema, resolver = _load_schema(schema_name)
    Draft202012Validator(schema, resolver=resolver).validate(payload)


def test_tenant_admin_command_schema_valida_exemplo_realista() -> None:
    _validate_payload(
        "tenant_admin_command.schema.json",
        {
            "contract_name": "AlterarPlanoDoTenant",
            "contract_version": "v1",
            "tenant_id": "33",
            "actor_id": "81",
            "actor_role": "admin_cliente",
            "correlation_id": "corr-tenant-admin-001",
            "idempotency_key": "tenant-admin-plan-33-001",
            "timestamp": "2026-03-30T12:00:00Z",
            "source_channel": "admin_cliente",
            "origin_kind": "human",
            "sensitivity_level": "administrative",
            "visibility_scope": "tenant_admin_summary",
            "command_name": "AlterarPlanoDoTenant",
            "target_domain": "tenant_admin",
            "requested_state_transition": {
                "aggregate": "tenant",
                "from": "Inicial",
                "to": "Intermediario",
            },
            "preconditions_asserted": [
                "tenant_matches_session",
                "csrf_checked",
            ],
            "requested_payload": {
                "plan_name": "Intermediario",
                "reason": "capacidade_operacional",
            },
        },
    )


def test_platform_admin_command_schema_valida_exemplo_realista() -> None:
    _validate_payload(
        "platform_admin_command.schema.json",
        {
            "contract_name": "AlterarPlanoDoTenantPelaPlataforma",
            "contract_version": "v1",
            "tenant_id": "33",
            "actor_id": "99",
            "actor_role": "diretoria",
            "correlation_id": "corr-platform-admin-001",
            "idempotency_key": "platform-admin-plan-33-001",
            "timestamp": "2026-03-30T12:05:00Z",
            "source_channel": "admin_geral",
            "origin_kind": "human",
            "sensitivity_level": "administrative",
            "visibility_scope": "platform_admin_aggregate",
            "command_name": "AlterarPlanoDoTenantPelaPlataforma",
            "target_domain": "platform_admin",
            "requested_state_transition": {
                "aggregate": "tenant",
                "from": "Intermediario",
                "to": "Ilimitado",
            },
            "preconditions_asserted": [
                "platform_admin_authenticated",
                "tenant_target_explicit",
            ],
            "requested_payload": {
                "tenant_id": "33",
                "plan_name": "Ilimitado",
            },
        },
    )


def test_tenant_admin_projection_congela_billing_e_documento_emitido_por_politica() -> None:
    case_snapshot = SimpleNamespace(
        case_ref=SimpleNamespace(
            case_id="case-33-1",
            document_id="document:legacy-laudo:33:91",
        ),
        case_state="issued",
        current_review_state="approved",
        current_document_state="issued",
        active_document_version_id="document:legacy-laudo:33:91",
    )

    projection = build_tenant_admin_view_projection(
        tenant_id=33,
        tenant_name="Empresa A",
        tenant_status="active",
        case_snapshots=[case_snapshot],
        plan_name="Intermediario",
        usage_status="attention",
        usage_percent=82,
        recommended_plan="Ilimitado",
        total_users=5,
        active_users=4,
        inspectors=2,
        reviewers=1,
        admin_clients=1,
        actor_id=81,
        actor_role="admin_cliente",
        source_channel="admin_cliente_bootstrap",
    ).model_dump(mode="json")

    assert projection["payload"]["billing_snapshot"] == {
        "plan_name": "Intermediario",
        "usage_status": "attention",
        "usage_percent": 82,
        "recommended_plan": "Ilimitado",
    }
    assert projection["payload"]["allowed_document_refs"] == [
        "document:legacy-laudo:33:91"
    ]


def test_platform_admin_projection_congela_consumo_e_saude_operacional_agregada() -> None:
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
    ).model_dump(mode="json")

    assert projection["payload"]["consumption_summary"] == {
        "active_tenants": 1,
        "alert_count": 1,
        "total_inspections": 44,
        "total_api_revenue_brl": "125.90",
        "chart_labels": ["Seg", "Ter"],
        "chart_values": [7, 9],
    }
    assert projection["payload"]["technical_visibility"] == "none_by_default"
    assert projection["payload"]["platform_alerts"] == ["tenant_blocked:2"]
