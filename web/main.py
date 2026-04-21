"""
main.py — Tariel.ia
Plataforma SaaS de inspeções inteligentes

Responsabilidades deste arquivo:
- criar e configurar a aplicação FastAPI
- aplicar middlewares globais
- endurecer headers e política de segurança
- inicializar banco e recursos no lifespan
- montar arquivos estáticos
- registrar roteadores
- definir endpoints operacionais (health/ready)
- tratar exceções globais
"""

from __future__ import annotations

import logging
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.http_runtime_support import (
    obter_ws_origins,
    pagina_html_erro,
    registrar_middlewares,
    rota_api,
)
from app.core.http_setup_support import (
    registrar_exception_handlers,
    registrar_openapi_custom,
    registrar_rotas_operacionais,
)
from app.core.logging_support import configurar_logging
from app.core.perf_support import medir_operacao, medir_operacao_async, registrar_instrumentacao_sql
from app.core.settings import env_bool, env_float, env_int, env_log_level, env_str, get_settings
from app.core.telemetry_support import configure_sentry_runtime, configure_telemetry_runtime
from app.domains.admin.uploads_cleanup import (
    start_uploads_cleanup_scheduler,
    stop_uploads_cleanup_scheduler,
)
from app.shared.database import (
    NivelAcesso,
    SessaoLocal,
    Usuario,
    inicializar_banco,
    motor_banco,
    obter_banco,
)
from app.domains.router_registry import (
    roteador_admin,
    roteador_cliente,
    roteador_inspetor,
    roteador_revisor,
)
from app.domains.revisor.realtime import describe_revisor_realtime, shutdown_revisor_realtime, startup_revisor_realtime
from app.shared.security import (
    SESSOES_ATIVAS,
    obter_dados_sessao_portal,
    portal_por_caminho,
    token_esta_ativo,
    usuario_tem_bloqueio_ativo,
)


# =============================================================================
# CAMINHOS
# =============================================================================

DIR_BASE: Final[Path] = Path(__file__).parent.resolve()
DIR_STATIC: Final[Path] = DIR_BASE / "static"


# =============================================================================
# HELPERS DE AMBIENTE
# =============================================================================

_obter_str_env = env_str
_obter_int_env = env_int
_obter_nivel_log_env = env_log_level


def _normalizar_host(valor: str) -> str:
    """
    Remove protocolo, barras finais e espaços.
    Mantém wildcard se existir, pois o TrustedHostMiddleware aceita "*.dominio".
    """
    texto = (valor or "").strip()
    if not texto:
        return ""

    texto = texto.removeprefix("https://").removeprefix("http://").rstrip("/")
    return texto.strip()


def _host_sem_porta(valor: str) -> str:
    texto = _normalizar_host(valor)
    if not texto or texto.startswith("*."):
        return texto
    return texto.split(":", 1)[0].strip()


def _deduplicar_preservando_ordem(valores: list[str]) -> list[str]:
    vistos: set[str] = set()
    saida: list[str] = []

    for valor in valores:
        if not valor or valor in vistos:
            continue
        vistos.add(valor)
        saida.append(valor)

    return saida


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bootstrap_banco_deve_bloquear_startup() -> bool:
    return env_bool("DB_BOOTSTRAP_BLOCKING_STARTUP", not EM_PRODUCAO)


def _atualizar_estado_bootstrap_banco(app: FastAPI, **campos: object) -> dict[str, object]:
    estado = dict(getattr(app.state, "db_bootstrap", {}) or {})
    estado.update(campos)
    estado["updated_at"] = _utc_iso_now()
    app.state.db_bootstrap = estado
    return estado


def _supervisionar_bootstrap_banco(app: FastAPI, stop_event: threading.Event) -> None:
    retry_base_seconds = max(env_float("DB_BOOTSTRAP_BACKGROUND_RETRY_BASE_SECONDS", 15.0), 1.0)
    retry_max_seconds = max(env_float("DB_BOOTSTRAP_BACKGROUND_RETRY_MAX_SECONDS", 60.0), retry_base_seconds)
    supervisor_attempt = 0

    while not stop_event.is_set():
        supervisor_attempt += 1
        _atualizar_estado_bootstrap_banco(
            app,
            status="starting" if supervisor_attempt == 1 else "retrying",
            ready=False,
            blocking=False,
            mode="background",
            supervisor_attempt=supervisor_attempt,
            next_retry_in_seconds=None,
        )
        try:
            with medir_operacao("boot", "startup.inicializar_banco.background"):
                inicializar_banco()

            with medir_operacao("boot", "startup.db_ping.background"):
                with SessaoLocal() as banco:
                    banco.execute(text("SELECT 1"))
        except Exception as erro:
            wait_seconds = min(retry_max_seconds, retry_base_seconds * supervisor_attempt)
            _atualizar_estado_bootstrap_banco(
                app,
                status="retrying",
                ready=False,
                blocking=False,
                mode="background",
                supervisor_attempt=supervisor_attempt,
                last_error=f"{type(erro).__name__}: {erro}",
                last_failure_at=_utc_iso_now(),
                next_retry_in_seconds=wait_seconds,
            )
            logger.error(
                "Bootstrap do banco segue pendente em background. Aplicacao continuara viva enquanto novas tentativas sao feitas.",
                extra={
                    "supervisor_attempt": supervisor_attempt,
                    "retry_in_seconds": wait_seconds,
                },
                exc_info=True,
            )
            if stop_event.wait(wait_seconds):
                return
            continue

        _atualizar_estado_bootstrap_banco(
            app,
            status="ready",
            ready=True,
            blocking=False,
            mode="background",
            supervisor_attempt=supervisor_attempt,
            last_error=None,
            last_failure_at=None,
            next_retry_in_seconds=None,
            ready_at=_utc_iso_now(),
        )
        logger.info(
            "Bootstrap do banco concluido com sucesso em background.",
            extra={"supervisor_attempt": supervisor_attempt},
        )
        return


# =============================================================================
# AMBIENTE
# =============================================================================

_settings = get_settings()
AMBIENTE: Final[str] = _settings.ambiente
EM_PRODUCAO: Final[bool] = _settings.em_producao
APP_VERSAO: Final[str] = _settings.app_versao
PORTA_APP: Final[int] = _settings.porta
HOST_BIND_APP: Final[str] = _normalizar_host(_settings.host_bind) or ("0.0.0.0" if not EM_PRODUCAO else "0.0.0.0")
LOG_LEVEL_DEV_ROOT: Final[int] = _obter_nivel_log_env("LOG_LEVEL_DEV_ROOT", logging.INFO)
LOG_LEVEL_DEV_TARIEL: Final[int] = _obter_nivel_log_env("LOG_LEVEL_DEV_TARIEL", logging.DEBUG)
REDIS_URL: Final[str | None] = _settings.redis_url or None


# =============================================================================
# HOSTS / DOMÍNIO
# =============================================================================

APP_HOST_PUBLICO: Final[str] = _normalizar_host(
    _obter_str_env(
        "APP_HOST_PUBLICO",
        _obter_str_env(
            "RENDER_EXTERNAL_HOSTNAME",
            "tariel.ia" if EM_PRODUCAO else "127.0.0.1:8000",
        ),
    )
)

_allowed_hosts_env = _obter_str_env("ALLOWED_HOSTS", "")
if _allowed_hosts_env:
    allowed_hosts_base = [_normalizar_host(item) for item in _allowed_hosts_env.split(",") if _normalizar_host(item)]
else:
    if EM_PRODUCAO:
        allowed_hosts_base = ["tariel.ia", "*.tariel.ia"]
    else:
        # Em dev, permite acesso por IP local (ex.: celular via 192.168.x.x)
        # sem exigir ajuste manual de ALLOWED_HOSTS.
        allowed_hosts_base = ["*"]

if APP_HOST_PUBLICO:
    allowed_hosts_base.append(APP_HOST_PUBLICO)
    allowed_hosts_base.append(_host_sem_porta(APP_HOST_PUBLICO))

ALLOWED_HOSTS: Final[list[str]] = _deduplicar_preservando_ordem(allowed_hosts_base)


# =============================================================================
# SEGREDO / SESSÃO
# =============================================================================

CHAVE_SECRETA = _obter_str_env("CHAVE_SECRETA_APP", "")
NOME_COOKIE_SESSAO: Final[str] = (
    _obter_str_env(
        "SESSION_COOKIE_NAME",
        "cracha_tariel_seguro",
    )
    or "cracha_tariel_seguro"
)
MAX_AGE_SESSAO: Final[int] = max(_obter_int_env("SESSION_MAX_AGE", 2592000), 300)

if not CHAVE_SECRETA:
    if EM_PRODUCAO:
        sys.stderr.write("[CRITICAL] CHAVE_SECRETA_APP não definida. Impossível iniciar em produção.\n")
        sys.exit(1)

    CHAVE_SECRETA = "dev-chave-fixa-tariel-2026-nao-usar-em-producao"

if EM_PRODUCAO and len(CHAVE_SECRETA) < 32:
    sys.stderr.write("[CRITICAL] CHAVE_SECRETA_APP muito curta. Use ao menos 32 caracteres em produção.\n")
    sys.exit(1)


# =============================================================================
# LOGGING
# =============================================================================

configurar_logging(
    em_producao=EM_PRODUCAO,
    ambiente=AMBIENTE,
    log_level_dev_root=LOG_LEVEL_DEV_ROOT,
    log_level_dev_tariel=LOG_LEVEL_DEV_TARIEL,
)
logger = logging.getLogger("tariel.main")
TELEMETRY_RUNTIME = configure_telemetry_runtime(settings=_settings)
SENTRY_RUNTIME = configure_sentry_runtime(settings=_settings)

if not EM_PRODUCAO:
    logger.warning(
        "Modo desenvolvimento ativo. Nunca suba esta configuração em produção.",
        extra={"ambiente": AMBIENTE},
    )

logger.info(
    "Runtime de observabilidade inicializado",
    extra={
        "otel_enabled": TELEMETRY_RUNTIME["otel"]["enabled"],
        "otel_exporter_mode": TELEMETRY_RUNTIME["otel"]["exporter_mode"],
        "sentry_enabled": SENTRY_RUNTIME["sentry"]["enabled"],
        "observability_release": TELEMETRY_RUNTIME["release"],
    },
)


# =============================================================================
# RATE LIMIT
# =============================================================================

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri=REDIS_URL,
    swallow_errors=True,
    in_memory_fallback=["200/minute"],
    in_memory_fallback_enabled=True,
)


# =============================================================================
# RUNTIME HTTP / SEGURANÇA DE FRONT
# =============================================================================

WS_ORIGINS: Final[list[str]] = obter_ws_origins(
    em_producao=EM_PRODUCAO,
    app_host_publico=_host_sem_porta(APP_HOST_PUBLICO),
)


# =============================================================================
# HELPERS DE SESSÃO / USUÁRIO
# =============================================================================


def _obter_usuario_da_sessao(
    request: Request,
    banco: Session,
) -> Optional[Usuario]:
    dados_sessao = obter_dados_sessao_portal(
        request.session,
        caminho=request.url.path,
    )
    token = dados_sessao.get("token")
    if not token or not token_esta_ativo(token):
        return None

    usuario_id = SESSOES_ATIVAS.get(token)
    if not usuario_id:
        return None

    usuario = banco.get(Usuario, usuario_id)
    if not usuario:
        return None

    if usuario_tem_bloqueio_ativo(usuario):
        return None

    return usuario


def _redirecionar_por_nivel(usuario: Usuario) -> RedirectResponse:
    nivel = usuario.nivel_acesso

    if nivel == NivelAcesso.INSPETOR.value:
        return RedirectResponse(url="/app/", status_code=302)

    if nivel == NivelAcesso.REVISOR.value:
        return RedirectResponse(url="/revisao/painel", status_code=302)

    if nivel == NivelAcesso.ADMIN_CLIENTE.value:
        return RedirectResponse(url="/cliente/painel", status_code=302)

    if nivel == NivelAcesso.DIRETORIA.value:
        return RedirectResponse(url="/admin/painel", status_code=302)

    return RedirectResponse(url="/app/login", status_code=302)


# =============================================================================
# LIFESPAN
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Iniciando Tariel.ia",
        extra={
            "ambiente": AMBIENTE,
            "versao": APP_VERSAO,
            "allowed_hosts": ALLOWED_HOSTS,
        },
    )

    bootstrap_stop: threading.Event | None = None

    try:
        if _bootstrap_banco_deve_bloquear_startup():
            _atualizar_estado_bootstrap_banco(
                app,
                status="starting",
                ready=False,
                blocking=True,
                mode="blocking",
                supervisor_attempt=1,
                next_retry_in_seconds=None,
            )
            with medir_operacao("boot", "startup.inicializar_banco"):
                inicializar_banco()

            with medir_operacao("boot", "startup.db_ping"):
                with SessaoLocal() as banco:
                    banco.execute(text("SELECT 1"))

            _atualizar_estado_bootstrap_banco(
                app,
                status="ready",
                ready=True,
                blocking=True,
                mode="blocking",
                supervisor_attempt=1,
                next_retry_in_seconds=None,
                last_error=None,
                last_failure_at=None,
                ready_at=_utc_iso_now(),
            )
        else:
            bootstrap_stop = threading.Event()
            app.state.db_bootstrap_stop = bootstrap_stop
            app.state.db_bootstrap_thread = threading.Thread(
                target=_supervisionar_bootstrap_banco,
                args=(app, bootstrap_stop),
                name="tariel-db-bootstrap",
                daemon=True,
            )
            _atualizar_estado_bootstrap_banco(
                app,
                status="starting",
                ready=False,
                blocking=False,
                mode="background",
                supervisor_attempt=0,
                next_retry_in_seconds=None,
            )
            app.state.db_bootstrap_thread.start()
            logger.warning(
                "Aplicacao iniciada com bootstrap do banco em background.",
                extra={"ambiente": AMBIENTE},
            )

        async with medir_operacao_async("boot", "startup.revisor_realtime"):
            await startup_revisor_realtime()
        with medir_operacao("boot", "startup.uploads_cleanup_scheduler"):
            start_uploads_cleanup_scheduler(
                ready_probe=lambda: bool(
                    dict(getattr(app.state, "db_bootstrap", {}) or {}).get("ready")
                ),
                wait_reason="db_bootstrap_pending",
            )

        logger.info("Inicialização concluída com sucesso")
    except Exception:
        if bootstrap_stop is not None:
            bootstrap_stop.set()
            app.state.db_bootstrap_thread.join(timeout=5)
        logger.critical(
            "Falha catastrófica na inicialização. Abortando.",
            exc_info=True,
        )
        raise

    yield

    stop_uploads_cleanup_scheduler()
    bootstrap_stop = getattr(app.state, "db_bootstrap_stop", None)
    bootstrap_thread = getattr(app.state, "db_bootstrap_thread", None)
    if bootstrap_stop is not None:
        bootstrap_stop.set()
    if bootstrap_thread is not None:
        bootstrap_thread.join(timeout=5)
    await shutdown_revisor_realtime()
    logger.info("Encerrando Tariel.ia")


# =============================================================================
# FACTORY DA APLICAÇÃO
# =============================================================================


def create_app() -> FastAPI:
    registrar_instrumentacao_sql(motor_banco)
    app = FastAPI(
        title="Tariel.ia",
        version=APP_VERSAO,
        docs_url=None if EM_PRODUCAO else "/docs",
        redoc_url=None if EM_PRODUCAO else "/redoc",
        openapi_url=None if EM_PRODUCAO else "/openapi.json",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.state.db_bootstrap = {
        "status": "not_started",
        "ready": False,
        "blocking": _bootstrap_banco_deve_bloquear_startup(),
        "mode": "blocking" if _bootstrap_banco_deve_bloquear_startup() else "background",
        "supervisor_attempt": 0,
        "next_retry_in_seconds": None,
        "updated_at": _utc_iso_now(),
    }
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    registrar_openapi_custom(app)
    registrar_exception_handlers(
        app,
        logger=logger,
        sessao_local=SessaoLocal,
        obter_dados_sessao_portal=obter_dados_sessao_portal,
        token_esta_ativo=token_esta_ativo,
        obter_usuario_da_sessao=_obter_usuario_da_sessao,
        redirecionar_por_nivel=_redirecionar_por_nivel,
        rota_api=rota_api,
        pagina_html_erro=pagina_html_erro,
    )
    registrar_middlewares(
        app,
        logger=logger,
        em_producao=EM_PRODUCAO,
        chave_secreta=CHAVE_SECRETA,
        max_age_sessao=MAX_AGE_SESSAO,
        nome_cookie_sessao=NOME_COOKIE_SESSAO,
        allowed_hosts=ALLOWED_HOSTS,
        ws_origins=WS_ORIGINS,
    )

    if not DIR_STATIC.is_dir():
        logger.warning(
            "Diretório de estáticos não encontrado",
            extra={"path": str(DIR_STATIC)},
        )
    else:
        app.mount("/static", StaticFiles(directory=str(DIR_STATIC)), name="static")

    # -------------------------------------------------------------------------
    # ROTEADORES
    # -------------------------------------------------------------------------

    app.include_router(roteador_admin, prefix="/admin", tags=["Administração"])
    app.include_router(roteador_cliente, prefix="/cliente", tags=["Cliente"])
    app.include_router(roteador_inspetor, prefix="/app", tags=["Inspetor"])
    app.include_router(roteador_revisor, tags=["Revisão"])
    registrar_rotas_operacionais(
        app,
        dir_static=DIR_STATIC,
        app_versao=APP_VERSAO,
        ambiente=AMBIENTE,
        em_producao=EM_PRODUCAO,
        redis_url=REDIS_URL,
        logger=logger,
        sessao_local=SessaoLocal,
        obter_banco=obter_banco,
        portal_por_caminho=portal_por_caminho,
        obter_dados_sessao_portal=obter_dados_sessao_portal,
        sessoes_ativas=SESSOES_ATIVAS,
        usuario_model=Usuario,
        describe_revisor_realtime=describe_revisor_realtime,
        token_esta_ativo=token_esta_ativo,
        obter_usuario_da_sessao=_obter_usuario_da_sessao,
        redirecionar_por_nivel=_redirecionar_por_nivel,
    )

    return app


# =============================================================================
# INSTÂNCIA DA APP
# =============================================================================

app = create_app()


# =============================================================================
# EXECUÇÃO LOCAL
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST_BIND_APP,
        port=PORTA_APP,
        reload=not EM_PRODUCAO,
        log_level="debug" if not EM_PRODUCAO else "info",
        access_log=not EM_PRODUCAO,
    )
