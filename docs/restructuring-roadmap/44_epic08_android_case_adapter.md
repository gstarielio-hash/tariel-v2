# Epic 08A - primeiro adapter Android para leitura canônica do caso

## Objetivo

Introduzir o primeiro adapter Android do V2 no sistema vivo sem:

- alterar endpoint publico;
- alterar payload publico do app;
- alterar UX do Android;
- alterar regras de negocio;
- abrir visao da Mesa ou visao administrativa para o mobile.

O foco desta fase foi transformar o Android em cliente indireto da `InspectorCaseViewProjectionV1`, ainda por compatibilidade.

## Endpoint escolhido

O ponto escolhido foi:

- `GET /app/api/mobile/laudos`

## Por que esse ponto foi escolhido

Esse endpoint foi o corte mais seguro porque:

- ja e um endpoint real do Android;
- representa leitura operacional de caso/laudo pelo papel `Inspetor`;
- devolve um payload simples e estavel de cards de laudo;
- nao carrega visao da Mesa;
- nao mistura bootstrap administrativo com leitura de caso;
- permite fallback por item sem quebrar o app inteiro.

`/app/api/mobile/bootstrap` foi descartado como ponto principal porque ele trata apenas boot do app e identidade, nao leitura de caso.

## O que foi implementado

Foram adicionados ou atualizados:

- `web/app/v2/adapters/android_case_view.py`
- `web/app/v2/adapters/__init__.py`
- `web/app/v2/runtime.py`
- `web/app/domains/chat/auth_mobile_support.py`
- `web/app/domains/chat/auth_mobile_routes.py`
- `web/tests/test_v2_android_case_adapter.py`

Estruturas novas:

- `AndroidCaseViewAdapterInputV1`
- `AndroidCaseCompatibilitySummaryV1`
- `AndroidCaseViewAdapterResultV1`

## Como o adapter funciona

Quando `TARIEL_V2_ANDROID_CASE_ADAPTER=1`:

1. `listar_cards_laudos_mobile_inspetor(...)` continua consultando os mesmos laudos do inspetor;
2. para cada laudo visivel, o sistema monta:
   - payload legado resumido do caso;
   - `TechnicalCaseStatusSnapshot`;
   - `InspectorCaseViewProjectionV1`;
   - `provenance`, `policy` e `document_facade` quando as flags correspondentes estao ativas;
3. o adapter Android reconstrói o card legado a partir da `InspectorCaseViewProjectionV1`;
4. se houver compatibilidade, usa o payload reconstruido;
5. se houver divergencia, faz fallback imediato para o card legado original.

## Regra de visibilidade

O adapter Android:

- usa apenas a visao do `Inspetor`;
- nao consome `ReviewDeskCaseViewProjectionV1`;
- nao expõe `policy_summary`, `origin_summary` ou `document_readiness` no payload publico do app;
- mantem provenance, policy e facade documental apenas como suporte interno de derivacao e telemetria.

## Feature flag

Nova flag desta fase:

- `TARIEL_V2_ANDROID_CASE_ADAPTER`

Comportamento:

- `0`: Android segue no caminho legado puro;
- `1`: `/app/api/mobile/laudos` passa a usar internamente `InspectorCaseViewProjectionV1` + adapter de compatibilidade;
- payload publico continua igual.

## Telemetria e fallback

Quando a flag esta ativa:

- os resultados por item ficam em `request.state.v2_android_case_adapter_results`;
- o resumo agregado fica em `request.state.v2_android_case_adapter_summary`;
- divergencias nao quebram o app;
- cada item pode cair individualmente para o card legado.

## O que nao mudou

- endpoint `/app/api/mobile/laudos`;
- shape publico de cada card retornado ao Android;
- contrato de auth mobile;
- UX do app;
- visibilidade limitada ao papel Inspetor.

## Rollback

Rollback simples:

1. desligar `TARIEL_V2_ANDROID_CASE_ADAPTER`;
2. opcionalmente desligar as demais flags V2 se tambem quiser parar provenance/policy/facade em leituras paralelas;
3. o endpoint volta imediatamente ao caminho legado puro.

## Testes adicionados

- `web/tests/test_v2_android_case_adapter.py`

Cobertura adicionada:

- shape do adapter Android;
- reconstrucao do card legado a partir da `InspectorCaseViewProjectionV1`;
- preservacao do payload publico de `/app/api/mobile/laudos`;
- visibilidade limitada ao papel Inspetor;
- integracao com provenance, policy, facade documental e document shadow sem expor esses campos ao app.

## Limitacoes atuais

- o Android ainda consome payload legado, nao contrato canônico direto;
- o adapter trabalha hoje sobre cards/lista, nao sobre leitura detalhada de um caso individual;
- a rota `/api/mobile/mesa/feed` ainda nao passou por adapter canônico;
- o app ainda nao consome telemetria canônica nem read models versionados.

## Proximo passo recomendado

- `Epic 08B - adapter canônico do feed mobile de interacoes/mesa com visibilidade controlada`
