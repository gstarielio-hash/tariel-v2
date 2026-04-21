# Epic 10A - Implementação real do soft gate documental sobre materialização/emissão

## Objetivo

Criar a primeira camada real, interna, observável e reversível de soft gate documental do V2 sem alterar comportamento público, UX, payloads nem o pipeline legado de materialização/emissão.

Nesta fase o gate:

- calcula decisão canônica de `would_block`
- usa somente sinais reais já disponíveis no V2 incremental
- fica acoplado a pontos reais do pipeline documental legado
- não bloqueia o usuário
- não muda a resposta pública das rotas integradas

## Pontos reais auditados do pipeline documental

### Pontos encontrados

- preview PDF do inspetor:
  - `web/app/domains/chat/chat_aux_routes.py::rota_pdf`
  - rota pública: `/app/api/gerar_pdf`
  - baixo risco
  - leitura/preview
  - side effect técnico limitado à geração temporária do PDF
- pacote documental da mesa:
  - `web/app/domains/revisor/mesa_api.py::obter_pacote_mesa_laudo`
  - rota pública: `/revisao/api/laudo/{laudo_id}/pacote`
  - baixo risco
  - leitura pura do pacote
  - já concentrava provenance, policy e facade do V2
- exportação PDF do pacote:
  - `web/app/domains/revisor/mesa_api.py::exportar_pacote_mesa_laudo_pdf`
  - gera arquivo, mas nesta fase foi deixado fora para manter a integração mais cirúrgica
- finalização/envio do laudo:
  - `web/app/domains/chat/laudo_service.py::finalizar_relatorio_resposta`
  - altera estado real
  - não escolhido nesta fase
- aprovação final da mesa:
  - `web/app/domains/revisor/service_messaging.py::avaliar_laudo_revisor`
  - altera estado real de emissão/liberação
  - não escolhido nesta fase

### Pontos escolhidos

Foram integrados exatamente dois pontos reais de baixo risco:

1. `rota_pdf`
2. `obter_pacote_mesa_laudo`

Motivo:

- são operações reais do pipeline documental legado
- já têm contexto suficiente para tenant, laudo, template, provenance e status
- permitem calcular gate canônico sem enforcement
- mantêm resposta pública e UX intactas

## Feature flag da fase

- `TARIEL_V2_DOCUMENT_SOFT_GATE`

Comportamento:

- desligada:
  - o sistema segue exatamente como antes
  - nenhuma decisão do soft gate é calculada
- ligada:
  - o soft gate é calculado internamente nos pontos integrados
  - a decisão é anexada a `request.state`
  - a operação real continua exatamente igual para o usuário

## Estruturas canônicas implementadas

Arquivos:

- `web/app/v2/document/gate_models.py`
- `web/app/v2/document/gates.py`
- `web/app/v2/document/gate_metrics.py`

Estruturas:

- `DocumentSoftGateRouteContextV1`
- `DocumentSoftGateBlockerV1`
- `DocumentSoftGateDecisionV1`
- `DocumentSoftGateTraceV1`
- `DocumentSoftGateSummaryV1`

Campos cobertos:

- `tenant_id`
- `case_id`
- `legacy_laudo_id`
- `document_id`
- `template_id`
- `template_key`
- `template_source_kind`
- `route_context`
- `operation_kind`
- `materialization_would_be_blocked`
- `issue_would_be_blocked`
- `blockers`
- `policy_summary`
- `provenance_summary`
- `document_readiness`
- `decision_source`
- `correlation_id`
- `request_id`
- `timestamp`

## Como a decisão soft gate é calculada

Fonte de sinais reais:

- `TechnicalCaseStatusSnapshot`
- `CanonicalDocumentFacadeV1`
- `DocumentMaterializationReadinessV1`
- `DocumentPolicyViewSummary`
- `ContentOriginSummary`
- binding real de template legado

Blockers canônicos avaliados nesta fase:

- `no_active_report`
- `template_not_bound`
- `template_source_unknown`
- `materialization_disallowed_by_policy`
- `issue_disallowed_by_policy`
- `review_requirement_not_satisfied`
- `engineer_approval_requirement_not_satisfied`
- `provenance_summary_unavailable`
- `document_source_insufficient`

Regras aplicadas:

- ausência de template binding bloqueia materialização e emissão
- `materialization_allowed=false` da facade/policy bloqueia materialização e emissão
- `issue_allowed=false` bloqueia emissão
- `review_required=true` sem caso aprovado bloqueia emissão
- `engineer_approval_required=true` sem `issue_allowed` bloqueia emissão
- provenance ausente ou `legacy_unknown` suficiente bloqueia emissão de forma conservadora
- quando um sinal não existe, o estado é tratado como `unknown` e materializado no blocker correspondente

## Integração real aplicada

### 1. Preview PDF do inspetor

Arquivo:

- `web/app/domains/chat/chat_aux_routes.py`

Integração:

- o gate é calculado logo antes do retorno do PDF
- o `route_context` registra:
  - `operation_kind=preview_pdf`
  - pipeline legado efetivo:
    - `editor_rico_preview`
    - `legacy_pdf_preview`
    - `legacy_pdf_fallback`
- a decisão fica em:
  - `request.state.v2_document_soft_gate_decision`
  - `request.state.v2_document_soft_gate_trace`

Importante:

- o retorno continua sendo o mesmo `FileResponse`
- o fallback legado continua intacto

### 2. Pacote documental da mesa

Arquivo:

- `web/app/domains/revisor/mesa_api.py`

Integração:

- o gate é calculado durante a leitura real do pacote
- o `route_context` registra:
  - `operation_kind=review_package_read`
  - `legacy_pipeline_name=legacy_review_package`
- a decisão fica em:
  - `request.state.v2_document_soft_gate_decision`
  - `request.state.v2_document_soft_gate_trace`
- quando a projeção V2 da mesa está ativa, o traço também é anexado ao summary interno da projeção

Importante:

- o `JSONResponse` público do pacote não muda
- o gate não interfere na leitura do pacote

## Observabilidade operacional

Arquivo:

- `web/app/v2/document/gate_metrics.py`

Foi adicionada agregação em memória com:

- total de decisões
- contagem de `materialization_would_block`
- contagem de `issue_would_block`
- agregação por `operation_kind`
- agregação por `blocker_code`
- agregação por tenant
- últimos traces recentes

Endpoint criado:

- `GET /admin/api/document-soft-gate/summary`

Proteção:

- admin only
- local only
- retorna `404` quando `TARIEL_V2_DOCUMENT_SOFT_GATE` está desligada

Como consultar localmente:

- subir a aplicação com `TARIEL_V2_DOCUMENT_SOFT_GATE=1`
- executar alguma chamada real em `/app/api/gerar_pdf` ou `/revisao/api/laudo/{laudo_id}/pacote`
- consultar:
  - `GET /admin/api/document-soft-gate/summary`

## Rollback

Rollback rápido:

- desligar `TARIEL_V2_DOCUMENT_SOFT_GATE`

Efeito:

- o cálculo do soft gate para de ocorrer
- nenhuma rota pública muda
- o pipeline legado segue exatamente como antes

## O que não mudou nesta fase

- nenhum payload público foi alterado
- nenhuma rota pública mudou contrato
- nenhum usuário foi bloqueado
- nenhuma regra de negócio efetiva foi reforçada
- nenhum banco novo foi criado
- nenhum pipeline DOCX/PDF legado foi substituído
- nenhum código Android foi tocado

## Validação executada

- `PYTHONPATH=web python3 -m py_compile web/app/v2/runtime.py web/app/v2/document/gate_models.py web/app/v2/document/gates.py web/app/v2/document/gate_metrics.py web/app/v2/document/__init__.py web/app/domains/chat/chat_aux_routes.py web/app/domains/revisor/mesa_api.py web/app/domains/admin/routes.py web/tests/test_v2_document_soft_gate.py web/tests/test_v2_document_soft_gate_integration.py web/tests/test_v2_document_soft_gate_summary.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_facade.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_shadow.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_integration.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_v2_document_soft_gate_summary.py`
- `PYTHONPATH=web python3 -m pytest -q web/tests/test_smoke.py`

## O que falta antes do hard gate

- integrar o mesmo gate em pontos mutáveis de emissão/finalização real
- definir rollout controlado de enforcement por tenant/template
- decidir o primeiro ponto de hard gate real com fallback/override operacional
- materializar auditoria histórica mais persistente se a fase seguinte exigir retenção além de memória
