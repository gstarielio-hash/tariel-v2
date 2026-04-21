from __future__ import annotations

from datetime import datetime, timezone

from app.v2.contracts.client_mesa import build_client_mesa_dashboard_projection


def test_client_mesa_dashboard_projection_explicit_contract_shape() -> None:
    now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)

    projection = build_client_mesa_dashboard_projection(
        tenant_id=33,
        company_id=33,
        company_name="Tariel Demo Local",
        active_plan="Ilimitado",
        blocked=False,
        health_label="Ritmo estavel",
        health_tone="aprovado",
        health_text="Fila sob controle.",
        total_reports=14,
        reviewer_summary={
            "total": 2,
            "active": 2,
            "blocked": 0,
            "with_recent_sessions": 1,
            "first_access_pending": 1,
        },
        review_status_totals={
            "drafts": 3,
            "waiting_review": 4,
            "approved": 5,
            "rejected": 1,
            "other_statuses": 1,
        },
        reviewers=[
            {
                "id": 51,
                "name": "Mesa Demo",
                "email": "mesa.demo.local@tariel.test",
                "portal_label": "Mesa Avaliadora",
                "active": True,
                "blocked": False,
                "temporary_password_active": True,
                "last_login_at": now,
                "last_login_label": "21/04/2026 09:00",
                "last_activity_at": now,
                "last_activity_label": "21/04/2026 09:15",
                "session_count": 1,
            }
        ],
        recent_audit=[
            {
                "id": 700,
                "portal": "cliente",
                "action": "mesa_resposta_enviada",
                "category": "mesa",
                "scope": "mesa",
                "summary": "Resposta enviada na mesa.",
                "detail": "Retorno do admin-cliente.",
                "actor_name": "Admin Cliente",
                "target_name": "Mesa Demo",
                "created_at": now,
                "created_at_label": "21/04/2026 09:20",
            }
        ],
        audit_summary={"total": 1, "categories": {"mesa": 1}, "scopes": {"mesa": 1}},
        review_queue_projection={
            "contract_name": "ReviewQueueDashboardProjectionV1",
            "payload": {
                "queue_summary": {
                    "awaiting_review_count": 4,
                    "total_pending_whispers": 2,
                },
                "queue_sections": {
                    "em_andamento": [],
                    "aguardando_avaliacao": [],
                    "historico": [],
                },
            },
        },
        actor_id=80,
        actor_role="admin_cliente",
        source_channel="admin_cliente_mesa_snapshot",
        timestamp=now,
    )

    dumped = projection.model_dump(mode="json")
    assert dumped["contract_name"] == "ClientMesaDashboardProjectionV1"
    assert dumped["projection_type"] == "client_mesa_dashboard_projection"
    assert dumped["tenant_id"] == "33"
    assert dumped["actor_role"] == "admin_cliente"
    assert dumped["payload"]["tenant_summary"]["company_name"] == "Tariel Demo Local"
    assert dumped["payload"]["reviewer_summary"]["with_recent_sessions"] == 1
    assert dumped["payload"]["review_status_totals"]["waiting_review"] == 4
    assert dumped["payload"]["recent_audit"][0]["category"] == "mesa"
    assert dumped["payload"]["review_queue_projection"]["contract_name"] == "ReviewQueueDashboardProjectionV1"
