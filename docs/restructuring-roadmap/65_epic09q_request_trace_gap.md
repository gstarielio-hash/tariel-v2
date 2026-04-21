# Epic 09Q - Request Trace Gap

## Objetivo

Fechar a lacuna operacional entre:

- o app declarando `request_dispatched=true` na central de atividade
- o backend continuando sem `observed_requests`, `v2_served` ou metadata de entrega

Escopo desta fase:

- tenant seguro `1 - Empresa Demo (DEV)`
- app Android e backend do workspace atual
- sem mudar payload publico, regra de negocio, rollout ou tenant real

## Hipotese auditada

Antes desta fase, a trilha factual era:

- o laudo `80` ja estava confirmado no shell autenticado
- a central materializava `terminal_state=empty`
- o app-side diagnostic expunha:
  - `request_dispatched=true`
  - `requested_targets=[80]`
  - `delivery=unknown`
- o backend terminava com:
  - `v2_served=0`
  - `observed_requests=0`
  - `human_ack_recent_events=[]`

Hipoteses principais avaliadas:

1. o request nunca saia do client HTTP do app
2. o request saia, mas morria antes de chegar ao backend local
3. o request chegava, mas nao entrava no caminho observado/contado
4. a central estava entrando em legado puro sem metadata V2/legacy suficiente para a automacao

## Rota real descoberta

O caminho real da central de atividade foi confirmado assim:

1. `useActivityCenterController.monitorarAtividade(...)`
2. `runMonitorActivityFlow(...)`
3. `carregarFeedMesaMobile(...)`
4. `carregarFeedMesaMobileV2(...)` ou `carregarFeedMesaMobileLegacy(...)`
5. `fetchComObservabilidade(...)`
6. backend:
   - `/app/api/mobile/v2/mesa/feed`
   - ou `/app/api/mobile/mesa/feed`

Ou seja:

- a central nao usa um repository paralelo oculto
- o request real passa pelo `mesaApi.ts`
- o ponto cego anterior estava entre o controller local e a observabilidade backend

## Implementacao aplicada

### 1. Trace canonico no app

Arquivos principais:

- `android/src/config/mobilePilotRequestTrace.ts`
- `android/src/config/apiCore.ts`
- `android/src/config/mesaApi.ts`

Mudancas:

- criado um resumo canonico do trace da central com:
  - `traceId`
  - `phase`
  - `routeDecision`
  - `actualRoute`
  - `attemptSequence`
  - `endpointPath`
  - `responseStatus`
  - `failureKind`
  - `validationSessionId`
  - `operatorRunId`
  - `deliveryMode`
  - `contractFlagEnabled`
- `fetchComObservabilidade(...)` passou a aceitar lifecycle hooks opcionais:
  - `onRequestSent`
  - `onResponseReceived`
  - `onRequestFailed`
- `carregarFeedMesaMobile(...)` passou a:
  - criar `traceId` proprio da central
  - propagar `X-Tariel-Mobile-Central-Trace`
  - emitir `intent_created`, `request_sent`, `response_received`, `request_failed` ou `request_cancelled`
  - registrar explicitamente se o caminho real foi:
    - `legacy`
    - `v2`
    - `v2 -> legacy`
  - registrar tambem se a flag local `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED` estava efetiva

### 2. Trace propagado ate a central/runner

Arquivos principais:

- `android/src/features/activity/monitorActivityFlow.ts`
- `android/src/features/activity/useActivityCenterController.ts`
- `android/src/features/InspectorMobileApp.tsx`
- `android/src/features/common/mobilePilotAutomationDiagnostics.ts`

Mudancas:

- o resultado do monitoramento agora carrega `feedRequestTrace`
- `useActivityCenterController` agora persiste `lastRequestTrace`
- o shell passa esse trace ao diagnostico da central
- o probe `pilot_activity_center_probe;...` agora materializa:
  - `request_phase`
  - `request_trace_id`
  - `request_flag_enabled`
  - `request_route_decision`
  - `request_actual_route`
  - `request_attempt_sequence`
  - `request_endpoint_path`
  - `request_status`
  - `request_failure_kind`
  - `request_backend_request_id`
  - `request_validation_session`
  - `request_operator_run`
- markers discretos adicionais:
  - `activity-center-request-trace-present`
  - `activity-center-request-phase-<kind>`
  - `activity-center-request-route-decision-<kind>`
  - `activity-center-request-actual-route-<kind>`
  - `activity-center-request-flag-enabled`
  - `activity-center-request-flag-disabled`

### 3. Captura do mesmo trace no backend

Arquivos principais:

- `web/app/v2/mobile_rollout.py`
- `web/app/v2/mobile_rollout_metrics.py`
- `web/app/domains/chat/mesa.py`

Mudancas:

- criado `HEADER_MOBILE_CENTRAL_TRACE`
- `extract_mobile_v2_request_metadata(...)` agora extrai `central_trace_id`
- criado `observe_mobile_v2_route_received(...)`
  - captura `received_route` nas rotas reais do feed
  - registra:
    - `trace_id`
    - `route`
    - `delivery_path`
    - `validation_session_id`
    - `operator_run_id`
    - `tenant_key`
    - `target_ids`
    - `correlation_id`
    - `client_route`
- criado buffer discreto `request_traces_recent` no summary operacional
- as observacoes canonicas existentes (`legacy_fallbacks` e `v2_served`) agora tambem gravam eventos `counted` com o mesmo `trace_id`

### 4. Runner enriquecido

Arquivo principal:

- `scripts/run_mobile_pilot_runner.py`

Mudancas:

- parse do probe da central expandido para os campos de request trace
- novos artefatos:
  - `app_request_trace_summary.json`
  - `backend_request_trace_summary_post_ui_wait.json`
  - `backend_request_trace_summary_after.json`
  - `request_trace_gap_summary.json`
- a classificacao agora diferencia, quando houver rodada valida:
  - `request_created_not_sent`
  - `request_sent_not_received_backend`
  - `request_received_backend_legacy_only`
  - `request_received_backend_v2_but_no_metadata`

## Validacoes executadas

- `python3 -m py_compile web/app/v2/mobile_rollout.py web/app/v2/mobile_rollout_metrics.py web/app/domains/chat/mesa.py scripts/run_mobile_pilot_runner.py`
- `cd android && npm test -- --runInBand src/config/mobilePilotRequestTrace.test.ts src/config/mesaApi.test.ts src/features/activity/monitorActivityFlow.test.ts src/features/activity/useActivityCenterController.test.ts src/features/common/mobilePilotAutomationDiagnostics.test.ts src/features/common/OperationalModals.test.tsx src/features/common/buildInspectorSessionModalsSections.test.ts`
- `cd android && npm run typecheck`
- `python3 -m pytest -q web/tests/test_v2_android_request_trace_gap.py web/tests/test_v2_android_rollout_metrics.py`
- `python3 -m pytest -q web/tests/test_smoke.py`

Resultado:

- `py_compile` -> `ok`
- `jest` -> `34 passed`
- `typecheck` -> `ok`
- `pytest test_v2_android_request_trace_gap.py + test_v2_android_rollout_metrics.py` -> `4 passed`
- `pytest web/tests/test_smoke.py` -> `26 passed`

## Execucao operacional real desta fase

Artefato da tentativa real:

- `artifacts/mobile_pilot_run/20260326_202310/`

O que aconteceu:

- o runner foi executado de verdade via `python3 scripts/run_mobile_pilot_runner.py`
- o ambiente foi auditado normalmente
- no preflight ADB, o unico device encontrado foi:
  - `RQCW20887GV`
  - estado `unauthorized`
- tentativa conservadora de recuperacao executada localmente:
  - `adb kill-server`
  - `adb start-server`
  - `adb devices -l`
- o device continuou `unauthorized`

Consequencia:

- nao houve `device` utilizavel para instalar/reinstalar o app
- nao houve rodada valida da central com os novos traces no tenant demo
- nenhum tenant real foi tocado

## Resultado honesto da fase

Entregas fechadas nesta fase:

- rastreabilidade ponta a ponta implementada no codigo: sim
- trace correlacionavel do app para o backend: sim
- summary operacional do backend com `request_traces_recent`: sim
- runner capaz de classificar a perda por camada: sim
- rodada real valida no device: nao

Classificacao operacional desta execucao:

- `blocked_no_device`

Camada onde a execucao morreu nesta data:

- antes da navegacao
- antes do fetch da central
- bloqueio ADB no device fisico (`unauthorized`)

## Como repetir

1. Reautorizar o device fisico no Android:

```bash
adb kill-server
adb start-server
adb devices -l
```

2. Confirmar que o device aparece como `device`

3. Rerodar:

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado"
python3 scripts/run_mobile_pilot_runner.py
```

Consultar principalmente:

- `artifacts/mobile_pilot_run/<timestamp>/adb_devices.txt`
- `artifacts/mobile_pilot_run/<timestamp>/app_request_trace_summary.json`
- `artifacts/mobile_pilot_run/<timestamp>/backend_request_trace_summary_after.json`
- `artifacts/mobile_pilot_run/<timestamp>/request_trace_gap_summary.json`
- `artifacts/mobile_pilot_run/<timestamp>/backend_summary_after.json`

## O que ainda falta

- executar uma rodada valida com o device novamente em estado `device`
- observar se o trace da central termina em:
  - `request_sent_not_received_backend`
  - `request_received_backend_legacy_only`
  - `request_received_backend_v2_but_no_metadata`
  - ou outra classificacao real
- so depois disso fechar a lacuna entre central/feed e `v2_served`/`human_ack`
