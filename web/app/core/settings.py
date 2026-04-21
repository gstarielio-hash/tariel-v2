"""Configuração central da aplicação (fonte única de ambiente)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


AMBIENTES_DEV = {"dev", "development", "local"}
AMBIENTES_PROD = {"producao", "production", "prod"}


def env_str(nome: str, padrao: str = "") -> str:
    return os.getenv(nome, padrao).strip()


def env_int(nome: str, padrao: int) -> int:
    bruto = env_str(nome, str(padrao))
    try:
        return int(bruto)
    except (TypeError, ValueError):
        return padrao


def env_float(nome: str, padrao: float) -> float:
    bruto = env_str(nome, str(padrao))
    try:
        return float(bruto)
    except (TypeError, ValueError):
        return padrao


def env_bool(nome: str, padrao: bool = False) -> bool:
    bruto = env_str(nome, "1" if padrao else "0").lower()
    return bruto in {"1", "true", "t", "sim", "yes", "y", "on"}


def env_log_level(nome: str, padrao: int) -> int:
    bruto = env_str(nome, "")
    if not bruto:
        return padrao

    texto = bruto.upper()
    valor = getattr(logging, texto, None)
    if isinstance(valor, int):
        return valor

    try:
        return int(bruto)
    except (TypeError, ValueError):
        return padrao


@dataclass(frozen=True, slots=True)
class Settings:
    ambiente: str
    em_producao: bool
    app_versao: str
    porta: int
    host_bind: str
    debug: bool
    redis_url: str
    revisor_realtime_backend: str
    revisor_realtime_fail_closed_on_startup: bool
    revisor_realtime_channel_prefix: str
    perf_mode: bool
    perf_buffer_limit: int
    perf_sql_slow_ms: int
    perf_route_slow_ms: int
    perf_external_slow_ms: int
    observability_header_name: str
    observability_client_request_header_name: str
    observability_trace_header_name: str
    observability_release: str
    otel_enabled: bool
    otel_service_name: str
    otel_service_namespace: str
    otel_exporter_mode: str
    otel_otlp_endpoint: str
    otel_export_timeout_ms: int
    sentry_dsn: str
    sentry_enabled: bool
    sentry_traces_sample_rate: float
    sentry_profiles_sample_rate: float
    sentry_send_default_pii: bool
    browser_analytics_enabled: bool
    browser_replay_enabled: bool
    mobile_analytics_opt_in_required: bool
    profile_uploads_path: str
    mesa_attachments_path: str
    visual_learning_uploads_path: str
    uploads_storage_mode: str
    uploads_profile_retention_days: int
    uploads_mesa_retention_days: int
    uploads_learning_retention_days: int
    uploads_cleanup_enabled: bool
    uploads_cleanup_grace_days: int
    uploads_cleanup_interval_hours: int
    uploads_cleanup_max_deletions_per_run: int
    uploads_backup_required: bool
    uploads_restore_drill_required: bool
    session_fail_closed_on_db_error: bool
    observability_log_retention_days: int
    observability_perf_retention_days: int
    observability_artifact_retention_days: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    ambiente = env_str("AMBIENTE", "").lower()
    if not ambiente:
        raise RuntimeError("AMBIENTE é obrigatório. Defina no .env (ex.: AMBIENTE=dev ou AMBIENTE=producao).")

    if ambiente not in (AMBIENTES_DEV | AMBIENTES_PROD):
        raise RuntimeError("AMBIENTE inválido. Use: dev, development, local, producao, production ou prod.")

    em_producao = ambiente in AMBIENTES_PROD
    revisor_realtime_backend = env_str("REVISOR_REALTIME_BACKEND", "memory").lower()
    if revisor_realtime_backend not in {"memory", "redis"}:
        raise RuntimeError("REVISOR_REALTIME_BACKEND inválido. Use: memory ou redis.")
    uploads_storage_mode = env_str(
        "TARIEL_UPLOADS_STORAGE_MODE",
        "persistent_disk" if em_producao else "local_fs",
    ).lower()
    if uploads_storage_mode not in {"local_fs", "persistent_disk", "custom"}:
        raise RuntimeError(
            "TARIEL_UPLOADS_STORAGE_MODE inválido. Use: local_fs, persistent_disk ou custom."
        )
    otel_exporter_mode = env_str("OTEL_EXPORTER_MODE", "console" if not em_producao else "none").lower()
    if otel_exporter_mode not in {"none", "console", "otlp"}:
        raise RuntimeError("OTEL_EXPORTER_MODE inválido. Use: none, console ou otlp.")
    sentry_dsn = env_str("SENTRY_DSN", "")

    return Settings(
        ambiente=ambiente,
        em_producao=em_producao,
        app_versao=env_str("APP_VERSAO", "2.0-SaaS"),
        porta=env_int("PORTA", 8000),
        host_bind=env_str("HOST_BIND", "0.0.0.0") or "0.0.0.0",
        debug=env_bool("DEBUG", not em_producao),
        redis_url=env_str("REDIS_URL", ""),
        revisor_realtime_backend=revisor_realtime_backend,
        revisor_realtime_fail_closed_on_startup=env_bool(
            "REVISOR_REALTIME_FAIL_CLOSED_ON_STARTUP",
            not em_producao,
        ),
        revisor_realtime_channel_prefix=env_str("REVISOR_REALTIME_CHANNEL_PREFIX", "tariel:revisor") or "tariel:revisor",
        perf_mode=env_bool("PERF_MODE", False),
        perf_buffer_limit=max(env_int("PERF_BUFFER_LIMIT", 300), 50),
        perf_sql_slow_ms=max(env_int("PERF_SQL_SLOW_MS", 80), 1),
        perf_route_slow_ms=max(env_int("PERF_ROUTE_SLOW_MS", 400), 1),
        perf_external_slow_ms=max(env_int("PERF_EXTERNAL_SLOW_MS", 250), 1),
        observability_header_name=env_str("OBSERVABILITY_HEADER_NAME", "X-Correlation-ID") or "X-Correlation-ID",
        observability_client_request_header_name=env_str(
            "OBSERVABILITY_CLIENT_REQUEST_HEADER_NAME",
            "X-Client-Request-Id",
        )
        or "X-Client-Request-Id",
        observability_trace_header_name=env_str("OBSERVABILITY_TRACE_HEADER_NAME", "X-Trace-Id") or "X-Trace-Id",
        observability_release=env_str("OBSERVABILITY_RELEASE", env_str("APP_VERSAO", "2.0-SaaS")) or "2.0-SaaS",
        otel_enabled=env_bool("OTEL_ENABLED", False),
        otel_service_name=env_str("OTEL_SERVICE_NAME", "tariel-web") or "tariel-web",
        otel_service_namespace=env_str("OTEL_SERVICE_NAMESPACE", "tariel") or "tariel",
        otel_exporter_mode=otel_exporter_mode,
        otel_otlp_endpoint=env_str("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
        otel_export_timeout_ms=max(env_int("OTEL_EXPORT_TIMEOUT_MS", 5000), 100),
        sentry_dsn=sentry_dsn,
        sentry_enabled=bool(sentry_dsn),
        sentry_traces_sample_rate=min(max(env_float("SENTRY_TRACES_SAMPLE_RATE", 0.0), 0.0), 1.0),
        sentry_profiles_sample_rate=min(max(env_float("SENTRY_PROFILES_SAMPLE_RATE", 0.0), 0.0), 1.0),
        sentry_send_default_pii=env_bool("SENTRY_SEND_DEFAULT_PII", False),
        browser_analytics_enabled=env_bool("TARIEL_BROWSER_ANALYTICS_ENABLED", False),
        browser_replay_enabled=env_bool("TARIEL_BROWSER_REPLAY_ENABLED", False),
        mobile_analytics_opt_in_required=env_bool("TARIEL_MOBILE_ANALYTICS_OPT_IN_REQUIRED", True),
        profile_uploads_path=env_str("PASTA_UPLOADS_PERFIS", "static/uploads/perfis")
        or "static/uploads/perfis",
        mesa_attachments_path=env_str("PASTA_ANEXOS_MESA", "") or "",
        visual_learning_uploads_path=env_str(
            "PASTA_APRENDIZADOS_VISUAIS_IA",
            "static/uploads/aprendizados_ia",
        )
        or "static/uploads/aprendizados_ia",
        uploads_storage_mode=uploads_storage_mode,
        uploads_profile_retention_days=max(
            env_int("TARIEL_UPLOADS_PROFILE_RETENTION_DAYS", 365),
            1,
        ),
        uploads_mesa_retention_days=max(
            env_int("TARIEL_UPLOADS_MESA_RETENTION_DAYS", 365),
            1,
        ),
        uploads_learning_retention_days=max(
            env_int("TARIEL_UPLOADS_LEARNING_RETENTION_DAYS", 365),
            1,
        ),
        uploads_cleanup_enabled=env_bool("TARIEL_UPLOADS_CLEANUP_ENABLED", False),
        uploads_cleanup_grace_days=max(
            env_int("TARIEL_UPLOADS_CLEANUP_GRACE_DAYS", 14),
            0,
        ),
        uploads_cleanup_interval_hours=max(
            env_int("TARIEL_UPLOADS_CLEANUP_INTERVAL_HOURS", 24),
            1,
        ),
        uploads_cleanup_max_deletions_per_run=max(
            env_int("TARIEL_UPLOADS_CLEANUP_MAX_DELETIONS_PER_RUN", 200),
            1,
        ),
        uploads_backup_required=env_bool(
            "TARIEL_UPLOADS_BACKUP_REQUIRED",
            em_producao,
        ),
        uploads_restore_drill_required=env_bool(
            "TARIEL_UPLOADS_RESTORE_DRILL_REQUIRED",
            em_producao,
        ),
        session_fail_closed_on_db_error=env_bool(
            "SESSAO_FAIL_CLOSED_ON_DB_ERROR",
            em_producao,
        ),
        observability_log_retention_days=max(env_int("OBSERVABILITY_LOG_RETENTION_DAYS", 14), 1),
        observability_perf_retention_days=max(env_int("OBSERVABILITY_PERF_RETENTION_DAYS", 7), 1),
        observability_artifact_retention_days=max(env_int("OBSERVABILITY_ARTIFACT_RETENTION_DAYS", 7), 1),
    )
