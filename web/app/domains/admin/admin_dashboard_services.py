"""Admin dashboard metrics services."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.shared.database import Empresa, Laudo


def buscar_metricas_ia_painel(
    db: Session,
    *,
    tenant_client_clause_fn: Callable[[], Any],
    plan_priority_clause_fn: Callable[[], Any],
    now_fn: Callable[[], datetime],
    list_catalog_families_fn: Callable[..., list[Any]],
    serialize_catalog_row_fn: Callable[[Any], dict[str, Any]],
    build_governance_rollup_fn: Callable[..., dict[str, Any]],
    build_commercial_scale_rollup_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    build_calibration_queue_rollup_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
) -> dict[str, Any]:
    qtd_clientes = db.scalar(select(func.count(Empresa.id)).where(tenant_client_clause_fn())) or 0
    total_inspecoes = db.scalar(select(func.count(Laudo.id))) or 0
    faturamento_ia = db.scalar(select(func.coalesce(func.sum(Laudo.custo_api_reais), 0))) or Decimal("0")
    familias_catalogadas = list_catalog_families_fn(db, filtro_classificacao="family")
    family_rows = [serialize_catalog_row_fn(item) for item in familias_catalogadas]

    stmt_ranking = select(Empresa).where(tenant_client_clause_fn()).order_by(
        plan_priority_clause_fn(),
        Empresa.id.desc(),
    )
    ranking = list(db.scalars(stmt_ranking).all())

    hoje = now_fn().date()
    labels: list[str] = []
    valores: list[int] = []

    for i in range(6, -1, -1):
        dia = hoje - timedelta(days=i)
        inicio = datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)
        fim = inicio + timedelta(days=1)

        qtd = (
            db.scalar(
                select(func.count(Laudo.id)).where(
                    Laudo.criado_em >= inicio,
                    Laudo.criado_em < fim,
                )
            )
            or 0
        )

        labels.append(dia.strftime("%a %d/%m"))
        valores.append(int(qtd))

    return {
        "qtd_clientes": int(qtd_clientes),
        "total_inspecoes": int(total_inspecoes),
        "receita_ia_total": faturamento_ia,
        "clientes": ranking,
        "governance_rollup": build_governance_rollup_fn(
            db,
            families=familias_catalogadas,
        ),
        "commercial_scale_rollup": build_commercial_scale_rollup_fn(family_rows),
        "calibration_queue_rollup": build_calibration_queue_rollup_fn(family_rows),
        "labels_grafico": labels,
        "valores_grafico": valores,
    }
