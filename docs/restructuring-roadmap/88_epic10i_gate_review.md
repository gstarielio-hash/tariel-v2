# Gate review formal do Epic 10I sobre `template_publish_activate` em `shadow_only`

## Objetivo

Executar uma revisao formal do novo ponto mutavel documental:

- `POST /revisao/api/templates-laudo/{template_id}/publicar`
- `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- `operation_kind=template_publish_activate`

com base em codigo atual, documentacao atual, artifacts reais e testes existentes, para decidir qual deve ser o proximo estado do slice apos a abertura inicial em `shadow_only`.

## Escopo revisado

- codigo atual do recorte:
  - `web/app/domains/revisor/template_publish_shadow.py`
  - `web/app/domains/revisor/templates_laudo_management_routes.py`
  - `web/app/v2/document/hard_gate.py`
  - `web/app/domains/admin/routes.py`
- testes rerodados:
  - `web/tests/test_v2_document_hard_gate_10i.py`
  - `web/tests/test_smoke.py`
- docs canonicos obrigatorios em `/home/gabriel/Área de trabalho/Tarie 2`
- roadmap/documentacao local da trilha `10A` -> `10I`
- artifacts obrigatorios:
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/`
  - `artifacts/document_next_strong_point_selection/20260327_225320/`

## Pre-checagem da revisao

- `pwd` confirmado em:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - o repositorio continua com worktree ampla e suja fora do recorte documental
  - a revisao permaneceu limitada ao slice do hard gate documental, aos artifacts e aos docs do roadmap
- artifact 10I mais recente localizado:
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/`
- tenant/alvos usados:
  - tenant:
    - `1`
  - templates:
    - `template_gap_10i_validation`
    - `template_ok_10i_validation`
  - rotas:
    - `POST /revisao/api/templates-laudo/{template_id}/publicar`
    - `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- flags revisadas:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=template_publish_activate`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES=template_gap_10i_validation,template_ok_10i_validation`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE=1`
- codigo alterado fora do recorte esperado:
  - a worktree possui alteracoes anteriores em varias areas do projeto
  - nao houve necessidade de tocar codigo de produto novo nesta fase de review

## Evidencias usadas

- docs canonicos V2 em `/home/gabriel/Área de trabalho/Tarie 2`:
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
  - `docs/restructuring-roadmap/81_epic10f_campaign_gate_review.md`
  - `docs/restructuring-roadmap/82_epic10g_stream_isolation_and_durable_evidence.md`
  - `docs/restructuring-roadmap/83_epic10g_shadow_campaign.md`
  - `docs/restructuring-roadmap/84_epic10h_cross_shadow_campaign.md`
  - `docs/restructuring-roadmap/85_epic10f_consolidated_gate_review.md`
  - `docs/restructuring-roadmap/86_next_strong_document_point_selection.md`
  - `docs/restructuring-roadmap/87_epic10i_template_publish_shadow.md`
  - `docs/restructuring-roadmap/99_execution_journal.md`
- artifacts obrigatorios:
  - `artifacts/document_next_strong_point_selection/20260327_225320/candidate_matrix.json`
  - `artifacts/document_next_strong_point_selection/20260327_225320/candidate_ranking.md`
  - `artifacts/document_next_strong_point_selection/20260327_225320/selection_decision.txt`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/flags_snapshot.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/runtime_summary.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/durable_summary.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/validation_cases.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/final_report.md`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/responses/admin_summary_response.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/responses/admin_durable_summary_response.json`

## Achados principais

### 1. O recorte e um bom ponto para `shadow` e realmente permaneceu `shadow_only`

No codigo atual:

- `template_publish_activate` esta listado como `shadow_only`
- a avaliacao roda apenas quando:
  - host e local/controlado
  - tenant esta allowlisted
  - operacao esta allowlisted
  - opcionalmente, o codigo do template esta allowlisted
- a integracao acontece em rotas dedicadas de templates e em helper proprio do slice

Nos artifacts revisados:

- `evaluations=2`
- `shadow_only=2`
- `would_block=1`
- `did_block=0`
- `HTTP 200=2`
- `audit_generated=2`

Nao apareceu evidencia de bleed para tenant real, nem de bloqueio funcional da publicacao.

### 2. Este ponto e semanticamente mais forte do que `review_reject` e `report_finalize_stream`

Leitura objetiva:

- publicar template ativa a versao operacional que governa o dominio documental do tenant
- a operacao fica em rotas de templates, nao em endpoint generico de chat
- o dominio ja possui auditoria operacional duravel

Resposta clara:

- sim, este ponto e mais forte para governanca documental futura do que `review_reject`
- sim, ele e mais claro e menos acoplado do que `report_finalize_stream`
- nao, isso ainda nao autoriza `enforce` agora

### 3. `template_not_bound` e `template_source_unknown` sao fortes para observacao, mas so parcialmente maduros para `future_enforce`

No 10I:

- `template_not_bound` apareceu `1` vez
- `template_source_unknown` apareceu `1` vez
- ambos so apareceram no caso `gap`
- ambos desapareceram no caso `template ok`

Leitura:

- fazem sentido semantico no ponto de publicacao
- sustentam observacao real
- ainda nao sustentam endurecimento real

Falta importante:

- ainda nao existe familia propria de blockers de governanca de template comprovada neste recorte
- qualquer discussao futura de `enforce` ainda depende de campanha propria deste ponto

### 4. A observabilidade atual e suficiente para `shadow` e melhor do que a do `report_finalize_stream`

Pontos fortes:

- `runtime_summary`
- `durable_summary`
- `admin_summary_response`
- `admin_durable_summary_response`
- artifacts JSON por execucao
- vinculo com `audit_record_id`
- auditoria operacional duravel do proprio dominio

Resposta objetiva:

- sim, a observabilidade atual e suficiente para manter `shadow`
- sim, ela e melhor do que a do `report_finalize_stream`
- nao, ela ainda nao e suficiente para defender `enforce`

O limite remanescente nao e falta de trilha duravel; o limite remanescente e amostra pequena demais.

### 5. A cobertura atual e suficiente para continuar em `shadow`, nao para endurecer

Validacoes rerodadas nesta revisao:

- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10i.py` -> `3 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`
- `python3 -m py_compile ...` -> sem erro
- `AMBIENTE=dev PYTHONPATH=web python3 -c "from main import create_app; app = create_app(); print('boot_ok', type(app).__name__)"` -> `boot_ok FastAPI`

Leitura:

- o 10I esta bem validado para continuar em `shadow_only`
- ele ainda nao esta validado o suficiente para qualquer promocao futura sem antes ampliar a evidencia operacional

## Decisao formal

Decisao:

- `approved_for_shadow_continuation`

Rationale curto:

- `template_publish_activate` confirmou semantica documental forte, isolamento melhor que os slices anteriores e auditoria duravel real.
- a evidencia do 10I ja basta para mantelo como frente ativa em `shadow_only`.
- a amostra ainda e pequena demais para qualquer conversa responsavel de `enforce`.

Condicoes para qualquer futura discussao de `enforce`:

- executar campanha operacional propria do `template_publish_activate` com amostra maior
- repetir o ponto em pelo menos um segundo harness
- manter rollout local/controlado com tenant allowlist e template code allowlist
- limitar qualquer futuro escopo inicial, no maximo, a `template_not_bound` e `template_source_unknown`
- provar se existe familia propria de blockers de governanca de template antes de qualquer endurecimento real

## Proximo passo recomendado

- campanha operacional ampliada do `template_publish_activate` em `shadow_only`

## Conclusao

`template_publish_activate` foi um bom ponto para abrir em `shadow_only`. O ponto e mais forte semanticamente e mais observavel do que os slices congelados anteriores, mas ainda precisa de campanha propria antes de qualquer conversa seria sobre avancar alem de `shadow`.
