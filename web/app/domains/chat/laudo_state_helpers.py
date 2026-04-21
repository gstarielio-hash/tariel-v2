"""Helpers de estado derivado e serializacao resumida de laudos."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.chat.chat_runtime import (
    ENTRY_MODE_AUTO_RECOMMENDED,
    ENTRY_MODE_REASON_EXISTING_CASE_STATE,
    normalizar_entry_mode_effective,
    normalizar_entry_mode_preference,
    normalizar_entry_mode_reason,
    resolver_modo_entrada_caso,
)
from app.domains.chat.mobile_ai_preferences import limpar_texto_visivel_chat
from app.domains.chat.normalization import nome_template_humano
from app.domains.chat.schemas import (
    GuidedInspectionDraftPayload,
    GuidedInspectionEvidenceRefPayload,
    GuidedInspectionMesaHandoffPayload,
)
from app.shared.database import Laudo, MensagemLaudo, StatusRevisao
from app.v2.acl.technical_case_core import (
    TechnicalCaseLifecycleStatus,
    TechnicalCaseStatusSnapshot,
    TechnicalCaseSurfaceAction,
    build_case_status_visual_label,
    build_technical_case_status_snapshot_from_legacy,
)


CARD_STATUS_LABELS = {
    "aberto": "Aberto",
    "aguardando": "Aguardando",
    "ajustes": "Ajustes",
    "aprovado": "Aprovado",
}


InspectorMutationSurface = Literal["chat", "mesa_reply"]
InspectorFinalizationTarget = Literal["aguardando_mesa", "aprovado"]
MesaDecisionTarget = Literal["devolvido_para_correcao", "aprovado"]
ManualReopenTarget = Literal["laudo_em_coleta", "devolvido_para_correcao"]


@dataclass(slots=True)
class CacheResumoLaudoRequest:
    interacao_por_laudo: dict[int, bool] = field(default_factory=dict)
    historico_visivel_por_laudo: dict[int, bool] = field(default_factory=dict)
    status_card_por_laudo: dict[int, str] = field(default_factory=dict)
    card_por_laudo: dict[int, dict[str, Any]] = field(default_factory=dict)
    case_snapshot_por_laudo: dict[int, TechnicalCaseStatusSnapshot] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LaudoLifecycleAuthority:
    status_revisao: str
    has_pending_reopen: bool

    @property
    def allows_inspector_edit(self) -> bool:
        return self.status_revisao == StatusRevisao.RASCUNHO.value

    @property
    def allows_mesa_review(self) -> bool:
        return self.status_revisao == StatusRevisao.AGUARDANDO.value

    def inspector_block_detail(
        self,
        *,
        surface: InspectorMutationSurface,
    ) -> str:
        if self.status_revisao == StatusRevisao.APROVADO.value:
            if surface == "mesa_reply":
                return "Laudo aprovado não pode receber novas mensagens."
            return "Laudo aprovado não pode ser editado."
        if self.status_revisao == StatusRevisao.REJEITADO.value:
            if surface == "mesa_reply":
                return "Laudo em ajustes precisa ser reaberto antes de responder à mesa."
            return "Laudo em ajustes precisa ser reaberto antes de receber novas mensagens."
        if self.has_pending_reopen:
            if surface == "mesa_reply":
                return "Laudo com ajustes da mesa precisa ser reaberto antes de responder."
            return "Laudo com ajustes da mesa precisa ser reaberto antes de continuar."
        if surface == "mesa_reply":
            return "Laudo aguardando avaliação não aceita novas mensagens até ser reaberto."
        return "Laudo aguardando avaliação não pode receber novas mensagens."

    def mesa_review_block_detail(self) -> str:
        if self.status_revisao == StatusRevisao.APROVADO.value:
            return "Laudo já foi aprovado e não pode ser avaliado novamente."
        if self.status_revisao == StatusRevisao.REJEITADO.value:
            return "Laudo devolvido para ajustes precisa ser reaberto antes de nova avaliação."
        if self.status_revisao == StatusRevisao.RASCUNHO.value:
            return "Laudo ainda está em rascunho e não pode ser avaliado pela mesa."
        return "Laudo não está aguardando avaliação."


@dataclass(slots=True, frozen=True)
class TechnicalCaseMutationAuthority:
    snapshot: TechnicalCaseStatusSnapshot
    has_pending_reopen: bool

    def allows_transition_to(
        self,
        target_status: TechnicalCaseLifecycleStatus,
    ) -> bool:
        return target_status in self.snapshot.allowed_next_lifecycle_statuses

    def allows_surface_action(
        self,
        action: TechnicalCaseSurfaceAction,
    ) -> bool:
        return action in self.snapshot.allowed_surface_actions

    def allows_inspector_finalization_to(
        self,
        target_status: InspectorFinalizationTarget,
    ) -> bool:
        return self.allows_surface_action("chat_finalize") and self.allows_transition_to(
            target_status
        )

    def allows_mesa_decision_to(
        self,
        target_status: MesaDecisionTarget,
    ) -> bool:
        action: TechnicalCaseSurfaceAction = (
            "mesa_approve"
            if target_status == "aprovado"
            else "mesa_return"
        )
        return self.allows_surface_action(action) and self.allows_transition_to(
            target_status
        )

    def should_signal_pending_reopen_from_mesa_feedback(self) -> bool:
        return (
            self.snapshot.active_owner_role == "mesa"
            and self.snapshot.case_lifecycle_status
            in {"aguardando_mesa", "em_revisao_mesa"}
        )

    def resolve_manual_reopen_target(self) -> ManualReopenTarget | None:
        if (
            self.snapshot.case_lifecycle_status == "devolvido_para_correcao"
            and self.allows_transition_to("laudo_em_coleta")
        ):
            return "laudo_em_coleta"
        if self.allows_surface_action("chat_reopen") and self.allows_transition_to(
            "devolvido_para_correcao"
        ):
            return "devolvido_para_correcao"
        return None


def criar_cache_resumo_laudos() -> CacheResumoLaudoRequest:
    return CacheResumoLaudoRequest()


def _normalizar_laudo_id(laudo_id: object) -> int | None:
    if not isinstance(laudo_id, (int, float, str, bytes, bytearray)):
        return None
    try:
        valor = int(laudo_id or 0)
    except (TypeError, ValueError):
        return None
    return valor if valor > 0 else None


def _coletar_laudo_ids(laudo_ids: Iterable[object]) -> list[int]:
    ids: list[int] = []
    vistos: set[int] = set()
    for laudo_id in laudo_ids:
        valor = _normalizar_laudo_id(laudo_id)
        if valor is None or valor in vistos:
            continue
        vistos.add(valor)
        ids.append(valor)
    return ids


def _normalizar_status_revisao_laudo(laudo: Laudo | object) -> str:
    valor = getattr(laudo, "status_revisao", "")
    if isinstance(valor, StatusRevisao):
        return valor.value
    valor_base = getattr(valor, "value", valor)
    try:
        return StatusRevisao.normalizar(valor_base)
    except ValueError:
        return str(valor_base or "").strip()


def precarregar_interacoes_laudos(
    banco: Session,
    laudo_ids: Iterable[object],
    *,
    cache: CacheResumoLaudoRequest,
) -> None:
    ids_pendentes = [laudo_id for laudo_id in _coletar_laudo_ids(laudo_ids) if laudo_id not in cache.interacao_por_laudo]
    if not ids_pendentes:
        return

    encontrados = {
        int(laudo_id)
        for laudo_id in banco.scalars(select(MensagemLaudo.laudo_id).where(MensagemLaudo.laudo_id.in_(ids_pendentes)).group_by(MensagemLaudo.laudo_id)).all()
    }
    for laudo_id in ids_pendentes:
        cache.interacao_por_laudo[laudo_id] = laudo_id in encontrados


def laudo_tem_interacao(
    banco: Session,
    laudo_id: int,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> bool:
    laudo_id_normalizado = _normalizar_laudo_id(laudo_id)
    if laudo_id_normalizado is None:
        return False

    if cache is not None and laudo_id_normalizado in cache.interacao_por_laudo:
        return bool(cache.interacao_por_laudo[laudo_id_normalizado])

    possui_interacao = banco.query(MensagemLaudo.id).filter(MensagemLaudo.laudo_id == laudo_id_normalizado).first() is not None
    if cache is not None:
        cache.interacao_por_laudo[laudo_id_normalizado] = bool(possui_interacao)
    return bool(possui_interacao)


def laudo_possui_historico_visivel(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> bool:
    laudo_id = int(laudo.id)
    if cache is not None and laudo_id in cache.historico_visivel_por_laudo:
        return bool(cache.historico_visivel_por_laudo[laudo_id])

    possui_historico = True
    if not laudo_tem_interacao(banco, laudo_id, cache=cache):
        if laudo.status_revisao != StatusRevisao.RASCUNHO.value:
            possui_historico = True
        else:
            possui_historico = bool((laudo.primeira_mensagem or "").strip() or (laudo.parecer_ia or "").strip())

    if cache is not None:
        cache.historico_visivel_por_laudo[laudo_id] = bool(possui_historico)
    return bool(possui_historico)


def obter_status_card_laudo(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> str:
    laudo_id = int(laudo.id)
    if cache is not None and laudo_id in cache.status_card_por_laudo:
        return str(cache.status_card_por_laudo[laudo_id])

    if not laudo_possui_historico_visivel(banco, laudo, cache=cache):
        if cache is not None:
            cache.status_card_por_laudo[laudo_id] = "oculto"
        return "oculto"

    status_revisao = _normalizar_status_revisao_laudo(laudo)

    if status_revisao == StatusRevisao.APROVADO.value:
        status = "aprovado"
    elif status_revisao == StatusRevisao.REJEITADO.value:
        status = "ajustes"
    elif status_revisao == StatusRevisao.AGUARDANDO.value:
        status = "ajustes" if laudo_tem_reabertura_pendente(laudo) else "aguardando"
    else:
        status = "aberto"

    if cache is not None:
        cache.status_card_por_laudo[laudo_id] = status
    return status


def obter_estado_api_laudo(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> str:
    status_card = obter_status_card_laudo(banco, laudo, cache=cache)
    mapa = {
        "oculto": "sem_relatorio",
        "aberto": "relatorio_ativo",
        "aguardando": "aguardando",
        "ajustes": "ajustes",
        "aprovado": "aprovado",
    }
    return mapa.get(status_card, "sem_relatorio")


def laudo_tem_reabertura_pendente(laudo: Laudo) -> bool:
    return getattr(laudo, "reabertura_pendente_em", None) is not None


def _agora_utc_state() -> datetime:
    return datetime.now(timezone.utc)


def _build_legacy_case_lifecycle_write_payload(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> dict[str, Any]:
    status_card = obter_status_card_laudo(banco, laudo, cache=cache)
    has_message_history = laudo_tem_interacao(
        banco,
        int(getattr(laudo, "id", 0) or 0),
        cache=cache,
    )
    return {
        "estado": obter_estado_api_laudo(banco, laudo, cache=cache),
        "laudo_id": int(getattr(laudo, "id", 0) or 0) or None,
        "status_card": status_card,
        "permite_reabrir": status_card in {"ajustes", "aprovado"},
        "has_message_history": bool(has_message_history),
    }


def build_legacy_case_lifecycle_read_payload(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> dict[str, Any]:
    return _build_legacy_case_lifecycle_write_payload(
        banco,
        laudo,
        cache=cache,
    )


def resolver_snapshot_leitura_caso_tecnico(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> TechnicalCaseStatusSnapshot:
    laudo_id = int(getattr(laudo, "id", 0) or 0)
    if cache is not None and laudo_id in cache.case_snapshot_por_laudo:
        return cache.case_snapshot_por_laudo[laudo_id]

    snapshot = build_technical_case_status_snapshot_from_legacy(
        tenant_id=getattr(laudo, "empresa_id", ""),
        legacy_payload=build_legacy_case_lifecycle_read_payload(
            banco,
            laudo,
            cache=cache,
        ),
        laudo=laudo,
    )
    if cache is not None and laudo_id > 0:
        cache.case_snapshot_por_laudo[laudo_id] = snapshot
    return snapshot


def resolver_autoridade_mutacao_caso_tecnico(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> TechnicalCaseMutationAuthority:
    snapshot = build_technical_case_status_snapshot_from_legacy(
        tenant_id=getattr(laudo, "empresa_id", ""),
        legacy_payload=_build_legacy_case_lifecycle_write_payload(
            banco,
            laudo,
            cache=cache,
        ),
        laudo=laudo,
    )
    return TechnicalCaseMutationAuthority(
        snapshot=snapshot,
        has_pending_reopen=laudo_tem_reabertura_pendente(laudo),
    )


def resolver_autoridade_lifecycle_laudo(laudo: Laudo) -> LaudoLifecycleAuthority:
    return LaudoLifecycleAuthority(
        status_revisao=_normalizar_status_revisao_laudo(laudo),
        has_pending_reopen=laudo_tem_reabertura_pendente(laudo),
    )


def laudo_permite_edicao_inspetor(laudo: Laudo) -> bool:
    return resolver_autoridade_lifecycle_laudo(laudo).allows_inspector_edit


def obter_detalhe_bloqueio_edicao_inspetor(
    laudo: Laudo,
    *,
    surface: InspectorMutationSurface = "chat",
) -> str:
    return resolver_autoridade_lifecycle_laudo(laudo).inspector_block_detail(
        surface=surface
    )


def laudo_aceita_avaliacao_mesa(laudo: Laudo) -> bool:
    return resolver_autoridade_lifecycle_laudo(laudo).allows_mesa_review


def obter_detalhe_bloqueio_avaliacao_mesa(laudo: Laudo) -> str:
    return resolver_autoridade_lifecycle_laudo(laudo).mesa_review_block_detail()


def laudo_permite_transicao_finalizacao_inspetor(
    banco: Session,
    laudo: Laudo,
    *,
    target_status: InspectorFinalizationTarget,
    cache: CacheResumoLaudoRequest | None = None,
) -> bool:
    return resolver_autoridade_mutacao_caso_tecnico(
        banco,
        laudo,
        cache=cache,
    ).allows_inspector_finalization_to(target_status)


def laudo_permite_transicao_decisao_mesa(
    banco: Session,
    laudo: Laudo,
    *,
    target_status: MesaDecisionTarget,
    cache: CacheResumoLaudoRequest | None = None,
) -> bool:
    return resolver_autoridade_mutacao_caso_tecnico(
        banco,
        laudo,
        cache=cache,
    ).allows_mesa_decision_to(target_status)


def laudo_deve_sinalizar_reabertura_pendente_apos_feedback_mesa(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> bool:
    return resolver_autoridade_mutacao_caso_tecnico(
        banco,
        laudo,
        cache=cache,
    ).should_signal_pending_reopen_from_mesa_feedback()


def resolver_alvo_reabertura_manual_laudo(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> ManualReopenTarget | None:
    return resolver_autoridade_mutacao_caso_tecnico(
        banco,
        laudo,
        cache=cache,
    ).resolve_manual_reopen_target()


def aplicar_finalizacao_inspetor_ao_laudo(
    laudo: Laudo,
    *,
    target_status: InspectorFinalizationTarget,
    occurred_at: datetime | None = None,
    clear_reopen_anchor: bool = True,
) -> datetime:
    timestamp = occurred_at or _agora_utc_state()
    if target_status == "aprovado":
        laudo.status_revisao = StatusRevisao.APROVADO.value
    elif target_status == "aguardando_mesa":
        laudo.status_revisao = StatusRevisao.AGUARDANDO.value
    else:
        raise ValueError(f"Inspector finalization target invalido: {target_status}")

    laudo.encerrado_pelo_inspetor_em = timestamp
    laudo.reabertura_pendente_em = None
    laudo.revisado_por = None
    laudo.motivo_rejeicao = None
    if clear_reopen_anchor:
        laudo.reaberto_em = None
    laudo.atualizado_em = timestamp
    return timestamp


def aplicar_decisao_mesa_ao_laudo(
    laudo: Laudo,
    *,
    target_status: MesaDecisionTarget,
    reviewer_id: int | None,
    rejection_reason: str | None = None,
    occurred_at: datetime | None = None,
    clear_reopen_anchor: bool = True,
) -> datetime:
    timestamp = occurred_at or _agora_utc_state()
    if target_status == "aprovado":
        laudo.status_revisao = StatusRevisao.APROVADO.value
        laudo.motivo_rejeicao = None
        laudo.reabertura_pendente_em = None
    elif target_status == "devolvido_para_correcao":
        laudo.status_revisao = StatusRevisao.REJEITADO.value
        laudo.motivo_rejeicao = str(rejection_reason or "").strip() or None
        laudo.reabertura_pendente_em = timestamp
    else:
        raise ValueError(f"Mesa decision target invalido: {target_status}")

    laudo.revisado_por = reviewer_id
    if clear_reopen_anchor:
        laudo.reaberto_em = None
    laudo.atualizado_em = timestamp
    return timestamp


def sinalizar_reabertura_pendente_por_feedback_mesa(
    laudo: Laudo,
    *,
    occurred_at: datetime | None = None,
) -> datetime:
    timestamp = occurred_at or _agora_utc_state()
    laudo.reabertura_pendente_em = timestamp
    laudo.atualizado_em = timestamp
    return timestamp


def aplicar_feedback_mesa_ao_laudo(
    banco: Session,
    laudo: Laudo,
    *,
    occurred_at: datetime | None = None,
    cache: CacheResumoLaudoRequest | None = None,
) -> datetime:
    timestamp = occurred_at or _agora_utc_state()
    if laudo_deve_sinalizar_reabertura_pendente_apos_feedback_mesa(
        banco,
        laudo,
        cache=cache,
    ):
        return sinalizar_reabertura_pendente_por_feedback_mesa(
            laudo,
            occurred_at=timestamp,
        )
    laudo.atualizado_em = timestamp
    return timestamp


def aplicar_reabertura_manual_ao_laudo(
    laudo: Laudo,
    *,
    target_status: ManualReopenTarget,
    reopened_at: datetime | None = None,
) -> datetime:
    if target_status not in {"laudo_em_coleta", "devolvido_para_correcao"}:
        raise ValueError(f"Manual reopen target invalido: {target_status}")

    timestamp = reopened_at or _agora_utc_state()
    laudo.status_revisao = StatusRevisao.RASCUNHO.value
    laudo.reaberto_em = timestamp
    laudo.reabertura_pendente_em = None
    laudo.encerrado_pelo_inspetor_em = None
    laudo.revisado_por = None
    laudo.motivo_rejeicao = None
    laudo.atualizado_em = timestamp
    return timestamp


def laudo_permite_reabrir(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> bool:
    status_card = obter_status_card_laudo(banco, laudo, cache=cache)
    return status_card in {"ajustes", "aprovado"}


def _laudo_e_rascunho_local_pristino(laudo: Laudo) -> bool:
    return (
        _normalizar_status_revisao_laudo(laudo) == StatusRevisao.RASCUNHO.value
        and getattr(laudo, "reaberto_em", None) is None
        and getattr(laudo, "revisado_por", None) is None
        and getattr(laudo, "encerrado_pelo_inspetor_em", None) is None
        and not laudo_tem_reabertura_pendente(laudo)
    )


def laudo_permite_exclusao_inspetor(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> bool:
    # Rascunhos locais ainda não enviados para a mesa podem ser descartados
    # mesmo quando o snapshot legado do sidebar demora a convergir.
    if _laudo_e_rascunho_local_pristino(laudo):
        return True

    snapshot = resolver_snapshot_leitura_caso_tecnico(banco, laudo, cache=cache)
    return str(snapshot.active_owner_role or "").strip() == "inspetor"


def obter_contexto_modo_entrada_laudo(laudo: Laudo | None) -> dict[str, str | None]:
    if laudo is None:
        return {
            "entry_mode_preference": None,
            "entry_mode_effective": None,
            "entry_mode_reason": None,
        }

    try:
        preference = normalizar_entry_mode_preference(getattr(laudo, "entry_mode_preference", None))
    except ValueError:
        preference = ENTRY_MODE_AUTO_RECOMMENDED

    effective = None
    try:
        effective = normalizar_entry_mode_effective(getattr(laudo, "entry_mode_effective", None))
    except ValueError:
        effective = None

    if effective:
        try:
            reason = normalizar_entry_mode_reason(getattr(laudo, "entry_mode_reason", None))
        except ValueError:
            reason = ENTRY_MODE_REASON_EXISTING_CASE_STATE
        return {
            "entry_mode_preference": preference,
            "entry_mode_effective": effective,
            "entry_mode_reason": reason,
        }

    decisao = resolver_modo_entrada_caso(
        requested_preference=preference,
    )
    return {
        "entry_mode_preference": decisao.preference,
        "entry_mode_effective": decisao.effective,
        "entry_mode_reason": decisao.reason,
    }


def serializar_contexto_case_lifecycle_legado(
    *,
    laudo: Laudo | None,
    legacy_payload: dict[str, Any] | None = None,
    tenant_id: object | None = None,
) -> dict[str, Any]:
    snapshot = build_technical_case_status_snapshot_from_legacy(
        tenant_id=tenant_id if tenant_id is not None else getattr(laudo, "empresa_id", ""),
        legacy_payload=legacy_payload or {},
        laudo=laudo,
    )
    return {
        "case_lifecycle_status": snapshot.case_lifecycle_status,
        "case_workflow_mode": snapshot.workflow_mode,
        "active_owner_role": snapshot.active_owner_role,
        "status_visual_label": build_case_status_visual_label(
            lifecycle_status=snapshot.case_lifecycle_status,
            active_owner_role=snapshot.active_owner_role,
        ),
        "allowed_next_lifecycle_statuses": list(snapshot.allowed_next_lifecycle_statuses),
        "allowed_lifecycle_transitions": [
            item.model_dump(mode="python")
            for item in snapshot.allowed_lifecycle_transitions
        ],
        "allowed_surface_actions": list(snapshot.allowed_surface_actions),
    }


def obter_guided_inspection_draft_laudo(laudo: Laudo | None) -> dict[str, Any] | None:
    if laudo is None:
        return None

    return _normalizar_guided_inspection_draft_payload(
        getattr(laudo, "guided_inspection_draft_json", None)
    )


def _resolver_guided_current_step_index(
    checklist: list[dict[str, Any]],
    completed_step_ids: list[str],
    preferred_index: object,
) -> int:
    if not checklist:
        return 0

    if completed_step_ids:
        completed = set(completed_step_ids)
        for index, item in enumerate(checklist):
            if str(item.get("id") or "").strip() not in completed:
                return index
        return len(checklist) - 1

    if not isinstance(preferred_index, (int, float, str, bytes, bytearray)):
        preferred = 0
    else:
        try:
            preferred = int(preferred_index or 0)
        except (TypeError, ValueError):
            preferred = 0
    return min(max(preferred, 0), len(checklist) - 1)


def _normalizar_guided_inspection_draft_payload(
    draft_raw: object,
) -> dict[str, Any] | None:
    if draft_raw is None:
        return None

    try:
        draft = GuidedInspectionDraftPayload.model_validate(draft_raw)
    except ValidationError:
        return None

    payload = draft.model_dump(mode="python")
    checklist = list(payload.get("checklist") or [])
    if not checklist:
        return None

    checklist_ids = {str(item.get("id") or "").strip() for item in checklist}
    payload["completed_step_ids"] = [
        step_id
        for step_id in payload.get("completed_step_ids") or []
        if step_id in checklist_ids
    ]
    payload["current_step_index"] = _resolver_guided_current_step_index(
        checklist,
        payload["completed_step_ids"],
        payload.get("current_step_index"),
    )
    evidence_refs: list[dict[str, Any]] = []
    message_ids_vistos: set[int] = set()
    for item in payload.get("evidence_refs") or []:
        step_id = str(item.get("step_id") or "").strip()
        if step_id not in checklist_ids:
            continue
        try:
            message_id = int(item.get("message_id") or 0)
        except (TypeError, ValueError):
            continue
        if message_id <= 0 or message_id in message_ids_vistos:
            continue
        message_ids_vistos.add(message_id)
        evidence_refs.append(
            {
                "message_id": message_id,
                "step_id": step_id,
                "step_title": str(item.get("step_title") or "").strip()[:120],
                "captured_at": str(item.get("captured_at") or "").strip()[:64],
                "evidence_kind": "chat_message",
                "attachment_kind": str(item.get("attachment_kind") or "none").strip() or "none",
            }
        )
    payload["evidence_refs"] = evidence_refs

    mesa_handoff = payload.get("mesa_handoff")
    if isinstance(mesa_handoff, dict):
        step_id = str(mesa_handoff.get("step_id") or "").strip()
        if step_id not in checklist_ids:
            payload["mesa_handoff"] = None

    payload["evidence_bundle_kind"] = "case_thread"
    return payload


def mesclar_guided_inspection_draft_laudo(
    *,
    laudo: Laudo,
    draft_payload: GuidedInspectionDraftPayload | None = None,
    evidence_ref: GuidedInspectionEvidenceRefPayload | None = None,
    mesa_handoff: GuidedInspectionMesaHandoffPayload | None = None,
) -> dict[str, Any] | None:
    payload_base = _normalizar_guided_inspection_draft_payload(
        draft_payload.model_dump(mode="python")
        if draft_payload is not None
        else getattr(laudo, "guided_inspection_draft_json", None)
    )
    if payload_base is None:
        return None

    if evidence_ref is not None:
        refs_existentes = [
            item
            for item in payload_base.get("evidence_refs") or []
            if int(item.get("message_id") or 0) != int(evidence_ref.message_id)
        ]
        refs_existentes.append(evidence_ref.model_dump(mode="python"))
        payload_base["evidence_refs"] = refs_existentes
        completed_step_ids = [
            str(item).strip()
            for item in payload_base.get("completed_step_ids") or []
            if str(item).strip()
        ]
        if evidence_ref.step_id not in completed_step_ids:
            completed_step_ids.append(evidence_ref.step_id)
        payload_base["completed_step_ids"] = completed_step_ids

    if mesa_handoff is not None and not payload_base.get("mesa_handoff"):
        payload_base["mesa_handoff"] = mesa_handoff.model_dump(mode="python")

    payload_normalizado = _normalizar_guided_inspection_draft_payload(payload_base)
    if payload_normalizado is None:
        return None

    laudo.guided_inspection_draft_json = payload_normalizado
    return payload_normalizado


def serializar_card_laudo(
    banco: Session,
    laudo: Laudo,
    *,
    cache: CacheResumoLaudoRequest | None = None,
) -> dict[str, Any]:
    laudo_id = int(laudo.id)
    if cache is not None and laudo_id in cache.card_por_laudo:
        return cache.card_por_laudo[laudo_id]

    status_card = obter_status_card_laudo(banco, laudo, cache=cache)
    preview = limpar_texto_visivel_chat(
        str(laudo.primeira_mensagem or ""),
        fallback_hidden_only="Evidência enviada",
    )
    titulo = str(laudo.setor_industrial or "").strip() or nome_template_humano(str(laudo.tipo_template or "padrao"))

    payload = {
        "id": laudo_id,
        "titulo": titulo,
        "preview": preview,
        "pinado": bool(laudo.pinado),
        "data_iso": laudo.criado_em.strftime("%Y-%m-%d"),
        "data_br": laudo.criado_em.strftime("%d/%m/%Y"),
        "hora_br": laudo.criado_em.strftime("%H:%M"),
        "tipo_template": str(laudo.tipo_template or "padrao"),
        "status_revisao": _normalizar_status_revisao_laudo(laudo),
        "status_card": status_card,
        "status_card_label": CARD_STATUS_LABELS.get(status_card, "Laudo"),
        "permite_edicao": laudo_permite_edicao_inspetor(laudo),
        "permite_exclusao": laudo_permite_exclusao_inspetor(banco, laudo, cache=cache),
        "permite_reabrir": laudo_permite_reabrir(banco, laudo, cache=cache),
        "possui_historico": status_card != "oculto",
        **obter_contexto_modo_entrada_laudo(laudo),
    }
    payload.update(
        serializar_contexto_case_lifecycle_legado(
            laudo=laudo,
            legacy_payload={
                "estado": obter_estado_api_laudo(banco, laudo, cache=cache),
                "laudo_id": laudo_id if status_card != "oculto" else None,
                "status_card": status_card,
                "permite_reabrir": payload["permite_reabrir"],
                "laudo_card": payload,
            },
        )
    )
    if cache is not None:
        cache.card_por_laudo[laudo_id] = payload
    return payload


__all__ = [
    "CacheResumoLaudoRequest",
    "CARD_STATUS_LABELS",
    "InspectorMutationSurface",
    "LaudoLifecycleAuthority",
    "ManualReopenTarget",
    "MesaDecisionTarget",
    "TechnicalCaseMutationAuthority",
    "criar_cache_resumo_laudos",
    "aplicar_feedback_mesa_ao_laudo",
    "aplicar_decisao_mesa_ao_laudo",
    "aplicar_finalizacao_inspetor_ao_laudo",
    "aplicar_reabertura_manual_ao_laudo",
    "build_legacy_case_lifecycle_read_payload",
    "laudo_tem_reabertura_pendente",
    "laudo_tem_interacao",
    "laudo_possui_historico_visivel",
    "obter_status_card_laudo",
    "obter_estado_api_laudo",
    "obter_guided_inspection_draft_laudo",
    "mesclar_guided_inspection_draft_laudo",
    "precarregar_interacoes_laudos",
    "laudo_permite_edicao_inspetor",
    "laudo_permite_exclusao_inspetor",
    "laudo_permite_transicao_decisao_mesa",
    "laudo_permite_transicao_finalizacao_inspetor",
    "obter_detalhe_bloqueio_edicao_inspetor",
    "laudo_aceita_avaliacao_mesa",
    "laudo_deve_sinalizar_reabertura_pendente_apos_feedback_mesa",
    "obter_detalhe_bloqueio_avaliacao_mesa",
    "resolver_autoridade_lifecycle_laudo",
    "resolver_autoridade_mutacao_caso_tecnico",
    "resolver_snapshot_leitura_caso_tecnico",
    "resolver_alvo_reabertura_manual_laudo",
    "sinalizar_reabertura_pendente_por_feedback_mesa",
    "laudo_permite_reabrir",
    "obter_contexto_modo_entrada_laudo",
    "serializar_contexto_case_lifecycle_legado",
    "serializar_card_laudo",
]
