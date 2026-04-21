from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests


def _ambiente_visual_suportado() -> bool:
    if sys.platform.startswith("linux"):
        return bool(os.getenv("DISPLAY", "").strip() or os.getenv("WAYLAND_DISPLAY", "").strip())
    return True


def _rodando_em_ci() -> bool:
    return os.getenv("CI", "").strip().lower() in {"1", "true", "yes", "on"}


def _e2e_visual_ativo() -> bool:
    valor = os.getenv("E2E_VISUAL", "").strip().lower()
    if valor in {"0", "false", "no", "off"}:
        return False
    if valor in {"1", "true", "yes", "on"}:
        return _ambiente_visual_suportado()
    if _rodando_em_ci():
        return False
    return _ambiente_visual_suportado()


def _e2e_slowmo_ms() -> int:
    bruto = os.getenv("E2E_SLOWMO_MS", "").strip() or "350"
    try:
        return max(int(bruto), 0)
    except ValueError:
        return 350


def _script_overlay_visual(nome_teste: str) -> str:
    return f"""
(() => {{
    const TEST_NAME = {json.dumps(nome_teste, ensure_ascii=False)};
    const STYLE_ID = "__tariel-e2e-visual-style";
    const OVERLAY_ID = "__tariel-e2e-visual-overlay";

    function simplify(value) {{
        const text = String(value || "").replace(/\\s+/g, " ").trim();
        if (!text) return "";
        return text.length > 88 ? text.slice(0, 85) + "..." : text;
    }}

    function pickTarget(node) {{
        if (!(node instanceof Element)) return null;
        return node.closest("button, a, input, textarea, select, label, [role='button'], [data-testid], [id], [name]") || node;
    }}

    function describe(node) {{
        if (!(node instanceof Element)) return "pagina";
        const parts = [];
        const tag = simplify(node.tagName || "").toLowerCase();
        const id = simplify(node.id);
        const name = simplify(node.getAttribute("name"));
        const role = simplify(node.getAttribute("role"));
        const label = simplify(
            node.getAttribute("aria-label")
            || node.getAttribute("placeholder")
            || node.getAttribute("title")
            || node.textContent
        );
        if (tag) parts.push(tag);
        if (id) parts.push("#" + id);
        if (name) parts.push(`[name="${{name}}"]`);
        if (role) parts.push(`[role="${{role}}"]`);
        if (label) parts.push(label);
        return parts.join(" ");
    }}

    function ensureStyle() {{
        if (document.getElementById(STYLE_ID)) return;
        const style = document.createElement("style");
        style.id = STYLE_ID;
        style.textContent = `
            #${{OVERLAY_ID}} {{
                position: fixed;
                top: 16px;
                right: 16px;
                z-index: 2147483647;
                pointer-events: none;
                min-width: 340px;
                max-width: min(48vw, 720px);
                padding: 10px 14px;
                border-radius: 14px;
                background: rgba(11, 18, 32, 0.92);
                color: #f8fafc;
                box-shadow: 0 16px 40px rgba(15, 23, 42, 0.28);
                border: 1px solid rgba(148, 163, 184, 0.35);
                font: 600 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                letter-spacing: 0.01em;
            }}
            #${{OVERLAY_ID}} .__tariel-e2e-title {{
                display: block;
                color: #cbd5e1;
                font-size: 11px;
                margin-bottom: 4px;
                text-transform: uppercase;
            }}
            #${{OVERLAY_ID}} .__tariel-e2e-action {{
                display: block;
                color: #f8fafc;
                word-break: break-word;
            }}
            .__tariel-e2e-focus {{
                outline: 3px solid rgba(59, 130, 246, 0.85) !important;
                outline-offset: 2px !important;
                transition: outline-color 120ms ease;
            }}
            .__tariel-e2e-click {{
                outline: 3px solid rgba(245, 158, 11, 0.95) !important;
                outline-offset: 2px !important;
                transition: outline-color 120ms ease;
            }}
        `;
        (document.head || document.documentElement).appendChild(style);
    }}

    function ensureOverlay() {{
        if (!document.body) return null;
        let overlay = document.getElementById(OVERLAY_ID);
        if (!overlay) {{
            overlay = document.createElement("aside");
            overlay.id = OVERLAY_ID;
            overlay.innerHTML = `
                <span class="__tariel-e2e-title"></span>
                <span class="__tariel-e2e-action"></span>
            `;
            document.body.appendChild(overlay);
        }}
        return overlay;
    }}

    function withOverlay(callback) {{
        ensureStyle();
        if (document.body) {{
            callback();
            return;
        }}
        document.addEventListener("DOMContentLoaded", callback, {{ once: true }});
    }}

    function flash(node, className) {{
        if (!(node instanceof Element)) return;
        node.classList.add(className);
        window.setTimeout(() => node.classList.remove(className), 900);
    }}

    function announce(action, node) {{
        withOverlay(() => {{
            const overlay = ensureOverlay();
            if (!overlay) return;
            const title = overlay.querySelector(".__tariel-e2e-title");
            const body = overlay.querySelector(".__tariel-e2e-action");
            if (title) title.textContent = TEST_NAME || "E2E visual";
            if (body) body.textContent = `${{String(action || "acao").toUpperCase()}}: ${{describe(node)}}`;
        }});
    }}

    ensureStyle();
    announce("boot", document.documentElement);

    document.addEventListener("focusin", (event) => {{
        const target = pickTarget(event.target);
        announce("focus", target);
        flash(target, "__tariel-e2e-focus");
    }}, true);

    document.addEventListener("pointerdown", (event) => {{
        const target = pickTarget(event.target);
        announce("click", target);
        flash(target, "__tariel-e2e-click");
    }}, true);

    document.addEventListener("input", (event) => {{
        announce("input", pickTarget(event.target));
    }}, true);

    document.addEventListener("change", (event) => {{
        announce("change", pickTarget(event.target));
    }}, true);

    document.addEventListener("keydown", (event) => {{
        if (!["Enter", "Tab", "Escape", "ArrowUp", "ArrowDown"].includes(event.key)) return;
        announce(`key ${{event.key}}`, pickTarget(document.activeElement || event.target));
    }}, true);

    window.addEventListener("load", () => {{
        announce("loaded", document.body || document.documentElement);
    }}, {{ once: true }});
}})();
"""


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict[str, object]) -> dict[str, object]:
    args = dict(browser_type_launch_args)
    if not _e2e_visual_ativo():
        return args

    launch_args = list(args.get("args", []))
    if "--start-maximized" not in launch_args:
        launch_args.append("--start-maximized")

    args["args"] = launch_args
    args["headless"] = False
    args["slow_mo"] = _e2e_slowmo_ms()
    return args


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, object]) -> dict[str, object]:
    """Evita interferência de Service Worker nos fluxos E2E de sessão/reload."""
    args = {
        **browser_context_args,
        "service_workers": "block",
    }
    if _e2e_visual_ativo():
        args["viewport"] = None
    return args


@pytest.fixture(autouse=True)
def _aplicar_overlay_visual_e2e(request: pytest.FixtureRequest, browser, monkeypatch: pytest.MonkeyPatch) -> None:
    if not _e2e_visual_ativo():
        return

    nome_teste = getattr(request.node, "name", "E2E visual")
    script = _script_overlay_visual(nome_teste)
    original_new_context = browser.new_context

    def _patched_new_context(*args, **kwargs):
        kwargs.setdefault("viewport", None)
        context = original_new_context(*args, **kwargs)
        context.add_init_script(script)
        return context

    monkeypatch.setattr(browser, "new_context", _patched_new_context)


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
        except Exception as erro:  # pragma: no cover - caminho de retentativa
            ultimo_erro = erro
        time.sleep(0.5)

    if ultimo_erro:
        raise RuntimeError(f"App não respondeu em {timeout_segundos}s. Último erro: {ultimo_erro}") from ultimo_erro
    raise RuntimeError(f"App não respondeu em {timeout_segundos}s.")


@pytest.fixture(scope="session")
def live_server_runtime(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str | None]:
    base_url_externo = os.getenv("E2E_BASE_URL", "").strip().rstrip("/")
    if base_url_externo:
        _aguardar_app(base_url_externo)
        yield {
            "base_url": base_url_externo,
            "database_url": (
                os.getenv("E2E_LOCAL_DATABASE_URL", "").strip()
                or os.getenv("DATABASE_URL", "").strip()
                or None
            ),
        }
        return

    projeto_dir = Path(__file__).resolve().parents[2]
    (projeto_dir / ".test-artifacts").mkdir(exist_ok=True)
    porta = _obter_porta_livre()
    base_url = f"http://127.0.0.1:{porta}"
    usar_db_local = os.getenv("E2E_USE_LOCAL_DB", "0").strip().lower() in {"1", "true", "yes", "on"}

    env = os.environ.copy()
    env.update({"AMBIENTE": "dev", "PYTHONUNBUFFERED": "1"})

    if usar_db_local:
        db_local = os.getenv("E2E_LOCAL_DATABASE_URL", "").strip()
        if not db_local:
            caminho_db_local = projeto_dir / "tariel_admin.db"
            db_local = f"sqlite:///{caminho_db_local.as_posix()}"
        env["DATABASE_URL"] = db_local
        env["SEED_DEV_BOOTSTRAP"] = os.getenv("E2E_LOCAL_SEED_BOOTSTRAP", "0").strip() or "0"
    else:
        pasta_db = tmp_path_factory.mktemp("playwright_db")
        caminho_db = pasta_db / "tariel_playwright.sqlite3"
        env["SEED_DEV_BOOTSTRAP"] = "1"
        env["DATABASE_URL"] = f"sqlite:///{caminho_db.as_posix()}"

    # Para suites de stress local, garantimos usuários dedicados de carga
    # (inspetor A/B, revisor e admin) no mesmo banco do servidor E2E.
    if os.getenv("RUN_E2E_LOCAL", "0").strip() == "1":
        subprocess.run(
            [sys.executable, "scripts/seed_usuario_uso_intenso.py"],
            cwd=str(projeto_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
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
        cwd=str(projeto_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _aguardar_app(base_url)
        yield {
            "base_url": base_url,
            "database_url": env.get("DATABASE_URL") or None,
        }
    finally:
        if processo.poll() is None:
            processo.terminate()
            try:
                processo.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - caminho de limpeza
                processo.kill()
                processo.wait(timeout=5)


@pytest.fixture(scope="session")
def live_server_url(live_server_runtime: dict[str, str | None]) -> str:
    return str(live_server_runtime.get("base_url") or "")


@pytest.fixture(scope="session")
def live_server_database_url(live_server_runtime: dict[str, str | None]) -> str | None:
    database_url = live_server_runtime.get("database_url")
    return str(database_url) if database_url else None


@pytest.fixture(scope="session")
def credenciais_seed() -> dict[str, dict[str, str]]:
    return {
        "inspetor": {
            "email": "inspetor@tariel.ia",
            "senha": "Dev@123456",
        },
        "revisor": {
            "email": "revisor@tariel.ia",
            "senha": "Dev@123456",
        },
        "admin_cliente": {
            "email": "admin-cliente@tariel.ia",
            "senha": "Dev@123456",
        },
        "admin": {
            "email": "admin@tariel.ia",
            "senha": "Dev@123456",
        },
    }
