"""Sub-roteador de onboarding e gestao SaaS do portal admin."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
from datetime import timedelta
from typing import Any, Callable, Optional, TypeVar

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.paths import resolve_family_schemas_dir
from app.domains.admin.auditoria import (
    listar_auditoria_admin_empresa,
    registrar_auditoria_admin_empresa_segura,
    serializar_registro_auditoria_admin,
)
from app.domains.chat.catalog_pdf_templates import (
    RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    ResolvedPdfTemplateRef,
    build_catalog_pdf_payload,
    has_viable_legacy_preview_overlay_for_pdf_template,
    materialize_runtime_document_editor_json,
    materialize_runtime_style_json_for_pdf_template,
    resolve_runtime_field_mapping_for_pdf_template,
    resolve_runtime_assets_for_pdf_template,
    should_use_rich_runtime_preview_for_pdf_template,
)
from app.domains.admin.portal_support import (
    URL_CLIENTES,
    URL_NOVO_CLIENTE,
    URL_PAINEL,
    _consumir_flash,
    _flash_primeiro_acesso_empresa,
    _flash_senha_temporaria,
    _normalizar_email,
    _normalizar_plano,
    _normalizar_texto,
    _redirect_err,
    _redirect_login,
    _redirect_ok,
    _redirect_step_up_admin,
    _render_template,
    _sessao_admin_reauth_expirada,
    _validar_csrf,
    _verificar_acesso_admin,
)
from app.domains.admin.services import (
    alternar_bloqueio,
    alternar_bloqueio_usuario_empresa,
    alterar_plano,
    atualizar_politica_admin_cliente_empresa,
    buscar_catalogo_familia_admin,
    buscar_detalhe_cliente,
    buscar_todos_clientes,
    criar_usuario_empresa,
    forcar_troca_senha_usuario_empresa,
    get_platform_default_new_tenant_plan,
    get_support_exceptional_policy_snapshot,
    get_tenant_exceptional_support_state,
    importar_familia_canonica_para_catalogo,
    importar_familias_canonicas_para_catalogo,
    registrar_novo_cliente,
    resetar_senha_inspetor,
    resetar_senha_usuario_empresa,
    resumir_catalogo_laudos_admin,
    sincronizar_portfolio_catalogo_empresa,
    upsert_calibracao_familia,
    upsert_familia_catalogo,
    upsert_governanca_review_familia,
    upsert_modo_tecnico_familia,
    upsert_oferta_comercial_familia,
    upsert_signatario_governado_laudo,
    upsert_tenant_family_release,
)
from app.domains.cliente.auditoria import listar_auditoria_empresa, serializar_registro_auditoria
from app.shared.backend_hotspot_metrics import observe_backend_hotspot
from app.shared.database import Empresa, NivelAcesso, Usuario, obter_banco
from app.shared.security import obter_usuario_html
from app.shared.tenant_admin_policy import summarize_tenant_admin_policy, tenant_admin_user_portal_label
from app.v2.contracts.envelopes import utc_now
from nucleo.template_editor_word import (
    MODO_EDITOR_RICO,
    documento_editor_padrao,
    estilo_editor_padrao,
    normalizar_documento_editor,
    normalizar_estilo_editor,
    normalizar_modo_editor,
)
from nucleo.template_laudos import gerar_preview_pdf_template, normalizar_codigo_template

logger = logging.getLogger("tariel.admin")

roteador_admin_clientes = APIRouter()
_T = TypeVar("_T")
URL_CATALOGO_LAUDOS = "/admin/catalogo-laudos"
URL_LOGIN_CLIENTE_PORTAL = "/cliente/login"
URL_LOGIN_INSPETOR_PORTAL = "/app/login"
URL_LOGIN_REVISOR_PORTAL = "/revisao/login"
_CHAVE_ONBOARDING_EMPRESA = "_admin_company_onboarding_bundle"
_PORTAL_LOGIN_URLS = {
    "cliente": URL_LOGIN_CLIENTE_PORTAL,
    "inspetor": URL_LOGIN_INSPETOR_PORTAL,
    "revisor": URL_LOGIN_REVISOR_PORTAL,
}
_CATALOGO_FAMILY_TABS = (
    "visao-geral",
    "schema-tecnico",
    "modos",
    "templates",
    "ofertas",
    "calibracao",
    "liberacao",
    "historico",
)


def _dict_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalizar_catalogo_family_tab(tab: str | None) -> str:
    tab_norm = str(tab or "").strip().lower()
    return tab_norm if tab_norm in _CATALOGO_FAMILY_TABS else _CATALOGO_FAMILY_TABS[0]


def _catalogo_family_tab_url(family_key: str, tab: str | None) -> str:
    family_key_norm = str(family_key or "").strip()
    tab_norm = _normalizar_catalogo_family_tab(tab)
    return f"{URL_CATALOGO_LAUDOS}/familias/{family_key_norm}?tab={tab_norm}#{tab_norm}"


def _catalogo_family_preview_path(family_key: str, suffix: str) -> Path:
    family_key_norm = normalizar_codigo_template(str(family_key or "").strip().lower())[:120]
    return (resolve_family_schemas_dir() / f"{family_key_norm}{suffix}").resolve()


def _flag_ligada(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor or "").strip().lower() in {"1", "true", "on", "sim", "yes"}


def _montar_portais_onboarding(portais: list[str] | tuple[str, ...] | None) -> list[dict[str, str]]:
    itens: list[dict[str, str]] = []
    for portal in list(portais or []):
        portal_norm = str(portal or "").strip().lower()
        login_url = _PORTAL_LOGIN_URLS.get(portal_norm)
        if not login_url:
            continue
        itens.append(
            {
                "portal": portal_norm,
                "label": tenant_admin_user_portal_label(portal_norm),
                "login_url": login_url,
            }
        )
    return itens


def _credencial_onboarding_admin_empresa(
    *,
    empresa: Empresa,
    login: str,
    senha: str,
) -> dict[str, Any]:
    return {
        "referencia": "Administrador da empresa",
        "usuario_nome": f"Responsavel {empresa.nome_fantasia}",
        "papel": "Administrador da empresa",
        "login": str(login or ""),
        "senha": str(senha or ""),
        "orientacao": "Use o login do portal da empresa e troque a senha temporaria no primeiro acesso.",
        "portais": _montar_portais_onboarding(["cliente"]),
    }


def _normalizar_credencial_onboarding_admin(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    referencia = _normalizar_texto(str(payload.get("referencia", "")), max_len=180)
    usuario_nome = _normalizar_texto(str(payload.get("usuario_nome", "")), max_len=180)
    papel = _normalizar_texto(str(payload.get("papel", "")), max_len=120)
    login = _normalizar_texto(str(payload.get("login", "")), max_len=254)
    senha = _normalizar_texto(str(payload.get("senha", "")), max_len=180)
    orientacao = _normalizar_texto(str(payload.get("orientacao", "")), max_len=260)

    portais_brutos = payload.get("portais")
    portais: list[dict[str, str]] = []
    if isinstance(portais_brutos, list):
        for item in portais_brutos:
            if not isinstance(item, dict):
                continue
            portal = _normalizar_texto(str(item.get("portal", "")), max_len=40).lower()
            label = _normalizar_texto(str(item.get("label", "")), max_len=120)
            login_url = _normalizar_texto(str(item.get("login_url", "")), max_len=240)
            if not portal or not login_url:
                continue
            portais.append(
                {
                    "portal": portal,
                    "label": label or tenant_admin_user_portal_label(portal),
                    "login_url": login_url,
                }
            )

    if not login or not senha:
        return None
    if not portais:
        allowed_portals = payload.get("allowed_portals")
        if isinstance(allowed_portals, (list, tuple)):
            portais = _montar_portais_onboarding(
                [str(portal or "").strip().lower() for portal in allowed_portals]
            )
    if not portais:
        portais = _montar_portais_onboarding(["cliente"])

    papel_resolvido = papel or "Acesso inicial"
    orientacao_padrao = (
        "Use o login abaixo no portal indicado. "
        "No primeiro acesso, o usuario precisa trocar a senha temporaria antes de continuar."
    )
    if len(portais) == 1 and portais[0].get("portal") == "cliente":
        orientacao_padrao = "Use o login do portal da empresa e troque a senha temporaria no primeiro acesso."

    return {
        "referencia": referencia or papel_resolvido,
        "usuario_nome": usuario_nome or login,
        "papel": papel_resolvido,
        "login": login,
        "senha": senha,
        "orientacao": orientacao or orientacao_padrao,
        "portais": portais,
    }


def _armazenar_bundle_onboarding_empresa(
    request: Request,
    *,
    empresa_id: int,
    empresa_nome: str,
    credenciais: list[dict[str, Any]],
) -> None:
    credenciais_norm = [
        item
        for item in (
            _normalizar_credencial_onboarding_admin(credencial)
            for credencial in list(credenciais or [])
        )
        if item is not None
    ]
    if not credenciais_norm:
        request.session.pop(_CHAVE_ONBOARDING_EMPRESA, None)
        return

    fila = request.session.get(_CHAVE_ONBOARDING_EMPRESA, {})
    if not isinstance(fila, dict):
        fila = {}

    fila[str(int(empresa_id))] = {
        "empresa_nome": _normalizar_texto(empresa_nome, max_len=200),
        "credenciais": credenciais_norm,
    }
    while len(fila) > 8:
        primeira = next(iter(fila))
        fila.pop(primeira, None)
    request.session[_CHAVE_ONBOARDING_EMPRESA] = fila


def _consumir_bundle_onboarding_empresa(
    request: Request,
    *,
    empresa_id: int,
) -> tuple[str, list[dict[str, Any]]]:
    fila = request.session.get(_CHAVE_ONBOARDING_EMPRESA, {})
    if not isinstance(fila, dict):
        request.session.pop(_CHAVE_ONBOARDING_EMPRESA, None)
        return "", []

    payload = fila.pop(str(int(empresa_id)), None)
    if fila:
        request.session[_CHAVE_ONBOARDING_EMPRESA] = fila
    else:
        request.session.pop(_CHAVE_ONBOARDING_EMPRESA, None)

    if not isinstance(payload, dict):
        return "", []

    empresa_nome = _normalizar_texto(str(payload.get("empresa_nome", "")), max_len=200)
    credenciais = [
        item
        for item in (
            _normalizar_credencial_onboarding_admin(credencial)
            for credencial in list(payload.get("credenciais") or [])
        )
        if item is not None
    ]
    return empresa_nome, credenciais


def _carregar_preview_catalogo_json(family_key: str, suffix: str) -> dict[str, Any] | None:
    path = _catalogo_family_preview_path(family_key, suffix)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _build_catalog_preview_template_ref(
    *,
    family_key: str,
    detalhe: dict[str, Any],
) -> ResolvedPdfTemplateRef | None:
    template_seed = _carregar_preview_catalogo_json(family_key, ".template_master_seed.json") or {}
    offer = _dict_payload(detalhe.get("offer"))
    template_code = normalizar_codigo_template(
        str(
            template_seed.get("template_code")
            or template_seed.get("codigo_template")
            or offer.get("template_default_code")
            or family_key
        ).strip().lower()
    )
    if not template_code:
        return None
    return ResolvedPdfTemplateRef(
        source_kind="catalog_canonical_seed",
        family_key=normalizar_codigo_template(str(family_key or "").strip().lower())[:120],
        template_id=None,
        codigo_template=template_code,
        versao=max(
            1,
            int(template_seed.get("versao") or template_seed.get("schema_version") or 1),
        ),
        modo_editor=normalizar_modo_editor(template_seed.get("modo_editor") or MODO_EDITOR_RICO),
        arquivo_pdf_base=str(template_seed.get("arquivo_pdf_base") or "").strip(),
        documento_editor_json=normalizar_documento_editor(
            template_seed.get("documento_editor_json") or documento_editor_padrao()
        ),
        estilo_json=normalizar_estilo_editor(
            template_seed.get("estilo_json") or estilo_editor_padrao()
        ),
        assets_json=list(template_seed.get("assets_json") or []),
    )


def _exigir_step_up_admin_ou_redirect(request: Request, *, return_to: str, mensagem: str) -> RedirectResponse | None:
    if not _sessao_admin_reauth_expirada(request):
        return None
    return _redirect_step_up_admin(request, return_to=return_to, mensagem=mensagem)


def _resolver_compat_admin(nome: str, fallback):
    modulo_rotas = sys.modules.get("app.domains.admin.routes")
    if modulo_rotas is None:
        return fallback
    candidato = getattr(modulo_rotas, nome, fallback)
    return candidato if callable(candidato) else fallback


def _resetar_senha_usuario_empresa_compat(banco: Session, *, empresa_id: int, usuario_id: int) -> str:
    modulo_rotas = sys.modules.get("app.domains.admin.routes")
    if modulo_rotas is not None:
        candidato_novo = getattr(modulo_rotas, "resetar_senha_usuario_empresa", None)
        if callable(candidato_novo):
            return str(candidato_novo(banco, empresa_id, usuario_id))

        candidato_legado = getattr(modulo_rotas, "resetar_senha_inspetor", None)
        if callable(candidato_legado) and candidato_legado is not resetar_senha_inspetor:
            return str(candidato_legado(banco, usuario_id))

    return str(resetar_senha_usuario_empresa(banco, empresa_id, usuario_id))


def _contexto_log_admin(**contexto: Any) -> dict[str, Any]:
    return {chave: valor for chave, valor in contexto.items() if valor is not None}


def _executar_leitura_admin(
    *,
    fallback: _T,
    mensagem_log: str,
    operacao: Callable[[], _T],
    **contexto: Any,
) -> _T:
    try:
        return operacao()
    except Exception:
        logger.exception(mensagem_log, extra=_contexto_log_admin(**contexto))
        return fallback


def _executar_acao_admin_redirect(
    *,
    url_erro: str,
    mensagem_log: str,
    operacao: Callable[[], RedirectResponse],
    mensagem_erro_usuario: str = "Erro interno. Tente novamente.",
    **contexto: Any,
) -> RedirectResponse:
    try:
        return operacao()
    except ValueError as erro:
        return _redirect_err(url_erro, str(erro))
    except Exception:
        logger.exception(mensagem_log, extra=_contexto_log_admin(**contexto))
        return _redirect_err(url_erro, mensagem_erro_usuario)


def _empresa_cliente_existe_no_banco(banco: Session, empresa_id: int) -> bool:
    empresa = banco.get(Empresa, int(empresa_id))
    return empresa is not None and not bool(getattr(empresa, "escopo_plataforma", False))


def _tenant_admin_visibility_policy_snapshot(
    banco: Session,
    *,
    empresa: Empresa | None = None,
) -> dict[str, Any]:
    support_policy = get_support_exceptional_policy_snapshot(banco)
    tenant_admin_policy = summarize_tenant_admin_policy(
        getattr(empresa, "admin_cliente_policy_json", None)
    )
    return {
        "management_projection_authoritative": True,
        "technical_access_mode": "surface_scoped_operational",
        "per_case_visibility_configurable": True,
        "per_case_action_configurable": True,
        "per_case_governance_owner": "admin_ceo_contract_setup",
        "commercial_operating_model": str(tenant_admin_policy["operating_model"]),
        "mobile_primary": bool(tenant_admin_policy["mobile_primary"]),
        "contract_operational_user_limit": tenant_admin_policy["contract_operational_user_limit"],
        "shared_mobile_operator_enabled": bool(
            tenant_admin_policy["shared_mobile_operator_enabled"]
        ),
        "shared_mobile_operator_web_inspector_enabled": bool(
            tenant_admin_policy["shared_mobile_operator_web_inspector_enabled"]
        ),
        "shared_mobile_operator_web_review_enabled": bool(
            tenant_admin_policy["shared_mobile_operator_web_review_enabled"]
        ),
        "shared_mobile_operator_surface_set": list(
            tenant_admin_policy["shared_mobile_operator_surface_set"]
        ),
        "operational_user_cross_portal_enabled": bool(
            tenant_admin_policy["operational_user_cross_portal_enabled"]
        ),
        "operational_user_admin_portal_enabled": bool(
            tenant_admin_policy["operational_user_admin_portal_enabled"]
        ),
        "tenant_assignable_portal_set": list(
            tenant_admin_policy["tenant_assignable_portal_set"]
        ),
        "commercial_package_scope": str(
            tenant_admin_policy["commercial_package_scope"]
        ),
        "commercial_capability_axes": list(
            tenant_admin_policy["commercial_capability_axes"]
        ),
        "cross_surface_session_strategy": str(
            tenant_admin_policy["cross_surface_session_strategy"]
        ),
        "cross_surface_session_unified": bool(
            tenant_admin_policy["cross_surface_session_unified"]
        ),
        "cross_surface_session_note": str(
            tenant_admin_policy["cross_surface_session_note"]
        ),
        "admin_client_case_visibility_mode": str(tenant_admin_policy["case_visibility_mode"]),
        "admin_client_case_action_mode": str(tenant_admin_policy["case_action_mode"]),
        "case_list_visible": bool(tenant_admin_policy["case_list_visible"]),
        "case_actions_enabled": bool(tenant_admin_policy["case_actions_enabled"]),
        "raw_evidence_access": "not_granted_by_projection",
        "issued_document_access": "tenant_scope_only",
        "exceptional_support_access": str(support_policy["mode"]),
        "exceptional_support_scope_level": str(support_policy["scope_level"]),
        "support_exceptional_protocol": str(
            tenant_admin_policy["support_exceptional_protocol"]
        ),
        "exceptional_support_step_up_required": bool(support_policy["step_up_required"]),
        "exceptional_support_approval_required": bool(support_policy["approval_required"]),
        "exceptional_support_justification_required": bool(support_policy["justification_required"]),
        "exceptional_support_max_duration_minutes": int(support_policy["max_duration_minutes"]),
        "tenant_retention_policy_owner": str(
            tenant_admin_policy["tenant_retention_policy_owner"]
        ),
        "technical_case_retention_min_days": int(
            tenant_admin_policy["technical_case_retention_min_days"]
        ),
        "issued_document_retention_min_days": int(
            tenant_admin_policy["issued_document_retention_min_days"]
        ),
        "audit_retention_min_days": int(
            tenant_admin_policy["audit_retention_min_days"]
        ),
        "human_signoff_required": bool(
            tenant_admin_policy["human_signoff_required"]
        ),
        "ai_assistance_audit_required": bool(
            tenant_admin_policy["ai_assistance_audit_required"]
        ),
        "human_override_justification_required": bool(
            tenant_admin_policy["human_override_justification_required"]
        ),
        "consent_collection_mode": str(
            tenant_admin_policy["consent_collection_mode"]
        ),
        "mandatory_audit_fields": list(
            tenant_admin_policy["mandatory_audit_fields"]
        ),
        "audit_scope": "tenant_operational_timeline",
        "audit_categories_visible": ["access", "commercial", "team", "support", "chat", "mesa"],
    }


def _mensagem_privacidade_operacional() -> str:
    return (
        "Por privacidade, a equipe de campo e a equipe de analise sao geridas "
        "pelo administrador da empresa no portal dela."
    )


def _obter_admin_cliente_alvo(
    banco: Session,
    *,
    empresa_id: int,
    usuario_id: int,
) -> Usuario:
    usuario_alvo = banco.get(Usuario, int(usuario_id))
    if usuario_alvo is None or int(getattr(usuario_alvo, "empresa_id", 0) or 0) != int(empresa_id):
        raise ValueError("Usuário não encontrado para esta empresa.")
    if int(getattr(usuario_alvo, "nivel_acesso", 0) or 0) != int(NivelAcesso.ADMIN_CLIENTE):
        raise ValueError(_mensagem_privacidade_operacional())
    return usuario_alvo


def _resolver_empresa_admin(banco: Session, *, empresa_id: int) -> Empresa:
    empresa = banco.get(Empresa, int(empresa_id))
    if empresa is None or bool(getattr(empresa, "escopo_plataforma", False)):
        raise ValueError("Empresa não encontrada.")
    return empresa


def _montar_payload_abertura_suporte_excepcional(
    banco: Session,
    *,
    empresa_id: int,
    usuario_admin: Usuario,
    justificativa: str,
    referencia_aprovacao: str,
) -> dict[str, Any]:
    _resolver_empresa_admin(banco, empresa_id=empresa_id)
    estado = get_tenant_exceptional_support_state(banco, empresa_id=int(empresa_id))
    policy = estado["policy"]
    if not bool(policy["can_open"]):
        raise ValueError("A política da plataforma mantém o suporte excepcional desabilitado.")
    if bool(estado["active"]):
        raise ValueError("Ja existe uma janela de suporte excepcional ativa para esta empresa.")

    justificativa_norm = _normalizar_texto(justificativa, max_len=500)
    referencia_norm = _normalizar_texto(referencia_aprovacao, max_len=120)
    if bool(policy["justification_required"]) and not justificativa_norm:
        raise ValueError("Informe a justificativa auditável para abrir suporte excepcional.")
    if bool(policy["approval_required"]) and not referencia_norm:
        raise ValueError("Informe a referência de aprovação antes de abrir suporte excepcional.")

    opened_at = utc_now()
    expires_at = opened_at + timedelta(minutes=max(1, int(policy["max_duration_minutes"])))
    return {
        "opened_at": opened_at,
        "expires_at": expires_at,
        "payload": {
            "mode": str(policy["mode"]),
            "scope_level": str(policy["scope_level"]),
            "approval_required": bool(policy["approval_required"]),
            "approval_reference": referencia_norm,
            "justification_required": bool(policy["justification_required"]),
            "justification": justificativa_norm,
            "step_up_required": bool(policy["step_up_required"]),
            "max_duration_minutes": int(policy["max_duration_minutes"]),
            "opened_at": opened_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "opened_via": "admin_client_detail",
            "actor_email": str(getattr(usuario_admin, "email", "") or ""),
        },
    }


def _processar_cadastro_cliente(
    *,
    request: Request,
    banco: Session,
    usuario_admin: Usuario,
    nome: str,
    cnpj: str,
    email: str,
    plano: str,
    segmento: str = "",
    cidade_estado: str = "",
    nome_responsavel: str = "",
    observacoes: str = "",
    admin_cliente_case_visibility_mode: str = "",
    admin_cliente_case_action_mode: str = "",
    admin_cliente_operating_model: str = "",
    admin_cliente_mobile_web_inspector_enabled: str = "",
    admin_cliente_mobile_web_review_enabled: str = "",
    admin_cliente_operational_user_cross_portal_enabled: str = "",
    admin_cliente_operational_user_admin_portal_enabled: str = "",
    provisionar_inspetor_inicial: str = "",
    inspetor_nome: str = "",
    inspetor_email: str = "",
    inspetor_telefone: str = "",
    provisionar_revisor_inicial: str = "",
    revisor_nome: str = "",
    revisor_email: str = "",
    revisor_telefone: str = "",
    revisor_crea: str = "",
    url_erro: str,
    url_sucesso: str | None = None,
) -> RedirectResponse:
    nome = _normalizar_texto(nome, max_len=200)
    cnpj = _normalizar_texto(cnpj, max_len=18)
    email = _normalizar_email(email)
    plano = _normalizar_plano(plano)
    segmento = _normalizar_texto(segmento, max_len=100)
    cidade_estado = _normalizar_texto(cidade_estado, max_len=100)
    nome_responsavel = _normalizar_texto(nome_responsavel, max_len=150)
    observacoes = _normalizar_texto(observacoes)
    inspetor_nome = _normalizar_texto(inspetor_nome, max_len=150)
    inspetor_email = _normalizar_email(inspetor_email) if inspetor_email else ""
    inspetor_telefone = _normalizar_texto(inspetor_telefone, max_len=30)
    revisor_nome = _normalizar_texto(revisor_nome, max_len=150)
    revisor_email = _normalizar_email(revisor_email) if revisor_email else ""
    revisor_telefone = _normalizar_texto(revisor_telefone, max_len=30)
    revisor_crea = _normalizar_texto(revisor_crea, max_len=60)

    if not nome or not cnpj or not email or not plano:
        return _redirect_err(url_erro, "Preencha os campos obrigatórios.")

    def _operacao() -> RedirectResponse:
        registrar_cliente = _resolver_compat_admin("registrar_novo_cliente", registrar_novo_cliente)
        resultado = registrar_cliente(
            banco,
            nome=nome,
            cnpj=cnpj,
            email_admin=email,
            plano=plano,
            segmento=segmento,
            cidade_estado=cidade_estado,
            nome_responsavel=nome_responsavel,
            observacoes=observacoes,
            admin_cliente_case_visibility_mode=admin_cliente_case_visibility_mode,
            admin_cliente_case_action_mode=admin_cliente_case_action_mode,
            admin_cliente_operating_model=admin_cliente_operating_model,
            admin_cliente_mobile_web_inspector_enabled=admin_cliente_mobile_web_inspector_enabled,
            admin_cliente_mobile_web_review_enabled=admin_cliente_mobile_web_review_enabled,
            admin_cliente_operational_user_cross_portal_enabled=admin_cliente_operational_user_cross_portal_enabled,
            admin_cliente_operational_user_admin_portal_enabled=admin_cliente_operational_user_admin_portal_enabled,
            provisionar_inspetor_inicial=provisionar_inspetor_inicial,
            inspetor_nome=inspetor_nome,
            inspetor_email=inspetor_email,
            inspetor_telefone=inspetor_telefone,
            provisionar_revisor_inicial=provisionar_revisor_inicial,
            revisor_nome=revisor_nome,
            revisor_email=revisor_email,
            revisor_telefone=revisor_telefone,
            revisor_crea=revisor_crea,
        )
        aviso_boas_vindas: str | None = None
        if isinstance(resultado, tuple) and len(resultado) == 3:
            empresa, senha_inicial, aviso_boas_vindas = resultado
        else:
            empresa, senha_inicial = resultado
            aviso_boas_vindas = None

        logger.info(
            "Cliente cadastrado | empresa_id=%s | admin_id=%s | email_admin=%s",
            empresa.id,
            usuario_admin.id,
            email,
        )

        credenciais_onboarding = [
            _credencial_onboarding_admin_empresa(
                empresa=empresa,
                login=email,
                senha=senha_inicial,
            )
        ]
        credenciais_onboarding.extend(list(getattr(empresa, "_onboarding_operational_credentials", []) or []))
        _armazenar_bundle_onboarding_empresa(
            request,
            empresa_id=int(empresa.id),
            empresa_nome=str(getattr(empresa, "nome_fantasia", "") or nome),
            credenciais=credenciais_onboarding,
        )
        _flash_primeiro_acesso_empresa(
            request,
            empresa=empresa.nome_fantasia,
            email=email,
        )

        destino = url_sucesso or f"{URL_CLIENTES}/{empresa.id}/acesso-inicial"
        mensagem_sucesso = f"Cliente {empresa.nome_fantasia} cadastrado com sucesso."
        if _flag_ligada(provisionar_inspetor_inicial) or _flag_ligada(provisionar_revisor_inicial):
            mensagem_sucesso = f"{mensagem_sucesso} Equipe inicial provisionada quando solicitada."
        if aviso_boas_vindas:
            mensagem_sucesso = f"{mensagem_sucesso} {aviso_boas_vindas}"
        return _redirect_ok(
            destino,
            mensagem_sucesso,
        )

    return _executar_acao_admin_redirect(
        url_erro=url_erro,
        mensagem_log="Falha inesperada ao cadastrar cliente",
        operacao=_operacao,
        admin_id=usuario_admin.id,
        email=email,
    )


@roteador_admin_clientes.get("/novo-cliente", response_class=HTMLResponse)
async def pagina_novo_cliente(
    request: Request,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    return _render_template(
        request,
        "admin/novo_cliente.html",
        {
            "usuario": usuario,
            "plano_padrao_onboarding": get_platform_default_new_tenant_plan(banco),
        },
    )


@roteador_admin_clientes.post("/novo-cliente")
async def processar_novo_cliente(
    request: Request,
    csrf_token: str = Form(default=""),
    nome: str = Form(...),
    cnpj: str = Form(...),
    segmento: str = Form(default=""),
    cidade_estado: str = Form(default=""),
    plano: str = Form(...),
    email: str = Form(...),
    nome_responsavel: str = Form(default=""),
    observacoes: str = Form(default=""),
    admin_cliente_case_visibility_mode: str = Form(default=""),
    admin_cliente_case_action_mode: str = Form(default=""),
    admin_cliente_operating_model: str = Form(default=""),
    admin_cliente_mobile_web_inspector_enabled: str = Form(default=""),
    admin_cliente_mobile_web_review_enabled: str = Form(default=""),
    admin_cliente_operational_user_cross_portal_enabled: str = Form(default=""),
    admin_cliente_operational_user_admin_portal_enabled: str = Form(default=""),
    provisionar_inspetor_inicial: str = Form(default=""),
    inspetor_nome: str = Form(default=""),
    inspetor_email: str = Form(default=""),
    inspetor_telefone: str = Form(default=""),
    provisionar_revisor_inicial: str = Form(default=""),
    revisor_nome: str = Form(default=""),
    revisor_email: str = Form(default=""),
    revisor_telefone: str = Form(default=""),
    revisor_crea: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(URL_NOVO_CLIENTE, "Requisição inválida.")

    return _processar_cadastro_cliente(
        request=request,
        banco=banco,
        usuario_admin=usuario,
        nome=nome,
        cnpj=cnpj,
        email=email,
        plano=plano,
        segmento=segmento,
        cidade_estado=cidade_estado,
        nome_responsavel=nome_responsavel,
        observacoes=observacoes,
        admin_cliente_case_visibility_mode=admin_cliente_case_visibility_mode,
        admin_cliente_case_action_mode=admin_cliente_case_action_mode,
        admin_cliente_operating_model=admin_cliente_operating_model,
        admin_cliente_mobile_web_inspector_enabled=admin_cliente_mobile_web_inspector_enabled,
        admin_cliente_mobile_web_review_enabled=admin_cliente_mobile_web_review_enabled,
        admin_cliente_operational_user_cross_portal_enabled=admin_cliente_operational_user_cross_portal_enabled,
        admin_cliente_operational_user_admin_portal_enabled=admin_cliente_operational_user_admin_portal_enabled,
        provisionar_inspetor_inicial=provisionar_inspetor_inicial,
        inspetor_nome=inspetor_nome,
        inspetor_email=inspetor_email,
        inspetor_telefone=inspetor_telefone,
        provisionar_revisor_inicial=provisionar_revisor_inicial,
        revisor_nome=revisor_nome,
        revisor_email=revisor_email,
        revisor_telefone=revisor_telefone,
        revisor_crea=revisor_crea,
        url_erro=URL_NOVO_CLIENTE,
    )


@roteador_admin_clientes.post("/cadastrar-empresa")
async def cadastrar_empresa(
    request: Request,
    csrf_token: str = Form(default=""),
    nome: str = Form(...),
    cnpj: str = Form(...),
    email: str = Form(...),
    plano: str = Form(...),
    admin_cliente_case_visibility_mode: str = Form(default=""),
    admin_cliente_case_action_mode: str = Form(default=""),
    admin_cliente_operating_model: str = Form(default=""),
    admin_cliente_mobile_web_inspector_enabled: str = Form(default=""),
    admin_cliente_mobile_web_review_enabled: str = Form(default=""),
    admin_cliente_operational_user_cross_portal_enabled: str = Form(default=""),
    admin_cliente_operational_user_admin_portal_enabled: str = Form(default=""),
    provisionar_inspetor_inicial: str = Form(default=""),
    inspetor_nome: str = Form(default=""),
    inspetor_email: str = Form(default=""),
    inspetor_telefone: str = Form(default=""),
    provisionar_revisor_inicial: str = Form(default=""),
    revisor_nome: str = Form(default=""),
    revisor_email: str = Form(default=""),
    revisor_telefone: str = Form(default=""),
    revisor_crea: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(URL_PAINEL, "Requisição inválida.")

    return _processar_cadastro_cliente(
        request=request,
        banco=banco,
        usuario_admin=usuario,
        nome=nome,
        cnpj=cnpj,
        email=email,
        plano=plano,
        admin_cliente_case_visibility_mode=admin_cliente_case_visibility_mode,
        admin_cliente_case_action_mode=admin_cliente_case_action_mode,
        admin_cliente_operating_model=admin_cliente_operating_model,
        admin_cliente_mobile_web_inspector_enabled=admin_cliente_mobile_web_inspector_enabled,
        admin_cliente_mobile_web_review_enabled=admin_cliente_mobile_web_review_enabled,
        admin_cliente_operational_user_cross_portal_enabled=admin_cliente_operational_user_cross_portal_enabled,
        admin_cliente_operational_user_admin_portal_enabled=admin_cliente_operational_user_admin_portal_enabled,
        provisionar_inspetor_inicial=provisionar_inspetor_inicial,
        inspetor_nome=inspetor_nome,
        inspetor_email=inspetor_email,
        inspetor_telefone=inspetor_telefone,
        provisionar_revisor_inicial=provisionar_revisor_inicial,
        revisor_nome=revisor_nome,
        revisor_email=revisor_email,
        revisor_telefone=revisor_telefone,
        revisor_crea=revisor_crea,
        url_erro=URL_PAINEL,
    )


@roteador_admin_clientes.get("/clientes", response_class=HTMLResponse)
async def lista_clientes(
    request: Request,
    nome: str = "",
    codigo: str = "",
    plano: str = "",
    status: str = "",
    saude: str = "",
    atividade: str = "",
    ordenar: str = "nome",
    direcao: str = "asc",
    pagina: int = 1,
    por_pagina: int = 20,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    nome = _normalizar_texto(nome, max_len=120)
    codigo = _normalizar_texto(codigo, max_len=40)
    plano = _normalizar_plano(plano) if plano else ""
    status = str(status or "").strip().lower()
    saude = str(saude or "").strip().lower()
    atividade = str(atividade or "").strip().lower()
    ordenar = str(ordenar or "").strip().lower()
    direcao = str(direcao or "").strip().lower()

    painel_clientes: dict[str, Any] = _executar_leitura_admin(
        fallback={"itens": [], "totais": {}, "pagination": {}, "filtros": {}},
        mensagem_log="Falha ao buscar lista de clientes",
        admin_id=usuario.id if usuario else None,
        operacao=lambda: buscar_todos_clientes(
            banco,
            filtro_nome=nome,
            filtro_codigo=codigo,
            filtro_plano=plano,
            filtro_status=status,
            filtro_saude=saude,
            filtro_atividade=atividade,
            ordenar_por=ordenar,
            direcao=direcao,
            pagina=pagina,
            por_pagina=por_pagina,
        ),
    )

    return _render_template(
        request,
        "admin/clientes.html",
        {
            "usuario": usuario,
            "clientes": painel_clientes.get("itens") or [],
            "totais_listagem": painel_clientes.get("totais") or {},
            "pagination": painel_clientes.get("pagination") or {},
            "filtros_listagem": painel_clientes.get("filtros") or {},
            "filtro_nome": nome,
            "filtro_codigo": codigo,
            "filtro_plano": plano,
            "filtro_status": status,
            "filtro_saude": saude,
            "filtro_atividade": atividade,
            "ordenar": ordenar,
            "direcao": direcao,
            "por_pagina": por_pagina,
            "total_ativos": int((painel_clientes.get("totais") or {}).get("ativos", 0)),
            "total_bloqueios": int((painel_clientes.get("totais") or {}).get("bloqueados", 0)),
            "total_alerta": int((painel_clientes.get("totais") or {}).get("alerta", 0)),
            "total_pendentes": int((painel_clientes.get("totais") or {}).get("pendentes", 0)),
            "total_sem_atividade": int((painel_clientes.get("totais") or {}).get("sem_atividade", 0)),
        },
    )


def _extrair_credenciais_onboarding_legadas(mensagens_flash: list[dict[str, Any]]) -> list[dict[str, Any]]:
    credenciais: list[dict[str, Any]] = []
    for mensagem in mensagens_flash:
        credencial = mensagem.get("credencial_onboarding")
        if not isinstance(credencial, dict):
            continue
        credencial_legada = _normalizar_credencial_onboarding_admin(
            {
                "referencia": str(credencial.get("referencia", "")),
                "usuario_nome": str(credencial.get("referencia", "")),
                "papel": str(credencial.get("portal_label", "")) or "Administrador da empresa",
                "login": str(credencial.get("login", "")),
                "senha": str(credencial.get("senha", "")),
                "orientacao": str(credencial.get("orientacao", "")),
                "portais": [
                    {
                        "portal": "cliente",
                        "label": str(credencial.get("portal_label", "")) or "Portal da empresa",
                        "login_url": str(credencial.get("portal_login_url", "")) or URL_LOGIN_CLIENTE_PORTAL,
                    }
                ],
            }
        )
        if credencial_legada is not None:
            credenciais.append(credencial_legada)
    return credenciais


@roteador_admin_clientes.get("/clientes/{empresa_id}/acesso-inicial", response_class=HTMLResponse)
async def acesso_inicial_cliente(
    request: Request,
    empresa_id: int,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    with observe_backend_hotspot(
        "admin_tenant_initial_access_view",
        request=request,
        surface="admin_ceo",
        tenant_id=empresa_id,
        user_id=getattr(usuario, "id", None),
        route_path=f"/admin/clientes/{empresa_id}/acesso-inicial",
        method="GET",
    ) as hotspot:
        if not _verificar_acesso_admin(usuario):
            hotspot.outcome = "redirect_login"
            hotspot.response_status_code = 303
            return _redirect_login()

        mensagens_flash = _consumir_flash(request)
        sucesso = _normalizar_texto(request.query_params.get("sucesso", ""), max_len=300)
        erro = _normalizar_texto(request.query_params.get("erro", ""), max_len=300)
        if sucesso:
            mensagens_flash.append({"tipo": "success", "texto": sucesso})
        if erro:
            mensagens_flash.append({"tipo": "error", "texto": erro})

        empresa_nome_onboarding, credenciais_onboarding = _consumir_bundle_onboarding_empresa(
            request,
            empresa_id=empresa_id,
        )
        if not credenciais_onboarding:
            credenciais_onboarding = _extrair_credenciais_onboarding_legadas(mensagens_flash)

        if not credenciais_onboarding:
            hotspot.outcome = "redirect_missing_bundle"
            hotspot.response_status_code = 303
            return _redirect_err(
                f"{URL_CLIENTES}/{empresa_id}",
                "Credencial inicial não está mais disponível. Gere uma nova senha no detalhe da empresa.",
            )

        empresa = banco.get(Empresa, empresa_id)
        empresa_nome = (
            getattr(empresa, "nome_fantasia", None)
            or empresa_nome_onboarding
            or credenciais_onboarding[0].get("referencia")
            or f"Empresa #{empresa_id}"
        )

        hotspot.outcome = "render_initial_access"
        hotspot.response_status_code = 200
        hotspot.detail.update({"credential_count": len(credenciais_onboarding)})
        return _render_template(
            request,
            "admin/cliente_acesso_inicial.html",
            {
                "usuario": usuario,
                "empresa": empresa,
                "empresa_id": empresa_id,
                "empresa_nome": empresa_nome,
                "credencial_onboarding": credenciais_onboarding[0],
                "credenciais_onboarding": credenciais_onboarding,
                "total_credenciais_onboarding": len(credenciais_onboarding),
                "mensagens_flash": mensagens_flash,
                "tem_detalhe_empresa": empresa is not None,
            },
        )


@roteador_admin_clientes.get("/catalogo-laudos", response_class=HTMLResponse)
async def catalogo_laudos_admin(
    request: Request,
    busca: str = "",
    macro_categoria: str = "",
    status_tecnico: str = "",
    prontidao: str = "",
    status_comercial: str = "",
    calibracao: str = "",
    liberacao: str = "",
    template_default: str = "",
    oferta_ativa: str = "",
    mode: str = "",
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    resumo = _executar_leitura_admin(
        fallback={
            "familias": [],
            "catalog_rows": [],
            "catalog_rows_total": 0,
            "ofertas_comerciais": [],
            "metodos_catalogo": [],
            "familias_canonicas": [],
            "macro_categorias": [],
            "template_default_options": [],
            "total_familias": 0,
            "total_familias_canonicas": 0,
            "total_publicadas": 0,
            "total_rascunho": 0,
            "total_arquivadas": 0,
            "total_ofertas_comerciais": 0,
            "total_ofertas_ativas": 0,
            "total_familias_calibradas": 0,
            "total_variantes_comerciais": 0,
            "total_metodos_catalogados": 0,
            "governance_rollup": {},
            "filtros": {},
        },
        mensagem_log="Falha ao carregar catálogo de famílias do Admin-CEO",
        admin_id=usuario.id if usuario else None,
        operacao=lambda: resumir_catalogo_laudos_admin(
            banco,
            filtro_busca=busca,
            filtro_macro_categoria=macro_categoria,
            filtro_status_tecnico=status_tecnico,
            filtro_prontidao=prontidao,
            filtro_status_comercial=status_comercial,
            filtro_calibracao=calibracao,
            filtro_liberacao=liberacao,
            filtro_template_default=template_default,
            filtro_oferta_ativa=oferta_ativa,
            filtro_mode=mode,
        ),
    )

    return _render_template(
        request,
        "admin/catalogo_laudos.html",
        {
            "usuario": usuario,
            **resumo,
        },
    )


@roteador_admin_clientes.get("/catalogo-laudos/familias/{family_key}", response_class=HTMLResponse)
async def detalhe_catalogo_familia_admin(
    request: Request,
    family_key: str,
    tab: str = "",
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    detalhe = _executar_leitura_admin(
        fallback=None,
        mensagem_log="Falha ao carregar detalhe da família do catálogo",
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
        operacao=lambda: buscar_catalogo_familia_admin(banco, family_key),
    )
    if not detalhe:
        return _redirect_err(URL_CATALOGO_LAUDOS, "Família não encontrada no catálogo oficial.")

    return _render_template(
        request,
        "admin/catalogo_familia_detalhe.html",
        {
            "usuario": usuario,
            "active_tab": _normalizar_catalogo_family_tab(tab),
            **detalhe,
        },
    )


@roteador_admin_clientes.get("/catalogo-laudos/familias/{family_key}/preview.pdf")
async def preview_catalogo_familia_admin(
    request: Request,
    family_key: str,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    detalhe = _executar_leitura_admin(
        fallback=None,
        mensagem_log="Falha ao carregar preview canônico da família no catálogo",
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
        operacao=lambda: buscar_catalogo_familia_admin(banco, family_key),
    )
    if not detalhe:
        raise HTTPException(status_code=404, detail="Família não encontrada no catálogo oficial.")

    template_ref = _build_catalog_preview_template_ref(
        family_key=family_key,
        detalhe=detalhe,
    )
    if template_ref is None:
        raise HTTPException(status_code=404, detail="Modelo base ainda não foi preparado para esta família.")

    source_payload = (
        _carregar_preview_catalogo_json(family_key, ".laudo_output_seed.json")
        or _carregar_preview_catalogo_json(family_key, ".laudo_output_exemplo.json")
        or {}
    )
    family = _dict_payload(detalhe.get("family"))
    family_label = str(family.get("display_name") or family_key).strip() or family_key
    preview_payload = build_catalog_pdf_payload(
        laudo=None,
        template_ref=template_ref,
        source_payload=source_payload,
        diagnostico=f"Prévia oficial do catálogo para {family_label}.",
        inspetor="Equipe Tariel",
        empresa="Tariel",
        data=utc_now().astimezone().strftime("%d/%m/%Y"),
        render_mode=RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
    )

    try:
        promoted_from_legacy = (
            normalizar_modo_editor(template_ref.modo_editor) != MODO_EDITOR_RICO
            and should_use_rich_runtime_preview_for_pdf_template(
                template_ref=template_ref,
                payload=preview_payload or {},
                render_mode=RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
            )
        )
        if normalizar_modo_editor(template_ref.modo_editor) == MODO_EDITOR_RICO or promoted_from_legacy:
            import app.domains.chat.chat as chat_facade

            runtime_assets = resolve_runtime_assets_for_pdf_template(
                template_ref=template_ref,
                payload=preview_payload or {},
            )
            runtime_document = materialize_runtime_document_editor_json(
                template_ref=template_ref,
                payload=preview_payload or {},
                render_mode=RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
            )
            pdf_preview = await chat_facade.gerar_pdf_editor_rico_bytes(
                documento_editor_json=runtime_document or documento_editor_padrao(),
                estilo_json=materialize_runtime_style_json_for_pdf_template(
                    template_ref=template_ref,
                    payload=preview_payload or {},
                    render_mode=RENDER_MODE_TEMPLATE_PREVIEW_BLANK,
                )
                or estilo_editor_padrao(),
                assets_json=runtime_assets,
                dados_formulario=preview_payload or {},
                public_verification=None,
            )
        elif has_viable_legacy_preview_overlay_for_pdf_template(template_ref=template_ref):
            pdf_preview = gerar_preview_pdf_template(
                caminho_pdf_base=template_ref.arquivo_pdf_base,
                mapeamento_campos=resolve_runtime_field_mapping_for_pdf_template(
                    template_ref=template_ref,
                ),
                dados_formulario=preview_payload or {},
            )
        else:
            raise FileNotFoundError("Template base indisponível para a prévia do catálogo.")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Falha ao gerar preview do catálogo | family_key=%s | admin_id=%s",
            family_key,
            usuario.id if usuario else None,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Falha ao gerar a prévia do laudo.") from exc

    nome_arquivo = f"catalogo_{template_ref.codigo_template}_v{template_ref.versao}.pdf"
    return Response(
        content=pdf_preview,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nome_arquivo}"'},
    )


@roteador_admin_clientes.post("/catalogo-laudos/familias/importar-canonico")
async def importar_familia_canonica_catalogo_admin(
    request: Request,
    csrf_token: str = Form(default=""),
    family_key: str = Form(...),
    status_catalogo: str = Form(default="publicado"),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(URL_CATALOGO_LAUDOS, "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        familia = importar_familia_canonica_para_catalogo(
            banco,
            family_key=family_key,
            status_catalogo=status_catalogo,
            criado_por_id=usuario.id if usuario else None,
        )
        logger.info(
            "Família canônica importada para catálogo | family_key=%s | admin_id=%s",
            familia.family_key,
            usuario.id if usuario else None,
        )
        return _redirect_ok(
            URL_CATALOGO_LAUDOS,
            f"Família canônica {familia.family_key} importada para o catálogo oficial.",
        )

    return _executar_acao_admin_redirect(
        url_erro=URL_CATALOGO_LAUDOS,
        mensagem_log="Falha ao importar família canônica para o catálogo",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
    )


@roteador_admin_clientes.post("/catalogo-laudos/familias/importar-canonico-lote")
async def importar_familias_canonicas_lote_catalogo_admin(
    request: Request,
    csrf_token: str = Form(default=""),
    status_catalogo: str = Form(default="publicado"),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(URL_CATALOGO_LAUDOS, "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        familias = importar_familias_canonicas_para_catalogo(
            banco,
            status_catalogo=status_catalogo,
            criado_por_id=usuario.id if usuario else None,
        )
        logger.info(
            "Lote de famílias canônicas importado | total=%s | admin_id=%s",
            len(familias),
            usuario.id if usuario else None,
        )
        return _redirect_ok(
            URL_CATALOGO_LAUDOS,
            f"{len(familias)} famílias canônicas importadas para o catálogo oficial.",
        )

    return _executar_acao_admin_redirect(
        url_erro=URL_CATALOGO_LAUDOS,
        mensagem_log="Falha ao importar lote de famílias canônicas para o catálogo",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
    )


@roteador_admin_clientes.post("/catalogo-laudos/familias")
async def salvar_familia_catalogo(
    request: Request,
    csrf_token: str = Form(default=""),
    family_key: str = Form(...),
    nome_exibicao: str = Form(...),
    macro_categoria: str = Form(default=""),
    nr_key: str = Form(default=""),
    descricao: str = Form(default=""),
    status_catalogo: str = Form(default="rascunho"),
    technical_status: str = Form(default=""),
    catalog_classification: str = Form(default=""),
    schema_version: int = Form(default=1),
    evidence_policy_json: str = Form(default=""),
    review_policy_json: str = Form(default=""),
    output_schema_seed_json: str = Form(default=""),
    governance_metadata_json: str = Form(default=""),
    return_to: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(URL_CATALOGO_LAUDOS, "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        familia = upsert_familia_catalogo(
            banco,
            family_key=family_key,
            nome_exibicao=nome_exibicao,
            macro_categoria=macro_categoria,
            nr_key=nr_key,
            descricao=descricao,
            status_catalogo=status_catalogo,
            technical_status=technical_status,
            catalog_classification=catalog_classification,
            schema_version=schema_version,
            evidence_policy_json_text=evidence_policy_json,
            review_policy_json_text=review_policy_json,
            output_schema_seed_json_text=output_schema_seed_json,
            governance_metadata_json_text=governance_metadata_json,
            criado_por_id=usuario.id if usuario else None,
        )
        logger.info(
            "Catálogo de famílias atualizado | family_key=%s | admin_id=%s",
            familia.family_key,
            usuario.id if usuario else None,
        )
        url_retorno = return_to or f"{URL_CATALOGO_LAUDOS}/familias/{familia.family_key}"
        return _redirect_ok(
            url_retorno,
            f"Família {familia.family_key} salva no catálogo oficial.",
        )

    return _executar_acao_admin_redirect(
        url_erro=URL_CATALOGO_LAUDOS,
        mensagem_log="Falha ao salvar família do catálogo",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
    )


@roteador_admin_clientes.post("/catalogo-laudos/familias/{family_key}/governanca-review")
async def salvar_governanca_review_catalogo(
    request: Request,
    family_key: str,
    csrf_token: str = Form(default=""),
    default_review_mode: str = Form(default=""),
    max_review_mode: str = Form(default=""),
    requires_family_lock: str = Form(default=""),
    block_on_scope_mismatch: str = Form(default=""),
    block_on_missing_required_evidence: str = Form(default=""),
    block_on_critical_field_absent: str = Form(default=""),
    blocking_conditions: str = Form(default=""),
    non_blocking_conditions: str = Form(default=""),
    red_flags_json: str = Form(default=""),
    requires_release_active: str = Form(default=""),
    requires_upload_doc_for_mobile_autonomous: str = Form(default=""),
    mobile_review_allowed_plans: str = Form(default=""),
    mobile_autonomous_allowed_plans: str = Form(default=""),
    return_to: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    url_retorno = return_to or _catalogo_family_tab_url(family_key, "schema-tecnico")
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(url_retorno, "Requisição inválida.")

    def _eh_true(valor: str) -> bool:
        return str(valor or "").strip().lower() in {"1", "true", "sim", "on", "ativo"}

    def _operacao() -> RedirectResponse:
        familia = upsert_governanca_review_familia(
            banco,
            family_key=family_key,
            default_review_mode=default_review_mode,
            max_review_mode=max_review_mode,
            requires_family_lock=_eh_true(requires_family_lock),
            block_on_scope_mismatch=_eh_true(block_on_scope_mismatch),
            block_on_missing_required_evidence=_eh_true(
                block_on_missing_required_evidence
            ),
            block_on_critical_field_absent=_eh_true(
                block_on_critical_field_absent
            ),
            blocking_conditions_text=blocking_conditions,
            non_blocking_conditions_text=non_blocking_conditions,
            red_flags_json_text=red_flags_json,
            requires_release_active=_eh_true(requires_release_active),
            requires_upload_doc_for_mobile_autonomous=_eh_true(
                requires_upload_doc_for_mobile_autonomous
            ),
            mobile_review_allowed_plans_text=mobile_review_allowed_plans,
            mobile_autonomous_allowed_plans_text=mobile_autonomous_allowed_plans,
            criado_por_id=usuario.id if usuario else None,
        )
        logger.info(
            "Governança review da família atualizada | family_key=%s | admin_id=%s",
            familia.family_key,
            usuario.id if usuario else None,
        )
        return _redirect_ok(url_retorno, "Governança de revisão da família salva.")

    return _executar_acao_admin_redirect(
        url_erro=url_retorno,
        mensagem_log="Falha ao salvar governança de revisão da família",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
    )


@roteador_admin_clientes.post("/catalogo-laudos/ofertas-comerciais")
async def salvar_oferta_comercial_catalogo(
    request: Request,
    csrf_token: str = Form(default=""),
    family_key: str = Form(...),
    offer_key: str = Form(default=""),
    family_mode_key: str = Form(default=""),
    nome_oferta: str = Form(default=""),
    descricao_comercial: str = Form(default=""),
    pacote_comercial: str = Form(default=""),
    prazo_padrao_dias: str = Form(default=""),
    ativo_comercial: str = Form(default=""),
    lifecycle_status: str = Form(default=""),
    showcase_enabled: str = Form(default=""),
    versao_oferta: int = Form(default=1),
    material_real_status: str = Form(default="sintetico"),
    material_level: str = Form(default=""),
    release_channel: str = Form(default=""),
    bundle_key: str = Form(default=""),
    bundle_label: str = Form(default=""),
    bundle_summary: str = Form(default=""),
    bundle_audience: str = Form(default=""),
    bundle_highlights: str = Form(default=""),
    included_features: str = Form(default=""),
    entitlement_monthly_issues: str = Form(default=""),
    entitlement_max_admin_clients: str = Form(default=""),
    entitlement_max_inspectors: str = Form(default=""),
    entitlement_max_reviewers: str = Form(default=""),
    entitlement_max_active_variants: str = Form(default=""),
    entitlement_max_integrations: str = Form(default=""),
    escopo_comercial: str = Form(default=""),
    exclusoes: str = Form(default=""),
    insumos_minimos: str = Form(default=""),
    variantes_comerciais: str = Form(default=""),
    template_default_code: str = Form(default=""),
    flags_json: str = Form(default=""),
    return_to: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(URL_CATALOGO_LAUDOS, "Requisição inválida.")

    ativo_norm = str(ativo_comercial or "").strip().lower() in {"1", "true", "sim", "on", "ativo"}
    showcase_norm = str(showcase_enabled or "").strip().lower() in {"1", "true", "sim", "on", "ativo"}

    def _operacao() -> RedirectResponse:
        oferta = upsert_oferta_comercial_familia(
            banco,
            family_key=family_key,
            offer_key=offer_key,
            family_mode_key=family_mode_key,
            nome_oferta=nome_oferta,
            descricao_comercial=descricao_comercial,
            pacote_comercial=pacote_comercial,
            prazo_padrao_dias=prazo_padrao_dias,
            ativo_comercial=ativo_norm,
            lifecycle_status=lifecycle_status,
            showcase_enabled=showcase_norm,
            versao_oferta=versao_oferta,
            material_real_status=material_real_status,
            material_level=material_level,
            release_channel=release_channel,
            bundle_key=bundle_key,
            bundle_label=bundle_label,
            bundle_summary=bundle_summary,
            bundle_audience=bundle_audience,
            bundle_highlights_text=bundle_highlights,
            included_features_text=included_features,
            entitlement_monthly_issues=entitlement_monthly_issues,
            entitlement_max_admin_clients=entitlement_max_admin_clients,
            entitlement_max_inspectors=entitlement_max_inspectors,
            entitlement_max_reviewers=entitlement_max_reviewers,
            entitlement_max_active_variants=entitlement_max_active_variants,
            entitlement_max_integrations=entitlement_max_integrations,
            escopo_comercial_text=escopo_comercial,
            exclusoes_text=exclusoes,
            insumos_minimos_text=insumos_minimos,
            variantes_comerciais_text=variantes_comerciais,
            template_default_code=template_default_code,
            flags_json_text=flags_json,
            criado_por_id=usuario.id if usuario else None,
        )
        logger.info(
            "Oferta comercial atualizada | family_key=%s | oferta_id=%s | admin_id=%s",
            family_key,
            oferta.id,
            usuario.id if usuario else None,
        )
        url_retorno = return_to or f"{URL_CATALOGO_LAUDOS}/familias/{family_key}#ofertas"
        return _redirect_ok(
            url_retorno,
            f"Oferta comercial da família {family_key} salva no catálogo.",
        )

    return _executar_acao_admin_redirect(
        url_erro=URL_CATALOGO_LAUDOS,
        mensagem_log="Falha ao salvar oferta comercial do catálogo",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
    )


@roteador_admin_clientes.post("/catalogo-laudos/familias/{family_key}/modos")
async def salvar_modo_tecnico_catalogo(
    request: Request,
    family_key: str,
    csrf_token: str = Form(default=""),
    mode_key: str = Form(...),
    nome_exibicao: str = Form(...),
    descricao: str = Form(default=""),
    regras_adicionais_json: str = Form(default=""),
    compatibilidade_template_json: str = Form(default=""),
    compatibilidade_oferta_json: str = Form(default=""),
    ativo: str = Form(default="on"),
    return_to: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    url_retorno = return_to or _catalogo_family_tab_url(family_key, "modos")
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(url_retorno, "Requisição inválida.")

    ativo_norm = str(ativo or "").strip().lower() in {"1", "true", "sim", "on", "ativo"}

    def _operacao() -> RedirectResponse:
        modo = upsert_modo_tecnico_familia(
            banco,
            family_key=family_key,
            mode_key=mode_key,
            nome_exibicao=nome_exibicao,
            descricao=descricao,
            regras_adicionais_json_text=regras_adicionais_json,
            compatibilidade_template_json_text=compatibilidade_template_json,
            compatibilidade_oferta_json_text=compatibilidade_oferta_json,
            ativo=ativo_norm,
            criado_por_id=usuario.id if usuario else None,
        )
        logger.info(
            "Modo técnico atualizado | family_key=%s | mode_key=%s | admin_id=%s",
            family_key,
            modo.mode_key,
            usuario.id if usuario else None,
        )
        return _redirect_ok(url_retorno, f"Modo técnico {modo.mode_key} salvo para a família.")

    return _executar_acao_admin_redirect(
        url_erro=url_retorno,
        mensagem_log="Falha ao salvar modo técnico da família",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
    )


@roteador_admin_clientes.post("/catalogo-laudos/familias/{family_key}/calibracao")
async def salvar_calibracao_catalogo(
    request: Request,
    family_key: str,
    csrf_token: str = Form(default=""),
    calibration_status: str = Form(...),
    reference_source: str = Form(default=""),
    summary_of_adjustments: str = Form(default=""),
    changed_fields_json: str = Form(default=""),
    changed_language_notes: str = Form(default=""),
    attachments_json: str = Form(default=""),
    return_to: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    url_retorno = return_to or _catalogo_family_tab_url(family_key, "calibracao")
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(url_retorno, "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        calibracao = upsert_calibracao_familia(
            banco,
            family_key=family_key,
            calibration_status=calibration_status,
            reference_source=reference_source,
            summary_of_adjustments=summary_of_adjustments,
            changed_fields_json_text=changed_fields_json,
            changed_language_notes=changed_language_notes,
            attachments_json_text=attachments_json,
            criado_por_id=usuario.id if usuario else None,
        )
        logger.info(
            "Calibração atualizada | family_key=%s | status=%s | admin_id=%s",
            family_key,
            calibracao.calibration_status,
            usuario.id if usuario else None,
        )
        return _redirect_ok(url_retorno, "Calibração da família salva.")

    return _executar_acao_admin_redirect(
        url_erro=url_retorno,
        mensagem_log="Falha ao salvar calibração da família",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
    )


@roteador_admin_clientes.post("/catalogo-laudos/familias/{family_key}/liberacao-tenant")
async def salvar_release_tenant_catalogo(
    request: Request,
    family_key: str,
    csrf_token: str = Form(default=""),
    tenant_id: int = Form(...),
    release_status: str = Form(default="draft"),
    allowed_modes: list[str] | None = Form(default=None),
    allowed_offers: list[str] | None = Form(default=None),
    allowed_templates: list[str] | None = Form(default=None),
    allowed_variants: list[str] | None = Form(default=None),
    force_review_mode: str = Form(default=""),
    max_review_mode: str = Form(default=""),
    mobile_review_override: str = Form(default=""),
    mobile_autonomous_override: str = Form(default=""),
    release_channel_override: str = Form(default=""),
    included_features: str = Form(default=""),
    entitlement_monthly_issues: str = Form(default=""),
    entitlement_max_admin_clients: str = Form(default=""),
    entitlement_max_inspectors: str = Form(default=""),
    entitlement_max_reviewers: str = Form(default=""),
    entitlement_max_active_variants: str = Form(default=""),
    entitlement_max_integrations: str = Form(default=""),
    default_template_code: str = Form(default=""),
    observacoes: str = Form(default=""),
    return_to: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    url_retorno = return_to or _catalogo_family_tab_url(family_key, "liberacao")
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(url_retorno, "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        registro = upsert_tenant_family_release(
            banco,
            tenant_id=int(tenant_id),
            family_key=family_key,
            release_status=release_status,
            allowed_modes=list(allowed_modes or []),
            allowed_offers=list(allowed_offers or []),
            allowed_templates=list(allowed_templates or []),
            allowed_variants=list(allowed_variants or []),
            force_review_mode=force_review_mode,
            max_review_mode=max_review_mode,
            mobile_review_override=mobile_review_override,
            mobile_autonomous_override=mobile_autonomous_override,
            release_channel_override=release_channel_override,
            included_features_text=included_features,
            entitlement_monthly_issues=entitlement_monthly_issues,
            entitlement_max_admin_clients=entitlement_max_admin_clients,
            entitlement_max_inspectors=entitlement_max_inspectors,
            entitlement_max_reviewers=entitlement_max_reviewers,
            entitlement_max_active_variants=entitlement_max_active_variants,
            entitlement_max_integrations=entitlement_max_integrations,
            default_template_code=default_template_code,
            observacoes=observacoes,
            criado_por_id=usuario.id if usuario else None,
        )
        logger.info(
            "Liberação por tenant atualizada | family_key=%s | tenant_id=%s | status=%s | admin_id=%s",
            family_key,
            tenant_id,
            registro.release_status,
            usuario.id if usuario else None,
        )
        return _redirect_ok(url_retorno, "Liberacao por empresa atualizada para a familia.")

    return _executar_acao_admin_redirect(
        url_erro=url_retorno,
        mensagem_log="Falha ao salvar liberação por tenant da família",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
        tenant_id=tenant_id,
    )


@roteador_admin_clientes.post("/catalogo-laudos/familias/{family_key}/technical-status")
async def atualizar_status_tecnico_catalogo(
    request: Request,
    family_key: str,
    csrf_token: str = Form(default=""),
    technical_status: str = Form(...),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(URL_CATALOGO_LAUDOS, "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        detalhe = buscar_catalogo_familia_admin(banco, family_key)
        if not detalhe:
            raise ValueError("Família não encontrada.")
        familia = detalhe["family_entity"]
        upsert_familia_catalogo(
            banco,
            family_key=str(familia.family_key),
            nome_exibicao=str(familia.nome_exibicao),
            macro_categoria=str(getattr(familia, "macro_categoria", "") or ""),
            nr_key=str(getattr(familia, "nr_key", "") or ""),
            descricao=str(getattr(familia, "descricao", "") or ""),
            status_catalogo="publicado" if str(technical_status).strip().lower() == "ready" else str(getattr(familia, "status_catalogo", "") or "rascunho"),
            technical_status=technical_status,
            catalog_classification=str(getattr(familia, "catalog_classification", "") or "family"),
            schema_version=int(getattr(familia, "schema_version", 1) or 1),
            evidence_policy_json_text=json.dumps(getattr(familia, "evidence_policy_json", None), ensure_ascii=False)
            if getattr(familia, "evidence_policy_json", None) is not None
            else "",
            review_policy_json_text=json.dumps(getattr(familia, "review_policy_json", None), ensure_ascii=False)
            if getattr(familia, "review_policy_json", None) is not None
            else "",
            output_schema_seed_json_text=json.dumps(getattr(familia, "output_schema_seed_json", None), ensure_ascii=False)
            if getattr(familia, "output_schema_seed_json", None) is not None
            else "",
            governance_metadata_json_text=json.dumps(getattr(familia, "governance_metadata_json", None), ensure_ascii=False)
            if getattr(familia, "governance_metadata_json", None) is not None
            else "",
            criado_por_id=usuario.id if usuario else None,
        )
        return _redirect_ok(URL_CATALOGO_LAUDOS, "Status técnico da família atualizado.")

    return _executar_acao_admin_redirect(
        url_erro=URL_CATALOGO_LAUDOS,
        mensagem_log="Falha ao atualizar status técnico da família do catálogo",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
    )


@roteador_admin_clientes.post("/catalogo-laudos/familias/{family_key}/offer-lifecycle")
async def atualizar_lifecycle_oferta_catalogo(
    request: Request,
    family_key: str,
    csrf_token: str = Form(default=""),
    lifecycle_status: str = Form(...),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(URL_CATALOGO_LAUDOS, "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        detalhe = buscar_catalogo_familia_admin(banco, family_key)
        if not detalhe or not detalhe.get("offer"):
            raise ValueError("Oferta comercial não encontrada para a família.")
        oferta = detalhe["offer"]
        oferta_entity = getattr(detalhe["family_entity"], "oferta_comercial", None)
        upsert_oferta_comercial_familia(
            banco,
            family_key=family_key,
            offer_key=str(oferta.get("offer_key") or family_key),
            nome_oferta=str(oferta.get("offer_name") or ""),
            descricao_comercial=str(oferta.get("description") or ""),
            pacote_comercial=str(oferta.get("package_name") or ""),
            prazo_padrao_dias=str(getattr(oferta_entity, "prazo_padrao_dias", "") or ""),
            lifecycle_status=lifecycle_status,
            showcase_enabled=bool(oferta.get("showcase_enabled")),
            versao_oferta=int(getattr(oferta_entity, "versao_oferta", 1) or 1),
            material_real_status=str(getattr(oferta_entity, "material_real_status", "") or "sintetico"),
            material_level=str(getattr(oferta_entity, "material_level", "") or "synthetic"),
            escopo_comercial_text=json.dumps(list(oferta.get("scope_items") or []), ensure_ascii=False),
            exclusoes_text=json.dumps(list(oferta.get("exclusion_items") or []), ensure_ascii=False),
            insumos_minimos_text=json.dumps(list(oferta.get("minimum_inputs") or []), ensure_ascii=False),
            variantes_comerciais_text=json.dumps(list(oferta.get("variants") or []), ensure_ascii=False),
            template_default_code=str(oferta.get("template_default_code") or ""),
            criado_por_id=usuario.id if usuario else None,
        )
        return _redirect_ok(URL_CATALOGO_LAUDOS, "Lifecycle da oferta comercial atualizado.")

    return _executar_acao_admin_redirect(
        url_erro=URL_CATALOGO_LAUDOS,
        mensagem_log="Falha ao atualizar lifecycle da oferta comercial",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        family_key=family_key,
    )


@roteador_admin_clientes.get("/clientes/{empresa_id}", response_class=HTMLResponse)
async def detalhe_cliente(
    request: Request,
    empresa_id: int,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    dados = _executar_leitura_admin(
        fallback=None,
        mensagem_log="Falha ao buscar detalhe do cliente",
        empresa_id=empresa_id,
        admin_id=usuario.id if usuario else None,
        operacao=lambda: buscar_detalhe_cliente(banco, empresa_id),
    )

    if not dados:
        mensagem = (
            "Não foi possível carregar os detalhes da empresa."
            if _empresa_cliente_existe_no_banco(banco, empresa_id)
            else "Empresa não encontrada."
        )
        return _redirect_err(URL_CLIENTES, mensagem)

    auditoria_admin = [
        serializar_registro_auditoria_admin(item)
        for item in listar_auditoria_admin_empresa(
            banco,
            empresa_id=empresa_id,
            limite=12,
        )
    ]
    auditoria_cliente = [
        serializar_registro_auditoria(item)
        for item in listar_auditoria_empresa(
            banco,
            empresa_id=empresa_id,
            limite=12,
        )
    ]
    suporte_excepcional = get_tenant_exceptional_support_state(banco, empresa_id=empresa_id)

    return _render_template(
        request,
        "admin/cliente_detalhe.html",
        {
            "usuario": usuario,
            "auditoria_admin": auditoria_admin,
            "auditoria_cliente": auditoria_cliente,
            "suporte_excepcional": suporte_excepcional,
            "visibility_policy": _tenant_admin_visibility_policy_snapshot(
                banco,
                empresa=dados.get("empresa") if isinstance(dados, dict) else None,
            ),
            **dados,
        },
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/politica-admin-cliente")
async def atualizar_politica_operacional_admin_cliente(
    request: Request,
    empresa_id: int,
    csrf_token: str = Form(default=""),
    admin_cliente_case_visibility_mode: str = Form(default=""),
    admin_cliente_case_action_mode: str = Form(default=""),
    admin_cliente_operating_model: str = Form(default=""),
    admin_cliente_mobile_web_inspector_enabled: str = Form(default=""),
    admin_cliente_mobile_web_review_enabled: str = Form(default=""),
    admin_cliente_operational_user_cross_portal_enabled: str = Form(default=""),
    admin_cliente_operational_user_admin_portal_enabled: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        politica = atualizar_politica_admin_cliente_empresa(
            banco,
            empresa_id=int(empresa_id),
            case_visibility_mode=admin_cliente_case_visibility_mode,
            case_action_mode=admin_cliente_case_action_mode,
            operating_model=admin_cliente_operating_model,
            mobile_web_inspector_enabled=admin_cliente_mobile_web_inspector_enabled,
            mobile_web_review_enabled=admin_cliente_mobile_web_review_enabled,
            operational_user_cross_portal_enabled=admin_cliente_operational_user_cross_portal_enabled,
            operational_user_admin_portal_enabled=admin_cliente_operational_user_admin_portal_enabled,
        )
        registrar_auditoria_admin_empresa_segura(
            banco,
            empresa_id=int(empresa_id),
            ator_usuario_id=usuario.id if usuario else None,
            acao="tenant_admin_client_policy_updated",
            resumo="Configuracao de acesso da empresa atualizada.",
            detalhe=(
                f"Modelo: {str(politica['operating_model_label'])}. "
                f"Visibilidade: {str(politica['case_visibility_mode_label'])}. "
                f"Ação: {str(politica['case_action_mode_label'])}."
            ),
            payload=politica,
        )
        return _redirect_ok(
            f"{URL_CLIENTES}/{empresa_id}",
            "Configuracao de acesso da empresa atualizada.",
        )

    return _executar_acao_admin_redirect(
        url_erro=f"{URL_CLIENTES}/{empresa_id}",
        mensagem_log="Falha ao atualizar política operacional do admin-cliente",
        operacao=_operacao,
        empresa_id=empresa_id,
        admin_id=usuario.id if usuario else None,
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/catalogo-laudos")
async def sincronizar_catalogo_laudos_empresa_admin(
    request: Request,
    empresa_id: int,
    csrf_token: str = Form(default=""),
    catalog_variant: list[str] | None = Form(default=None),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")

    url_retorno = f"{URL_CLIENTES}/{empresa_id}"

    def _operacao() -> RedirectResponse:
        resultado = sincronizar_portfolio_catalogo_empresa(
            banco,
            empresa_id=int(empresa_id),
            selection_tokens=list(catalog_variant or []),
            admin_id=usuario.id if usuario else None,
        )
        registrar_auditoria_admin_empresa_segura(
            banco,
            empresa_id=int(empresa_id),
            ator_usuario_id=usuario.id if usuario else None,
            acao="tenant_report_catalog_synced",
            resumo="Portfolio comercial de laudos sincronizado para a empresa.",
            detalhe=(
                f"{int(resultado['selected_count'])} variantes ativas no catálogo operacional do cliente."
            ),
            payload={
                "selected_count": int(resultado["selected_count"]),
                "governed_mode": bool(resultado["governed_mode"]),
                "activated": list(resultado["activated"]),
                "reactivated": list(resultado["reactivated"]),
                "deactivated": list(resultado["deactivated"]),
            },
        )
        return _redirect_ok(
            url_retorno,
            (
                "Portfólio de laudos sincronizado."
                if int(resultado["selected_count"]) > 0
                else (
                    "Portfolio limpo. A empresa permanece governada pelo Admin-CEO, sem modelos liberados."
                    if bool(resultado.get("governed_mode"))
                    else "Portfolio limpo. A empresa voltou ao modo antigo, sem catalogo ativo."
                )
            ),
        )

    return _executar_acao_admin_redirect(
        url_erro=url_retorno,
        mensagem_log="Falha ao sincronizar portfólio de laudos do tenant",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        empresa_id=empresa_id,
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/signatarios-governados")
async def salvar_signatario_governado_admin(
    request: Request,
    empresa_id: int,
    csrf_token: str = Form(default=""),
    signatario_id: int | None = Form(default=None),
    nome: str = Form(...),
    funcao: str = Form(...),
    registro_profissional: str = Form(default=""),
    valid_until: str = Form(default=""),
    allowed_family_keys: list[str] | None = Form(default=None),
    observacoes: str = Form(default=""),
    ativo: str | None = Form(default=None),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    url_retorno = f"{URL_CLIENTES}/{empresa_id}"
    if not _validar_csrf(request, csrf_token):
        return _redirect_err(url_retorno, "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        registro = upsert_signatario_governado_laudo(
            banco,
            tenant_id=int(empresa_id),
            signatario_id=signatario_id,
            nome=nome,
            funcao=funcao,
            registro_profissional=registro_profissional,
            valid_until=valid_until,
            allowed_family_keys=list(allowed_family_keys or []),
            observacoes=observacoes,
            ativo=ativo is not None,
            criado_por_id=usuario.id if usuario else None,
        )
        logger.info(
            "Signatário governado salvo | tenant_id=%s | signatario_id=%s | admin_id=%s",
            empresa_id,
            registro.id,
            usuario.id if usuario else None,
        )
        return _redirect_ok(url_retorno, "Responsavel pela assinatura salvo para a empresa.")

    return _executar_acao_admin_redirect(
        url_erro=url_retorno,
        mensagem_log="Falha ao salvar signatário governado do tenant",
        operacao=_operacao,
        admin_id=usuario.id if usuario else None,
        empresa_id=empresa_id,
        signatario_id=signatario_id,
    )


@roteador_admin_clientes.get("/clientes/{empresa_id}/diagnostico")
async def exportar_diagnostico_cliente_admin(
    request: Request,
    empresa_id: int,
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()
    step_up = _exigir_step_up_admin_ou_redirect(
        request,
        return_to=f"{URL_CLIENTES}/{empresa_id}/diagnostico",
        mensagem="Reautenticação necessária para exportar o diagnóstico administrativo.",
    )
    if step_up is not None:
        return step_up

    dados = buscar_detalhe_cliente(banco, empresa_id)
    if not dados:
        mensagem = (
            "Não foi possível carregar os detalhes da empresa."
            if _empresa_cliente_existe_no_banco(banco, empresa_id)
            else "Empresa não encontrada."
        )
        return _redirect_err(URL_CLIENTES, mensagem)

    empresa = dados["empresa"]
    usuarios = dados.get("usuarios") or []
    auditoria_admin = [
        serializar_registro_auditoria_admin(item)
        for item in listar_auditoria_admin_empresa(
            banco,
            empresa_id=empresa_id,
            limite=20,
        )
    ]
    auditoria_cliente = [
        serializar_registro_auditoria(item)
        for item in listar_auditoria_empresa(
            banco,
            empresa_id=empresa_id,
            limite=20,
        )
    ]
    suporte_excepcional = get_tenant_exceptional_support_state(banco, empresa_id=empresa_id)
    seguranca = _dict_payload(dados.get("seguranca"))
    payload = {
        "contract_name": "PlatformTenantOperationalDiagnosticV1",
        "generated_at": utc_now().isoformat(),
        "portal": "admin",
        "actor": {
            "usuario_id": int(usuario.id),
            "papel": "diretoria",
            "email": str(getattr(usuario, "email", "") or ""),
        },
        "tenant": {
            "id": int(empresa.id),
            "nome_fantasia": str(getattr(empresa, "nome_fantasia", "") or ""),
            "cnpj": str(getattr(empresa, "cnpj", "") or ""),
            "plano_ativo": str(getattr(empresa, "plano_ativo", "") or ""),
            "status_bloqueio": bool(getattr(empresa, "status_bloqueio", False)),
            "segmento": str(getattr(empresa, "segmento", "") or ""),
            "cidade_estado": str(getattr(empresa, "cidade_estado", "") or ""),
            "nome_responsavel": str(getattr(empresa, "nome_responsavel", "") or ""),
        },
        "resumo_operacional": {
            "total_usuarios": int((dados.get("resumo_operacional") or {}).get("usuarios_total", len(usuarios))),
            "admins_cliente": int((dados.get("resumo_operacional") or {}).get("admins_total", len(dados.get("admins_cliente") or []))),
            "inspetores": int((dados.get("resumo_operacional") or {}).get("inspetores_total", len(dados.get("inspetores") or []))),
            "revisores": int((dados.get("resumo_operacional") or {}).get("revisores_total", len(dados.get("revisores") or []))),
            "total_laudos": int(dados.get("total_laudos") or 0),
            "limite_plano": dados.get("limite_plano"),
            "uso_percentual": dados.get("uso_percentual"),
        },
        "status_operacional": {
            "status": (dados.get("status_admin") or {}).get("label"),
            "saude": (dados.get("saude_admin") or {}).get("label"),
            "saude_razao": (dados.get("saude_admin") or {}).get("razao"),
        },
        "seguranca": {
            "total_sessoes_ativas": int((dados.get("seguranca") or {}).get("total_sessoes_ativas", 0)),
            "usuarios_com_sessao_ativa": int((dados.get("seguranca") or {}).get("usuarios_com_sessao_ativa", 0)),
            "usuarios_bloqueados": int((dados.get("seguranca") or {}).get("usuarios_bloqueados", 0)),
            "usuarios_troca_senha_pendente": int((dados.get("seguranca") or {}).get("usuarios_troca_senha_pendente", 0)),
            "ultimo_acesso": (dados.get("seguranca") or {}).get("ultimo_acesso_label"),
        },
        "usuarios_administrativos": [
            {
                "id": int(item.get("id") or 0),
                "nome": str(item.get("nome_completo") or ""),
                "email": str(item.get("email") or ""),
                "perfil": str(item.get("role_label") or ""),
                "ativo": bool(item.get("ativo")),
                "senha_temporaria_ativa": bool(item.get("senha_temporaria_ativa")),
            }
            for item in (dados.get("admins_cliente") or [])
        ],
        "equipe_operacional_privada": {
            "inspetores_total": int((dados.get("resumo_operacional") or {}).get("inspetores_total", 0)),
            "mesa_avaliadora_total": int((dados.get("resumo_operacional") or {}).get("revisores_total", 0)),
            "gestao_direta_pelo_admin_ceo": False,
            "suporte_realizado_via_admin_cliente": True,
        },
        "sessoes_ativas": [
            {
                "usuario_id": int(item.get("usuario_id") or 0),
                "usuario_nome": str(item.get("usuario_nome") or ""),
                "role": str(item.get("role_label") or ""),
                "ultima_atividade": str(item.get("ultima_atividade_label") or ""),
                "expira_em": str(item.get("expira_em_label") or ""),
            }
            for item in seguranca.get("sessoes_ativas", [])
        ],
        "falhas_recentes": [
            {
                "acao": str(getattr(item, "acao", "") or ""),
                "resumo": str(getattr(item, "resumo", "") or ""),
                "criado_em": (
                    criado_em.isoformat()
                    if (criado_em := getattr(item, "criado_em", None)) is not None
                    else ""
                ),
            }
            for item in (dados.get("falhas_recentes") or [])
        ],
        "auditoria_admin": auditoria_admin,
        "auditoria_cliente": auditoria_cliente,
        "visibility_policy": _tenant_admin_visibility_policy_snapshot(banco),
        "support_exceptional": suporte_excepcional,
        "fronteiras": {
            "admin_scope": "cross_tenant_with_explicit_target",
            "tenant_scope": "company_scoped",
            "chat_scope": "company_scoped",
            "mesa_scope": "company_scoped",
        },
    }
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="tariel-admin-tenant-{int(empresa.id)}-diagnostico.json"'
        },
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/suporte-excepcional/abrir")
async def abrir_suporte_excepcional_cliente_admin(
    request: Request,
    empresa_id: int,
    csrf_token: str = Form(default=""),
    justificativa: str = Form(default=""),
    referencia_aprovacao: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")
    step_up = _exigir_step_up_admin_ou_redirect(
        request,
        return_to=f"{URL_CLIENTES}/{empresa_id}",
        mensagem="Reautenticacao necessaria para abrir suporte excepcional da empresa.",
    )
    if step_up is not None:
        return step_up

    def _operacao() -> RedirectResponse:
        abertura = _montar_payload_abertura_suporte_excepcional(
            banco,
            empresa_id=empresa_id,
            usuario_admin=usuario,
            justificativa=justificativa,
            referencia_aprovacao=referencia_aprovacao,
        )
        registrar_auditoria_admin_empresa_segura(
            banco,
            empresa_id=empresa_id,
            ator_usuario_id=int(usuario.id),
            acao="tenant_exceptional_support_opened",
            resumo=f"Suporte excepcional aberto para a empresa #{empresa_id}.",
            detalhe=(
                "Janela controlada de suporte administrativo aberta pelo Admin-CEO "
                f"até {abertura['expires_at'].strftime('%d/%m/%Y %H:%M UTC')}."
            ),
            payload=abertura["payload"],
        )
        logger.info(
            "Suporte excepcional aberto | empresa_id=%s | admin_id=%s | scope=%s | expires_at=%s",
            empresa_id,
            usuario.id,
            abertura["payload"]["scope_level"],
            abertura["expires_at"].isoformat(),
        )
        return _redirect_ok(
            f"{URL_CLIENTES}/{empresa_id}",
            "Janela de suporte excepcional aberta com trilha auditável.",
        )

    return _executar_acao_admin_redirect(
        url_erro=f"{URL_CLIENTES}/{empresa_id}",
        mensagem_log="Falha ao abrir suporte excepcional do tenant",
        operacao=_operacao,
        empresa_id=empresa_id,
        admin_id=usuario.id if usuario else None,
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/suporte-excepcional/encerrar")
async def encerrar_suporte_excepcional_cliente_admin(
    request: Request,
    empresa_id: int,
    csrf_token: str = Form(default=""),
    motivo_encerramento: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")
    step_up = _exigir_step_up_admin_ou_redirect(
        request,
        return_to=f"{URL_CLIENTES}/{empresa_id}",
        mensagem="Reautenticacao necessaria para encerrar suporte excepcional da empresa.",
    )
    if step_up is not None:
        return step_up

    def _operacao() -> RedirectResponse:
        _resolver_empresa_admin(banco, empresa_id=empresa_id)
        estado = get_tenant_exceptional_support_state(banco, empresa_id=empresa_id)
        if not bool(estado["active"]):
            raise ValueError("Nao existe uma janela de suporte excepcional ativa para esta empresa.")
        motivo = _normalizar_texto(motivo_encerramento, max_len=300)
        registrar_auditoria_admin_empresa_segura(
            banco,
            empresa_id=empresa_id,
            ator_usuario_id=int(usuario.id),
            acao="tenant_exceptional_support_closed",
            resumo=f"Suporte excepcional encerrado para a empresa #{empresa_id}.",
            detalhe=motivo or "Janela excepcional encerrada manualmente pelo Admin-CEO.",
            payload={
                "opened_record_id": int(estado["opened_record_id"]),
                "closed_at": utc_now().isoformat(),
                "closed_reason": motivo,
                "expired": False,
                "scope_level": str(estado["scope_level"]),
            },
        )
        logger.info(
            "Suporte excepcional encerrado | empresa_id=%s | admin_id=%s | opened_record_id=%s",
            empresa_id,
            usuario.id,
            estado["opened_record_id"],
        )
        return _redirect_ok(
            f"{URL_CLIENTES}/{empresa_id}",
            "Janela de suporte excepcional encerrada.",
        )

    return _executar_acao_admin_redirect(
        url_erro=f"{URL_CLIENTES}/{empresa_id}",
        mensagem_log="Falha ao encerrar suporte excepcional do tenant",
        operacao=_operacao,
        empresa_id=empresa_id,
        admin_id=usuario.id if usuario else None,
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/bloquear")
async def toggle_bloqueio(
    request: Request,
    empresa_id: int,
    csrf_token: str = Form(default=""),
    motivo: str = Form(default=""),
    confirmar_desbloqueio: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")
    step_up = _exigir_step_up_admin_ou_redirect(
        request,
        return_to=f"{URL_CLIENTES}/{empresa_id}",
        mensagem="Reautenticação necessária para bloquear ou desbloquear empresa.",
    )
    if step_up is not None:
        return step_up

    def _operacao() -> RedirectResponse:
        resultado = alternar_bloqueio(
            banco,
            empresa_id,
            motivo=motivo,
            confirmar_desbloqueio=confirmar_desbloqueio == "1",
        )
        bloqueado = bool(resultado["blocked"])
        mensagem = "Acesso bloqueado com sucesso." if bloqueado else "Acesso restaurado com sucesso."
        registrar_auditoria_admin_empresa_segura(
            banco,
            empresa_id=empresa_id,
            ator_usuario_id=int(usuario.id),
            acao="tenant_block_toggled",
            resumo=f"Bloqueio da empresa #{empresa_id} {'ativado' if bloqueado else 'removido'}.",
            detalhe="Acao administrativa executada pelo portal Admin-CEO.",
            payload={
                "blocked": bool(bloqueado),
                "reason": str(resultado.get("reason") or ""),
                "sessions_invalidated": int(resultado.get("sessions_invalidated") or 0),
            },
        )

        logger.info(
            "Bloqueio de empresa alterado | empresa_id=%s | bloqueado=%s | sessoes_encerradas=%s | admin_id=%s",
            empresa_id,
            bloqueado,
            int(resultado.get("sessions_invalidated") or 0),
            usuario.id,
        )
        return _redirect_ok(
            f"{URL_CLIENTES}/{empresa_id}",
            (
                f"{mensagem} Sessões encerradas: {int(resultado.get('sessions_invalidated') or 0)}."
                if bloqueado
                else mensagem
            ),
        )

    return _executar_acao_admin_redirect(
        url_erro=f"{URL_CLIENTES}/{empresa_id}",
        mensagem_log="Falha ao alternar bloqueio",
        operacao=_operacao,
        empresa_id=empresa_id,
        admin_id=usuario.id if usuario else None,
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/trocar-plano")
async def trocar_plano(
    request: Request,
    empresa_id: int,
    csrf_token: str = Form(default=""),
    plano: str = Form(...),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")
    step_up = _exigir_step_up_admin_ou_redirect(
        request,
        return_to=f"{URL_CLIENTES}/{empresa_id}",
        mensagem="Reautenticacao necessaria para alterar o plano da empresa.",
    )
    if step_up is not None:
        return step_up

    plano_normalizado = _normalizar_plano(plano)

    def _operacao() -> RedirectResponse:
        preview = alterar_plano(banco, empresa_id, plano_normalizado)
        registrar_auditoria_admin_empresa_segura(
            banco,
            empresa_id=empresa_id,
            ator_usuario_id=int(usuario.id),
            acao="tenant_plan_changed",
            resumo=f"Plano da empresa #{empresa_id} alterado para {plano_normalizado}.",
            detalhe="Acao administrativa executada pelo portal Admin-CEO.",
            payload=preview,
        )

        logger.info(
            "Plano alterado | empresa_id=%s | plano=%s | admin_id=%s",
            empresa_id,
            plano_normalizado,
            usuario.id,
        )
        return _redirect_ok(
            f"{URL_CLIENTES}/{empresa_id}",
            f"Plano atualizado para {plano_normalizado}.",
        )

    return _executar_acao_admin_redirect(
        url_erro=f"{URL_CLIENTES}/{empresa_id}",
        mensagem_log="Falha ao trocar plano",
        operacao=_operacao,
        empresa_id=empresa_id,
        plano=plano_normalizado,
        admin_id=usuario.id if usuario else None,
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/resetar-senha/{usuario_id}")
async def resetar_senha(
    request: Request,
    empresa_id: int,
    usuario_id: int,
    csrf_token: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")
    step_up = _exigir_step_up_admin_ou_redirect(
        request,
        return_to=f"{URL_CLIENTES}/{empresa_id}",
        mensagem="Reautenticação necessária para forçar troca de senha do usuário.",
    )
    if step_up is not None:
        return step_up

    def _operacao() -> RedirectResponse:
        usuario_alvo = _obter_admin_cliente_alvo(
            banco,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        usuario_resetado = forcar_troca_senha_usuario_empresa(
            banco,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        registrar_auditoria_admin_empresa_segura(
            banco,
            empresa_id=empresa_id,
            ator_usuario_id=int(usuario.id),
            alvo_usuario_id=usuario_id,
            acao="tenant_user_password_reset",
            resumo=(
                f"Troca obrigatoria de senha forcada para o administrador da empresa "
                f"{usuario_alvo.nome_completo} pelo Admin-CEO."
            ),
            detalhe="As sessões ativas foram encerradas e o próximo login exigirá troca de senha.",
            payload={"user_id": int(usuario_id), "force_password_change": True},
        )

        logger.info(
            "Troca obrigatoria de senha marcada | usuario_id=%s | empresa_id=%s | admin_id=%s",
            usuario_id,
            empresa_id,
            usuario.id,
        )
        return _redirect_ok(
            f"{URL_CLIENTES}/{empresa_id}",
            f"{usuario_resetado.nome_completo} deverá trocar a senha no próximo login.",
        )

    return _executar_acao_admin_redirect(
        url_erro=f"{URL_CLIENTES}/{empresa_id}",
        mensagem_log="Falha ao resetar senha",
        operacao=_operacao,
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        admin_id=usuario.id if usuario else None,
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/adicionar-inspetor")
async def novo_inspetor(
    request: Request,
    empresa_id: int,
    csrf_token: str = Form(default=""),
    nome: str = Form(...),
    email: str = Form(...),
    perfil: str = Form(default="inspetor"),
    crea: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", _mensagem_privacidade_operacional())


@roteador_admin_clientes.post("/clientes/{empresa_id}/adicionar-admin-cliente")
async def novo_admin_cliente(
    request: Request,
    empresa_id: int,
    csrf_token: str = Form(default=""),
    nome: str = Form(...),
    email: str = Form(...),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")
    step_up = _exigir_step_up_admin_ou_redirect(
        request,
        return_to=f"{URL_CLIENTES}/{empresa_id}",
        mensagem="Reautenticação necessária para criar um administrador da empresa.",
    )
    if step_up is not None:
        return step_up

    nome = _normalizar_texto(nome, max_len=150)
    email_normalizado = _normalizar_email(email)

    if not nome or not email_normalizado:
        return _redirect_err(
            f"{URL_CLIENTES}/{empresa_id}",
            "Preencha nome e e-mail do administrador da empresa.",
        )

    def _operacao() -> RedirectResponse:
        usuario_criado, senha_inicial = criar_usuario_empresa(
            banco,
            empresa_id=empresa_id,
            nome=nome,
            email=email_normalizado,
            nivel_acesso="admin_cliente",
        )
        registrar_auditoria_admin_empresa_segura(
            banco,
            empresa_id=empresa_id,
            ator_usuario_id=int(usuario.id),
            alvo_usuario_id=int(usuario_criado.id),
            acao="tenant_admin_client_created",
            resumo=f"Administrador da empresa {nome} criado pelo Admin-CEO.",
            detalhe="A conta foi preparada para o portal da empresa.",
            payload={"email": email_normalizado, "role": "admin_cliente"},
        )

        logger.info(
            "Admin-cliente criado | empresa_id=%s | email=%s | admin_id=%s",
            empresa_id,
            email_normalizado,
            usuario.id,
        )
        _flash_senha_temporaria(
            request,
            referencia=f"{nome} ({email_normalizado})",
            senha=senha_inicial,
        )
        return _redirect_ok(
            f"{URL_CLIENTES}/{empresa_id}",
            f"Administrador da empresa {nome} adicionado com sucesso.",
        )

    return _executar_acao_admin_redirect(
        url_erro=f"{URL_CLIENTES}/{empresa_id}",
        mensagem_log="Falha ao adicionar admin-cliente",
        operacao=_operacao,
        empresa_id=empresa_id,
        email=email_normalizado,
        admin_id=usuario.id if usuario else None,
    )


@roteador_admin_clientes.post("/clientes/{empresa_id}/usuarios/{usuario_id}/atualizar-crea")
async def atualizar_crea_usuario_operacional(
    request: Request,
    empresa_id: int,
    usuario_id: int,
    csrf_token: str = Form(default=""),
    crea: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")
    return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", _mensagem_privacidade_operacional())


@roteador_admin_clientes.post("/clientes/{empresa_id}/usuarios/{usuario_id}/bloquear")
async def alternar_bloqueio_usuario(
    request: Request,
    empresa_id: int,
    usuario_id: int,
    csrf_token: str = Form(default=""),
    banco: Session = Depends(obter_banco),
    usuario: Optional[Usuario] = Depends(obter_usuario_html),
):
    if not _verificar_acesso_admin(usuario):
        return _redirect_login()

    if not _validar_csrf(request, csrf_token):
        return _redirect_err(f"{URL_CLIENTES}/{empresa_id}", "Requisição inválida.")

    def _operacao() -> RedirectResponse:
        usuario_alvo = _obter_admin_cliente_alvo(
            banco,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        usuario_atualizado = alternar_bloqueio_usuario_empresa(
            banco,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
        )
        registrar_auditoria_admin_empresa_segura(
            banco,
            empresa_id=empresa_id,
            ator_usuario_id=int(usuario.id),
            alvo_usuario_id=int(usuario_atualizado.id),
            acao="tenant_user_block_toggled",
            resumo=f"Acesso do administrador da empresa {usuario_alvo.nome_completo} alterado pelo Admin-CEO.",
            detalhe="Sessoes ativas do usuario foram encerradas no portal da empresa.",
            payload={"user_id": int(usuario_atualizado.id), "active": bool(usuario_atualizado.ativo)},
        )
        return _redirect_ok(
            f"{URL_CLIENTES}/{empresa_id}",
            (
                f"{usuario_atualizado.nome_completo} reativado com sucesso."
                if bool(usuario_atualizado.ativo)
                else f"{usuario_atualizado.nome_completo} bloqueado com sucesso."
            ),
        )

    return _executar_acao_admin_redirect(
        url_erro=f"{URL_CLIENTES}/{empresa_id}",
        mensagem_log="Falha ao alternar bloqueio do usuário",
        operacao=_operacao,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        admin_id=usuario.id if usuario else None,
    )
