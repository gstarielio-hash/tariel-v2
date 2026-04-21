# Epic 09I - coleta organica guiada no tenant demo

## Objetivo

Transformar o uso humano real do app Android no tenant demo promovido em evidencia organica distinguivel do probe, sem mudar UX, sem tocar no legado e sem contar trafego sintetico como validacao organica.

## O que foi implementado

- Sessao organica identificavel no backend:
  - `web/app/v2/mobile_organic_validation.py`
  - cada sessao nasce com `organic_validation_session_id` no formato `orgv_<id>`
  - a sessao continua limitada ao tenant demo seguro e as superficies `feed` e `thread`
- Sinal organico exposto no gate remoto:
  - `GET /app/api/mobile/v2/capabilities`
  - campos aditivos:
    - `organic_validation_active`
    - `organic_validation_session_id`
    - `organic_validation_surfaces`
    - `organic_validation_target_suggestions`
    - `organic_validation_surface_coverage`
    - `organic_validation_has_partial_coverage`
    - `organic_validation_targets_ready`
- Propagacao discreta no app Android:
  - `android/src/config/mobileV2Rollout.ts`
  - `android/src/config/mesaApi.ts`
  - quando a sessao organica esta ativa para a rota, o app envia:
    - `X-Tariel-Mobile-Usage-Mode: organic_validation`
    - `X-Tariel-Mobile-Validation-Session: <session_id>`
  - isso vale para:
    - leitura V2 de `feed`
    - leitura V2 de `thread`
    - fallback legado subsequente dessas rotas, quando houver
- Classificacao de trafego no backend:
  - `probe`
  - `organic_validation`
  - `organic_general`
  - `legacy_fallback_from_validation`
  - `legacy_general`
- Cobertura organica por superficie e alvo:
  - o summary admin agora mede:
    - `organic_validation_surface_summaries`
    - `organic_validation_surface_coverage`
    - `organic_validation_distinct_targets`
    - `organic_validation_missing_targets`
    - `surface_coverage_summary`
    - `probe_vs_organic_evidence`

## Como iniciar e acompanhar

1. Iniciar sessao organica local/admin:
   - `POST /admin/api/mobile-v2-rollout/organic-validation/start`
2. Abrir o app Android real com:
   - `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED=1`
3. Consumir `feed` e `thread` no tenant demo `1 - Empresa Demo (DEV)`
4. Consultar:
   - `GET /admin/api/mobile-v2-rollout/summary`

## Como a cobertura e medida

- O backend so conta como validacao organica o request que chegar com:
  - `X-Tariel-Mobile-Usage-Mode=organic_validation`
  - `X-Tariel-Mobile-Validation-Session=<session_id_ativo>`
- O probe continua separado e nao sai de `insufficient_evidence` sozinho nesta avaliacao.
- A sessao organica agora mede:
  - deltas desde o baseline da abertura da sessao
  - cobertura por superficie
  - alvos sugeridos, cobertos e faltantes
  - fallback organico por superficie

## Regra de saida de `insufficient_evidence`

O tenant demo so sai de `insufficient_evidence` quando houver evidencia organica real suficiente dentro da sessao, incluindo:

- requests V2 organicos minimos por superficie
- cobertura minima de `feed`
- cobertura minima de `thread`
- pelo menos um alvo elegivel real coberto
- fallback dentro do limite configurado
- sem depender apenas de probe

## Rollback

- Encerrar sessao organica:
  - `POST /admin/api/mobile-v2-rollout/organic-validation/stop`
- Forcar legado por superficie:
  - `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=rollback_forced,1:thread=rollback_forced`
- Forcar tenant demo inteiro para legado:
  - `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=legacy_only`
  - ou `TARIEL_V2_ANDROID_ROLLOUT=0`

## Estado atual e limite desta fase

- Nenhum tenant real foi promovido.
- O tenant demo continua sendo o unico alvo.
- A fase fecha o loop tecnico backend -> app -> backend para evidencia organica.
- Ainda falta uso humano real do app no tenant demo para concluir a sessao com evidencia suficiente antes de qualquer candidato real.
