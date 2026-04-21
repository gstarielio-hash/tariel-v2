# Epic 05A - provenance minima IA/humana nas leituras canonicas

## Objetivo

Introduzir a primeira camada real de provenance minima no sistema vivo de forma:

- aditiva;
- segura;
- com rollback simples;
- sem alterar endpoint publico, payload publico, regra de negocio, UX ou auth/session.

O foco desta fase nao foi criar lineage completo, auditoria completa ou UI nova. O objetivo foi fazer as leituras canônicas do Inspetor e da Mesa passarem a carregar um resumo canônico de origem do conteúdo com degradacao segura para `legacy_unknown` quando o legado nao sustenta classificacao confiavel.

## O que foi implementado

Foram adicionados os artefatos principais:

- `web/app/v2/contracts/provenance.py`
- `web/app/v2/provenance.py`
- `web/app/v2/contracts/projections.py`
- `web/app/v2/acl/technical_case_core.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/domains/revisor/mesa_api.py`

Estruturas canonicas adicionadas:

- `OriginKind`
- `ProvenanceEntry`
- `ContentOriginSummary`
- `MessageOriginCounters`

Categorias minimas implementadas:

- `human`
- `ai_assisted`
- `ai_generated`
- `system`
- `legacy_unknown`

Observacao importante:

- `ai_assisted` ja existe como categoria canonica, mas nao passou a ser inferida automaticamente sem sinal confiavel no legado atual.

## Onde a derivacao e confiavel

Sinais usados com confianca:

- `TipoMensagem.USER`
- `TipoMensagem.HUMANO_INSP`
- `TipoMensagem.HUMANO_ENG`
- `TipoMensagem.IA`
- `laudo.primeira_mensagem`
- `laudo.parecer_ia`
- `laudo.confianca_ia_json`
- `PacoteMesaLaudo.resumo_mensagens`
- `PacoteMesaLaudo.revisoes_recentes[].origem`

Interpretacao canonica atual:

- mensagens `user`, `humano_insp` e `humano_eng` contam como sinal `human`;
- mensagens `ia`, `parecer_ia` e revisoes com `origem=ia` contam como sinal `ai_generated`;
- estado sem relatorio ativo e sem conteudo classificado cai em `system`;
- `dados_formulario` legado e sinais sem autoria confiavel caem em `legacy_unknown`.

## Onde a derivacao fica em `legacy_unknown`

Nesta fase, o sistema deliberadamente nao finge precisao quando o legado nao sustenta classificacao real.

Casos marcados como `legacy_unknown`:

- `dados_formulario` do laudo/pacote;
- mensagens fora do conjunto canonico atual de tipos;
- `revisoes_recentes[].origem` com valor desconhecido;
- relatorio ativo sem sinais suficientes de origem confiavel.

## Como a provenance entra no snapshot canonico

`TechnicalCaseStatusSnapshotV1` agora pode carregar:

- `content_origin_summary`

Isso permite que a ACL do `Technical Case Core` continue sendo a costura central entre:

- legado de status/identidade;
- projecao canonica do Inspetor;
- projecao canonica da Mesa.

## Como a provenance entra na projecao do Inspetor

`InspectorCaseViewProjectionV1` agora pode carregar:

- `origin_summary`
- `has_human_inputs`
- `has_ai_outputs`
- `has_ai_assisted_content`
- `has_legacy_unknown_content`
- `human_vs_ai_mix`
- `provenance_quality`

Origem da derivacao no fluxo do Inspetor:

- `web/app/domains/chat/laudo_service.py`
- query minima dos tipos de mensagem do laudo quando a flag esta ativa;
- sinais adicionais do proprio `Laudo` (`primeira_mensagem`, `parecer_ia`, `confianca_ia_json`, `dados_formulario`).

## Como a provenance entra na projecao da Mesa

`ReviewDeskCaseViewProjectionV1` agora pode carregar:

- `origin_summary`
- `has_human_inputs`
- `has_ai_outputs`
- `has_ai_assisted_content`
- `has_legacy_unknown_content`
- `human_vs_ai_mix`
- `provenance_quality`

Origem da derivacao no fluxo da Mesa:

- `web/app/domains/revisor/mesa_api.py`
- `PacoteMesaLaudo`
- `ResumoMensagensMesa`
- `parecer_ia`
- `dados_formulario`
- `revisoes_recentes[].origem`

## Feature flag

Flag desta fase:

- `TARIEL_V2_PROVENANCE`

Flags relacionadas:

- `TARIEL_V2_ENVELOPES`
- `TARIEL_V2_CASE_CORE_ACL`
- `TARIEL_V2_INSPECTOR_PROJECTION`
- `TARIEL_V2_REVIEW_DESK_PROJECTION`

Comportamento:

- `TARIEL_V2_PROVENANCE=0`: o sistema continua sem derivar provenance nas leituras canônicas.
- `TARIEL_V2_PROVENANCE=1`: provenance minima e derivada internamente e anexada ao snapshot canonico e as projecoes do Inspetor e da Mesa.
- payload legado continua igual.

## Como a integracao preserva o payload legado

Fluxo incremental desta fase:

1. os endpoints legados continuam montando os payloads publicos do mesmo jeito;
2. quando `TARIEL_V2_PROVENANCE=1`, o sistema deriva `ContentOriginSummary` internamente;
3. esse resumo entra no `TechnicalCaseStatusSnapshot` quando a ACL/projecao precisa do snapshot;
4. as projecoes canônicas do Inspetor e da Mesa passam a carregar provenance;
5. os adapters legados continuam ignorando esses campos novos;
6. o payload publico atual nao muda.

## Telemetria e degradacao segura

Quando a flag esta ativa:

- o resumo de provenance fica em `request.state.v2_content_provenance_summary`;
- os resultados das projecoes do Inspetor e da Mesa passam a carregar `provenance` em `request.state`;
- falhas de derivacao no fluxo do Inspetor degradam para resumo seguro usando `legacy_unknown` e sao logadas em `debug`;
- o sistema nao marca `ai_assisted` sem sinal confiavel.

## O que nao mudou

- endpoints publicos atuais do Inspetor e da Mesa;
- payload publico consumido hoje por web e Android;
- regra de negocio do ciclo do laudo;
- auth/session/multiportal;
- UI do Inspetor e da Mesa;
- documento/laudo como superficie publica principal;
- Android;
- banco e schema.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_PROVENANCE`;
2. opcionalmente desligar `TARIEL_V2_CASE_CORE_ACL`, `TARIEL_V2_INSPECTOR_PROJECTION` e `TARIEL_V2_REVIEW_DESK_PROJECTION` se tambem quiser parar os caminhos canônicos paralelos;
3. o sistema volta imediatamente a nao derivar provenance nas leituras canônicas;
4. nao ha rollback de rota, UI, banco ou schema.

## Testes adicionados e ajustados

- `web/tests/test_v2_provenance.py`
- `web/tests/test_v2_case_core_acl.py`
- `web/tests/test_v2_envelopes.py`
- `web/tests/test_v2_projection_shadow.py`
- `web/tests/test_v2_inspector_projection.py`
- `web/tests/test_v2_reviewdesk_projection.py`

Cobertura desta fase:

- shape das estruturas de provenance;
- serializacao do resumo canonico;
- derivacao segura do Inspetor;
- derivacao segura da Mesa;
- projecoes canônicas com provenance;
- comportamento sob `TARIEL_V2_PROVENANCE`;
- garantia de nao regressao do payload publico atual.

## Proximos passos que dependem desta fase

Esta fase destrava:

- exibicao futura de provenance na UI sem mudar o contrato legado;
- trilha minima de auditoria sobre participacao humana e da IA;
- futura facade documental com rastreio de origem mais consistente;
- policy engine sobre `ai_document_assist_mode` e gate humano final.

Proximo passo recomendado apos esta fase:

- `Epic 06A - policy engine minimo por tenant/template sobre revisao e materializacao`

## Riscos remanescentes

- `ai_assisted` continua sem derivacao automatica porque o legado ainda nao sustenta esse nivel de precisao;
- `dados_formulario` permanece em `legacy_unknown` ate existir autoria confiavel por campo;
- a provenance atual e um resumo de leitura, nao lineage completo nem auditoria formal;
- o payload publico legado continua sem expor provenance nesta fase.
