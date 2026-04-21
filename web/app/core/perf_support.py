"""Observabilidade dev-only para a Fase 01 de reestruturação."""

from __future__ import annotations

import re
import threading
import time
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Iterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core.observability_privacy import sanitize_observability_value
from app.core.settings import get_settings
from app.core.telemetry_support import start_operation_trace

_REQUESTS: deque[dict[str, Any]] = deque()
_SQL_QUERIES: deque[dict[str, Any]] = deque()
_OPERATIONS: deque[dict[str, Any]] = deque()
_BOOT_EVENTS: deque[dict[str, Any]] = deque()
_STORE_LOCK = threading.RLock()
_REQUEST_STATE_CTX: ContextVar["_RequestPerfState | None"] = ContextVar("tariel_request_perf_state", default=None)
_SQL_SPACE_RE = re.compile(r"\s+")
_EXTERNAL_CATEGORIES = frozenset({"external", "ai", "ocr", "integration"})
_RENDER_CATEGORIES = frozenset({"pdf", "template", "render", "ssr"})


@dataclass(slots=True)
class _RequestPerfState:
    request_id: str
    correlation_id: str
    method: str
    path: str
    route_group: str
    started_at: float
    started_epoch_ms: int
    sql_count: int = 0
    sql_total_ms: float = 0.0
    slow_sql_count: int = 0
    slow_sql_ms: float = 0.0
    external_count: int = 0
    external_total_ms: float = 0.0
    render_count: int = 0
    render_total_ms: float = 0.0
    sql_samples: list[dict[str, Any]] = field(default_factory=list)
    operation_samples: list[dict[str, Any]] = field(default_factory=list)


def _settings():
    return get_settings()


def backend_perf_habilitado() -> bool:
    settings = _settings()
    return bool(settings.perf_mode and not settings.em_producao)


def frontend_perf_habilitado() -> bool:
    return backend_perf_habilitado()


def contexto_template_perf() -> dict[str, Any]:
    ativo = frontend_perf_habilitado()
    return {
        "perf_mode": ativo,
        "perf_summary_url": "/debug-perf/summary" if ativo else "",
        "perf_report_url": "/debug-perf/report" if ativo else "",
        "perf_reset_url": "/debug-perf/reset" if ativo else "",
    }


def _truncate(valor: Any, limite: int = 260) -> str:
    texto = str(valor or "").strip()
    if len(texto) <= limite:
        return texto
    return f"{texto[: max(limite - 3, 0)]}..."


def _safe_json_like(valor: Any, *, profundidade: int = 0) -> Any:
    if profundidade >= 3:
        return sanitize_observability_value(_truncate(valor, 180))

    if valor is None or isinstance(valor, (str, int, float, bool)):
        return sanitize_observability_value(valor)

    if isinstance(valor, dict):
        return {
            str(chave): _safe_json_like(item, profundidade=profundidade + 1)
            for chave, item in list(valor.items())[:20]
        }

    if isinstance(valor, (list, tuple, set)):
        return [_safe_json_like(item, profundidade=profundidade + 1) for item in list(valor)[:20]]

    if hasattr(valor, "filename") or hasattr(valor, "content_type"):
        return {
            "__type__": valor.__class__.__name__,
            "filename": getattr(valor, "filename", None),
            "content_type": getattr(valor, "content_type", None),
        }

    return sanitize_observability_value(_truncate(valor, 180))


def _append_buffer(buffer: deque[dict[str, Any]], item: dict[str, Any], *, limite: int) -> None:
    with _STORE_LOCK:
        buffer.append(item)
        while len(buffer) > limite:
            buffer.popleft()


def _path_group(path: str) -> str:
    if path.startswith("/app/api/"):
        return "app_api"
    if path.startswith("/cliente/api/"):
        return "cliente_api"
    if path.startswith("/revisao/api/"):
        return "revisao_api"
    if path.startswith("/admin/api/"):
        return "admin_api"
    if path.startswith("/app"):
        return "app_html"
    if path.startswith("/cliente"):
        return "cliente_html"
    if path.startswith("/revisao"):
        return "revisao_html"
    if path.startswith("/admin"):
        return "admin_html"
    return "infra"


def _ignorar_path(path: str) -> bool:
    return path.startswith("/static/") or path.startswith("/debug-perf/")


def _normalizar_sql(statement: Any) -> str:
    texto = _SQL_SPACE_RE.sub(" ", str(statement or "")).strip()
    return str(sanitize_observability_value(_truncate(texto or "<sql-vazio>", 320)))


def _limite_requests() -> int:
    return int(_settings().perf_buffer_limit)


def _limite_sql() -> int:
    return int(_settings().perf_buffer_limit) * 8


def _limite_operacoes() -> int:
    return int(_settings().perf_buffer_limit) * 6


def _limite_boot() -> int:
    return 40


def _sql_lento_ms() -> int:
    return int(_settings().perf_sql_slow_ms)


def _route_lenta_ms() -> int:
    return int(_settings().perf_route_slow_ms)


def _external_lento_ms() -> int:
    return int(_settings().perf_external_slow_ms)


def iniciar_request_perf(
    *,
    request_id: str,
    correlation_id: str,
    method: str,
    path: str,
) -> Token[_RequestPerfState | None] | None:
    if not backend_perf_habilitado() or _ignorar_path(path):
        return None

    estado = _RequestPerfState(
        request_id=request_id,
        correlation_id=correlation_id,
        method=str(method or "GET").upper(),
        path=str(path or "/"),
        route_group=_path_group(str(path or "/")),
        started_at=time.perf_counter(),
        started_epoch_ms=int(time.time() * 1000),
    )
    return _REQUEST_STATE_CTX.set(estado)


def request_perf_atual() -> _RequestPerfState | None:
    return _REQUEST_STATE_CTX.get()


def registrar_query_sql(statement: Any, *, duration_ms: float, rowcount: int | None = None) -> None:
    if not backend_perf_habilitado():
        return

    duracao = round(max(float(duration_ms or 0.0), 0.0), 3)
    estado = request_perf_atual()
    lenta = duracao >= _sql_lento_ms()
    payload = {
        "request_id": estado.request_id if estado else None,
        "path": estado.path if estado else "",
        "method": estado.method if estado else "",
        "route_group": estado.route_group if estado else "background",
        "duration_ms": duracao,
        "slow": lenta,
        "rowcount": rowcount,
        "statement": _normalizar_sql(statement),
        "captured_at": int(time.time() * 1000),
    }

    if estado:
        estado.sql_count += 1
        estado.sql_total_ms += duracao
        if lenta:
            estado.slow_sql_count += 1
            estado.slow_sql_ms += duracao
        if lenta or len(estado.sql_samples) < 6:
            estado.sql_samples.append(
                {
                    "duration_ms": duracao,
                    "slow": lenta,
                    "rowcount": rowcount,
                    "statement": payload["statement"],
                }
            )

    _append_buffer(_SQL_QUERIES, payload, limite=_limite_sql())


def registrar_operacao(
    categoria: str,
    nome: str,
    *,
    duration_ms: float,
    detail: dict[str, Any] | None = None,
) -> None:
    if not backend_perf_habilitado():
        return

    duracao = round(max(float(duration_ms or 0.0), 0.0), 3)
    categoria_limpa = str(categoria or "function").strip().lower() or "function"
    nome_limpo = str(nome or "operacao").strip() or "operacao"
    estado = request_perf_atual()
    payload = {
        "category": categoria_limpa,
        "name": nome_limpo,
        "request_id": estado.request_id if estado else None,
        "path": estado.path if estado else "",
        "method": estado.method if estado else "",
        "route_group": estado.route_group if estado else "background",
        "duration_ms": duracao,
        "slow": duracao >= (_external_lento_ms() if categoria_limpa in _EXTERNAL_CATEGORIES else _route_lenta_ms()),
        "detail": _safe_json_like(detail or {}),
        "captured_at": int(time.time() * 1000),
    }

    if estado:
        if categoria_limpa in _EXTERNAL_CATEGORIES:
            estado.external_count += 1
            estado.external_total_ms += duracao
        if categoria_limpa in _RENDER_CATEGORIES:
            estado.render_count += 1
            estado.render_total_ms += duracao
        if len(estado.operation_samples) < 8 or payload["slow"]:
            estado.operation_samples.append(
                {
                    "category": categoria_limpa,
                    "name": nome_limpo,
                    "duration_ms": duracao,
                    "slow": payload["slow"],
                    "detail": payload["detail"],
                }
            )

    _append_buffer(_OPERATIONS, payload, limite=_limite_operacoes())
    if categoria_limpa == "boot":
        _append_buffer(_BOOT_EVENTS, payload, limite=_limite_boot())


@contextmanager
def medir_operacao(categoria: str, nome: str, *, detail: dict[str, Any] | None = None) -> Iterator[None]:
    with start_operation_trace(categoria, nome, detail=detail):
        if not backend_perf_habilitado():
            yield
            return

        inicio = time.perf_counter()
        detalhe = dict(detail or {})
        try:
            yield
        except Exception as exc:
            detalhe["failed"] = True
            detalhe["error"] = _truncate(getattr(exc, "message", None) or str(exc), 200)
            raise
        finally:
            registrar_operacao(
                categoria,
                nome,
                duration_ms=(time.perf_counter() - inicio) * 1000,
                detail=detalhe,
            )


@asynccontextmanager
async def medir_operacao_async(categoria: str, nome: str, *, detail: dict[str, Any] | None = None):
    with start_operation_trace(categoria, nome, detail=detail):
        if not backend_perf_habilitado():
            yield
            return

        inicio = time.perf_counter()
        detalhe = dict(detail or {})
        try:
            yield
        except Exception as exc:
            detalhe["failed"] = True
            detalhe["error"] = _truncate(getattr(exc, "message", None) or str(exc), 200)
            raise
        finally:
            registrar_operacao(
                categoria,
                nome,
                duration_ms=(time.perf_counter() - inicio) * 1000,
                detail=detalhe,
            )


def encerrar_request_perf(
    token: Token[_RequestPerfState | None] | None,
    *,
    status_code: int,
    content_type: str = "",
    detail: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    estado = request_perf_atual()
    if token is None or estado is None:
        return None

    try:
        _REQUEST_STATE_CTX.reset(token)
    except Exception:
        _REQUEST_STATE_CTX.set(None)

    if _ignorar_path(estado.path):
        return None

    duracao = round((time.perf_counter() - estado.started_at) * 1000, 3)
    content_type_limpo = str(content_type or "")
    eh_html = "text/html" in content_type_limpo.lower()
    render_total_ms = round(estado.render_total_ms or (duracao if eh_html else 0.0), 3)
    payload = {
        "request_id": estado.request_id,
        "correlation_id": estado.correlation_id,
        "method": estado.method,
        "path": estado.path,
        "route_group": estado.route_group,
        "status_code": int(status_code),
        "duration_ms": duracao,
        "slow": duracao >= _route_lenta_ms(),
        "content_type": content_type_limpo,
        "is_html": eh_html,
        "is_stream": "text/event-stream" in content_type_limpo.lower(),
        "started_epoch_ms": estado.started_epoch_ms,
        "sql_count": estado.sql_count,
        "sql_total_ms": round(estado.sql_total_ms, 3),
        "slow_sql_count": estado.slow_sql_count,
        "slow_sql_ms": round(estado.slow_sql_ms, 3),
        "external_count": estado.external_count,
        "external_total_ms": round(estado.external_total_ms, 3),
        "render_count": estado.render_count,
        "render_total_ms": render_total_ms,
        "sql_samples": list(estado.sql_samples),
        "operation_samples": list(estado.operation_samples),
        "detail": _safe_json_like(detail or {}),
    }
    _append_buffer(_REQUESTS, payload, limite=_limite_requests())
    return payload


def construir_server_timing(metric: dict[str, Any] | None) -> str:
    if not metric:
        return ""

    partes = [f"app;dur={float(metric.get('duration_ms') or 0.0):.1f}"]
    sql_count = int(metric.get("sql_count") or 0)
    if sql_count > 0:
        partes.append(f"sql;dur={float(metric.get('sql_total_ms') or 0.0):.1f};desc=\"queries={sql_count}\"")
    external_count = int(metric.get("external_count") or 0)
    if external_count > 0:
        partes.append(f"ext;dur={float(metric.get('external_total_ms') or 0.0):.1f};desc=\"calls={external_count}\"")
    if metric.get("is_html"):
        partes.append(f"ssr;dur={float(metric.get('render_total_ms') or 0.0):.1f}")
    return ", ".join(partes)


def resetar_perf() -> None:
    with _STORE_LOCK:
        _REQUESTS.clear()
        _SQL_QUERIES.clear()
        _OPERATIONS.clear()
        _BOOT_EVENTS.clear()


def _copiar_buffer(buffer: deque[dict[str, Any]]) -> list[dict[str, Any]]:
    with _STORE_LOCK:
        return [dict(item) for item in buffer]


def _agrupar_top(
    registros: list[dict[str, Any]],
    *,
    campos: tuple[str, ...],
    limite: int = 10,
) -> list[dict[str, Any]]:
    grupos: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in registros:
        chave = tuple(item.get(campo) for campo in campos)
        agregado = grupos.get(chave)
        if agregado is None:
            agregado = {campo: item.get(campo) for campo in campos}
            agregado.update(
                {
                    "count": 0,
                    "total_ms": 0.0,
                    "max_ms": 0.0,
                    "avg_ms": 0.0,
                    "slow_count": 0,
                }
            )
            grupos[chave] = agregado

        duracao = float(item.get("duration_ms") or 0.0)
        agregado["count"] += 1
        agregado["total_ms"] += duracao
        agregado["max_ms"] = max(float(agregado["max_ms"]), duracao)
        agregado["slow_count"] += 1 if item.get("slow") else 0

    saida = []
    for agregado in grupos.values():
        total = float(agregado["total_ms"])
        count = max(int(agregado["count"]), 1)
        agregado["total_ms"] = round(total, 3)
        agregado["max_ms"] = round(float(agregado["max_ms"]), 3)
        agregado["avg_ms"] = round(total / count, 3)
        saida.append(agregado)

    saida.sort(key=lambda item: (float(item["total_ms"]), float(item["max_ms"])), reverse=True)
    return saida[:limite]


def resumo_perf() -> dict[str, Any]:
    enabled = backend_perf_habilitado()
    requests = _copiar_buffer(_REQUESTS)
    queries = _copiar_buffer(_SQL_QUERIES)
    operations = _copiar_buffer(_OPERATIONS)
    boot = _copiar_buffer(_BOOT_EVENTS)

    routes_top = _agrupar_top(requests, campos=("method", "path", "route_group"), limite=10)
    shells_top = _agrupar_top(
        [item for item in requests if item.get("is_html") and str(item.get("method")) == "GET"],
        campos=("method", "path", "route_group"),
        limite=10,
    )
    sql_top = _agrupar_top(queries, campos=("statement",), limite=10)
    integrations_top = _agrupar_top(
        [item for item in operations if str(item.get("category")) in _EXTERNAL_CATEGORIES],
        campos=("category", "name"),
        limite=10,
    )
    render_top = _agrupar_top(
        [item for item in operations if str(item.get("category")) in _RENDER_CATEGORIES],
        campos=("category", "name"),
        limite=10,
    )

    slow_requests = sorted(requests, key=lambda item: float(item.get("duration_ms") or 0.0), reverse=True)[:10]
    slow_queries = sorted(queries, key=lambda item: float(item.get("duration_ms") or 0.0), reverse=True)[:10]

    return {
        "enabled": enabled,
        "config": {
            "perf_mode": enabled,
            "buffer_limit": _limite_requests(),
            "sql_buffer_limit": _limite_sql(),
            "operation_buffer_limit": _limite_operacoes(),
            "sql_slow_ms": _sql_lento_ms(),
            "route_slow_ms": _route_lenta_ms(),
            "external_slow_ms": _external_lento_ms(),
        },
        "counts": {
            "requests": len(requests),
            "queries": len(queries),
            "operations": len(operations),
            "boot_events": len(boot),
        },
        "top_routes": routes_top,
        "top_shells": shells_top,
        "top_queries": sql_top,
        "top_integrations": integrations_top,
        "top_render_ops": render_top,
        "slow_requests": slow_requests,
        "slow_queries": slow_queries,
        "recent_boot": boot[-10:],
    }


def relatorio_perf() -> dict[str, Any]:
    resumo = resumo_perf()
    resumo.update(
        {
            "requests": _copiar_buffer(_REQUESTS),
            "queries": _copiar_buffer(_SQL_QUERIES),
            "operations": _copiar_buffer(_OPERATIONS),
            "boot_events": _copiar_buffer(_BOOT_EVENTS),
        }
    )
    return resumo


def registrar_rotas_perf(app: FastAPI) -> None:
    settings = _settings()
    if settings.em_producao or not settings.perf_mode:
        return

    @app.get("/debug-perf/summary", include_in_schema=False)
    async def debug_perf_summary() -> JSONResponse:
        return JSONResponse(resumo_perf())

    @app.get("/debug-perf/report", include_in_schema=False)
    async def debug_perf_report() -> JSONResponse:
        return JSONResponse(relatorio_perf())

    @app.post("/debug-perf/reset", include_in_schema=False)
    async def debug_perf_reset() -> JSONResponse:
        resetar_perf()
        return JSONResponse({"ok": True, "detail": "Buffers de performance resetados."})


def registrar_instrumentacao_sql(engine: Engine) -> None:
    if not backend_perf_habilitado():
        return

    if getattr(engine, "_tariel_perf_sql_registered", False):
        return

    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        del conn, cursor, statement, parameters, executemany
        context._tariel_perf_started_at = time.perf_counter()  # noqa: SLF001

    @event.listens_for(engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        del conn, parameters, executemany
        inicio = getattr(context, "_tariel_perf_started_at", None)  # noqa: SLF001
        if inicio is None:
            return
        try:
            rowcount = int(cursor.rowcount) if cursor and cursor.rowcount is not None else None
        except Exception:
            rowcount = None
        registrar_query_sql(statement, duration_ms=(time.perf_counter() - float(inicio)) * 1000, rowcount=rowcount)

    setattr(engine, "_tariel_perf_sql_registered", True)


__all__ = [
    "backend_perf_habilitado",
    "frontend_perf_habilitado",
    "contexto_template_perf",
    "iniciar_request_perf",
    "encerrar_request_perf",
    "request_perf_atual",
    "registrar_query_sql",
    "registrar_operacao",
    "medir_operacao",
    "medir_operacao_async",
    "construir_server_timing",
    "resumo_perf",
    "relatorio_perf",
    "resetar_perf",
    "registrar_rotas_perf",
    "registrar_instrumentacao_sql",
]
