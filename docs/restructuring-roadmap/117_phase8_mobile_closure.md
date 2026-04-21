# Fase 08 - Mobile: fechamento operacional

Data: `2026-03-30`

## Objetivo fechado

Promover a `Fase 08 - Mobile` sem depender de smoke manual ad hoc para saber se o app sobe, autentica, retoma contexto e atravessa o trilho principal da Mesa.

## O que entrou neste fechamento

- bootstrap, histórico, chat e fila offline mantidos no app com baseline local estável
- registro operacional de dispositivo/push por tenant fechado no backend e no app, com snapshot exportável no diagnóstico
- `fetch` do auth mobile endurecido com timeout real e abort para não deixar o login pendurado em release
- persistência local de sessão desacoplada do gating visual do login, evitando travamento do shell por `SecureStore`
- probe discreto de login adicionado ao app e ao runner oficial para não perder o estágio da falha em futuras rodadas
- build/distribuição local institucionalizados no `Makefile` com `make mobile-baseline`, `make mobile-preview` e `make smoke-mobile`
- smoke real controlado institucionalizado em `python3 scripts/run_mobile_pilot_runner.py`

## Superfícies e arquivos-chave

- `android/src/config/apiCore.ts`
- `android/src/config/authApi.ts`
- `android/src/features/session/useInspectorSession.ts`
- `android/src/features/auth/LoginScreen.tsx`
- `android/src/features/auth/buildLoginScreenProps.ts`
- `android/src/features/settings/useSettingsOperationsActions.ts`
- `android/src/features/system/pushRegistration.ts`
- `android/src/features/system/usePushRegistrationController.ts`
- `android/src/config/pushApi.ts`
- `web/app/domains/chat/auth_mobile_routes.py`
- `web/app/domains/chat/auth_mobile_push_support.py`
- `web/app/domains/chat/auth_contracts.py`
- `web/app/shared/db/models_auth.py`
- `web/alembic/versions/b7d4c1e9a2f3_mobile_push_device_registry.py`
- `scripts/run_mobile_pilot_runner.py`
- `android/README.md`
- `Makefile`

## Evidência real gerada

Artifact autoritativo:

- `artifacts/mobile_pilot_run/20260330_203601/`

Resumo do artifact:

- `maestro_run.txt` verde de ponta a ponta
- `result=selected_laudo_confirmed`
- login concluído e `open-settings-button` visível no shell autenticado
- seleção do laudo confirmada no histórico com `selected_laudo_id=89`
- central de atividade e thread da Mesa renderizadas no mesmo fluxo
- `v2_served_total_after=2`

Arquivos úteis do artifact:

- `artifacts/mobile_pilot_run/20260330_203601/final_report.md`
- `artifacts/mobile_pilot_run/20260330_203601/maestro_run.txt`
- `artifacts/mobile_pilot_run/20260330_203601/ui_marker_summary.json`
- `artifacts/mobile_pilot_run/20260330_203601/backend_summary_after.json`
- `artifacts/mobile_pilot_run/20260330_203601/operator_run_status_after.json`

## Validação local

- `cd android && npm run typecheck`
- `cd android && npm run test -- --runInBand src/config/apiCore.test.ts src/config/authApi.test.ts src/features/session/useInspectorSession.test.ts src/features/session/useInspectorRootSession.test.ts src/features/session/useInspectorRootSessionFlow.test.ts src/features/common/buildInspectorScreenProps.test.ts`
- `python3 scripts/run_mobile_pilot_runner.py`

## Leitura operacional correta do resultado

- o smoke técnico controlado do mobile ficou verde e reproduzível
- a promoção da fase não depende mais de repetir login/histórico/mesa manualmente para descobrir se a APK funciona
- `candidate_ready_for_real_tenant` continua `false`, mas isso pertence à trilha separada de validação orgânica/humana do tenant demo
- essa trilha continua sendo guard-rail para qualquer tenant real, não bloqueio para encerrar a `Fase 08`

## Resultado

Com este slice:

- a `Fase 08 - Mobile` pode ser promovida com build local, smoke real controlado e push operacional explícitos
- o risco técnico do app deixa de depender de memória informal ou teste manual improvisado
- a frente principal volta para `Fase 09 - Documento, template e IA`
