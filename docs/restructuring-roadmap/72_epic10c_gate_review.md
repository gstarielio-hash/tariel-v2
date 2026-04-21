# Gate review formal do Epic 10C antes de qualquer novo ponto mutável documental

## Objetivo

Executar uma revisão formal do Epic 10C com base em código atual, documentação atual, artefatos reais e testes existentes para decidir se algum novo ponto mutável documental pode ser aberto.

## Escopo revisado

- implementação do hard gate em:
  - `web/app/domains/chat/laudo_service.py::finalizar_relatorio_resposta`
  - `web/app/domains/revisor/mesa_api.py::avaliar_laudo` no recorte `acao=aprovar`
- modelos e runtime em:
  - `web/app/v2/document/hard_gate.py`
  - `web/app/v2/document/hard_gate_models.py`
  - `web/app/v2/document/hard_gate_metrics.py`
  - `web/app/v2/runtime.py`
- ajuste de boot/import em:
  - `web/app/domains/chat/__init__.py`
- artefatos operacionais mais recentes em:
  - `artifacts/document_hard_gate_validation_10c/20260327_104739/`
- testes de soft gate, hard gate, 10C e smoke rerodados nesta revisão

## Pré-checagem da revisão

- `pwd` confirmado em:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short` permanece muito amplo/sujo no repositório:
  - a revisão foi limitada ao recorte do hard gate documental e aos artefatos associados
- artefato operacional mais recente do 10C localizado em:
  - `artifacts/document_hard_gate_validation_10c/20260327_104739/`
- tenant validado no 10C:
  - `empresa_id=2`
  - `Tariel.ia Lab Carga Local`
- operação validada no 10C:
  - `POST /revisao/api/laudo/{laudo_id}/avaliar`
  - apenas `acao=aprovar`
- flags usadas no 10C:
  - `TARIEL_V2_DOCUMENT_HARD_GATE`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`

## Evidências usadas

- `docs/restructuring-roadmap/67_epic10a_document_soft_gate.md`
- `docs/restructuring-roadmap/68_epic10b_document_hard_gate.md`
- `docs/restructuring-roadmap/69_epic10b_hard_gate_validation.md`
- `docs/restructuring-roadmap/70_epic10b_gate_review.md`
- `docs/restructuring-roadmap/71_epic10c_next_mutable_document_point.md`
- `docs/restructuring-roadmap/99_execution_journal.md`
- `artifacts/document_hard_gate_validation_10c/20260327_104739/runtime_summary.json`
- `artifacts/document_hard_gate_validation_10c/20260327_104739/final_report.md`
- `artifacts/document_hard_gate_validation_10c/20260327_104739/state/precheck_target_discovery.json`
- `artifacts/document_hard_gate_validation_10c/20260327_104739/responses/enforce_blocked_review_approve_response.json`
- `artifacts/document_hard_gate_validation_10c/20260327_104739/summaries/hard_gate_summary_after_shadow.json`
- `artifacts/document_hard_gate_validation_10c/20260327_104739/summaries/hard_gate_summary_after_enforce.json`
- `artifacts/document_hard_gate_validation_10c/20260327_104739/summaries/hard_gate_summary_after_rollback.json`
- `web/app/domains/revisor/mesa_api.py`
- `web/app/domains/revisor/service_messaging.py`
- `web/app/domains/chat/__init__.py`

## Achados principais

### 1. O 10C realmente manteve um único novo ponto mutável, mas o risco agora é moderado

Busca no código do hard gate mostra apenas duas integrações mutáveis reais:

- `report_finalize` em `web/app/domains/chat/laudo_service.py`
- `review_approve` em `web/app/domains/revisor/mesa_api.py`

Logo, o 10C não abriu múltiplos pontos ao mesmo tempo. Ainda assim, o ponto novo é mais sensível do que o 10B porque:

- ele muda o laudo para `APROVADO`
- registra a decisão da mesa
- dispara notificação final ao inspetor

Conclusão:

- o recorte segue seguro o bastante para um slice controlado
- a avaliação do ponto mutável sobe de `baixo_risco` para `risco_moderado`

### 2. A separação entre blockers em enforce e em shadow foi aplicada corretamente

O summary depois do enforce e a resposta `422` provam:

- blockers realmente usados no bloqueio:
  - `template_not_bound`
  - `template_source_unknown`
- blockers mais sensíveis continuaram apenas em `shadow_only`:
  - `issue_disallowed_by_policy`
  - `review_requirement_not_satisfied`
  - `engineer_approval_requirement_not_satisfied`
  - `engineer_approval_pending`
  - `review_still_required_for_issue`

Isso foi coerente com as condições do gate review do 10B e evitou ampliar enforcement sem trilha suficiente.

Limite ainda aberto:

- `materialization_disallowed_by_policy`
- `no_active_report`

continuam no conjunto de `enforce` do `review_approve`, mas ainda sem prova operacional equivalente a `template_not_bound` e `template_source_unknown` no runtime do 10C.

Conclusão:

- blockers em enforce estão adequados para o 10C
- blockers em shadow foram corretamente mantidos fora do bloqueio real
- a maturidade geral dos blockers continua `razoavel`, não `forte`

### 3. A observabilidade atual basta apenas com restrições

Pontos fortes confirmados:

- summary admin/local-only por `operation_kind`, `blocker_code` e `tenant`
- `recent_results` com payload de decisão
- artefatos before/after por execução com request, response e summary

Limitações confirmadas:

- contadores continuam em memória
- restart zera a série
- a trilha histórica depende dos artefatos exportados por execução

Conclusão:

- a observabilidade atual é `suficiente_com_restricoes`
- ela basta para abrir o próximo ponto apenas se o rollout continuar local/controlado e com artefatos disciplinados por execução

### 4. O rollback continua simples

O 10C repetiu o padrão esperado:

- shadow:
  - `would_block=1`
  - `did_block=0`
- enforce:
  - `did_block=1`
- rollback:
  - desligando apenas `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE`
  - o mesmo perfil de alvo voltou a responder `HTTP 200`

Conclusão:

- o rollback permanece `simples`

### 5. O recorte local/controlado continua sem evidência de bleed para tenants reais

As barreiras efetivamente ativas continuam sendo:

- host local/controlado
- tenant allowlisted
- operation allowlisted
- validação operacional feita em `empresa_id=2`

Esta revisão não encontrou evidência de enforcement atingindo tenant real ou operação fora da allowlist.

### 6. O ajuste de boot/import continua aceitável, mas segue como condição de avanço

O lazy-load em `web/app/domains/chat/__init__.py` continua:

- localizado
- compatível com o contrato público do pacote
- suficiente para manter o boot real funcionando

O check barato de revisão foi rerodado:

- `cd web && python3 -c "import main; app = main.create_app(); print('boot_import_ok')"` -> `boot_import_ok`

Conclusão:

- a correção continua aceitável
- ela ainda justifica manter check de boot/import antes de qualquer nova rodada operacional

## Testes rerodados nesta revisão

- `cd web && python3 -c "import main; app = main.create_app(); print('boot_import_ok')"` -> `boot_import_ok`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate.py` -> `2 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_integration.py` -> `2 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_summary.py` -> `1 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate.py` -> `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_enforce.py` -> `4 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_summary.py` -> `1 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10c.py` -> `5 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`

Observação:

- `py_compile` não foi rerodado nesta revisão porque nenhuma alteração nova em código Python de produto foi feita nesta fase; a integridade atual foi confirmada por boot/import e pela bateria de testes acima

## Decisão formal

- `approved_with_conditions`

### Rationale curto

O 10C provou que o segundo ponto mutável controlado continua disciplinado, com enforcement restrito, rollback simples e sem bleed para tenant real. O próximo ponto, porém, só pode abrir se permanecer igualmente controlado, porque:

- o risco do ponto atual já é moderado
- a observabilidade continua em memória
- blockers mais sensíveis ainda não têm trilha suficiente para enforcement

## Condições explícitas para o próximo ponto mutável

- abrir no máximo um novo ponto mutável
- manter host local/controlado, tenant allowlisted e operation allowlisted
- não promover blockers hoje em `shadow_only` para `enforce` sem prova operacional dedicada no próprio novo ponto
- manter check barato de boot/import antes da validação operacional
- continuar exportando summaries, requests e responses por execução
- se o próximo candidato tiver blast radius maior que `review_approve`, começar em `shadow_only` antes de qualquer `enforce`

## O que ainda não deve acontecer

- qualquer ampliação para tenant real
- qualquer enforcement global
- abertura simultânea de múltiplos pontos mutáveis
- promoção de blockers sensíveis por conveniência, sem evidência operacional

## Artefatos desta revisão

- `artifacts/document_hard_gate_review_10c/20260327_115916/review_summary.json`
- `artifacts/document_hard_gate_review_10c/20260327_115916/review_findings.md`
- `artifacts/document_hard_gate_review_10c/20260327_115916/source_artifacts_index.txt`
- `artifacts/document_hard_gate_review_10c/20260327_115916/decision.txt`
