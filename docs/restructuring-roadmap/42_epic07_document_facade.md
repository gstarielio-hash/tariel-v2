# Epic 07A - facade documental minima para materializacao controlada

## Objetivo

Introduzir a primeira camada real de `facade documental` no sistema vivo de forma:

- aditiva;
- segura;
- com rollback simples;
- sem alterar endpoint publico, payload publico, regra de negocio efetiva, UX ou auth/session.

O foco desta fase nao foi materializar documento novo nem substituir o pipeline documental legado. O objetivo foi modelar uma leitura canonica de `readiness documental`, `binding de template` e `blockers` a partir do caso canonico.

## O que foi implementado

Foram adicionados os artefatos principais:

- `web/app/v2/document/models.py`
- `web/app/v2/document/template_binding.py`
- `web/app/v2/document/facade.py`
- `web/app/v2/document/__init__.py`
- `web/app/v2/runtime.py`
- `web/app/v2/contracts/projections.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/domains/revisor/mesa_api.py`

Estruturas canonicas adicionadas:

- `DocumentTemplateBindingRef`
- `DocumentPolicyViewSummary`
- `DocumentBlockerSummary`
- `DocumentMaterializationReadinessV1`
- `CanonicalDocumentFacadeV1`

## Qual e a facade documental minima agora

A facade documental minima atual responde internamente:

- qual `template` esta vinculado ao caso, se houver;
- qual e o `template_source_kind` observado no legado;
- se a materializacao estaria permitida no modelo canonico atual;
- se a emissao estaria permitida no modelo canonico atual;
- qual e o `current_document_status` canônico observado;
- quais blockers impedem ou adiam o proximo passo documental;
- se a prontidao atual esta em:
  - `not_applicable`
  - `blocked`
  - `ready_for_materialization`
  - `ready_for_issue`

## Como o binding de template e resolvido

O binding atual usa somente sinais reais do legado:

- `tenant_id`
- `tipo_template`
- `TemplateLaudo` ativo na biblioteca da empresa
- `modo_editor`
- `codigo_template`
- `versao`

Mapeamento canonico implementado:

- `modo_editor=legado_pdf` -> `template_source_kind=legacy_pdf`
- `modo_editor=editor_rico` -> `template_source_kind=editor_rico`
- sem template ativo compativel -> `binding_status=not_bound` e `template_source_kind=unknown`

Observacao importante:

- nesta fase, `editor_rico` nao foi rebatizado artificialmente para `docx_word`;
- o contrato canonico ja deixa espaco para `docx_word` e `structured_template_future`, mas o legado atual ainda nao sustenta essa troca de forma segura.

## Como o readiness documental e derivado

Sinais usados com seguranca:

- `TechnicalCaseStatusSnapshot`
- `PolicyDecisionSummary`
- `ContentOriginSummary`
- `tipo_template`
- `status_revisao`
- `dados_formulario`
- `parecer_ia`
- template ativo da biblioteca quando existir

Interpretacao canonica atual:

- sem laudo ativo -> `current_document_status=not_started`
- com laudo ativo + conteudo parcial (`dados_formulario` ou `parecer_ia`) -> `current_document_status=partially_filled`
- com caso aprovado -> `current_document_status=approved_for_issue`
- com laudo ativo sem sinais adicionais -> `current_document_status=draft_document`

## Blockers canonicos implementados

Blockers minimos desta fase:

- `no_active_report`
- `template_not_bound`
- `materialization_disallowed_by_policy`
- `review_still_required_for_issue`
- `engineer_approval_pending`
- `legacy_content_origin_unknown`

Regras atuais:

- blockers de `template`, `data` e `policy` entram como `blocking=true`;
- blockers de revisao, aprovacao e origem incerta entram como `blocking=false`, porque informam o gate futuro sem impedir a leitura canonica nesta fase.

## Feature flag

Flag desta fase:

- `TARIEL_V2_DOCUMENT_FACADE`

Flags relacionadas:

- `TARIEL_V2_ENVELOPES`
- `TARIEL_V2_CASE_CORE_ACL`
- `TARIEL_V2_INSPECTOR_PROJECTION`
- `TARIEL_V2_REVIEW_DESK_PROJECTION`
- `TARIEL_V2_PROVENANCE`
- `TARIEL_V2_POLICY_ENGINE`

Comportamento:

- `TARIEL_V2_DOCUMENT_FACADE=0`: o sistema continua sem montar a facade documental canonica.
- `TARIEL_V2_DOCUMENT_FACADE=1`: a facade documental passa a ser derivada internamente e anexada as projecoes canonicas do Inspetor e da Mesa.
- payload legado continua igual.

## Onde a facade entra nas projecoes

`InspectorCaseViewProjectionV1` agora pode carregar:

- `document_readiness`
- `template_binding_summary`
- `document_blockers`

`ReviewDeskCaseViewProjectionV1` agora pode carregar:

- `document_readiness`
- `template_binding_summary`
- `document_blockers`

Integracao real:

- `web/app/domains/chat/laudo_service.py`
- `web/app/domains/revisor/mesa_api.py`

Observacao importante:

- os adapters legados continuam ignorando os campos documentais novos;
- o contrato publico atual nao mudou.

## Telemetria e degradacao segura

Quando a flag esta ativa:

- o resumo de readiness fica em `request.state.v2_document_facade_summary`;
- os resultados das projecoes do Inspetor e da Mesa passam a carregar `document_facade` em `request.state`;
- se faltar template ou dado minimo, a facade degrada para blockers canonicos seguros;
- se houver falha de derivacao, o sistema segue no fluxo legado.

## O que nao mudou

- endpoints publicos atuais do Inspetor e da Mesa;
- payload publico consumido hoje por web e Android;
- regra de negocio efetiva do ciclo do laudo;
- auth/session/multiportal;
- UI do Inspetor e da Mesa;
- pipeline documental legado;
- Android;
- banco e schema.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_DOCUMENT_FACADE`;
2. opcionalmente desligar `TARIEL_V2_CASE_CORE_ACL`, `TARIEL_V2_INSPECTOR_PROJECTION`, `TARIEL_V2_REVIEW_DESK_PROJECTION`, `TARIEL_V2_POLICY_ENGINE` e `TARIEL_V2_PROVENANCE` se tambem quiser parar os caminhos canônicos paralelos;
3. o sistema volta imediatamente a nao derivar facade documental nas leituras canônicas;
4. nao ha rollback de rota, UI, banco ou schema.

## Testes adicionados e ajustados

- `web/tests/test_v2_document_facade.py`

Cobertura desta fase:

- shape das estruturas documentais;
- facade documental minima;
- blockers seguros quando faltam dados;
- binding de template ativo quando ele existe;
- integracao da facade na projecao do Inspetor;
- integracao da facade na projecao da Mesa;
- comportamento sob `TARIEL_V2_DOCUMENT_FACADE`;
- garantia de nao regressao do payload publico atual.

## O que ainda falta para materializacao real e emissao

Esta fase nao materializa nem emite documento. Ainda faltam:

- contrato explicito de `MaterializarLaudoAPartirDoCaso`;
- facade documental chamando o pipeline legado em shadow mode;
- retorno do resultado da materializacao ao caso canonico;
- estrategia real de `DOCX/Word` como template-fonte;
- gates de aprovacao humana aplicados antes de emissao.

## Proximos passos que dependem desta fase

Esta fase destrava:

- facade documental com chamada controlada ao pipeline legado;
- comparacao shadow entre readiness canonico e materializacao efetiva;
- futura transicao de template `legacy_pdf` para fontes mais ricas;
- retorno canonico de `DocumentoMaterializado` ao caso.

Proximo passo recomendado apos esta fase:

- `Epic 07B - chamada shadow da facade documental ao pipeline legado sem trocar o contrato publico`

## Riscos remanescentes

- a facade ainda depende do template ativo da biblioteca; sem binding, o readiness fica bloqueado;
- `editor_rico` ainda e apenas um source kind observado do legado, nao um pipeline documental canônico novo;
- a fase ainda nao fecha o contrato de materializacao nem escreve estado documental soberano;
- o payload publico legado continua sem expor readiness documental nesta fase.
