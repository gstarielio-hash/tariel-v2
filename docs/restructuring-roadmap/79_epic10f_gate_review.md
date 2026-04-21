# Gate review formal do Epic 10F+ sobre `report_finalize_stream` shadow_only

## Objetivo

Revisar formalmente o Epic 10F+ para decidir, com evidencia real, se o ponto mutavel `report_finalize_stream` pode avancar alem de `shadow_only`.

## Escopo revisado

- codigo atual do 10F+:
  - `web/app/domains/chat/chat_stream_routes.py`
  - `web/app/domains/chat/laudo_service.py`
  - `web/app/v2/document/hard_gate.py`
  - `web/app/v2/document/hard_gate_models.py`
  - `web/app/v2/document/hard_gate_metrics.py`
  - `web/app/domains/admin/routes.py`
- testes:
  - `web/tests/test_v2_document_hard_gate_10f.py`
  - `web/tests/test_smoke.py`
- docs da trilha 10A -> 10F+
- artefatos operacionais reais do 10F+:
  - `artifacts/document_hard_gate_validation_10f/20260327_155813/`

## Pre-checagem da revisao

- workspace:
  - `/home/gabriel/Area de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - o repositorio continua muito sujo e com mudancas nao relacionadas, inclusive fora do recorte documental
  - por isso a revisao ficou restrita ao slice do hard gate documental e aos artifacts do 10F+
- artefato mais recente do 10F+ localizado em:
  - `artifacts/document_hard_gate_validation_10f/20260327_155813/`
- tenant e alvos usados no 10F+:
  - tenant:
    - `1`
    - `Empresa A`
  - host:
    - `testclient`
  - alvos:
    - laudo `1` -> `shadow_report_finalize_stream_with_template_gap`
    - laudo `2` -> `shadow_report_finalize_stream_with_active_template`
- flags usadas na validacao real do 10F+:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=report_finalize_stream`
- alteracoes fora do recorte esperado:
  - sim, existem muitas mudancas nao relacionadas no worktree global
  - no recorte do 10F+, os arquivos auditados continuam localizados no slice esperado

## Evidencias usadas

- `docs/restructuring-roadmap/67_epic10a_document_soft_gate.md`
- `docs/restructuring-roadmap/68_epic10b_document_hard_gate.md`
- `docs/restructuring-roadmap/69_epic10b_hard_gate_validation.md`
- `docs/restructuring-roadmap/70_epic10b_gate_review.md`
- `docs/restructuring-roadmap/71_epic10c_next_mutable_document_point.md`
- `docs/restructuring-roadmap/72_epic10c_gate_review.md`
- `docs/restructuring-roadmap/73_epic10d_candidate_selection.md`
- `docs/restructuring-roadmap/74_epic10d_review_reject_shadow.md`
- `docs/restructuring-roadmap/75_epic10d_gate_review.md`
- `docs/restructuring-roadmap/76_epic10e_review_reject_semantics.md`
- `docs/restructuring-roadmap/77_epic10f_strong_document_point_selection.md`
- `docs/restructuring-roadmap/78_epic10f_report_finalize_stream_shadow.md`
- `docs/restructuring-roadmap/99_execution_journal.md`
- `artifacts/document_hard_gate_validation_10f/20260327_155813/runtime_summary.json`
- `artifacts/document_hard_gate_validation_10f/20260327_155813/validation_cases.json`
- `artifacts/document_hard_gate_validation_10f/20260327_155813/final_report.md`
- `artifacts/document_hard_gate_validation_10f/20260327_155813/boot_import_check.txt`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/v2/document/hard_gate.py`
- `web/app/v2/document/hard_gate_metrics.py`
- `web/tests/test_v2_document_hard_gate_10f.py`

## Achados principais

### 1. `report_finalize_stream` foi um bom ponto para abrir em shadow

- o slice fechou o bypass estrutural mais relevante ainda fora do hard gate reconciliado
- a transicao observada e documentalmente forte:
  - `Rascunho -> Aguardando Aval`
  - grava `encerrado_pelo_inspetor_em`
- o fluxo funcional via SSE foi preservado, com `HTTP 200` nos dois casos observados

Classificacao do ponto:

- `risco_moderado`

### 2. O 10F+ realmente ficou restrito a `shadow_only`

Evidencia estrutural:

- `report_finalize_stream` entrou em `_SHADOW_ONLY_OPERATION_KINDS`
- `enforce_enabled` ficou sempre `false`
- `did_block` ficou sempre `false`
- a instrumentacao nova so roda em:
  - host local/controlado
  - tenant allowlisted
  - operation allowlisted

Evidencia operacional:

- `runtime_summary.json`
  - `evaluations=2`
  - `would_block=1`
  - `did_block=0`
  - `shadow_only=2`
  - `enforce_controlled=0`
- `validation_cases.json`
  - os dois laudos seguiram para `Aguardando Aval`

Conclusao:

- o recorte foi corretamente mantido em `shadow_only`

### 3. O recorte dentro de `/app/api/chat` continua seguro para observacao, mas ainda nao isolado o bastante para discutir enforce

- o branch `eh_comando_finalizar` esta explicitamente identificado e hoje e observavel por:
  - `operation_kind`
  - `route_name`
  - `route_path`
  - `source_channel`
  - `legacy_pipeline_name`
- isso basta para separar o shadow do restante do chat
- porem, o handler continua convivendo com:
  - comandos rapidos
  - whispers
  - fluxo normal de IA
  - branch CBMGO

Conclusao:

- seguro o bastante para `shadow`
- ainda acoplado demais ao endpoint principal para qualquer discussao precoce de `enforce`

### 4. Os blockers observados sao semanticamente corretos, mas apenas parcialmente maduros neste recorte

Blockers observados:

- `template_not_bound`
- `template_source_unknown`

Leitura:

- fazem sentido para finalizacao documental
- reaproveitam os sinais maduros ja vistos no `report_finalize` do 10B

Limite:

- no recorte do stream, esses sinais so foram observados em uma amostra pequena
- ainda nao houve observacao dedicada, neste recorte, para:
  - `materialization_disallowed_by_policy`
  - `no_active_report`

Conclusao:

- `template_not_bound` e `template_source_unknown` sao os melhores candidatos para futura discussao de `enforce`
- ainda assim, hoje a avaliacao dos blockers e:
  - `parcialmente_maduros`

### 5. A observabilidade atual basta para seguir em shadow, mas nao para discutir future_enforce

Pontos fortes:

- summary admin/local-only
- `runtime_summary`, `validation_cases` e `final_report` reais
- `recent_results` com metadados de rota
- `boot_import_check.txt` no artifact

Limites:

- summary ainda e volatil em memoria
- apenas duas avaliacoes operacionais neste slice
- historico depende dos artifacts exportados por execucao

Conclusao:

- observabilidade:
  - `suficiente_com_restricoes`

### 6. O rollback continua simples

- remover `report_finalize_stream` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
- ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`

Conclusao:

- rollback:
  - `simples`

## Testes rerodados nesta revisao

- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10f.py` -> `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`
- `python3 -m py_compile web/app/domains/chat/chat_stream_routes.py web/app/domains/chat/laudo_service.py web/app/v2/document/hard_gate.py web/app/v2/document/hard_gate_models.py web/app/v2/document/gate_models.py web/tests/test_v2_document_hard_gate_10f.py` -> `ok`

## Decisao formal

- `hold_before_any_enforce`

### Rationale curto

O 10F+ comprovou que `report_finalize_stream` foi bem aberto em `shadow_only`: sem bleed para tenant real, sem bloquear a finalizacao via stream, com summary real e rollback simples. O review tambem confirmou que este e um ponto semanticamente forte e que `template_not_bound` e `template_source_unknown` fazem sentido nesse recorte. Ainda assim, a amostra operacional e pequena, o summary segue volatil em memoria e o ponto continua embutido no endpoint principal de chat/SSE. Portanto, ainda nao existe base suficiente para sequer discutir `enforce`.

## Condicoes explicitas antes de qualquer discussao futura de enforce

- ampliar a amostra operacional do recorte em `shadow`, com mais de uma execucao bloqueavel e observacao dedicada para `materialization_disallowed_by_policy` e `no_active_report`
- provar que o branch `eh_comando_finalizar` esta suficientemente isolado do restante de `/app/api/chat`, seja por evidencias adicionais de runtime ou por refino estrutural antes do endurecimento
- manter check barato de boot/import e exportacao disciplinada de artifacts por execucao enquanto o summary seguir volatil em memoria
- rerodar gate review dedicado apos a nova rodada de shadow

## O que ainda nao deve acontecer

- qualquer ampliacao para tenant real
- qualquer promocao de blocker atual para `enforce` em `report_finalize_stream`
- qualquer inferencia de maturidade de `enforce` baseada apenas em duas avaliacoes e summary em memoria
