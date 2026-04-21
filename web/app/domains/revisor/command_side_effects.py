from __future__ import annotations

from typing import Any

from app.domains.revisor.base import logger
from app.domains.revisor.command_handlers import (
    ReviewCoverageReturnCommand,
    ReviewDecisionCommand,
    ReviewPendencyStatusCommand,
    ReviewReplyAttachmentCommand,
    ReviewReplyCommand,
    ReviewWhisperReplyCommand,
)
from app.domains.revisor.realtime import (
    notificar_inspetor_sse,
    notificar_whisper_resposta_revisor,
)
from app.domains.revisor.service_contracts import (
    AvaliacaoLaudoResult,
    CoverageReturnRequestResult,
    PendenciaMesaResult,
    RespostaChatAnexoResult,
    RespostaChatResult,
    WhisperRespostaResult,
)
from sqlalchemy.orm import Session
from app.shared.database import RegistroAuditoriaEmpresa, Usuario, agora_utc


def _reviewer_name(usuario: Usuario) -> str:
    nome = getattr(usuario, "nome", None) or getattr(usuario, "nome_completo", None)
    return str(nome or f"Revisor #{getattr(usuario, 'id', '-')}")


def _registrar_auditoria_revisor_segura(
    *,
    banco: Session,
    usuario: Usuario,
    acao: str,
    resumo: str,
    detalhe: str = "",
    alvo_usuario_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    try:
        timestamp = agora_utc()
        registro = RegistroAuditoriaEmpresa(
            empresa_id=int(getattr(usuario, "empresa_id")),
            ator_usuario_id=int(getattr(usuario, "id")) if getattr(usuario, "id", None) is not None else None,
            alvo_usuario_id=int(alvo_usuario_id) if alvo_usuario_id is not None else None,
            portal="revisor",
            acao=str(acao or "acao").strip()[:80],
            resumo=str(resumo or "Ação registrada").strip()[:220],
            detalhe=(str(detalhe or "").strip() or None),
            payload_json=payload or None,
            criado_em=timestamp,
            atualizado_em=timestamp,
        )
        banco.add(registro)
        banco.flush()
    except Exception:
        logger.warning(
            "Falha ao registrar auditoria do revisor | empresa_id=%s | ator_usuario_id=%s | acao=%s",
            getattr(usuario, "empresa_id", None),
            getattr(usuario, "id", None),
            acao,
            exc_info=True,
        )


async def run_review_decision_side_effects(
    *,
    command: ReviewDecisionCommand,
    result: AvaliacaoLaudoResult,
) -> None:
    if result.modo_schemathesis or result.idempotent_replay:
        return

    reviewer_name = _reviewer_name(command.usuario)
    await notificar_inspetor_sse(
        inspetor_id=result.inspetor_id,
        laudo_id=result.laudo_id,
        tipo="mensagem_eng",
        texto=result.texto_notificacao_inspetor,
        mensagem_id=result.mensagem_id,
        de_usuario_id=getattr(command.usuario, "id", None),
        de_nome=reviewer_name,
    )
    _registrar_auditoria_revisor_segura(
        banco=command.banco,
        usuario=command.usuario,
        acao="mesa_laudo_avaliado",
        resumo=f"Mesa {result.acao} o laudo #{result.laudo_id}.",
        detalhe=(
            f"Status final: {result.status_revisao}."
            + (f" Motivo: {result.motivo}" if str(result.motivo or "").strip() else "")
        ),
        alvo_usuario_id=result.inspetor_id,
        payload={
            "laudo_id": result.laudo_id,
            "acao": result.acao,
            "status_revisao": result.status_revisao,
            "motivo": result.motivo,
            "mensagem_id": result.mensagem_id,
        },
    )


async def run_review_reply_side_effects(
    *,
    command: ReviewReplyCommand,
    result: RespostaChatResult,
) -> None:
    reviewer_name = _reviewer_name(command.usuario)
    await notificar_inspetor_sse(
        inspetor_id=result.inspetor_id,
        laudo_id=result.laudo_id,
        tipo="mensagem_eng",
        texto=result.texto_notificacao,
        mensagem_id=result.mensagem_id,
        referencia_mensagem_id=result.referencia_mensagem_id,
        de_usuario_id=getattr(command.usuario, "id", None),
        de_nome=reviewer_name,
        mensagem=result.mensagem_payload,
    )
    _registrar_auditoria_revisor_segura(
        banco=command.banco,
        usuario=command.usuario,
        acao="mesa_resposta_enviada",
        resumo=f"Mesa respondeu o laudo #{result.laudo_id}.",
        detalhe="Mensagem textual enviada ao inspetor.",
        alvo_usuario_id=result.inspetor_id,
        payload={
            "laudo_id": result.laudo_id,
            "mensagem_id": result.mensagem_id,
            "referencia_mensagem_id": result.referencia_mensagem_id,
            "texto_preview": str(command.texto or "").strip()[:160],
        },
    )


async def run_review_reply_attachment_side_effects(
    *,
    command: ReviewReplyAttachmentCommand,
    result: RespostaChatAnexoResult,
) -> None:
    reviewer_name = _reviewer_name(command.usuario)
    await notificar_inspetor_sse(
        inspetor_id=result.inspetor_id,
        laudo_id=result.laudo_id,
        tipo="mensagem_eng",
        texto=result.texto_notificacao,
        mensagem_id=result.mensagem_id,
        referencia_mensagem_id=result.referencia_mensagem_id,
        de_usuario_id=getattr(command.usuario, "id", None),
        de_nome=reviewer_name,
        mensagem=result.mensagem_payload,
    )
    _registrar_auditoria_revisor_segura(
        banco=command.banco,
        usuario=command.usuario,
        acao="mesa_resposta_com_anexo",
        resumo=f"Mesa enviou resposta com anexo no laudo #{result.laudo_id}.",
        detalhe=f"Arquivo enviado: {str(command.nome_arquivo or 'anexo_mesa').strip()[:120]}.",
        alvo_usuario_id=result.inspetor_id,
        payload={
            "laudo_id": result.laudo_id,
            "mensagem_id": result.mensagem_id,
            "referencia_mensagem_id": result.referencia_mensagem_id,
            "nome_arquivo": str(command.nome_arquivo or "").strip(),
            "mime_type": str(command.mime_type or "").strip(),
        },
    )


async def run_review_whisper_reply_side_effects(
    *,
    command: ReviewWhisperReplyCommand,
    result: WhisperRespostaResult,
) -> None:
    reviewer_name = _reviewer_name(command.usuario)
    await notificar_whisper_resposta_revisor(
        empresa_id=int(getattr(command.usuario, "empresa_id")),
        destinatario_id=result.destinatario_id,
        laudo_id=result.laudo_id,
        de_usuario_id=int(getattr(command.usuario, "id")),
        de_nome=reviewer_name,
        mensagem_id=result.mensagem_id,
        referencia_mensagem_id=result.referencia_mensagem_id,
        preview=result.preview,
    )
    await notificar_inspetor_sse(
        inspetor_id=result.destinatario_id,
        laudo_id=result.laudo_id,
        tipo="whisper_eng",
        texto=str(command.mensagem or "").strip(),
        mensagem_id=result.mensagem_id,
        referencia_mensagem_id=result.referencia_mensagem_id,
        de_usuario_id=getattr(command.usuario, "id", None),
        de_nome=reviewer_name,
    )
    logger.info(
        "Whisper enviado | laudo=%s | revisor=%s | destinatario_id=%s",
        command.laudo_id,
        reviewer_name,
        result.destinatario_id,
    )
    _registrar_auditoria_revisor_segura(
        banco=command.banco,
        usuario=command.usuario,
        acao="mesa_whisper_enviado",
        resumo=f"Mesa enviou whisper no laudo #{result.laudo_id}.",
        detalhe="Mensagem privada enviada ao inspetor.",
        alvo_usuario_id=result.destinatario_id,
        payload={
            "laudo_id": result.laudo_id,
            "destinatario_id": result.destinatario_id,
            "mensagem_id": result.mensagem_id,
            "referencia_mensagem_id": result.referencia_mensagem_id,
            "preview": result.preview,
        },
    )


async def run_review_pendency_status_side_effects(
    *,
    command: ReviewPendencyStatusCommand,
    result: PendenciaMesaResult,
) -> None:
    reviewer_name = _reviewer_name(command.usuario)
    await notificar_inspetor_sse(
        inspetor_id=result.inspetor_id,
        laudo_id=result.laudo_id,
        tipo="pendencia_mesa",
        texto=result.texto_notificacao,
        mensagem_id=result.mensagem_id,
        de_usuario_id=getattr(command.usuario, "id", None),
        de_nome=reviewer_name,
    )
    _registrar_auditoria_revisor_segura(
        banco=command.banco,
        usuario=command.usuario,
        acao="mesa_pendencia_atualizada",
        resumo=(
            f"Mesa resolveu a pendência #{result.mensagem_id} do laudo #{result.laudo_id}."
            if result.lida
            else f"Mesa reabriu a pendência #{result.mensagem_id} do laudo #{result.laudo_id}."
        ),
        detalhe=f"Pendências abertas após a operação: {result.pendencias_abertas}.",
        alvo_usuario_id=result.inspetor_id,
        payload={
            "laudo_id": result.laudo_id,
            "mensagem_id": result.mensagem_id,
            "lida": result.lida,
            "resolvida_por_id": result.resolvida_por_id,
            "pendencias_abertas": result.pendencias_abertas,
        },
    )


async def run_review_coverage_return_side_effects(
    *,
    command: ReviewCoverageReturnCommand,
    result: CoverageReturnRequestResult,
) -> None:
    reviewer_name = _reviewer_name(command.usuario)
    await notificar_inspetor_sse(
        inspetor_id=result.inspetor_id,
        laudo_id=result.laudo_id,
        tipo="pendencia_mesa",
        texto=result.texto_notificacao,
        mensagem_id=result.mensagem_id,
        de_usuario_id=getattr(command.usuario, "id", None),
        de_nome=reviewer_name,
        mensagem=result.mensagem_payload,
    )
    _registrar_auditoria_revisor_segura(
        banco=command.banco,
        usuario=command.usuario,
        acao="mesa_refazer_coverage_solicitado",
        resumo=f"Mesa devolveu o item {result.evidence_key} do laudo #{result.laudo_id} para o inspetor.",
        detalhe=f"Bloco operacional: {result.block_key}.",
        alvo_usuario_id=result.inspetor_id,
        payload={
            "laudo_id": result.laudo_id,
            "mensagem_id": result.mensagem_id,
            "evidence_key": result.evidence_key,
            "block_key": result.block_key,
            "title": command.title,
            "kind": command.kind,
            "required": command.required,
        },
    )


__all__ = [
    "run_review_coverage_return_side_effects",
    "run_review_decision_side_effects",
    "run_review_pendency_status_side_effects",
    "run_review_reply_attachment_side_effects",
    "run_review_reply_side_effects",
    "run_review_whisper_reply_side_effects",
]
