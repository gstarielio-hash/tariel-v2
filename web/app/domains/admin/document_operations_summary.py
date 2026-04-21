from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.perf_support import backend_perf_habilitado, relatorio_perf
from app.domains.admin.services import buscar_metricas_ia_painel
from app.shared.backend_hotspot_metrics import get_backend_hotspot_operational_summary
from app.shared.database import Laudo, StatusRevisao
from app.v2.contracts.envelopes import utc_now
from app.v2.document import (
    document_hard_gate_observability_enabled,
    document_soft_gate_observability_enabled,
    get_document_hard_gate_operational_summary,
    get_document_soft_gate_operational_summary,
)
from app.v2.document.hard_gate_evidence import (
    document_hard_gate_durable_evidence_enabled,
    get_document_hard_gate_durable_summary,
)
from app.v2.report_pack_rollout_metrics import (
    get_report_pack_rollout_operational_summary,
    report_pack_rollout_observability_enabled,
)

_OPERATION_CATEGORY_ORDER = (
    "ocr",
    "ai",
    "pdf",
    "template",
    "render",
    "integration",
)


def _to_float(value: Any) -> float:
    if isinstance(value, Decimal):
        return round(float(value), 6)
    try:
        return round(float(value or 0.0), 6)
    except Exception:
        return 0.0


def _normalize_review_status_key(value: Any) -> str:
    raw_value = getattr(value, "value", value)
    try:
        return StatusRevisao.normalizar(raw_value)
    except Exception:
        return str(raw_value or "")


def _build_perf_category_summary(operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "total_ms": 0.0,
            "max_ms": 0.0,
            "avg_ms": 0.0,
            "slow_count": 0,
        }
    )

    for item in operations:
        category = str(item.get("category") or "").strip().lower()
        if not category:
            continue

        current = grouped[category]
        duration_ms = float(item.get("duration_ms") or 0.0)
        current["count"] += 1
        current["total_ms"] += duration_ms
        current["max_ms"] = max(float(current["max_ms"]), duration_ms)
        current["slow_count"] += 1 if item.get("slow") else 0

    items: list[dict[str, Any]] = []
    for category, payload in grouped.items():
        count = max(int(payload["count"]), 1)
        items.append(
            {
                "category": category,
                "count": int(payload["count"]),
                "total_ms": round(float(payload["total_ms"]), 3),
                "max_ms": round(float(payload["max_ms"]), 3),
                "avg_ms": round(float(payload["total_ms"]) / count, 3),
                "slow_count": int(payload["slow_count"]),
            }
        )

    items.sort(
        key=lambda item: (
            _OPERATION_CATEGORY_ORDER.index(item["category"])
            if item["category"] in _OPERATION_CATEGORY_ORDER
            else len(_OPERATION_CATEGORY_ORDER),
            -float(item["total_ms"]),
        )
    )
    return items


def _build_case_lifecycle_summary(db: Session) -> dict[str, Any]:
    total_cases = int(db.scalar(select(func.count(Laudo.id))) or 0)
    status_rows = db.execute(
        select(Laudo.status_revisao, func.count(Laudo.id)).group_by(Laudo.status_revisao)
    ).all()
    status_counts = {
        _normalize_review_status_key(status): int(count or 0)
        for status, count in status_rows
    }
    pending_reopen = int(
        db.scalar(
            select(func.count(Laudo.id)).where(Laudo.reabertura_pendente_em.is_not(None))
        )
        or 0
    )
    manual_reopens = int(
        db.scalar(select(func.count(Laudo.id)).where(Laudo.reaberto_em.is_not(None))) or 0
    )
    inspector_finalized = int(
        db.scalar(
            select(func.count(Laudo.id)).where(Laudo.encerrado_pelo_inspetor_em.is_not(None))
        )
        or 0
    )
    pending_templates_rows = db.execute(
        select(Laudo.tipo_template, func.count(Laudo.id).label("count"))
        .where(Laudo.reabertura_pendente_em.is_not(None))
        .group_by(Laudo.tipo_template)
        .order_by(func.count(Laudo.id).desc(), Laudo.tipo_template.asc())
        .limit(5)
    ).all()
    distribution = [
        {
            "status": "rascunho",
            "label": "Em coleta",
            "count": int(status_counts.get(StatusRevisao.RASCUNHO.value, 0)),
        },
        {
            "status": "aguardando",
            "label": "Aguardando mesa",
            "count": int(status_counts.get(StatusRevisao.AGUARDANDO.value, 0)),
        },
        {
            "status": "aprovado",
            "label": "Aprovado",
            "count": int(status_counts.get(StatusRevisao.APROVADO.value, 0)),
        },
        {
            "status": "rejeitado",
            "label": "Devolvido para correção",
            "count": int(status_counts.get(StatusRevisao.REJEITADO.value, 0)),
        },
    ]
    return {
        "contract_name": "TechnicalCaseLifecycleSummaryV1",
        "generated_at": utc_now().isoformat(),
        "totals": {
            "total_cases": total_cases,
            "inspector_collecting": int(status_counts.get(StatusRevisao.RASCUNHO.value, 0)),
            "awaiting_mesa_review": int(
                status_counts.get(StatusRevisao.AGUARDANDO.value, 0)
            ),
            "approved": int(status_counts.get(StatusRevisao.APROVADO.value, 0)),
            "returned_to_inspector": int(
                status_counts.get(StatusRevisao.REJEITADO.value, 0)
            ),
            "pending_reopen": pending_reopen,
            "manual_reopens": manual_reopens,
            "inspector_finalized": inspector_finalized,
        },
        "status_distribution": distribution,
        "top_pending_reopen_templates": [
            {
                "template_key": str(template_key or "padrao"),
                "count": int(count or 0),
            }
            for template_key, count in pending_templates_rows
        ],
    }


def build_document_operations_operational_summary(db: Session) -> dict[str, Any]:
    ai_metrics = buscar_metricas_ia_painel(db)
    perf_report = relatorio_perf() if backend_perf_habilitado() else {
        "enabled": False,
        "counts": {
            "requests": 0,
            "queries": 0,
            "operations": 0,
            "boot_events": 0,
        },
        "top_integrations": [],
        "top_render_ops": [],
        "operations": [],
    }
    operations = (
        perf_report.get("operations", [])
        if isinstance(perf_report.get("operations", []), list)
        else []
    )

    return {
        "contract_name": "DocumentOperationsSummaryV1",
        "generated_at": utc_now().isoformat(),
        "feature_flags": {
            "document_soft_gate_enabled": document_soft_gate_observability_enabled(),
            "document_hard_gate_enabled": document_hard_gate_observability_enabled(),
            "document_hard_gate_durable_enabled": document_hard_gate_durable_evidence_enabled(),
            "report_pack_rollout_enabled": report_pack_rollout_observability_enabled(),
            "perf_mode_enabled": bool(perf_report.get("enabled")),
        },
        "ai_costs": {
            "total_inspections": int(ai_metrics.get("total_inspecoes") or 0),
            "ai_cost_total_reais": _to_float(ai_metrics.get("receita_ia_total")),
        },
        "document_soft_gate": (
            get_document_soft_gate_operational_summary()
            if document_soft_gate_observability_enabled()
            else None
        ),
        "document_hard_gate": (
            get_document_hard_gate_operational_summary()
            if document_hard_gate_observability_enabled()
            else None
        ),
        "durable_evidence": (
            get_document_hard_gate_durable_summary()
            if document_hard_gate_durable_evidence_enabled()
            else None
        ),
        "report_pack_rollout": (
            get_report_pack_rollout_operational_summary()
            if report_pack_rollout_observability_enabled()
            else None
        ),
        "case_lifecycle": _build_case_lifecycle_summary(db),
        "backend_hotspots": get_backend_hotspot_operational_summary(),
        "heavy_operations": {
            "counts": perf_report.get("counts", {}),
            "top_integrations": perf_report.get("top_integrations", []),
            "top_render_ops": perf_report.get("top_render_ops", []),
            "by_category": _build_perf_category_summary(operations),
        },
    }


__all__ = [
    "build_document_operations_operational_summary",
]
