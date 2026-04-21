# Epic 10G - isolamento estrutural e trilha duravel de evidencia para `report_finalize_stream`

## Objetivo

Cumprir as condicoes abertas no gate review do `report_finalize_stream` sem abrir `enforce` e sem mudar o contrato publico de `POST /app/api/chat`.

Nesta fase o recorte continuou estritamente:

- `shadow_only`
- local/controlado
- sem bloqueio real
- sem tenant real
- sem alterar payload publico ou UX

## Escopo implementado

Arquivos principais do slice:

- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/report_finalize_stream_shadow.py`
- `web/app/v2/document/hard_gate_evidence.py`
- `web/app/domains/admin/routes.py`
- `scripts/run_document_hard_gate_10g_validation.py`
- `web/tests/test_v2_document_hard_gate_10g.py`

## Isolamento estrutural entregue

O branch `eh_comando_finalizar` do `POST /app/api/chat` deixou de carregar diretamente a logica documental do recorte.

Agora o fluxo publico continua entrando por:

- `web/app/domains/chat/chat_stream_routes.py::rota_chat`

mas a finalizacao via stream e delegada para um modulo dedicado:

- `web/app/domains/chat/report_finalize_stream_shadow.py::processar_finalizacao_stream_documental`

O modulo dedicado concentra:

- o inicio/fim explicito do slice `report_finalize_stream`
- o escopo local/controlado do shadow
- a chamada de `_avaliar_gate_documental_finalizacao(...)`
- a persistencia local de evidencia duravel
- o payload interno de observacao em `request.state`
- a resposta SSE final do recorte

Com isso, o endpoint publico permanece igual, mas o slice ficou:

- mais testavel
- mais revisavel
- menos misturado com whispers, comandos rapidos e fluxo normal da IA

## Trilha duravel entregue

Foi adicionado um helper local-only de evidencia:

- `web/app/v2/document/hard_gate_evidence.py`

Capacidades novas:

- gravacao por execucao em arquivo JSON sob `durable_evidence/executions/<operation_kind>/`
- journal append-only em:
  - `durable_evidence/index.jsonl`
- agregacao local de resumo persistido:
  - `DocumentHardGateDurableSummaryV1`
- export runner-friendly de snapshot:
  - `durable_summary.json`
  - `durable_entries.json`

Campos reforcados por execucao:

- `correlation_id`
- `request_id`
- `operation_kind`
- `tenant_id`
- `legacy_laudo_id`
- `route_name`
- `route_path`
- `source_channel`
- `blockers`
- `would_block`
- `did_block`
- `shadow_only`
- `timestamp`
- `functional_outcome`
- `response.media_type`
- `response.sse_preserved`

Essa trilha continua:

- opcional
- local-only
- sem banco novo
- sem impacto em producao quando as flags nao estao ligadas

## Observabilidade admin/local

O summary em memoria continua existindo:

- `GET /admin/api/document-hard-gate/summary`

E agora existe leitura persistida local-only:

- `GET /admin/api/document-hard-gate/durable-summary`

Uso esperado:

- `summary`
  - estado vivo do processo
- `durable-summary`
  - reconstruir historico local a partir do journal em arquivo

## Runner reutilizavel

Foi criado um runner local para campanhas futuras do mesmo slice:

- `scripts/run_document_hard_gate_10g_validation.py`

Comandos:

- caso com template gap:
  - `python3 scripts/run_document_hard_gate_10g_validation.py --case gap`
- caso com template ativo:
  - `python3 scripts/run_document_hard_gate_10g_validation.py --case template_ok`

O runner:

- executa `boot/import check`
- cria SQLite dedicado da rodada
- liga as flags locais necessarias
- roda o slice `report_finalize_stream`
- consome o SSE real
- exporta summary em memoria e durable summary
- grava artifacts por execucao

## Validacao operacional real do 10G

Rodada controlada executada em:

- `artifacts/document_hard_gate_validation_10g/20260327_211111/`

Caso util observado:

- `shadow_stream_gap_padrao_10g`
  - `HTTP 200`
  - `content-type: text/event-stream`
  - `sse_preservado=true`
  - `would_block=true`
  - `did_block=false`
  - `shadow_only=true`
  - blockers:
    - `template_not_bound`
    - `template_source_unknown`
  - artefato duravel individual:
    - `artifacts/document_hard_gate_validation_10g/20260327_211111/durable_evidence/executions/report_finalize_stream/20260327_211114_620018__tenant_1__laudo_1__corr_36f887d7750a47109384015e93ab0ac1.json`

Resumo do runtime:

- `evaluations=1`
- `shadow_only=1`
- `did_block=0`

Resumo duravel:

- `evaluations=1`
- `shadow_only=1`
- `did_block=0`

## Artefatos de referencia do 10G

- `artifacts/document_hard_gate_validation_10g/20260327_211111/boot_import_check.txt`
- `artifacts/document_hard_gate_validation_10g/20260327_211111/runtime_summary.json`
- `artifacts/document_hard_gate_validation_10g/20260327_211111/durable_summary.json`
- `artifacts/document_hard_gate_validation_10g/20260327_211111/validation_cases.json`
- `artifacts/document_hard_gate_validation_10g/20260327_211111/final_report.md`
- `artifacts/document_hard_gate_validation_10g/20260327_211111/source_artifacts_index.txt`
- `artifacts/document_hard_gate_validation_10g/20260327_211111/summaries/durable_summary.json`
- `artifacts/document_hard_gate_validation_10g/20260327_211111/summaries/durable_entries.json`

## Testes e checks rodados

- `python3 -m py_compile web/app/v2/document/hard_gate_evidence.py web/app/domains/chat/report_finalize_stream_shadow.py web/app/domains/chat/chat_stream_routes.py web/app/domains/admin/routes.py web/tests/test_v2_document_hard_gate_10g.py scripts/run_document_hard_gate_10g_validation.py`
  - `ok`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10g.py`
  - `2 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10f.py`
  - `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`
  - `26 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -c "import main; main.create_app(); print('boot_import_ok')"`
  - `boot_import_ok`
- `python3 scripts/run_document_hard_gate_10g_validation.py --case gap`
  - artifacts gerados em `artifacts/document_hard_gate_validation_10g/20260327_211111/`

## Rollback rapido

Para desligar rapidamente o slice sem remover codigo:

- remover `report_finalize_stream` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
- ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`
- e, se preciso, desligar tambem:
  - `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR`

Como a trilha duravel e somente local e flagada, nao existe migracao de banco para desfazer.

## O que ainda falta antes de reabrir qualquer discussao de enforce

- observar `materialization_disallowed_by_policy` neste mesmo slice, se existir caso seguro e real
- observar `no_active_report` neste mesmo slice, se existir caminho semanticamente valido
- acumular mais de uma rodada controlada fora do mesmo runner
- manter a revisao disciplinada sobre `template_not_bound` e `template_source_unknown`, sem ampliar escopo de `enforce`
- continuar sem tenant real e sem alterar payload publico
