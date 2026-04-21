from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import OperationalError

from app.shared.db import bootstrap


class _DummyConnection:
    def __enter__(self) -> "_DummyConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def execute(self, _query) -> None:  # noqa: ANN001
        return None


class _DummyEngine:
    def __init__(self) -> None:
        self.dispose_calls = 0

    def connect(self) -> _DummyConnection:
        return _DummyConnection()

    def dispose(self) -> None:
        self.dispose_calls += 1


def _fake_database_module(logger: Mock, engine: _DummyEngine | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        logger=logger,
        _EM_PRODUCAO=True,
        _SEED_DEV_BOOTSTRAP=False,
        motor_banco=engine or _DummyEngine(),
    )


def _operational_error() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("ssl closed"))


def test_inicializar_banco_reexecuta_bootstrap_em_operational_error_transitorio(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = Mock()
    engine = _DummyEngine()
    tentativas = {"count": 0}
    sleeps: list[float] = []

    monkeypatch.setattr(bootstrap, "_database_module", lambda: _fake_database_module(logger, engine))
    monkeypatch.setattr(bootstrap, "seed_limites_plano", lambda: None)
    monkeypatch.setattr(bootstrap, "_bootstrap_admin_inicial_producao", lambda: None)
    monkeypatch.setattr(bootstrap, "_bootstrap_catalogo_canonico_producao", lambda: None)
    monkeypatch.setattr(bootstrap, "_seed_dev", lambda: None)
    monkeypatch.setattr(bootstrap, "env_bool", lambda _name, default=False: True)
    monkeypatch.setattr(bootstrap, "env_int", lambda _name, default: 3 if "MAX_ATTEMPTS" in _name else default)
    monkeypatch.setattr(
        bootstrap,
        "env_float",
        lambda name, default: 0.25 if "RETRY_BASE_SECONDS" in name else (1.0 if "RETRY_MAX_SECONDS" in name else default),
    )
    monkeypatch.setattr(bootstrap.time, "sleep", lambda seconds: sleeps.append(seconds))

    def _aplicar() -> None:
        tentativas["count"] += 1
        if tentativas["count"] < 3:
            raise _operational_error()

    monkeypatch.setattr(bootstrap, "_aplicar_migracoes_versionadas", _aplicar)

    bootstrap.inicializar_banco()

    assert tentativas["count"] == 3
    assert sleeps == [0.25, 0.5]
    assert engine.dispose_calls == 2
    assert logger.warning.call_count == 2
    logger.info.assert_any_call("Banco de dados inicializado com sucesso.")


def test_inicializar_banco_propaga_operational_error_apos_esgotar_tentativas(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = Mock()
    engine = _DummyEngine()
    sleeps: list[float] = []

    monkeypatch.setattr(bootstrap, "_database_module", lambda: _fake_database_module(logger, engine))
    monkeypatch.setattr(bootstrap, "seed_limites_plano", lambda: None)
    monkeypatch.setattr(bootstrap, "_bootstrap_admin_inicial_producao", lambda: None)
    monkeypatch.setattr(bootstrap, "_bootstrap_catalogo_canonico_producao", lambda: None)
    monkeypatch.setattr(bootstrap, "_seed_dev", lambda: None)
    monkeypatch.setattr(bootstrap, "env_bool", lambda _name, default=False: True)
    monkeypatch.setattr(bootstrap, "env_int", lambda _name, default: 2 if "MAX_ATTEMPTS" in _name else default)
    monkeypatch.setattr(
        bootstrap,
        "env_float",
        lambda name, default: 0.1 if "RETRY_BASE_SECONDS" in name else (1.0 if "RETRY_MAX_SECONDS" in name else default),
    )
    monkeypatch.setattr(bootstrap.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(bootstrap, "_aplicar_migracoes_versionadas", lambda: (_ for _ in ()).throw(_operational_error()))

    with pytest.raises(OperationalError):
        bootstrap.inicializar_banco()

    assert sleeps == [0.1]
    assert engine.dispose_calls == 1
    assert logger.warning.call_count == 1
    assert logger.critical.call_count == 1


def test_inicializar_banco_pula_migracoes_quando_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = Mock()
    engine = _DummyEngine()
    migrations = {"count": 0}
    seeds = {"limites": 0, "admin": 0, "catalogo": 0}

    monkeypatch.setattr(bootstrap, "_database_module", lambda: _fake_database_module(logger, engine))
    monkeypatch.setattr(bootstrap, "env_bool", lambda name, default=False: False if name == "DB_BOOTSTRAP_RUN_MIGRATIONS" else default)
    monkeypatch.setattr(bootstrap, "_detectar_schema_incompleto", lambda: (False, []))
    monkeypatch.setattr(
        bootstrap,
        "_aplicar_migracoes_versionadas",
        lambda: migrations.__setitem__("count", migrations["count"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "seed_limites_plano",
        lambda: seeds.__setitem__("limites", seeds["limites"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "_bootstrap_admin_inicial_producao",
        lambda: seeds.__setitem__("admin", seeds["admin"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "_bootstrap_catalogo_canonico_producao",
        lambda: seeds.__setitem__("catalogo", seeds["catalogo"] + 1),
    )
    monkeypatch.setattr(bootstrap, "_seed_dev", lambda: None)

    bootstrap.inicializar_banco()

    assert migrations["count"] == 0
    assert seeds == {"limites": 1, "admin": 1, "catalogo": 1}
    logger.info.assert_any_call(
        "Bootstrap do banco executando sem migracoes versionadas nesta inicializacao.",
        extra={"db_bootstrap_run_migrations": False},
    )


def test_inicializar_banco_forca_migracoes_quando_schema_esta_incompleto(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = Mock()
    engine = _DummyEngine()
    migrations = {"count": 0}
    seeds = {"limites": 0, "admin": 0, "catalogo": 0}

    monkeypatch.setattr(bootstrap, "_database_module", lambda: _fake_database_module(logger, engine))
    monkeypatch.setattr(bootstrap, "env_bool", lambda name, default=False: False if name == "DB_BOOTSTRAP_RUN_MIGRATIONS" else default)
    monkeypatch.setattr(bootstrap, "_detectar_schema_incompleto", lambda: (True, ["limites_plano", "usuarios"]))
    monkeypatch.setattr(
        bootstrap,
        "_aplicar_migracoes_versionadas",
        lambda: migrations.__setitem__("count", migrations["count"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "seed_limites_plano",
        lambda: seeds.__setitem__("limites", seeds["limites"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "_bootstrap_admin_inicial_producao",
        lambda: seeds.__setitem__("admin", seeds["admin"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "_bootstrap_catalogo_canonico_producao",
        lambda: seeds.__setitem__("catalogo", seeds["catalogo"] + 1),
    )
    monkeypatch.setattr(bootstrap, "_seed_dev", lambda: None)

    bootstrap.inicializar_banco()

    assert migrations["count"] == 1
    assert seeds == {"limites": 1, "admin": 1, "catalogo": 1}
    logger.warning.assert_any_call(
        "Schema do banco incompleto; executando migracoes versionadas automaticamente.",
        extra={
            "db_bootstrap_run_migrations": False,
            "db_missing_tables_count": 2,
            "db_missing_tables_sample": ["limites_plano", "usuarios"],
        },
    )
