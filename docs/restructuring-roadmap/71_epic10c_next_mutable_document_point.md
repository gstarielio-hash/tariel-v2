# Epic 10C - abertura condicionada do próximo ponto mutável documental

## Objetivo

Abrir exatamente um novo ponto mutável documental do V2 em recorte local/controlado, mantendo:

- tenant allowlisted
- operação allowlisted
- `shadow_only` e `enforce_controlled`
- rollback simples
- artefatos por execução
- check de boot/import preservado
- blockers sensíveis ainda só em shadow

## Ponto mutável escolhido

- rota:
  - `POST /revisao/api/laudo/{laudo_id}/avaliar`
- recorte exato:
  - apenas `acao=aprovar`
- integração principal:
  - `web/app/domains/revisor/mesa_api.py::avaliar_laudo`

## Por que este foi o próximo melhor ponto após `/app/api/laudo/{laudo_id}/finalizar`

- é a próxima mutação documental real centralizada após o envio do laudo para a mesa
- continua sendo um único comando operacional claro dentro do fluxo legado
- o recorte ficou ainda mais controlado do que “abrir a rota toda”, porque só `aprovar` entrou no hard gate
- `rejeitar` ficou fora desta fase para evitar abrir um segundo ponto mutável
- a política e a facade documental já conseguem derivar contexto suficiente da mesa para essa decisão

## Por que ainda foi considerado seguro o suficiente

- o enforcement continua local/controlado e depende de allowlist de tenant e operação
- o ponto novo não abriu enforcement global nem para tenants reais
- só blockers já considerados seguros pelo gate review foram promovidos a bloqueio real
- blockers mais sensíveis de revisão/aprovação/provenance continuam observáveis, porém em `shadow_only`
- o rollback continua imediato desligando `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE` ou removendo a operação da allowlist

## Modelagem aplicada

## Operation kind novo

- `review_approve`

## Reaproveitamento dos modelos do 10B

Foram reaproveitados:

- `DocumentHardGateDecisionV1`
- `DocumentHardGateBlockerV1`
- `DocumentHardGateEnforcementResultV1`
- `DocumentHardGateSummaryV1`

Mudança mínima de shape:

- `DocumentHardGateBlockerV1` agora carrega:
  - `enforcement_scope`
  - `enforce_blocking`

Isso permitiu separar:

- blockers que realmente bloqueiam no recorte controlado
- blockers que continuam apenas como observabilidade em shadow

## Blockers em enforce

No novo ponto `review_approve`, continuam aptos a bloqueio real apenas:

- `template_not_bound`
- `template_source_unknown`
- `materialization_disallowed_by_policy`
- `no_active_report`

Na validação operacional desta fase, os blockers efetivamente observados em enforce foram:

- `template_not_bound`
- `template_source_unknown`

## Blockers apenas em shadow

No `review_approve`, estes blockers permanecem observáveis, porém não bloqueiam de verdade nesta fase:

- `issue_disallowed_by_policy`
- `review_requirement_not_satisfied`
- `engineer_approval_requirement_not_satisfied`
- `engineer_approval_pending`
- `review_still_required_for_issue`
- blockers correlatos de provenance/documento que não tenham trilha operacional suficiente

## Como foi integrado

- `web/app/domains/revisor/mesa_api.py` ganhou `_avaliar_gate_documental_aprovacao_revisor(...)`
- a rota `avaliar_laudo` passa a rodar esse caminho apenas quando `acao == "aprovar"`
- `request.state` materializa:
  - `v2_case_core_snapshot`
  - `v2_policy_decision_summary`
  - `v2_document_facade_summary`
  - `v2_document_soft_gate_decision`
  - `v2_document_soft_gate_trace`
  - `v2_document_hard_gate_decision`
  - `v2_document_hard_gate_enforcement`
- quando o hard gate está em `enforce_controlled` e há blocker em enforce:
  - a rota responde `422 DOCUMENT_HARD_GATE_BLOCKED`
- quando só existem blockers `shadow_only`:
  - a aprovação segue normalmente

## Observabilidade

O mesmo endpoint admin/local-only do 10B foi reaproveitado:

- `GET /admin/api/document-hard-gate/summary`

Ampliação entregue:

- `by_operation_kind` agora inclui `review_approve`
- `by_blocker_code` agora distingue:
  - `enforce`
  - `shadow_only`
  - `did_block`

Isso permite responder, no 10C:

- quantas avaliações ocorreram no novo ponto
- quantas vezes teria bloqueado
- quantas vezes bloqueou de verdade
- quais blockers apareceram
- quais blockers ficaram apenas em shadow

## Check de boot/import preservado

Antes da validação operacional foi mantido o check barato:

- `cd web && python3 -c "import main; app = main.create_app(); print('boot_import_ok')"`

Resultado real da execução:

- `boot_import_ok`

Isso reduz o risco de reintroduzir o ciclo de import detectado no 10B.

## Validação operacional real do 10C

Artefatos:

- `artifacts/document_hard_gate_validation_10c/20260327_104739/`

Tenant validado:

- `empresa_id=2`
- `Tariel.ia Lab Carga Local`

Credenciais normalizadas localmente antes da rodada:

- `web/scripts/seed_usuario_uso_intenso.py`

Motivo:

- garantir senha conhecida apenas para o tenant local/controlado, sem tocar em tenant real

### Shadow

- flags:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=0`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=2`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=review_approve`
- alvo:
  - `laudo_id=85`
- resultado:
  - `HTTP 200`
  - laudo foi para `Aprovado`
- summary:
  - `evaluations=1`
  - `would_block=1`
  - `did_block=0`
  - `shadow_only=1`

### Enforce bloqueado

- flags:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=2`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=review_approve`
- alvo:
  - `laudo_id=86`
- resultado:
  - `HTTP 422`
  - `codigo=DOCUMENT_HARD_GATE_BLOCKED`
  - `operacao=review_approve`
- blockers em enforce observados:
  - `template_not_bound`
  - `template_source_unknown`
- estado final:
  - laudo permaneceu em `Aguardando Aval`

### Enforce permitido com blockers só em shadow

- alvo:
  - `laudo_id=88`
- resultado:
  - `HTTP 200`
  - laudo foi para `Aprovado`
- prova relevante no summary:
  - `issue_disallowed_by_policy` com `shadow_only=2`
  - `review_requirement_not_satisfied` com `shadow_only=2`
  - `engineer_approval_requirement_not_satisfied` com `shadow_only=2`

Isso provou que blockers mais sensíveis continuaram observáveis, mas não foram promovidos imprudentemente a bloqueio real.

### Rollback

- rollback aplicado:
  - desligando apenas `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE`
- alvo:
  - `laudo_id=87`
- resultado:
  - `HTTP 200`
  - laudo foi para `Aprovado`
- summary:
  - `evaluations=1`
  - `would_block=1`
  - `did_block=0`
  - `shadow_only=1`

## Validações rodadas

- `python3 -m py_compile web/app/v2/document/gate_models.py web/app/v2/document/hard_gate_models.py web/app/v2/document/hard_gate.py web/app/v2/document/hard_gate_metrics.py web/app/domains/revisor/mesa_api.py web/tests/test_v2_document_hard_gate_10c.py`
- `cd web && python3 -c "import main; app = main.create_app(); print('boot_import_ok')"`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_integration.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_summary.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_enforce.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_summary.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10c.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`

## Rollback

Rollback imediato do 10C:

- desligar `TARIEL_V2_DOCUMENT_HARD_GATE`

Rollback para manter apenas shadow:

- manter `TARIEL_V2_DOCUMENT_HARD_GATE=1`
- desligar `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE`

Rollback por escopo:

- remover `review_approve` da `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
- remover o tenant da `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS`

## O que ainda falta antes de ampliar novamente

- decidir se o próximo recorte fica em rejeição controlada, aprovação final mais forte ou emissão, sem abrir dois pontos ao mesmo tempo
- provar operacionalmente se algum blocker adicional merece promoção de `shadow_only` para `enforce`
- manter a disciplina de artefatos por execução enquanto o summary continuar em memória
