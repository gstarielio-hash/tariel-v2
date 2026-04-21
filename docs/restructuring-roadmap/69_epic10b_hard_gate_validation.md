# Epic 10B - Validacao operacional do primeiro hard gate documental controlado

## Objetivo

Validar operacionalmente o hard gate documental do Epic 10B, em ambiente local/controlado, cobrindo:

- `shadow_only`
- `enforce_controlled`
- rollback imediato
- summary admin/local-only antes e depois de cada fase
- um caso com blocker real
- um caso permitido em enforce

Sem tocar em tenant real, sem mudar payload publico global e sem ampliar o escopo do enforcement.

## Precheck da execucao

- workspace:
  - `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`
- backend local:
  - nao havia processo escutando em `127.0.0.1:8000` no inicio
- flags do hard gate no ambiente base:
  - ausentes no shell antes da validacao
- summary admin/local:
  - acessado via `GET /admin/api/document-hard-gate/summary`
- operacao validada:
  - `POST /app/api/laudo/{laudo_id}/finalizar`

## Tenant e alvo escolhidos

### Tenant validado

- `empresa_id=2`
- `Tariel.ia Lab Carga Local`

### Motivo da escolha

- tenant explicitamente local/controlado
- sem bloqueio operacional
- com usuarios seed proprios
- sem templates ativos existentes, o que permitiu montar um caso com blocker real sem tocar no demo principal

### Usuario operacional usado

- `stress.inspetor@tariel.local`

### Usuario admin usado para summary

- `admin-legado@tariel.ia`

## Ajuste minimo necessario para destravar o runtime

Durante a pre-checagem, o backend nao subiu com `uvicorn` por um ciclo de import:

- `app.v2.document.__init__`
- `app.v2.document.template_binding`
- `app.domains.chat.normalization`
- `app.domains.chat.__init__`
- `app.domains.chat.auth_mobile_support`
- `app.v2.document`

Foi aplicado ajuste minimo em:

- `web/app/domains/chat/__init__.py`

Mudanca feita:

- exports do pacote `app.domains.chat` passaram a ser lazy-loaded via `__getattr__`

Efeito:

- o backend local voltou a subir em runtime real
- o contrato publico do pacote foi preservado
- nenhum payload/UX/tenant real foi alterado

## Alvos criados para a validacao

Artefato:

- `artifacts/document_hard_gate_validation/20260327_092450/state/targets_created.json`

Alvos:

- `laudo_id=81`
  - `shadow_blocked`
  - tenant 2
  - `tipo_template=avcb`
  - sem template ativo vinculado
- `laudo_id=82`
  - `enforce_blocked`
  - tenant 2
  - `tipo_template=avcb`
  - sem template ativo vinculado
- `laudo_id=83`
  - `rollback_blocked`
  - tenant 2
  - `tipo_template=avcb`
  - sem template ativo vinculado
- `laudo_id=84`
  - `enforce_allowed`
  - tenant 2
  - `tipo_template=padrao`
  - template temporario ativo criado apenas para validacao

Todos os alvos passaram no `gate_qualidade` antes da validacao real.

## Flags usadas por fase

### Shadow

- `TARIEL_V2_DOCUMENT_HARD_GATE=1`
- `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=0`
- `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=2`
- `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=report_finalize`

### Enforce

- `TARIEL_V2_DOCUMENT_HARD_GATE=1`
- `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
- `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=2`
- `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=report_finalize`

### Rollback

- rollback validado desligando apenas o `enforce`
- o hard gate permaneceu ligado em `shadow_only`

## Resultado da validacao shadow

Artefatos principais:

- `artifacts/document_hard_gate_validation/20260327_092450/summaries/hard_gate_summary_before_shadow.json`
- `artifacts/document_hard_gate_validation/20260327_092450/responses/shadow_finalize_response.json`
- `artifacts/document_hard_gate_validation/20260327_092450/summaries/hard_gate_summary_after_shadow.json`

Execucao:

- alvo usado:
  - `laudo_id=81`
- response:
  - `HTTP 200`
- efeito:
  - laudo avancou para `Aguardando Aval`

Summary:

- antes:
  - `evaluations=0`
  - `would_block=0`
  - `did_block=0`
- depois:
  - `evaluations=1`
  - `would_block=1`
  - `did_block=0`
  - `shadow_only=1`

Conclusao:

- o hard gate calculou decisao canônica real
- o summary refletiu `would_block=true`
- o modo shadow nao bloqueou o fluxo

## Resultado da validacao enforce

Artefatos principais:

- `artifacts/document_hard_gate_validation/20260327_092450/summaries/hard_gate_summary_before_enforce.json`
- `artifacts/document_hard_gate_validation/20260327_092450/responses/enforce_blocked_response.json`
- `artifacts/document_hard_gate_validation/20260327_092450/responses/enforce_allowed_response.json`
- `artifacts/document_hard_gate_validation/20260327_092450/summaries/hard_gate_summary_after_enforce.json`

### Caso bloqueado

- alvo usado:
  - `laudo_id=82`
- response:
  - `HTTP 422`
- payload:
  - `codigo=DOCUMENT_HARD_GATE_BLOCKED`
  - `operacao=report_finalize`
  - `modo=enforce_controlled`

Blockers reais observados:

- `template_not_bound`
- `template_source_unknown`

Estado final:

- laudo permaneceu em `Rascunho`

### Caso permitido

- alvo usado:
  - `laudo_id=84`
- response:
  - `HTTP 200`
- efeito:
  - laudo avancou para `Aguardando Aval`

### Summary

- antes:
  - `evaluations=0`
  - `would_block=0`
  - `did_block=0`
- depois:
  - `evaluations=2`
  - `would_block=1`
  - `would_allow=1`
  - `did_block=1`
  - `did_allow=1`
  - `enforce_controlled=2`

Conclusao:

- o enforce bloqueou de verdade quando havia blockers canonicos relevantes
- o enforce nao virou bloqueio global: o caso elegivel passou normalmente

## Resultado da validacao do rollback

Artefatos principais:

- `artifacts/document_hard_gate_validation/20260327_092450/summaries/hard_gate_summary_before_rollback.json`
- `artifacts/document_hard_gate_validation/20260327_092450/responses/rollback_finalize_response.json`
- `artifacts/document_hard_gate_validation/20260327_092450/summaries/hard_gate_summary_after_rollback.json`

Execucao:

- rollback aplicado:
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=0`
- alvo usado:
  - `laudo_id=83`
- response:
  - `HTTP 200`
- efeito:
  - laudo avancou para `Aguardando Aval`

Summary:

- antes:
  - `evaluations=0`
  - `would_block=0`
  - `did_block=0`
- depois:
  - `evaluations=1`
  - `would_block=1`
  - `did_block=0`
  - `shadow_only=1`

Conclusao:

- o rollback voltou imediatamente ao comportamento anterior
- o summary refletiu corretamente a reversao de `enforce_controlled` para `shadow_only`

## Observabilidade consultada

- `GET /admin/api/document-hard-gate/summary`
- `artifacts/document_hard_gate_validation/20260327_092450/runtime_summary.json`
- `artifacts/document_hard_gate_validation/20260327_092450/final_report.md`

Arquivos uteis adicionais:

- requests:
  - `artifacts/document_hard_gate_validation/20260327_092450/requests/`
- responses:
  - `artifacts/document_hard_gate_validation/20260327_092450/responses/`
- estado dos alvos:
  - `artifacts/document_hard_gate_validation/20260327_092450/state/`
- logs de backend:
  - `artifacts/document_hard_gate_validation/20260327_092450/logs/`

## Validacao automatizada executada

- `python3 -m py_compile web/app/domains/chat/__init__.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_integration.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_summary.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_enforce.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_summary.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`

## Classificacao honesta da validacao

- validacao completa no contexto local/controlado escolhido
- `shadow`, `enforce` e `rollback` comprovados com artefatos reais
- caso bloqueado e caso permitido comprovados

## O que ainda falta antes de abrir 10C

- decidir se o proximo ponto mutavel merece enforcement ou so observabilidade reforcada
- manter sob controle o risco de regressao de import circular no boot do backend
- definir se o tenant demo principal tambem precisa de uma rodada operacional separada ou se o tenant local validado ja basta para o gate de promocao interna

## Rollback desta validacao

- desligar `TARIEL_V2_DOCUMENT_HARD_GATE`
- ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE`
- ou remover o tenant/operacao das allowlists

Nesta execucao, o rollback validado de forma real foi:

- manter `TARIEL_V2_DOCUMENT_HARD_GATE=1`
- desligar `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE`
