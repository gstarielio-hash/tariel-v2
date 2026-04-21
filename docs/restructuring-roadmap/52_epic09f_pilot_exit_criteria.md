# Epic 09F - acompanhamento pos-janela do tenant demo promovido e criterio formal de saida do piloto

## Objetivo

Transformar o tenant demo ja promovido em um piloto operacionalmente avaliavel, sem promover tenant real e sem mudar:

- endpoints legados;
- payloads legados;
- UX do app Android;
- regras de negocio;
- fallback automatico.

## Tenant avaliado nesta fase

Tenant acompanhado:

- `empresa_id=1`
- `Empresa Demo (DEV)`

Motivo de seguranca:

- e um seed explicito de desenvolvimento;
- usa CNPJ placeholder `00000000000000`;
- ja havia sido o tenant formalmente promovido no Epic 09E;
- nenhum tenant real foi inferido ou promovido nesta fase.

## Estado real observado apos a janela

Configuracao local atual em `web/.env`:

- `TARIEL_V2_ANDROID_PILOT_TENANT_KEY=1`
- `TARIEL_V2_ANDROID_PILOT_PROMOTED_SINCE=2026-03-23T22:40:00Z`
- `TARIEL_V2_ANDROID_PILOT_ROLLOUT_WINDOW_STARTED_AT=2026-03-23T22:40:00Z`
- `TARIEL_V2_ANDROID_PILOT_ROLLBACK_WINDOW_HOURS=24`

Com isso, o summary local passou a refletir um piloto de fato pos-janela:

- `rollback_window_active=false`
- `window_elapsed=true`
- `pilot_outcome=insufficient_evidence`
- `evaluation_reason=no_v2_traffic_observed`
- `candidate_for_real_tenant=false`

Ou seja:

- nao houve indicio tecnico de hold ou rollback automatico;
- mas tambem nao houve evidencia suficiente para considerar o piloto saudavel;
- e nenhum tenant real deve avancar a partir deste estado.

## Motor canonico de avaliacao do piloto

O backend agora calcula avaliacao explicita por superficie e por tenant agregado, usando:

- `MobileV2SurfaceEvaluation`
- `MobileV2PilotEvaluation`

Resultados canonicos implementados:

- `insufficient_evidence`
- `observing`
- `healthy`
- `attention`
- `hold_recommended`
- `rollback_recommended`
- `candidate_for_real_tenant`

## Criterios formais

Thresholds configuraveis:

- `TARIEL_V2_ANDROID_PILOT_MIN_REQUESTS`
- `TARIEL_V2_ANDROID_PILOT_MAX_FALLBACK_RATE_PERCENT`
- `TARIEL_V2_ANDROID_PILOT_MAX_VISIBILITY_VIOLATIONS`
- `TARIEL_V2_ANDROID_PILOT_MAX_PARSE_ERRORS`
- `TARIEL_V2_ANDROID_PILOT_MAX_HTTP_FAILURES`
- `TARIEL_V2_ANDROID_PILOT_REQUIRE_FULL_WINDOW`
- `TARIEL_V2_ANDROID_PILOT_ALLOW_CANDIDATE_WITHOUT_WINDOW_ELAPSED`

Regras conservadoras desta fase:

- sem trafego V2: `insufficient_evidence`;
- com trafego parcial antes do fim da janela: `observing`;
- com volume minimo e estabilidade: `healthy`;
- com fallback/falhas abaixo dos limites mas presentes: `attention`;
- com fallback acima do limite apos a janela ou `hold` explicito: `hold_recommended`;
- com parse/visibility acima do limite ou `rollback_forced` explicito: `rollback_recommended`;
- `candidate_for_real_tenant` so quando as superficies promovidas estiverem saudaveis, com janela cumprida e evidencia suficiente.

## Summary operacional enriquecido

Endpoint:

- `GET /admin/api/mobile-v2-rollout/summary`

Campos relevantes adicionados:

- `pilot_evaluation_thresholds`
- `tenant_rollout_states[].pilot_outcome`
- `tenant_rollout_states[].evidence_level`
- `tenant_rollout_states[].evaluation_reason`
- `tenant_rollout_states[].candidate_for_real_tenant`
- `tenant_rollout_states[].requires_hold`
- `tenant_rollout_states[].requires_rollback`
- `tenant_rollout_states[].window_elapsed`
- `tenant_rollout_states[].requests_v2_observed`
- `tenant_rollout_states[].requests_fallback_observed`
- `tenant_rollout_states[].fallback_rate`
- `tenant_rollout_states[].fallback_reason_breakdown`
- os mesmos campos por superficie em `tenant_surface_states[]`
- enriquecimento de `first_promoted_tenant` com o mesmo resumo executivo

Leitura operacional recomendada:

1. localizar `first_promoted_tenant`;
2. confirmar `window_elapsed=true`;
3. verificar `pilot_outcome`;
4. confirmar os outcomes de `feed` e `thread`;
5. se `candidate_for_real_tenant=false`, nao avancar para tenant real;
6. se `requires_hold=true` ou `requires_rollback=true`, interromper o piloto local.

## Telemetria discreta do app Android

O app continua sem analytics pesada nem mudanca de UX.

Melhorias feitas:

- motivos de fallback remoto agora diferenciam `legacy_only`, `hold`, `rollback_forced` e `route_disabled`;
- o backend deixa de confundir esses motivos de gate com falhas reais de parse/HTTP;
- os headers discretos de fallback continuam os mesmos, apenas com motivo mais util para operacao.

## Comportamento do app

Nada mudou para o usuario final.

Operacionalmente:

- `promoted` continua usando V2 quando a flag local permite;
- `hold` e `rollback_forced` derrubam para legado na proxima reavaliacao do gate;
- o cache curto durante a janela continua;
- fora da janela, o app permanece conservador e o fallback automatico segue intacto.

## Runbook desta fase

### Para avaliar o piloto demo

1. reiniciar o backend para recarregar `web/.env`;
2. consultar `GET /admin/api/mobile-v2-rollout/summary`;
3. confirmar `first_promoted_tenant.tenant_key=1`;
4. ler `pilot_outcome`, `evaluation_reason`, `window_elapsed`, `requests_v2_observed` e `requests_fallback_observed`;
5. checar `tenant_surface_states` de `feed` e `thread`.

### Se o piloto continuar sem evidencia

- manter `Empresa Demo (DEV)` como tenant local de observacao;
- nao promover tenant real;
- induzir trafego controlado do app com o tenant demo antes de qualquer nova decisao.

### Hold rapido

- `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=hold,1:thread=hold`

### Rollback rapido

- `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=rollback_forced,1:thread=rollback_forced`
- ou `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=legacy_only`
- ou `TARIEL_V2_ANDROID_ROLLOUT=0`

## O que ainda falta antes de qualquer tenant real

- gerar trafego real controlado no tenant demo para sair de `insufficient_evidence`;
- observar pelo menos um ciclo completo com uso de `feed` e `thread`;
- manter o piloto sem `hold_recommended` nem `rollback_recommended`;
- decidir a passagem para tenant real apenas depois de `candidate_for_real_tenant=true`.
