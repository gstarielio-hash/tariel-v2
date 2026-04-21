# Runtime Hygiene e DX Local do Web

## Objetivo

Esta fase trata apenas de higiene de runtime e experiência de desenvolvimento local. O foco foi:

- impedir que o Service Worker contamine o localhost;
- evitar interferência do Service Worker no SSE de `/app/api/notificacoes/sse`;
- reduzir warnings falsos positivos;
- deduplicar logs repetitivos;
- deixar mais claro o que deve ser executado no terminal e o que deve ser executado no console do navegador.

Não houve mudança de regra de negócio, endpoint funcional, contrato, payload ou fluxo principal do produto.

## Causa principal do problema entre Service Worker e SSE

Confirmado no código:

- o Service Worker real do inspetor está em `web/static/js/shared/trabalhador_servico.js`;
- o registro do worker é feito por `web/static/js/shared/app_shell.js`;
- o SSE do inspetor usa `EventSource` em `web/static/js/inspetor/notifications_sse.js`;
- a rota crítica é `/app/api/notificacoes/sse`.

Antes desta fase:

- o localhost podia continuar controlado por um Service Worker antigo;
- o worker ainda entrava no ciclo de `fetch` para requests com `Accept: text/event-stream`;
- quando o fetch interno falhava, o navegador reportava erro como falha do Service Worker na requisição SSE;
- isso contaminava o fluxo local com reconexões barulhentas e erro visual no console.

## O que foi feito

### 1. Service Worker desativado automaticamente em localhost

Aplicado em `web/static/js/shared/app_shell.js`.

Comportamento novo:

- em `localhost` e `127.0.0.1`, o shell não registra mais o Service Worker do `/app`;
- se existir um registro antigo do worker, ele é desregistrado automaticamente;
- caches `tariel-*` do worker são limpos;
- se a página ainda estiver controlada por um worker antigo, o shell força um único reload local para liberar o controller e sair do estado contaminado.

Objetivo:

- ambiente local limpo;
- sem cache antigo do worker afetando boot;
- sem SSE passando por worker local legado.

### 2. Bypass explícito de SSE no Service Worker

Aplicado em `web/static/js/shared/trabalhador_servico.js`.

Comportamento novo:

- requests com `Accept: text/event-stream` não recebem mais `respondWith`;
- `/app/api/notificacoes/sse` passa direto para a rede;
- o Service Worker deixa de participar do caminho do EventSource.

Objetivo:

- o worker nunca mais ser a causa direta de falha do SSE;
- manter notificações normais sem cache e sem interceptação indevida.

### 3. Warnings opcionais rebaixados

Aplicado em:

- `web/static/js/chat/chat_sidebar.js`
- `web/static/js/shared/hardware.js`
- `web/static/js/chat/chat_painel_core.js`

Mudanças:

- ausência do botão `Falar com Engenheiro` passou a ser tratada como ausência opcional, não como warning alto;
- ausência de DOM opcional de anexo em páginas/contextos parciais virou log discreto;
- mensagens esperadas de bootstrap incompleto, como `TarielAPI ainda não disponível` e `TarielChatRender ainda não está disponível`, foram rebaixadas para debug único.

### 4. Divergência de estado tratada como transitória antes de virar warning

Aplicado em `web/static/js/chat/chat_index_page.js`.

Comportamento novo:

- divergência entre fontes de `estadoRelatorio` e `laudoAtualId` não dispara warning agressivo na primeira reconciliação;
- primeiro a divergência é tratada como transitória;
- só vira warning quando persiste por múltiplas reconciliações ou tempo suficiente para parecer anomalia real;
- o warning é emitido no máximo uma vez por assinatura persistente.

Objetivo:

- não confundir boot normal com bug real;
- manter sinal útil quando a divergência realmente persiste.

### 5. Logs repetitivos agora ficam em debug ou uma vez só

Aplicado em:

- `web/static/js/shared/api-core.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_relatorio.js`

Mudanças:

- `TarielCore` agora expõe `DEBUG_ATIVO`, `debug()` e `logOnce()`;
- logs de `info`, `log` e `debug` deixam de poluir o console por padrão em dev;
- aliases legados de evento passaram de warning para debug deduplicado;
- sincronização repetitiva de estado do relatório foi movida para debug.

## Helpers úteis no console do navegador

Quando o backend estiver com `PERF_MODE=1`, o frontend agora pode consultar o backend direto do console:

```js
await window.TarielPerf.fetchBackendSummary()
await window.TarielPerf.fetchBackendReport()
await window.TarielPerf.resetBackendSummary()
```

Esses helpers evitam confusão entre:

- comandos de terminal, como `curl`;
- comandos do console do navegador, como `window.TarielPerf.*`.

## O que vai no terminal

Exemplos:

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web"
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

```bash
curl -s http://127.0.0.1:8000/debug-perf/summary | jq
```

## O que vai no console do navegador

Exemplos:

```js
window.TarielPerf.printSummary()
window.TarielPerf.topFunctions()
await window.TarielPerf.fetchBackendSummary()
localStorage.removeItem("tarielPerf")
localStorage.removeItem("tarielDebug")
sessionStorage.removeItem("tariel_sw_local_reset")
location.reload()
```

## Como limpar o ambiente local manualmente

### Limpar flags de debug/perf

No console do navegador:

```js
localStorage.removeItem("tarielPerf")
localStorage.removeItem("tarielDebug")
sessionStorage.removeItem("tariel_sw_local_reset")
location.reload()
```

### Desregistrar o Service Worker manualmente

No console do navegador:

```js
const regs = await navigator.serviceWorker.getRegistrations()
await Promise.all(regs.map((reg) => reg.unregister()))
const keys = await caches.keys()
await Promise.all(keys.filter((key) => key.startsWith("tariel-")).map((key) => caches.delete(key)))
location.reload()
```

## Como validar SSE em localhost

1. Subir o web local.
2. Abrir `/app`.
3. No console do navegador, confirmar:

```js
navigator.serviceWorker.controller
```

Resultado esperado em localhost:

- `null` ou equivalente sem controller ativo do `/app`.

4. Na aba Network, filtrar por `notificacoes/sse`.

Resultado esperado:

- request viva de `EventSource`;
- sem erro atribuído ao Service Worker;
- sem mensagem de interceptação do worker no console.

## O que permanece intencionalmente sem mudança

- regras de negócio;
- contratos;
- endpoints funcionais;
- auth/session/multiportal;
- backend de negócio;
- fluxo funcional do inspetor;
- SSE de produção como mecanismo funcional.

## Arquivos críticos desta fase

- `web/static/js/shared/app_shell.js`
- `web/static/js/shared/trabalhador_servico.js`
- `web/static/js/inspetor/notifications_sse.js`
- `web/static/js/shared/api-core.js`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_sidebar.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_relatorio.js`
- `web/static/js/shared/hardware.js`
