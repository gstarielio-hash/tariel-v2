# Fase 10 - Observabilidade, operação e segurança

Fechada em `2026-03-30`.

## Resultado

A `Fase 10` foi promovida com `correlation_id` ponta a ponta, tracing opcional com `OpenTelemetry`, captura opcional de erro/performance com `Sentry`, política explícita de analytics/replay/LGPD e governança versionada de checks obrigatórios.

## O que entrou

- backend com headers canônicos, `traceparent`, logs estruturados com `trace_id/span_id`, scrubbing sensível e spans de operação
- `frontend paralelo da Mesa` com contexto observável por request no BFF, forwarding explícito para o backend legado e respostas com headers canônicos
- Android com a mesma gramática de correlação e `traceparent` em cada request
- leitura administrativa explícita em `GET /admin/api/observability/summary`
- runner oficial `make observability-acceptance`
- política operacional em `docs/developer-experience/07_observability_runtime_and_privacy_policy.md`

## Arquivos centrais

- `web/app/core/settings.py`
- `web/app/core/observability_privacy.py`
- `web/app/core/telemetry_support.py`
- `web/app/core/http_runtime_support.py`
- `web/app/core/http_setup_support.py`
- `web/app/core/logging_support.py`
- `web/app/core/perf_support.py`
- `web/app/domains/admin/observability_summary.py`
- `web/app/domains/admin/routes.py`
- `android/src/config/apiCore.ts`
- `android/src/config/mesaApi.ts`
- `scripts/run_observability_phase_acceptance.py`
- `Makefile`

## Evidência operacional

- artifact oficial: `artifacts/observability_phase_acceptance/20260330_220809/observability_phase_acceptance_summary.json`
- relatório humano do runner: `artifacts/observability_phase_acceptance/20260330_220809/final_report.md`
- status do runner: `ok`

## Validação final

- `make observability-acceptance` verde em `2026-03-30`
- `make contract-check` verde em `2026-03-30`
- `make verify` verde em `2026-03-30`

## Observações

- `OpenTelemetry` e `Sentry` continuam opt-in por ambiente; o runtime já está institucionalizado, mas não é forçado em todos os ambientes por default
- `browser analytics` e `browser replay` permanecem desligados por padrão
- `mobile analytics` continua dependente de opt-in explícito

## Próximo passo

Promover a `Fase 11 - Higiene permanente e governança`, começando por política de `artifacts/`, revisão de `.gitignore` por workspace, limpeza de saídas locais e disciplina explícita de `worktree`/`PLANS.md`
