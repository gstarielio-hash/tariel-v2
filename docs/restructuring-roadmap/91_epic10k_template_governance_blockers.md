# Epic 10K - descoberta controlada da familia propria de blockers de governanca de template

## Objetivo

Executar uma descoberta formal sobre o recorte:

- `POST /revisao/api/templates-laudo/{template_id}/publicar`
- `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- `operation_kind=template_publish_activate`

para responder, com evidencia real, se existe hoje uma familia propria de blockers de governanca de template que sustente algo alem de observacao em `shadow_only`.

## Fontes e evidencias usadas

- docs canonicos em `/home/gabriel/Área de trabalho/Tarie 2`
- roadmap local ate `10J`
- artefatos revisados:
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/`
  - `artifacts/document_hard_gate_review_10i/20260327_235811/`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/`
  - `artifacts/document_hard_gate_review_10j/20260328_065704/`
- codigo auditado:
  - `web/app/domains/revisor/templates_laudo_management_routes.py`
  - `web/app/domains/revisor/templates_laudo_support.py`
  - `web/app/domains/revisor/templates_laudo_editor_routes.py`
  - `web/app/domains/revisor/template_publish_shadow.py`
  - `web/app/shared/db/models_laudo.py`
  - `web/nucleo/template_editor_word.py`
  - `web/tests/test_v2_document_hard_gate_10i.py`
  - `web/tests/test_regras_rotas_criticas.py`

## Pre-checagem

- `pwd`:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - worktree global continua ampla e suja fora do recorte
  - esta fase ficou restrita a artefatos, docs e journal
- artifacts localizados:
  - `10I` validacao:
    - `artifacts/document_hard_gate_validation_10i/20260327_233048/`
  - `10I` gate review:
    - `artifacts/document_hard_gate_review_10i/20260327_235811/`
  - `10J` campanha ampliada:
    - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/`
  - `10J` gate review:
    - `artifacts/document_hard_gate_review_10j/20260328_065704/`
- tenant e flags revisados:
  - tenant local/controlado:
    - `1`
  - host:
    - `testclient`
  - flags base:
    - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
    - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
    - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=template_publish_activate`
    - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=1`
    - `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE=1`
- template codes revisados:
  - campanhas anteriores:
    - `template_gap_10i_validation`
    - `template_ok_10i_validation`
    - `template_gap_10j_http_legacy`
    - `template_ok_10j_http_legacy`
    - `template_gap_10j_http_editor`
    - `template_ok_10j_http_editor`
  - descoberta `10K`:
    - `template_10k_archived_publish`
    - `template_10k_multiple_active_conflict`

## O que e governanca de template neste sistema

No estado atual do produto, governanca de template nao e apenas armazenar um arquivo PDF ou JSON de editor. O dominio implementa uma biblioteca documental por tenant com:

- versionamento por `empresa_id + codigo_template + versao`
- ciclo de vida explicito por `status_template`
  - `rascunho`
  - `em_teste`
  - `ativo`
  - `legado`
  - `arquivado`
- nocao de versao operacional ativa por grupo de `codigo_template`
- rebaixamento automatico dos ativos anteriores no publish
- `base_recomendada` como governanca auxiliar, distinta do ativo operacional
- auditoria do proprio dominio em `revisao_templates`
- geracao de snapshot PDF no publish de `editor_rico`

Em linguagem de produto + sistema:

- publicar e o comando de promocao operacional da biblioteca do tenant
- ao publicar, a versao escolhida vira a referencia ativa do grupo
- as versoes ativas anteriores sao rebaixadas para `legado`
- no editor rico, a publicacao tambem atualiza a base PDF que operacionaliza aquele template
- tudo isso fica rastreado em auditoria por `template_publicado`

## Candidatos a blockers proprios mapeados

### Reaproveitados que continuam validos so para `shadow`

- `template_not_bound`
  - observado estavelmente em `10I` e `10J`
  - continua util para observacao, mas nao e familia propria adicional de governanca
- `template_source_unknown`
  - observado estavelmente em `10I` e `10J`
  - continua util para observacao, mas nao e familia propria adicional de governanca

### Candidatos proprios com base real no dominio, mas ainda nao maduros como blocker

- `publish_transition_invalid`
  - base real:
    - o dominio possui estados de ciclo de vida bem definidos
  - limite atual:
    - o publish atual nao valida transicao de status antes de promover a versao
- `active_version_conflict`
  - base real:
    - a governanca tenta manter um unico ativo por `codigo_template`
  - limite atual:
    - o publish auto-normaliza o grupo em vez de bloquear conflito
- `template_snapshot_generation_invalid`
  - base real:
    - o publish do `editor_rico` depende de gerar snapshot PDF
    - ha caminho real de `HTTP 500` se a geracao falhar
  - limite atual:
    - isso ainda aparece mais como falha operacional de editor do que como blocker maduro de politica
- `publish_audit_context_missing`
  - base real:
    - auditoria e obrigatoria no fluxo
  - limite atual:
    - nao houve caso seguro sem fault injection para observar ausencia real de contexto de auditoria

## Observacoes reais executadas

Artifacts desta fase:

- `artifacts/template_governance_blockers_discovery/20260328_072049/blockers_hypotheses.json`
- `artifacts/template_governance_blockers_discovery/20260328_072049/blockers_classification.md`
- `artifacts/template_governance_blockers_discovery/20260328_072049/domain_governance_summary.md`
- `artifacts/template_governance_blockers_discovery/20260328_072049/source_evidence_index.txt`
- `artifacts/template_governance_blockers_discovery/20260328_072049/observations.json`

### 1. `archived_transition_direct_publish`

- harness:
  - `direct_route_call`
- template:
  - `template_10k_archived_publish`
- cenario:
  - havia uma versao `ativo`
  - a versao candidata estava `arquivado`
- resultado observado:
  - publicacao concluida com sucesso
  - `would_block=false`
  - `did_block=false`
  - sem blockers
  - versao anterior foi para `legado`
  - versao `arquivado` voltou para `ativo`
  - `audit_generated=true`
- leitura:
  - `publish_transition_invalid` nao apareceu como blocker maduro

### 2. `multiple_active_conflict_http_editor_publish`

- harness:
  - `testclient_http_harness`
- template:
  - `template_10k_multiple_active_conflict`
- cenario:
  - havia duas versoes simultaneamente `ativo`
  - a versao candidata estava `em_teste` em `editor_rico`
- resultado observado:
  - `HTTP 200`
  - `would_block=false`
  - `did_block=false`
  - sem blockers
  - as duas versoes ativas anteriores foram para `legado`
  - a versao candidata virou `ativo`
  - snapshot PDF presente
  - `audit_generated=true`
- leitura:
  - `active_version_conflict` nao apareceu como blocker
  - o comportamento real foi de auto-cura do grupo

## Classificacao final da descoberta

- governanca real de template:
  - sim
- familia propria madura de blockers de governanca de template:
  - nao
- familia propria inicial, mas insuficiente:
  - sim

Leitura consolidada:

- o sistema ja tem governanca real de template, mas ela ainda se expressa mais como promocao permissiva, rebaixamento automatico e auditoria do que como politica madura de bloqueio
- os blockers com evidencia estavel continuam sendo os reaproveitados `template_not_bound` e `template_source_unknown`
- os candidatos proprios encontrados ainda sao imaturos, auto-corretivos ou dependentes de falha operacional, nao de regra documental pronta para gate

## Validacoes rerodadas

- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10i.py`
  - `5 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`
  - `26 passed`
- `python3 -m py_compile web/app/domains/revisor/template_publish_shadow.py web/app/domains/revisor/templates_laudo_management_routes.py web/app/domains/revisor/templates_laudo_support.py web/app/domains/revisor/templates_laudo_editor_routes.py web/nucleo/template_editor_word.py web/tests/test_v2_document_hard_gate_10i.py`
  - `ok`

## Decisao formal desta fase

- `familia_propria_insuficiente`

## O que isso muda no roadmap

- `template_publish_activate` continua semanticamente forte e melhor observavel do que `review_reject` e `report_finalize_stream`
- a descoberta `10K` reduz a incerteza sobre o problema correto:
  - o gargalo nao e falta de observabilidade
  - o gargalo e que a familia propria de blockers ainda nao esta madura no produto real
- por isso, a discussao futura de `enforce` continua conservadora:
  - ou se aceita por mais tempo um escopo apenas com blockers observacionais reaproveitados
  - ou se prova depois, com outra fase controlada, que existe uma familia propria de blockers de governanca de template de fato

## Conclusao

A conclusao correta desta fase e explicita:

- existe governanca de template no sistema
- existem candidatos proprios plausiveis
- mas ainda nao existe uma familia propria madura de blockers de governanca de template para `template_publish_activate`

Isso mantem o ponto forte para `shadow`, mas ainda nao melhora o suficiente a base para qualquer avancar alem disso.
