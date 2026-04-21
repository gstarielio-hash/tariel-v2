# 05. Mapa Template -> JS -> CSS

## Matriz Principal

| Template / Partial | Região | JS principal | CSS principal | Responsabilidade |
| --- | --- | --- | --- | --- |
| `web/templates/index.html` | entrypoint HTML | todos os bundles carregados aqui | herdado de `web/templates/inspetor/base.html` | página raiz do inspetor |
| `web/templates/inspetor/base.html` | shell global | `web/static/js/shared/app_shell.js`, `web/static/js/shared/ui.js` | `web/static/css/shared/app_shell.css`, `web/static/css/shared/official_visual_system.css`, `web/static/css/inspetor/tokens.css`, `web/static/css/inspetor/reboot.css`, `web/static/css/inspetor/workspace_chrome.css`, `web/static/css/inspetor/workspace_history.css`, `web/static/css/inspetor/workspace_rail.css`, `web/static/css/inspetor/workspace_states.css` | shell global, boot JSON, quick dock, overlay |
| `web/templates/inspetor/_portal_main.html` | mount principal | `web/static/js/chat/chat_index_page.js` | `web/static/css/inspetor/reboot.css`, `web/static/css/inspetor/workspace_chrome.css`, `web/static/css/inspetor/workspace_rail.css`, `web/static/css/inspetor/workspace_states.css` | grid geral, datasets SSR, composição portal + workspace + mesa |
| `web/templates/inspetor/_sidebar.html` | sidebar esquerda | `web/static/js/chat/chat_sidebar.js`, `web/static/js/shared/ui.js`, `web/static/js/chat/chat_perfil_usuario.js` | `web/static/css/inspetor/reboot.css`, `web/static/css/shared/app_shell.css` | histórico, busca, Home, perfil, logout |
| `web/templates/inspetor/_portal_home.html` | portal/home | `web/static/js/chat/chat_index_page.js`, `web/static/js/chat/chat_painel_laudos.js` | `web/static/css/inspetor/reboot.css`, `web/static/css/shared/official_visual_system.css` | cards, recentes, atalhos rápidos |
| `web/templates/inspetor/_workspace.html` | shell do workspace | `web/static/js/chat/chat_index_page.js` | `web/static/css/inspetor/reboot.css`, `web/static/css/inspetor/workspace_chrome.css`, `web/static/css/inspetor/workspace_history.css`, `web/static/css/inspetor/workspace_rail.css`, `web/static/css/inspetor/workspace_states.css` | header/toolbar compartilhados, views, composer, rail |
| `web/templates/inspetor/workspace/_workspace_header.html` | header interno | `web/static/js/chat/chat_index_page.js`, `web/static/js/shared/ui.js`, `web/static/js/chat/chat_painel_relatorio.js` | `web/static/css/inspetor/workspace_chrome.css`, `web/static/css/shared/official_visual_system.css` | Home, título, subtítulo, badge, preview, finalizar |
| `web/templates/inspetor/workspace/_workspace_toolbar.html` | toolbar/tabs | `web/static/js/chat/chat_index_page.js`, `web/static/js/chat/chat_painel_laudos.js` | `web/static/css/inspetor/workspace_chrome.css`, `web/static/css/shared/official_visual_system.css` | tabs, busca, filtros, status do assistente |
| `web/templates/inspetor/workspace/_assistant_landing.html` | landing do assistente | `web/static/js/chat/chat_index_page.js` | `web/static/css/inspetor/workspace_states.css`, `web/static/css/inspetor/reboot.css` | entrada assistida antes do laudo |
| `web/templates/inspetor/workspace/_inspection_record.html` | registro/anexos | `web/static/js/chat/chat_index_page.js`, `web/static/js/shared/hardware.js`, `web/static/js/shared/api.js` | `web/static/css/inspetor/reboot.css` | anexos e registro técnico |
| `web/templates/inspetor/workspace/_inspection_conversation.html` | conversa ativa | `web/static/js/shared/chat-render.js`, `web/static/js/shared/api.js`, `web/static/js/chat/chat_index_page.js` | `web/static/css/inspetor/reboot.css`, `web/static/css/inspetor/workspace_states.css` | árvore de mensagens, scroll, digitação |
| `web/templates/inspetor/workspace/_workspace_context_rail.html` | rail direito | `web/static/js/chat/chat_index_page.js`, `web/static/js/inspetor/pendencias.js`, `web/static/js/inspetor/mesa_widget.js` | `web/static/css/inspetor/workspace_rail.css`, `web/static/css/shared/official_visual_system.css` | progresso, contexto IA, pendências, mesa, atividade |
| `web/templates/inspetor/_mesa_widget.html` | widget da mesa | `web/static/js/inspetor/mesa_widget.js`, `web/static/js/chat/chat_painel_mesa.js` | `web/static/css/inspetor/reboot.css`, `web/static/css/inspetor/workspace_rail.css` | conversa paralela com mesa |
| `web/templates/inspetor/modals/_nova_inspecao.html` | overlay nova inspeção | `web/static/js/inspetor/modals.js`, `web/static/js/chat/chat_index_page.js` | `web/static/css/inspetor/reboot.css` | criação de contexto inicial da inspeção |
| `web/templates/inspetor/modals/_gate_qualidade.html` | overlay gate | `web/static/js/inspetor/modals.js`, `web/static/js/chat/chat_painel_relatorio.js` | `web/static/css/inspetor/reboot.css` | bloqueio/pendências antes da finalização |
| `web/templates/inspetor/modals/_perfil.html` | overlay perfil | `web/static/js/chat/chat_perfil_usuario.js` | `web/static/css/inspetor/reboot.css` | edição de perfil do usuário |

## Autoridades de Layout

### Confirmado no código

As principais autoridades de layout do inspetor são:

- `web/templates/inspetor/_portal_main.html`
- `web/templates/inspetor/_workspace.html`
- `web/templates/inspetor/workspace/_workspace_header.html`
- `web/templates/inspetor/workspace/_workspace_toolbar.html`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`

## CSS realmente ativo

### Confirmado no código

O runtime atual usa:

- `web/static/css/inspetor/tokens.css`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`
- `web/static/css/shared/app_shell.css`
- `web/static/css/shared/global.css`
- `web/static/css/shared/material-symbols.css`

### Confirmado por teste

`web/tests/test_smoke.py` protege contra regressão e confirma que os caminhos aposentados:

- `web/templates/base.html`
- `web/static/css/chat/chat_base.css`
- `web/static/css/chat/chat_index.css`
- `web/static/css/chat/chat_mobile.css`
- `web/static/css/inspetor/home.css`
- `web/static/css/inspetor/mesa.css`
- `web/static/css/inspetor/modals.css`
- `web/static/css/inspetor/profile.css`
- `web/static/css/inspetor/responsive.css`
- `web/static/css/inspetor/shell.css`
- `web/static/css/inspetor/workspace.css`
- `web/static/css/shared/layout.css`

foram removidos fisicamente e não entram mais no runtime oficial do inspetor.

## Seletores e Hooks Críticos

## Shell e navegação

- `#painel-chat`
- `[data-screen-root="portal"]`
- `[data-screen-root="workspace"]`
- `[data-screen-root="mesa-widget"]`
- `[data-action="go-home"]`
- `#btn-shell-home`

## Sidebar

- `#barra-historico`
- `#busca-historico-input`
- `#lista-historico`
- `#banner-relatorio-sidebar`
- `#btn-abrir-perfil-chat`

## Workspace

- `.thread-nav`
- `.thread-tab`
- `.technical-chat-bar`
- `#chat-thread-search`
- `[data-chat-filter]`
- `#chat-thread-results`
- `#chat-ai-status-chip`
- `#workspace-titulo-laudo`
- `#workspace-subtitulo-laudo`
- `#workspace-status-badge`
- `#btn-finalizar-inspecao`

## Conversa e composer

- `#area-mensagens`
- `#indicador-digitando`
- `#btn-ir-fim-chat`
- `.rodape-entrada`
- `#preview-anexo`
- `#btn-anexo`
- `#input-anexo`
- `#btn-microfone`
- `#campo-mensagem`
- `#btn-enviar`
- `#slash-command-palette`

## Context rail

- `#workspace-progress-card`
- `#workspace-context-template`
- `#painel-pendencias-mesa`
- `#workspace-mesa-card-status`
- `#workspace-activity-list`

## Mesa widget

- `#painel-mesa-widget`
- `#mesa-widget-lista`
- `#mesa-widget-input`
- `#mesa-widget-enviar`

## Relação Template x Runtime

### Confirmado no código

- O SSR monta a estrutura base inteira.
- O JS não cria a aplicação do zero; ele ativa, oculta, sincroniza e, em alguns pontos legados, recria partes pontuais.
- O workspace foi modularizado em partials.
- A toolbar e o header interno são compartilhados.

## Componentes compartilhados

- `_workspace_header.html`
- `_workspace_toolbar.html`
- composer compartilhado em `_workspace.html`
- context rail compartilhado em `_workspace_context_rail.html`

## Componentes com cheiro de legado

### Confirmado no código

- `web/static/js/chat/chat_painel_laudos.js::garantirThreadNav()`
- `web/static/js/chat/chat_sidebar.js` ainda procura `#btn-sidebar-engenheiro`
- `web/static/js/shared/api.js::renderizarHistoricoCarregado()` injeta fillers

## Inferência

- A modularização de templates avançou mais rápido que a consolidação do estado e dos fallbacks JS. Isso explica por que o layout parece mais moderno que a malha de sincronização por baixo.

## Dúvida Aberta

- Não há um documento único no repositório definindo oficialmente quais seletores são contrato estável entre módulos e quais são apenas detalhes de implementação.
