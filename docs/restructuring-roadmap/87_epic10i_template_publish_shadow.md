# Epic 10I - abertura controlada de `template_publish_activate` em `shadow_only`

## Objetivo

Abrir o ponto mutável documental `template_publish_activate` no domínio de templates do revisor apenas em `shadow_only`, sem bloquear a publicação real e sem alterar contrato público.

## Escopo aberto

- rotas cobertas:
  - `POST /revisao/api/templates-laudo/{template_id}/publicar`
  - `POST /revisao/api/templates-laudo/editor/{template_id}/publicar`
- `operation_kind`:
  - `template_publish_activate`
- semântica:
  - `publicar`
- modo:
  - `shadow_only`

## Implementação realizada

### Isolamento do slice

- o recorte foi isolado em:
  - [template_publish_shadow.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/app/domains/revisor/template_publish_shadow.py)
- a rota pública continuou intacta em:
  - [templates_laudo_management_routes.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/app/domains/revisor/templates_laudo_management_routes.py)
- as duas rotas de publicação agora delegam a mesma implementação interna `_publicar_template_laudo_impl(...)`, que:
  - calcula o shadow scope;
  - avalia a decisão documental canônica;
  - registra `request.state`;
  - persiste evidência durável local-only;
  - preserva a publicação real do template e a resposta JSON já existente.

### Integração com o hard gate

- `operation_kind` novo registrado em:
  - [gate_models.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/app/v2/document/gate_models.py)
- `template_publish_activate` ficou explicitamente marcado como `shadow_only` em:
  - [hard_gate.py](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/app/v2/document/hard_gate.py)
- o hard gate deste ponto considera apenas blockers de template na fase de abertura.

### Blockers observados na abertura

- `template_not_bound`
- `template_source_unknown`

Racional:

- quando nao havia template ativo anterior para o mesmo código, o recorte registrou um gap operacional de binding/template source;
- quando ja havia uma versao ativa do mesmo código, o recorte passou sem blockers.

### Flags e recorte controlado

- o slice so observa quando todos os filtros abaixo estao satisfeitos:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - host local/controlado
  - tenant em `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS`
  - operação `template_publish_activate` em `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
  - opcionalmente, código do template em `TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES`

## Observabilidade adicionada

- summary operacional do hard gate passa a agregar `template_publish_activate`
- a trilha durável local-only registra:
  - `tenant_id`
  - `operation_kind`
  - `route_name`
  - `route_path`
  - `template_id`
  - `codigo_template`
  - `versao`
  - `modo_editor`
  - `blockers`
  - `would_block`
  - `did_block`
  - `audit_record_id`
  - `audit_generated`
- a auditoria de templates continuou sendo produzida em `RegistroAuditoriaEmpresa` e exposta em `GET /revisao/api/templates-laudo/auditoria`

## Validação executada

### Testes

- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate.py` -> `3 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_enforce.py` -> `4 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10d.py` -> `3 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10f.py` -> `3 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10g.py` -> `2 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10i.py` -> `3 passed`
- `AMBIENTE=dev PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`

### Boot/import e rodada operacional

- boot/import:
  - `AMBIENTE=dev python3 -c "import sys; sys.path.insert(0, 'web'); import main; main.create_app(); print('boot_import_ok')"` -> `boot_import_ok`
- runner local:
  - `AMBIENTE=dev PYTHONPATH=web python3 scripts/run_document_hard_gate_10i_validation.py`
- artifacts principais:
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/runtime_summary.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/durable_summary.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/validation_cases.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/final_report.md`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/responses/admin_summary_response.json`
  - `artifacts/document_hard_gate_validation_10i/20260327_233048/responses/admin_durable_summary_response.json`

### Resultado da rodada controlada

- casos úteis:
  - `template_publish_gap_shadow`
  - `template_publish_ok_shadow`
- resultados:
  - `2` avaliações
  - `2` respostas HTTP equivalentes a sucesso funcional
  - `1` caso com `would_block=true`
  - `0` casos com `did_block=true`
  - `2` casos com `shadow_only=true`
  - `2` auditorias operacionais geradas

## Rollback

- desligar completamente:
  - remover `template_publish_activate` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
  - ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`
- desligar apenas a trilha durável:
  - desligar `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE`
  - ou remover `TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR`
- opcionalmente restringir ainda mais o recorte:
  - usar `TARIEL_V2_DOCUMENT_HARD_GATE_TEMPLATE_CODES`

## O que ainda falta antes de qualquer discussão futura de enforce

- ampliar a amostra operacional do novo ponto em campanha dedicada
- confirmar estabilidade dos blockers de template em mais de um harness
- provar se existe uma família própria de blockers de governança de template além de `template_not_bound` e `template_source_unknown`
- decidir se esse ponto admite `future_controlled_enforce` sem misturar blockers case-level que pertencem a emissão/finalização de laudo

## Conclusão

`template_publish_activate` foi aberto de verdade em `shadow_only`, com integração real nas duas rotas de publicação, sem bloquear a publicação funcional do template. A decisão documental agora fica visível no summary local e na trilha durável, enquanto `did_block` permanece `false` em todos os casos desta fase.
