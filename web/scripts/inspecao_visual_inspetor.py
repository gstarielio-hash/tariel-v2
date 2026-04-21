from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from PIL import Image, ImageChops
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "visual" / "inspetor"
DEFAULT_CREDENTIALS = {
    "email": "inspetor@tariel.ia",
    "senha": "Dev@123456",
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
  const limit = 16;
  const minTarget = (window.matchMedia("(pointer: coarse)").matches || window.innerWidth <= 768) ? 40 : 36;
  const selectorFor = (el) => {
    if (!el || !(el instanceof Element)) return "";
    if (el.id) return `#${el.id}`;
    const classes = Array.from(el.classList || []).slice(0, 3).join(".");
    return `${el.tagName.toLowerCase()}${classes ? "." + classes : ""}`;
  };

  const isVisible = (el) => {
    if (!(el instanceof Element)) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity || "1") === 0) {
      return false;
    }
    const rect = el.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  };

  const textSample = (el) => (el.textContent || "").replace(/\\s+/g, " ").trim().slice(0, 80);
  const shouldIgnoreClip = (el, selector) => {
    if (!el || !(el instanceof Element)) return true;
    if (["HTML", "BODY"].includes(el.tagName)) return true;
    if (selector === "#painel-chat" || selector === "div.container-app") return true;
    const style = window.getComputedStyle(el);
    if (["auto", "scroll"].includes(style.overflowX) || ["auto", "scroll"].includes(style.overflowY)) {
      return true;
    }
    return false;
  };

  const visible = Array.from(document.querySelectorAll("body *")).filter(isVisible);
  const offscreen = [];
  const clipped = [];
  const tinyTargets = [];
  const duplicateIds = [];
  const seenIds = new Map();

  for (const el of visible) {
    const rect = el.getBoundingClientRect();
    if ((rect.left < -1 || rect.right > window.innerWidth + 1) && offscreen.length < limit) {
      offscreen.push({
        selector: selectorFor(el),
        text: textSample(el),
        left: Math.round(rect.left),
        right: Math.round(rect.right),
        width: Math.round(rect.width),
      });
    }

    const style = window.getComputedStyle(el);
    const clipsX = ["hidden", "clip"].includes(style.overflowX) || ["hidden", "clip"].includes(style.textOverflow);
    const clipsY = ["hidden", "clip"].includes(style.overflowY);
    const hasText = textSample(el).length > 0;
    const selector = selectorFor(el);
    if (
      hasText &&
      !shouldIgnoreClip(el, selector) &&
      ((clipsX && el.scrollWidth > el.clientWidth + 4) || (clipsY && el.scrollHeight > el.clientHeight + 4)) &&
      clipped.length < limit
    ) {
      clipped.push({
        selector,
        text: textSample(el),
        clientWidth: el.clientWidth,
        scrollWidth: el.scrollWidth,
        clientHeight: el.clientHeight,
        scrollHeight: el.scrollHeight,
      });
    }

    const clickable = el.matches("button, a, input, textarea, select, [role='button'], [tabindex]");
    if (!clickable) continue;

    if (el.matches("input, textarea, select")) {
      const parent = el.parentElement;
      if (parent instanceof Element) {
        const parentRect = parent.getBoundingClientRect();
        if (parentRect.width >= rect.width && parentRect.height >= minTarget) {
          continue;
        }
      }
    }

    if ((rect.width < minTarget || rect.height < minTarget) && tinyTargets.length < limit) {
      tinyTargets.push({
        selector,
        text: textSample(el),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      });
    }
  }

  Array.from(document.querySelectorAll("[id]")).forEach((el) => {
    const current = seenIds.get(el.id) || 0;
    seenIds.set(el.id, current + 1);
  });
  for (const [id, count] of seenIds.entries()) {
    if (count > 1 && duplicateIds.length < limit) {
      duplicateIds.push({ id, count });
    }
  }

  return {
    viewport: { width: window.innerWidth, height: window.innerHeight },
    document: {
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
    },
    horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    offscreen,
    clipped,
    tinyTargets,
    duplicateIds,
    focus: {
      active: selectorFor(document.activeElement),
    },
    openDialogs: Array.from(document.querySelectorAll('[role="dialog"], dialog, .modal-overlay.ativo'))
      .filter(isVisible)
      .slice(0, limit)
      .map((el) => selectorFor(el)),
  };
}
"""


@dataclass
class ScreenshotResult:
    slug: str
    label: str
    image_path: str
    full_page: bool
    viewport: dict[str, int]
    audit: dict[str, Any]


def _slugify(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("_", "-")
        .replace("--", "-")
    )


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


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
    pasta_db = Path(tempfile.mkdtemp(prefix="inspetor_visual_db_"))
    caminho_db = pasta_db / "tariel_visual.sqlite3"

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


def _api_fetch(
    page: Page,
    *,
    path: str,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    form_body: dict[str, str] | None = None,
) -> dict[str, Any]:
    csrf_meta = page.locator('meta[name="csrf-token"]').first
    csrf_token = csrf_meta.get_attribute("content") if csrf_meta.count() else ""
    if not csrf_token:
        token_input = page.locator('input[name="csrf_token"]').first
        csrf_token = token_input.input_value() if token_input.count() else ""

    headers: dict[str, str] = {}
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token

    kwargs: dict[str, Any] = {
        "method": method.upper(),
        "headers": headers,
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        kwargs["data"] = json.dumps(json_body, ensure_ascii=False)
    elif form_body is not None:
        kwargs["form"] = form_body

    resposta = page.request.fetch(urljoin(page.url, path), **kwargs)
    return {
        "status": resposta.status,
        "ok": resposta.ok,
        "url": resposta.url,
        "body": resposta.json() if "application/json" in resposta.headers.get("content-type", "") else resposta.text(),
    }


def _fazer_login(
    page: Page,
    *,
    base_url: str,
    portal: str = "app",
    email: str,
    senha: str,
    rota_sucesso_regex: str = r"/app/?(?:\?.*)?$",
) -> None:
    page.goto(f"{base_url}/{portal}/login", wait_until="domcontentloaded")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="senha"]').fill(senha)
    page.locator('button[type="submit"]').first.click()
    page.wait_for_url(lambda url: __import__("re").search(rota_sucesso_regex, url) is not None, timeout=15000)
    page.wait_for_function(
        """() => Boolean(
            window.TarielInspetorRuntime &&
            document.getElementById("painel-chat") &&
            (
                document.querySelector("#workspace-assistant-landing:not([hidden])") ||
                document.querySelector("[data-open-inspecao-modal]:not([hidden])") ||
                document.querySelector("#btn-abrir-modal-novo:not([hidden])")
            )
        )"""
    )


def _preencher_modal_nova_inspecao(
    page: Page,
    *,
    tipo_template: str = "padrao",
    equipamento: str = "Caldeira B-202",
    cliente: str = "Petrobras",
    unidade: str = "REPLAN - Paulínia",
    objetivo: str = "",
) -> dict[str, str]:
    page.locator("#select-template-inspecao").select_option(tipo_template, force=True)
    page.locator("#input-local-inspecao").fill(equipamento)
    page.locator("#input-cliente-inspecao").fill(cliente)
    page.locator("#input-unidade-inspecao").fill(unidade)
    page.locator("#textarea-objetivo-inspecao").fill(objetivo)
    return {
        "equipamento": equipamento,
        "cliente": cliente,
        "unidade": unidade,
        "objetivo": objetivo,
    }


def _confirmar_modal_nova_inspecao(page: Page) -> None:
    page.locator("#btn-confirmar-inspecao").click()
    page.locator("#painel-chat").wait_for(state="visible")
    page.wait_for_function(
        """() => document.getElementById("painel-chat")?.getAttribute("data-inspecao-ui") === "workspace" """,
        timeout=15000,
    )
    page.locator("#workspace-titulo-laudo").wait_for(state="visible")


def _abrir_modal_nova_inspecao(page: Page) -> None:
    candidatos = (
        "#workspace-assistant-landing [aria-controls='modal-nova-inspecao']",
        "#workspace-assistant-landing [data-open-inspecao-modal]",
        "#btn-workspace-open-inspecao-modal",
        "#btn-abrir-modal-novo",
        "[data-open-inspecao-modal]",
        "[aria-controls='modal-nova-inspecao']",
    )
    modal = page.locator("#modal-nova-inspecao")

    for seletor in candidatos:
        locator = page.locator(seletor)
        total = locator.count()
        if not total:
            continue
        for indice in range(total):
            gatilho = locator.nth(indice)
            if not gatilho.is_visible():
                continue
            gatilho.scroll_into_view_if_needed()
            gatilho.click(force=True)
            try:
                modal.wait_for(state="visible", timeout=4000)
                return
            except Exception:
                continue
    raise RuntimeError("Não foi possível localizar um gatilho visível para o modal de nova inspeção.")


def _abrir_home_explicita(page: Page) -> None:
    if page.locator("#btn-shell-home").count():
        page.evaluate("() => document.getElementById('btn-shell-home')?.click()")
        page.wait_for_timeout(250)
        if page.locator("#tela-boas-vindas").count():
            page.locator("#tela-boas-vindas").wait_for(state="visible", timeout=8000)
            return
    if page.locator("a[href='/app/']").first.count():
        page.locator("a[href='/app/']").first.click()
        page.wait_for_timeout(250)
        if page.locator("#tela-boas-vindas").count():
            page.locator("#tela-boas-vindas").wait_for(state="visible", timeout=8000)
            return
    raise RuntimeError("Não foi possível abrir a home explícita do portal.")


def _abrir_workspace_novo_laudo(page: Page) -> None:
    _abrir_modal_nova_inspecao(page)
    _preencher_modal_nova_inspecao(page)
    _confirmar_modal_nova_inspecao(page)


def _obter_laudo_ativo(page: Page) -> int:
    deadline = time.time() + 12.0
    while time.time() < deadline:
        laudo_id = int(
            page.evaluate(
                "() => Number(window.TarielAPI?.obterLaudoAtualId?.() || document.body?.dataset?.laudoAtualId || 0)"
            )
        )
        if laudo_id > 0:
            return laudo_id

        try:
            status = _api_fetch(page, path="/app/api/laudo/status", method="GET")
            body = status.get("body")
            if status.get("status") == 200 and isinstance(body, dict):
                laudo_status = int(body.get("laudo_id") or 0)
                if laudo_status > 0:
                    return laudo_status
        except Exception:
            pass

        page.wait_for_timeout(250)

    raise RuntimeError("Laudo ativo não foi disponibilizado no front.")


def _forcar_estado_relatorio_workspace(page: Page, laudo_id: int, *, estado: str = "relatorio_ativo") -> None:
    page.evaluate(
        """async (payload) => {
            if (window.TarielAPI?.carregarLaudo) {
                await window.TarielAPI.carregarLaudo(payload.laudoId, { forcar: true, silencioso: true });
            }
            if (window.TarielAPI?.setLaudoAtualId) {
                window.TarielAPI.setLaudoAtualId(payload.laudoId);
            }
            if (window.TarielAPI?.setEstadoRelatorio) {
                window.TarielAPI.setEstadoRelatorio(payload.estado);
            }
            document.body.dataset.laudoAtualId = String(payload.laudoId);
            document.body.dataset.estadoRelatorio = String(payload.estado);
            document.dispatchEvent(new CustomEvent("tariel:estado-relatorio", {
                detail: {
                    estado: payload.estado,
                    laudo_id: payload.laudoId,
                    laudoId: payload.laudoId,
                },
                bubbles: true,
            }));
        }""",
        {"estado": estado, "laudoId": laudo_id},
    )
    page.wait_for_timeout(250)


def _aceitar_proximo_dialogo(page: Page) -> None:
    page.once("dialog", lambda dialog: dialog.accept())


def _injetar_estilo_estavel(page: Page) -> None:
    page.add_style_tag(content=DISABLE_MOTION_STYLE)
    page.wait_for_function("() => document.fonts ? document.fonts.status === 'loaded' : true")
    page.wait_for_timeout(250)


def _coletar_auditoria(page: Page) -> dict[str, Any]:
    return page.evaluate(DOM_AUDIT_SCRIPT)


def _salvar_screenshot(
    page: Page,
    *,
    output_dir: Path,
    slug: str,
    label: str,
    full_page: bool,
) -> ScreenshotResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / f"{slug}.png"
    _injetar_estilo_estavel(page)
    page.screenshot(path=str(image_path), full_page=full_page)
    audit = _coletar_auditoria(page)
    viewport = {
        "width": int(page.viewport_size["width"]),
        "height": int(page.viewport_size["height"]),
    }
    return ScreenshotResult(
        slug=slug,
        label=label,
        image_path=str(image_path),
        full_page=full_page,
        viewport=viewport,
        audit=audit,
    )


def _comparar_imagens(baseline_path: Path, current_path: Path, diff_path: Path) -> dict[str, Any]:
    with Image.open(baseline_path).convert("RGBA") as base_img, Image.open(current_path).convert("RGBA") as current_img:
        if base_img.size != current_img.size:
            return {
                "matched": False,
                "reason": "size_mismatch",
                "baseline_size": list(base_img.size),
                "current_size": list(current_img.size),
            }

        diff = ImageChops.difference(base_img, current_img)
        bbox = diff.getbbox()
        if bbox is None:
            return {
                "matched": True,
                "changed_pixels": 0,
                "change_ratio": 0.0,
                "diff_path": None,
            }

        mask = diff.convert("L").point(lambda v: 255 if v else 0)
        changed_pixels = sum(1 for pixel in mask.getdata() if pixel)
        total_pixels = base_img.size[0] * base_img.size[1]
        change_ratio = changed_pixels / total_pixels if total_pixels else 0.0

        highlight = current_img.copy()
        overlay = Image.new("RGBA", current_img.size, (255, 0, 0, 0))
        overlay.putalpha(mask)
        highlight = Image.alpha_composite(highlight, overlay)
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        highlight.save(diff_path)

        return {
            "matched": False,
            "changed_pixels": changed_pixels,
            "change_ratio": round(change_ratio, 6),
            "diff_path": str(diff_path),
            "bbox": list(bbox),
        }


def _gerar_galeria(output_dir: Path, report: dict[str, Any]) -> None:
    html_parts = [
        "<!doctype html>",
        "<html lang='pt-BR'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>Inspecao Visual Inspetor</title>",
        "<style>",
        "body { font-family: system-ui, sans-serif; margin: 24px; background: #0f172a; color: #e2e8f0; }",
        "h1, h2 { margin: 0 0 12px; }",
        ".meta { margin-bottom: 24px; color: #94a3b8; }",
        ".grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 24px; }",
        ".card { background: #111827; border: 1px solid #243041; border-radius: 16px; padding: 16px; }",
        ".card img { width: 100%; height: auto; border-radius: 12px; border: 1px solid #334155; background: #fff; }",
        ".bad { color: #fca5a5; }",
        ".ok { color: #86efac; }",
        "code { font-size: 13px; }",
        ".audit { margin-top: 12px; font-size: 14px; line-height: 1.5; }",
        ".audit ul { padding-left: 18px; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>Inspecao Visual Inspetor</h1><p class='meta'>Gerado em {report['generated_at']} | Base URL: <code>{report['base_url']}</code></p>",
        "<div class='grid'>",
    ]

    for shot in report["screenshots"]:
        image_rel = os.path.relpath(shot["image_path"], output_dir)
        comparison = shot.get("comparison")
        html_parts.append("<section class='card'>")
        html_parts.append(f"<h2>{shot['label']}</h2>")
        html_parts.append(f"<p><code>{shot['slug']}</code></p>")
        html_parts.append(f"<img src='{image_rel}' alt='{shot['label']}'>")
        html_parts.append("<div class='audit'>")
        html_parts.append(
            f"<p>Viewport: <code>{shot['viewport']['width']}x{shot['viewport']['height']}</code> | Full page: <code>{str(shot['full_page']).lower()}</code></p>"
        )
        overflow_horizontal = bool(shot["audit"]["horizontalOverflow"])
        overflow_class = "bad" if overflow_horizontal else "ok"
        overflow_label = "sim" if overflow_horizontal else "nao"
        html_parts.append(
            f"<p>Overflow horizontal: <strong class='{overflow_class}'>{overflow_label}</strong></p>"
        )
        offscreen_total = len(shot["audit"]["offscreen"])
        clipped_total = len(shot["audit"]["clipped"])
        tiny_targets_total = len(shot["audit"]["tinyTargets"])
        html_parts.append(
            "<p>"
            f"Offscreen: <code>{offscreen_total}</code> | "
            f"Clipped: <code>{clipped_total}</code> | "
            f"Tiny targets: <code>{tiny_targets_total}</code>"
            "</p>"
        )
        if comparison:
            if comparison.get("matched"):
                html_parts.append("<p class='ok'>Baseline: sem diferencas.</p>")
            else:
                diff_path = comparison.get("diff_path")
                if diff_path:
                    diff_rel = os.path.relpath(diff_path, output_dir)
                    html_parts.append(
                        (
                            f"<p class='bad'>Baseline: {comparison.get('change_ratio', 'n/a')} "
                            f"de pixels alterados.</p><img src='{diff_rel}' alt='Diff {shot['label']}'>"
                        )
                    )
                else:
                    html_parts.append(f"<p class='bad'>Baseline: {comparison.get('reason', 'diferenca')}.</p>")
        html_parts.append("</div></section>")

    html_parts.extend(["</div>", "</body>", "</html>"])
    (output_dir / "index.html").write_text("\n".join(html_parts), encoding="utf-8")


def _contexto_desktop(browser: Browser) -> BrowserContext:
    return browser.new_context(
        viewport={"width": 1440, "height": 1100},
        locale="pt-BR",
        color_scheme="light",
        service_workers="block",
    )


def _contexto_mobile(browser: Browser) -> BrowserContext:
    return browser.new_context(
        viewport={"width": 390, "height": 844},
        locale="pt-BR",
        color_scheme="light",
        is_mobile=True,
        has_touch=True,
        service_workers="block",
    )


def _anexar_coleta_erros(page: Page, collector: dict[str, list[str]]) -> None:
    page.on("pageerror", lambda exc: collector["pageerror"].append(str(exc)))
    page.on(
        "console",
        lambda msg: collector["console"].append(f"{msg.type}: {msg.text}")
        if msg.type in {"error", "warning"}
        else None,
    )


def _capturar_fluxo_desktop(
    *,
    playwright: Playwright,
    base_url: str,
    output_dir: Path,
    credentials: dict[str, str],
    collector: dict[str, list[str]],
) -> list[ScreenshotResult]:
    browser = playwright.chromium.launch(headless=True)
    context = _contexto_desktop(browser)
    page = context.new_page()
    _anexar_coleta_erros(page, collector)

    results: list[ScreenshotResult] = []
    try:
        _fazer_login(page, base_url=base_url, email=credentials["email"], senha=credentials["senha"])
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="desktop-chat-inicial",
                label="Desktop Chat Inicial",
                full_page=True,
            )
        )

        _abrir_home_explicita(page)
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="desktop-home-explicita",
                label="Desktop Home Explicita",
                full_page=True,
            )
        )
        page.goto(f"{base_url}/app/", wait_until="domcontentloaded")
        page.wait_for_function(
            """() => document.getElementById("painel-chat")?.getAttribute("data-inspecao-ui") === "workspace" """,
            timeout=15000,
        )

        _abrir_modal_nova_inspecao(page)
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="desktop-modal-nova-inspecao",
                label="Desktop Modal Nova Inspecao",
                full_page=False,
            )
        )

        _preencher_modal_nova_inspecao(page)
        _confirmar_modal_nova_inspecao(page)
        laudo_id = _obter_laudo_ativo(page)
        _forcar_estado_relatorio_workspace(page, laudo_id)
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="desktop-workspace",
                label="Desktop Workspace",
                full_page=False,
            )
        )

        page.locator("#btn-mesa-widget-toggle").click()
        page.locator("#painel-mesa-widget").wait_for(state="visible")
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="desktop-workspace-mesa",
                label="Desktop Workspace Mesa",
                full_page=False,
            )
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)

        page.wait_for_function("() => Boolean(document.getElementById('btn-abrir-perfil-chat'))")
        page.evaluate("() => document.getElementById('btn-abrir-perfil-chat')?.click()")
        page.locator("#modal-perfil-chat").wait_for(state="visible")
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="desktop-modal-perfil",
                label="Desktop Modal Perfil",
                full_page=False,
            )
        )
        page.locator("#btn-fechar-modal-perfil").click()
        page.locator("#modal-perfil-chat").wait_for(state="hidden")

        _aceitar_proximo_dialogo(page)
        if page.locator("#btn-finalizar-inspecao").is_visible():
            page.locator("#btn-finalizar-inspecao").click()
        else:
            page.evaluate(
                """async () => {
                    if (typeof window.finalizarInspecaoCompleta === "function") {
                        await window.finalizarInspecaoCompleta();
                    }
                }"""
            )
        page.locator("#modal-gate-qualidade").wait_for(state="visible", timeout=12000)
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="desktop-gate-qualidade",
                label="Desktop Gate Qualidade",
                full_page=False,
            )
        )
    finally:
        context.close()
        browser.close()
    return results


def _capturar_fluxo_mobile(
    *,
    playwright: Playwright,
    base_url: str,
    output_dir: Path,
    credentials: dict[str, str],
    collector: dict[str, list[str]],
) -> list[ScreenshotResult]:
    browser = playwright.chromium.launch(headless=True)
    context = _contexto_mobile(browser)
    page = context.new_page()
    _anexar_coleta_erros(page, collector)

    results: list[ScreenshotResult] = []
    try:
        _fazer_login(page, base_url=base_url, email=credentials["email"], senha=credentials["senha"])
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="mobile-chat-inicial",
                label="Mobile Chat Inicial",
                full_page=True,
            )
        )

        _abrir_home_explicita(page)
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="mobile-home-explicita",
                label="Mobile Home Explicita",
                full_page=True,
            )
        )
        page.goto(f"{base_url}/app/", wait_until="domcontentloaded")
        page.wait_for_function(
            """() => document.getElementById("painel-chat")?.getAttribute("data-inspecao-ui") === "workspace" """,
            timeout=15000,
        )

        _abrir_workspace_novo_laudo(page)
        laudo_id = _obter_laudo_ativo(page)
        _forcar_estado_relatorio_workspace(page, laudo_id)
        results.append(
            _salvar_screenshot(
                page,
                output_dir=output_dir,
                slug="mobile-workspace",
                label="Mobile Workspace",
                full_page=True,
            )
        )
    finally:
        context.close()
        browser.close()
    return results


def _aplicar_baseline(
    *,
    screenshots: list[dict[str, Any]],
    output_dir: Path,
    baseline_dir: Path | None,
    replace_baseline_dir: Path | None,
) -> None:
    if baseline_dir:
        for shot in screenshots:
            baseline_path = baseline_dir / Path(shot["image_path"]).name
            if not baseline_path.exists():
                shot["comparison"] = {"matched": False, "reason": "baseline_missing"}
                continue
            diff_path = output_dir / "diffs" / baseline_path.name
            shot["comparison"] = _comparar_imagens(baseline_path, Path(shot["image_path"]), diff_path)

    if replace_baseline_dir:
        replace_baseline_dir.mkdir(parents=True, exist_ok=True)
        for shot in screenshots:
            shutil.copy2(shot["image_path"], replace_baseline_dir / Path(shot["image_path"]).name)


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Inspecao Visual do Inspetor",
        "",
        f"- Gerado em: `{report['generated_at']}`",
        f"- Base URL: `{report['base_url']}`",
        f"- Page errors: `{len(report['errors']['pageerror'])}`",
        f"- Console warnings/errors: `{len(report['errors']['console'])}`",
        "",
        "## Capturas",
        "",
    ]

    for shot in report["screenshots"]:
        lines.append(f"### {shot['label']}")
        lines.append(f"- Arquivo: `{shot['image_path']}`")
        lines.append(f"- Viewport: `{shot['viewport']['width']}x{shot['viewport']['height']}`")
        lines.append(f"- Overflow horizontal: `{'sim' if shot['audit']['horizontalOverflow'] else 'nao'}`")
        lines.append(f"- Elementos fora da viewport: `{len(shot['audit']['offscreen'])}`")
        lines.append(f"- Possivel clipping: `{len(shot['audit']['clipped'])}`")
        lines.append(f"- Tiny targets: `{len(shot['audit']['tinyTargets'])}`")
        comparison = shot.get("comparison")
        if comparison:
            lines.append(f"- Baseline: `{json.dumps(comparison, ensure_ascii=False)}`")
        lines.append("")

    if report["errors"]["pageerror"]:
        lines.append("## Page Errors")
        lines.append("")
        for item in report["errors"]["pageerror"]:
            lines.append(f"- `{item}`")
        lines.append("")

    if report["errors"]["console"]:
        lines.append("## Console")
        lines.append("")
        for item in report["errors"]["console"]:
            lines.append(f"- `{item}`")
        lines.append("")

    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Captura e compara estados visuais do Portal do Inspetor.")
    parser.add_argument("--base-url", default="", help="URL base já em execução. Se omitida, o script sobe um servidor local temporário.")
    parser.add_argument("--output-dir", default="", help="Diretório de saída das capturas.")
    parser.add_argument("--baseline-dir", default="", help="Diretório com PNGs baseline para comparação.")
    parser.add_argument("--replace-baseline-dir", default="", help="Atualiza este diretório com as imagens capturadas.")
    parser.add_argument("--email", default=DEFAULT_CREDENTIALS["email"], help="Usuário do inspetor.")
    parser.add_argument("--senha", default=DEFAULT_CREDENTIALS["senha"], help="Senha do inspetor.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_ROOT / _now_stamp()
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_dir = Path(args.baseline_dir) if args.baseline_dir else None
    replace_baseline_dir = Path(args.replace_baseline_dir) if args.replace_baseline_dir else None
    credentials = {"email": args.email, "senha": args.senha}
    collector = {"pageerror": [], "console": []}

    with _servidor_local(args.base_url.strip() or None) as (base_url, _processo), sync_playwright() as playwright:
        screenshots: list[ScreenshotResult] = []
        screenshots.extend(
            _capturar_fluxo_desktop(
                playwright=playwright,
                base_url=base_url,
                output_dir=output_dir,
                credentials=credentials,
                collector=collector,
            )
        )
        screenshots.extend(
            _capturar_fluxo_mobile(
                playwright=playwright,
                base_url=base_url,
                output_dir=output_dir,
                credentials=credentials,
                collector=collector,
            )
        )

    serialized_shots = [
        {
            "slug": shot.slug,
            "label": shot.label,
            "image_path": shot.image_path,
            "full_page": shot.full_page,
            "viewport": shot.viewport,
            "audit": shot.audit,
        }
        for shot in screenshots
    ]
    _aplicar_baseline(
        screenshots=serialized_shots,
        output_dir=output_dir,
        baseline_dir=baseline_dir,
        replace_baseline_dir=replace_baseline_dir,
    )

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": args.base_url.strip() or "temp-local-server",
        "screenshots": serialized_shots,
        "errors": collector,
    }
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "report.md").write_text(_markdown_report(report), encoding="utf-8")
    _gerar_galeria(output_dir, report)

    print(f"Capturas geradas em: {output_dir}")
    print(f"Galeria HTML: {output_dir / 'index.html'}")
    print(f"Relatório JSON: {output_dir / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
