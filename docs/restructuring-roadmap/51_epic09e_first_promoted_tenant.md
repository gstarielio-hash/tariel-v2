# Epic 09E - primeiro tenant promovido com runbook operacional e janela de rollback

## Objetivo

Executar a primeira promocao controlada real do mobile V2 em um tenant explicitamente seguro, mantendo:

- endpoints legados intactos;
- payloads legados intactos;
- UX do app Android intacta;
- fallback automatico;
- controle por tenant/superficie;
- rollback rapido durante uma janela formal do piloto.

## Tenant promovido nesta fase

Tenant escolhido:

- `empresa_id=1`
- `Empresa Demo (DEV)`

Por que ele foi considerado seguro:

- existe como seed explicito de desenvolvimento em `web/app/shared/db/bootstrap.py`;
- usa o CNPJ placeholder `00000000000000`;
- existe no banco local real `web/tariel_admin (1).db`;
- possui usuarios `Inspetor` ativos, portanto consegue consumir o app mobile real;
- e mais conservador do que promover o tenant de carga local na primeira janela operacional.

Tenant seguro tambem encontrado, mas nao escolhido como primeiro piloto:

- `empresa_id=2`
- `Tariel.ia Lab Carga Local`
- mantido como opcao de carga/teste, nao como primeiro promoted do piloto mobile.

## Promocao aplicada

Promocao local efetiva configurada em `web/.env`:

- `TARIEL_V2_ANDROID_PUBLIC_CONTRACT=1`
- `TARIEL_V2_ANDROID_ROLLOUT=1`
- `TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY=1`
- `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=pilot_enabled`
- `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=promoted,1:thread=promoted`
- `TARIEL_V2_ANDROID_PILOT_TENANT_KEY=1`
- `TARIEL_V2_ANDROID_PILOT_PROMOTED_SINCE=2026-03-25T22:40:00Z`
- `TARIEL_V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT=2026-03-25T22:40:00Z`
- `TARIEL_V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS=24`
- `TARIEL_V2_ANDROID_PILOT_SOURCE=seed_dev_demo_company`
- `TARIEL_V2_ANDROID_PILOT_NOTE=first_local_pilot`

Superficies promovidas:

- `feed`
- `thread`

## Janela formal de rollback

Janela configurada:

- inicio formal: `2026-03-25T22:40:00Z`
- fim da janela: `2026-03-26T22:40:00Z`
- duracao: `24h`

Comportamento operacional:

- durante a janela, o summary admin passa a expor `rollback_window_active`;
- o app Android usa cache mais curto para `capabilities` quando a superficie promovida ainda esta dentro da janela;
- se o estado mudar para `hold` ou `rollback_forced`, o app volta ao legado na proxima reavaliacao curta do gate.

## Observabilidade operacional do piloto

Endpoint principal:

- `GET /admin/api/mobile-v2-rollout/summary`

Campos novos relevantes para 09E:

- `first_promoted_tenant`
- `tenant_rollout_states`
- `tenant_surface_states`
- `promotion_thresholds`

Para o tenant promovido, o summary agora deixa claro:

- qual tenant esta no piloto formal;
- quais superficies estao `promoted`, `hold` ou `rollback_forced`;
- `promoted_since`;
- `rollout_window_started_at`;
- `rollback_window_until`;
- `rollback_window_active`;
- `promotion_source`;
- `promotion_note`;
- `health_status` e `health_reason`;
- volume observado de requests V2;
- volume de fallback legado.

Telemetria discreta preservada:

- o backend continua agregando `v2_served` e `legacy_fallbacks` por tenant/superficie;
- leituras V2 agora carregam no agregado o estado da superficie (`promoted`, `pilot_enabled`, `candidate_for_promotion`), o que facilita confirmar se o tenant promovido esta realmente usando V2.

## Comportamento do app Android

O app continua sem mudanca de UX.

Com a flag local ligada em `android/.env`:

- `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED=1`

o cliente:

- usa V2 normalmente quando a superficie estiver em `promoted`;
- continua aceitando `pilot_enabled` e `candidate_for_promotion`;
- cai imediatamente para legado quando receber `hold` ou `rollback_forced`;
- usa TTL menor durante a janela formal de rollback do tenant promovido;
- invalida cache apos falha real de leitura V2, preservando o fallback automatico.

## Runbook operacional

### Antes de acompanhar o piloto

1. confirmar que o backend foi reiniciado para recarregar `web/.env`;
2. autenticar com um `Inspetor` do tenant `Empresa Demo (DEV)`;
3. garantir que o app local esteja com `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED=1`.

### Durante a janela

1. consultar `GET /admin/api/mobile-v2-rollout/summary`;
2. verificar `first_promoted_tenant.tenant_key=1`;
3. confirmar `promoted_surfaces` contendo `feed` e `thread`;
4. acompanhar `v2_served`, `legacy_fallbacks`, `health_status` e `health_reason`;
5. manter o piloto somente se o estado permanecer `healthy` ou sem sinais de atencao relevantes.

### Hold imediato

Para segurar sem remover o tenant do piloto:

- `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=hold,1:thread=hold`

Ou segurar apenas uma superficie:

- `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:thread=hold`

### Rollback forcado

Rollback por superficie:

- `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=rollback_forced,1:thread=rollback_forced`

Rollback completo para legado:

- `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=legacy_only`

Kill-switch global:

- `TARIEL_V2_ANDROID_ROLLOUT=0`

## O que ainda falta antes de ampliar a promocao

- ter historico persistente, e nao apenas agregacao em memoria;
- formalizar um workflow administrativo para promoted/hold/rollback sem depender de env;
- decidir o criterio de saida do piloto para tenants reais fora do ambiente demo/local;
- promover um segundo tenant seguro com comparacao operacional entre demo e carga local.
