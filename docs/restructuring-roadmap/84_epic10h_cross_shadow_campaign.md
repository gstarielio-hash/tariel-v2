# Epic 10H - campanha operacional cruzada de `shadow` para `report_finalize_stream`

## Objetivo

Executar uma campanha operacional cruzada do slice:

- `POST /app/api/chat`
- branch `eh_comando_finalizar`
- `operation_kind=report_finalize_stream`

com dois harnesses diferentes, mantendo `shadow_only`, `did_block=false` e `enforce_enabled=false`.

## Pre-checagem executada

- `pwd`:
  - `/home/gabriel/Area de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - o worktree continua amplo e sujo fora deste slice; a fase 10H ficou restrita ao runner complementar, artifacts e docs/journal
- boot/import check:
  - `AMBIENTE=dev PYTHONPATH=web python3 -c "import main; main.create_app(); print('boot_import_ok')"`
  - registrado em:
    - `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/boot_import_check.txt`
- flags confirmadas para o recorte:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=report_finalize_stream`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE=1`
- tenant/host controlados:
  - tenant:
    - `1`
    - `Empresa A`
  - hosts/harnesses:
    - runner principal direto
    - `testclient`

## Harnesses usados

- `main_runner_direto_rota_chat`
  - caminho do 10G reaproveitado
  - chama `rota_chat` diretamente com `Request` sintetico
- `testclient_http_harness`
  - `scripts/run_document_hard_gate_10h_http_harness.py`
  - faz login real em `/app/login`
  - executa `POST /app/api/chat`
  - preserva contrato publico e SSE via `TestClient`

## Descoberta conservadora dos casos

Casos reais e seguros exercitados:

- `template_gap`
- `template_ok`

Casos procurados e mantidos como `nao_observado`:

- `materialization_disallowed_by_policy`
- `no_active_report`

Motivo auditado no codigo atual:

- `report_finalize_stream` exige laudo ativo para entrar no branch observado
- `web/app/v2/acl/technical_case_core.py` deriva `has_active_report` a partir de `legacy_laudo_id`
- `web/app/v2/policy/engine.py` deriva `document_materialization_allowed = bool(case_snapshot.has_active_report)`

Conclusao:

- nao existe hoje, neste mesmo slice, caminho seguro e sem invencao para observar esses dois blockers
- por isso ambos permaneceram honestamente `nao_observado`

## Campanha executada

Diretorio da campanha:

- `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/`

Foram executadas 4 rodadas uteis novas:

- `main_runner_gap_round_1`
  - harness:
    - `main_runner_direto_rota_chat`
  - resultado:
    - `HTTP 200`
    - `text/event-stream`
    - `would_block=true`
    - `did_block=false`
    - blockers:
      - `template_not_bound`
      - `template_source_unknown`
- `main_runner_ok_round_1`
  - harness:
    - `main_runner_direto_rota_chat`
  - resultado:
    - `HTTP 200`
    - `text/event-stream`
    - `would_block=false`
    - `did_block=false`
    - blockers:
      - nenhum
- `http_harness_gap_round_1`
  - harness:
    - `testclient_http_harness`
  - resultado:
    - `HTTP 200`
    - `text/event-stream`
    - `would_block=true`
    - `did_block=false`
    - blockers:
      - `template_not_bound`
      - `template_source_unknown`
- `http_harness_ok_round_1`
  - harness:
    - `testclient_http_harness`
  - resultado:
    - `HTTP 200`
    - `text/event-stream`
    - `would_block=false`
    - `did_block=false`
    - blockers:
      - nenhum

## Agregacao da campanha

Resumo agregado em `campaign_summary.json`:

- execucoes uteis novas:
  - `4`
- evaluations novas:
  - `4`
- execucoes por harness:
  - `main_runner_direto_rota_chat`:
    - `2`
  - `testclient_http_harness`:
    - `2`
- tipos de caso distintos:
  - `2`
  - `template_gap`
  - `template_ok`
- `HTTP 200`:
  - `4`
- SSE preservado:
  - `4`
- `would_block=true`:
  - `2`
- `would_block=false`:
  - `2`
- `did_block=true`:
  - `0`
- `shadow_without_bleed_count`:
  - `4`

Blockers observados:

- `template_not_bound`:
  - `2`
- `template_source_unknown`:
  - `2`

Blockers ainda nao observados:

- `materialization_disallowed_by_policy`
- `no_active_report`

## O que a campanha cruzada provou

- o slice permaneceu `shadow_only` em dois caminhos operacionais diferentes
- o harness HTTP/TestClient confirmou que o contrato publico de `/app/api/chat` segue funcional:
  - login real
  - `POST /app/api/chat`
  - `HTTP 200`
  - `text/event-stream`
- os dois harnesses convergiram no mesmo padrao semantico:
  - `template_gap` => `would_block=true` com `template_not_bound` e `template_source_unknown`
  - `template_ok` => sem blockers
- todas as quatro execucoes mantiveram:
  - `did_block=false`
  - `enforce_enabled=false`
  - tenant local/controlado
  - sem bleed para tenant real

## Observabilidade disponivel

Artifacts principais:

- `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/campaign_summary.json`
- `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/campaign_cases.json`
- `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/campaign_findings.md`
- `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/harness_matrix.json`
- `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/source_cases_index.txt`
- `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/responses/admin_summary_response.json`
- `artifacts/document_hard_gate_shadow_campaign_10h/20260327_214808/durable_evidence/`

Cada rodada individual preserva:

- `runtime_summary.json`
- `durable_summary.json`
- `validation_cases.json`
- `responses/*.sse`
- `durable_evidence/`

## Como repetir

- runner principal:
  - `python3 scripts/run_document_hard_gate_10g_validation.py --case gap --output-dir <dir>`
  - `python3 scripts/run_document_hard_gate_10g_validation.py --case template_ok --output-dir <dir>`
- segundo harness:
  - `python3 scripts/run_document_hard_gate_10h_http_harness.py --case gap --output-dir <dir>`
  - `python3 scripts/run_document_hard_gate_10h_http_harness.py --case template_ok --output-dir <dir>`
- depois consolidar os runs em um root de campanha com:
  - `campaign_summary.json`
  - `campaign_cases.json`
  - `campaign_findings.md`
  - `harness_matrix.json`
  - `source_cases_index.txt`

## Validacoes rodadas

- `python3 -m py_compile scripts/run_document_hard_gate_10g_validation.py scripts/run_document_hard_gate_10h_http_harness.py web/app/domains/chat/report_finalize_stream_shadow.py web/app/v2/document/hard_gate_evidence.py`
  - `ok`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10g.py`
  - `2 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10f.py`
  - `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`
  - `26 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -c "import main; main.create_app(); print('boot_import_ok')"`
  - `boot_import_ok`

## O que ainda falta antes de qualquer novo debate sobre `enforce`

- os blockers `materialization_disallowed_by_policy` e `no_active_report` continuam `nao_observado` neste slice
- a evidencia segue local/controlada
- a proxima conversa deve ser um novo gate review, nao um rollout de `enforce`

## Proximo passo recomendado

Novo gate review formal do `report_finalize_stream` com base em:

- validacao 10G
- campanha ampliada 10G
- campanha cruzada 10H

sem assumir `enforce` automaticamente.
