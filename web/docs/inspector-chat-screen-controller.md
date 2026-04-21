# Inspector Chat Screen Controller

## Objetivo

Este controller centraliza a decisão de tela do frontend do inspetor sem alterar backend, contratos, eventos de negócio ou handlers principais.

A decisão final de tela agora é resolvida em `static/js/chat/chat_index_page.js` por `resolveInspectorScreen()`.

## Estados antigos que entram no resolver

O resolver usa somente estado já existente na stack atual:

- `estado.modoInspecaoUI`
  - `home`
  - `workspace`
- `estado.workspaceStage`
  - `assistant`
  - `inspection`
- estado visual do modal de nova inspeção
  - `#modal-nova-inspecao.hidden`
  - `#modal-nova-inspecao.classList.contains("ativo")`
- aba atual da thread
  - `document.body.dataset.threadTab`
- presença de linhas reais no workspace
  - `coletarLinhasWorkspace()`

## Screen modes resultantes

### `portal_dashboard`

Resultado quando:

- `estado.modoInspecaoUI === "home"`
- e o modal de nova inspeção não está aberto

Efeito visual:

- root do portal ativo
- root do workspace inativo
- root do mesa widget inativo

### `assistant_landing`

Resultado quando:

- `estado.modoInspecaoUI === "workspace"`
- `estado.workspaceStage === "assistant"`
- e o modal de nova inspeção não está aberto

Efeito visual:

- root do workspace ativo
- root do portal inativo
- root do mesa widget ativo

### `new_inspection`

Resultado quando:

- o modal `Nova Inspeção` está aberto

Efeito visual:

- root do workspace ativo
- root do portal inativo
- root do mesa widget ativo

Observação:

- nesta fase o modal continua sendo modal;
- o screen mode só passa a tratá-lo como modo explícito dentro da área de workspace.

### `inspection_record`

Resultado quando:

- `estado.modoInspecaoUI === "workspace"`
- `estado.workspaceStage === "inspection"`
- e a aba atual não é uma conversa ativa com linhas renderizadas

Casos típicos:

- aba `anexos`
- laudo técnico aberto sem conversa renderizada suficiente para classificar como conversa ativa

### `inspection_conversation`

Resultado quando:

- `estado.modoInspecaoUI === "workspace"`
- `estado.workspaceStage === "inspection"`
- aba atual `chat`
- existem linhas renderizadas em `coletarLinhasWorkspace()`

## Roots que passaram a obedecer ao controller

### Root `portal`

Arquivo:

- `templates/inspetor/_portal_home.html`

Marcadores:

- `data-screen-root="portal"`
- `data-active="true|false"`
- `aria-hidden`
- `hidden`
- `inert`

### Root `workspace`

Arquivo:

- `templates/inspetor/_workspace.html`

Marcadores:

- `data-screen-root="workspace"`
- `data-active="true|false"`
- `aria-hidden`
- `hidden`
- `inert`

### Root `mesa-widget`

Arquivo:

- `templates/inspetor/_portal_main.html`

Marcadores:

- `data-screen-root="mesa-widget"`
- `data-active="true|false"`
- `aria-hidden`
- `hidden`
- `inert`

## Sincronização aplicada pelo runtime

O runtime agora escreve o resultado consolidado em:

- `body.dataset.inspectorScreen`
- `#painel-chat.dataset.inspectorScreen`

A sincronização de roots é feita por:

- `resolveInspectorScreen()`
- `sincronizarInspectorScreen()`
- `definirRootAtivo()`

## Resultado desta fase

Sem desmontar agressivamente o DOM, o portal e o workspace deixam de concorrer visualmente ao mesmo tempo.

Os hooks existentes continuam no lugar. A mudança desta fase é de autoridade de layout, não de regra de negócio.
