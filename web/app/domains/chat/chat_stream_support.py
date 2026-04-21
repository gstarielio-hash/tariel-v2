"""Preparação e persistência do fluxo principal de chat do inspetor."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.domains.chat.auth_helpers import usuario_nome
from app.domains.chat.auth_mobile_support import obter_contexto_preferencia_modo_entrada_usuario
from app.domains.chat.app_context import logger
from app.domains.chat.catalog_pdf_templates import capture_catalog_snapshot_for_laudo
from app.domains.chat.chat_runtime import MODO_DEEP, resolver_modo_entrada_caso
from app.domains.chat.commands_helpers import (
    montar_resposta_comando_rapido,
    registrar_comando_rapido_historico,
)
from app.domains.chat.core_helpers import agora_utc, obter_preview_primeira_mensagem
from app.domains.chat.laudo_access_helpers import obter_laudo_do_inspetor
from app.domains.chat.laudo_state_helpers import (
    laudo_permite_edicao_inspetor,
    laudo_possui_historico_visivel,
    laudo_tem_interacao,
    mesclar_guided_inspection_draft_laudo,
    obter_detalhe_bloqueio_edicao_inspetor,
    serializar_card_laudo,
)
from app.domains.chat.learning_helpers import (
    anexar_contexto_aprendizado_na_mensagem,
    construir_contexto_aprendizado_para_ia,
    registrar_aprendizado_visual_automatico_chat,
)
from app.domains.chat.limits_helpers import (
    garantir_deep_research_habilitado,
    garantir_limite_laudos,
    garantir_upload_documento_habilitado,
)
from app.domains.chat.media_helpers import (
    nome_documento_seguro,
    validar_historico_total,
    validar_imagem_base64,
)
from app.domains.chat.mobile_ai_preferences import (
    anexar_preferencias_ia_mobile_na_mensagem,
    combinar_preferencias_ia_mobile_contexto,
    extrair_preferencias_ia_mobile_embutidas,
    limpar_historico_visivel_chat,
)
from app.domains.chat.normalization import (
    nome_template_humano,
    normalizar_tipo_template,
    resolver_familia_padrao_template,
)
from app.domains.chat.report_pack_helpers import (
    atualizar_report_pack_draft_laudo,
    build_pre_laudo_prompt_context,
    build_pre_laudo_summary,
    obter_pre_laudo_outline_report_pack,
)
from app.domains.chat.schemas import (
    GuidedInspectionEvidenceRefPayload,
    GuidedInspectionMesaHandoffPayload,
)
from app.domains.chat.session_helpers import aplicar_contexto_laudo_selecionado
from app.domains.chat.template_governance import (
    apply_template_governance_to_laudo,
    resolve_guided_template_governance,
)
from app.v2.case_runtime import (
    build_legacy_case_status_payload_from_laudo,
    build_technical_case_context_bundle,
)
from app.shared.database import (
    Laudo,
    MensagemLaudo,
    StatusRevisao,
    TipoMensagem,
    Usuario,
    commit_ou_rollback_operacional,
)
from nucleo.inspetor.comandos_chat import (
    analisar_comando_finalizacao,
    analisar_comando_rapido_chat,
    mensagem_para_mesa,
    remover_mencao_mesa,
)
from nucleo.inspetor.referencias_mensagem import compor_texto_com_referencia


@dataclass(slots=True)
class ChatPreparedRoute:
    mensagem_limpa: str
    preferencias_ia_mobile: str
    dados_imagem_validos: Any
    texto_documento: str
    nome_documento: str
    laudo: Laudo
    primeira_interacao_real: bool
    historico_dict: list[dict[str, Any]]
    guided_inspection_draft: Any
    guided_inspection_context: Any


@dataclass(slots=True)
class ChatPersistedMessageContext:
    laudo: Laudo
    historico_dict: list[dict[str, Any]]
    headers: dict[str, str]
    mensagem_para_ia: str
    dados_imagem_validos: Any
    texto_documento: str
    nome_documento: str
    eh_whisper_para_mesa: bool
    eh_comando_finalizar: bool
    tipo_template_finalizacao: str | None
    referencia_mensagem_id: int | None
    texto_exibicao: str
    card_laudo_payload: dict[str, Any] | None
    laudo_id_atual: int
    empresa_id_atual: int
    usuario_id_atual: int
    usuario_nome_atual: str
    mensagem_usuario_id: int
    eh_deep: bool

def _resolver_review_mode_guided_flow(
    *,
    banco: Session,
    usuario: Usuario,
    laudo: Laudo,
) -> str:
    runtime_bundle = build_technical_case_context_bundle(
        banco=banco,
        usuario=usuario,
        laudo=laudo,
        legacy_payload=build_legacy_case_status_payload_from_laudo(
            banco=banco,
            laudo=laudo,
            include_entry_mode_context=True,
        ),
        source_channel="chat_guided_flow",
        template_key=getattr(laudo, "tipo_template", None),
        family_key=getattr(laudo, "catalog_family_key", None),
        variant_key=getattr(laudo, "catalog_variant_key", None),
        laudo_type=getattr(laudo, "tipo_template", None),
        document_type=getattr(laudo, "tipo_template", None),
        report_pack_draft=getattr(laudo, "report_pack_draft_json", None),
        include_document_facade=False,
    )
    review_mode = getattr(getattr(runtime_bundle.policy_decision, "summary", None), "review_mode", "")
    return str(review_mode or "").strip().lower()


def prepare_chat_stream_route(
    *,
    dados,
    request: Request,
    usuario: Usuario,
    banco: Session,
) -> tuple[ChatPreparedRoute | None, JSONResponse | None]:
    validar_historico_total(dados.historico)

    mensagem_limpa, preferencias_embutidas = extrair_preferencias_ia_mobile_embutidas(
        dados.mensagem or ""
    )
    preferencias_ia_mobile = combinar_preferencias_ia_mobile_contexto(
        getattr(dados, "preferencias_ia_mobile", ""),
        preferencias_embutidas,
    )
    comando_rapido, argumento_comando_rapido = analisar_comando_rapido_chat(mensagem_limpa)
    dados_imagem_validos = validar_imagem_base64(dados.dados_imagem)
    texto_documento = (dados.texto_documento or "").strip()
    nome_documento = nome_documento_seguro(dados.nome_documento)

    if not mensagem_limpa and not dados_imagem_validos and not texto_documento:
        raise HTTPException(status_code=400, detail="Envie texto, imagem ou documento.")

    if texto_documento:
        garantir_upload_documento_habilitado(usuario, banco)

    if dados.modo == MODO_DEEP:
        garantir_deep_research_habilitado(usuario, banco)

    laudo: Laudo | None = None
    primeira_interacao_real = False
    guided_template_key = (
        normalizar_tipo_template(dados.guided_inspection_draft.template_key)
        if getattr(dados, "guided_inspection_draft", None) is not None
        else None
    )
    guided_template_resolution = None
    if dados.laudo_id:
        laudo = obter_laudo_do_inspetor(banco, dados.laudo_id, usuario)
        primeira_interacao_real = not laudo_tem_interacao(banco, laudo.id)

        if not laudo_permite_edicao_inspetor(laudo):
            raise HTTPException(
                status_code=400,
                detail=obter_detalhe_bloqueio_edicao_inspetor(
                    laudo,
                    surface="chat",
                ),
            )
        if guided_template_key:
            guided_template_resolution = resolve_guided_template_governance(
                banco,
                usuario=usuario,
                template_key=guided_template_key,
                laudo=laudo,
            )
            guided_template_key = str(
                guided_template_resolution.get("runtime_template_code") or guided_template_key
            ).strip().lower() or guided_template_key
            apply_template_governance_to_laudo(
                laudo=laudo,
                resolucao_template=guided_template_resolution,
            )
            capture_catalog_snapshot_for_laudo(
                banco=banco,
                laudo=laudo,
            )

    if comando_rapido:
        if dados_imagem_validos or texto_documento:
            raise HTTPException(
                status_code=400,
                detail="Comandos rápidos não aceitam imagem ou documento.",
            )

        if comando_rapido == "enviar_mesa":
            if not laudo:
                raise HTTPException(
                    status_code=400,
                    detail="A conversa com a mesa avaliadora só é permitida após iniciar uma nova inspeção.",
                )
            if not argumento_comando_rapido:
                raise HTTPException(
                    status_code=400,
                    detail="Use /enviar_mesa seguido da mensagem para a mesa avaliadora.",
                )
            mensagem_limpa = f"@insp {argumento_comando_rapido}"
        else:
            if not laudo:
                raise HTTPException(
                    status_code=400,
                    detail="Esse comando exige um relatório ativo.",
                )

            texto_comando = montar_resposta_comando_rapido(
                banco=banco,
                laudo=laudo,
                comando=comando_rapido,
                argumento=argumento_comando_rapido,
            )
            registrar_comando_rapido_historico(
                banco=banco,
                laudo=laudo,
                usuario=usuario,
                comando=comando_rapido,
                argumento=argumento_comando_rapido,
                resposta=texto_comando,
            )
            banco.flush()
            aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)

            return None, JSONResponse(
                {
                    "texto": texto_comando,
                    "tipo": "comando_rapido",
                    "comando": f"/{comando_rapido}",
                    "laudo_id": laudo.id,
                    "laudo_card": serializar_card_laudo(banco, laudo),
                }
            )

    if not laudo:
        garantir_limite_laudos(usuario, banco)
        if guided_template_key:
            guided_template_resolution = resolve_guided_template_governance(
                banco,
                usuario=usuario,
                template_key=guided_template_key,
                laudo=None,
            )
            guided_template_key = str(
                guided_template_resolution.get("runtime_template_code") or guided_template_key
            ).strip().lower() or guided_template_key
        guided_template_family = (
            resolver_familia_padrao_template(guided_template_key)
            if guided_template_key
            else None
        )
        contexto_preferencia_modo_entrada = obter_contexto_preferencia_modo_entrada_usuario(
            banco,
            usuario_id=int(usuario.id),
        )
        try:
            entry_mode_decision = resolver_modo_entrada_caso(
                requested_preference=dados.entry_mode_preference,
                existing_preference=contexto_preferencia_modo_entrada.entry_mode_preference,
                last_case_mode=(
                    contexto_preferencia_modo_entrada.last_case_mode
                    if contexto_preferencia_modo_entrada.remember_last_case_mode
                    else None
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        laudo = Laudo(
            empresa_id=usuario.empresa_id,
            usuario_id=usuario.id,
            setor_industrial=(
                nome_template_humano(guided_template_key)
                if guided_template_key and str(dados.setor or "").strip().lower() == "geral"
                else dados.setor
            ),
            tipo_template=guided_template_key or "padrao",
            catalog_selection_token=(
                str((guided_template_resolution or {}).get("selection_token") or "").strip() or None
            ),
            catalog_family_key=(
                str(
                    (guided_template_resolution or {}).get("family_key")
                    or (guided_template_family or {}).get("family_key")
                    or ""
                ).strip()
                or None
            ),
            catalog_family_label=(
                str(
                    (guided_template_resolution or {}).get("family_label")
                    or (guided_template_family or {}).get("family_label")
                    or ""
                ).strip()
                or None
            ),
            catalog_variant_key=(
                str((guided_template_resolution or {}).get("variant_key") or "").strip() or None
            ),
            catalog_variant_label=(
                str((guided_template_resolution or {}).get("variant_label") or "").strip() or None
            ),
            codigo_hash=uuid.uuid4().hex,
            primeira_mensagem=None,
            modo_resposta=dados.modo,
            is_deep_research=(dados.modo == MODO_DEEP),
            status_revisao=StatusRevisao.RASCUNHO.value,
            entry_mode_preference=entry_mode_decision.preference,
            entry_mode_effective=entry_mode_decision.effective,
            entry_mode_reason=entry_mode_decision.reason,
        )
        banco.add(laudo)
        primeira_interacao_real = True

        try:
            banco.flush()
            capture_catalog_snapshot_for_laudo(
                banco=banco,
                laudo=laudo,
            )
        except Exception:
            banco.rollback()
            logger.error("Falha ao criar laudo.", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar sessão de laudo.",
            )

    aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)

    return ChatPreparedRoute(
        mensagem_limpa=mensagem_limpa,
        preferencias_ia_mobile=preferencias_ia_mobile,
        dados_imagem_validos=dados_imagem_validos,
        texto_documento=texto_documento,
        nome_documento=nome_documento,
        laudo=laudo,
        primeira_interacao_real=primeira_interacao_real,
        historico_dict=limpar_historico_visivel_chat(
            [msg.model_dump() for msg in dados.historico]
        ),
        guided_inspection_draft=dados.guided_inspection_draft,
        guided_inspection_context=dados.guided_inspection_context,
    ), None


def persist_chat_user_message(
    *,
    dados,
    request: Request,
    usuario: Usuario,
    banco: Session,
    prepared: ChatPreparedRoute,
) -> ChatPersistedMessageContext:
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    eh_comando_finalizar, tipo_template_finalizacao = analisar_comando_finalizacao(
        prepared.mensagem_limpa,
        normalizar_tipo_template=normalizar_tipo_template,
    )
    eh_whisper_para_mesa = mensagem_para_mesa(prepared.mensagem_limpa)
    referencia_mensagem_id = None
    texto_exibicao = ""

    if eh_whisper_para_mesa:
        tipo_msg_usuario = TipoMensagem.HUMANO_INSP.value
        texto_exibicao = remover_mencao_mesa(prepared.mensagem_limpa)
        if not texto_exibicao:
            raise HTTPException(status_code=400, detail="Mensagem para a mesa está vazia.")
        referencia_mensagem_id = int(dados.referencia_mensagem_id or 0) or None
        texto_salvar = compor_texto_com_referencia(texto_exibicao, referencia_mensagem_id)
    elif eh_comando_finalizar:
        tipo_msg_usuario = TipoMensagem.USER.value
        texto_salvar = "*(Inspetor solicitou encerramento e geração do laudo)*"
        texto_exibicao = texto_salvar
    else:
        tipo_msg_usuario = TipoMensagem.USER.value
        texto_salvar = prepared.mensagem_limpa or prepared.nome_documento or "[imagem]"
        texto_exibicao = texto_salvar

    mensagem_usuario = MensagemLaudo(
        laudo_id=prepared.laudo.id,
        remetente_id=usuario.id,
        tipo=tipo_msg_usuario,
        conteudo=texto_salvar,
        custo_api_reais=Decimal("0.0000"),
    )
    banco.add(mensagem_usuario)
    banco.flush()

    timestamp_operacao = agora_utc()
    prepared.laudo.atualizado_em = timestamp_operacao
    prepared.laudo.modo_resposta = dados.modo
    prepared.laudo.is_deep_research = dados.modo == MODO_DEEP

    if not prepared.laudo.primeira_mensagem:
        prepared.laudo.primeira_mensagem = obter_preview_primeira_mensagem(
            prepared.mensagem_limpa,
            nome_documento=prepared.nome_documento,
            tem_imagem=bool(prepared.dados_imagem_validos),
        )

    if tipo_msg_usuario == TipoMensagem.USER.value and not eh_comando_finalizar:
        registrar_aprendizado_visual_automatico_chat(
            banco,
            empresa_id=usuario.empresa_id,
            laudo_id=prepared.laudo.id,
            criado_por_id=usuario.id,
            setor_industrial=str(prepared.laudo.setor_industrial or "geral"),
            mensagem_id=int(mensagem_usuario.id),
            mensagem_chat=prepared.mensagem_limpa,
            dados_imagem=prepared.dados_imagem_validos,
            referencia_mensagem_id=int(dados.referencia_mensagem_id or 0) or None,
        )

    guided_evidence_ref = None
    guided_mesa_handoff = None
    if prepared.guided_inspection_context is not None:
        guided_evidence_ref = GuidedInspectionEvidenceRefPayload(
            message_id=int(mensagem_usuario.id),
            step_id=prepared.guided_inspection_context.step_id,
            step_title=prepared.guided_inspection_context.step_title,
            captured_at=timestamp_operacao.isoformat(),
            evidence_kind="chat_message",
            attachment_kind=prepared.guided_inspection_context.attachment_kind,
        )
        review_mode_guided = _resolver_review_mode_guided_flow(
            banco=banco,
            usuario=usuario,
            laudo=prepared.laudo,
        )
        if review_mode_guided == "mesa_required":
            guided_mesa_handoff = GuidedInspectionMesaHandoffPayload(
                required=True,
                review_mode=review_mode_guided,
                reason_code="policy_review_mode",
                recorded_at=timestamp_operacao.isoformat(),
                step_id=prepared.guided_inspection_context.step_id,
                step_title=prepared.guided_inspection_context.step_title,
            )

    mesclar_guided_inspection_draft_laudo(
        laudo=prepared.laudo,
        draft_payload=prepared.guided_inspection_draft,
        evidence_ref=guided_evidence_ref,
        mesa_handoff=guided_mesa_handoff,
    )
    report_pack_draft = atualizar_report_pack_draft_laudo(
        banco=banco,
        laudo=prepared.laudo,
    )
    if (
        isinstance(getattr(prepared.laudo, "guided_inspection_draft_json", None), dict)
        and isinstance(report_pack_draft, dict)
        and isinstance(report_pack_draft.get("quality_gates"), dict)
        and str(report_pack_draft["quality_gates"].get("final_validation_mode") or "").strip().lower()
        == "mobile_autonomous"
    ):
        prepared.laudo.guided_inspection_draft_json["mesa_handoff"] = None

    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao confirmar mensagem inicial do stream de chat.",
    )
    aplicar_contexto_laudo_selecionado(request, banco, prepared.laudo, usuario)

    laudo_id_atual = prepared.laudo.id
    empresa_id_atual = usuario.empresa_id
    usuario_id_atual = usuario.id
    usuario_nome_atual = usuario_nome(usuario)
    card_laudo_payload = (
        serializar_card_laudo(banco, prepared.laudo)
        if prepared.primeira_interacao_real and laudo_possui_historico_visivel(banco, prepared.laudo)
        else None
    )
    contexto_aprendizado_ia = construir_contexto_aprendizado_para_ia(
        banco,
        empresa_id=empresa_id_atual,
        laudo_id=laudo_id_atual,
        setor_industrial=str(prepared.laudo.setor_industrial or "geral"),
        mensagem_atual=prepared.mensagem_limpa,
    )
    pre_laudo_summary = build_pre_laudo_summary(
        obter_pre_laudo_outline_report_pack(report_pack_draft)
    )
    mensagem_base_para_ia = anexar_preferencias_ia_mobile_na_mensagem(
        prepared.mensagem_limpa,
        preferencias_ia_mobile=prepared.preferencias_ia_mobile,
    )
    pre_laudo_prompt_context = build_pre_laudo_prompt_context(
        pre_laudo_summary,
        template_key=(
            report_pack_draft.get("template_key")
            if isinstance(report_pack_draft, dict)
            else getattr(prepared.laudo, "tipo_template", None)
        ),
        guided_context=prepared.guided_inspection_context,
        analysis_basis=(
            dict(report_pack_draft.get("analysis_basis") or {})
            if isinstance(report_pack_draft, dict)
            and isinstance(report_pack_draft.get("analysis_basis"), dict)
            else None
        ),
    )
    if pre_laudo_prompt_context:
        if mensagem_base_para_ia:
            mensagem_base_para_ia = (
                f"{pre_laudo_prompt_context}\n\n{mensagem_base_para_ia}"
            )
        else:
            mensagem_base_para_ia = pre_laudo_prompt_context

    mensagem_para_ia = anexar_contexto_aprendizado_na_mensagem(
        mensagem_base_para_ia,
        contexto_aprendizado=contexto_aprendizado_ia,
    )

    return ChatPersistedMessageContext(
        laudo=prepared.laudo,
        historico_dict=prepared.historico_dict,
        headers=headers,
        mensagem_para_ia=mensagem_para_ia,
        dados_imagem_validos=prepared.dados_imagem_validos,
        texto_documento=prepared.texto_documento,
        nome_documento=prepared.nome_documento,
        eh_whisper_para_mesa=eh_whisper_para_mesa,
        eh_comando_finalizar=eh_comando_finalizar,
        tipo_template_finalizacao=tipo_template_finalizacao,
        referencia_mensagem_id=referencia_mensagem_id,
        texto_exibicao=texto_exibicao,
        card_laudo_payload=card_laudo_payload,
        laudo_id_atual=laudo_id_atual,
        empresa_id_atual=empresa_id_atual,
        usuario_id_atual=usuario_id_atual,
        usuario_nome_atual=usuario_nome_atual,
        mensagem_usuario_id=int(mensagem_usuario.id),
        eh_deep=(dados.modo == MODO_DEEP),
    )


__all__ = [
    "ChatPersistedMessageContext",
    "ChatPreparedRoute",
    "persist_chat_user_message",
    "prepare_chat_stream_route",
]
