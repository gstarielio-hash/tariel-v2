# Briefing Consolidado do Chat Inspetor
Este arquivo foi escrito para ser enviado a outra IA como contexto técnico compacto e autoexplicativo sobre o sistema "Chat Inspetor".

## 1. O que é o sistema
- O Chat Inspetor é o portal principal do usuário inspetor no produto Tariel.
- Ele reúne portal/home, workspace técnico, conversa com IA, anexos, mesa avaliadora, pendências e finalização de laudo na mesma página.
- Não é uma SPA isolada. É uma página SSR servida por `/app/` e depois hidratada por vários módulos JS.
- Entry point HTML: `web/templates/index.html`.
- Shell base: `web/templates/inspetor/base.html`.
- Shell funcional do inspetor: `web/templates/inspetor/_portal_main.html`.
- Mount principal: `#painel-chat`.

## 2. Arquitetura geral
### SSR
- `web/app/domains/chat/auth_portal_routes.py::pagina_inicial()` serve `/app/`.
- O backend reconcilia o estado do laudo em `web/app/domains/chat/session_helpers.py::estado_relatorio_sanitizado()`.
- O backend monta cards e recentes do portal via `web/app/domains/chat/auth_mobile_support.py`.
- `web/templates/inspetor/_portal_main.html` já chega com:
  - `data-inspecao-ui`
  - `data-workspace-stage`
  - `data-inspector-screen`
- `web/templates/inspetor/base.html` injeta bootstrap JSON em `#tariel-boot`.
### Hidratação client-side
- `web/static/js/chat/chat_index_page.js` controla screen mode, workspace e boa parte do estado visual.
- `web/static/js/chat/chat_painel_core.js` cria `window.TarielChatPainel`.
- `web/static/js/shared/api.js` cria `window.TarielAPI`.
- `web/static/js/shared/chat-network.js` implementa chamadas reais de rede.
- `web/static/js/shared/ui.js` cuida do quick dock e da semântica global de Home.
- `web/static/js/inspetor/*.js` cobrem modal, mesa, pendências e notificações SSE.

## 3. Estrutura de templates
### Entry points e shell
- `web/templates/index.html`
- `web/templates/inspetor/base.html`
- `web/templates/inspetor/_portal_main.html`
### Sidebar e portal
- `web/templates/inspetor/_sidebar.html`
- `web/templates/inspetor/_portal_home.html`
### Workspace
- `web/templates/inspetor/_workspace.html`
- `web/templates/inspetor/workspace/_workspace_header.html`
- `web/templates/inspetor/workspace/_workspace_toolbar.html`
- `web/templates/inspetor/workspace/_assistant_landing.html`
- `web/templates/inspetor/workspace/_inspection_record.html`
- `web/templates/inspetor/workspace/_inspection_conversation.html`
- `web/templates/inspetor/workspace/_workspace_context_rail.html`
### Modais e widget
- `web/templates/inspetor/modals/_nova_inspecao.html`
- `web/templates/inspetor/modals/_gate_qualidade.html`
- `web/templates/inspetor/modals/_perfil.html`
- `web/templates/inspetor/_mesa_widget.html`

## 4. CSS realmente usado
- `web/static/css/shared/global.css`
- `web/static/css/shared/material-symbols.css`
- `web/static/css/shared/app_shell.css`
- `web/static/css/inspetor/tokens.css`
- `web/static/css/inspetor/reboot.css`
- Observação crítica: os arquivos antigos em `web/static/css/inspetor/{home,mesa,modals,profile,responsive,shell,workspace}.css` existem, mas não são os CSS de produção carregados no fluxo atual.

## 5. Screen modes confirmados
Os modos são resolvidos em `web/static/js/chat/chat_index_page.js::resolveInspectorScreen()`.

| Modo | Gatilho principal | Root dominante |
| --- | --- | --- |
| `portal_dashboard` | `modoInspecaoUI === "home"` ou `?home=1` | `#tela-boas-vindas` |
| `assistant_landing` | workspace sem laudo ativo | `#workspace-assistant-landing` |
| `new_inspection` | modal nova inspeção aberto | `#modal-nova-inspecao` |
| `inspection_record` | laudo ativo em anexos ou sem conversa visível | `#workspace-anexos-panel` |
| `inspection_conversation` | laudo ativo na tab `chat` com mensagens | `#area-mensagens` |

Regra de resolução:
1. modal aberto -> `new_inspection`
2. `estado.modoInspecaoUI === "home"` -> `portal_dashboard`
3. `estado.workspaceStage === "assistant"` -> `assistant_landing`
4. tab `chat` + mensagens -> `inspection_conversation`
5. caso contrário -> `inspection_record`

## 6. Regiões de UI mais importantes
### Sidebar esquerda
- arquivo: `web/templates/inspetor/_sidebar.html`
- seletores críticos: `#barra-historico`, `#busca-historico-input`, `#lista-historico`, link Portal com `data-action="go-home"`, `#btn-abrir-perfil-chat`
### Portal/home
- arquivo: `web/templates/inspetor/_portal_home.html`
- seletores críticos: `#tela-boas-vindas`, `#btn-abrir-modal-novo`, `#secao-home-recentes`, `.portal-report-card`, `.portal-model-card.btn-acao-rapida`
### Header interno
- arquivo: `web/templates/inspetor/workspace/_workspace_header.html`
- seletores críticos: `.btn-home-cabecalho`, `#workspace-titulo-laudo`, `#workspace-subtitulo-laudo`, `#workspace-status-badge`, `#btn-workspace-preview`, `#btn-finalizar-inspecao`
### Toolbar
- arquivo: `web/templates/inspetor/workspace/_workspace_toolbar.html`
- seletores críticos: `.thread-nav`, `.thread-tab[data-tab="chat"]`, `.thread-tab[data-tab="anexos"]`, `#chat-thread-search`, `[data-chat-filter]`, `#chat-thread-results`, `#chat-ai-status-chip`
### Conversa
- arquivo: `web/templates/inspetor/workspace/_inspection_conversation.html`
- seletores críticos: `#area-mensagens`, `#indicador-digitando`, `#btn-ir-fim-chat`
### Registro/anexos
- arquivo: `web/templates/inspetor/workspace/_inspection_record.html`
- seletores críticos: `#workspace-anexos-panel`, `#workspace-anexos-count`, `#workspace-anexos-grid`
### Composer
- fica em `web/templates/inspetor/_workspace.html`
- seletores críticos: `.rodape-entrada`, `#preview-anexo`, `#btn-anexo`, `#input-anexo`, `#btn-foto-rapida`, `#btn-microfone`, `#campo-mensagem`, `#btn-enviar`, `#slash-command-palette`
### Context rail
- arquivo: `web/templates/inspetor/workspace/_workspace_context_rail.html`
- seletores críticos: `#workspace-progress-card`, `#workspace-context-template`, `#painel-pendencias-mesa`, `#workspace-mesa-card-status`, `#workspace-activity-list`
### Widget da mesa
- arquivo: `web/templates/inspetor/_mesa_widget.html`
- seletores críticos: `#painel-mesa-widget`, `#mesa-widget-lista`, `#mesa-widget-input`, `#mesa-widget-enviar`

## 7. Autoridades principais
### Layout
- `web/templates/inspetor/_portal_main.html`
- `web/templates/inspetor/_workspace.html`
- `web/templates/inspetor/workspace/_workspace_header.html`
- `web/templates/inspetor/workspace/_workspace_toolbar.html`
- `web/static/css/inspetor/reboot.css`
### Navegação
- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_painel_laudos.js`
### Estado
- servidor: `web/app/domains/chat/session_helpers.py`
- cliente visual: `web/static/js/chat/chat_index_page.js`
- cliente legado/global: `web/static/js/chat/chat_painel_core.js`
- cliente bridge/API: `web/static/js/shared/api.js`

## 8. Onde vive o estado
Não existe uma única store.
### Fontes de verdade confirmadas
- sessão do servidor
- `estado` em `chat_index_page.js`
- `STATE` em `chat_painel_core.js`
- estado interno em `shared/api.js`
- `document.body.dataset`
- `localStorage`
- `sessionStorage`
### Datasets importantes
- `document.body.dataset.inspecaoUi`
- `document.body.dataset.workspaceStage`
- `document.body.dataset.inspectorScreen`
- `document.body.dataset.threadTab`
- `document.body.dataset.laudoAtualId`
- `document.body.dataset.estadoRelatorio`
- `document.body.dataset.homeActionVisible`
- `document.body.dataset.forceHomeLanding`
### Query params
- `home=1`
- `laudo=<id>`
### Storage
- `localStorage["tariel_laudo_atual"]`
- `localStorage["tariel_modo_resposta"]`
- `localStorage["tariel_modo_foco"]`
- `sessionStorage["tariel_force_home_landing"]`
- `sessionStorage["tariel_workspace_retomada_home_pendente"]`
- `localStorage["tariel_workspace_contexto_fixado_${laudoId || 'ativo'}"]`

## 9. Eventos relevantes
### Navegação e UI
- `tariel:navigate-home`
- `tariel:screen-synced`
- `tariel:thread-tab-alterada`
### Laudo e chat
- `tariel:laudo-selecionado`
- `tariel:estado-relatorio`
- `tariel:relatorio-iniciado`
- `tariel:relatorio-finalizado`
- `tariel:cancelar-relatorio`
- `tariel:historico-laudo-renderizado`
- `tariel:chat-status`
### Mensagens
- `tariel:mensagem-copiar`
- `tariel:mensagem-citar`
- `tariel:mensagem-fixar-contexto`
- `tariel:mensagem-enviar-mesa`
- `tariel:prompt-enviado`
- `tariel:executar-comando-slash`
### Mesa
- `tariel:mesa-avaliadora-ativada`
- `tariel:mesa-status`
### Compatibilidade legada
- o código ainda escuta aliases antigos sem `:`, como `tarielrelatorio-iniciado`

## 10. Fluxo dos principais botões e ações
### Home / Portal
- affordances usam `data-action="go-home"`
- `web/static/js/shared/ui.js::solicitarNavegacaoHome(...)` dispara `tariel:navigate-home`
- `web/static/js/chat/chat_index_page.js::navegarParaHome(...)` executa a navegação real
- no processo, o frontend pode limpar `tariel_laudo_atual`, remover `?laudo=`, marcar `tariel_force_home_landing` e fazer `POST /app/api/laudo/desativar`
### Nova inspeção
- elementos `[data-open-inspecao-modal]` abrem `#modal-nova-inspecao`
- `web/static/js/inspetor/modals.js` controla o modal
- confirmação chama início de laudo
### Laudos recentes
- cards do portal usam datasets `data-home-*`
- clique chama `abrirLaudoPeloHome(...)`
- tenta `window.TarielChatPainel.selecionarLaudo(...)`
- fallback: `window.TarielAPI.carregarLaudo(...)`
### Tabs, busca e filtros
- tabs atualizam `document.body.dataset.threadTab`
- busca usa `#chat-thread-search`
- filtros usam `[data-chat-filter]`
- filtragem é feita por `chat_index_page.js::filtrarTimelineWorkspace()`
### Finalização
- botão central: `#btn-finalizar-inspecao`
- read-only e reabrir dependem também de `chat_painel_relatorio.js`
- gate de qualidade aparece em `#modal-gate-qualidade`
### Mesa
- botão `#btn-mesa-widget-toggle`
- ou prefixo `@insp ` via `chat_painel_mesa.js`

## 11. Backend e integrações
### Backend crítico
- `web/app/domains/chat/auth_portal_routes.py`
- `web/app/domains/chat/session_helpers.py`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/chat_aux_routes.py`
- `web/app/domains/chat/mesa.py`
- `web/app/domains/chat/pendencias.py`
- `web/app/domains/chat/chat_runtime_support.py`
### Endpoints centrais
- `POST /app/api/chat`
- `GET /app/api/laudo/status`
- `POST /app/api/laudo/iniciar`
- `POST /app/api/laudo/{laudo_id}/finalizar`
- `GET /app/api/laudo/{laudo_id}/mensagens`
- `POST /app/api/upload_doc`
- `POST /app/api/gerar_pdf`
- `POST /app/api/laudo/desativar`
- `GET /app/api/notificacoes/sse`
- endpoints dedicados de mesa e pendências
### Integrações explícitas
- `window.TarielAPI`
- `window.TarielChatPainel`
- SSE de chat
- SSE de notificações
- mesa avaliadora
- anexos/documentos

## 12. Legado, duplicações e riscos
### Confirmado no código
- múltiplas autoridades de estado coexistem
- eventos novos e aliases legados coexistem
- `chat_painel_laudos.js::garantirThreadNav()` ainda recria `.thread-nav`
- `shared/api.js::renderizarHistoricoCarregado()` injeta mensagens sintéticas
- `inspetor/pendencias.js` injeta pendências placeholder
- `chat_sidebar.js` ainda procura `#btn-sidebar-engenheiro`
- existem dois caminhos conceituais para mesa: widget e prefixo `@insp `
- existem mais de um caminho para finalização no network layer
### Impacto prático
- a UI pode parecer mais complexa do que o layout sugere
- mudanças pequenas de DOM podem quebrar fluxos indiretos
- screen mode, laudo atual e estado do relatório podem divergir se a sincronização falhar

## 13. Arquivos mais importantes para leitura inicial
- `web/templates/index.html`
- `web/templates/inspetor/_portal_main.html`
- `web/templates/inspetor/_workspace.html`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-network.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/shared/ui.js`
- `web/app/domains/chat/auth_portal_routes.py`
- `web/app/domains/chat/session_helpers.py`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/mesa.py`
- `web/app/domains/chat/pendencias.py`

## 14. O que olhar primeiro numa futura refatoração
1. consolidar a fonte de verdade de laudo atual, screen mode e estado do relatório
2. retirar fillers sintéticos de histórico e pendências
3. remover `garantirThreadNav()` quando houver segurança de template/teste
4. escolher um caminho oficial para mesa
5. reduzir acoplamento por dataset e eventos legados

## 15. Confirmado, inferência e dúvidas abertas
### Confirmado no código
- os cinco screen modes listados acima
- a página única SSR com hidratação posterior
- Home centralizado semanticamente em `data-action="go-home"`
- uso de `window.TarielAPI` e `window.TarielChatPainel`
- widget de mesa ativo
- rail direito ativo
- CSS de produção concentrado em `reboot.css`
### Inferência provável
- a UI já passou por reorganização estrutural do topo e do workspace, mas ainda não consolidou o estado
- a próxima melhoria arquitetural deveria atacar estado e fallbacks, não a composição base do layout
### Dúvidas abertas
- consumidor atual dos endpoints de aprendizados em `web/app/domains/chat/learning.py`
- precedência oficial entre sessão, `chat_index_page.js`, `TarielChatPainel`, `TarielAPI`, dataset e storage
- qual caminho de mesa é o definitivo no produto
- qual caminho de finalização é o canônico em todos os cenários
