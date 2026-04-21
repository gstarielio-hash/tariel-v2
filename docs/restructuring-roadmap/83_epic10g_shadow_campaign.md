# Epic 10G+ - campanha operacional ampliada de `shadow` para `report_finalize_stream` com trilha duravel

## Objetivo

Executar uma campanha operacional ampliada do slice:

- `POST /app/api/chat`
- branch `eh_comando_finalizar`
- `operation_kind=report_finalize_stream`

usando o isolamento estrutural e a trilha duravel entregues no 10G, sem abrir `enforce` e sem alterar comportamento funcional.

## Pre-checagem executada

- `pwd`:
  - `/home/gabriel/Area de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - o worktree continua muito amplo e sujo fora do slice documental; esta fase ficou restrita a artifacts da campanha e a docs/journal
- boot/import check:
  - `AMBIENTE=dev PYTHONPATH=web python3 -c "import main; main.create_app(); print('boot_import_ok')"`
  - registrado em:
    - `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/boot_import_check.txt`
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
  - host:
    - `testclient`
- runner confirmado:
  - `scripts/run_document_hard_gate_10g_validation.py`
  - executado com sucesso nas quatro rodadas desta campanha

## Descoberta conservadora dos casos

Casos reais e seguros observaveis neste slice:

- `template_gap`
  - recorte com `template_not_bound` e `template_source_unknown`
- `template_ok`
  - recorte com template compativel ativo e sem blockers de template

Casos procurados mas mantidos como `nao_observado`:

- `materialization_disallowed_by_policy`
- `no_active_report`

Motivo auditado no codigo atual:

- `report_finalize_stream` pressupoe laudo ativo
- `web/app/v2/acl/technical_case_core.py` deriva `has_active_report` a partir de `legacy_laudo_id`
- `web/app/v2/policy/engine.py` deriva `document_materialization_allowed = bool(case_snapshot.has_active_report)`

Conclusao:

- nao existe hoje, neste mesmo slice, caminho seguro e sem invencao para observar esses dois blockers
- por isso ambos permaneceram honestamente `nao_observado`

## Campanha executada

Diretorio da campanha:

- `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/`

Foram executadas 4 rodadas uteis novas, todas locais/controladas, cada uma com evidence duravel propria:

- `shadow_stream_gap_padrao_round_1`
  - artifacts em:
    - `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/runs/shadow_stream_gap_padrao_round_1/`
  - resultado:
    - `HTTP 200`
    - `text/event-stream`
    - `would_block=true`
    - `did_block=false`
    - blockers:
      - `template_not_bound`
      - `template_source_unknown`
- `shadow_stream_ok_padrao_round_1`
  - artifacts em:
    - `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/runs/shadow_stream_ok_padrao_round_1/`
  - resultado:
    - `HTTP 200`
    - `text/event-stream`
    - `would_block=false`
    - `did_block=false`
    - blockers:
      - nenhum
- `shadow_stream_gap_padrao_round_2`
  - artifacts em:
    - `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/runs/shadow_stream_gap_padrao_round_2/`
  - resultado:
    - `HTTP 200`
    - `text/event-stream`
    - `would_block=true`
    - `did_block=false`
    - blockers:
      - `template_not_bound`
      - `template_source_unknown`
- `shadow_stream_ok_padrao_round_2`
  - artifacts em:
    - `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/runs/shadow_stream_ok_padrao_round_2/`
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

## O que a campanha provou

- o slice continua funcional em `shadow_only` mesmo em campanha ampliada:
  - `HTTP 200`
  - `text/event-stream`
  - `did_block=false`
  - `enforce_enabled=false`
- `template_not_bound` e `template_source_unknown` continuam repetindo de forma estavel nos casos `template_gap`
- os casos `template_ok` continuam limpos, sem regressao funcional e sem blockers de template
- a trilha duravel do 10G funcionou em todas as 4 rodadas:
  - artifact individual por execucao
  - journal `index.jsonl`
  - durable summary agregado
  - response admin/local-only salvo na campanha

## Observabilidade disponivel

Artifacts principais:

- `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/campaign_summary.json`
- `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/campaign_cases.json`
- `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/campaign_findings.md`
- `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/source_cases_index.txt`
- `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/responses/admin_summary_response.json`
- `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/responses/durable_summary_response.json`
- `artifacts/document_hard_gate_shadow_campaign_10g/20260327_212348/durable_evidence/`

Cada rodada individual tambem preserva:

- `runtime_summary.json`
- `durable_summary.json`
- `validation_cases.json`
- `responses/*.sse`
- `durable_evidence/`

## Validacoes rodadas

- `python3 -m py_compile web/app/domains/chat/report_finalize_stream_shadow.py web/app/v2/document/hard_gate_evidence.py scripts/run_document_hard_gate_10g_validation.py`
  - `ok`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10g.py`
  - `2 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10f.py`
  - `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`
  - `26 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -c "import main; main.create_app(); print('boot_import_ok')"`
  - `boot_import_ok`

## Leitura final da amostra

- a amostra melhorou materialmente
- a campanha adicionou 4 execucoes uteis novas e dois tipos de caso reais/seguros
- isso ja e suficiente para abrir um novo gate review do `report_finalize_stream`
- isso ainda nao prova base para `enforce`, porque:
  - `materialization_disallowed_by_policy` e `no_active_report` seguem `nao_observado`
  - toda a evidencia continua local/controlada

## Proximo passo recomendado

Novo gate review formal do `report_finalize_stream` com base em:

- campanha 10F
- validacao 10G
- campanha ampliada 10G

sem assumir `enforce` automaticamente.
