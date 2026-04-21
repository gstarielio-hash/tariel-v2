# Epic 09A - adocao opt-in do contrato publico mobile V2 no app Android

## Objetivo

Fazer o app Android real consumir de forma opt-in e reversivel os contratos publicos:

- `MobileInspectorFeedV2`
- `MobileInspectorThreadV2`

Sem:

- quebrar o app Android atual;
- alterar a UX;
- remover o caminho legado;
- tocar o backend ja validado;
- expor visibilidade alem do papel `Inspetor`.

## Onde o app Android foi encontrado

O app Android estava acessivel neste workspace em:

- `android/`

Tecnologia real encontrada:

- `React Native + Expo`
- codigo de produto em `android/src`
- projeto nativo Android em `android/android`

Sinais auditados antes da implementacao:

- `android/android/settings.gradle`
- `android/android/build.gradle`
- `android/android/app/build.gradle`
- `android/src/config/mesaApi.ts`
- `android/src/features/mesa/useMesaController.ts`
- `android/src/features/activity/monitorActivityFlow.ts`
- `android/src/types/mobile.ts`

## Ponto de integracao escolhido

O corte mais seguro no app ficou em:

- `android/src/config/mesaApi.ts`

Motivo:

- e a camada de rede realmente usada pelo app para o feed e para a thread da mesa;
- `useMesaController` e `monitorActivityFlow` ja consomem esse modulo;
- permite manter o retorno legado para a UI atual;
- concentra flag, parse, mapper e fallback sem espalhar condicoes em tela, controller ou estado local.

## O que foi implementado

Arquivos adicionados ou alterados:

- `android/src/config/mobileV2Config.ts`
- `android/src/config/mobileV2MesaAdapter.ts`
- `android/src/config/mesaApi.ts`
- `android/src/types/mobileV2.ts`
- `android/src/config/mobileV2MesaAdapter.test.ts`
- `android/src/config/mesaApi.test.ts`
- `android/.env.example`

## Contratos V2 adicionados no app

Foram criados DTOs tipados para o cliente mobile:

- `MobileInspectorCaseCardV2`
- `MobileInspectorReviewSignalsV2`
- `MobileInspectorInteractionSummaryV2`
- `MobileInspectorFeedItemV2`
- `MobileInspectorFeedV2`
- `MobileInspectorThreadMessageV2`
- `MobileInspectorThreadSyncV2`
- `MobileInspectorThreadV2`

Esses DTOs fazem parse explicito do payload V2 e rejeitam:

- `contract_name` inesperado;
- `contract_version` diferente de `v2`;
- `visibility_scope` fora de `inspetor_mobile`;
- `actor_role` fora de `inspetor` ou `mesa`;
- ausencia de identificadores necessarios para compatibilidade com a UI atual.

## Como o app passou a usar o V2

Quando a flag do app esta desligada:

- `carregarFeedMesaMobile(...)` usa o endpoint legado `/app/api/mobile/mesa/feed`;
- `carregarMensagensMesaMobile(...)` usa o endpoint legado `/app/api/laudo/{laudo_id}/mesa/mensagens`.

Quando a flag do app esta ligada:

1. o app tenta primeiro:
   - `GET /app/api/mobile/v2/mesa/feed`
   - `GET /app/api/mobile/v2/laudo/{laudo_id}/mesa/mensagens`
2. o payload V2 e parseado e validado;
3. o mapper converte o contrato V2 para:
   - `MobileMesaFeedResponse`
   - `MobileMesaMensagensResponse`
4. a UI atual continua recebendo os mesmos tipos legados de antes.

## Mapper V2 -> modelos atuais da UI

O mapper de compatibilidade reconstrói:

- `MobileMesaFeedResponse` a partir de `MobileInspectorFeedV2`
- `MobileMesaMensagensResponse` a partir de `MobileInspectorThreadV2`
- `MobileMesaMessage` a partir de `MobileInspectorThreadMessageV2`

Campos preservados para a UI atual:

- ids legados (`legacy_laudo_id`, `message_id`)
- ordenacao da thread
- cursores de sync (`cursor_proximo`, `cursor_ultimo_id`, `sync`)
- `estado`, `status_card`, `permite_edicao`, `permite_reabrir`
- resumo de mesa (`total_mensagens`, `mensagens_nao_lidas`, `pendencias_*`)
- `client_message_id`, `referencia_mensagem_id` e anexos

Campos V2 nao promovidos para a UX atual nesta fase:

- `policy_summary`
- `document_readiness`
- `document_blockers`
- qualquer metadado fora do payload legado ja esperado pela UI

## Fallback implementado

O fallback do cliente agora e automatico e transparente:

- flag desligada -> legado puro
- flag ligada -> tenta V2
- erro `404`, falha HTTP, erro de parse, incompatibilidade estrutural ou violacao de visibilidade -> fallback imediato para o legado

Isso foi implementado somente no app, sem tocar o backend.

## Feature flag do app

Nova flag local do cliente:

- `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED`

Comportamento:

- `0` ou ausente: app continua no legado
- `1`: app tenta V2 para feed/thread de mesa

Arquivo atualizado para ativacao local segura:

- `android/.env.example`

## Telemetria discreta no app

Quando a flag do app esta ligada, o cliente registra eventos discretos de observabilidade:

- `mesa_feed_v2_read`
- `mesa_thread_v2_read`

Detalhes registrados:

- `used_v2`
- `fallback_legacy:<motivo>`
- `legacy_failed:<motivo>`

Esses eventos nao mudam a UX e nao interrompem o fluxo principal.

## O que nao mudou

- a UI do app Android
- o contrato legado retornado para a UI atual
- os endpoints legados
- os comandos de escrita do app
- auth, session e multiportal
- o backend ja validado

## Rollback

Rollback rapido no app:

1. definir `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED=0` ou remover a variavel;
2. rebuild/reload do app;
3. o cliente volta imediatamente a usar apenas os endpoints legados.

Rollback adicional no backend, se desejado:

1. desligar `TARIEL_V2_ANDROID_PUBLIC_CONTRACT`;
2. as rotas `/app/api/mobile/v2/...` deixam de responder;
3. o app com fallback volta a operar pelo legado.

## O que ainda falta antes do V2 virar padrao no app

- rollout por tenant/coorte real no cliente
- observar fallback/uso V2 em ambiente piloto
- definir criterio de promocao para ligar a flag por padrao
- evoluir eventual contrato V2 de escrita/comandos, se isso entrar no roadmap
- remover o legado apenas depois de estabilidade comprovada

## Validacoes rodadas

- `npm run typecheck`
- `npm run test -- --runInBand src/config/mesaApi.test.ts src/config/mobileV2MesaAdapter.test.ts`
- `npm run lint`
- `python3 -m pytest -q web/tests/test_v2_android_public_contract.py`
- `python3 -m pytest -q web/tests/test_smoke.py`
