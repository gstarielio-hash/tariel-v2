"""Runtime de engine e sessão SQLAlchemy da aplicação."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.core.settings import env_int, env_str

load_dotenv()

_URL_PADRAO = "postgresql:///tariel_dev"
_AMBIENTE = env_str("AMBIENTE", "dev").strip().lower()
_EM_PRODUCAO = _AMBIENTE == "production"
_LOGGER = logging.getLogger("tariel.banco_dados")
_PARAMETROS_RUNTIME_SOBRESCREVEM_QUERY_EXISTENTE = frozenset({"sslmode", "connect_timeout"})


def _driver_postgres_sqlalchemy() -> str:
    driver = env_str("DB_SQLALCHEMY_DRIVER", "psycopg").strip().lower()
    if driver in {"psycopg", "psycopg2", "pg8000"}:
        return driver
    return "psycopg"


def _normalizar_url_banco(valor: str) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return _URL_PADRAO

    if texto.startswith("postgres://"):
        return f"postgresql+{_driver_postgres_sqlalchemy()}://" + texto.removeprefix("postgres://")

    if texto.startswith("postgresql://") and not re.match(r"^postgresql\+[a-z0-9_]+://", texto):
        return f"postgresql+{_driver_postgres_sqlalchemy()}://" + texto.removeprefix("postgresql://")

    return texto


def _parametros_runtime_postgres() -> dict[str, str]:
    parametros: dict[str, str] = {}

    sslmode = env_str("DB_SSLMODE", "").strip().lower()
    if sslmode:
        parametros["sslmode"] = sslmode

    connect_timeout = env_int("DB_CONNECT_TIMEOUT", 0)
    if connect_timeout > 0:
        parametros["connect_timeout"] = str(connect_timeout)

    application_name = env_str("DB_APPLICATION_NAME", "tariel-web" if _EM_PRODUCAO else "").strip()
    if application_name:
        parametros["application_name"] = application_name

    return parametros


def _aplicar_parametros_runtime_postgres(url: str) -> str:
    if not url.startswith("postgresql+") or _driver_postgres_sqlalchemy() == "pg8000":
        return url

    parametros_runtime = _parametros_runtime_postgres()
    if not parametros_runtime:
        return url

    partes = urlsplit(url)
    query_existente = parse_qsl(partes.query, keep_blank_values=True)
    indices_existentes = {chave: indice for indice, (chave, _valor) in enumerate(query_existente)}

    for chave, valor in parametros_runtime.items():
        indice_existente = indices_existentes.get(chave)
        if indice_existente is None:
            query_existente.append((chave, valor))
            indices_existentes[chave] = len(query_existente) - 1
            continue

        if chave in _PARAMETROS_RUNTIME_SOBRESCREVEM_QUERY_EXISTENTE:
            query_existente[indice_existente] = (chave, valor)

    return urlunsplit(
        (
            partes.scheme,
            partes.netloc,
            partes.path,
            urlencode(query_existente),
            partes.fragment,
        )
    )


def _connect_args_postgres() -> dict[str, Any]:
    if _driver_postgres_sqlalchemy() != "pg8000":
        return {}

    connect_args: dict[str, Any] = {}
    sslmode = env_str("DB_SSLMODE", "").strip().lower()
    if sslmode:
        connect_args["ssl_context"] = False if sslmode == "disable" else True

    connect_timeout = env_int("DB_CONNECT_TIMEOUT", 0)
    if connect_timeout > 0:
        connect_args["timeout"] = connect_timeout

    application_name = env_str("DB_APPLICATION_NAME", "tariel-web" if _EM_PRODUCAO else "").strip()
    if application_name:
        connect_args["application_name"] = application_name

    return connect_args


URL_BANCO = _aplicar_parametros_runtime_postgres(_normalizar_url_banco(env_str("DATABASE_URL", _URL_PADRAO)))
_EH_SQLITE = URL_BANCO.startswith("sqlite")
_EH_SQLITE_MEMORIA = _EH_SQLITE and (
    URL_BANCO in {"sqlite://", "sqlite:///:memory:"}
    or ":memory:" in URL_BANCO
    or "mode=memory" in URL_BANCO
)


def _criar_engine():
    kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "future": True,
    }

    if _EH_SQLITE:
        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool if _EH_SQLITE_MEMORIA else NullPool
    else:
        kwargs["pool_size"] = env_int("DB_POOL_SIZE", 3 if _EM_PRODUCAO else 10)
        kwargs["max_overflow"] = env_int("DB_MAX_OVERFLOW", 0 if _EM_PRODUCAO else 20)
        kwargs["pool_timeout"] = env_int("DB_POOL_TIMEOUT", 30)
        kwargs["pool_recycle"] = env_int("DB_POOL_RECYCLE", 300 if _EM_PRODUCAO else 3600)
        connect_args = _connect_args_postgres()
        if connect_args:
            kwargs["connect_args"] = connect_args

    engine = create_engine(URL_BANCO, **kwargs)
    if not _EH_SQLITE:
        _log_diagnostico_driver_postgres(engine, kwargs)

    if _EH_SQLITE:

        @event.listens_for(engine, "connect")
        def _configurar_sqlite(conn, _record):
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")

            if not _EH_SQLITE_MEMORIA:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")

            cursor.close()

    return engine


def _diagnostico_driver_postgres() -> dict[str, Any]:
    driver = _driver_postgres_sqlalchemy()

    if driver == "pg8000":
        try:
            import pg8000
        except Exception:
            return {"sqlalchemy_driver": driver}

        return {
            "sqlalchemy_driver": driver,
            "pg8000_version": pg8000.__version__,
        }

    if driver == "psycopg2":
        try:
            import psycopg2
            from psycopg2 import extensions
        except Exception:
            return {"sqlalchemy_driver": driver}

        return {
            "sqlalchemy_driver": driver,
            "psycopg2_version": psycopg2.__version__,
            "libpq_version": extensions.libpq_version(),
        }

    try:
        import psycopg
        from psycopg import pq
    except Exception:
        return {"sqlalchemy_driver": driver}

    return {
        "sqlalchemy_driver": driver,
        "psycopg_version": psycopg.__version__,
        "psycopg_impl": pq.__impl__,
        "libpq_version": pq.version(),
        "libpq_build_version": getattr(pq, "__build_version__", None),
    }


def _log_diagnostico_driver_postgres(engine, engine_kwargs: dict[str, Any]) -> None:  # noqa: ANN001
    diagnostico = _diagnostico_driver_postgres()
    diagnostico.update(
        {
            "engine_pool": type(engine.pool).__name__,
            "db_pool_size": engine_kwargs.get("pool_size"),
            "db_max_overflow": engine_kwargs.get("max_overflow"),
            "db_pool_timeout": engine_kwargs.get("pool_timeout"),
            "db_pool_recycle": engine_kwargs.get("pool_recycle"),
            "db_runtime_url_param_keys": sorted(_parametros_runtime_postgres().keys()),
            "db_runtime_connect_arg_keys": sorted(_connect_args_postgres().keys()),
        }
    )
    _LOGGER.info("Engine Postgres configurada.", extra=diagnostico)


motor_banco = _criar_engine()
SessaoLocal = sessionmaker(
    bind=motor_banco,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


__all__ = [
    "SessaoLocal",
    "URL_BANCO",
    "_normalizar_url_banco",
    "motor_banco",
]
