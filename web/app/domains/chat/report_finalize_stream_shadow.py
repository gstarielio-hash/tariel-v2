"""Isolamento estrutural do slice report_finalize_stream em shadow_only."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from fastapi import Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.domains.chat.app_context import logger
from app.domains.chat.catalog_pdf_templates import materialize_catalog_payload_for_laudo
from app.domains.chat.core_helpers import agora_utc, evento_sse
from app.domains.chat.gate_helpers import garantir_gate_qualidade_laudo
from app.domains.chat.ia_runtime import obter_cliente_ia_ativo
from app.domains.chat.laudo_service import _avaliar_gate_documental_finalizacao
from app.domains.chat.laudo_state_helpers import (
    aplicar_finalizacao_inspetor_ao_laudo,
    serializar_card_laudo,
)
from app.domains.chat.normalization import nome_template_humano
from app.domains.chat.session_helpers import aplicar_contexto_laudo_selecionado, obter_contexto_inicial_laudo_sessao
from app.domains.chat.template_governance import resolve_case_bound_runtime_template
from app.domains.chat.templates_ai import obter_schema_template_ia
from app.shared.database import (
    Laudo,
    MensagemLaudo,
    TipoMensagem,
    Usuario,
    commit_ou_rollback_operacional,
)
from app.v2.document.hard_gate_evidence import record_document_hard_gate_durable_evidence
from app.v2.runtime import (
    v2_document_hard_gate_enabled,
    v2_document_hard_gate_operation_allowlist,
    v2_document_hard_gate_tenant_allowlist,
)

_LOCAL_CONTROLLED_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_REPORT_FINALIZE_STREAM_OPERATION: Literal["report_finalize_stream"] = "report_finalize_stream"
_REPORT_FINALIZE_STREAM_ROUTE_NAME = "rota_chat_report_finalize_stream"
_REPORT_FINALIZE_STREAM_LEGACY_PIPELINE = "legacy_report_finalize_stream"
_REPORT_FINALIZE_STREAM_SOURCE_CHANNEL = "web_app_chat"


def report_finalize_stream_shadow_scope_enabled(
    *,
    request: Request,
    usuario: Usuario,
) -> bool:
    if not v2_document_hard_gate_enabled():
        return False

    remote_host = str(getattr(getattr(request, "client", None), "host", "") or "").strip().lower()
    if remote_host and remote_host not in _LOCAL_CONTROLLED_HOSTS:
        return False

    tenant_id = str(getattr(usuario, "empresa_id", "") or "").strip()
    if tenant_id not in set(v2_document_hard_gate_tenant_allowlist()):
        return False

    return _REPORT_FINALIZE_STREAM_OPERATION in set(v2_document_hard_gate_operation_allowlist())


def _build_shadow_scope_payload(
    *,
    request: Request,
    usuario: Usuario,
    laudo: Laudo,
    scope_enabled: bool,
) -> dict[str, Any]:
    return {
        "operation_kind": _REPORT_FINALIZE_STREAM_OPERATION,
        "route_name": _REPORT_FINALIZE_STREAM_ROUTE_NAME,
        "route_path": str(request.scope.get("path") or "/app/api/chat"),
        "remote_host": str(getattr(getattr(request, "client", None), "host", "") or ""),
        "tenant_id": str(getattr(usuario, "empresa_id", "") or ""),
        "legacy_laudo_id": int(getattr(laudo, "id", 0) or 0),
        "enabled": bool(scope_enabled),
    }


def _persist_shadow_observation(
    *,
    request: Request,
    usuario: Usuario,
    laudo: Laudo,
    hard_gate_result: Any | None,
    texto_resposta: str,
) -> str | None:
    if hard_gate_result is None:
        return None

    encerrado_em = getattr(laudo, "encerrado_pelo_inspetor_em", None)
    artifact_path = record_document_hard_gate_durable_evidence(
        hard_gate_result,
        remote_host=getattr(getattr(request, "client", None), "host", None),
        observation_context={
            "functional_outcome": "stream_finalize_completed_shadow_only",
            "response": {
                "status_code": 200,
                "media_type": "text/event-stream",
                "sse_preserved": True,
            },
            "target": {
                "legacy_laudo_id": int(getattr(laudo, "id", 0) or 0),
                "tipo_template": str(getattr(laudo, "tipo_template", "") or ""),
                "status_revisao": str(getattr(laudo, "status_revisao", "") or ""),
                "encerrado_pelo_inspetor_em": (
                    encerrado_em.isoformat() if encerrado_em is not None else None
                ),
            },
            "source_context": {
                "slice_name": _REPORT_FINALIZE_STREAM_OPERATION,
                "branch_name": "eh_comando_finalizar",
                "route_context": "chat_stream_finalize_shadow",
                "tenant_id": str(getattr(usuario, "empresa_id", "") or ""),
            },
            "assistant_message_preview": texto_resposta[:160],
        },
    )
    if artifact_path:
        request.state.v2_report_finalize_stream_shadow_artifact_path = artifact_path
    return artifact_path


async def processar_finalizacao_stream_documental(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
    laudo: Laudo,
    historico_dict: list[dict[str, Any]],
    dados_imagem_validos: list[str] | None,
    texto_documento: str,
    tipo_template_finalizacao: str,
    headers: dict[str, str],
) -> StreamingResponse:
    template_binding = resolve_case_bound_runtime_template(
        laudo=laudo,
        requested_template_key=tipo_template_finalizacao,
    )
    tipo_template_efetivo = str(
        template_binding.get("effective_template_code") or "padrao"
    ).strip().lower() or "padrao"
    if bool(template_binding.get("overrode_requested_template")):
        logger.info(
            "Finalizacao stream preservou binding governado do caso | laudo_id=%s | requested=%s | effective=%s | selection_token=%s",
            getattr(laudo, "id", None),
            template_binding.get("requested_template_code"),
            tipo_template_efetivo,
            template_binding.get("selection_token"),
        )

    laudo.tipo_template = tipo_template_efetivo
    laudo.atualizado_em = agora_utc()

    texto_resposta = "✅ **Sessão finalizada!** O laudo foi encaminhado para o engenheiro revisor."

    schema_pydantic = obter_schema_template_ia(tipo_template_efetivo)
    if schema_pydantic is not None:
        texto_resposta = (
            f"✅ **Relatório {nome_template_humano(tipo_template_efetivo)} "
            "estruturado gerado!** Os campos documentais foram consolidados."
        )
        try:
            cliente_ia_ativo = obter_cliente_ia_ativo()
            dados_imagem_payload = (
                "\n".join(dados_imagem_validos)
                if dados_imagem_validos
                else None
            )
            dados_json = await cliente_ia_ativo.gerar_json_estruturado(
                schema_pydantic=schema_pydantic,
                historico=historico_dict,
                dados_imagem=dados_imagem_payload,
                texto_documento=texto_documento,
            )
            laudo.dados_formulario = dados_json
        except Exception:
            logger.error(
                "Falha ao gerar JSON estruturado do template %s.",
                tipo_template_efetivo,
                exc_info=True,
            )
            texto_resposta = (
                "❌ O laudo foi enviado ao revisor, mas houve falha ao estruturar "
                "os campos documentais."
            )

    contexto_inicial = obter_contexto_inicial_laudo_sessao(
        request,
        laudo_id=int(laudo.id),
    )
    dados_formulario_atual = laudo.dados_formulario if isinstance(laudo.dados_formulario, dict) else {}
    source_payload = {
        **contexto_inicial,
        **dados_formulario_atual,
    } if (contexto_inicial or dados_formulario_atual) else None
    materialize_catalog_payload_for_laudo(
        laudo=laudo,
        source_payload=source_payload,
        diagnostico=str(getattr(laudo, "parecer_ia", "") or ""),
        inspetor=str(getattr(usuario, "nome_completo", "") or ""),
        empresa=str(getattr(getattr(usuario, "empresa", None), "nome_fantasia", "") or ""),
    )

    garantir_gate_qualidade_laudo(banco, laudo)

    shadow_scope_enabled = report_finalize_stream_shadow_scope_enabled(
        request=request,
        usuario=usuario,
    )
    request.state.v2_report_finalize_stream_shadow_scope = _build_shadow_scope_payload(
        request=request,
        usuario=usuario,
        laudo=laudo,
        scope_enabled=shadow_scope_enabled,
    )

    hard_gate_result = None
    if shadow_scope_enabled:
        try:
            _, hard_gate_result = _avaliar_gate_documental_finalizacao(
                request=request,
                usuario=usuario,
                banco=banco,
                laudo=laudo,
                route_name=_REPORT_FINALIZE_STREAM_ROUTE_NAME,
                route_path=str(request.scope.get("path") or "/app/api/chat"),
                source_channel=_REPORT_FINALIZE_STREAM_SOURCE_CHANNEL,
                operation_kind=_REPORT_FINALIZE_STREAM_OPERATION,
                legacy_pipeline_name=_REPORT_FINALIZE_STREAM_LEGACY_PIPELINE,
            )
        except Exception:
            logger.debug(
                "Falha ao avaliar hard gate documental da finalizacao via stream.",
                exc_info=True,
            )
            request.state.v2_document_hard_gate_error = "report_finalize_stream_hard_gate_failed"

    aplicar_finalizacao_inspetor_ao_laudo(
        laudo,
        target_status="aguardando_mesa",
        occurred_at=agora_utc(),
    )
    banco.add(
        MensagemLaudo(
            laudo_id=laudo.id,
            tipo=TipoMensagem.IA.value,
            conteudo=texto_resposta,
            custo_api_reais=Decimal("0.0000"),
        )
    )

    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao confirmar finalizacao do laudo no stream de chat.",
    )
    aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)

    artifact_path = None
    if hard_gate_result is not None:
        try:
            artifact_path = _persist_shadow_observation(
                request=request,
                usuario=usuario,
                laudo=laudo,
                hard_gate_result=hard_gate_result,
                texto_resposta=texto_resposta,
            )
        except Exception:
            logger.debug(
                "Falha ao persistir evidencia duravel do hard gate documental via stream.",
                exc_info=True,
            )
            request.state.v2_report_finalize_stream_shadow_evidence_error = (
                "report_finalize_stream_durable_evidence_failed"
            )

    request.state.v2_report_finalize_stream_shadow_observation = {
        **_build_shadow_scope_payload(
            request=request,
            usuario=usuario,
            laudo=laudo,
            scope_enabled=shadow_scope_enabled,
        ),
        "artifact_path": artifact_path,
        "functional_outcome": "stream_finalize_completed_shadow_only",
        "response_status_code": 200,
        "response_media_type": "text/event-stream",
        "sse_preserved": True,
        "hard_gate_observed": hard_gate_result is not None,
        "did_block": bool(getattr(getattr(hard_gate_result, "decision", None), "did_block", False)),
    }

    async def gerador_envio():
        yield evento_sse(
            {
                "laudo_id": laudo.id,
                "laudo_card": serializar_card_laudo(banco, laudo),
            }
        )
        yield evento_sse({"texto": texto_resposta})
        yield "data: [FIM]\n\n"

    return StreamingResponse(
        gerador_envio(),
        media_type="text/event-stream",
        headers=headers,
    )


__all__ = [
    "processar_finalizacao_stream_documental",
    "report_finalize_stream_shadow_scope_enabled",
]
