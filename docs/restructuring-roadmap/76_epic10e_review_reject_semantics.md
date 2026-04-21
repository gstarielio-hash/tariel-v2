# Epic 10E - decisao formal sobre o futuro semantico de `review_reject`

## Objetivo

Decidir, com evidencia real do codigo atual, da documentacao atual e dos artifacts reais do 10D, qual deve ser o futuro semantico de `review_reject` antes de qualquer discussao de `enforce`.

## Escopo

- ponto avaliado:
  - `POST /revisao/api/laudo/{laudo_id}/avaliar`
  - `acao=rejeitar`
  - `operation_kind=review_reject`
- o objetivo desta fase nao foi implementar `enforce`
- o objetivo desta fase nao foi tocar em tenant real
- o objetivo desta fase nao foi alterar payloads, UX, Android, banco ou legado

## Evidencias revisadas

- docs canonicos V2 em `/home/gabriel/Area de trabalho/Tarie 2`
- `docs/restructuring-roadmap/67_epic10a_document_soft_gate.md`
- `docs/restructuring-roadmap/68_epic10b_document_hard_gate.md`
- `docs/restructuring-roadmap/69_epic10b_hard_gate_validation.md`
- `docs/restructuring-roadmap/70_epic10b_gate_review.md`
- `docs/restructuring-roadmap/71_epic10c_next_mutable_document_point.md`
- `docs/restructuring-roadmap/72_epic10c_gate_review.md`
- `docs/restructuring-roadmap/73_epic10d_candidate_selection.md`
- `docs/restructuring-roadmap/74_epic10d_review_reject_shadow.md`
- `docs/restructuring-roadmap/75_epic10d_gate_review.md`
- `artifacts/document_hard_gate_validation_10d/20260327_141956/runtime_summary.json`
- `artifacts/document_hard_gate_validation_10d/20260327_141956/validation_cases.json`
- `artifacts/document_hard_gate_validation_10d/20260327_141956/final_report.md`
- `artifacts/document_hard_gate_review_10d/20260327_144154/review_summary.json`
- `artifacts/document_hard_gate_review_10d/20260327_144154/review_findings.md`
- `web/app/domains/revisor/service_messaging.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/app/v2/document/hard_gate.py`
- `web/tests/test_v2_document_hard_gate_10d.py`

## Leitura semantica formal

### 1. `review_reject` e um caminho corretivo da mesa

No fluxo atual, rejeitar:

- exige ou normaliza motivo
- marca o laudo como `REJEITADO`
- grava `motivo_rejeicao`
- grava `reabertura_pendente_em`
- notifica o inspetor com `Corrija e reenvie`

Isso caracteriza uma devolucao para ajuste, nao uma mutacao documental de emissao, publicacao ou finalizacao.

### 2. Bloquear rejeicao pode prender o caso no estado errado

Se a mesa identifica problema e precisa devolver o caso, bloquear `review_reject` por readiness documental produziria o efeito errado:

- o caso ficaria sem aprovacao
- o caso tambem ficaria sem devolucao corretiva
- a mesa perderia o caminho normal de saneamento do trabalho

Portanto, existe risco operacional real em transformar rejeicao em alvo de `enforce` documental sem semantica propria.

### 3. Os blockers observados no 10D pertencem a outro dominio

Blockers observados:

- `template_not_bound`
- `template_source_unknown`
- `issue_disallowed_by_policy`
- `review_requirement_not_satisfied`
- `engineer_approval_requirement_not_satisfied`
- `engineer_approval_pending`
- `review_still_required_for_issue`

Leitura:

- eles descrevem readiness de emissao, issue, aprovacao e proveniencia documental
- eles nao descrevem quando a mesa deveria ser proibida de rejeitar

Logo, reaproveitar esses blockers como `enforce` em `review_reject` seria misturar semanticas.

### 4. Blockers proprios de rejeicao, se existirem, pertencem a outra camada

Exemplos hipoteticos semanticamente coerentes:

- `rejection_reason_missing`
- `actor_not_allowed_to_reject`
- `invalid_transition_to_rejected`
- `review_context_missing`

Mas esses exemplos sao:

- validacao de negocio
- autorizacao
- maquina de estados da revisao
- integridade do contexto da mesa

Eles nao sao blockers do hard gate documental atual. Parte dessas protecoes ja existe hoje no proprio fluxo de revisao.

## Classificacao dos blockers do 10D

- apropriados apenas para observacao:
  - `template_not_bound`
  - `template_source_unknown`
  - `issue_disallowed_by_policy`
- potencialmente validos para rejeicao futura:
  - nenhum
- inadequados para rejeicao:
  - `review_requirement_not_satisfied`
  - `engineer_approval_requirement_not_satisfied`
  - `engineer_approval_pending`
  - `review_still_required_for_issue`

## Decisao formal

- `deprecate_review_reject_as_enforce_candidate`

Rationale:

- `review_reject` e um caminho corretivo de devolucao para ajuste
- blockers atuais de emissao/aprovacao sao inadequados para barrar esse caminho
- possiveis regras proprias de rejeicao pertencem a revisao/negocio, nao ao hard gate documental

## O que essa decisao significa na pratica

- `review_reject` pode continuar em `shadow_only` como telemetria local/controlada
- `review_reject` nao deve seguir na trilha de futuros `enforce candidates` do hard gate documental
- qualquer endurecimento futuro deve mirar pontos com semantica documental mais forte

## Impacto no roadmap

Depois do 10E, a trilha de endurecimento documental deve priorizar:

- emitir
- publicar
- finalizar
- outra mutacao documental irreversivel ou externamente observavel

E deve reduzir prioridade ou excluir da trilha de `enforce` pontos corretivos como:

- `review_reject`
- `report_reopen`

## Validacoes rerodadas nesta fase

- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10d.py` -> `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`
- `python3 -m py_compile web/app/domains/revisor/mesa_api.py web/app/v2/document/hard_gate.py web/tests/test_v2_document_hard_gate_10d.py` -> `ok`

## Rollback

Nao houve mudanca de codigo de produto.

Rollback desta fase:

- descartar apenas os artifacts e docs do 10E, se necessario

## Artefatos desta fase

- `artifacts/document_review_reject_semantics/20260327_150443/semantics_review_summary.json`
- `artifacts/document_review_reject_semantics/20260327_150443/semantics_findings.md`
- `artifacts/document_review_reject_semantics/20260327_150443/blockers_classification.txt`
- `artifacts/document_review_reject_semantics/20260327_150443/decision.txt`

## Proximo passo recomendado

Selecionar formalmente o proximo ponto mutavel documental com semantica forte de governanca documental para a trilha de endurecimento, deixando `review_reject` apenas como telemetria shadow.
