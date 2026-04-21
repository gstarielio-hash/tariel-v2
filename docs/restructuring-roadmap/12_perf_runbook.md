# Fase 01: Runbook de Medição

## Objetivo

Este runbook descreve como ligar, coletar e interpretar as medições da Fase 01 sem alterar comportamento funcional do produto.

## Pré-requisitos

- ambiente local ou dev;
- autenticação válida para os portais que serão medidos;
- backend iniciado com `PERF_MODE=1` para medir servidor e para injetar o runtime frontend em `/cliente`, `/revisao` e `/admin`;
- navegador com DevTools aberto para coletar o relatório frontend.

## Nota de higiene local

Em `localhost`, o Service Worker do inspetor passou a ser desativado automaticamente para evitar interferência em SSE e cache local antigo.

Consequências práticas:

- não usar Service Worker como referência para medir SSE em localhost;
- se o console parecer contaminado por estado antigo, limpar flags locais e recarregar;
- preferir os helpers do navegador para consultar o backend de perf, em vez de colar `curl` no console.

## Boot recomendado

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web"
PERF_MODE=1 \
PERF_BUFFER_LIMIT=300 \
PERF_SQL_SLOW_MS=80 \
PERF_ROUTE_SLOW_MS=400 \
PERF_EXTERNAL_SLOW_MS=250 \
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Desligar

Backend:

- remover `PERF_MODE`;
- ou usar `PERF_MODE=0`;
- reiniciar o processo.

Frontend:

```js
localStorage.removeItem("tarielPerf");
location.reload();
```

## Sequência mínima de coleta

### 1. Resetar buffers do backend

```bash
curl -s -X POST http://127.0.0.1:8000/debug-perf/reset
```

### 2. Medir o shell do inspetor

Abrir:

```text
http://127.0.0.1:8000/app/?perf=1
```

Executar pelo menos:

- carregar a home do inspetor;
- abrir uma inspeção existente;
- enviar uma mensagem curta;
- repetir o teste com anexo ou imagem quando possível.

### 3. Medir o shell do cliente

Abrir:

```text
http://127.0.0.1:8000/cliente/painel?perf=1
```

Executar pelo menos:

- esperar o bootstrap inicial;
- navegar entre `Admin`, `Chat` e `Mesa Avaliadora`;
- abrir um laudo no Chat;
- abrir um item na Mesa.

### 4. Medir o shell do revisor

Abrir:

```text
http://127.0.0.1:8000/revisao/painel?perf=1
```

Executar pelo menos:

- abrir um laudo;
- carregar histórico;
- abrir pacote;
- exportar PDF do pacote, se houver dados;
- rodar preview/publicação de template, se a sessão tiver acesso.

### 5. Medir o shell administrativo

Abrir:

```text
http://127.0.0.1:8000/admin/painel?perf=1
```

Executar pelo menos:

- first load completo;
- interação com gráficos e filtros visíveis;
- navegação pelas ações mais usadas da página.

## Como consultar o backend

### Sumário leve

```bash
curl -s http://127.0.0.1:8000/debug-perf/summary
```

Se houver `jq`:

```bash
curl -s http://127.0.0.1:8000/debug-perf/summary | jq
```

Leituras mais úteis:

- `top_routes`
- `top_shells`
- `top_queries`
- `top_integrations`
- `top_render_ops`
- `slow_requests`
- `slow_queries`
- `recent_boot`

### Relatório completo

```bash
curl -s http://127.0.0.1:8000/debug-perf/report | jq
```

Use quando precisar dos buffers completos:

- `requests`
- `queries`
- `operations`
- `boot_events`

### Headers por request

```bash
curl -I http://127.0.0.1:8000/app/login
```

Quando o perf estiver ativo, observar:

- `X-Correlation-ID`
- `X-Request-Id`
- `X-Response-Time`
- `Server-Timing`

## Como consultar o frontend

No console do navegador:

```js
window.TarielPerf.printSummary()
window.TarielPerf.getReport()
window.TarielPerf.topFunctions()
window.TarielPerf.topNetwork()
window.TarielPerf.topLongTasks()
await window.TarielPerf.fetchBackendSummary()
await window.TarielPerf.fetchBackendReport()
await window.TarielPerf.resetBackendSummary()
```

Leituras práticas:

- `printSummary()`: visão rápida do shell atual;
- `topFunctions()`: onde o runtime está concentrando custo;
- `topNetwork()`: requests mais lentos vistos pelo browser;
- `topLongTasks()`: travamentos perceptíveis na thread principal;
- `getReport()`: dump completo para análise posterior.

## Limpeza rápida de flags locais

No console do navegador:

```js
localStorage.removeItem("tarielPerf")
localStorage.removeItem("tarielDebug")
sessionStorage.removeItem("tariel_sw_local_reset")
location.reload()
```

## Como separar backend de frontend

### Custo de backend

Usar:

- `Server-Timing`;
- `X-Response-Time`;
- `GET /debug-perf/summary`;
- `GET /debug-perf/report`.

Sinais principais:

- request lento com `sql_total_ms` alto indica peso de banco;
- request lento com `external_total_ms` alto indica IA/OCR/rede externa;
- request HTML lento com `render_total_ms` alto indica shell/SSR caro;
- rota lenta com pouco SQL e pouco external aponta lógica interna ou serialização pesada.

### Custo de frontend

Usar:

- `window.TarielPerf.topFunctions()`;
- `window.TarielPerf.topNetwork()`;
- `window.TarielPerf.topLongTasks()`;
- aba Performance/Network do navegador quando precisar do flame chart.

Sinais principais:

- backend rápido e `topFunctions()` alto indica problema de runtime/render local;
- backend rápido e `topNetwork()` alto em assets indica first load pesado;
- long tasks altas com DOM snapshots densos indicam renderização/layout caro.

## Rotas e operações que devem ser observadas primeiro

### Rotas HTML

- `GET /app/`
- `GET /cliente/painel`
- `GET /revisao/painel`
- `GET /admin/painel`

### Rotas API

- `POST /app/api/chat`
- `GET /cliente/api/bootstrap`
- `GET /revisao/api/laudo/{laudo_id}/completo`
- `GET /revisao/api/laudo/{laudo_id}/pacote`
- `GET /revisao/api/laudo/{laudo_id}/pacote/exportar-pdf`
- `POST /revisao/api/templates-laudo/{template_id}/preview`
- `POST /revisao/api/templates-laudo/editor/{template_id}/preview`

### Operações internas

- `ai.gemini.generate_content_stream.chat`
- `ai.gemini.generate_content.structured`
- `ocr.google_vision.text_detection`
- `template.gerar_preview_pdf_template`
- `pdf.gerar_pdf_html_playwright`

## Top 10 suspeitas agora mensuráveis

1. `POST /app/api/chat` pode estar dominado por IA externa e trabalho serial no backend.
2. `GET /revisao/painel` pode estar caro por montagem de fila, métricas e HTML inicial.
3. `GET /cliente/painel` pode estar diluindo custo entre SSR, bootstrap e fan-out do portal.
4. `GET /cliente/api/bootstrap` pode concentrar payload e acoplamento excessivos do cliente web.
5. `GET /revisao/api/laudo/{laudo_id}/completo` pode concentrar consultas e montagem de contexto demais.
6. `GET /revisao/api/laudo/{laudo_id}/pacote` e `.../exportar-pdf` podem misturar leitura de dados com render documental pesado.
7. `POST /revisao/api/templates-laudo/{template_id}/preview` pode sofrer com geração síncrona de preview.
8. `ai.gemini.generate_content_stream.chat` pode virar o principal componente de latência percebida do chat.
9. `ocr.google_vision.text_detection` pode penalizar mensagens com imagem mais do que o fluxo atual assume.
10. `cliente.renderEverything`, `cliente.bootstrapPortal` e `revisor.carregarLaudo` podem concentrar o custo de runtime no browser.

## Checks mínimos desta fase

Validação recomendada após mudanças de observabilidade:

```bash
python3 -m pytest -q web/tests/test_perf_support.py
python3 -m pytest -q web/tests/test_smoke.py -k 'template_revisor_aponta_websocket_com_prefixo_revisao or templates_cliente_explicitam_abas_e_formularios_principais'
```

## O que esta fase não altera

- regras de negócio;
- contratos e payloads;
- endpoints existentes;
- autorização e autenticação;
- comportamento funcional de backend;
- comportamento funcional de frontend;
- configuração de produção;
- arquitetura dos módulos.

## Regra de encerramento

Esta fase não autoriza refatoração automática dos hotspots. Ela apenas cria baseline observável para decidir a próxima etapa com dados reais.
