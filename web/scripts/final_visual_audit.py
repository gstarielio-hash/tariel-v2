from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import requests
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

WEB_ROOT = Path(__file__).resolve().parents[1]
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from app.domains.admin.mfa import current_totp  # noqa: E402
from scripts.inspecao_visual_inspetor import (  # noqa: E402
    _abrir_home_explicita,
    _abrir_modal_nova_inspecao,
    _confirmar_modal_nova_inspecao,
    _forcar_estado_relatorio_workspace,
    _injetar_estilo_estavel,
    _obter_laudo_ativo,
    _preencher_modal_nova_inspecao,
)


PROJECT_ROOT = WEB_ROOT
REPO_ROOT = PROJECT_ROOT.parent
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "final_visual_audit"
DEFAULT_CREDENTIALS = {
    "admin": {"email": "admin@tariel.ia", "senha": "Dev@123456"},
    "admin_cliente": {"email": "admin-cliente@tariel.ia", "senha": "Dev@123456"},
    "inspetor": {"email": "inspetor@tariel.ia", "senha": "Dev@123456"},
    "revisor": {"email": "revisor@tariel.ia", "senha": "Dev@123456"},
}
DISABLE_MOTION_STYLE = """
*,
*::before,
*::after {
  animation: none !important;
  transition: none !important;
  caret-color: transparent !important;
}
html {
  scroll-behavior: auto !important;
}
"""

DOM_AUDIT_SCRIPT = """
() => {
  const pick = (selector) => Array.from(document.querySelectorAll(selector)).filter((el) => {
    if (!(el instanceof Element)) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity || "1") === 0) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  });
  const sample = (elements, limit = 12) => elements.slice(0, limit).map((el) => ({
    tag: el.tagName.toLowerCase(),
    id: el.id || "",
    className: String(el.className || "").trim().slice(0, 160),
    text: (el.textContent || "").replace(/\\s+/g, " ").trim().slice(0, 120),
    role: el.getAttribute("role") || "",
  }));
  const main = document.querySelector("main") || document.body;
  const mainText = (main?.innerText || "").replace(/\\s+/g, " ").trim();
  const linkedStyles = Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map((el) => el.getAttribute("href") || "");
  const linkedScripts = Array.from(document.querySelectorAll("script[src]")).map((el) => el.getAttribute("src") || "");
  const buttons = pick('button, a[class*="btn"], a.btn, [role="button"]');
  const inputs = pick("input, select, textarea");
  const badges = pick('[class*="badge"], [class*="chip"], [class*="pill"], [data-status], [class*="status"]');
  const alerts = pick('[role="alert"], .alert, .feedback, .auth-error, .toast-sw');
  const modals = pick('[role="dialog"], dialog, .modal, .modal-overlay, [class*="modal"]');
  const tables = pick("table");
  const tabs = pick('[role="tab"], .tab, .tabs, .cliente-tab');
  const cards = pick('[class*="card"], [class*="panel"], [class*="box"], [class*="surface"]');
  const headings = pick("h1, h2, h3");
  const sections = pick("section");
  return {
    title: document.title,
    url: window.location.pathname + window.location.search,
    bodyClass: document.body.className || "",
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
    },
    linkedStyles,
    linkedScripts,
    counts: {
      buttons: buttons.length,
      inputs: inputs.length,
      badges: badges.length,
      alerts: alerts.length,
      modals: modals.length,
      tables: tables.length,
      tabs: tabs.length,
      cards: cards.length,
      headings: headings.length,
      sections: sections.length,
      wordsMain: mainText ? mainText.split(/\\s+/).length : 0,
    },
    samples: {
      buttons: sample(buttons),
      inputs: sample(inputs),
      badges: sample(badges),
      alerts: sample(alerts),
      modals: sample(modals),
      tables: sample(tables),
      tabs: sample(tabs),
      cards: sample(cards),
      headings: sample(headings),
    },
  };
}
"""

_ADMIN_TOTP_SECRET_CACHE: str | None = None


@dataclass
class ShotPlan:
    slug: str
    label: str
    url: str
    wait_selector: str | None = None
    full_page: bool = True
    action: Callable[[Page, str], None] | None = None


@dataclass
class SurfacePlan:
    surface: str
    login_url: str
    bootstrap: Callable[[Page, str], None]
    shots: list[ShotPlan]
    viewport: dict[str, int]


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _obter_porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _aguardar_app(base_url: str, timeout_segundos: int = 90) -> None:
    inicio = time.time()
    ultimo_erro: Exception | None = None
    while (time.time() - inicio) < timeout_segundos:
        try:
            resposta = requests.get(f"{base_url}/health", timeout=2.0)
            if resposta.status_code == 200:
                return
        except Exception as erro:
            ultimo_erro = erro
        time.sleep(0.5)
    if ultimo_erro:
        raise RuntimeError(f"App não respondeu em {timeout_segundos}s. Último erro: {ultimo_erro}") from ultimo_erro
    raise RuntimeError(f"App não respondeu em {timeout_segundos}s.")


@contextmanager
def _servidor_local(base_url: str | None) -> Any:
    if base_url:
        _aguardar_app(base_url)
        yield base_url.rstrip("/"), None
        return

    porta = _obter_porta_livre()
    base_url_local = f"http://127.0.0.1:{porta}"
    pasta_db = Path(tempfile.mkdtemp(prefix="final_visual_audit_db_"))
    caminho_db = pasta_db / "tariel_final_visual_audit.sqlite3"

    env = os.environ.copy()
    env.update(
        {
            "AMBIENTE": "dev",
            "PYTHONUNBUFFERED": "1",
            "SEED_DEV_BOOTSTRAP": "1",
            "DATABASE_URL": f"sqlite:///{caminho_db.as_posix()}",
        }
    )

    processo = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(porta),
            "--log-level",
            "warning",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _aguardar_app(base_url_local)
        yield base_url_local, processo
    finally:
        if processo.poll() is None:
            processo.terminate()
            try:
                processo.wait(timeout=10)
            except subprocess.TimeoutExpired:
                processo.kill()
                processo.wait(timeout=5)
        shutil.rmtree(pasta_db, ignore_errors=True)


def _safe_wait_for_url(page: Page, pattern: str, timeout: int = 15000) -> None:
    page.wait_for_url(lambda url: re.search(pattern, url) is not None, timeout=timeout)


def _extract_admin_totp_secret(page: Page) -> str:
    conteudo = page.content()
    match_uri = re.search(r"secret=([A-Z2-7]+)", conteudo)
    if match_uri:
        return match_uri.group(1)

    match_segredo = re.search(r"Segredo TOTP:\s*<code>([A-Z2-7 ]+)</code>", conteudo)
    if match_segredo and match_segredo.group(1):
        return re.sub(r"\s+", "", match_segredo.group(1))

    texto = page.locator("body").inner_text()
    match_texto = re.search(r"Segredo TOTP:\s*([A-Z2-7 ]+)", texto)
    if match_texto:
        return re.sub(r"\s+", "", match_texto.group(1))

    raise RuntimeError("Segredo TOTP do Admin-CEO não encontrado na tela de setup.")


def _obter_segredo_totp_admin_no_banco() -> str | None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url.startswith("sqlite:///"):
        return None
    caminho_db = database_url.removeprefix("sqlite:///").split("?", 1)[0].strip()
    if not caminho_db:
        return None

    conexao = sqlite3.connect(caminho_db)
    try:
        cursor = conexao.execute(
            "select mfa_secret_b32 from usuarios where email = ? and ativo = 1 limit 1",
            ("admin@tariel.ia",),
        )
        linha = cursor.fetchone()
    finally:
        conexao.close()

    if not linha or not linha[0]:
        return None
    return str(linha[0]).strip() or None


def _complete_admin_mfa(page: Page) -> None:
    global _ADMIN_TOTP_SECRET_CACHE
    if re.search(r"/admin/mfa/setup/?$", page.url):
        _ADMIN_TOTP_SECRET_CACHE = _extract_admin_totp_secret(page)
        page.locator('input[name="codigo"]').fill(current_totp(_ADMIN_TOTP_SECRET_CACHE))
        page.locator('button[type="submit"]').click()
        return

    if re.search(r"/admin/mfa/challenge/?$", page.url):
        if not _ADMIN_TOTP_SECRET_CACHE:
            _ADMIN_TOTP_SECRET_CACHE = _obter_segredo_totp_admin_no_banco()
        if not _ADMIN_TOTP_SECRET_CACHE:
            raise RuntimeError("Segredo TOTP do Admin-CEO indisponível para concluir o challenge MFA.")
        page.locator('input[name="codigo"]').fill(current_totp(_ADMIN_TOTP_SECRET_CACHE))
        page.locator('button[type="submit"]').click()


def _login_admin(page: Page, base_url: str) -> None:
    cred = DEFAULT_CREDENTIALS["admin"]
    page.goto(f"{base_url}/admin/login", wait_until="domcontentloaded")
    page.locator('input[name="email"]').fill(cred["email"])
    page.locator('input[name="senha"]').fill(cred["senha"])
    page.locator('button[type="submit"]').first.click()
    if re.search(r"/admin/mfa/(setup|challenge)/?$", page.url):
        _complete_admin_mfa(page)
    _safe_wait_for_url(page, r"/admin/painel(?:\?.*)?$")
    page.locator(".admin-layout").wait_for(state="visible")


def _login_cliente(page: Page, base_url: str) -> None:
    cred = DEFAULT_CREDENTIALS["admin_cliente"]
    page.goto(f"{base_url}/cliente/login", wait_until="domcontentloaded")
    page.locator('input[name="email"]').fill(cred["email"])
    page.locator('input[name="senha"]').fill(cred["senha"])
    page.locator('button[type="submit"]').first.click()
    _safe_wait_for_url(page, r"/cliente/(?:painel|chat|mesa)(?:\?.*)?$")
    page.locator(".cliente-shell").wait_for(state="visible")


def _login_revisor(page: Page, base_url: str) -> None:
    cred = DEFAULT_CREDENTIALS["revisor"]
    page.goto(f"{base_url}/revisao/login", wait_until="domcontentloaded")
    page.locator('input[name="email"]').fill(cred["email"])
    page.locator('input[name="senha"]').fill(cred["senha"])
    page.locator('button[type="submit"]').first.click()
    _safe_wait_for_url(page, r"/revisao/painel(?:\?.*)?$")
    page.locator(".mesa-shell").wait_for(state="visible")


def _login_inspetor(page: Page, base_url: str) -> None:
    cred = DEFAULT_CREDENTIALS["inspetor"]
    page.goto(f"{base_url}/app/login", wait_until="domcontentloaded")
    page.locator('input[name="email"]').fill(cred["email"])
    page.locator('input[name="senha"]').fill(cred["senha"])
    page.locator('button[type="submit"]').first.click()
    _safe_wait_for_url(page, r"/app/?(?:\?.*)?$")
    page.wait_for_function(
        """() => Boolean(
            document.getElementById("painel-chat") &&
            window.TarielInspetorRuntime &&
            typeof window.TarielInspetorRuntime.actions?.abrirModalNovaInspecao === "function"
        )"""
    )


def _context_for(browser: Browser, viewport: dict[str, int]) -> BrowserContext:
    return browser.new_context(
        viewport=viewport,
        locale="pt-BR",
        color_scheme="light",
        service_workers="block",
    )


def _collect_page_audit(page: Page) -> dict[str, Any]:
    _injetar_estilo_estavel(page)
    return page.evaluate(DOM_AUDIT_SCRIPT)


def _capture_page(
    page: Page,
    *,
    output_dir: Path,
    surface: str,
    shot: ShotPlan,
    base_url: str,
) -> dict[str, Any]:
    page.goto(f"{base_url}{shot.url}", wait_until="domcontentloaded")
    if shot.wait_selector:
        page.locator(shot.wait_selector).wait_for(state="visible", timeout=20000)
    if shot.action:
        shot.action(page, base_url)
    _injetar_estilo_estavel(page)
    image_path = output_dir / f"{shot.slug}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(image_path), full_page=shot.full_page)
    audit = _collect_page_audit(page)
    return {
        "surface": surface,
        "slug": shot.slug,
        "label": shot.label,
        "image_path": str(image_path.relative_to(output_dir.parent)),
        "full_page": shot.full_page,
        "viewport": page.viewport_size,
        "audit": audit,
    }


def _prepare_inspetor_workspace(page: Page, _base_url: str) -> None:
    _abrir_home_explicita(page)
    _abrir_modal_nova_inspecao(page)
    _preencher_modal_nova_inspecao(page)
    _confirmar_modal_nova_inspecao(page)
    laudo_id = _obter_laudo_ativo(page)
    _forcar_estado_relatorio_workspace(page, laudo_id)
    page.locator("#workspace-titulo-laudo").wait_for(state="visible")


def _open_inspetor_mesa_workspace(page: Page, _base_url: str) -> None:
    workspace_title = page.locator("#workspace-titulo-laudo").first
    if workspace_title.count() == 0 or not workspace_title.is_visible():
        _prepare_inspetor_workspace(page, _base_url)
    mesa_tab = page.locator('[data-tab="mesa"]').first
    mesa_tab.wait_for(state="visible")
    mesa_tab.click()
    page.locator("#workspace-mesa-stage").wait_for(state="visible")


def _ensure_inspetor_home(page: Page, _base_url: str) -> None:
    _abrir_home_explicita(page)
    page.locator("#tela-boas-vindas").wait_for(state="visible")


def _surface_plans() -> list[SurfacePlan]:
    return [
        SurfacePlan(
            surface="admin",
            login_url="/admin/login",
            bootstrap=_login_admin,
            viewport={"width": 1440, "height": 1100},
            shots=[
                ShotPlan("admin_login", "Admin Login", "/admin/login", ".auth-card", False),
                ShotPlan("admin_dashboard", "Admin Dashboard", "/admin/painel", ".admin-layout", True),
                ShotPlan("admin_clients", "Admin Clients", "/admin/clientes", ".admin-layout", True),
            ],
        ),
        SurfacePlan(
            surface="cliente",
            login_url="/cliente/login",
            bootstrap=_login_cliente,
            viewport={"width": 1440, "height": 1100},
            shots=[
                ShotPlan("cliente_login", "Cliente Login", "/cliente/login", ".auth-card", False),
                ShotPlan("cliente_admin", "Cliente Admin Surface", "/cliente/painel", ".cliente-shell", True),
                ShotPlan("cliente_chat", "Cliente Chat Surface", "/cliente/chat", ".cliente-shell", True),
                ShotPlan("cliente_mesa", "Cliente Mesa Surface", "/cliente/mesa", ".cliente-shell", True),
            ],
        ),
        SurfacePlan(
            surface="app",
            login_url="/app/login",
            bootstrap=_login_inspetor,
            viewport={"width": 1440, "height": 1100},
            shots=[
                ShotPlan("app_login", "App Login", "/app/login", ".auth-card", False),
                ShotPlan("app_home", "App Home", "/app/", "#painel-chat", True, _ensure_inspetor_home),
                ShotPlan("app_workspace", "App Workspace", "/app/", "#painel-chat", False, _prepare_inspetor_workspace),
                ShotPlan("app_workspace_mesa", "App Workspace Mesa", "/app/", "#painel-chat", False, _open_inspetor_mesa_workspace),
            ],
        ),
        SurfacePlan(
            surface="revisao",
            login_url="/revisao/login",
            bootstrap=_login_revisor,
            viewport={"width": 1440, "height": 1100},
            shots=[
                ShotPlan("revisao_login", "Revisao Login", "/revisao/login", ".auth-card", False),
                ShotPlan("revisao_painel", "Revisao Painel", "/revisao/painel", ".mesa-shell", True),
                ShotPlan("revisao_templates_biblioteca", "Revisao Templates Biblioteca", "/revisao/templates-laudo", ".templates-shell", True),
                ShotPlan("revisao_templates_editor", "Revisao Templates Editor", "/revisao/templates-laudo/editor?novo=1", ".templates-shell", True),
            ],
        ),
    ]


def _collect_css_inventory(shots: list[dict[str, Any]]) -> dict[str, Any]:
    inventory: dict[str, Any] = {}
    for shot in shots:
        surface = shot["surface"]
        inventory.setdefault(
            surface,
            {
                "stylesheets": set(),
                "scripts": set(),
                "pages": [],
            },
        )
        audit = shot["audit"]
        inventory[surface]["stylesheets"].update(audit["linkedStyles"])
        inventory[surface]["scripts"].update(audit["linkedScripts"])
        inventory[surface]["pages"].append(
            {
                "slug": shot["slug"],
                "url": audit["url"],
                "title": audit["title"],
                "bodyClass": audit["bodyClass"],
                "counts": audit["counts"],
            }
        )
    for surface, data in inventory.items():
        data["stylesheets"] = sorted(data["stylesheets"])
        data["scripts"] = sorted(data["scripts"])
    return inventory


def _write_source_index(output_root: Path, stage: str, shots: list[dict[str, Any]]) -> None:
    lines = [
        "Tariel final visual audit",
        f"Generated at: {datetime.now().isoformat()}",
        f"Stage: {stage}",
        f"Repo: {PROJECT_ROOT}",
        "",
        "Canonical surfaces:",
        "- /admin",
        "- /cliente",
        "- /app",
        "- /revisao",
        "",
        "Captured pages:",
    ]
    for shot in shots:
        lines.append(f"- {shot['surface']} :: {shot['slug']} :: {shot['audit']['url']}")
    lines.extend(
        [
            "",
            "Primary visual sources:",
            "- web/templates/admin/*.html",
            "- web/templates/cliente*.html and web/templates/cliente/**/*",
            "- web/templates/index.html and web/templates/inspetor/**/*",
            "- web/templates/painel_revisor.html",
            "- web/templates/revisor_templates_*.html",
            "- web/static/css/admin/*",
            "- web/static/css/cliente/*",
            "- web/static/css/inspetor/*",
            "- web/static/css/revisor/*",
            "- web/static/css/shared/*",
            "- web/static/js/admin/*",
            "- web/static/js/cliente/*",
            "- web/static/js/chat/*",
            "- web/static/js/inspetor/*",
            "- web/static/js/revisor/*",
        ]
    )
    (output_root / "source_index.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scan_source_inventory() -> dict[str, Any]:
    cliente_templates = list((PROJECT_ROOT / "templates" / "cliente").rglob("*.html")) + [
        PROJECT_ROOT / "templates" / "cliente_portal.html",
        PROJECT_ROOT / "templates" / "login_cliente.html",
    ]
    app_templates = list((PROJECT_ROOT / "templates" / "inspetor").rglob("*.html")) + [
        PROJECT_ROOT / "templates" / "index.html",
        PROJECT_ROOT / "templates" / "login_app.html",
    ]
    app_styles = list((PROJECT_ROOT / "static" / "css" / "inspetor").glob("*.css")) + list(
        (PROJECT_ROOT / "static" / "css" / "chat").glob("*.css")
    )
    app_scripts = list((PROJECT_ROOT / "static" / "js" / "inspetor").glob("*.js")) + list(
        (PROJECT_ROOT / "static" / "js" / "chat").glob("*.js")
    )
    revisao_templates = [
        PROJECT_ROOT / "templates" / "painel_revisor.html",
        PROJECT_ROOT / "templates" / "login_revisor.html",
        PROJECT_ROOT / "templates" / "revisor_templates_biblioteca.html",
        PROJECT_ROOT / "templates" / "revisor_templates_editor_word.html",
    ]
    mappings = {
        "admin": {
            "templates": sorted(str(path.relative_to(PROJECT_ROOT)) for path in (PROJECT_ROOT / "templates" / "admin").glob("*.html")),
            "styles": sorted(str(path.relative_to(PROJECT_ROOT)) for path in (PROJECT_ROOT / "static" / "css" / "admin").glob("*.css")),
            "scripts": sorted(str(path.relative_to(PROJECT_ROOT)) for path in (PROJECT_ROOT / "static" / "js" / "admin").glob("*.js")),
        },
        "cliente": {
            "templates": sorted(
                str(path.relative_to(PROJECT_ROOT))
                for path in cliente_templates
                if path.exists()
            ),
            "styles": sorted(str(path.relative_to(PROJECT_ROOT)) for path in (PROJECT_ROOT / "static" / "css" / "cliente").glob("*.css")),
            "scripts": sorted(str(path.relative_to(PROJECT_ROOT)) for path in (PROJECT_ROOT / "static" / "js" / "cliente").glob("*.js")),
        },
        "app": {
            "templates": sorted(
                str(path.relative_to(PROJECT_ROOT))
                for path in app_templates
                if path.exists()
            ),
            "styles": sorted(str(path.relative_to(PROJECT_ROOT)) for path in app_styles),
            "scripts": sorted(str(path.relative_to(PROJECT_ROOT)) for path in app_scripts),
        },
        "revisao": {
            "templates": sorted(
                str(path.relative_to(PROJECT_ROOT))
                for path in revisao_templates
                if path.exists()
            ),
            "styles": sorted(str(path.relative_to(PROJECT_ROOT)) for path in (PROJECT_ROOT / "static" / "css" / "revisor").glob("*.css")),
            "scripts": sorted(str(path.relative_to(PROJECT_ROOT)) for path in (PROJECT_ROOT / "static" / "js" / "revisor").glob("*.js")),
        },
    }
    return mappings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auditoria visual final das superfícies oficiais do Tariel.")
    parser.add_argument("--base-url", default="", help="URL base já em execução. Se omitida, o script sobe um servidor local temporário.")
    parser.add_argument("--output-root", default="", help="Diretório raiz do artifact final.")
    parser.add_argument("--stage", choices=["before", "after"], required=True, help="Se a coleta representa o estado antes ou depois da padronização.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_root = Path(args.output_root) if args.output_root else DEFAULT_OUTPUT_ROOT / _now_stamp()
    output_root.mkdir(parents=True, exist_ok=True)
    screenshots_dir = output_root / f"screenshots_{args.stage}"
    inventory_path = output_root / f"visual_inventory_{args.stage}.json"
    source_inventory_path = output_root / f"source_inventory_{args.stage}.json"

    with _servidor_local(args.base_url.strip() or None) as (base_url, _processo), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        all_shots: list[dict[str, Any]] = []

        try:
            for plan in _surface_plans():
                context = _context_for(browser, plan.viewport)
                page = context.new_page()
                try:
                    for shot in plan.shots:
                        if shot.url == plan.login_url:
                            all_shots.append(
                                _capture_page(
                                    page,
                                    output_dir=screenshots_dir,
                                    surface=plan.surface,
                                    shot=shot,
                                    base_url=base_url,
                                )
                            )
                            plan.bootstrap(page, base_url)
                        else:
                            all_shots.append(
                                _capture_page(
                                    page,
                                    output_dir=screenshots_dir,
                                    surface=plan.surface,
                                    shot=shot,
                                    base_url=base_url,
                                )
                            )
                finally:
                    context.close()
        finally:
            browser.close()

    visual_inventory = {
        "generated_at": datetime.now().isoformat(),
        "stage": args.stage,
        "base_url": args.base_url.strip() or "<local-temporary-server>",
        "screenshots_dir": str(screenshots_dir.relative_to(output_root)),
        "shots": all_shots,
        "css_inventory_by_surface": _collect_css_inventory(all_shots),
        "source_inventory_by_surface": _scan_source_inventory(),
    }
    inventory_path.write_text(json.dumps(visual_inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    source_inventory_path.write_text(
        json.dumps(visual_inventory["source_inventory_by_surface"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_source_index(output_root, args.stage, all_shots)
    print(str(inventory_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
