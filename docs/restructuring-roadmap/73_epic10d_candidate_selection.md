# Selecao controlada do proximo ponto mutavel documental apos o gate review do 10C

## Objetivo

Escolher formalmente o melhor proximo ponto mutavel documental para o 10D sem ainda implementa-lo, respeitando:

- um unico novo ponto mutavel
- rollout apenas local/controlado
- tenant allowlisted
- operation allowlisted
- manutencao do check de boot/import
- nenhuma promocao indevida de blockers hoje em `shadow_only`

## Pre-checagem

- workspace:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- artefatos mais recentes localizados:
  - 10B:
    - `artifacts/document_hard_gate_validation/20260327_092450/`
  - 10C:
    - `artifacts/document_hard_gate_validation_10c/20260327_104739/`
  - gate review do 10C:
    - `artifacts/document_hard_gate_review_10c/20260327_115916/`
- pontos mutaveis ja cobertos:
  - `report_finalize`
  - `review_approve`
- condicoes herdadas do gate review do 10C confirmadas:
  - abrir no maximo um novo ponto mutavel
  - manter host local/controlado
  - manter tenant allowlisted
  - manter operation allowlisted
  - nao promover blockers hoje em `shadow_only` para `enforce` sem prova operacional dedicada
  - manter boot/import check
  - continuar exportando artifacts por execucao
  - se o proximo candidato tiver blast radius maior que `review_approve`, iniciar em `shadow_only`

## Candidatos reais auditados

### Candidato A

- rota:
  - `POST /revisao/api/laudo/{laudo_id}/avaliar`
- recorte:
  - `acao=rejeitar`
- servico:
  - `web/app/domains/revisor/mesa_api.py::avaliar_laudo`
  - `web/app/domains/revisor/service_messaging.py::avaliar_laudo_revisor`
- `operation_kind` proposto:
  - `review_reject`

### Candidato B

- rota:
  - `POST /app/api/laudo/{laudo_id}/reabrir`
  - `POST /cliente/api/chat/laudos/{laudo_id}/reabrir`
- servico:
  - `web/app/domains/chat/laudo_service.py::reabrir_laudo_resposta`
- `operation_kind` proposto:
  - `report_reopen`

### Candidato C

- rota:
  - `POST /revisao/api/templates-laudo/{template_id}/publicar`
- servico:
  - `web/app/domains/revisor/templates_laudo_management_routes.py::publicar_template_laudo`
- `operation_kind` proposto:
  - `template_publish_activate`

### Candidato D

- rotas:
  - `POST /revisao/api/templates-laudo/lote/status`
  - `POST /revisao/api/templates-laudo/lote/excluir`
- servico:
  - `web/app/domains/revisor/templates_laudo_management_routes.py`
- `operation_kind` proposto:
  - `template_library_batch_mutation`

## Operacoes auditadas e excluidas do ranking mutavel

- `POST /app/api/gerar_pdf`
  - `preview_pdf` ja existe como ponto de soft gate e gera apenas arquivo temporario
- `GET /revisao/api/laudo/{laudo_id}/pacote/exportar-pdf`
  - `review_package_pdf_export` exporta PDF temporario do pacote, sem mutar estado documental
- `review_issue`
  - aparece em `web/app/v2/document/gate_models.py` e em `web/tests/test_v2_document_hard_gate.py`, mas a auditoria nao encontrou rota mutavel real de emissao implementada no produto atual

## Rankeamento comparativo

### Candidato A - melhor

Motivos:

- continua dentro do mesmo comando tecnico do 10C
- reusa bem `request.state`, pacote da mesa, provenance, policy, facade e summary do hard gate
- aceita allowlist por tenant e operacao com o menor custo de implementacao conceitual
- o blast radius e moderado e restrito ao portal do revisor

Limite:

- e um caminho corretivo, nao um caminho de emissao
- por isso, blockers do hard gate atual nao devem virar bloqueio real aqui

Conclusao:

- melhor candidato para um 10D **apenas em `shadow_only`**

### Candidato B - aceitavel com restricoes

Motivos:

- rollback simples
- mutacao documental real

Problemas:

- o servico e reaproveitado por inspetor e admin-cliente
- a superficie cresce para dois portais
- o contexto documental e mais fraco do que no fluxo da mesa
- bloquear reabertura por readiness documental e semanticamente ruim

Conclusao:

- aceitavel so se o candidato A for descartado
- tambem apenas em `shadow_only`

### Candidato C - segurar

Problemas:

- blast radius tenant-wide
- muda a versao ativa da biblioteca
- rebaixa versoes anteriores
- nao reusa bem os blockers e summaries do hard gate atual

Conclusao:

- nao deve ser o 10D

### Candidato D - nao abrir agora

Problemas:

- mutacao em lote ou exclusao
- rollback pior
- aderencia fraca ao hard gate documental do caso

Conclusao:

- nao abrir agora

## Achado estrutural importante

Durante a selecao foi identificado um ponto mutavel paralelo ja existente:

- `web/app/domains/chat/chat_stream_routes.py`
- o comando `finalizarlaudoagora` ainda faz:
  - `status_revisao = Aguardando`
  - fora de `web/app/domains/chat/laudo_service.py`

Interpretacao:

- isso nao impede abrir um 10D **muito restrito e so em `shadow_only`**
- mas impede usar o 10D como argumento para ampliar enforcement mais forte sem antes reconciliar ou escopar esse bypass

## Candidato escolhido

- rota:
  - `POST /revisao/api/laudo/{laudo_id}/avaliar`
- recorte:
  - `acao=rejeitar`
- servico:
  - `web/app/domains/revisor/mesa_api.py::avaliar_laudo`
  - `web/app/domains/revisor/service_messaging.py::avaliar_laudo_revisor`
- `operation_kind` proposto:
  - `review_reject`

## Por que foi escolhido

- e o candidato com melhor continuidade arquitetural apos o 10C
- fica no mesmo bounded context tecnico da mesa
- reusa a mesma base de observabilidade ja provada
- mantem o rollout local/controlado simples
- nao exige abrir um segundo dominio ou um fluxo tenant-wide

## Modo de abertura recomendado para o 10D

- `shadow_only`

## Blockers recomendados em enforce no 10D

- nenhum

Racional:

- `review_reject` e caminho corretivo
- a mesa nao deve ser impedida de rejeitar um caso porque o documento ainda nao esta pronto para materializacao ou emissao

## Blockers recomendados em shadow no 10D

- `no_active_report`
- `template_not_bound`
- `template_source_unknown`
- `materialization_disallowed_by_policy`
- `issue_disallowed_by_policy`
- `review_requirement_not_satisfied`
- `engineer_approval_requirement_not_satisfied`
- `engineer_approval_pending`
- `review_still_required_for_issue`
- `provenance_summary_unavailable`
- `document_source_insufficient`

## Tenant/host/contexto recomendado

- tenant allowlist:
  - `2`
  - `Tariel.ia Lab Carga Local`
- operation allowlist:
  - `review_reject`
- host/contexto:
  - local only
  - `127.0.0.1`
  - `::1`
  - `localhost`
  - `testclient`

## Rollback recomendado

- remover `review_reject` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
- ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`

## Validacao rerodada nesta selecao

- `cd web && python3 -c "import main; app = main.create_app(); print('boot_import_ok')"` -> `boot_import_ok`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate.py` -> `2 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_integration.py` -> `2 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_summary.py` -> `1 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate.py` -> `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_enforce.py` -> `4 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_summary.py` -> `1 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10c.py` -> `5 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`

## Decisao formal

- `approved_for_10d_shadow_only`

### Rationale curto

O melhor candidato real e `review_reject`, porque reaproveita quase toda a base de observabilidade e o contexto tecnico do 10C sem abrir outro dominio mutavel. Mesmo assim, ele so deve abrir em `shadow_only`, porque rejeicao e caminho corretivo e nao deve ser barrada pelos blockers documentais atuais.

## O que ficou descartado ou adiado

- `report_reopen`
  - adiado como segunda opcao, por tocar inspetor e admin-cliente ao mesmo tempo
- `template_publish_activate`
  - adiado por blast radius tenant-wide e baixa aderencia ao gate atual
- mutacoes em lote de templates
  - descartadas para esta trilha

## Artefatos desta selecao

- `artifacts/document_next_mutable_point_selection/20260327_124413/candidate_matrix.json`
- `artifacts/document_next_mutable_point_selection/20260327_124413/candidate_ranking.md`
- `artifacts/document_next_mutable_point_selection/20260327_124413/selection_decision.txt`
- `artifacts/document_next_mutable_point_selection/20260327_124413/source_evidence_index.txt`

## Artefatos desta fase

- `artifacts/document_next_mutable_point_selection/20260327_122207/candidate_matrix.json`
- `artifacts/document_next_mutable_point_selection/20260327_122207/candidate_ranking.md`
- `artifacts/document_next_mutable_point_selection/20260327_122207/selection_decision.txt`
- `artifacts/document_next_mutable_point_selection/20260327_122207/source_evidence_index.txt`
