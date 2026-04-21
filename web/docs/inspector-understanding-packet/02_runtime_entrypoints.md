# 02. Runtime Entrypoints

## Por Onde a UI Nasce

## 1. Rota HTTP principal

### Confirmado no código

- `web/main.py` registra o domínio do inspetor em `/app`.
- `web/app/domains/router_registry.py` expõe `roteador_inspetor`.
- `web/app/domains/chat/router.py` agrega os routers do domínio de chat.
- `web/app/domains/chat/auth_portal_routes.py::pagina_inicial()` serve a página principal do inspetor.

### Rota principal

- `GET /app/`

### Alias de laudo

- `GET /app/laudo/{laudo_id}`
- comportamento: aplica o contexto do laudo na sessão e redireciona para `/app/?laudo={id}`

## 2. Preparação SSR do contexto

Em `web/app/domains/chat/auth_portal_routes.py::pagina_inicial()` o backend:

- valida acesso do usuário inspetor
- reconcilia estado do relatório via `web/app/domains/chat/session_helpers.py::estado_relatorio_sanitizado()`
- coleta laudos recentes via `web/app/domains/chat/auth_mobile_support.py::listar_laudos_recentes_portal_inspetor()`
- monta o contexto do portal via `web/app/domains/chat/auth_mobile_support.py::montar_contexto_portal_inspetor()`
- detecta `home_forcado_inicial` pelo query param `home=1`
- injeta tudo em `web/templates/index.html`

## 3. Template raiz e shell

### `web/templates/index.html`

Responsabilidades confirmadas:

- estende `web/templates/inspetor/base.html`
- define as classes de body:
  - `pagina-chat`
  - `pagina-chat-dashboard-v2`
  - `pagina-chat-redesign`
- inclui:
  - `web/templates/inspetor/_portal_main.html`
  - `web/templates/inspetor/modals/_nova_inspecao.html`
  - `web/templates/inspetor/modals/_gate_qualidade.html`
  - `web/templates/inspetor/modals/_perfil.html`
- carrega todos os assets JS do runtime inspetor

### `web/templates/inspetor/base.html`

Responsabilidades confirmadas:

- define o shell global
- injeta o JSON bootstrap em `#tariel-boot`
- carrega CSS shared + CSS inspetor ativo
- renderiza quick dock e overlay globais

### Dados expostos em `#tariel-boot`

Confirmados em `base.html`:

- `csrfToken`
- `usuarioNome`
- `empresaNome`
- `laudosMesUsados`
- `laudosMesLimite`
- `planoUploadDoc`
- `deepResearchDisponivel`
- `estadoRelatorio`
- `laudoAtivoId`
- `suporteWhatsapp`
- `ambiente`

## 4. Mount principal do inspetor

### `web/templates/inspetor/_portal_main.html`

Este é o shell real da página do inspetor.

### Root principal

```html
<main id="painel-chat" ... data-screen-controller="inspector">
```

### Datasets SSR importantes

- `data-inspecao-ui`
- `data-workspace-stage`
- `data-inspector-screen`

### Regras SSR confirmadas

Em `_portal_main.html`, o servidor calcula:

- `modo_inspecao_inicial = "home"` ou `"workspace"`
- `workspace_stage_inicial = "inspection"` ou `"assistant"`
- `inspector_screen_inicial = "portal_dashboard"`, `"assistant_landing"` ou `"inspection_record"`

### Regiões montadas pelo shell

- `web/templates/inspetor/_sidebar.html`
- `web/templates/inspetor/_portal_home.html`
- `web/templates/inspetor/_workspace.html`
- `web/templates/inspetor/_mesa_widget.html`

## 5. Subárvore do workspace

### `web/templates/inspetor/_workspace.html`

O workspace é um shell compartilhado que contém:

- header interno compartilhado
- toolbar compartilhada
- raízes de views:
  - `data-workspace-view-root="assistant_landing"`
  - `data-workspace-view-root="inspection_record"`
  - `data-workspace-view-root="inspection_conversation"`
- estado vazio compartilhado
- composer compartilhado
- context rail compartilhado
- aviso de laudo bloqueado

## 6. Ordem de carga do JavaScript

### Confirmado no código

`web/templates/index.html` carrega, nesta ordem relevante:

1. `web/static/js/shared/api-core.js`
2. `web/static/js/shared/chat-render.js`
3. `web/static/js/shared/chat-network-utils.js`
4. `web/static/js/shared/chat-network.js`
5. `web/static/js/shared/api.js`
6. `web/static/js/shared/ui.js`
7. `web/static/js/shared/hardware.js`
8. `web/static/js/chat/chat_sidebar.js`
9. `web/static/js/inspetor/modals.js`
10. `web/static/js/inspetor/pendencias.js`
11. `web/static/js/inspetor/mesa_widget.js`
12. `web/static/js/inspetor/notifications_sse.js`
13. `web/static/js/chat/chat_index_page.js`
14. `web/static/js/chat/chat_perfil_usuario.js`
15. `web/static/js/chat/chat_painel_core.js`
16. `web/static/js/chat/chat_painel_laudos.js`
17. `web/static/js/chat/chat_painel_historico_acoes.js`
18. `web/static/js/chat/chat_painel_mesa.js`
19. `web/static/js/chat/chat_painel_relatorio.js`
20. `web/static/js/chat/chat_painel_index.js`

## 7. Quem hidrata o quê

### Hidratação do shell e navegação

- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_index_page.js`

### Hidratação do histórico/laudos

- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/chat/chat_painel_historico_acoes.js`
- `web/static/js/shared/api.js`

### Hidratação de modais

- `web/static/js/inspetor/modals.js`
- `web/static/js/chat/chat_perfil_usuario.js`

### Hidratação de mesa/pendências/notificações

- `web/static/js/inspetor/mesa_widget.js`
- `web/static/js/inspetor/pendencias.js`
- `web/static/js/inspetor/notifications_sse.js`

## 8. CSS realmente carregado no fluxo

### Confirmado no código

`web/templates/inspetor/base.html` carrega:

- `web/static/css/shared/global.css`
- `web/static/css/shared/material-symbols.css`
- `web/static/css/inspetor/tokens.css`
- `web/static/css/shared/app_shell.css`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`

### Confirmado por teste

`web/tests/test_smoke.py` verifica que o runtime do inspetor usa o pipeline modularizado atual e que `web/templates/base.html`, `web/static/css/shared/layout.css`, `web/static/css/chat/{chat_base,chat_mobile,chat_index}.css` e `web/static/css/inspetor/{shell,home,workspace,mesa,modals,profile,responsive}.css` não existem mais nem entram no boot oficial.

## 9. Bootstrap de estado e runtime

### `web/static/js/shared/app_shell.js`

Responsabilidades confirmadas:

- lê `#tariel-boot`
- expõe `window.TARIEL`
- inicializa rede/toasts/shell global
- evita competir com a sidebar do chat quando `#painel-chat` existe

### `web/static/js/chat/chat_index_page.js`

Responsabilidades confirmadas:

- consolida `estado`
- registra módulos em `window.TarielInspetorModules`
- resolve o screen mode atual
- sincroniza raízes visíveis da UI
- conecta Home, toolbar, context rail, modal e workspace

## Confirmado no Código

- O SSR já define um estado inicial coerente do inspetor antes de qualquer JS rodar.
- O cliente não nasce em uma SPA separada; ele hidrata uma página SSR única.
- `#painel-chat` é o mount principal do runtime do inspetor.
- O boot da UI depende de dados de sessão, query params, dataset do DOM e armazenamento local.

## Inferência

- A ordem dos scripts sugere uma arquitetura incremental: primeiro o core compartilhado, depois os módulos de tela/integração, e por fim um boot compatível com código legado.

## Dúvida Aberta

- Não existe um contrato único documentado para a ordem de inicialização entre `chat_index_page.js`, `shared/api.js` e `chat_painel_index.js`; ela precisa ser inferida pela ordem de script e pelos listeners.
