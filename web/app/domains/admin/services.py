# ==========================================
# TARIEL CONTROL TOWER — SERVICOS_SAAS.PY
# Responsabilidade:
# - onboarding de clientes SaaS
# - métricas do painel administrativo
# - gestão de empresas e usuários do ecossistema
# - regras comerciais de plano e limite
# ==========================================

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
import json
import logging
from pathlib import Path
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.paths import canonical_docs_logical_path, resolve_family_schemas_dir, resolve_master_templates_dir
from app.core.settings import env_str, get_settings
from app.domains.admin import admin_platform_identity_services as _admin_platform_identity_services
from app.domains.admin import admin_dashboard_services as _admin_dashboard_services
from app.domains.admin import tenant_client_cleanup_services as _tenant_client_cleanup_services
from app.domains.admin import tenant_onboarding_services as _tenant_onboarding_services
from app.domains.admin import tenant_client_read_services as _tenant_client_read_services
from app.domains.admin import tenant_client_write_services as _tenant_client_write_services
from app.domains.admin import tenant_plan_services as _tenant_plan_services
from app.domains.admin import tenant_signatory_services as _tenant_signatory_services
from app.domains.chat.catalog_document_contract import (
    MASTER_TEMPLATE_REGISTRY,
    resolve_master_template_id_for_family,
)
from app.domains.admin.observability_summary import build_admin_observability_operational_summary
from app.domains.admin.platform_settings_console_overview import (
    build_platform_settings_console_overview,
)
from app.domains.admin.platform_settings_console_sections import (
    build_platform_settings_console_sections,
)
from app.domains.admin.platform_settings_state import (
    _PLATFORM_SETTING_DEFINITIONS,
    _SUPPORT_EXCEPTIONAL_MODE_LABELS,
    _SUPPORT_EXCEPTIONAL_SCOPE_LABELS,
    _build_runtime_items,
    _build_setting_items,
    _coerce_platform_setting_value,
    _platform_setting_row_map,
    _platform_setting_snapshot,
    _platform_settings_users,
    _setting_value_label,
    get_platform_default_new_tenant_plan,  # noqa: F401
    get_platform_setting_value,
    get_support_exceptional_policy_snapshot,  # noqa: F401
    get_tenant_exceptional_support_state,  # noqa: F401
)
from app.domains.admin.platform_settings_setting_descriptors import (
    build_access_setting_descriptors,
    build_defaults_setting_descriptors,
    build_rollout_setting_descriptors,
    build_support_setting_descriptors,
)
from app.domains.admin.runtime_rollout_descriptors import build_rollout_runtime_descriptors
from app.domains.admin.runtime_settings_descriptors import (
    build_access_runtime_descriptors,
    build_document_runtime_descriptors,
    build_observability_runtime_descriptors,
)
from app.domains.admin import tenant_user_services as _tenant_user_services
from app.domains.admin.tenant_user_services import (
    _buscar_empresa,
    _normalizar_texto_curto,
    _normalizar_texto_opcional,
    criar_usuario_empresa as _criar_usuario_empresa,
)
from app.shared.catalog_commercial_governance import (
    RELEASE_CHANNEL_ORDER,
    merge_offer_commercial_flags,
    merge_release_contract_policy,
    normalize_release_channel,
    release_channel_meta,
    sanitize_commercial_bundle,
    sanitize_contract_entitlements,
    summarize_offer_commercial_governance,
    summarize_release_contract_governance,
)
from app.shared.tenant_admin_policy import (
    summarize_tenant_admin_policy,
)
from app.shared.database import (
    CalibracaoFamiliaLaudo,
    ConfiguracaoPlataforma,
    Empresa,
    FamiliaLaudoCatalogo,
    MetodoCatalogoInspecao,
    ModoTecnicoFamiliaLaudo,
    OfertaComercialFamiliaLaudo,
    PlanoEmpresa,
    RegistroAuditoriaEmpresa,
    TenantFamilyReleaseLaudo,
    Usuario,
    flush_ou_rollback_integridade,
)
from app.shared.tenant_report_catalog import (
    build_admin_tenant_catalog_snapshot,
    catalog_offer_variants,
    list_active_tenant_catalog_activations,
    sync_tenant_catalog_activations,
)
from app.shared.security import gerar_senha_fortificada as _gerar_senha_fortificada
from app.v2.document import document_hard_gate_observability_enabled
from app.v2.document.hard_gate_evidence import document_hard_gate_durable_evidence_enabled
logger = logging.getLogger("tariel.saas")

_MODO_DEV = not get_settings().em_producao
_BACKEND_NOTIFICACAO_BOAS_VINDAS = env_str(
    "ADMIN_WELCOME_NOTIFICATION_BACKEND",
    "log" if _MODO_DEV else "noop",
).strip().lower()

UI_AUDIT_TENANT_PREFIX = _tenant_client_cleanup_services.UI_AUDIT_TENANT_PREFIX
AdminIdentityAuthorizationResult = _admin_platform_identity_services.AdminIdentityAuthorizationResult
_resolver_empresa_plataforma = _admin_platform_identity_services._resolver_empresa_plataforma
_tenant_cliente_clause = _admin_platform_identity_services._tenant_cliente_clause
autenticar_identidade_admin = _admin_platform_identity_services.autenticar_identidade_admin
listar_operadores_plataforma = _admin_platform_identity_services.listar_operadores_plataforma
registrar_auditoria_identidade_admin = _admin_platform_identity_services.registrar_auditoria_identidade_admin
_PRIORIDADE_PLANO = _tenant_plan_services._PRIORIDADE_PLANO
_case_prioridade_plano = _tenant_plan_services._case_prioridade_plano
_label_limite = _tenant_plan_services._label_limite
_normalizar_plano = _tenant_plan_services._normalizar_plano
_obter_limite_laudos_empresa = _tenant_plan_services._obter_limite_laudos_empresa
_obter_limite_usuarios_empresa = _tenant_plan_services._obter_limite_usuarios_empresa
construir_preview_troca_plano = _tenant_plan_services.construir_preview_troca_plano
_atividade_recente_compat = _tenant_client_read_services._atividade_recente_compat
_classificar_saude_empresa = _tenant_client_read_services._classificar_saude_empresa
_classificar_status_empresa = _tenant_client_read_services._classificar_status_empresa
_coletar_contexto_empresas = _tenant_client_read_services._coletar_contexto_empresas
_formatar_data_admin = _tenant_client_read_services._formatar_data_admin
_max_datetime_admin = _tenant_client_read_services._max_datetime_admin
_normalizar_datetime_admin = _tenant_client_read_services._normalizar_datetime_admin
_normalizar_direcao_ordenacao = _tenant_client_read_services._normalizar_direcao_ordenacao
_normalizar_filtro_atividade = _tenant_client_read_services._normalizar_filtro_atividade
_normalizar_filtro_saude = _tenant_client_read_services._normalizar_filtro_saude
_normalizar_filtro_status = _tenant_client_read_services._normalizar_filtro_status
_normalizar_ordenacao_clientes = _tenant_client_read_services._normalizar_ordenacao_clientes
_normalizar_paginacao = _tenant_client_read_services._normalizar_paginacao
_role_label = _tenant_client_read_services._role_label
buscar_todos_clientes = _tenant_client_read_services.buscar_todos_clientes
_listar_ids_usuarios_operacionais_empresa = _tenant_client_write_services._listar_ids_usuarios_operacionais_empresa
_normalizar_politica_admin_cliente_empresa = _tenant_client_write_services._normalizar_politica_admin_cliente_empresa
alternar_bloqueio = _tenant_client_write_services.alternar_bloqueio
alterar_plano = _tenant_client_write_services.alterar_plano
atualizar_politica_admin_cliente_empresa = _tenant_client_write_services.atualizar_politica_admin_cliente_empresa
remover_empresas_cliente_por_ids = _tenant_client_cleanup_services.remover_empresas_cliente_por_ids
remover_empresas_temporarias_auditoria_ui = _tenant_client_cleanup_services.remover_empresas_temporarias_auditoria_ui

alternar_bloqueio_usuario_empresa = _tenant_user_services.alternar_bloqueio_usuario_empresa
atualizar_usuario_empresa = _tenant_user_services.atualizar_usuario_empresa
excluir_usuario_empresa = _tenant_user_services.excluir_usuario_empresa
filtro_usuarios_operacionais_cliente = _tenant_user_services.filtro_usuarios_operacionais_cliente
filtro_usuarios_gerenciaveis_cliente = _tenant_user_services.filtro_usuarios_gerenciaveis_cliente
forcar_troca_senha_usuario_empresa = _tenant_user_services.forcar_troca_senha_usuario_empresa
resetar_senha_inspetor = _tenant_user_services.resetar_senha_inspetor
resetar_senha_usuario_empresa = _tenant_user_services.resetar_senha_usuario_empresa
criar_usuario_empresa = _criar_usuario_empresa
gerar_senha_fortificada = _gerar_senha_fortificada
_serializar_usuario_admin = _tenant_client_read_services._serializar_usuario_admin
_resumir_primeiro_acesso_empresa = _tenant_client_read_services._resumir_primeiro_acesso_empresa
_serializar_signatario_governado_admin = _tenant_signatory_services._serializar_signatario_governado_admin
upsert_signatario_governado_laudo = _tenant_signatory_services.upsert_signatario_governado_laudo

# =========================================================
# NORMALIZAÇÃO / CONTRATO COMERCIAL
# =========================================================

_SHOWROOM_PLAN_LABELS = {
    PlanoEmpresa.INICIAL.value: {
        "label": "Starter",
        "short_label": "Starter",
        "support_label": "Inicial",
    },
    PlanoEmpresa.INTERMEDIARIO.value: {
        "label": "Pro",
        "short_label": "Pro",
        "support_label": "Intermediario",
    },
    PlanoEmpresa.ILIMITADO.value: {
        "label": "Enterprise",
        "short_label": "Enterprise",
        "support_label": "Ilimitado",
    },
}

def _catalog_showroom_plan_label(plan_name: str) -> dict[str, str]:
    normalized = PlanoEmpresa.normalizar(plan_name)
    return dict(
        _SHOWROOM_PLAN_LABELS.get(
            normalized,
            {
                "label": normalized,
                "short_label": normalized,
                "support_label": normalized,
            },
        )
    )


def _catalog_human_join(values: list[str]) -> str:
    labels = [str(item).strip() for item in values if str(item).strip()]
    if not labels:
        return "Sem assinatura liberada"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} e {labels[1]}"
    return ", ".join(labels[:-1]) + f" e {labels[-1]}"


def _catalog_macro_category_sort_key(value: str) -> tuple[int, int, str]:
    label = str(value or "").strip()
    normalized = label.casefold()
    nr_match = re.search(r"\bnr\D*(\d{1,3})\b", normalized)
    if nr_match:
        return (0, int(nr_match.group(1)), normalized)
    return (1, 9999, normalized)

_CATALOGO_TECHNICAL_STATUS_LABELS = {
    "draft": ("Em preparo", "draft"),
    "review": ("Em ajuste", "review"),
    "ready": ("Pronta", "ready"),
    "deprecated": ("Arquivada", "archived"),
}
_CATALOGO_LIFECYCLE_STATUS_LABELS = {
    "draft": ("Em preparo", "draft"),
    "testing": ("Em validacao", "testing"),
    "active": ("Ativa", "active"),
    "paused": ("Pausada", "paused"),
    "archived": ("Arquivada", "archived"),
}
_CATALOGO_CALIBRATION_STATUS_LABELS = {
    "none": ("Sem validacao", "idle"),
    "synthetic_only": ("Base inicial", "draft"),
    "partial_real": ("Em validacao", "testing"),
    "real_calibrated": ("Validada", "active"),
}
_CATALOGO_RELEASE_STATUS_LABELS = {
    "draft": ("Em preparo", "draft"),
    "active": ("Liberada", "active"),
    "paused": ("Pausado", "paused"),
    "expired": ("Encerrada", "archived"),
}
_CATALOGO_REVIEW_MODE_LABELS = {
    "mesa_required": ("Analise interna", "review"),
    "mobile_review_allowed": ("Aplicativo com apoio da analise", "testing"),
    "mobile_autonomous": ("Aplicativo com autonomia", "active"),
}
_CATALOGO_REVIEW_OVERRIDE_LABELS = {
    "inherit": "Usar configuracao padrao",
    "allow": "Permitir",
    "deny": "Bloquear",
}
_CATALOGO_RED_FLAG_SEVERITY_LABELS = {
    "low": ("Baixa", "idle"),
    "medium": ("Média", "testing"),
    "high": ("Alta", "review"),
    "critical": ("Crítica", "active"),
}
_CATALOGO_READINESS_LABELS = {
    "technical_only": ("Base pronta", "idle"),
    "partial": ("Quase pronta", "testing"),
    "sellable": ("Pronta para venda", "active"),
    "calibrated": ("Validada", "active"),
}
_CATALOGO_MATERIAL_WORKSPACE_STATUS_LABELS = {
    "aguardando_material_real": ("Aguardando material", "testing"),
    "baseline_sintetica_externa_validada": ("Base validada", "active"),
    "material_real_calibrado": ("Validada com material real", "active"),
    "workspace_bootstrapped": ("Pasta inicial criada", "draft"),
}
_CATALOGO_MATERIAL_PRIORITY_LABELS = {
    "resolved": ("Resolvido", "active"),
    "immediate": ("Prioridade alta", "review"),
    "active_queue": ("Na fila", "testing"),
    "waiting_material": ("Aguardando material", "draft"),
    "bootstrap": ("Preparar base", "idle"),
}
_CATALOGO_DOCUMENT_PREVIEW_STATUS_LABELS = {
    "bootstrap": ("Inicio da base", "draft"),
    "foundation": ("Base pronta", "testing"),
    "reference_ready": ("Com referencia", "review"),
    "premium_ready": ("Pronto para uso", "active"),
}
_CATALOGO_SHOWCASE_STATUS_LABELS = {
    "building": ("Em montagem", "draft"),
    "demonstration_ready": ("Modelo demonstrativo pronto", "active"),
}
_CATALOGO_MATERIAL_PREVIEW_STATUS_LABELS = {
    "none": ("Sem material real", "idle"),
    "reference_ready": ("Com base de referencia", "testing"),
    "real_calibrated": ("Calibrado com material real", "active"),
}
_CATALOGO_VARIANT_LIBRARY_STATUS_LABELS = {
    "operational": ("Pronta", "active"),
    "template_mapped": ("Modelo ligado", "testing"),
    "needs_template": ("Falta modelo", "draft"),
}
_CATALOGO_TEMPLATE_REFINEMENT_STATUS_LABELS = {
    "continuous": ("Ajuste continuo", "active"),
    "refinement_due": ("Precisa de ajuste", "review"),
    "mapped": ("Modelo ligado", "testing"),
    "registry_gap": ("Falta registro", "draft"),
}
_CATALOGO_MATERIAL_WORKLIST_STATUS_LABELS = {
    "done": ("Concluído", "active"),
    "pending": ("Pendente", "draft"),
    "blocking": ("Bloqueio", "review"),
    "in_progress": ("Em andamento", "testing"),
}
_CATALOGO_MATERIAL_WORKLIST_PHASE_LABELS = {
    "intake_pending": ("Coleta prioritária", "review"),
    "packaging_reference": ("Consolidação do pacote", "testing"),
    "template_refinement": ("Refino de template", "review"),
    "continuous": ("Refino contínuo", "active"),
}
_MATERIAL_REAL_EXECUTION_TRACK_PRESETS: dict[str, dict[str, Any]] = {
    "nr13_inspecao_tubulacao": {
        "track_id": "nr13_wave1_finish",
        "track_label": "Fechamento NR13 wave 1",
        "focus_label": "Fechar a trilha premium de tubulação usando material real e harmonizar a linguagem com a baseline de NR13 já validada.",
        "recommended_owner": "Curadoria Tariel + operação do cliente",
        "next_checkpoint": "2026-04-17",
        "lane": "wave1_critical_finish",
        "sort_order": 10,
    },
    "nr13_integridade_caldeira": {
        "track_id": "nr13_wave1_finish",
        "track_label": "Fechamento NR13 wave 1",
        "focus_label": "Subir a família de integridade para o mesmo nível premium já alcançado por caldeira e vaso de pressão.",
        "recommended_owner": "Curadoria Tariel + responsável técnico do cliente",
        "next_checkpoint": "2026-04-17",
        "lane": "wave1_critical_finish",
        "sort_order": 11,
    },
    "nr13_teste_hidrostatico": {
        "track_id": "nr13_wave1_finish",
        "track_label": "Fechamento NR13 wave 1",
        "focus_label": "Consolidar a variante de teste com anexos, memória e conclusão vendável de NR13.",
        "recommended_owner": "Curadoria Tariel + operação do cliente",
        "next_checkpoint": "2026-04-19",
        "lane": "wave1_critical_finish",
        "sort_order": 12,
    },
    "nr13_teste_estanqueidade_tubulacao_gas": {
        "track_id": "nr13_wave1_finish",
        "track_label": "Fechamento NR13 wave 1",
        "focus_label": "Fechar a família de estanqueidade com material real e amarração forte de evidência, anexo e conclusão.",
        "recommended_owner": "Curadoria Tariel + operação do cliente",
        "next_checkpoint": "2026-04-19",
        "lane": "wave1_critical_finish",
        "sort_order": 13,
    },
    "nr12_inspecao_maquina_equipamento": {
        "track_id": "wave1_expand_nr12",
        "track_label": "Expansão premium NR12",
        "focus_label": "Abrir a baseline real inaugural de inspeção de máquinas com casca premium de inspeção vendável.",
        "recommended_owner": "Curadoria Tariel + SST do cliente",
        "next_checkpoint": "2026-04-24",
        "lane": "wave1_critical_expand",
        "sort_order": 30,
    },
    "nr12_apreciacao_risco_maquina": {
        "track_id": "wave1_expand_nr12",
        "track_label": "Expansão premium NR12",
        "focus_label": "Pressionar o template mestre técnico com material real de apreciação de risco e anexos de engenharia.",
        "recommended_owner": "Curadoria Tariel + engenharia do cliente",
        "next_checkpoint": "2026-04-24",
        "lane": "wave1_critical_expand",
        "sort_order": 31,
    },
    "nr20_inspecao_instalacoes_inflamaveis": {
        "track_id": "wave1_expand_nr20",
        "track_label": "Expansão premium NR20",
        "focus_label": "Abrir acervo real de inspeção de inflamáveis para consolidar linguagem, evidência e anexo pack.",
        "recommended_owner": "Curadoria Tariel + operação do cliente",
        "next_checkpoint": "2026-04-26",
        "lane": "wave1_critical_expand",
        "sort_order": 40,
    },
    "nr20_prontuario_instalacoes_inflamaveis": {
        "track_id": "wave1_expand_nr20",
        "track_label": "Expansão premium NR20",
        "focus_label": "Consolidar documentação controlada e prontuário com material real e governança mais rígida.",
        "recommended_owner": "Curadoria Tariel + documentação técnica do cliente",
        "next_checkpoint": "2026-04-26",
        "lane": "wave1_critical_expand",
        "sort_order": 41,
    },
    "nr33_avaliacao_espaco_confinado": {
        "track_id": "wave1_expand_nr33",
        "track_label": "Expansão premium NR33",
        "focus_label": "Subir a baseline real de avaliação de espaço confinado e alinhar red flags, bloqueios e evidência forte.",
        "recommended_owner": "Curadoria Tariel + operação do cliente",
        "next_checkpoint": "2026-04-28",
        "lane": "wave1_critical_expand",
        "sort_order": 50,
    },
    "nr33_permissao_entrada_trabalho": {
        "track_id": "wave1_expand_nr33",
        "track_label": "Expansão premium NR33",
        "focus_label": "Consolidar a PET com material real, governança documental e postura de emissão controlada.",
        "recommended_owner": "Curadoria Tariel + operação do cliente",
        "next_checkpoint": "2026-04-28",
        "lane": "wave1_critical_expand",
        "sort_order": 51,
    },
}
_CATALOGO_METHOD_HINTS: tuple[tuple[str, str, str], ...] = (
    ("ultrassom", "ultrassom", "inspection_method"),
    ("liquido_penetrante", "liquido_penetrante", "inspection_method"),
    ("particula_magnetica", "particula_magnetica", "inspection_method"),
    ("visual", "visual", "inspection_method"),
    ("estanqueidade", "estanqueidade", "inspection_method"),
    ("hidrostatic", "hidrostatico", "inspection_method"),
)
_REVIEW_MODE_ORDER = {
    "mobile_autonomous": 0,
    "mobile_review_allowed": 1,
    "mesa_required": 2,
}


def build_admin_platform_settings_console(banco: Session) -> dict[str, Any]:
    rows = _platform_setting_row_map(banco)
    users = _platform_settings_users(rows, banco)
    observability = build_admin_observability_operational_summary()
    privacy = observability.get("privacy") or {}
    operators = listar_operadores_plataforma(banco)
    admin_reauth_max_age_minutes = int(
        get_platform_setting_value(banco, "admin_reauth_max_age_minutes")
    )
    support_exceptional_mode = str(
        get_platform_setting_value(banco, "support_exceptional_mode")
    )
    support_exceptional_approval_required = bool(
        get_platform_setting_value(banco, "support_exceptional_approval_required")
    )
    support_exceptional_justification_required = bool(
        get_platform_setting_value(banco, "support_exceptional_justification_required")
    )
    support_exceptional_max_duration_minutes = int(
        get_platform_setting_value(banco, "support_exceptional_max_duration_minutes")
    )
    support_exceptional_scope_level = str(
        get_platform_setting_value(banco, "support_exceptional_scope_level")
    )
    review_ui_canonical = str(get_platform_setting_value(banco, "review_ui_canonical"))
    default_new_tenant_plan = str(
        get_platform_setting_value(banco, "default_new_tenant_plan")
    )
    access_runtime_descriptors = build_access_runtime_descriptors(
        operator_count=len(operators)
    )

    access_items = [
        *_build_runtime_items(access_runtime_descriptors[:1]),
        *_build_setting_items(
            banco,
            rows,
            users,
            build_access_setting_descriptors(),
        ),
        *_build_runtime_items(access_runtime_descriptors[1:]),
    ]

    support_items = _build_setting_items(
        banco,
        rows,
        users,
        build_support_setting_descriptors(),
    )

    rollout_items = [
        *_build_setting_items(
            banco,
            rows,
            users,
            build_rollout_setting_descriptors(),
        ),
        *_build_runtime_items(build_rollout_runtime_descriptors()),
    ]

    document_items = _build_runtime_items(build_document_runtime_descriptors())

    observability_items = _build_runtime_items(
        build_observability_runtime_descriptors(privacy)
    )

    defaults_items = _build_setting_items(
        banco,
        rows,
        users,
        build_defaults_setting_descriptors(),
    )

    sections = build_platform_settings_console_sections(
        access_items=access_items,
        admin_reauth_max_age_minutes=admin_reauth_max_age_minutes,
        support_items=support_items,
        support_exceptional_mode=support_exceptional_mode,
        support_exceptional_mode_options=[
            {"value": key, "label": label}
            for key, label in _SUPPORT_EXCEPTIONAL_MODE_LABELS.items()
        ],
        support_exceptional_approval_required=support_exceptional_approval_required,
        support_exceptional_justification_required=support_exceptional_justification_required,
        support_exceptional_max_duration_minutes=support_exceptional_max_duration_minutes,
        support_exceptional_scope_level=support_exceptional_scope_level,
        support_exceptional_scope_options=[
            {"value": key, "label": label}
            for key, label in _SUPPORT_EXCEPTIONAL_SCOPE_LABELS.items()
        ],
        rollout_items=rollout_items,
        review_ui_canonical=review_ui_canonical,
        document_items=document_items,
        observability_items=observability_items,
        defaults_items=defaults_items,
        default_new_tenant_plan=default_new_tenant_plan,
        default_new_tenant_plan_options=[
            {"value": plano, "label": plano}
            for plano in PlanoEmpresa.valores()
        ],
    )

    return {
        "summary_cards": build_platform_settings_console_overview(
            rows=rows.values(),
            privacy=privacy,
            environment_label=str(
                observability.get("environment") or get_settings().ambiente
            ).upper(),
            review_ui_canonical_label=_setting_value_label(
                "review_ui_canonical",
                review_ui_canonical,
            ),
            support_exceptional_mode=support_exceptional_mode,
            document_hard_gate_enabled=document_hard_gate_observability_enabled(),
            durable_evidence_enabled=document_hard_gate_durable_evidence_enabled(),
        ),
        "sections": sections,
    }


def _platform_setting_changes_payload(
    banco: Session,
    updates: dict[str, Any],
    *,
    rows: dict[str, ConfiguracaoPlataforma],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for key, raw_value in updates.items():
        if key not in _PLATFORM_SETTING_DEFINITIONS:
            raise ValueError("Configuração de plataforma inválida.")
        before = _platform_setting_snapshot(banco, key, rows=rows)
        after_value = _coerce_platform_setting_value(key, raw_value)
        if before["value"] == after_value:
            continue
        row = rows.get(key)
        if row is not None:
            row.valor_json = after_value
        else:
            row = ConfiguracaoPlataforma(
                chave=key,
                categoria=str(_PLATFORM_SETTING_DEFINITIONS[key]["category"]),
                valor_json=after_value,
            )
            banco.add(row)
            rows[key] = row
        changes.append(
            {
                "key": key,
                "before": before["value"],
                "before_source": before["source"],
                "after": after_value,
            }
        )
    return changes


def apply_platform_settings_update(
    banco: Session,
    *,
    actor_user: Usuario,
    group_key: str,
    reason: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    justification = _normalizar_texto_curto(reason, campo="Justificativa", max_len=300)
    rows = _platform_setting_row_map(banco)
    changes = _platform_setting_changes_payload(banco, updates, rows=rows)
    if not changes:
        raise ValueError("Nenhuma alteração efetiva foi detectada.")

    for change in changes:
        row = rows[change["key"]]
        row.categoria = str(_PLATFORM_SETTING_DEFINITIONS[change["key"]]["category"])
        row.motivo_ultima_alteracao = justification
        row.atualizada_por_usuario_id = int(actor_user.id)

    empresa_plataforma = _resolver_empresa_plataforma(banco, usuario=actor_user)
    if empresa_plataforma is None:
        raise ValueError("Tenant de plataforma não encontrado para auditar a alteração.")

    resumo = {
        "access": "Política de acesso da plataforma atualizada.",
        "support": "Política de suporte excepcional atualizada.",
        "rollout": "Política de rollout operacional atualizada.",
        "defaults": "Defaults globais da plataforma atualizados.",
    }.get(group_key, "Configuração de plataforma atualizada.")

    detalhe = {
        "access": "Mudança de segurança aplicada ao Admin-CEO.",
        "support": "Mudança de suporte excepcional aplicada à governança da plataforma.",
        "rollout": "Mudança de superfície canônica aplicada à revisão.",
        "defaults": "Mudança aplicada ao onboarding padrão de novos tenants.",
    }.get(group_key, "Mudança administrativa aplicada à plataforma.")

    banco.add(
        RegistroAuditoriaEmpresa(
            empresa_id=int(empresa_plataforma.id),
            ator_usuario_id=int(actor_user.id),
            portal="admin",
            acao="platform_setting_updated",
            resumo=resumo,
            detalhe=detalhe,
            payload_json={
                "group": group_key,
                "reason": justification,
                "changes": changes,
            },
        )
    )
    flush_ou_rollback_integridade(
        banco,
        logger_operacao=logger,
        mensagem_erro="Falha ao persistir configuração de plataforma.",
    )
    return {
        "group": group_key,
        "changes": changes,
        "reason": justification,
    }


# =========================================================
# HELPERS
# =========================================================


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalizar_datetime_admin(valor: datetime | None) -> datetime | None:
    if not isinstance(valor, datetime):
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _max_datetime_admin(valores: Iterable[datetime | None]) -> datetime | None:
    candidatos = [valor for valor in valores if isinstance(valor, datetime)]
    return max(candidatos) if candidatos else None


def _dict_payload_admin(valor: Any) -> dict[str, Any]:
    return dict(valor) if isinstance(valor, dict) else {}

def _normalizar_cnpj(cnpj: str) -> str:
    valor = re.sub(r"\D+", "", str(cnpj or ""))
    if len(valor) != 14:
        raise ValueError("CNPJ inválido. Informe 14 dígitos.")
    return valor


def _normalizar_chave_catalogo(valor: str, *, campo: str, max_len: int) -> str:
    texto = str(valor or "").strip().lower()
    texto = (
        texto.replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    if not texto:
        raise ValueError(f"{campo} é obrigatório.")
    return texto[:max_len]


def _normalizar_json_opcional(valor: str, *, campo: str) -> Any | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        return json.loads(texto)
    except json.JSONDecodeError as erro:
        raise ValueError(f"{campo} precisa ser JSON válido.") from erro


def _normalizar_lista_textual(valor: str, *, campo: str, max_len_item: int = 240) -> list[str] | None:
    texto = str(valor or "").strip()
    if not texto:
        return None

    if texto.startswith("["):
        payload = _normalizar_json_opcional(texto, campo=campo)
        if not isinstance(payload, list):
            raise ValueError(f"{campo} precisa ser uma lista JSON ou linhas de texto.")
        itens_brutos = payload
    else:
        itens_brutos = texto.splitlines()

    itens: list[str] = []
    vistos: set[str] = set()
    for bruto in itens_brutos:
        linha = re.sub(r"^[\-\*\u2022]+\s*", "", str(bruto or "").strip())
        if not linha:
            continue
        linha = linha[:max_len_item]
        chave = linha.casefold()
        if chave in vistos:
            continue
        vistos.add(chave)
        itens.append(linha)
    return itens or None


def _normalizar_status_catalogo_familia(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "rascunho",
        "rascunho": "rascunho",
        "draft": "rascunho",
        "publicado": "publicado",
        "published": "publicado",
        "arquivado": "arquivado",
        "archived": "arquivado",
        "archive": "arquivado",
    }
    if texto not in aliases:
        raise ValueError("Status do catálogo inválido.")
    return aliases[texto]


def _normalizar_status_material_real_oferta(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "sintetico",
        "sintetico": "sintetico",
        "sintetica": "sintetico",
        "base_sintetica": "sintetico",
        "parcial": "parcial",
        "misto": "parcial",
        "hibrido": "parcial",
        "material_real_parcial": "parcial",
        "calibrado": "calibrado",
        "real": "calibrado",
        "material_real": "calibrado",
    }
    if texto not in aliases:
        raise ValueError("Status de material real inválido.")
    return aliases[texto]


def _normalizar_variantes_comerciais(valor: str | list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    itens: list[Any]
    if isinstance(valor, list):
        itens = valor
    else:
        texto = str(valor or "").strip()
        if not texto:
            return None
        if texto.startswith("["):
            payload = _normalizar_json_opcional(texto, campo="Variantes comerciais")
            if not isinstance(payload, list):
                raise ValueError("Variantes comerciais precisam ser uma lista JSON.")
            itens = payload
        else:
            itens = [linha for linha in texto.splitlines() if linha.strip()]

    variantes: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for indice, bruto in enumerate(itens, start=1):
        if isinstance(bruto, dict):
            variant_key_raw = (
                bruto.get("variant_key")
                or bruto.get("codigo")
                or bruto.get("slug")
                or bruto.get("chave")
                or bruto.get("nome_exibicao")
                or bruto.get("nome")
                or ""
            )
            nome_raw = bruto.get("nome_exibicao") or bruto.get("nome") or variant_key_raw
            template_code_raw = bruto.get("template_code") or bruto.get("codigo_template") or ""
            uso_raw = bruto.get("uso_recomendado") or bruto.get("descricao") or ""
        else:
            linha = re.sub(r"^[\-\*\u2022]+\s*", "", str(bruto or "").strip())
            if not linha:
                continue
            partes = [parte.strip() for parte in linha.split("|")]
            variant_key_raw = partes[0] if partes else ""
            nome_raw = partes[1] if len(partes) > 1 else variant_key_raw
            template_code_raw = partes[2] if len(partes) > 2 else ""
            uso_raw = partes[3] if len(partes) > 3 else ""

        variant_key = _normalizar_chave_catalogo(variant_key_raw, campo="Código da variante", max_len=80)
        if variant_key in vistos:
            continue
        vistos.add(variant_key)
        variantes.append(
            {
                "variant_key": variant_key,
                "nome_exibicao": _normalizar_texto_curto(
                    str(nome_raw or variant_key_raw),
                    campo="Nome da variante",
                    max_len=120,
                ),
                "template_code": (
                    _normalizar_chave_catalogo(str(template_code_raw), campo="Template code", max_len=80)
                    if str(template_code_raw or "").strip()
                    else None
                ),
                "uso_recomendado": _normalizar_texto_opcional(str(uso_raw or ""), 240),
                "ordem": indice,
            }
        )
    return variantes or None


def _normalizar_status_tecnico_catalogo(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "draft",
        "draft": "draft",
        "rascunho": "draft",
        "review": "review",
        "revisao": "review",
        "ready": "ready",
        "publicado": "ready",
        "deprecated": "deprecated",
        "arquivado": "deprecated",
        "archived": "deprecated",
    }
    if texto not in aliases:
        raise ValueError("Status técnico inválido.")
    return aliases[texto]


def _normalizar_classificacao_catalogo(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "family",
        "family": "family",
        "familia": "family",
        "inspection_method": "inspection_method",
        "metodo_inspecao": "inspection_method",
        "evidence_method": "evidence_method",
        "metodo_evidencia": "evidence_method",
    }
    if texto not in aliases:
        raise ValueError("Classificação do catálogo inválida.")
    return aliases[texto]


def _normalizar_lifecycle_status_oferta(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "draft",
        "draft": "draft",
        "rascunho": "draft",
        "testing": "testing",
        "teste": "testing",
        "active": "active",
        "ativo": "active",
        "paused": "paused",
        "pausado": "paused",
        "archived": "archived",
        "arquivado": "archived",
    }
    if texto not in aliases:
        raise ValueError("Lifecycle da oferta inválido.")
    return aliases[texto]


def _normalizar_material_level_catalogo(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "synthetic",
        "synthetic": "synthetic",
        "sintetico": "synthetic",
        "partial": "partial",
        "parcial": "partial",
        "real_calibrated": "real_calibrated",
        "calibrado": "real_calibrated",
        "real": "real_calibrated",
    }
    if texto not in aliases:
        raise ValueError("Material level inválido.")
    return aliases[texto]


def _normalizar_status_calibracao_catalogo(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "none",
        "none": "none",
        "nenhum": "none",
        "synthetic_only": "synthetic_only",
        "sintetico": "synthetic_only",
        "partial_real": "partial_real",
        "parcial": "partial_real",
        "real_calibrated": "real_calibrated",
        "calibrado": "real_calibrated",
    }
    if texto not in aliases:
        raise ValueError("Status de calibração inválido.")
    return aliases[texto]


def _normalizar_status_release_catalogo(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": "draft",
        "draft": "draft",
        "rascunho": "draft",
        "active": "active",
        "ativo": "active",
        "paused": "paused",
        "pausado": "paused",
        "expired": "expired",
        "expirado": "expired",
    }
    if texto not in aliases:
        raise ValueError("Status de liberação inválido.")
    return aliases[texto]


def _normalizar_release_channel_catalogo(
    valor: str | None,
    *,
    campo: str,
    allow_empty: bool = True,
) -> str | None:
    try:
        return normalize_release_channel(valor, allow_empty=allow_empty)
    except ValueError as exc:
        raise ValueError(f"{campo} inválido.") from exc


def _normalizar_limite_contractual(
    valor: int | str | None,
    *,
    campo: str,
) -> int | None:
    if valor is None or valor == "":
        return None
    try:
        parsed = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{campo} precisa ser inteiro.") from exc
    if parsed < 0:
        raise ValueError(f"{campo} precisa ser zero ou positivo.")
    return parsed


def _normalizar_lista_json_canonica(
    valor: str | list[str] | tuple[str, ...] | None,
    *,
    campo: str,
    max_len_item: int = 120,
) -> list[str] | None:
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        itens_brutos = list(valor)
    else:
        texto = str(valor or "").strip()
        if not texto:
            return None
        if texto.startswith("["):
            payload = _normalizar_json_opcional(texto, campo=campo)
            if not isinstance(payload, list):
                raise ValueError(f"{campo} precisa ser uma lista JSON.")
            itens_brutos = payload
        else:
            itens_brutos = texto.splitlines()

    itens: list[str] = []
    vistos: set[str] = set()
    for bruto in itens_brutos:
        item = _normalizar_chave_catalogo(bruto, campo=campo, max_len=max_len_item)
        if not item or item in vistos:
            continue
        vistos.add(item)
        itens.append(item)
    return itens or None


def _normalizar_nr_key(valor: str, *, family_key: str = "") -> str | None:
    bruto = str(valor or "").strip().lower()
    if not bruto and str(family_key or "").startswith("nr"):
        match = re.match(r"^(nr\d+)", str(family_key or "").strip().lower())
        bruto = match.group(1) if match else ""
    if not bruto:
        return None
    bruto = bruto.replace(" ", "").replace("/", "").replace("-", "")
    match = re.search(r"(nr\d+[a-z]*)", bruto)
    if match:
        return match.group(1)[:40]
    return _normalizar_chave_catalogo(bruto, campo="NR key", max_len=40) or None


def _inferir_classificacao_catalogo(*, family_key: str, nome_exibicao: str = "", macro_categoria: str = "") -> str:
    family_norm = str(family_key or "").strip().lower()
    nome_norm = str(nome_exibicao or "").strip().lower()
    macro_norm = str(macro_categoria or "").strip().lower()
    if family_norm.startswith("end_"):
        return "inspection_method"
    texto = " ".join((family_norm, nome_norm, macro_norm))
    if any(chave in texto for chave, _metodo, _categoria in _CATALOGO_METHOD_HINTS):
        return "inspection_method"
    return "family"


def _metodos_sugeridos_para_familia(*, family_key: str, nome_exibicao: str = "") -> list[dict[str, str]]:
    texto = " ".join((str(family_key or "").strip().lower(), str(nome_exibicao or "").strip().lower()))
    sugestoes: list[dict[str, str]] = []
    vistos: set[str] = set()
    for pista, method_key, categoria in _CATALOGO_METHOD_HINTS:
        if pista not in texto or method_key in vistos:
            continue
        vistos.add(method_key)
        sugestoes.append(
            {
                "method_key": method_key,
                "categoria": categoria,
                "nome_exibicao": method_key.replace("_", " ").title(),
            }
        )
    return sugestoes


def _label_catalogo(mapa: dict[str, tuple[str, str]], chave: str, fallback: str) -> dict[str, str]:
    label, tone = mapa.get(chave, (fallback, "draft"))
    return {"key": chave, "label": label, "tone": tone}


def _humanizar_slug(valor: str) -> str:
    texto = str(valor or "").strip().replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", texto).strip().title()


def _catalogo_modelo_label(codigo: str | None, *, fallback: str | None = None) -> str | None:
    codigo_norm = str(codigo or "").strip()
    if not codigo_norm:
        return fallback
    contract = dict(MASTER_TEMPLATE_REGISTRY.get(codigo_norm) or {})
    if not contract:
        contract = dict(_template_library_registry_index().get(codigo_norm) or {})
    label = str(contract.get("label") or "").strip()
    if label:
        return label
    if re.fullmatch(r"[a-z]{2,4}", codigo_norm.lower()):
        return codigo_norm.upper()
    return _humanizar_slug(codigo_norm) or fallback or codigo_norm


def _catalogo_texto_leitura(valor: str | None, *, fallback: str | None = None) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return fallback
    if re.search(r"[_-]", texto):
        return _humanizar_slug(texto)
    return texto


def _catalogo_scope_summary_label(
    *,
    allowed_modes: list[str] | None,
    allowed_templates: list[str] | None,
    allowed_variants: list[str] | None,
) -> str:
    modos = len(list(allowed_modes or []))
    modelos = len(list(allowed_templates or []))
    opcoes = len(list(allowed_variants or []))
    if modos == 0 and modelos == 0 and opcoes == 0:
        return "Sem recortes extras. A empresa segue a família completa."
    partes: list[str] = []
    if modos:
        partes.append(f"{modos} forma(s) de uso")
    if modelos:
        partes.append(f"{modelos} modelo(s) específico(s)")
    if opcoes:
        partes.append(f"{opcoes} opção(ões) liberada(s)")
    return " • ".join(partes)


def _normalizar_selection_tokens_catalogo(
    valor: str | list[str] | tuple[str, ...] | None,
    *,
    campo: str,
) -> list[str] | None:
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        itens_brutos = list(valor)
    else:
        texto = str(valor or "").strip()
        if not texto:
            return None
        if texto.startswith("["):
            payload = _normalizar_json_opcional(texto, campo=campo)
            if not isinstance(payload, list):
                raise ValueError(f"{campo} precisa ser uma lista JSON.")
            itens_brutos = payload
        else:
            itens_brutos = texto.splitlines()

    itens: list[str] = []
    vistos: set[str] = set()
    for bruto in itens_brutos:
        token = str(bruto or "").strip().lower()
        if not token or token in vistos:
            continue
        vistos.add(token)
        itens.append(token)
    return itens or None


def _normalizar_review_mode_governanca(
    valor: str | None,
    *,
    campo: str,
    allow_empty: bool = True,
) -> str | None:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": None if allow_empty else "mesa_required",
        "inherit": None if allow_empty else "mesa_required",
        "none": None if allow_empty else "mesa_required",
        "mesa_required": "mesa_required",
        "mesa": "mesa_required",
        "mobile_review_allowed": "mobile_review_allowed",
        "mobile_review": "mobile_review_allowed",
        "mobile_review_governed": "mobile_review_allowed",
        "mobile_autonomous": "mobile_autonomous",
        "autonomous": "mobile_autonomous",
        "autonomo": "mobile_autonomous",
    }
    if texto not in aliases:
        raise ValueError(f"{campo} inválido.")
    return aliases[texto]


def _normalizar_override_tristate(
    valor: str | None,
    *,
    campo: str,
) -> bool | None:
    texto = str(valor or "").strip().lower()
    aliases = {
        "": None,
        "inherit": None,
        "padrao": None,
        "allow": True,
        "permitir": True,
        "enabled": True,
        "on": True,
        "deny": False,
        "bloquear": False,
        "disabled": False,
        "off": False,
    }
    if texto not in aliases:
        raise ValueError(f"{campo} inválido.")
    return aliases[texto]


def _normalizar_planos_governanca(
    valor: str | list[str] | tuple[str, ...] | None,
    *,
    campo: str,
) -> list[str] | None:
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        itens_brutos = list(valor)
    else:
        texto = str(valor or "").strip()
        if not texto:
            return None
        if texto.startswith("["):
            payload = _normalizar_json_opcional(texto, campo=campo)
            if not isinstance(payload, list):
                raise ValueError(f"{campo} precisa ser uma lista JSON.")
            itens_brutos = payload
        else:
            itens_brutos = texto.splitlines()

    itens: list[str] = []
    vistos: set[str] = set()
    for bruto in itens_brutos:
        texto = str(bruto or "").strip()
        if not texto:
            continue
        plano = PlanoEmpresa.normalizar(texto)
        if plano in vistos:
            continue
        vistos.add(plano)
        itens.append(plano)
    return itens or None


def _normalizar_red_flags_governanca(
    valor: str | list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if valor is None:
        return None
    if isinstance(valor, list):
        itens_brutos = valor
    else:
        texto = str(valor or "").strip()
        if not texto:
            return None
        payload = _normalizar_json_opcional(texto, campo="Red flags")
        if payload is None:
            return None
        if not isinstance(payload, list):
            raise ValueError("Red flags precisam ser uma lista JSON.")
        itens_brutos = payload

    itens: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for bruto in itens_brutos:
        if not isinstance(bruto, dict):
            raise ValueError("Cada red flag precisa ser um objeto JSON.")
        title = _normalizar_texto_curto(
            str(bruto.get("title") or bruto.get("titulo") or ""),
            campo="Título da red flag",
            max_len=140,
        )
        message = _normalizar_texto_curto(
            str(bruto.get("message") or bruto.get("mensagem") or ""),
            campo="Mensagem da red flag",
            max_len=400,
        )
        code_raw = str(bruto.get("code") or bruto.get("codigo") or title)
        code = _normalizar_chave_catalogo(code_raw, campo="Código da red flag", max_len=80)
        if code in vistos:
            continue
        vistos.add(code)
        severity_key = str(bruto.get("severity") or "high").strip().lower()
        if severity_key not in _CATALOGO_RED_FLAG_SEVERITY_LABELS:
            raise ValueError("Severidade da red flag inválida.")
        source = _normalizar_texto_opcional(str(bruto.get("source") or "family_policy"), 80) or "family_policy"
        itens.append(
            {
                "code": code,
                "title": title,
                "message": message,
                "severity": severity_key,
                "blocking": bool(bruto.get("blocking", True)),
                "when_missing_required_evidence": bool(
                    bruto.get("when_missing_required_evidence", False)
                ),
                "source": source,
            }
        )
    return itens or None


def _normalizar_features_contractuais(
    valor: str | list[str] | tuple[str, ...] | None,
    *,
    campo: str,
) -> list[str] | None:
    itens = _normalizar_lista_json_canonica(valor, campo=campo, max_len_item=80)
    payload = sanitize_contract_entitlements({"included_features": itens or []})
    if payload is None:
        return None
    return list(payload.get("included_features") or []) or None


def _normalizar_bundle_comercial_payload(
    *,
    bundle_key: str = "",
    bundle_label: str = "",
    bundle_summary: str = "",
    bundle_audience: str = "",
    bundle_highlights_text: str = "",
) -> dict[str, Any] | None:
    highlights = _normalizar_lista_textual(
        bundle_highlights_text,
        campo="Destaques do bundle",
        max_len_item=120,
    )
    return sanitize_commercial_bundle(
        {
            "bundle_key": _normalizar_chave_catalogo(bundle_key, campo="Bundle key", max_len=80)
            if str(bundle_key or "").strip()
            else "",
            "bundle_label": _normalizar_texto_opcional(bundle_label, 120),
            "summary": _normalizar_texto_opcional(bundle_summary, 240),
            "audience": _normalizar_texto_opcional(bundle_audience, 120),
            "highlights": highlights or [],
        }
    )


def _normalizar_contract_entitlements_payload(
    *,
    included_features_text: str = "",
    monthly_issues: int | str | None = None,
    max_admin_clients: int | str | None = None,
    max_inspectors: int | str | None = None,
    max_reviewers: int | str | None = None,
    max_active_variants: int | str | None = None,
    max_integrations: int | str | None = None,
) -> dict[str, Any] | None:
    return sanitize_contract_entitlements(
        {
            "included_features": _normalizar_features_contractuais(
                included_features_text,
                campo="Features contratuais",
            )
            or [],
            "limits": {
                "monthly_issues": _normalizar_limite_contractual(
                    monthly_issues,
                    campo="Limite mensal de emissões",
                ),
                "max_admin_clients": _normalizar_limite_contractual(
                    max_admin_clients,
                    campo="Limite de admins-cliente",
                ),
                "max_inspectors": _normalizar_limite_contractual(
                    max_inspectors,
                    campo="Limite de inspetores",
                ),
                "max_reviewers": _normalizar_limite_contractual(
                    max_reviewers,
                    campo="Limite de revisores",
                ),
                "max_active_variants": _normalizar_limite_contractual(
                    max_active_variants,
                    campo="Limite de variantes ativas",
                ),
                "max_integrations": _normalizar_limite_contractual(
                    max_integrations,
                    campo="Limite de integrações",
                ),
            },
        }
    )


def _review_mode_label_meta(review_mode: str | None) -> dict[str, str]:
    resolved = (
        _normalizar_review_mode_governanca(review_mode, campo="Review mode")
        if review_mode
        else None
    )
    if resolved is None:
        return {"key": "inherit", "label": "Herdado", "tone": "idle"}
    return _label_catalogo(
        _CATALOGO_REVIEW_MODE_LABELS,
        resolved,
        resolved.replace("_", " "),
    )


def _override_choice_label(value: bool | None) -> dict[str, str]:
    key = "inherit" if value is None else "allow" if value else "deny"
    tone = "idle" if value is None else "active" if value else "review"
    return {
        "key": key,
        "label": _CATALOGO_REVIEW_OVERRIDE_LABELS[key],
        "tone": tone,
    }


def _red_flag_severity_meta(severity: str | None) -> dict[str, str]:
    key = str(severity or "high").strip().lower()
    return _label_catalogo(
        _CATALOGO_RED_FLAG_SEVERITY_LABELS,
        key,
        key or "high",
    )


def _effective_review_mode_cap(*review_modes: str | None) -> str | None:
    normalized = [
        mode
        for mode in (
            _normalizar_review_mode_governanca(item, campo="Review mode")
            if item is not None
            else None
            for item in review_modes
        )
        if mode is not None
    ]
    if not normalized:
        return None
    return sorted(normalized, key=lambda item: _REVIEW_MODE_ORDER[item], reverse=True)[0]


def _merge_review_policy_governance(
    base_policy: dict[str, Any] | None,
    *,
    default_review_mode: str | None,
    max_review_mode: str | None,
    requires_family_lock: bool,
    block_on_scope_mismatch: bool,
    block_on_missing_required_evidence: bool,
    block_on_critical_field_absent: bool,
    blocking_conditions: list[str] | None,
    non_blocking_conditions: list[str] | None,
    red_flags: list[dict[str, Any]] | None,
    requires_release_active: bool,
    requires_upload_doc_for_mobile_autonomous: bool,
    mobile_review_allowed_plans: list[str] | None,
    mobile_autonomous_allowed_plans: list[str] | None,
) -> dict[str, Any]:
    review_policy = dict(base_policy or {})
    tenant_entitlements = (
        dict(review_policy.get("tenant_entitlements") or {})
        if isinstance(review_policy.get("tenant_entitlements"), dict)
        else {}
    )

    managed_keys = {
        "default_review_mode",
        "max_review_mode",
        "requires_family_lock",
        "block_on_scope_mismatch",
        "block_on_missing_required_evidence",
        "block_on_critical_field_absent",
        "blocking_conditions",
        "non_blocking_conditions",
        "red_flags",
        "tenant_entitlements",
    }
    review_policy = {
        key: value
        for key, value in review_policy.items()
        if key not in managed_keys
    }

    if default_review_mode:
        review_policy["default_review_mode"] = default_review_mode
    if max_review_mode:
        review_policy["max_review_mode"] = max_review_mode
    review_policy["requires_family_lock"] = bool(requires_family_lock)
    review_policy["block_on_scope_mismatch"] = bool(block_on_scope_mismatch)
    review_policy["block_on_missing_required_evidence"] = bool(
        block_on_missing_required_evidence
    )
    review_policy["block_on_critical_field_absent"] = bool(
        block_on_critical_field_absent
    )
    if blocking_conditions:
        review_policy["blocking_conditions"] = blocking_conditions
    if non_blocking_conditions:
        review_policy["non_blocking_conditions"] = non_blocking_conditions
    if red_flags:
        review_policy["red_flags"] = red_flags

    tenant_entitlements = {
        key: value
        for key, value in tenant_entitlements.items()
        if key
        not in {
            "requires_release_active",
            "requires_upload_doc_for_mobile_autonomous",
            "mobile_review_allowed_plans",
            "mobile_review_plans",
            "mobile_autonomous_allowed_plans",
            "mobile_autonomous_plans",
        }
    }
    tenant_entitlements["requires_release_active"] = bool(requires_release_active)
    tenant_entitlements["requires_upload_doc_for_mobile_autonomous"] = bool(
        requires_upload_doc_for_mobile_autonomous
    )
    if mobile_review_allowed_plans:
        tenant_entitlements["mobile_review_allowed_plans"] = mobile_review_allowed_plans
    if mobile_autonomous_allowed_plans:
        tenant_entitlements["mobile_autonomous_allowed_plans"] = (
            mobile_autonomous_allowed_plans
        )
    review_policy["tenant_entitlements"] = tenant_entitlements
    return review_policy


def _merge_release_governance_policy(
    base_policy: dict[str, Any] | None,
    *,
    force_review_mode: str | None,
    max_review_mode: str | None,
    mobile_review_override: bool | None,
    mobile_autonomous_override: bool | None,
    release_channel_override: str | None,
    contract_entitlements: dict[str, Any] | None,
) -> dict[str, Any] | None:
    governance_policy = dict(base_policy or {})
    managed_keys = {
        "force_review_mode",
        "max_review_mode",
        "mobile_review_override",
        "mobile_autonomous_override",
        "release_channel_override",
        "contract_entitlements",
    }
    governance_policy = {
        key: value
        for key, value in governance_policy.items()
        if key not in managed_keys
    }
    if force_review_mode:
        governance_policy["force_review_mode"] = force_review_mode
    if max_review_mode:
        governance_policy["max_review_mode"] = max_review_mode
    if mobile_review_override is not None:
        governance_policy["mobile_review_override"] = mobile_review_override
    if mobile_autonomous_override is not None:
        governance_policy["mobile_autonomous_override"] = mobile_autonomous_override
    governance_policy = merge_release_contract_policy(
        governance_policy,
        release_channel_override=release_channel_override,
        contract_entitlements=contract_entitlements,
    ) or {}
    return governance_policy or None


def _resumir_governanca_review_policy(review_policy: Any) -> dict[str, Any]:
    payload = dict(review_policy or {}) if isinstance(review_policy, dict) else {}
    tenant_entitlements = (
        dict(payload.get("tenant_entitlements") or {})
        if isinstance(payload.get("tenant_entitlements"), dict)
        else {}
    )
    red_flags = _normalizar_red_flags_governanca(list(payload.get("red_flags") or [])) or []
    blocking_conditions = _normalizar_lista_textual(
        json.dumps(list(payload.get("blocking_conditions") or []), ensure_ascii=False),
        campo="Blocking conditions",
    ) or []
    non_blocking_conditions = _normalizar_lista_textual(
        json.dumps(list(payload.get("non_blocking_conditions") or []), ensure_ascii=False),
        campo="Non-blocking conditions",
    ) or []
    review_plans = _normalizar_planos_governanca(
        list(
            tenant_entitlements.get("mobile_review_allowed_plans")
            or tenant_entitlements.get("mobile_review_plans")
            or []
        ),
        campo="Planos com revisão mobile",
    ) or []
    autonomy_plans = _normalizar_planos_governanca(
        list(
            tenant_entitlements.get("mobile_autonomous_allowed_plans")
            or tenant_entitlements.get("mobile_autonomous_plans")
            or []
        ),
        campo="Planos com autonomia mobile",
    ) or []
    return {
        "default_review_mode": _review_mode_label_meta(
            payload.get("default_review_mode")
        ),
        "max_review_mode": _review_mode_label_meta(payload.get("max_review_mode")),
        "requires_family_lock": bool(payload.get("requires_family_lock")),
        "block_on_scope_mismatch": bool(payload.get("block_on_scope_mismatch")),
        "block_on_missing_required_evidence": bool(
            payload.get("block_on_missing_required_evidence")
        ),
        "block_on_critical_field_absent": bool(
            payload.get("block_on_critical_field_absent")
        ),
        "blocking_conditions": blocking_conditions,
        "non_blocking_conditions": non_blocking_conditions,
        "red_flags": [
            {
                **item,
                "severity_meta": _red_flag_severity_meta(item.get("severity")),
            }
            for item in red_flags
        ],
        "red_flags_count": len(red_flags),
        "tenant_entitlements": {
            "requires_release_active": bool(
                tenant_entitlements.get("requires_release_active")
            ),
            "requires_upload_doc_for_mobile_autonomous": bool(
                tenant_entitlements.get("requires_upload_doc_for_mobile_autonomous")
            ),
            "mobile_review_allowed_plans": review_plans,
            "mobile_autonomous_allowed_plans": autonomy_plans,
        },
    }


def _resumir_governanca_release_policy(governance_policy: Any) -> dict[str, Any]:
    payload = (
        dict(governance_policy or {})
        if isinstance(governance_policy, dict)
        else {}
    )
    review_override = payload.get("mobile_review_override")
    autonomy_override = payload.get("mobile_autonomous_override")
    if not isinstance(review_override, bool):
        review_override = None
    if not isinstance(autonomy_override, bool):
        autonomy_override = None
    force_review_mode = _normalizar_review_mode_governanca(
        payload.get("force_review_mode"),
        campo="Force review mode",
    )
    max_review_mode = _normalizar_review_mode_governanca(
        payload.get("max_review_mode"),
        campo="Max review mode",
    )
    effective_cap = _effective_review_mode_cap(force_review_mode, max_review_mode)
    commercial = summarize_release_contract_governance(governance_policy)
    return {
        "force_review_mode": _review_mode_label_meta(force_review_mode),
        "max_review_mode": _review_mode_label_meta(max_review_mode),
        "mobile_review_override": _override_choice_label(review_override),
        "mobile_autonomous_override": _override_choice_label(autonomy_override),
        "effective_cap": _review_mode_label_meta(effective_cap),
        "release_channel_override": commercial["release_channel_override"],
        "effective_release_channel": commercial["effective_release_channel"],
        "contract_entitlements_override": commercial["contract_entitlements_override"],
        "effective_contract_entitlements": commercial["effective_contract_entitlements"],
        "has_overrides": any(
            (
                force_review_mode is not None,
                max_review_mode is not None,
                review_override is not None,
                autonomy_override is not None,
                commercial["release_channel_override"]["key"] != "inherit",
                commercial["contract_entitlements_override"]["has_data"],
            )
        ),
    }


def _review_mode_display_order() -> tuple[str, str, str]:
    return ("mesa_required", "mobile_review_allowed", "mobile_autonomous")


def _review_mode_with_cap(requested_mode: str, cap_mode: str | None) -> str:
    if not cap_mode:
        return requested_mode
    return sorted(
        (requested_mode, cap_mode),
        key=lambda item: _REVIEW_MODE_ORDER[item],
        reverse=True,
    )[0]


def _plan_allowed_for_governance_rollup(
    *,
    plan_name: str | None,
    allowed_plans: list[str],
) -> bool:
    if not allowed_plans:
        return True
    try:
        normalized_plan = PlanoEmpresa.normalizar(str(plan_name or "").strip())
    except ValueError:
        normalized_plan = str(plan_name or "").strip()
    return normalized_plan.lower() in {item.lower() for item in allowed_plans}


def _strictest_review_mode(counter: Counter[str]) -> str | None:
    modes = [mode for mode in _review_mode_display_order() if int(counter.get(mode, 0)) > 0]
    if not modes:
        return None
    return sorted(modes, key=lambda item: _REVIEW_MODE_ORDER[item], reverse=True)[0]


def _dominant_review_mode(counter: Counter[str]) -> str | None:
    modes = [mode for mode in _review_mode_display_order() if int(counter.get(mode, 0)) > 0]
    if not modes:
        return None
    return sorted(
        modes,
        key=lambda item: (int(counter.get(item, 0)), _REVIEW_MODE_ORDER[item]),
        reverse=True,
    )[0]


def _format_review_mode_breakdown(counter: Counter[str]) -> str:
    partes = [
        f"{int(counter.get(mode, 0))} {str(_review_mode_label_meta(mode)['label'])}"
        for mode in _review_mode_display_order()
        if int(counter.get(mode, 0)) > 0
    ]
    return " • ".join(partes)


def _release_channel_display_order() -> tuple[str, str, str]:
    return ("pilot", "limited_release", "general_release")


def _dominant_release_channel(counter: Counter[str], *, fallback: str = "pilot") -> str:
    channels = [
        channel
        for channel in _release_channel_display_order()
        if int(counter.get(channel, 0)) > 0
    ]
    if not channels:
        return fallback
    return sorted(
        channels,
        key=lambda item: (int(counter.get(item, 0)), RELEASE_CHANNEL_ORDER.get(item, 0)),
        reverse=True,
    )[0]


def _build_review_mode_counter_rows(
    counter: Counter[str],
    *,
    total: int,
    tenant_sets: dict[str, set[int]] | None = None,
    family_sets: dict[str, set[str]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mode in _review_mode_display_order():
        count = int(counter.get(mode, 0))
        rows.append(
            {
                "mode": _review_mode_label_meta(mode),
                "count": count,
                "share": round((count / total) * 100, 1) if total else 0.0,
                "tenant_count": len((tenant_sets or {}).get(mode, set())),
                "family_count": len((family_sets or {}).get(mode, set())),
            }
        )
    return rows


def _build_release_channel_counter_rows(
    counter: Counter[str],
    *,
    total: int,
    tenant_sets: dict[str, set[int]] | None = None,
    family_sets: dict[str, set[str]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for channel in _release_channel_display_order():
        count = int(counter.get(channel, 0))
        rows.append(
            {
                "channel": release_channel_meta(channel),
                "count": count,
                "share": round((count / total) * 100, 1) if total else 0.0,
                "tenant_count": len((tenant_sets or {}).get(channel, set())),
                "family_count": len((family_sets or {}).get(channel, set())),
            }
        )
    return rows


def _build_release_status_counter_rows(counter: Counter[str], *, total: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for status in ("active", "draft", "paused", "expired"):
        count = int(counter.get(status, 0))
        rows.append(
            {
                "status": _label_catalogo(
                    _CATALOGO_RELEASE_STATUS_LABELS,
                    status,
                    status or "draft",
                ),
                "count": count,
                "share": round((count / total) * 100, 1) if total else 0.0,
            }
        )
    return rows


def _resolve_governance_rollup_release_mode(
    *,
    family: FamiliaLaudoCatalogo,
    release: TenantFamilyReleaseLaudo,
    tenant: Empresa | None,
) -> dict[str, Any]:
    oferta = getattr(family, "oferta_comercial", None)
    review_policy = (
        dict(getattr(family, "review_policy_json", None) or {})
        if isinstance(getattr(family, "review_policy_json", None), dict)
        else {}
    )
    tenant_entitlements = (
        dict(review_policy.get("tenant_entitlements") or {})
        if isinstance(review_policy.get("tenant_entitlements"), dict)
        else {}
    )
    release_policy = (
        dict(getattr(release, "governance_policy_json", None) or {})
        if isinstance(getattr(release, "governance_policy_json", None), dict)
        else {}
    )

    default_review_mode = (
        _normalizar_review_mode_governanca(
            review_policy.get("default_review_mode"),
            campo="Default review mode",
        )
        or "mesa_required"
    )
    family_max_review_mode = (
        _normalizar_review_mode_governanca(
            review_policy.get("max_review_mode"),
            campo="Max review mode",
        )
        or "mobile_autonomous"
    )
    release_force_review_mode = _normalizar_review_mode_governanca(
        release_policy.get("force_review_mode"),
        campo="Force review mode",
    )
    release_max_review_mode = _normalizar_review_mode_governanca(
        release_policy.get("max_review_mode"),
        campo="Release max review mode",
    )
    effective_cap = (
        _effective_review_mode_cap(family_max_review_mode, release_max_review_mode)
        or family_max_review_mode
    )
    requested_review_mode = release_force_review_mode or default_review_mode
    capped_review_mode = _review_mode_with_cap(requested_review_mode, effective_cap)

    review_allowed_plans = _normalizar_planos_governanca(
        list(
            tenant_entitlements.get("mobile_review_allowed_plans")
            or tenant_entitlements.get("mobile_review_plans")
            or []
        ),
        campo="Planos com revisão mobile",
    ) or []
    autonomy_allowed_plans = _normalizar_planos_governanca(
        list(
            tenant_entitlements.get("mobile_autonomous_allowed_plans")
            or tenant_entitlements.get("mobile_autonomous_plans")
            or []
        ),
        campo="Planos com autonomia mobile",
    ) or []

    review_override = release_policy.get("mobile_review_override")
    if not isinstance(review_override, bool):
        review_override = None
    autonomy_override = release_policy.get("mobile_autonomous_override")
    if not isinstance(autonomy_override, bool):
        autonomy_override = None

    tenant_plan = str(getattr(tenant, "plano_ativo", "") or "").strip() or None
    tenant_blocked = bool(getattr(tenant, "status_bloqueio", False))
    mobile_review_allowed = _plan_allowed_for_governance_rollup(
        plan_name=tenant_plan,
        allowed_plans=review_allowed_plans,
    )
    mobile_autonomous_allowed = _plan_allowed_for_governance_rollup(
        plan_name=tenant_plan,
        allowed_plans=autonomy_allowed_plans,
    )
    if review_override is not None:
        mobile_review_allowed = review_override
    if autonomy_override is not None:
        mobile_autonomous_allowed = autonomy_override
    if tenant_blocked:
        mobile_review_allowed = False
        mobile_autonomous_allowed = False
    if not mobile_review_allowed:
        mobile_autonomous_allowed = False

    effective_review_mode = capped_review_mode
    if effective_review_mode == "mobile_autonomous" and not mobile_autonomous_allowed:
        effective_review_mode = "mobile_review_allowed" if mobile_review_allowed else "mesa_required"
    elif effective_review_mode == "mobile_review_allowed" and not mobile_review_allowed:
        effective_review_mode = "mesa_required"

    commercial = summarize_release_contract_governance(
        getattr(release, "governance_policy_json", None),
        offer_flags_payload=getattr(oferta, "flags_json", None) if oferta is not None else None,
        offer_lifecycle_status=_offer_lifecycle_resolvido(oferta),
    )

    return {
        "effective_review_mode": effective_review_mode,
        "requested_review_mode": requested_review_mode,
        "effective_cap": effective_cap,
        "default_review_mode": default_review_mode,
        "mobile_review_allowed": bool(mobile_review_allowed),
        "mobile_autonomous_allowed": bool(mobile_autonomous_allowed),
        "tenant_plan": tenant_plan,
        "tenant_blocked": tenant_blocked,
        "effective_release_channel": commercial["effective_release_channel"]["key"],
        "red_flags_count": len(
            _normalizar_red_flags_governanca(list(review_policy.get("red_flags") or []))
            or []
        ),
    }


def _build_catalog_governance_rollup(
    db: Session,
    *,
    families: list[FamiliaLaudoCatalogo],
) -> dict[str, Any]:
    tenant_ids = {
        int(getattr(release, "tenant_id", 0) or 0)
        for family in families
        for release in list(getattr(family, "tenant_releases", None) or [])
        if int(getattr(release, "tenant_id", 0) or 0) > 0
    }
    tenant_lookup = {
        int(item.id): item
        for item in list(
            db.scalars(
                select(Empresa).where(
                    Empresa.id.in_(tenant_ids) if tenant_ids else False,
                    _tenant_cliente_clause(),
                )
            ).all()
        )
    } if tenant_ids else {}

    family_default_counter: Counter[str] = Counter()
    release_status_counter: Counter[str] = Counter()
    active_release_counter: Counter[str] = Counter()
    active_channel_counter: Counter[str] = Counter()
    release_channel_tenants: dict[str, set[int]] = defaultdict(set)
    release_channel_families: dict[str, set[str]] = defaultdict(set)
    release_mode_tenants: dict[str, set[int]] = defaultdict(set)
    release_mode_families: dict[str, set[str]] = defaultdict(set)
    tenant_mode_counters: dict[int, Counter[str]] = defaultdict(Counter)
    tenant_meta: dict[int, dict[str, Any]] = {}
    family_highlights: list[dict[str, Any]] = []
    family_red_flags_total = 0
    families_with_red_flags = 0

    for family in families:
        family_key = str(getattr(family, "family_key", "") or "").strip()
        family_label = str(getattr(family, "nome_exibicao", "") or family_key)
        review_policy = (
            dict(getattr(family, "review_policy_json", None) or {})
            if isinstance(getattr(family, "review_policy_json", None), dict)
            else {}
        )
        family_default_mode = (
            _normalizar_review_mode_governanca(
                review_policy.get("default_review_mode"),
                campo="Default review mode",
            )
            or "mesa_required"
        )
        family_default_counter[family_default_mode] += 1
        red_flags_count = len(
            _normalizar_red_flags_governanca(list(review_policy.get("red_flags") or []))
            or []
        )
        family_red_flags_total += red_flags_count
        if red_flags_count > 0:
            families_with_red_flags += 1

        family_release_counter: Counter[str] = Counter()
        family_release_channel_counter: Counter[str] = Counter()
        family_release_tenants: set[int] = set()

        for release in list(getattr(family, "tenant_releases", None) or []):
            tenant_id = int(getattr(release, "tenant_id", 0) or 0)
            tenant = tenant_lookup.get(tenant_id)
            if tenant is None:
                continue

            release_status = str(getattr(release, "release_status", "") or "draft").strip().lower() or "draft"
            release_status_counter[release_status] += 1
            if release_status != "active":
                continue

            resolved = _resolve_governance_rollup_release_mode(
                family=family,
                release=release,
                tenant=tenant,
            )
            effective_mode = str(resolved["effective_review_mode"])
            effective_channel = str(resolved.get("effective_release_channel") or "pilot")
            active_release_counter[effective_mode] += 1
            active_channel_counter[effective_channel] += 1
            release_mode_tenants[effective_mode].add(tenant_id)
            release_mode_families[effective_mode].add(family_key)
            release_channel_tenants[effective_channel].add(tenant_id)
            release_channel_families[effective_channel].add(family_key)
            family_release_counter[effective_mode] += 1
            family_release_channel_counter[effective_channel] += 1
            family_release_tenants.add(tenant_id)
            tenant_mode_counters[tenant_id][effective_mode] += 1
            tenant_meta[tenant_id] = {
                "tenant_id": tenant_id,
                "tenant_label": str(getattr(tenant, "nome_fantasia", "") or f"Tenant {tenant_id}"),
                "plan_label": str(getattr(tenant, "plano_ativo", "") or "Sem plano"),
                "blocked": bool(getattr(tenant, "status_bloqueio", False)),
            }

        if sum(int(item) for item in family_release_counter.values()) <= 0:
            continue

        dominant_mode = _dominant_review_mode(family_release_counter) or family_default_mode
        family_highlights.append(
            {
                "family_key": family_key,
                "family_label": family_label,
                "active_release_count": sum(int(item) for item in family_release_counter.values()),
                "tenant_count": len(family_release_tenants),
                "red_flags_count": red_flags_count,
                "default_review_mode": _review_mode_label_meta(family_default_mode),
                "dominant_mode": _review_mode_label_meta(dominant_mode),
                "release_channel": release_channel_meta(
                    _dominant_release_channel(family_release_channel_counter, fallback="pilot")
                ),
                "mode_breakdown": _build_review_mode_counter_rows(
                    family_release_counter,
                    total=sum(int(item) for item in family_release_counter.values()),
                ),
                "mode_breakdown_label": _format_review_mode_breakdown(family_release_counter),
            }
        )

    tenant_highlights: list[dict[str, Any]] = []
    tenant_strictest_counter: Counter[str] = Counter()
    for tenant_id, counter in tenant_mode_counters.items():
        strictest_mode = _strictest_review_mode(counter)
        if strictest_mode is None:
            continue
        tenant_strictest_counter[strictest_mode] += 1
        meta = tenant_meta.get(tenant_id, {})
        tenant_highlights.append(
            {
                "tenant_id": tenant_id,
                "tenant_label": str(meta.get("tenant_label") or f"Tenant {tenant_id}"),
                "plan_label": str(meta.get("plan_label") or "Sem plano"),
                "blocked": bool(meta.get("blocked")),
                "active_release_count": sum(int(item) for item in counter.values()),
                "strictest_mode": _review_mode_label_meta(strictest_mode),
                "mode_breakdown": _build_review_mode_counter_rows(
                    counter,
                    total=sum(int(item) for item in counter.values()),
                ),
                "mode_breakdown_label": _format_review_mode_breakdown(counter),
            }
        )

    tenant_highlights.sort(
        key=lambda item: (
            -_REVIEW_MODE_ORDER[str((item["strictest_mode"] or {}).get("key") or "mesa_required")],
            -int(item["active_release_count"]),
            str(item["tenant_label"]).lower(),
        )
    )
    family_highlights.sort(
        key=lambda item: (
            -int(item["active_release_count"]),
            -_REVIEW_MODE_ORDER[str((item["dominant_mode"] or {}).get("key") or "mesa_required")],
            str(item["family_label"]).lower(),
        )
    )

    total_active_releases = sum(int(item) for item in active_release_counter.values())
    total_releases = sum(int(item) for item in release_status_counter.values())
    return {
        "scope_family_count": len(families),
        "families_with_active_release_count": len(family_highlights),
        "families_with_red_flags_count": int(families_with_red_flags),
        "family_red_flags_total": int(family_red_flags_total),
        "tenant_count": len(tenant_highlights),
        "active_release_count": int(total_active_releases),
        "inactive_release_count": int(total_releases - total_active_releases),
        "family_default_modes": _build_review_mode_counter_rows(
            family_default_counter,
            total=len(families),
        ),
        "effective_release_modes": _build_review_mode_counter_rows(
            active_release_counter,
            total=total_active_releases,
            tenant_sets=release_mode_tenants,
            family_sets=release_mode_families,
        ),
        "effective_release_channels": _build_release_channel_counter_rows(
            active_channel_counter,
            total=total_active_releases,
            tenant_sets=release_channel_tenants,
            family_sets=release_channel_families,
        ),
        "tenant_strictest_modes": _build_review_mode_counter_rows(
            tenant_strictest_counter,
            total=len(tenant_highlights),
        ),
        "release_status_counts": _build_release_status_counter_rows(
            release_status_counter,
            total=total_releases,
        ),
        "tenant_highlights": tenant_highlights[:6],
        "family_highlights": family_highlights[:6],
    }


def _repo_root_dir() -> Path:
    return Path(__file__).resolve().parents[4]


def _family_schemas_dir() -> Path:
    candidate = (_repo_root_dir() / "docs" / "family_schemas").resolve()
    if candidate.is_dir():
        return candidate
    return resolve_family_schemas_dir()


def _ler_json_arquivo(path: Path, *, campo: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as erro:
        raise ValueError(f"{campo} não encontrado em {path.name}.") from erro
    except json.JSONDecodeError as erro:
        raise ValueError(f"{campo} inválido em {path.name}.") from erro
    if not isinstance(payload, dict):
        raise ValueError(f"{campo} em {path.name} precisa ser um objeto JSON.")
    return payload


def _family_schema_file_path(family_key: str) -> Path:
    family_key_norm = _normalizar_chave_catalogo(family_key, campo="Family key", max_len=120)
    return (_family_schemas_dir() / f"{family_key_norm}.json").resolve()


def _family_artifact_file_path(family_key: str, artifact_suffix: str) -> Path:
    family_key_norm = _normalizar_chave_catalogo(family_key, campo="Family key", max_len=120)
    return (_family_schemas_dir() / f"{family_key_norm}{artifact_suffix}").resolve()

def listar_catalogo_familias(
    db: Session,
    *,
    filtro_status: str = "",
    filtro_busca: str = "",
    filtro_classificacao: str = "family",
) -> list[FamiliaLaudoCatalogo]:
    stmt = select(FamiliaLaudoCatalogo).options(
        selectinload(FamiliaLaudoCatalogo.oferta_comercial),
        selectinload(FamiliaLaudoCatalogo.modos_tecnicos),
        selectinload(FamiliaLaudoCatalogo.calibracao),
        selectinload(FamiliaLaudoCatalogo.tenant_releases),
    )

    status = str(filtro_status or "").strip()
    if status:
        status_norm = _normalizar_status_catalogo_familia(status)
        technical_norm = _normalizar_status_tecnico_catalogo(status)
        stmt = stmt.where(
            (FamiliaLaudoCatalogo.status_catalogo == status_norm)
            | (FamiliaLaudoCatalogo.technical_status == technical_norm)
        )

    classificacao = str(filtro_classificacao or "").strip()
    if classificacao:
        stmt = stmt.where(
            FamiliaLaudoCatalogo.catalog_classification == _normalizar_classificacao_catalogo(classificacao)
        )

    busca = str(filtro_busca or "").strip()
    if busca:
        termo = f"%{busca}%"
        stmt = stmt.where(
            FamiliaLaudoCatalogo.family_key.ilike(termo)
            | FamiliaLaudoCatalogo.nome_exibicao.ilike(termo)
            | FamiliaLaudoCatalogo.macro_categoria.ilike(termo)
        )

    stmt = stmt.order_by(
        FamiliaLaudoCatalogo.technical_status.asc(),
        FamiliaLaudoCatalogo.macro_categoria.asc(),
        FamiliaLaudoCatalogo.nome_exibicao.asc(),
    )
    return list(db.scalars(stmt).all())


def listar_ofertas_comerciais_catalogo(
    db: Session,
    *,
    filtro_lifecycle: str = "",
) -> list[OfertaComercialFamiliaLaudo]:
    stmt = (
        select(OfertaComercialFamiliaLaudo)
        .options(selectinload(OfertaComercialFamiliaLaudo.familia))
        .join(FamiliaLaudoCatalogo, OfertaComercialFamiliaLaudo.family_id == FamiliaLaudoCatalogo.id)
    )
    lifecycle = str(filtro_lifecycle or "").strip()
    if lifecycle:
        stmt = stmt.where(OfertaComercialFamiliaLaudo.lifecycle_status == _normalizar_lifecycle_status_oferta(lifecycle))
    stmt = stmt.order_by(
        OfertaComercialFamiliaLaudo.lifecycle_status.asc(),
        OfertaComercialFamiliaLaudo.material_level.desc(),
        FamiliaLaudoCatalogo.macro_categoria.asc(),
        OfertaComercialFamiliaLaudo.nome_oferta.asc(),
    )
    return list(db.scalars(stmt).all())


def listar_family_schemas_canonicos() -> list[dict[str, Any]]:
    diretorio = _family_schemas_dir()
    if not diretorio.exists():
        return []

    itens: list[dict[str, Any]] = []
    for path in sorted(diretorio.glob("*.json")):
        nome = path.name
        if (
            nome.endswith(".laudo_output_seed.json")
            or nome.endswith(".laudo_output_exemplo.json")
            or nome.endswith(".template_master_seed.json")
        ):
            continue
        payload = _ler_json_arquivo(path, campo="Family schema canônico")
        family_key = _normalizar_chave_catalogo(payload.get("family_key") or path.stem, campo="Family key", max_len=120)
        nome_exibicao = str(payload.get("nome_exibicao") or family_key)
        macro_categoria = str(payload.get("macro_categoria") or "")
        itens.append(
            {
                "family_key": family_key,
                "nome_exibicao": nome_exibicao,
                "macro_categoria": macro_categoria,
                "catalog_classification": _inferir_classificacao_catalogo(
                    family_key=family_key,
                    nome_exibicao=nome_exibicao,
                    macro_categoria=macro_categoria,
                ),
                "schema_version": int(payload.get("schema_version") or 1),
                "has_template_seed": _family_artifact_file_path(family_key, ".template_master_seed.json").exists(),
                "has_laudo_output_seed": _family_artifact_file_path(family_key, ".laudo_output_seed.json").exists(),
                "has_laudo_output_exemplo": _family_artifact_file_path(family_key, ".laudo_output_exemplo.json").exists(),
                "path": str(path),
            }
        )
    return itens


def carregar_family_schema_canonico(family_key: str) -> dict[str, Any]:
    path = _family_schema_file_path(family_key)
    payload = _ler_json_arquivo(path, campo="Family schema canônico")
    family_key_payload = _normalizar_chave_catalogo(
        payload.get("family_key") or path.stem,
        campo="Family key",
        max_len=120,
    )
    if family_key_payload != _normalizar_chave_catalogo(family_key, campo="Family key", max_len=120):
        raise ValueError("Family schema canônico com chave divergente do arquivo.")
    return payload


def _buscar_familia_catalogo_por_chave(db: Session, family_key: str) -> FamiliaLaudoCatalogo:
    family_key_norm = _normalizar_chave_catalogo(family_key, campo="Família", max_len=120)
    familia = db.scalar(select(FamiliaLaudoCatalogo).where(FamiliaLaudoCatalogo.family_key == family_key_norm))
    if familia is None:
        raise ValueError("Família do catálogo não encontrada.")
    return familia


def _catalog_family_artifact_snapshot(family_key: str) -> dict[str, bool]:
    family_key_norm = _normalizar_chave_catalogo(family_key, campo="Family key", max_len=120)
    return {
        "has_family_schema": _family_schema_file_path(family_key_norm).exists(),
        "has_template_seed": _family_artifact_file_path(family_key_norm, ".template_master_seed.json").exists(),
        "has_laudo_output_seed": _family_artifact_file_path(family_key_norm, ".laudo_output_seed.json").exists(),
        "has_laudo_output_exemplo": _family_artifact_file_path(family_key_norm, ".laudo_output_exemplo.json").exists(),
    }


def _repo_relative_path_label(path: Path | None) -> str | None:
    if path is None:
        return None
    canonical_label = canonical_docs_logical_path(path)
    if canonical_label is not None:
        return canonical_label
    try:
        return str(path.resolve().relative_to(_repo_root_dir())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _template_library_registry_path() -> Path:
    candidate = (_repo_root_dir() / "docs" / "master_templates" / "library_registry.json").resolve()
    if candidate.exists():
        return candidate
    return (resolve_master_templates_dir() / "library_registry.json").resolve()


def _load_template_library_registry() -> dict[str, Any]:
    path = _template_library_registry_path()
    if not path.exists():
        return {"version": 0, "templates": []}
    payload = _ler_json_arquivo(path, campo="Library registry")
    templates = payload.get("templates")
    if not isinstance(templates, list):
        payload["templates"] = []
    return payload


def _build_template_library_rollup(rows_all: list[dict[str, Any]]) -> dict[str, Any]:
    registry = _load_template_library_registry()
    templates = [
        item
        for item in list(registry.get("templates") or [])
        if isinstance(item, dict)
    ]
    ready_templates = [
        item for item in templates if str(item.get("status") or "").strip().lower() == "ready"
    ]
    families_with_full_artifacts = sum(
        1
        for item in rows_all
        if all(bool(item["artifact_snapshot"].get(key)) for key in (
            "has_family_schema",
            "has_template_seed",
            "has_laudo_output_seed",
            "has_laudo_output_exemplo",
        ))
    )
    families_with_template_default = sum(
        1 for item in rows_all if str(item.get("template_default_code") or "").strip()
    )
    return {
        "registry_path": _repo_relative_path_label(_template_library_registry_path()),
        "registry_version": int(registry.get("version") or 0),
        "template_count": len(templates),
        "ready_template_count": len(ready_templates),
        "demonstration_ready_count": int(families_with_full_artifacts),
        "families_with_full_artifacts": int(families_with_full_artifacts),
        "families_with_template_default": int(families_with_template_default),
        "sellable_family_count": sum(
            1 for item in rows_all if str((item["readiness"] or {}).get("key") or "") in {"sellable", "calibrated"}
        ),
        "templates": [
            {
                "master_template_id": str(item.get("master_template_id") or "").strip() or None,
                "label": str(item.get("label") or "").strip() or "Template premium",
                "documental_type": str(item.get("documental_type") or "").strip() or None,
                "status": _label_catalogo(
                    {"ready": ("Pronto", "active"), "draft": ("Rascunho", "draft")},
                    str(item.get("status") or "").strip().lower() or "draft",
                    "Rascunho",
                ),
                "artifact_path": str(item.get("artifact_path") or "").strip() or None,
                "usage": str(item.get("usage") or "").strip() or None,
            }
            for item in templates[:6]
        ],
    }


def _template_library_registry_index() -> dict[str, dict[str, Any]]:
    registry = _load_template_library_registry()
    index: dict[str, dict[str, Any]] = {}
    for item in list(registry.get("templates") or []):
        if not isinstance(item, dict):
            continue
        master_template_id = str(item.get("master_template_id") or "").strip()
        if not master_template_id:
            continue
        index[master_template_id] = item
    return index


def _material_real_workspace_roots() -> list[Path]:
    docs_dir = (_repo_root_dir() / "docs").resolve()
    return sorted(path for path in docs_dir.glob("portfolio_empresa_*_material_real") if path.is_dir())


def _find_material_real_workspace(family_key: str) -> Path | None:
    family_key_norm = _normalizar_chave_catalogo(family_key, campo="Family key", max_len=120)
    for root in _material_real_workspace_roots():
        candidate = (root / family_key_norm).resolve()
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _build_material_real_workspace_summary(family_key: str) -> dict[str, Any] | None:
    workspace = _find_material_real_workspace(family_key)
    if workspace is None:
        return None
    status_path = (workspace / "status_refino.json").resolve()
    briefing_path = (workspace / "briefing_real.md").resolve()
    coleta_dir = (workspace / "coleta_entrada").resolve()
    pacote_dir = (workspace / "pacote_referencia").resolve()
    manifest_path = (workspace / "manifesto_coleta.json").resolve()
    pacote_manifest = (pacote_dir / "manifest.json").resolve()
    pacote_bundle = (pacote_dir / "tariel_filled_reference_bundle.json").resolve()
    status_payload = _read_json_if_exists(status_path) or {}
    manifest_payload = _read_json_if_exists(manifest_path) or {}
    status_key = str(status_payload.get("status_refino") or "").strip().lower() or "workspace_bootstrapped"
    status_meta = _label_catalogo(
        _CATALOGO_MATERIAL_WORKSPACE_STATUS_LABELS,
        status_key,
        _humanizar_slug(status_key) or "Workspace",
    )
    material_recebido = [
        str(item).strip()
        for item in list(status_payload.get("material_recebido") or [])
        if str(item).strip()
    ]
    lacunas = [
        str(item).strip()
        for item in list(status_payload.get("lacunas_abertas") or [])
        if str(item).strip()
    ]
    validacoes = [
        item
        for item in list(status_payload.get("artefatos_externos_validados") or [])
        if isinstance(item, dict)
    ]
    has_reference_pack = pacote_manifest.exists() and pacote_bundle.exists()
    execution_track = _build_material_real_execution_track(
        family_key=family_key,
        display_name=str(manifest_payload.get("nome_exibicao") or family_key),
        status_key=status_key,
        manifest_payload=manifest_payload,
        material_recebido=material_recebido,
        has_reference_pack=has_reference_pack,
        validations_count=len(validacoes),
        material_real_workspace={"status": status_meta},
    )
    worklist = _build_material_real_worklist(
        family_key=family_key,
        manifest_payload=manifest_payload,
        material_recebido=material_recebido,
        has_reference_pack=has_reference_pack,
        validations_count=len(validacoes),
        status_key=status_key,
    )
    return {
        "workspace_path": _repo_relative_path_label(workspace),
        "source_root": _repo_relative_path_label(workspace.parent),
        "status": status_meta,
        "status_key": status_key,
        "has_briefing": briefing_path.exists(),
        "has_status_refino": status_path.exists(),
        "has_manifesto_coleta": manifest_path.exists(),
        "has_coleta_entrada": coleta_dir.exists(),
        "has_pacote_referencia": pacote_dir.exists(),
        "has_reference_manifest": pacote_manifest.exists(),
        "has_reference_bundle": pacote_bundle.exists(),
        "material_recebido_count": len(material_recebido),
        "lacunas_count": len(lacunas),
        "validations_count": len(validacoes),
        "material_recebido": material_recebido[:6],
        "lacunas_abertas": lacunas[:4],
        "proximo_passo": str(status_payload.get("proximo_passo") or "").strip() or None,
        "artefatos_externos_validados": validacoes[:3],
        "execution_track": execution_track,
        "worklist": worklist,
    }


def _build_material_real_priority_summary(
    row: dict[str, Any],
    material_real_workspace: dict[str, Any] | None,
) -> dict[str, Any]:
    calibration_key = str((row.get("calibration_status") or {}).get("key") or "")
    commercial_key = str((row.get("commercial_status") or {}).get("key") or "")
    active_release_count = int(row.get("active_release_count") or 0)
    workspace_status_key = str((material_real_workspace or {}).get("status_key") or "")
    has_reference_pack = bool(
        (material_real_workspace or {}).get("has_reference_manifest")
        and (material_real_workspace or {}).get("has_reference_bundle")
    )
    lacunas_count = int((material_real_workspace or {}).get("lacunas_count") or 0)

    if calibration_key == "real_calibrated":
        status_key = "resolved"
    elif has_reference_pack and commercial_key == "active":
        status_key = "immediate"
    elif material_real_workspace is not None and workspace_status_key == "aguardando_material_real":
        status_key = "waiting_material"
    elif material_real_workspace is not None:
        status_key = "active_queue"
    else:
        status_key = "bootstrap"

    actions: list[str] = []
    signals: list[str] = []
    if status_key == "resolved":
        actions.extend(
            [
                "Manter linguagem e PDF sob monitoramento de emissão.",
                "Usar a família como baseline para próximas variantes comerciais.",
            ]
        )
    elif status_key == "immediate":
        actions.extend(
            [
                "Calibrar o modelo oficial com o pacote validado.",
                "Homologar PDF final, anexo pack e narrativa técnica.",
                "Promover a família para operação vendável mais forte.",
            ]
        )
    elif status_key == "active_queue":
        actions.extend(
            [
                "Consolidar briefing, coleta e referência antes da homologação final.",
                "Fechar lacunas abertas de evidência e documentação.",
            ]
        )
    elif status_key == "waiting_material":
        actions.extend(
            [
                "Receber acervo real do cliente para substituir a baseline sintética.",
                "Validar ZIP, PDF e bundle antes de promover o pacote de referência.",
            ]
        )
    else:
        actions.extend(
            [
                "Abrir a trilha de material real para a família.",
                "Criar briefing, coleta de entrada e pacote de referência inicial.",
            ]
        )

    if active_release_count > 0:
        signals.append(f"{active_release_count} empresa(s) já dependem desta família.")
    if lacunas_count > 0:
        signals.append(f"{lacunas_count} lacuna(s) aberta(s) na trilha de material real.")
    if material_real_workspace and material_real_workspace.get("validations_count"):
        signals.append(
            f"{int(material_real_workspace.get('validations_count') or 0)} artefato(s) externo(s) já validados."
        )
    if not signals and material_real_workspace is None:
        signals.append("A família ainda não abriu uma trilha de material real no repositório.")

    priority_rank = {
        "immediate": 4,
        "active_queue": 3,
        "waiting_material": 2,
        "bootstrap": 1,
        "resolved": 0,
    }.get(status_key, 0)
    return {
        "status": _label_catalogo(
            _CATALOGO_MATERIAL_PRIORITY_LABELS,
            status_key,
            _humanizar_slug(status_key) or "Prioridade",
        ),
        "priority_rank": priority_rank,
        "signals": signals[:3],
        "recommended_actions": actions[:3],
        "workspace_status": (
            (material_real_workspace or {}).get("status")
            or _label_catalogo(
                _CATALOGO_MATERIAL_WORKSPACE_STATUS_LABELS,
                "workspace_bootstrapped",
                "Workspace bootstrap",
            )
        ),
    }


def _material_real_has_received_item(
    material_recebido: list[str],
    *,
    item_id: str,
    drop_folder: str | None = None,
) -> bool:
    values = [str(item).strip().lower() for item in material_recebido if str(item).strip()]
    folder_name = Path(str(drop_folder)).name.strip().lower() if drop_folder else ""
    probes = {
        str(item_id or "").strip().lower(),
        str(drop_folder or "").strip().lower(),
        folder_name,
    }
    alias_map = {
        "modelo_atual_vazio": {"modelo atual", "modelo_atual_vazio"},
        "documentos_finais_reais": {"documentos_finais_reais", "documentos finais", "pdf"},
        "padrao_linguagem_tecnica": {"padrao_linguagem_tecnica", "linguagem tecnica"},
        "regras_comerciais_e_operacionais": {"regras_comerciais_e_operacionais", "regras comerciais"},
        "evidencias_reais_associadas": {"evidencias_reais_associadas", "evidencias reais", "foto", "zip"},
        "documentos_base_e_memoria": {"documentos_base_e_memoria", "memoria", "planilha"},
        "programa_e_certificacao": {"programa_e_certificacao", "certificacao", "certificado"},
    }
    probes.update(alias_map.get(str(item_id or "").strip().lower(), set()))
    probes = {probe for probe in probes if probe}
    return any(probe in value for value in values for probe in probes)


def _build_material_real_worklist_item(
    *,
    task_id: str,
    title: str,
    done: bool,
    blocking: bool,
    deliverable: str,
    owner: str,
) -> dict[str, Any]:
    status_key = "done" if done else "blocking" if blocking else "pending"
    return {
        "task_id": task_id,
        "title": title,
        "status": _label_catalogo(
            _CATALOGO_MATERIAL_WORKLIST_STATUS_LABELS,
            status_key,
            _humanizar_slug(status_key) or "Tarefa",
        ),
        "blocking": bool(blocking),
        "deliverable": deliverable,
        "owner": owner,
    }


def _build_material_real_execution_track(
    *,
    family_key: str,
    display_name: str,
    status_key: str,
    manifest_payload: dict[str, Any],
    material_recebido: list[str],
    has_reference_pack: bool,
    validations_count: int,
    material_real_workspace: dict[str, Any],
) -> dict[str, Any]:
    preset = dict(_MATERIAL_REAL_EXECUTION_TRACK_PRESETS.get(family_key) or {})
    kind = str(manifest_payload.get("kind") or "").strip() or "inspection"
    material_count = len(material_recebido)
    if status_key == "material_real_calibrado":
        phase_key = "continuous"
    elif has_reference_pack or validations_count > 0:
        phase_key = "template_refinement"
    elif material_count > 0:
        phase_key = "packaging_reference"
    else:
        phase_key = "intake_pending"
    default_owner = {
        "inspection": "Curadoria Tariel + operação do cliente",
        "test": "Curadoria Tariel + operação do cliente",
        "ndt": "Curadoria Tariel + END do cliente",
        "documentation": "Curadoria Tariel + documentação técnica do cliente",
        "engineering": "Curadoria Tariel + engenharia do cliente",
        "calculation": "Curadoria Tariel + engenharia do cliente",
        "training": "Curadoria Tariel + coordenação de treinamento do cliente",
    }.get(kind, "Curadoria Tariel + operação do cliente")
    return {
        "track_id": str(preset.get("track_id") or "material_real_growth"),
        "track_label": str(preset.get("track_label") or "Fila de material real"),
        "focus_label": str(
            preset.get("focus_label")
            or f"Elevar {display_name} de base canônica para baseline premium com material real."
        ),
        "lane": str(preset.get("lane") or "portfolio_growth"),
        "recommended_owner": str(preset.get("recommended_owner") or default_owner),
        "next_checkpoint": str(preset.get("next_checkpoint") or "Sem checkpoint sugerido"),
        "sort_order": int(preset.get("sort_order") or 999),
        "phase": _label_catalogo(
            _CATALOGO_MATERIAL_WORKLIST_PHASE_LABELS,
            phase_key,
            _humanizar_slug(phase_key) or "Fase",
        ),
        "template_pressure": _catalogo_modelo_label(
            resolve_master_template_id_for_family(family_key),
            fallback="Modelo oficial da família",
        ),
        "workspace_status": (
            material_real_workspace.get("status")
            or _label_catalogo(
                _CATALOGO_MATERIAL_WORKSPACE_STATUS_LABELS,
                "workspace_bootstrapped",
                "Workspace bootstrap",
            )
        ),
    }


def _build_material_real_worklist(
    *,
    family_key: str,
    manifest_payload: dict[str, Any],
    material_recebido: list[str],
    has_reference_pack: bool,
    validations_count: int,
    status_key: str,
) -> dict[str, Any]:
    tasks: list[dict[str, Any]] = []
    checklist = [
        item
        for item in list(manifest_payload.get("material_real_checklist") or [])
        if isinstance(item, dict)
    ]
    required_slots = [
        item
        for item in list(manifest_payload.get("required_slots_snapshot") or [])
        if isinstance(item, dict)
    ]

    for item in checklist[:5]:
        item_id = str(item.get("item_id") or "").strip() or "material"
        drop_folder = str(item.get("drop_folder") or "").strip() or None
        min_items = max(1, int(item.get("min_items") or 1))
        done = _material_real_has_received_item(
            material_recebido,
            item_id=item_id,
            drop_folder=drop_folder,
        )
        tasks.append(
            _build_material_real_worklist_item(
                task_id=item_id,
                title=f"Receber {str(item.get('label') or item_id).strip().lower()}",
                done=done,
                blocking=bool(item.get("required", True)) and not done,
                deliverable=f"{min_items} item(ns) em {drop_folder or 'coleta_entrada/'}",
                owner="Operação do cliente",
            )
        )

    slots_done = any("slots_reais" in str(item).strip().lower() for item in material_recebido)
    if required_slots:
        tasks.append(
            _build_material_real_worklist_item(
                task_id="map_slots_criticos",
                title="Mapear slots críticos com exemplos reais",
                done=slots_done,
                blocking=not slots_done,
                deliverable=f"{len(required_slots)} slot(s) obrigatórios confrontados com exemplos reais",
                owner="Curadoria Tariel",
            )
        )

    if validations_count > 0 or has_reference_pack:
        tasks.append(
            _build_material_real_worklist_item(
                task_id="baseline_sintetica",
                title="Validar ou reaproveitar baseline sintética externa",
                done=validations_count > 0,
                blocking=False,
                deliverable="ZIP/PDF/bundle validados como fallback ou ponto de partida",
                owner="Curadoria Tariel",
            )
        )

    tasks.append(
        _build_material_real_worklist_item(
            task_id="consolidar_pacote_referencia",
            title="Consolidar pacote de referência da família",
            done=has_reference_pack,
            blocking=not has_reference_pack,
            deliverable="manifest.json + tariel_filled_reference_bundle.json + assets/pdf em pacote_referencia/",
            owner="Curadoria Tariel",
        )
    )
    tasks.append(
        _build_material_real_worklist_item(
            task_id="refinar_template_pdf",
            title="Refinar template mestre, overlay e PDF final",
            done=status_key == "material_real_calibrado",
            blocking=False,
            deliverable="Template, narrativa e acabamento premium homologados",
            owner="Curadoria Tariel",
        )
    )

    pending_items = [item for item in tasks if str((item.get("status") or {}).get("key") or "") != "done"]
    blocking_items = [item for item in pending_items if bool(item.get("blocking"))]
    done_items = [item for item in tasks if str((item.get("status") or {}).get("key") or "") == "done"]
    return {
        "task_count": len(tasks),
        "pending_count": len(pending_items),
        "blocking_count": len(blocking_items),
        "done_count": len(done_items),
        "next_blocking_task": (blocking_items[0].get("title") if blocking_items else None),
        "items": tasks[:7],
    }


def _preview_section_status(
    *,
    chain_complete: bool,
    has_reference_pack: bool,
    calibration_key: str,
) -> dict[str, str]:
    if chain_complete and has_reference_pack and calibration_key == "real_calibrated":
        status_key = "premium_ready"
    elif chain_complete and has_reference_pack:
        status_key = "reference_ready"
    elif chain_complete:
        status_key = "foundation"
    else:
        status_key = "bootstrap"
    return _label_catalogo(
        _CATALOGO_DOCUMENT_PREVIEW_STATUS_LABELS,
        status_key,
        _humanizar_slug(status_key) or "Preview",
    )


def _showcase_preview_status(*, chain_complete: bool) -> dict[str, str]:
    status_key = "demonstration_ready" if chain_complete else "building"
    return _label_catalogo(
        _CATALOGO_SHOWCASE_STATUS_LABELS,
        status_key,
        _humanizar_slug(status_key) or "Preview",
    )


def _material_preview_status(*, has_reference_pack: bool, calibration_key: str) -> dict[str, str]:
    if calibration_key == "real_calibrated":
        status_key = "real_calibrated"
    elif has_reference_pack or calibration_key == "partial_real":
        status_key = "reference_ready"
    else:
        status_key = "none"
    return _label_catalogo(
        _CATALOGO_MATERIAL_PREVIEW_STATUS_LABELS,
        status_key,
        _humanizar_slug(status_key) or "Material",
    )


def _document_preview_objective(
    *,
    row: dict[str, Any],
    family_schema: dict[str, Any] | None,
) -> dict[str, str]:
    nr_label = str(
        row.get("nr_key")
        or (family_schema or {}).get("macro_categoria")
        or row.get("macro_category")
        or ""
    ).strip().upper()
    family_name = str(
        row.get("display_name")
        or (family_schema or {}).get("nome_exibicao")
        or "este laudo"
    ).strip()
    objective_title = f"Objetivo da {nr_label}" if nr_label else "Objetivo do modelo"
    objective_summary = (
        f"Mostrar como o laudo de {family_name} chega pronto para receber evidencias, analise e conclusao final."
    )
    if nr_label:
        objective_summary = (
            f"Mostrar como o laudo de {family_name} atende o objetivo da {nr_label}, "
            "com estrutura pronta para receber evidencias, analise e conclusao final."
        )
    return {
        "title": objective_title,
        "summary": objective_summary,
    }


def _build_document_preview_summary(
    *,
    row: dict[str, Any],
    artifact_snapshot: dict[str, bool],
    family_schema: dict[str, Any] | None,
    offer: dict[str, Any] | None,
    calibration: dict[str, Any],
    material_real_workspace: dict[str, Any] | None,
    family_methods: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_policy = family_schema.get("evidence_policy") if isinstance(family_schema, dict) else {}
    if not isinstance(evidence_policy, dict):
        evidence_policy = {}
    minimum_evidence = evidence_policy.get("minimum_evidence")
    if not isinstance(minimum_evidence, dict):
        minimum_evidence = {}
    required_slots_raw = evidence_policy.get("required_slots")
    optional_slots_raw = evidence_policy.get("optional_slots")
    required_slots = [
        {
            "slot_id": str(item.get("slot_id") or "").strip() or None,
            "label": str(item.get("label") or item.get("slot_id") or "").strip() or "Slot obrigatório",
            "purpose": str(item.get("purpose") or "").strip() or None,
        }
        for item in list(required_slots_raw or [])
        if isinstance(item, dict)
    ]
    optional_slots = [
        {
            "slot_id": str(item.get("slot_id") or "").strip() or None,
            "label": str(item.get("label") or item.get("slot_id") or "").strip() or "Slot opcional",
        }
        for item in list(optional_slots_raw or [])
        if isinstance(item, dict)
    ]
    chain_complete = all(
        bool(artifact_snapshot.get(key))
        for key in (
            "has_family_schema",
            "has_template_seed",
            "has_laudo_output_seed",
            "has_laudo_output_exemplo",
        )
    )
    has_reference_pack = bool(
        (material_real_workspace or {}).get("has_reference_manifest")
        and (material_real_workspace or {}).get("has_reference_bundle")
    )
    calibration_key = str((calibration.get("status") or {}).get("key") or "")
    preview_status = _preview_section_status(
        chain_complete=chain_complete,
        has_reference_pack=has_reference_pack,
        calibration_key=calibration_key,
    )
    showcase_status = _showcase_preview_status(chain_complete=chain_complete)
    material_status = _material_preview_status(
        has_reference_pack=has_reference_pack,
        calibration_key=calibration_key,
    )
    objective = _document_preview_objective(
        row=row,
        family_schema=family_schema,
    )
    scope_payload = family_schema.get("scope") if isinstance(family_schema, dict) else {}
    if not isinstance(scope_payload, dict):
        scope_payload = {}
    scope_signals = [
        str(item).strip()
        for item in list(scope_payload.get("scope_signals") or [])
        if str(item).strip()
    ]
    sections = [
        {
            "title": "Casca profissional",
            "status": _label_catalogo(
                _CATALOGO_DOCUMENT_PREVIEW_STATUS_LABELS,
                "foundation" if chain_complete else "bootstrap",
                "Casca documental",
            ),
            "bullets": [
                "Modelo oficial premium governado no catálogo.",
                "Estrutura documental preservada da base ao PDF final.",
                f"Modelo principal: {_catalogo_modelo_label((offer or {}).get('template_default_code'), fallback='em definição')}.",
            ],
        },
        {
            "title": "Metodologia e evidências",
            "status": _label_catalogo(
                _CATALOGO_DOCUMENT_PREVIEW_STATUS_LABELS,
                "reference_ready" if has_reference_pack else "foundation" if required_slots else "bootstrap",
                "Metodologia",
            ),
            "bullets": (
                [item["label"] for item in required_slots[:3]]
                or [item["display_name"] for item in family_methods[:3]]
                or ["Definir slots críticos de evidência."]
            ),
        },
        {
            "title": "Conclusão e emissão",
            "status": _label_catalogo(
                _CATALOGO_DOCUMENT_PREVIEW_STATUS_LABELS,
                "premium_ready" if calibration_key == "real_calibrated" else "reference_ready" if has_reference_pack else "foundation",
                "Emissão",
            ),
            "bullets": [
                "QR/hash público, anexo pack e emissão oficial transacional.",
                "Diff entre emissões e trilha de revisão por bloco.",
                "Responsaveis autorizados pela assinatura e pacote oficial exportavel.",
            ],
        },
    ]
    return {
        "status": preview_status,
        "showcase_status": showcase_status,
        "material_status": material_status,
        "title": str((offer or {}).get("offer_name") or row.get("display_name") or "Preview documental"),
        "subtitle": str((offer or {}).get("description") or "").strip()
        or str((family_schema or {}).get("descricao") or "").strip()
        or "Casca documental premium governada para esta família.",
        "objective": objective,
        "template_default_code": str((offer or {}).get("template_default_code") or "").strip() or None,
        "template_default_label": _catalogo_modelo_label(
            str((offer or {}).get("template_default_code") or "").strip() or None
        ),
        "minimum_evidence": {
            "fotos": int(minimum_evidence.get("fotos") or 0),
            "documentos": int(minimum_evidence.get("documentos") or 0),
            "textos": int(minimum_evidence.get("textos") or 0),
        },
        "required_slots": required_slots[:6],
        "optional_slots": optional_slots[:5],
        "required_slot_count": len(required_slots),
        "optional_slot_count": len(optional_slots),
        "scope_signals": scope_signals[:4],
        "sections": sections,
        "premium_features": [
            "QR/hash público",
            "anexo pack oficial",
            "diff entre emissões",
            "responsaveis pela assinatura",
        ],
    }


def _build_catalog_home_document_preview(
    *,
    family: FamiliaLaudoCatalogo,
    row: dict[str, Any],
    metodos_catalogo: list[Any],
) -> dict[str, Any]:
    family_key = str(getattr(family, "family_key", "") or row.get("family_key") or "").strip()
    artifact_snapshot = dict(row.get("artifact_snapshot") or _catalog_family_artifact_snapshot(family_key))
    oferta = getattr(family, "oferta_comercial", None)
    material_real_workspace = _build_material_real_workspace_summary(family_key)
    try:
        family_schema = carregar_family_schema_canonico(family_key)
    except ValueError:
        family_schema = None

    family_methods = [
        {
            "method_key": str(getattr(item, "method_key", "") or "").strip(),
            "display_name": str(getattr(item, "nome_exibicao", "") or "").strip(),
            "categoria": str(getattr(item, "categoria", "") or "").strip(),
        }
        for item in metodos_catalogo
        if str(getattr(item, "method_key", "") or "").strip() in family_key
    ]
    calibration_payload = {
        "status": _label_catalogo(
            _CATALOGO_CALIBRATION_STATUS_LABELS,
            _calibracao_status_resolvido(family, oferta),
            "Sem calibracao",
        ),
    }
    preview = _build_document_preview_summary(
        row=row,
        artifact_snapshot=artifact_snapshot,
        family_schema=family_schema,
        offer=(
            {
                "offer_name": str(getattr(oferta, "nome_oferta", "") or "").strip()
                or str(getattr(family, "nome_exibicao", "") or family_key),
                "description": str(getattr(oferta, "descricao_comercial", "") or "").strip() or None,
                "template_default_code": str(getattr(oferta, "template_default_code", "") or "").strip() or None,
            }
            if oferta is not None
            else None
        ),
        calibration=calibration_payload,
        material_real_workspace=material_real_workspace,
        family_methods=family_methods,
    )
    if preview["showcase_status"]["key"] == "demonstration_ready" and preview["material_status"]["key"] == "real_calibrated":
        preview_note = "Modelo demonstrativo pronto e ja calibrado com material real."
    elif preview["showcase_status"]["key"] == "demonstration_ready" and preview["material_status"]["key"] == "reference_ready":
        preview_note = "Modelo demonstrativo pronto e ja apoiado por base de referencia."
    elif preview["showcase_status"]["key"] == "demonstration_ready":
        preview_note = "Modelo demonstrativo pronto para vitrine. O laudo ja abre como documento antes do material real."
    elif bool(artifact_snapshot.get("has_laudo_output_seed")):
        preview_note = "Base do laudo pronta. Ainda falta fechar o modelo demonstrativo final."
    else:
        preview_note = "Estrutura em montagem antes do laudo-exemplo final."
    return {
        **preview,
        "preview_note": preview_note,
    }


def _enrich_catalog_rows_with_document_preview(
    *,
    rows: list[dict[str, Any]],
    families: list[FamiliaLaudoCatalogo],
    metodos_catalogo: list[Any],
) -> list[dict[str, Any]]:
    families_by_key = {
        str(getattr(item, "family_key", "") or "").strip().lower(): item
        for item in families
        if str(getattr(item, "family_key", "") or "").strip()
    }
    enriched_rows: list[dict[str, Any]] = []
    for row in rows:
        family_key = str(row.get("family_key") or "").strip().lower()
        family = families_by_key.get(family_key)
        if family is None:
            enriched_rows.append(row)
            continue
        enriched_rows.append(
            {
                **row,
                "document_preview": _build_catalog_home_document_preview(
                    family=family,
                    row=row,
                    metodos_catalogo=metodos_catalogo,
                ),
            }
        )
    return enriched_rows


def _build_variant_library_summary(
    *,
    family_key: str,
    offer: dict[str, Any] | None,
    artifact_snapshot: dict[str, bool],
    active_release_count: int,
) -> dict[str, Any]:
    variants = list((offer or {}).get("variants") or [])
    operational_runtime_ready = bool(
        artifact_snapshot.get("has_template_seed") and artifact_snapshot.get("has_laudo_output_seed")
    )
    cards: list[dict[str, Any]] = []
    template_codes: set[str] = set()
    template_usage_counter: Counter[str] = Counter()
    for item in variants:
        template_code = str(item.get("template_code") or "").strip() or None
        if template_code:
            template_codes.add(template_code)
            template_usage_counter[template_code] += 1
        if template_code and operational_runtime_ready:
            status_key = "operational"
        elif template_code:
            status_key = "template_mapped"
        else:
            status_key = "needs_template"
        variant_key = str(item.get("variant_key") or "").strip() or "variant_sem_chave"
        cards.append(
            {
                "variant_key": variant_key,
                "label": str(item.get("nome_exibicao") or variant_key).strip() or variant_key,
                "template_code": template_code,
                "template_label": _catalogo_modelo_label(template_code, fallback="Modelo em definição"),
                "usage": str(item.get("uso_recomendado") or "").strip() or None,
                "selection_token": f"catalog:{str(family_key).strip().lower()}:{variant_key.lower()}",
                "status": _label_catalogo(
                    _CATALOGO_VARIANT_LIBRARY_STATUS_LABELS,
                    status_key,
                    _humanizar_slug(status_key) or "Variante",
                ),
            }
        )
    ambiguous_template_count = sum(1 for count in template_usage_counter.values() if count > 1)
    return {
        "variant_count": len(cards),
        "template_mapped_count": sum(1 for item in cards if item["template_code"]),
        "operational_count": sum(1 for item in cards if item["status"]["key"] == "operational"),
        "unique_template_count": len(template_codes),
        "ambiguous_template_count": ambiguous_template_count,
        "selection_guidance": (
            "Escolha a opção de uso explicitamente quando duas opções compartilham a mesma apresentação do documento."
            if ambiguous_template_count
            else "Cada opção pode ter narrativa e uso recomendado próprios sem misturar a apresentação do documento."
        ),
        "variants": cards,
        "release_signal": (
            f"{active_release_count} empresa(s) já usam esta família."
            if active_release_count > 0
            else "Ainda sem empresas liberadas para esta família."
        ),
    }


def _build_template_refinement_target(
    *,
    family_key: str,
    display_name: str,
    material_real_priority: dict[str, Any],
    variant_library: dict[str, Any],
    template_default_code: str | None,
    active_release_count: int,
) -> dict[str, Any]:
    master_template_id = resolve_master_template_id_for_family(family_key)
    contract = dict(MASTER_TEMPLATE_REGISTRY.get(master_template_id) or {})
    registry_entry = _template_library_registry_index().get(master_template_id)
    priority_key = str((material_real_priority.get("status") or {}).get("key") or "")
    if registry_entry is None:
        status_key = "registry_gap"
    elif priority_key in {"immediate", "active_queue"}:
        status_key = "refinement_due"
    elif priority_key == "resolved":
        status_key = "continuous"
    else:
        status_key = "mapped"

    recommended_actions: list[str] = []
    if status_key == "registry_gap":
        recommended_actions.extend(
            [
                "Registrar o modelo oficial desta família na biblioteca documental.",
                "Preparar a estrutura do documento e a saída base para abrir a vitrine comercial.",
            ]
        )
    else:
        recommended_actions.append(
            "Refinar o modelo oficial com os aprendizados do material real e da Mesa."
        )
        if int(variant_library.get("variant_count") or 0) > 0:
            recommended_actions.append(
                "Garantir que as opções comerciais herdem a mesma apresentação premium do documento."
            )
        if active_release_count > 0:
            recommended_actions.append(
                "Priorizar este ajuste porque já existe empresa operando a família."
            )
    template_default_label = _catalogo_modelo_label(template_default_code)
    signals = [
        item
        for item in (
            f"{active_release_count} empresa(s) ativa(s)" if active_release_count > 0 else "",
            f"{int(variant_library.get('variant_count') or 0)} opção(ões) comercial(is)"
            if int(variant_library.get("variant_count") or 0) > 0
            else "",
            f"Modelo principal: {template_default_label}" if template_default_label else "",
        )
        if item
    ]
    resolved_label = str(contract.get("label") or "").strip() or (
        str(registry_entry.get("label") or "").strip() if registry_entry is not None else master_template_id
    )
    resolved_summary = str(contract.get("summary") or "").strip() or (
        str(registry_entry.get("usage") or "").strip() if registry_entry is not None else ""
    )
    resolved_documental_type = str(contract.get("documental_type") or "").strip() or (
        str(registry_entry.get("documental_type") or "").strip() if registry_entry is not None else ""
    )
    return {
        "master_template_id": master_template_id,
        "label": resolved_label,
        "summary": resolved_summary or None,
        "documental_type": resolved_documental_type or None,
        "artifact_path": str(
            ((registry_entry or {}).get("artifact_path") or contract.get("seed_path") or "")
        ).strip()
        or None,
        "registry_registered": registry_entry is not None,
        "registry_label": str(registry_entry.get("label") or "").strip() or None if registry_entry else None,
        "template_default_code": template_default_code,
        "template_default_label": template_default_label,
        "family_label": display_name,
        "signals": signals[:3],
        "recommended_actions": recommended_actions[:3],
        "status": _label_catalogo(
            _CATALOGO_TEMPLATE_REFINEMENT_STATUS_LABELS,
            status_key,
            _humanizar_slug(status_key) or "Template",
        ),
    }


def _build_calibration_queue_rollup(rows_all: list[dict[str, Any]]) -> dict[str, Any]:
    actionable_items: list[dict[str, Any]] = []
    template_pressure_counter: dict[str, dict[str, Any]] = {}
    for row in rows_all:
        family_key = str(row.get("family_key") or "")
        workspace = _build_material_real_workspace_summary(family_key)
        priority = _build_material_real_priority_summary(row, workspace)
        execution_track = dict((workspace or {}).get("execution_track") or {})
        worklist = dict((workspace or {}).get("worklist") or {})
        priority_key = str((priority.get("status") or {}).get("key") or "")
        if priority_key == "resolved":
            continue
        variant_library = {
            "variant_count": int(row.get("variant_count") or 0),
        }
        target = _build_template_refinement_target(
            family_key=family_key,
            display_name=str(row.get("display_name") or family_key),
            material_real_priority=priority,
            variant_library=variant_library,
            template_default_code=str(row.get("template_default_code") or "").strip() or None,
            active_release_count=int(row.get("active_release_count") or 0),
        )
        pressure_score = (
            int(priority.get("priority_rank") or 0) * 100
            + int(row.get("active_release_count") or 0) * 10
            + int(row.get("variant_count") or 0)
        )
        queue_reason = {
            "immediate": "Pacote validado já permite calibrar template, PDF final e anexo pack.",
            "active_queue": "Workspace real aberto, com sinais suficientes para refino, mas ainda com lacunas.",
            "waiting_material": "Família comercialmente pronta, porém aguardando acervo real do cliente.",
            "bootstrap": "Família vendável sem trilha de material real aberta.",
        }.get(priority_key, "Família com necessidade de calibração operacional.")
        if str(execution_track.get("focus_label") or "").strip():
            queue_reason = str(execution_track.get("focus_label") or "").strip()
        actionable_items.append(
            {
                "family_key": family_key,
                "display_name": str(row.get("display_name") or family_key),
                "priority": priority,
                "execution_track": execution_track,
                "worklist": worklist,
                "workspace_status": priority.get("workspace_status"),
                "readiness": row.get("readiness"),
                "active_release_count": int(row.get("active_release_count") or 0),
                "variant_count": int(row.get("variant_count") or 0),
                "template_refinement_target": target,
                "queue_reason": queue_reason,
                "workspace_path": (workspace or {}).get("workspace_path"),
                "next_action": str(
                    worklist.get("next_blocking_task")
                    or (priority.get("recommended_actions") or [None])[0]
                    or ""
                ).strip()
                or None,
                "next_checkpoint": str(execution_track.get("next_checkpoint") or "").strip() or None,
                "worklist_pending_count": int(worklist.get("pending_count") or 0),
                "execution_sort_order": int(execution_track.get("sort_order") or 999),
                "pressure_score": pressure_score,
            }
        )
        entry = template_pressure_counter.setdefault(
            target["master_template_id"],
            {
                "master_template_id": target["master_template_id"],
                "label": target["label"],
                "status": target["status"],
                "artifact_path": target.get("artifact_path"),
                "family_count": 0,
                "active_release_count": 0,
                "variant_count": 0,
                "families": [],
            },
        )
        entry["family_count"] += 1
        entry["active_release_count"] += int(row.get("active_release_count") or 0)
        entry["variant_count"] += int(row.get("variant_count") or 0)
        if len(entry["families"]) < 3:
            entry["families"].append(str(row.get("display_name") or family_key))

    actionable_items.sort(
        key=lambda item: (
            int(item.get("execution_sort_order") or 999),
            -int(item.get("pressure_score") or 0),
            str(item.get("display_name") or "").lower(),
        )
    )
    template_targets = sorted(
        template_pressure_counter.values(),
        key=lambda item: (
            -int(item.get("family_count") or 0),
            -int(item.get("active_release_count") or 0),
            -int(item.get("variant_count") or 0),
            str(item.get("label") or "").lower(),
        ),
    )
    priority_counter = Counter(
        str((item.get("priority") or {}).get("status", {}).get("key") or "")
        for item in actionable_items
    )
    return {
        "queue_count": len(actionable_items),
        "priority_modes": [
            {
                "status": _label_catalogo(
                    _CATALOGO_MATERIAL_PRIORITY_LABELS,
                    key,
                    _humanizar_slug(key) or "Prioridade",
                ),
                "count": int(priority_counter.get(key, 0)),
            }
            for key in ("immediate", "active_queue", "waiting_material", "bootstrap")
        ],
        "highlights": actionable_items[:6],
        "template_targets": template_targets[:6],
    }


def _build_material_real_rollup(rows_all: list[dict[str, Any]]) -> dict[str, Any]:
    workspace_by_family = {
        str(row["family_key"]): _build_material_real_workspace_summary(str(row["family_key"]))
        for row in rows_all
    }
    summaries = [item for item in workspace_by_family.values() if item is not None]
    validated = [
        item
        for item in summaries
        if str((item["status"] or {}).get("key") or "") == "baseline_sintetica_externa_validada"
    ]
    packages_ready = [
        item
        for item in summaries
        if bool(item.get("has_reference_manifest")) and bool(item.get("has_reference_bundle"))
    ]
    priority_rows = [
        {
            "family_key": str(row["family_key"]),
            "display_name": str(row["display_name"]),
            "workspace_path": (workspace_by_family.get(str(row["family_key"])) or {}).get("workspace_path"),
            "priority": _build_material_real_priority_summary(
                row,
                workspace_by_family.get(str(row["family_key"])),
            ),
        }
        for row in rows_all
    ]
    priority_rows.sort(
        key=lambda item: (
            -int(_dict_payload_admin(item.get("priority")).get("priority_rank") or 0),
            str(item["display_name"]).lower(),
        )
    )
    priority_counter = Counter(
        str(
            _dict_payload_admin(
                _dict_payload_admin(item.get("priority")).get("status")
            ).get("key")
            or ""
        )
        for item in priority_rows
    )
    return {
        "workspace_count": len(summaries),
        "validated_workspace_count": len(validated),
        "reference_package_ready_count": len(packages_ready),
        "with_briefing_count": sum(1 for item in summaries if bool(item.get("has_briefing"))),
        "priority_modes": [
            {
                "status": _label_catalogo(
                    _CATALOGO_MATERIAL_PRIORITY_LABELS,
                    key,
                    _humanizar_slug(key) or "Prioridade",
                ),
                "count": int(priority_counter.get(key, 0)),
            }
            for key in ("immediate", "active_queue", "waiting_material", "bootstrap", "resolved")
        ],
        "highlights": [
            {
                "family_key": str(row["family_key"]),
                "display_name": str(row["display_name"]),
                "status": (workspace_by_family.get(str(row["family_key"])) or {}).get("status"),
                "workspace_path": summary["workspace_path"],
            }
            for row in rows_all
            for summary in [workspace_by_family.get(str(row["family_key"]))]
            if summary is not None
        ][:6],
        "priority_highlights": [
            {
                "family_key": item["family_key"],
                "display_name": item["display_name"],
                "status": _dict_payload_admin(item.get("priority")).get("status"),
                "workspace_path": item.get("workspace_path"),
                "next_action": (
                    _dict_payload_admin(item.get("priority")).get("recommended_actions")
                    or [None]
                )[0],
            }
            for item in priority_rows[:6]
        ],
    }


def _build_commercial_scale_rollup(rows_all: list[dict[str, Any]]) -> dict[str, Any]:
    bundle_counter: Counter[str] = Counter()
    bundle_meta: dict[str, dict[str, Any]] = {}
    channel_counter: Counter[str] = Counter()
    feature_counter: Counter[str] = Counter()

    for row in rows_all:
        commercial = row.get("contract_entitlements") or {}
        for feature in list(commercial.get("included_features") or []):
            key = str(feature.get("key") or "").strip()
            if key:
                feature_counter[key] += 1

        channel_key = str((row.get("release_channel") or {}).get("key") or "").strip()
        if channel_key:
            channel_counter[channel_key] += 1

        bundle = row.get("commercial_bundle")
        if isinstance(bundle, dict):
            bundle_key = str(bundle.get("bundle_key") or "").strip()
            if bundle_key:
                bundle_counter[bundle_key] += 1
                bundle_meta[bundle_key] = {
                    "bundle_key": bundle_key,
                    "bundle_label": str(bundle.get("bundle_label") or bundle_key).strip(),
                    "summary": str(bundle.get("summary") or "").strip() or None,
                    "audience": str(bundle.get("audience") or "").strip() or None,
                    "highlights": list(bundle.get("highlights") or []),
                }
                continue
        package_name = str(row.get("offer_package") or "").strip()
        if package_name:
            bundle_key = _normalizar_chave_catalogo(
                package_name,
                campo="Pacote comercial",
                max_len=80,
            )
            if bundle_key:
                bundle_counter[bundle_key] += 1
                bundle_meta.setdefault(
                    bundle_key,
                    {
                        "bundle_key": bundle_key,
                        "bundle_label": package_name,
                        "summary": None,
                        "audience": None,
                        "highlights": [],
                    },
                )

    bundle_rows = sorted(
        (
            {
                **meta,
                "family_count": int(bundle_counter.get(bundle_key, 0)),
            }
            for bundle_key, meta in bundle_meta.items()
        ),
        key=lambda item: (-int(item["family_count"]), str(item["bundle_label"]).lower()),
    )
    total_channels = sum(int(item) for item in channel_counter.values())
    total_features = sum(int(item) for item in feature_counter.values())
    return {
        "bundle_count": len(bundle_rows),
        "bundle_highlights": bundle_rows[:6],
        "release_channels": [
            {
                "channel": release_channel_meta(channel),
                "count": int(channel_counter.get(channel, 0)),
                "share": round((int(channel_counter.get(channel, 0)) / total_channels) * 100, 1)
                if total_channels
                else 0.0,
            }
            for channel in ("pilot", "limited_release", "general_release")
        ],
        "feature_highlights": [
            {
                "feature": {
                    "key": key,
                    "label": next(
                        (
                            item.get("label")
                            for row in rows_all
                            for item in list(((row.get("contract_entitlements") or {}).get("included_features") or []))
                            if str(item.get("key") or "").strip() == key
                        ),
                        _humanizar_slug(key),
                    ),
                },
                "count": int(feature_counter.get(key, 0)),
                "share": round((int(feature_counter.get(key, 0)) / total_features) * 100, 1)
                if total_features
                else 0.0,
            }
            for key, _count in feature_counter.most_common(6)
        ],
    }


def _upsert_metodos_catalogo_para_familia(
    db: Session,
    *,
    familia: FamiliaLaudoCatalogo,
    criado_por_id: int | None = None,
) -> list[MetodoCatalogoInspecao]:
    itens = _metodos_sugeridos_para_familia(
        family_key=str(getattr(familia, "family_key", "") or ""),
        nome_exibicao=str(getattr(familia, "nome_exibicao", "") or ""),
    )
    registros: list[MetodoCatalogoInspecao] = []
    for item in itens:
        method_key = _normalizar_chave_catalogo(item["method_key"], campo="Method key", max_len=80)
        registro = db.scalar(select(MetodoCatalogoInspecao).where(MetodoCatalogoInspecao.method_key == method_key))
        if registro is None:
            registro = MetodoCatalogoInspecao(
                method_key=method_key,
                nome_exibicao=_normalizar_texto_curto(item["nome_exibicao"], campo="Método", max_len=120),
                categoria=item["categoria"],
                criado_por_id=criado_por_id,
                ativo=True,
            )
            db.add(registro)
        registros.append(registro)
    return registros


def _calibracao_status_resolvido(
    familia: FamiliaLaudoCatalogo,
    oferta: OfertaComercialFamiliaLaudo | None,
) -> str:
    calibracao = getattr(familia, "calibracao", None)
    if calibracao is not None and str(getattr(calibracao, "calibration_status", "") or "").strip():
        return str(calibracao.calibration_status)
    material_status = str(getattr(oferta, "material_level", "") or "").strip().lower()
    if material_status == "real_calibrated":
        return "real_calibrated"
    if material_status == "partial":
        return "partial_real"
    if material_status == "synthetic":
        return "synthetic_only"
    material_status_legacy = str(getattr(oferta, "material_real_status", "") or "").strip().lower()
    if material_status_legacy == "calibrado":
        return "real_calibrated"
    if material_status_legacy == "parcial":
        return "partial_real"
    if material_status_legacy == "sintetico":
        return "synthetic_only"
    return "none"


def _offer_lifecycle_resolvido(oferta: OfertaComercialFamiliaLaudo | None) -> str | None:
    if oferta is None:
        return None
    lifecycle = str(getattr(oferta, "lifecycle_status", "") or "").strip().lower()
    if lifecycle:
        return lifecycle
    return "active" if bool(getattr(oferta, "ativo_comercial", False)) else "draft"


def _total_releases_ativas_familia(familia: FamiliaLaudoCatalogo) -> int:
    total = 0
    for item in list(getattr(familia, "tenant_releases", None) or []):
        if str(getattr(item, "release_status", "") or "").strip().lower() == "active":
            total += 1
    return total


def derivar_prontidao_catalogo(
    *,
    technical_status: str,
    has_template_seed: bool,
    has_laudo_output_seed: bool,
    offer_lifecycle_status: str | None,
    calibration_status: str,
    active_release_count: int,
) -> str:
    tecnico_pronto = str(technical_status or "").strip().lower() == "ready"
    possui_template = bool(has_template_seed or has_laudo_output_seed)
    oferta_ativa = str(offer_lifecycle_status or "").strip().lower() == "active"
    calibracao = str(calibration_status or "").strip().lower()

    if not tecnico_pronto or not possui_template:
        return "technical_only"
    if not oferta_ativa:
        return "technical_only"
    if active_release_count <= 0:
        return "partial"
    if calibracao == "real_calibrated":
        return "calibrated"
    if calibracao in {"partial_real", "synthetic_only"}:
        return "sellable"
    return "partial"


def _catalog_plan_distribution_summary(familia: FamiliaLaudoCatalogo) -> dict[str, Any]:
    review_summary = _resumir_governanca_review_policy(
        getattr(familia, "review_policy_json", None)
    )
    tenant_entitlements = dict(review_summary.get("tenant_entitlements") or {})
    review_plans = {
        str(item).strip()
        for item in list(tenant_entitlements.get("mobile_review_allowed_plans") or [])
        if str(item).strip()
    }
    autonomy_plans = {
        str(item).strip()
        for item in list(tenant_entitlements.get("mobile_autonomous_allowed_plans") or [])
        if str(item).strip()
    }
    has_explicit_plan_rules = bool(review_plans or autonomy_plans)
    requires_release_active = bool(tenant_entitlements.get("requires_release_active"))
    items: list[dict[str, Any]] = []
    enabled_count = 0

    for plan_name in PlanoEmpresa.valores():
        showroom_label = _catalog_showroom_plan_label(plan_name)
        enabled = (
            plan_name in review_plans or plan_name in autonomy_plans
            if has_explicit_plan_rules
            else True
        )
        access_level = "full" if plan_name in autonomy_plans else "enabled" if enabled else "disabled"
        items.append(
            {
                "key": _normalizar_chave_catalogo(plan_name, campo="Plano", max_len=40),
                "label": showroom_label["label"],
                "short_label": showroom_label["short_label"],
                "support_label": showroom_label["support_label"],
                "enabled": bool(enabled),
                "access_level": access_level,
            }
        )
        enabled_count += int(enabled)

    total = len(items)
    if enabled_count == total and total > 0:
        summary_label = "Todas as assinaturas"
    elif enabled_count <= 0:
        summary_label = "Sem assinatura liberada"
    else:
        summary_label = "Distribuicao seletiva"

    enabled_labels = [str(item["short_label"]) for item in items if item["enabled"]]

    summary_hint = (
        "Assinatura compativel e liberacao ativa."
        if requires_release_active
        else "Disponibilidade comercial exibida na vitrine."
    )
    if not has_explicit_plan_rules:
        summary_hint = "Liberado para qualquer assinatura ativa."

    return {
        "enabled_count": int(enabled_count),
        "total_count": int(total),
        "summary_label": summary_label,
        "summary_hint": summary_hint,
        "enabled_labels_text": _catalog_human_join(enabled_labels),
        "requires_release_active": requires_release_active,
        "has_explicit_plan_rules": has_explicit_plan_rules,
        "items": items,
    }


def _serializar_familia_catalogo_row(
    familia: FamiliaLaudoCatalogo,
    *,
    artifact_snapshot: dict[str, bool] | None = None,
) -> dict[str, Any]:
    oferta = getattr(familia, "oferta_comercial", None)
    commercial_governance = summarize_offer_commercial_governance(
        getattr(oferta, "flags_json", None) if oferta is not None else None,
        offer_lifecycle_status=_offer_lifecycle_resolvido(oferta),
    )
    technical_status = str(getattr(familia, "technical_status", "") or "").strip().lower() or _normalizar_status_tecnico_catalogo(
        str(getattr(familia, "status_catalogo", "") or "")
    )
    lifecycle_status = _offer_lifecycle_resolvido(oferta)
    calibration_status = _calibracao_status_resolvido(familia, oferta)
    snapshots = artifact_snapshot or _catalog_family_artifact_snapshot(str(familia.family_key))
    active_release_count = _total_releases_ativas_familia(familia)
    readiness = derivar_prontidao_catalogo(
        technical_status=technical_status,
        has_template_seed=bool(snapshots["has_template_seed"]),
        has_laudo_output_seed=bool(snapshots["has_laudo_output_seed"]),
        offer_lifecycle_status=lifecycle_status,
        calibration_status=calibration_status,
        active_release_count=active_release_count,
    )
    technical = _label_catalogo(_CATALOGO_TECHNICAL_STATUS_LABELS, technical_status, technical_status or "N/D")
    commercial = (
        _label_catalogo(_CATALOGO_LIFECYCLE_STATUS_LABELS, lifecycle_status, lifecycle_status or "Sem oferta")
        if lifecycle_status
        else {"key": "none", "label": "Sem oferta", "tone": "idle"}
    )
    calibration = _label_catalogo(
        _CATALOGO_CALIBRATION_STATUS_LABELS,
        calibration_status,
        calibration_status or "Sem leitura",
    )
    readiness_meta = _label_catalogo(_CATALOGO_READINESS_LABELS, readiness, readiness)
    modes = list(getattr(familia, "modos_tecnicos", None) or [])
    variants = catalog_offer_variants(familia, oferta)
    classification = str(getattr(familia, "catalog_classification", "") or "").strip().lower() or "family"
    return {
        "family_id": int(familia.id),
        "family_key": str(familia.family_key),
        "display_name": str(familia.nome_exibicao),
        "macro_category": str(getattr(familia, "macro_categoria", "") or "").strip() or "Sem macro categoria",
        "nr_key": str(getattr(familia, "nr_key", "") or "").strip() or None,
        "catalog_classification": classification,
        "classification_label": {
            "family": "Família",
            "inspection_method": "Método de inspeção",
            "evidence_method": "Método de evidência",
        }.get(classification, "Família"),
        "technical_status": technical,
        "commercial_status": commercial,
        "calibration_status": calibration,
        "readiness": readiness_meta,
        "offer_name": str(getattr(oferta, "nome_oferta", "") or "").strip() or None,
        "offer_key": str(getattr(oferta, "offer_key", "") or "").strip() or None,
        "offer_package": str(getattr(oferta, "pacote_comercial", "") or "").strip() or None,
        "release_channel": commercial_governance["release_channel"],
        "commercial_bundle": commercial_governance["commercial_bundle"],
        "contract_entitlements": commercial_governance["contract_entitlements"],
        "plan_distribution": _catalog_plan_distribution_summary(familia),
        "template_default_code": str(getattr(oferta, "template_default_code", "") or "").strip() or None,
        "offer_showcase_enabled": bool(getattr(oferta, "showcase_enabled", False)) if oferta is not None else False,
        "active_release_count": int(active_release_count),
        "mode_count": len(modes),
        "variant_count": len(variants),
        "modes": [
            {
                "mode_key": str(item.mode_key),
                "display_name": str(item.nome_exibicao),
                "active": bool(item.ativo),
            }
            for item in modes
        ],
        "artifact_snapshot": snapshots,
    }


def upsert_familia_catalogo(
    db: Session,
    *,
    family_key: str,
    nome_exibicao: str,
    macro_categoria: str = "",
    nr_key: str = "",
    descricao: str = "",
    status_catalogo: str = "rascunho",
    technical_status: str = "",
    catalog_classification: str = "",
    schema_version: int = 1,
    evidence_policy_json_text: str = "",
    review_policy_json_text: str = "",
    output_schema_seed_json_text: str = "",
    governance_metadata_json_text: str = "",
    criado_por_id: int | None = None,
) -> FamiliaLaudoCatalogo:
    family_key_norm = _normalizar_chave_catalogo(family_key, campo="Family key", max_len=120)
    nome_norm = _normalizar_texto_curto(nome_exibicao, campo="Nome de exibição", max_len=180)
    macro_norm = _normalizar_texto_opcional(macro_categoria, 80)
    nr_key_norm = _normalizar_nr_key(nr_key, family_key=family_key_norm)
    descricao_norm = _normalizar_texto_opcional(descricao)
    status_norm = _normalizar_status_catalogo_familia(status_catalogo)
    technical_status_norm = _normalizar_status_tecnico_catalogo(
        technical_status or ("ready" if status_norm == "publicado" else "deprecated" if status_norm == "arquivado" else "draft")
    )
    classification_norm = _normalizar_classificacao_catalogo(
        catalog_classification or _inferir_classificacao_catalogo(
            family_key=family_key_norm,
            nome_exibicao=nome_norm,
            macro_categoria=macro_norm or "",
        )
    )
    schema_version_int = max(1, int(schema_version or 1))

    familia = db.scalar(select(FamiliaLaudoCatalogo).where(FamiliaLaudoCatalogo.family_key == family_key_norm))
    if familia is None:
        familia = FamiliaLaudoCatalogo(
            family_key=family_key_norm,
            criado_por_id=criado_por_id,
        )
        db.add(familia)

    familia.nome_exibicao = nome_norm
    familia.macro_categoria = macro_norm
    familia.nr_key = nr_key_norm
    familia.descricao = descricao_norm
    familia.status_catalogo = status_norm
    familia.technical_status = technical_status_norm
    familia.catalog_classification = classification_norm
    familia.schema_version = schema_version_int
    familia.evidence_policy_json = _normalizar_json_opcional(evidence_policy_json_text, campo="Evidence policy")
    familia.review_policy_json = _normalizar_json_opcional(review_policy_json_text, campo="Review policy")
    familia.output_schema_seed_json = _normalizar_json_opcional(output_schema_seed_json_text, campo="Output schema seed")
    familia.governance_metadata_json = _normalizar_json_opcional(
        governance_metadata_json_text,
        campo="Governance metadata",
    )
    familia.publicado_em = _agora_utc() if status_norm == "publicado" else None
    if criado_por_id and not familia.criado_por_id:
        familia.criado_por_id = criado_por_id

    _upsert_metodos_catalogo_para_familia(db, familia=familia, criado_por_id=criado_por_id)
    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível salvar a família do catálogo.",
    )
    return familia


def upsert_governanca_review_familia(
    db: Session,
    *,
    family_key: str,
    default_review_mode: str = "",
    max_review_mode: str = "",
    requires_family_lock: bool = False,
    block_on_scope_mismatch: bool = False,
    block_on_missing_required_evidence: bool = False,
    block_on_critical_field_absent: bool = False,
    blocking_conditions_text: str = "",
    non_blocking_conditions_text: str = "",
    red_flags_json_text: str = "",
    requires_release_active: bool = False,
    requires_upload_doc_for_mobile_autonomous: bool = False,
    mobile_review_allowed_plans_text: str = "",
    mobile_autonomous_allowed_plans_text: str = "",
    criado_por_id: int | None = None,
) -> FamiliaLaudoCatalogo:
    familia = _buscar_familia_catalogo_por_chave(db, family_key)
    review_policy = _merge_review_policy_governance(
        dict(getattr(familia, "review_policy_json", None) or {})
        if isinstance(getattr(familia, "review_policy_json", None), dict)
        else {},
        default_review_mode=_normalizar_review_mode_governanca(
            default_review_mode,
            campo="Modo padrão de revisão",
        ),
        max_review_mode=_normalizar_review_mode_governanca(
            max_review_mode,
            campo="Modo máximo de revisão",
        ),
        requires_family_lock=bool(requires_family_lock),
        block_on_scope_mismatch=bool(block_on_scope_mismatch),
        block_on_missing_required_evidence=bool(block_on_missing_required_evidence),
        block_on_critical_field_absent=bool(block_on_critical_field_absent),
        blocking_conditions=_normalizar_lista_textual(
            blocking_conditions_text,
            campo="Condições bloqueantes",
        ),
        non_blocking_conditions=_normalizar_lista_textual(
            non_blocking_conditions_text,
            campo="Condições não bloqueantes",
        ),
        red_flags=_normalizar_red_flags_governanca(red_flags_json_text),
        requires_release_active=bool(requires_release_active),
        requires_upload_doc_for_mobile_autonomous=bool(
            requires_upload_doc_for_mobile_autonomous
        ),
        mobile_review_allowed_plans=_normalizar_planos_governanca(
            mobile_review_allowed_plans_text,
            campo="Planos com revisão mobile",
        ),
        mobile_autonomous_allowed_plans=_normalizar_planos_governanca(
            mobile_autonomous_allowed_plans_text,
            campo="Planos com autonomia mobile",
        ),
    )
    familia.review_policy_json = review_policy
    if criado_por_id and not familia.criado_por_id:
        familia.criado_por_id = criado_por_id

    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível salvar a governança de revisão da família.",
    )
    return familia


def upsert_oferta_comercial_familia(
    db: Session,
    *,
    family_key: str,
    offer_key: str = "",
    family_mode_key: str = "",
    nome_oferta: str = "",
    descricao_comercial: str = "",
    pacote_comercial: str = "",
    prazo_padrao_dias: int | str | None = None,
    ativo_comercial: bool = False,
    lifecycle_status: str = "",
    showcase_enabled: bool | None = None,
    versao_oferta: int = 1,
    material_real_status: str = "sintetico",
    material_level: str = "",
    escopo_comercial_text: str = "",
    exclusoes_text: str = "",
    insumos_minimos_text: str = "",
    variantes_comerciais_text: str = "",
    release_channel: str = "",
    bundle_key: str = "",
    bundle_label: str = "",
    bundle_summary: str = "",
    bundle_audience: str = "",
    bundle_highlights_text: str = "",
    included_features_text: str = "",
    entitlement_monthly_issues: int | str | None = None,
    entitlement_max_admin_clients: int | str | None = None,
    entitlement_max_inspectors: int | str | None = None,
    entitlement_max_reviewers: int | str | None = None,
    entitlement_max_active_variants: int | str | None = None,
    entitlement_max_integrations: int | str | None = None,
    template_default_code: str = "",
    flags_json_text: str = "",
    criado_por_id: int | None = None,
) -> OfertaComercialFamiliaLaudo:
    familia = _buscar_familia_catalogo_por_chave(db, family_key)
    mode_key_norm = _normalizar_chave_catalogo(family_mode_key, campo="Modo técnico", max_len=80) if family_mode_key else ""
    modo = None
    if mode_key_norm:
        modo = db.scalar(
            select(ModoTecnicoFamiliaLaudo).where(
                ModoTecnicoFamiliaLaudo.family_id == familia.id,
                ModoTecnicoFamiliaLaudo.mode_key == mode_key_norm,
            )
        )
        if modo is None:
            raise ValueError("Modo técnico não encontrado para a família.")
    oferta = db.scalar(
        select(OfertaComercialFamiliaLaudo).where(OfertaComercialFamiliaLaudo.family_id == familia.id)
    )
    if oferta is None:
        oferta = OfertaComercialFamiliaLaudo(
            family_id=int(familia.id),
            criado_por_id=criado_por_id,
        )
        db.add(oferta)

    prazo_norm: int | None
    if prazo_padrao_dias in (None, ""):
        prazo_norm = None
    else:
        prazo_norm = int(prazo_padrao_dias) if isinstance(prazo_padrao_dias, (int, str)) else None
        if prazo_norm is not None and prazo_norm < 0:
            raise ValueError("Prazo padrão precisa ser zero ou positivo.")

    lifecycle_norm = _normalizar_lifecycle_status_oferta(
        lifecycle_status or ("active" if bool(ativo_comercial) else "draft")
    )
    material_real_norm = _normalizar_status_material_real_oferta(material_real_status)
    material_level_norm = _normalizar_material_level_catalogo(
        material_level
        or (
            "real_calibrated"
            if material_real_norm == "calibrado"
            else "partial"
            if material_real_norm == "parcial"
            else "synthetic"
        )
    )
    offer_key_norm = _normalizar_chave_catalogo(
        offer_key or family_key,
        campo="Offer key",
        max_len=120,
    )

    oferta.nome_oferta = _normalizar_texto_curto(
        nome_oferta or str(familia.nome_exibicao or familia.family_key),
        campo="Nome da oferta",
        max_len=180,
    )
    oferta.offer_key = offer_key_norm
    oferta.family_mode_id = int(modo.id) if modo is not None else None
    oferta.descricao_comercial = _normalizar_texto_opcional(descricao_comercial)
    oferta.pacote_comercial = _normalizar_texto_opcional(pacote_comercial, 80)
    oferta.prazo_padrao_dias = prazo_norm
    oferta.ativo_comercial = lifecycle_norm == "active"
    oferta.lifecycle_status = lifecycle_norm
    oferta.showcase_enabled = bool(
        showcase_enabled if showcase_enabled is not None else lifecycle_norm in {"active", "testing"}
    )
    oferta.versao_oferta = max(1, int(versao_oferta or 1))
    oferta.material_real_status = material_real_norm
    oferta.material_level = material_level_norm
    oferta.escopo_json = _normalizar_lista_textual(escopo_comercial_text, campo="Escopo comercial")
    oferta.exclusoes_json = _normalizar_lista_textual(exclusoes_text, campo="Exclusões")
    oferta.insumos_minimos_json = _normalizar_lista_textual(insumos_minimos_text, campo="Insumos mínimos")
    oferta.variantes_json = _normalizar_variantes_comerciais(variantes_comerciais_text)
    oferta.template_default_code = (
        _normalizar_chave_catalogo(template_default_code, campo="Template default", max_len=120)
        if str(template_default_code or "").strip()
        else None
    )
    flags_payload = _normalizar_json_opcional(flags_json_text, campo="Flags da oferta")
    oferta.flags_json = merge_offer_commercial_flags(
        flags_payload,
        release_channel=_normalizar_release_channel_catalogo(
            release_channel,
            campo="Release channel da oferta",
        ),
        commercial_bundle=_normalizar_bundle_comercial_payload(
            bundle_key=bundle_key,
            bundle_label=bundle_label,
            bundle_summary=bundle_summary,
            bundle_audience=bundle_audience,
            bundle_highlights_text=bundle_highlights_text,
        ),
        contract_entitlements=_normalizar_contract_entitlements_payload(
            included_features_text=included_features_text,
            monthly_issues=entitlement_monthly_issues,
            max_admin_clients=entitlement_max_admin_clients,
            max_inspectors=entitlement_max_inspectors,
            max_reviewers=entitlement_max_reviewers,
            max_active_variants=entitlement_max_active_variants,
            max_integrations=entitlement_max_integrations,
        ),
    )
    oferta.publicado_em = _agora_utc() if oferta.lifecycle_status == "active" else None
    if criado_por_id and not oferta.criado_por_id:
        oferta.criado_por_id = criado_por_id

    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível salvar a oferta comercial da família.",
    )
    return oferta


def upsert_modo_tecnico_familia(
    db: Session,
    *,
    family_key: str,
    mode_key: str,
    nome_exibicao: str,
    descricao: str = "",
    regras_adicionais_json_text: str = "",
    compatibilidade_template_json_text: str = "",
    compatibilidade_oferta_json_text: str = "",
    ativo: bool = True,
    criado_por_id: int | None = None,
) -> ModoTecnicoFamiliaLaudo:
    familia = _buscar_familia_catalogo_por_chave(db, family_key)
    mode_key_norm = _normalizar_chave_catalogo(mode_key, campo="Modo técnico", max_len=80)
    modo = db.scalar(
        select(ModoTecnicoFamiliaLaudo).where(
            ModoTecnicoFamiliaLaudo.family_id == familia.id,
            ModoTecnicoFamiliaLaudo.mode_key == mode_key_norm,
        )
    )
    if modo is None:
        modo = ModoTecnicoFamiliaLaudo(
            family_id=int(familia.id),
            mode_key=mode_key_norm,
            criado_por_id=criado_por_id,
        )
        db.add(modo)

    modo.nome_exibicao = _normalizar_texto_curto(nome_exibicao, campo="Nome do modo", max_len=120)
    modo.descricao = _normalizar_texto_opcional(descricao)
    modo.regras_adicionais_json = _normalizar_json_opcional(
        regras_adicionais_json_text,
        campo="Regras adicionais do modo",
    )
    modo.compatibilidade_template_json = _normalizar_json_opcional(
        compatibilidade_template_json_text,
        campo="Compatibilidade de template",
    )
    modo.compatibilidade_oferta_json = _normalizar_json_opcional(
        compatibilidade_oferta_json_text,
        campo="Compatibilidade de oferta",
    )
    modo.ativo = bool(ativo)
    if criado_por_id and not modo.criado_por_id:
        modo.criado_por_id = criado_por_id

    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível salvar o modo técnico da família.",
    )
    return modo


def upsert_calibracao_familia(
    db: Session,
    *,
    family_key: str,
    calibration_status: str,
    reference_source: str = "",
    last_calibrated_at: datetime | None = None,
    summary_of_adjustments: str = "",
    changed_fields_json_text: str = "",
    changed_language_notes: str = "",
    attachments_json_text: str = "",
    criado_por_id: int | None = None,
) -> CalibracaoFamiliaLaudo:
    familia = _buscar_familia_catalogo_por_chave(db, family_key)
    calibracao = db.scalar(
        select(CalibracaoFamiliaLaudo).where(CalibracaoFamiliaLaudo.family_id == familia.id)
    )
    if calibracao is None:
        calibracao = CalibracaoFamiliaLaudo(
            family_id=int(familia.id),
            criado_por_id=criado_por_id,
        )
        db.add(calibracao)

    calibracao.calibration_status = _normalizar_status_calibracao_catalogo(calibration_status)
    calibracao.reference_source = _normalizar_texto_opcional(reference_source, 255)
    calibracao.last_calibrated_at = last_calibrated_at
    calibracao.summary_of_adjustments = _normalizar_texto_opcional(summary_of_adjustments)
    calibracao.changed_fields_json = _normalizar_json_opcional(changed_fields_json_text, campo="Changed fields")
    calibracao.changed_language_notes = _normalizar_texto_opcional(changed_language_notes)
    calibracao.attachments_json = _normalizar_json_opcional(attachments_json_text, campo="Attachments")
    if criado_por_id and not calibracao.criado_por_id:
        calibracao.criado_por_id = criado_por_id

    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível salvar a calibração da família.",
    )
    return calibracao


def importar_familia_canonica_para_catalogo(
    db: Session,
    *,
    family_key: str,
    status_catalogo: str = "publicado",
    criado_por_id: int | None = None,
) -> FamiliaLaudoCatalogo:
    schema = carregar_family_schema_canonico(family_key)
    evidence_policy = schema.get("evidence_policy")
    review_policy = schema.get("review_policy")
    output_schema_seed = schema.get("output_schema_seed")

    return upsert_familia_catalogo(
        db,
        family_key=str(schema.get("family_key") or family_key),
        nome_exibicao=str(schema.get("nome_exibicao") or family_key),
        macro_categoria=str(schema.get("macro_categoria") or ""),
        descricao=str(schema.get("descricao") or ""),
        status_catalogo=status_catalogo,
        schema_version=int(schema.get("schema_version") or 1),
        evidence_policy_json_text=json.dumps(evidence_policy, ensure_ascii=False) if evidence_policy is not None else "",
        review_policy_json_text=json.dumps(review_policy, ensure_ascii=False) if review_policy is not None else "",
        output_schema_seed_json_text=(
            json.dumps(output_schema_seed, ensure_ascii=False) if output_schema_seed is not None else ""
        ),
        criado_por_id=criado_por_id,
    )


def importar_familias_canonicas_para_catalogo(
    db: Session,
    *,
    family_keys: list[str] | tuple[str, ...] | None = None,
    status_catalogo: str = "publicado",
    criado_por_id: int | None = None,
) -> list[FamiliaLaudoCatalogo]:
    schemas = listar_family_schemas_canonicos()
    family_keys_resolvidas = list(family_keys or [item["family_key"] for item in schemas])
    familias_importadas: list[FamiliaLaudoCatalogo] = []
    vistos: set[str] = set()
    for item in family_keys_resolvidas:
        family_key = _normalizar_chave_catalogo(item, campo="Family key", max_len=120)
        if family_key in vistos:
            continue
        vistos.add(family_key)
        familias_importadas.append(
            importar_familia_canonica_para_catalogo(
                db,
                family_key=family_key,
                status_catalogo=status_catalogo,
                criado_por_id=criado_por_id,
            )
        )
    return familias_importadas


def _catalog_row_matches_filters(
    row: dict[str, Any],
    *,
    filtro_macro_categoria: str = "",
    filtro_status_tecnico: str = "",
    filtro_prontidao: str = "",
    filtro_status_comercial: str = "",
    filtro_calibracao: str = "",
    filtro_liberacao: str = "",
    filtro_template_default: str = "",
    filtro_oferta_ativa: str = "",
    filtro_mode: str = "",
) -> bool:
    if filtro_macro_categoria:
        if str(row["macro_category"]).strip().lower() != str(filtro_macro_categoria).strip().lower():
            return False
    if filtro_status_tecnico:
        if str((row["technical_status"] or {}).get("key") or "") != _normalizar_status_tecnico_catalogo(filtro_status_tecnico):
            return False
    if filtro_prontidao:
        if str((row["readiness"] or {}).get("key") or "") != str(filtro_prontidao).strip().lower():
            return False
    if filtro_status_comercial:
        comparado = str((row["commercial_status"] or {}).get("key") or "")
        desejado = str(filtro_status_comercial).strip().lower()
        if desejado == "none":
            if comparado != "none":
                return False
        elif comparado != _normalizar_lifecycle_status_oferta(desejado):
            return False
    if filtro_calibracao:
        if str((row["calibration_status"] or {}).get("key") or "") != _normalizar_status_calibracao_catalogo(filtro_calibracao):
            return False
    if filtro_liberacao:
        desejado = str(filtro_liberacao).strip().lower()
        ativos = int(row["active_release_count"])
        if desejado == "active" and ativos <= 0:
            return False
        if desejado == "none" and ativos > 0:
            return False
    if filtro_template_default:
        desejado = str(filtro_template_default).strip().lower()
        template_default = str(row.get("template_default_code") or "").strip().lower()
        if desejado == "configured" and not (template_default or row["artifact_snapshot"]["has_template_seed"]):
            return False
        if desejado == "unconfigured" and (template_default or row["artifact_snapshot"]["has_template_seed"]):
            return False
        if desejado not in {"configured", "unconfigured"} and template_default != desejado:
            return False
    if filtro_oferta_ativa:
        desejado = str(filtro_oferta_ativa).strip().lower()
        ativa = str((row["commercial_status"] or {}).get("key") or "") == "active"
        if desejado == "true" and not ativa:
            return False
        if desejado == "false" and ativa:
            return False
    if filtro_mode:
        desejado = str(filtro_mode).strip().lower()
        modos = [str(item.get("mode_key") or "").strip().lower() for item in row["modes"]]
        if desejado == "available" and not modos:
            return False
        if desejado not in {"available", ""} and desejado not in modos:
            return False
    return True


def listar_metodos_catalogo(db: Session) -> list[MetodoCatalogoInspecao]:
    stmt = select(MetodoCatalogoInspecao).order_by(
        MetodoCatalogoInspecao.categoria.asc(),
        MetodoCatalogoInspecao.nome_exibicao.asc(),
    )
    return list(db.scalars(stmt).all())


def resumir_catalogo_laudos_admin(
    db: Session,
    *,
    filtro_busca: str = "",
    filtro_macro_categoria: str = "",
    filtro_status_tecnico: str = "",
    filtro_prontidao: str = "",
    filtro_status_comercial: str = "",
    filtro_calibracao: str = "",
    filtro_liberacao: str = "",
    filtro_template_default: str = "",
    filtro_oferta_ativa: str = "",
    filtro_mode: str = "",
) -> dict[str, Any]:
    familias = listar_catalogo_familias(db, filtro_busca=filtro_busca, filtro_classificacao="family")
    ofertas_comerciais = listar_ofertas_comerciais_catalogo(db)
    metodos_catalogo = listar_metodos_catalogo(db)
    familias_canonicas = listar_family_schemas_canonicos()
    rows_all = [_serializar_familia_catalogo_row(item) for item in familias]
    rows = [
        item
        for item in rows_all
        if _catalog_row_matches_filters(
            item,
            filtro_macro_categoria=filtro_macro_categoria,
            filtro_status_tecnico=filtro_status_tecnico,
            filtro_prontidao=filtro_prontidao,
            filtro_status_comercial=filtro_status_comercial,
            filtro_calibracao=filtro_calibracao,
            filtro_liberacao=filtro_liberacao,
            filtro_template_default=filtro_template_default,
            filtro_oferta_ativa=filtro_oferta_ativa,
            filtro_mode=filtro_mode,
        )
    ]
    family_keys_no_recorte = {
        str(item["family_key"]).strip().lower()
        for item in rows
        if str(item.get("family_key") or "").strip()
    }
    familias_no_recorte = [
        item
        for item in familias
        if str(getattr(item, "family_key", "") or "").strip().lower() in family_keys_no_recorte
    ]
    rows = _enrich_catalog_rows_with_document_preview(
        rows=rows,
        families=familias_no_recorte,
        metodos_catalogo=metodos_catalogo,
    )
    total_publicadas = sum(1 for item in rows_all if item["technical_status"]["key"] == "ready")
    total_rascunho = sum(1 for item in rows_all if item["technical_status"]["key"] == "draft")
    total_arquivadas = sum(1 for item in rows_all if item["technical_status"]["key"] == "deprecated")
    total_ofertas_comerciais = len(ofertas_comerciais)
    total_ofertas_ativas = sum(1 for item in ofertas_comerciais if _offer_lifecycle_resolvido(item) == "active")
    total_familias_calibradas = sum(1 for item in rows_all if item["calibration_status"]["key"] == "real_calibrated")
    total_variantes_comerciais = sum(int(item["variant_count"]) for item in rows_all)
    template_library_rollup = _build_template_library_rollup(rows_all)
    material_real_rollup = _build_material_real_rollup(rows_all)
    commercial_scale_rollup = _build_commercial_scale_rollup(rows_all)
    calibration_queue_rollup = _build_calibration_queue_rollup(rows_all)
    material_real_priority_rollup = {
        "priority_modes": material_real_rollup.get("priority_modes", []),
        "highlights": material_real_rollup.get("priority_highlights", []),
    }
    macro_categorias = sorted(
        {
            str(item["macro_category"] or "").strip()
            for item in rows_all
            if str(item["macro_category"] or "").strip()
        },
        key=_catalog_macro_category_sort_key,
    )
    template_defaults = sorted(
        {
            str(item.get("template_default_code") or "").strip()
            for item in rows_all
            if str(item.get("template_default_code") or "").strip()
        }
    )
    return {
        "familias": familias,
        "catalog_rows": rows,
        "catalog_rows_total": len(rows_all),
        "ofertas_comerciais": ofertas_comerciais,
        "metodos_catalogo": metodos_catalogo,
        "familias_canonicas": familias_canonicas,
        "macro_categorias": macro_categorias,
        "template_default_options": template_defaults,
        "governance_rollup": _build_catalog_governance_rollup(
            db,
            families=familias_no_recorte,
        ),
        "template_library_rollup": template_library_rollup,
        "material_real_rollup": material_real_rollup,
        "commercial_scale_rollup": commercial_scale_rollup,
        "material_real_priority_rollup": material_real_priority_rollup,
        "calibration_queue_rollup": calibration_queue_rollup,
        "total_familias": len(rows_all),
        "total_publicadas": int(total_publicadas),
        "total_rascunho": int(total_rascunho),
        "total_arquivadas": int(total_arquivadas),
        "total_ofertas_comerciais": int(total_ofertas_comerciais),
        "total_ofertas_ativas": int(total_ofertas_ativas),
        "total_familias_calibradas": int(total_familias_calibradas),
        "total_variantes_comerciais": int(total_variantes_comerciais),
        "total_familias_canonicas": len(familias_canonicas),
        "total_metodos_catalogados": len(metodos_catalogo),
        "filtros": {
            "busca": filtro_busca,
            "macro_categoria": filtro_macro_categoria,
            "status_tecnico": filtro_status_tecnico,
            "prontidao": filtro_prontidao,
            "status_comercial": filtro_status_comercial,
            "calibracao": filtro_calibracao,
            "liberacao": filtro_liberacao,
            "template_default": filtro_template_default,
            "oferta_ativa": filtro_oferta_ativa,
            "mode": filtro_mode,
        },
    }


def _catalogo_actor_label(actor: Usuario | None, *, fallback: str = "Sistema Tariel") -> str:
    if actor is None:
        return fallback
    nome = str(getattr(actor, "nome_completo", "") or getattr(actor, "email", "") or "").strip()
    if nome:
        return nome
    actor_id = getattr(actor, "id", None)
    return f"Usuário #{int(actor_id)}" if actor_id else fallback


def _serializar_release_catalogo_familia(
    item: TenantFamilyReleaseLaudo,
    *,
    empresa_lookup: dict[int, Empresa],
    oferta: OfertaComercialFamiliaLaudo | None = None,
) -> dict[str, Any]:
    tenant = empresa_lookup.get(int(item.tenant_id))
    release_status = str(getattr(item, "release_status", "") or "").strip().lower() or "draft"
    commercial = summarize_release_contract_governance(
        getattr(item, "governance_policy_json", None),
        offer_flags_payload=getattr(oferta, "flags_json", None) if oferta is not None else None,
        offer_lifecycle_status=_offer_lifecycle_resolvido(oferta),
    )
    return {
        "id": int(item.id),
        "tenant_id": int(item.tenant_id),
        "tenant_label": str(getattr(tenant, "nome_fantasia", "") or f"Empresa {item.tenant_id}"),
        "release_status": _label_catalogo(
            _CATALOGO_RELEASE_STATUS_LABELS,
            release_status,
            release_status or "Rascunho",
        ),
        "allowed_modes": list(getattr(item, "allowed_modes_json", None) or []),
        "allowed_offers": list(getattr(item, "allowed_offers_json", None) or []),
        "allowed_templates": list(getattr(item, "allowed_templates_json", None) or []),
        "allowed_variants": list(getattr(item, "allowed_variants_json", None) or []),
        "default_template_code": str(getattr(item, "default_template_code", "") or "").strip() or None,
        "default_template_label": _catalogo_modelo_label(
            str(getattr(item, "default_template_code", "") or "").strip() or None,
            fallback="Herdado da família",
        ),
        "observacoes": str(getattr(item, "observacoes", "") or "").strip() or None,
        "start_at": _normalizar_datetime_admin(getattr(item, "start_at", None)),
        "end_at": _normalizar_datetime_admin(getattr(item, "end_at", None)),
        "start_at_label": _formatar_data_admin(_normalizar_datetime_admin(getattr(item, "start_at", None)), fallback="Imediato"),
        "end_at_label": _formatar_data_admin(_normalizar_datetime_admin(getattr(item, "end_at", None)), fallback="Sem expiração"),
        "updated_at": _normalizar_datetime_admin(getattr(item, "atualizado_em", None)),
        "updated_at_label": _formatar_data_admin(_normalizar_datetime_admin(getattr(item, "atualizado_em", None))),
        "actor_label": _catalogo_actor_label(getattr(item, "criado_por", None)),
        "governance": _resumir_governanca_release_policy(
            getattr(item, "governance_policy_json", None)
        ),
        "effective_release_channel": commercial["effective_release_channel"],
        "contract_entitlements": commercial["effective_contract_entitlements"],
        "scope_summary": _catalogo_scope_summary_label(
            allowed_modes=list(getattr(item, "allowed_modes_json", None) or []),
            allowed_templates=list(getattr(item, "allowed_templates_json", None) or []),
            allowed_variants=list(getattr(item, "allowed_variants_json", None) or []),
        ),
    }


def _historico_catalogo_familia(
    familia: FamiliaLaudoCatalogo,
    *,
    tenant_releases: list[TenantFamilyReleaseLaudo],
) -> list[dict[str, Any]]:
    eventos: list[dict[str, Any]] = []

    tipo_labels = {
        "family": "Família",
        "offer": "Oferta",
        "calibration": "Calibração",
        "tenant_release": "Liberação para empresa",
    }

    def _push(
        tipo: str,
        titulo: str,
        quando: datetime | None,
        detalhe: str = "",
        *,
        actor_label: str = "Sistema Tariel",
        diff_summary: str = "",
    ) -> None:
        quando_norm = _normalizar_datetime_admin(quando)
        if quando_norm is None:
            return
        eventos.append(
            {
                "tipo": tipo,
                "tipo_label": tipo_labels.get(tipo, "Evento"),
                "titulo": titulo,
                "detalhe": detalhe,
                "actor_label": actor_label,
                "diff_summary": diff_summary,
                "quando": quando_norm,
                "quando_label": _formatar_data_admin(quando_norm),
            }
        )

    macro_categoria = str(getattr(familia, "macro_categoria", "") or "").strip() or "Sem macro categoria"
    _push(
        "family",
        "Família atualizada",
        _normalizar_datetime_admin(getattr(familia, "atualizado_em", None)) or _normalizar_datetime_admin(getattr(familia, "criado_em", None)),
        f"Status técnico: {str(getattr(familia, 'technical_status', '') or 'draft')}.",
        actor_label=_catalogo_actor_label(getattr(familia, "criado_por", None)),
        diff_summary=f"Schema v{int(getattr(familia, 'schema_version', 1) or 1)} • macro {macro_categoria}",
    )
    oferta = getattr(familia, "oferta_comercial", None)
    if oferta is not None:
        variants = catalog_offer_variants(familia, oferta)
        _push(
            "offer",
            "Oferta comercial revisada",
            _normalizar_datetime_admin(getattr(oferta, "atualizado_em", None)) or _normalizar_datetime_admin(getattr(oferta, "criado_em", None)),
            f"Situação do pacote: {str(getattr(oferta, 'lifecycle_status', '') or _offer_lifecycle_resolvido(oferta) or 'draft')}.",
            actor_label=_catalogo_actor_label(getattr(oferta, "criado_por", None)),
            diff_summary=" • ".join(
                trecho
                for trecho in (
                    "modelo principal "
                    + str(
                        _catalogo_modelo_label(
                            str(getattr(oferta, "template_default_code", "") or "").strip() or None,
                            fallback="em definição",
                        )
                    ),
                    f"{len(variants)} opções",
                    str(getattr(oferta, "pacote_comercial", "") or "").strip() or "",
                )
                if trecho
            ),
        )
    calibracao = getattr(familia, "calibracao", None)
    if calibracao is not None:
        changed_fields = list(getattr(calibracao, "changed_fields_json", None) or [])
        _push(
            "calibration",
            "Calibração registrada",
            _normalizar_datetime_admin(getattr(calibracao, "last_calibrated_at", None))
            or _normalizar_datetime_admin(getattr(calibracao, "atualizado_em", None)),
            f"Status: {str(getattr(calibracao, 'calibration_status', '') or 'none')}.",
            actor_label=_catalogo_actor_label(getattr(calibracao, "criado_por", None)),
            diff_summary=" • ".join(
                trecho
                for trecho in (
                    _catalogo_texto_leitura(
                        str(getattr(calibracao, "reference_source", "") or "").strip() or None
                    )
                    or "",
                    f"{len(changed_fields)} campos alterados" if changed_fields else "",
                )
                if trecho
            ),
        )
    for item in tenant_releases:
        _push(
            "tenant_release",
            "Liberação para empresa revisada",
            _normalizar_datetime_admin(getattr(item, "atualizado_em", None)) or _normalizar_datetime_admin(getattr(item, "criado_em", None)),
            f"Empresa {int(item.tenant_id)} em {str(getattr(item, 'release_status', '') or 'draft')}.",
            actor_label=_catalogo_actor_label(getattr(item, "criado_por", None)),
            diff_summary=" • ".join(
                trecho
                for trecho in (
                    _catalogo_modelo_label(
                        str(getattr(item, "default_template_code", "") or "").strip() or None,
                        fallback="modelo herdado",
                    ),
                    f"{len(list(getattr(item, 'allowed_templates_json', None) or []))} modelos"
                    if list(getattr(item, "allowed_templates_json", None) or [])
                    else "",
                    f"{len(list(getattr(item, 'allowed_variants_json', None) or []))} opções"
                    if list(getattr(item, "allowed_variants_json", None) or [])
                    else "",
                )
                if trecho
            ),
        )
    eventos.sort(key=lambda item: item["quando"], reverse=True)
    return eventos


def buscar_catalogo_familia_admin(db: Session, family_key: str) -> dict[str, Any] | None:
    family_key_norm = _normalizar_chave_catalogo(family_key, campo="Family key", max_len=120)
    familia = db.scalar(
        select(FamiliaLaudoCatalogo)
        .options(
            selectinload(FamiliaLaudoCatalogo.criado_por),
            selectinload(FamiliaLaudoCatalogo.oferta_comercial).selectinload(OfertaComercialFamiliaLaudo.criado_por),
            selectinload(FamiliaLaudoCatalogo.modos_tecnicos).selectinload(ModoTecnicoFamiliaLaudo.criado_por),
            selectinload(FamiliaLaudoCatalogo.calibracao).selectinload(CalibracaoFamiliaLaudo.criado_por),
            selectinload(FamiliaLaudoCatalogo.tenant_releases).selectinload(TenantFamilyReleaseLaudo.criado_por),
        )
        .where(FamiliaLaudoCatalogo.family_key == family_key_norm)
    )
    if familia is None:
        return None

    oferta = getattr(familia, "oferta_comercial", None)
    offer_governance = (
        _dict_payload_admin(
            summarize_offer_commercial_governance(
                getattr(oferta, "flags_json", None),
                offer_lifecycle_status=_offer_lifecycle_resolvido(oferta),
            )
        )
        if oferta is not None
        else {}
    )
    releases = list(
        db.scalars(
            select(TenantFamilyReleaseLaudo)
            .options(selectinload(TenantFamilyReleaseLaudo.criado_por))
            .where(TenantFamilyReleaseLaudo.family_id == familia.id)
            .order_by(TenantFamilyReleaseLaudo.tenant_id.asc())
        ).all()
    )
    empresas = list(
        db.scalars(
            select(Empresa)
            .where(Empresa.escopo_plataforma.is_(False))
            .order_by(Empresa.nome_fantasia.asc())
        ).all()
    )
    empresa_lookup = {int(item.id): item for item in empresas}
    artifact_snapshot = _catalog_family_artifact_snapshot(str(familia.family_key))
    row = _serializar_familia_catalogo_row(familia, artifact_snapshot=artifact_snapshot)
    template_library_rollup = _build_template_library_rollup([row])
    material_real_workspace = _build_material_real_workspace_summary(str(familia.family_key))
    try:
        family_schema = carregar_family_schema_canonico(str(familia.family_key))
    except ValueError:
        family_schema = None

    variantes = catalog_offer_variants(familia, oferta)
    available_variant_tokens = [
        f"catalog:{str(familia.family_key).strip().lower()}:{str(item.get('variant_key') or '').strip().lower()}"
        for item in variantes
        if str(item.get("variant_key") or "").strip()
    ]
    family_methods = [
        {
            "method_key": str(item.method_key),
            "display_name": str(item.nome_exibicao),
            "categoria": str(item.categoria),
        }
        for item in listar_metodos_catalogo(db)
        if str(getattr(item, "method_key", "") or "").strip() in str(familia.family_key)
    ]
    calibration_payload = {
        "status": _label_catalogo(
            _CATALOGO_CALIBRATION_STATUS_LABELS,
            _calibracao_status_resolvido(familia, oferta),
            "Sem calibração",
        ),
        "reference_source": str(getattr(getattr(familia, "calibracao", None), "reference_source", "") or "").strip() or None,
        "reference_source_label": _catalogo_texto_leitura(
            str(getattr(getattr(familia, "calibracao", None), "reference_source", "") or "").strip() or None,
            fallback="Sem fonte de referência",
        ),
        "summary": str(getattr(getattr(familia, "calibracao", None), "summary_of_adjustments", "") or "").strip() or None,
        "changed_language_notes": str(getattr(getattr(familia, "calibracao", None), "changed_language_notes", "") or "").strip() or None,
        "changed_fields": list(getattr(getattr(familia, "calibracao", None), "changed_fields_json", None) or []),
        "attachments": [
            {
                "label": str(item.get("label") or item.get("name") or item.get("path") or "Anexo de calibração").strip(),
                "path": str(item.get("path") or "").strip() or None,
            }
            for item in list(getattr(getattr(familia, "calibracao", None), "attachments_json", None) or [])
            if isinstance(item, dict)
        ],
        "last_calibrated_at_label": _formatar_data_admin(
            _normalizar_datetime_admin(getattr(getattr(familia, "calibracao", None), "last_calibrated_at", None))
        ),
        "actor_label": _catalogo_actor_label(getattr(getattr(familia, "calibracao", None), "criado_por", None)),
    }
    document_preview = _build_document_preview_summary(
        row=row,
        artifact_snapshot=artifact_snapshot,
        family_schema=family_schema,
        offer=(
            {
                "offer_name": str(getattr(oferta, "nome_oferta", "") or "").strip() or str(familia.nome_exibicao),
                "description": str(getattr(oferta, "descricao_comercial", "") or "").strip() or None,
                "template_default_code": str(getattr(oferta, "template_default_code", "") or "").strip() or None,
            }
            if oferta is not None
            else None
        ),
        calibration=calibration_payload,
        material_real_workspace=material_real_workspace,
        family_methods=family_methods,
    )
    variant_library = _build_variant_library_summary(
        family_key=str(familia.family_key),
        offer={
            "variants": variantes,
            "offer_name": str(getattr(oferta, "nome_oferta", "") or "").strip() or None,
        }
        if oferta is not None
        else None,
        artifact_snapshot=artifact_snapshot,
        active_release_count=int(row.get("active_release_count") or 0),
    )
    material_real_priority = _build_material_real_priority_summary(row, material_real_workspace)
    template_refinement_target = _build_template_refinement_target(
        family_key=str(familia.family_key),
        display_name=str(row.get("display_name") or familia.family_key),
        material_real_priority=material_real_priority,
        variant_library=variant_library,
        template_default_code=str(row.get("template_default_code") or "").strip() or None,
        active_release_count=int(row.get("active_release_count") or 0),
    )
    return {
        "family": row,
        "family_entity": familia,
        "review_governance": _resumir_governanca_review_policy(
            getattr(familia, "review_policy_json", None)
        ),
        "family_schema": family_schema,
        "artifact_snapshot": artifact_snapshot,
        "template_library": {
            "registry_path": template_library_rollup.get("registry_path"),
            "registry_templates": template_library_rollup.get("templates", []),
            "has_full_canonical_artifact_chain": all(
                bool(artifact_snapshot.get(key)) for key in (
                    "has_family_schema",
                    "has_template_seed",
                    "has_laudo_output_seed",
                    "has_laudo_output_exemplo",
                )
            ),
            "missing_artifacts": [
                label
                for key, label in (
                    ("has_family_schema", "Estrutura da família"),
                    ("has_template_seed", "Modelo base"),
                    ("has_laudo_output_seed", "Documento base"),
                    ("has_laudo_output_exemplo", "Exemplo do documento"),
                )
                if not bool(artifact_snapshot.get(key))
            ],
            "template_default_code": row.get("template_default_code"),
            "template_default_label": _catalogo_modelo_label(
                str(row.get("template_default_code") or "").strip() or None
            ),
        },
        "material_real_workspace": material_real_workspace,
        "technical_modes": [
            {
                "id": int(item.id),
                "mode_key": str(item.mode_key),
                "display_name": str(item.nome_exibicao),
                "description": str(getattr(item, "descricao", "") or "").strip() or None,
                "active": bool(item.ativo),
                "actor_label": _catalogo_actor_label(getattr(item, "criado_por", None)),
                "updated_at_label": _formatar_data_admin(
                    _normalizar_datetime_admin(getattr(item, "atualizado_em", None) or getattr(item, "criado_em", None))
                ),
            }
            for item in list(getattr(familia, "modos_tecnicos", None) or [])
        ],
        "offer": (
            {
                "id": int(oferta.id),
                "offer_key": str(getattr(oferta, "offer_key", "") or "").strip() or str(familia.family_key),
                "offer_name": str(getattr(oferta, "nome_oferta", "") or "").strip() or str(familia.nome_exibicao),
                "package_name": str(getattr(oferta, "pacote_comercial", "") or "").strip() or None,
                "description": str(getattr(oferta, "descricao_comercial", "") or "").strip() or None,
                "release_channel": offer_governance["release_channel"],
                "commercial_bundle": offer_governance["commercial_bundle"],
                "contract_entitlements": offer_governance["contract_entitlements"],
                "lifecycle_status": _label_catalogo(
                    _CATALOGO_LIFECYCLE_STATUS_LABELS,
                    _offer_lifecycle_resolvido(oferta) or "draft",
                    "Draft",
                ),
                "material_level": _label_catalogo(
                    _CATALOGO_CALIBRATION_STATUS_LABELS,
                    _calibracao_status_resolvido(familia, oferta),
                    "Sem calibração",
                ),
                "showcase_enabled": bool(getattr(oferta, "showcase_enabled", False)),
                "template_default_code": str(getattr(oferta, "template_default_code", "") or "").strip() or None,
                "template_display_name": _catalogo_modelo_label(
                    str(getattr(oferta, "template_default_code", "") or "").strip() or None,
                    fallback="Modelo principal em definição",
                ),
                "scope_items": list(getattr(oferta, "escopo_json", None) or []),
                "exclusion_items": list(getattr(oferta, "exclusoes_json", None) or []),
                "minimum_inputs": list(getattr(oferta, "insumos_minimos_json", None) or []),
                "variants": variantes,
                "actor_label": _catalogo_actor_label(getattr(oferta, "criado_por", None)),
                "updated_at_label": _formatar_data_admin(
                    _normalizar_datetime_admin(getattr(oferta, "atualizado_em", None) or getattr(oferta, "criado_em", None))
                ),
            }
            if oferta is not None
            else None
        ),
        "calibration": calibration_payload,
        "material_real_priority": material_real_priority,
        "document_preview": document_preview,
        "variant_library": variant_library,
        "template_refinement_target": template_refinement_target,
        "tenant_releases": [
            _serializar_release_catalogo_familia(
                item,
                empresa_lookup=empresa_lookup,
                oferta=oferta,
            )
            for item in releases
        ],
        "tenants": [
            {
                "id": int(item.id),
                "label": str(item.nome_fantasia),
            }
            for item in empresas
        ],
        "available_variant_tokens": available_variant_tokens,
        "family_methods": family_methods,
        "available_methods": [
            {
                "method_key": str(item.method_key),
                "display_name": str(item.nome_exibicao),
                "categoria": str(item.categoria),
            }
            for item in listar_metodos_catalogo(db)
        ],
        "history": _historico_catalogo_familia(familia, tenant_releases=releases),
    }


def upsert_tenant_family_release(
    db: Session,
    *,
    tenant_id: int,
    family_key: str,
    release_status: str,
    allowed_modes: list[str] | tuple[str, ...] | str | None = None,
    allowed_offers: list[str] | tuple[str, ...] | str | None = None,
    allowed_templates: list[str] | tuple[str, ...] | str | None = None,
    allowed_variants: list[str] | tuple[str, ...] | str | None = None,
    force_review_mode: str = "",
    max_review_mode: str = "",
    mobile_review_override: str = "",
    mobile_autonomous_override: str = "",
    release_channel_override: str = "",
    included_features_text: str = "",
    entitlement_monthly_issues: int | str | None = None,
    entitlement_max_admin_clients: int | str | None = None,
    entitlement_max_inspectors: int | str | None = None,
    entitlement_max_reviewers: int | str | None = None,
    entitlement_max_active_variants: int | str | None = None,
    entitlement_max_integrations: int | str | None = None,
    default_template_code: str = "",
    observacoes: str = "",
    criado_por_id: int | None = None,
) -> TenantFamilyReleaseLaudo:
    empresa = _buscar_empresa(db, int(tenant_id))
    familia = _buscar_familia_catalogo_por_chave(db, family_key)
    oferta = getattr(familia, "oferta_comercial", None)
    registro = db.scalar(
        select(TenantFamilyReleaseLaudo).where(
            TenantFamilyReleaseLaudo.tenant_id == int(empresa.id),
            TenantFamilyReleaseLaudo.family_id == int(familia.id),
        )
    )
    if registro is None:
        registro = TenantFamilyReleaseLaudo(
            tenant_id=int(empresa.id),
            family_id=int(familia.id),
            criado_por_id=criado_por_id,
        )
        db.add(registro)

    release_status_norm = _normalizar_status_release_catalogo(release_status)
    allowed_modes_norm = _normalizar_lista_json_canonica(allowed_modes, campo="Allowed modes")
    allowed_offers_norm = _normalizar_lista_json_canonica(allowed_offers, campo="Allowed offers")
    allowed_templates_norm = _normalizar_lista_json_canonica(allowed_templates, campo="Allowed templates")
    allowed_variants_norm = _normalizar_selection_tokens_catalogo(allowed_variants, campo="Allowed variants")
    governance_policy = _merge_release_governance_policy(
        dict(getattr(registro, "governance_policy_json", None) or {})
        if isinstance(getattr(registro, "governance_policy_json", None), dict)
        else {},
        force_review_mode=_normalizar_review_mode_governanca(
            force_review_mode,
            campo="Force review mode",
        ),
        max_review_mode=_normalizar_review_mode_governanca(
            max_review_mode,
            campo="Max review mode",
        ),
        mobile_review_override=_normalizar_override_tristate(
            mobile_review_override,
            campo="Override de revisão mobile",
        ),
        mobile_autonomous_override=_normalizar_override_tristate(
            mobile_autonomous_override,
            campo="Override de autonomia mobile",
        ),
        release_channel_override=_normalizar_release_channel_catalogo(
            release_channel_override,
            campo="Override de release channel",
        ),
        contract_entitlements=_normalizar_contract_entitlements_payload(
            included_features_text=included_features_text,
            monthly_issues=entitlement_monthly_issues,
            max_admin_clients=entitlement_max_admin_clients,
            max_inspectors=entitlement_max_inspectors,
            max_reviewers=entitlement_max_reviewers,
            max_active_variants=entitlement_max_active_variants,
            max_integrations=entitlement_max_integrations,
        ),
    )
    registro.offer_id = int(oferta.id) if oferta is not None else None
    registro.allowed_modes_json = allowed_modes_norm
    registro.allowed_offers_json = allowed_offers_norm
    registro.allowed_templates_json = allowed_templates_norm
    registro.allowed_variants_json = allowed_variants_norm
    registro.governance_policy_json = governance_policy
    registro.default_template_code = (
        _normalizar_chave_catalogo(default_template_code, campo="Template default", max_len=120)
        if str(default_template_code or "").strip()
        else None
    )
    registro.release_status = release_status_norm
    registro.start_at = _agora_utc() if release_status_norm == "active" and getattr(registro, "start_at", None) is None else getattr(registro, "start_at", None)
    registro.end_at = _agora_utc() if release_status_norm in {"paused", "expired"} else None
    registro.observacoes = _normalizar_texto_opcional(observacoes)
    if criado_por_id and not registro.criado_por_id:
        registro.criado_por_id = criado_por_id

    ativos_existentes = list_active_tenant_catalog_activations(db, empresa_id=int(empresa.id))
    outros_tokens = [
        f"catalog:{str(item.family_key).strip().lower()}:{str(item.variant_key).strip().lower()}"
        for item in ativos_existentes
        if str(item.family_key).strip().lower() != str(familia.family_key).strip().lower()
    ]
    tokens_familia = allowed_variants_norm if release_status_norm == "active" else []
    sync_tenant_catalog_activations(
        db,
        empresa_id=int(empresa.id),
        selection_tokens=[*outros_tokens, *(tokens_familia or [])],
        admin_id=criado_por_id,
    )

    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível salvar a liberação por tenant da família.",
    )
    return registro


def resumir_portfolio_catalogo_empresa(db: Session, *, empresa_id: int) -> dict[str, Any]:
    return build_admin_tenant_catalog_snapshot(db, empresa_id=int(empresa_id))


def sincronizar_portfolio_catalogo_empresa(
    db: Session,
    *,
    empresa_id: int,
    selection_tokens: list[str] | tuple[str, ...],
    admin_id: int | None = None,
) -> dict[str, Any]:
    _buscar_empresa(db, int(empresa_id))
    resultado = sync_tenant_catalog_activations(
        db,
        empresa_id=int(empresa_id),
        selection_tokens=selection_tokens,
        admin_id=int(admin_id) if admin_id is not None else None,
    )
    flush_ou_rollback_integridade(
        db,
        logger_operacao=logger,
        mensagem_erro="Não foi possível sincronizar o portfólio comercial do tenant.",
    )
    return resultado


# =========================================================
# ONBOARDING
# =========================================================


def registrar_novo_cliente(
    db: Session,
    nome: str,
    cnpj: str,
    email_admin: str,
    plano: str,
    segmento: str = "",
    cidade_estado: str = "",
    nome_responsavel: str = "",
    observacoes: str = "",
    admin_cliente_case_visibility_mode: str = "",
    admin_cliente_case_action_mode: str = "",
    admin_cliente_operating_model: str = "",
    admin_cliente_mobile_web_inspector_enabled: str | bool = "",
    admin_cliente_mobile_web_review_enabled: str | bool = "",
    admin_cliente_operational_user_cross_portal_enabled: str | bool = "",
    admin_cliente_operational_user_admin_portal_enabled: str | bool = "",
    provisionar_inspetor_inicial: str | bool = "",
    inspetor_nome: str = "",
    inspetor_email: str = "",
    inspetor_telefone: str = "",
    provisionar_revisor_inicial: str | bool = "",
    revisor_nome: str = "",
    revisor_email: str = "",
    revisor_telefone: str = "",
    revisor_crea: str = "",
) -> tuple[Empresa, str, str | None]:
    return _tenant_onboarding_services.registrar_novo_cliente(
        db,
        nome=nome,
        cnpj=cnpj,
        email_admin=email_admin,
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
        normalizar_cnpj_fn=_normalizar_cnpj,
        welcome_email_fn=_disparar_email_boas_vindas,
        password_generator=gerar_senha_fortificada,
    )


# =========================================================
# PAINEL ADMINISTRATIVO
# =========================================================


def buscar_metricas_ia_painel(db: Session) -> dict[str, Any]:
    return _admin_dashboard_services.buscar_metricas_ia_painel(
        db,
        tenant_client_clause_fn=_tenant_cliente_clause,
        plan_priority_clause_fn=_case_prioridade_plano,
        now_fn=_agora_utc,
        list_catalog_families_fn=listar_catalogo_familias,
        serialize_catalog_row_fn=_serializar_familia_catalogo_row,
        build_governance_rollup_fn=_build_catalog_governance_rollup,
        build_commercial_scale_rollup_fn=_build_commercial_scale_rollup,
        build_calibration_queue_rollup_fn=_build_calibration_queue_rollup,
    )


# =========================================================
# GESTÃO DE CLIENTES SAAS
# =========================================================


def buscar_detalhe_cliente(db: Session, empresa_id: int) -> dict[str, Any] | None:
    return _tenant_client_read_services.buscar_detalhe_cliente(
        db,
        empresa_id,
        portfolio_summary_fn=resumir_portfolio_catalogo_empresa,
        tenant_admin_policy_summary_fn=summarize_tenant_admin_policy,
        user_serializer=_serializar_usuario_admin,
        first_access_summary_fn=_resumir_primeiro_acesso_empresa,
        signatory_serializer=_serializar_signatario_governado_admin,
    )


# =========================================================
# STUB DE COMUNICAÇÃO
# =========================================================


_aviso_notificacao_boas_vindas = _tenant_onboarding_services._aviso_notificacao_boas_vindas


def _disparar_email_boas_vindas(email: str, empresa: str, senha: str) -> str | None:
    return _tenant_onboarding_services._disparar_email_boas_vindas(
        email,
        empresa,
        senha,
        notification_backend=_BACKEND_NOTIFICACAO_BOAS_VINDAS,
        logger_operacao=logger,
        aviso_factory=_aviso_notificacao_boas_vindas,
    )
