# Epic 10B - Primeiro hard gate documental controlado

## Objetivo

Implementar o primeiro hard gate documental real do V2 de forma extremamente restrita, reversível e segura:

- um único ponto mutável real
- shadow e enforce separados
- enforcement apenas em tenant allowlisted e contexto local
- rollback imediato por flag
- sem tocar em tenant real
- sem alterar payloads públicos fora da operação controlada

## Ponto mutável escolhido

- `web/app/domains/chat/laudo_service.py::finalizar_relatorio_resposta`
- rota consumidora principal:
  - `/app/api/laudo/{laudo_id}/finalizar`

### Por que este ponto foi escolhido

Foi escolhido exatamente este ponto, e não a aprovação final da mesa, porque:

- já existe lógica centralizada de transição mutável
- já existe um gate anterior de segurança (`gate_qualidade`)
- a operação move `RASCUNHO -> AGUARDANDO`, sem emitir documento final nem liberar ART
- o blast radius é menor do que bloquear aprovação final da mesa
- ele casa melhor com blockers de materialização do soft gate

Em termos canônicos, este é o menor ponto mutável útil para o primeiro enforcement documental.

## Flags da fase

- `TARIEL_V2_DOCUMENT_HARD_GATE`
- `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE`
- `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS`
- `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`

### Semântica

- nenhuma flag:
  - nada muda
- `TARIEL_V2_DOCUMENT_HARD_GATE=1`:
  - o hard gate calcula decisão real, mas fica em `shadow_only` por padrão
- `TARIEL_V2_DOCUMENT_HARD_GATE=1` + `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`:
  - o sistema ainda só bloqueia se:
    - o host for local/controlado
    - o tenant estiver em `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS`
    - a operação estiver em `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`

Operação usada nesta fase:

- `report_finalize`

## Modelos canônicos implementados

Arquivos:

- `web/app/v2/document/hard_gate_models.py`
- `web/app/v2/document/hard_gate.py`
- `web/app/v2/document/hard_gate_metrics.py`

Estruturas:

- `DocumentHardGateBlockerV1`
- `DocumentHardGateDecisionV1`
- `DocumentHardGateEnforcementResultV1`
- `DocumentHardGateSummaryV1`

Campos materializados:

- `tenant_id`
- `case_id`
- `legacy_laudo_id`
- `document_id`
- `operation_kind`
- `hard_gate_enabled`
- `enforce_requested`
- `enforce_enabled`
- `would_block`
- `did_block`
- `blockers`
- `decision_source`
- `policy_summary`
- `document_readiness`
- `provenance_summary`
- `request_id`
- `correlation_id`
- `timestamp`

## Como o hard gate é calculado

O hard gate não cria lógica paralela nova. Ele parte diretamente do soft gate e usa:

- `TechnicalCaseStatusSnapshot`
- `CanonicalDocumentFacadeV1`
- `DocumentSoftGateTraceV1`
- blockers canônicos já derivados no 10A

### Blockers reaproveitados

Para `report_finalize`, o hard gate usa apenas blockers do soft gate que impactam materialização:

- `no_active_report`
- `template_not_bound`
- `template_source_unknown`
- `materialization_disallowed_by_policy`

Blockers apenas de emissão, como:

- `issue_disallowed_by_policy`
- `review_requirement_not_satisfied`
- `engineer_approval_requirement_not_satisfied`
- `document_source_insufficient`

continuam observáveis, mas não são usados para barrar `finalizar_relatorio_resposta`.

Isso evita bloquear prematuramente uma etapa que ainda não é emissão final.

## Modo shadow + enforce

### Shadow

Quando só `TARIEL_V2_DOCUMENT_HARD_GATE=1` está ligado:

- a decisão é calculada
- `would_block` é contabilizado
- a operação segue normalmente
- a resposta pública continua igual

### Enforce controlado

O bloqueio real só acontece quando todas as condições abaixo são verdadeiras:

1. `TARIEL_V2_DOCUMENT_HARD_GATE=1`
2. `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
3. host local/controlado
4. tenant em `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS`
5. operação em `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
6. existem blockers canônicos relevantes para a operação

Se qualquer condição falhar:

- o modo volta para `shadow_only`
- não há bloqueio real

## Resposta de bloqueio

Quando `report_finalize` é bloqueado em `enforce_controlled`, a rota responde com `422` e payload coerente com o padrão atual de gates:

- `codigo=DOCUMENT_HARD_GATE_BLOCKED`
- `permitido=false`
- `operacao=report_finalize`
- `modo=enforce_controlled`
- `mensagem`
- `blockers`

O laudo permanece em `RASCUNHO`.

## Observabilidade operacional

Endpoint novo:

- `GET /admin/api/document-hard-gate/summary`

Proteção:

- admin only
- local only
- `404` quando o hard gate está desligado

Contadores expostos:

- `evaluations`
- `would_block`
- `did_block`
- `shadow_only`
- `enforce_controlled`
- `disabled`
- agregação por operação
- agregação por blocker
- agregação por tenant
- últimos resultados recentes

Também fica disponível em request state:

- `request.state.v2_document_hard_gate_decision`
- `request.state.v2_document_hard_gate_enforcement`

## Rollback

Rollback imediato:

- desligar `TARIEL_V2_DOCUMENT_HARD_GATE`

Rollback de enforcement mantendo shadow:

- manter `TARIEL_V2_DOCUMENT_HARD_GATE=1`
- desligar `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE`

Rollback por escopo:

- remover tenant da allowlist
- remover `report_finalize` da allowlist de operações

## O que não mudou nesta fase

- nenhum tenant real entra em enforcement
- a aprovação final da mesa não foi bloqueada
- nenhum payload público fora da finalização controlada mudou
- nenhum pipeline documental legado foi substituído
- nenhum código Android foi alterado

## Validação executada

- `python3 -m py_compile web/app/v2/runtime.py web/app/v2/document/__init__.py web/app/v2/document/hard_gate_models.py web/app/v2/document/hard_gate.py web/app/v2/document/hard_gate_metrics.py web/app/domains/chat/laudo_service.py web/app/domains/chat/laudo.py web/app/domains/admin/routes.py web/tests/test_v2_document_hard_gate.py web/tests/test_v2_document_hard_gate_enforce.py web/tests/test_v2_document_hard_gate_summary.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_integration.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_summary.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_enforce.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_summary.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`

## O que ainda falta antes de ampliar o hard gate

- decidir se o próximo enforcement entra em aprovação final da mesa
- materializar política por tenant/template menos baseline
- manter histórico mais persistente se o hard gate sair do contexto local controlado
- validar uma trilha operacional antes de qualquer ampliação para além do tenant demo
