# Epic 06A - policy engine minimo por tenant/template nas leituras canonicas

## Objetivo

Introduzir a primeira camada real de `policy engine` no sistema vivo de forma:

- aditiva;
- segura;
- com rollback simples;
- sem alterar endpoint publico, payload publico, regra de negocio efetiva, UX ou auth/session.

O foco desta fase nao foi aplicar enforcement real no fluxo. O objetivo foi centralizar decisoes minimas de politica em um ponto nomeado e passar a anexar esse resumo as leituras canonicas do Inspetor e da Mesa.

## O que foi implementado

Foram adicionados os artefatos principais:

- `web/app/v2/policy/models.py`
- `web/app/v2/policy/tenant_rules.py`
- `web/app/v2/policy/engine.py`
- `web/app/v2/policy/__init__.py`
- `web/app/v2/runtime.py`
- `web/app/v2/contracts/projections.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/domains/revisor/mesa_api.py`

Estruturas canonicas adicionadas:

- `PolicySourceRef`
- `ReviewRequirementDecision`
- `DocumentMaterializationDecision`
- `PolicyDecisionSummary`
- `TechnicalCasePolicyDecision`

## Qual modelo de decisao de politica existe agora

O engine minimo atual produz decisoes sobre:

- `review_required`
- `review_mode`
- `engineer_approval_required`
- `document_materialization_allowed`
- `document_issue_allowed`
- `policy_source_kind`
- `policy_source_id`
- `rationale`

Valores de `review_mode` implementados nesta fase:

- `none`
- `mesa_required`

Categorias de origem implementadas nesta fase:

- `default`
- `system`

Observacao importante:

- os tipos `tenant` e `template` ja existem no contrato canonico, mas ainda nao ha override persistido no legado atual para usa-los com seguranca;
- por isso, o engine atual usa `default` e `system` de forma explicita em vez de inventar configuracao inexistente.

## De onde a politica e derivada

Sinais usados com seguranca:

- `tenant_id` / `empresa_id`
- `tipo_template`
- `TechnicalCaseStatusSnapshot.canonical_status`
- `TechnicalCaseStatusSnapshot.has_active_report`

Interpretacao canonica atual:

- sem laudo ativo, o baseline fica em:
  - `review_required = false`
  - `review_mode = none`
  - `engineer_approval_required = false`
  - `document_materialization_allowed = false`
  - `document_issue_allowed = false`
- com laudo ativo, o baseline fica em:
  - `review_required = true`
  - `review_mode = mesa_required`
  - `engineer_approval_required = true`
  - `document_materialization_allowed = true`
- `document_issue_allowed` so fica `true` quando o estado canonico do caso ja e `approved`

## Onde a politica entra na projecao do Inspetor

`InspectorCaseViewProjectionV1` agora pode carregar:

- `policy_summary`
- `review_required`
- `review_mode`
- `engineer_approval_required`
- `materialization_allowed`
- `issue_allowed`
- `policy_source_summary`
- `policy_rationale`

Origem da integracao:

- `web/app/domains/chat/laudo_service.py`
- o snapshot canonico do caso e montado normalmente;
- quando `TARIEL_V2_POLICY_ENGINE=1`, o engine deriva a decisao de politica;
- essa decisao entra na projecao canônica do Inspetor;
- o adapter legado continua ignorando esses campos novos.

## Onde a politica entra na projecao da Mesa

`ReviewDeskCaseViewProjectionV1` agora pode carregar:

- `policy_summary`
- `review_required`
- `review_mode`
- `engineer_approval_required`
- `materialization_allowed`
- `issue_allowed`
- `policy_source_summary`
- `policy_rationale`

Origem da integracao:

- `web/app/domains/revisor/mesa_api.py`
- o snapshot canonico do caso e montado normalmente;
- quando `TARIEL_V2_POLICY_ENGINE=1`, o engine deriva a decisao de politica;
- essa decisao entra na projecao canônica da Mesa;
- o adapter legado continua ignorando os campos de politica.

## Feature flag

Flag desta fase:

- `TARIEL_V2_POLICY_ENGINE`

Flags relacionadas:

- `TARIEL_V2_ENVELOPES`
- `TARIEL_V2_CASE_CORE_ACL`
- `TARIEL_V2_INSPECTOR_PROJECTION`
- `TARIEL_V2_REVIEW_DESK_PROJECTION`
- `TARIEL_V2_PROVENANCE`

Comportamento:

- `TARIEL_V2_POLICY_ENGINE=0`: o sistema continua sem derivar policy summary nas leituras canônicas.
- `TARIEL_V2_POLICY_ENGINE=1`: o sistema deriva policy summary internamente e anexa as decisoes as projecoes canônicas do Inspetor e da Mesa.
- payload legado continua igual.

## Telemetria e degradacao segura

Quando a flag esta ativa:

- o resumo de politica fica em `request.state.v2_policy_decision_summary`;
- os resultados das projecoes do Inspetor e da Mesa passam a carregar `policy` em `request.state`;
- se algo falhar na derivacao, o sistema degrada com seguranca para sem `policy_decision` e segue no fluxo legado;
- nao ha bloqueio de caso, revisao, materializacao ou emissao nesta fase.

## O que nao mudou

- endpoints publicos atuais do Inspetor e da Mesa;
- payload publico consumido hoje por web e Android;
- regra de negocio efetiva do ciclo do laudo;
- auth/session/multiportal;
- UI do Inspetor e da Mesa;
- Android;
- banco e schema;
- enforcement real de tenant/template.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_POLICY_ENGINE`;
2. opcionalmente desligar `TARIEL_V2_CASE_CORE_ACL`, `TARIEL_V2_INSPECTOR_PROJECTION` e `TARIEL_V2_REVIEW_DESK_PROJECTION` se tambem quiser parar os caminhos canônicos paralelos;
3. o sistema volta imediatamente a nao derivar policy summary nas leituras canônicas;
4. nao ha rollback de rota, UI, banco ou schema.

## Testes adicionados e ajustados

- `web/tests/test_v2_policy_engine.py`

Cobertura desta fase:

- shape das decisoes de politica;
- defaults conservadores sem laudo ativo;
- gate minimo de emissao no estado canonico aprovado;
- projecao do Inspetor com `policy_summary`;
- projecao da Mesa com `policy_summary`;
- comportamento sob `TARIEL_V2_POLICY_ENGINE`;
- garantia de nao regressao do payload publico atual.

## O que ainda falta para enforcement real

Esta fase nao faz enforcement. Ainda faltam:

- fonte real de override por tenant;
- fonte real de override por template;
- gates de comando consultando policy engine antes de mudar estado;
- document facade consultando politica de materializacao e emissao;
- auditoria mais rica de por que uma politica impediu ou permitiu um avanço.

## Proximos passos que dependem desta fase

Esta fase destrava:

- primeiro enforcement real sobre escrita do caso/documento;
- policy source mais rica por tenant/template;
- facade documental consultando gates canônicos;
- futura visibilidade controlada por tenant/persona sem espalhar regra por portal.

Proximo passo recomendado apos esta fase:

- `Epic 07A - facade documental minima para materializacao controlada a partir do caso canonico`

## Riscos remanescentes

- a politica atual ainda e baseline derivado de `default` e `system`, sem override real por tenant/template;
- `document_materialization_allowed` ainda representa permissao canônica de leitura/planejamento, nao gate efetivo de escrita;
- `document_issue_allowed` depende apenas do estado canonico atual, sem workflow de aprovacao humana explicitamente aplicado;
- o payload publico legado continua sem expor policy summary nesta fase.
