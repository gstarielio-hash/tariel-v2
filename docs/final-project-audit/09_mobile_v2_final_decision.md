# 09 - Mobile V2 Final Decision

Data de fechamento desta fase: 2026-04-04.

## Decisão canônica

O mobile V2 saiu do estado ambíguo de `observing` como decisão arquitetural e passou a ser tratado como `closed_with_guardrails` quando existir evidência durável válida da lane oficial do produto.

A promoção não foi feita por decreto. A regra nova exige ao mesmo tempo:

- tenant piloto com superfícies obrigatórias em `promoted`
- artifact durável recente da lane oficial
- `status=ok`
- `result=success_human_confirmed`
- `operatorRunOutcome=completed_successfully`
- `feedCovered=true`
- `threadCovered=true`
- ausência de sinais de falha ambiental
- `pilot_outcome_after in {healthy, candidate_for_real_tenant}` no `final_report.md`

Quando essa evidência existe, o backend publica:

- `mobile_v2_architecture_status=closed_with_guardrails`
- `mobile_v2_architecture_reason=durable_mobile_acceptance_evidence`
- `mobile_v2_legacy_fallback_policy=guardrail_only`
- `mobile_v2_transition_active=false`

## O que mudou no código

- `web/app/v2/mobile_acceptance_evidence.py`
  - lê e valida a evidência durável da lane oficial em `.tmp_online/devkit/mobile_pilot_lane_status.json`
  - cruza a lane com o `final_report.md` correspondente
- `web/app/v2/mobile_rollout.py`
  - passa a considerar essa evidência na resolução do fechamento arquitetural
  - publica `mobile_v2_durable_acceptance_evidence` no resumo operacional
- `web/app/v2/mobile_rollout_metrics.py`
  - inclui o novo campo no fallback/default do summary

## Estado vivo confirmado nesta execução

Resumo real lido no runtime local após a implementação:

- `mobile_v2_closure_summary.mobile_v2_architecture_status = closed_with_guardrails`
- `mobile_v2_closure_summary.mobile_v2_architecture_reason = durable_mobile_acceptance_evidence`
- `mobile_v2_closure_summary.mobile_v2_legacy_fallback_policy = guardrail_only`
- `mobile_v2_durable_acceptance_evidence.valid_for_closure = true`

Artifacts duráveis confirmados nesta fase:

- `artifacts/mobile_pilot_run/20260404_155245/final_report.md`
- `artifacts/mobile_pilot_run/20260404_155907/final_report.md`
- `.tmp_online/devkit/mobile_pilot_lane_status.json`

## Leitura honesta

O `organic_validation_outcome` pode continuar aparecendo como `observing` no resumo orgânico porque ele continua medindo a janela orgânica volátil. Isso deixou de ser o ponto de decisão arquitetural final. A decisão final agora é baseada na lane oficial persistida, que é a evidência mais forte do produto real no host controlado.

## Estado final desta frente

- decisão arquitetural do mobile V2: fechada
- fallback legado: mantido apenas como guardrail
- ambiguidade entre `observing` volátil e produto efetivamente validado: removida

## O que ainda não foi fingido

Nada neste fechamento afirma que o legado pode ser removido imediatamente. O legado continua como proteção operacional, mas não mais como modo estrutural primário da arquitetura.
