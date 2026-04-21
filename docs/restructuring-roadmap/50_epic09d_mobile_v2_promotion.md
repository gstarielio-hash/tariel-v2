# Epic 09D - promocao controlada do piloto mobile V2 por tenant e superficie

## Objetivo

Transformar o rollout tecnico do mobile V2 em um piloto operacionalmente governavel, sem:

- alterar endpoints legados;
- alterar payloads legados;
- alterar UX do app Android;
- remover fallback;
- forcar adocao global;
- criar banco novo.

O foco desta fase foi explicitar `estado`, `prontidao de promocao`, `hold` e `rollback` por tenant/superficie sobre a base ja entregue em 09A/09B.

## Estados de rollout implementados

Estados canonicos no backend:

- `legacy_only`
- `pilot_enabled`
- `candidate_for_promotion`
- `promoted`
- `hold`
- `rollback_forced`

Superficies governadas nesta fase:

- `feed`
- `thread`

Modelos adicionados na implementacao:

- `MobileV2RolloutState`
- `MobileV2SurfaceState`
- `MobileV2PromotionReadiness`

## Como o estado e resolvido

O backend agora resolve o rollout em tres camadas:

1. `estado base do tenant`
   - derivado de:
     - `TARIEL_V2_ANDROID_PUBLIC_CONTRACT`
     - `TARIEL_V2_ANDROID_ROLLOUT`
     - `TARIEL_V2_ANDROID_ROLLOUT_TENANT_ALLOWLIST`
     - `TARIEL_V2_ANDROID_ROLLOUT_COHORT_ALLOWLIST`
     - `TARIEL_V2_ANDROID_ROLLOUT_PERCENT`
2. `override explicito por tenant`
   - `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES`
   - formato: `33=promoted,44=hold`
3. `override explicito por tenant/superficie`
   - `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES`
   - formato: `33:feed=promoted,33:thread=hold,44:thread=rollback_forced`

As flags globais de superficie continuam existindo como kill-switch conservador:

- `TARIEL_V2_ANDROID_FEED_ENABLED`
- `TARIEL_V2_ANDROID_THREAD_ENABLED`

## Criterio operacional de promocao

A promocao automatica continua desabilitada.

O backend apenas calcula `promotion_readiness` por tenant/superficie usando a agregacao em memoria ja existente, com:

- `observed_requests`
- `v2_served`
- `legacy_fallbacks` reais
- `rollout_denied`
- `parse_errors`
- `visibility_errors`
- `service_errors`
- `fallback_rate`

Thresholds configuraveis:

- `TARIEL_V2_ANDROID_PROMOTION_MIN_REQUESTS`
- `TARIEL_V2_ANDROID_PROMOTION_MAX_FALLBACK_RATE_PERCENT`
- `TARIEL_V2_ANDROID_PROMOTION_MAX_SERVICE_ERRORS`
- `TARIEL_V2_ANDROID_PROMOTION_MAX_PARSE_VISIBILITY_ERRORS`

Regras codificadas:

- sem volume minimo -> nao promove;
- fallback rate acima do limite -> nao promove;
- parse/visibility acima do limite -> nao promove;
- erros de estabilidade acima do limite -> nao promove;
- quando tudo passa e o estado configurado ainda e `pilot_enabled`, a superficie passa a expor `candidate_for_promotion`.

`promoted` continua exigindo override operacional explicito.

## Observabilidade expandida

O resumo admin existente foi expandido em:

- `GET /admin/api/mobile-v2-rollout/summary`

Guardas mantidas:

- sessao `Admin-CEO`
- flag `TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY`

Campos novos adicionados ao resumo:

- `tenant_rollout_states`
- `tenant_surface_states`
- `promotion_thresholds`

Cada linha por superficie agora traz:

- `rollout_state`
- `configured_state`
- `surface_state`
- `enabled`
- `candidate_for_promotion`
- `promoted`
- `hold`
- `rollback_forced`
- `promotion_readiness`
- `legacy_fallback_reasons`
- `rollout_denied_reasons`

O resumo continua seguro:

- sem conteudo tecnico bruto;
- sem texto de mensagem;
- sem anexos;
- sem payload legado do caso.

## Capabilities enriquecido

`GET /app/api/mobile/v2/capabilities` continua sendo o gate remoto do app, mas agora devolve tambem:

- `rollout_state`
- `feed_rollout_state`
- `thread_rollout_state`
- `feed_candidate_for_promotion`
- `thread_candidate_for_promotion`
- `feed_promoted`
- `thread_promoted`
- `feed_hold`
- `thread_hold`
- `feed_rollback_forced`
- `thread_rollback_forced`

Os campos antigos foram preservados:

- `mobile_v2_reads_enabled`
- `mobile_v2_feed_enabled`
- `mobile_v2_thread_enabled`
- `reason`
- `source`
- `feed_reason`
- `thread_reason`

## Como o app Android passou a respeitar os estados

O app continua simples e sem mudanca de UX:

- usa V2 apenas quando `feed/thread` estao em:
  - `pilot_enabled`
  - `candidate_for_promotion`
  - `promoted`
- cai para legado quando recebe:
  - `legacy_only`
  - `hold`
  - `rollback_forced`

O parser do app continua compativel com backends anteriores:

- se os campos novos de estado nao vierem, o cliente infere o comportamento pelos booleans antigos;
- se os campos vierem invalidos, o cliente degrada para legado.

## Cache do app

O cache em memoria do capabilities foi mantido, mas ficou mais explicito:

- TTL padrao continua curto;
- estados `hold` e `rollback_forced` usam TTL de emergencia menor;
- qualquer falha real na leitura V2 invalida o cache para forcar reavaliacao antes da proxima tentativa.

Isso reduz a janela de uso de um estado antigo apos rollback operacional, sem persistencia extra em disco.

## Rollback operacional

Rollback rapido agora pode acontecer em niveis diferentes:

1. desligar tudo:
   - `TARIEL_V2_ANDROID_ROLLOUT=0`
2. remover o namespace publico V2:
   - `TARIEL_V2_ANDROID_PUBLIC_CONTRACT=0`
3. segurar um tenant inteiro:
   - `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=33=hold`
4. voltar um tenant inteiro para legado:
   - `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=33=legacy_only`
5. forcar rollback de uma superficie:
   - `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=33:thread=rollback_forced`
6. desligar uma superficie globalmente:
   - `TARIEL_V2_ANDROID_THREAD_ENABLED=0`

O app permanece com fallback automatico para o legado em todos esses cenarios.

## O que nao mudou

- endpoints legados do Android;
- payloads legados;
- UX do app;
- auth, session e multiportal;
- regras de negocio;
- ausencia de banco novo;
- adocao opt-in do app via `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED`.

## O que ainda falta antes de tornar V2 padrao para algum tenant

- acompanhar dados reais de piloto com volume operacional suficiente;
- definir tenant(s) reais de promocao explicita para `promoted`;
- decidir criterio de saida por tenant inteiro, e nao apenas por superficie;
- validar se o mesmo modelo deve governar futuros contratos mobile V2 de escrita/comandos.
