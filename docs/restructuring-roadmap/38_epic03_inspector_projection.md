# Epic 03A - primeira projeção canônica do Inspetor consumindo a ACL

## Objetivo

Introduzir a primeira projeção canônica real do Inspetor dentro do sistema vivo de forma:

- aditiva;
- segura;
- com rollback simples;
- sem alterar endpoint publico, payload publico, regra de negocio, UX ou auth/session.

O foco desta fase nao foi migrar a UI para o contrato novo. O objetivo foi fazer a resposta atual de status do Inspetor poder ser produzida internamente a partir de uma projeção canônica consumindo a ACL do `Technical Case Core`.

## O que foi implementado

Foram adicionados os artefatos principais:

- `web/app/v2/contracts/projections.py`
- `web/app/v2/adapters/__init__.py`
- `web/app/v2/adapters/inspector_status.py`

Contrato novo implementado:

- `InspectorCaseViewProjectionV1`

Payload canonico minimo da projeção:

- `legacy_laudo_id`
- `case_status`
- `legacy_public_state`
- `legacy_status_card`
- `legacy_review_status`
- `allows_edit`
- `allows_reopen`
- `has_active_report`
- `has_interaction`
- `review_requested`
- `review_feedback_pending`
- `review_visible_to_inspector`
- `document_available`
- `document_approved`
- `laudo_card`
- `report_types`
- `case_snapshot_timestamp`

## Como a projeção consome a ACL

Builder principal:

- `build_inspector_case_view_projection(...)`

Ele recebe:

- `TechnicalCaseStatusSnapshot`
- flags operacionais do Inspetor
- catalogo de tipos de relatorio
- `laudo_card`

Fonte canonica interna desta fase:

- `TechnicalCaseStatusSnapshot`
- `TechnicalCaseRef`

Isso significa que a projeção nao depende mais do payload legado bruto como contrato interno. Ela depende da ACL do caso e de contexto operacional explicito.

## Adapter de volta para o payload legado

Adapter implementado:

- `adapt_inspector_case_view_projection_to_legacy_status(...)`

Esse adapter reconstrói o payload legado esperado por `/app/api/laudo/status`, preservando:

- `estado`
- `laudo_id`
- `status_card`
- `permite_edicao`
- `permite_reabrir`
- `tem_interacao`
- `tipos_relatorio`
- `laudo_card`

Com isso, a projeção virou consumer real do caminho de status sem alterar o contrato publico.

## Feature flag

Flag desta fase:

- `TARIEL_V2_INSPECTOR_PROJECTION`

Flags relacionadas:

- `TARIEL_V2_CASE_CORE_ACL`
- `TARIEL_V2_ENVELOPES`

Comportamento:

- `TARIEL_V2_INSPECTOR_PROJECTION=0`: resposta continua no caminho legado puro.
- `TARIEL_V2_INSPECTOR_PROJECTION=1`: a resposta de status usa a projeção canônica do Inspetor + adapter para voltar ao payload legado.
- `TARIEL_V2_CASE_CORE_ACL=1`: o snapshot canonico do caso tambem fica exposto em `request.state`.
- `TARIEL_V2_ENVELOPES=1`: o shadow mode do contrato piloto continua rodando em paralelo.

Observacao importante:

- a projeção do Inspetor depende da ACL; por isso, quando `TARIEL_V2_INSPECTOR_PROJECTION=1`, o snapshot do caso e montado internamente mesmo que a flag isolada da ACL esteja desligada.

## Ponto de integração

Integracao principal:

- `web/app/domains/chat/laudo_service.py`
- funcao `obter_status_relatorio_resposta()`

Fluxo incremental desta fase:

1. o payload legado ainda e montado do jeito antigo;
2. o snapshot canonico do caso e resolvido pela ACL;
3. se `TARIEL_V2_INSPECTOR_PROJECTION=1`, `InspectorCaseViewProjectionV1` e construida;
4. o adapter reconstrói o payload legado a partir da projeção;
5. se o adapter for compativel, esse payload adaptado passa a ser a resposta final;
6. se houver divergencia, o sistema faz fallback para o payload legado original e registra o evento de forma discreta;
7. se `TARIEL_V2_ENVELOPES=1`, o shadow mode do `InspectorCaseStatusProjectionV1` continua rodando em paralelo.

## Telemetria e divergencia controlada

Quando a projeção esta ativa:

- o resultado da projeção fica em `request.state.v2_inspector_projection_result`;
- o sistema registra `compatible`, `divergences` e `used_projection`;
- divergencias sao logadas em `debug`;
- em caso de incompatibilidade, a resposta ao usuario nao muda.

## O que nao mudou

- endpoint publico `/app/api/laudo/status`;
- payload consumido hoje por web e Android;
- regra de negocio do ciclo do laudo;
- auth/session/multiportal;
- UI do Inspetor;
- Android;
- escrita do caso;
- documento/laudo como superficie publica principal.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_INSPECTOR_PROJECTION`;
2. opcionalmente desligar `TARIEL_V2_CASE_CORE_ACL` e `TARIEL_V2_ENVELOPES` se tambem quiser parar os caminhos paralelos;
3. o endpoint volta imediatamente ao caminho legado puro;
4. nao ha rollback de rota, UI, banco ou schema.

## Testes adicionados e ajustados

- `web/tests/test_v2_inspector_projection.py`
- `web/tests/test_v2_case_core_acl.py`
- `web/tests/test_v2_envelopes.py`
- `web/tests/test_v2_projection_shadow.py`

Cobertura desta fase:

- shape da projeção canônica do Inspetor;
- builder da projeção a partir da ACL;
- adapter da projeção para o payload legado;
- comportamento sob `TARIEL_V2_INSPECTOR_PROJECTION`;
- garantia de nao regressao do payload publico;
- convivencia da projeção com ACL e shadow mode.

## Proximos passos que dependem desta fase

Esta fase destrava:

- consumer final futuro do Inspetor sobre contrato canônico;
- primeira projeção canônica da Mesa usando a mesma base de ACL;
- provenance minima IA/humana visivel na leitura operacional;
- eventuais adapters canônicos para Android.

Proximo passo recomendado apos esta fase:

- `Epic 04A - primeira projecao canonica da Mesa consumindo a ACL do Technical Case Core`

## Riscos remanescentes

- a projeção do Inspetor ainda reconstrói o payload legado como superficie principal, nao substitui a API publica;
- `case_id`, `thread_id` e `document_id` ainda sao derivados do laudo legado via namespace;
- ainda nao existe consumer final de UI lendo `InspectorCaseViewProjectionV1` diretamente;
- a ACL continua cobrindo leitura de status/identidade, nao escrita nem orquestracao completa do caso.
