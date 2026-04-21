# Epic 10F - selecao formal do proximo ponto mutavel documental com semantica forte

## Objetivo

Escolher formalmente o proximo ponto mutavel documental depois da decisao do 10E, agora focando apenas em operacoes com semantica forte de governanca documental.

## Pre-checagem

- workspace:
  - `/home/gabriel/Area de trabalho/TARIEL/Tariel Control Consolidado`
- artefatos relevantes revisados:
  - `artifacts/document_hard_gate_validation/20260327_092450/`
  - `artifacts/document_hard_gate_review/20260327_100250/`
  - `artifacts/document_hard_gate_validation_10c/20260327_104739/`
  - `artifacts/document_hard_gate_review_10c/20260327_115916/`
  - `artifacts/document_next_mutable_point_selection/20260327_124413/`
  - `artifacts/document_hard_gate_validation_10d/20260327_141956/`
  - `artifacts/document_hard_gate_review_10d/20260327_144154/`
  - `artifacts/document_review_reject_semantics/20260327_150443/`
- pontos mutaveis ja cobertos:
  - `report_finalize`
  - `review_approve`
- `review_reject`:
  - permanece apenas em `shadow_only`
  - saiu da trilha de futuros `enforce candidates` no 10E

## Candidatos fortes auditados

### Candidato A - finalizacao no stream do inspetor

- rota:
  - `POST /app/api/chat`
- servico:
  - `web/app/domains/chat/chat_stream_routes.py::rota_chat`
- recorte:
  - branch `eh_comando_finalizar` / comando `finalizarlaudoagora`
- `operation_kind` recomendado:
  - `report_finalize_stream`
- semantica:
  - `finalizar`

Leitura:

- e um caminho mutavel real ainda fora do hard gate reconciliado
- muda o mesmo estado forte do 10B:
  - `Rascunho -> Aguardando Aval`
- grava `encerrado_pelo_inspetor_em`
- limpa `reabertura_pendente_em`
- tem efeito visivel imediato no stream/SSE do inspetor

### Candidato B - publicar template ativo

- rotas:
  - `POST /revisao/api/templates-laudo/{template_id}/publicar`
  - `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- servico:
  - `web/app/domains/revisor/templates_laudo_management_routes.py::publicar_template_laudo`
- `operation_kind` provavel:
  - `template_publish_activate`
- semantica:
  - `publicar`

Leitura:

- torna uma versao de template ativa
- rebaixa versoes ativas anteriores do mesmo codigo
- tem efeito operacional para laudos futuros do tenant

### Candidato C - mutacao em lote da biblioteca

- rotas:
  - `POST /revisao/api/templates-laudo/lote/status`
  - `POST /revisao/api/templates-laudo/lote/excluir`
- servico:
  - `web/app/domains/revisor/templates_laudo_management_routes.py`
- `operation_kind` provavel:
  - `template_library_batch_mutation`
- semantica:
  - `outra`

Leitura:

- e governanca tenant-wide
- altera varios templates de uma vez
- pode excluir itens da biblioteca

## Operacoes auditadas e descartadas do ranking

- `POST /app/api/laudo/{laudo_id}/finalizar`
  - ja coberta no 10B
- `POST /cliente/api/chat/laudos/{laudo_id}/finalizar`
  - usa o mesmo servico do 10B, logo nao e novo ponto
- `review_issue`
  - existe no contrato, mas a auditoria nao encontrou rota mutavel real implementada
- `POST /revisao/api/templates-laudo/{template_id}/base-recomendada`
  - hoje atua mais como curadoria de biblioteca do que como governanca documental forte do fluxo vivo, porque o inspetor seleciona template ativo por tipo em `web/app/domains/chat/template_helpers.py`

## Rankeamento comparativo

### Candidato A - melhor

Motivos:

- fecha uma lacuna estrutural ja conhecida
- reaproveita a mesma semantica forte de finalizacao do 10B
- reaproveita os blockers maduros com melhor aderencia:
  - `template_not_bound`
  - `template_source_unknown`
- aceita rollout local/controlado com tenant allowlist e operation allowlist
- rollback simples

Risco:

- o ponto fica dentro do endpoint principal de chat/SSE
- o recorte convive com stream, IA e caminho CBMGO
- ainda nao possui trilha propria de runtime sob hard gate

Conclusao:

- melhor proximo candidato real
- deve abrir primeiro em `shadow_only`

### Candidato B - aceitavel com condicoes pesadas

Motivos:

- tem semantica forte de publicacao
- afeta a versao operacional de template

Problemas:

- blast radius tenant-wide
- baixa aderencia aos blockers case-level ja maduros
- exigiria familia nova de blockers de biblioteca/template
- observabilidade atual e fraca para esse tipo de governanca

Conclusao:

- nao e o melhor proximo passo
- se algum dia abrir, deve comecar em `shadow_only`

### Candidato C - nao abrir agora

Problemas:

- mutacao em lote e exclusao
- blast radius muito alto
- rollback fragil
- baixa observabilidade e nenhum reaproveitamento serio dos blockers atuais

Conclusao:

- nao abrir agora

## Candidato escolhido

- rota:
  - `POST /app/api/chat`
- servico:
  - `web/app/domains/chat/chat_stream_routes.py::rota_chat`
- recorte:
  - branch `eh_comando_finalizar`
- `operation_kind` recomendado:
  - `report_finalize_stream`
- semantica:
  - `finalizar`

## Por que foi escolhido

- e o ponto forte mais proximo da trilha ja provada em runtime
- usa a mesma transicao documental forte que o 10B, mas fecha um bypass estrutural que segue fora do hard gate
- e superior a `template_publish_activate` porque reaproveita blockers maduros e nao exige abrir uma nova familia semantica de governanca de template
- e superior a mutacoes em lote porque o rollback e muito mais simples e o blast radius e menor

## Blockers recomendados para o futuro candidato

### Em enforce na abertura

- nenhum

Rationale:

- apesar de `template_not_bound` e `template_source_unknown` serem os sinais mais maduros, este caminho ainda nao tem validacao operacional propria
- `materialization_disallowed_by_policy` e `no_active_report` continuam com prova operacional mais fraca neste recorte

### Em shadow na abertura

- `template_not_bound`
- `template_source_unknown`
- `materialization_disallowed_by_policy`
- `no_active_report`

Observacao:

- apos uma rodada propria de shadow nesse caminho, os primeiros candidatos naturais para promocao seriam:
  - `template_not_bound`
  - `template_source_unknown`

## Modo recomendado

- `shadow_only`

## Decisao formal

- `approved_for_shadow_first_only`

## Rationale curto

O melhor proximo ponto mutavel com semantica forte nao e uma nova acao corretiva nem uma mutacao tenant-wide da biblioteca. E o caminho de finalizacao ja existente no stream do inspetor, porque ele fecha o bypass estrutural mais relevante do recorte documental, preserva a mesma semantica forte de `report_finalize` e reaproveita os blockers mais maduros do roadmap. Ainda assim, por estar no endpoint principal de chat/SSE e sem trilha propria de runtime sob hard gate, deve abrir primeiro em `shadow_only`.

## Validacoes rerodadas nesta fase

- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate.py` -> `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_enforce.py` -> `4 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10d.py` -> `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`
- `python3 -m py_compile web/app/domains/chat/chat_stream_routes.py web/app/domains/chat/laudo_service.py web/app/domains/revisor/templates_laudo_management_routes.py web/app/v2/document/hard_gate.py` -> `ok`

## Artefatos desta fase

- `artifacts/document_strong_semantics_selection/20260327_152341/candidate_matrix.json`
- `artifacts/document_strong_semantics_selection/20260327_152341/candidate_ranking.md`
- `artifacts/document_strong_semantics_selection/20260327_152341/selection_decision.txt`
- `artifacts/document_strong_semantics_selection/20260327_152341/source_evidence_index.txt`

## Proximo passo recomendado

Epic 10F+ - abertura controlada do recorte `report_finalize_stream` em `shadow_only` no endpoint `POST /app/api/chat`
