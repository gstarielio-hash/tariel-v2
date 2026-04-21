# Pacote de Entendimento do Chat Inspetor

Este diretório documenta o sistema "Chat Inspetor" sem alterar o produto. O objetivo é permitir que outra IA, ou um engenheiro entrando no código agora, entenda a UI, os modos de tela, o fluxo de runtime, as integrações backend e os pontos frágeis antes de propor qualquer mudança.

## Resumo Executivo

O Chat Inspetor é o portal principal do usuário inspetor em `web/templates/index.html`, servido por `/app/`, com shell SSR e hidratação client-side. O runtime combina:

- SSR inicial em `web/app/domains/chat/auth_portal_routes.py` e `web/templates/inspetor/*.html`
- controlador de tela em `web/static/js/chat/chat_index_page.js`
- núcleo de estado legado/compartilhado em `web/static/js/chat/chat_painel_core.js`
- ponte de API e histórico em `web/static/js/shared/api.js`
- rede/SSE em `web/static/js/shared/chat-network.js` e `web/static/js/inspetor/notifications_sse.js`
- layout visual em `web/static/css/inspetor/reboot.css`, `web/static/css/shared/official_visual_system.css` e nos slices `web/static/css/inspetor/workspace_{chrome,history,rail,states}.css`

O sistema opera em cinco modos confirmados no código:

- `portal_dashboard`
- `assistant_landing`
- `new_inspection`
- `inspection_record`
- `inspection_conversation`

## Arquivos Mais Críticos do Sistema

- `web/templates/index.html`
- `web/templates/inspetor/_portal_main.html`
- `web/templates/inspetor/_workspace.html`
- `web/templates/inspetor/workspace/_workspace_header.html`
- `web/templates/inspetor/workspace/_workspace_toolbar.html`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-network.js`
- `web/static/js/shared/ui.js`
- `web/static/css/inspetor/reboot.css`
- `web/app/domains/chat/auth_portal_routes.py`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/mesa.py`
- `web/app/domains/chat/pendencias.py`

## Autoridades Principais

### Autoridades de layout

- `web/templates/inspetor/_portal_main.html`
- `web/templates/inspetor/_workspace.html`
- `web/templates/inspetor/workspace/_workspace_header.html`
- `web/templates/inspetor/workspace/_workspace_toolbar.html`
- `web/static/css/inspetor/reboot.css`

### Autoridades de navegação

- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_painel_laudos.js`

### Autoridades de estado

- servidor: `web/app/domains/chat/session_helpers.py`
- cliente, estado global legado: `web/static/js/chat/chat_painel_core.js`
- cliente, bridge/API/histórico: `web/static/js/shared/api.js`
- cliente, screen mode/UI: `web/static/js/chat/chat_index_page.js`

## Como Ler Este Pacote

1. Comece por `10_FOR_CHATGPT.md` se o objetivo é entregar contexto rápido a outra IA.
2. Leia `01_system_overview.md` e `03_screen_modes_and_user_flows.md` para entender a experiência ponta a ponta.
3. Use `04_frontend_state_and_events.md` e `06_backend_api_and_dataflow.md` para rastrear estado, eventos e chamadas.
4. Use `08_legacy_duplication_and_risks.md` antes de qualquer refatoração.
5. Use `11_file_index.md` como mapa de arquivos ativos e sensíveis.

## Índice

- `01_system_overview.md`: visão geral do sistema e papel do Chat Inspetor no produto
- `02_runtime_entrypoints.md`: rotas, templates base, shells e pontos de montagem
- `03_screen_modes_and_user_flows.md`: modos de tela e fluxos detalhados do usuário
- `04_frontend_state_and_events.md`: estado, datasets, storage, eventos, listeners e sincronização
- `05_template_js_css_map.md`: matriz template -> partial -> JS -> CSS -> responsabilidade
- `06_backend_api_and_dataflow.md`: rotas, endpoints, payloads, integrações e fluxo de dados
- `07_ui_regions_and_components.md`: anatomia visual da interface
- `08_legacy_duplication_and_risks.md`: legado, duplicações, acoplamentos e riscos
- `09_glossary_and_open_questions.md`: glossário interno e dúvidas abertas
- `10_FOR_CHATGPT.md`: briefing consolidado para envio a outra IA
- `11_file_index.md`: índice dos arquivos mais importantes
- `UPLOAD_ORDER.md`: ordem recomendada de envio ao ChatGPT

## Confirmado no Código

- O entrypoint do inspetor é `web/templates/index.html`.
- O shell real do inspetor usa `web/templates/inspetor/base.html` e `web/templates/inspetor/_portal_main.html`.
- O controlador de screen mode é `web/static/js/chat/chat_index_page.js`, especialmente `resolveInspectorScreen()`.
- O CSS realmente carregado para o fluxo atual é concentrado em `web/static/css/inspetor/reboot.css`, `web/static/css/shared/official_visual_system.css` e nos slices `workspace_{chrome,history,rail,states}.css`, além de `tokens.css` e `app_shell.css`.
- `web/templates/base.html`, `web/static/css/shared/layout.css` e os bundles antigos de `web/static/css/chat/` e `web/static/css/inspetor/` da trilha visual antiga foram removidos fisicamente.
- A navegação Home foi centralizada semanticamente com `data-action="go-home"` e o evento `tariel:navigate-home`.

## Inferência

- A arquitetura atual já está em uma fase de transição: o shell e o topo do workspace foram modularizados, mas o sistema ainda convive com camadas legadas de estado e fallback.

## Dúvida Aberta

- Não há no frontend atual um consumidor explícito, confirmado no runtime do inspetor, para os endpoints de aprendizados em `web/app/domains/chat/learning.py`. O backend existe; o uso no fluxo atual permanece incerto.
