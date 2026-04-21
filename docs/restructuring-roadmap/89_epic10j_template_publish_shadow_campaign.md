# Epic 10J - campanha operacional ampliada de `template_publish_activate` em `shadow_only`

## Objetivo

Executar uma campanha operacional real, local e controlada para ampliar a amostra de `template_publish_activate` sem abrir `enforce`, sem tocar em tenant real e sem alterar payloads públicos, UX, Android ou contratos do produto.

## Escopo desta fase

- rotas exercitadas:
  - `POST /revisao/api/templates-laudo/{template_id}/publicar`
  - `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- `operation_kind`:
  - `template_publish_activate`
- modo:
  - `shadow_only`
- tenant:
  - `1`
- host:
  - `testclient`

## Pré-checagem executada

- `pwd`:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - registrado em `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/git_status_short.txt`
- boot/import:
  - `AMBIENTE=dev PYTHONPATH=web python3 -c "import main; main.create_app(); print('boot_import_ok')"` -> `boot_import_ok`
- `shadow_only_operations` confirmadas:
  - `['report_finalize_stream', 'review_reject', 'template_publish_activate']`
- operação allowlisted:
  - `template_publish_activate`
- tenant local/controlado confirmado:
  - `tenant=1 host=testclient`
- runner existente do `10I` confirmado e executado:
  - `scripts/run_document_hard_gate_10i_validation.py`

## Casos reais e seguros encontrados

- `legacy_gap`
  - rota legado
  - sem template ativo anterior do mesmo código
  - blockers observados:
    - `template_not_bound`
    - `template_source_unknown`
- `legacy_ok`
  - rota legado
  - já havia template ativo anterior do mesmo código
  - sem blockers observados
- `editor_gap`
  - rota editor
  - sem template ativo anterior do mesmo código
  - blockers observados:
    - `template_not_bound`
    - `template_source_unknown`
- `editor_ok`
  - rota editor
  - já havia template ativo anterior do mesmo código
  - sem blockers observados

Casos adicionais de família própria de governança de template:

- `nao_observado`

## Harnesses usados

### 1. Harness principal

- nome:
  - `direct_route_call`
- runner:
  - [run_document_hard_gate_10i_validation.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/scripts/run_document_hard_gate_10i_validation.py)
- estratégia:
  - chamada direta da implementação das rotas já usada no `10I`
- execuções úteis:
  - `2`

### 2. Harness complementar

- nome:
  - `testclient_http_harness`
- runner:
  - [run_document_hard_gate_10j_http_harness.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/scripts/run_document_hard_gate_10j_http_harness.py)
- estratégia:
  - `TestClient` com login real do revisor e chamadas HTTP nas duas rotas públicas
- execuções úteis:
  - `4`

## Execução da campanha

- orquestrador:
  - [run_document_hard_gate_10j_shadow_campaign.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/scripts/run_document_hard_gate_10j_shadow_campaign.py)
- artifact root:
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/`
- total de execuções úteis:
  - `6`
- execuções por harness:
  - `direct_route_call`: `2`
  - `testclient_http_harness`: `4`
- templates distintos exercitados:
  - `6`
- perfis de caso distintos:
  - `4`

## Resultado agregado

- `HTTP 200`:
  - `6`
- publicação funcional preservada:
  - `6`
- `audit_generated=true`:
  - `6`
- `would_block=true`:
  - `3`
- `would_block=false`:
  - `3`
- `did_block=true`:
  - `0`
- `did_block=false`:
  - `6`
- shadow sem bleed:
  - `6`

## Blockers observados

- `template_not_bound`: `3`
- `template_source_unknown`: `3`

## Blockers ainda não observados

- família própria adicional de blockers de governança de template:
  - `nao_observado`

## Observabilidade preservada

Os artifacts desta campanha mantêm consulta local para:

- summary agregado:
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/campaign_summary.json`
- casos agregados:
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/campaign_cases.json`
- findings:
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/campaign_findings.md`
- matriz de harness:
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/harness_matrix.json`
- runtime summary local por harness:
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/summaries/direct_route_call/runtime_summary.json`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/summaries/testclient_http_harness/runtime_summary.json`
- durable summary local por harness:
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/summaries/direct_route_call/durable_summary.json`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/summaries/testclient_http_harness/durable_summary.json`
- admin/local summary:
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/summaries/direct_route_call/admin_summary_response.json`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/summaries/testclient_http_harness/admin_summary_response.json`
- admin/local durable summary:
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/summaries/direct_route_call/admin_durable_summary_response.json`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/summaries/testclient_http_harness/admin_durable_summary_response.json`

## Validação executada

- `python3 -m py_compile scripts/run_document_hard_gate_10j_http_harness.py scripts/run_document_hard_gate_10j_shadow_campaign.py web/tests/test_v2_document_hard_gate_10i.py` -> `ok`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10i.py` -> `5 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -c "import main; main.create_app(); print('boot_import_ok')"` -> `boot_import_ok`
- `AMBIENTE=dev PYTHONPATH=web python3 scripts/run_document_hard_gate_10j_shadow_campaign.py` -> campanha concluída com `6` execuções úteis

## Avaliação da amostra

- a amostra melhorou de forma material em relação ao `10I`
- o ponto foi repetido em dois harnesses diferentes
- as duas rotas públicas foram exercitadas com casos `gap` e `ok`
- `did_block` permaneceu `false` em toda a campanha
- a publicação real continuou funcional em todas as execuções

Resposta objetiva para a fase:

- faz sentido abrir um novo gate review deste ponto para continuidade em `shadow_only`
- ainda nao faz sentido discutir `enforce`

## Rollback

- desligar completamente o slice:
  - remover `template_publish_activate` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
  - ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`
- desligar apenas a trilha durável:
  - desligar `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE`
  - ou remover `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR`
- restringir novamente o recorte, se necessario:
  - usar `TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES`

## Conclusão

A campanha operacional do `10J` ampliou de verdade a amostra de `template_publish_activate` em `shadow_only`, repetindo o ponto em dois harnesses e quatro perfis de caso sem qualquer bleed funcional. Os únicos blockers observados continuaram sendo `template_not_bound` e `template_source_unknown`; a família adicional de governança de template permaneceu `nao_observado`, o que mantém a recomendação restrita a um novo gate review de `shadow`, não de `enforce`.
