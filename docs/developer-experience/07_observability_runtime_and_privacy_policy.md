# Runtime de Observabilidade e Política de Privacidade

## Objetivo

Congelar a gramática operacional de observabilidade do Tariel sem depender de convenção informal entre backend, reviewdesk SSR, mobile e operação.

## Headers canônicos

As superfícies críticas passaram a compartilhar estes headers:

- `X-Correlation-ID`
  Identificador transversal do fluxo.
- `X-Request-Id`
  Identificador do request atual na superfície que recebeu a chamada.
- `X-Client-Request-Id`
  Identificador do caller anterior quando a chamada veio de outra superfície cliente.
- `X-Trace-Id`
  `trace_id` atual exposto na resposta.
- `traceparent`
  contexto W3C para continuação de trace.

Compatibilidade mantida:

- `X-Mesa-Trace-Id`
- `X-Mesa-Client-Trace-Id`

## Runtime por superfície

### Backend web

- `MiddlewareCorrelationID` agora aceita, propaga e expõe `correlation_id`, `request_id`, `client_request_id`, `trace_id` e `traceparent`.
- logs estruturados carregam `correlation_id`, `trace_id` e `span_id`.
- `perf_support` abre spans internos para operações medidas sem vazar payload sensível.
- exceções globais podem ser capturadas opcionalmente pelo `Sentry`.

### Reviewdesk SSR

- o backend web centraliza o contexto observável da Mesa no mesmo runtime do portal;
- chamadas do browser para rotas SSR e APIs da revisão carregam os headers canônicos;
- as respostas mantêm `correlation_id`, `request_id`, `trace_id` e `traceparent` consistentes;
- compatibilidades legadas de header continuam aceitas sem criar uma segunda superfície web.

### Android

- `apiCore.ts` injeta `X-Correlation-ID`, `X-Request-Id`, `X-Client-Request-Id`, `X-Mesa-Client-Trace-Id` e `traceparent` em cada request;
- `mesaApi.ts` preserva `client_message_id` como seed explícita nas mutações da Mesa;
- a observabilidade local do app continua subordinada ao opt-in do usuário.

## Chaves de ambiente

- `OTEL_ENABLED`
- `OTEL_SERVICE_NAME`
- `OTEL_SERVICE_NAMESPACE`
- `OTEL_EXPORTER_MODE`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_EXPORT_TIMEOUT_MS`
- `SENTRY_DSN`
- `SENTRY_TRACES_SAMPLE_RATE`
- `SENTRY_PROFILES_SAMPLE_RATE`
- `SENTRY_SEND_DEFAULT_PII`
- `TARIEL_BROWSER_ANALYTICS_ENABLED`
- `TARIEL_BROWSER_REPLAY_ENABLED`
- `TARIEL_MOBILE_ANALYTICS_OPT_IN_REQUIRED`
- `OBSERVABILITY_LOG_RETENTION_DAYS`
- `OBSERVABILITY_PERF_RETENTION_DAYS`
- `OBSERVABILITY_ARTIFACT_RETENTION_DAYS`

Defaults operacionais atuais:

- `OTEL_ENABLED=0`
- `OTEL_EXPORTER_MODE=console` fora de produção e `none` em produção
- `Sentry` desligado enquanto `SENTRY_DSN` estiver vazio
- `browser analytics` desligado por padrão
- `browser replay` desligado por padrão
- `mobile analytics` exige opt-in explícito

## Política de privacidade e LGPD

- observabilidade fica em `metadata_minimizada`;
- emails, `Authorization`, `Cookie`, `Set-Cookie`, `CSRF`, `token`, `password`, `secret` e textos equivalentes são mascarados;
- `browser replay` não é habilitado por padrão;
- logs, buffers de `perf` e artifacts usam retenção operacional explícita por dias;
- payload sensível não deve ser usado como campo livre de log.

## Entry points oficiais

- `GET /admin/api/observability/summary`
- `make observability-acceptance`
- `make contract-check`
- `make verify`
