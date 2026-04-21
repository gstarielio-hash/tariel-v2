# Epic 09K - operator validation run para sessao organica humana real

## Objetivo

Dar ao time interno um fluxo operacional minimo e controlado para executar uma rodada humana real do piloto mobile V2 no tenant demo, sem mudar UX, sem tocar em tenant real e sem depender de leitura manual de logs para concluir o que aconteceu.

## O que foi implementado

- Novo modulo operacional:
  - `web/app/v2/mobile_operator_run.py`
- Modelos canonicos:
  - `MobileOperatorValidationRun`
  - `MobileOperatorValidationTarget`
  - `MobileOperatorValidationProgress`
  - `MobileOperatorValidationStatus`
- Outcomes operacionais explicitados:
  - `blocked_no_targets`
  - `in_progress`
  - `completed_successfully`
  - `completed_with_fallback`
  - `completed_inconclusive`
  - `aborted`

## Como o run funciona

O operator run reaproveita a sessao organica ja existente, mas passa a organizar a rodada humana em cima dela:

1. resolve os targets minimos do tenant demo para `feed` e `thread`
2. bloqueia o run se uma das superficies nao tiver alvo elegivel
3. abre uma sessao organica nova e limpa para essa rodada
4. devolve `operator_run_id`, `session_id`, superficies exigidas e instrucoes objetivas para o operador
5. acompanha cobertura tecnica e confirmacao humana por target
6. encerra a rodada com um outcome operacional claro

## Endpoints admin/local-only

- `POST /admin/api/mobile-v2-rollout/operator-run/start`
- `GET /admin/api/mobile-v2-rollout/operator-run/status`
- `POST /admin/api/mobile-v2-rollout/operator-run/finish`

Guard-rails:

- exige sessao admin valida
- exige host local controlado
- limita o run ao tenant demo configurado em `TARIEL_V2_ANDROID_PILOT_TENANT_KEY`
- nao fica exposto ao app nem ao usuario final como funcionalidade de UX

## Criterio minimo do run

O run so pode terminar como `completed_successfully` quando:

- houver pelo menos um target exigido coberto em `feed`
- houver pelo menos um target exigido coberto em `thread`
- a cobertura tecnica minima por superficie estiver atendida
- a confirmacao humana minima de `feed` e `thread` tiver sido registrada
- nao houver `hold_recommended` nem `rollback_recommended` na sessao organica subjacente
- nao houver fallback observado acima do aceitavel

Resultados inferiores:

- `completed_with_fallback`
  - cobertura minima humana completa, mas com fallback controlado observado
- `completed_inconclusive`
  - cobertura humana minima nao atingida, ou houve problema operacional relevante
- `blocked_no_targets`
  - o tenant demo nao ofereceu alvos suficientes para iniciar a rodada
- `aborted`
  - encerramento manual explicito antes da conclusao

## Como o app participa sem mudar UX

O app continua sem tela nova e sem depender do run para funcionar.

Quando um operator run esta ativo:

- `GET /app/api/mobile/v2/capabilities` passa a devolver:
  - `operator_validation_run_active`
  - `operator_validation_run_id`
  - `operator_validation_required_surfaces`
- o app reutiliza esse sinal apenas para propagar o `operator_run_id` discretamente
- os requests de leitura e o ack humano passam a carregar:
  - `X-Tariel-Mobile-Operator-Run`
- o body do ack humano tambem leva:
  - `operator_run_id`

Isso melhora a rastreabilidade do run sem tocar na UX.

## Como ler o progresso

Consultar:

- `GET /admin/api/mobile-v2-rollout/operator-run/status`
- `GET /admin/api/mobile-v2-rollout/summary`

Campos relevantes adicionados:

- `operator_run_active`
- `operator_run_id`
- `operator_run_outcome`
- `operator_run_reason`
- `operator_run_started_at`
- `operator_run_ended_at`
- `operator_run_session_id`
- `operator_run_progress`
- `required_surfaces`
- `covered_surfaces`
- `missing_targets`
- `operator_run_instructions`
- `human_coverage_from_operator_run`
- `validation_session_source`

Em `tenant_surface_states`, cada superficie do tenant demo agora tambem mostra:

- `operator_run_surface_completed`
- `operator_run_missing_targets`

## Execucao local real desta fase

Foi executado um run local real no tenant demo:

- tenant:
  - `empresa_id=1`
  - `Empresa Demo (DEV)`
- run iniciado com sucesso:
  - `operator_run_id=oprv_eb0b740c2862`
  - `session_id=orgv_6eebb7d61d7d`
  - `required_surfaces=[feed, thread]`
- run concluido formalmente com:
  - `operator_run_outcome=completed_inconclusive`
  - `operator_run_reason=minimum_human_coverage_not_met`

Interpretacao correta:

- a camada operacional do run ficou pronta e validada
- o tenant demo tinha targets suficientes para o run
- ainda nao houve a sessao humana real observada no app Android
- por isso o resultado real desta execucao continua conservador

## Rollback

- encerrar run ativo:
  - `POST /admin/api/mobile-v2-rollout/operator-run/finish`
- abortar explicitamente:
  - `POST /admin/api/mobile-v2-rollout/operator-run/finish?abort=1`
- encerrar a sessao organica:
  - `POST /admin/api/mobile-v2-rollout/organic-validation/stop`
- voltar o tenant demo ao legado:
  - `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=legacy_only`
- voltar por superficie:
  - `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=rollback_forced,1:thread=rollback_forced`
- desligar o V2 no app:
  - `EXPO_PUBLIC_ANDROID_V2_READ_CONTRACTS_ENABLED=0`

## O que ainda falta antes de decidir `candidate_ready_for_real_tenant`

- executar uma rodada humana real no app Android usando o tenant demo
- cobrir `feed` e `thread` com confirmacao humana minima no mesmo run
- manter fallback e erros em nivel aceitavel durante a rodada
- so depois usar o resultado do run como evidencia operacional para discutir o proximo passo do piloto
