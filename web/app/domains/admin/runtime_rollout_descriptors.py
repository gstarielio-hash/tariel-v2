from __future__ import annotations

from typing import Any

from app.v2.mobile_rollout_metrics import mobile_v2_rollout_observability_enabled
from app.v2.report_pack_rollout_metrics import report_pack_rollout_observability_enabled


def build_rollout_runtime_descriptors() -> list[dict[str, Any]]:
    mobile_enabled = mobile_v2_rollout_observability_enabled()
    report_pack_enabled = report_pack_rollout_observability_enabled()
    return [
        {
            "title": "Observabilidade do Mobile V2",
            "description": "Supervisiona rollout móvel sem expor conteúdo técnico bruto no Admin-CEO.",
            "value_label": "Habilitado" if mobile_enabled else "Observação",
            "status_tone_key": "positive" if mobile_enabled else "neutral",
            "source_kind": "environment",
            "scope_label": "Mobile e rollout",
            "technical_path": "/admin/api/mobile-v2-rollout/summary",
        },
        {
            "title": "Observabilidade do report pack",
            "description": "Resume gates, divergência e queda para Mesa das famílias semânticas já modeladas.",
            "value_label": "Habilitada" if report_pack_enabled else "Observação",
            "status_tone_key": "positive" if report_pack_enabled else "neutral",
            "source_kind": "environment",
            "scope_label": "Documento e rollout",
            "technical_path": "/admin/api/report-pack-rollout/summary",
        },
    ]


__all__ = ["build_rollout_runtime_descriptors"]
