# Epic 09M - Backend Evidence Closure

## Objetivo

Fechar a lacuna entre a UI do Android V2 e a contabilidade formal do backend no tenant demo seguro, de modo que:

- `feed` e `thread` contem como `v2_served` quando a rota V2 for realmente usada
- o `human_ack` seja enviado de forma robusta e idempotente
- o summary admin exponha com clareza quando um ack foi aceito, duplicado ou rejeitado
- o runner operacional espere a telemetria antes de encerrar a rodada

Sem mudar UX visivel, payloads publicos, tenant real ou regras de negocio.

## Lacuna encontrada antes da implementacao

Os artefatos de `artifacts/mobile_pilot_run/20260326_152441/` mostravam:

- a thread `Mesa` abria de verdade
- o backend continuava com `v2_served=0`
- o backend continuava com `human_confirmed_count=0`

A auditoria do codigo mostrou duas causas principais:

1. `thread`:
   - o `ack` da Mesa dependia de `mensagensMesa.length > 0`
   - no laudo `80`, a `Mesa` podia abrir em estado vazio valido
   - nesse caso o render acontecia, mas o `ack` nunca era disparado
2. `feed`:
   - a central de atividade so dependia do poll periodico para rodar `runMonitorActivityFlow`
   - o runner abria e fechava o modal rapido demais
   - na pratica nao havia request V2 observada para `feed`

## Implementacao aplicada

### App Android

Arquivos principais:

- `android/src/config/mobileV2HumanValidation.ts`
- `android/src/config/mobileV2HumanValidation.test.ts`
- `android/src/features/activity/monitorActivityFlow.ts`
- `android/src/features/activity/monitorActivityFlow.test.ts`
- `android/src/features/activity/useActivityCenterController.ts`
- `android/src/features/activity/useActivityCenterController.test.ts`
- `android/src/features/InspectorMobileApp.tsx`

Mudancas:

- criado helper canonico `shouldSendHumanAck(...)`
- criado helper canonico `buildHumanAckPayload(...)`
- normalizacao centralizada de `targetIds` para o `ack`
- o `ack` da `thread` deixou de depender de haver mensagens; agora depende de render valido da superficie `Mesa`
- `runMonitorActivityFlow` passou a expor explicitamente os `laudoIds` realmente consultados no `feed`
- a central de atividade passou a disparar um ciclo de monitoramento imediatamente ao abrir, sem esperar apenas o intervalo
- o app passou a manter markers operacionais discretos:
  - `activity-center-feed-v2-ready`
  - `activity-center-feed-v2-target-<id>`
- o `feed` passou a derivar os alvos de `human_ack` tambem dos `targetIds` realmente consultados no monitoramento

### Backend

Arquivo principal:

- `web/app/v2/mobile_organic_validation.py`

Mudancas:

- o summary organico agora expõe `human_ack_recent_events`
- cada evento recente de `ack` registra:
  - `status` (`accepted`, `duplicate`, `rejected`)
  - `tenant_key`
  - `session_id`
  - `surface`
  - `target_id`
  - `checkpoint_kind`
  - `delivery_mode`
  - `operator_run_id`
  - `capabilities_version`
  - `rollout_bucket`
  - `rejection_reason`, quando houver
- os rejeitados canonicos passaram a ficar rastreaveis no summary admin, em vez de aparecer apenas como `409` no endpoint

### Runner e Maestro

Arquivos principais:

- `android/maestro/mobile-v2-pilot-run.yaml`
- `scripts/run_mobile_pilot_runner.py`

Mudancas:

- o flow do Maestro passou a selecionar o laudo `80` no historico antes de abrir a central de atividade
- a central de atividade agora espera markers operacionais do `feed V2` antes de continuar
- o runner passou a salvar:
  - `backend_summary_post_ui_wait.json`
  - `operator_run_status_post_ui_wait.json`
  - `backend_evidence_post_ui_wait.json`
- o runner tambem passou a esperar alguns segundos pelo backend apos a UI, antes de finalizar o `operator_run`
- o `final_report.md` do runner agora inclui `v2_served_total_after` e a contagem de `human_ack_recent_events_after`

## Validacoes executadas

- `python3 -m py_compile web/app/v2/mobile_organic_validation.py scripts/run_mobile_pilot_runner.py`
- `cd android && npm test -- --runInBand --runTestsByPath src/config/mobileV2HumanValidation.test.ts src/features/activity/monitorActivityFlow.test.ts src/features/activity/useActivityCenterController.test.ts src/features/chat/ThreadConversationPane.test.tsx`
- `cd android && npm run typecheck`
- `python3 -m pytest -q web/tests/test_v2_android_ack_accounting.py web/tests/test_v2_android_surface_served_accounting.py web/tests/test_smoke.py`

Resultado:

- `py_compile` -> `ok`
- `android jest` -> `4 suites passed, 8 tests passed`
- `android typecheck` -> `ok`
- `pytest` -> `28 passed`

## Rodada real executada

Rodada autoritativa:

- `artifacts/mobile_pilot_run/20260326_160710/`

Artefatos principais:

- `artifacts/mobile_pilot_run/20260326_160710/final_report.md`
- `artifacts/mobile_pilot_run/20260326_160710/maestro_run.txt`
- `artifacts/mobile_pilot_run/20260326_160710/backend_summary_post_ui_wait.json`
- `artifacts/mobile_pilot_run/20260326_160710/backend_evidence_post_ui_wait.json`
- `artifacts/mobile_pilot_run/20260326_160710/operator_run_status_after.json`
- `artifacts/mobile_pilot_run/20260326_160710/ui_dumps/ui_after_maestro_failure.xml`
- `artifacts/mobile_pilot_run/20260326_160710/screenshots/screenshots/pilot-run-conversation.png`

O que aconteceu de verdade:

- backend local subiu
- app Android foi rebuildado, reinstalado e aberto no device `RQCW20887GV`
- `operator_run` e sessao organica do tenant demo foram iniciados
- o historico filtrou o laudo `80`
- o tap em `history-item-80` nao fez a UI expor `mesa-tab-button` dentro da janela esperada
- mesmo assim o flow prosseguiu para configuracoes e abriu a `activity-center`
- a `activity-center` ficou em `Nenhuma atividade recente`
- o marker `activity-center-feed-v2-ready` nunca apareceu
- o backend nao registrou nenhuma leitura `feed` ou `thread`; somente `capabilities`

Evidencia backend apos a UI:

- `v2_served=0`
- `human_ack_recent_events=[]`
- `human_confirmed_count=0`
- `recent_events` contendo apenas `capabilities_checks`

Resultado operacional honesto da rodada:

- `app_opened_but_target_not_reached`

Estado final do operator run:

- `operator_run_outcome=aborted`
- `operator_run_reason=operator_aborted`

## Conclusao honesta da fase

O slice 09M entregou:

- contabilizacao e auditoria melhores no backend
- `ack` mais robusto no app para `thread` vazia
- trigger imediato da central de atividade
- runner com espera e artefatos melhores

Mas a rodada real ainda nao fechou a evidencia backend porque ela morreu antes da primeira leitura V2 do `feed` ou da `thread`.

Nesta execucao, a lacuna principal deixou de ser contabilizacao backend pura e voltou a ser operacional:

- o laudo `80` nao ficou selecionado de forma confiavel antes da etapa da central de atividade
- a central abriu vazia
- nenhum request V2 foi observado, entao nao havia como contabilizar `served` ou `human_ack`

## Como repetir

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado"
python3 scripts/run_mobile_pilot_runner.py
```

Conferir:

- `artifacts/mobile_pilot_run/<timestamp>/maestro_run.txt`
- `artifacts/mobile_pilot_run/<timestamp>/backend_summary_post_ui_wait.json`
- `artifacts/mobile_pilot_run/<timestamp>/backend_evidence_post_ui_wait.json`
- `artifacts/mobile_pilot_run/<timestamp>/operator_run_status_after.json`
- `artifacts/mobile_pilot_run/<timestamp>/ui_dumps/ui_after_maestro_failure.xml`

## O que ainda falta

- estabilizar a selecao efetiva do laudo `80` antes da etapa da central de atividade
- entender por que a central abriu vazia na rodada real, mesmo com trigger imediato do monitor
- provar no backend pelo menos uma leitura `feed` V2 e uma leitura `thread` V2 na mesma sessao organica
- so depois disso validar se `human_ack` fecha a cobertura formal como esperado
