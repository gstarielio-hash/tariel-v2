from __future__ import annotations

import logging
import secrets
import time
import uuid
from typing import Any, Final

from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.logging_support import correlation_id_ctx, span_id_ctx, trace_id_ctx
from app.core.perf_support import (
    backend_perf_habilitado,
    construir_server_timing,
    encerrar_request_perf,
    iniciar_request_perf,
)
from app.core.settings import get_settings
from app.core.telemetry_support import (
    mark_current_span_exception,
    mark_current_span_success,
    start_request_trace,
    sync_trace_context_to_request,
)

CSP_STYLE_FONTES: Final[str] = "https://fonts.googleapis.com"
CSP_FONT_GSTATIC: Final[str] = "https://fonts.gstatic.com"
CSP_SCRIPTS_CDN: Final[str] = "https://cdn.jsdelivr.net"


def obter_ws_origins(*, em_producao: bool, app_host_publico: str | None) -> list[str]:
    if em_producao:
        host_publico = str(app_host_publico or "").strip()
        if not host_publico:
            return []
        return [f"wss://{host_publico}"]

    return [
        "ws://127.0.0.1:8000",
        "ws://localhost:8000",
    ]


def construir_csp(
    nonce: str,
    *,
    em_producao: bool,
    ws_origins: list[str],
    para_app: bool = True,
) -> str:
    if not para_app:
        return "default-src 'self'; frame-ancestors 'none';"

    connect_src = " ".join(
        [
            "'self'",
            "blob:",
            *ws_origins,
            CSP_SCRIPTS_CDN,
            CSP_STYLE_FONTES,
            CSP_FONT_GSTATIC,
        ]
    )

    partes = [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-src 'none'",
        "manifest-src 'self'",
        f"style-src 'self' {CSP_STYLE_FONTES} 'unsafe-inline'",
        f"font-src 'self' data: {CSP_FONT_GSTATIC}",
        f"script-src 'self' {CSP_SCRIPTS_CDN} 'nonce-{nonce}' 'unsafe-hashes'",
        "img-src 'self' data: blob: https://cdn-icons-png.flaticon.com",
        f"connect-src {connect_src}",
        "worker-src 'self' blob:",
        "media-src 'self' blob:",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]

    if em_producao:
        partes.append("upgrade-insecure-requests")

    return "; ".join(partes) + ";"


def rota_api(path: str) -> bool:
    return path.startswith(("/api/", "/app/api/", "/revisao/api/", "/cliente/api/", "/admin/api/"))


def rota_protegida_html(path: str) -> bool:
    return path.startswith(("/admin", "/app", "/cliente", "/revisao"))


def deve_no_store(path: str) -> bool:
    if path.startswith("/static"):
        return False

    if path in {"/favicon.ico"}:
        return False

    return rota_protegida_html(path)


def pagina_html_erro(
    titulo: str,
    mensagem: str,
    correlation_id: str | None = None,
    status_code: int = 500,
) -> HTMLResponse:
    cid_html = f"<p style='opacity:.7;font-size:12px;margin-top:18px;'>CID: {correlation_id}</p>" if correlation_id else ""

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>{titulo}</title>
        <style>
            body {{
                margin: 0;
                font-family: Inter, Arial, sans-serif;
                background: #081624;
                color: #ffffff;
                display: grid;
                place-items: center;
                min-height: 100vh;
                padding: 24px;
            }}
            .box {{
                width: 100%;
                max-width: 560px;
                background: #10263d;
                border: 1px solid rgba(255,255,255,.08);
                border-radius: 18px;
                padding: 28px;
                box-shadow: 0 20px 60px rgba(0,0,0,.35);
            }}
            h1 {{
                margin: 0 0 12px;
                font-size: 22px;
            }}
            p {{
                margin: 0;
                line-height: 1.6;
                color: #c6d5e3;
            }}
            a {{
                display: inline-block;
                margin-top: 18px;
                color: #F47B20;
                text-decoration: none;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>{titulo}</h1>
            <p>{mensagem}</p>
            {cid_html}
            <a href="/app/login">Ir para o login</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=status_code)


class MiddlewareCorrelationID(BaseHTTPMiddleware):
    def __init__(self, app: Any, *, logger: logging.Logger) -> None:
        super().__init__(app)
        self.logger = logger
        settings = get_settings()
        self.header = settings.observability_header_name
        self.client_request_header = settings.observability_client_request_header_name
        self.trace_header = settings.observability_trace_header_name
        self.fallback_headers = (
            self.client_request_header,
            "X-Request-Id",
            "X-Mesa-Client-Trace-Id",
        )

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        correlation_id = ""
        for header_name in (self.header, *self.fallback_headers):
            candidate = str(request.headers.get(header_name) or "").strip()
            if candidate:
                correlation_id = candidate
                break
        if not correlation_id:
            correlation_id = uuid.uuid4().hex

        client_request_id = ""
        for header_name in (self.client_request_header, self.header, "X-Mesa-Client-Trace-Id"):
            candidate = str(request.headers.get(header_name) or "").strip()
            if candidate:
                client_request_id = candidate
                break

        request.state.correlation_id = correlation_id
        request.state.request_id = correlation_id
        request.state.client_request_id = client_request_id or None
        token_ctx = correlation_id_ctx.set(correlation_id)
        token_trace = trace_id_ctx.set("-")
        token_span = span_id_ctx.set("-")
        token_perf = iniciar_request_perf(
            request_id=correlation_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )
        inicio = time.perf_counter()

        with start_request_trace(
            request=request,
            span_name=f"{request.method} {request.url.path}",
            correlation_id=correlation_id,
            request_id=correlation_id,
            client_request_id=client_request_id or None,
        ):
            sync_trace_context_to_request(request)
            try:
                response = await call_next(request)
            except Exception as exc:
                duracao_ms = round((time.perf_counter() - inicio) * 1000, 1)
                mark_current_span_exception(exc, status_code=500)
                encerrar_request_perf(
                    token_perf,
                    status_code=500,
                    detail={
                        "error": "exception",
                        "path": request.url.path,
                        "method": request.method,
                    },
                )
                self.logger.exception(
                    "Falha durante processamento da requisição",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "duration_ms": duracao_ms,
                    },
                )
                raise
            else:
                duracao_ms = round((time.perf_counter() - inicio) * 1000, 1)
                trace_snapshot = mark_current_span_success(response.status_code) or sync_trace_context_to_request(request)
                response_content_type = response.headers.get("content-type", "")
                metric = encerrar_request_perf(
                    token_perf,
                    status_code=response.status_code,
                    content_type=response_content_type,
                    detail={
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": response.status_code,
                    },
                )
                response.headers[self.header] = correlation_id
                response.headers["X-Request-Id"] = correlation_id
                response.headers["X-Response-Time"] = f"{duracao_ms}ms"
                if client_request_id:
                    response.headers[self.client_request_header] = client_request_id
                if trace_snapshot:
                    response.headers[self.trace_header] = trace_snapshot["trace_id"]
                    response.headers["traceparent"] = trace_snapshot["traceparent"]
                if backend_perf_habilitado():
                    server_timing = construir_server_timing(metric)
                    if server_timing:
                        response.headers["Server-Timing"] = server_timing

                self.logger.info(
                    "Requisição processada",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": response.status_code,
                        "duration_ms": duracao_ms,
                    },
                )
                return response
            finally:
                correlation_id_ctx.reset(token_ctx)
                trace_id_ctx.reset(token_trace)
                span_id_ctx.reset(token_span)


class MiddlewareHeadersSeguranca(BaseHTTPMiddleware):
    HEADERS_REMOVER: Final[tuple[str, ...]] = ("server", "x-powered-by")

    def __init__(
        self,
        app: Any,
        *,
        em_producao: bool,
        ws_origins: list[str],
    ) -> None:
        super().__init__(app)
        self.em_producao = em_producao
        self.ws_origins = ws_origins

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce

        response = await call_next(request)
        caminho = request.url.path

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-DNS-Prefetch-Control"] = "off"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"

        if deve_no_store(caminho):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        for header in self.HEADERS_REMOVER:
            if header in response.headers:
                del response.headers[header]

        if self.em_producao:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        if rota_protegida_html(caminho):
            response.headers["Content-Security-Policy"] = construir_csp(
                nonce=nonce,
                em_producao=self.em_producao,
                ws_origins=self.ws_origins,
                para_app=True,
            )

        return response


def registrar_middlewares(
    app: FastAPI,
    *,
    logger: logging.Logger,
    em_producao: bool,
    chave_secreta: str,
    max_age_sessao: int,
    nome_cookie_sessao: str,
    allowed_hosts: list[str],
    ws_origins: list[str],
) -> None:
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(MiddlewareCorrelationID, logger=logger)
    app.add_middleware(
        MiddlewareHeadersSeguranca,
        em_producao=em_producao,
        ws_origins=ws_origins,
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=chave_secreta,
        https_only=em_producao,
        same_site="lax",
        max_age=max_age_sessao,
        session_cookie=nome_cookie_sessao,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )
