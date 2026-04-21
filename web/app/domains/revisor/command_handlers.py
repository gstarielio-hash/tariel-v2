from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.domains.revisor.document_boundary import (
    build_legacy_case_status_payload_for_review,
    evaluate_reviewdesk_document_gate_for_decision,
    review_reject_shadow_scope_enabled as _review_reject_shadow_scope_enabled,
)
from app.domains.revisor.service_contracts import (
    AvaliacaoLaudoResult,
    CoverageReturnRequestResult,
    PendenciaMesaResult,
    RespostaChatAnexoResult,
    RespostaChatResult,
    WhisperRespostaResult,
)
from app.domains.revisor.service_messaging import (
    atualizar_pendencia_mesa_revisor_status,
    avaliar_laudo_revisor,
    solicitar_refazer_item_coverage_revisor,
    registrar_resposta_chat_com_anexo_revisor,
    registrar_resposta_chat_revisor,
    registrar_whisper_resposta_revisor,
)
from app.shared.database import Usuario
from app.v2.document import (
    DocumentHardGateEnforcementResultV1,
    build_document_hard_gate_block_detail,
)
from app.v2.runtime import v2_document_hard_gate_enabled, v2_document_soft_gate_enabled


@dataclass(slots=True)
class ReviewDecisionCommand:
    request: Request
    banco: Session
    usuario: Usuario
    laudo_id: int
    acao: Literal["aprovar", "rejeitar"]
    motivo: str
    resposta_api: bool
    modo_schemathesis: bool


@dataclass(slots=True)
class ReviewReplyCommand:
    banco: Session
    usuario: Usuario
    laudo_id: int
    texto: str
    referencia_mensagem_id: int | None


@dataclass(slots=True)
class ReviewReplyAttachmentCommand:
    banco: Session
    usuario: Usuario
    laudo_id: int
    nome_arquivo: str
    mime_type: str
    conteudo_arquivo: bytes
    texto: str
    referencia_mensagem_id: int | None


@dataclass(slots=True)
class ReviewWhisperReplyCommand:
    banco: Session
    usuario: Usuario
    laudo_id: int
    mensagem: str
    destinatario_id: int
    referencia_mensagem_id: int | None


@dataclass(slots=True)
class ReviewPendencyStatusCommand:
    banco: Session
    usuario: Usuario
    laudo_id: int
    mensagem_id: int
    lida: bool


@dataclass(slots=True)
class ReviewCoverageReturnCommand:
    banco: Session
    usuario: Usuario
    laudo_id: int
    evidence_key: str
    title: str
    kind: str
    required: bool
    source_status: str | None
    operational_status: str | None
    mesa_status: str | None
    component_type: str | None
    view_angle: str | None
    severity: str
    summary: str | None
    required_action: str | None
    failure_reasons: list[str]


def _reviewer_name(usuario: Usuario) -> str:
    nome = getattr(usuario, "nome", None) or getattr(usuario, "nome_completo", None)
    return str(nome or f"Revisor #{getattr(usuario, 'id', '-')}")


def _avaliar_gate_documental_decisao_revisor(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
    laudo_id: int,
    operation_kind: Literal["review_approve", "review_reject"],
    route_name: str,
    legacy_pipeline_name: str,
) -> tuple[object | None, object | None]:
    soft_gate_enabled = v2_document_soft_gate_enabled()
    hard_gate_enabled = v2_document_hard_gate_enabled()
    if not soft_gate_enabled and not hard_gate_enabled:
        return None, None

    return evaluate_reviewdesk_document_gate_for_decision(
        request=request,
        usuario=usuario,
        banco=banco,
        laudo_id=laudo_id,
        operation_kind=operation_kind,
        route_name=route_name,
        legacy_pipeline_name=legacy_pipeline_name,
    )


def handle_review_decision_command(command: ReviewDecisionCommand) -> AvaliacaoLaudoResult:
    hard_gate_result: DocumentHardGateEnforcementResultV1 | None = None
    if command.acao == "aprovar":
        try:
            _, hard_gate_raw = _avaliar_gate_documental_decisao_revisor(
                request=command.request,
                usuario=command.usuario,
                banco=command.banco,
                laudo_id=command.laudo_id,
                operation_kind="review_approve",
                route_name="avaliar_laudo_review_approve",
                legacy_pipeline_name="legacy_review_approve",
            )
            hard_gate_result = cast(DocumentHardGateEnforcementResultV1 | None, hard_gate_raw)
        except Exception:
            from app.domains.revisor.base import logger

            logger.debug(
                "Falha ao avaliar hard gate documental da aprovacao da mesa.",
                exc_info=True,
            )
            command.request.state.v2_document_hard_gate_error = "review_approve_hard_gate_failed"
    elif command.acao == "rejeitar" and _review_reject_shadow_scope_enabled(
        request=command.request,
        usuario=command.usuario,
        ):
        try:
            _, hard_gate_raw = _avaliar_gate_documental_decisao_revisor(
                request=command.request,
                usuario=command.usuario,
                banco=command.banco,
                laudo_id=command.laudo_id,
                operation_kind="review_reject",
                route_name="avaliar_laudo_review_reject",
                legacy_pipeline_name="legacy_review_reject",
            )
            hard_gate_result = cast(DocumentHardGateEnforcementResultV1 | None, hard_gate_raw)
        except Exception:
            from app.domains.revisor.base import logger

            logger.debug(
                "Falha ao avaliar hard gate documental da rejeicao da mesa.",
                exc_info=True,
            )
            command.request.state.v2_document_hard_gate_error = "review_reject_hard_gate_failed"

    if hard_gate_result is not None and hard_gate_result.decision.did_block:
        raise HTTPException(
            status_code=int(hard_gate_result.blocked_response_status or 422),
            detail=build_document_hard_gate_block_detail(hard_gate_result),
        )

    return avaliar_laudo_revisor(
        command.banco,
        laudo_id=command.laudo_id,
        empresa_id=command.usuario.empresa_id,
        revisor_id=command.usuario.id,
        revisor_nome=_reviewer_name(command.usuario),
        acao=command.acao,
        motivo=command.motivo,
        resposta_api=command.resposta_api,
        modo_schemathesis=bool(command.modo_schemathesis),
    )


def handle_review_reply_command(command: ReviewReplyCommand) -> RespostaChatResult:
    return registrar_resposta_chat_revisor(
        command.banco,
        laudo_id=command.laudo_id,
        empresa_id=command.usuario.empresa_id,
        revisor_id=command.usuario.id,
        texto=command.texto,
        referencia_mensagem_id=command.referencia_mensagem_id,
        revisor_nome=_reviewer_name(command.usuario),
    )


def handle_review_reply_attachment_command(
    command: ReviewReplyAttachmentCommand,
) -> RespostaChatAnexoResult:
    return registrar_resposta_chat_com_anexo_revisor(
        command.banco,
        laudo_id=command.laudo_id,
        empresa_id=command.usuario.empresa_id,
        revisor_id=command.usuario.id,
        nome_arquivo=command.nome_arquivo,
        mime_type=command.mime_type,
        conteudo_arquivo=command.conteudo_arquivo,
        texto=command.texto,
        referencia_mensagem_id=command.referencia_mensagem_id,
    )


def handle_review_whisper_reply_command(
    command: ReviewWhisperReplyCommand,
) -> WhisperRespostaResult:
    return registrar_whisper_resposta_revisor(
        command.banco,
        laudo_id=command.laudo_id,
        empresa_id=command.usuario.empresa_id,
        revisor_id=command.usuario.id,
        mensagem=command.mensagem,
        destinatario_id=command.destinatario_id,
        referencia_mensagem_id=command.referencia_mensagem_id,
    )


def handle_review_pendency_status_command(
    command: ReviewPendencyStatusCommand,
) -> PendenciaMesaResult:
    return atualizar_pendencia_mesa_revisor_status(
        command.banco,
        laudo_id=command.laudo_id,
        empresa_id=command.usuario.empresa_id,
        mensagem_id=command.mensagem_id,
        lida=bool(command.lida),
        revisor_id=command.usuario.id,
    )


def handle_review_coverage_return_command(
    command: ReviewCoverageReturnCommand,
) -> CoverageReturnRequestResult:
    return solicitar_refazer_item_coverage_revisor(
        command.banco,
        laudo_id=command.laudo_id,
        empresa_id=command.usuario.empresa_id,
        revisor_id=command.usuario.id,
        revisor_nome=_reviewer_name(command.usuario),
        evidence_key=command.evidence_key,
        title=command.title,
        kind=command.kind,
        required=bool(command.required),
        source_status=command.source_status,
        operational_status=command.operational_status,
        mesa_status=command.mesa_status,
        component_type=command.component_type,
        view_angle=command.view_angle,
        severity=command.severity,
        summary=command.summary,
        required_action=command.required_action,
        failure_reasons=command.failure_reasons,
    )


__all__ = [
    "ReviewCoverageReturnCommand",
    "ReviewDecisionCommand",
    "ReviewPendencyStatusCommand",
    "ReviewReplyAttachmentCommand",
    "ReviewReplyCommand",
    "ReviewWhisperReplyCommand",
    "build_legacy_case_status_payload_for_review",
    "handle_review_coverage_return_command",
    "handle_review_decision_command",
    "handle_review_pendency_status_command",
    "handle_review_reply_attachment_command",
    "handle_review_reply_command",
    "handle_review_whisper_reply_command",
]
