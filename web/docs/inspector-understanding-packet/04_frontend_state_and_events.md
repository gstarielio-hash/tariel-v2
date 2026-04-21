# 04. Estado Frontend e Eventos

## Visão Geral

O Chat Inspetor não tem uma única store central. O estado está distribuído entre sessão no servidor, objetos JS globais, estado local do screen controller, datasets no DOM, query params e storage do navegador.

Isso é o principal fator de complexidade do frontend atual.

## Autoridades de Estado

| Autoridade | Arquivo | Escopo | Exemplos |
| --- | --- | --- | --- |
| Sessão do servidor | `web/app/domains/chat/session_helpers.py` | laudo ativo e estado do relatório do ponto de vista SSR/backend | `request.session["laudo_ativo_id"]`, `request.session["estado_relatorio"]` |
| Estado local do screen controller | `web/static/js/chat/chat_index_page.js` | modo de tela, toolbar, rail, modal, mesa widget, pendências, contexto visual | `estado.modoInspecaoUI`, `estado.workspaceStage`, `estado.inspectorScreen` |
| Estado global legado do chat | `web/static/js/chat/chat_painel_core.js` | laudo atual, histórico, flags globais de chat | `STATE.laudoAtualId`, `STATE.estadoRelatorio`, `STATE.historicoConversa` |
| Estado do bridge de API | `web/static/js/shared/api.js` | sincronização com backend, histórico carregado, envio, preview | `state.laudoAtualId`, `state.historicoConversa`, `_estadoRelatorio` |
| Datasets do DOM | `document.body.dataset` e `document.documentElement.dataset` | estado refletido para CSS e módulos desacoplados | `threadTab`, `inspectorScreen`, `laudoAtualId` |
| Armazenamento local | localStorage/sessionStorage | persistência parcial entre navegações | `tariel_laudo_atual`, `tariel_force_home_landing` |

## Estado em `chat_index_page.js`

### Confirmado no código

`web/static/js/chat/chat_index_page.js` mantém um objeto `estado` que inclui pelo menos:

- `tipoTemplateAtivo`
- `statusMesa`
- `statusMesaDescricao`
- `modoInspecaoUI`
- `workspaceStage`
- `inspectorScreen`
- `workspaceVisualContext`
- `modalNovaInspecaoPrePrompt`
- `filtroPendencias`
- `mesaWidgetAberto`
- `mesaWidgetMensagens`
- `mesaWidgetTemMais`
- `mesaWidgetNaoLidas`
- `mesaWidgetConexao`
- `mesaWidgetAnexoPendente`
- `mesaWidgetReferenciaAtiva`
- `retomadaHomePendente`
- estado de busca/filtro da timeline
- contexto fixado

## Estado em `chat_painel_core.js`

### Confirmado no código

`web/static/js/chat/chat_painel_core.js` cria `window.TarielChatPainel` e mantém um `STATE` global com:

- `laudoAtualId`
- `estadoRelatorio`
- `historicoConversa`
- `ultimoDiagnosticoBruto`
- `iaRespondendo`
- estado de anexos/documentos pendentes

Esse módulo também define:

- `KEY_LAUDO_ATUAL = "tariel_laudo_atual"`
- `ATALHO_MESA_AVALIADORA = "@insp "`

## Estado em `shared/api.js`

### Confirmado no código

`web/static/js/shared/api.js` mantém outro estado interno com:

- `laudoAtualId`
- `_estadoRelatorio`
- `historicoConversa`
- histórico paginado e cursores
- flags de preview/anexo/imagem

Esse arquivo é a ponte entre UI e `shared/chat-network.js`.

## Datasets do DOM

## `document.body.dataset`

Valores confirmados no fluxo atual:

- `inspecaoUi`
- `workspaceStage`
- `inspectorScreen`
- `homeActionVisible`
- `threadTab`
- `laudoAtualId`
- `forceHomeLanding`
- `estadoRelatorio`
- `finalizandoLaudo`
- `iaRespondendo`
- `apiEvents`

## `document.documentElement.dataset`

Valores confirmados:

- `chatPainelCore`
- `chatPainelBoot`
- `chatBootstrapOwner`
- `uiDockRapidoWired`
- `uiHomeActionWired`
- `uiEvents`

## Query Params

Parâmetros confirmados:

- `home=1`
- `laudo=<id>`

### Uso prático

- `home=1` força o portal
- `laudo=<id>` tenta selecionar um laudo no boot

## localStorage e sessionStorage

### localStorage

- `tariel_laudo_atual`
- `tariel_modo_resposta`
- `tariel_modo_foco`
- `tariel_workspace_contexto_fixado_${laudoId || "ativo"}`

### sessionStorage

- `tariel_force_home_landing`
- `tariel_workspace_retomada_home_pendente`

## Data Attributes Importantes

### Navegação e fluxo

- `data-action="go-home"`
- `data-home-destino`
- `data-open-inspecao-modal`
- `data-screen-controller="inspector"`
- `data-screen-root="portal"`, `"workspace"`, `"mesa-widget"`
- `data-workspace-view-root="assistant_landing"`, `"inspection_record"`, `"inspection_conversation"`

### Portal/home

- `data-home-laudo-id`
- `data-home-template`
- `data-home-title`
- `data-home-subtitle`
- `data-home-status`

### Toolbar e chat

- `data-tab="chat"`
- `data-tab="anexos"`
- `data-chat-filter`
- `data-chat-status`

### Pendências

- `data-filtro-pendencias`

### Contexto e ações de mensagem

- `data-context-remove-index`
- `data-ref-id`
- `data-responder-mensagem-id`
- `data-ir-mensagem-id`

## Eventos DOM Relevantes

## Eventos de navegação e screen mode

- `tariel:navigate-home`
- `tariel:screen-synced`
- `tariel:thread-tab-alterada`
- `popstate`

## Eventos de chat e mensagem

- `tariel:mensagem-copiar`
- `tariel:mensagem-citar`
- `tariel:mensagem-fixar-contexto`
- `tariel:mensagem-enviar-mesa`
- `tariel:chat-status`
- `tariel:prompt-enviado`
- `tariel:executar-comando-slash`

## Eventos de ciclo de vida do laudo

- `tariel:laudo-selecionado`
- `tariel:estado-relatorio`
- `tariel:relatorio-iniciado`
- `tariel:relatorio-finalizado`
- `tariel:cancelar-relatorio`
- `tariel:gate-qualidade-falhou`
- `tariel:historico-laudo-renderizado`

## Eventos de mesa

- `tariel:mesa-avaliadora-ativada`
- `tariel:mesa-status`

## Aliases legados ainda escutados

### Confirmado no código

`chat_index_page.js` ainda escuta aliases sem `:`:

- `tarielrelatorio-iniciado`
- `tarielrelatorio-finalizado`
- `tarielrelatorio-cancelado`
- alias legado para mesa/status/gate/histórico

Isso é evidência direta de compatibilidade retroativa ainda ativa.

## Listeners e módulos de sincronização

## `web/static/js/shared/ui.js`

Responsabilidades:

- intercepta clique em `[data-action="go-home"]`
- dispara `solicitarNavegacaoHome(...)`
- sincroniza o quick dock conforme `document.body.dataset.homeActionVisible`
- persiste modo foco e modo resposta

## `web/static/js/chat/chat_index_page.js`

Responsabilidades:

- escuta `tariel:navigate-home`
- resolve screen mode
- sincroniza `portal` vs `workspace`
- sincroniza view interna do workspace
- filtra timeline
- renderiza contexto IA, progresso, atividade, mesa card e anexos
- observa mutações em `#area-mensagens`

## `web/static/js/chat/chat_painel_laudos.js`

Responsabilidades:

- consome `home=1`
- lê `?laudo=`
- lê `localStorage["tariel_laudo_atual"]`
- atualiza URL e seleção de laudo
- reage a `popstate`

## `web/static/js/shared/api.js`

Responsabilidades:

- dispara eventos de API/estado
- carrega histórico
- envia prompt
- injeta mensagens no DOM via renderer

## Observadores e sincronização derivada

### Confirmado no código

`chat_index_page.js::inicializarObservadorWorkspace()` usa `MutationObserver` em `#area-mensagens` para manter o estado derivado do workspace sincronizado:

- screen mode
- contexto IA
- contadores
- painéis do rail

## Fallbacks e sincronizações legadas

### Confirmado no código

- `web/static/js/chat/chat_painel_laudos.js::garantirThreadNav()` recria `.thread-nav` se ela não existir.
- `web/static/js/shared/api.js::renderizarHistoricoCarregado()` injeta conteúdo sintético quando o histórico real é vazio ou insuficiente.
- `web/static/js/inspetor/pendencias.js` injeta pendências placeholder quando não há pendências abertas reais.

Esses pontos são centrais para entender por que a UI pode parecer "bagunçada" mesmo quando os dados reais não justificariam aquele estado visual.

## Confirmado no Código

- O estado do inspetor é distribuído e redundante.
- Datasets do DOM são parte ativa do contrato entre módulos.
- `chat_index_page.js` é a autoridade de screen mode, mas não a única autoridade de laudo/estado.
- A sincronização depende fortemente de eventos customizados e storage.

## Inferência

- Qualquer refatoração segura precisará primeiro reduzir o número de fontes de verdade para laudo atual, estado de relatório e screen mode.

## Dúvida Aberta

- Não há um contrato formal explícito definindo precedência entre `chat_index_page.js`, `TarielChatPainel`, `window.TarielAPI` e `document.body.dataset` quando eles entram em divergência.
