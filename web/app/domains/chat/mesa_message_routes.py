"""Rotas de envio e anexo do canal mesa."""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.domains.chat.auth_helpers import usuario_nome
from app.domains.chat.app_context import logger
from app.domains.chat.core_helpers import agora_utc, obter_preview_primeira_mensagem, resposta_json_ok
from app.domains.chat.laudo_access_helpers import obter_laudo_do_inspetor
from app.domains.chat.laudo_state_helpers import (
    laudo_permite_edicao_inspetor,
    laudo_tem_interacao,
    obter_detalhe_bloqueio_edicao_inspetor,
)
from app.domains.chat.mensagem_helpers import notificar_mesa_whisper, serializar_mensagem_mesa
from app.domains.chat.mesa_mobile_support import (
    carregar_mensagem_idempotente,
    carregar_mensagens_mesa_por_laudo_ids,
    normalizar_client_message_id,
    obter_request_id,
    serializar_estado_resumo_mesa_laudo,
)
from app.domains.chat.request_parsing_helpers import InteiroOpcionalNullish
from app.domains.chat.schemas import DadosMesaMensagem
from app.domains.chat.session_helpers import aplicar_contexto_laudo_selecionado, exigir_csrf
from app.domains.mesa.attachments import (
    conteudo_mensagem_mesa_com_anexo,
    remover_arquivo_anexo_mesa,
    resumo_mensagem_mesa,
    salvar_arquivo_anexo_mesa,
)
from app.domains.mesa.operational_tasks import (
    extract_operational_context,
    inspector_response_matches_operational_task,
)
from app.shared.database import (
    AnexoMesa,
    EvidenceMesaStatus,
    EvidenceOperationalStatus,
    MensagemLaudo,
    TipoMensagem,
    Usuario,
    obter_banco,
)
from app.shared.operational_memory import registrar_validacao_evidencia
from app.shared.operational_memory_contracts import EvidenceValidationInput
from app.shared.operational_memory_hooks import resolve_open_return_to_inspector_irregularities
from app.shared.security import exigir_inspetor
from app.shared.tenant_entitlement_guard import ensure_tenant_capability_for_user
from nucleo.inspetor.referencias_mensagem import compor_texto_com_referencia

def _resposta_envio_idempotente_mesa(
    *,
    request: Request,
    banco: Session,
    laudo,
    usuario: Usuario,
    mensagem_idempotente: MensagemLaudo,
    request_id: str,
):
    contexto = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)
    estado_resumo = serializar_estado_resumo_mesa_laudo(
        banco,
        laudo=laudo,
        mensagens=carregar_mensagens_mesa_por_laudo_ids(banco, [laudo.id]).get(laudo.id, []),
    )
    return resposta_json_ok(
        {
            "laudo_id": laudo.id,
            "mensagem": serializar_mensagem_mesa(mensagem_idempotente),
            "laudo_card": estado_resumo["laudo_card"],
            "estado": contexto["estado"],
            "permite_edicao": contexto["permite_edicao"],
            "permite_reabrir": contexto["permite_reabrir"],
            "resumo": estado_resumo["resumo"],
            "request_id": request_id,
            "idempotent_replay": True,
        }
    )


def _carregar_mensagem_referencia_laudo(
    banco: Session,
    *,
    laudo_id: int,
    referencia_mensagem_id: int | None,
) -> MensagemLaudo | None:
    if not referencia_mensagem_id:
        return None
    return banco.scalar(
        select(MensagemLaudo)
        .where(
            MensagemLaudo.laudo_id == laudo_id,
            MensagemLaudo.id == referencia_mensagem_id,
        )
        .options(selectinload(MensagemLaudo.anexos_mesa))
    )


def _replacement_evidence_key_for_response(
    *,
    mensagem: MensagemLaudo,
    anexos: list[AnexoMesa] | None = None,
) -> str:
    anexos_validos = list(anexos or [])
    if len(anexos_validos) == 1 and getattr(anexos_validos[0], "id", None):
        return f"msg:{int(mensagem.id)}:anexo:{int(anexos_validos[0].id)}"
    return f"msg:{int(mensagem.id)}"


def _tentar_resolver_tarefa_operacional_referenciada(
    banco: Session,
    *,
    laudo,
    inspetor_id: int,
    mensagem_referencia: MensagemLaudo | None,
    mensagem_resposta: MensagemLaudo,
    texto_limpo: str,
    anexos: list[AnexoMesa] | None = None,
) -> None:
    if mensagem_referencia is None or mensagem_referencia.resolvida_em is not None:
        return

    contexto = extract_operational_context(mensagem_referencia)
    if contexto is None:
        return
    if not inspector_response_matches_operational_task(
        operational_context=contexto,
        text=texto_limpo,
        attachments=anexos,
    ):
        return

    evidence_key = str(contexto.get("evidence_key") or "").strip()
    if evidence_key:
        registrar_validacao_evidencia(
            banco,
            EvidenceValidationInput(
                laudo_id=int(laudo.id),
                evidence_key=evidence_key,
                component_type=str(contexto.get("component_type") or "").strip() or None,
                view_angle=str(contexto.get("view_angle") or "").strip() or None,
                operational_status=EvidenceOperationalStatus.REPLACED.value,
                mesa_status=EvidenceMesaStatus.NEEDS_RECHECK.value,
                failure_reasons=[],
                evidence_metadata={
                    "origin": "inspector_operational_response",
                    "message_id": int(mensagem_resposta.id),
                    "reference_message_id": int(mensagem_referencia.id),
                    "required_action": str(contexto.get("required_action") or ""),
                    "response_text_preview": texto_limpo[:160] if texto_limpo else "",
                    "response_attachment_categories": [
                        str(getattr(anexo, "categoria", "") or "").strip()
                        for anexo in list(anexos or [])
                    ],
                },
                replacement_evidence_key=_replacement_evidence_key_for_response(
                    mensagem=mensagem_resposta,
                    anexos=anexos,
                ),
                validated_by_user_id=int(inspetor_id),
                last_evaluated_at=agora_utc(),
            ),
        )

    mensagem_referencia.lida = True
    mensagem_referencia.resolvida_por_id = int(inspetor_id)
    mensagem_referencia.resolvida_em = agora_utc()

    resolve_open_return_to_inspector_irregularities(
        banco,
        laudo_id=int(laudo.id),
        resolved_by_id=int(inspetor_id),
        resolution_mode="edited_case_data",
        resolution_notes=f"Inspetor respondeu ao refazer operacional da mensagem #{int(mensagem_referencia.id)}.",
        block_key=str(contexto.get("block_key") or "").strip() or None,
        evidence_key=evidence_key or None,
    )


async def enviar_mensagem_mesa_laudo(
    laudo_id: int,
    dados: DadosMesaMensagem,
    request: Request,
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    exigir_csrf(request)
    ensure_tenant_capability_for_user(
        usuario,
        capability="inspector_send_to_mesa",
    )
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    request_id = obter_request_id(request)

    if not laudo_permite_edicao_inspetor(laudo):
        raise HTTPException(
            status_code=400,
            detail=obter_detalhe_bloqueio_edicao_inspetor(
                laudo,
                surface="mesa_reply",
            ),
        )

    texto_limpo = (dados.texto or "").strip()
    if not texto_limpo:
        raise HTTPException(status_code=400, detail="Mensagem para a mesa está vazia.")

    primeira_interacao_real = not laudo_tem_interacao(banco, laudo.id)
    client_message_id = normalizar_client_message_id(dados.client_message_id)
    mensagem_idempotente = carregar_mensagem_idempotente(
        banco,
        laudo_id=laudo.id,
        remetente_id=usuario.id,
        client_message_id=client_message_id,
    )
    if mensagem_idempotente is not None:
        return _resposta_envio_idempotente_mesa(
            request=request,
            banco=banco,
            laudo=laudo,
            usuario=usuario,
            mensagem_idempotente=mensagem_idempotente,
            request_id=request_id,
        )

    referencia_mensagem_id = int(dados.referencia_mensagem_id or 0) or None
    mensagem_referencia = _carregar_mensagem_referencia_laudo(
        banco,
        laudo_id=int(laudo.id),
        referencia_mensagem_id=referencia_mensagem_id,
    )
    if referencia_mensagem_id and mensagem_referencia is None:
        raise HTTPException(status_code=404, detail="Mensagem de referência não encontrada.")

    mensagem = MensagemLaudo(
        laudo_id=laudo.id,
        remetente_id=usuario.id,
        tipo=TipoMensagem.HUMANO_INSP.value,
        conteudo=compor_texto_com_referencia(texto_limpo, referencia_mensagem_id),
        custo_api_reais=Decimal("0.0000"),
        client_message_id=client_message_id,
    )
    banco.add(mensagem)
    laudo.atualizado_em = agora_utc()
    if primeira_interacao_real:
        laudo.primeira_mensagem = obter_preview_primeira_mensagem(texto_limpo)
    try:
        banco.flush()
        _tentar_resolver_tarefa_operacional_referenciada(
            banco,
            laudo=laudo,
            inspetor_id=int(usuario.id),
            mensagem_referencia=mensagem_referencia,
            mensagem_resposta=mensagem,
            texto_limpo=texto_limpo,
            anexos=[],
        )
        banco.flush()
        banco.commit()
    except IntegrityError:
        banco.rollback()
        mensagem_idempotente = carregar_mensagem_idempotente(
            banco,
            laudo_id=laudo.id,
            remetente_id=usuario.id,
            client_message_id=client_message_id,
        )
        if mensagem_idempotente is not None:
            laudo_recarregado = obter_laudo_do_inspetor(banco, laudo_id, usuario)
            return _resposta_envio_idempotente_mesa(
                request=request,
                banco=banco,
                laudo=laudo_recarregado,
                usuario=usuario,
                mensagem_idempotente=mensagem_idempotente,
                request_id=request_id,
            )
        logger.error(
            "Falha de integridade ao confirmar envio de mensagem do inspetor para a mesa.",
            exc_info=True,
        )
        raise
    except Exception:
        banco.rollback()
        logger.error(
            "Falha ao confirmar envio de mensagem do inspetor para a mesa.",
            exc_info=True,
        )
        raise
    contexto = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)

    payload = serializar_mensagem_mesa(mensagem)
    await notificar_mesa_whisper(
        empresa_id=usuario.empresa_id,
        laudo_id=laudo.id,
        inspetor_id=usuario.id,
        inspetor_nome=usuario_nome(usuario),
        preview=texto_limpo,
        mensagem=payload,
    )
    estado_resumo = serializar_estado_resumo_mesa_laudo(
        banco,
        laudo=laudo,
        mensagens=carregar_mensagens_mesa_por_laudo_ids(banco, [laudo.id]).get(laudo.id, []),
    )
    return resposta_json_ok(
        {
            "laudo_id": laudo.id,
            "mensagem": payload,
            "laudo_card": estado_resumo["laudo_card"],
            "estado": contexto["estado"],
            "permite_edicao": contexto["permite_edicao"],
            "permite_reabrir": contexto["permite_reabrir"],
            "resumo": estado_resumo["resumo"],
            "request_id": request_id,
            "idempotent_replay": False,
        },
        status_code=201,
    )


async def enviar_mensagem_mesa_laudo_com_anexo(
    laudo_id: int,
    request: Request,
    arquivo: UploadFile = File(...),
    texto: str = Form(default=""),
    referencia_mensagem_id: Annotated[InteiroOpcionalNullish, Form()] = None,
    client_message_id: Annotated[str | None, Form()] = None,
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    exigir_csrf(request)
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    request_id = obter_request_id(request)

    if not laudo_permite_edicao_inspetor(laudo):
        raise HTTPException(
            status_code=400,
            detail=obter_detalhe_bloqueio_edicao_inspetor(
                laudo,
                surface="mesa_reply",
            ),
        )

    texto_limpo = str(texto or "").strip()
    primeira_interacao_real = not laudo_tem_interacao(banco, laudo.id)
    client_message_id_normalizado = normalizar_client_message_id(client_message_id)
    mensagem_idempotente = carregar_mensagem_idempotente(
        banco,
        laudo_id=laudo.id,
        remetente_id=usuario.id,
        client_message_id=client_message_id_normalizado,
    )
    if mensagem_idempotente is not None:
        return _resposta_envio_idempotente_mesa(
            request=request,
            banco=banco,
            laudo=laudo,
            usuario=usuario,
            mensagem_idempotente=mensagem_idempotente,
            request_id=request_id,
        )

    referencia_id = int(referencia_mensagem_id or 0) or None
    mensagem_referencia = _carregar_mensagem_referencia_laudo(
        banco,
        laudo_id=int(laudo.id),
        referencia_mensagem_id=referencia_id,
    )
    if referencia_id and mensagem_referencia is None:
        raise HTTPException(status_code=404, detail="Mensagem de referência não encontrada.")

    conteudo_arquivo = await arquivo.read()
    dados_arquivo = salvar_arquivo_anexo_mesa(
        empresa_id=usuario.empresa_id,
        laudo_id=laudo.id,
        nome_original=str(arquivo.filename or "anexo_mesa"),
        mime_type=str(arquivo.content_type or ""),
        conteudo=conteudo_arquivo,
    )

    try:
        mensagem = MensagemLaudo(
            laudo_id=laudo.id,
            remetente_id=usuario.id,
            tipo=TipoMensagem.HUMANO_INSP.value,
            conteudo=compor_texto_com_referencia(
                conteudo_mensagem_mesa_com_anexo(texto_limpo),
                referencia_id,
            ),
            custo_api_reais=Decimal("0.0000"),
            client_message_id=client_message_id_normalizado,
        )
        banco.add(mensagem)
        banco.flush()

        anexo = AnexoMesa(
            laudo_id=laudo.id,
            mensagem_id=mensagem.id,
            enviado_por_id=usuario.id,
            nome_original=dados_arquivo["nome_original"],
            nome_arquivo=dados_arquivo["nome_arquivo"],
            mime_type=dados_arquivo["mime_type"],
            categoria=dados_arquivo["categoria"],
            tamanho_bytes=dados_arquivo["tamanho_bytes"],
            caminho_arquivo=dados_arquivo["caminho_arquivo"],
        )
        mensagem.anexos_mesa.append(anexo)
        banco.flush()

        laudo.atualizado_em = agora_utc()
        if primeira_interacao_real:
            laudo.primeira_mensagem = obter_preview_primeira_mensagem(
                texto_limpo,
                nome_documento=anexo.nome_original if anexo.categoria == "documento" else "",
                tem_imagem=anexo.categoria == "imagem",
            )
        _tentar_resolver_tarefa_operacional_referenciada(
            banco,
            laudo=laudo,
            inspetor_id=int(usuario.id),
            mensagem_referencia=mensagem_referencia,
            mensagem_resposta=mensagem,
            texto_limpo=texto_limpo,
            anexos=[anexo],
        )
        banco.commit()
    except IntegrityError:
        banco.rollback()
        remover_arquivo_anexo_mesa(dados_arquivo.get("caminho_arquivo"))
        mensagem_idempotente = carregar_mensagem_idempotente(
            banco,
            laudo_id=laudo.id,
            remetente_id=usuario.id,
            client_message_id=client_message_id_normalizado,
        )
        if mensagem_idempotente is not None:
            laudo_recarregado = obter_laudo_do_inspetor(banco, laudo_id, usuario)
            return _resposta_envio_idempotente_mesa(
                request=request,
                banco=banco,
                laudo=laudo_recarregado,
                usuario=usuario,
                mensagem_idempotente=mensagem_idempotente,
                request_id=request_id,
            )
        logger.error(
            "Falha de integridade ao confirmar envio de anexo do inspetor para a mesa.",
            exc_info=True,
        )
        raise
    except Exception:
        banco.rollback()
        remover_arquivo_anexo_mesa(dados_arquivo.get("caminho_arquivo"))
        logger.error(
            "Falha ao confirmar envio de anexo do inspetor para a mesa.",
            exc_info=True,
        )
        raise

    contexto = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)
    preview = resumo_mensagem_mesa(mensagem.conteudo, anexos=[anexo])

    payload = serializar_mensagem_mesa(mensagem)
    await notificar_mesa_whisper(
        empresa_id=usuario.empresa_id,
        laudo_id=laudo.id,
        inspetor_id=usuario.id,
        inspetor_nome=usuario_nome(usuario),
        preview=preview,
        mensagem=payload,
    )
    estado_resumo = serializar_estado_resumo_mesa_laudo(
        banco,
        laudo=laudo,
        mensagens=carregar_mensagens_mesa_por_laudo_ids(banco, [laudo.id]).get(laudo.id, []),
    )
    return resposta_json_ok(
        {
            "laudo_id": laudo.id,
            "mensagem": payload,
            "laudo_card": estado_resumo["laudo_card"],
            "estado": contexto["estado"],
            "permite_edicao": contexto["permite_edicao"],
            "permite_reabrir": contexto["permite_reabrir"],
            "resumo": estado_resumo["resumo"],
            "request_id": request_id,
            "idempotent_replay": False,
        },
        status_code=201,
    )


async def baixar_anexo_mesa_laudo(
    laudo_id: int,
    anexo_id: int,
    usuario: Usuario = Depends(exigir_inspetor),
    banco: Session = Depends(obter_banco),
):
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    anexo = banco.scalar(
        select(AnexoMesa).where(
            AnexoMesa.id == anexo_id,
            AnexoMesa.laudo_id == laudo.id,
        )
    )
    if not anexo or not str(anexo.caminho_arquivo or "").strip() or not os.path.isfile(str(anexo.caminho_arquivo)):
        raise HTTPException(status_code=404, detail="Anexo da mesa não encontrado.")

    return FileResponse(
        path=str(anexo.caminho_arquivo),
        filename=str(anexo.nome_original or anexo.nome_arquivo or f"anexo_mesa_{anexo.id}"),
        media_type=str(anexo.mime_type or "application/octet-stream"),
    )


__all__ = [
    "enviar_mensagem_mesa_laudo",
    "enviar_mensagem_mesa_laudo_com_anexo",
    "baixar_anexo_mesa_laudo",
]
