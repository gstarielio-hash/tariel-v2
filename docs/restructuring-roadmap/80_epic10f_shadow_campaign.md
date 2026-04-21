# Epic 10F+ - campanha operacional ampliada de `shadow` para `report_finalize_stream`

## Objetivo

Aumentar a massa de evidencia operacional do recorte:

- `POST /app/api/chat`
- branch `eh_comando_finalizar`
- comando `COMANDO_SISTEMA FINALIZARLAUDOAGORA`
- `operation_kind=report_finalize_stream`

sem abrir `enforce`, sem tocar em tenant real e sem alterar comportamento funcional.

## Precheck executado

- `pwd`:
  - `/home/gabriel/Area de trabalho/TARIEL/Tariel Control Consolidado`
- `git status --short`:
  - worktree continua amplo/sujo fora do slice documental; a campanha ficou restrita a artifacts e docs
- boot/import check:
  - `AMBIENTE=dev PYTHONPATH=web python3 -c "import main; main.create_app(); print('boot_import_ok')"`
  - resultado em:
    - `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/boot_import_check.txt`
- flags usadas:
  - `TARIEL_V2_DOCUMENT_HARD_GATE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_ENFORCE=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_TENANTS=1`
  - `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS=report_finalize_stream`
- tenant/controlado:
  - tenant `1`
  - `Empresa A`
  - host `testclient`

## Descoberta conservadora dos casos

Casos uteis e seguros encontrados no harness local/controlado:

- `template gap`:
  - finalizacao via stream com `padrao` sem template ativo compativel
- `template ok`:
  - finalizacao via stream com `padrao` e template ativo compativel

Casos tentados, mas descartados da amostra util:

- `nr13`
  - o fluxo caiu no gate de qualidade especifico do template antes de produzir avaliacao de `report_finalize_stream`
  - por isso nao entrou na campanha agregada

Casos que continuaram `nao_observado` nesta fase:

- `materialization_disallowed_by_policy`
- `no_active_report`

Motivo:

- o recorte real de finalizacao via stream exige laudo ativo;
- no policy engine atual, havendo laudo ativo, `document_materialization_allowed` fica `true`;
- forcar esses blockers neste slice significaria sair do caminho real observado.

## Campanha executada

Foram executadas 4 rodadas uteis novas, todas por HTTP local via `TestClient`, com SQLite dedicado da campanha em:

- `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/campaign_10f.db`

Casos agregados:

- `shadow_stream_gap_padrao_round_1`
  - HTTP `200`
  - `content-type: text/event-stream`
  - `would_block=true`
  - `did_block=false`
  - blockers:
    - `template_not_bound`
    - `template_source_unknown`
- `shadow_stream_ok_padrao_round_1`
  - HTTP `200`
  - `content-type: text/event-stream`
  - `would_block=false`
  - `did_block=false`
  - blockers:
    - nenhum
- `shadow_stream_gap_padrao_round_2`
  - HTTP `200`
  - `content-type: text/event-stream`
  - `would_block=true`
  - `did_block=false`
  - blockers:
    - `template_not_bound`
    - `template_source_unknown`
- `shadow_stream_ok_padrao_round_2`
  - HTTP `200`
  - `content-type: text/event-stream`
  - `would_block=false`
  - `did_block=false`
  - blockers:
    - nenhum

Em todas as 4 execucoes uteis:

- `report_finalize_stream` permaneceu em `shadow_only`
- `enforce_enabled=false`
- `did_block=false`
- o laudo terminou em `Aguardando Aval`
- nao houve bleed fora de tenant/operacao allowlisted

## Agregacao da campanha

Resumo agregado em `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/campaign_summary.json`:

- novas avaliacoes uteis:
  - `4`
- novas execucoes funcionais:
  - `4`
- novas ocorrencias com `would_block=true`:
  - `2`
- novas ocorrencias com `did_block=true`:
  - `0`
- novas execucoes `shadow_only` sem bleed:
  - `4`
- blockers observados:
  - `template_not_bound`:
    - `2`
  - `template_source_unknown`:
    - `2`
- blockers ainda nao observados:
  - `materialization_disallowed_by_policy`
  - `no_active_report`

Summary admin/local no fim da campanha:

- `evaluations=4`
- `would_block=2`
- `did_block=0`
- `shadow_only=4`

## O que a campanha provou

- `template_not_bound` e `template_source_unknown` se repetem de forma estavel neste recorte quando nao existe template ativo compativel
- com template ativo compativel, esses blockers desaparecem sem regressao funcional
- o recorte continua seguro para `shadow`:
  - sem bloqueio real
  - sem mudanca de payload publico
  - sem mudanca de UX
  - sem tenant real
- o rollback continua trivial:
  - remover `report_finalize_stream` de `TARIEL_V2_DOCUMENT_HARD_GATE_OPERATIONS`
  - ou desligar `TARIEL_V2_DOCUMENT_HARD_GATE`

## O que ainda falta

Antes de qualquer novo gate review de `enforce`, ainda faltam:

- observar `materialization_disallowed_by_policy` neste recorte, se algum caso seguro realmente existir
- observar `no_active_report`, se surgir um caminho real que ainda seja semanticamente o mesmo slice
- acumular mais amostra fora deste unico harness local
- manter artifacts por execucao e summary local-only enquanto a observabilidade seguir volatil em memoria

## Artefatos principais

- `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/campaign_summary.json`
- `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/campaign_cases.json`
- `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/campaign_findings.md`
- `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/source_cases_index.txt`
- `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/boot_import_check.txt`
- `artifacts/document_hard_gate_shadow_campaign_10f/20260327_162958/responses/admin_summary_response.json`

## Validacoes rerodadas

- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_hard_gate_10f.py`
  - `3 passed`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`
  - `26 passed`

## Proximo passo recomendado

Novo gate review formal do `report_finalize_stream` usando a amostra ampliada desta campanha, sem abrir `enforce` automaticamente.
