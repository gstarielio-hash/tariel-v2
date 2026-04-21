# Epic 01A - Envelopes canonicos base + contrato piloto em shadow mode

## Objetivo

Introduzir no sistema vivo a primeira camada real dos envelopes canonicos do V2 de forma:

- aditiva;
- segura;
- com rollback simples;
- sem alterar endpoint publico, payload publico, regra de negocio, UX ou auth/session.

O foco desta fase nao foi criar ACL do caso nem trocar consumidor final. O objetivo foi abrir a base contratual para os proximos slices.

## O que foi implementado

Foi criada uma estrutura incremental nova em `web/app/v2/` com:

- `web/app/v2/runtime.py`
- `web/app/v2/contracts/envelopes.py`
- `web/app/v2/contracts/commands.py`
- `web/app/v2/contracts/events.py`
- `web/app/v2/contracts/projections.py`
- `web/app/v2/shadow.py`

Biblioteca base implementada:

- `BaseEnvelope`
- `CommandEnvelope`
- `DomainEventEnvelope`
- `CollaborationEventEnvelope`
- `ProjectionEnvelope`

Campos suportados na base:

- `contract_name`
- `contract_version`
- `tenant_id`
- `case_id`
- `thread_id`
- `document_id`
- `actor_id`
- `actor_role`
- `correlation_id`
- `causation_id`
- `idempotency_key`
- `source_channel`
- `origin_kind`
- `sensitivity`
- `visibility_scope`
- `timestamp`
- `payload`

## Contrato piloto escolhido

Contrato piloto implementado:

- `InspectorCaseStatusProjectionV1`

Motivo da escolha:

- o endpoint `/app/api/laudo/status` ja existe, e leitura de baixo risco;
- ele nao exige mudanca de UX;
- ele permite montar uma projeção paralela sem alterar o payload legado;
- ele se conecta diretamente ao backlog do V2 para `Projecao canonica do Inspetor`.

Payload piloto modelado:

- `legacy_laudo_id`
- `state`
- `allows_reopen`
- `has_active_report`
- `laudo_card`
- `legacy_payload_keys`

Observacao importante:

- neste primeiro slice, `case_id` do envelope piloto ainda e derivado do `laudo_id` legado quando presente;
- isso e uma compatibilidade temporaria e intencional, ate a futura ACL do `Technical Case Core`.

## Feature flag

Flag implementada:

- `TARIEL_V2_ENVELOPES`

Comportamento:

- desligada por padrao;
- quando desligada, nada do piloto roda;
- quando ligada, o sistema continua respondendo o payload atual normalmente e monta a projeção piloto em paralelo.

## Como funciona o shadow mode

Ponto piloto real:

- `web/app/domains/chat/laudo_service.py`
- funcao `obter_status_relatorio_resposta()`

Fluxo:

1. o payload atual do status do relatorio continua sendo montado do jeito antigo;
2. quando `TARIEL_V2_ENVELOPES=1`, `run_inspector_case_status_shadow()` roda em paralelo;
3. o contrato `InspectorCaseStatusProjectionV1` e construido a partir do payload legado;
4. um resultado de compatibilidade e montado e armazenado em `request.state`;
5. o payload publico retornado para o cliente nao muda.

Leitura pratica:

- ha consumer real do contrato novo;
- esse consumer ainda e interno e controlado;
- ele ja valida shape, serializacao e compatibilidade basica sem afetar web ou Android.

## O que nao mudou

- endpoints publicos atuais;
- payload retornado por `/app/api/laudo/status`;
- regras de negocio do ciclo do laudo;
- auth/session/multiportal;
- UI do Inspetor, Cliente, Revisor ou Admin;
- Android;
- ACL do caso;
- facade documental;
- policy engine.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_ENVELOPES`;
2. o shadow mode para imediatamente;
3. o payload legado continua como unico caminho ativo;
4. a biblioteca `app.v2` permanece inerte ate nova rodada.

Nao ha necessidade de rollback estrutural de rota, UI ou banco nesta fase.

## Testes adicionados

- `web/tests/test_v2_envelopes.py`
- `web/tests/test_v2_projection_shadow.py`

Cobertura desta fase:

- shape do envelope base;
- shape e serializacao do contrato piloto;
- comportamento do shadow mode ligado e desligado;
- garantia de que `/app/api/laudo/status` continua retornando o mesmo payload publico.

## Proximos passos que dependem desta fase

Esta fase destrava:

- ACL do `Technical Case Core`;
- projeção canonica do Inspetor;
- provenance minima IA/humana;
- adapters paralelos futuros para web e Android.

Proximo passo recomendado apos esta fase:

- `Epic 02A - primeira ACL do Technical Case Core sobre o status/identidade do laudo legado`

## Riscos remanescentes

- o piloto ainda usa `laudo_id` como referencia provisoria de `case_id`;
- ainda nao existe ACL do caso para separar definitivamente `caso`, `thread` e `documento`;
- o consumer piloto ainda e interno e nao prova leitura canônica em uma superficie final;
- observabilidade de divergencia ainda e minima e deliberadamente discreta.
