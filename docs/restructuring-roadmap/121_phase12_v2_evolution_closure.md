# Fase 12 - Evolucao estrutural V2

Fechada em `2026-03-31`.

## Resultado

A `Fase 12` foi promovida com a espinha estrutural do `V2` materializada no sistema vivo, sem troca forçada dos payloads publicos legados e com aceite oficial proprio da fase.

## O que entrou

- base de envelopes canônicos em `web/app/v2/contracts/envelopes.py`
- ACL rica do `Technical Case Core` em `web/app/v2/acl/technical_case_core.py` e `web/app/v2/acl/technical_case_snapshot.py`
- projeção canônica do Inspetor em `web/app/v2/contracts/projections.py` e `web/app/v2/contracts/inspector_document.py`
- projeção canônica da Mesa em `web/app/v2/contracts/review_queue.py`
- provenance mínima em `web/app/v2/contracts/provenance.py` e `web/app/v2/provenance.py`
- `policy engine` mínimo em `web/app/v2/policy/engine.py`
- facade documental em `web/app/v2/document/facade.py`, com integração e gates próprios
- adapter Android canônico em `web/app/v2/adapters/android_case_feed.py` e `web/app/v2/adapters/android_case_thread.py`
- metering administrativo explícito sem leitura técnica bruta em `web/app/v2/billing/metering.py`
- runner oficial da fase em `scripts/run_v2_phase_acceptance.py` e entrypoint `make v2-acceptance`

## Arquivos centrais

- `Makefile`
- `scripts/run_v2_phase_acceptance.py`
- `web/app/v2/contracts/envelopes.py`
- `web/app/v2/acl/technical_case_snapshot.py`
- `web/app/v2/contracts/projections.py`
- `web/app/v2/contracts/review_queue.py`
- `web/app/v2/contracts/inspector_document.py`
- `web/app/v2/contracts/provenance.py`
- `web/app/v2/policy/engine.py`
- `web/app/v2/document/facade.py`
- `web/app/v2/adapters/android_case_feed.py`
- `web/app/v2/adapters/android_case_thread.py`
- `web/app/v2/billing/metering.py`

## Evidencia operacional

- artifact oficial: `artifacts/v2_phase_acceptance/20260331_071151/v2_phase_acceptance_summary.json`
- relatorio humano do runner: `artifacts/v2_phase_acceptance/20260331_071151/final_report.md`
- status do runner: `ok`

## Validacao final

- `make v2-acceptance` verde em `2026-03-31`
- `make contract-check` verde em `2026-03-31`
- `make verify` verde em `2026-03-31`

## Observacoes

- a fase foi fechada sem promover reescrita big bang; os slices estruturais continuam em `shadow mode`, `feature flag` ou rollback explicito onde a superficie publica ainda nao consome o contrato V2 diretamente
- o pacote administrativo agora depende de um adapter explicito de `billing/metering`, reduzindo o acoplamento de consumo/plano dentro das projecoes
- futuras frentes deixam de ser “Fase 13” dentro deste plano mestre; passam a ser evolucao pos-plano sobre a base estrutural ja consolidada

## Proximo passo

Encerrar o plano mestre atual e abrir novas frentes apenas como evolucao pos-plano, mantendo `make verify`, `make contract-check` e `make v2-acceptance` como gates canonicos.
