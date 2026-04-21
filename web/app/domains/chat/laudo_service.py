"""Serviços neutros do ciclo de laudo do portal inspetor."""

from __future__ import annotations

from urllib.parse import urlsplit
import uuid
from typing import Any, Literal, TypeAlias, cast

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.chat.app_context import logger
from app.domains.chat.auth_mobile_support import obter_contexto_preferencia_modo_entrada_usuario
from app.domains.chat.catalog_pdf_templates import (
    capture_catalog_snapshot_for_laudo,
    materialize_catalog_payload_for_laudo,
)
from app.domains.chat.chat_runtime import (
    MODO_DETALHADO,
    resolver_modo_entrada_caso,
)
from app.domains.chat.core_helpers import agora_utc
from app.domains.chat.gate_helpers import (
    avaliar_gate_qualidade_laudo,
    normalize_human_override_case_key,
)
from app.domains.chat.ia_runtime import obter_cliente_ia_ativo
from app.domains.chat.laudo_access_helpers import obter_laudo_do_inspetor
from app.domains.chat.laudo_state_helpers import (
    aplicar_finalizacao_inspetor_ao_laudo,
    aplicar_reabertura_manual_ao_laudo,
    laudo_permite_edicao_inspetor,
    laudo_permite_transicao_finalizacao_inspetor,
    laudo_permite_reabrir,
    laudo_tem_interacao,
    obter_contexto_modo_entrada_laudo,
    obter_guided_inspection_draft_laudo,
    resolver_alvo_reabertura_manual_laudo,
    serializar_card_laudo,
)
from app.domains.chat.mobile_ai_preferences import limpar_historico_visivel_chat
from app.domains.chat.schemas import GuidedInspectionDraftPayload
from app.domains.chat.limits_helpers import garantir_limite_laudos
from app.domains.chat.normalization import (
    nome_template_humano,
    resolver_familia_padrao_template,
)
from app.domains.chat.report_pack_helpers import (
    atualizar_final_validation_mode_report_pack,
    atualizar_report_pack_draft_laudo,
    build_pre_laudo_summary,
    obter_dados_formulario_candidate_report_pack,
    obter_pre_laudo_outline_report_pack,
    obter_report_pack_draft_laudo,
)
from app.domains.chat.session_helpers import (
    aplicar_contexto_laudo_selecionado,
    definir_contexto_inicial_laudo_sessao,
    estado_relatorio_sanitizado,
    obter_contexto_inicial_laudo_sessao,
)
from app.domains.chat.template_governance import (
    apply_template_governance_to_laudo,
    reaffirm_case_bound_template_governance,
    resolve_guided_template_governance,
)
from app.domains.chat.templates_ai import obter_schema_template_ia
from app.v2.adapters.inspector_status import adapt_inspector_case_view_projection_to_legacy_status
from app.v2.acl import (
    is_mobile_review_command_allowed,
)
from app.v2.case_runtime import (
    build_technical_case_context_bundle,
    build_legacy_case_status_payload_from_laudo,
    build_technical_case_runtime_bundle,
)
from app.v2.contracts.inspector_document import build_inspector_document_view_projection
from app.v2.contracts.projections import build_inspector_case_view_projection
from app.v2.document import (
    build_document_hard_gate_block_detail,
    build_document_hard_gate_decision,
    build_document_hard_gate_enforcement_result,
    build_document_soft_gate_route_context,
    build_document_soft_gate_trace,
    record_document_hard_gate_result,
    record_document_soft_gate_trace,
)
from app.v2.report_pack_rollout_metrics import record_report_pack_finalization_observation
from app.v2.runtime import actor_role_from_user
from app.v2.runtime import v2_case_core_acl_enabled
from app.v2.runtime import v2_document_facade_enabled
from app.v2.runtime import v2_document_hard_gate_enabled
from app.v2.runtime import v2_document_shadow_enabled
from app.v2.runtime import v2_document_soft_gate_enabled
from app.v2.runtime import v2_inspector_projection_enabled
from app.v2.runtime import v2_policy_engine_enabled
from app.v2.runtime import v2_provenance_enabled
from app.v2.provenance import (
    build_inspector_content_origin_summary,
    load_message_origin_counters,
)
from app.v2.shadow import run_inspector_case_status_shadow
from app.shared.database import (
    EvidenceMesaStatus,
    EvidenceOperationalStatus,
    Laudo,
    MensagemLaudo,
    OperationalIrregularity,
    OperationalIrregularityStatus,
    OperationalSeverity,
    StatusRevisao,
    TipoMensagem,
    Usuario,
    commit_ou_rollback_operacional,
)
from app.shared.inspection_history import (
    build_clone_from_last_inspection_seed,
    build_human_override_summary,
    build_inspection_history_summary,
)
from app.shared.official_issue_package import build_official_issue_summary
from app.shared.tenant_entitlement_guard import (
    ensure_tenant_capability_for_user,
    tenant_access_policy_for_user,
)
from app.shared.operational_memory import (
    registrar_evento_operacional,
    registrar_validacao_evidencia,
)
from app.shared.operational_memory_contracts import (
    EvidenceValidationInput,
    OperationalEventInput,
)
from app.shared.operational_memory_hooks import (
    find_replayable_approved_case_snapshot_for_laudo,
    record_approved_case_snapshot_for_laudo,
    record_quality_gate_validations,
    record_return_to_inspector_irregularity,
    resolve_open_return_to_inspector_irregularities,
)
from app.shared.public_verification import build_public_verification_payload
from app.shared.tenant_report_catalog import resolve_tenant_template_request

PayloadJson: TypeAlias = dict[str, Any]
ResultadoJson: TypeAlias = tuple[PayloadJson, int]

RESPOSTA_LAUDO_NAO_ENCONTRADO = {404: {"description": "Laudo não encontrado."}}
RESPOSTA_GATE_QUALIDADE_REPROVADO = {
    422: {
        "description": "Gate de qualidade reprovado.",
        "content": {"application/json": {"schema": {"type": "object"}}},
    }
}
RESPOSTA_DOCUMENT_HARD_GATE_BLOQUEADO = {
    422: {
        "description": "Hard gate documental controlado bloqueou a operacao.",
        "content": {"application/json": {"schema": {"type": "object"}}},
    }
}
_QUALITY_GATE_OVERRIDE_REASON_MIN_LENGTH = 12
_QUALITY_GATE_OVERRIDE_BLOCK_KEY = "quality_gate_override"


def _alinhar_status_canonico_nr35_persistido(laudo: Laudo) -> None:
    family_key = str(getattr(laudo, "catalog_family_key", "") or "").strip().lower()
    if family_key not in {"nr35_inspecao_linha_de_vida", "nr35_inspecao_ponto_ancoragem"}:
        return

    payload = getattr(laudo, "dados_formulario", None)
    if not isinstance(payload, dict):
        return
    conclusao = payload.get("conclusao")
    if not isinstance(conclusao, dict):
        return

    status_operacional = str(conclusao.get("status_operacional") or "").strip().lower()
    status_map = {
        "bloqueio": "bloqueio",
        "ajuste": "ajuste",
        "conforme": "conforme",
        "liberado": "conforme",
        "avaliacao_complementar": "pendente",
    }
    status_canonico = status_map.get(status_operacional)
    if not status_canonico:
        return

    conclusao["status"] = status_canonico
    if not str(conclusao.get("status_final") or "").strip():
        conclusao["status_final"] = status_canonico


def _aplicar_binding_familia_padrao_laudo(
    *,
    laudo: Laudo,
    tipo_template: str | None,
    force_update: bool = False,
) -> None:
    binding = resolver_familia_padrao_template(tipo_template)
    family_key = str(binding.get("family_key") or "").strip() or None
    if family_key is None:
        return
    if getattr(laudo, "catalog_selection_token", None) and not force_update:
        return
    if force_update or not str(getattr(laudo, "catalog_family_key", "") or "").strip():
        laudo.catalog_family_key = family_key
    family_label = str(binding.get("family_label") or "").strip() or None
    if family_label and (
        force_update or not str(getattr(laudo, "catalog_family_label", "") or "").strip()
    ):
        laudo.catalog_family_label = family_label


async def _resolver_tipo_template_bruto(
    *,
    request: Request,
    tipo_template: str | None,
    tipotemplate: str | None,
) -> str:
    tipo_template_bruto = (tipo_template or tipotemplate or "").strip().lower()

    if not tipo_template_bruto:
        payload_json: PayloadJson = {}
        try:
            payload_json = await request.json()
        except Exception:
            payload_json = {}

        tipo_template_bruto = str(
            payload_json.get("tipo_template")
            or payload_json.get("tipotemplate")
            or payload_json.get("template")
            or ""
        ).strip().lower()

    return tipo_template_bruto or "padrao"


async def _resolver_entry_mode_preference_bruta(
    *,
    request: Request,
    entry_mode_preference: str | None,
) -> str | None:
    valor_bruto = str(entry_mode_preference or "").strip().lower()
    if valor_bruto:
        return valor_bruto

    payload_json: PayloadJson = {}
    try:
        payload_json = await request.json()
    except Exception:
        payload_json = {}

    valor_bruto = str(
        payload_json.get("entry_mode_preference")
        or payload_json.get("entryModePreference")
        or payload_json.get("entry_mode")
        or ""
    ).strip().lower()
    return valor_bruto or None


def _normalizar_texto_contexto_inicial(
    valor: str | None,
    *,
    limite: int,
) -> str:
    texto = " ".join(str(valor or "").strip().split())
    if not texto:
        return ""
    return texto[:limite]


def _construir_dados_formulario_inicial(
    *,
    cliente: str | None,
    unidade: str | None,
    local_inspecao: str | None,
    objetivo: str | None,
    nome_inspecao: str | None,
) -> dict[str, str] | None:
    payload = {
        "cliente": _normalizar_texto_contexto_inicial(cliente, limite=120),
        "unidade": _normalizar_texto_contexto_inicial(unidade, limite=120),
        "local_inspecao": _normalizar_texto_contexto_inicial(local_inspecao, limite=120),
        "objetivo": _normalizar_texto_contexto_inicial(objetivo, limite=600),
        "nome_inspecao": _normalizar_texto_contexto_inicial(nome_inspecao, limite=160),
    }
    dados_filtrados = {chave: valor for chave, valor in payload.items() if valor}
    return dados_filtrados or None


def _request_base_url(request: Request | None) -> str | None:
    if request is None:
        return None
    try:
        raw = str(getattr(request, "base_url", "") or "").strip()
    except Exception:
        raw = ""
    if not raw:
        return None
    parsed = urlsplit(raw)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _review_mode_final_from_report_pack(laudo: Laudo, *, fallback: str | None = None) -> str | None:
    report_pack = getattr(laudo, "report_pack_draft_json", None)
    if isinstance(report_pack, dict):
        quality_gates = report_pack.get("quality_gates")
        if isinstance(quality_gates, dict):
            review_mode = str(quality_gates.get("final_validation_mode") or "").strip()
            if review_mode:
                return review_mode
    return fallback


def _texto_curto_limpo(valor: Any, *, limite: int) -> str:
    texto = " ".join(str(valor or "").strip().split())
    if not texto:
        return ""
    return texto[:limite]


def _bool_request_flag(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    texto = str(valor or "").strip().lower()
    return texto in {"1", "true", "on", "yes", "sim"}


def _lista_request_textos(valor: Any) -> list[str]:
    if isinstance(valor, list):
        candidatos = valor
    else:
        candidatos = str(valor or "").split(",")

    vistos: set[str] = set()
    resultado: list[str] = []
    for item in candidatos:
        texto = _texto_curto_limpo(item, limite=160).lower()
        if not texto or texto in vistos:
            continue
        vistos.add(texto)
        resultado.append(texto)
    return resultado


def _lista_request_override_cases(valor: Any) -> list[str]:
    vistos: set[str] = set()
    resultado: list[str] = []
    for item in _lista_request_textos(valor):
        chave = normalize_human_override_case_key(item)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(chave)
    return resultado


async def _ler_payload_request_tolerante(request: Request) -> dict[str, Any]:
    cache = getattr(request.state, "_tariel_request_payload_cache", None)
    if isinstance(cache, dict):
        return cache

    payload: dict[str, Any] = {}
    try:
        form = await request.form()
        if form:
            for chave, valor in form.multi_items():
                if chave in payload:
                    atual = payload[chave]
                    if isinstance(atual, list):
                        atual.append(valor)
                    else:
                        payload[chave] = [atual, valor]
                else:
                    payload[chave] = valor
    except Exception:
        payload = {}

    if not payload:
        try:
            json_payload = await request.json()
        except Exception:
            json_payload = {}
        if isinstance(json_payload, dict):
            payload = dict(json_payload)

    request.state._tariel_request_payload_cache = payload
    return payload


async def _resolver_intencao_override_gate_qualidade(
    request: Request,
) -> dict[str, Any]:
    payload = await _ler_payload_request_tolerante(request)
    requested = _bool_request_flag(
        payload.get("quality_gate_override")
        or payload.get("human_override_quality_gate")
        or payload.get("override_gate_qualidade")
    )
    return {
        "requested": requested,
        "reason": _texto_curto_limpo(
            payload.get("quality_gate_override_reason")
            or payload.get("human_override_reason")
            or payload.get("override_gate_qualidade_justificativa"),
            limite=2000,
        ),
        "requested_cases": _lista_request_override_cases(
            payload.get("quality_gate_override_cases")
            or payload.get("human_override_cases")
        ),
    }


def _registrar_override_humano_gate_qualidade(
    *,
    banco: Session,
    laudo: Laudo,
    usuario: Usuario,
    final_validation_mode: str,
    gate_override_request: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(gate_override_request, dict):
        return None

    reason = _texto_curto_limpo(gate_override_request.get("reason"), limite=2000)
    if not reason:
        return None

    policy = (
        dict(gate_override_request.get("human_override_policy") or {})
        if isinstance(gate_override_request.get("human_override_policy"), dict)
        else {}
    )
    now = agora_utc()
    actor_user_id = int(getattr(usuario, "id", 0) or 0) or None
    actor_name = _texto_curto_limpo(
        getattr(usuario, "nome_completo", None) or getattr(usuario, "nome", None),
        limite=160,
    )
    matched_cases = _lista_request_override_cases(
        gate_override_request.get("requested_cases")
        or policy.get("matched_override_cases")
    )
    matched_case_labels = [
        _texto_curto_limpo(item, limite=160)
        for item in list(policy.get("matched_override_case_labels") or [])
        if _texto_curto_limpo(item, limite=160)
    ]
    overrideable_item_ids = [
        _texto_curto_limpo(item.get("id"), limite=120)
        for item in list(policy.get("overrideable_items") or [])
        if isinstance(item, dict) and _texto_curto_limpo(item.get("id"), limite=120)
    ]
    entry = {
        "scope": "quality_gate",
        "applied_at": now.isoformat(),
        "actor_user_id": actor_user_id,
        "actor_name": actor_name or None,
        "reason": reason,
        "matched_override_cases": matched_cases,
        "matched_override_case_labels": matched_case_labels,
        "overrideable_item_ids": overrideable_item_ids,
        "final_validation_mode": _texto_curto_limpo(final_validation_mode, limite=80),
        "responsibility_notice": _texto_curto_limpo(
            policy.get("responsibility_notice")
            or "A responsabilidade final permanece com a validação e assinatura humana.",
            limite=400,
        ),
    }

    draft = dict(obter_report_pack_draft_laudo(laudo) or {})
    quality_gates = dict(draft.get("quality_gates") or {})
    history = [
        dict(item)
        for item in list(quality_gates.get("human_override_history") or [])
        if isinstance(item, dict)
    ]
    history.append(entry)
    history = history[-5:]
    quality_gates["human_override"] = entry
    quality_gates["human_override_history"] = history
    quality_gates["human_override_count"] = len(history)
    draft["quality_gates"] = quality_gates
    laudo.report_pack_draft_json = draft

    try:
        registrar_evento_operacional(
            banco,
            OperationalEventInput(
                laudo_id=int(laudo.id),
                event_type="evidence_conclusion_conflict",
                event_source="inspetor",
                severity="warning",
                actor_user_id=actor_user_id,
                block_key=_QUALITY_GATE_OVERRIDE_BLOCK_KEY,
                event_metadata=entry,
            ),
        )
    except Exception:
        logger.warning(
            "Falha ao registrar trilha operacional do override humano do gate | laudo_id=%s",
            int(getattr(laudo, "id", 0) or 0),
            exc_info=True,
        )

    return entry


def _build_legacy_case_status_payload_for_document_mutation(
    *,
    banco: Session,
    laudo: Laudo,
) -> dict[str, Any]:
    return build_legacy_case_status_payload_from_laudo(
        banco=banco,
        laudo=laudo,
        include_entry_mode_context=True,
    )


def _build_case_lifecycle_response_fields(
    contexto: dict[str, Any] | None,
) -> dict[str, Any]:
    contexto_resolvido = contexto if isinstance(contexto, dict) else {}
    return {
        "case_lifecycle_status": contexto_resolvido.get("case_lifecycle_status"),
        "case_workflow_mode": contexto_resolvido.get("case_workflow_mode"),
        "active_owner_role": contexto_resolvido.get("active_owner_role"),
        "allowed_next_lifecycle_statuses": list(
            contexto_resolvido.get("allowed_next_lifecycle_statuses") or []
        ),
        "allowed_lifecycle_transitions": list(
            contexto_resolvido.get("allowed_lifecycle_transitions") or []
        ),
        "allowed_surface_actions": list(
            contexto_resolvido.get("allowed_surface_actions") or []
        ),
    }


def _avaliar_gate_documental_finalizacao(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
    laudo: Laudo,
    route_name: str = "finalizar_relatorio_resposta",
    route_path: str | None = None,
    source_channel: str = "web_app",
    operation_kind: Literal["report_finalize", "report_finalize_stream"] = "report_finalize",
    legacy_pipeline_name: str = "legacy_report_finalize",
) -> tuple[Any | None, Any | None]:
    soft_gate_enabled = v2_document_soft_gate_enabled()
    hard_gate_enabled = v2_document_hard_gate_enabled()
    if not soft_gate_enabled and not hard_gate_enabled:
        return None, None

    provenance_summary = None
    try:
        message_counters = load_message_origin_counters(
            banco,
            laudo_id=int(laudo.id),
        )
        provenance_summary = build_inspector_content_origin_summary(
            laudo=laudo,
            message_counters=message_counters,
            has_active_report=True,
        )
        request.state.v2_content_provenance_summary = provenance_summary.model_dump(mode="python")
    except Exception:
        logger.debug("Falha ao derivar provenance da finalizacao documental.", exc_info=True)

    runtime_bundle = build_technical_case_runtime_bundle(
        request=request,
        banco=banco,
        usuario=usuario,
        laudo=laudo,
        legacy_payload=_build_legacy_case_status_payload_for_document_mutation(
            banco=banco,
            laudo=laudo,
        ),
        source_channel=source_channel,
        template_key=getattr(laudo, "tipo_template", None),
        family_key=getattr(laudo, "catalog_family_key", None),
        variant_key=getattr(laudo, "catalog_variant_key", None),
        laudo_type=getattr(laudo, "tipo_template", None),
        document_type=getattr(laudo, "tipo_template", None),
        provenance_summary=provenance_summary,
        current_review_status=getattr(laudo, "status_revisao", None),
        has_form_data=bool(getattr(laudo, "dados_formulario", None)),
        has_ai_draft=bool(str(getattr(laudo, "parecer_ia", "") or "").strip()),
        report_pack_draft=getattr(laudo, "report_pack_draft_json", None),
    )
    case_snapshot = runtime_bundle.case_snapshot
    document_facade = runtime_bundle.document_facade
    if case_snapshot is None or document_facade is None:
        return None, None

    soft_gate_trace = build_document_soft_gate_trace(
        case_snapshot=case_snapshot,
        document_facade=document_facade,
        route_context=build_document_soft_gate_route_context(
            route_name=route_name,
            route_path=str(
                route_path
                or request.scope.get("path")
                or "/app/api/laudo/{laudo_id}/finalizar"
            ),
            http_method=str(request.method or "POST"),
            source_channel=source_channel,
            operation_kind=operation_kind,
            side_effect_free=False,
            legacy_pipeline_name=legacy_pipeline_name,
        ),
        correlation_id=case_snapshot.correlation_id,
        request_id=(
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or case_snapshot.correlation_id
        ),
    )
    request.state.v2_document_soft_gate_decision = soft_gate_trace.decision.model_dump(mode="python")
    request.state.v2_document_soft_gate_trace = soft_gate_trace.model_dump(mode="python")
    if soft_gate_enabled:
        record_document_soft_gate_trace(soft_gate_trace)

    hard_gate_result = None
    if hard_gate_enabled:
        hard_gate_result = build_document_hard_gate_enforcement_result(
            decision=build_document_hard_gate_decision(
                soft_gate_trace=soft_gate_trace,
                remote_host=getattr(getattr(request, "client", None), "host", None),
            )
        )
        request.state.v2_document_hard_gate_decision = hard_gate_result.decision.model_dump(mode="python")
        request.state.v2_document_hard_gate_enforcement = hard_gate_result.model_dump(mode="python")
        record_document_hard_gate_result(hard_gate_result)

    return soft_gate_trace, hard_gate_result


async def obter_status_relatorio_resposta(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
) -> ResultadoJson:
    payload = estado_relatorio_sanitizado(
        request,
        banco,
        usuario,
        mutar_sessao=False,
    )

    laudo_card = None
    laudo = None
    laudo_id = payload.get("laudo_id")
    if laudo_id:
        laudo = obter_laudo_do_inspetor(banco, int(laudo_id), usuario)
        atualizar_report_pack_draft_laudo(banco=banco, laudo=laudo)
        if laudo_tem_interacao(banco, laudo.id) or laudo.status_revisao != StatusRevisao.RASCUNHO.value:
            laudo_card = serializar_card_laudo(banco, laudo)

    resposta = {
        **payload,
        "tenant_access_policy": tenant_access_policy_for_user(usuario),
        "laudo_card": laudo_card,
        "guided_inspection_draft": obter_guided_inspection_draft_laudo(laudo),
        "report_pack_draft": obter_report_pack_draft_laudo(laudo),
        "pre_laudo_summary": build_pre_laudo_summary(
            obter_pre_laudo_outline_report_pack(obter_report_pack_draft_laudo(laudo))
        ),
        "public_verification": (
            build_public_verification_payload(
                laudo=laudo,
                base_url=_request_base_url(request),
            )
            if laudo is not None
            else None
        ),
        "emissao_oficial": (
            build_official_issue_summary(
                banco,
                laudo=laudo,
            )
            if laudo is not None
            else None
        ),
    }
    case_snapshot = None
    provenance_summary = None
    policy_decision = None
    document_facade = None
    runtime_bundle = None
    if v2_provenance_enabled():
        try:
            message_counters = load_message_origin_counters(
                banco,
                laudo_id=int(laudo.id) if laudo is not None and getattr(laudo, "id", None) else None,
            )
            provenance_summary = build_inspector_content_origin_summary(
                laudo=laudo,
                message_counters=message_counters,
                has_active_report=bool(resposta.get("laudo_id")),
            )
        except Exception:
            logger.debug("Falha ao derivar provenance do inspetor no V2.", exc_info=True)
            provenance_summary = build_inspector_content_origin_summary(
                laudo=laudo,
                message_counters=None,
                has_active_report=bool(resposta.get("laudo_id")),
            )
        request.state.v2_content_provenance_summary = provenance_summary.model_dump(mode="python")

    if (
        v2_case_core_acl_enabled()
        or v2_inspector_projection_enabled()
        or v2_policy_engine_enabled()
        or v2_document_facade_enabled()
    ):
        runtime_bundle = build_technical_case_runtime_bundle(
            request=request,
            banco=banco,
            usuario=usuario,
            laudo=laudo,
            legacy_payload=resposta,
            source_channel="web_app",
            template_key=getattr(laudo, "tipo_template", None),
            family_key=getattr(laudo, "catalog_family_key", None),
            variant_key=getattr(laudo, "catalog_variant_key", None),
            laudo_type=getattr(laudo, "tipo_template", None),
            document_type=getattr(laudo, "tipo_template", None),
            provenance_summary=provenance_summary,
            current_review_status=getattr(laudo, "status_revisao", None),
            has_form_data=bool(getattr(laudo, "dados_formulario", None)),
            has_ai_draft=bool(str(getattr(laudo, "parecer_ia", "") or "").strip()),
            report_pack_draft=getattr(laudo, "report_pack_draft_json", None),
            include_full_snapshot=bool(laudo is not None and getattr(laudo, "id", None)),
            include_policy_decision=bool(v2_policy_engine_enabled()),
            include_document_facade=bool(v2_document_facade_enabled()),
            attach_document_shadow=bool(v2_document_shadow_enabled()),
            allow_partial_failures=True,
        )
        case_snapshot = runtime_bundle.case_snapshot

    if v2_policy_engine_enabled() and case_snapshot is not None:
        policy_decision = runtime_bundle.policy_decision if runtime_bundle is not None else None

    if v2_document_facade_enabled() and case_snapshot is not None:
        document_facade = runtime_bundle.document_facade if runtime_bundle is not None else None

    actor_role = actor_role_from_user(usuario)
    if document_facade is not None and case_snapshot is not None:
        try:
            inspector_document_projection = build_inspector_document_view_projection(
                case_snapshot=case_snapshot,
                document_facade=document_facade,
                actor_id=usuario.id,
                actor_role=actor_role,
                source_channel="web_app",
            )
            request.state.v2_inspector_document_projection_result = {
                "projection": inspector_document_projection.model_dump(mode="python"),
                "document_facade": document_facade.model_dump(mode="python"),
                "document_shadow": (
                    document_facade.legacy_pipeline_shadow.model_dump(mode="python")
                    if document_facade.legacy_pipeline_shadow is not None
                    else None
                ),
            }
        except Exception:
            logger.debug(
                "Falha ao derivar projecao documental do inspetor no V2.",
                exc_info=True,
            )

    resposta_publica = resposta
    if v2_inspector_projection_enabled() and case_snapshot is not None:
        inspector_projection = build_inspector_case_view_projection(
            case_snapshot=case_snapshot,
            actor_id=usuario.id,
            actor_role=actor_role,
            source_channel="web_app",
            allows_edit=bool(resposta.get("permite_edicao")),
            has_interaction=bool(resposta.get("tem_interacao")),
            report_types=dict(resposta.get("tipos_relatorio") or {}),
            laudo_card=resposta.get("laudo_card"),
            public_verification=resposta.get("public_verification"),
            emissao_oficial=resposta.get("emissao_oficial"),
            policy_decision=policy_decision,
            document_facade=document_facade,
        )
        adapted = adapt_inspector_case_view_projection_to_legacy_status(
            projection=inspector_projection,
            expected_legacy_payload=resposta,
        )
        request.state.v2_inspector_projection_result = {
            "projection": inspector_projection.model_dump(mode="python"),
            "compatible": adapted.compatible,
            "divergences": adapted.divergences,
            "used_projection": adapted.compatible,
            "provenance": (
                provenance_summary.model_dump(mode="python")
                if provenance_summary is not None
                else None
            ),
            "policy": (
                policy_decision.summary.model_dump(mode="python")
                if policy_decision is not None
                else None
            ),
            "document_facade": (
                document_facade.model_dump(mode="python")
                if document_facade is not None
                else None
            ),
            "document_shadow": (
                document_facade.legacy_pipeline_shadow.model_dump(mode="python")
                if document_facade is not None and document_facade.legacy_pipeline_shadow is not None
                else None
            ),
        }
        if adapted.compatible:
            resposta_publica = {
                **adapted.payload,
                "status_visual_label": resposta.get("status_visual_label"),
                "tenant_access_policy": resposta.get("tenant_access_policy"),
                "tipo_template_options": resposta.get("tipo_template_options"),
                "catalog_governed_mode": resposta.get("catalog_governed_mode"),
                "catalog_state": resposta.get("catalog_state"),
                "catalog_permissions": resposta.get("catalog_permissions"),
                "entry_mode_preference": resposta.get("entry_mode_preference"),
                "entry_mode_effective": resposta.get("entry_mode_effective"),
                "entry_mode_reason": resposta.get("entry_mode_reason"),
                "guided_inspection_draft": resposta.get("guided_inspection_draft"),
                "report_pack_draft": resposta.get("report_pack_draft"),
                "pre_laudo_summary": resposta.get("pre_laudo_summary"),
            }
        else:
            logger.debug(
                "V2 inspector projection divergiu | divergences=%s",
                ",".join(adapted.divergences),
            )

    run_inspector_case_status_shadow(
        request=request,
        usuario=usuario,
        legacy_payload=resposta_publica,
        case_snapshot=case_snapshot,
    )

    return (resposta_publica, 200)


def salvar_guided_inspection_draft_mobile_resposta(
    *,
    laudo_id: int,
    guided_inspection_draft: GuidedInspectionDraftPayload | None,
    usuario: Usuario,
    banco: Session,
) -> ResultadoJson:
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    if laudo.status_revisao != StatusRevisao.RASCUNHO.value:
        raise HTTPException(
            status_code=400,
            detail="Somente laudos em rascunho aceitam persistencia do draft guiado.",
        )

    if guided_inspection_draft is not None:
        resolucao_template = resolve_guided_template_governance(
            banco,
            usuario=usuario,
            template_key=guided_inspection_draft.template_key,
            laudo=laudo,
        )
        laudo.guided_inspection_draft_json = guided_inspection_draft.model_dump(mode="python")
        apply_template_governance_to_laudo(
            laudo=laudo,
            resolucao_template=resolucao_template,
        )
        capture_catalog_snapshot_for_laudo(
            banco=banco,
            laudo=laudo,
        )
    else:
        laudo.guided_inspection_draft_json = None
    atualizar_report_pack_draft_laudo(banco=banco, laudo=laudo)
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao salvar draft guiado do laudo mobile.",
    )
    banco.refresh(laudo)

    return (
        {
            "ok": True,
            "laudo_id": int(laudo.id),
            "guided_inspection_draft": obter_guided_inspection_draft_laudo(laudo),
            "report_pack_draft": obter_report_pack_draft_laudo(laudo),
            "pre_laudo_summary": build_pre_laudo_summary(
                obter_pre_laudo_outline_report_pack(obter_report_pack_draft_laudo(laudo))
            ),
        },
        200,
    )


async def iniciar_relatorio_resposta(
    *,
    request: Request,
    tipo_template: str | None,
    tipotemplate: str | None,
    cliente: str | None,
    unidade: str | None,
    local_inspecao: str | None,
    objetivo: str | None,
    nome_inspecao: str | None,
    entry_mode_preference: str | None,
    usuario: Usuario,
    banco: Session,
) -> ResultadoJson:
    ensure_tenant_capability_for_user(
        usuario,
        capability="inspector_case_create",
    )
    tipo_template_bruto = await _resolver_tipo_template_bruto(
        request=request,
        tipo_template=tipo_template,
        tipotemplate=tipotemplate,
    )
    try:
        resolucao_template = resolve_tenant_template_request(
            banco,
            empresa_id=int(usuario.empresa_id),
            requested_value=tipo_template_bruto,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    tipo_template_normalizado = str(resolucao_template["runtime_template_code"] or "padrao").strip().lower() or "padrao"
    family_binding = resolver_familia_padrao_template(tipo_template_normalizado)
    family_key_resolvida = (
        str(resolucao_template.get("family_key") or "").strip()
        or str(family_binding.get("family_key") or "").strip()
        or None
    )
    family_label_resolvida = (
        str(resolucao_template.get("family_label") or "").strip()
        or str(family_binding.get("family_label") or "").strip()
        or None
    )
    entry_mode_preference_bruta = await _resolver_entry_mode_preference_bruta(
        request=request,
        entry_mode_preference=entry_mode_preference,
    )
    contexto_preferencia_modo_entrada = obter_contexto_preferencia_modo_entrada_usuario(
        banco,
        usuario_id=int(usuario.id),
    )
    try:
        entry_mode_decision = resolver_modo_entrada_caso(
            requested_preference=entry_mode_preference_bruta,
            existing_preference=contexto_preferencia_modo_entrada.entry_mode_preference,
            last_case_mode=(
                contexto_preferencia_modo_entrada.last_case_mode
                if contexto_preferencia_modo_entrada.remember_last_case_mode
                else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    garantir_limite_laudos(usuario, banco)

    dados_formulario_inicial = _construir_dados_formulario_inicial(
        cliente=cliente,
        unidade=unidade,
        local_inspecao=local_inspecao,
        objetivo=objetivo,
        nome_inspecao=nome_inspecao,
    )
    clone_from_last_inspection = build_clone_from_last_inspection_seed(
        banco,
        empresa_id=int(usuario.empresa_id),
        family_key=str(family_key_resolvida or tipo_template_normalizado),
        current_payload=dados_formulario_inicial,
    )
    prefill_data = (
        clone_from_last_inspection.get("prefill_data")
        if isinstance(clone_from_last_inspection, dict)
        else None
    )
    if isinstance(prefill_data, dict):
        dados_formulario_inicial = dict(prefill_data)
    setor_industrial = (
        str((dados_formulario_inicial or {}).get("local_inspecao") or "").strip()
        or str((dados_formulario_inicial or {}).get("nome_inspecao") or "").strip()
        or nome_template_humano(tipo_template_normalizado)
    )

    laudo = Laudo(
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        tipo_template=tipo_template_normalizado,
        catalog_selection_token=resolucao_template.get("selection_token"),
        catalog_family_key=family_key_resolvida,
        catalog_family_label=family_label_resolvida,
        catalog_variant_key=resolucao_template.get("variant_key"),
        catalog_variant_label=resolucao_template.get("variant_label"),
        status_revisao=StatusRevisao.RASCUNHO.value,
        setor_industrial=setor_industrial[:100],
        primeira_mensagem=None,
        modo_resposta=MODO_DETALHADO,
        codigo_hash=uuid.uuid4().hex,
        is_deep_research=False,
        entry_mode_preference=entry_mode_decision.preference,
        entry_mode_effective=entry_mode_decision.effective,
        entry_mode_reason=entry_mode_decision.reason,
    )

    banco.add(laudo)
    banco.flush()
    capture_catalog_snapshot_for_laudo(
        banco=banco,
        laudo=laudo,
    )
    banco.flush()
    banco.refresh(laudo)
    # O laudo precisa estar committed antes do próximo request do inspetor
    # (ex.: widget/canal da mesa) para evitar 404 por registro ainda não visível.
    banco.commit()
    banco.refresh(laudo)

    definir_contexto_inicial_laudo_sessao(
        request,
        laudo_id=laudo.id,
        contexto=dados_formulario_inicial,
    )
    contexto = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)

    logger.info(
        "Relatório iniciado | usuario_id=%s | tipo=%s | family_key=%s | variant_key=%s | laudo_id=%s",
        usuario.id,
        tipo_template_normalizado,
        resolucao_template.get("family_key"),
        resolucao_template.get("variant_key"),
        laudo.id,
    )
    public_verification = build_public_verification_payload(
        laudo=laudo,
        base_url=_request_base_url(request),
    )

    return (
        {
            "success": True,
            "laudo_id": laudo.id,
            "hash": laudo.codigo_hash[-6:],
            "message": f"✅ Inspeção {nome_template_humano(tipo_template_normalizado)} criada. Envie a primeira mensagem para iniciar o laudo.",
            "estado": "sem_relatorio",
            "tipo_template": tipo_template_normalizado,
            "catalog_governed_mode": bool(resolucao_template.get("governed_mode")),
            "catalog_selection_token": resolucao_template.get("selection_token"),
            "catalog_family_key": resolucao_template.get("family_key"),
            "catalog_variant_key": resolucao_template.get("variant_key"),
            "clone_from_last_inspection": clone_from_last_inspection,
            "public_verification": public_verification,
            **_build_case_lifecycle_response_fields(contexto),
            **obter_contexto_modo_entrada_laudo(laudo),
            "laudo_card": serializar_card_laudo(banco, laudo),
        },
        200,
    )


_OPEN_RETURN_TO_INSPECTOR_STATUSES = (
    OperationalIrregularityStatus.OPEN.value,
    OperationalIrregularityStatus.ACKNOWLEDGED.value,
)
_MOBILE_APPROVAL_REVIEW_MODES = {"mobile_autonomous", "mobile_review_allowed"}
_REOPEN_ISSUED_DOCUMENT_POLICIES = {"keep_visible", "hide_from_case"}


def _resolver_review_mode_final(
    *,
    request: Request,
    laudo: Laudo,
) -> str:
    policy_summary = getattr(request.state, "v2_policy_decision_summary", None)
    if not isinstance(policy_summary, dict):
        policy_summary = {}
    return str(
        policy_summary.get("review_mode")
        or ((getattr(laudo, "report_pack_draft_json", None) or {}).get("quality_gates") or {}).get(
            "final_validation_mode"
        )
        or "mesa_required"
    ).strip().lower()


def _normalize_reopen_issued_document_policy(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _REOPEN_ISSUED_DOCUMENT_POLICIES:
        return normalized
    return "keep_visible"


def _registrar_documento_emitido_reaberto(
    *,
    laudo: Laudo,
    actor_user_id: int | None,
    issued_document_policy: str,
    previous_issued_document_name: str | None,
) -> bool:
    previous_name = str(previous_issued_document_name or "").strip()
    if not previous_name:
        return False
    draft = dict(obter_report_pack_draft_laudo(laudo) or {})
    history = list(draft.get("reopen_issued_document_history") or [])
    history.append(
        {
            "reopened_at": agora_utc().isoformat(),
            "actor_user_id": actor_user_id,
            "source_kind": "issued_pdf_previous_cycle",
            "file_name": previous_name,
            "issued_document_policy": issued_document_policy,
            "visible_in_active_case": issued_document_policy == "keep_visible",
            "internal_learning_candidate": True,
        }
    )
    draft["reopen_issued_document_history"] = history[-20:]
    draft["last_reopen_issued_document_policy"] = issued_document_policy
    laudo.report_pack_draft_json = draft
    return True


def _garantir_comando_revisao_mobile_permitido(
    *,
    request: Request,
    usuario: Usuario,
    banco: Session,
    laudo: Laudo,
    command: str,
    block_key: str | None = None,
) -> None:
    legacy_payload = _build_legacy_case_status_payload_for_document_mutation(
        banco=banco,
        laudo=laudo,
    )
    runtime_bundle = build_technical_case_context_bundle(
        banco=banco,
        usuario=usuario,
        laudo=laudo,
        legacy_payload=legacy_payload,
        source_channel="mobile_review_command",
        include_policy_decision=False,
        include_document_facade=False,
    )
    case_snapshot = runtime_bundle.case_snapshot
    assert case_snapshot is not None
    review_mode_from_policy = getattr(request.state, "v2_policy_decision_summary", None)
    if not isinstance(review_mode_from_policy, dict):
        review_mode_from_policy = {}
    report_pack_quality_gates = (
        (getattr(laudo, "report_pack_draft_json", None) or {}).get("quality_gates") or {}
    )
    review_mode = str(
        review_mode_from_policy.get("review_mode")
        or report_pack_quality_gates.get("final_validation_mode")
        or ""
    ).strip().lower() or None
    allows_edit = laudo_permite_edicao_inspetor(laudo)
    allowed = []
    for candidate in (
        "enviar_para_mesa",
        "aprovar_no_mobile",
        "devolver_no_mobile",
        "reabrir_bloco",
    ):
        if is_mobile_review_command_allowed(
            lifecycle_status=case_snapshot.case_lifecycle_status,
            allows_edit=allows_edit,
            review_mode=review_mode,
            command=candidate,
            has_block_review_items=bool(str(block_key or "").strip()),
            allow_approval_when_review_mode_unresolved=review_mode is None,
        ):
            allowed.append(candidate)
    if command in allowed:
        return
    raise HTTPException(
        status_code=422,
        detail={
            "code": "mobile_review_command_not_allowed",
            "message": "O comando solicitado nao esta liberado para o estado atual do caso.",
            "command": command,
            "case_lifecycle_status": case_snapshot.case_lifecycle_status,
            "case_workflow_mode": case_snapshot.workflow_mode,
            "active_owner_role": case_snapshot.active_owner_role,
            "review_mode": review_mode or "unresolved",
            "allows_edit": allows_edit,
            "allowed_next_lifecycle_statuses": list(
                case_snapshot.allowed_next_lifecycle_statuses
            ),
            "allowed_lifecycle_transitions": [
                item.model_dump(mode="python")
                for item in case_snapshot.allowed_lifecycle_transitions
            ],
            "allowed_surface_actions": list(case_snapshot.allowed_surface_actions),
            "allowed_commands": allowed,
        },
    )


def _contar_irregularidades_abertas_retorno_inspetor(
    *,
    banco: Session,
    laudo_id: int,
    block_key: str | None = None,
) -> int:
    consulta = (
        select(OperationalIrregularity.id)
        .where(
            OperationalIrregularity.laudo_id == int(laudo_id),
            OperationalIrregularity.irregularity_type.in_(
                ("block_returned_to_inspector", "field_reopened")
            ),
            OperationalIrregularity.status.in_(_OPEN_RETURN_TO_INSPECTOR_STATUSES),
        )
    )
    if block_key:
        consulta = consulta.where(OperationalIrregularity.block_key == str(block_key))
    return len(list(banco.scalars(consulta).all()))


def _garantir_sem_irregularidades_abertas_para_aprovacao(
    *,
    banco: Session,
    laudo_id: int,
) -> None:
    total_abertas = _contar_irregularidades_abertas_retorno_inspetor(
        banco=banco,
        laudo_id=laudo_id,
    )
    if total_abertas <= 0:
        return
    raise HTTPException(
        status_code=422,
        detail={
            "code": "mobile_review_pending_returns",
            "message": "Ainda existem blocos ou pendencias operacionais em refazer no mobile.",
            "open_return_count": total_abertas,
        },
    )


def _sincronizar_validacao_evidencia_revisao_mobile(
    *,
    banco: Session,
    laudo_id: int,
    actor_user_id: int | None,
    evidence_key: str | None,
    summary: str | None,
    reason: str | None,
    required_action: str | None,
    failure_reasons: list[str] | None,
) -> None:
    evidence_key_limpo = str(evidence_key or "").strip()
    if not evidence_key_limpo:
        return
    registrar_validacao_evidencia(
        banco,
        EvidenceValidationInput(
            laudo_id=int(laudo_id),
            evidence_key=evidence_key_limpo,
            operational_status=EvidenceOperationalStatus.IRREGULAR.value,
            mesa_status=EvidenceMesaStatus.NEEDS_RECHECK.value,
            failure_reasons=list(failure_reasons or []),
            evidence_metadata={
                "origin": "mobile_review_command",
                "summary": str(summary or "").strip(),
                "reason": str(reason or "").strip(),
                "required_action": str(required_action or "").strip(),
            },
            validated_by_user_id=actor_user_id,
            last_evaluated_at=agora_utc(),
        ),
    )


def _registrar_retorno_mobile_para_ajuste(
    *,
    banco: Session,
    laudo: Laudo,
    actor_user_id: int | None,
    command: Literal["devolver_no_mobile", "reabrir_bloco"],
    block_key: str | None,
    evidence_key: str | None,
    title: str | None,
    reason: str | None,
    summary: str | None,
    required_action: str | None,
    failure_reasons: list[str] | None,
) -> None:
    block_key_limpo = str(block_key or "").strip() or (
        "mobile_review:global" if command == "devolver_no_mobile" else "mobile_review:block"
    )
    title_limpo = " ".join(str(title or "").strip().split())[:180]
    reason_limpo = " ".join(str(reason or "").strip().split())[:800]
    summary_limpo = " ".join(str(summary or "").strip().split())[:280]
    required_action_limpa = " ".join(str(required_action or "").strip().split())[:280]
    failure_reasons_norm = [
        " ".join(str(item or "").strip().split())[:120]
        for item in list(failure_reasons or [])
        if str(item or "").strip()
    ]
    default_summary = (
        summary_limpo
        or reason_limpo
        or (
            f"Bloco {title_limpo or block_key_limpo} reaberto na revisão mobile."
            if command == "reabrir_bloco"
            else f"Caso devolvido para ajuste na revisão mobile ({title_limpo or 'ajuste operacional'})."
        )
    )
    default_required_action = (
        required_action_limpa
        or (
            f"Revalidar o bloco {title_limpo or block_key_limpo} antes de concluir o caso."
            if command == "reabrir_bloco"
            else "Corrigir os pontos sinalizados antes de reenviar ou aprovar no mobile."
        )
    )
    event_type = (
        "field_reopened" if command == "reabrir_bloco" else "block_returned_to_inspector"
    )

    _sincronizar_validacao_evidencia_revisao_mobile(
        banco=banco,
        laudo_id=int(laudo.id),
        actor_user_id=actor_user_id,
        evidence_key=evidence_key,
        summary=default_summary,
        reason=reason_limpo,
        required_action=default_required_action,
        failure_reasons=failure_reasons_norm,
    )
    record_return_to_inspector_irregularity(
        banco,
        laudo=laudo,
        actor_user_id=actor_user_id,
        event_type=event_type,
        block_key=block_key_limpo,
        evidence_key=str(evidence_key or "").strip() or None,
        severity=OperationalSeverity.WARNING.value,
        source="inspetor",
        details={
            "decision_source": "mobile_review",
            "title": title_limpo,
            "reason": reason_limpo,
            "summary": default_summary,
            "required_action": default_required_action,
            "failure_reasons": failure_reasons_norm,
        },
    )
    laudo.atualizado_em = agora_utc()
    banco.flush()
    commit_ou_rollback_operacional(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao registrar devolucao operacional do mobile.",
    )


async def _preparar_laudo_para_decisao_final(
    *,
    laudo_id: int,
    request: Request,
    usuario: Usuario,
    banco: Session,
) -> tuple[Laudo, str]:
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    atualizar_report_pack_draft_laudo(banco=banco, laudo=laudo)
    request.state.pending_quality_gate_override = None

    if laudo.status_revisao != StatusRevisao.RASCUNHO.value:
        raise HTTPException(status_code=400, detail="Laudo já foi enviado ou finalizado.")

    _aplicar_binding_familia_padrao_laudo(
        laudo=laudo,
        tipo_template=getattr(laudo, "tipo_template", None),
    )

    schema_pydantic = obter_schema_template_ia(laudo.tipo_template)
    if schema_pydantic is not None and not laudo.dados_formulario:
        dados_formulario_candidate = obter_dados_formulario_candidate_report_pack(laudo)
        if dados_formulario_candidate is not None:
            laudo.dados_formulario = dados_formulario_candidate

    if schema_pydantic is not None and not laudo.dados_formulario:
        try:
            mensagens = (
                banco.query(MensagemLaudo)
                .filter(MensagemLaudo.laudo_id == laudo_id)
                .order_by(MensagemLaudo.criado_em.asc())
                .all()
            )

            historico = limpar_historico_visivel_chat(
                [
                    {
                        "papel": (
                            "usuario"
                            if m.tipo in (
                                TipoMensagem.USER.value,
                                TipoMensagem.HUMANO_INSP.value,
                            )
                            else "assistente"
                        ),
                        "texto": m.conteudo,
                    }
                    for m in mensagens
                    if m.tipo in (
                        TipoMensagem.USER.value,
                        TipoMensagem.HUMANO_INSP.value,
                        TipoMensagem.IA.value,
                    )
                ]
            )

            cliente_ia_ativo = obter_cliente_ia_ativo()
            dados_json = await cliente_ia_ativo.gerar_json_estruturado(
                schema_pydantic=schema_pydantic,
                historico=historico,
                dados_imagem="",
                texto_documento="",
            )
            laudo.dados_formulario = dados_json
        except Exception:
            logger.warning(
                "Falha ao gerar JSON estruturado do template %s na finalização | laudo_id=%s",
                laudo.tipo_template,
                laudo_id,
                exc_info=True,
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
    _alinhar_status_canonico_nr35_persistido(laudo)

    gate_result = avaliar_gate_qualidade_laudo(banco, laudo)
    try:
        record_quality_gate_validations(
            banco,
            laudo=laudo,
            gate_result=gate_result,
            actor_user_id=int(getattr(usuario, "id", 0) or 0) or None,
        )
    except Exception:
        logger.warning(
            "Falha ao persistir validacoes operacionais do quality gate | laudo_id=%s",
            laudo_id,
            exc_info=True,
        )
    gate_override_request = await _resolver_intencao_override_gate_qualidade(request)
    if not bool(gate_result.get("aprovado", False)):
        override_policy = (
            dict(gate_result.get("human_override_policy") or {})
            if isinstance(gate_result.get("human_override_policy"), dict)
            else {}
        )
        if not bool(gate_override_request.get("requested")):
            raise HTTPException(status_code=422, detail=gate_result)

        if not bool(override_policy.get("available")):
            override_policy["requested"] = True
            override_policy["validation_error"] = (
                "Este bloqueio ainda exige correção da coleta; a exceção governada não pode ser aplicada agora."
            )
            gate_result["human_override_policy"] = override_policy
            gate_result["mensagem"] = str(override_policy["validation_error"])
            raise HTTPException(status_code=422, detail=gate_result)

        reason = _texto_curto_limpo(
            gate_override_request.get("reason"),
            limite=2000,
        )
        if len(reason) < _QUALITY_GATE_OVERRIDE_REASON_MIN_LENGTH:
            override_policy["requested"] = True
            override_policy["validation_error"] = (
                "Informe uma justificativa interna com pelo menos 12 caracteres para seguir com a exceção governada."
            )
            gate_result["human_override_policy"] = override_policy
            gate_result["mensagem"] = str(override_policy["validation_error"])
            raise HTTPException(status_code=422, detail=gate_result)

        request.state.pending_quality_gate_override = {
            **gate_override_request,
            "reason": reason,
            "human_override_policy": override_policy,
        }

    hard_gate_result = None
    try:
        _, hard_gate_result = _avaliar_gate_documental_finalizacao(
            request=request,
            usuario=usuario,
            banco=banco,
            laudo=laudo,
        )
    except Exception:
        logger.debug("Falha ao avaliar hard gate documental da finalizacao.", exc_info=True)
        request.state.v2_document_hard_gate_error = "report_finalize_hard_gate_failed"

    if hard_gate_result is not None and hard_gate_result.decision.did_block:
        raise HTTPException(
            status_code=int(hard_gate_result.blocked_response_status or 422),
            detail=build_document_hard_gate_block_detail(hard_gate_result),
        )

    return laudo, _resolver_review_mode_final(request=request, laudo=laudo)


def _persistir_decisao_final_laudo(
    *,
    banco: Session,
    laudo: Laudo,
    usuario: Usuario,
    laudo_id: int,
    final_validation_mode: str,
    status_destino: str,
    document_outcome: str,
    mesa_resolution_summary: dict[str, Any],
    quality_gate_override_request: dict[str, Any] | None = None,
) -> None:
    target_case_lifecycle_status: Literal["aguardando_mesa", "aprovado"] = (
        "aprovado"
        if status_destino == StatusRevisao.APROVADO.value
        else "aguardando_mesa"
    )
    if not laudo_permite_transicao_finalizacao_inspetor(
        banco,
        laudo,
        target_status=target_case_lifecycle_status,
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Laudo não está em estágio compatível com aprovação final."
                if target_case_lifecycle_status == "aprovado"
                else "Laudo não está em estágio compatível com envio para a mesa."
            ),
        )

    aplicar_finalizacao_inspetor_ao_laudo(
        laudo,
        target_status=target_case_lifecycle_status,
        occurred_at=agora_utc(),
        clear_reopen_anchor=target_case_lifecycle_status != "aprovado",
    )
    atualizar_final_validation_mode_report_pack(
        laudo=laudo,
        final_validation_mode=final_validation_mode,
    )
    _registrar_override_humano_gate_qualidade(
        banco=banco,
        laudo=laudo,
        usuario=usuario,
        final_validation_mode=final_validation_mode,
        gate_override_request=quality_gate_override_request or {},
    )
    if status_destino == StatusRevisao.APROVADO.value:
        try:
            record_approved_case_snapshot_for_laudo(
                banco,
                laudo=laudo,
                approved_by_id=int(getattr(usuario, "id", 0) or 0) or None,
                document_outcome=document_outcome,
                mesa_resolution_summary=mesa_resolution_summary,
            )
        except Exception:
            logger.warning(
                "Falha ao registrar snapshot aprovado do fluxo mobile | laudo_id=%s",
                laudo_id,
                exc_info=True,
            )
    record_report_pack_finalization_observation(
        laudo=laudo,
        report_pack_draft=obter_report_pack_draft_laudo(laudo),
        final_validation_mode=final_validation_mode,
        status_revisao=laudo.status_revisao,
    )
    banco.flush()


async def finalizar_relatorio_resposta(
    *,
    laudo_id: int,
    request: Request,
    usuario: Usuario,
    banco: Session,
) -> ResultadoJson:
    ensure_tenant_capability_for_user(
        usuario,
        capability="inspector_case_finalize",
    )
    laudo_existente = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    if laudo_existente.status_revisao == StatusRevisao.APROVADO.value:
        snapshot_replay = find_replayable_approved_case_snapshot_for_laudo(
            banco,
            laudo=laudo_existente,
            approved_by_id=int(getattr(usuario, "id", 0) or 0) or None,
            document_outcome="approved_mobile_autonomous",
            mesa_resolution_summary={
                "decision": "approved",
                "decision_source": "mobile_autonomous",
                "actor_user_id": int(getattr(usuario, "id", 0) or 0) or None,
                "review_mode_final": "mobile_autonomous",
            },
        )
        if snapshot_replay is not None:
            contexto_existente = aplicar_contexto_laudo_selecionado(request, banco, laudo_existente, usuario)
            return (
                {
                    "success": True,
                    "message": "✅ Aprovação mobile já consolidada anteriormente para este caso.",
                    "laudo_id": laudo_existente.id,
                    "estado": contexto_existente["estado"],
                    "permite_reabrir": contexto_existente["permite_reabrir"],
                    "review_mode_final": _review_mode_final_from_report_pack(
                        laudo_existente,
                        fallback="mobile_autonomous",
                    ),
                    "idempotent_replay": True,
                    "inspection_history": build_inspection_history_summary(
                        banco,
                        laudo=laudo_existente,
                    ),
                    "human_override_summary": build_human_override_summary(laudo_existente),
                    "public_verification": build_public_verification_payload(
                        laudo=laudo_existente,
                        base_url=_request_base_url(request),
                    ),
                    "pre_laudo_summary": build_pre_laudo_summary(
                        obter_pre_laudo_outline_report_pack(obter_report_pack_draft_laudo(laudo_existente))
                    ),
                    **_build_case_lifecycle_response_fields(contexto_existente),
                    **obter_contexto_modo_entrada_laudo(laudo_existente),
                    "laudo_card": serializar_card_laudo(banco, laudo_existente),
                    "report_pack_draft": obter_report_pack_draft_laudo(laudo_existente),
                },
                200,
            )

    laudo, final_validation_mode = await _preparar_laudo_para_decisao_final(
        laudo_id=laudo_id,
        request=request,
        usuario=usuario,
        banco=banco,
    )
    status_destino = (
        StatusRevisao.APROVADO.value
        if final_validation_mode == "mobile_autonomous"
        else StatusRevisao.AGUARDANDO.value
    )
    _persistir_decisao_final_laudo(
        banco=banco,
        laudo=laudo,
        usuario=usuario,
        laudo_id=laudo_id,
        final_validation_mode=final_validation_mode,
        status_destino=status_destino,
        document_outcome=(
            "approved_mobile_autonomous"
            if final_validation_mode == "mobile_autonomous"
            else "submitted_to_mesa"
        ),
        mesa_resolution_summary={
            "decision": "approved" if final_validation_mode == "mobile_autonomous" else "send_to_mesa",
            "decision_source": final_validation_mode,
            "actor_user_id": int(getattr(usuario, "id", 0) or 0) or None,
            "review_mode_final": final_validation_mode,
        },
        quality_gate_override_request=getattr(
            request.state,
            "pending_quality_gate_override",
            None,
        ),
    )
    contexto = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)

    logger.info("Relatório finalizado | usuario_id=%s | laudo_id=%s", usuario.id, laudo_id)

    return (
        {
            "success": True,
            "message": (
                "✅ Relatório aprovado automaticamente com o report pack canônico do caso."
                if final_validation_mode == "mobile_autonomous"
                else "✅ Relatório enviado para engenharia! Já aparece na Mesa de Avaliação."
            ),
            "laudo_id": laudo.id,
            "estado": contexto["estado"],
            "permite_reabrir": contexto["permite_reabrir"],
            "review_mode_final": final_validation_mode,
            "idempotent_replay": False,
            "inspection_history": build_inspection_history_summary(
                banco,
                laudo=laudo,
            ),
            "human_override_summary": build_human_override_summary(laudo),
            "public_verification": build_public_verification_payload(
                laudo=laudo,
                base_url=_request_base_url(request),
            ),
            "pre_laudo_summary": build_pre_laudo_summary(
                obter_pre_laudo_outline_report_pack(obter_report_pack_draft_laudo(laudo))
            ),
            **_build_case_lifecycle_response_fields(contexto),
            **obter_contexto_modo_entrada_laudo(laudo),
            "laudo_card": serializar_card_laudo(banco, laudo),
            "report_pack_draft": obter_report_pack_draft_laudo(laudo),
        },
        200,
    )


async def executar_comando_revisao_mobile_resposta(
    *,
    laudo_id: int,
    request: Request,
    usuario: Usuario,
    banco: Session,
    command: str,
    block_key: str | None = None,
    evidence_key: str | None = None,
    title: str | None = None,
    reason: str | None = None,
    summary: str | None = None,
    required_action: str | None = None,
    failure_reasons: list[str] | None = None,
) -> ResultadoJson:
    comando = str(command or "").strip().lower()
    if comando not in {
        "enviar_para_mesa",
        "aprovar_no_mobile",
        "devolver_no_mobile",
        "reabrir_bloco",
    }:
        raise HTTPException(status_code=400, detail="Comando de revisão mobile inválido.")
    if comando == "enviar_para_mesa":
        ensure_tenant_capability_for_user(
            usuario,
            capability="inspector_send_to_mesa",
        )
    elif comando == "aprovar_no_mobile":
        ensure_tenant_capability_for_user(
            usuario,
            capability="mobile_case_approve",
        )

    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    if laudo.status_revisao == StatusRevisao.APROVADO.value:
        if comando == "aprovar_no_mobile":
            snapshot_replay = find_replayable_approved_case_snapshot_for_laudo(
                banco,
                laudo=laudo,
                approved_by_id=int(getattr(usuario, "id", 0) or 0) or None,
                document_outcome="approved_mobile_review",
                mesa_resolution_summary={
                    "decision": "approved",
                    "decision_source": "mobile_review",
                    "actor_user_id": int(getattr(usuario, "id", 0) or 0) or None,
                    "review_mode_final": _review_mode_final_from_report_pack(
                        laudo,
                        fallback="mobile_autonomous",
                    ),
                },
            )
            if snapshot_replay is not None:
                contexto_existente = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)
                return (
                    {
                        "ok": True,
                        "command": comando,
                        "message": "Caso já estava aprovado no mobile; replay idempotente reaproveitado.",
                        "laudo_id": int(laudo.id),
                        "estado": contexto_existente["estado"],
                        "permite_edicao": contexto_existente["permite_edicao"],
                        "permite_reabrir": contexto_existente["permite_reabrir"],
                        "review_mode_final": _review_mode_final_from_report_pack(
                            laudo,
                            fallback="mobile_autonomous",
                        ),
                        "idempotent_replay": True,
                        "inspection_history": build_inspection_history_summary(
                            banco,
                            laudo=laudo,
                        ),
                        "human_override_summary": build_human_override_summary(laudo),
                        "public_verification": build_public_verification_payload(
                            laudo=laudo,
                            base_url=_request_base_url(request),
                        ),
                        **_build_case_lifecycle_response_fields(contexto_existente),
                        **obter_contexto_modo_entrada_laudo(laudo),
                        "laudo_card": serializar_card_laudo(banco, laudo),
                    },
                    200,
                )
        raise HTTPException(status_code=400, detail="Laudo aprovado nao aceita comandos de revisão mobile.")
    _garantir_comando_revisao_mobile_permitido(
        request=request,
        usuario=usuario,
        banco=banco,
        laudo=laudo,
        command=comando,
        block_key=block_key,
    )

    actor_user_id = int(getattr(usuario, "id", 0) or 0) or None
    review_mode_final: str | None = None
    status_destino = str(getattr(laudo, "status_revisao", "") or "")
    success_message = ""

    if comando in {"enviar_para_mesa", "aprovar_no_mobile"}:
        laudo, review_mode_resolvido = await _preparar_laudo_para_decisao_final(
            laudo_id=laudo_id,
            request=request,
            usuario=usuario,
            banco=banco,
        )
        if comando == "aprovar_no_mobile":
            if review_mode_resolvido not in _MOBILE_APPROVAL_REVIEW_MODES:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "mobile_review_not_allowed",
                        "message": "A policy ativa nao permite aprovacao final no mobile para este caso.",
                        "review_mode": review_mode_resolvido,
                    },
                )
            _garantir_sem_irregularidades_abertas_para_aprovacao(
                banco=banco,
                laudo_id=int(laudo.id),
            )
            review_mode_final = review_mode_resolvido
            status_destino = StatusRevisao.APROVADO.value
            _persistir_decisao_final_laudo(
                banco=banco,
                laudo=laudo,
                usuario=usuario,
                laudo_id=laudo_id,
                final_validation_mode=review_mode_final,
                status_destino=status_destino,
                document_outcome="approved_mobile_review",
                mesa_resolution_summary={
                    "decision": "approved",
                    "decision_source": "mobile_review",
                    "actor_user_id": actor_user_id,
                    "review_mode_final": review_mode_final,
                },
                quality_gate_override_request=getattr(
                    request.state,
                    "pending_quality_gate_override",
                    None,
                ),
            )
            resolve_open_return_to_inspector_irregularities(
                banco,
                laudo_id=int(laudo.id),
                resolved_by_id=actor_user_id,
                resolution_mode="edited_case_data",
                resolution_notes="Aprovacao final consolidada no fluxo mobile.",
            )
            banco.flush()
            success_message = "Caso aprovado no mobile com trilha governada."
        else:
            review_mode_final = "mesa_required"
            status_destino = StatusRevisao.AGUARDANDO.value
            _persistir_decisao_final_laudo(
                banco=banco,
                laudo=laudo,
                usuario=usuario,
                laudo_id=laudo_id,
                final_validation_mode=review_mode_final,
                status_destino=status_destino,
                document_outcome="submitted_to_mesa",
                mesa_resolution_summary={
                    "decision": "send_to_mesa",
                    "decision_source": "mobile_review",
                    "actor_user_id": actor_user_id,
                    "review_mode_final": review_mode_resolvido,
                    "review_mode_override": review_mode_final,
                },
                quality_gate_override_request=getattr(
                    request.state,
                    "pending_quality_gate_override",
                    None,
                ),
            )
            success_message = "Caso enviado para a Mesa Avaliadora a partir do mobile."
    else:
        if laudo.status_revisao != StatusRevisao.RASCUNHO.value:
            raise HTTPException(
                status_code=400,
                detail="Somente laudos em rascunho aceitam devolucao ou reabertura de bloco no mobile.",
            )
        reaffirm_case_bound_template_governance(laudo=laudo)
        if comando == "reabrir_bloco" and not str(block_key or "").strip():
            raise HTTPException(status_code=400, detail="block_key e obrigatório para reabrir bloco.")
        mobile_return_command = cast(
            Literal["devolver_no_mobile", "reabrir_bloco"],
            comando,
        )
        _registrar_retorno_mobile_para_ajuste(
            banco=banco,
            laudo=laudo,
            actor_user_id=actor_user_id,
            command=mobile_return_command,
            block_key=block_key,
            evidence_key=evidence_key,
            title=title,
            reason=reason,
            summary=summary,
            required_action=required_action,
            failure_reasons=failure_reasons,
        )
        success_message = (
            "Bloco reaberto na revisao mobile."
            if comando == "reabrir_bloco"
            else "Caso devolvido para ajuste no fluxo mobile."
        )

    contexto = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)
    return (
        {
            "ok": True,
            "command": comando,
            "message": success_message,
            "laudo_id": int(laudo.id),
            "estado": contexto["estado"],
            "permite_edicao": contexto["permite_edicao"],
            "permite_reabrir": contexto["permite_reabrir"],
            "review_mode_final": review_mode_final,
            "idempotent_replay": False,
            "inspection_history": build_inspection_history_summary(
                banco,
                laudo=laudo,
            ),
            "human_override_summary": build_human_override_summary(laudo),
            "public_verification": build_public_verification_payload(
                laudo=laudo,
                base_url=_request_base_url(request),
            ),
            **_build_case_lifecycle_response_fields(contexto),
            **obter_contexto_modo_entrada_laudo(laudo),
            "laudo_card": serializar_card_laudo(banco, laudo),
        },
        200,
    )


def obter_gate_qualidade_laudo_resposta(
    *,
    laudo_id: int,
    usuario: Usuario,
    banco: Session,
) -> ResultadoJson:
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    resultado = avaliar_gate_qualidade_laudo(banco, laudo)
    try:
        record_quality_gate_validations(
            banco,
            laudo=laudo,
            gate_result=resultado,
            actor_user_id=int(getattr(usuario, "id", 0) or 0) or None,
        )
    except Exception:
        logger.warning(
            "Falha ao persistir observacao operacional do gate de qualidade | laudo_id=%s",
            laudo_id,
            exc_info=True,
        )

    status_http = 200 if bool(resultado.get("aprovado", False)) else 422
    return resultado, status_http


async def reabrir_laudo_resposta(
    *,
    laudo_id: int,
    request: Request,
    usuario: Usuario,
    banco: Session,
    issued_document_policy: str | None = None,
) -> ResultadoJson:
    laudo = obter_laudo_do_inspetor(banco, laudo_id, usuario)
    reopen_target = resolver_alvo_reabertura_manual_laudo(banco, laudo)
    if reopen_target is None or not laudo_permite_reabrir(banco, laudo):
        raise HTTPException(
            status_code=400,
            detail="Este laudo ainda não possui ajustes liberados para reabertura.",
        )

    policy_applied = _normalize_reopen_issued_document_policy(issued_document_policy)
    previous_issued_document_name = str(getattr(laudo, "nome_arquivo_pdf", "") or "").strip() or None
    actor_user_id = int(getattr(usuario, "id", 0) or 0) or None
    internal_learning_candidate_registered = _registrar_documento_emitido_reaberto(
        laudo=laudo,
        actor_user_id=actor_user_id,
        issued_document_policy=policy_applied,
        previous_issued_document_name=previous_issued_document_name,
    )
    if previous_issued_document_name and policy_applied == "hide_from_case":
        laudo.nome_arquivo_pdf = None
    reaffirm_case_bound_template_governance(laudo=laudo)
    aplicar_reabertura_manual_ao_laudo(
        laudo,
        target_status=reopen_target,
        reopened_at=agora_utc(),
    )
    banco.flush()

    contexto = aplicar_contexto_laudo_selecionado(request, banco, laudo, usuario)

    return (
        {
            "success": True,
            "message": "Inspeção reaberta. Você já pode continuar o laudo.",
            "laudo_id": laudo.id,
            "estado": contexto["estado"],
            "permite_reabrir": contexto["permite_reabrir"],
            **_build_case_lifecycle_response_fields(contexto),
            "issued_document_policy_applied": policy_applied,
            "had_previous_issued_document": previous_issued_document_name is not None,
            "previous_issued_document_visible_in_case": bool(
                previous_issued_document_name and policy_applied == "keep_visible"
            ),
            "internal_learning_candidate_registered": internal_learning_candidate_registered,
            **obter_contexto_modo_entrada_laudo(laudo),
            "laudo_card": serializar_card_laudo(banco, laudo),
        },
        200,
    )


__all__ = [
    "RESPOSTA_DOCUMENT_HARD_GATE_BLOQUEADO",
    "RESPOSTA_GATE_QUALIDADE_REPROVADO",
    "RESPOSTA_LAUDO_NAO_ENCONTRADO",
    "ResultadoJson",
    "executar_comando_revisao_mobile_resposta",
    "finalizar_relatorio_resposta",
    "iniciar_relatorio_resposta",
    "obter_gate_qualidade_laudo_resposta",
    "obter_status_relatorio_resposta",
    "reabrir_laudo_resposta",
]
