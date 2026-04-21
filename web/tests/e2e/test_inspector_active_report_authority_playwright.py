from __future__ import annotations

import os
import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.test_portais_playwright import (
    _api_fetch,
    _carregar_laudo_no_inspetor,
    _fazer_login,
)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_E2E", "0") != "1",
    reason="Defina RUN_E2E=1 para executar os testes Playwright.",
)


def test_e2e_query_laudo_e_home_forcada_preservam_contexto_autoritativo(
    page: Page,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    _fazer_login(
        page,
        base_url=live_server_url,
        portal="app",
        email=credenciais_seed["inspetor"]["email"],
        senha=credenciais_seed["inspetor"]["senha"],
        rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
    )

    resposta_inicio = _api_fetch(
        page,
        path="/app/api/laudo/iniciar",
        method="POST",
        form_body={"tipo_template": "padrao"},
    )
    assert resposta_inicio["status"] == 200
    laudo_id = int(resposta_inicio["body"]["laudo_id"])

    laudo_front = _carregar_laudo_no_inspetor(page, laudo_id)
    assert laudo_front == laudo_id

    resposta_chat = _api_fetch(
        page,
        path="/app/api/chat",
        method="POST",
        json_body={
            "mensagem": "/pendencias",
            "dados_imagem": "",
            "setor": "geral",
            "historico": [],
            "modo": "detalhado",
            "texto_documento": "",
            "nome_documento": "",
            "laudo_id": laudo_id,
        },
    )
    assert resposta_chat["status"] == 200

    status_ativo = _api_fetch(page, path="/app/api/laudo/status", method="GET")
    assert status_ativo["status"] == 200
    assert int(status_ativo["body"]["laudo_id"] or 0) == laudo_id

    page.goto(f"{live_server_url}/app/?home=1", wait_until="domcontentloaded")
    expect(page.locator("#tela-boas-vindas")).to_be_visible(timeout=10000)

    status_home = _api_fetch(page, path="/app/api/laudo/status", method="GET")
    assert status_home["status"] == 200
    assert int(status_home["body"]["laudo_id"] or 0) == laudo_id

    page.goto(f"{live_server_url}/app/?laudo={laudo_id}", wait_until="domcontentloaded")
    page.wait_for_function(
        """(idLaudo) => {
            const ativo = Number(
                window.TarielAPI?.obterLaudoAtualId?.() ||
                document.body?.dataset?.laudoAtualId ||
                0
            );
            return ativo === Number(idLaudo);
        }""",
        arg=laudo_id,
        timeout=10000,
    )

    status_query = _api_fetch(page, path="/app/api/laudo/status", method="GET")
    assert status_query["status"] == 200
    assert int(status_query["body"]["laudo_id"] or 0) == laudo_id
