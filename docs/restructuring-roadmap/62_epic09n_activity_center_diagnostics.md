# Epic 09N - Activity Center Diagnostics

## Objetivo

Fechar a lacuna operacional que ainda impedia a rodada assistida do piloto Android V2 no tenant demo:

- confirmar quando o laudo `80` foi realmente selecionado
- parar de tratar `mesa-tab-button` como evidencia de selecao valida
- expor estados terminais discretos da central de atividade
- rerodar o runner com evidencias melhores e classificacao honesta

Sem mudar UX visivel, tenant real, payloads publicos ou regras de negocio.

## Causa mais provavel da falha anterior

A auditoria dos artefatos de `artifacts/mobile_pilot_run/20260326_160710/` e do app real mostrou duas causas acopladas:

1. `mesa-tab-button` era um falso positivo
   - o botao existe no shell padrao do app mesmo sem um laudo realmente aberto
   - a screenshot `pilot-run-conversation.png` da fase 09M ja mostrava o shell generico do chat, nao a conversa do laudo `80`
   - por isso a rodada podia aparentar progresso mesmo sem selecao real
2. o laudo `80` depende de selecao real para entrar no monitoramento da central
   - consulta real ao mobile local mostrou `laudo 80 -> status_card="aberto"`
   - a central monitora automaticamente o laudo ativo e, sem laudo ativo, apenas laudos em `ajustes/aguardando`
   - logo, quando a selecao falhava, o `80` nao era consultado no `feed`
   - isso explica por que a central podia ficar vazia e o backend manter `v2_served=0`

Conclusao operacional:

- a fase 09M morreu cedo demais para provar algo sobre a central naquela rodada especifica
- o bloqueio primario voltou a ser a selecao efetiva do laudo `80`
- a central vazia observada antes continua coerente com a ausencia dessa selecao, porque `80` nao e elegivel por status sem estar ativo

## Implementacao aplicada

### Historico

Arquivos principais:

- `android/src/features/history/HistoryDrawerPanel.tsx`
- `android/src/features/history/HistoryDrawerPanel.test.tsx`

Mudancas:

- `ScrollView` do historico agora usa `keyboardShouldPersistTaps="handled"`
- os itens do historico ganharam `accessibilityState.selected`
- foram adicionados markers discretos por item:
  - `history-target-visible-<id>`
  - `history-item-selected-<id>`

Motivo:

- reduzir a chance de o primeiro tap com teclado aberto apenas fechar o teclado em vez de selecionar o laudo
- tornar o historico observavel sem mexer em UX

### Diagnostico da central

Arquivos principais:

- `android/src/features/activity/monitorActivityFlow.ts`
- `android/src/features/activity/useActivityCenterController.ts`
- `android/src/features/common/mobilePilotAutomationDiagnostics.ts`
- `android/src/features/common/mobilePilotAutomationDiagnostics.test.ts`
- `android/src/features/InspectorMobileApp.tsx`

Mudancas:

- `runMonitorActivityFlow(...)` agora retorna um resumo operacional com:
  - `requestDispatched`
  - `requestedTargetIds`
  - `feedReadMetadata`
  - `generatedNotificationsCount`
  - `errorMessage`
- `useActivityCenterController` passou a manter um diagnostico discreto da central:
  - `phase`: `idle/loading/settled/error`
  - `requestDispatched`
  - `requestedTargetIds`
  - `lastReadMetadata`
  - `lastError`
- foi criado um builder canonico de markers operacionais para:
  - `selected-history-item-marker`
  - `selected-history-item-id-<id>`
  - `selected-history-item-none`
  - `activity-center-request-dispatched`
  - `activity-center-request-not-started`
  - `activity-center-terminal-state`
  - `activity-center-state-loading`
  - `activity-center-state-loaded`
  - `activity-center-state-empty`
  - `activity-center-state-error`
  - `activity-center-feed-v2-served`
  - `activity-center-feed-legacy-served`
  - `activity-center-feed-v2-target-<id>`

Observacao honesta:

- esses markers existem no app, mas na rodada real final o `uiautomator` do Android continuou nao materializando os markers globais ocultos no dump
- por isso o runner passou a ser mais honesto na etapa de espera, mas o `ui_marker_summary.json` final ainda nao captura esses markers como esperado

### Runner e Maestro

Arquivos principais:

- `android/maestro/mobile-v2-pilot-run.yaml`
- `scripts/run_mobile_pilot_runner.py`

Mudancas:

- o Maestro deixou de tratar `mesa-tab-button` como prova de selecao
- a etapa critica agora espera `selected-history-item-id-${TARGET_LAUDO_ID}`
- o runner passou a salvar `ui_marker_summary.json`
- a classificacao passou a considerar explicitamente:
  - `app_opened_but_target_not_reached`
  - `central_opened_but_empty`
  - `central_opened_with_legacy_only`
  - `central_opened_with_v2_but_no_ack`

Resultado pratico:

- a rodada nao prossegue mais com falso positivo de selecao
- ela para exatamente no ponto em que o laudo `80` nao se confirma

## Validacoes executadas

- `maestro check-syntax android/maestro/mobile-v2-pilot-run.yaml`
- `python3 -m py_compile scripts/run_mobile_pilot_runner.py`
- `cd android && npm test -- --runInBand --runTestsByPath src/features/common/mobilePilotAutomationDiagnostics.test.ts src/features/history/HistoryDrawerPanel.test.tsx src/features/activity/monitorActivityFlow.test.ts src/features/activity/useActivityCenterController.test.ts src/features/chat/ThreadConversationPane.test.tsx`
- `cd android && npm run typecheck`
- `python3 -m pytest -q web/tests/test_smoke.py`

Todos passaram antes da rodada final.

## Rodadas reais desta fase

### Rodada 1 - `artifacts/mobile_pilot_run/20260326_164854`

- o flow ja esperava `selected-history-item-id-80`
- a selecao nao foi confirmada
- o Maestro abortou ainda na etapa do historico
- a screenshot final mostrou novamente o shell generico do chat

### Rodada 2 - `artifacts/mobile_pilot_run/20260326_165914`

- ajustes discretos tentaram tornar os markers globais mais visiveis para a automacao
- o resultado operacional permaneceu o mesmo
- `selected-history-item-id-80` nao apareceu

### Rodada final e autoritativa - `artifacts/mobile_pilot_run/20260326_170358`

Arquivos principais:

- `artifacts/mobile_pilot_run/20260326_170358/final_report.md`
- `artifacts/mobile_pilot_run/20260326_170358/maestro_run.txt`
- `artifacts/mobile_pilot_run/20260326_170358/ui_marker_summary.json`
- `artifacts/mobile_pilot_run/20260326_170358/ui_dumps/ui_after_maestro_failure.xml`
- `artifacts/mobile_pilot_run/20260326_170358/screenshots/device_after_maestro_failure.png`

O que aconteceu de verdade:

- o app foi rebuildado, reinstalado e aberto no device `RQCW20887GV`
- o historico abriu e o target `history-item-80` ficou visivel
- o Maestro tocou `history-item-80`
- o marker de selecao real `selected-history-item-id-80` nunca apareceu
- no retry seguinte, o proprio `history-item-80` ja nao estava mais na arvore
- o dump final mostrou apenas o shell generico:
  - `open-history-button`
  - `open-settings-button`
  - `chat-tab-button`
  - `mesa-tab-button`
  - `chat-composer-input`
- a central de atividade nao foi aberta nesta rodada final
- o backend terminou sem trafego V2 nem `human_ack`

## Resultado honesto da fase

- selecao do laudo `80` estabilizada no runner: parcialmente
  - o runner agora detecta a ausencia de selecao real e para cedo
  - a selecao em si ainda nao ficou deterministica no device
- central de atividade diagnosticada: sim
  - `80` so entra no monitoramento do feed quando esta realmente selecionado
  - como `status_card="aberto"`, a central nao o inclui automaticamente sem selecao ativa
- cobertura `feed`: nao
- cobertura `thread`: nao
- resultado operacional correto da rodada final: `app_opened_but_target_not_reached`

## O que ainda falta

- descobrir por que o tap em `history-item-80` ainda retorna para o shell generico em vez de abrir a conversa do laudo
- tornar observavel, de forma que o `uiautomator` enxergue, o estado global de selecao real do laudo
- so depois disso rerodar a central para separar:
  - `request_not_started`
  - `empty`
  - `legacy`
  - `v2`

## Como repetir

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado"
python3 scripts/run_mobile_pilot_runner.py
```

Conferir principalmente:

- `artifacts/mobile_pilot_run/<timestamp>/maestro_run.txt`
- `artifacts/mobile_pilot_run/<timestamp>/ui_dumps/ui_after_maestro_failure.xml`
- `artifacts/mobile_pilot_run/<timestamp>/ui_marker_summary.json`
- `artifacts/mobile_pilot_run/<timestamp>/final_report.md`
