# Epic 09H - validacao organica assistida do tenant demo promovido

## Objetivo

Adicionar uma janela operacional explicita para observar apenas trafego organico do tenant demo promovido, sem:

- tocar em tenant real;
- promover tenant real;
- mudar UX do app Android;
- alterar payloads legados;
- transformar probe sintetico em evidencia organica.

## Tenant validado nesta fase

Tenant alvo:

- `empresa_id=1`
- `Empresa Demo (DEV)`

Motivo de seguranca:

- seed local explicito de desenvolvimento;
- CNPJ placeholder `00000000000000`;
- ja promovido de forma controlada em `feed` e `thread`;
- continua sendo o unico tenant permitido para esta sessao.

## Modelo implementado

Arquivo principal:

- `web/app/v2/mobile_organic_validation.py`

Modelos canonicos:

- `MobileV2OrganicValidationSession`
- `MobileV2OrganicValidationBaseline`
- `MobileV2OrganicSurfaceValidationSummary`
- `MobileV2OrganicValidationSummary`

Campos centrais da sessao:

- `tenant_key`
- `surfaces`
- `started_at`
- `expires_at`
- `ended_at`
- `active`
- `baselines`

Campos centrais da avaliacao:

- `organic_validation_outcome`
- `candidate_ready_for_real_tenant`
- `organic_validation_requests_v2`
- `organic_validation_requests_fallback`
- `organic_validation_fallback_rate`
- `organic_validation_reason_breakdown`
- `surface_coverage_summary`
- `probe_vs_organic_evidence`

## Como iniciar e encerrar

Rotas admin/local-only:

- `POST /admin/api/mobile-v2-rollout/organic-validation/start`
- `POST /admin/api/mobile-v2-rollout/organic-validation/stop`

Guard-rails:

- exige sessao Admin-CEO valida;
- exige host local controlado (`127.0.0.1`, `localhost`, `testclient`);
- exige que o tenant configurado em `TARIEL_V2_ANDROID_PILOT_TENANT_KEY` seja um tenant seguro;
- exige que `feed` e `thread` estejam promovidos no tenant demo.

Comportamento:

- `start` sempre abre uma nova sessao com baseline atual dos contadores organicos e dos contadores de probe;
- `stop` encerra a sessao sem forcar sucesso; se a janela nao transcorreu, `candidate_ready_for_real_tenant` continua bloqueado.

## Como o trafego organico e distinguido do probe

Nesta fase, o criterio operacional ficou:

- `probe` = requests marcados com `X-Tariel-Mobile-V2-Probe: 1`
- `organico` = requests mobile sem marcacao de probe

Como a sessao trata isso:

- contadores organicos sao calculados como `total - probe`;
- o baseline da sessao captura tambem os contadores de probe para calcular deltas separados;
- `probe_vs_organic_evidence` mostra se houve trafego apenas sintetico (`probe_only`), apenas organico (`organic_only`) ou misto (`mixed`);
- o probe continua ignorado para `candidate_ready_for_real_tenant`.

## Criterios da sessao organica

Thresholds configuraveis:

- `TARIEL_V2_ANDROID_ORGANIC_VALIDATION_WINDOW_MINUTES`
- `TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MIN_REQUESTS_PER_SURFACE`
- `TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_FALLBACK_RATE_PERCENT`
- `TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_VISIBILITY_VIOLATIONS`
- `TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_PARSE_ERRORS`
- `TARIEL_V2_ANDROID_ORGANIC_VALIDATION_MAX_HTTP_FAILURES`
- `TARIEL_V2_ANDROID_ORGANIC_VALIDATION_REQUIRE_FULL_WINDOW`

Outcomes possiveis:

- `insufficient_evidence`
- `observing`
- `healthy`
- `candidate_ready_for_real_tenant`
- `hold_recommended`
- `rollback_recommended`

Regras principais:

- sem trafego organico: `insufficient_evidence`;
- trafego parcial por superficie: `observing`;
- volume minimo por superficie com estabilidade, mas antes do fim da janela: `healthy`;
- parse/visibility acima do limite: `rollback_recommended`;
- fallback rate ou falhas HTTP acima do limite: `hold_recommended`;
- `candidate_ready_for_real_tenant` so quando `feed` e `thread` atingem cobertura minima organica e a janela exigida transcorreu.

## Como ler o summary

Endpoint principal:

- `GET /admin/api/mobile-v2-rollout/summary`

Campos novos no payload raiz:

- `organic_validation_active`
- `organic_validation_expired`
- `organic_validation_started_at`
- `organic_validation_ended_at`
- `organic_validation_expires_at`
- `organic_validation_window_elapsed`
- `organic_validation_outcome`
- `candidate_ready_for_real_tenant`
- `organic_validation_requests_v2`
- `organic_validation_requests_fallback`
- `organic_validation_fallback_rate`
- `organic_validation_reason_breakdown`
- `organic_validation_surface_summaries`
- `surface_coverage_summary`
- `probe_vs_organic_evidence`
- `organic_validation_thresholds`

Esses mesmos sinais tambem aparecem:

- em `first_promoted_tenant`;
- no row do tenant demo em `tenant_rollout_states`;
- por superficie em `tenant_surface_states`.

## Estado local observado nesta fase

Execucao local real feita durante a implementacao:

1. sessao organica aberta para `Empresa Demo (DEV)`;
2. probe controlado executado de novo no mesmo processo;
3. summary validado imediatamente apos a execucao.

Estado observado:

- `pilot_outcome=healthy`
- `organic_validation_outcome=insufficient_evidence`
- `probe_vs_organic_evidence.evidence_source=probe_only`
- `probe_requests_v2_since_start=10`
- `organic_requests_v2_since_start=0`
- `candidate_ready_for_real_tenant=false`

Interpretacao correta:

- o rollout V2 segue tecnicamente saudavel via probe;
- a sessao organica nao foi enganada pelo probe;
- ainda falta uso organico real do app no tenant demo antes de qualquer decisao sobre tenant real.

## Rollback e desligamento rapido

Encerrar observacao organica:

- `POST /admin/api/mobile-v2-rollout/organic-validation/stop`

Desligar o piloto V2 do tenant demo:

- `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=rollback_forced,1:thread=rollback_forced`
- ou `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=legacy_only`
- ou `TARIEL_V2_ANDROID_ROLLOUT=0`

## O que ainda falta antes de qualquer tenant real

- observar requests organicos reais do app em `feed` e `thread`;
- sair de `probe_only` em `probe_vs_organic_evidence`;
- manter a sessao sem `hold_recommended` e sem `rollback_recommended`;
- atingir `candidate_ready_for_real_tenant` no tenant demo antes de sequer discutir um candidato real.
