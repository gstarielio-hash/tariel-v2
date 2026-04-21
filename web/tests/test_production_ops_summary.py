from __future__ import annotations

import main

from app.core.settings import get_settings
from app.domains.admin.production_ops_summary import (
    build_admin_production_operations_summary,
)
from app.shared.database import NivelAcesso, Usuario
from app.shared.security import obter_usuario_html
import app.shared.security_session_store as security_session_store


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_production_ops_summary_expoe_politica_canonica(monkeypatch) -> None:
    monkeypatch.setenv("AMBIENTE", "production")
    monkeypatch.setenv("PASTA_UPLOADS_PERFIS", "/opt/render/project/src/web/static/uploads/perfis")
    monkeypatch.setenv("PASTA_ANEXOS_MESA", "/opt/render/project/src/web/static/uploads/mesa_anexos")
    monkeypatch.setenv("PASTA_APRENDIZADOS_VISUAIS_IA", "/opt/render/project/src/web/static/uploads/aprendizados_ia")
    monkeypatch.setenv("TARIEL_UPLOADS_STORAGE_MODE", "persistent_disk")
    monkeypatch.setenv("TARIEL_UPLOADS_PROFILE_RETENTION_DAYS", "365")
    monkeypatch.setenv("TARIEL_UPLOADS_MESA_RETENTION_DAYS", "365")
    monkeypatch.setenv("TARIEL_UPLOADS_LEARNING_RETENTION_DAYS", "365")
    monkeypatch.setenv("TARIEL_UPLOADS_CLEANUP_ENABLED", "1")
    monkeypatch.setenv("TARIEL_UPLOADS_CLEANUP_INTERVAL_HOURS", "24")
    monkeypatch.setenv("TARIEL_UPLOADS_CLEANUP_MAX_DELETIONS_PER_RUN", "200")
    monkeypatch.setenv("TARIEL_UPLOADS_BACKUP_REQUIRED", "1")
    monkeypatch.setenv("TARIEL_UPLOADS_RESTORE_DRILL_REQUIRED", "1")
    monkeypatch.setenv("SESSAO_CACHE_DB_REVALIDACAO_SEGUNDOS", "0")
    monkeypatch.setenv("SESSAO_FAIL_CLOSED_ON_DB_ERROR", "1")
    monkeypatch.setattr(
        security_session_store,
        "SESSAO_CACHE_DB_REVALIDACAO_SEGUNDOS",
        0,
        raising=False,
    )
    monkeypatch.setattr(
        security_session_store,
        "SESSAO_FAIL_CLOSED_ON_DB_ERROR",
        True,
        raising=False,
    )
    _clear_settings_cache()
    try:
        payload = build_admin_production_operations_summary()

        assert payload["uploads"]["storage_mode"] == "persistent_disk"
        assert payload["uploads"]["persistent_root_ready"] is True
        assert payload["uploads"]["backup_required"] is True
        assert payload["uploads"]["cleanup_mode"] == "automatic"
        assert payload["sessions"]["storage_mode"] == "db_authoritative_with_local_cache"
        assert payload["sessions"]["multi_instance_ready"] is True
        assert payload["sessions"]["fail_closed_on_db_error"] is True
        assert payload["readiness"]["production_ready"] is True
    finally:
        _clear_settings_cache()


def test_admin_route_production_ops_summary_retorna_payload_operacional(
    ambiente_critico,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AMBIENTE", "production")
    monkeypatch.setenv("PASTA_UPLOADS_PERFIS", "/opt/render/project/src/web/static/uploads/perfis")
    monkeypatch.setenv("PASTA_ANEXOS_MESA", "/opt/render/project/src/web/static/uploads/mesa_anexos")
    monkeypatch.setenv("PASTA_APRENDIZADOS_VISUAIS_IA", "/opt/render/project/src/web/static/uploads/aprendizados_ia")
    monkeypatch.setenv("TARIEL_UPLOADS_STORAGE_MODE", "persistent_disk")
    monkeypatch.setenv("TARIEL_UPLOADS_CLEANUP_ENABLED", "1")
    monkeypatch.setenv("TARIEL_UPLOADS_BACKUP_REQUIRED", "1")
    monkeypatch.setenv("TARIEL_UPLOADS_RESTORE_DRILL_REQUIRED", "1")
    monkeypatch.setenv("SESSAO_CACHE_DB_REVALIDACAO_SEGUNDOS", "0")
    monkeypatch.setenv("SESSAO_FAIL_CLOSED_ON_DB_ERROR", "1")
    monkeypatch.setattr(
        security_session_store,
        "SESSAO_CACHE_DB_REVALIDACAO_SEGUNDOS",
        0,
        raising=False,
    )
    monkeypatch.setattr(
        security_session_store,
        "SESSAO_FAIL_CLOSED_ON_DB_ERROR",
        True,
        raising=False,
    )
    _clear_settings_cache()
    try:
        client = ambiente_critico["client"]
        ids = ambiente_critico["ids"]
        main.app.dependency_overrides[obter_usuario_html] = lambda: Usuario(
            id=ids["admin_a"],
            empresa_id=ids["empresa_a"],
            nivel_acesso=NivelAcesso.DIRETORIA.value,
            email="admin@empresa-a.test",
        )
        resposta = client.get("/admin/api/production-ops/summary")
        main.app.dependency_overrides.pop(obter_usuario_html, None)

        assert resposta.status_code == 200
        payload = resposta.json()
        assert payload["contract_name"] == "AdminProductionOpsSummaryV1"
        assert payload["readiness"]["production_ready"] is True
        assert payload["sessions"]["multi_instance_ready"] is True
    finally:
        main.app.dependency_overrides.pop(obter_usuario_html, None)
        _clear_settings_cache()
