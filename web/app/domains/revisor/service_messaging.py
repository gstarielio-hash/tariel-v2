from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.chat.laudo_state_helpers import (
    aplicar_feedback_mesa_ao_laudo,
    aplicar_decisao_mesa_ao_laudo,
    laudo_permite_transicao_decisao_mesa,
    obter_detalhe_bloqueio_avaliacao_mesa,
    resolver_snapshot_leitura_caso_tecnico,
)
from app.domains.chat.template_governance import reaffirm_case_bound_template_governance
from app.domains.mesa.attachments import (
    conteudo_mensagem_mesa_com_anexo,
    remover_arquivo_anexo_mesa,
    resumo_mensagem_mesa,
    salvar_arquivo_anexo_mesa,
)
from app.domains.mesa.operational_tasks import (
    build_coverage_return_request_metadata,
    build_coverage_return_request_text,
    extract_operational_context,
)
from app.domains.revisor.base import (
    _agora_utc,
    _marcar_whispers_lidos_laudo,
    _nome_resolvedor_mensagem,
    _registrar_mensagem_revisor,
    _serializar_mensagem,
    _validar_destinatario_whisper,
    logger,
)
from app.domains.revisor.common import _obter_laudo_empresa
from app.domains.revisor.service_contracts import (
    AvaliacaoLaudoResult,
    CoverageReturnRequestResult,
    PendenciaMesaResult,
    RespostaChatAnexoResult,
    RespostaChatResult,
    WhisperRespostaResult,
)
from app.shared.database import AnexoMesa, MensagemLaudo, StatusRevisao, TipoMensagem, Usuario, commit_ou_rollback_operacional
from app.shared.tenant_entitlement_guard import ensure_tenant_capability_for_user
from app.shared.operational_memory_hooks import (
    ensure_approved_case_snapshot_for_laudo,
    find_replayable_approved_case_snapshot_for_laudo,
    record_return_to_inspector_irregularity,
    resolve_open_return_to_inspector_irregularities,
)
from app.v2.acl.technical_case_core import build_case_status_visual_label
from app.v2.report_pack_rollout_metrics import record_report_pack_review_decision
from nucleo.inspetor.referencias_mensagem import compor_texto_com_referencia


def _build_avaliacao_case_fields(case_snapshot) -> dict[str, Any]:
    return {
        "case_status": str(case_snapshot.canonical_status or ""),
        "case_lifecycle_status": str(case_snapshot.case_lifecycle_status or ""),
        "case_workflow_mode": str(case_snapshot.workflow_mode or ""),
        "active_owner_role": str(case_snapshot.active_owner_role or ""),
        "allowed_next_lifecycle_statuses": [
            str(item or "").strip()
            for item in list(case_snapshot.allowed_next_lifecycle_statuses or [])
            if str(item or "").strip()
        ],
        "allowed_surface_actions": [
            str(item or "").strip()
            for item in list(case_snapshot.allowed_surface_actions or [])
            if str(item or "").strip()
        ],
        "status_visual_label": build_case_status_visual_label(
            lifecycle_status=case_snapshot.case_lifecycle_status,
            active_owner_role=case_snapshot.active_owner_role,
        ),
    }


def garantir_referencia_mensagem(
    banco: Session,
    *,
    laudo_id: int,
    referencia_mensagem_id: int | None,
) -> None:
    if not referencia_mensagem_id:
        return

    referencia_existe = banco.scalar(
        select(MensagemLaudo.id).where(
            MensagemLaudo.laudo_id == laudo_id,
            MensagemLaudo.id == referencia_mensagem_id,
        )
    )
    if not referencia_existe:
        raise HTTPException(status_code=404, detail="Mensagem de referência não encontrada.")


def avaliar_laudo_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    revisor_id: int,
    revisor_nome: str,
    acao: str,
    motivo: str,
    resposta_api: bool,
    modo_schemathesis: bool,
) -> AvaliacaoLaudoResult:
    revisor = banco.get(Usuario, int(revisor_id))
    ensure_tenant_capability_for_user(
        revisor,
        capability="reviewer_decision",
    )
    laudo = _obter_laudo_empresa(banco, laudo_id, empresa_id)
    reaffirm_case_bound_template_governance(laudo=laudo)
    acao_normalizada = str(acao or "").strip().lower()
    motivo_normalizado = str(motivo or "").strip()
    if acao_normalizada not in {"aprovar", "rejeitar"}:
        raise HTTPException(status_code=400, detail="Ação inválida.")
    target_case_lifecycle_status: Literal["devolvido_para_correcao", "aprovado"] = (
        "aprovado"
        if acao_normalizada == "aprovar"
        else "devolvido_para_correcao"
    )
    case_snapshot = resolver_snapshot_leitura_caso_tecnico(banco, laudo)
    approval_replay_allowed = (
        str(case_snapshot.case_lifecycle_status or "").strip() in {"aprovado", "emitido"}
        and str(case_snapshot.active_owner_role or "").strip() == "none"
    )

    if (
        acao_normalizada == "aprovar"
        and not modo_schemathesis
        and approval_replay_allowed
        and laudo.status_revisao == StatusRevisao.APROVADO.value
    ):
        snapshot_replay = find_replayable_approved_case_snapshot_for_laudo(
            banco,
            laudo=laudo,
            approved_by_id=revisor_id,
            document_outcome="approved_by_mesa",
            mesa_resolution_summary={
                "decision": "aprovar",
                "reviewer_id": revisor_id,
                "reviewer_name": revisor_nome,
                "motivo": "",
                "message_id": None,
            },
        )
        if snapshot_replay is not None:
            return AvaliacaoLaudoResult(
                laudo_id=laudo.id,
                acao=acao_normalizada,
                status_revisao=laudo.status_revisao,
                motivo=str(laudo.motivo_rejeicao or "").strip(),
                modo_schemathesis=False,
                idempotent_replay=True,
                inspetor_id=laudo.usuario_id,
                mensagem_id=None,
                texto_notificacao_inspetor="",
                **_build_avaliacao_case_fields(case_snapshot),
            )

    if not modo_schemathesis and not laudo_permite_transicao_decisao_mesa(
        banco,
        laudo,
        target_status=target_case_lifecycle_status,
    ):
        raise HTTPException(
            status_code=400,
            detail=obter_detalhe_bloqueio_avaliacao_mesa(laudo),
        )

    texto_notificacao_inspetor = ""
    conteudo_notificacao = ""
    status_destino = laudo.status_revisao
    motivo_rejeicao = laudo.motivo_rejeicao
    approval_idempotent_replay = False

    if acao_normalizada == "aprovar":
        status_destino = StatusRevisao.APROVADO.value
        motivo_rejeicao = None
        texto_notificacao_inspetor = "✅ Seu laudo foi aprovado pela mesa avaliadora."
        conteudo_notificacao = "✅ **APROVADO!** Laudo finalizado e liberado com ART."
        logger.info("Laudo aprovado | laudo=%s | revisor=%s", laudo_id, revisor_nome)
    elif acao_normalizada == "rejeitar":
        if not motivo_normalizado:
            if resposta_api:
                motivo_normalizado = "Devolvido pela mesa sem motivo detalhado."
            else:
                raise HTTPException(status_code=400, detail="Motivo obrigatório.")

        status_destino = StatusRevisao.REJEITADO.value
        motivo_rejeicao = motivo_normalizado
        texto_notificacao_inspetor = f"⚠️ Seu laudo foi rejeitado. Motivo: {motivo_normalizado}"
        conteudo_notificacao = f"⚠️ **REJEITADO** Motivo: {motivo_normalizado}\n\nCorrija e reenvie."
        logger.info("Laudo rejeitado | laudo=%s | revisor=%s", laudo_id, revisor_nome)

    if modo_schemathesis:
        return AvaliacaoLaudoResult(
            laudo_id=laudo.id,
            acao=acao_normalizada,
            status_revisao=status_destino,
            motivo=motivo_rejeicao or "",
            modo_schemathesis=True,
            **_build_avaliacao_case_fields(case_snapshot),
        )

    aplicar_decisao_mesa_ao_laudo(
        laudo,
        target_status=target_case_lifecycle_status,
        reviewer_id=revisor_id,
        rejection_reason=motivo_rejeicao,
        occurred_at=_agora_utc(),
        clear_reopen_anchor=target_case_lifecycle_status != "aprovado",
    )

    mensagem_notificacao: MensagemLaudo | None = _registrar_mensagem_revisor(
        banco,
        laudo_id=laudo.id,
        usuario_id=revisor_id,
        tipo=TipoMensagem.HUMANO_ENG,
        conteudo=conteudo_notificacao,
    )
    banco.flush()

    try:
        if status_destino == StatusRevisao.APROVADO.value:
            _snapshot, approval_idempotent_replay = ensure_approved_case_snapshot_for_laudo(
                banco,
                laudo=laudo,
                approved_by_id=revisor_id,
                document_outcome="approved_by_mesa",
                mesa_resolution_summary={
                    "decision": acao_normalizada,
                    "reviewer_id": revisor_id,
                    "reviewer_name": revisor_nome,
                    "motivo": motivo_rejeicao or "",
                    "message_id": int(mensagem_notificacao.id) if mensagem_notificacao else None,
                },
            )
            if approval_idempotent_replay:
                mensagem_notificacao = None
        elif status_destino == StatusRevisao.REJEITADO.value:
            record_return_to_inspector_irregularity(
                banco,
                laudo=laudo,
                actor_user_id=revisor_id,
                event_type="block_returned_to_inspector",
                block_key="review_decision:final",
                severity="warning",
                source="mesa",
                details={
                    "decision": acao_normalizada,
                    "reviewer_id": revisor_id,
                    "reviewer_name": revisor_nome,
                    "reason": motivo_rejeicao or "",
                    "message_id": int(mensagem_notificacao.id) if mensagem_notificacao else None,
                },
            )
        else:
            resolve_open_return_to_inspector_irregularities(
                banco,
                laudo_id=int(laudo.id),
                resolved_by_id=revisor_id,
                resolution_mode="edited_case_data",
                resolution_notes="Fluxo de revisao consolidado sem bloqueios pendentes.",
            )
    except Exception:
        logger.warning(
            "Falha ao registrar memoria operacional da decisao da mesa | laudo=%s | acao=%s",
            laudo_id,
            acao_normalizada,
            exc_info=True,
        )

    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao confirmar avaliacao do laudo pela mesa.",
    )
    record_report_pack_review_decision(
        laudo=laudo,
        action=acao_normalizada,
        status_revisao=laudo.status_revisao,
    )
    decision_snapshot = resolver_snapshot_leitura_caso_tecnico(banco, laudo)
    return AvaliacaoLaudoResult(
        laudo_id=laudo.id,
        acao=acao_normalizada,
        status_revisao=laudo.status_revisao,
        motivo=laudo.motivo_rejeicao or "",
        modo_schemathesis=False,
        idempotent_replay=approval_idempotent_replay,
        inspetor_id=laudo.usuario_id,
        mensagem_id=mensagem_notificacao.id if mensagem_notificacao else None,
        texto_notificacao_inspetor=texto_notificacao_inspetor,
        **_build_avaliacao_case_fields(decision_snapshot),
    )


def registrar_whisper_resposta_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    revisor_id: int,
    mensagem: str,
    destinatario_id: int,
    referencia_mensagem_id: int | None,
) -> WhisperRespostaResult:
    laudo = _obter_laudo_empresa(banco, laudo_id, empresa_id)
    destinatario = _validar_destinatario_whisper(
        banco,
        destinatario_id=destinatario_id,
        empresa_id=empresa_id,
        laudo=laudo,
    )
    garantir_referencia_mensagem(
        banco,
        laudo_id=laudo.id,
        referencia_mensagem_id=referencia_mensagem_id,
    )

    texto_mensagem = str(mensagem or "").strip()
    mensagem_salva = _registrar_mensagem_revisor(
        banco,
        laudo_id=laudo.id,
        usuario_id=revisor_id,
        tipo=TipoMensagem.HUMANO_ENG,
        conteudo=compor_texto_com_referencia(
            f"💬 **Engenharia:** {texto_mensagem}",
            referencia_mensagem_id,
        ),
    )
    laudo.atualizado_em = _agora_utc()
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao confirmar whisper da mesa.",
    )

    return WhisperRespostaResult(
        laudo_id=laudo.id,
        destinatario_id=destinatario.id,
        mensagem_id=mensagem_salva.id,
        referencia_mensagem_id=referencia_mensagem_id,
        preview=texto_mensagem[:120],
    )


def registrar_resposta_chat_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    revisor_id: int,
    texto: str,
    referencia_mensagem_id: int | None,
    revisor_nome: str,
) -> RespostaChatResult:
    laudo = _obter_laudo_empresa(banco, laudo_id, empresa_id)
    texto_limpo = str(texto or "").strip()
    if not texto_limpo:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")

    garantir_referencia_mensagem(
        banco,
        laudo_id=laudo.id,
        referencia_mensagem_id=referencia_mensagem_id,
    )

    mensagem_salva = _registrar_mensagem_revisor(
        banco,
        laudo_id=laudo.id,
        usuario_id=revisor_id,
        tipo=TipoMensagem.HUMANO_ENG,
        conteudo=compor_texto_com_referencia(texto_limpo, referencia_mensagem_id),
    )
    aplicar_feedback_mesa_ao_laudo(
        banco,
        laudo,
        occurred_at=_agora_utc(),
    )
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao confirmar resposta textual da mesa.",
    )

    logger.info(
        "Chat engenharia | laudo=%s | revisor=%s | len=%d",
        laudo_id,
        revisor_nome,
        len(texto_limpo),
    )
    return RespostaChatResult(
        laudo_id=laudo.id,
        inspetor_id=laudo.usuario_id,
        mensagem_id=mensagem_salva.id,
        referencia_mensagem_id=referencia_mensagem_id,
        texto_notificacao=texto_limpo,
        mensagem_payload=_serializar_mensagem(mensagem_salva, com_data_longa=True),
    )


def _carregar_pendencia_coverage_aberta(
    banco: Session,
    *,
    laudo_id: int,
    evidence_key: str,
    block_key: str,
) -> MensagemLaudo | None:
    mensagens = (
        banco.execute(
            select(MensagemLaudo)
            .where(
                MensagemLaudo.laudo_id == int(laudo_id),
                MensagemLaudo.tipo == TipoMensagem.HUMANO_ENG.value,
                MensagemLaudo.lida.is_(False),
            )
            .order_by(MensagemLaudo.id.desc())
        )
        .scalars()
        .all()
    )
    for mensagem in mensagens:
        contexto = extract_operational_context(mensagem)
        if contexto is None:
            continue
        if (
            str(contexto.get("evidence_key") or "").strip() == str(evidence_key).strip()
            and str(contexto.get("block_key") or "").strip() == str(block_key).strip()
        ):
            return mensagem
    return None


def solicitar_refazer_item_coverage_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    revisor_id: int,
    revisor_nome: str,
    evidence_key: str,
    title: str,
    kind: str,
    required: bool,
    source_status: str | None,
    operational_status: str | None,
    mesa_status: str | None,
    component_type: str | None,
    view_angle: str | None,
    severity: str,
    summary: str | None,
    required_action: str | None,
    failure_reasons: list[str] | None,
) -> CoverageReturnRequestResult:
    laudo = _obter_laudo_empresa(banco, laudo_id, empresa_id)
    metadata = build_coverage_return_request_metadata(
        evidence_key=evidence_key,
        title=title,
        kind=kind,
        required=required,
        source_status=source_status,
        operational_status=operational_status,
        mesa_status=mesa_status,
        component_type=component_type,
        view_angle=view_angle,
        severity=severity,
        summary=summary,
        required_action=required_action,
        failure_reasons=failure_reasons,
    )
    texto_pendencia = build_coverage_return_request_text(metadata)
    block_key = str(metadata.get("block_key") or "").strip()
    evidence_key_limpo = str(metadata.get("evidence_key") or evidence_key).strip()

    mensagem_salva = _carregar_pendencia_coverage_aberta(
        banco,
        laudo_id=int(laudo.id),
        evidence_key=evidence_key_limpo,
        block_key=block_key,
    )
    if mensagem_salva is not None:
        mensagem_salva.conteudo = texto_pendencia
        mensagem_salva.metadata_json = metadata
        mensagem_salva.lida = False
        mensagem_salva.resolvida_por_id = None
        mensagem_salva.resolvida_em = None
    else:
        mensagem_salva = _registrar_mensagem_revisor(
            banco,
            laudo_id=laudo.id,
            usuario_id=revisor_id,
            tipo=TipoMensagem.HUMANO_ENG,
            conteudo=texto_pendencia,
            metadata_json=metadata,
        )
        banco.flush()

    aplicar_feedback_mesa_ao_laudo(
        banco,
        laudo,
        occurred_at=_agora_utc(),
    )
    banco.flush()

    try:
        record_return_to_inspector_irregularity(
            banco,
            laudo=laudo,
            actor_user_id=revisor_id,
            event_type="block_returned_to_inspector",
            block_key=block_key,
            evidence_key=evidence_key_limpo,
            severity=severity,
            source="mesa",
            details={
                "message_id": int(mensagem_salva.id),
                "reviewer_id": revisor_id,
                "reviewer_name": revisor_nome,
                "title": str(metadata.get("title") or ""),
                "kind": str(metadata.get("kind") or ""),
                "summary": str(metadata.get("summary") or ""),
                "required_action": str(metadata.get("required_action") or ""),
                "failure_reasons": list(metadata.get("failure_reasons") or []),
                "expected_reply_mode": str(metadata.get("expected_reply_mode") or ""),
            },
        )
    except Exception:
        logger.warning(
            "Falha ao registrar irregularidade de coverage devolvido ao inspetor | laudo=%s | evidence_key=%s",
            laudo_id,
            evidence_key_limpo,
            exc_info=True,
        )

    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao solicitar refazer do item de coverage.",
    )

    return CoverageReturnRequestResult(
        laudo_id=laudo.id,
        inspetor_id=laudo.usuario_id,
        mensagem_id=mensagem_salva.id,
        evidence_key=evidence_key_limpo,
        block_key=block_key,
        texto_notificacao=f"Refazer solicitado pela mesa: {str(metadata.get('title') or 'item de coverage')}.",
        mensagem_payload=_serializar_mensagem(mensagem_salva, com_data_longa=True),
    )


def registrar_resposta_chat_com_anexo_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    revisor_id: int,
    nome_arquivo: str,
    mime_type: str,
    conteudo_arquivo: bytes,
    texto: str,
    referencia_mensagem_id: int | None,
) -> RespostaChatAnexoResult:
    laudo = _obter_laudo_empresa(banco, laudo_id, empresa_id)
    texto_limpo = str(texto or "").strip()
    garantir_referencia_mensagem(
        banco,
        laudo_id=laudo.id,
        referencia_mensagem_id=referencia_mensagem_id,
    )

    dados_arquivo = salvar_arquivo_anexo_mesa(
        empresa_id=empresa_id,
        laudo_id=laudo.id,
        nome_original=nome_arquivo,
        mime_type=mime_type,
        conteudo=conteudo_arquivo,
    )

    try:
        mensagem_salva = _registrar_mensagem_revisor(
            banco,
            laudo_id=laudo.id,
            usuario_id=revisor_id,
            tipo=TipoMensagem.HUMANO_ENG,
            conteudo=compor_texto_com_referencia(
                conteudo_mensagem_mesa_com_anexo(texto_limpo),
                referencia_mensagem_id,
            ),
        )
        banco.flush()

        anexo = AnexoMesa(
            laudo_id=laudo.id,
            mensagem_id=mensagem_salva.id,
            enviado_por_id=revisor_id,
            nome_original=dados_arquivo["nome_original"],
            nome_arquivo=dados_arquivo["nome_arquivo"],
            mime_type=dados_arquivo["mime_type"],
            categoria=dados_arquivo["categoria"],
            tamanho_bytes=dados_arquivo["tamanho_bytes"],
            caminho_arquivo=dados_arquivo["caminho_arquivo"],
        )
        mensagem_salva.anexos_mesa.append(anexo)

        aplicar_feedback_mesa_ao_laudo(
            banco,
            laudo,
            occurred_at=_agora_utc(),
        )
        commit_ou_rollback_operacional(
            banco,
            logger_operacao=logger,
            mensagem_erro="Falha ao confirmar resposta da mesa com anexo.",
        )
    except Exception:
        banco.rollback()
        remover_arquivo_anexo_mesa(dados_arquivo.get("caminho_arquivo"))
        raise

    resumo_notificacao = resumo_mensagem_mesa(
        mensagem_salva.conteudo,
        anexos=[anexo],
    )
    return RespostaChatAnexoResult(
        laudo_id=laudo.id,
        inspetor_id=laudo.usuario_id,
        mensagem_id=mensagem_salva.id,
        referencia_mensagem_id=referencia_mensagem_id,
        texto_notificacao=resumo_notificacao,
        mensagem_payload=_serializar_mensagem(mensagem_salva, com_data_longa=True),
    )


def carregar_anexo_mesa_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    anexo_id: int,
) -> AnexoMesa:
    laudo = _obter_laudo_empresa(banco, laudo_id, empresa_id)
    anexo = (
        banco.query(AnexoMesa)
        .filter(
            AnexoMesa.id == anexo_id,
            AnexoMesa.laudo_id == laudo.id,
        )
        .first()
    )
    if not anexo or not str(anexo.caminho_arquivo or "").strip() or not os.path.isfile(str(anexo.caminho_arquivo)):
        raise HTTPException(status_code=404, detail="Anexo da mesa não encontrado.")
    return anexo


def marcar_whispers_lidos_revisor(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
) -> int:
    _obter_laudo_empresa(banco, laudo_id, empresa_id)
    total = _marcar_whispers_lidos_laudo(banco, laudo_id=laudo_id)
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao marcar whispers da mesa como lidos.",
    )
    return total


def atualizar_pendencia_mesa_revisor_status(
    banco: Session,
    *,
    laudo_id: int,
    empresa_id: int,
    mensagem_id: int,
    lida: bool,
    revisor_id: int,
) -> PendenciaMesaResult:
    laudo = _obter_laudo_empresa(banco, laudo_id, empresa_id)
    mensagem = (
        banco.query(MensagemLaudo)
        .filter(
            MensagemLaudo.id == mensagem_id,
            MensagemLaudo.laudo_id == laudo.id,
            MensagemLaudo.tipo == TipoMensagem.HUMANO_ENG.value,
        )
        .first()
    )
    if not mensagem:
        raise HTTPException(status_code=404, detail="Pendência da mesa não encontrada.")

    mensagem.lida = bool(lida)
    if mensagem.lida:
        mensagem.resolvida_por_id = revisor_id
        mensagem.resolvida_em = _agora_utc()
        texto_notificacao = f"Pendência #{mensagem.id} marcada como resolvida pela mesa."
    else:
        mensagem.resolvida_por_id = None
        mensagem.resolvida_em = None
        texto_notificacao = f"Pendência #{mensagem.id} foi reaberta pela mesa."

    if not mensagem.lida:
        aplicar_feedback_mesa_ao_laudo(
            banco,
            laudo,
            occurred_at=_agora_utc(),
        )
    else:
        laudo.atualizado_em = _agora_utc()
    banco.flush()

    try:
        block_key = f"mesa_pendency:{int(mensagem.id)}"
        if mensagem.lida:
            resolve_open_return_to_inspector_irregularities(
                banco,
                laudo_id=int(laudo.id),
                resolved_by_id=revisor_id,
                resolution_mode="edited_case_data",
                resolution_notes=texto_notificacao,
                block_key=block_key,
            )
        else:
            record_return_to_inspector_irregularity(
                banco,
                laudo=laudo,
                actor_user_id=revisor_id,
                event_type="field_reopened",
                block_key=block_key,
                severity="warning",
                source="mesa",
                details={
                    "mensagem_id": int(mensagem.id),
                    "texto_pendencia": resumo_mensagem_mesa(mensagem.conteudo),
                    "resolved_by_id": revisor_id,
                },
            )
    except Exception:
        logger.warning(
            "Falha ao registrar memoria operacional da pendencia da mesa | laudo=%s | mensagem=%s",
            laudo_id,
            mensagem_id,
            exc_info=True,
        )

    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao atualizar status da pendencia da mesa.",
    )
    banco.refresh(mensagem)

    pendencias_abertas = (
        banco.query(func.count(MensagemLaudo.id))
        .filter(
            MensagemLaudo.laudo_id == laudo.id,
            MensagemLaudo.tipo == TipoMensagem.HUMANO_ENG.value,
            MensagemLaudo.lida.is_(False),
        )
        .scalar()
        or 0
    )

    return PendenciaMesaResult(
        laudo_id=laudo.id,
        mensagem_id=mensagem.id,
        lida=bool(mensagem.lida),
        resolvida_por_id=mensagem.resolvida_por_id,
        resolvida_por_nome=_nome_resolvedor_mensagem(mensagem),
        resolvida_em=mensagem.resolvida_em.isoformat() if mensagem.resolvida_em else "",
        pendencias_abertas=int(pendencias_abertas),
        inspetor_id=laudo.usuario_id,
        texto_notificacao=texto_notificacao,
    )


__all__ = [
    "atualizar_pendencia_mesa_revisor_status",
    "avaliar_laudo_revisor",
    "carregar_anexo_mesa_revisor",
    "garantir_referencia_mensagem",
    "marcar_whispers_lidos_revisor",
    "solicitar_refazer_item_coverage_revisor",
    "registrar_resposta_chat_com_anexo_revisor",
    "registrar_resposta_chat_revisor",
    "registrar_whisper_resposta_revisor",
]
