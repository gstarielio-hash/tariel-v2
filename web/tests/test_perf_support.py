from __future__ import annotations

import logging
import re

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.http_runtime_support import registrar_middlewares
from app.core.perf_support import (
    contexto_template_perf,
    registrar_instrumentacao_sql,
    registrar_rotas_perf,
    resetar_perf,
)
from app.core.settings import get_settings
from app.core.telemetry_support import trace
from app.shared.database import SessaoLocal, motor_banco


def _criar_app_perf(
    *,
    sessao_local=SessaoLocal,
    database_engine=motor_banco,
) -> FastAPI:
    registrar_instrumentacao_sql(database_engine)

    app = FastAPI()
    app.state.limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"])
    registrar_middlewares(
        app,
        logger=logging.getLogger("tests.perf"),
        em_producao=False,
        chave_secreta="dev-chave-fixa-perf-tests-1234567890",
        max_age_sessao=3600,
        nome_cookie_sessao="perf-tests",
        allowed_hosts=["*"],
        ws_origins=["ws://127.0.0.1:8000"],
    )
    registrar_rotas_perf(app)

    @app.get("/app/ping")
    async def app_ping() -> HTMLResponse:
        return HTMLResponse("<html><body>ok</body></html>")

    @app.get("/app/sql")
    async def app_sql() -> JSONResponse:
        with sessao_local() as banco:
            banco.execute(text("SELECT 1"))
        return JSONResponse({"ok": True})

    return app


def test_contexto_template_perf_reflete_modo_ativo(monkeypatch) -> None:
    monkeypatch.setenv("AMBIENTE", "dev")
    monkeypatch.setenv("PERF_MODE", "1")
    get_settings.cache_clear()

    try:
        contexto = contexto_template_perf()
    finally:
        get_settings.cache_clear()

    assert contexto["perf_mode"] is True
    assert contexto["perf_summary_url"] == "/debug-perf/summary"
    assert contexto["perf_report_url"] == "/debug-perf/report"


def test_perf_headers_e_summary_expoem_sql_por_request(monkeypatch) -> None:
    if trace is None:
        pytest.skip("OpenTelemetry indisponivel neste runtime.")

    monkeypatch.setenv("AMBIENTE", "dev")
    monkeypatch.setenv("PERF_MODE", "1")
    monkeypatch.setenv("PERF_BUFFER_LIMIT", "80")
    monkeypatch.setenv("PERF_SQL_SLOW_MS", "1")
    monkeypatch.setenv("OTEL_ENABLED", "1")
    monkeypatch.setenv("OTEL_EXPORTER_MODE", "none")
    get_settings.cache_clear()
    resetar_perf()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    try:
        app = _criar_app_perf(sessao_local=session_local, database_engine=engine)
        with TestClient(app) as client:
            resposta = client.get("/app/sql")
            assert resposta.status_code == 200
            assert resposta.headers["X-Request-Id"]
            assert resposta.headers["X-Correlation-ID"]
            assert re.match(r"^[0-9a-f]{32}$", resposta.headers["X-Trace-Id"])
            assert re.match(
                r"^00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]$",
                resposta.headers["traceparent"],
            )
            assert "Server-Timing" in resposta.headers
            assert "sql;dur=" in resposta.headers["Server-Timing"]

            html = client.get("/app/ping")
            assert html.status_code == 200
            assert "ssr;dur=" in html.headers["Server-Timing"]

            summary = client.get("/debug-perf/summary")
            assert summary.status_code == 200
            payload = summary.json()
            assert payload["enabled"] is True
            assert payload["counts"]["requests"] >= 2
            assert any(item["path"] == "/app/sql" for item in payload["top_routes"])
            assert payload["top_queries"]

            report = client.get("/debug-perf/report")
            assert report.status_code == 200
            report_payload = report.json()
            assert any(item["path"] == "/app/sql" for item in report_payload["requests"])

            reset = client.post("/debug-perf/reset")
            assert reset.status_code == 200
            summary_resetado = client.get("/debug-perf/summary").json()
            assert summary_resetado["counts"]["requests"] == 0
            assert summary_resetado["counts"]["queries"] == 0
    finally:
        resetar_perf()
        get_settings.cache_clear()
        engine.dispose()
