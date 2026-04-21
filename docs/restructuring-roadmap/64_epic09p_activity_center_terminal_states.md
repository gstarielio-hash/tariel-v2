# Epic 09P - Activity Center Terminal States

## Objetivo

Materializar, no proprio modal da central de atividade, um estado terminal canonico e automatizavel depois que o laudo `80` ja esta confirmado no shell autenticado.

Escopo desta fase:

- tenant seguro `1 - Empresa Demo (DEV)`
- app Android do workspace atual
- runner operacional real com Maestro
- sem mexer em dominio, rollout, tenant real ou payload publico

## Auditoria do controller e da arvore da central

A auditoria do codigo confirmou:

1. `useActivityCenterController` ja conhecia quase todo o estado relevante
   - `phase`
   - `requestDispatched`
   - `requestedTargetIds`
   - `lastReadMetadata`
   - `lastError`
2. `runMonitorActivityFlow(...)` ja decidia se havia targets elegiveis e se o ciclo do feed da Mesa tinha sido disparado
3. o bloqueio real da 09O nao era falta de estado interno
   - o bloqueio era de materializacao
   - o helper global do shell construia markers da central
   - mas o modal da central nao renderizava esses markers dentro da propria arvore
   - por isso o `uiautomator` e o Maestro viam apenas `activity-center-empty-state`, sem `activity-center-terminal-state`

Conclusao da auditoria:

- o app ja sabia diferenciar mais do que mostrava
- a central vazia nao estava sendo classificada de forma canonica na arvore do modal
- era necessario trazer o diagnostico para dentro do modal, em modo de automacao, com estado terminal unico por rodada

## Implementacao aplicada

### 1. Helper canonico do terminal state

Arquivo principal:

- `android/src/features/common/mobilePilotAutomationDiagnostics.ts`

Mudancas:

- criado `resolveActivityCenterAutomationTerminalState(...)`
- criado `resolveActivityCenterAutomationDeliveryMode(...)`
- criado `buildActivityCenterAutomationMarkerIds(...)`
- criado `buildActivityCenterAutomationProbeLabel(...)`
- estados terminais canonicos:
  - `no_request`
  - `empty`
  - `loaded_legacy`
  - `loaded_v2`
  - `loaded_unknown`
  - `error`
- markers canonicos gerados:
  - `activity-center-terminal-state`
  - `activity-center-terminal-state-no-request`
  - `activity-center-terminal-state-empty`
  - `activity-center-terminal-state-loaded-legacy`
  - `activity-center-terminal-state-loaded-v2`
  - `activity-center-terminal-state-loaded-unknown`
  - `activity-center-terminal-state-error`
  - `activity-center-request-dispatched`
  - `activity-center-request-not-started`
  - `activity-center-request-target-<id>`
  - `activity-center-feed-v2-served`
  - `activity-center-feed-legacy-served`
  - `activity-center-feed-delivery-unknown`
  - `activity-center-skip-already-monitoring`
  - `activity-center-skip-network-blocked`
  - `activity-center-skip-no-target`

### 2. Observabilidade explicita da central no app

Arquivos principais:

- `android/src/features/activity/monitorActivityFlow.ts`
- `android/src/features/activity/useActivityCenterController.ts`
- `android/src/features/InspectorMobileApp.tsx`
- `android/src/features/common/SessionModalsStack.tsx`
- `android/src/features/common/OperationalModals.tsx`
- `android/src/features/common/buildInspectorSessionModalsSections.ts`
- `android/src/features/common/inspectorUiBuilderTypes.ts`

Mudancas:

- `runMonitorActivityFlow(...)` passou a expor `skipReason`
  - `already_monitoring`
  - `no_target`
- `useActivityCenterController` passou a guardar `lastSkipReason`
  - e tambem marca `network_blocked` quando a central nao pode sincronizar
- o app passou a derivar um `activityCenterAutomationDiagnostics` unico no shell
- esse diagnostico e entregue ao `ActivityCenterModal`
- o modal agora renderiza um probe real e discreto na propria arvore:
  - `activity-center-automation-probe`
  - `content-desc` parseavel `pilot_activity_center_probe;...`
  - markers reais dentro do card da central

Importante:

- o probe e os markers so aparecem com `EXPO_PUBLIC_MOBILE_AUTOMATION_DIAGNOSTICS=1`
- a UX visivel do usuario final nao mudou fora desse modo de automacao

### 3. Runner e Maestro

Arquivos principais:

- `android/maestro/mobile-v2-pilot-run.yaml`
- `scripts/run_mobile_pilot_runner.py`

Mudancas:

- o Maestro agora espera explicitamente `activity-center-terminal-state`
- a rodada so prossegue para thread se `activity-center-feed-v2-served` realmente aparecer
- se o feed nao entra em V2, o flow termina na central e preserva o modal no dump final
- o runner passou a parsear `pilot_activity_center_probe`
- novas classificacoes operacionais:
  - `central_no_request_fired`
  - `central_loaded_empty`
  - `central_loaded_legacy`
  - `central_loaded_v2`
  - `central_error`
  - `central_unknown_terminal_state`
- o `final_report.md` agora registra:
  - `ui_activity_center_terminal_state`
  - `ui_activity_center_request_dispatched`
  - `ui_activity_center_requested_targets`
  - `ui_activity_center_skip_reason`
  - confirmacao do terminal state pelo proprio Maestro

## Validacoes executadas

- `maestro check-syntax android/maestro/mobile-v2-pilot-run.yaml`
- `python3 -m py_compile scripts/run_mobile_pilot_runner.py`
- `cd android && npm test -- --runInBand --runTestsByPath src/features/common/mobilePilotAutomationDiagnostics.test.ts src/features/common/OperationalModals.test.tsx src/features/common/buildInspectorSessionModalsSections.test.ts src/features/activity/monitorActivityFlow.test.ts src/features/activity/useActivityCenterController.test.ts`
- `cd android && npm run typecheck`
- `python3 -m pytest -q web/tests/test_smoke.py`

Resultado:

- `maestro check-syntax` -> `OK`
- `py_compile` -> `ok`
- `jest` -> `18 passed`
- `typecheck` -> `ok`
- `pytest` -> `26 passed`

## Rodadas reais desta fase

### Tentativa de preflight bloqueada - `20260326_193812`

- o runner encontrou o device `RQCW20887GV` como `unauthorized`
- a rodada foi interrompida antes do preflight completo
- o bloqueio foi recuperado de forma conservadora com:

```bash
adb kill-server
adb start-server
adb devices -l
```

- o device voltou para estado `device`

### Rodada 1 - `artifacts/mobile_pilot_run/20260326_193848`

O que aconteceu:

- a selecao do laudo `80` foi confirmada novamente
- a central abriu
- o dump final passou a mostrar, pela primeira vez nesta trilha, os markers canonicos no proprio modal:
  - `activity-center-terminal-state`
  - `activity-center-terminal-state-empty`
  - `activity-center-request-dispatched`
  - `activity-center-request-target-80`
- o probe parseado registrou:
  - `phase=settled`
  - `terminal_state=empty`
  - `request_dispatched=true`
  - `requested_targets=80`
  - `delivery=unknown`
- o Maestro ainda falhou no `extendedWaitUntil` do terminal state porque o probe do modal estava materializado com geometria pequena demais para o criterio visual dele
- mesmo assim, o runner classificou corretamente:
  - `central_loaded_empty`

### Rodada autoritativa - `artifacts/mobile_pilot_run/20260326_194352`

O ajuste final do probe do modal:

- reaproveitou o mesmo padrao visual minimo que ja funcionava no shell autenticado
- `collapsable={false}`
- pequenos blocos com `backgroundColor` e bounds validos para o Maestro

Resultado real:

- `Assert that id: activity-center-terminal-state is visible... COMPLETED`
- `Run flow when id: activity-center-feed-v2-served is visible... SKIPPED`
- `ui_marker_summary.json` final:
  - `activity_center_terminal_state=empty`
  - `activity_center_request_dispatched=true`
  - `activity_center_requested_targets=[80]`
  - `activity_center_delivery_mode=unknown`
  - `activity_center_skip_reason=none`
- `operator_run_outcome=completed_inconclusive`
- `operator_run_reason=minimum_human_coverage_not_met`
- `backend_summary_after.json` seguiu com:
  - `v2_served=0`
  - `observed_requests=0`
  - `human_ack_recent_events=[]`

## Resultado honesto da fase

Entregas fechadas nesta fase:

- estado terminal canonico da central materializado no modal: sim
- estado terminal lido pelo runner: sim
- estado terminal confirmado visualmente pelo Maestro: sim
- request local da central explicitado como disparado para target `80`: sim
- diferenciacao entre `no_request` e `empty`: sim

Resultado operacional da rodada autoritativa:

- `central_loaded_empty`

Leitura factual da rodada:

- o shell confirmou o laudo `80`
- a central abriu e atingiu terminal `empty`
- o proprio app declarou `request_dispatched=true` e `requested_targets=80`
- o app nao declarou `loaded_v2` nem `loaded_legacy`
- o backend continuou sem observar trafego `feed/thread`

Conclusao tecnica mais provavel:

- a lacuna remanescente deixou de ser a navegacao e deixou de ser a observabilidade da central
- a proxima pergunta agora e por que o app considera o request da central disparado, mas nao materializa metadata de entrega nem produz qualquer evidencia backend de request

## Como repetir

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado"
python3 scripts/run_mobile_pilot_runner.py
```

Consultar principalmente:

- `artifacts/mobile_pilot_run/<timestamp>/maestro_run.txt`
- `artifacts/mobile_pilot_run/<timestamp>/ui_marker_summary.json`
- `artifacts/mobile_pilot_run/<timestamp>/ui_dumps/ui_after_maestro.xml`
- `artifacts/mobile_pilot_run/<timestamp>/backend_summary_after.json`
- `artifacts/mobile_pilot_run/<timestamp>/operator_run_status_after.json`

## O que ainda falta

- provar por que a central marca `request_dispatched=true` sem gerar metadata de entrega nem trafego backend observado
- descobrir se o request esta sendo abortado antes de sair, desviado por estado stale ou resolvido por um caminho que nao atualiza `lastReadMetadata`
- so depois disso rerodar a transicao para `loaded_v2` e retomar a trilha de `v2_served` e `human_ack`
