# Epic 08D - implementacao real do contrato publico mobile V2 para feed/thread

## Objetivo

Consolidar uma primeira superficie publica mobile V2, versionada e opt-in, para a Mesa visivel ao Inspetor sem:

- alterar os endpoints legados ja consumidos pelo Android;
- alterar o payload legado atual;
- alterar o app Android existente;
- alterar UX, auth, session ou multiportal;
- alterar regras de negocio;
- expor visao administrativa;
- expor visao completa da Mesa;
- transformar o Android em cliente da projecao da Mesa.

O foco desta fase foi abrir um namespace publico novo e explicito para futura migracao do app, reaproveitando os adapters canonicos internos criados nos slices 08A, 08B e 08C.

## Namespace e rotas escolhidos

Namespace escolhido:

- `/app/api/mobile/v2`

Rotas publicas adicionadas:

- `GET /app/api/mobile/v2/mesa/feed`
- `GET /app/api/mobile/v2/laudo/{laudo_id}/mesa/mensagens`

## Por que essa convencao foi escolhida

Esse desenho foi escolhido porque:

- separa de forma explicita contrato legado e contrato V2;
- evita reaproveitamento silencioso das rotas antigas;
- permite rollout opt-in sem tocar no app atual;
- facilita rollback simples por feature flag;
- preserva o Android atual intacto enquanto abre uma superficie futura clara;
- mantem a leitura ancorada no papel `Inspetor`, nao na visao completa da Mesa.

Rotas antigas mantidas intactas:

- `GET /app/api/mobile/mesa/feed`
- `GET /app/api/laudo/{laudo_id}/mesa/mensagens`

## Contratos publicos V2 criados

Arquivo principal:

- `web/app/v2/contracts/mobile.py`

Contratos adicionados:

- `MobileInspectorFeedV2`
- `MobileInspectorFeedItemV2`
- `MobileInspectorThreadV2`
- `MobileInspectorThreadMessageV2`
- `MobileInspectorThreadSyncV2`
- `MobileInspectorInteractionSummaryV2`
- `MobileInspectorReviewSignalsV2`
- `MobileInspectorCaseCardV2`

Esses contratos expõem de forma versionada e explicita:

- `contract_name`
- `contract_version`
- `tenant_id`
- `source_channel`
- `visibility_scope`
- `case_id`
- `legacy_laudo_id`
- `thread_id`
- envelope do feed
- envelope da thread
- itens do feed
- itens da thread
- cursores/sync da thread
- provenance resumida quando disponivel
- sinais de review visiveis ao Inspetor
- `policy_summary` e `document_readiness` apenas quando ja entram pela visao do Inspetor

Nao entram no contrato publico V2:

- comentarios internos nao visiveis da Mesa;
- payload administrativo;
- `ReviewDeskCaseViewProjectionV1`;
- `dados_formulario`;
- `parecer_ia`;
- `recent_reviews`;
- visao completa da Mesa.

## Como a implementacao reaproveita os adapters existentes

Os endpoints novos reaproveitam a base do V2 ja existente:

- `TechnicalCaseStatusSnapshot`
- `InspectorCaseViewProjectionV1`
- `InspectorCaseInteractionViewV1`
- `InspectorCaseConversationViewV1`
- `InspectorVisibleReviewSignalsV1`

E tambem rodam os adapters legados ja implementados em paralelo para compatibilidade e telemetria:

- `web/app/v2/adapters/android_case_view.py`
- `web/app/v2/adapters/android_case_feed.py`
- `web/app/v2/adapters/android_case_thread.py`

Uso pratico:

1. o endpoint V2 deriva a leitura canônica do Inspetor;
2. monta o contrato publico `MobileInspectorFeedV2` ou `MobileInspectorThreadV2`;
3. compara em paralelo essa mesma leitura com o legado usando os adapters existentes;
4. registra divergencias em `request.state`;
5. responde apenas com o contrato V2, sem tocar nas rotas legadas.

## Como a visibilidade foi restringida

O recorte continua conservador:

- so aparecem mensagens `HUMANO_INSP` e `HUMANO_ENG`;
- o Android continua herdando o papel do Inspetor;
- sinais de review entram apenas quando ja sao visiveis ao Inspetor no modelo atual;
- nao ha promocao de `USER`, `IA`, comentarios internos ou decisao administrativa;
- em duvida, o contrato novo continua omitindo o dado.

## Feature flag

Nova flag desta fase:

- `TARIEL_V2_ANDROID_PUBLIC_CONTRACT`

Comportamento:

- `0`: as rotas `/app/api/mobile/v2/...` ficam indisponiveis com `404`;
- `1`: os endpoints publicos versionados V2 ficam ativos;
- as rotas legadas continuam intactas em ambos os casos.

## Telemetria e compatibilidade

Quando a flag esta ativa:

- o feed registra `request.state.v2_android_public_contract_feed_results`;
- o feed registra `request.state.v2_android_public_contract_feed_summary`;
- a thread registra `request.state.v2_android_public_contract_thread_result`;
- a thread registra `request.state.v2_android_public_contract_thread_summary`.

Esses registros carregam:

- snapshot/projecao/interacoes canonicas;
- contrato publico V2 gerado;
- compatibilidade do `android_case_view`;
- compatibilidade do `android_case_feed` ou `android_case_thread`;
- divergencias relevantes para rollout e migracao futura.

## O que nao mudou

- o payload publico atual de `GET /app/api/mobile/mesa/feed`;
- o payload publico atual de `GET /app/api/laudo/{laudo_id}/mesa/mensagens`;
- o app Android existente;
- UX do app;
- auth, session e multiportal;
- regras de negocio;
- UI web;
- banco legado.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_ANDROID_PUBLIC_CONTRACT`;
2. as rotas `/app/api/mobile/v2/...` voltam imediatamente a responder `404`;
3. as rotas legadas continuam funcionando sem qualquer alteracao adicional.

## O que ainda falta antes da migracao real do Android

- o app Android consumir de fato `MobileInspectorFeedV2` e `MobileInspectorThreadV2`;
- rollout controlado por tenant/coorte no cliente real;
- definicao de estrategia de versionamento e sunset do legado quando o app migrar;
- possivel contrato V2 para comandos/escrita mobile, se isso vier a ser necessario;
- consolidacao de policy/readiness como experiencia explicita do app, caso vire requisito de produto.
