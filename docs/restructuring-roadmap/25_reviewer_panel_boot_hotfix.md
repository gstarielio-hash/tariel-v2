# Fase 01.9 - Hotfix seguro do boot de `/revisao/painel`

## Objetivo

Reduzir o custo do boot do painel do revisor sem alterar:

- endpoints;
- payloads;
- regras de negocio;
- auth/session/multiportal;
- contratos do painel do revisor;
- HTML final entregue pelo SSR.

## Hotfix aplicado

## 1. Primeiro laudo aberto agora reaproveita `/completo?incluir_historico=true`

Arquivo:

- `web/static/js/revisor/painel_revisor_page.js`

Mudanca:

- `carregarLaudo()` passou a buscar `GET /revisao/api/laudo/{id}/completo?incluir_historico=true`;
- a timeline inicial agora e hidratada diretamente de `dados.historico` + `dados.historico_paginado`;
- o boot deixou de disparar `carregarHistoricoMensagens({ appendAntigas: false })` como request separado no first load.

Efeito:

- o primeiro laudo aberto caiu de 3 requests para 2;
- o painel continua usando `/revisao/api/laudo/{id}/mensagens` apenas para paginacao adicional, refresh posterior ou contexto reaberto.

## 2. Reuso de request em voo para o loader principal do laudo

Arquivos:

- `web/static/js/revisor/painel_revisor_page.js`
- `web/static/js/revisor/revisor_painel_core.js`

Mudanca:

- novo par de estado:
  - `state.laudoLoadPromise`
  - `state.laudoLoadLaudoId`
- se o mesmo laudo ja estiver em carregamento e um novo disparo chegar antes da conclusao, o painel reutiliza a promise em voo em vez de abortar e reiniciar o mesmo fetch.

Efeito:

- evita reload redundante no mesmo laudo durante o bootstrap;
- mantem troca de laudo diferente com abort seguro do contexto anterior.

## 3. Reuso de request em voo para o pacote da mesa

Arquivo:

- `web/static/js/revisor/revisor_painel_core.js`

Mudanca:

- novo par de estado:
  - `state.pacoteMesaPromise`
  - `state.pacoteMesaEmVooLaudoId`
- `obterPacoteMesaLaudo()` agora reutiliza a promise em voo do mesmo laudo quando o fetch ainda nao terminou.

Efeito:

- evita fan-out duplicado em acoes como abrir resumo, baixar pacote ou reabrir o mesmo contexto da mesa enquanto o pacote ainda esta carregando.

## 4. SSR do painel passou a usar lookup em lote para dados derivados

Arquivo:

- `web/app/domains/revisor/panel.py`

Mudanca:

- o SSR deixou de depender de acesso lazy por item para:
  - nome do inspetor (`Usuario`) nas listas;
  - hash curto do laudo nos whispers.
- os nomes dos inspetores agora sao resolvidos por uma consulta batelada unica (`usuarios_por_id`);
- os hashes dos laudos dos whispers agora sao resolvidos por uma consulta batelada unica (`whispers_hash_por_laudo`).

Efeito:

- o painel deixa de crescer por item em datasets com varios inspetores ou whispers de laudos distintos;
- o SSR fica mais previsivel para a Fase 2.

## Resultado observado

### Mesmo seed local do baseline

SSR de `GET /revisao/painel`:

- antes: `sql_count=16`, `duration_ms=12.601`
- depois: `sql_count=14`, `duration_ms=11.867`

Primeiro laudo aberto:

- antes: `3 requests`, `total_sql=18`
- depois: `2 requests`, `total_sql=14`

Detalhe do fluxo atual medido:

- `GET /revisao/api/laudo/1/completo?incluir_historico=true` -> `sql_count=7`, `duration_ms=9.696`
- `GET /revisao/api/laudo/1/pacote` -> `sql_count=7`, `duration_ms=7.803`

Leitura pratica:

- o ganho principal foi reduzir a cadeia de boot do laudo ativo;
- o SSR tambem caiu 2 queries no seed comparavel, alem de eliminar lazy loads por item.

## O que permaneceu igual

- rota `/revisao/painel`
- APIs `/revisao/api/laudo/*`
- payload de `/completo`, `/mensagens` e `/pacote`
- websocket `/revisao/ws/whispers`
- filtros, lista de laudos, historico, mesa, aprendizados e acoes principais
- contratos escondidos em `#revisor-front-contract`

## Riscos remanescentes

- o portal ainda carrega toda a stack JS do revisor no HTML inicial; esta fase nao modulariza parse/ship de bundle;
- `/revisao/api/laudo/{id}/pacote` continua sendo o subrequest mais pesado do primeiro laudo aberto;
- `window.TarielRevisorPainel` continua sendo namespace global obrigatorio;
- `#revisor-front-contract` continua sendo dependencia de ordem e compatibilidade entre template e runtime.

## Cobertura adicionada

Novo teste:

- `web/tests/test_reviewer_panel_boot_hotfix.py`

O teste trava a regressao mais sensivel desta fase:

- o boot SSR do painel nao pode voltar a lazy-load por item `Usuario` ou `Laudo` ao montar listas e whispers.
