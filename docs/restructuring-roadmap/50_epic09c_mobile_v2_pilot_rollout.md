# Epic 09C - piloto controlado por tenant do mobile V2 com agregacao operacional de fallback

## Objetivo

Operacionalizar o rollout mobile V2 ja existente como piloto real por tenant/coorte, sem:

- alterar UX do app Android;
- tocar nos endpoints e payloads legados;
- mudar auth, session, multiportal ou regras de negocio;
- remover o caminho legado;
- obrigar adocao global do V2.

## Estrategia de piloto adotada

O piloto continua apoiado em duas guardas:

1. flag local do app `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED`;
2. gate remoto `GET /app/api/mobile/v2/capabilities`.

O backend endureceu a decisao para expor metadado operacional suficiente ao app e a observabilidade:

- allowlist por tenant via `TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST`;
- allowlist por coorte estavel via `TARIEL_V2_ANDROID_ROLLOUT_COHORT_ALLOWLIST`;
- rollout percentual conservador via `TARIEL_V2_ANDROID_ROLLOUT_PERCENT`;
- switches separados por superficie:
  - `TARIEL_V2_ANDROID_FEED_ENABLED`
  - `TARIEL_V2_ANDROID_THREAD_ENABLED`
- versao de capabilities e bucket de rollout expostos ao cliente:
  - `capabilities_version`
  - `rollout_bucket`

## Backend implementado

Arquivos centrais:

- `web/app/v2/mobile_rollout.py`
- `web/app/v2/mobile_rollout_metrics.py`
- `web/app/domains/chat/mesa.py`
- `web/app/domains/admin/routes.py`

Melhorias feitas:

- o modelo de capabilities agora diferencia `tenant_allowed`, `cohort_allowed`, `rollout_reason` e `rollout_bucket`;
- feed e thread continuam com gate separado, mas agora com metrica operacional agregada;
- foi criada agregacao leve em memoria com contadores limitados e ultimos eventos resumidos;
- o backend registra:
  - checks de capabilities;
  - negativas de rollout por endpoint;
  - requests V2 efetivamente servidos;
  - fallbacks para legado por razao resumida.

Essa agregacao nao guarda mensagens, payloads nem dados sensiveis do conteudo da mesa.

## Observabilidade do piloto

Superficie escolhida:

- `GET /admin/api/mobile-v2-rollout/summary`

Protecoes:

- exige sessao valida do Admin-CEO;
- depende da flag `TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY`;
- nao e exposta ao app mobile;
- devolve apenas resumo agregado:
  - totais;
  - por tenant;
  - por endpoint;
  - por reason;
  - por bucket/coorte;
  - ultimos eventos resumidos.

## App Android

Arquivos centrais:

- `android/src/config/mobileV2Rollout.ts`
- `android/src/config/mesaApi.ts`
- `android/src/features/common/buildRefreshAction.ts`
- `android/src/features/session/useInspectorSession.ts`

Melhorias feitas:

- o cache do gate remoto passou a ter TTL explicito de `15_000 ms`;
- o cache agora pode ser invalidado por sessao e por refresh manual;
- o app envia metadata discreta nas leituras V2 e nos fallbacks:
  - `X-Tariel-Mobile-V2-Attempted`
  - `X-Tariel-Mobile-V2-Route`
  - `X-Tariel-Mobile-V2-Capabilities-Version`
  - `X-Tariel-Mobile-V2-Rollout-Bucket`
  - `X-Tariel-Mobile-V2-Fallback-Reason`
  - `X-Tariel-Mobile-V2-Gate-Source`
- as razoes de fallback ficaram padronizadas:
  - `rollout_denied`
  - `rollout_unknown`
  - `capabilities_fetch_error`
  - `http_404`
  - `http_error`
  - `parse_error`
  - `visibility_violation`
  - `adapter_error`
  - `unknown`

O app continua conservador:

1. flag local desligada -> legado;
2. gate remoto nega -> legado;
3. gate remoto falha -> legado;
4. V2 falha -> legado.

## Cache e refresh

Politica adotada nesta fase:

- cache em memoria por token;
- TTL curto de 15 segundos;
- invalidacao explicita:
  - no bootstrap da sessao;
  - no refresh manual;
  - no logout.

Isso reduz a janela de decisao velha sem transformar o gate remoto em dependencia obrigatoria persistida.

## Rollback

Rollback rapido:

1. desligar `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED` no app;
2. desligar `TARIEL_V2_ANDROID_ROLLOUT` para negar o gate remoto;
3. desligar `TARIEL_V2_ANDROID_PUBLIC_CONTRACT` para indisponibilizar as rotas publicas V2;
4. desligar `TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY` se for necessario ocultar o resumo operacional do painel admin.

Nenhum desses passos altera UX ou exige mexer no legado.

## O que ainda falta antes de ampliar o piloto

- definir tenants/coortes reais de piloto acompanhados operacionalmente;
- validar thresholds operacionais para promocao do V2 por superficie;
- decidir se o resumo agregado deve ganhar exportacao ou integracao com observabilidade externa;
- preparar criterio de saida da fase em que feed/thread V2 possam ser habilitados por tenant com menor supervisao manual.
