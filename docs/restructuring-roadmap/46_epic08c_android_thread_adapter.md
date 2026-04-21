# Epic 08C - implementacao real do adapter canonico da conversa detalhada mobile

## Objetivo

Introduzir o primeiro adapter canônico da conversa detalhada mobile da mesa dentro do sistema vivo sem:

- alterar endpoint publico;
- alterar payload publico do app Android;
- alterar UX do app;
- alterar regras de negocio;
- expor visao completa da Mesa;
- expor comentarios internos da Mesa;
- expor metadados administrativos;
- transformar o Android em consumidor direto da projecao da Mesa.

O foco desta fase foi transformar a conversa detalhada do mobile em consumidora indireta da leitura canônica do Inspetor, preservando o contrato legado atual do Android.

## Ponto de integracao escolhido

Endpoint escolhido:

- `GET /app/api/laudo/{laudo_id}/mesa/mensagens`

Arquivos de integracao:

- `web/app/domains/chat/mesa.py`
- `web/app/v2/adapters/android_case_thread.py`

## Por que esse ponto foi escolhido

Esse foi o corte mais seguro e mais representativo da "conversa detalhada" usada pelo Android porque:

- e o endpoint real chamado pelo app ao abrir a thread detalhada da mesa;
- suporta carga completa e sincronizacao incremental por `apos_id`;
- devolve o payload completo que o app usa para `itens`, `resumo` e `sync`;
- ja herda o papel do `Inspetor` e nao e uma rota administrativa;
- permite fallback imediato da resposta inteira para o payload legado;
- e o passo natural depois do feed resumido de `GET /app/api/mobile/mesa/feed`.

Rotas auditadas e nao escolhidas como ponto principal:

- `GET /app/api/mobile/mesa/feed`
  ja foi coberta no Epic 08B e serve apenas como feed resumido;
- `GET /app/api/laudo/{laudo_id}/mesa/resumo`
  e leitura resumida por laudo, nao a conversa detalhada;
- rotas de envio da mesa
  nao sao leitura detalhada e nao eram o menor risco para o primeiro adapter da thread.

## O que foi implementado

Foram adicionados ou atualizados:

- `web/app/v2/contracts/interactions.py`
- `web/app/v2/adapters/android_case_feed.py`
- `web/app/v2/adapters/android_case_thread.py`
- `web/app/v2/adapters/__init__.py`
- `web/app/v2/runtime.py`
- `web/app/domains/chat/mesa.py`
- `web/tests/test_v2_android_case_thread_adapter.py`

Estruturas novas adicionadas:

- `InspectorCaseThreadMessageV1`
- `InspectorCaseConversationViewV1`
- `AndroidCaseThreadAdapterInputV1`
- `AndroidCaseThreadCompatibilitySummaryV1`
- `AndroidCaseThreadMessageAdapterResultV1`
- `AndroidCaseThreadAdapterResultV1`

Expansoes no modelo canônico de interacoes:

- `InspectorCaseInteractionViewV1` agora tambem carrega:
  - `content_text`
  - `display_date`
  - `resolved_at_label`
  - `resolved_by_name`
  - `attachments`
  - `delivery_status`

## Como o adapter consome a leitura canônica do caso

Quando `TARIEL_V2_ANDROID_THREAD_ADAPTER=1`:

1. a rota legado de `/app/api/laudo/{laudo_id}/mesa/mensagens` continua sendo montada primeiro como base de comparacao;
2. o sistema deriva:
   - `TechnicalCaseStatusSnapshot`;
   - `InspectorCaseViewProjectionV1`;
   - `InspectorCaseInteractionViewV1` para as mensagens visiveis ao Inspetor;
   - `InspectorCaseConversationViewV1` para a thread detalhada;
   - `InspectorVisibleReviewSignalsV1`;
   - `provenance`, `policy` e `document_facade` quando as flags correspondentes estao ativas;
3. o adapter reconstrói o payload legado completo da thread a partir da projecao do Inspetor + conversa canônica;
4. se houver compatibilidade, a resposta reconstruida passa a ser servida;
5. se houver divergencia ou excecao, a rota cai imediatamente de volta para o payload legado original.

Observacao importante:

- o adapter nao consome `ReviewDeskCaseViewProjectionV1`;
- a fase continua usando a leitura canônica do Inspetor como fronteira de seguranca;
- sinais de revisao entram apenas quando ja estao visiveis ao Inspetor no recorte atual.

## Como a visibilidade foi restringida ao papel Inspetor

O adapter foi desenhado de forma conservadora:

- usa apenas o laudo do proprio inspetor autenticado;
- reaproveita o filtro legado da rota detalhada:
  - `HUMANO_INSP`
  - `HUMANO_ENG`
- nao promove `USER`, `IA`, revisoes internas ou pacote administrativo da Mesa para o payload publico do Android;
- nao expõe `origin_summary`, `policy_summary`, `document_readiness`, `legacy_pipeline_shadow` ou qualquer metadado administrativo no payload publico;
- nao abre comentarios internos da Mesa fora do que o endpoint do Inspetor ja conseguia observar hoje.

Leitura pratica:

- a thread detalhada continua sendo uma conversa do `Inspetor`;
- a Mesa so aparece no recorte ja permitido ao Inspetor;
- em duvida, o adapter degrada para o legado.

## Feature flag

Nova flag desta fase:

- `TARIEL_V2_ANDROID_THREAD_ADAPTER`

Comportamento:

- `0`: `/app/api/laudo/{laudo_id}/mesa/mensagens` continua no caminho legado puro;
- `1`: o endpoint passa a usar internamente snapshot canônico + `InspectorCaseViewProjectionV1` + conversa canônica + adapter de thread;
- payload publico continua igual.

## Telemetria e divergencia discreta

Quando a flag esta ativa:

- o resultado detalhado fica em `request.state.v2_android_thread_adapter_result`;
- o resumo agregado fica em `request.state.v2_android_thread_adapter_summary`;
- o sistema registra:
  - `compatible`
  - `divergences`
  - `used_projection`
  - `total_messages`
  - `compatible_messages`
- divergencias ficam em `debug`;
- qualquer incompatibilidade degrada de volta para o payload legado original.

## O que nao mudou

- endpoint `/app/api/laudo/{laudo_id}/mesa/mensagens`;
- shape publico retornado ao Android;
- auth mobile, sessao e multiportal;
- rotas de envio da mesa;
- UX do app Android;
- regras de negocio de mesa/reabertura/revisao;
- visao administrativa;
- Android como cliente do papel `Inspetor`.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_ANDROID_THREAD_ADAPTER`;
2. opcionalmente desligar as demais flags V2 auxiliares (`PROVENANCE`, `POLICY_ENGINE`, `DOCUMENT_FACADE`, `DOCUMENT_SHADOW`) se tambem quiser parar as leituras paralelas;
3. a rota volta imediatamente ao caminho legado puro.

## Testes adicionados

- `web/tests/test_v2_android_case_thread_adapter.py`

Cobertura adicionada:

- shape do adapter da conversa detalhada;
- uso da leitura canônica do Inspetor;
- preservacao do payload publico de `/app/api/laudo/{laudo_id}/mesa/mensagens`;
- visibilidade controlada da conversa detalhada para o papel Inspetor;
- convivencia com provenance, policy e facade documental sem vazamento no payload publico.

## O que ainda falta antes de Android consumir contratos canônicos diretamente

- versao publica nomeada para o contrato mobile de thread/conversa detalhada;
- adapter canônico do resumo detalhado da mesa como contrato publico proprio, se o app precisar parar de depender do payload herdado;
- rollout controlado por tenant/coorte no app real;
- migrar o Android para consumo direto de read models versionados quando a compatibilidade estiver estabilizada.
