# Epic 07B - integracao shadow da facade documental com o pipeline legado

## Objetivo

Conectar a `CanonicalDocumentFacadeV1` ao caminho real de decisao do pipeline documental legado sem:

- alterar endpoint publico;
- alterar payload publico;
- alterar UX;
- emitir documento novo;
- substituir o pipeline legado.

O foco desta fase foi transformar a facade documental em uma leitura canônica que tambem sabe responder, em shadow mode, qual caminho legado seria usado para preview/materializacao e se ele concorda ou nao com o readiness canônico.

## Ponto real do legado integrado

O ponto seguro escolhido foi o controle de decisao observado hoje em `web/app/domains/chat/chat_aux_routes.py`, na rota `rota_pdf()`.

Esse caminho legado atualmente decide:

- `editor_rico` -> `gerar_pdf_editor_rico_bytes(...)`
- `legado_pdf` -> `gerar_preview_pdf_template(...)`
- fallback -> `GeradorLaudos.gerar_pdf_inspecao(...)`

Nesta fase, a integracao nao chamou a emissao real. Ela espelhou a decisao de selecao do pipeline, usando sinais reais do legado:

- `TemplateLaudo` ativo;
- `modo_editor`;
- disponibilidade de `documento_editor_json`;
- disponibilidade de `arquivo_pdf_base`;
- presenca de `dados_formulario`;
- existencia de laudo ativo.

## O que foi implementado

Foram adicionados ou atualizados:

- `web/app/v2/document/models.py`
- `web/app/v2/document/template_binding.py`
- `web/app/v2/document/legacy_adapter.py`
- `web/app/v2/document/__init__.py`
- `web/app/v2/runtime.py`
- `web/app/v2/contracts/projections.py`
- `web/app/domains/chat/laudo_service.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/tests/test_v2_document_shadow.py`

Novos contratos internos:

- `LegacyDocumentPipelineShadowInputV1`
- `LegacyDocumentReadinessComparisonV1`
- `LegacyDocumentPipelineShadowResultV1`

Novos metadados no binding canônico:

- `legacy_template_status`
- `legacy_template_mode`
- `legacy_pdf_base_available`
- `legacy_editor_document_present`

## Como funciona o shadow mode agora

Quando `TARIEL_V2_DOCUMENT_SHADOW=1` e a facade documental ja foi montada:

1. o sistema constroi `LegacyDocumentPipelineShadowInputV1`;
2. o adapter avalia qual controle de pipeline legado seria selecionado;
3. o resultado entra em `CanonicalDocumentFacadeV1.legacy_pipeline_shadow`;
4. esse resultado tambem fica registrado em `request.state.v2_document_shadow_summary`;
5. as projecoes canônicas do Inspetor e da Mesa passam a carregar:
   - `legacy_pipeline_shadow`
   - `legacy_pipeline_name`
   - `legacy_template_resolution`
   - `legacy_materialization_allowed`
   - `legacy_issue_allowed`
   - `legacy_blockers`
   - `compatibility_summary`

Tudo isso continua interno/canônico. O payload publico legado segue igual.

## Pipelines e resultados observados

Pipelines nomeados nesta fase:

- `editor_rico_preview`
- `legacy_pdf_preview`
- `legacy_pdf_fallback`
- `not_available`

Exemplos de blockers shadow:

- `legacy_no_active_report`
- `legacy_editor_document_missing`
- `legacy_pdf_base_missing`
- `legacy_template_mode_unknown`
- `legacy_template_requires_form_data`

## Comparacao canônico x legado

O adapter shadow passa a comparar:

- `materialization_allowed` canônico vs legado;
- `issue_allowed` canônico vs legado;
- se o binding canônico coincide com o caminho realmente selecionado pelo legado;
- se o estado de bloqueio canônico coincide com o bloqueio observado no legado.

Campos principais da comparacao:

- `template_binding_agrees`
- `blockers_match`
- `divergences`
- `compatibility_state`
- `comparison_quality`

Observacao importante:

- quando o legado cai para `legacy_pdf_fallback` por ausencia de `dados_formulario`, o sistema registra essa divergencia sem alterar o retorno ao usuario.

## Feature flag

Nova flag desta fase:

- `TARIEL_V2_DOCUMENT_SHADOW`

Comportamento:

- `0`: a facade documental continua sem shadow adapter legado;
- `1`: o shadow adapter roda internamente nos fluxos do Inspetor e da Mesa;
- payload publico continua igual.

## Pontos de integracao reais

Integracao aplicada em:

- `web/app/domains/chat/laudo_service.py` no fluxo de `/app/api/laudo/status`
- `web/app/domains/revisor/mesa_api.py` no fluxo de `/revisao/api/laudo/{laudo_id}/pacote`

Nesses dois pontos:

- a leitura canônica passa a carregar o shadow do pipeline legado;
- os adapters legados continuam preservando o payload atual;
- o fallback operacional continua sendo o caminho legado puro.

## Telemetria e degradacao segura

Quando a flag esta ativa:

- o resultado shadow fica em `request.state.v2_document_shadow_summary`;
- as projecoes canônicas carregam o shadow serializado;
- falhas do shadow nao quebram o fluxo;
- inconsistencias degradam para blockers e divergencias seguras;
- nao ha log ruidoso nem emissao real de documento.

## O que nao mudou

- endpoint publico do Inspetor;
- endpoint publico da Mesa;
- payload publico consumido hoje;
- pipeline legado visivel ao usuario;
- emissao/materializacao real;
- UX;
- auth/session/multiportal;
- banco e schema.

## Rollback

Rollback simples:

1. desligar `TARIEL_V2_DOCUMENT_SHADOW`;
2. opcionalmente desligar `TARIEL_V2_DOCUMENT_FACADE` e as demais flags V2 relacionadas se tambem quiser parar os caminhos canônicos paralelos;
3. o sistema volta imediatamente a nao avaliar o pipeline legado em shadow mode.

## Testes adicionados

- `web/tests/test_v2_document_shadow.py`

Cobertura adicionada:

- shape do input/result shadow;
- selecao de `editor_rico_preview`;
- queda controlada para `legacy_pdf_fallback`;
- preservacao do payload publico do Inspetor;
- preservacao do payload publico da Mesa.

## O que ainda falta antes de materializacao real

Esta fase ainda nao faz:

- chamada real de materializacao controlada;
- emissao canônica;
- retorno do documento materializado ao caso;
- enforcement de policy;
- troca do pipeline legado por DOCX/Word ou schema estruturado.

Proximo passo recomendado:

- `Epic 08A - primeiro adapter Android para contratos canônicos de leitura do caso`
