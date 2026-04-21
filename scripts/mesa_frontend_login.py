#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import http.cookiejar
import re
import sys
import urllib.parse
import urllib.request


def _csrf_from_html(body: str) -> str:
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', body)
    if not match:
        raise RuntimeError("Nao foi possivel localizar csrf_token na tela de login.")
    return html.unescape(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Obtém a cookie de sessão do portal /revisao para o frontend Next local.",
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--senha", required=True)
    args = parser.parse_args()

    base_url = str(args.base_url).rstrip("/")
    login_url = f"{base_url}/revisao/login"
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    with opener.open(login_url, timeout=8) as response:
        body = response.read().decode("utf-8", errors="replace")

    csrf_token = _csrf_from_html(body)
    payload = urllib.parse.urlencode(
        {
          "email": args.email,
          "senha": args.senha,
          "csrf_token": csrf_token,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        login_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": login_url,
        },
    )

    with opener.open(request, timeout=8) as response:
        final_url = response.geturl()

    if final_url.endswith("/revisao/trocar-senha"):
        raise RuntimeError(
            "O usuario caiu em troca obrigatoria de senha; use uma conta seed pronta ou forneça MESA_BACKEND_COOKIE."
        )

    cookies = [f"{cookie.name}={cookie.value}" for cookie in jar]
    if not cookies:
        raise RuntimeError("Nenhuma cookie de sessao foi criada pelo login do revisor.")

    sys.stdout.write("; ".join(cookies))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - script operacional
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
