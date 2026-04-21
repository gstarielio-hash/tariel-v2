# Epic 04A - primeira projecao canonica da Mesa consumindo a ACL

## Objetivo

Introduzir a primeira projecao canonica real da Mesa Avaliadora dentro do sistema vivo de forma:

- aditiva;
- segura;
- com rollback simples;
- sem alterar endpoint publico, payload publico, regra de negocio, UX ou auth/session.

O foco desta fase nao foi migrar o painel do revisor para consumir o contrato novo diretamente. O objetivo foi fazer um endpoint real da Mesa poder ser produzido internamente a partir de uma projecao canonica consumindo a ACL do `Technical Case Core`.

## O que foi implementado

Foram adicionados os artefatos principais:

- `web/app/v2/contracts/projections.py`
- `web/app/v2/adapters/__init__.py`
- `web/app/v2/adapters/reviewdesk_package.py`
- `web/app/domains/revisor/mesa_api.py`

Contrato novo implementado:

- `ReviewDeskCaseViewProjectionV1`

Payload canonico minimo da projecao:

- `legacy_laudo_id`
- `codigo_hash`
- `tipo_template`
- `setor_industrial`
- `case_status`
- `review_status`
- `document_status`
- `legacy_review_status`
- `status_conformidade`
- `has_open_pendencies`
- `has_recent_whispers`
- `requires_reviewer_action`
- `pending_open_count`
- `pending_resolved_count`
- `recent_whispers_count`
- `recent_reviews_count`
- `created_at`
- `updated_at`
- `last_interaction_at`
- `field_time_minutes`
- `inspector_id`
- `reviewer_id`
- `has_form_data`
- `has_ai_draft`
- `summary_messages`
- `summary_evidence`
- `summary_pending`
- `open_pendencies`
- `recent_resolved_pendencies`
- `recent_whispers`
- `recent_reviews`
- `dados_formulario`
- `parecer_ia`
- `case_snapshot_timestamp`

## Como a projecao consome a ACL

Builder principal:

- `build_reviewdesk_case_view_projection(...)`

Ele recebe:

- `TechnicalCaseStatusSnapshot`
- `PacoteMesaLaudo`
- metadados de ator e canal

Fonte canonica interna desta fase:

- `TechnicalCaseStatusSnapshot`
- `TechnicalCaseRef`
- `PacoteMesaLaudo`

Isso significa que a projecao da Mesa nao depende mais do payload legado do endpoint como contrato interno. Ela depende da ACL do caso e do agregado de pacote da Mesa.

## Adapter de volta para o payload legado do revisor

Adapter implementado:

- `adapt_reviewdesk_case_view_projection_to_legacy_package(...)`

Esse adapter reconstrói o payload legado esperado por `/revisao/api/laudo/{laudo_id}/pacote`, preservando:

- `laudo_id`
- `codigo_hash`
- `tipo_template`
- `setor_industrial`
- `status_revisao`
- `status_conformidade`
- `criado_em`
- `atualizado_em`
- `tempo_em_campo_minutos`
- `ultima_interacao_em`
- `inspetor_id`
- `revisor_id`
- `dados_formulario`
- `parecer_ia`
- `resumo_mensagens`
- `resumo_evidencias`
- `resumo_pendencias`
- `pendencias_abertas`
- `pendencias_resolvidas_recentes`
- `whispers_recentes`
- `revisoes_recentes`

Com isso, a projecao virou consumer real do caminho da Mesa sem alterar o contrato publico.

## Feature flag

Flag desta fase:

- `TARIEL_V2_REVIEW_DESK_PROJECTION`

Flags relacionadas:

- `TARIEL_V2_CASE_CORE_ACL`
- `TARIEL_V2_ENVELOPES`
- `TARIEL_V2_INSPECTOR_PROJECTION`

Comportamento:

- `TARIEL_V2_REVIEW_DESK_PROJECTION=0`: o endpoint do revisor continua no caminho legado puro.
- `TARIEL_V2_REVIEW_DESK_PROJECTION=1`: o endpoint escolhido da Mesa usa a projecao canonica + adapter para voltar ao payload legado.
- `TARIEL_V2_CASE_CORE_ACL=1`: o snapshot canonico do caso tambem fica exposto em `request.state`.
- `TARIEL_V2_ENVELOPES=1`: o shadow mode legado do slice anterior pode continuar rodando em paralelo no fluxo do inspetor.

Observacao importante:

- a projecao da Mesa depende da ACL; por isso, quando `TARIEL_V2_REVIEW_DESK_PROJECTION=1`, o snapshot do caso e montado internamente mesmo que a flag isolada da ACL esteja desligada.

## Endpoint escolhido e justificativa

Ponto de integracao escolhido:

- `/revisao/api/laudo/{laudo_id}/pacote`
- `web/app/domains/revisor/mesa_api.py`
- funcao `obter_pacote_mesa_laudo()`

Justificativa da escolha:

- e o agregado mais representativo da visao operacional da Mesa;
- concentra pendencias, whispers, revisoes recentes e resumos estruturados em um unico payload;
- ja possui um contrato legado relativamente estavel;
- e um corte mais seguro do que `/revisao/api/laudo/{laudo_id}/completo`, porque evita misturar historico completo e superficie maior do que o necessario para o primeiro consumer real da Mesa.

## Como a integracao preserva o payload legado

Fluxo incremental desta fase:

1. o pacote legado da Mesa continua sendo montado do jeito antigo por `carregar_pacote_mesa_laudo_revisor()`;
2. o payload publico legado continua sendo materializado como base de comparacao;
3. quando `TARIEL_V2_CASE_CORE_ACL=1` ou `TARIEL_V2_REVIEW_DESK_PROJECTION=1`, a ACL monta `TechnicalCaseStatusSnapshot` usando o contexto do revisor;
4. quando `TARIEL_V2_REVIEW_DESK_PROJECTION=1`, `ReviewDeskCaseViewProjectionV1` e construida a partir do snapshot canonico + `PacoteMesaLaudo`;
5. o adapter reconstrói o payload legado do pacote a partir da projecao;
6. se o adapter for compativel com o payload legado esperado, esse payload adaptado passa a ser a resposta final;
7. se houver divergencia, o sistema faz fallback para o payload legado original e registra o evento de forma discreta;
8. a resposta ao usuario continua com o mesmo shape publico.

## Telemetria e divergencia controlada

Quando a projecao esta ativa:

- o snapshot canonico do caso fica em `request.state.v2_case_core_snapshot`;
- o resultado da projecao fica em `request.state.v2_reviewdesk_projection_result`;
- o sistema registra `compatible`, `divergences` e `used_projection`;
- divergencias sao logadas em `debug`;
- em caso de incompatibilidade, a resposta ao usuario nao muda.

## O que nao mudou

- endpoint publico `/revisao/api/laudo/{laudo_id}/pacote`;
- payload consumido hoje pelo painel do revisor;
- regra de negocio do fluxo da Mesa;
- auth/session/multiportal;
- painel do revisor;
- Android;
- escrita do caso;
- documento/laudo como superficie publica principal.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_REVIEW_DESK_PROJECTION`;
2. opcionalmente desligar `TARIEL_V2_CASE_CORE_ACL` e `TARIEL_V2_ENVELOPES` se tambem quiser parar os caminhos paralelos;
3. o endpoint volta imediatamente ao caminho legado puro;
4. nao ha rollback de rota, UI, banco ou schema.

## Testes adicionados e ajustados

- `web/tests/test_v2_reviewdesk_projection.py`
- `web/tests/test_v2_case_core_acl.py`
- `web/tests/test_v2_envelopes.py`
- `web/tests/test_v2_projection_shadow.py`
- `web/tests/test_v2_inspector_projection.py`

Cobertura desta fase:

- shape da projecao canonica da Mesa;
- builder da projecao a partir da ACL;
- adapter da projecao para o payload legado do pacote;
- comportamento sob `TARIEL_V2_REVIEW_DESK_PROJECTION`;
- garantia de nao regressao do payload publico;
- convivencia da projecao com ACL e slices anteriores.

## Proximos passos que dependem desta fase

Esta fase destrava:

- consumer futuro do painel da Mesa sobre contrato canonico;
- consolidacao de status de revisao e documento sob contratos V2;
- provenance minima IA/humana na leitura da Mesa;
- futuras projecoes administrativas derivadas de caso + revisao.

Proximo passo recomendado apos esta fase:

- `Epic 05A - provenance minima IA/humana nas leituras canonicas de Inspetor e Mesa`

## Riscos remanescentes

- `ReviewDeskCaseViewProjectionV1` ainda reconstrói o payload legado como superficie principal, nao substitui a API publica;
- `case_id`, `thread_id` e `document_id` ainda sao derivados do laudo legado via namespace;
- a projecao da Mesa ainda depende de fallback para o payload legado em caso de divergencia;
- o `Technical Case Core` continua sem escrita e sem estado soberano persistido.
