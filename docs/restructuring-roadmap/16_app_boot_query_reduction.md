# Fase 01.6 — Hotfix de N+1 no Boot SSR de `/app`

## Objetivo

Reduzir a amplificação de queries no SSR do portal do Inspetor (`GET /app/`) sem alterar endpoints públicos, payloads, regras de negócio, auth/session, contratos multiportal ou comportamento visual do HTML entregue.

## Fonte exata do N+1

### Query repetida identificada

O hotspot remanescente do boot de `/app/` vinha da consulta de existência de mensagens por laudo:

- `SELECT mensagens_laudo.id ... WHERE mensagens_laudo.laudo_id = ? LIMIT ? OFFSET ?`

### Função raiz

Arquivo:
- `web/app/domains/chat/laudo_state_helpers.py`

Função:
- `laudo_tem_interacao()`

Implementação original:
- fazia `banco.query(MensagemLaudo.id).filter(MensagemLaudo.laudo_id == laudo_id).first()`
- uma chamada por laudo
- reaplicada várias vezes no mesmo request

## Onde o loop acontecia no SSR de `/app`

### Handler real do request

`GET /app/`:
- `web/main.py` monta `roteador_inspetor` em `/app`
- `web/app/domains/chat/auth_portal_routes.py`
- handler: `pagina_inicial()`

### Cadeia de helpers do boot

`pagina_inicial()` montava o SSR chamando:

1. `estado_relatorio_sanitizado()`
2. `listar_laudos_recentes_portal_inspetor()`
3. `montar_contexto_portal_inspetor()`

### Loops que reexecutavam a query

`web/app/domains/chat/session_helpers.py`
- `estado_relatorio_sanitizado()`
- para o laudo ativo, chamava repetidamente:
  - `obter_estado_api_laudo()`
  - `obter_status_card_laudo()`
  - `laudo_permite_reabrir()`
  - `laudo_tem_interacao()`
- isso podia repetir a verificação de `mensagens_laudo` várias vezes no mesmo laudo

`web/app/domains/chat/auth_mobile_support.py`
- `listar_laudos_recentes_portal_inspetor()`
- loop sobre até `limite_consulta=40` laudos
- para cada item visível, a cadeia abaixo podia ser chamada mais de uma vez:
  - `laudo_possui_historico_visivel()`
  - `serializar_card_laudo()`
  - `obter_status_card_laudo()`
  - `laudo_permite_reabrir()`

`web/app/domains/chat/auth_mobile_support.py`
- `montar_contexto_portal_inspetor()`
- loop em todos os laudos do inspetor para:
  - filtrar visíveis
  - computar cards de status
  - montar `laudos_portal_cards`
- a mesma verificação de interação era refeita para o mesmo laudo em mais de um bloco do contexto

## O que não era a origem do N+1

Não foi encontrado template Jinja disparando query item a item.

Templates auditados:
- `web/templates/inspetor/_portal_main.html`
- `web/templates/inspetor/_sidebar.html`
- `web/templates/inspetor/_portal_home.html`
- `web/templates/inspetor/_macros.html`

Conclusão:
- o N+1 vinha do backend antes do render
- o template só consumia coleções já montadas (`laudos_sidebar`, `laudos_portal_cards`, `cards_status`)

## Hotfix aplicado

### 1. Cache por request explícito

Arquivo:
- `web/app/domains/chat/laudo_state_helpers.py`

Adicionado:
- `CacheResumoLaudoRequest`
- `criar_cache_resumo_laudos()`

Esse cache guarda, por laudo e por request:
- existência de interação
- visibilidade do histórico
- `status_card`
- payload resumido de card

Escopo:
- só request-scope
- sem cache global
- sem persistência

### 2. Carga em lote de interação por laudo

Arquivo:
- `web/app/domains/chat/laudo_state_helpers.py`

Adicionado:
- `precarregar_interacoes_laudos()`

Estratégia:
- em vez de consultar `mensagens_laudo` laudo a laudo
- carrega os `laudo_id` que possuem mensagens em uma query em lote
- preenche o cache do request antes dos loops de SSR

### 3. Reuso do mesmo cache em todo o boot de `/app`

Arquivo:
- `web/app/domains/chat/auth_portal_routes.py`

Mudança:
- `pagina_inicial()` agora cria um único `resumo_cache`
- o mesmo cache é repassado para:
  - `estado_relatorio_sanitizado()`
  - `listar_laudos_recentes_portal_inspetor()`
  - `montar_contexto_portal_inspetor()`

### 4. Helpers SSR agora usam dados já resolvidos

Arquivos:
- `web/app/domains/chat/auth_mobile_support.py`
- `web/app/domains/chat/session_helpers.py`

Mudanças:
- `listar_laudos_recentes_portal_inspetor()` faz preload em lote antes do loop
- `montar_contexto_portal_inspetor()` reutiliza o mesmo cache para filtros, status e cards
- `estado_relatorio_sanitizado()` deixa de recalcular a mesma existência de mensagens várias vezes para o laudo ativo

## Como o template passou a receber os dados

O HTML continua recebendo o mesmo modelo final de render:

- `laudos_sidebar`
- `laudos_portal_cards`
- `cards_status`
- `estado_relatorio`

Diferença interna:
- esses objetos agora chegam com status/resumo derivados a partir de carga em lote + memoização por request
- o template não precisa dirigir leitura por laudo nem repetir helper com query implícita

## O que permaneceu igual

- endpoints públicos
- payloads
- regras de negócio
- auth/session/multiportal
- HTML final entregue ao usuário
- UX da sidebar, recentes, fixados, badges e abertura de laudos
- integrações IA/OCR/PDF

## Riscos residuais

- ainda existem duas leituras de `Laudo` no boot (`recentes` e `todos`) por motivos de montagem distinta de contexto; isso não é o hotspot de `mensagens_laudo`, mas ainda é custo restante
- se um benchmark incluir laudo ativo em sessão fora do conjunto previamente carregado, pode surgir uma query adicional isolada para o laudo selecionado
- o hotfix remove o N+1 principal, mas não tenta reestruturar profundamente o pipeline SSR nesta fase

## Redução esperada no próximo benchmark

Baseline observado:
- `GET /app/` com ~181 queries
- ~179 repetições da leitura de `mensagens_laudo`

Após o hotfix, espera-se:
- eliminar a query `SELECT mensagens_laudo.id ... WHERE mensagens_laudo.laudo_id = ? LIMIT ? OFFSET ?` em loop por laudo
- substituir isso por:
  - 1 query em lote para detectar interação dos laudos do boot
  - 1 query agregada de evidências por laudo
  - no máximo 1 query extra em cenário com laudo ativo fora do conjunto pré-carregado

Expectativa prática para `GET /app/`:
- sair de ~181 queries para faixa de um dígito alto ou baixo duplo dígito, dependendo do estado da sessão
- o componente específico de `mensagens_laudo` deve cair de ~179 leituras repetidas para algo próximo de `2` no cenário comum do boot da home

## Arquivos tocados nesta fase

- `web/app/domains/chat/laudo_state_helpers.py`
- `web/app/domains/chat/session_helpers.py`
- `web/app/domains/chat/auth_mobile_support.py`
- `web/app/domains/chat/auth_portal_routes.py`
- `web/tests/test_app_boot_query_reduction.py`
- `docs/restructuring-roadmap/16_app_boot_query_reduction.md`
