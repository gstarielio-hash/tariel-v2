# Fase 01: Observabilidade de Backend

## Objetivo

Esta fase adiciona observabilidade dev-only ao backend para medir custo real de request, SQL, integrações externas, SSR aproximado, geração documental e boot do web antes de qualquer refatoração estrutural.

## Confirmado no código desta fase

- `web/app/core/perf_support.py` centraliza buffers em memória, contextos de request, medição de SQL, medição de operações, sumários e endpoints de debug.
- `web/app/core/http_runtime_support.py` injeta `X-Request-Id`, `X-Correlation-ID`, `X-Response-Time` e `Server-Timing` quando `PERF_MODE` está ativo.
- `web/app/core/http_setup_support.py` registra `GET /debug-perf/summary`, `GET /debug-perf/report` e `POST /debug-perf/reset` fora de produção.
- `web/main.py` registra a instrumentação SQL no `motor_banco` e mede o boot em `startup.inicializar_banco`, `startup.db_ping` e `startup.revisor_realtime`.
- `web/app/domains/chat/chat_stream_routes.py` preserva o contexto de observabilidade no executor do chat usando `copy_context()`.
- `web/nucleo/cliente_ia.py` mede OCR e chamadas Gemini como operações de categoria `ocr` e `ai`.
- `web/nucleo/template_laudos.py` mede preview e gravação de PDF/template como categoria `template`.
- `web/nucleo/template_editor_word.py` mede geração de PDF via Playwright e operações do editor/template como categorias `pdf` e `template`.

## Como ativar

A observabilidade de backend só liga fora de produção.

Variáveis disponíveis:

- `PERF_MODE=1`: liga a coleta de backend.
- `PERF_BUFFER_LIMIT=300`: tamanho base dos buffers em memória.
- `PERF_SQL_SLOW_MS=80`: limiar de slow query.
- `PERF_ROUTE_SLOW_MS=400`: limiar de rota lenta.
- `PERF_EXTERNAL_SLOW_MS=250`: limiar de integração/operação externa lenta.

Exemplo de boot local:

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/web"
PERF_MODE=1 \
PERF_BUFFER_LIMIT=300 \
PERF_SQL_SLOW_MS=80 \
PERF_ROUTE_SLOW_MS=400 \
PERF_EXTERNAL_SLOW_MS=250 \
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Para desligar:

- remover `PERF_MODE`;
- ou definir `PERF_MODE=0`;
- reiniciar o processo web.

## O que é medido por request

| Métrica | Origem | Leitura |
| --- | --- | --- |
| `request_id` | `MiddlewareCorrelationID` | Hoje usa o mesmo valor de `X-Correlation-ID`. |
| `method`, `path`, `route_group`, `status_code` | `perf_support.py` | Agrupa `/app`, `/cliente`, `/revisao`, `/admin` em HTML e API. |
| `duration_ms` | middleware | Custo total do request no backend. |
| `is_html`, `is_stream` | middleware | Separa SSR/shell HTML de SSE/stream. |
| `sql_count`, `sql_total_ms` | eventos SQLAlchemy | Quantidade e custo acumulado de queries no request. |
| `slow_sql_count`, `slow_sql_ms` | eventos SQLAlchemy | Slow queries segundo `PERF_SQL_SLOW_MS`. |
| `external_count`, `external_total_ms` | `registrar_operacao()` | Integrações externas, IA e OCR. |
| `render_count`, `render_total_ms` | `registrar_operacao()` + fallback HTML | Preview/export/template/render. |
| `sql_samples`, `operation_samples` | buffers do request | Amostras úteis para inspeção rápida. |

## Grupos de rota observáveis

Os requests entram em grupos padronizados:

- `app_api`
- `cliente_api`
- `revisao_api`
- `admin_api`
- `app_html`
- `cliente_html`
- `revisao_html`
- `admin_html`
- `infra`

Isso permite comparar custo de shell HTML contra custo de API sem misturar tudo no mesmo bucket.

## SQL, integrações e render

### SQL

- A instrumentação é registrada no `motor_banco` com eventos do SQLAlchemy.
- Cada statement é normalizado e truncado antes de ir para o buffer.
- O sumário expõe `top_queries`, `slow_queries` e contagem por request.

### Integrações externas

Operações com maior valor nesta fase:

- `ocr.google_vision.text_detection`
- `ai.gemini.generate_content.structured`
- `ai.gemini.generate_content_stream.chat`

Elas aparecem em `top_integrations` e também contribuem para `external_total_ms` do request.

### Render, template e PDF

Operações medidas nesta fase:

- `template.salvar_pdf_template_base`
- `template.gerar_preview_pdf_template`
- `pdf.gerar_pdf_html_playwright`
- `template.gerar_pdf_editor_rico_bytes`
- `pdf.gerar_pdf_base_placeholder_editor`
- `template.salvar_asset_editor_template`

Elas aparecem em `top_render_ops`.

### SSR

Para respostas HTML, o backend calcula `render_total_ms` de duas formas:

- usa soma explícita de operações de categoria `render`, `template`, `pdf` ou `ssr`, quando existirem;
- usa o tempo total do request como aproximação de SSR quando a resposta é HTML e não há marcação mais específica.

## Headers expostos quando ativo

- `X-Correlation-ID`
- `X-Request-Id`
- `X-Response-Time`
- `Server-Timing`

Formato real do `Server-Timing`:

- `app;dur=...`
- `sql;dur=...;desc="queries=N"`
- `ext;dur=...;desc="calls=N"`
- `ssr;dur=...` para HTML

## Endpoints dev-only

Disponíveis apenas fora de produção:

- `GET /debug-perf/summary`
- `GET /debug-perf/report`
- `POST /debug-perf/reset`

Leituras:

- `summary`: top rotas, top shells, top queries, top integrações, top render ops, slow requests, slow queries e boot recente.
- `report`: mesmo conteúdo do sumário mais buffers completos de `requests`, `queries`, `operations` e `boot_events`.
- `reset`: limpa buffers em memória.

Observação: `/debug-perf/*` e `/static/*` não entram na contagem de requests observados para evitar poluição do relatório.

## Hotspots agora observáveis no backend

- `POST /app/api/chat`
- `GET /revisao/painel`
- `GET /cliente/painel`
- `GET /admin/painel`
- `GET /revisao/api/laudo/{laudo_id}/completo`
- `GET /revisao/api/laudo/{laudo_id}/pacote`
- `GET /revisao/api/laudo/{laudo_id}/pacote/exportar-pdf`
- `POST /revisao/api/templates-laudo/{template_id}/preview`
- `POST /revisao/api/templates-laudo/editor/{template_id}/preview`
- operações IA/OCR e PDF/template listadas acima

## O que esta fase não faz

- não muda regra de negócio;
- não muda contratos;
- não muda endpoints;
- não altera autorização, sessão ou multiportal;
- não adiciona fila, cache, retry ou circuit breaker;
- não persiste métricas em banco, Redis ou serviço externo;
- não roda em produção.

## Limitações conhecidas

- os buffers são locais ao processo; não há agregação distribuída;
- `X-Request-Id` e `X-Correlation-ID` hoje são o mesmo identificador;
- o relatório é intencionalmente leve e não substitui tracing distribuído;
- a aproximação de SSR por request HTML mede custo total do backend, não custo fino de template engine por bloco.
