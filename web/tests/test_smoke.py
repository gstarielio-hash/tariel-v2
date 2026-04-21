import json

from fastapi.testclient import TestClient
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.domains.admin.services as admin_services
import app.domains.chat.routes as rotas_inspetor
import app.domains.revisor.routes as rotas_revisor
import app.shared.database as banco_dados
import app.shared.db.runtime as db_runtime
import app.shared.security as seguranca
import main
import pytest


def _write_canonical_catalog_fixture(tmp_path: Path, *, family_keys: list[str]) -> Path:
    docs_dir = tmp_path / "docs"
    family_dir = docs_dir / "family_schemas"
    master_dir = docs_dir / "master_templates"
    family_dir.mkdir(parents=True, exist_ok=True)
    master_dir.mkdir(parents=True, exist_ok=True)

    for family_key in family_keys:
        macro = family_key.split("_", 1)[0].upper()
        payload = {
            "family_key": family_key,
            "nome_exibicao": family_key.replace("_", " ").title(),
            "macro_categoria": macro,
            "schema_version": 1,
            "descricao": f"Schema canônico {family_key}.",
        }
        (family_dir / f"{family_key}.json").write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )

    return docs_dir


@pytest.fixture
def cliente_main_isolado():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    banco_dados.Base.metadata.create_all(bind=engine)

    def override_obter_banco():
        banco = SessionLocal()
        try:
            yield banco
            if banco_dados.sessao_tem_mutacoes_pendentes(banco):
                banco.commit()
        except Exception:
            banco.rollback()
            raise
        finally:
            banco.close()

    main.app.dependency_overrides[banco_dados.obter_banco] = override_obter_banco

    sessao_local_banco_original = banco_dados.SessaoLocal
    sessao_local_seguranca_original = seguranca.SessaoLocal
    sessao_local_inspetor_original = rotas_inspetor.SessaoLocal
    sessao_local_revisor_original = rotas_revisor.SessaoLocal
    sessao_local_main_original = main.SessaoLocal
    inicializar_banco_original = main.inicializar_banco
    sessionmaker_original_binds: dict[int, object] = {}
    for factory in {
        sessao_local_banco_original,
        sessao_local_seguranca_original,
        sessao_local_inspetor_original,
        sessao_local_revisor_original,
        sessao_local_main_original,
    }:
        if hasattr(factory, "configure"):
            sessionmaker_original_binds[id(factory)] = factory.kw.get("bind")
            factory.configure(bind=engine)
    banco_dados.SessaoLocal = SessionLocal
    seguranca.SessaoLocal = SessionLocal
    rotas_inspetor.SessaoLocal = SessionLocal
    rotas_revisor.SessaoLocal = SessionLocal
    main.SessaoLocal = SessionLocal
    main.inicializar_banco = lambda: None

    try:
        with TestClient(main.app) as cliente:
            yield cliente
    finally:
        banco_dados.SessaoLocal = sessao_local_banco_original
        seguranca.SessaoLocal = sessao_local_seguranca_original
        rotas_inspetor.SessaoLocal = sessao_local_inspetor_original
        rotas_revisor.SessaoLocal = sessao_local_revisor_original
        main.SessaoLocal = sessao_local_main_original
        for factory in {
            sessao_local_banco_original,
            sessao_local_seguranca_original,
            sessao_local_inspetor_original,
            sessao_local_revisor_original,
            sessao_local_main_original,
        }:
            if hasattr(factory, "configure"):
                factory.configure(bind=sessionmaker_original_binds.get(id(factory)))
        main.inicializar_banco = inicializar_banco_original
        main.app.dependency_overrides.clear()
        seguranca.SESSOES_ATIVAS.clear()
        seguranca._SESSAO_EXPIRACAO.clear()  # noqa: SLF001
        seguranca._SESSAO_META.clear()  # noqa: SLF001
        engine.dispose()


def test_healthcheck_retorna_ok(cliente_main_isolado: TestClient) -> None:
    resposta = cliente_main_isolado.get("/health")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["rate_limit_storage"] == ("redis_configurado" if main.REDIS_URL else "memory")
    assert "versao" in corpo
    assert "revisor_realtime_status" in corpo


def test_healthcheck_expone_fallback_em_memoria_quando_rate_limit_storage_redis_cai(
    cliente_main_isolado: TestClient,
) -> None:
    limiter = main.app.state.limiter
    estado_original = getattr(limiter, "_storage_dead", False)
    limiter._storage_dead = True

    try:
        resposta = cliente_main_isolado.get("/health")
    finally:
        limiter._storage_dead = estado_original

    assert resposta.status_code == 200
    assert resposta.json()["rate_limit_storage"] == "memory_fallback"


def test_readiness_retorna_banco_ok(cliente_main_isolado: TestClient) -> None:
    resposta = cliente_main_isolado.get("/ready")

    assert resposta.status_code == 200
    corpo = resposta.json()
    realtime_esperado = main.describe_revisor_realtime()
    assert corpo["status"] == "ok"
    assert corpo["banco"] == "ok"
    assert corpo["rate_limit_storage"] == ("redis_configurado" if main.REDIS_URL else "memory")
    assert corpo["revisor_realtime_backend"] == realtime_esperado["backend"]
    assert corpo["revisor_realtime_configured_backend"] == realtime_esperado["configured_backend"]
    assert corpo["revisor_realtime_distributed"] == realtime_esperado["distributed"]
    assert corpo["revisor_realtime_status"] == realtime_esperado["startup_status"]
    assert corpo["revisor_realtime_degraded"] == realtime_esperado["degraded"]
    assert corpo["revisor_realtime_last_error"] == realtime_esperado["last_error"]
    assert "production_ops_ready" in corpo
    assert "uploads_storage_mode" in corpo
    assert "uploads_persistent_storage_ready" in corpo
    assert "uploads_cleanup_wait_reason" in corpo
    assert "session_multi_instance_ready" in corpo


def test_readiness_expone_fallback_em_memoria_quando_rate_limit_storage_redis_cai(
    cliente_main_isolado: TestClient,
) -> None:
    limiter = main.app.state.limiter
    estado_original = getattr(limiter, "_storage_dead", False)
    limiter._storage_dead = True

    try:
        resposta = cliente_main_isolado.get("/ready")
    finally:
        limiter._storage_dead = estado_original

    assert resposta.status_code == 200
    assert resposta.json()["rate_limit_storage"] == "memory_fallback"


def test_readiness_retorna_503_quando_bootstrap_do_banco_esta_pendente(cliente_main_isolado: TestClient) -> None:
    estado_original = dict(getattr(main.app.state, "db_bootstrap", {}) or {})
    main.app.state.db_bootstrap = {
        "status": "retrying",
        "ready": False,
        "blocking": False,
        "mode": "background",
        "supervisor_attempt": 3,
        "next_retry_in_seconds": 6.0,
    }

    try:
        resposta = cliente_main_isolado.get("/ready")
    finally:
        main.app.state.db_bootstrap = estado_original

    assert resposta.status_code == 503
    corpo = resposta.json()
    realtime_esperado = main.describe_revisor_realtime()
    assert corpo["status"] == "starting"
    assert corpo["banco"] == "retrying"
    assert corpo["rate_limit_storage"] == ("redis_configurado" if main.REDIS_URL else "memory")
    assert corpo["revisor_realtime_backend"] == realtime_esperado["backend"]
    assert corpo["revisor_realtime_configured_backend"] == realtime_esperado["configured_backend"]
    assert corpo["revisor_realtime_distributed"] == realtime_esperado["distributed"]
    assert corpo["revisor_realtime_status"] == realtime_esperado["startup_status"]
    assert corpo["revisor_realtime_degraded"] == realtime_esperado["degraded"]
    assert corpo["revisor_realtime_last_error"] == realtime_esperado["last_error"]
    assert corpo["db_bootstrap"]["supervisor_attempt"] == 3


def test_raiz_redireciona_para_login_sem_sessao(cliente_main_isolado: TestClient) -> None:
    resposta = cliente_main_isolado.get("/", follow_redirects=False)

    assert resposta.status_code in {302, 303, 307}
    assert resposta.headers["location"] == "/app/login"


def test_templates_chat_mantem_controles_essenciais_de_ui() -> None:
    raiz = Path(__file__).resolve().parents[1]
    inspetor_base_html = (raiz / "templates" / "inspetor" / "base.html").read_text(encoding="utf-8")
    index_html = (raiz / "templates" / "index.html").read_text(encoding="utf-8")
    portal_main_html = (raiz / "templates" / "inspetor" / "_portal_main.html").read_text(encoding="utf-8")
    sidebar_html = (raiz / "templates" / "inspetor" / "_sidebar.html").read_text(encoding="utf-8")
    workspace_html = (raiz / "templates" / "inspetor" / "_workspace.html").read_text(encoding="utf-8")
    workspace_header_html = (raiz / "templates" / "inspetor" / "workspace" / "_workspace_header.html").read_text(encoding="utf-8")
    workspace_toolbar_html = (raiz / "templates" / "inspetor" / "workspace" / "_workspace_toolbar.html").read_text(encoding="utf-8")
    workspace_assistant_html = (raiz / "templates" / "inspetor" / "workspace" / "_assistant_landing.html").read_text(encoding="utf-8")
    workspace_history_html = (raiz / "templates" / "inspetor" / "workspace" / "_inspection_history.html").read_text(encoding="utf-8")
    workspace_record_html = (raiz / "templates" / "inspetor" / "workspace" / "_inspection_record.html").read_text(encoding="utf-8")
    workspace_conversation_html = (raiz / "templates" / "inspetor" / "workspace" / "_inspection_conversation.html").read_text(encoding="utf-8")
    workspace_mesa_html = (raiz / "templates" / "inspetor" / "workspace" / "_inspection_mesa.html").read_text(encoding="utf-8")
    workspace_rail_html = (raiz / "templates" / "inspetor" / "workspace" / "_workspace_context_rail.html").read_text(encoding="utf-8")
    mesa_widget_html = (raiz / "templates" / "inspetor" / "_mesa_widget.html").read_text(encoding="utf-8")
    home_html = (raiz / "templates" / "inspetor" / "_portal_home.html").read_text(encoding="utf-8")
    gate_modal_html = (raiz / "templates" / "inspetor" / "modals" / "_gate_qualidade.html").read_text(encoding="utf-8")
    nova_inspecao_html = (raiz / "templates" / "inspetor" / "modals" / "_nova_inspecao.html").read_text(encoding="utf-8")

    assert not (raiz / "templates" / "base.html").exists()
    assert 'id="btn-toggle-ui"' in inspetor_base_html
    assert 'id="icone-toggle-ui"' in inspetor_base_html
    assert 'id="btn-shell-home"' in inspetor_base_html
    assert 'id="btn-shell-profile"' in inspetor_base_html

    assert '{% include "inspetor/_portal_main.html" %}' in index_html
    assert '{% include "inspetor/modals/_nova_inspecao.html" %}' in index_html
    assert '{% include "inspetor/modals/_gate_qualidade.html" %}' in index_html
    assert '{% include "inspetor/modals/_perfil.html" %}' in index_html

    assert 'data-action="go-home"' in sidebar_html
    assert '{% include "inspetor/workspace/_workspace_header.html" %}' in workspace_html
    assert '{% include "inspetor/workspace/_workspace_toolbar.html" %}' in workspace_html
    assert '{% include "inspetor/workspace/_assistant_landing.html" %}' in workspace_html
    assert '{% include "inspetor/workspace/_inspection_history.html" %}' in workspace_html
    assert '{% include "inspetor/workspace/_inspection_record.html" %}' in workspace_html
    assert '{% include "inspetor/workspace/_inspection_conversation.html" %}' in workspace_html
    assert '{% include "inspetor/workspace/_inspection_mesa.html" %}' in workspace_html
    assert '{% include "inspetor/workspace/_workspace_context_rail.html" %}' in workspace_html
    assert 'id="btn-anexo"' in workspace_html
    assert 'id="input-anexo"' in workspace_html
    assert 'id="preview-anexo"' in workspace_html
    assert 'id="btn-toggle-humano"' in workspace_html
    assert 'id="rodape-contexto-titulo"' in workspace_html
    assert 'id="rodape-contexto-status"' in workspace_html
    assert 'class="btn-secundario btn-home-cabecalho technical-record-back"' in workspace_header_html
    assert 'data-action="go-home"' in workspace_header_html
    assert 'id="workspace-titulo-laudo"' in workspace_header_html
    assert 'id="workspace-status-badge"' in workspace_header_html
    assert 'id="workspace-summary-state"' in workspace_header_html
    assert 'id="workspace-summary-evidencias"' in workspace_header_html
    assert 'id="workspace-summary-pendencias"' in workspace_header_html
    assert 'id="workspace-summary-mesa"' in workspace_header_html
    assert 'id="workspace-public-verification"' in workspace_header_html
    assert 'id="workspace-public-verification-link"' in workspace_header_html
    assert 'id="btn-workspace-copy-verification"' in workspace_header_html
    assert 'id="workspace-official-issue"' in workspace_header_html
    assert 'id="workspace-official-issue-title"' in workspace_header_html
    assert 'id="workspace-official-issue-chip"' in workspace_header_html
    assert 'id="btn-workspace-open-inspecao-modal"' in workspace_header_html
    assert 'class="thread-nav"' in workspace_toolbar_html
    assert 'id="workspace-nav-caption"' in workspace_toolbar_html
    assert 'id="workspace-nav-status"' in workspace_toolbar_html
    assert 'data-tab="conversa"' in workspace_toolbar_html
    assert 'data-tab="historico"' in workspace_toolbar_html
    assert 'data-tab="anexos"' in workspace_toolbar_html
    assert 'data-tab="mesa"' in workspace_toolbar_html
    assert "thread-breadcrumb" not in workspace_toolbar_html
    assert 'id="workspace-assistant-landing"' in workspace_assistant_html
    assert 'data-workspace-user-greeting-name' in workspace_assistant_html
    assert "Por onde começamos?" in workspace_assistant_html
    assert 'id="workspace-assistant-governance"' in workspace_assistant_html
    assert 'id="workspace-assistant-governance-title"' in workspace_assistant_html
    assert 'id="workspace-assistant-governance-detail"' in workspace_assistant_html
    assert 'data-component-slice="workspace-history"' in workspace_history_html
    assert "data-workspace-history-root" in workspace_history_html
    assert 'data-history-state="idle"' in workspace_history_html
    assert 'data-history-focus="idle"' in workspace_history_html
    assert "workspace-history-hero" in workspace_history_html
    assert 'id="chat-thread-search"' in workspace_history_html
    assert "data-workspace-history-search" in workspace_history_html
    assert 'data-chat-filter=' in workspace_history_html
    assert 'data-history-type-filter=' in workspace_history_html
    assert "data-history-empty" in workspace_history_html
    assert 'id="workspace-history-timeline"' in workspace_history_html
    assert "data-history-timeline" in workspace_history_html
    assert 'id="btn-workspace-history-continue"' in workspace_history_html
    assert "data-history-continue" in workspace_history_html
    assert 'id="workspace-history-source"' in workspace_history_html
    assert 'id="workspace-history-active-filter"' in workspace_history_html
    assert 'id="workspace-history-total"' in workspace_history_html
    assert 'id="workspace-history-governance"' in workspace_history_html
    assert 'id="workspace-history-governance-title"' in workspace_history_html
    assert 'id="workspace-history-governance-detail"' in workspace_history_html
    assert 'id="btn-workspace-history-reissue"' in workspace_history_html
    assert 'id="workspace-anexos-panel"' in workspace_record_html
    assert 'id="workspace-anexos-grid"' in workspace_record_html
    assert 'id="area-mensagens"' in workspace_conversation_html
    assert 'id="btn-ir-fim-chat"' in workspace_conversation_html
    assert 'id="workspace-mesa-stage"' in workspace_mesa_html
    assert 'id="btn-mesa-widget-toggle"' in workspace_rail_html
    assert 'data-mesa-toggle-label' in workspace_rail_html
    assert 'data-rail-toggle="progress"' in workspace_rail_html
    assert 'data-rail-toggle="context"' in workspace_rail_html
    assert 'data-rail-toggle="pendencias"' in workspace_rail_html
    assert 'data-rail-toggle="mesa"' in workspace_rail_html
    assert 'data-rail-toggle="pinned"' in workspace_rail_html
    assert 'id="workspace-activity-list"' in workspace_rail_html
    assert "inspetor-runtime-compat" not in workspace_html
    assert "rodape-entrada__compat" not in workspace_html
    assert 'id="mesa-widget-btn-anexo"' in mesa_widget_html
    assert 'id="mesa-widget-input-anexo"' in mesa_widget_html
    assert 'id="mesa-widget-preview-anexo"' in mesa_widget_html
    assert 'id="mesa-widget-resumo"' in mesa_widget_html
    assert 'id="mesa-widget-resumo-titulo"' in mesa_widget_html
    assert 'id="mesa-widget-chip-pendencias"' in mesa_widget_html
    assert 'id="portal-governance-summary"' in home_html
    assert 'id="portal-governance-summary-title"' in home_html
    assert 'id="portal-governance-summary-detail"' in home_html
    assert 'id="mesa-widget-chip-nao-lidas"' in mesa_widget_html
    assert 'id="bloco-gate-roteiro-template"' in gate_modal_html
    assert 'id="texto-gate-roteiro-template"' in gate_modal_html
    assert 'id="lista-gate-roteiro-template"' in gate_modal_html
    assert 'id="btn-editar-nome-inspecao"' in nova_inspecao_html
    assert 'id="preview-nome-inspecao"' in nova_inspecao_html
    assert 'id="input-nome-inspecao"' in nova_inspecao_html
    assert "modal-runtime-compat" not in nova_inspecao_html
    assert "data-preprompt=" in home_html
    assert 'id="banner-notificacao-engenharia"' in portal_main_html


def test_workspace_chat_oferece_atalho_de_reemissao_no_composer() -> None:
    raiz = Path(__file__).resolve().parents[1]
    chat_index_js = (raiz / "static" / "js" / "chat" / "chat_index_page.js").read_text(encoding="utf-8")
    ui_bindings_js = (raiz / "static" / "js" / "inspetor" / "ui_bindings.js").read_text(encoding="utf-8")
    workspace_states_css = (raiz / "static" / "css" / "inspetor" / "workspace_states.css").read_text(encoding="utf-8")

    assert 'data-suggestion-action="reissue"' in chat_index_js
    assert "composer_suggestion_reissue" in ui_bindings_js
    assert "redirecionarEntradaParaReemissaoWorkspace" in chat_index_js
    assert "composer-suggestion--warning" in workspace_states_css


def test_modo_foco_promove_portal_para_chat_livre_no_mobile() -> None:
    raiz = Path(__file__).resolve().parents[1]
    chat_index_js = (raiz / "static" / "js" / "chat" / "chat_index_page.js").read_text(encoding="utf-8")
    ui_js = (raiz / "static" / "js" / "shared" / "ui.js").read_text(encoding="utf-8")

    assert "tariel:focus-mode-changed" in ui_js
    assert 'document.body.classList.contains("modo-foco") && baseScreen === "assistant_landing"' in ui_js
    assert "modoFocoPodePromoverPortalParaChat" in chat_index_js
    assert "promoverPortalParaChatNoModoFoco" in chat_index_js
    assert 'origem: "focus_mode_toggle"' in chat_index_js


def test_superficies_cliente_mesa_inspetor_e_mobile_usam_copy_sem_jargao_interno() -> None:
    raiz = Path(__file__).resolve().parents[1]
    cliente_novo_html = (raiz / "templates" / "cliente" / "chat" / "_new_report.html").read_text(encoding="utf-8")
    painel_revisor_html = (raiz / "templates" / "painel_revisor.html").read_text(encoding="utf-8")
    portal_inspetor_html = (raiz / "templates" / "inspetor" / "_portal_home.html").read_text(encoding="utf-8")
    auth_mobile_routes = (raiz / "app" / "domains" / "chat" / "auth_mobile_routes.py").read_text(encoding="utf-8")

    assert "Abertura guiada de laudo" in cliente_novo_html
    assert "Modelo liberado" in cliente_novo_html
    assert "Sessão ativa em <strong>/revisao/painel</strong>" not in painel_revisor_html
    assert "fila da mesa" in painel_revisor_html
    assert "modelos pendente de publicação" not in painel_revisor_html.lower()
    assert "Retome laudos, inicie inspecoes e acompanhe os retornos da mesa" in portal_inspetor_html
    assert "Escolha um modelo liberado" in portal_inspetor_html
    assert "Empresa sem elegibilidade para esta confirmação assistida." in auth_mobile_routes
    assert "Tenant não elegível para confirmação orgânica." not in auth_mobile_routes


def test_modulo_modals_exporta_acoes_consumidas_pelo_boot_do_portal() -> None:
    raiz = Path(__file__).resolve().parents[1]
    modals_js = (raiz / "static" / "js" / "inspetor" / "modals.js").read_text(encoding="utf-8")

    assert "Object.assign(ctx.actions, {" in modals_js
    assert "aplicarContextoVisualWorkspace," in modals_js
    assert "criarContextoVisualPadrao," in modals_js
    assert "extrairContextoVisualWorkspace," in modals_js
    assert "atualizarPreviewNomeInspecao," in modals_js
    assert "toggleEdicaoNomeInspecao," in modals_js
    assert "modalNovaInspecaoEstaValida," in modals_js


def test_chat_usa_assets_modulares_e_service_worker_compartilhado() -> None:
    raiz = Path(__file__).resolve().parents[1]
    inspetor_base_html = (raiz / "templates" / "inspetor" / "base.html").read_text(encoding="utf-8")
    index_html = (raiz / "templates" / "index.html").read_text(encoding="utf-8")
    main_py = (raiz / "main.py").read_text(encoding="utf-8")
    http_setup_py = (raiz / "app" / "core" / "http_setup_support.py").read_text(encoding="utf-8")
    worker_compartilhado = (raiz / "static" / "js" / "shared" / "trabalhador_servico.js").read_text(encoding="utf-8")
    trecho_nucleo = worker_compartilhado.split("const ARQUIVOS_NUCLEO = [", 1)[1].split("];", 1)[0]

    assert not (raiz / "templates" / "base.html").exists()
    assert not (raiz / "static" / "css" / "shared" / "layout.css").exists()
    assert not (raiz / "static" / "css" / "chat" / "chat_base.css").exists()
    assert not (raiz / "static" / "css" / "chat" / "chat_mobile.css").exists()
    assert not (raiz / "static" / "css" / "chat" / "chat_index.css").exists()
    assert not (raiz / "static" / "css" / "inspetor" / "shell.css").exists()
    assert not (raiz / "static" / "css" / "inspetor" / "home.css").exists()
    assert not (raiz / "static" / "css" / "inspetor" / "modals.css").exists()
    assert not (raiz / "static" / "css" / "inspetor" / "profile.css").exists()
    assert not (raiz / "static" / "css" / "inspetor" / "mesa.css").exists()
    assert not (raiz / "static" / "css" / "inspetor" / "responsive.css").exists()
    assert not (raiz / "static" / "css" / "inspetor" / "workspace.css").exists()

    assert "/static/css/shared/global.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/shared/material-symbols.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/inspetor/tokens.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/shared/app_shell.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/inspetor/reboot.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/shared/official_visual_system.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/inspetor/workspace_chrome.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/inspetor/workspace_history.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/inspetor/workspace_rail.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/inspetor/workspace_states.css?v={{ v_app }}" in inspetor_base_html
    assert "/static/css/shared/layout.css?v={{ v_app }}" not in inspetor_base_html
    assert "/static/css/chat/chat_base.css?v={{ v_app }}" not in inspetor_base_html
    assert "/static/css/chat/chat_mobile.css?v={{ v_app }}" not in inspetor_base_html
    assert "/static/css/inspetor/shell.css?v={{ v_app }}" not in inspetor_base_html
    assert "/static/css/inspetor/home.css?v={{ v_app }}" not in inspetor_base_html
    assert "/static/css/inspetor/workspace.css?v={{ v_app }}" not in inspetor_base_html
    assert "/static/css/inspetor/modals.css?v={{ v_app }}" not in inspetor_base_html
    assert "/static/css/inspetor/profile.css?v={{ v_app }}" not in inspetor_base_html
    assert "/static/css/inspetor/mesa.css?v={{ v_app }}" not in inspetor_base_html
    assert "/static/css/inspetor/responsive.css?v={{ v_app }}" not in inspetor_base_html

    assert "/static/js/shared/api.js" in index_html
    assert "/static/js/shared/ui.js" in index_html
    assert "/static/js/shared/hardware.js" in index_html
    assert "/static/js/inspetor/modals.js" in index_html
    assert "/static/js/inspetor/pendencias.js" in index_html
    assert "/static/js/inspetor/mesa_widget.js" in index_html
    assert "/static/js/inspetor/notifications_sse.js" in index_html
    assert "/static/js/api.js" not in index_html
    assert "/static/js/ui.js" not in index_html
    assert "/static/js/hardware.js" not in index_html

    assert "registrar_rotas_operacionais(" in main_py
    assert 'dir_static / "js" / "shared" / "trabalhador_servico.js"' in http_setup_py
    assert "/static/js/shared/api.js" in worker_compartilhado
    assert "/static/js/shared/ui.js" in worker_compartilhado
    assert "/static/js/shared/hardware.js" in worker_compartilhado
    assert "/static/css/shared/global.css" in worker_compartilhado
    assert "/static/css/shared/material-symbols.css" in worker_compartilhado
    assert "/static/css/inspetor/tokens.css" in worker_compartilhado
    assert "/static/css/shared/app_shell.css" in worker_compartilhado
    assert "/static/css/inspetor/reboot.css" in worker_compartilhado
    assert "/static/css/shared/official_visual_system.css" in worker_compartilhado
    assert "/static/css/inspetor/workspace_chrome.css" in worker_compartilhado
    assert "/static/css/inspetor/workspace_history.css" in worker_compartilhado
    assert "/static/css/inspetor/workspace_rail.css" in worker_compartilhado
    assert "/static/css/inspetor/workspace_states.css" in worker_compartilhado
    assert "PIPELINE_RUNTIME_OFICIAL" in worker_compartilhado
    assert "cssRetired" not in worker_compartilhado
    assert "/static/css/shared/layout.css" not in worker_compartilhado
    assert "/static/css/chat/chat_base.css" not in worker_compartilhado
    assert "/static/css/chat/chat_mobile.css" not in worker_compartilhado
    assert "/static/css/inspetor/workspace.css" not in worker_compartilhado
    assert "/static/css/shared/layout.css" not in trecho_nucleo
    assert "/static/css/chat/chat_base.css" not in trecho_nucleo
    assert "/static/css/chat/chat_mobile.css" not in trecho_nucleo
    assert "/static/css/inspetor/shell.css" not in worker_compartilhado
    assert "/static/css/inspetor/home.css" not in worker_compartilhado
    assert "/static/css/inspetor/workspace.css" not in trecho_nucleo
    assert "/static/css/inspetor/modals.css" not in worker_compartilhado
    assert "/static/css/inspetor/profile.css" not in worker_compartilhado
    assert "/static/css/inspetor/mesa.css" not in worker_compartilhado
    assert "/static/css/inspetor/responsive.css" not in worker_compartilhado
    assert "/static/js/shared/app_shell.js" in worker_compartilhado
    assert "/static/js/shared/api-core.js" in worker_compartilhado
    assert "/static/js/shared/chat-render.js" in worker_compartilhado
    assert "/static/js/chat/chat_sidebar.js" not in worker_compartilhado
    assert "/static/js/inspetor/modals.js" in worker_compartilhado
    assert "/static/js/inspetor/mesa_widget.js" in worker_compartilhado
    assert "/static/js/chat/chat_index_page.js" in worker_compartilhado
    assert "/static/js/api.js" not in worker_compartilhado
    assert "/static/js/ui.js" not in worker_compartilhado
    assert "/static/js/hardware.js" not in worker_compartilhado
    assert "/static/css/chat.css" not in worker_compartilhado
    assert "/static/css/chat/chat_index.css" not in worker_compartilhado

    arquivos_legados = [
        raiz / "templates" / "base.html",
        raiz / "static" / "css" / "shared" / "layout.css",
        raiz / "static" / "css" / "chat" / "chat_base.css",
        raiz / "static" / "css" / "chat" / "chat_mobile.css",
        raiz / "static" / "css" / "chat" / "chat_index.css",
        raiz / "static" / "css" / "inspetor" / "shell.css",
        raiz / "static" / "css" / "inspetor" / "home.css",
        raiz / "static" / "css" / "inspetor" / "modals.css",
        raiz / "static" / "css" / "inspetor" / "profile.css",
        raiz / "static" / "css" / "inspetor" / "mesa.css",
        raiz / "static" / "css" / "inspetor" / "responsive.css",
        raiz / "static" / "css" / "inspetor" / "workspace.css",
        raiz / "static" / "css" / "global.css",
        raiz / "static" / "css" / "layout.css",
        raiz / "static" / "css" / "chat.css",
        raiz / "static" / "js" / "api.js",
        raiz / "static" / "js" / "ui.js",
        raiz / "static" / "js" / "hardware.js",
        raiz / "static" / "js" / "trabalhador_servico.js",
        raiz / "static" / "js" / "chat" / "chat_panel_legacy.js",
    ]
    assert all(not caminho.exists() for caminho in arquivos_legados)


def test_chat_css_responsivo_separa_nucleo_e_familia_inspetor() -> None:
    raiz = Path(__file__).resolve().parents[1]
    tokens_css = (raiz / "static" / "css" / "inspetor" / "tokens.css").read_text(encoding="utf-8")
    reboot_css = (raiz / "static" / "css" / "inspetor" / "reboot.css").read_text(encoding="utf-8")

    assert not (raiz / "static" / "css" / "chat" / "chat_mobile.css").exists()
    assert not (raiz / "static" / "css" / "chat" / "chat_index.css").exists()
    assert ".barra-status-inspecao {" in tokens_css
    assert "--font-sans: var(--font-base);" in tokens_css
    assert "--font-display: var(--font-heading);" in tokens_css
    assert "--surface-panel-radius: 18px;" in tokens_css
    assert ".technical-record-header {" in reboot_css
    assert ".modal-overlay {" in reboot_css
    assert ".painel-mesa-widget {" in reboot_css
    assert "font-family: var(--font-display);" in reboot_css
    assert "border-radius: var(--surface-panel-radius);" in reboot_css
    assert "@media (max-width: 1199px)" in reboot_css
    assert "#btn-finalizar-inspecao[hidden]" not in tokens_css

    assert ".modal-overlay {" in reboot_css


def test_global_css_preserva_tipografia_do_body() -> None:
    raiz = Path(__file__).resolve().parents[1]
    global_css = (raiz / "static" / "css" / "shared" / "global.css").read_text(encoding="utf-8")

    assert "body,\nbutton,\ninput,\ntextarea,\nselect {" not in global_css
    assert "button,\ninput,\ntextarea,\nselect {\n    font: inherit;" in global_css
    assert "body {\n    margin: 0;" in global_css
    assert "font-family: var(--font-base);" in global_css


def test_template_revisor_aponta_websocket_com_prefixo_revisao() -> None:
    raiz = Path(__file__).resolve().parents[1]
    painel_revisor_html = (raiz / "templates" / "painel_revisor.html").read_text(encoding="utf-8")
    assert "{% if perf_mode %}" in painel_revisor_html
    assert "/static/js/shared/api-core.js?v={{ v_app }}" in painel_revisor_html
    assert "/revisao/ws/whispers" in painel_revisor_html
    assert "/revisao/api/laudo/${state.laudoAtivoId}/pacote" in painel_revisor_html
    assert "/revisao/api/laudo/${state.laudoAtivoId}/pacote/exportar-pdf" in painel_revisor_html
    assert "/revisao/api/laudo/${alvo}/marcar-whispers-lidos" in painel_revisor_html
    assert "/revisao/api/laudo/${laudoId}/pendencias/${msgId}" in painel_revisor_html
    assert "/revisao/api/laudo/${state.laudoAtivoId}/responder-anexo" in painel_revisor_html
    assert "js-btn-pacote-json" in painel_revisor_html
    assert "js-btn-pacote-pdf" in painel_revisor_html
    assert 'id="modal-pacote"' in painel_revisor_html
    assert 'id="mesa-operacao-painel"' in painel_revisor_html
    assert 'id="mesa-operacao-conteudo"' in painel_revisor_html
    assert 'id="view-structured-document"' in painel_revisor_html
    assert "pendencias_resolvidas_recentes" in painel_revisor_html
    assert 'data-mesa-action="responder-item"' in painel_revisor_html
    assert 'data-mesa-action="alternar-pendencia"' in painel_revisor_html
    assert "js-indicador-whispers" in painel_revisor_html
    assert "js-indicador-pendencias" in painel_revisor_html
    assert "js-indicador-aprendizados" in painel_revisor_html
    assert "data-collaboration-summary=" in painel_revisor_html
    assert 'id="filtro-aprendizados"' in painel_revisor_html
    assert "anexo-mensagem-link" in painel_revisor_html
    assert 'id="btn-anexo-resposta"' in painel_revisor_html
    assert 'id="input-anexo-resposta"' in painel_revisor_html
    assert 'id="preview-resposta-anexo"' in painel_revisor_html


def test_ci_principal_roda_smoke_e2e_da_mesa_web() -> None:
    projeto = Path(__file__).resolve().parents[2]
    ci_yaml = (projeto / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "web-e2e-mesa:" in ci_yaml
    assert "Install Playwright browsers" in ci_yaml
    assert "test_e2e_admin_cliente_mesa_ignora_resposta_atrasada_ao_trocar_de_laudo" in ci_yaml
    assert "test_e2e_revisor_mesa_ignora_respostas_atrasadas_ao_trocar_de_laudo" in ci_yaml


def test_database_url_render_usa_driver_psycopg() -> None:
    assert banco_dados._normalizar_url_banco("postgres://user:pass@host:5432/app") == "postgresql+psycopg://user:pass@host:5432/app"
    assert banco_dados._normalizar_url_banco("postgresql://user:pass@host:5432/app") == "postgresql+psycopg://user:pass@host:5432/app"
    assert banco_dados._normalizar_url_banco("postgresql+psycopg://user:pass@host:5432/app") == "postgresql+psycopg://user:pass@host:5432/app"


def test_database_url_render_pode_trocar_driver_para_psycopg2(monkeypatch) -> None:
    monkeypatch.setenv("DB_SQLALCHEMY_DRIVER", "psycopg2")

    assert db_runtime._normalizar_url_banco("postgres://user:pass@host:5432/app") == "postgresql+psycopg2://user:pass@host:5432/app"
    assert db_runtime._normalizar_url_banco("postgresql://user:pass@host:5432/app") == "postgresql+psycopg2://user:pass@host:5432/app"


def test_database_url_render_pode_trocar_driver_para_pg8000(monkeypatch) -> None:
    monkeypatch.setenv("DB_SQLALCHEMY_DRIVER", "pg8000")

    assert db_runtime._normalizar_url_banco("postgres://user:pass@host:5432/app") == "postgresql+pg8000://user:pass@host:5432/app"
    assert db_runtime._normalizar_url_banco("postgresql://user:pass@host:5432/app") == "postgresql+pg8000://user:pass@host:5432/app"


def test_runtime_parametros_postgres_suporta_ssl_timeout_e_application_name(monkeypatch) -> None:
    monkeypatch.setattr(db_runtime, "_EM_PRODUCAO", True)
    monkeypatch.setenv("DB_SSLMODE", "require")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "10")
    monkeypatch.delenv("DB_APPLICATION_NAME", raising=False)

    assert db_runtime._parametros_runtime_postgres() == {
        "sslmode": "require",
        "connect_timeout": "10",
        "application_name": "tariel-web",
    }


def test_runtime_parametros_postgres_omite_campos_vazios(monkeypatch) -> None:
    monkeypatch.setattr(db_runtime, "_EM_PRODUCAO", False)
    monkeypatch.delenv("DB_SSLMODE", raising=False)
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "0")
    monkeypatch.delenv("DB_APPLICATION_NAME", raising=False)

    assert db_runtime._parametros_runtime_postgres() == {}


def test_runtime_connect_args_pg8000_suporta_ssl_timeout_e_application_name(monkeypatch) -> None:
    monkeypatch.setattr(db_runtime, "_EM_PRODUCAO", True)
    monkeypatch.setenv("DB_SQLALCHEMY_DRIVER", "pg8000")
    monkeypatch.setenv("DB_SSLMODE", "require")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "10")
    monkeypatch.delenv("DB_APPLICATION_NAME", raising=False)

    assert db_runtime._connect_args_postgres() == {
        "ssl_context": True,
        "timeout": 10,
        "application_name": "tariel-web",
    }


def test_runtime_aplica_parametros_postgres_na_url_preserva_query_customizada_e_sobrescreve_parametros_operacionais(monkeypatch) -> None:
    monkeypatch.setattr(db_runtime, "_EM_PRODUCAO", True)
    monkeypatch.setenv("DB_SSLMODE", "disable")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "10")
    monkeypatch.setenv("DB_APPLICATION_NAME", "tariel-web")

    url = db_runtime._aplicar_parametros_runtime_postgres(
        "postgresql+psycopg2://user:pass@host:5432/app?application_name=custom&sslmode=require&connect_timeout=2"
    )

    assert url == "postgresql+psycopg2://user:pass@host:5432/app?application_name=custom&sslmode=disable&connect_timeout=10"


def test_runtime_nao_injeta_parametros_libpq_na_url_quando_driver_e_pg8000(monkeypatch) -> None:
    monkeypatch.setattr(db_runtime, "_EM_PRODUCAO", True)
    monkeypatch.setenv("DB_SQLALCHEMY_DRIVER", "pg8000")
    monkeypatch.setenv("DB_SSLMODE", "require")
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "10")
    monkeypatch.setenv("DB_APPLICATION_NAME", "tariel-web")

    url = db_runtime._aplicar_parametros_runtime_postgres(
        "postgresql+pg8000://user:pass@host:5432/app?application_name=custom"
    )

    assert url == "postgresql+pg8000://user:pass@host:5432/app?application_name=custom"


def test_bootstrap_admin_producao_garante_primeiro_acesso_mesmo_com_outros_usuarios(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    banco_dados.Base.metadata.create_all(engine)
    sessao_teste = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    monkeypatch.setattr(banco_dados, "SessaoLocal", sessao_teste)
    monkeypatch.setattr(banco_dados, "_EM_PRODUCAO", True)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "admin@tariel.ia")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "Senha@123456")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_NOME", "Gabriel")
    monkeypatch.setenv("BOOTSTRAP_EMPRESA_NOME", "Tariel.ia")
    monkeypatch.setenv("BOOTSTRAP_EMPRESA_CNPJ", "11111111111111")

    with sessao_teste() as banco:
        empresa = banco_dados.Empresa(
            nome_fantasia="Cliente A",
            cnpj="22222222222222",
            plano_ativo=banco_dados.PlanoEmpresa.INICIAL.value,
        )
        banco.add(empresa)
        banco.flush()
        banco.add(
            banco_dados.Usuario(
                empresa_id=int(empresa.id),
                nome_completo="Inspetor Existente",
                email="inspetor@cliente.com",
                senha_hash=seguranca.criar_hash_senha("OutraSenha@123"),
                nivel_acesso=int(banco_dados.NivelAcesso.INSPETOR),
            )
        )
        banco.commit()

    banco_dados._bootstrap_admin_inicial_producao()

    with sessao_teste() as banco:
        admin = banco.query(banco_dados.Usuario).filter_by(email="admin@tariel.ia").one()
        assert admin.nome_completo == "Gabriel"
        assert admin.nivel_acesso == int(banco_dados.NivelAcesso.DIRETORIA)
        assert admin.empresa.cnpj == "11111111111111"
        assert admin.empresa.escopo_plataforma is True
        assert admin.portal_admin_autorizado is True
        assert admin.admin_identity_status == "active"
        assert admin.senha_temporaria_ativa is False
        assert seguranca.verificar_senha("Senha@123456", admin.senha_hash) is True


def test_bootstrap_catalogo_canonico_producao_importa_familias_ausentes(monkeypatch, tmp_path: Path) -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    banco_dados.Base.metadata.create_all(engine)
    sessao_teste = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    _write_canonical_catalog_fixture(
        tmp_path,
        family_keys=["nr13_inspecao_vaso_pressao", "nr35_inspecao_linha_de_vida"],
    )

    monkeypatch.setattr(banco_dados, "SessaoLocal", sessao_teste)
    monkeypatch.setattr(banco_dados, "_EM_PRODUCAO", True)
    monkeypatch.setattr(admin_services, "_repo_root_dir", lambda: tmp_path)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "admin@tariel.ia")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "Senha@123456")
    monkeypatch.setenv("BOOTSTRAP_CATALOGO_CANONICO", "1")

    banco_dados._bootstrap_admin_inicial_producao()
    banco_dados._bootstrap_catalogo_canonico_producao()
    banco_dados._bootstrap_catalogo_canonico_producao()

    with sessao_teste() as banco:
        admin = banco.query(banco_dados.Usuario).filter_by(email="admin@tariel.ia").one()
        familias = (
            banco.query(banco_dados.FamiliaLaudoCatalogo)
            .order_by(banco_dados.FamiliaLaudoCatalogo.family_key.asc())
            .all()
        )

        assert [item.family_key for item in familias] == [
            "nr13_inspecao_vaso_pressao",
            "nr35_inspecao_linha_de_vida",
        ]
        assert all(item.status_catalogo == "publicado" for item in familias)
        assert all(item.catalog_classification == "family" for item in familias)
        assert all(item.criado_por_id == admin.id for item in familias)


def test_bootstrap_catalogo_canonico_producao_nao_sobrescreve_familia_existente(
    monkeypatch,
    tmp_path: Path,
) -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    banco_dados.Base.metadata.create_all(engine)
    sessao_teste = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    _write_canonical_catalog_fixture(
        tmp_path,
        family_keys=["nr13_inspecao_vaso_pressao", "nr35_inspecao_linha_de_vida"],
    )

    monkeypatch.setattr(banco_dados, "SessaoLocal", sessao_teste)
    monkeypatch.setattr(banco_dados, "_EM_PRODUCAO", True)
    monkeypatch.setattr(admin_services, "_repo_root_dir", lambda: tmp_path)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "admin@tariel.ia")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "Senha@123456")
    monkeypatch.setenv("BOOTSTRAP_CATALOGO_CANONICO", "1")

    banco_dados._bootstrap_admin_inicial_producao()

    with sessao_teste() as banco:
        banco.add(
            banco_dados.FamiliaLaudoCatalogo(
                family_key="nr13_inspecao_vaso_pressao",
                nome_exibicao="NR13 custom",
                macro_categoria="NR13",
                status_catalogo="rascunho",
                technical_status="draft",
                catalog_classification="family",
                schema_version=7,
            )
        )
        banco.commit()

    banco_dados._bootstrap_catalogo_canonico_producao()

    with sessao_teste() as banco:
        familias = {
            item.family_key: item
            for item in banco.query(banco_dados.FamiliaLaudoCatalogo).all()
        }

        assert set(familias) == {"nr13_inspecao_vaso_pressao", "nr35_inspecao_linha_de_vida"}
        assert familias["nr13_inspecao_vaso_pressao"].nome_exibicao == "NR13 custom"
        assert familias["nr13_inspecao_vaso_pressao"].technical_status == "draft"
        assert familias["nr13_inspecao_vaso_pressao"].status_catalogo == "rascunho"
        assert familias["nr13_inspecao_vaso_pressao"].schema_version == 7
        assert familias["nr35_inspecao_linha_de_vida"].status_catalogo == "publicado"


def test_openapi_do_inspetor_endurece_request_bodies_criticos(cliente_main_isolado: TestClient) -> None:
    schema = cliente_main_isolado.get("/openapi.json").json()

    body_iniciar = schema["components"]["schemas"]["Body_api_iniciar_relatorio_app_api_laudo_iniciar_post"]
    variantes_tipo = body_iniciar["properties"]["tipo_template"]["anyOf"]
    variantes_alias = body_iniciar["properties"]["tipotemplate"]["anyOf"]
    assert {"type": "string", "maxLength": 0} in variantes_tipo
    assert {"type": "string", "maxLength": 0} in variantes_alias

    body_mesa_anexo = schema["components"]["schemas"]["Body_enviar_mensagem_mesa_laudo_com_anexo_app_api_laudo__laudo_id__mesa_anexo_post"]
    assert body_mesa_anexo["properties"]["arquivo"]["minLength"] == 1
    assert body_mesa_anexo["properties"]["arquivo"]["format"] == "binary"
    assert "contentMediaType" not in body_mesa_anexo["properties"]["arquivo"]

    op_mesa_anexo = schema["paths"]["/app/api/laudo/{laudo_id}/mesa/anexo"]["post"]
    laudo_param = next(param for param in op_mesa_anexo["parameters"] if param["name"] == "laudo_id")
    assert laudo_param["schema"]["minimum"] == 1


def test_openapi_do_inspetor_endurece_chat_e_perfil(cliente_main_isolado: TestClient) -> None:
    schema = cliente_main_isolado.get("/openapi.json").json()

    body_perfil = schema["components"]["schemas"]["DadosAtualizarPerfilUsuario"]
    assert body_perfil["properties"]["nome_completo"]["minLength"] == 3
    assert body_perfil["properties"]["email"]["pattern"] == r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

    body_perfil_foto = schema["components"]["schemas"]["Body_api_upload_foto_perfil_usuario_app_api_perfil_foto_post"]
    assert body_perfil_foto["properties"]["foto"]["minLength"] == 1
    assert body_perfil_foto["properties"]["foto"]["format"] == "binary"
    assert "contentMediaType" not in body_perfil_foto["properties"]["foto"]

    dados_chat = schema["components"]["schemas"]["DadosChat"]
    assert len(dados_chat["anyOf"]) == 3
    assert dados_chat["anyOf"][0]["properties"]["mensagem"]["minLength"] == 1
    assert dados_chat["anyOf"][1]["properties"]["dados_imagem"]["minLength"] == 1
    assert dados_chat["anyOf"][2]["properties"]["texto_documento"]["minLength"] == 1

    op_perfil = schema["paths"]["/app/api/perfil"]["put"]
    assert "requestBody" in op_perfil
    assert "400" in op_perfil["responses"]
    assert "409" in op_perfil["responses"]

    op_perfil_foto = schema["paths"]["/app/api/perfil/foto"]["post"]
    assert "400" in op_perfil_foto["responses"]
    assert "413" in op_perfil_foto["responses"]
    assert "415" in op_perfil_foto["responses"]

    op_chat = schema["paths"]["/app/api/chat"]["post"]
    assert "400" in op_chat["responses"]
    assert "application/json" in op_chat["responses"]["200"]["content"]
    assert "text/event-stream" in op_chat["responses"]["200"]["content"]

    body_upload_doc = schema["components"]["schemas"]["Body_rota_upload_doc_app_api_upload_doc_post"]
    assert body_upload_doc["properties"]["arquivo"]["minLength"] == 1
    assert body_upload_doc["properties"]["arquivo"]["format"] == "binary"
    assert "contentMediaType" not in body_upload_doc["properties"]["arquivo"]

    op_upload_doc = schema["paths"]["/app/api/upload_doc"]["post"]
    assert "400" in op_upload_doc["responses"]
    assert "413" in op_upload_doc["responses"]
    assert "415" in op_upload_doc["responses"]
    assert "422" in op_upload_doc["responses"]
    assert "501" in op_upload_doc["responses"]

    op_pdf = schema["paths"]["/app/api/gerar_pdf"]["post"]
    assert "application/pdf" in op_pdf["responses"]["200"]["content"]
    assert "500" in op_pdf["responses"]

    op_sse = schema["paths"]["/app/api/notificacoes/sse"]["get"]
    assert "text/event-stream" in op_sse["responses"]["200"]["content"]


def test_openapi_expoe_endpoints_mobile_do_inspetor(cliente_main_isolado: TestClient) -> None:
    schema = cliente_main_isolado.get("/openapi.json").json()

    paths = schema["paths"]
    assert "/app/api/mobile/auth/login" in paths
    assert "/app/api/mobile/bootstrap" in paths
    assert "/app/api/mobile/laudos" in paths
    assert "/app/api/mobile/account/profile" in paths
    assert "/app/api/mobile/account/password" in paths
    assert "/app/api/mobile/account/photo" in paths
    assert "/app/api/mobile/account/settings" in paths
    assert "/app/api/mobile/push/register" in paths
    assert "/app/api/mobile/support/report" in paths
    assert "/app/api/mobile/auth/logout" in paths
    assert "requestBody" in paths["/app/api/mobile/auth/login"]["post"]
    assert "requestBody" in paths["/app/api/mobile/account/profile"]["put"]
    assert "requestBody" in paths["/app/api/mobile/account/password"]["post"]
    assert "requestBody" in paths["/app/api/mobile/account/photo"]["post"]
    assert "requestBody" in paths["/app/api/mobile/account/settings"]["put"]
    assert "requestBody" in paths["/app/api/mobile/push/register"]["post"]
    assert "requestBody" in paths["/app/api/mobile/support/report"]["post"]

    settings_body_ref = paths["/app/api/mobile/account/settings"]["put"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    settings_body_name = settings_body_ref.rsplit("/", maxsplit=1)[-1]
    settings_body_schema = schema["components"]["schemas"][settings_body_name]
    assert "experiencia_ia" in settings_body_schema["properties"]


def test_base_mobile_do_inspetor_foi_isolada_em_android() -> None:
    raiz = Path(__file__).resolve().parents[1]
    android_raiz = raiz.parent / "android"
    package_mobile = json.loads((android_raiz / "package.json").read_text(encoding="utf-8"))
    app_mobile = json.loads((android_raiz / "app.json").read_text(encoding="utf-8"))
    readme_mobile = (android_raiz / "README.md").read_text(encoding="utf-8")
    env_mobile = (android_raiz / ".env.example").read_text(encoding="utf-8")

    assert package_mobile["name"] == "tariel-inspetor-mobile"
    assert package_mobile["scripts"]["typecheck"] == "tsc --noEmit"
    assert "expo-image-picker" in package_mobile["dependencies"]
    assert "expo-document-picker" in package_mobile["dependencies"]
    assert app_mobile["expo"]["name"] == "Tariel Inspetor"
    assert app_mobile["expo"]["slug"] == "tariel-inspetor"
    assert app_mobile["expo"]["android"]["package"] == "com.tarielia.inspetor"
    assert "expo-document-picker" in app_mobile["expo"]["plugins"]
    assert any(isinstance(item, list) and item[0] == "expo-image-picker" for item in app_mobile["expo"]["plugins"])
    assert (android_raiz / "src" / "features" / "InspectorMobileApp.tsx").exists()
    assert "login mobile do inspetor via token bearer" in readme_mobile
    assert "home mobile mais estruturada, com cards rápidos de contexto para fluxo, conexão, laudos e fila local" in readme_mobile
    assert "pós-login refinado com chips de contexto, seção de laudos mais legível e composer com hierarquia visual própria" in readme_mobile
    assert "camera, imagem e documento direto no composer do chat" in readme_mobile
    assert "lista compacta de laudos recentes com troca rápida no header" in readme_mobile
    assert "preview e abertura autenticada de anexos no chat e na mesa" in readme_mobile
    assert "fila local offline para segurar texto, imagem e documento sem perder o fluxo" in readme_mobile
    assert "retomada de pendências offline direto no composer do chat ou da mesa" in readme_mobile
    assert "painel completo da fila offline para revisar, retomar e limpar pendências em campo" in readme_mobile
    assert "reenvio individual de cada pendência offline quando a conexão voltar" in readme_mobile
    assert "filtros e diagnóstico rápido da fila offline para separar Chat/Mesa e identificar falhas de reenvio" in readme_mobile
    assert "backoff automático por pendência para evitar reenvio agressivo quando a rede volta instável" in readme_mobile
    assert "priorização visual da fila offline para destacar falhas e envios prontos primeiro" in readme_mobile
    assert "central de atividade do inspetor com badge, feed persistido e monitoramento leve da mesa/status" in readme_mobile
    assert "cache de leitura offline para reabrir bootstrap, laudos, chat e mesa sem derrubar a sessão" in readme_mobile
    assert "rascunhos persistidos por laudo no chat e na mesa para retomar de onde parou" in readme_mobile
    assert "rascunhos persistidos de imagem e documento para não perder anexos preparados" in readme_mobile
    assert "expo-file-system" in package_mobile["dependencies"]
    assert "expo-sharing" in package_mobile["dependencies"]
    assert "EXPO_PUBLIC_API_BASE_URL=" in env_mobile


def test_openapi_do_revisor_endurece_templates_laudo_para_schemathesis(
    monkeypatch,
    cliente_main_isolado: TestClient,
) -> None:
    monkeypatch.setenv("SCHEMATHESIS_TEST_HINTS", "1")
    main.app.openapi_schema = None
    try:
        schema = cliente_main_isolado.get("/openapi.json").json()
    finally:
        main.app.openapi_schema = None

    body_asset = schema["components"]["schemas"]["Body_upload_asset_template_editor_laudo_revisao_api_templates_laudo_editor__template_id__assets_post"]
    assert body_asset["properties"]["arquivo"]["minLength"] == 1
    assert body_asset["properties"]["arquivo"]["format"] == "binary"
    assert "contentMediaType" not in body_asset["properties"]["arquivo"]

    body_upload = schema["components"]["schemas"]["Body_upload_template_laudo_revisao_api_templates_laudo_upload_post"]
    assert body_upload["properties"]["arquivo_base"]["minLength"] == 1
    assert body_upload["properties"]["arquivo_base"]["format"] == "binary"
    assert body_upload["properties"]["nome"]["minLength"] == 1
    assert body_upload["properties"]["codigo_template"]["minLength"] == 1

    dados_preview = schema["components"]["schemas"]["DadosPreviewTemplateLaudo"]
    assert dados_preview["properties"]["laudo_id"]["enum"] == [1]
    assert dados_preview["properties"]["dados_formulario"]["minProperties"] == 1

    op_editor = schema["paths"]["/revisao/api/templates-laudo/editor"]["post"]
    assert "201" in op_editor["responses"]
    assert "409" in op_editor["responses"]

    op_preview_editor = schema["paths"]["/revisao/api/templates-laudo/editor/{template_id}/preview"]["post"]
    assert "application/pdf" in op_preview_editor["responses"]["200"]["content"]

    op_arquivo_base = schema["paths"]["/revisao/api/templates-laudo/{template_id}/arquivo-base"]["get"]
    assert "application/pdf" in op_arquivo_base["responses"]["200"]["content"]

    op_editor_asset = schema["paths"]["/revisao/api/templates-laudo/editor/{template_id}/assets/{asset_id}"]["get"]
    template_param = next(param for param in op_editor_asset["parameters"] if param["name"] == "template_id")
    asset_param = next(param for param in op_editor_asset["parameters"] if param["name"] == "asset_id")
    assert template_param["schema"]["enum"] == [2]
    assert asset_param["schema"]["enum"] == ["seed-asset-logo"]
    assert "image/png" in op_editor_asset["responses"]["200"]["content"]


def test_openapi_expoe_so_rotas_de_api_e_operacionais(cliente_main_isolado: TestClient) -> None:
    schema = cliente_main_isolado.get("/openapi.json").json()

    paths = schema["paths"]
    assert "/app/api/chat" in paths
    assert "/cliente/api/empresa/resumo" in paths
    assert "/revisao/api/templates-laudo" in paths
    assert "/admin/api/metricas-grafico" in paths
    assert "/app/login" not in paths
    assert "/app/" not in paths
    assert "/cliente/painel" not in paths
    assert "/cliente/chat" not in paths
    assert "/cliente/mesa" not in paths
    assert "/revisao/login" not in paths
    assert "/admin/painel" not in paths


def test_run_schemathesis_carrega_hooks_binarios() -> None:
    raiz = Path(__file__).resolve().parents[1]
    script = (raiz / "scripts" / "run_schemathesis.ps1").read_text(encoding="utf-8")
    hooks = (raiz / "scripts" / "schemathesis_hooks.py").read_text(encoding="utf-8")
    common = (raiz / "scripts" / "test_common.ps1").read_text(encoding="utf-8")

    assert "SCHEMATHESIS_HOOKS" in script
    assert "scripts\\schemathesis_hooks.py" in script
    assert 'ValidateSet("publico", "inspetor", "revisor", "cliente", "admin")' in script
    assert 'ValidateSet("inspetor", "revisor", "cliente", "admin")' in common
    assert '@schemathesis.deserializer("application/pdf")' in hooks
    assert '@schemathesis.deserializer("application/octet-stream")' in hooks
    assert '@schemathesis.deserializer("image/png", "image/jpeg", "image/webp")' in hooks


def test_templates_cliente_explicitam_abas_e_formularios_principais() -> None:
    raiz = Path(__file__).resolve().parents[1]
    login_cliente = (raiz / "templates" / "login_cliente.html").read_text(encoding="utf-8")
    portal_cliente_main = (raiz / "templates" / "cliente_portal.html").read_text(encoding="utf-8")
    portal_cliente_admin_content = (raiz / "templates" / "cliente" / "painel" / "_content.html").read_text(encoding="utf-8")
    portal_cliente_admin_overview = (raiz / "templates" / "cliente" / "painel" / "_overview.html").read_text(encoding="utf-8")
    portal_cliente_partials = sorted((raiz / "templates" / "cliente").rglob("*.html"))
    portal_cliente = "\n".join(
        [portal_cliente_main, *(path.read_text(encoding="utf-8") for path in portal_cliente_partials)]
    )
    portal_runtime_js = (raiz / "static" / "js" / "cliente" / "portal_runtime.js").read_text(encoding="utf-8")
    portal_priorities_js = (raiz / "static" / "js" / "cliente" / "portal_priorities.js").read_text(encoding="utf-8")
    portal_admin_surface_js = (raiz / "static" / "js" / "cliente" / "portal_admin_surface.js").read_text(encoding="utf-8")
    painel_page_js = (raiz / "static" / "js" / "cliente" / "painel_page.js").read_text(encoding="utf-8")
    portal_admin_js = (raiz / "static" / "js" / "cliente" / "portal_admin.js").read_text(encoding="utf-8")
    portal_chat_surface_js = (raiz / "static" / "js" / "cliente" / "portal_chat_surface.js").read_text(encoding="utf-8")
    chat_page_js = (raiz / "static" / "js" / "cliente" / "chat_page.js").read_text(encoding="utf-8")
    portal_chat_js = (raiz / "static" / "js" / "cliente" / "portal_chat.js").read_text(encoding="utf-8")
    portal_mesa_surface_js = (raiz / "static" / "js" / "cliente" / "portal_mesa_surface.js").read_text(encoding="utf-8")
    mesa_page_js = (raiz / "static" / "js" / "cliente" / "mesa_page.js").read_text(encoding="utf-8")
    portal_mesa_js = (raiz / "static" / "js" / "cliente" / "portal_mesa.js").read_text(encoding="utf-8")
    portal_shared_helpers_js = (raiz / "static" / "js" / "cliente" / "portal_shared_helpers.js").read_text(encoding="utf-8")
    portal_shell_js = (raiz / "static" / "js" / "cliente" / "portal_shell.js").read_text(encoding="utf-8")
    portal_bindings_js = (raiz / "static" / "js" / "cliente" / "portal_bindings.js").read_text(encoding="utf-8")
    portal_js = (raiz / "static" / "js" / "cliente" / "portal.js").read_text(encoding="utf-8")
    portal_foundation_css = (raiz / "static" / "css" / "cliente" / "portal_foundation.css").read_text(encoding="utf-8")
    portal_components_css = (raiz / "static" / "css" / "cliente" / "portal_components.css").read_text(encoding="utf-8")
    portal_workspace_css = (raiz / "static" / "css" / "cliente" / "portal_workspace.css").read_text(encoding="utf-8")
    portal_admin_surface_css = (raiz / "static" / "css" / "cliente" / "portal_admin_surface.css").read_text(encoding="utf-8")
    portal_chat_surface_css = (raiz / "static" / "css" / "cliente" / "portal_chat_surface.css").read_text(encoding="utf-8")
    portal_mesa_surface_css = (raiz / "static" / "css" / "cliente" / "portal_mesa_surface.css").read_text(encoding="utf-8")
    portal_admin_theme_css = (raiz / "static" / "css" / "cliente" / "portal_admin_theme.css").read_text(encoding="utf-8")
    portal_admin_bundle_js = portal_admin_surface_js + "\n" + painel_page_js + "\n" + portal_admin_js
    portal_chat_bundle_js = portal_chat_surface_js + "\n" + chat_page_js + "\n" + portal_chat_js
    portal_mesa_bundle_js = portal_mesa_surface_js + "\n" + mesa_page_js + "\n" + portal_mesa_js

    assert 'action="/cliente/login"' in login_cliente
    assert "Portal da empresa" in login_cliente
    assert "/static/css/cliente/cliente_auth.css?v={{ v_app }}" in login_cliente
    assert "/static/css/shared/auth_shell.css?v={{ v_app }}" not in login_cliente
    assert "Continuar com Google" not in login_cliente
    assert "Continuar com Microsoft" not in login_cliente
    assert "Esqueceu a senha?" not in login_cliente
    assert "/admin/login" not in login_cliente
    assert "/revisao/login" in login_cliente

    assert 'class="cliente-tabs-shell"' in portal_cliente_main
    assert '{% include "cliente/_primary_tabs.html" %}' in portal_cliente_main
    assert '{% include "cliente/painel/_content.html" %}' in portal_cliente_main
    assert '{% include "cliente/chat/_content.html" %}' in portal_cliente_main
    assert '{% include "cliente/mesa/_content.html" %}' in portal_cliente_main
    assert '{% include "cliente/_scripts.html" %}' in portal_cliente_main
    assert '{% include "cliente/_shell_header.html" %}' in portal_cliente
    assert '{% include "cliente/_shell_header.html" %}' not in portal_cliente_admin_content
    assert '{% include "cliente/_shell_header.html" %}' in portal_cliente_admin_overview
    assert 'class="admin-surface-layout"' in portal_cliente
    assert 'class="admin-content-header"' in portal_cliente
    assert '{% include "cliente/painel/_overview.html" %}' in portal_cliente
    assert '{% include "cliente/painel/_capacity.html" %}' in portal_cliente
    assert '{% include "cliente/painel/_team.html" %}' in portal_cliente
    assert '{% include "cliente/painel/_support.html" %}' in portal_cliente
    assert '{% include "cliente/chat/_overview.html" %}' in portal_cliente
    assert '{% include "cliente/chat/_new_report.html" %}' in portal_cliente
    assert '{% include "cliente/chat/_queue.html" %}' in portal_cliente
    assert '{% include "cliente/chat/_case.html" %}' in portal_cliente
    assert '{% include "cliente/mesa/_overview.html" %}' in portal_cliente
    assert '{% include "cliente/mesa/_queue.html" %}' in portal_cliente
    assert '{% include "cliente/mesa/_pending.html" %}' in portal_cliente
    assert '{% include "cliente/mesa/_reply.html" %}' in portal_cliente
    assert 'id="hero-prioridades"' in portal_cliente
    assert 'id="tab-admin"' in portal_cliente
    assert 'id="tab-chat"' in portal_cliente
    assert 'id="tab-mesa"' in portal_cliente
    assert 'aria-label="Navegação principal do portal da empresa"' in portal_cliente
    assert "Administrador da empresa" in portal_cliente
    assert 'id="admin-resumo-geral"' in portal_cliente
    assert 'id="admin-auditoria-lista"' in portal_cliente
    assert 'id="admin-credencial-painel"' in portal_cliente
    assert 'id="btn-admin-credencial-copiar"' in portal_cliente
    assert 'id="btn-admin-credencial-ocultar"' in portal_cliente
    assert 'id="admin-onboarding-resumo"' in portal_cliente
    assert 'id="admin-onboarding-lista"' in portal_cliente
    assert 'id="admin-saude-resumo"' in portal_cliente
    assert 'id="admin-saude-historico"' in portal_cliente
    assert 'id="empresa-alerta-capacidade"' in portal_cliente
    assert 'id="plano-impacto-preview"' in portal_cliente
    assert 'id="admin-planos-historico"' in portal_cliente
    assert 'id="form-plano"' in portal_cliente
    assert 'id="btn-plano-registrar"' in portal_cliente
    assert 'id="form-usuario"' in portal_cliente
    assert 'id="usuario-capacidade-nota"' in portal_cliente
    assert 'id="btn-usuario-criar"' in portal_cliente
    assert '<option value="admin_cliente">' not in portal_cliente
    assert 'id="form-chat-laudo"' in portal_cliente
    assert 'id="chat-capacidade-nota"' in portal_cliente
    assert 'id="btn-chat-laudo-criar"' in portal_cliente
    assert 'id="form-chat-msg"' in portal_cliente
    assert 'id="btn-chat-upload-doc"' in portal_cliente
    assert 'id="chat-upload-doc"' in portal_cliente
    assert 'id="chat-upload-status"' in portal_cliente
    assert 'id="form-mesa-msg"' in portal_cliente
    assert 'id="usuarios-busca"' in portal_cliente
    assert 'id="chat-busca-laudos"' in portal_cliente
    assert 'id="mesa-busca-laudos"' in portal_cliente
    assert 'id="chat-resumo-geral"' in portal_cliente
    assert 'id="chat-triagem"' in portal_cliente
    assert 'id="chat-movimentos"' in portal_cliente
    assert 'id="chat-alertas-operacionais"' in portal_cliente
    assert 'id="mesa-resumo-geral"' in portal_cliente
    assert 'id="mesa-triagem"' in portal_cliente
    assert 'id="mesa-movimentos"' in portal_cliente
    assert 'id="mesa-alertas-operacionais"' in portal_cliente
    assert 'id="chat-contexto"' in portal_cliente
    assert 'id="mesa-contexto"' in portal_cliente
    assert 'data-admin-stage="overview"' in portal_cliente
    assert 'data-admin-stage="capacity"' in portal_cliente
    assert 'data-admin-stage="team"' in portal_cliente
    assert 'data-admin-stage="support"' in portal_cliente
    assert 'data-admin-section-tab="overview"' in portal_cliente
    assert 'data-admin-section-tab="capacity"' in portal_cliente
    assert 'data-admin-section-tab="team"' in portal_cliente
    assert 'data-admin-section-tab="support"' in portal_cliente
    assert 'data-admin-panel="overview"' in portal_cliente
    assert 'data-admin-panel="capacity"' in portal_cliente
    assert 'data-admin-panel="team"' in portal_cliente
    assert 'data-admin-panel="support"' in portal_cliente
    assert 'data-surface-nav="admin"' in portal_cliente
    assert 'id="admin-section-summary-title"' in portal_cliente
    assert 'id="admin-section-summary-meta"' in portal_cliente
    assert 'id="admin-section-count-overview"' in portal_cliente
    assert 'id="admin-section-count-capacity"' in portal_cliente
    assert 'id="admin-section-count-team"' in portal_cliente
    assert 'id="admin-section-count-support"' in portal_cliente
    assert 'data-chat-panel="overview"' in portal_cliente
    assert 'data-chat-panel="new"' in portal_cliente
    assert 'data-chat-panel="queue"' in portal_cliente
    assert 'data-chat-panel="case"' in portal_cliente
    assert 'data-chat-section-tab="overview"' in portal_cliente
    assert 'data-chat-section-tab="new"' in portal_cliente
    assert 'data-chat-section-tab="queue"' in portal_cliente
    assert 'data-chat-section-tab="case"' in portal_cliente
    assert 'data-surface-nav="chat"' in portal_cliente
    assert 'id="chat-section-summary-title"' in portal_cliente
    assert 'id="chat-section-summary-meta"' in portal_cliente
    assert 'id="chat-section-count-overview"' in portal_cliente
    assert 'id="chat-section-count-new"' in portal_cliente
    assert 'id="chat-section-count-queue"' in portal_cliente
    assert 'id="chat-section-count-case"' in portal_cliente
    assert 'data-mesa-panel="overview"' in portal_cliente
    assert 'data-mesa-panel="queue"' in portal_cliente
    assert 'data-mesa-panel="pending"' in portal_cliente
    assert 'data-mesa-panel="reply"' in portal_cliente
    assert 'data-mesa-section-tab="overview"' in portal_cliente
    assert 'data-mesa-section-tab="queue"' in portal_cliente
    assert 'data-mesa-section-tab="pending"' in portal_cliente
    assert 'data-mesa-section-tab="reply"' in portal_cliente
    assert 'data-surface-nav="mesa"' in portal_cliente
    assert 'id="mesa-section-summary-title"' in portal_cliente
    assert 'id="mesa-section-summary-meta"' in portal_cliente
    assert 'id="mesa-section-count-overview"' in portal_cliente
    assert 'id="mesa-section-count-queue"' in portal_cliente
    assert 'id="mesa-section-count-pending"' in portal_cliente
    assert 'id="mesa-section-count-reply"' in portal_cliente
    assert 'data-stage-state="idle"' in portal_cliente
    assert 'data-cliente-tab-inicial="{{ cliente_tab_inicial | default(\'admin\') | e }}"' in portal_cliente
    assert 'data-cliente-chat-section-inicial="{{ cliente_chat_section_inicial | default(\'overview\') | e }}"' in portal_cliente
    assert 'data-cliente-mesa-section-inicial="{{ cliente_mesa_section_inicial | default(\'overview\') | e }}"' in portal_cliente
    assert 'data-cliente-route-admin="{{ cliente_surface_routes.admin | default(\'/cliente/painel\') | e }}"' in portal_cliente
    assert 'data-cliente-route-chat="{{ cliente_surface_routes.chat | default(\'/cliente/chat\') | e }}"' in portal_cliente
    assert 'data-cliente-route-mesa="{{ cliente_surface_routes.mesa | default(\'/cliente/mesa\') | e }}"' in portal_cliente
    assert "/static/css/admin/admin_icons.css" in portal_cliente
    assert "/static/css/cliente/portal_foundation.css?v={{ v_app }}" in portal_cliente
    assert "/static/css/cliente/portal_components.css?v={{ v_app }}" in portal_cliente
    assert "/static/css/cliente/portal.css?v={{ v_app }}" in portal_cliente
    assert "/static/css/cliente/portal_workspace.css?v={{ v_app }}" in portal_cliente
    assert "/static/css/cliente/portal_admin_surface.css?v={{ v_app }}" in portal_cliente
    assert "/static/css/cliente/portal_chat_surface.css?v={{ v_app }}" in portal_cliente
    assert "/static/css/cliente/portal_mesa_surface.css?v={{ v_app }}" in portal_cliente
    assert "/static/css/cliente/portal_admin_theme.css?v={{ v_app }}" in portal_cliente
    assert 'class="panel panel--admin{% if (cliente_tab_inicial | default(\'admin\')) == \'admin\' %} active{% endif %}"' in portal_cliente
    assert 'class="panel panel--chat{% if (cliente_tab_inicial | default(\'admin\')) == \'chat\' %} active{% endif %}"' in portal_cliente
    assert 'class="panel panel--mesa{% if (cliente_tab_inicial | default(\'admin\')) == \'mesa\' %} active{% endif %}"' in portal_cliente
    assert 'class="surface-tabs"' in portal_cliente
    assert 'class="surface-stage-panels"' in portal_cliente
    assert "{% if perf_mode %}" in portal_cliente
    assert "/static/js/shared/api-core.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_admin_surface.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_chat_surface.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_mesa_surface.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/painel_page.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/chat_page.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/mesa_page.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_runtime.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_priorities.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_admin.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_chat.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_mesa.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_shared_helpers.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_shell.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal_bindings.js?v={{ v_app }}" in portal_cliente
    assert "/static/js/cliente/portal.js?v={{ v_app }}" in portal_cliente
    assert 'data-portal-contract="cliente"' in portal_cliente
    assert 'data-portal-module="runtime"' in portal_cliente
    assert 'data-portal-module="priorities"' in portal_cliente
    assert 'data-portal-module="admin"' in portal_cliente
    assert 'data-portal-module="chat"' in portal_cliente
    assert 'data-portal-module="mesa"' in portal_cliente
    assert 'data-portal-module="sharedHelpers"' in portal_cliente
    assert 'data-portal-module="shell"' in portal_cliente
    assert 'data-portal-module="bindings"' in portal_cliente
    assert 'data-portal-module="portal"' in portal_cliente
    portal_scripts = [
        "/static/js/cliente/portal_runtime.js?v={{ v_app }}",
        "/static/js/cliente/portal_priorities.js?v={{ v_app }}",
        "/static/js/cliente/portal_admin.js?v={{ v_app }}",
        "/static/js/cliente/portal_chat.js?v={{ v_app }}",
        "/static/js/cliente/portal_mesa.js?v={{ v_app }}",
        "/static/js/cliente/portal_shared_helpers.js?v={{ v_app }}",
        "/static/js/cliente/portal_shell.js?v={{ v_app }}",
        "/static/js/cliente/portal_bindings.js?v={{ v_app }}",
        "/static/js/cliente/portal.js?v={{ v_app }}",
    ]
    for anterior, posterior in zip(portal_scripts, portal_scripts[1:], strict=False):
        assert portal_cliente.index(anterior) < portal_cliente.index(posterior)
    assert "window.TarielClientePortalRuntime" in portal_runtime_js
    assert "window.TarielClientePortalPriorities" in portal_priorities_js
    assert "window.TarielClientePortalAdminSurface" in portal_admin_surface_js
    assert 'aria-current", ativa ? "page" : "false"' in portal_admin_surface_js
    assert "window.TarielClientePainelPage" in painel_page_js
    assert "window.TarielClientePortalAdmin" in portal_admin_js
    assert "window.TarielClientePortalChatSurface" in portal_chat_surface_js
    assert 'aria-current", ativa ? "page" : "false"' in portal_chat_surface_js
    assert "window.TarielClienteChatPage" in chat_page_js
    assert "window.TarielClientePortalChat" in portal_chat_js
    assert "window.TarielClientePortalMesaSurface" in portal_mesa_surface_js
    assert 'aria-current", ativa ? "page" : "false"' in portal_mesa_surface_js
    assert "window.TarielClienteMesaPage" in mesa_page_js
    assert "window.TarielClientePortalMesa" in portal_mesa_js
    assert "window.TarielClientePortalSharedHelpers" in portal_shared_helpers_js
    assert "window.TarielClientePortalShell" in portal_shell_js
    assert "window.TarielClientePortalBindings" in portal_bindings_js
    assert "function definirTab(nome, persistir = true, options = {})" in portal_runtime_js
    assert "function sincronizarTabComUrl({ replace = false } = {})" in portal_runtime_js
    assert "function tabAtualDaUrl()" in portal_runtime_js
    assert 'const INITIAL_TAB = ["admin", "chat", "mesa"].includes(bodyDataset.clienteTabInicial)' in portal_js
    assert "const ROUTE_MAP = Object.freeze({" in portal_js
    assert "const PORTAL_BOOT_CONTRACT" in portal_js
    assert "const PORTAL_BRIDGE_SPECS" in portal_js
    assert "PORTAL_BOOT_STATUS_READY" in portal_js
    assert '__TARIEL_CLIENTE_PORTAL_WIRED__' in portal_js
    assert "missing-required-bridges" in portal_js
    assert "missing-optional-globals" in portal_js
    assert "template-order-mismatch" in portal_js
    assert 'script[data-portal-contract="cliente"][data-portal-module]' in portal_js
    assert "construirPrioridadesPortal" in portal_priorities_js
    assert "filtrarLaudosChat" in portal_priorities_js
    assert "filtrarLaudosMesa" in portal_priorities_js
    assert "plano_sugerido" in portal_shared_helpers_js
    assert "tenant_admin_projection" in portal_shell_js
    assert "tenant_admin_projection" in portal_admin_bundle_js
    assert "visibility_policy" in portal_admin_bundle_js
    assert "usuario-capacidade-nota" in portal_admin_bundle_js
    assert "admin-planos-historico" in portal_admin_bundle_js
    assert "/cliente/api/bootstrap?surface=" in portal_shell_js
    assert "chat-alertas-operacionais" in portal_shell_js
    assert "admin-saude-resumo" in portal_admin_bundle_js
    assert "saude_operacional" in portal_admin_bundle_js
    assert "/cliente/api/empresa/plano/interesse" in portal_admin_bundle_js
    assert "requestIdleCallback" in portal_admin_surface_js
    assert "abrirSecaoAdmin" in portal_admin_bundle_js
    assert "resolverSecaoAdminPorTarget" in portal_admin_bundle_js
    assert "renderCredencialTemporaria" in painel_page_js
    assert "adminCredencialTemporaria" in painel_page_js
    assert "btn-admin-credencial-copiar" in painel_page_js
    assert "abrirSecaoChat" in portal_chat_bundle_js
    assert "resolverSecaoChatPorTarget" in portal_chat_bundle_js
    assert "abrirSecaoMesa" in portal_mesa_bundle_js
    assert "resolverSecaoMesaPorTarget" in portal_mesa_bundle_js
    assert "preparar-upgrade" in portal_bindings_js
    assert "renderCentralPrioridades" in portal_shell_js
    assert "await bootstrapPortal({ surface: tab, carregarDetalhes: true, force: false })" in portal_bindings_js
    assert "abrir-prioridade" in portal_bindings_js
    assert "data-admin-section-tab" in portal_admin_bundle_js
    assert "data-chat-section-tab" in portal_bindings_js
    assert "data-mesa-section-tab" in portal_bindings_js
    assert 'kind === "chat-section"' in portal_bindings_js
    assert 'kind === "mesa-section"' in portal_bindings_js
    assert "function renderAdminSurface()" in portal_shell_js
    assert "function renderChatSurface()" in portal_shell_js
    assert "function renderMesaSurface()" in portal_shell_js
    assert "function renderSurface(surface)" in portal_shell_js
    assert "renderEverything({ surface: state.ui?.tab || surfaceAtiva })" in portal_shell_js
    assert 'perfSnapshot(`cliente:render:${normalizarSurface(surface)}`)' in portal_shell_js
    assert "renderOnboardingEquipe" in portal_admin_bundle_js
    assert "renderChatTriagem" in portal_chat_bundle_js
    assert "renderChatMovimentos" in portal_chat_bundle_js
    assert "renderChatDocumentoPendente" in portal_chat_bundle_js
    assert "state.chat.loadedLaudoId" in portal_chat_bundle_js
    assert "/cliente/api/chat/upload_doc" in portal_chat_bundle_js
    assert "renderMesaTriagem" in portal_mesa_bundle_js
    assert "renderMesaMovimentos" in portal_mesa_bundle_js
    assert "state.mesa.loadedLaudoId" in portal_mesa_bundle_js
    assert "/cliente/api/mesa/laudos/" in portal_mesa_bundle_js
    assert 'data-act="toggle-pendencia"' in portal_mesa_bundle_js
    assert "renderAnexos" in portal_shared_helpers_js
    assert "renderAvisosOperacionais" in portal_shared_helpers_js
    assert "bootstrapPortal" in portal_shell_js
    assert "renderEverything" in portal_shell_js
    assert "sincronizarSelecoes" in portal_shell_js
    assert "bindCrossSliceRouter" in portal_bindings_js
    assert "bindTabs" in portal_bindings_js
    assert "bindFiltros" in portal_bindings_js
    assert "filtrar-usuarios-status" in portal_admin_bundle_js
    assert "filtrar-chat-status" in portal_chat_bundle_js
    assert "filtrar-mesa-status" in portal_mesa_bundle_js
    assert "laudoChatParado" in portal_priorities_js
    assert ".composer-toolbar" in portal_components_css
    assert "laudoMesaParado" in portal_priorities_js
    assert "Ver parados" in portal_chat_bundle_js
    assert "Chamado do inspetor" in portal_mesa_bundle_js
    assert "Parado ha" in portal_priorities_js
    assert "usuariosSituacao" in portal_js
    assert "chatSituacao" in portal_js
    assert "mesaSituacao" in portal_js
    assert "bindCommercialActions" in portal_bindings_js
    assert "aplicarFiltrosUsuarios" in portal_admin_bundle_js
    assert "focarUsuarioNaTabela" in portal_admin_bundle_js
    assert 'data-act="reset-user"' in portal_admin_bundle_js
    assert 'data-act="toggle-user"' in portal_admin_bundle_js
    assert 'data-user="${usuario.id}"' in portal_admin_bundle_js
    assert "user-row-highlight" in portal_components_css
    assert ".cliente-shell" in portal_foundation_css
    assert ".hero-card--primary" in portal_foundation_css
    assert ".metric-card" in portal_components_css
    assert ".context-guidance" in portal_components_css
    assert ".workspace-shell" in portal_workspace_css
    assert ".workspace-columns--chat" in portal_workspace_css
    assert ".admin-map" in portal_admin_surface_css
    assert ".admin-stage" in portal_admin_surface_css
    assert "@import url(\"../admin/admin_tokens.css\")" in portal_admin_theme_css
    assert ".cliente-admin-tab" in portal_admin_theme_css
    assert ".tab-main" in portal_admin_theme_css
    assert ".workspace-radar-grid--chat" in portal_chat_surface_css
    assert ".panel--chat .workspace-box--thread" in portal_chat_surface_css
    assert ".workspace-radar-grid--mesa" in portal_mesa_surface_css
    assert ".panel--mesa .workspace-box--thread" in portal_mesa_surface_css


def test_logins_e_blueprint_nao_reintroduzem_autofill_dev() -> None:
    raiz = Path(__file__).resolve().parents[1]
    login_admin = (raiz / "templates" / "admin" / "login.html").read_text(encoding="utf-8")
    login_cliente = (raiz / "templates" / "login_cliente.html").read_text(encoding="utf-8")
    login_app = (raiz / "templates" / "login_app.html").read_text(encoding="utf-8")
    login_revisor = (raiz / "templates" / "login_revisor.html").read_text(encoding="utf-8")
    env_exemplo = (raiz / ".env.example").read_text(encoding="utf-8")
    render_yaml = (raiz.parent / "render.yaml").read_text(encoding="utf-8")

    assert "Modo Dev" not in login_admin
    assert 'document.getElementById("email").value = "admin@tariel.ia";' not in login_admin
    assert 'document.getElementById("senha").value = "Dev@123456";' not in login_admin
    assert 'value="admin-cliente@tariel.ia"' not in login_cliente
    assert 'value="inspetor@tariel.ia"' not in login_app
    assert 'value="revisor@tariel.ia"' not in login_revisor
    assert "Dev@123456" not in login_cliente
    assert "Dev@123456" not in login_app
    assert "Dev@123456" not in login_revisor

    assert "BOOTSTRAP_ADMIN_EMAIL=" in env_exemplo
    assert "BOOTSTRAP_ADMIN_PASSWORD=" in env_exemplo
    assert "BOOTSTRAP_ADMIN_EMAIL" in render_yaml
    assert "BOOTSTRAP_ADMIN_PASSWORD" in render_yaml
    assert "rootDir: web" in render_yaml


def test_manifesto_aponta_para_icones_existentes_e_sem_marca_legada() -> None:
    raiz = Path(__file__).resolve().parents[1]
    manifesto_path = raiz / "static" / "manifesto.json"
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))

    assert manifesto["name"] == "tariel.ia"
    assert manifesto["short_name"] == "tariel.ia"

    for icone in manifesto["icons"]:
        caminho_relativo = str(icone["src"]).removeprefix("/static/")
        caminho = raiz / "static" / caminho_relativo
        assert caminho.exists(), f"Icone ausente no manifesto: {icone['src']}"


def test_portais_principais_referenciam_marca_nos_templates_de_login() -> None:
    raiz = Path(__file__).resolve().parents[1]
    logo_dark = raiz / "static" / "img" / "logo-horizontal-dark.png"
    logo_light = raiz / "static" / "img" / "logo-horizontal-light.png"

    assert logo_dark.exists()
    assert logo_light.exists()

    login_admin = (raiz / "templates" / "admin" / "login.html").read_text(encoding="utf-8")
    login_cliente = (raiz / "templates" / "login_cliente.html").read_text(encoding="utf-8")
    login_app = (raiz / "templates" / "login_app.html").read_text(encoding="utf-8")
    login_revisor = (raiz / "templates" / "login_revisor.html").read_text(encoding="utf-8")
    trocar_senha = (raiz / "templates" / "trocar_senha.html").read_text(encoding="utf-8")
    portal_cliente = (raiz / "templates" / "cliente_portal.html").read_text(encoding="utf-8")
    dashboard = (raiz / "templates" / "admin" / "dashboard.html").read_text(encoding="utf-8")
    clientes = (raiz / "templates" / "admin" / "clientes.html").read_text(encoding="utf-8")
    detalhe = (raiz / "templates" / "admin" / "cliente_detalhe.html").read_text(encoding="utf-8")

    assert "/static/img/logo-horizontal-dark.png" in login_admin
    assert "/static/img/logo-horizontal-dark.png" in login_cliente
    assert "/static/img/logo-horizontal-dark.png" in login_app
    assert "Mesa Avaliadora" in login_revisor
    assert "/static/img/logo-horizontal-dark.png" not in login_revisor
    assert "/static/img/logo-horizontal-dark.png" in trocar_senha
    assert "/static/css/admin/admin_auth_shell.css" in trocar_senha
    assert "/static/img/logo-horizontal-dark.png" in portal_cliente
    assert "/static/img/logo-horizontal-dark.png" in dashboard
    assert "/static/img/logo-horizontal-dark.png" in clientes
    assert "/static/img/logo-horizontal-dark.png" in detalhe


def test_nomenclatura_admin_ceo_e_admin_cliente_fica_clara_nos_portais() -> None:
    raiz = Path(__file__).resolve().parents[1]
    login_admin = (raiz / "templates" / "admin" / "login.html").read_text(encoding="utf-8")
    login_cliente = (raiz / "templates" / "login_cliente.html").read_text(encoding="utf-8")
    login_app = (raiz / "templates" / "login_app.html").read_text(encoding="utf-8")
    dashboard_admin = (raiz / "templates" / "admin" / "dashboard.html").read_text(encoding="utf-8")
    clientes_admin = (raiz / "templates" / "admin" / "clientes.html").read_text(encoding="utf-8")
    detalhe_cliente = (raiz / "templates" / "admin" / "cliente_detalhe.html").read_text(encoding="utf-8")
    novo_cliente = (raiz / "templates" / "admin" / "novo_cliente.html").read_text(encoding="utf-8")
    dashboard_cliente = (raiz / "app" / "domains" / "cliente" / "dashboard.py").read_text(encoding="utf-8")
    routes_cliente = (raiz / "app" / "domains" / "cliente" / "routes.py").read_text(encoding="utf-8")
    portal_bridge_cliente = (raiz / "app" / "domains" / "cliente" / "portal_bridge.py").read_text(encoding="utf-8")
    routes_admin = (raiz / "app" / "domains" / "admin" / "routes.py").read_text(encoding="utf-8")
    security = (raiz / "app" / "shared" / "security.py").read_text(encoding="utf-8")

    assert "Portal Admin-CEO" in login_admin
    assert "Admin-CEO da Tariel.ia" in login_admin
    assert "Portal da empresa" in login_cliente
    assert "Admin-CEO" not in login_cliente
    assert "Portal do Inspetor" in login_app
    assert "Painel Admin-CEO" in dashboard_admin
    assert "Empresas assinantes" in clientes_admin
    assert "Administradores da empresa (" in detalhe_cliente
    assert "Equipe operacional privada da empresa" in detalhe_cliente
    assert "Provisionar empresa assinante" in novo_cliente
    assert "Admin-CEO" not in dashboard_cliente
    assert "from app.domains.cliente.portal_bridge import (" in routes_cliente
    assert "from app.domains.chat.chat import " not in routes_cliente
    assert "from app.domains.revisor.routes import " not in routes_cliente
    assert "Contrato explícito de integrações do portal cliente" in portal_bridge_cliente
    assert "from app.domains.chat.chat import rota_chat" in portal_bridge_cliente
    assert "obter_mensagens_laudo, rota_chat, rota_upload_doc" not in portal_bridge_cliente
    assert "from app.domains.chat.chat_service import (" in portal_bridge_cliente
    assert "from app.domains.chat.laudo import " not in portal_bridge_cliente
    assert "from app.domains.chat.laudo_service import (" in portal_bridge_cliente
    assert "from app.domains.revisor.routes import " not in portal_bridge_cliente
    assert "Área restrita ao Admin-CEO" in routes_admin
    assert "Acesso restrito ao portal da empresa." in security
    assert "Acesso restrito ao portal Admin-CEO." in security


def test_tela_templates_laudo_separa_biblioteca_e_editor_word() -> None:
    raiz = Path(__file__).resolve().parents[1]
    html_biblioteca = (raiz / "templates" / "revisor_templates_biblioteca.html").read_text(encoding="utf-8")
    html_editor = (raiz / "templates" / "revisor_templates_editor_word.html").read_text(encoding="utf-8")
    js_biblioteca = (raiz / "static" / "js" / "revisor" / "templates_biblioteca_page.js").read_text(encoding="utf-8")
    js_word = (raiz / "static" / "js" / "revisor" / "templates_editor_word.js").read_text(encoding="utf-8")

    assert 'id="search-templates"' in html_biblioteca
    assert 'id="filter-modo"' in html_biblioteca
    assert 'id="sort-templates"' in html_biblioteca
    assert 'id="metric-total"' in html_biblioteca
    assert 'id="metric-word"' in html_biblioteca
    assert 'id="metric-ativo"' in html_biblioteca
    assert 'id="metric-recente"' in html_biblioteca
    assert 'id="selected-template-banner"' in html_biblioteca
    assert 'id="template-preview-modal"' in html_biblioteca
    assert 'id="preview-modal-frame"' in html_biblioteca
    assert 'id="btn-choose-preview-template"' in html_biblioteca
    assert "Vitrine de modelos" in html_biblioteca
    assert "Estes pontos recebem os dados do caso" in html_biblioteca
    assert "Cada card mostra a identidade da NR, a leitura do documento" in html_biblioteca
    assert "/static/js/revisor/templates_biblioteca_page.js" in html_biblioteca

    assert 'id="btn-open-editor-a4"' in html_editor
    assert 'id="card-editor-word"' in html_editor
    assert 'id="editor-word-surface"' in html_editor
    assert 'class="word-workspace-shell"' in html_editor
    assert 'class="word-left-rail"' in html_editor
    assert 'class="word-inspector word-side-panel"' in html_editor
    assert 'id="btn-editor-preview"' in html_editor
    assert 'id="btn-word-toggle-side"' in html_editor
    assert 'id="editor-compare-template-select"' in html_editor
    assert 'id="btn-editor-compare"' in html_editor
    assert 'id="editor-compare-blocks"' in html_editor
    assert "Painel lateral" in html_editor
    assert "Visualização do documento" in html_editor
    assert "Diff visual por bloco" in html_editor
    assert "/static/js/revisor/templates_editor_word.js" in html_editor

    assert "/revisao/api/templates-laudo" in js_biblioteca
    assert "/revisao/api/templates-laudo/${Number(item.id)}/preview" in js_biblioteca
    assert "/revisao/api/templates-laudo/${Number(id)}/arquivo-base" in js_biblioteca
    assert "js-open-preview" in js_biblioteca
    assert "js-select-model" in js_biblioteca
    assert "selected-template-banner" in html_biblioteca
    assert "ordenacao" in js_biblioteca
    assert "atualizarMetricas" in js_biblioteca
    assert "construirGrupos" in js_biblioteca
    assert "template-group-card" in js_biblioteca
    assert "template-version-pill" in js_biblioteca
    assert "grupo_total_versoes" in js_biblioteca
    assert "previewBlobUrl" in js_biblioteca
    assert "template-preview-modal" in html_biblioteca
    assert "Documento base" in html_biblioteca
    assert "Versões visíveis" in js_biblioteca
    assert "renderizarThumbTemplate" in js_biblioteca

    assert "/revisao/api/templates-laudo/editor" in js_word
    assert "/revisao/api/templates-laudo/diff?" in js_word
    assert "asset://" in js_word
    assert "origem_modo" in js_word
    assert "defineTab(\"documento\")" in js_word
    assert "Mostrar painel lateral" in js_word


def test_chat_sidebar_e_modal_perfil_expoem_controles_essenciais() -> None:
    raiz = Path(__file__).resolve().parents[1]
    sidebar_html = (raiz / "templates" / "inspetor" / "_sidebar.html").read_text(encoding="utf-8")
    index_html = (raiz / "templates" / "index.html").read_text(encoding="utf-8")
    perfil_modal_html = (raiz / "templates" / "inspetor" / "modals" / "_perfil.html").read_text(encoding="utf-8")

    assert 'id="btn-sidebar-open-assistant-chat"' in sidebar_html
    assert 'id="lista-historico"' in sidebar_html
    assert 'id="secao-laudos-pinados"' in sidebar_html
    assert 'id="secao-laudos-historico"' in sidebar_html
    assert 'id="estado-vazio-historico"' in sidebar_html
    assert 'id="btn-abrir-perfil-chat"' in sidebar_html
    assert 'data-foto-url="' in sidebar_html
    assert 'class="inspetor-user-card__avatar"' in sidebar_html
    assert "Perfil e personalização" in sidebar_html
    assert "inspetor-runtime-compat" not in sidebar_html

    assert '{% include "inspetor/modals/_perfil.html" %}' in index_html
    assert "/static/js/chat/chat_sidebar.js" not in index_html
    assert 'id="modal-perfil-chat"' in perfil_modal_html
    assert 'id="input-perfil-nome"' in perfil_modal_html
    assert 'id="input-perfil-email"' in perfil_modal_html
    assert 'id="input-perfil-telefone"' in perfil_modal_html
    assert 'id="input-foto-perfil"' in perfil_modal_html
