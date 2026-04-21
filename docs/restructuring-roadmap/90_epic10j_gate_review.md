# Gate review formal do Epic 10J sobre `template_publish_activate` após campanha ampliada em `shadow_only`

## Objetivo

Executar uma revisão formal do recorte:

- `POST /revisao/api/templates-laudo/{template_id}/publicar`
- `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- `operation_kind=template_publish_activate`

usando código atual, documentação atual, artifacts reais do `10I` e da campanha `10J`, para decidir se este ponto pode algum dia avançar além de `shadow_only`.

## Escopo revisado

- código atual do recorte:
  - `web/app/domains/revisor/template_publish_shadow.py`
  - `web/app/domains/revisor/templates_laudo_management_routes.py`
  - `web/app/v2/document/hard_gate.py`
  - `web/app/v2/document/hard_gate_evidence.py`
  - `web/app/domains/admin/routes.py`
- testes rerodados:
  - `web/tests/test_v2_document_hard_gate_10i.py`
  - `web/tests/test_smoke.py`
- docs canônicos obrigatórios em `/home/gabriel/Área de trabalho/Tarie 2`
- roadmap/documentação local da trilha `10A` -> `10J`
- artifacts obrigatórios:
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/`
  - `artifacts/document_hard_gate_review_10i/20260327_235811/`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/`

## Pré-checagem da revisão

- `pwd` confirmado em:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - o repositório continua com worktree ampla e suja fora do recorte documental
  - a revisão ficou restrita ao slice do hard gate documental, artifacts e docs
- artifacts mais recentes localizados:
  - validação 10I:
    - `artifacts/document_hard_gate_validation_10i/20260327_233048/`
  - review 10I:
    - `artifacts/document_hard_gate_review_10i/20260327_235811/`
  - campanha ampliada 10J:
    - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/`
- tenant/escopo usados:
  - tenant:
    - `1`
  - host:
    - `testclient`
  - operação:
    - `template_publish_activate`
  - rotas:
    - `POST /revisao/api/templates-laudo/{template_id}/publicar`
    - `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- flags revisadas:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=template_publish_activate`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES` variando por execução controlada
- código alterado fora do recorte esperado:
  - sim
  - a worktree global segue com muitas alterações não relacionadas, inclusive Android e outras trilhas
  - esta fase não alterou código de produto

## Evidências usadas

- docs canônicos V2 em `/home/gabriel/Área de trabalho/Tarie 2`:
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
  - `docs/restructuring-roadmap/88_epic10i_gate_review.md`
  - `docs/restructuring-roadmap/89_epic10j_template_publish_shadow_campaign.md`
  - `docs/restructuring-roadmap/99_execution_journal.md`
- artifacts operacionais reais:
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/runtime_summary.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/durable_summary.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/validation_cases.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/final_report.md`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/responses/admin_summary_response.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/responses/admin_durable_summary_response.json`
  - `artifacts/document_hard_gate_review_10i/20260327_235811/review_summary.json`
  - `artifacts/document_hard_gate_review_10i/20260327_235811/review_findings.md`
  - `artifacts/document_hard_gate_review_10i/20260327_235811/decision.txt`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/campaign_summary.json`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/campaign_cases.json`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/campaign_findings.md`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/harness_matrix.json`

## Achados principais

### 1. O recorte continua sendo um bom ponto para `shadow` e realmente permaneceu `shadow_only`

No código atual:

- `template_publish_activate` permanece listado como `shadow_only`;
- `enforce_enabled` continua `false` neste `operation_kind`;
- `did_block` continua `false`;
- a instrumentação só roda em host local/controlado, tenant allowlisted, operação allowlisted e template code allowlisted quando configurado.

Na evidência acumulada revisada:

- `8` execuções úteis totais;
- `2` harnesses reais;
- `4` perfis de caso;
- `HTTP 200=8`;
- `audit_generated=8`;
- `did_block=0` em `100%` das execuções;
- nenhum bleed observado para tenant real.

Resposta objetiva:

- sim, `template_publish_activate` continua sendo um bom ponto para `shadow`.

### 2. O ponto continua semanticamente forte e melhor do que `report_finalize_stream` e `review_reject`

Leitura consolidada:

- publicar template ativa a versão operacional que governa o domínio documental do tenant;
- o ponto está em rotas dedicadas de templates;
- o domínio já possui auditoria operacional durável nativa.

Resposta objetiva:

- sim, ele continua semanticamente melhor do que `report_finalize_stream` e `review_reject`;
- sim, ele continua sendo um candidato potencial a `future_enforce`;
- não, isso ainda não autoriza avançar além de `shadow_only` agora.

O que ainda falta observar:

- uma família própria adicional de blockers de governança de template além de binding/source gap.

### 3. Os blockers atuais continuam fortes para observação, mas só parcialmente maduros

Blockers observados com repetição estável:

- `template_not_bound`
  - `4` ocorrências acumuladas revisadas
- `template_source_unknown`
  - `4` ocorrências acumuladas revisadas

Leitura:

- continuam fortes para observação;
- já são parcialmente maduros para uma futura conversa de `enforce` muito estreito;
- a ausência de uma família própria adicional de blockers de governança de template pesa materialmente contra qualquer avanço além de `shadow_only` agora.

Resposta objetiva:

- a ausência dessa família adicional não impede manter `shadow`;
- ela impede aprovar agora qualquer avanço além de `shadow_only`.

### 4. A observabilidade atual já é suficiente para `shadow` e suficiente com restrições para uma conversa futura

Fontes revisadas:

- `runtime_summary`
- `durable_summary`
- `validation_cases`
- `final_report`
- `admin_summary_response`
- `admin_durable_summary_response`
- `campaign_summary`
- `campaign_cases`
- `harness_matrix`
- auditoria operacional do domínio de templates

Leitura:

- a observabilidade atual é suficiente para manter `shadow`;
- ela já é suficiente com restrições para uma futura conversa de `enforce`;
- ela é melhor do que a do `report_finalize_stream` de forma material.

O gargalo remanescente:

- não é observabilidade;
- é a lacuna semântica e operacional da família própria adicional de blockers de governança de template.

### 5. O 10J está bem validado para continuar em `shadow`, mas ainda não para avançar além disso

Checks atuais:

- `boot_import_ok`
- `py_compile` sem erro
- `web/tests/test_v2_document_hard_gate_10i.py` -> `5 passed`
- `web/tests/test_smoke.py` -> `26 passed`

Leitura:

- sim, o 10J está bem validado para continuar em `shadow`;
- não, ele ainda não está validado o suficiente para aprovar qualquer avanço além de `shadow_only` agora.

O que ainda falta objetivamente:

- observar e classificar uma família própria adicional de blockers de governança de template;
- ou justificar formalmente, com nova evidência dedicada, por que um eventual escopo futuro continuaria limitado apenas a `template_not_bound` e `template_source_unknown`.

## Decisão formal

Decisão:

- `hold_before_any_enforce`

Rationale curto:

- `template_publish_activate` confirmou semântica forte, dois harnesses, amostra materialmente melhor e observabilidade durável suficiente.
- porém toda a evidência de blockers continua restrita a `template_not_bound` e `template_source_unknown`.
- a família própria adicional de governança de template segue `nao_observado`.
- portanto, a decisão conservadora correta é segurar qualquer avanço além de `shadow_only` por enquanto.

## Condições para qualquer futura discussão de `enforce`

- observar e validar ao menos uma família própria adicional de blockers de governança de template, ou justificar formalmente por evidência dedicada por que o escopo inicial continuaria restrito apenas a `template_not_bound` e `template_source_unknown`;
- provar comportamento bloqueado e comportamento permitido em piloto estritamente local/controlado, com tenant allowlist, template code allowlist, rollback imediato e trilha durável em pelo menos dois harnesses;
- manter qualquer futuro escopo inicial sem misturar blockers case-level de emissão/finalização de laudo com a semântica de publicação de template.

## Conclusão

`template_publish_activate` permanece um ponto documental forte e um bom candidato potencial de longo prazo, mas ainda não pode avançar além de `shadow_only` agora. A campanha ampliada resolveu a falta de amostra pequena e de harness único; o limitante remanescente passou a ser a ausência de uma família própria adicional de blockers de governança de template.
