# Epic 09O - Prova automatizavel de laudoSelecionadoId no shell autenticado

## Objetivo

Descobrir se o `tap` em `history-item-80` realmente chegava ao callback de selecao do app e, principalmente, produzir uma prova automatizavel do `laudoSelecionadoId` no shell autenticado sem mudar UX visivel para o usuario final.

Escopo desta fase:

- tenant seguro `1 - Empresa Demo (DEV)`
- app Android do workspace atual
- runner operacional real com Maestro
- sem mexer em backend funcional, payload publico ou regra de negocio

## Auditoria do caminho real de selecao

A auditoria do app confirmou o caminho canonico da selecao:

1. `HistoryDrawerPanel` dispara `onSelecionarHistorico(item)` no `Pressable` do item
2. `useHistoryController.handleSelecionarHistorico(card)` fecha o drawer, fixa a aba em `chat` e chama `handleSelecionarLaudo(card)`
3. `useInspectorChatController.handleSelecionarLaudo(card)` chama `abrirLaudoPorId(accessToken, laudoId)`
4. `abrirLaudoPorId(...)` faz `carregarMensagensLaudo(...)` e, em caso de sucesso, executa `setConversation(proximaConversa)`
5. o `laudoSelecionadoId` do shell nasce de `conversaAtiva?.laudoId ?? null` em `buildInspectorBaseDerivedStateSections.ts`

Conclusao:

- o `laudoSelecionadoId` nao vive no drawer nem num estado local do item
- a fonte de verdade segura continua sendo `conversa.laudoId`
- o shell ja podia estar atualizando corretamente antes, mas a prova anterior era fraca porque os markers estavam ocultos/off-screen e o runner so olhava o dump final, ja depois de sair da tela de selecao

## Implementacao aplicada

### 1. Diagnostico de selecao extraido para helpers puros

Arquivo:

- `android/src/features/common/mobilePilotAutomationDiagnostics.ts`

Foram criados helpers canonicos para o ciclo de selecao:

- `recordHistorySelectionTap(...)`
- `recordHistorySelectionCallbackCompleted(...)`
- `syncHistorySelectionWithShell(...)`

Estados acompanhados:

- `targetTappedId`
- `callbackFiredId`
- `callbackCompletedId`
- `selectionLostId`

Isso permitiu testar o fluxo de forma unitaria e usar a mesma semantica tanto no app quanto no runner.

### 2. Prova materializada no shell autenticado

Arquivo:

- `android/src/features/InspectorMobileApp.tsx`

Mudancas:

- foi criado `handleSelecionarHistoricoComDiagnostico`, um wrapper operacional sobre `handleSelecionarHistorico`
- esse wrapper registra:
  - callback de selecao disparado
  - callback concluido
- o shell agora sincroniza o diagnostico com `conversa?.laudoId`
- quando `EXPO_PUBLIC_MOBILE_AUTOMATION_DIAGNOSTICS=1`, o app renderiza um probe real e minuscule no viewport, em vez de markers ocultos fora da tela

Markers principais desta fase:

- `history-selection-callback-fired-<id>`
- `history-selection-callback-completed-<id>`
- `authenticated-shell-selected-laudo-id-<id>`
- `authenticated-shell-selection-ready-<id>`
- `authenticated-shell-selection-lost-<id>`

Tambem foi adicionado um `content-desc` resumido e parseavel:

- `pilot_selection_probe;target_tapped=...;callback_fired=...;callback_completed=...;selected_laudo_id=...`

Importante:

- o probe so e materializado no modo de automacao desta trilha
- nao houve mudanca de UX funcional para o usuario final

### 3. Maestro e runner ajustados para a prova real

Arquivos:

- `android/maestro/mobile-v2-pilot-run.yaml`
- `scripts/run_mobile_pilot_runner.py`

Mudancas:

- o Maestro passou a esperar explicitamente:
  - `history-selection-callback-fired-${TARGET_LAUDO_ID}`
  - `authenticated-shell-selection-ready-${TARGET_LAUDO_ID}`
- o runner passou a registrar a confirmacao de selecao pelo proprio stdout do Maestro
- o runner deixou de depender apenas do `ui_dump` final, que nesta fase ja pode estar na central de atividade e nao mais no shell
- o runner tambem passou a reconhecer `activity-center-empty-state` como `activity_center_state=empty`

## Validacoes executadas

- `maestro check-syntax android/maestro/mobile-v2-pilot-run.yaml`
- `python3 -m py_compile scripts/run_mobile_pilot_runner.py`
- `cd android && npm test -- --runInBand --runTestsByPath src/features/common/mobilePilotAutomationDiagnostics.test.ts`
- `cd android && npm run typecheck`
- `python3 -m pytest -q web/tests/test_smoke.py`

Resultado:

- `maestro check-syntax` -> `OK`
- `py_compile` -> `ok`
- `jest` -> `7 passed`
- `typecheck` -> `ok`
- `pytest` -> `26 passed`

## Rodadas reais desta fase

### Rodada 1 - `artifacts/mobile_pilot_run/20260326_180433`

O que aconteceu:

- o app foi rebuildado e reinstalado no device `RQCW20887GV`
- o Maestro conseguiu, pela primeira vez nesta trilha, confirmar:
  - `history-selection-callback-fired-80`
  - `authenticated-shell-selection-ready-80`
- o flow avancou alem da selecao e abriu configuracoes + central de atividade
- a central abriu vazia

Problema remanescente nesta rodada:

- o runner ainda classificou olhando apenas o dump final da central
- como o `ui_dump` final ja nao estava mais no shell, ele perdeu a confirmacao anterior da selecao e escreveu um `result` incorreto

### Rodada autoritativa - `artifacts/mobile_pilot_run/20260326_180956`

Arquivos principais:

- `artifacts/mobile_pilot_run/20260326_180956/final_report.md`
- `artifacts/mobile_pilot_run/20260326_180956/maestro_run.txt`
- `artifacts/mobile_pilot_run/20260326_180956/ui_marker_summary.json`
- `artifacts/mobile_pilot_run/20260326_180956/ui_dumps/ui_after_maestro_failure.xml`
- `artifacts/mobile_pilot_run/20260326_180956/backend_summary_after.json`
- `artifacts/mobile_pilot_run/20260326_180956/operator_run_status_after.json`

O que foi provado de verdade:

- `Tap on id: history-item-${TARGET_LAUDO_ID}... COMPLETED`
- `Assert that id: history-selection-callback-fired-${TARGET_LAUDO_ID} is visible... COMPLETED`
- `Assert that id: authenticated-shell-selection-ready-${TARGET_LAUDO_ID} is visible... COMPLETED`

Conclusao factual:

- o `tap` chegou ao callback real de selecao
- a selecao subiu ate o shell autenticado
- o `laudoSelecionadoId` do shell para o target `80` ficou provado de forma automatizavel

## Resultado honesto da rodada final

Resultado correto desta fase:

- `selected_laudo_confirmed`

Cobertura operacional:

- `feed`: nao
- `thread`: nao

Estado do backend apos a rodada:

- `v2_served=0`
- `human_ack_recent_events=0`
- `operator_run_outcome=aborted`

O bloqueio real que sobrou nao e mais a selecao do laudo:

- a central de atividade abre
- o dump final mostra `activity-center-empty-state`
- o marker `activity-center-terminal-state` nao apareceu nessa tela
- o backend continuou sem requests V2 ou `human_ack`

Portanto, a fase 09O fechou a pergunta principal:

- o callback e a propagacao ate o shell funcionam
- a lacuna anterior era de observabilidade/prova automatizavel
- o bloqueio operacional seguinte migrou para a central vazia e seus markers terminais

## Como repetir

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado"
python3 scripts/run_mobile_pilot_runner.py
```

Consultar principalmente:

- `artifacts/mobile_pilot_run/<timestamp>/maestro_run.txt`
- `artifacts/mobile_pilot_run/<timestamp>/final_report.md`
- `artifacts/mobile_pilot_run/<timestamp>/ui_marker_summary.json`
- `artifacts/mobile_pilot_run/<timestamp>/ui_dumps/ui_after_maestro_failure.xml`

## O que ainda falta

- materializar no app os markers terminais canonicos da central (`loading/empty/loaded/error`) de forma coerente com a tela real
- descobrir por que a central abre vazia mesmo com o laudo `80` selecionado
- so depois disso rerodar `feed/thread` para recuperar `v2_served` e `human_ack`
