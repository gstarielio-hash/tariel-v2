# Inspector Performance Audit

## Objetivo

Registrar a Fase 0 de auditoria de performance do Chat Inspetor sem alterar backend, contratos, regras de negócio, fluxos funcionais ou layout. A instrumentação é exclusivamente de desenvolvimento e fica desligada fora do modo `perf`.

## Ativação

- `?perf=1` na URL
- ou `localStorage.tarielPerf = "1"`

O runtime de perf nasce em `web/static/js/shared/api-core.js` e expõe `window.TarielPerf`.

## Logger global

`window.TarielPerf` expõe:

- `printSummary()`
- `getReport()`
- `clear()`
- `topFunctions()`
- `topNetwork()`
- `topLongTasks()`

O relatório agrupa amostras por categoria e mantém:

- `boot`
- `transition`
- `state`
- `render`
- `function`
- `network`
- `observer`
- `storage`
- `counter`

## Métricas coletadas

### Navegação e bootstrap

- navigation timing
- `DOMContentLoaded`
- `load`
- snapshots de DOM no boot
- boot dos módulos `ui`, `chat_painel_core` e `chat_index_page`
- prontidão de portal, workspace e composer

### Rede

- `fetch` e `XMLHttpRequest`
- URL
- método
- duração total
- status
- tamanho estimado do request
- `content-length` quando disponível
- `ttfbApproxMs` aproximado no `fetch`
- custo de leitura do corpo (`json`, `text`, `blob`, `arrayBuffer`)

### Runtime do navegador

- `PerformanceObserver` para `longtask`
- `paint`
- `largest-contentful-paint`
- `layout-shift`
- `resource`

### DOM e estrutura

Snapshots estruturais por região:

- sidebar
- portal
- workspace
- `#area-mensagens`
- rail direito
- modal de nova inspeção
- lista de laudos
- lista de pendências

Cada snapshot registra presença, visibilidade, contagem de nós e dimensões de scroll/client.

### Repetição excessiva

- contagem total de listeners
- listeners duplicados por alvo/tipo/listener/capture
- observers criados
- callbacks de observer
- escritas em `localStorage` e `sessionStorage`
- contadores de sincronização de dataset/storage no screen controller do inspetor

## Pontos instrumentados

### `web/static/js/shared/api-core.js`

- bootstrap do logger `TarielPerf`
- patch de `fetch`
- patch de `XMLHttpRequest`
- patch de `EventTarget.addEventListener`
- patch de `MutationObserver`
- patch de `Storage`
- capture de navigation/resource/paint/LCP/CLS/long tasks

### `web/static/js/shared/ui.js`

- `inicializar()`
- `inicializarDockRapido()`
- observer do dock rápido rotulado como `ui.dockRapido`

### `web/static/js/chat/chat_painel_core.js`

- `executarBootTasks()`
- cada boot task registrada
- `inicializarRenderChat()`
- `inicializarApiChat()`

### `web/static/js/chat/chat_painel_laudos.js`

- `selecionarLaudo()`
- `selecionarThreadTab()`
- início da transição de abertura de laudo
- início da transição de troca de tab da thread

### `web/static/js/chat/chat_painel_relatorio.js`

- `finalizarInspecaoCompleta()`
- `reabrirLaudoAtual()`
- `sincronizarEstadoRelatorioNaUI()`

### `web/static/js/chat/chat_painel_mesa.js`

- `ativarMesaAvaliadora()`
- `enviarParaMesaAvaliadora()`
- `wireMesaAvaliadoraHooks()`

### `web/static/js/inspetor/pendencias.js`

- `renderizarListaPendencias()`
- `carregarPendenciasMesa()`
- `marcarPendenciasComoLidas()`
- `exportarPendenciasPdf()`
- snapshots de DOM após render e carga

### `web/static/js/inspetor/mesa_widget.js`

- `carregarMensagensMesaWidget()`
- `enviarMensagemMesaWidget()`
- `abrirMesaWidget()`
- `fecharMesaWidget()`
- snapshots de DOM do widget

### `web/static/js/shared/chat-render.js`

- `adicionarMensagemInspetor()`
- `criarBolhaIA()`
- `adicionarMensagemNaUI()`
- `mostrarAcoesPosResposta()`
- `renderizarConfiancaIA()`
- `renderizarCitacoes()`

### `web/static/js/shared/api.js`

- `sincronizarEstadoRelatorioWrapper()`
- `renderizarHistoricoCarregado()`
- `carregarMensagensAntigasLaudoAtual()`
- `carregarLaudoPorId()`
- `processarEnvio()`
- término da transição de abertura de laudo quando o histórico termina de renderizar

### `web/static/js/chat/chat_index_page.js`

- `resolverInspectorBaseScreenPorSnapshot()`
- `resolverEstadoAutoritativoInspector()`
- `espelharEstadoInspectorNoDataset()`
- `espelharEstadoInspectorNoStorage()`
- `sincronizarEstadoInspector()`
- `resolveInspectorScreen()`
- `aplicarMatrizVisibilidadeInspector()`
- `sincronizarWorkspaceRail()`
- `sincronizarWidgetsGlobaisWorkspace()`
- `sincronizarInspectorScreen()`
- `atualizarPainelWorkspaceDerivado()`
- `atualizarThreadWorkspace()`
- `abrirChatLivreInspector()`
- `abrirNovaInspecaoComScreenSync()`
- `exibirConversaFocadaNovoChat()`
- `promoverPrimeiraMensagemNovoChatSePronta()`
- `boot()`
- observers rotulados:
  - `chat_index_page.sidebarHistorico`
  - `chat_index_page.workspace`

## Transições auditadas

- boot em `/app/`
- clique em `Novo Chat`
- entrada em `assistant_landing`
- primeira mensagem do `Novo Chat`
- promoção para focused conversation
- abertura de laudo
- troca de tab da thread
- abertura da modal de `Nova Inspeção`
- carga de pendências

## Hipóteses iniciais de gargalo por inspeção do código

Estas hipóteses são observacionais. Esta fase não corrige nada.

- `chat_index_page.js` concentra múltiplas fontes de sincronização de tela, com escrita repetida em `dataset`, storage e derivados de workspace.
- `sincronizarEstadoInspector()` e funções derivadas tendem a ser chamadas em cascata por eventos, resize e observers.
- o observer de `#area-mensagens` dispara `atualizarPainelWorkspaceDerivado()` e `promoverPrimeiraMensagemNovoChatSePronta()` após mutações frequentes da thread.
- `renderizarHistoricoCarregado()` limpa e reconstrói a área inteira de mensagens, o que é candidato a custo alto de DOM e layout em históricos maiores.
- o bootstrap local carrega muitos scripts independentes antes de estabilizar a tela do inspetor.
- a sidebar/histórico e painéis auxiliares possuem vários binds e observers que podem se sobrepor em cliques simples.
- pendências e mesa widget reconstroem listas completas de DOM e podem competir com o fluxo principal do chat.

## Escopo preservado

Não houve mudança em:

- backend
- endpoints
- contratos
- regras de negócio
- lógica de criação de laudo/contexto
- fluxo funcional de `Novo Chat`
- fluxo funcional de `Nova Inspeção`
- layout visual do produto
