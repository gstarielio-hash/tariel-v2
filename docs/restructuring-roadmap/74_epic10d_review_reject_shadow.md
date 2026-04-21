# Epic 10D - abertura de `review_reject` em `shadow_only`

## Objetivo

Abrir o ponto mutavel documental `review_reject` no hard gate do V2 de forma:

- aditiva
- reversivel
- local/controlada
- restrita a tenant allowlisted e operation allowlisted
- sem bloquear a rejeicao real
- sem mudar payload publico

## Escopo implementado

O ponto aberto foi:

- rota:
  - `POST /revisao/api/laudo/{laudo_id}/avaliar`
- recorte:
  - `acao=rejeitar`
- integracao real:
  - `web/app/domains/revisor/mesa_api.py::avaliar_laudo`
  - `web/app/domains/revisor/mesa_api.py::_avaliar_gate_documental_decisao_revisor`
  - `web/app/domains/revisor/service_messaging.py::avaliar_laudo_revisor`
- `operation_kind` aberto:
  - `review_reject`

## Como o 10D ficou contido

- `review_reject` entra no hard gate apenas quando todos os criterios abaixo forem verdadeiros:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - host local/controlado
    - `127.0.0.1`
    - `::1`
    - `localhost`
    - `testclient`
  - tenant allowlisted
  - operation allowlisted com `review_reject`
- fora desse recorte, a instrumentacao do novo ponto nao roda
- dentro do recorte, a decisao e calculada, registrada em `request.state` e enviada ao summary operacional

## Invariantes de `shadow_only`

- `review_reject` foi adicionado ao contrato de `operation_kind`
- os blockers relevantes sao os mesmos blockers documentais de materializacao/emissao usados para leitura do caso da mesa
- para `review_reject`, todos os blockers ficam em:
  - `shadow_only`
- para `review_reject`, o hard gate agora calcula:
  - `would_block=true` quando houver blockers relevantes
  - `did_block=false` sempre nesta fase
- mesmo com `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`, `review_reject` nao entra em `enforce_controlled`

## Blockers observados na validacao real

Blockers vistos de fato em `artifacts/document_hard_gate_validation_10d/20260327_141956/`:

- em ambos os casos:
  - `engineer_approval_pending`
  - `engineer_approval_requirement_not_satisfied`
  - `issue_disallowed_by_policy`
  - `review_requirement_not_satisfied`
  - `review_still_required_for_issue`
- no caso sem template ativo compativel:
  - `template_not_bound`
  - `template_source_unknown`

Blockers recomendados pela selecao que continuam apenas observaveis e nao foram promovidos nesta fase:

- `no_active_report`
- `materialization_disallowed_by_policy`
- `provenance_summary_unavailable`
- `document_source_insufficient`

## Validacao operacional executada

Base de validacao:

- tenant allowlisted:
  - `2`
  - `Tariel.ia Lab Carga Local`
- operation allowlisted:
  - `review_reject`
- host:
  - `127.0.0.1`
- banco:
  - SQLite temporario controlado em `artifacts/document_hard_gate_validation_10d/20260327_141956/validation_10d.db`

Casos executados por HTTP real:

- `shadow_review_reject_with_template_gap`
  - HTTP `200`
  - resposta publica mantida
  - laudo persistido em `Rejeitado`
  - summary registrou `review_reject` com `would_block=true` e `did_block=false`
- `shadow_review_reject_with_reduced_blockers`
  - HTTP `200`
  - resposta publica mantida
  - laudo persistido em `Rejeitado`
  - summary registrou `review_reject` com blockers apenas em `shadow_only`

Artefatos principais:

- `artifacts/document_hard_gate_validation_10d/20260327_141956/runtime_summary.json`
- `artifacts/document_hard_gate_validation_10d/20260327_141956/validation_cases.json`
- `artifacts/document_hard_gate_validation_10d/20260327_141956/final_report.md`

## Rollback rapido

- remover `review_reject` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
- ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`

Nao ha migracao de banco nova nem alteracao de payload publico para desfazer.

## O que ainda falta antes de qualquer enforce

- prova operacional dedicada para qualquer blocker que um dia tente bloquear `review_reject`
- criterio semantico claro de quais blockers poderiam bloquear um caminho corretivo sem prejudicar a mesa
- reconciliar ou isolar o bypass de `finalizarlaudoagora` em `web/app/domains/chat/chat_stream_routes.py`
- manter observabilidade por artifacts enquanto o summary seguir volatil em memoria
