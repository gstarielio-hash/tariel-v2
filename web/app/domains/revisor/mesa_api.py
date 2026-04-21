from __future__ import annotations

import os
from typing import Annotated, Literal

from fastapi import Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.domains.chat.media_helpers import safe_remove_file
from app.domains.chat.request_parsing_helpers import InteiroOpcionalNullish
from app.domains.revisor.base import (
    DadosEmissaoOficialMesa,
    DadosPendenciaMesa,
    DadosSolicitacaoCoverageReturn,
    DadosRespostaChat,
    DadosWhisper,
    RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
    logger,
    roteador_revisor,
)
from app.domains.revisor.command_handlers import (
    ReviewCoverageReturnCommand,
    ReviewDecisionCommand,
    ReviewPendencyStatusCommand,
    ReviewReplyAttachmentCommand,
    ReviewReplyCommand,
    ReviewWhisperReplyCommand,
    handle_review_coverage_return_command,
    handle_review_decision_command,
    handle_review_pendency_status_command,
    handle_review_reply_attachment_command,
    handle_review_reply_command,
    handle_review_whisper_reply_command,
)
from app.domains.revisor.command_side_effects import (
    run_review_coverage_return_side_effects,
    run_review_decision_side_effects,
    run_review_pendency_status_side_effects,
    run_review_reply_attachment_side_effects,
    run_review_reply_side_effects,
    run_review_whisper_reply_side_effects,
)
from app.domains.revisor.common import _validar_csrf
from app.domains.revisor.document_boundary import (
    build_reviewdesk_complete_payload,
    build_reviewdesk_case_package_payload,
)
from app.domains.revisor.service import (
    carregar_anexo_mesa_revisor,
    carregar_historico_chat_revisor,
    carregar_pacote_mesa_laudo_revisor,
    gerar_exportacao_pacote_mesa_laudo_pdf,
    gerar_exportacao_pacote_mesa_laudo_zip,
    marcar_whispers_lidos_revisor,
    validar_parametros_pacote_mesa,
)
from app.shared.database import Usuario, obter_banco
from app.shared.backend_hotspot_metrics import observe_backend_hotspot
from app.shared.official_issue_package import OfficialIssueConflictError, load_active_official_issue_record
from app.shared.official_issue_transaction import emitir_oficialmente_transacional
from app.shared.security import exigir_revisor
from app.shared.tenant_entitlement_guard import ensure_tenant_capability_for_user


def _ensure_reviewer_decision_capability(usuario: Usuario) -> None:
    ensure_tenant_capability_for_user(
        usuario,
        capability="reviewer_decision",
    )


def _ensure_reviewer_issue_capability(usuario: Usuario) -> None:
    ensure_tenant_capability_for_user(
        usuario,
        capability="reviewer_issue",
    )


@roteador_revisor.post(
    "/api/laudo/{laudo_id}/avaliar",
    responses={
        **RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
        400: {"description": "Requisição inválida para avaliação."},
        403: {"description": "CSRF inválido."},
        422: {"description": "Hard gate documental controlado bloqueou a operação."},
    },
)
async def avaliar_laudo(
    laudo_id: int,
    request: Request,
    acao: Literal["aprovar", "rejeitar"] = Form(...),
    motivo: str = Form(default=""),
    csrf_token: str = Form(default=""),
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    resposta_api = bool(request.headers.get("X-CSRF-Token"))
    modo_schemathesis = resposta_api and os.getenv("SCHEMATHESIS_TEST_HINTS", "0").strip() == "1"
    token_csrf = str(csrf_token or "").strip() or request.headers.get("X-CSRF-Token", "")
    if not _validar_csrf(request, token_csrf):
        raise HTTPException(status_code=403, detail="Token CSRF inválido.")

    comando = ReviewDecisionCommand(
        request=request,
        banco=banco,
        usuario=usuario,
        laudo_id=laudo_id,
        acao=acao,
        motivo=motivo,
        resposta_api=resposta_api,
        modo_schemathesis=bool(modo_schemathesis),
    )
    resultado = handle_review_decision_command(comando)

    await run_review_decision_side_effects(
        command=comando,
        result=resultado,
    )

    if resposta_api:
        return JSONResponse(
            {
                "success": True,
                "laudo_id": resultado.laudo_id,
                "acao": resultado.acao,
                "status_revisao": resultado.status_revisao,
                "case_status": resultado.case_status,
                "case_lifecycle_status": resultado.case_lifecycle_status,
                "case_workflow_mode": resultado.case_workflow_mode,
                "active_owner_role": resultado.active_owner_role,
                "allowed_next_lifecycle_statuses": list(resultado.allowed_next_lifecycle_statuses),
                "allowed_surface_actions": list(resultado.allowed_surface_actions),
                "status_visual_label": resultado.status_visual_label,
                "motivo": resultado.motivo,
                "idempotent_replay": bool(resultado.idempotent_replay),
            }
        )

    return RedirectResponse(url="/revisao/painel", status_code=status.HTTP_303_SEE_OTHER)


@roteador_revisor.post(
    "/api/whisper/responder",
    responses={
        **RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
        400: {"description": "Destinatário inválido para o laudo."},
        403: {"description": "CSRF inválido."},
    },
)
async def whisper_responder(
    dados: DadosWhisper,
    request: Request,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    if not _validar_csrf(request):
        raise HTTPException(status_code=403, detail="CSRF inválido.")

    comando = ReviewWhisperReplyCommand(
        banco=banco,
        usuario=usuario,
        laudo_id=dados.laudo_id,
        mensagem=dados.mensagem,
        destinatario_id=dados.destinatario_id,
        referencia_mensagem_id=int(dados.referencia_mensagem_id or 0) or None,
    )
    resultado = handle_review_whisper_reply_command(comando)

    await run_review_whisper_reply_side_effects(
        command=comando,
        result=resultado,
    )
    return JSONResponse({"success": True, "destinatario_id": resultado.destinatario_id})


@roteador_revisor.post(
    "/api/laudo/{laudo_id}/responder",
    responses={**RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR, 400: {"description": "Mensagem inválida."}},
)
async def responder_chat_campo(
    laudo_id: int,
    dados: DadosRespostaChat,
    request: Request,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    token = request.headers.get("X-CSRF-Token", "")
    if not _validar_csrf(request, token):
        raise HTTPException(status_code=403, detail="CSRF inválido.")

    comando = ReviewReplyCommand(
        banco=banco,
        usuario=usuario,
        laudo_id=laudo_id,
        texto=dados.texto,
        referencia_mensagem_id=int(dados.referencia_mensagem_id or 0) or None,
    )
    resultado = handle_review_reply_command(comando)

    await run_review_reply_side_effects(
        command=comando,
        result=resultado,
    )

    return JSONResponse({"success": True})


@roteador_revisor.post(
    "/api/laudo/{laudo_id}/responder-anexo",
    responses={
        **RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
        400: {"description": "Upload inválido."},
        413: {"description": "Arquivo acima do limite."},
        415: {"description": "Tipo de arquivo não suportado."},
    },
)
async def responder_chat_campo_com_anexo(
    laudo_id: int,
    request: Request,
    arquivo: UploadFile = File(...),
    texto: str = Form(default=""),
    referencia_mensagem_id: Annotated[InteiroOpcionalNullish, Form()] = None,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    token = request.headers.get("X-CSRF-Token", "")
    if not _validar_csrf(request, token):
        raise HTTPException(status_code=403, detail="CSRF inválido.")

    conteudo_arquivo = await arquivo.read()
    comando = ReviewReplyAttachmentCommand(
        banco=banco,
        usuario=usuario,
        laudo_id=laudo_id,
        nome_arquivo=str(arquivo.filename or "anexo_mesa"),
        mime_type=str(arquivo.content_type or ""),
        conteudo_arquivo=conteudo_arquivo,
        texto=texto,
        referencia_mensagem_id=int(referencia_mensagem_id or 0) or None,
    )
    resultado = handle_review_reply_attachment_command(comando)

    await run_review_reply_attachment_side_effects(
        command=comando,
        result=resultado,
    )

    return JSONResponse(
        {
            "success": True,
            "mensagem": resultado.mensagem_payload,
        }
    )


@roteador_revisor.get(
    "/api/laudo/{laudo_id}/mesa/anexos/{anexo_id}",
    responses={
        200: {
            "description": "Arquivo do anexo da mesa.",
            "content": {
                "application/pdf": {},
                "image/png": {},
                "image/jpeg": {},
                "image/webp": {},
                "application/octet-stream": {},
            },
        },
        404: {"description": "Anexo da mesa não encontrado."},
    },
)
async def baixar_anexo_mesa_revisor(
    laudo_id: int,
    anexo_id: int,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    anexo = carregar_anexo_mesa_revisor(
        banco,
        laudo_id=laudo_id,
        empresa_id=usuario.empresa_id,
        anexo_id=anexo_id,
    )

    return FileResponse(
        path=str(anexo.caminho_arquivo),
        filename=str(anexo.nome_original or anexo.nome_arquivo or f"anexo_mesa_{anexo.id}"),
        media_type=str(anexo.mime_type or "application/octet-stream"),
    )


@roteador_revisor.post(
    "/api/laudo/{laudo_id}/marcar-whispers-lidos",
    responses=RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
)
async def marcar_whispers_lidos(
    laudo_id: int,
    request: Request,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    token = request.headers.get("X-CSRF-Token", "")
    if not _validar_csrf(request, token):
        raise HTTPException(status_code=403, detail="CSRF inválido.")

    total = marcar_whispers_lidos_revisor(
        banco,
        laudo_id=laudo_id,
        empresa_id=usuario.empresa_id,
    )

    return JSONResponse({"success": True, "marcadas": total})


@roteador_revisor.patch(
    "/api/laudo/{laudo_id}/pendencias/{mensagem_id}",
    responses={
        **RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
        404: {"description": "Pendência da mesa não encontrada."},
    },
)
async def atualizar_pendencia_mesa_revisor(
    laudo_id: int,
    mensagem_id: int,
    dados: DadosPendenciaMesa,
    request: Request,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    token = request.headers.get("X-CSRF-Token", "")
    if not _validar_csrf(request, token):
        raise HTTPException(status_code=403, detail="CSRF inválido.")

    comando = ReviewPendencyStatusCommand(
        banco=banco,
        usuario=usuario,
        laudo_id=laudo_id,
        mensagem_id=mensagem_id,
        lida=bool(dados.lida),
    )
    resultado = handle_review_pendency_status_command(comando)

    await run_review_pendency_status_side_effects(
        command=comando,
        result=resultado,
    )

    return JSONResponse(
        {
            "success": True,
            "mensagem_id": resultado.mensagem_id,
            "lida": resultado.lida,
            "resolvida_por_id": resultado.resolvida_por_id,
            "resolvida_por_nome": resultado.resolvida_por_nome,
            "resolvida_em": resultado.resolvida_em,
            "pendencias_abertas": resultado.pendencias_abertas,
        }
    )


@roteador_revisor.post(
    "/api/laudo/{laudo_id}/coverage/solicitar-refazer",
    responses={
        **RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
        400: {"description": "Item de coverage inválido."},
        403: {"description": "CSRF inválido."},
    },
)
async def solicitar_refazer_item_coverage(
    laudo_id: int,
    dados: DadosSolicitacaoCoverageReturn,
    request: Request,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    token = request.headers.get("X-CSRF-Token", "")
    if not _validar_csrf(request, token):
        raise HTTPException(status_code=403, detail="CSRF inválido.")

    comando = ReviewCoverageReturnCommand(
        banco=banco,
        usuario=usuario,
        laudo_id=laudo_id,
        evidence_key=dados.evidence_key,
        title=dados.title,
        kind=dados.kind,
        required=bool(dados.required),
        source_status=dados.source_status,
        operational_status=dados.operational_status,
        mesa_status=dados.mesa_status,
        component_type=dados.component_type,
        view_angle=dados.view_angle,
        severity=dados.severity,
        summary=dados.summary,
        required_action=dados.required_action,
        failure_reasons=list(dados.failure_reasons or []),
    )
    resultado = handle_review_coverage_return_command(comando)

    await run_review_coverage_return_side_effects(
        command=comando,
        result=resultado,
    )

    return JSONResponse(
        {
            "success": True,
            "mensagem": resultado.mensagem_payload,
            "evidence_key": resultado.evidence_key,
            "block_key": resultado.block_key,
        }
    )


@roteador_revisor.get(
    "/api/laudo/{laudo_id}/mensagens",
    responses=RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
)
async def obter_historico_chat_revisor(
    laudo_id: int,
    cursor: Annotated[InteiroOpcionalNullish, Query()] = None,
    limite: int = Query(default=60, ge=20, le=200),
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    return carregar_historico_chat_revisor(
        banco,
        laudo_id=laudo_id,
        empresa_id=usuario.empresa_id,
        cursor=cursor,
        limite=limite,
    )


@roteador_revisor.get(
    "/api/laudo/{laudo_id}/completo",
    responses=RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
)
async def obter_laudo_completo(
    laudo_id: int,
    request: Request,
    incluir_historico: bool = Query(default=False),
    cursor: Annotated[InteiroOpcionalNullish, Query()] = None,
    limite: int = Query(default=60, ge=20, le=200),
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    payload = build_reviewdesk_complete_payload(
        request=request,
        usuario=usuario,
        banco=banco,
        laudo_id=laudo_id,
        incluir_historico=incluir_historico,
        cursor=cursor,
        limite=limite,
    )
    return JSONResponse(content=jsonable_encoder(payload))


@roteador_revisor.get(
    "/api/laudo/{laudo_id}/pacote",
    responses=RESPOSTA_LAUDO_NAO_ENCONTRADO_REVISOR,
)
async def obter_pacote_mesa_laudo(
    laudo_id: int,
    request: Request,
    limite_whispers: int = Query(default=80, ge=20, le=300),
    limite_pendencias: int = Query(default=80, ge=20, le=300),
    limite_revisoes: int = Query(default=10, ge=1, le=50),
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    with observe_backend_hotspot(
        "mesa_case_package_read",
        request=request,
        surface="mesa",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        laudo_id=laudo_id,
        case_id=laudo_id,
        route_path=f"/revisao/api/laudo/{laudo_id}/pacote",
        method="GET",
    ) as hotspot:
        validar_parametros_pacote_mesa(request.query_params.keys())
        payload_publico = build_reviewdesk_case_package_payload(
            request=request,
            usuario=usuario,
            banco=banco,
            laudo_id=laudo_id,
            limite_whispers=limite_whispers,
            limite_pendencias=limite_pendencias,
            limite_revisoes=limite_revisoes,
        )
        hotspot.outcome = "package_payload"
        hotspot.response_status_code = 200
        return JSONResponse(content=jsonable_encoder(payload_publico))


@roteador_revisor.get(
    "/api/laudo/{laudo_id}/pacote/exportar-pdf",
    responses={
        200: {"description": "PDF do pacote da mesa.", "content": {"application/pdf": {}}},
        404: {"description": "Laudo não encontrado."},
        500: {"description": "Falha ao exportar o PDF do pacote."},
    },
)
async def exportar_pacote_mesa_laudo_pdf(
    laudo_id: int,
    request: Request,
    limite_whispers: int = Query(default=80, ge=20, le=300),
    limite_pendencias: int = Query(default=80, ge=20, le=300),
    limite_revisoes: int = Query(default=10, ge=1, le=50),
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    with observe_backend_hotspot(
        "mesa_export_package_pdf",
        request=request,
        surface="mesa",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        laudo_id=laudo_id,
        case_id=laudo_id,
        route_path=f"/revisao/api/laudo/{laudo_id}/pacote/exportar-pdf",
        method="GET",
    ) as hotspot:
        _ensure_reviewer_decision_capability(usuario)
        validar_parametros_pacote_mesa(request.query_params.keys())
        pacote_carregado = carregar_pacote_mesa_laudo_revisor(
            banco,
            laudo_id=laudo_id,
            empresa_id=usuario.empresa_id,
            limite_whispers=limite_whispers,
            limite_pendencias=limite_pendencias,
            limite_revisoes=limite_revisoes,
        )

        try:
            exportacao = gerar_exportacao_pacote_mesa_laudo_pdf(
                banco,
                pacote_carregado=pacote_carregado,
                usuario=usuario,
            )
            hotspot.outcome = "file_response"
            hotspot.response_status_code = 200
            return FileResponse(
                path=exportacao.caminho_pdf,
                filename=exportacao.filename,
                media_type="application/pdf",
                background=BackgroundTask(safe_remove_file, exportacao.caminho_pdf),
            )
        except Exception:
            logger.exception(
                "Falha ao exportar pacote da mesa em PDF | laudo_id=%s empresa_id=%s",
                laudo_id,
                usuario.empresa_id,
            )
            hotspot.status = "error"
            hotspot.error_class = "infra"
            hotspot.error_code = "mesa_export_pdf_failed"
            hotspot.outcome = "internal_error_json"
            hotspot.response_status_code = 500
            return JSONResponse(
                status_code=500,
                content={"erro": "Falha ao exportar o PDF do pacote da mesa."},
            )


@roteador_revisor.get(
    "/api/laudo/{laudo_id}/pacote/exportar-oficial",
    responses={
        200: {"description": "ZIP da emissão oficial governada.", "content": {"application/zip": {}}},
        404: {"description": "Laudo não encontrado."},
        500: {"description": "Falha ao exportar o ZIP oficial."},
    },
)
async def exportar_pacote_mesa_laudo_zip(
    laudo_id: int,
    request: Request,
    limite_whispers: int = Query(default=80, ge=20, le=300),
    limite_pendencias: int = Query(default=80, ge=20, le=300),
    limite_revisoes: int = Query(default=10, ge=1, le=50),
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    with observe_backend_hotspot(
        "mesa_export_package_zip",
        request=request,
        surface="mesa",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        laudo_id=laudo_id,
        case_id=laudo_id,
        route_path=f"/revisao/api/laudo/{laudo_id}/pacote/exportar-oficial",
        method="GET",
    ) as hotspot:
        _ensure_reviewer_issue_capability(usuario)
        validar_parametros_pacote_mesa(request.query_params.keys())
        pacote_carregado = carregar_pacote_mesa_laudo_revisor(
            banco,
            laudo_id=laudo_id,
            empresa_id=usuario.empresa_id,
            limite_whispers=limite_whispers,
            limite_pendencias=limite_pendencias,
            limite_revisoes=limite_revisoes,
        )

        try:
            exportacao = gerar_exportacao_pacote_mesa_laudo_zip(
                banco,
                pacote_carregado=pacote_carregado,
                usuario=usuario,
            )
            hotspot.outcome = "file_response"
            hotspot.response_status_code = 200
            return FileResponse(
                path=exportacao.caminho_zip,
                filename=exportacao.filename,
                media_type="application/zip",
                background=BackgroundTask(safe_remove_file, exportacao.caminho_zip),
            )
        except Exception:
            logger.exception(
                "Falha ao exportar pacote oficial da mesa em ZIP | laudo_id=%s empresa_id=%s",
                laudo_id,
                usuario.empresa_id,
            )
            hotspot.status = "error"
            hotspot.error_class = "infra"
            hotspot.error_code = "mesa_export_zip_failed"
            hotspot.outcome = "internal_error_json"
            hotspot.response_status_code = 500
            return JSONResponse(
                status_code=500,
                content={"erro": "Falha ao exportar o ZIP oficial da emissão."},
            )


@roteador_revisor.post(
    "/api/laudo/{laudo_id}/emissao-oficial",
    responses={
        200: {"description": "Emissão oficial transacional registrada."},
        403: {"description": "CSRF inválido."},
        409: {"description": "A emissão oficial ativa mudou durante a tentativa de reemissão."},
        404: {"description": "Laudo não encontrado."},
        422: {"description": "Bloqueio de governança para emissão oficial."},
    },
)
async def emitir_oficialmente_laudo(
    laudo_id: int,
    dados: DadosEmissaoOficialMesa,
    request: Request,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    with observe_backend_hotspot(
        "mesa_official_issue",
        request=request,
        surface="mesa",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        laudo_id=laudo_id,
        case_id=laudo_id,
        route_path=f"/revisao/api/laudo/{laudo_id}/emissao-oficial",
        method="POST",
    ) as hotspot:
        token = request.headers.get("X-CSRF-Token", "")
        if not _validar_csrf(request, token):
            raise HTTPException(status_code=403, detail="CSRF inválido.")
        _ensure_reviewer_issue_capability(usuario)

        pacote_carregado = carregar_pacote_mesa_laudo_revisor(
            banco,
            laudo_id=laudo_id,
            empresa_id=usuario.empresa_id,
            limite_whispers=80,
            limite_pendencias=80,
            limite_revisoes=10,
        )
        try:
            resultado = emitir_oficialmente_transacional(
                banco,
                laudo=pacote_carregado.laudo,
                actor_user=usuario,
                signatory_id=int(dados.signatory_id or 0) or None,
                expected_active_issue_id=int(dados.expected_current_issue_id or 0) or None,
                expected_active_issue_number=str(dados.expected_current_issue_number or "").strip() or None,
            )
        except OfficialIssueConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        record_payload = resultado.get("record_payload") if isinstance(resultado, dict) else None
        hotspot.outcome = "issue_recorded"
        hotspot.response_status_code = 200
        return JSONResponse(
            jsonable_encoder(
                {
                    "success": True,
                    "laudo_id": int(pacote_carregado.laudo.id),
                    "issue_number": (record_payload or {}).get("issue_number"),
                    "issue_state": (record_payload or {}).get("issue_state"),
                    "package_sha256": (record_payload or {}).get("package_sha256"),
                    "idempotent_replay": bool((resultado or {}).get("idempotent_replay")),
                    "reissued": bool((record_payload or {}).get("reissue_of_issue_id")),
                    "superseded_issue_number": (record_payload or {}).get("reissue_of_issue_number"),
                    "reissue_reason_codes": list((record_payload or {}).get("reissue_reason_codes") or []),
                    "reissue_reason_summary": (record_payload or {}).get("reissue_reason_summary"),
                    "download_url": f"/revisao/api/laudo/{laudo_id}/emissao-oficial/download",
                    "record": record_payload,
                }
            )
        )


@roteador_revisor.get(
    "/api/laudo/{laudo_id}/emissao-oficial/download",
    responses={
        200: {"description": "Bundle congelado da emissão oficial.", "content": {"application/zip": {}}},
        404: {"description": "Emissão oficial não encontrada."},
    },
)
async def baixar_emissao_oficial_congelada(
    laudo_id: int,
    request: Request,
    usuario: Usuario = Depends(exigir_revisor),
    banco: Session = Depends(obter_banco),
):
    with observe_backend_hotspot(
        "mesa_official_issue_download",
        request=request,
        surface="mesa",
        tenant_id=getattr(usuario, "empresa_id", None),
        user_id=getattr(usuario, "id", None),
        laudo_id=laudo_id,
        case_id=laudo_id,
        route_path=f"/revisao/api/laudo/{laudo_id}/emissao-oficial/download",
        method="GET",
    ) as hotspot:
        _ensure_reviewer_issue_capability(usuario)
        pacote_carregado = carregar_pacote_mesa_laudo_revisor(
            banco,
            laudo_id=laudo_id,
            empresa_id=usuario.empresa_id,
            limite_whispers=20,
            limite_pendencias=20,
            limite_revisoes=5,
        )
        record = load_active_official_issue_record(banco, laudo=pacote_carregado.laudo)
        path = str(getattr(record, "package_storage_path", "") or "").strip() if record is not None else ""
        if not path or not os.path.isfile(path):
            raise HTTPException(status_code=404, detail="Emissão oficial congelada não encontrada.")
        filename = str(getattr(record, "package_filename", "") or getattr(record, "issue_number", "") or "emissao_oficial.zip")
        hotspot.outcome = "file_response"
        hotspot.response_status_code = 200
        return FileResponse(
            path=path,
            filename=filename,
            media_type="application/zip",
        )


__all__ = [
    "atualizar_pendencia_mesa_revisor",
    "avaliar_laudo",
    "baixar_anexo_mesa_revisor",
    "exportar_pacote_mesa_laudo_zip",
    "exportar_pacote_mesa_laudo_pdf",
    "baixar_emissao_oficial_congelada",
    "emitir_oficialmente_laudo",
    "marcar_whispers_lidos",
    "obter_historico_chat_revisor",
    "obter_laudo_completo",
    "obter_pacote_mesa_laudo",
    "responder_chat_campo",
    "responder_chat_campo_com_anexo",
    "whisper_responder",
]
