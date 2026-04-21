# Gate review formal do Epic 10D sobre `review_reject` shadow_only

## Objetivo

Revisar formalmente o Epic 10D para decidir, com evidencia real, se o ponto mutavel `review_reject` pode avancar alem de `shadow_only`.

## Escopo revisado

- codigo atual do 10D:
  - `web/app/v2/document/hard_gate.py`
  - `web/app/v2/document/hard_gate_metrics.py`
  - `web/app/domains/revisor/mesa_api.py`
  - `web/app/domains/revisor/service_messaging.py`
  - `web/app/domains/admin/routes.py`
- testes:
  - `web/tests/test_v2_document_hard_gate_10d.py`
  - `web/tests/test_smoke.py`
- docs da trilha 10A -> 10D
- artefatos operacionais reais do 10D:
  - `artifacts/document_hard_gate_validation_10d/20260327_141956/`

## Pre-checagem da revisao

- workspace:
  - `/home/gabriel/Area de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - repositiorio continua muito sujo e com mudancas nao relacionadas, inclusive fora do recorte documental
  - por isso a revisao ficou restrita ao slice do hard gate documental e aos artifacts do 10D
- artefato mais recente do 10D localizado em:
  - `artifacts/document_hard_gate_validation_10d/20260327_141956/`
- tenant e alvos usados no 10D:
  - tenant:
    - `2`
    - `Tariel.ia Lab Carga Local`
  - alvos:
    - laudo `1` -> `shadow_review_reject_with_template_gap`
    - laudo `2` -> `shadow_review_reject_with_reduced_blockers`
- flags usadas na validacao real do 10D:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=2`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=review_reject`
- alteracoes fora do recorte esperado:
  - sim, existem muitas mudancas nao relacionadas no worktree global
  - no recorte do 10D, os arquivos auditados continuam localizados no slice esperado

## Evidencias usadas

- `docs/restructuring-roadmap/67_epic10a_document_soft_gate.md`
- `docs/restructuring-roadmap/68_epic10b_document_hard_gate.md`
- `docs/restructuring-roadmap/69_epic10b_hard_gate_validation.md`
- `docs/restructuring-roadmap/70_epic10b_gate_review.md`
- `docs/restructuring-roadmap/71_epic10c_next_mutable_document_point.md`
- `docs/restructuring-roadmap/72_epic10c_gate_review.md`
- `docs/restructuring-roadmap/73_epic10d_candidate_selection.md`
- `docs/restructuring-roadmap/74_epic10d_review_reject_shadow.md`
- `artifacts/document_hard_gate_validation_10d/20260327_141956/prep_state.json`
- `artifacts/document_hard_gate_validation_10d/20260327_141956/runtime_summary.json`
- `artifacts/document_hard_gate_validation_10d/20260327_141956/validation_cases.json`
- `artifacts/document_hard_gate_validation_10d/20260327_141956/final_report.md`

## Achados principais

### 1. `review_reject` foi um bom ponto para abrir em shadow

Motivos:

- reaproveitou o mesmo bounded context da mesa e o mesmo circuito tecnico do 10C
- adicionou observabilidade real sem alterar payload ou UX
- manteve o caminho funcional da rejeicao intacto

Classificacao:

- ponto mutavel de `risco_moderado`

Racional:

- rejeicao muda estado, notifica o inspetor e devolve o caso para correcao
- portanto nao e baixo risco
- mas o 10D nao introduziu bloqueio funcional real nesse ponto

### 2. A restricao a `shadow_only` foi aplicada corretamente

Evidencia estrutural:

- em `web/app/v2/document/hard_gate.py`
  - `review_reject` nunca entra em `enforce_enabled`
  - todos os blockers ficam em `shadow_only`
  - `did_block` permanece `false`
- em `web/app/domains/revisor/mesa_api.py`
  - o novo ponto so e instrumentado em host local/controlado, tenant allowlisted e operation allowlisted

Evidencia operacional:

- `runtime_summary.json`
  - `evaluations=2`
  - `would_block=2`
  - `did_block=0`
  - `shadow_only=2`
  - `enforce_controlled=0`
- `validation_cases.json`
  - os dois casos retornaram `HTTP 200`
  - os dois laudos terminaram em `Rejeitado`

Conclusao:

- a decisao de manter todo o 10D em `shadow_only` foi correta

### 3. O conjunto atual de blockers nao sustenta enforce em `review_reject`

Blockers observados no 10D:

- `template_not_bound`
- `template_source_unknown`
- `issue_disallowed_by_policy`
- `review_requirement_not_satisfied`
- `engineer_approval_requirement_not_satisfied`
- `engineer_approval_pending`
- `review_still_required_for_issue`

Leitura semantica:

- todos eles descrevem readiness para emissao, aprovacao humana ou estado documental
- nenhum deles descreve uma condicao legitima para impedir a mesa de rejeitar um caso e devolve-lo para ajuste

Conclusao:

- no contexto de `review_reject`, estes blockers sao:
  - bons para observacao e telemetria
  - inadequados para bloqueio real

### 4. Existe risco semantico real em bloquear um caminho corretivo

O proprio racional da selecao do 10D ja reconhecia:

- `review_reject` e um caminho corretivo
- a mesa nao deve ser impedida de rejeitar porque o documento ainda nao esta pronto para emissao

O runtime do 10D reforca isso:

- ate o caso com template ativo continuou mostrando blockers de issue/review/aprovacao
- esses sinais confirmam que o caso ainda nao esta pronto para emitir
- mas isso nao significa que a mesa deva ser proibida de devolver o caso

Conclusao:

- `review_reject` deve permanecer `shadow_only` por mais tempo
- e possivel que o conjunto atual de blockers nunca deva virar `enforce` neste ponto

### 5. A observabilidade atual basta para continuar em shadow, mas nao para discutir future_enforce

Pontos positivos:

- summary admin/local-only por operacao, blocker e tenant
- `runtime_summary`, `validation_cases` e `final_report` reais
- contagem explicita de `evaluations`, `would_block` e `did_block`

Limites:

- summary ainda e volatil em memoria
- apenas duas avaliacoes operacionais no 10D
- nao existe trilha persistente longa o suficiente para inferir maturidade de enforce

Conclusao:

- observabilidade `suficiente_com_restricoes`
- suficiente para `shadow`
- insuficiente para discutir `future_enforce`

### 6. O rollback continua simples

- remover `review_reject` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
- ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`

Conclusao:

- rollback `simples`

### 7. Ha risco estrutural remanescente contra qualquer endurecimento

O achado anterior continua valendo:

- `web/app/domains/chat/chat_stream_routes.py::finalizarlaudoagora` ainda muta revisao fora do recorte reconciliado do hard gate

Isso nao invalida o 10D em shadow.

Mas pesa contra:

- qualquer argumento de maior maturidade estrutural
- qualquer endurecimento adicional sem uma rodada propria de reconciliacao

## Testes rerodados nesta revisao

- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10d.py` -> `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`
- `python3 -m py_compile web/app/domains/revisor/mesa_api.py web/app/v2/document/hard_gate.py web/tests/test_v2_document_hard_gate_10d.py` -> `ok`

## Decisao formal

- `hold_before_any_enforce`

### Rationale curto

O 10D comprovou que `review_reject` foi bem aberto em `shadow_only`: sem bleed para tenant real, sem bloquear a operacao, com summary real e rollback simples. Mas o review tambem confirmou que os blockers observados sao blockers de emissao/aprovacao documental, nao blockers legitimos para impedir a rejeicao de um caso. Portanto, nao existe base semantica nem operacional para discutir `enforce` agora.

## Posicao operacional recomendada

- manter `review_reject` em `shadow_only`
- seguir aprendendo com telemetria
- nao promover nenhum blocker atual a `enforce` neste ponto

## Condicoes explicitas antes de qualquer discussao futura de enforce

- definir semantica e politica explicitas para bloqueio de rejeicao
- criar blockers especificos de `review_reject`, em vez de reaproveitar blockers de emissao
- produzir validacao operacional dedicada mostrando beneficio real de bloquear rejeicao sem degradar o fluxo corretivo
- ampliar observabilidade para historico persistente e amostra operacional significativamente maior
- reconciliar ou isolar caminhos paralelos de mutacao de revisao antes de usar este ponto como base para endurecimento

## O que ainda nao deve acontecer

- qualquer ampliacao para tenant real
- qualquer promocao de blocker atual para `enforce` em `review_reject`
- qualquer inferencia de maturidade de enforce baseada apenas em duas avaliacoes e summary em memoria

## Artefatos desta revisao

- `artifacts/document_hard_gate_review_10d/20260327_144154/review_summary.json`
- `artifacts/document_hard_gate_review_10d/20260327_144154/review_findings.md`
- `artifacts/document_hard_gate_review_10d/20260327_144154/source_artifacts_index.txt`
- `artifacts/document_hard_gate_review_10d/20260327_144154/decision.txt`
