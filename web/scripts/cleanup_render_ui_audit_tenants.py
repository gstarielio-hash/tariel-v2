from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.render_ui_user_journey import DEFAULT_BASE_URL, DEFAULT_RENDER_CACHE, JourneyRunner


def _extract_csrf(html: str) -> str:
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if not match:
        raise RuntimeError("CSRF não encontrado na página de configurações do Admin-CEO.")
    return match.group(1)


def _parse_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for item in str(raw or "").split(","):
        texto = item.strip()
        if not texto:
            continue
        ids.append(int(texto))
    return sorted({item for item in ids if item > 0})


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpa tenants temporários Tariel UI Audit em produção.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--render-cache", default=str(DEFAULT_RENDER_CACHE))
    parser.add_argument("--company-ids", default="46,47,48,49,50,51,52,53")
    parser.add_argument(
        "--reason",
        default="Limpeza operacional dos tenants temporários criados na auditoria UI de produção.",
    )
    args = parser.parse_args()

    render_cache = Path(args.render_cache).expanduser().resolve()
    runner = JourneyRunner(
        base_url=str(args.base_url),
        artifact_root=Path("/tmp/tariel_cleanup_artifacts"),
        render_cache_path=render_cache,
        headless=True,
        slow_mo_ms=0,
        pause_scale=0.2,
    )
    admin_email, admin_password = runner.read_render_credentials()
    company_ids = _parse_ids(args.company_ids)
    if not company_ids:
        raise RuntimeError("Informe ao menos um ID de empresa para limpar.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        runner.wire_page(page, "cleanup-ui-audit")
        runner.login_admin(page, email=admin_email, password=admin_password)

        page.goto(f"{runner.base_url}/admin/configuracoes", wait_until="domcontentloaded")
        csrf = _extract_csrf(page.content())

        payload = {
            "csrf_token": csrf,
            "company_ids": ",".join(str(item) for item in company_ids),
            "confirmation_phrase": "EXCLUIR TARIEL UI AUDIT",
            "motivo_operacao": str(args.reason),
        }
        resultado = page.evaluate(
            """async (payload) => {
                const body = new URLSearchParams(payload);
                const resposta = await fetch("/admin/configuracoes/manutencao/limpar-auditoria-ui", {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body,
                    redirect: "follow",
                });
                return {
                    ok: resposta.ok,
                    status: resposta.status,
                    url: resposta.url,
                    text: await resposta.text(),
                };
            }""",
            payload,
        )

        page.goto(f"{runner.base_url}/admin/clientes?nome=Tariel%20UI%20Audit", wait_until="domcontentloaded")
        html = page.content()
        remanescentes = [
            company_id
            for company_id in company_ids
            if f"/admin/clientes/{company_id}" in html
        ]

        browser.close()

    print(
        json.dumps(
            {
                "company_ids_requested": company_ids,
                "cleanup_response": {
                    "ok": bool(resultado.get("ok")),
                    "status": int(resultado.get("status") or 0),
                    "url": str(resultado.get("url") or ""),
                },
                "remaining_company_ids": remanescentes,
                "success_banner_present": "empresa(s) temporária(s) removida(s)" in str(resultado.get("text") or ""),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
