# Fase 09 - Documento, template e IA: fechamento operacional

Data: `2026-03-30`

## Objetivo fechado

Promover a `Fase 09 - Documento, template e IA` sem depender de leitura informal do legado para saber se o ciclo documental, o lifecycle de template e a provenance IA/humana continuam íntegros na superfície oficial da Mesa.

## O que entrou neste fechamento

- lifecycle de template materializado no `frontend paralelo da Mesa`, com ações oficiais de `publish`, troca de status, base recomendada, clone, preview e download do arquivo-base
- rotas BFF do `frontend paralelo da Mesa` para `publish`, `status`, `base-recomendada`, `clonar`, `preview` e `arquivo-base`, usando a sessão real do navegador
- provenance IA/humana exposta no detalhe do caso da Mesa, com badges, qualidade, contagens e notas, sem quebrar o fold principal validado pela baseline visual
- agregação administrativa de `OCR`, geração documental, custos de IA e operações pesadas em `GET /admin/api/document-operations/summary`
- runner oficial da fase em `make document-acceptance`, produzindo artifact documental reproduzível

## Superfícies e arquivos-chave

- `web/app/domains/admin/document_operations_summary.py`
- `web/app/domains/admin/routes.py`
- `web/tests/test_v2_document_operations_summary.py`
- `scripts/run_document_phase_acceptance.py`
- `Makefile`

## Evidência real gerada

Artifact autoritativo:

- `artifacts/document_phase_acceptance/20260330_213625/`

Resumo do artifact:

- `document_phase_acceptance_summary.json` com `status=ok`
- `run_document_hard_gate_10g_validation.py` verde
- `run_document_hard_gate_10i_validation.py` verde
- testes focais do `frontend paralelo da Mesa` verdes
- build do `frontend paralelo da Mesa` verde
- `pytest` focal do backend documental verde

Arquivos úteis do artifact:

- `artifacts/document_phase_acceptance/20260330_213625/document_phase_acceptance_summary.json`
- `artifacts/document_phase_acceptance/20260330_213625/final_report.md`

## Validação local

- `make document-acceptance`
- `make verify`
- `make contract-check`

## Leitura operacional correta do resultado

- o lifecycle documental e de template agora está visível e acionável na superfície oficial da Mesa
- a provenance IA/humana deixou de ficar implícita no payload e passou a compor a leitura auditável do caso
- `OCR`, custos e geração documental pesada deixaram de depender de inspeção manual de logs para leitura agregada
- o fechamento da fase não depende mais de checklist informal: existe runner oficial com artifact e baseline verde

## Resultado

Com este slice:

- a `Fase 09 - Documento, template e IA` pode ser promovida com aceite reproduzível
- a frente principal volta para `Fase 10 - Observabilidade, operação e segurança`
