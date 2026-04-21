# Fase 01: Observabilidade de Frontend

## Objetivo

Esta fase torna o frontend observável em modo dev/perf sem alterar fluxo funcional. O foco é medir first load, boot de shell, funções pesadas do runtime, rede, long tasks e snapshots leves de DOM.

## Confirmado no código desta fase

- `web/static/js/shared/api-core.js` já era a base de telemetria frontend e foi reaproveitado como runtime único de observabilidade.
- `web/templates/cliente_portal.html` injeta `api-core.js` quando `perf_mode` está ativo no backend.
- `web/templates/painel_revisor.html` injeta `api-core.js` quando `perf_mode` está ativo no backend.
- `web/templates/dashboard.html` injeta `api-core.js` quando `perf_mode` está ativo no backend.
- `web/static/js/cliente/portal.js` passou a medir boot, troca de abas, bootstrap, render geral e cargas de Chat/Mesa.
- `web/static/js/revisor/revisor_painel_core.js` expõe helpers de medição e snapshot para o shell da mesa.
- `web/static/js/revisor/painel_revisor_page.js` mede boot, WebSocket, carga do laudo, resposta do engenheiro e devolução.
- `web/static/js/revisor/revisor_painel_mesa.js` mede renderização de painel operacional, pacote e exportações.
- `web/static/js/revisor/revisor_painel_historico.js` mede timeline e carga de histórico.
- `web/static/js/revisor/revisor_painel_aprendizados.js` mede render e validação de aprendizados.

## Matriz de ativação

| Área | Script de observabilidade | Condição para carregar | Condição para coletar |
| --- | --- | --- | --- |
| `/app` | `web/static/js/shared/api-core.js` | já faz parte da shell do inspetor | `?perf=1` ou `localStorage.tarielPerf=1` |
| `/cliente/painel` | `web/static/js/shared/api-core.js` | `PERF_MODE=1` no backend | `?perf=1` ou `localStorage.tarielPerf=1` |
| `/revisao/painel` | `web/static/js/shared/api-core.js` | `PERF_MODE=1` no backend | `?perf=1` ou `localStorage.tarielPerf=1` |
| `/admin/painel` | `web/static/js/shared/api-core.js` | `PERF_MODE=1` no backend | `?perf=1` ou `localStorage.tarielPerf=1` |

Resumo prático:

1. para `/cliente`, `/revisao` e `/admin`, primeiro ligue `PERF_MODE=1` no backend;
2. depois abra a URL com `?perf=1` ou grave `localStorage.tarielPerf=1`;
3. fora disso, o runtime fica ausente ou em modo no-op.

## Como ativar no navegador

Opção por query string:

```text
http://127.0.0.1:8000/app/?perf=1
http://127.0.0.1:8000/cliente/painel?perf=1
http://127.0.0.1:8000/revisao/painel?perf=1
http://127.0.0.1:8000/admin/painel?perf=1
```

Opção persistente:

```js
localStorage.setItem("tarielPerf", "1");
location.reload();
```

Para desligar:

```js
localStorage.removeItem("tarielPerf");
location.reload();
```

## O que é coletado pelo runtime

### Métricas automáticas

- navegação e tempo de carregamento;
- `paint` timings;
- LCP;
- CLS;
- recursos de rede via `PerformanceObserver`;
- chamadas `fetch` e `XMLHttpRequest`;
- long tasks;
- duplicação de listeners;
- callbacks de observers;
- escritas em storage.

### Métricas por função

O runtime agrega chamadas marcadas com `measureSync` e `measureAsync`, produzindo:

- `count`
- `totalMs`
- `avgMs`
- `maxMs`
- `minMs`
- `lastMs`
- `failures`

As tabelas mais úteis saem por `topFunctions()`.

### Snapshots leves de DOM

Os snapshots não serializam o HTML inteiro. Eles guardam contagens pequenas e regiões-alvo para responder perguntas como:

- quantos nós existem na tela;
- qual shell estava ativo;
- quantos itens foram renderizados em listas principais;
- em que momento um estado específico do DOM apareceu.

## Cobertura por shell

### Inspetor `/app`

Cobertura principal já existente no frontend do inspetor:

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/chat/chat_painel_mesa.js`
- `web/static/js/chat/chat_painel_relatorio.js`
- `web/static/js/shared/ui.js`
- `web/static/js/shared/api.js`

Essa área já entrega top functions, rede e long tasks sem mudança de contrato.

### Cliente `/cliente/painel`

Funções explicitamente medidas:

- `cliente.api`
- `cliente.definirTab`
- `cliente.renderEverything`
- `cliente.bootstrapPortal`
- `cliente.loadChat`
- `cliente.loadMesa`
- `cliente.init`

Isso permite separar:

- custo de bootstrap do portal;
- custo de trocar de aba;
- custo de render geral;
- custo de fan-out do bootstrap para APIs do cliente.

### Revisor `/revisao/painel`

Funções explicitamente medidas:

- `revisor.inicializarWebSocket`
- `revisor.carregarLaudo`
- `revisor.enviarMensagemEngenheiro`
- `revisor.confirmarDevolucao`
- `revisor.obterPacoteMesaLaudo`
- `revisor.marcarWhispersComoLidosLaudo`
- `revisor.renderizarPainelMesaOperacional`
- `revisor.atualizarPendenciaMesaOperacional`
- `revisor.carregarPainelMesaOperacional`
- `revisor.abrirResumoPacoteMesa`
- `revisor.baixarPacoteMesaJson`
- `revisor.baixarPacoteMesaPdf`
- `revisor.renderTimeline`
- `revisor.carregarHistoricoMensagens`
- `revisor.renderizarPainelAprendizadosVisuais`
- `revisor.validarAprendizadoVisual`

Isso torna visível o custo real do shell mais sensível depois do chat.

### Admin `/admin/painel`

Nesta fase o admin entra com cobertura automática do runtime:

- navegação;
- paint/LCP/CLS;
- recursos;
- fetch/XHR;
- long tasks.

Não foi criada instrumentação manual adicional no admin porque a fase ainda é de baseline, não de expansão de superfície.

## Buffers e segurança operacional

Guardrails já confirmados:

- se o perf não estiver ativo, `window.TarielPerf` vira no-op;
- os arrays em memória são limitados no browser;
- não há envio automático dessas métricas para backend;
- a instrumentação fica restrita ao browser local do operador;
- não há mudança de endpoint nem de payload funcional.

## Consultas principais no console

```js
window.TarielPerf.printSummary()
window.TarielPerf.getReport()
window.TarielPerf.topFunctions()
window.TarielPerf.topNetwork()
window.TarielPerf.topLongTasks()
```

## Hotspots agora observáveis no frontend

- parse e boot da shell do inspetor em `/app`;
- bootstrap do portal cliente em `/cliente/painel`;
- render e troca de abas do portal cliente;
- carga do laudo no shell do revisor;
- timeline/histórico no revisor;
- montagem de pacote e exportações no revisor;
- long tasks ligadas a listas, cards e modais densos;
- requests frontend mais lentos por shell;
- peso real de recursos externos e estáticos no first load.

## O que esta fase não faz

- não troca framework;
- não introduz bundler;
- não move estado de runtime;
- não reescreve controllers grandes;
- não altera markup funcional;
- não muda endpoints, payloads ou contratos;
- não envia RUM para produção.

## Limitações conhecidas

- o frontend ainda depende de inspeção manual via DevTools/console;
- o admin tem cobertura passiva, não uma malha de funções medida como cliente/revisor;
- as medições são por navegador e por sessão local, não agregadas centralmente.
