# Roadmap review formal pos-10K sobre o futuro de `template_publish_activate`

## Objetivo

Fechar, com evidencia real do codigo atual, da documentacao atual e dos artefatos acumulados ate o `10K`, qual deve ser o foco ativo do roadmap documental a partir de agora.

## Escopo revisado

- docs canonicos em `/home/gabriel/Área de trabalho/Tarie 2`
- docs locais de `67` ate `91`
- artefatos obrigatorios:
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/`
  - `artifacts/document_hard_gate_review_10j/20260328_065704/`
  - `artifacts/template_governance_blockers_discovery/20260328_072049/`

## Pre-checagem

- `pwd`:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - worktree ampla e suja fora do recorte
  - a fase ficou restrita a docs, journal e artefatos de review
- artefatos mais recentes localizados:
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/`
  - `artifacts/document_hard_gate_shadow_campaign_10i/20260328_062125/`
  - `artifacts/document_hard_gate_review_10j/20260328_065704/`
  - `artifacts/template_governance_blockers_discovery/20260328_072049/`

## Estado consolidado do roadmap

### Pontos ja cobertos e validados

- `report_finalize`
  - baseline documental validada nas fases iniciais
- `review_approve`
  - segundo ponto mutavel real validado em recorte local/controlado

### Pontos congelados em `shadow`

- `review_reject`
  - pode permanecer no maximo como telemetria local/controlada
  - nao segue na trilha de `future enforce candidate`
- `report_finalize_stream`
  - virou slice observado em `shadow_only`
  - ja nao justifica novas campanhas dedicadas agora

### Ponto atual que chegou a familia insuficiente

- `template_publish_activate`
  - `10I` provou abertura segura em `shadow_only`
  - `10J` ampliou amostra e reforcou evidencias em dois harnesses
  - `10K` provou que ainda nao existe familia propria madura de blockers de governanca de template

Leitura consolidada:

- `template_publish_activate` continua sendo o ponto semanticamente mais forte desta trilha
- mas o gargalo agora nao e observabilidade nem amostra pequena
- o gargalo passou a ser maturidade semantica insuficiente da familia propria de blockers

## Futuro de `template_publish_activate`

Resposta formal:

- deve continuar como slice observado em `shadow_only`
- nao deve continuar como foco ativo imediato do roadmap
- nao vale insistir em mais descoberta de blockers proprios agora

Rationale:

- o ganho incremental caiu muito depois do `10K`
- a descoberta real mostrou permissao e auto-cura no dominio, nao politica madura de bloqueio
- insistir agora tende a perseguir falhas operacionais do `editor_rico` ou excecoes de fluxo, nao a abrir uma nova base documental consistente para `enforce`

## Escolha do novo foco ativo

### O que nao entra agora

- `continue_template_governance_discovery`
  - custo/ganho ruim neste momento
- `report_reopen`
  - continua sendo caminho corretivo e multiportal
- `template_status_transition`
  - recorte menos nitido do que publicar
- `template_library_batch_mutation`
  - blast radius alto e rollback pior

### Decisao correta de roadmap

- `shift_active_focus_to_next_documental_point`

Em termos praticos:

- `template_publish_activate` sai do foco ativo
- `template_publish_activate` permanece como slice observado em `shadow`
- o novo foco ativo passa a ser:
  - `select_new_documental_candidate`

## Decisao formal

- decisao geral:
  - `shift_active_focus_to_next_documental_point`
- futuro de `template_publish_activate`:
  - `keep_template_publish_as_observed_shadow_slice`
- novo foco ativo:
  - `select_new_documental_candidate`

## Rationale curto

O roadmap documental ja extraiu de `template_publish_activate` a melhor parte do investimento possivel nesta fase:

- semantica forte comprovada
- observabilidade melhor do que os slices anteriores
- trilha duravel
- campanha propria ampliada
- descoberta explicita de que a familia propria de blockers ainda nao amadureceu

O proximo movimento correto nao e insistir no mesmo ponto. E transformar essa descoberta numa nova selecao formal do proximo ponto documental do roadmap.

## Riscos remanescentes

- o roadmap ainda nao tem um novo candidato pronto para entrar direto como foco ativo sem reselecao
- ha risco de reabrir um ponto corretivo ou semanticamente fraco se a proxima selecao nao usar a mesma disciplina aplicada ate aqui

## Validacoes rerodadas

- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10i.py`
  - `5 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`
  - `26 passed`
- `python3 -m py_compile web/app/domains/revisor/template_publish_shadow.py web/app/domains/revisor/templates_laudo_management_routes.py web/app/domains/revisor/templates_laudo_support.py web/app/domains/revisor/templates_laudo_editor_routes.py web/nucleo/template_editor_word.py web/tests/test_v2_document_hard_gate_10i.py`
  - `ok`

## Artefatos desta fase

- `artifacts/document_roadmap_review_post_10k/20260328_075332/roadmap_state_matrix.json`
- `artifacts/document_roadmap_review_post_10k/20260328_075332/roadmap_review_findings.md`
- `artifacts/document_roadmap_review_post_10k/20260328_075332/decision.txt`
- `artifacts/document_roadmap_review_post_10k/20260328_075332/source_evidence_index.txt`

## Proximo passo recomendado

Nova selecao formal do proximo ponto documental forte do roadmap pos-10K, ja considerando:

- `review_reject` fora da trilha de endurecimento
- `report_finalize_stream` congelado como slice observado
- `template_publish_activate` congelado como slice observado forte, mas sem familia madura de blockers proprios
