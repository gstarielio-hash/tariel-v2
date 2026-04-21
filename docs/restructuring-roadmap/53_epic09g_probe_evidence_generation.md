# Epic 09G - geracao controlada de evidencia operacional no tenant demo

## Objetivo

Sair do estado `insufficient_evidence` do tenant demo promovido sem:

- tocar em tenant real;
- criar escrita de negocio;
- alterar payloads legados;
- alterar UX do app Android;
- transformar o probe em trafego permanente.

## Tenant alvo

Tenant usado nesta fase:

- `empresa_id=1`
- `Empresa Demo (DEV)`

Motivo de seguranca:

- seed explicito de desenvolvimento;
- CNPJ placeholder `00000000000000`;
- ja promovido de forma controlada nas fases 09E e 09F;
- nenhum tenant real entrou no fluxo.

## Como os alvos do probe sao escolhidos

Arquivo principal:

- `web/app/v2/mobile_probe.py`

Funcao de descoberta:

- `resolve_demo_mobile_probe_targets()`

Regras aplicadas:

- so considera o tenant configurado em `TARIEL_V2_ANDROID_PILOT_TENANT_KEY`;
- exige que esse tenant apareca em `discover_mobile_v2_safe_pilot_candidates()`;
- exige pelo menos um `Inspetor` ativo;
- seleciona poucos `Laudos` do tenant demo para `feed`;
- seleciona poucos `Laudos` do tenant demo com pelo menos uma mensagem para `thread`;
- se `feed` ou `thread` nao tiver alvo seguro, o probe bloqueia e nao inventa caso.

## Mecanismo do probe

O probe foi implementado como rotina interna controlada:

- `execute_demo_mobile_v2_pilot_probe()`
- `run_demo_mobile_v2_pilot_probe()`

E tambem como gatilho admin/local-only:

- `POST /admin/api/mobile-v2-rollout/probe/run`

Guard-rails do gatilho:

- requer sessao admin valida;
- requer `TARIEL_V2_ANDROID_PILOT_PROBE=1`;
- bloqueia host nao local;
- roda apenas sobre o tenant demo seguro resolvido;
- usa volume pequeno e timeout curto.

## Feature flag

Flag principal:

- `TARIEL_V2_ANDROID_PILOT_PROBE`

Configuracoes auxiliares:

- `TARIEL_V2_ANDROID_PILOT_PROBE_MAX_REQUESTS_PER_SURFACE`
- `TARIEL_V2_ANDROID_PILOT_PROBE_TARGET_LIMIT`
- `TARIEL_V2_ANDROID_PILOT_PROBE_TIMEOUT_MS`
- `TARIEL_V2_ANDROID_PILOT_PROBE_DELAY_MS`
- `TARIEL_V2_ANDROID_PILOT_PROBE_INCLUDE_LEGACY_COMPARE`

Comportamento:

- desligado por padrao em `web/.env.example`;
- ligado localmente em `web/.env` para o tenant demo;
- nao roda sozinho; apenas permite o acionamento controlado.

## Como o probe marca o trafego

Cabecalhos internos usados:

- `X-Tariel-Mobile-V2-Probe: 1`
- `X-Tariel-Mobile-V2-Probe-Source: demo_controlled`

Resultado:

- o backend distingue leituras V2 organicas de leituras V2 de probe;
- o backend distingue fallback organico de fallback de probe;
- o summary admin mostra essa separacao sem expor conteudo tecnico bruto.

## Observabilidade adicionada

Endpoint principal:

- `GET /admin/api/mobile-v2-rollout/summary`

Campos novos relevantes:

- `probe_active`
- `probe_last_run_at`
- `probe_requests_v2`
- `probe_requests_fallback`
- `probe_surfaces_exercised`
- `probe_status`
- `probe_detail`
- `probe_totals`
- `organic_requests_v2`
- `organic_requests_fallback`
- `probe_requests_v2` e `probe_requests_fallback` por tenant/superficie
- `probe_reason_breakdown`
- `probe_resolved_insufficient_evidence`

Leitura operacional recomendada:

1. verificar `first_promoted_tenant`;
2. confirmar `probe_status=completed`;
3. confirmar `probe_requests_v2 > 0`;
4. confirmar `pilot_outcome` do tenant e de `feed/thread`;
5. checar `probe_resolved_insufficient_evidence`;
6. confirmar que `candidate_for_real_tenant` continua `false` enquanto so houver evidencia de probe.

## Resultado local observado nesta fase

Execucao local real realizada:

- `probe_requests_v2=10`
- `probe_requests_fallback=0`
- `probe_surfaces_exercised=[feed, thread]`

Estado observado imediatamente apos o run no tenant demo:

- `pilot_outcome=healthy`
- `evaluation_reason=pilot_healthy_via_probe`
- `probe_resolved_insufficient_evidence=true`
- `candidate_for_real_tenant=false`

Interpretacao correta:

- o piloto deixou de estar inconclusivo por falta de uso;
- a evidencia atual veio de probe controlado, nao de trafego organico;
- por isso ainda nao ha base para qualquer tenant real.

## Como desligar rapidamente

Desligamento do gatilho:

- `TARIEL_V2_ANDROID_PILOT_PROBE=0`

Rollback do piloto V2 continua igual:

- `TARIEL_V2_ANDROID_ROLLOUT_SURFACE_STATE_OVERRIDES=1:feed=rollback_forced,1:thread=rollback_forced`
- ou `TARIEL_V2_ANDROID_ROLLOUT_STATE_OVERRIDES=1=legacy_only`
- ou `TARIEL_V2_ANDROID_ROLLOUT=0`

## O que ainda falta antes de usar tenant real

- observar algum uso organico do app no tenant demo;
- confirmar que `organic_requests_v2` deixa de ser zero;
- manter o tenant demo sem `attention`, `hold_recommended` ou `rollback_recommended`;
- decidir qualquer candidato real apenas depois de evidencia organica complementar ao probe.
