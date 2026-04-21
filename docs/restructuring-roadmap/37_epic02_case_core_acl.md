# Epic 02A - ACL inicial do Technical Case Core sobre o laudo legado

## Objetivo

Introduzir a primeira ACL real do `Technical Case Core` dentro do sistema vivo de forma:

- aditiva;
- segura;
- com rollback simples;
- sem alterar endpoint publico, payload publico, regra de negocio, UX ou auth/session.

O foco desta fase nao foi criar o `Technical Case Core` completo. O objetivo foi encapsular a primeira leitura canonica de identidade e estado do caso a partir do legado de laudo.

## O que foi implementado

Foi criada a estrutura incremental:

- `web/app/v2/acl/__init__.py`
- `web/app/v2/acl/technical_case_core.py`

Modelos canonicos internos adicionados:

- `TechnicalCaseRef`
- `TechnicalCaseStatusSnapshot`

Funcoes principais da ACL:

- `build_technical_case_ref_from_legacy_laudo(...)`
- `resolve_canonical_case_status_from_legacy(...)`
- `build_technical_case_status_snapshot_from_legacy(...)`
- `build_technical_case_status_snapshot_for_user(...)`

## Ponto do legado encapsulado

O primeiro encapsulamento real foi feito no mesmo fluxo de baixo risco do Epic 01A:

- `web/app/domains/chat/laudo_service.py`
- funcao `obter_status_relatorio_resposta()`

Sinais do legado agora traduzidos pela ACL:

- `laudo_id`
- `estado`
- `permite_reabrir`
- `status_card`
- `status_revisao`
- `laudo_card`

O sistema atual continua produzindo o payload legado exatamente como antes. A ACL roda internamente e produz um snapshot canonico em paralelo.

## Contrato interno novo da ACL

Identidade canonica incremental:

- `case_id`: `case:legacy-laudo:{tenant_id}:{laudo_id}`
- `thread_id`: `thread:legacy-laudo:{tenant_id}:{laudo_id}`
- `document_id`: `document:legacy-laudo:{tenant_id}:{laudo_id}`

Status canonico minimo desta fase:

- `draft`
- `collecting_evidence`
- `needs_reviewer`
- `review_feedback_pending`
- `approved`

Mapeamento inicial legado -> canonico:

- `sem_relatorio` -> `draft`
- `relatorio_ativo` / `Rascunho` -> `collecting_evidence`
- `aguardando` / `Aguardando Aval` -> `needs_reviewer`
- `ajustes` / `Rejeitado` / `permite_reabrir=true` -> `review_feedback_pending`
- `aprovado` / `Aprovado` -> `approved`

## Feature flags

Flags desta fase:

- `TARIEL_V2_CASE_CORE_ACL`
- `TARIEL_V2_ENVELOPES`

Comportamento:

- `TARIEL_V2_CASE_CORE_ACL=0`: a ACL nao roda no fluxo piloto.
- `TARIEL_V2_CASE_CORE_ACL=1`: a ACL monta `TechnicalCaseStatusSnapshot` e o armazena em `request.state`.
- `TARIEL_V2_ENVELOPES=1`: o shadow mode continua montando `InspectorCaseStatusProjectionV1`.
- quando as duas flags estao ativas, a projeção piloto passa a ser alimentada pela ACL, e nao mais por derivacao espalhada do laudo.

## Como funciona o shadow mode agora

Fluxo incremental atualizado:

1. o payload legado de `/app/api/laudo/status` continua sendo montado do jeito antigo;
2. quando `TARIEL_V2_CASE_CORE_ACL=1`, a ACL monta `TechnicalCaseStatusSnapshot`;
3. o snapshot canonico fica disponivel em `request.state.v2_case_core_snapshot`;
4. quando `TARIEL_V2_ENVELOPES=1`, `run_inspector_case_status_shadow()` continua rodando em paralelo;
5. se a ACL estiver ativa, `InspectorCaseStatusProjectionV1` passa a ser construida a partir do snapshot canonico;
6. divergencias continuam discretas e ficam registradas apenas no shadow result interno.

## O que nao mudou

- endpoint publico `/app/api/laudo/status`;
- payload legado retornado para web e Android;
- regra de negocio do ciclo do laudo;
- auth/session/multiportal;
- consumidor final do contrato novo;
- Android;
- documento/laudo como contrato publico atual;
- tempo real e colaboracao.

## Rollback

Rollback operacional simples:

1. desligar `TARIEL_V2_CASE_CORE_ACL`;
2. opcionalmente desligar `TARIEL_V2_ENVELOPES` se tambem quiser parar o shadow mode do piloto;
3. o sistema volta a usar apenas a leitura legado + projeção legado do Epic 01A;
4. nao ha rollback de rota, UI, banco ou schema.

## Testes adicionados e ajustados

- `web/tests/test_v2_case_core_acl.py`
- `web/tests/test_v2_envelopes.py`
- `web/tests/test_v2_projection_shadow.py`

Cobertura desta fase:

- mapeamento `laudo legado -> TechnicalCaseRef`;
- normalizacao do status canonico do caso;
- integracao da ACL com `InspectorCaseStatusProjectionV1`;
- preservacao do payload publico atual;
- comportamento sob feature flags;
- integracao da ACL no fluxo real de `obter_status_relatorio_resposta()`.

## Proximos passos que dependem desta ACL

Esta fase destrava:

- primeira projeção canonica real do Inspetor;
- consumer piloto da projeção com `case_id` canonico;
- provenance minima IA/humana vinculada ao caso;
- futuras ACLs para thread principal e documento.

Proximo passo recomendado apos esta fase:

- `Epic 03A - primeira projecao canonica do Inspetor consumindo a ACL do Technical Case Core`

## Riscos remanescentes

- o `case_id` canonico ainda e uma identidade namespaced derivada do `laudo_id` legado, nao uma entidade soberana persistida;
- a ACL ainda cobre apenas leitura de status/identidade e nao orquestra estado real do caso;
- a separacao definitiva entre `caso`, `thread` e `documento` ainda depende de slices futuros;
- o consumer piloto continua interno e em shadow mode.
