from __future__ import annotations

import os
import re
import time
import uuid
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, expect

from tests.e2e.conftest import _e2e_visual_ativo
from tests.e2e.test_portais_playwright import (
    _abrir_modal_nova_inspecao,
    _api_fetch,
    _confirmar_modal_nova_inspecao,
    _esperar_contexto_workspace_inspetor,
    _fazer_login,
    _obter_laudo_ativo,
    _preencher_modal_nova_inspecao,
)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_E2E", "0") != "1",
    reason="Defina RUN_E2E=1 para executar os testes Playwright.",
)

VISUAL_ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / ".test-artifacts" / "visual"


def _ler_env_ms(nome: str, padrao: int) -> int:
    bruto = os.getenv(nome, "").strip()
    if not bruto:
        return padrao
    try:
        return max(int(bruto), 0)
    except ValueError:
        return padrao


def _pause_ms_padrao() -> int:
    return _ler_env_ms("E2E_VISUAL_STEP_PAUSE_MS", 2600 if _e2e_visual_ativo() else 0)


def _pause_final_ms_padrao() -> int:
    return _ler_env_ms("E2E_VISUAL_FINAL_PAUSE_MS", 6500 if _e2e_visual_ativo() else 0)


def _aguardar_estabilidade_visual(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        page.wait_for_timeout(400)

    page.wait_for_function(
        """() => !document.fonts || document.fonts.status === "loaded" """,
        timeout=10000,
    )
    page.wait_for_timeout(300)


def _ocultar_overlay_visual(page: Page) -> None:
    page.evaluate(
        """() => {
            const overlay = document.getElementById("__tariel-e2e-visual-overlay");
            if (overlay) overlay.remove();
            const style = document.getElementById("__tariel-e2e-visual-style");
            if (style) style.remove();
            const reviewPanel = document.getElementById("__tariel-visual-review-panel");
            if (reviewPanel) reviewPanel.remove();
            const reviewStyle = document.getElementById("__tariel-visual-review-style");
            if (reviewStyle) reviewStyle.remove();
        }"""
    )


def _mostrar_guia_visual(page: Page, *, titulo: str, itens: list[str]) -> None:
    page.evaluate(
        """(payload) => {
            const STYLE_ID = "__tariel-visual-review-style";
            const PANEL_ID = "__tariel-visual-review-panel";

            let style = document.getElementById(STYLE_ID);
            if (!style) {
                style = document.createElement("style");
                style.id = STYLE_ID;
                style.textContent = `
                    #${STYLE_ID} {}
                    #${PANEL_ID} {
                        position: fixed;
                        left: 22px;
                        bottom: 22px;
                        z-index: 2147483646;
                        width: min(420px, calc(100vw - 44px));
                        padding: 16px 18px;
                        border-radius: 18px;
                        background: rgba(15, 23, 42, 0.94);
                        color: #f8fafc;
                        border: 1px solid rgba(148, 163, 184, 0.34);
                        box-shadow: 0 24px 50px rgba(15, 23, 42, 0.34);
                        font-family: "IBM Plex Sans", system-ui, sans-serif;
                    }
                    #${PANEL_ID} strong {
                        display: block;
                        margin-bottom: 8px;
                        font-size: 15px;
                        letter-spacing: 0.01em;
                    }
                    #${PANEL_ID} ul {
                        margin: 0;
                        padding-left: 18px;
                        display: grid;
                        gap: 6px;
                        font-size: 13px;
                        line-height: 1.45;
                        color: #dbe4ee;
                    }
                `;
                document.head.appendChild(style);
            }

            let panel = document.getElementById(PANEL_ID);
            if (!panel) {
                panel = document.createElement("aside");
                panel.id = PANEL_ID;
                document.body.appendChild(panel);
            }

            const tituloSeguro = String(payload?.titulo || "").trim();
            const itens = Array.isArray(payload?.itens) ? payload.itens : [];
            panel.innerHTML = `
                <strong>${tituloSeguro}</strong>
                <ul>${itens.map((item) => `<li>${String(item)}</li>`).join("")}</ul>
            `;
        }""",
        {"titulo": titulo, "itens": itens},
    )


def _pausar_observacao(page: Page, *, titulo: str, itens: list[str], pausa_ms: int | None = None) -> None:
    _mostrar_guia_visual(page, titulo=titulo, itens=itens)
    ms = _pause_ms_padrao() if pausa_ms is None else max(int(pausa_ms), 0)
    if ms > 0:
        page.wait_for_timeout(ms)


def _salvar_screenshot(page: Page, nome: str, *, seletor: str | None = None) -> Path:
    VISUAL_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    _ocultar_overlay_visual(page)
    _aguardar_estabilidade_visual(page)

    caminho = VISUAL_ARTIFACTS_DIR / f"{nome}.png"
    if seletor:
        alvo = page.locator(seletor)
        expect(alvo).to_be_visible(timeout=10000)
        alvo.screenshot(path=str(caminho))
    else:
        page.screenshot(path=str(caminho), full_page=True)

    print(f"[visual] screenshot salvo: {caminho}")
    assert caminho.exists()
    return caminho


def _garantir_landing_novo_chat(page: Page) -> None:
    assistant_landing = page.locator("#workspace-assistant-landing")
    if assistant_landing.is_visible():
        return

    botao_chat_livre = page.locator('[data-action="open-assistant-chat"]:visible').first
    expect(botao_chat_livre).to_be_visible(timeout=10000)
    botao_chat_livre.click()
    expect(assistant_landing).to_be_visible(timeout=10000)


def test_e2e_inspetor_exporta_referencias_visuais(
    browser: Browser,
    live_server_url: str,
    credenciais_seed: dict[str, dict[str, str]],
) -> None:
    contexto_kwargs: dict[str, object] = {"color_scheme": "light"}
    if _e2e_visual_ativo():
        contexto_kwargs["viewport"] = None
    else:
        contexto_kwargs["viewport"] = {"width": 1720, "height": 1240}

    contexto = browser.new_context(**contexto_kwargs)
    try:
        page = contexto.new_page()
        _fazer_login(
            page,
            base_url=live_server_url,
            portal="app",
            email=credenciais_seed["inspetor"]["email"],
            senha=credenciais_seed["inspetor"]["senha"],
            rota_sucesso_regex=rf"{re.escape(live_server_url)}/app/?$",
        )

        _pausar_observacao(
            page,
            titulo="Revisao 0: Portal do Inspetor",
            itens=[
                "altura do hero e proximidade das acoes principais",
                "peso visual da sidebar em relacao ao miolo",
                "densidade e proporcao dos KPIs",
                "consistencia de selecao nos cards e chips",
                "sensacao geral de portal operacional versus dashboard",
            ],
        )
        _salvar_screenshot(page, "00-inspetor-portal-home")

        page.locator("#btn-abrir-perfil-chat").click()
        expect(page.locator("#modal-perfil-chat")).to_be_visible(timeout=10000)
        _pausar_observacao(
            page,
            titulo="Revisao 0b: Modal Perfil",
            itens=[
                "contraste do titulo, labels e textos auxiliares",
                "coerencia com o modal Nova Inspecao",
                "proporcao entre avatar, campos e footer",
                "qualidade percebida do fundo, borda e sombra",
            ],
        )
        _salvar_screenshot(
            page,
            "05-inspetor-modal-perfil",
            seletor="#modal-perfil-chat .modal-container-perfil",
        )
        page.locator("#btn-fechar-modal-perfil").click()
        expect(page.locator("#modal-perfil-chat")).to_be_hidden(timeout=10000)

        _garantir_landing_novo_chat(page)
        _pausar_observacao(
            page,
            titulo="Revisao 1: Novo Chat",
            itens=[
                "hierarquia do hero e do composer",
                "respiro lateral e vertical da tela",
                "tamanho e peso da tipografia principal",
                "contraste entre fundo, botoes e textos",
                "transicao de entrada e sensacao geral do layout",
            ],
        )
        _salvar_screenshot(page, "01-inspetor-novo-chat")

        _abrir_modal_nova_inspecao(page)
        expect(page.locator("#modal-nova-inspecao")).to_be_visible(timeout=10000)
        contexto_inspecao = _preencher_modal_nova_inspecao(
            page,
            tipo_template="padrao",
            equipamento="Caldeira B-202",
            cliente="Petrobras",
            unidade="REPLAN - Paulínia",
            objetivo="Gerar referência visual consistente do workspace.",
        )
        _pausar_observacao(
            page,
            titulo="Revisao 2: Modal Nova Inspecao",
            itens=[
                "alinhamento entre titulo, texto e campos",
                "largura util do modal e distribuicao do formulario",
                "legibilidade dos labels, placeholders e selects",
                "cores de borda, hover, foco e selecao",
                "animacao de abertura e fechamento do painel",
            ],
        )
        _salvar_screenshot(
            page,
            "02-inspetor-modal-nova-inspecao",
            seletor="#modal-nova-inspecao .modal-container-nova-inspecao",
        )
        _confirmar_modal_nova_inspecao(page, validar_contexto_visual=False, **contexto_inspecao)

        laudo_id = _obter_laudo_ativo(page)
        expect(page.locator("#workspace-titulo-laudo")).to_have_text(contexto_inspecao["equipamento"])
        _pausar_observacao(
            page,
            titulo="Revisao 3: Workspace Conversa",
            itens=[
                "peso visual de sidebar, header, rail e composer",
                "espacamento entre mensagens, cards e controles",
                "fontes, tamanhos e altura de linha da conversa",
                "cores normais e ativas de tabs, chips e botoes",
                "fluidez das transicoes entre estados do workspace",
            ],
        )
        _salvar_screenshot(page, "03-inspetor-workspace-conversa")

        texto = f"Registro visual E2E {uuid.uuid4().hex[:8]}"
        resposta_chat = _api_fetch(
            page,
            path="/app/api/chat",
            method="POST",
            json_body={
                "mensagem": texto,
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

        prazo_historico = time.time() + 10.0
        historico_disponivel = False
        while time.time() < prazo_historico:
            historico = _api_fetch(
                page,
                path=f"/app/api/laudo/{laudo_id}/mensagens",
                method="GET",
            )
            itens = historico.get("body", {}).get("itens") if isinstance(historico.get("body"), dict) else None
            if historico.get("status") == 200 and isinstance(itens, list) and len(itens) >= 1:
                historico_disponivel = True
                break
            page.wait_for_timeout(250)
        assert historico_disponivel, "Histórico visual do laudo não ficou disponível a tempo."

        page.goto(
            f"{live_server_url}/app/?laudo={laudo_id}&aba=historico",
            wait_until="domcontentloaded",
        )
        _esperar_contexto_workspace_inspetor(
            page,
            laudo_id=laudo_id,
            aba="historico",
            view="inspection_history",
        )
        page.evaluate(
            """async (idLaudo) => {
                if (window.TarielAPI?.carregarLaudo) {
                    await window.TarielAPI.carregarLaudo(idLaudo, {
                        forcar: true,
                        silencioso: true,
                    });
                }
            }""",
            laudo_id,
        )
        expect(page.locator("#workspace-history-timeline")).to_be_visible(timeout=10000)
        expect(page.locator(".workspace-history-card__text").first).to_be_visible(timeout=10000)
        _pausar_observacao(
            page,
            titulo="Revisao 4: Workspace Historico",
            itens=[
                "foco de leitura da timeline no centro",
                "concorrencia visual entre historico e funcionalidades laterais",
                "tamanho da fonte e ritmo de leitura dos cards",
                "cores de filtro, selecao e estado ativo",
                "suavidade da troca entre conversa e historico",
            ],
        )
        _salvar_screenshot(page, "04-inspetor-workspace-historico")

        page.goto(
            f"{live_server_url}/app/?laudo={laudo_id}&aba=mesa",
            wait_until="domcontentloaded",
        )
        _esperar_contexto_workspace_inspetor(
            page,
            laudo_id=laudo_id,
            aba="mesa",
            view="inspection_mesa",
        )
        expect(page.locator("#painel-mesa-widget")).to_be_visible(timeout=10000)
        _pausar_observacao(
            page,
            titulo="Revisao 5: Workspace Mesa",
            itens=[
                "consistencia entre mesa tecnica e o resto do workspace",
                "peso do cabecalho versus conteudo util",
                "contraste dos textos, chips e mensagens",
                "qualidade do campo de resposta e das acoes da mesa",
            ],
        )
        _salvar_screenshot(page, "06-inspetor-workspace-mesa")
        pausa_final_ms = _pause_final_ms_padrao()
        if pausa_final_ms > 0:
            page.wait_for_timeout(pausa_final_ms)
    finally:
        contexto.close()
