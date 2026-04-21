# Inspetor - hardening de abas URL-first e historico canonico

Criado em `2026-04-01`.

## Objetivo

Fechar o slice residual do `inspetor` depois da reorganizacao do workspace focado, transformando as abas do workspace em estado URL-first verificavel e trocando a timeline de historico para uma fonte canonica vinda do payload do laudo, em vez de depender apenas do DOM ja montado.

## O que entrou

- o `chat_painel_core.js` passou a expor leitura e escrita explicitas de `?aba=` com `obterThreadTabDaURL()` e `definirThreadTabNaURL()`, preservando `history.state` junto com `laudo`;
- a selecao de laudo no `chat_painel_laudos.js` passou a carregar o workspace com `threadTab` explicito, inclusive em `boot` e `popstate`;
- o `chat_index_page.js` passou a tratar a aba do workspace como concern de navegacao URL-first, separada da autoridade do laudo/estado do backend;
- o resolver do inspetor agora considera `?aba=` antes de cair no dataset legado, evitando cair sempre em `historico` no reload de `mesa` e `anexos`;
- a timeline de `Histórico` passou a consumir o payload canonico de `window.TarielAPI.obterHistoricoLaudoAtual()` e do evento `tariel:historico-laudo-renderizado`, com fallback apenas para registros transientes do DOM;
- os cards do historico ganharam suporte a anexos canonicos, classificacao por ator/tipo e metadados recolhiveis da IA;
- a suite browser ganhou cobertura especifica para deep link de aba, reload, back/forward e leitura do historico tecnico no novo workspace.

## Hotspots desta rodada

- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/chat/chat_index_page.js`
- `web/static/css/inspetor/reboot.css`
- `web/tests/e2e/test_portais_playwright.py`
- `web/tests/test_smoke.py`

## Validacao executada

Checks de sintaxe:

```bash
node --check web/static/js/chat/chat_painel_core.js
node --check web/static/js/chat/chat_painel_laudos.js
node --check web/static/js/chat/chat_index_page.js
```

Recortes focais:

```bash
pytest tests/test_smoke.py -q -k templates_chat_mantem_controles_essenciais_de_ui
pytest tests/test_inspector_active_report_authority.py -q
```

Resultado:

- `4 passed`

Recorte browser:

```bash
env RUN_E2E=1 pytest tests/e2e/test_inspector_active_report_authority_playwright.py -q
env RUN_E2E=1 pytest tests/e2e/test_portais_playwright.py -q -k 'inspetor_abas_workspace_preservam_url_reload_e_historico or inspetor_historico_workspace_usa_payload_canonico_e_filtros or widget_mesa_so_abre_com_inspecao_ativa or widget_mesa_envia_mensagem_via_ui_e_persiste or historico_pin_unpin_e_excluir_laudo' -rs
```

Resultado:

- `6 passed, 34 deselected`

## O que isso fecha

- o `inspetor` deixa de depender de `threadTab` apenas como estado efemero do runtime;
- `historico`, `anexos` e `mesa` passam a sobreviver a deep link, reload e back/forward com URL explicita;
- a timeline de historico deixa de ser so uma leitura do DOM atual e passa a refletir o payload canonico do laudo quando ele existe;
- o workspace focado fica fechado tambem como checkpoint de endurecimento, nao apenas como reorganizacao visual.

## O que continua fora

- redesign premium amplo do `inspetor` fora deste workspace;
- API nova dedicada so para timeline tecnica do historico;
- reabertura de contratos de auth, sessao ou backend sensivel por causa desta navegacao.

## Leitura final

O `inspetor` agora fecha melhor a propria promessa de workspace focado: a aba ativa virou estado navegavel e recuperavel, e o modo `Histórico` deixou de depender do que sobrou renderizado no centro da tela. O que sobra daqui para frente ja nao e hardening estrutural do workspace, e sim evolucao opcional de UX e produto.
