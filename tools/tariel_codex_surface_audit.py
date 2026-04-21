#!/usr/bin/env python3
"""
Tariel surface audit scanner.

Heuristic scanner to help Codex audit whether expected routes, screens, files,
UI signals, and backend wiring exist in the live repository.

It does NOT prove runtime correctness. It flags likely gaps such as:
- missing route
- missing template/screen
- UI keyword present without backend signal
- backend signal present without UI signal
- missing assets expected by the surface

Usage:
    python tools/tariel_codex_surface_audit.py --repo . \
        --output artifacts/tariel_surface_audit_report.md \
        --json-output artifacts/tariel_surface_audit_report.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

DECORATOR_ROUTE_RE = re.compile(
    r'@\s*(?P<router>[A-Za-z0-9_\.]+)\.(?P<method>get|post|put|patch|delete)\(\s*[ruRU]*["\'](?P<route>[^"\']+)["\']'
)
ADD_API_ROUTE_RE = re.compile(
    r'(?P<router>[A-Za-z0-9_\.]+)\.add_api_route\(\s*[ruRU]*["\'](?P<route>[^"\']+)["\'](?P<rest>.*?)\)',
    re.DOTALL,
)
ROUTER_PREFIX_RE = re.compile(
    r'(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*APIRouter\((?P<args>.*?)\)',
    re.DOTALL,
)
PREFIX_ARG_RE = re.compile(r'prefix\s*=\s*[ruRU]*["\']([^"\']+)["\']')
ADD_API_ROUTE_METHODS_RE = re.compile(r'methods\s*=\s*\[([^\]]+)\]')

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "playwright-report",
    "test-results",
    "__pycache__",
    "artifacts",
}

TEXT_EXTS = {
    ".py",
    ".html",
    ".jinja",
    ".j2",
    ".js",
    ".ts",
    ".tsx",
    ".css",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}


@dataclass
class ActionSpec:
    name: str
    ui_keywords: List[str] = field(default_factory=list)
    behavior_keywords: List[str] = field(default_factory=list)
    note: str = ""


@dataclass
class RouteSpec:
    route: str
    methods: List[str] = field(default_factory=list)
    files_should_exist: List[str] = field(default_factory=list)
    ui_scan_roots: List[str] = field(default_factory=list)
    required_api_routes: List[str] = field(default_factory=list)
    actions: List[ActionSpec] = field(default_factory=list)
    notes: str = ""


@dataclass
class SurfaceSpec:
    name: str
    routes: List[RouteSpec]


MANIFEST: List[SurfaceSpec] = [
    SurfaceSpec(
        name="admin-geral",
        routes=[
            RouteSpec(
                route="/admin/login",
                methods=["GET", "POST"],
                files_should_exist=[
                    "web/app/domains/admin/routes.py",
                    "web/templates/login.html",
                ],
                ui_scan_roots=["web/templates", "web/static/js"],
                actions=[
                    ActionSpec(
                        name="login_admin",
                        ui_keywords=["admin", "senha", "entrar"],
                        behavior_keywords=["/admin/login", "logout", "session", "auditoria"],
                    ),
                ],
                notes="Login/logout isolado do portal admin.",
            ),
            RouteSpec(
                route="/admin/painel",
                methods=["GET"],
                files_should_exist=[
                    "web/templates/dashboard.html",
                    "web/app/domains/admin/routes.py",
                ],
                ui_scan_roots=["web/templates", "web/static/js", "web/app/domains/admin"],
                required_api_routes=["/admin/api/metricas-grafico"],
                actions=[
                    ActionSpec(
                        name="metricas_e_graficos",
                        ui_keywords=["métrica", "gráfico", "periodo", "clientes", "chart"],
                        behavior_keywords=["/admin/api/metricas-grafico", "metricas", "billing", "saúde"],
                    ),
                    ActionSpec(
                        name="atalhos_rapidos",
                        ui_keywords=["novo cliente", "auditoria", "diagnóstico", "suporte"],
                        behavior_keywords=["/admin/novo-cliente", "/admin/auditoria", "export"],
                    ),
                ],
            ),
            RouteSpec(
                route="/admin/clientes",
                methods=["GET"],
                files_should_exist=[
                    "web/templates/clientes.html",
                    "web/app/domains/admin/client_routes.py",
                ],
                ui_scan_roots=["web/templates", "web/static/js", "web/app/domains/admin"],
                actions=[
                    ActionSpec(
                        name="listar_filtrar_clientes",
                        ui_keywords=["clientes", "buscar", "status", "plano", "filtro"],
                        behavior_keywords=["empresa", "listar", "filter", "plan", "block"],
                    ),
                    ActionSpec(
                        name="acoes_rapidas_clientes",
                        ui_keywords=["bloquear", "desbloquear", "resetar senha", "detalhe"],
                        behavior_keywords=["reset", "bloquear", "/admin/clientes/"],
                    ),
                ],
            ),
            RouteSpec(
                route="/admin/clientes/{empresa_id}",
                methods=["GET"],
                files_should_exist=[
                    "web/templates/cliente_detalhe.html",
                    "web/app/domains/admin/client_routes.py",
                ],
                ui_scan_roots=["web/templates", "web/static/js", "web/app/domains/admin"],
                actions=[
                    ActionSpec(
                        name="gerenciar_empresa",
                        ui_keywords=["editar", "empresa", "bloquear", "plano", "limite"],
                        behavior_keywords=["plano", "limit", "block", "audit"],
                    ),
                    ActionSpec(
                        name="gerenciar_usuarios",
                        ui_keywords=["usuário", "inspetor", "resetar senha", "reenviar convite"],
                        behavior_keywords=["usuario", "reset", "invite", "block"],
                    ),
                    ActionSpec(
                        name="diagnostico_e_auditoria",
                        ui_keywords=["auditoria", "diagnóstico", "suporte"],
                        behavior_keywords=["audit", "diagnostic", "support"],
                    ),
                ],
            ),
            RouteSpec(
                route="/admin/novo-cliente",
                methods=["GET", "POST"],
                files_should_exist=[
                    "web/templates/novo_cliente.html",
                    "web/app/domains/admin/client_routes.py",
                ],
                ui_scan_roots=["web/templates", "web/static/js", "web/app/domains/admin"],
                actions=[
                    ActionSpec(
                        name="criar_cliente",
                        ui_keywords=["novo cliente", "empresa", "plano", "admin inicial"],
                        behavior_keywords=["create", "empresa", "plano", "usuario"],
                    ),
                ],
            ),
            RouteSpec(
                route="/admin/auditoria",
                methods=["GET"],
                files_should_exist=["web/app/domains/admin"],
                ui_scan_roots=["web/templates", "web/static/js", "web/app/domains/admin"],
                actions=[
                    ActionSpec(
                        name="auditoria_admin",
                        ui_keywords=["auditoria", "ação", "portal", "período"],
                        behavior_keywords=["audit", "correlation", "user_agent"],
                    ),
                ],
                notes="Citadas no plano mestre atual; pode existir em template/rota nova.",
            ),
            RouteSpec(
                route="/admin/api/metricas-grafico",
                methods=["GET"],
                files_should_exist=["web/app/domains/admin/services.py"],
                ui_scan_roots=["web/app/domains/admin", "web/templates", "web/static/js"],
                actions=[
                    ActionSpec(
                        name="api_metricas",
                        ui_keywords=["gráfico", "métrica"],
                        behavior_keywords=["metricas-grafico", "chart", "aggreg", "period"],
                    ),
                ],
            ),
        ],
    ),
    SurfaceSpec(
        name="inspetor-web",
        routes=[
            RouteSpec(
                route="/app/login",
                methods=["GET", "POST"],
                files_should_exist=[
                    "web/app/domains/chat/auth_portal_routes.py",
                ],
                ui_scan_roots=["web/templates", "web/static/js", "web/app/domains/chat"],
                actions=[
                    ActionSpec(
                        name="login_inspetor",
                        ui_keywords=["senha", "entrar", "inspetor"],
                        behavior_keywords=["/app/login", "logout", "session"],
                    ),
                ],
            ),
            RouteSpec(
                route="/app/",
                methods=["GET"],
                files_should_exist=[
                    "web/templates/index.html",
                    "web/templates/inspetor/base.html",
                    "web/static/js/chat/chat_index_page.js",
                    "web/app/domains/chat/chat_stream_routes.py",
                    "web/app/domains/chat/laudo.py",
                    "web/app/domains/chat/mesa.py",
                ],
                ui_scan_roots=[
                    "web/templates/inspetor",
                    "web/static/js/chat",
                    "web/static/js/inspetor",
                    "web/static/js/shared",
                    "web/app/domains/chat",
                ],
                required_api_routes=[
                    "/app/api/chat",
                    "/app/api/upload_doc",
                    "/app/api/notificacoes/sse",
                    "/app/api/laudo/iniciar",
                    "/app/api/laudo/status",
                ],
                actions=[
                    ActionSpec(
                        name="shell_e_navegacao",
                        ui_keywords=["go-home", "home", "sidebar", "perfil", "nova inspeção", "modo foco"],
                        behavior_keywords=["go-home", "sidebar", "profile", "modal", "?laudo=", "localStorage"],
                    ),
                    ActionSpec(
                        name="composer_chat",
                        ui_keywords=["enviar", "anexar", "foto", "preview", "retry"],
                        behavior_keywords=["/app/api/chat", "/app/api/upload_doc", "draft", "csrf", "stream"],
                    ),
                    ActionSpec(
                        name="acoes_laudo",
                        ui_keywords=["finalizar", "reabrir", "gate", "pdf", "revisões", "pin"],
                        behavior_keywords=["/app/api/laudo", "finalizar", "reabrir", "gerar_pdf", "gate-qualidade"],
                    ),
                    ActionSpec(
                        name="mesa_no_inspetor",
                        ui_keywords=["mesa", "pendências", "resumo", "anexo"],
                        behavior_keywords=["/mesa/mensagem", "/mesa/anexo", "/mesa/resumo", "/pendencias"],
                    ),
                    ActionSpec(
                        name="notificacoes_sse",
                        ui_keywords=["notificação", "badge", "heartbeat"],
                        behavior_keywords=["/app/api/notificacoes/sse", "EventSource", "reconnect"],
                    ),
                ],
            ),
            RouteSpec(
                route="/app/api/chat",
                methods=["POST"],
                files_should_exist=["web/app/domains/chat/chat_stream_routes.py"],
                ui_scan_roots=["web/app/domains/chat", "web/static/js/chat", "web/static/js/shared"],
                actions=[
                    ActionSpec(
                        name="stream_chat",
                        ui_keywords=["enviar", "stream", "mensagem"],
                        behavior_keywords=["persist", "citação", "sse", "gemini", "vision"],
                    ),
                ],
            ),
            RouteSpec(
                route="/app/api/upload_doc",
                methods=["POST"],
                files_should_exist=["web/app/domains/chat/chat_aux_routes.py"],
                ui_scan_roots=["web/app/domains/chat", "web/static/js/chat", "web/static/js/shared"],
                actions=[
                    ActionSpec(
                        name="upload_doc",
                        ui_keywords=["upload", "anexo", "preview", "limpar"],
                        behavior_keywords=["content_type", "size", "upload", "preview"],
                    ),
                ],
            ),
            RouteSpec(
                route="/app/api/gerar_pdf",
                methods=["POST"],
                files_should_exist=["web/app/domains/chat/chat_aux_routes.py"],
                ui_scan_roots=["web/app/domains/chat", "web/templates/inspetor", "web/static/js/chat"],
                actions=[
                    ActionSpec(
                        name="gerar_pdf",
                        ui_keywords=["gerar pdf", "preview", "documento"],
                        behavior_keywords=["gerar_pdf", "gate", "template", "document"],
                    ),
                ],
            ),
            RouteSpec(
                route="/app/api/notificacoes/sse",
                methods=["GET"],
                files_should_exist=["web/static/js/inspetor/notifications_sse.js"],
                ui_scan_roots=["web/static/js/inspetor", "web/app/domains/chat"],
                actions=[
                    ActionSpec(
                        name="sse",
                        ui_keywords=["notificação", "badge", "heartbeat"],
                        behavior_keywords=["EventSource", "heartbeat", "reconnect", "sse"],
                    ),
                ],
            ),
            RouteSpec(
                route="/app/api/perfil",
                methods=["GET", "PUT"],
                files_should_exist=["web/static/js/chat/chat_perfil_usuario.js"],
                ui_scan_roots=["web/static/js/chat", "web/templates/inspetor"],
                actions=[
                    ActionSpec(
                        name="perfil_web",
                        ui_keywords=["perfil", "nome", "email", "telefone", "senha", "foto"],
                        behavior_keywords=["/app/api/perfil", "foto", "password", "save"],
                    ),
                ],
            ),
        ],
    ),
    SurfaceSpec(
        name="portal-cliente",
        routes=[
            RouteSpec(
                route="/cliente/login",
                methods=["GET", "POST"],
                files_should_exist=["web/app/domains/cliente/routes.py"],
                ui_scan_roots=["web/templates", "web/static/js/cliente", "web/app/domains/cliente"],
                actions=[
                    ActionSpec(
                        name="login_cliente",
                        ui_keywords=["cliente", "entrar", "senha"],
                        behavior_keywords=["/cliente/login", "logout", "session"],
                    ),
                ],
            ),
            RouteSpec(
                route="/cliente/painel",
                methods=["GET"],
                files_should_exist=[
                    "web/templates/cliente_portal.html",
                    "web/static/js/cliente/portal.js",
                    "web/app/domains/cliente/routes.py",
                ],
                ui_scan_roots=[
                    "web/templates",
                    "web/static/js/cliente",
                    "web/app/domains/cliente",
                ],
                required_api_routes=[
                    "/cliente/api/bootstrap",
                    "/cliente/api/empresa/resumo",
                    "/cliente/api/usuarios",
                    "/cliente/api/chat/mensagem",
                    "/cliente/api/mesa/laudos",
                ],
                actions=[
                    ActionSpec(
                        name="shell_cliente",
                        ui_keywords=["admin", "chat", "mesa", "uso", "plano", "suporte"],
                        behavior_keywords=["bootstrap", "portal", "tab", "support"],
                    ),
                    ActionSpec(
                        name="gestao_empresa",
                        ui_keywords=["usuários", "auditoria", "plano", "limite", "upgrade"],
                        behavior_keywords=["/cliente/api/usuarios", "/cliente/api/auditoria", "upgrade", "billing"],
                    ),
                    ActionSpec(
                        name="chat_company_scoped",
                        ui_keywords=["laudos", "mensagens", "enviar", "upload", "gate", "finalizar"],
                        behavior_keywords=["/cliente/api/chat/laudos", "/cliente/api/chat/mensagem", "/cliente/api/chat/upload_doc"],
                    ),
                    ActionSpec(
                        name="mesa_company_scoped",
                        ui_keywords=["mesa", "pacote", "responder", "pendência", "anexo"],
                        behavior_keywords=["/cliente/api/mesa/laudos", "/pacote", "/responder"],
                    ),
                ],
            ),
            RouteSpec(
                route="/cliente/api/bootstrap",
                methods=["GET"],
                files_should_exist=["web/app/domains/cliente/dashboard_bootstrap.py"],
                ui_scan_roots=["web/app/domains/cliente", "web/static/js/cliente"],
                actions=[
                    ActionSpec(
                        name="bootstrap_cliente",
                        ui_keywords=["bootstrap"],
                        behavior_keywords=["shadow", "projection", "bootstrap"],
                    ),
                ],
            ),
        ],
    ),
    SurfaceSpec(
        name="revisor-ssr",
        routes=[
            RouteSpec(
                route="/revisao/login",
                methods=["GET", "POST"],
                files_should_exist=["web/app/domains/revisor/auth_portal.py"],
                ui_scan_roots=["web/templates", "web/static/js/revisor", "web/app/domains/revisor"],
                actions=[
                    ActionSpec(
                        name="login_revisor",
                        ui_keywords=["revisor", "senha", "entrar"],
                        behavior_keywords=["/revisao/login", "logout", "session"],
                    ),
                ],
            ),
            RouteSpec(
                route="/revisao/painel",
                methods=["GET"],
                files_should_exist=[
                    "web/templates/painel_revisor.html",
                    "web/static/js/revisor/painel_revisor_page.js",
                    "web/app/domains/revisor/panel.py",
                ],
                ui_scan_roots=["web/templates", "web/static/js/revisor", "web/app/domains/revisor"],
                required_api_routes=[
                    "/revisao/api/laudo/{laudo_id}/mensagens",
                    "/revisao/api/laudo/{laudo_id}/pacote",
                    "/revisao/api/laudo/{laudo_id}/responder",
                ],
                actions=[
                    ActionSpec(
                        name="fila_e_caso",
                        ui_keywords=["fila", "caso", "histórico", "pacote"],
                        behavior_keywords=["panel", "queue", "pacote", "completo"],
                    ),
                    ActionSpec(
                        name="reply_e_decisao",
                        ui_keywords=["responder", "anexo", "pendência", "avaliar"],
                        behavior_keywords=["/responder", "/responder-anexo", "/avaliar", "/pendencias/"],
                    ),
                    ActionSpec(
                        name="aprendizados_e_ws",
                        ui_keywords=["aprendizado", "whisper", "badge"],
                        behavior_keywords=["/aprendizados", "ws/whispers", "reconnect"],
                    ),
                ],
            ),
            RouteSpec(
                route="/revisao/templates-laudo",
                methods=["GET"],
                files_should_exist=[
                    "web/templates/revisor_templates_biblioteca.html",
                    "web/static/js/revisor/templates_biblioteca_page.js",
                ],
                ui_scan_roots=["web/templates", "web/static/js/revisor", "web/app/domains/revisor"],
                actions=[
                    ActionSpec(
                        name="biblioteca_templates",
                        ui_keywords=["template", "publicar", "preview", "comparar", "clonar", "status"],
                        behavior_keywords=["templates", "publish", "preview", "diff", "clone", "status"],
                    ),
                ],
            ),
            RouteSpec(
                route="/revisao/templates-laudo/editor",
                methods=["GET"],
                files_should_exist=[
                    "web/templates/revisor_templates_editor_word.html",
                    "web/static/js/revisor/templates_editor_word.js",
                ],
                ui_scan_roots=["web/templates", "web/static/js/revisor", "web/app/domains/revisor"],
                actions=[
                    ActionSpec(
                        name="editor_templates",
                        ui_keywords=["editor", "salvar", "asset", "preview", "publicar"],
                        behavior_keywords=["save", "asset", "preview", "publish"],
                    ),
                ],
            ),
        ],
    ),
    SurfaceSpec(
        name="mobile-inspetor",
        routes=[
            RouteSpec(
                route="/app/api/mobile/auth/login",
                methods=["POST"],
                files_should_exist=[
                    "android/src/features/InspectorMobileApp.tsx",
                    "android/src/config/authApi.ts",
                ],
                ui_scan_roots=["android/src/features", "android/src/config"],
                actions=[
                    ActionSpec(
                        name="auth_mobile",
                        ui_keywords=["login", "logout", "sessão", "bootstrap"],
                        behavior_keywords=["/app/api/mobile/auth/login", "/app/api/mobile/auth/logout", "/app/api/mobile/bootstrap"],
                    ),
                ],
            ),
            RouteSpec(
                route="/app/api/mobile/laudos",
                methods=["GET"],
                files_should_exist=["android/src/config/chatApi.ts"],
                ui_scan_roots=["android/src/features", "android/src/config"],
                actions=[
                    ActionSpec(
                        name="historico_mobile",
                        ui_keywords=["histórico", "laudos", "buscar", "filtro"],
                        behavior_keywords=["/app/api/mobile/laudos", "history", "filter", "cache"],
                    ),
                ],
            ),
            RouteSpec(
                route="/app/api/mobile/mesa/feed",
                methods=["GET"],
                files_should_exist=["android/src/config/mesaApi.ts"],
                ui_scan_roots=["android/src/features", "android/src/config"],
                actions=[
                    ActionSpec(
                        name="mesa_mobile",
                        ui_keywords=["mesa", "feed", "resumo", "reply", "anexo"],
                        behavior_keywords=["/app/api/mobile/mesa/feed", "reply", "attachment", "sync"],
                    ),
                ],
            ),
            RouteSpec(
                route="/app/api/mobile/account/settings",
                methods=["GET", "PUT"],
                files_should_exist=[
                    "android/src/features/settings",
                    "android/src/config/settingsApi.ts",
                ],
                ui_scan_roots=["android/src/features/settings", "android/src/settings", "android/src/config"],
                actions=[
                    ActionSpec(
                        name="settings_mobile",
                        ui_keywords=["conta", "experiência", "ia", "aparência", "notificações", "privacidade", "fala"],
                        behavior_keywords=["/app/api/mobile/account/settings", "schema", "persist", "migrate"],
                    ),
                    ActionSpec(
                        name="conversation_tone",
                        ui_keywords=["tom", "amigável", "friendly", "balanced", "direct"],
                        behavior_keywords=["conversation_tone", "friendly", "balanced", "direct", "settings"],
                        note="Se a opção aparece, precisa ser persistida e aplicada ao chat.",
                    ),
                ],
            ),
            RouteSpec(
                route="/app/api/mobile/support/report",
                methods=["POST"],
                files_should_exist=["android/src/config"],
                ui_scan_roots=["android/src/features", "android/src/config"],
                actions=[
                    ActionSpec(
                        name="suporte_mobile",
                        ui_keywords=["diagnóstico", "suporte", "reportar"],
                        behavior_keywords=["support/report", "diagnostic", "export"],
                    ),
                ],
            ),
        ],
    ),
]


def iter_files(repo: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        root_path = Path(root)
        for file_name in files:
            path = root_path / file_name
            if path.suffix.lower() in TEXT_EXTS:
                yield path


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return ""
    except Exception:
        return ""


def infer_domain_prefix(path: Path, repo: Path) -> str:
    rel = str(path.relative_to(repo))
    if rel.startswith("web/app/domains/admin/"):
        return "/admin"
    if rel.startswith("web/app/domains/cliente/"):
        return "/cliente"
    if rel.startswith("web/app/domains/chat/"):
        return "/app"
    if rel.startswith("web/app/domains/revisor/"):
        return "/revisao"
    return ""


def normalize_full_route(prefix: str, route: str) -> str:
    prefix_normalized = str(prefix or "").strip()
    route_normalized = str(route or "").strip()
    if not route_normalized.startswith("/"):
        route_normalized = "/" + route_normalized
    if not prefix_normalized or route_normalized == prefix_normalized or route_normalized.startswith(prefix_normalized + "/"):
        return route_normalized
    return prefix_normalized.rstrip("/") + route_normalized


def extract_router_prefixes(text: str) -> Dict[str, str]:
    prefixes: Dict[str, str] = {}
    for match in ROUTER_PREFIX_RE.finditer(text):
        prefix_match = PREFIX_ARG_RE.search(match.group("args") or "")
        prefixes[match.group("name")] = prefix_match.group(1) if prefix_match else ""
    return prefixes


def extract_routes(repo: Path) -> Dict[str, List[Tuple[str, str]]]:
    route_map: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for path in iter_files(repo):
        if path.suffix.lower() != ".py":
            continue
        text = safe_read(path)
        rel = str(path.relative_to(repo))
        router_prefixes = extract_router_prefixes(text)
        fallback_prefix = infer_domain_prefix(path, repo)

        for match in DECORATOR_ROUTE_RE.finditer(text):
            router_name = match.group("router").split(".")[-1]
            route = normalize_full_route(
                router_prefixes.get(router_name) or fallback_prefix,
                match.group("route"),
            )
            route_map[route].append((match.group("method").upper(), rel))

        for match in ADD_API_ROUTE_RE.finditer(text):
            router_name = match.group("router").split(".")[-1]
            route = normalize_full_route(
                router_prefixes.get(router_name) or fallback_prefix,
                match.group("route"),
            )
            methods_match = ADD_API_ROUTE_METHODS_RE.search(match.group("rest") or "")
            if methods_match:
                methods = [
                    token.strip().strip("\"'").upper()
                    for token in methods_match.group(1).split(",")
                    if token.strip()
                ]
            else:
                methods = ["GET"]
            for method in methods:
                route_map[route].append((method, rel))

    return route_map


def build_text_index(repo: Path) -> Dict[str, str]:
    index: Dict[str, str] = {}
    for path in iter_files(repo):
        rel = str(path.relative_to(repo))
        index[rel] = safe_read(path)
    return index


def path_exists(repo: Path, relative_path: str) -> bool:
    path = repo / relative_path
    if path.exists():
        return True
    matches = list(repo.glob(relative_path + "*"))
    return bool(matches)


def files_under_roots(index: Dict[str, str], roots: Sequence[str]) -> Dict[str, str]:
    if not roots:
        return index
    result = {}
    for rel, text in index.items():
        if any(rel.startswith(root.rstrip("/")) for root in roots):
            result[rel] = text
    return result


def keyword_hits(files: Dict[str, str], keywords: Sequence[str]) -> List[str]:
    hits = []
    lowered_keywords = [kw.lower() for kw in keywords if kw]
    for rel, text in files.items():
        lowered = text.lower()
        if any(kw in lowered for kw in lowered_keywords):
            hits.append(rel)
    return hits


def action_status(ui_hits: List[str], behavior_hits: List[str]) -> str:
    if ui_hits and behavior_hits:
        return "OK_WIRED"
    if ui_hits and not behavior_hits:
        return "PLACEHOLDER_RISK"
    if not ui_hits and behavior_hits:
        return "BACKEND_ONLY"
    return "MISSING"


def route_status(route: str, methods: Sequence[str], extracted: Dict[str, List[Tuple[str, str]]]) -> Tuple[str, List[Tuple[str, str]]]:
    route_variants = {route}
    if route.endswith("/"):
        route_variants.add(route[:-1])
    else:
        route_variants.add(route + "/")
    matches: List[Tuple[str, str]] = []
    for variant in route_variants:
        for item in extracted.get(variant, []):
            matches.append(item)
    if not matches:
        return "MISSING", []
    if not methods:
        return "FOUND", matches
    found_methods = {method for method, _ in matches}
    required_methods = {m.upper() for m in methods}
    if required_methods.issubset(found_methods):
        return "FOUND", matches
    return "PARTIAL", matches


def score_route(
    repo: Path,
    route_spec: RouteSpec,
    extracted_routes: Dict[str, List[Tuple[str, str]]],
    text_index: Dict[str, str],
) -> Dict[str, object]:
    route_state, route_matches = route_status(route_spec.route, route_spec.methods, extracted_routes)
    file_checks = {
        rel: path_exists(repo, rel)
        for rel in route_spec.files_should_exist
    }
    ui_files = files_under_roots(text_index, route_spec.ui_scan_roots)
    actions = []
    for action in route_spec.actions:
        ui_hits = keyword_hits(ui_files, action.ui_keywords)
        behavior_hits = keyword_hits(ui_files, action.behavior_keywords)
        actions.append(
            {
                "name": action.name,
                "status": action_status(ui_hits, behavior_hits),
                "ui_hits": ui_hits[:20],
                "behavior_hits": behavior_hits[:20],
                "note": action.note,
            }
        )
    required_api = {}
    for api_route in route_spec.required_api_routes:
        api_state, api_matches = route_status(api_route, [], extracted_routes)
        required_api[api_route] = {
            "status": api_state,
            "matches": api_matches,
        }
    overall = "OK"
    if route_state == "MISSING" or any(not ok for ok in file_checks.values()):
        overall = "GAP"
    if any(action["status"] in {"PLACEHOLDER_RISK", "MISSING"} for action in actions):
        overall = "GAP"
    if any(value["status"] == "MISSING" for value in required_api.values()):
        overall = "GAP"
    return {
        "route": route_spec.route,
        "methods": route_spec.methods,
        "route_state": route_state,
        "route_matches": route_matches,
        "required_files": file_checks,
        "required_api": required_api,
        "actions": actions,
        "overall": overall,
        "notes": route_spec.notes,
    }


def render_markdown(repo: Path, results: Dict[str, List[Dict[str, object]]]) -> str:
    lines: List[str] = []
    lines.append("# Tariel surface audit report")
    lines.append("")
    lines.append(f"Repo analisado: `{repo}`")
    lines.append("")
    lines.append("Este relatório é heurístico. Ele detecta presença, wiring provável e risco de placeholder, mas não substitui smoke/E2E.")
    lines.append("")
    gap_count = 0
    total_count = 0
    for surface, items in results.items():
        for item in items:
            total_count += 1
            if item["overall"] != "OK":
                gap_count += 1
    lines.append(f"Resumo: **{total_count - gap_count} OK** / **{gap_count} com GAP** / **{total_count} totais**")
    lines.append("")
    for surface, items in results.items():
        lines.append(f"## {surface}")
        lines.append("")
        for item in items:
            lines.append(f"### `{item['route']}` — {item['overall']}")
            lines.append("")
            lines.append(f"- métodos esperados: `{', '.join(item['methods']) or 'não especificado'}`")
            lines.append(f"- rota no código: `{item['route_state']}`")
            if item["route_matches"]:
                for method, file_name in item["route_matches"][:10]:
                    lines.append(f"  - encontrada: `{method}` em `{file_name}`")
            else:
                lines.append("  - não encontrada por regex de decorators FastAPI")
            lines.append("- arquivos esperados:")
            for rel, ok in item["required_files"].items():
                lines.append(f"  - {'OK' if ok else 'MISSING'} `{rel}`")
            if item["required_api"]:
                lines.append("- APIs relacionadas:")
                for api_route, api_info in item["required_api"].items():
                    lines.append(f"  - `{api_route}` -> {api_info['status']}")
                    for method, file_name in api_info["matches"][:5]:
                        lines.append(f"    - `{method}` em `{file_name}`")
            if item["notes"]:
                lines.append(f"- nota: {item['notes']}")
            lines.append("- ações:")
            for action in item["actions"]:
                lines.append(f"  - **{action['name']}** -> `{action['status']}`")
                if action["note"]:
                    lines.append(f"    - nota: {action['note']}")
                if action["ui_hits"]:
                    lines.append(f"    - sinais de UI: `{', '.join(action['ui_hits'][:5])}`")
                if action["behavior_hits"]:
                    lines.append(f"    - sinais de comportamento: `{', '.join(action['behavior_hits'][:5])}`")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Heuristic Tariel surface audit scanner")
    parser.add_argument("--repo", required=True, help="Path to live Tariel repository")
    parser.add_argument("--output", default="", help="Markdown report output path")
    parser.add_argument("--json-output", default="", help="JSON report output path")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")

    extracted_routes = extract_routes(repo)
    text_index = build_text_index(repo)

    results: Dict[str, List[Dict[str, object]]] = {}
    for surface in MANIFEST:
        surface_results = []
        for route_spec in surface.routes:
            surface_results.append(score_route(repo, route_spec, extracted_routes, text_index))
        results[surface.name] = surface_results

    md = render_markdown(repo, results)
    print(md)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md, encoding="utf-8")
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
