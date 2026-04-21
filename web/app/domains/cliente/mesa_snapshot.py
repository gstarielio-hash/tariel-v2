"""Snapshot governado da mesa para o portal admin-cliente."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.cliente.auditoria import (
    listar_auditoria_empresa,
    resumir_auditoria_serializada,
    serializar_registro_auditoria,
)
from app.domains.cliente.dashboard_company_summary import resumo_empresa_cliente
from app.domains.revisor.panel_state import build_review_panel_state
from app.shared.database import NivelAcesso, SessaoAtiva, StatusRevisao, Usuario
from app.v2.contracts.client_mesa import build_client_mesa_dashboard_projection
from app.v2.contracts.review_queue import build_review_queue_dashboard_projection
from app.v2.runtime import actor_role_from_user

_ROLE_LABEL_REVIEWER = "Mesa Avaliadora"


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_datetime_label(value: datetime | None, fallback: str) -> str:
    normalized = _normalize_datetime(value)
    if normalized is None:
        return fallback
    return normalized.astimezone().strftime("%d/%m/%Y %H:%M")


def _normalize_review_status(value: Any) -> str:
    return str(getattr(value, "value", value) or "").strip().lower()


def _review_status_bucket(value: Any) -> str:
    normalized = _normalize_review_status(value)
    if normalized == StatusRevisao.RASCUNHO.value:
        return "drafts"
    if normalized == StatusRevisao.AGUARDANDO.value:
        return "waiting_review"
    if normalized == StatusRevisao.APROVADO.value:
        return "approved"
    if normalized == StatusRevisao.REJEITADO.value:
        return "rejected"
    return "other_statuses"


def _build_reviewer_snapshot(
    banco: Session,
    *,
    company_id: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reviewers = list(
        banco.scalars(
            select(Usuario)
            .where(
                Usuario.empresa_id == int(company_id),
                Usuario.nivel_acesso == int(NivelAcesso.REVISOR),
            )
            .order_by(Usuario.nome_completo.asc(), Usuario.id.asc())
        ).all()
    )
    reviewer_ids = [int(item.id) for item in reviewers if int(item.id or 0) > 0]
    sessions_by_user: dict[int, dict[str, Any]] = {}
    if reviewer_ids:
        session_rows = banco.execute(
            select(
                SessaoAtiva.usuario_id,
                func.count(SessaoAtiva.token),
                func.max(SessaoAtiva.ultima_atividade_em),
            )
            .where(
                SessaoAtiva.usuario_id.in_(reviewer_ids),
                SessaoAtiva.portal == "revisor",
                SessaoAtiva.expira_em > datetime.now(timezone.utc),
            )
            .group_by(SessaoAtiva.usuario_id)
        ).all()
        sessions_by_user = {
            int(user_id): {
                "session_count": int(total or 0),
                "last_activity_at": _normalize_datetime(last_activity_at),
            }
            for user_id, total, last_activity_at in session_rows
            if int(user_id or 0) > 0
        }

    payload = []
    summary = {
        "total": 0,
        "active": 0,
        "blocked": 0,
        "with_recent_sessions": 0,
        "first_access_pending": 0,
    }

    for reviewer in reviewers:
        session_meta = sessions_by_user.get(int(reviewer.id), {})
        session_count = int(session_meta.get("session_count") or 0)
        last_activity_at = session_meta.get("last_activity_at")
        blocked = not bool(getattr(reviewer, "ativo", False)) or bool(getattr(reviewer, "status_bloqueio", False))
        temporary_password_active = bool(getattr(reviewer, "senha_temporaria_ativa", False))
        last_login_at = _normalize_datetime(getattr(reviewer, "ultimo_login", None))

        payload.append(
            {
                "id": int(reviewer.id),
                "name": str(getattr(reviewer, "nome_completo", None) or getattr(reviewer, "nome", None) or ""),
                "email": str(getattr(reviewer, "email", "") or ""),
                "portal_label": _ROLE_LABEL_REVIEWER,
                "active": not blocked,
                "blocked": blocked,
                "temporary_password_active": temporary_password_active,
                "last_login_at": last_login_at,
                "last_login_label": _format_datetime_label(last_login_at, "Nunca acessou"),
                "last_activity_at": last_activity_at,
                "last_activity_label": _format_datetime_label(last_activity_at, "Sem sessão recente"),
                "session_count": session_count,
            }
        )

        summary["total"] += 1
        summary["active"] += int(not blocked)
        summary["blocked"] += int(blocked)
        summary["with_recent_sessions"] += int(session_count > 0)
        summary["first_access_pending"] += int(temporary_password_active)

    return payload, summary


def build_cliente_mesa_snapshot_projection(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
):
    company_summary = resumo_empresa_cliente(banco, usuario)
    panel_state = build_review_panel_state(
        request=request,
        usuario=usuario,
        banco=banco,
    )
    review_queue_projection = build_review_queue_dashboard_projection(
        tenant_id=usuario.empresa_id,
        filtro_inspetor_id=panel_state.filtro_inspetor_id,
        filtro_busca=panel_state.filtro_busca,
        filtro_aprendizados=panel_state.filtro_aprendizados,
        filtro_operacao=panel_state.filtro_operacao,
        whispers_pendentes=panel_state.whispers_pendentes,
        laudos_em_andamento=panel_state.laudos_em_andamento,
        laudos_pendentes=panel_state.laudos_pendentes,
        laudos_avaliados=panel_state.laudos_avaliados,
        total_aprendizados_pendentes=panel_state.total_aprendizados_pendentes,
        total_pendencias_abertas=panel_state.total_pendencias_abertas,
        total_whispers_pendentes=panel_state.total_whispers_pendentes,
        totais_operacao=panel_state.totais_operacao,
        templates_operacao=panel_state.templates_operacao,
        actor_id=usuario.id,
        actor_role=actor_role_from_user(usuario),
        source_channel="admin_cliente_mesa_snapshot",
        correlation_id=str(request.headers.get("X-Correlation-ID") or "").strip() or None,
    )

    reviewers, reviewer_summary = _build_reviewer_snapshot(
        banco,
        company_id=int(usuario.empresa_id),
    )
    audit_items = [
        serializar_registro_auditoria(item)
        for item in listar_auditoria_empresa(
            banco,
            empresa_id=int(usuario.empresa_id),
            limite=12,
            scope="mesa",
        )
    ]
    recent_audit = [
        {
            "id": int(item.get("id") or 0),
            "portal": str(item.get("portal") or ""),
            "action": str(item.get("acao") or ""),
            "category": str(item.get("categoria") or ""),
            "scope": str(item.get("scope") or ""),
            "summary": str(item.get("resumo") or ""),
            "detail": str(item.get("detalhe") or ""),
            "actor_name": str(item.get("ator_nome") or ""),
            "target_name": str(item.get("alvo_nome") or ""),
            "created_at": _normalize_datetime(
                datetime.fromisoformat(item["criado_em"]) if str(item.get("criado_em") or "").strip() else None
            ),
            "created_at_label": str(item.get("criado_em_label") or ""),
        }
        for item in audit_items
    ]

    review_status_totals = {
        "drafts": 0,
        "waiting_review": 0,
        "approved": 0,
        "rejected": 0,
        "other_statuses": 0,
    }
    queue_sections = (
        review_queue_projection.payload.get("queue_sections", {})
        if isinstance(getattr(review_queue_projection, "payload", None), dict)
        else {}
    )
    for section_name in ("em_andamento", "aguardando_avaliacao", "historico"):
        for item in list(queue_sections.get(section_name) or []):
            bucket = _review_status_bucket(item.get("status_revisao"))
            review_status_totals[bucket] += 1

    return build_client_mesa_dashboard_projection(
        tenant_id=usuario.empresa_id,
        company_id=int(company_summary.get("id") or 0),
        company_name=str(company_summary.get("nome_fantasia") or ""),
        active_plan=str(company_summary.get("plano_ativo") or ""),
        blocked=bool(company_summary.get("status_bloqueio")),
        health_label=str((company_summary.get("saude_operacional") or {}).get("status") or ""),
        health_tone=str((company_summary.get("saude_operacional") or {}).get("tone") or ""),
        health_text=str((company_summary.get("saude_operacional") or {}).get("texto") or ""),
        total_reports=int(company_summary.get("total_laudos") or 0),
        reviewer_summary=reviewer_summary,
        review_status_totals=review_status_totals,
        reviewers=reviewers,
        recent_audit=recent_audit,
        audit_summary=resumir_auditoria_serializada(audit_items),
        review_queue_projection=review_queue_projection.model_dump(mode="json"),
        actor_id=usuario.id,
        actor_role=actor_role_from_user(usuario),
        source_channel="admin_cliente_mesa_snapshot",
        correlation_id=str(request.headers.get("X-Correlation-ID") or "").strip() or None,
    )


__all__ = [
    "build_cliente_mesa_snapshot_projection",
]
