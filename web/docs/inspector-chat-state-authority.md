# Chat Inspetor: Autoridade de Estado

## Escopo desta fase

- Confirmado no código: esta fase consolidou a autoridade de estado do inspetor sem alterar backend, endpoints, contratos de dados, SSE, mesa, anexos, envio, finalização ou reabertura.
- Confirmado no código: a reconciliação ficou centralizada em [web/static/js/chat/chat_index_page.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/chat/chat_index_page.js).
- Confirmado no código: `TarielChatPainel` e `TarielAPI` continuam existindo, mas passaram a participar da reconciliação de forma explícita.

## Reconciliador central

### Estrutura principal

- Confirmado no código: a estrutura global `window.TarielInspectorState` agora expõe:
  - `resolverEstadoAutoritativoInspector(overrides)`
  - `sincronizarEstadoInspector(overrides, opts)`
  - `obterSnapshotEstadoInspectorAtual()`
- Confirmado no código: `resolverEstadoAutoritativoInspector()` monta o snapshot autoritativo.
- Confirmado no código: `sincronizarEstadoInspector()` aplica esse snapshot ao runtime, compatibilidade legada, datasets e storage.

### Separação de responsabilidades

- Confirmado no código: cálculo do snapshot ocorre em `resolverEstadoAutoritativoInspector()`.
- Confirmado no código: aplicação do snapshot local ocorre em `aplicarSnapshotEstadoInspector()`.
- Confirmado no código: espelho para compatibilidade ocorre em `espelharEstadoInspectorCompat()`.
- Confirmado no código: espelho para datasets ocorre em `espelharEstadoInspectorNoDataset()`.
- Confirmado no código: espelho para storage ocorre em `espelharEstadoInspectorNoStorage()`.

## Precedência adotada por campo

### `laudoAtualId`

- Fonte primária no runtime: ações explícitas que chamam `sincronizarEstadoInspector({ laudoAtualId })`.
- Participantes de reconciliação: `window.TarielAPI`, `window.TarielChatPainel`, datasets, SSR, URL e `localStorage`.
- Ordem confirmada no código:
  1. override explícito
  2. `window.TarielAPI.obterSnapshotEstadoCompat()` / `obterLaudoAtualId()`
  3. `window.TarielChatPainel.obterSnapshotEstadoPainel()` / `state.laudoAtualId`
  4. `dataset` (`#painel-chat` / `document.body`)
  5. SSR (`window.TARIEL.laudoAtivoId`)
  6. URL (`?laudo=`)
  7. `localStorage` (`tariel_laudo_atual`)
  8. estado local já reconciliado

### `estadoRelatorio`

- Fonte primária no runtime: ações explícitas e eventos que chamam `sincronizarEstadoInspector({ estadoRelatorio })`.
- Participantes de reconciliação: `TarielAPI`, `TarielChatPainel`, datasets e SSR.
- Ordem confirmada no código:
  1. override explícito
  2. `window.TarielAPI.obterSnapshotEstadoCompat()` / `obterEstadoRelatorioNormalizado()`
  3. `window.TarielChatPainel.obterSnapshotEstadoPainel()` / `state.estadoRelatorio`
  4. `dataset`
  5. SSR (`window.TARIEL.estadoRelatorio`)
  6. estado local já reconciliado

### `modoInspecaoUI`

- Fonte primária no runtime: ações explícitas do inspetor (`definirModoInspecaoUI`, Home, seleção de fluxo).
- Fallback de boot: SSR/dataset.
- Regra extra confirmada no código: `forceHomeLanding` vence `modoInspecaoUI` quando não há override explícito.
- Ordem confirmada no código:
  1. override explícito
  2. `dataset`
  3. SSR (`#painel-chat[data-inspecao-ui]`)
  4. estado local já reconciliado
  5. ajuste derivado por `forceHomeLanding`

### `workspaceStage`

- Fonte primária no runtime: ações explícitas (`definirWorkspaceStage`, início/cancelamento/retomada de inspeção).
- Fallback de boot: dataset SSR.
- Regra extra confirmada no código: em `modoInspecaoUI === "home"`, o fallback seguro vira `assistant` se não houver override explícito.
- Ordem confirmada no código:
  1. override explícito
  2. `dataset`
  3. SSR (`#painel-chat[data-workspace-stage]`)
  4. estado local já reconciliado
  5. derivação por contexto (`estadoRelatorio` / `laudoAtualId`)

### `threadTab`

- Fonte primária no runtime: ação explícita de troca de tab.
- Fallback de boot: `dataset`.
- Ordem confirmada no código:
  1. override explícito
  2. `dataset`
  3. estado local já reconciliado
  4. fallback `"chat"`

### `forceHomeLanding`

- Fonte primária no runtime: ações explícitas de Home e consumo de boot.
- Fallback de boot: query param `?home=1` e `sessionStorage`.
- Ordem confirmada no código:
  1. override explícito
  2. `dataset`
  3. `sessionStorage` (`tariel_force_home_landing`) e URL
  4. estado local já reconciliado

### `retomadaHomePendente`

- Fonte primária no runtime: `definirRetomadaHomePendente(...)`, que passa pelo reconciliador.
- Fallback de boot: `sessionStorage` (`tariel_workspace_retomada_home_pendente`).
- Ordem confirmada no código:
  1. override explícito
  2. estado local válido e não expirado
  3. storage válido e não expirado
  4. `null`

### `inspectorScreen`

- Confirmado no código: não é mais tratado como campo primário independente.
- Confirmado no código: agora ele é derivado do snapshot reconciliado por `resolverInspectorBaseScreenPorSnapshot(snapshot)`.
- Regras confirmadas:
  - `modoInspecaoUI === "home"` => `portal_dashboard`
  - `workspaceStage === "assistant"` => `assistant_landing`
  - `threadTab === "chat"` com linhas => `inspection_conversation`
  - caso contrário => `inspection_record`
  - `overlayOwner === "new_inspection"` => `inspectorScreen = "new_inspection"`

### `homeActionVisible`

- Confirmado no código: virou campo derivado, não mais fonte primária.
- Regra confirmada: só fica `true` quando não há overlay ativo e `inspectorBaseScreen` está em `inspection_record` ou `inspection_conversation`.

## O que virou fonte primária, fallback ou reflexo

### Fontes primárias

- Confirmado no código: ações explícitas do usuário e do runtime atual via `sincronizarEstadoInspector(...)`.
- Confirmado no código: `resolverEstadoAutoritativoInspector(...)` é a autoridade de precedência.

### Fontes de boot e fallback

- Confirmado no código: SSR (`window.TARIEL` e `#painel-chat[data-*]`) inicializa o snapshot quando ainda não existe estado reconciliado.
- Confirmado no código: URL `?laudo=` e `localStorage` continuam como fallback para `laudoAtualId`.
- Confirmado no código: URL `?home=1` e `sessionStorage` continuam como fallback para `forceHomeLanding`.

### Fontes refletidas

- Confirmado no código: `document.body.dataset.*` e `#painel-chat.dataset.*` agora são majoritariamente espelho do snapshot reconciliado.
- Confirmado no código: `inspectorScreen`, `inspectorBaseScreen` e `homeActionVisible` são derivados e espelhados, não escolhidos de forma solta.

## Compatibilidade legada preservada

### `TarielChatPainel`

- Confirmado no código: [web/static/js/chat/chat_painel_core.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/chat/chat_painel_core.js) agora expõe:
  - `sincronizarEstadoPainel(parcial)`
  - `obterSnapshotEstadoPainel()`
- Confirmado no código: o core também reage a `tariel:laudo-selecionado` e `tariel:estado-relatorio`.

### `TarielAPI`

- Confirmado no código: [web/static/js/shared/api.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/shared/api.js) agora expõe:
  - `sincronizarEstadoCompat(payload)`
  - `obterSnapshotEstadoCompat()`
- Confirmado no código: isso mantém compatibilidade com `chat_index_page.js` sem reescrever o módulo.

### Módulos legados que foram redirecionados

- Confirmado no código: [web/static/js/chat/chat_painel_laudos.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/chat/chat_painel_laudos.js) passou a usar o reconciliador para `laudoAtualId`, `threadTab` e `forceHomeLanding`.
- Confirmado no código: [web/static/js/chat/chat_painel_relatorio.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/chat/chat_painel_relatorio.js) passou a usar o reconciliador para `laudoAtualId`, `estadoRelatorio` e limpeza de `forceHomeLanding`.
- Confirmado no código: [web/static/js/chat/chat_painel_historico_acoes.js](/home/gabriel/%C3%81rea%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/static/js/chat/chat_painel_historico_acoes.js) passou a usar o reconciliador ao limpar o laudo selecionado.

## Datasets e storages que continuam existindo por compatibilidade

### Datasets

- Confirmado no código: `document.body.dataset.laudoAtualId`
- Confirmado no código: `document.body.dataset.estadoRelatorio`
- Confirmado no código: `document.body.dataset.inspecaoUi`
- Confirmado no código: `document.body.dataset.workspaceStage`
- Confirmado no código: `document.body.dataset.threadTab`
- Confirmado no código: `document.body.dataset.forceHomeLanding`
- Confirmado no código: `document.body.dataset.inspectorScreen`
- Confirmado no código: `document.body.dataset.inspectorBaseScreen`
- Confirmado no código: `document.body.dataset.inspectorOverlayOwner`
- Confirmado no código: `document.body.dataset.homeActionVisible`
- Confirmado no código: `document.body.dataset.inspectorStateDivergence`

### Storage

- Confirmado no código: `localStorage["tariel_laudo_atual"]` continua como persistência/fallback do laudo.
- Confirmado no código: `sessionStorage["tariel_force_home_landing"]` continua como persistência/fallback de retorno Home.
- Confirmado no código: `sessionStorage["tariel_workspace_retomada_home_pendente"]` continua como persistência/fallback da retomada.

## Divergência e instrumentação

- Confirmado no código: `resolverEstadoAutoritativoInspector()` registra warning único em desenvolvimento quando detecta divergência entre fontes relevantes de `laudoAtualId` ou `estadoRelatorio`.
- Confirmado no código: a UI não quebra em caso de divergência; o reconciliador escolhe um valor por precedência e espelha esse resultado.
- Confirmado no código: o body recebe `data-inspector-state-divergence` para diagnóstico leve.

## Hooks e consumers preservados

- Confirmado no código: `chat_painel_laudos.js` continua compatível com URL, `localStorage` e `TarielChatPainel`.
- Confirmado no código: `shared/api.js` continua emitindo `tariel:estado-relatorio`, `tariel:relatorio-iniciado`, `tariel:relatorio-finalizado` e `tariel:laudo-card-sincronizado`.
- Confirmado no código: `shared/ui.js` continua lendo datasets para Home rápido e screen mode.
- Confirmado no código: screen mode, tabs, busca, filtros, rail, mesa widget e composer continuam consumindo os mesmos hooks públicos relevantes.

## O que ainda permanece legado ou arriscado

- Confirmado no código: ainda existem fallbacks legados em módulos como `chat_painel_laudos.js` e `chat_painel_relatorio.js` caso `window.TarielInspectorState` não esteja disponível.
- Confirmado no código: aliases legados de eventos não foram removidos.
- Confirmado no código: `shared/api.js` ainda mantém estado interno próprio para o chat.
- Confirmado no código: `TarielChatPainel.state` ainda existe e continua sendo preenchido por compatibilidade.
- Inferência: a próxima fase natural é reduzir ainda mais leituras diretas de dataset e fechar melhor os pontos de boot duplicados.
- Dúvida aberta: ainda não há uma camada formal única de “state transitions” para todos os fluxos históricos do produto; esta fase consolidou precedência e espelho, mas não reescreveu todos os caminhos antigos.
