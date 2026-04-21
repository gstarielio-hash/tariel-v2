# Epic 08B - implementacao real do adapter canonico do feed mobile de interacoes

## Objetivo

Introduzir o primeiro adapter canônico do feed mobile de interações/mesa dentro do sistema vivo sem:

- alterar endpoint publico;
- alterar payload publico do app Android;
- alterar UX do app;
- alterar regras de negocio;
- expor visão administrativa;
- expor visão completa da Mesa;
- transformar o Android em consumidor direto da projeção da Mesa.

O foco desta fase foi transformar o feed mobile da mesa em consumidor indireto da leitura canônica do Inspetor, preservando o contrato legado atual do Android.

## Ponto de integracao escolhido

Endpoint escolhido:

- `GET /app/api/mobile/mesa/feed`

Arquivos de integracao:

- `web/app/domains/chat/mesa.py`
- `web/app/domains/chat/mesa_mobile_support.py`

## Por que esse ponto foi escolhido

Esse foi o corte mais seguro e mais representativo do "feed de interações" do Android porque:

- e um endpoint mobile-only ja consumido pelo app;
- e o primeiro ponto que o Android usa para detectar atividade de mesa por laudo;
- carrega um feed resumido com cursor delta por `cursor_atualizado_em`;
- antecede a abertura da conversa detalhada em `/app/api/laudo/{laudo_id}/mesa/mensagens`;
- permite fallback por item sem quebrar o feed inteiro;
- nao exige tocar a UX da conversa detalhada nem o contrato de envio de mensagens.

Rotas auditadas e nao escolhidas como ponto principal:

- `/app/api/laudo/{laudo_id}/mesa/mensagens`
  continua sendo o detalhe da conversa, nao o feed resumido;
- `/app/api/laudo/{laudo_id}/mesa/resumo`
  e leitura pontual por laudo, nao o agregador mobile do monitor de atividade;
- `/app/api/laudo/{laudo_id}/mensagens`
  e historico principal do chat, nao o feed de feedback/revisao da mesa.

## O que foi implementado

Foram adicionados ou atualizados:

- `web/app/v2/contracts/interactions.py`
- `web/app/v2/adapters/android_case_feed.py`
- `web/app/v2/adapters/__init__.py`
- `web/app/v2/runtime.py`
- `web/app/domains/chat/mesa_mobile_support.py`
- `web/app/domains/chat/mesa.py`
- `web/tests/test_v2_android_case_feed_adapter.py`

Estruturas novas adicionadas:

- `InspectorCaseInteractionViewV1`
- `InspectorVisibleReviewSignalsV1`
- `AndroidCaseFeedAdapterInputV1`
- `AndroidCaseFeedCompatibilitySummaryV1`
- `AndroidCaseFeedItemAdapterResultV1`

## Como o adapter consome a leitura canônica do caso

Quando `TARIEL_V2_ANDROID_FEED_ADAPTER=1`:

1. o feed legado de `/app/api/mobile/mesa/feed` continua sendo montado primeiro como base de comparacao;
2. para cada laudo alterado do feed, o sistema monta:
   - `TechnicalCaseStatusSnapshot`;
   - `InspectorCaseViewProjectionV1`;
   - `InspectorCaseInteractionViewV1` para as interacoes visiveis ao Inspetor;
   - `InspectorVisibleReviewSignalsV1`;
   - `provenance`, `policy` e `document_facade` quando as flags correspondentes estao ativas;
3. o adapter reconstrói o item legado do feed a partir da projeção do Inspetor + interacoes canônicas;
4. se houver compatibilidade, o item reconstruido passa a ser servido;
5. se houver divergencia ou excecao, o item cai imediatamente para o payload legado original.

Observacao importante:

- o adapter nao consome `ReviewDeskCaseViewProjectionV1`;
- a fase usa a leitura canônica do Inspetor como fronteira de seguranca;
- sinais de revisao entram apenas como interacoes ja visiveis no recorte do Inspetor.

## Como a visibilidade foi restringida ao papel Inspetor

O adapter foi desenhado de forma conservadora:

- usa apenas laudos do proprio inspetor autenticado;
- reaproveita o filtro legado de mensagens da mesa:
  - `HUMANO_INSP`
  - `HUMANO_ENG`
- nao usa `PacoteMesaLaudo` nem `revisoes_recentes` como payload para o Android;
- nao expõe `origin_summary`, `policy_summary`, `document_readiness`, `legacy_pipeline_shadow` ou qualquer metadado administrativo no payload publico;
- nao abre comentarios internos da Mesa fora do que o endpoint do Inspetor ja conseguia observar hoje.

Leitura pratica:

- feedback/revisao so entra quando ja esta visivel ao Inspetor pelo caminho atual;
- em duvida, o adapter degrada para o legado.

## Feature flag

Nova flag desta fase:

- `TARIEL_V2_ANDROID_FEED_ADAPTER`

Comportamento:

- `0`: `/app/api/mobile/mesa/feed` continua no caminho legado puro;
- `1`: o endpoint passa a usar internamente snapshot canônico + `InspectorCaseViewProjectionV1` + adapter de feed item a item;
- payload publico continua igual.

## Telemetria e divergencia discreta

Quando a flag esta ativa:

- cada resultado por item fica em `request.state.v2_android_feed_adapter_results`;
- o resumo agregado fica em `request.state.v2_android_feed_adapter_summary`;
- o sistema registra:
  - `compatible`
  - `divergences`
  - `used_projection`
- divergencias ficam em `debug`;
- qualquer incompatibilidade degrada de volta para o item legado original.

## O que nao mudou

- endpoint `/app/api/mobile/mesa/feed`;
- shape publico retornado ao Android;
- auth mobile;
- rotas `/app/api/laudo/{laudo_id}/mesa/mensagens` e `/mesa/resumo`;
- UX do app Android;
- regras de negocio de mesa/reabertura/revisao;
- visibilidade administrativa;
- Android como cliente do papel `Inspetor`.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_ANDROID_FEED_ADAPTER`;
2. opcionalmente desligar as demais flags V2 auxiliares (`PROVENANCE`, `POLICY_ENGINE`, `DOCUMENT_FACADE`, `DOCUMENT_SHADOW`) se tambem quiser parar as leituras paralelas;
3. o endpoint volta imediatamente ao caminho legado puro.

## Testes adicionados

- `web/tests/test_v2_android_case_feed_adapter.py`

Cobertura adicionada:

- shape do adapter do feed;
- uso da leitura canônica do Inspetor;
- preservacao do payload publico de `/app/api/mobile/mesa/feed`;
- visibilidade controlada do feed para o papel Inspetor;
- convivencia com provenance, policy e facade documental sem vazamento no payload publico.

## O que ainda falta antes de Android consumir contratos canônicos diretamente

- adapter canônico do detalhe `/app/api/laudo/{laudo_id}/mesa/mensagens`;
- versao publica nomeada para o contrato mobile de feed/interacoes;
- consumo direto de read models versionados pelo app;
- rollout controlado por tenant/coorte no app real.
