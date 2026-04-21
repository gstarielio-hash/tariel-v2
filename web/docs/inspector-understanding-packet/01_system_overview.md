# 01. Visão Geral do Sistema

## O que é o Chat Inspetor

O Chat Inspetor é a interface principal do usuário inspetor dentro do produto Tariel. Ele combina portal, workspace técnico, conversa com IA, anexos, contexto operacional, mesa avaliadora, pendências e finalização de laudo em uma mesma tela SSR + client-side hydration.

O entrypoint HTML é `web/templates/index.html`, servido por `/app/` a partir de `web/app/domains/chat/auth_portal_routes.py::pagina_inicial()`.

## Função no Produto

O Chat Inspetor faz pelo menos seis papéis ao mesmo tempo:

- apresentar o portal inicial com cards, laudos recentes e atalhos
- iniciar uma nova inspeção por modal
- manter um workspace técnico com cabeçalho, toolbar, rail de contexto e composer
- exibir conversa ativa entre inspetor e IA
- operar anexos, mesa avaliadora e pendências do laudo
- orquestrar o ciclo de vida do laudo: iniciar, acompanhar, finalizar, reabrir, voltar para Home

## Grandes Áreas do Fluxo

### 1. Shell base

- template base: `web/templates/inspetor/base.html`
- shell principal: `web/templates/inspetor/_portal_main.html`
- container visual principal: `#painel-chat`

### 2. Sidebar esquerda

- template: `web/templates/inspetor/_sidebar.html`
- runtime principal: `web/static/js/chat/chat_sidebar.js`
- função: histórico, busca, Portal/Home, nova inspeção, perfil, logout

### 3. Portal/Home

- template: `web/templates/inspetor/_portal_home.html`
- função: dashboard, cards de status, laudos recentes, ações rápidas por modelo

### 4. Workspace

- template shell: `web/templates/inspetor/_workspace.html`
- partials principais:
  - `web/templates/inspetor/workspace/_workspace_header.html`
  - `web/templates/inspetor/workspace/_workspace_toolbar.html`
  - `web/templates/inspetor/workspace/_assistant_landing.html`
  - `web/templates/inspetor/workspace/_inspection_record.html`
  - `web/templates/inspetor/workspace/_inspection_conversation.html`
  - `web/templates/inspetor/workspace/_workspace_context_rail.html`

### 5. Modais e overlays

- nova inspeção: `web/templates/inspetor/modals/_nova_inspecao.html`
- gate de qualidade: `web/templates/inspetor/modals/_gate_qualidade.html`
- perfil: `web/templates/inspetor/modals/_perfil.html`
- runtime principal: `web/static/js/inspetor/modals.js` e `web/static/js/chat/chat_perfil_usuario.js`

### 6. Runtime de dados e integrações

- screen controller: `web/static/js/chat/chat_index_page.js`
- estado global legado do chat: `web/static/js/chat/chat_painel_core.js`
- API bridge e histórico: `web/static/js/shared/api.js`
- rede/streaming: `web/static/js/shared/chat-network.js`
- SSE de notificações: `web/static/js/inspetor/notifications_sse.js`
- mesa avaliadora: `web/static/js/inspetor/mesa_widget.js` e `web/static/js/chat/chat_painel_mesa.js`
- pendências: `web/static/js/inspetor/pendencias.js`

## Principais Telas e Modos

Os modos confirmados no código vêm de `web/static/js/chat/chat_index_page.js::resolveInspectorScreen()`:

- `portal_dashboard`
- `assistant_landing`
- `new_inspection`
- `inspection_record`
- `inspection_conversation`

Esses modos não são rotas separadas. Eles compartilham a mesma página e são resolvidos pelo frontend com base em:

- modal aberto ou fechado
- `estado.modoInspecaoUI`
- `estado.workspaceStage`
- `document.body.dataset.threadTab`
- existência de mensagens no workspace

## Como o Usuário Entra e Sai de Cada Modo

### Entrada no sistema

- rota principal: `GET /app/`
- alias de laudo: `GET /app/laudo/{laudo_id}` redireciona para `/app/?laudo={id}`
- o servidor decide contexto inicial e renderiza SSR
- o frontend revalida e ajusta o modo no boot

### Entrada em Home

- query param `?home=1`
- ação semântica `data-action="go-home"`
- evento `tariel:navigate-home`
- função efetiva: `web/static/js/chat/chat_index_page.js::navegarParaHome()`

### Entrada em nova inspeção

- clique em qualquer elemento com `data-open-inspecao-modal`
- modal `#modal-nova-inspecao` aberto por `web/static/js/inspetor/modals.js`
- enquanto o modal está aberto, o screen mode vira `new_inspection`

### Entrada em laudo ativo

- via cards do Home
- via item da sidebar/histórico
- via query param `?laudo=<id>`
- via seleção persistida em `localStorage["tariel_laudo_atual"]`

### Saída de laudo ativo para Home

- qualquer affordance com `data-action="go-home"`
- quick dock `#btn-shell-home`
- botão do header `.btn-home-cabecalho`
- link Portal na sidebar

## Confirmações Estruturais Importantes

### Confirmado no código

- O shell SSR define `data-inspecao-ui`, `data-workspace-stage` e `data-inspector-screen` já em `web/templates/inspetor/_portal_main.html`.
- O frontend pode mudar esses valores depois no boot, principalmente em `web/static/js/chat/chat_index_page.js::sincronizarInspectorScreen()`.
- `web/static/js/chat/chat_index_page.js` é a autoridade prática de screen mode.
- `web/static/js/shared/ui.js` é a autoridade semântica da ação Home no frontend.
- `web/static/css/inspetor/reboot.css` é a autoridade visual do runtime atual.

### Inferência

- O sistema passou por uma migração de um layout mais espalhado para um shell de workspace compartilhado. Isso explica por que há módulos novos bem estruturados convivendo com fallbacks e aliases legados.

### Dúvida aberta

- Não há um diagrama arquitetural único dentro do repositório que consolide SSR, chat runtime, mesa, pendências e perfil no mesmo documento. O entendimento precisa ser montado a partir de múltiplos arquivos.
