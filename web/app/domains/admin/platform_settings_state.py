from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import env_int, env_str
from app.shared.database import (
    ConfiguracaoPlataforma,
    PlanoEmpresa,
    RegistroAuditoriaEmpresa,
    Usuario,
)

logger = logging.getLogger("tariel.saas")

_REVIEW_UI_CANONICAL_ENV = "REVIEW_UI_CANONICAL"
_REVIEW_UI_PRIMARY_SURFACE_ENV = "TARIEL_REVIEW_DESK_PRIMARY_SURFACE"

_SUPPORT_EXCEPTIONAL_MODE_LABELS = {
    "disabled": "Desabilitado",
    "approval_required": "Aprovação obrigatória",
    "incident_controlled": "Incidente controlado",
}
_SUPPORT_EXCEPTIONAL_SCOPE_LABELS = {
    "metadata_only": "Metadados administrativos",
    "administrative": "Suporte administrativo",
    "tenant_diagnostic": "Diagnóstico de tenant",
}
_REVIEW_UI_LABELS = {
    "ssr": "SSR legado",
}
_SETTING_SOURCE_LABELS = {
    "database": "Configuração da plataforma",
    "environment": "Ambiente",
    "default": "Padrão da plataforma",
    "fixed": "Regra do portal",
    "runtime": "Runtime",
}
_SETTING_STATUS_TONE = {
    "positive": "positive",
    "neutral": "neutral",
    "warning": "warning",
    "critical": "critical",
}
_PLATFORM_SETTING_DEFINITIONS: dict[str, dict[str, Any]] = {
    "admin_reauth_max_age_minutes": {
        "category": "access",
        "type": "int",
        "scope_label": "Somente Admin-CEO",
        "min": 1,
        "max": 120,
        "impact": "Define por quantos minutos uma reautenticação TOTP libera ações críticas.",
    },
    "review_ui_canonical": {
        "category": "rollout",
        "type": "enum",
        "scope_label": "Revisão e Mesa",
        "allowed": ("ssr",),
        "impact": "Mantém a revisão no painel SSR legado para preservar um único fluxo operacional.",
    },
    "support_exceptional_mode": {
        "category": "support",
        "type": "enum",
        "scope_label": "Todos os tenants",
        "allowed": tuple(_SUPPORT_EXCEPTIONAL_MODE_LABELS.keys()),
        "impact": "Governa se o suporte excepcional pode ser aberto e em que regime operacional.",
    },
    "support_exceptional_approval_required": {
        "category": "support",
        "type": "bool",
        "scope_label": "Todos os tenants",
        "impact": "Exige aprovação formal antes de qualquer suporte excepcional autorizado.",
    },
    "support_exceptional_justification_required": {
        "category": "support",
        "type": "bool",
        "scope_label": "Todos os tenants",
        "impact": "Exige justificativa auditável para toda abertura de suporte excepcional.",
    },
    "support_exceptional_max_duration_minutes": {
        "category": "support",
        "type": "int",
        "scope_label": "Todos os tenants",
        "min": 15,
        "max": 1440,
        "impact": "Limita a janela máxima, em minutos, para suporte excepcional ativo.",
    },
    "support_exceptional_scope_level": {
        "category": "support",
        "type": "enum",
        "scope_label": "Todos os tenants",
        "allowed": tuple(_SUPPORT_EXCEPTIONAL_SCOPE_LABELS.keys()),
        "impact": "Delimita o maior escopo operacional permitido em modo excepcional.",
    },
    "default_new_tenant_plan": {
        "category": "defaults",
        "type": "enum",
        "scope_label": "Novos tenants",
        "allowed": tuple(PlanoEmpresa.valores()),
        "impact": "Define o plano selecionado por padrão no onboarding de novas empresas.",
    },
}


def _normalize_optional_text_platform_settings(
    value: Any,
    max_len: int | None = None,
) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:max_len] if max_len is not None else text


def _normalize_datetime_platform_settings(value: datetime | None) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_datetime_platform_settings(
    value: datetime | None,
    *,
    fallback: str = "Sem atividade",
) -> str:
    normalized = _normalize_datetime_platform_settings(value)
    if normalized is None:
        return fallback
    return normalized.strftime("%d/%m/%Y %H:%M UTC")


def _now_utc_platform_settings() -> datetime:
    return datetime.now(timezone.utc)


def _platform_setting_source_label(source: str) -> str:
    return _SETTING_SOURCE_LABELS.get(str(source or "").strip().lower(), "Fonte desconhecida")


def _normalize_review_ui_surface(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"ssr", "legacy"}:
        return "ssr"
    raise ValueError("Escolha uma UI canônica válida para a revisão.")


def _platform_setting_default(key: str) -> tuple[Any, str]:
    if key == "admin_reauth_max_age_minutes":
        source = "environment" if env_str("ADMIN_REAUTH_MAX_AGE_MINUTES", "") else "default"
        return max(env_int("ADMIN_REAUTH_MAX_AGE_MINUTES", 10), 1), source
    if key == "review_ui_canonical":
        env_canonical = _normalize_optional_text_platform_settings(
            env_str(_REVIEW_UI_CANONICAL_ENV, ""),
            max_len=20,
        )
        env_primary = _normalize_optional_text_platform_settings(
            env_str(_REVIEW_UI_PRIMARY_SURFACE_ENV, ""),
            max_len=20,
        )
        if env_canonical:
            try:
                if _normalize_review_ui_surface(env_canonical) != "ssr":
                    logger.warning(
                        "REVIEW_UI_CANONICAL fora do fluxo SSR oficial. Normalizando para 'ssr'."
                    )
            except ValueError:
                logger.warning(
                    "REVIEW_UI_CANONICAL inválido no ambiente. Ignorando valor %r.",
                    env_canonical,
                )
        if env_primary:
            try:
                if _normalize_review_ui_surface(env_primary) != "ssr":
                    logger.warning(
                        "TARIEL_REVIEW_DESK_PRIMARY_SURFACE fora do fluxo SSR oficial. Normalizando para 'ssr'."
                    )
            except ValueError:
                logger.warning(
                    "TARIEL_REVIEW_DESK_PRIMARY_SURFACE inválido no ambiente. Ignorando valor %r.",
                    env_primary,
                )
        return "ssr", "default"
    if key == "support_exceptional_mode":
        return "approval_required", "default"
    if key == "support_exceptional_approval_required":
        return True, "default"
    if key == "support_exceptional_justification_required":
        return True, "default"
    if key == "support_exceptional_max_duration_minutes":
        return 120, "default"
    if key == "support_exceptional_scope_level":
        return "administrative", "default"
    if key == "default_new_tenant_plan":
        return PlanoEmpresa.INICIAL.value, "default"
    raise KeyError(f"Configuração de plataforma desconhecida: {key}")


def _coerce_platform_setting_value(key: str, value: Any) -> Any:
    definition = _PLATFORM_SETTING_DEFINITIONS[key]
    setting_type = definition["type"]
    if setting_type == "int":
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Informe um valor numérico válido.") from exc
        min_value = int(definition.get("min", normalized))
        max_value = int(definition.get("max", normalized))
        if normalized < min_value or normalized > max_value:
            raise ValueError(f"Informe um valor entre {min_value} e {max_value}.")
        return normalized
    if setting_type == "bool":
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "on", "sim", "yes"}
    if setting_type == "enum":
        if key == "default_new_tenant_plan":
            normalized_enum = PlanoEmpresa.normalizar(value)
        elif key == "review_ui_canonical":
            normalized_enum = _normalize_review_ui_surface(value)
        else:
            normalized_enum = str(value or "").strip().lower()
        allowed = tuple(definition.get("allowed") or ())
        if normalized_enum not in allowed:
            raise ValueError("Selecione uma opção válida.")
        return normalized_enum
    raise ValueError("Tipo de configuração não suportado.")


def _platform_setting_row_map(banco: Session) -> dict[str, ConfiguracaoPlataforma]:
    return {
        row.chave: row
        for row in banco.scalars(select(ConfiguracaoPlataforma)).all()
    }


def _platform_setting_snapshot(
    banco: Session,
    key: str,
    *,
    rows: dict[str, ConfiguracaoPlataforma] | None = None,
    users: dict[int, Usuario] | None = None,
) -> dict[str, Any]:
    if key not in _PLATFORM_SETTING_DEFINITIONS:
        raise KeyError(f"Configuração de plataforma desconhecida: {key}")

    row_map = rows or _platform_setting_row_map(banco)
    row = row_map.get(key)
    if row is not None:
        try:
            value = _coerce_platform_setting_value(key, row.valor_json)
            source = "database"
        except ValueError:
            value, source = _platform_setting_default(key)
            logger.warning(
                "Configuracao persistida invalida para %s. Reaplicando padrao operacional %r.",
                key,
                value,
            )
    else:
        value, source = _platform_setting_default(key)

    actor_label = "Sistema"
    if row is not None and row.atualizada_por_usuario_id and users is not None:
        actor = users.get(int(row.atualizada_por_usuario_id))
        if actor is not None:
            actor_label = (
                getattr(actor, "nome_completo", None)
                or getattr(actor, "email", None)
                or f"Usuário #{actor.id}"
            )

    changed_at = (
        _normalize_datetime_platform_settings(
            getattr(row, "atualizado_em", None) or getattr(row, "criado_em", None)
        )
        if row is not None
        else None
    )
    return {
        "key": key,
        "value": value,
        "source": source,
        "source_label": _platform_setting_source_label(source),
        "last_changed_at": changed_at,
        "last_changed_at_label": (
            changed_at.strftime("%d/%m/%Y %H:%M UTC")
            if changed_at
            else "Sem customização"
        ),
        "last_changed_by_label": actor_label if row is not None else "Padrão da plataforma",
        "reason": str(getattr(row, "motivo_ultima_alteracao", "") or "").strip(),
    }


def get_platform_setting_value(banco: Session, key: str) -> Any:
    return _platform_setting_snapshot(banco, key)["value"]


def get_platform_default_new_tenant_plan(banco: Session) -> str:
    return str(get_platform_setting_value(banco, "default_new_tenant_plan"))


def get_support_exceptional_policy_snapshot(banco: Session) -> dict[str, Any]:
    mode = str(get_platform_setting_value(banco, "support_exceptional_mode") or "approval_required")
    approval_required = bool(
        get_platform_setting_value(banco, "support_exceptional_approval_required")
    )
    justification_required = bool(
        get_platform_setting_value(banco, "support_exceptional_justification_required")
    )
    max_duration_minutes = int(
        get_platform_setting_value(banco, "support_exceptional_max_duration_minutes") or 120
    )
    scope_level = str(
        get_platform_setting_value(banco, "support_exceptional_scope_level") or "administrative"
    )
    return {
        "mode": mode,
        "mode_label": _SUPPORT_EXCEPTIONAL_MODE_LABELS.get(mode, "Política desconhecida"),
        "approval_required": approval_required,
        "justification_required": justification_required,
        "max_duration_minutes": max_duration_minutes,
        "scope_level": scope_level,
        "scope_level_label": _SUPPORT_EXCEPTIONAL_SCOPE_LABELS.get(
            scope_level,
            "Escopo desconhecido",
        ),
        "step_up_required": True,
        "can_open": mode != "disabled",
    }


def get_tenant_exceptional_support_state(
    banco: Session,
    *,
    empresa_id: int,
) -> dict[str, Any]:
    policy = get_support_exceptional_policy_snapshot(banco)
    registros = list(
        banco.scalars(
            select(RegistroAuditoriaEmpresa)
            .where(
                RegistroAuditoriaEmpresa.empresa_id == int(empresa_id),
                RegistroAuditoriaEmpresa.portal == "admin",
                RegistroAuditoriaEmpresa.acao.in_(
                    ("tenant_exceptional_support_opened", "tenant_exceptional_support_closed")
                ),
            )
            .order_by(RegistroAuditoriaEmpresa.id.asc())
        ).all()
    )

    abertura_ativa: RegistroAuditoriaEmpresa | None = None
    payload_abertura: dict[str, Any] = {}
    fechamento_recente: RegistroAuditoriaEmpresa | None = None

    for registro in registros:
        acao = str(getattr(registro, "acao", "") or "")
        payload = (
            registro.payload_json
            if isinstance(getattr(registro, "payload_json", None), dict)
            else {}
        )
        if acao == "tenant_exceptional_support_opened":
            abertura_ativa = registro
            payload_abertura = payload
            fechamento_recente = None
            continue
        if acao != "tenant_exceptional_support_closed" or abertura_ativa is None:
            continue
        opened_record_id = payload.get("opened_record_id")
        if opened_record_id is None or int(opened_record_id) == int(abertura_ativa.id):
            fechamento_recente = registro
            abertura_ativa = None
            payload_abertura = {}

    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return _normalize_datetime_platform_settings(value)
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return _normalize_datetime_platform_settings(
                datetime.fromisoformat(text.replace("Z", "+00:00"))
            )
        except ValueError:
            return None

    opened_at = (
        _normalize_datetime_platform_settings(getattr(abertura_ativa, "criado_em", None))
        if abertura_ativa
        else None
    )
    expires_at = _parse_datetime(payload_abertura.get("expires_at")) if abertura_ativa else None
    if opened_at is not None and expires_at is None:
        duration_minutes = int(
            payload_abertura.get("max_duration_minutes") or policy["max_duration_minutes"]
        )
        expires_at = opened_at + timedelta(minutes=max(1, duration_minutes))

    active = bool(
        abertura_ativa is not None
        and expires_at is not None
        and _now_utc_platform_settings() <= expires_at
    )
    expired = bool(
        abertura_ativa is not None
        and expires_at is not None
        and _now_utc_platform_settings() > expires_at
    )

    actor = getattr(abertura_ativa, "ator_usuario", None) if abertura_ativa else None
    actor_label = (
        getattr(actor, "nome_completo", None)
        or getattr(actor, "email", None)
        or (
            f"Usuário #{int(abertura_ativa.ator_usuario_id)}"
            if abertura_ativa and abertura_ativa.ator_usuario_id
            else ""
        )
    )

    if active:
        status = "active"
        status_label = "Suporte excepcional ativo"
    elif expired:
        status = "expired"
        status_label = "Janela excepcional expirada"
    elif not policy["can_open"]:
        status = "disabled"
        status_label = "Suporte excepcional desabilitado"
    else:
        status = "available"
        status_label = "Suporte excepcional disponível sob governança"

    return {
        "policy": policy,
        "active": active,
        "expired": expired,
        "status": status,
        "status_label": status_label,
        "opened_record_id": int(abertura_ativa.id) if abertura_ativa else None,
        "opened_at": opened_at,
        "opened_at_label": _format_datetime_platform_settings(
            opened_at,
            fallback="Nunca aberto",
        ),
        "expires_at": expires_at,
        "expires_at_label": _format_datetime_platform_settings(
            expires_at,
            fallback="Sem janela definida",
        ),
        "opened_by_label": actor_label or "Não aplicável",
        "approval_reference": str(payload_abertura.get("approval_reference") or "").strip(),
        "justification": str(payload_abertura.get("justification") or "").strip(),
        "scope_level": str(
            payload_abertura.get("scope_level")
            or policy["scope_level"]
        ),
        "scope_level_label": _SUPPORT_EXCEPTIONAL_SCOPE_LABELS.get(
            str(payload_abertura.get("scope_level") or policy["scope_level"]),
            "Escopo desconhecido",
        ),
        "last_closed_at": _normalize_datetime_platform_settings(
            getattr(fechamento_recente, "criado_em", None)
        ),
        "last_closed_at_label": _format_datetime_platform_settings(
            getattr(fechamento_recente, "criado_em", None),
            fallback="Sem encerramento registrado",
        ),
    }


def _setting_value_label(key: str, value: Any) -> str:
    if key == "admin_reauth_max_age_minutes":
        return f"{int(value)} min"
    if key == "review_ui_canonical":
        return _REVIEW_UI_LABELS.get(str(value), str(value))
    if key == "support_exceptional_mode":
        return _SUPPORT_EXCEPTIONAL_MODE_LABELS.get(str(value), str(value))
    if key == "support_exceptional_scope_level":
        return _SUPPORT_EXCEPTIONAL_SCOPE_LABELS.get(str(value), str(value))
    if key == "support_exceptional_max_duration_minutes":
        return f"{int(value)} min"
    if key == "default_new_tenant_plan":
        return PlanoEmpresa.normalizar(value)
    if isinstance(value, bool):
        return "Habilitado" if value else "Desabilitado"
    return str(value)


def _setting_status_tone_for_value(key: str, value: Any) -> str:
    if key in {
        "support_exceptional_mode",
        "support_exceptional_scope_level",
        "support_exceptional_approval_required",
        "support_exceptional_justification_required",
    }:
        if key == "support_exceptional_mode":
            if value == "disabled":
                return _SETTING_STATUS_TONE["neutral"]
            if value == "incident_controlled":
                return _SETTING_STATUS_TONE["warning"]
            return _SETTING_STATUS_TONE["positive"]
        if isinstance(value, bool):
            return (
                _SETTING_STATUS_TONE["positive"]
                if value
                else _SETTING_STATUS_TONE["warning"]
            )
        if value == "tenant_diagnostic":
            return _SETTING_STATUS_TONE["warning"]
    if isinstance(value, bool):
        return _SETTING_STATUS_TONE["positive"] if value else _SETTING_STATUS_TONE["neutral"]
    return _SETTING_STATUS_TONE["neutral"]


def _build_setting_item(
    banco: Session,
    key: str,
    *,
    title: str,
    description: str,
    rows: dict[str, ConfiguracaoPlataforma],
    users: dict[int, Usuario],
    technical_path: str | None = None,
) -> dict[str, Any]:
    snapshot = _platform_setting_snapshot(banco, key, rows=rows, users=users)
    definition = _PLATFORM_SETTING_DEFINITIONS[key]
    value = snapshot["value"]
    return {
        "key": key,
        "title": title,
        "description": description,
        "value_label": _setting_value_label(key, value),
        "value_raw": value,
        "source_label": snapshot["source_label"],
        "scope_label": str(definition["scope_label"]),
        "status_tone": _setting_status_tone_for_value(key, value),
        "last_changed_label": snapshot["last_changed_at_label"],
        "last_changed_by_label": snapshot["last_changed_by_label"],
        "reason": snapshot["reason"],
        "impact": str(definition.get("impact") or ""),
        "technical_path": technical_path,
    }


def _build_runtime_item(
    *,
    title: str,
    description: str,
    value_label: str,
    status_tone: str,
    source_label: str,
    scope_label: str,
    technical_path: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    return {
        "title": title,
        "description": description,
        "value_label": value_label,
        "source_label": source_label,
        "scope_label": scope_label,
        "status_tone": status_tone,
        "last_changed_label": "Gerenciado pela origem",
        "last_changed_by_label": source_label,
        "reason": reason,
        "impact": "",
        "technical_path": technical_path,
    }


def _build_runtime_items(descriptors: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _build_runtime_item(
            title=str(item.get("title") or "").strip(),
            description=str(item.get("description") or "").strip(),
            value_label=str(item.get("value_label") or "").strip(),
            status_tone=_SETTING_STATUS_TONE[
                str(item.get("status_tone_key") or "neutral").strip() or "neutral"
            ],
            source_label=_platform_setting_source_label(
                str(item.get("source_kind") or "runtime").strip() or "runtime"
            ),
            scope_label=str(item.get("scope_label") or "").strip(),
            technical_path=str(item.get("technical_path") or "").strip() or None,
            reason=str(item.get("reason") or "").strip(),
        )
        for item in descriptors
    ]


def _build_setting_items(
    banco: Session,
    rows: dict[str, ConfiguracaoPlataforma],
    users: dict[int, Usuario],
    descriptors: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        _build_setting_item(
            banco,
            str(item["key"]),
            title=str(item["title"]),
            description=str(item["description"]),
            rows=rows,
            users=users,
            technical_path=str(item.get("technical_path") or "").strip() or None,
        )
        for item in descriptors
    ]


def _platform_settings_users(
    rows: dict[str, ConfiguracaoPlataforma],
    banco: Session,
) -> dict[int, Usuario]:
    user_ids = {
        int(row.atualizada_por_usuario_id)
        for row in rows.values()
        if row.atualizada_por_usuario_id is not None
    }
    if not user_ids:
        return {}
    return {
        int(user.id): user
        for user in banco.scalars(select(Usuario).where(Usuario.id.in_(user_ids))).all()
    }


__all__ = [
    "_PLATFORM_SETTING_DEFINITIONS",
    "_SUPPORT_EXCEPTIONAL_MODE_LABELS",
    "_SUPPORT_EXCEPTIONAL_SCOPE_LABELS",
    "_build_runtime_items",
    "_build_setting_items",
    "_coerce_platform_setting_value",
    "_platform_setting_row_map",
    "_platform_setting_snapshot",
    "_platform_settings_users",
    "_setting_value_label",
    "get_platform_default_new_tenant_plan",
    "get_platform_setting_value",
    "get_support_exceptional_policy_snapshot",
    "get_tenant_exceptional_support_state",
]
