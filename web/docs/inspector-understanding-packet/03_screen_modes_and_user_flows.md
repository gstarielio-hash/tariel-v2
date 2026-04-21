# 03. Screen Modes e Fluxos do Usuário

## Screen Modes Confirmados

Os modos abaixo são confirmados em `web/static/js/chat/chat_index_page.js::resolveInspectorScreen()`.

| Screen mode | Gatilho de entrada | Root/template principal | Controlador | Regiões visíveis principais | Próximo fluxo típico |
| --- | --- | --- | --- | --- | --- |
| `portal_dashboard` | `estado.modoInspecaoUI === "home"` ou `?home=1` | `web/templates/inspetor/_portal_home.html` | `chat_index_page.js` | portal, cards, recentes, ações rápidas | abrir laudo, abrir modal nova inspeção |
| `assistant_landing` | workspace ativo com `estado.workspaceStage === "assistant"` | `web/templates/inspetor/workspace/_assistant_landing.html` | `chat_index_page.js` | header, landing do assistente, composer/contexto parcial | nova inspeção |
| `new_inspection` | `#modal-nova-inspecao` aberto | `web/templates/inspetor/modals/_nova_inspecao.html` sobre workspace | `chat_index_page.js` + `inspetor/modals.js` | modal nova inspeção | iniciar laudo |
| `inspection_record` | laudo ativo sem conversa visível, ou tab `anexos`, ou chat vazio | `web/templates/inspetor/workspace/_inspection_record.html` | `chat_index_page.js` | header, toolbar, anexos, rail, composer | anexar, começar conversa, finalizar |
| `inspection_conversation` | laudo ativo com tab `chat` e mensagens renderizadas | `web/templates/inspetor/workspace/_inspection_conversation.html` | `chat_index_page.js` | header, toolbar, mensagens, rail, composer | continuar conversa, mesa, finalizar |

## Regra de Resolução de Tela

### Confirmado no código

`web/static/js/chat/chat_index_page.js::resolveInspectorScreen()` aplica esta ordem:

1. se o modal de nova inspeção está aberto, retorna `new_inspection`
2. se `estado.modoInspecaoUI === "home"`, retorna `portal_dashboard`
3. se `estado.workspaceStage === "assistant"`, retorna `assistant_landing`
4. se `document.body.dataset.threadTab === "chat"` e existem linhas em `#area-mensagens`, retorna `inspection_conversation`
5. caso contrário, retorna `inspection_record`

## Modo por Modo

## `portal_dashboard`

### Gatilho de entrada

- `GET /app/?home=1`
- click em qualquer affordance `data-action="go-home"`
- `web/static/js/chat/chat_painel_laudos.js::consumirFlagTelaInicial()`
- `web/static/js/chat/chat_index_page.js::navegarParaHome()`

### Template root

- `web/templates/inspetor/_portal_home.html`
- root: `#tela-boas-vindas`

### Dados/flags que ativam

- `document.body.dataset.forceHomeLanding = "true"`
- `estado.modoInspecaoUI = "home"`
- `data-inspector-screen="portal_dashboard"`

### Regiões que aparecem

- cards de status
- laudos recentes
- atalhos rápidos por modelo
- CTA de nova inspeção

### Ações do usuário

- abrir modal nova inspeção em `#btn-abrir-modal-novo`
- abrir histórico expandido
- abrir laudo recente por card `.portal-report-card`
- selecionar modelo rápido `.portal-model-card.btn-acao-rapida`

### Próximo fluxo

- `new_inspection`
- `inspection_record`
- `inspection_conversation`

## `assistant_landing`

### Gatilho de entrada

- workspace ativo sem laudo em andamento
- SSR inicial em `_portal_main.html` quando `workspace_stage_inicial == "assistant"`
- boot client-side em `chat_index_page.js`

### Template root

- `web/templates/inspetor/workspace/_assistant_landing.html`
- root: `#workspace-assistant-landing`

### Dados/flags que ativam

- `estado.workspaceStage = "assistant"`
- `data-workspace-view-root="assistant_landing"`

### Regiões que aparecem

- header interno compartilhado
- landing com prompts rápidos
- botão de abrir nova inspeção
- composer compartilhado

### Ações do usuário

- abrir modal de nova inspeção
- clicar em prompt `[data-assistant-prompt]`

### Próximo fluxo

- `new_inspection`

## `new_inspection`

### Gatilho de entrada

- click em `[data-open-inspecao-modal]`
- ações de modelo rápido no portal

### Template root

- `web/templates/inspetor/modals/_nova_inspecao.html`
- modal root: `#modal-nova-inspecao`

### JS que controla

- `web/static/js/inspetor/modals.js`
- integração com `web/static/js/chat/chat_index_page.js`

### Dados/flags que ativam

- modal com `.ativo`
- `resolveInspectorScreen()` detecta modal aberto

### Ações do usuário

- selecionar template
- preencher local, cliente, unidade, objetivo
- editar nome da inspeção
- confirmar abertura

### Próximo fluxo

- `inspection_record` ou `inspection_conversation`, dependendo do histórico e tab

## `inspection_record`

### Gatilho de entrada

- laudo ativo selecionado
- tab `anexos`
- ausência de mensagens no chat

### Template root

- `web/templates/inspetor/workspace/_inspection_record.html`
- root funcional: `#workspace-anexos-panel`

### JS que controla

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/hardware.js`

### Regiões que aparecem

- header interno
- toolbar com tabs
- painel de anexos
- rail de contexto
- composer

### Ações do usuário

- anexar arquivo em `#btn-anexo` / `#input-anexo`
- foto rápida em `#btn-foto-rapida`
- alternar para tab `chat`
- finalizar ou preview

### Próximo fluxo

- `inspection_conversation`
- finalização/gate
- Home

## `inspection_conversation`

### Gatilho de entrada

- tab `chat`
- existência de mensagens renderizadas em `#area-mensagens`

### Template root

- `web/templates/inspetor/workspace/_inspection_conversation.html`
- root funcional: `#area-mensagens`

### JS que controla

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-render.js`
- `web/static/js/shared/chat-network.js`
- `web/static/js/chat/chat_painel_mesa.js`

### Regiões que aparecem

- árvore de mensagens
- indicador digitando `#indicador-digitando`
- botão ir para fim `#btn-ir-fim-chat`
- toolbar de busca/filtro
- rail de contexto e mesa
- composer

### Ações do usuário

- enviar mensagem
- citar/copiar/fixar contexto
- enviar para mesa
- filtrar/buscar timeline
- finalizar inspeção

### Próximo fluxo

- permanência na conversa
- `inspection_record`
- Home
- gate de qualidade

## Fluxos do Usuário

## 1. Abrir Home/Portal

### Passo a passo

1. O usuário entra em `GET /app/?home=1`, ou clica em um elemento com `data-action="go-home"`.
2. `web/static/js/shared/ui.js::inicializarAcaoHome()` intercepta o clique e chama `solicitarNavegacaoHome(...)`.
3. Esse método dispara `CustomEvent("tariel:navigate-home")`.
4. `web/static/js/chat/chat_index_page.js::bindEventosPagina()` escuta esse evento.
5. `processarAcaoHome()` chama `navegarParaHome(destino, { preservarContexto })`.
6. `navegarParaHome()` limpa `tariel_laudo_atual`, remove `?laudo=`, opcionalmente marca `sessionStorage["tariel_force_home_landing"] = "1"` e navega para `/app/?home=1`.
7. No novo load SSR, `_portal_main.html` entra em `portal_dashboard`.

### Arquivos envolvidos

- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/inspetor/_sidebar.html`
- `web/templates/inspetor/workspace/_workspace_header.html`

## 2. Clicar no assistente

### Passo a passo

1. O usuário cai no workspace com `assistant_landing`.
2. A landing está em `#workspace-assistant-landing`.
3. O clique em um prompt `[data-assistant-prompt]` é tratado por `chat_index_page.js`.
4. O prompt é inserido no composer ou usado como pré-contexto de nova inspeção.

### Observação

- O papel exato do prompt depende de `chat_index_page.js` e do contexto ativo. Em uso normal, ele acelera a transição para iniciar uma coleta.

## 3. Clicar em Nova Inspeção

### Passo a passo

1. O usuário clica em `[data-open-inspecao-modal]`.
2. `web/static/js/inspetor/modals.js::abrirModalNovaInspecao()` abre `#modal-nova-inspecao`.
3. Enquanto o modal está aberto, `resolveInspectorScreen()` retorna `new_inspection`.
4. O usuário preenche template, equipamento, cliente e unidade.
5. Ao confirmar, `chat_index_page.js` chama `iniciarInspecao(tipo, { contextoVisual })`.
6. O laudo é iniciado via API e o contexto visual do workspace é atualizado.
7. O modal fecha e o fluxo continua em inspeção ativa.

## 4. Abrir Laudos Recentes

### Passo a passo

1. O backend já injeta os cards e itens recentes via `_montar_contexto_portal_inspetor()`.
2. No portal, os cards `.portal-report-card` já carregam dados como `data-home-laudo-id`, `data-home-template`, `data-home-title`, `data-home-subtitle`, `data-home-status`.
3. O clique vai para `chat_index_page.js::abrirLaudoPeloHome(...)`.
4. Esse método tenta usar `window.TarielChatPainel.selecionarLaudo(...)`.
5. Se não houver esse caminho, cai no fallback `window.TarielAPI.carregarLaudo(...)` e emite `tariel:laudo-selecionado`.

## 5. Abrir um Laudo em Andamento

### Caminhos confirmados

- card do Home
- item da sidebar/histórico
- query param `?laudo=<id>`
- laudo persistido em `localStorage["tariel_laudo_atual"]`

### Arquivos envolvidos

- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/shared/api.js`
- `web/static/js/chat/chat_sidebar.js`
- `web/app/domains/chat/auth_portal_routes.py`

## 6. Entrar em Registro Técnico

### Interpretação adotada

No runtime atual, "Registro Técnico" corresponde ao estado visual `inspection_record`, centrado na view de anexos/registro do laudo.

### Passo a passo

1. Um laudo ativo é selecionado.
2. O screen mode fica em `inspection_record` se a tab atual for `anexos`, ou se ainda não houver mensagens renderizadas.
3. O conteúdo principal vem de `web/templates/inspetor/workspace/_inspection_record.html`.
4. O painel usa `#workspace-anexos-panel`, `#workspace-anexos-grid` e `#workspace-anexos-count`.

## 7. Entrar em Conversa Ativa

### Passo a passo

1. Um laudo ativo já existe.
2. A toolbar muda para tab `chat`.
3. `document.body.dataset.threadTab` passa a `"chat"`.
4. Se `#area-mensagens` tiver linhas, `resolveInspectorScreen()` retorna `inspection_conversation`.
5. A árvore de mensagens fica visível e o rail se mantém sincronizado.

## 8. Usar busca, filtros e tabs

### Passo a passo

1. A toolbar compartilhada está em `web/templates/inspetor/workspace/_workspace_toolbar.html`.
2. O campo `#chat-thread-search` e os botões `[data-chat-filter]` pertencem a essa mesma estrutura.
3. `chat_index_page.js::filtrarTimelineWorkspace()` usa texto + filtro ativo para esconder/mostrar `.linha-mensagem`.
4. As tabs `.thread-tab[data-tab="chat"]` e `.thread-tab[data-tab="anexos"]` atualizam `document.body.dataset.threadTab`.
5. O listener `tariel:thread-tab-alterada` também participa da sincronização.

## 9. Usar anexos

### Passo a passo

1. O usuário aciona `#btn-anexo` ou `#btn-foto-rapida`.
2. `#input-anexo` é usado para upload.
3. `web/static/js/shared/hardware.js` e `web/static/js/shared/api.js` coordenam preview, limpeza e envio.
4. O backend relevante inclui `POST /app/api/upload_doc` e, para mesa, `POST /app/api/laudo/{laudo_id}/mesa/anexo`.
5. A UI reflete anexos em `#preview-anexo`, `#workspace-anexos-grid` e no widget de mesa, quando aplicável.

## 10. Usar mesa, pendências e contexto IA

### Mesa

1. O usuário abre `#btn-mesa-widget-toggle`.
2. `web/static/js/inspetor/mesa_widget.js` carrega resumo e mensagens.
3. Também é possível acionar a mesa por prefixo `@insp ` via `web/static/js/chat/chat_painel_mesa.js`.

### Pendências

1. O rail direito contém `#painel-pendencias-mesa`.
2. `web/static/js/inspetor/pendencias.js` chama os endpoints de pendências e paginação.
3. Filtros usam `[data-filtro-pendencias]`.

### Contexto IA

1. O rail renderiza resumo, evidências, pendências, mesa, equipamento e operação.
2. `chat_index_page.js` calcula e renderiza isso com base no estado da conversa e do laudo.
3. O usuário pode fixar contexto em localStorage usando eventos de mensagem.

## 11. Voltar para Home

### Passo a passo

1. O usuário clica no link Portal da sidebar, no botão do header ou no quick dock.
2. Todos usam `data-action="go-home"`.
3. `shared/ui.js` dispara `tariel:navigate-home`.
4. `chat_index_page.js` centraliza a implementação e navega para `/app/?home=1`.
5. Opcionalmente, o frontend preserva contexto para retomada posterior usando sessionStorage.

## Confirmado no Código

- Os modos de tela não são rotas distintas; são resolvidos em uma única página.
- O botão Home do header, o link Portal da sidebar e o quick dock convergem para a mesma semântica de navegação.
- A diferença entre `inspection_record` e `inspection_conversation` depende da tab e da existência de mensagens.

## Inferência

- `new_inspection` é um mode operacional, não uma "tela" no sentido de layout independente; ele sobrepõe um modal ao workspace e força a semântica de estado.

## Dúvida Aberta

- O termo de produto "Registro técnico" não aparece como string dominante no runtime; a correspondência mais segura hoje é com `inspection_record`.
