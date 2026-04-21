# Epic 09J - validacao organica com confirmacao humana

## Objetivo

Permitir que uso humano real do app Android no tenant demo promovido conte como evidencia organica validavel, separado de probe sintetico e separado de request tecnico sem renderizacao confirmada.

## O que foi implementado

- Endpoint autenticado e side-effect free para `ack` humano:
  - `POST /app/api/mobile/v2/organic-validation/ack`
  - aceita apenas:
    - sessao organica ativa
    - tenant demo seguro atual
    - `surface` em `feed` ou `thread`
    - `target_id` elegivel
    - `checkpoint_kind` em `rendered`, `opened` ou `viewed`
  - a rota so atualiza observabilidade da sessao organica
- Modelo canonico de confirmacao humana no backend:
  - `MobileOrganicHumanCheckpoint`
  - `MobileOrganicHumanSurfaceSummary`
  - confirmacoes ficam em memoria, associadas ao `organic_validation_session_id`
  - cada confirmacao registra:
    - tenant
    - session_id
    - surface
    - target_id
    - checkpoint_kind
    - `confirmed_at`
    - `source_channel=android_app`
    - `delivery_mode`
- Summary organico enriquecido:
  - `human_confirmed_count`
  - `human_confirmed_targets`
  - `human_confirmed_last_seen_at`
  - `human_confirmed_required_coverage_met`
  - `human_confirmed_surface_summaries`
  - por superficie o summary agora tambem expõe:
    - `human_confirmed_count`
    - `human_confirmed_targets`
    - `human_confirmed_last_seen_at`
    - `human_confirmed_required_coverage_met`
    - `legacy_rendered_under_validation_count`
- Regra endurecida para `candidate_ready_for_real_tenant`:
  - requests organicos e cobertura tecnica continuam obrigatorios
  - `candidate_ready_for_real_tenant` so sobe quando `feed` e `thread` tiverem cobertura minima **e** confirmacao humana valida
  - sem `human_confirmed`, o estado pode ficar `healthy`, mas nao vira candidato

## Onde o app dispara o ack

- Thread:
  - `android/src/features/mesa/useMesaController.ts`
  - a leitura da thread da mesa recebe metadado interno de origem (`v2` vs `legacy`)
  - `android/src/features/InspectorMobileApp.tsx` envia o `ack` apenas quando:
    - a aba `mesa` esta aberta
    - existem mensagens realmente renderizadas
    - a leitura veio de V2
    - existe sessao organica ativa
- Feed:
  - o endpoint `mesa/feed` continua sendo exercitado pelo monitor de atividade
  - `android/src/features/activity/monitorActivityFlow.ts` preserva o metadado interno da ultima leitura do feed
  - `android/src/features/InspectorMobileApp.tsx` envia o `ack` do feed apenas quando:
    - a central de atividade esta aberta
    - ha alvos reais da mesa na lista visivel
    - a ultima leitura do feed veio de V2
    - existe sessao organica ativa

## Como o app propaga isso sem mudar UX

- O app nao mostra tela nova e nao depende do `ack` para funcionar.
- O `ack` usa o mesmo `session_id` organico que ja vinha do capabilities.
- O request do `ack` leva headers tecnicos consistentes com a sessao:
  - `X-Tariel-Mobile-Usage-Mode=organic_validation`
  - `X-Tariel-Mobile-Validation-Session=<session_id>`
- Falhas no `ack` sao ignoradas silenciosamente.

## Como ler o summary

Consultar:

- `GET /admin/api/mobile-v2-rollout/summary`

Interpretacao relevante:

- `organic_validation_outcome`
  - estado tecnico geral da sessao organica
- `human_confirmed_required_coverage_met`
  - `true` so quando `feed` e `thread` ja tiveram confirmacao humana valida minima
- `human_confirmed_surface_summaries`
  - mostra por superficie quais alvos foram confirmados e quando
- `candidate_ready_for_real_tenant`
  - agora depende de criterios tecnicos + cobertura humana minima

## Rollback

- Encerrar a sessao organica:
  - `POST /admin/api/mobile-v2-rollout/organic-validation/stop`
- Voltar o tenant demo ao legado:
  - `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=legacy_only`
- Voltar uma superficie especifica ao legado:
  - `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=rollback_forced,1:thread=rollback_forced`

## Estado atual desta fase

- Nenhum tenant real foi promovido.
- O mecanismo de confirmacao humana foi implementado de ponta a ponta.
- Nenhuma confirmacao humana sintetica foi injetada nesta fase.
- O tenant demo continua conservador ate existir uso humano real do app durante uma sessao organica ativa.

## O que ainda falta antes de qualquer tenant real

- uso humano real do app no tenant demo cobrindo `feed` e `thread`
- confirmacoes humanas validas registradas no summary
- evidencia organica suficiente, com fallback aceitavel
- somente depois disso o demo pode virar base para discutir um candidato real
