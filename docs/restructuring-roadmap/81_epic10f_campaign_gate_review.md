# Gate review formal do `report_finalize_stream` apos campanha ampliada de shadow

## Objetivo

Executar uma revisao formal do recorte:

- `POST /app/api/chat`
- branch `eh_comando_finalizar`
- `operation_kind=report_finalize_stream`

com base em codigo atual, documentacao atual, artifacts reais e testes existentes, para decidir qual deve ser o proximo estado do slice apos a campanha ampliada de shadow.

## Escopo revisado

- codigo atual do recorte:
  - `web/app/domains/chat/chat_stream_routes.py`
  - `web/app/domains/chat/laudo_service.py`
  - `web/app/v2/document/hard_gate.py`
  - `web/app/v2/document/hard_gate_models.py`
  - `web/app/v2/document/hard_gate_metrics.py`
  - `web/app/v2/document/gates.py`
  - `web/app/v2/document/facade.py`
  - `web/app/v2/policy/engine.py`
  - `web/app/v2/acl/technical_case_core.py`
  - `web/app/domains/admin/routes.py`
- testes rerodados:
  - `web/tests/test_v2_document_hard_gate_10f.py`
  - `web/tests/test_smoke.py`
- docs canonicos obrigatorios em `/home/gabriel/Area de trabalho/Tarie 2`
- roadmap/documentacao local da trilha 10A -> 10F+
- artifacts obrigatorios:
  - `artifacts/document_hard_gate_validation_10f/20260327_155813/`
  - `artifacts/document_hard_gate_review_10f/20260327_161354/`
  - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/`

## Pre-checagem da revisao

- `pwd` confirmado em:
  - `/home/gabriel/Area de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - o repositorio continua amplo/sujo fora do recorte documental
  - por isso a revisao permaneceu limitada ao slice do hard gate documental e aos artifacts associados
- artifacts 10F mais recentes localizados:
  - validacao:
    - `artifacts/document_hard_gate_validation_10f/20260327_155813/`
  - review anterior:
    - `artifacts/document_hard_gate_review_10f/20260327_161354/`
  - campanha ampliada:
    - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/`
- tenant/host/operacao usados:
  - tenant:
    - `1`
    - `Empresa A`
  - host:
    - `testclient/local controlled`
  - rota:
    - `POST /app/api/chat`
  - `operation_kind`:
    - `report_finalize_stream`
- flags revisadas:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=report_finalize_stream`

## Evidencias usadas

- docs canonicos V2 em `/home/gabriel/Area de trabalho/Tarie 2`:
  - `docs/63_FOR_CHATGPT.md`
  - `docs/product-canonical-vision/20_roles_and_permissions.md`
  - `docs/product-canonical-vision/21_privacy_and_data_governance.md`
  - `docs/product-canonical-vision/22_tenant_policies.md`
  - `docs/architecture-v2/50_target_architecture.md`
  - `docs/architecture-v2/52_template_and_document_strategy.md`
  - `docs/architecture-v2/53_security_and_tenancy.md`
  - `docs/architecture-v2/55_anti_corruption_layers.md`
  - `docs/migration/60_migration_strategy.md`
  - `docs/migration/65_success_metrics.md`
  - `docs/migration/68_rollout_and_feature_flags.md`
  - `docs/migration/69_validation_matrix.md`
- roadmap local:
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
  - `docs/restructuring-roadmap/79_epic10f_gate_review.md`
  - `docs/restructuring-roadmap/80_epic10f_shadow_campaign.md`
  - `docs/restructuring-roadmap/99_execution_journal.md`
- artifacts obrigatorios:
  - `artifacts/document_hard_gate_validation_10f/20260327_155813/runtime_summary.json`
  - `artifacts/document_hard_gate_validation_10f/20260327_155813/validation_cases.json`
  - `artifacts/document_hard_gate_validation_10f/20260327_155813/final_report.md`
  - `artifacts/document_hard_gate_review_10f/20260327_161354/review_summary.json`
  - `artifacts/document_hard_gate_review_10f/20260327_161354/review_findings.md`
  - `artifacts/document_hard_gate_review_10f/20260327_161354/decision.txt`
  - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/campaign_summary.json`
  - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/campaign_cases.json`
  - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/campaign_findings.md`
  - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/source_cases_index.txt`
  - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/boot_import_check.txt`
  - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/responses/admin_summary_response.json`

## Achados principais

### 1. O recorte continua seguro para `shadow` e realmente permanece `shadow_only`

No codigo atual:

- `report_finalize_stream` continua listado em `_SHADOW_ONLY_OPERATION_KINDS`
- `enforce_enabled` fica `false` para esse `operation_kind`
- `did_block` fica `false`
- a instrumentacao so roda em host local/controlado, tenant allowlisted e operacao allowlisted

Nos artifacts revisados:

- validacao 10F+:
  - `evaluations=2`
  - `did_block=0`
  - `shadow_only=2`
- campanha ampliada:
  - `evaluations=4`
  - `did_block=0`
  - `shadow_only=4`

Nao apareceu evidencia de bleed para tenant real, nem de bloqueio funcional do SSE do inspetor.

### 2. A amostra ampliada ja basta para aprovar continuidade em shadow, mas nao basta para `future_enforce`

A nova leitura consolidada ficou assim:

- 2 casos uteis na validacao inicial do 10F+
- 4 casos uteis na campanha ampliada
- total combinado:
  - `6` casos uteis
  - `6` respostas `HTTP 200`
  - `6` SSE preservados
  - `3` casos com `would_block=true`
  - `3` casos com `would_block=false`
  - `0` casos com `did_block=true`

Isso e suficiente para aprovar explicitamente a continuidade do slice em `shadow_only`.

Isso ainda nao e suficiente para discutir `future_enforce` porque a evidencia segue concentrada em um unico contexto local/controlado, com summary volatil em memoria e um branch ainda embutido no endpoint principal de chat.

### 3. `template_not_bound` e `template_source_unknown` sao os blockers mais maduros deste recorte, mas ainda so parcialmente

No conjunto combinado:

- `template_not_bound` apareceu `3` vezes
- `template_source_unknown` apareceu `3` vezes
- ambos se repetiram em todos os casos `template gap`
- ambos desapareceram em todos os casos `template ok`

Leitura:

- isso mostra estabilidade suficiente para mantelos como candidatos futuros
- nao mostra maturidade suficiente para aprovar `future_enforce` agora

Portanto, eles seguem `parcialmente_maduros`: fortes para observacao e candidaturas futuras, ainda insuficientes para endurecimento no estado atual.

### 4. `materialization_disallowed_by_policy` e `no_active_report` ainda fazem falta critica para qualquer discussao de enforce

Esses blockers continuam `nao_observado` neste slice.

A ausencia foi auditada no codigo:

- `report_finalize_stream` pressupoe laudo ativo
- o policy engine atual deriva `document_materialization_allowed=true` quando existe laudo ativo

Leitura:

- essa ausencia nao desqualifica a continuidade em `shadow_only`
- mas impede qualquer discussao ampla de `enforce`
- no minimo, esses dois blockers devem continuar fora de qualquer futuro escopo de bloqueio ate que exista observacao propria neste mesmo recorte

### 5. A observabilidade atual e suficiente para manter `shadow`, mas ainda nao para endurecer

Pontos fortes:

- summary admin/local-only por operacao, blocker e tenant
- `recent_results` com metadados de rota
- artifacts por execucao com:
  - `runtime_summary`
  - `validation_cases`
  - `campaign_summary`
  - `campaign_cases`
  - `admin_summary_response`
  - `boot_import_check`

Limites:

- `web/app/v2/document/hard_gate_metrics.py` ainda mantem tudo em memoria
- restart zera a serie
- a trilha historica depende dos artifacts exportados

Resposta objetiva:

- sim, a observabilidade atual e suficiente para manter `shadow`
- nao, ela ainda nao e suficiente para qualquer discussao de `future_enforce`
- sim, a volatilidade em memoria ainda pesa contra avancar alem de `shadow_only`

### 6. O rollback continua simples, mas o branch ainda precisa de mais isolamento antes de qualquer enforce

Rollback atual:

- remover `report_finalize_stream` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
- ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`

Limite estrutural remanescente:

- o branch continua dentro de `POST /app/api/chat`
- ainda convive com comandos rapidos, whispers, IA e caminhos especiais do proprio handler

Resposta objetiva:

- rollback: `simples`
- isolamento: suficiente para `shadow`, ainda insuficiente para `enforce`

## Testes rerodados nesta revisao

- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10f.py` -> `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`
- `python3 -m py_compile web/app/domains/chat/chat_stream_routes.py web/app/domains/chat/laudo_service.py web/app/v2/document/hard_gate.py web/app/v2/document/hard_gate_models.py web/app/v2/document/hard_gate_metrics.py web/app/v2/document/gate_models.py web/tests/test_v2_document_hard_gate_10f.py` -> `ok`

## Decisao formal

- `approved_for_shadow_continuation`

### Rationale curto

`report_finalize_stream` deve continuar explicitamente em `shadow_only`.

A campanha ampliada resolveu a principal duvida do gate review anterior: agora existe amostra suficiente para aprovar a continuidade em shadow com evidencia real. O recorte segue contido, nao bloqueia o fluxo, preserva SSE, repete os blockers de template de forma estavel e mantem rollback simples. Ainda nao existe base suficiente para qualquer discussao de `enforce` porque:

- a evidencia continua toda local/controlada
- o summary segue volatil em memoria
- o branch ainda vive no endpoint principal de chat/SSE
- `materialization_disallowed_by_policy` e `no_active_report` continuam sem observacao propria neste slice

## Condicoes explicitas para qualquer discussao futura de enforce

- limitar qualquer futuro escopo candidato de `enforce`, no maximo, a:
  - `template_not_bound`
  - `template_source_unknown`
- manter `materialization_disallowed_by_policy` e `no_active_report` fora de qualquer `enforce` enquanto nao houver observacao dedicada neste mesmo recorte
- executar uma nova janela controlada de evidencia fora do unico harness atual, preservando SSE e exportando artifacts por execucao
- demonstrar isolamento estrutural mais forte do branch `eh_comando_finalizar` dentro de `POST /app/api/chat`
- manter boot/import check e trilha duravel de review enquanto o summary seguir volatil em memoria

## O que ainda nao deve acontecer

- abrir `enforce` nesta fase
- ampliar para tenant real
- promover blockers nao observados para `enforce`
- inferir maturidade de `enforce` apenas da serie em memoria e deste unico contexto local

## Artefatos desta revisao

- `artifacts/document_hard_gate_review_10f_campaign/20260327_204148/review_summary.json`
- `artifacts/document_hard_gate_review_10f_campaign/20260327_204148/review_findings.md`
- `artifacts/document_hard_gate_review_10f_campaign/20260327_204148/source_artifacts_index.txt`
- `artifacts/document_hard_gate_review_10f_campaign/20260327_204148/decision.txt`
