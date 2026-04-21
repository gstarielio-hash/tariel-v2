# Epic 09R - Diagnóstico e correção da flag V2 no runtime do Android

## Objetivo

Descobrir por que o app Android continuava entrando no caminho legado em runtime, mesmo com o ambiente local aparentemente configurado para V2, e corrigir a causa com o menor impacto possível.

Escopo desta fase:

- workspace atual
- app Android real em `android/`
- tenant seguro `1 - Empresa Demo (DEV)`
- sem mudar UX
- sem mudar payload público
- sem tocar em regra de negócio
- sem tocar em tenant real

## Evidência de partida

O artefato anterior `artifacts/mobile_pilot_run/20260327_063400/` já mostrava:

- `ui_activity_center_request_flag_enabled=false`
- `ui_activity_center_request_route_decision=legacy`
- `ui_activity_center_request_actual_route=legacy`
- `result=request_received_backend_legacy_only`

Ao mesmo tempo:

- `artifacts/mobile_pilot_run/20260327_063400/flags_snapshot.json` mostrava `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED=1` em `android/.env`
- `artifacts/mobile_pilot_run/20260327_063400/capabilities_before.json` e `capabilities_after.json` mostravam:
  - `mobile_v2_reads_enabled=true`
  - `feed_rollout_state=promoted`
  - `thread_rollout_state=promoted`

Ou seja:

- o `.env` local estava ligado
- o gate remoto não estava negando V2
- a perda da flag acontecia dentro do app/runtime

## Auditoria explícita das hipóteses

### 1. A flag `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED` não chega ao runtime do app

Conclusão:

- parcialmente verdadeira no bundle executado antes do patch

Diagnóstico:

- o app lia a flag em `android/src/config/mobileV2Config.ts`
- a leitura usava `process.env[ANDROID_V2_READ_CONTRACTS_FLAG]`
- em Expo/React Native, a substituição de `EXPO_PUBLIC_*` é estática e depende de acesso direto, por exemplo:
  - `process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED`
- o acesso dinâmico por chave escapava da substituição do bundle
- por isso o runtime efetivo caía em `undefined` e o parser devolvia `false`

### 2. A flag chega, mas está sendo parseada incorretamente

Conclusão:

- falso como causa principal

Diagnóstico:

- o parser booleano aceitava `1`, `true`, `on` e `yes`
- com valor real `1`, o parser funciona
- o problema estava antes do parse: o valor não estava materializado no bundle release/preview

### 3. A flag chega, mas `mobileV2Config`/`mesaApi` ainda decide pelo legado

Conclusão:

- verdadeiro apenas como consequência do item 1

Diagnóstico:

- `mesaApi.ts` usava `androidV2ReadContractsEnabled()`
- como a leitura retornava `false`, a central decidia `legacy`
- a lógica de decisão em si não estava ignorando V2; ela recebia o sinal errado

### 4. O build `android:preview` não está reconstruindo com a env certa

Conclusão:

- não era a causa principal, mas havia risco de reprodutibilidade fraca

Diagnóstico:

- `android_install.log` da rodada problemática já mostrava:
  - `env: load .env`
  - `env: export EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED`
- portanto o fluxo de preview já lia `.env`
- ainda assim, os scripts locais foram endurecidos para carregar e propagar explicitamente `EXPO_PUBLIC_*`

### 5. Existe cache antigo do app/Expo/Metro

Conclusão:

- não apareceu como causa determinante nesta trilha

Diagnóstico:

- após corrigir a leitura estática da env e repetir o build preview, o app passou a expor `runtime_flag_enabled=true`
- isso elimina cache antigo como explicação principal para o comportamento observado

### 6. A flag do app está ligada, mas o gate remoto retorna algo que força legado

Conclusão:

- falso para esta fase

Diagnóstico:

- `capabilities_*` do artefato anterior já mostravam rollout promovido para `feed` e `thread`
- o rerun final terminou com:
  - `legacy_fallbacks=0`
  - `rollout_denied=0`
  - `v2_served=7`

### 7. O app considera a flag local só em algumas superfícies e não na central

Conclusão:

- falso

Diagnóstico:

- a central usa `runMonitorActivityFlow(...)`
- que chama `carregarFeedMesaMobile(...)`
- que decide V2 vs legado em `android/src/config/mesaApi.ts`
- é a mesma fonte de verdade usada pela camada V2 de leitura do app

### 8. A central usa um caminho/repository diferente do feed/thread esperado e ignora a config V2

Conclusão:

- falso

Diagnóstico:

- a auditoria do fluxo confirmou:
  - `useActivityCenterController`
  - `runMonitorActivityFlow`
  - `carregarFeedMesaMobile`
  - `mesaApi.ts`
- não havia repository oculto separado para a central

## Causa raiz

A causa exata era:

- `android/src/config/mobileV2Config.ts` lia a env V2 por acesso dinâmico:
  - `process.env[ANDROID_V2_READ_CONTRACTS_FLAG]`
- no runtime do Expo preview/release, isso não garante inlining de `EXPO_PUBLIC_*`
- o valor efetivo da flag no bundle ficava ausente
- o parser tratava o valor ausente como `false`
- `mesaApi.ts` então escolhia `legacy`

## Correção mínima aplicada

### 1. Leitura estática e snapshot explícito da flag

Arquivo:

- `android/src/config/mobileV2Config.ts`

Mudanças:

- a leitura principal passou para:
  - `process.env.EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED`
- foi criado `getAndroidV2ReadContractsRuntimeSnapshot()`
- o snapshot materializa:
  - `envKey`
  - `rawValue`
  - `normalizedValue`
  - `enabled`
  - `parser`
  - `source`

Objetivo:

- provar o valor real da flag dentro do app executado
- evitar dependência de inferência pelo `.env`

### 2. Prova automatizável persistente do valor em runtime

Arquivos:

- `android/src/features/common/mobilePilotAutomationDiagnostics.ts`
- `android/src/features/InspectorMobileApp.tsx`
- `scripts/run_mobile_pilot_runner.py`

Mudanças:

- o marker global `pilot_selection_probe` passou a carregar:
  - `runtime_flag_enabled`
  - `runtime_flag_raw_value`
  - `runtime_flag_source`
- isso mantém a prova da flag mesmo depois que a central fecha e a automação segue para a thread
- o runner passou a parsear e salvar esses campos em:
  - `ui_marker_summary.json`
  - `request_trace_gap_summary.json`
  - `final_report.md`

### 3. Prova explícita do motivo da decisão da central

Arquivos:

- `android/src/config/mobilePilotRequestTrace.ts`
- `android/src/config/mesaApi.ts`
- `android/src/features/common/mobilePilotAutomationDiagnostics.ts`
- `scripts/run_mobile_pilot_runner.py`

Mudanças:

- o trace da central passou a materializar:
  - `contractFlagRawValue`
  - `contractFlagSource`
  - `decisionReason`
  - `decisionSource`
  - `fallbackReason`
- o probe da central e o runner agora diferenciam:
  - flag local desligada
  - decisão local V2
  - fallback V2 -> legado
  - negação remota/rollout

### 4. Reprodutibilidade do build preview

Arquivos:

- `android/scripts/run-android-preview.cjs`
- `android/scripts/run-android-dev.cjs`

Mudanças:

- os scripts passaram a carregar explicitamente `EXPO_PUBLIC_*` de `android/.env`
- a rodada salva em log:
  - `Usando Android V2 preview flag=<valor>`

Isso reduz ambiguidade operacional sem alterar o fluxo padrão do time.

## Comando correto de build/execução após o patch

Para o preview local reprodutível:

- `cd android && npm run android:preview`

Para a rodada operacional completa:

- `python3 scripts/run_mobile_pilot_runner.py`

Prova esperada no artefato:

- `android_install.log` com `Usando Android V2 preview flag=1`
- `ui_marker_summary.json` com:
  - `runtime_flag_enabled=true`
  - `runtime_flag_raw_value=1`
  - `runtime_flag_source=expo_public_env`

## Validações executadas

- `cd android && npm test -- --runInBand src/config/mobileV2Config.test.ts src/config/mesaApi.test.ts src/features/common/mobilePilotAutomationDiagnostics.test.ts src/features/activity/monitorActivityFlow.test.ts src/features/activity/useActivityCenterController.test.ts`
- `cd android && npm run typecheck`
- `python3 -m py_compile scripts/run_mobile_pilot_runner.py`
- `python3 -m pytest -q web/tests/test_smoke.py`

Resultado:

- Jest: `30 passed`
- typecheck: `ok`
- py_compile: `ok`
- pytest smoke: `26 passed`

## Execução operacional real desta fase

### Rodada intermediária

Artefato:

- `artifacts/mobile_pilot_run/20260327_070529/`

Resultado:

- a prova do caminho V2 já apareceu no Maestro e no backend
- mas o dump final ainda não preservava o valor bruto da flag, porque a central já tinha sido fechada

### Rodada autoritativa final

Artefato:

- `artifacts/mobile_pilot_run/20260327_071448/`

Provas coletadas:

- `android_install.log`
  - `Usando Android V2 preview flag=1`
- `ui_marker_summary.json`
  - `runtime_flag_enabled=true`
  - `runtime_flag_raw_value=1`
  - `runtime_flag_source=expo_public_env`
  - `selection_probe.activity_center_delivery=v2`
- `maestro_run.txt`
  - `activity-center-feed-v2-served ... COMPLETED`
  - `mesa-thread-surface ... COMPLETED`
- `backend_summary_after.json`
  - `v2_served=7`
  - `legacy_fallbacks=0`
  - `rollout_denied=0`
  - `covered_surfaces=["feed","thread"]`
  - `operator_run_outcome=completed_successfully`
  - `human_confirmed_required_coverage_met=true`
- `final_report.md`
  - `result=success_human_confirmed`

## Resultado honesto da fase

Entregas fechadas:

- diagnóstico exato de onde a flag se perdia: sim
- prova automatizável do valor real da flag em runtime: sim
- prova automatizável do caminho V2 escolhido: sim
- correção mínima e segura: sim
- rerun operacional real após a correção: sim

Classificação factual desta rodada final:

- `success_human_confirmed`

Leitura equivalente para o objetivo técnico desta fase:

- a flag V2 ficou ativa no app executado
- o app entrou no caminho V2 elegível
- `v2_served > 0`
- `human_ack > 0`
- `feed` e `thread` ficaram cobertos

## Riscos remanescentes

- o dump final preserva a prova global da flag e da entrega V2, mas o trace detalhado da central continua dependente de ela ainda estar aberta no último dump
- o tenant demo continua em trilha de validação local; esta fase não promove tenant real nem altera rollout

## Próximo passo recomendado

Executar a próxima fase operacional que consome a trilha já corrigida, sem reabrir a hipótese da flag local:

- runner operacional posterior focado em continuidade de validação/promoção controlada, usando os artefatos de `20260327_071448/` como baseline
