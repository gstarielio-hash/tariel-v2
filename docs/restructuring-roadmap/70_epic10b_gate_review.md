# Epic 10B - Gate review formal antes do Epic 10C

## Objetivo

Executar uma revisao formal do Epic 10B com base em codigo atual, documentacao atual, artefatos reais e testes existentes, para decidir se o Epic 10C pode ser aberto.

## Escopo revisado

- implementacao do hard gate em `web/app/domains/chat/laudo_service.py::finalizar_relatorio_resposta`
- flags de shadow/enforce/allowlists em `web/app/v2/runtime.py`
- observabilidade em `web/app/v2/document/hard_gate_metrics.py` e `GET /admin/api/document-hard-gate/summary`
- artefatos operacionais mais recentes em `artifacts/document_hard_gate_validation/20260327_092450/`
- ajuste minimo de boot em `web/app/domains/chat/__init__.py`
- testes de soft gate, hard gate e smoke rerodados nesta fase

## Evidencias usadas

- `docs/restructuring-roadmap/68_epic10b_document_hard_gate.md`
- `docs/restructuring-roadmap/69_epic10b_hard_gate_validation.md`
- `docs/restructuring-roadmap/99_execution_journal.md`
- `artifacts/document_hard_gate_validation/20260327_092450/runtime_summary.json`
- `artifacts/document_hard_gate_validation/20260327_092450/summaries/hard_gate_summary_after_shadow.json`
- `artifacts/document_hard_gate_validation/20260327_092450/summaries/hard_gate_summary_after_enforce.json`
- `artifacts/document_hard_gate_validation/20260327_092450/summaries/hard_gate_summary_after_rollback.json`
- `artifacts/document_hard_gate_validation/20260327_092450/responses/enforce_blocked_response.json`
- `artifacts/document_hard_gate_validation/20260327_092450/state/precheck_target_discovery.json`
- `web/app/domains/revisor/service_messaging.py`

## Achados

### 1. O ponto mutavel escolhido segue sendo o menor recorte util de risco baixo

`POST /app/api/laudo/{laudo_id}/finalizar` foi uma escolha defensavel para o 10B porque:

- a mutacao e centralizada em `finalizar_relatorio_resposta`
- ja existe `gate_qualidade` antes da transicao
- a operacao so move o laudo para `Aguardando Aval`
- ela nao aprova o laudo nem libera a etapa final da mesa

O contraste com `web/app/domains/revisor/service_messaging.py`, que leva o laudo a `APROVADO` e registra notificacao final, confirma que o 10B ficou no ponto mutavel menos perigoso entre os caminhos realmente mutaveis analisados.

### 2. Shadow, enforce e rollback estao maduros para um proximo passo ainda restrito

O artefato `artifacts/document_hard_gate_validation/20260327_092450/runtime_summary.json` prova:

- `shadow_only` com `would_block=1` e `did_block=0`
- `enforce_controlled` com `422 DOCUMENT_HARD_GATE_BLOCKED`
- caso permitido em enforce com `HTTP 200`
- rollback imediato ao desligar apenas `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE`

Isso valida que o desenho de controle do 10B funciona como esperado no recorte local/controlado.

### 3. Os blockers atuais sao razoaveis, mas ainda nao completos para ampliacao sem condicoes

Blockers operacionalmente provados:

- `template_not_bound`
- `template_source_unknown`

Blocker com origem canonica boa para um proximo recorte restrito, embora sem prova operacional de bloqueio nesta fase:

- `materialization_disallowed_by_policy`

Blockers presentes no codigo, mas ainda sem prova operacional equivalente para enforcement:

- `issue_disallowed_by_policy`
- `review_requirement_not_satisfied`
- `engineer_approval_requirement_not_satisfied`
- `document_source_insufficient`

Conclusao: os blockers sao suficientes para o 10B e razoaveis para abrir o 10C somente se o 10C permanecer restrito e continuar prudente sobre quais sinais podem bloquear de verdade.

### 4. A observabilidade atual basta apenas com restricoes

Pontos fortes:

- `request.state.v2_document_hard_gate_decision`
- `request.state.v2_document_hard_gate_enforcement`
- `GET /admin/api/document-hard-gate/summary`
- artefatos por execucao da validacao operacional

Limitacoes:

- os contadores ficam em memoria
- restart zera a serie
- nao ha trilha historica persistente na aplicacao

Conclusao: a observabilidade atual e suficiente para abrir o 10C somente se ele continuar local/admin-only e com exportacao de artefatos por execucao.

### 5. O ajuste de import circular foi aceitavel, mas virou condicao de seguimento

O lazy-load em `web/app/domains/chat/__init__.py` foi uma correcao localizada e pragmatica:

- preservou o contrato publico do pacote
- destravou o boot real com `uvicorn`
- nao alterou payloads nem tenants

Ao mesmo tempo, ele revelou fragilidade nas fronteiras de import entre `app.v2.document` e `app.domains.chat`. Isso nao justifica segurar o 10C por si so, mas justifica manter um check barato de boot/import antes da proxima rodada operacional.

## Testes rerodados nesta revisao

- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate.py` -> `2 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_integration.py` -> `2 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_summary.py` -> `1 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate.py` -> `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_enforce.py` -> `4 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_summary.py` -> `1 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py` -> `26 passed`

## Decisao formal

- `approved_for_10c_with_conditions`

### Rationale curto

O 10B passou no gate minimo para seguir: ponto mutavel de baixo risco, enforcement comprovadamente restrito, rollback simples, caso bloqueado real, caso permitido real e testes rerodados sem regressao. O 10C, porem, deve continuar extremamente controlado porque a observabilidade ainda e em memoria e varios blockers mais sensiveis ainda nao foram provados em runtime como bloqueio real.

## Condicoes explicitas para abrir o 10C

- manter o 10C em um unico novo ponto mutavel
- manter rollout apenas local/controlado, com tenant allowlisted e operacao allowlisted
- nao promover blockers de revisao/aprovacao/provenance a bloqueio real sem uma trilha controlada no novo ponto
- continuar exportando summaries e responses por execucao
- preservar um check de boot/import antes da validacao operacional do 10C

## O que ainda nao deve acontecer

- qualquer enforcement fora do mesmo recorte local/controlado
- qualquer ampliacao para tenant real
- qualquer dependencia de observabilidade historica que o summary atual nao possui

## Artefatos desta revisao

- `artifacts/document_hard_gate_review/20260327_100250/review_summary.json`
- `artifacts/document_hard_gate_review/20260327_100250/review_findings.md`
- `artifacts/document_hard_gate_review/20260327_100250/source_artifacts_index.txt`
- `artifacts/document_hard_gate_review/20260327_100250/decision.txt`
