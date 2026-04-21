# Chat Inspetor: Estabilidade do Workspace

## Escopo desta fase

Este documento registra a FASE 5 da reorganização do frontend do inspetor.

- Confirmado no código: não houve alteração de backend, endpoints, contratos de dados, SSE, envio de mensagens, anexos, finalização, reabertura ou regra funcional de mesa.
- Confirmado no código: o foco ficou em autoridade estrutural da toolbar, previsibilidade do rail direito e escopo visual de widgets globais.

## Toolbar do workspace

### Autoridade estrutural

- Confirmado no código: a partial [web/templates/inspetor/workspace/_workspace_toolbar.html](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/templates/inspetor/workspace/_workspace_toolbar.html) permanece como fonte estrutural única da toolbar.
- Confirmado no código: os hooks críticos continuam vindo do template SSR, incluindo `.thread-nav`, `.thread-tab`, `#chat-thread-search`, `[data-chat-filter]`, `#chat-thread-results`, `#chat-ai-status-chip` e `#chat-ai-status-text`.

### O que aconteceu com `garantirThreadNav()`

- Confirmado no código: [web/static/js/chat/chat_painel_laudos.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/chat/chat_painel_laudos.js) ainda chama `garantirThreadNav()` no boot e durante seleção de tabs.
- Confirmado no código: a função deixou de recriar markup de `.thread-nav` e `.thread-tabs`.
- Confirmado no código: agora ela apenas:
  - valida se `.thread-nav` existe no DOM;
  - faz o wiring do clique se o template estiver presente;
  - registra um warning único se a toolbar não existir.
- Confirmado no código: `selecionarThreadTab(tab)` continua atualizando `document.body.dataset.threadTab` e emitindo `tariel:thread-tab-alterada`, mesmo que o nav não exista.

### Efeito prático

- Confirmado no código: o template virou a autoridade da existência da toolbar.
- Confirmado no código: o JS deixou de ser uma segunda fonte estrutural concorrente para as tabs.

## Rail direito do workspace

### Host estrutural

- Confirmado no código: o rail continua na partial [web/templates/inspetor/workspace/_workspace_context_rail.html](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/templates/inspetor/workspace/_workspace_context_rail.html).
- Confirmado no código: o rail agora expõe `data-workspace-rail-root` e `data-workspace-rail-visible`.
- Confirmado no código: o root do workspace em [web/templates/inspetor/_workspace.html](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/templates/inspetor/_workspace.html) agora expõe:
  - `data-workspace-view`
  - `data-workspace-layout`
  - `data-workspace-rail-visible`

### Autoridade de visibilidade

- Confirmado no código: [web/static/js/chat/chat_index_page.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/chat/chat_index_page.js) passou a centralizar a decisão do rail em `sincronizarWorkspaceRail(screen)`.
- Confirmado no código: essa função usa `resolveWorkspaceView(screen)` e `resolveWorkspaceRailVisibility(screen)`.
- Confirmado no código: as regras atuais são:
  - `inspection_record`: rail visível
  - `inspection_conversation`: rail visível
  - `assistant_landing`: rail oculto
  - `portal_dashboard`: rail oculto
  - `new_inspection`: rail oculto, mesmo quando existe `baseScreen` técnico por baixo

### Layout

- Confirmado no código: [web/static/css/inspetor/reboot.css](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/css/inspetor/reboot.css) agora trata o workspace com dois estados explícitos:
  - `data-workspace-layout="thread-with-rail"`
  - `data-workspace-layout="thread-only"`
- Confirmado no código: em `thread-only`, o grid colapsa para uma coluna e remove o gap do rail.
- Confirmado no código: isso evita espaço morto lateral quando a landing está ativa ou quando `new_inspection` domina visualmente a tela.

## Widgets e painéis globais

### Mesa widget dedicado

- Confirmado no código: o widget dedicado continua em [web/templates/inspetor/_mesa_widget.html](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/templates/inspetor/_mesa_widget.html), montado sob `data-screen-root="mesa-widget"` no shell SSR.
- Confirmado no código: [web/static/js/chat/chat_index_page.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/chat/chat_index_page.js) passou a controlar a disponibilidade visual do widget por `sincronizarWidgetsGlobaisWorkspace(screen)`.
- Confirmado no código: as regras atuais são:
  - `inspection_record`: permitido
  - `inspection_conversation`: permitido
  - `assistant_landing`: oculto
  - `portal_dashboard`: oculto
  - `new_inspection`: oculto
- Confirmado no código: quando o contexto não permite o widget, o root `data-screen-root="mesa-widget"` é desativado e o painel é fechado se estiver aberto.
- Confirmado no código: [web/static/js/inspetor/mesa_widget.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/inspetor/mesa_widget.js) agora espelha esse escopo em:
  - `body.mesa-widget-disponivel`
  - `document.body.dataset.mesaWidgetScope`
  - `#painel-mesa-widget[data-widget-scope]`

### Quick dock

- Confirmado no código: [web/static/js/shared/ui.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/shared/ui.js) passou a decidir a exibição do dock por `dockRapidoPodeAparecer()`.
- Confirmado no código: o dock rápido agora só fica operacional em `inspection_record` e `inspection_conversation`, sem overlay ativo.
- Confirmado no código: `document.body.dataset.homeActionVisible` continua sendo respeitado, mas deixou de ser suficiente sozinho para forçar o dock em contextos errados.

### Overlay da sidebar

- Confirmado no código: [web/static/js/shared/ui.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/shared/ui.js) ganhou `sidebarPodeAbrirNoContextoAtual()` e `sincronizarSidebarOverlayPorContexto()`.
- Confirmado no código: o overlay da sidebar continua funcional, mas deixa de abrir quando existe `overlayOwner`.
- Confirmado no código: ao receber `tariel:screen-synced`, a sidebar fecha silenciosamente se o contexto atual não permitir uma camada extra.

## Seletores e hooks preservados

### Preservados

- Confirmado no código: `.thread-nav`
- Confirmado no código: `.thread-tab`
- Confirmado no código: `#chat-thread-search`
- Confirmado no código: `[data-chat-filter]`
- Confirmado no código: `#chat-thread-results`
- Confirmado no código: `#chat-ai-status-chip`
- Confirmado no código: `#chat-ai-status-text`
- Confirmado no código: `document.body.dataset.threadTab`
- Confirmado no código: `#painel-pendencias-mesa`
- Confirmado no código: `#btn-mesa-widget-toggle`
- Confirmado no código: `#painel-mesa-widget`

### Atualizados ou adicionados

- Confirmado no código: `data-workspace-view`
- Confirmado no código: `data-workspace-layout`
- Confirmado no código: `data-workspace-rail-visible`
- Confirmado no código: `document.body.dataset.workspaceView`
- Confirmado no código: `document.body.dataset.workspaceRailVisible`
- Confirmado no código: `document.body.dataset.mesaWidgetVisible`
- Confirmado no código: `document.body.dataset.mesaWidgetScope`
- Confirmado no código: `data-widget-allowed`
- Confirmado no código: `data-widget-scope`

## Limitações que permanecem

- Confirmado no código: `chat_index_page.js` ainda é uma autoridade grande demais para estado visual, screen mode, workspace, mesa e contexto.
- Confirmado no código: a precedência profunda entre sessão, datasets, storage, `TarielChatPainel` e `TarielAPI` não foi reorganizada nesta fase.
- Confirmado no código: `pendencias.js` continua podendo manipular o conteúdo interno de `#painel-pendencias-mesa`; o que mudou foi apenas a autoridade da visibilidade do rail, não a autoridade dos dados.
- Confirmado no código: a dualidade conceitual entre widget de mesa dedicado e fluxo textual de mesa continua existente.
- Inferência: ainda existe risco de acoplamento implícito em qualquer fluxo novo que dependa de `querySelector()` em vez de hooks declarados no template.
- Dúvida aberta: não há uma camada formal de contratos de layout entre shell global e módulos do inspetor; o sistema ainda se apoia bastante em datasets e seletores como contrato implícito.

## Resultado desta fase

- Confirmado no código: a toolbar do workspace deixou de ter duas fontes estruturais.
- Confirmado no código: o rail direito passou a responder ao screen mode real do workspace.
- Confirmado no código: o widget dedicado de mesa e o dock rápido deixaram de competir visualmente com landing, portal e overlay de nova inspeção.
- Confirmado no código: a composição do workspace ficou mais previsível sem alterar a lógica funcional do produto.
