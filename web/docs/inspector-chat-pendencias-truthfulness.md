# Verdade das Pendências no Chat Inspetor

## Objetivo

Registrar a FASE 9 da reorganização do frontend do inspetor: remover placeholders sintéticos do painel de pendências e substituir isso por estados honestos de loading, vazio e erro, sem alterar backend, endpoints, payloads ou regras funcionais.

## Confirmado no código

### Onde os placeholders falsos existiam

- Template SSR: `web/templates/inspetor/workspace/_workspace_context_rail.html`
  - `#painel-pendencias-mesa`
  - `#lista-pendencias-mesa`
  - dois `<li class="technical-pending-item">` artificiais com textos de exemplo
- Runtime: `web/static/js/inspetor/pendencias.js`
  - função `renderizarListaPendencias(pendencias = [], append = false)`
  - quando o backend retornava zero itens em `abertas`, o JS reinjetava os mesmos cards fake

Também havia um contador inicial artificial no rail:

- `#workspace-progress-pendencias` nascia como `2 pendências`

### O que foi removido ou neutralizado

- Os `<li class="technical-pending-item">` falsos saíram do template do rail.
- O branch de `renderizarListaPendencias(...)` que recriava pendências sintéticas foi removido.
- O painel deixou de preencher a lista para “parecer cheia”.
- O contador SSR do progresso passou a nascer em `0 pendências`.

Agora:

- `#lista-pendencias-mesa` só recebe itens reais vindos do backend
- quando não há itens reais, o painel usa estado vazio honesto
- quando há falha de carga, usa estado de erro honesto

### Como ficaram os estados honestos

Arquivo: `web/templates/inspetor/workspace/_workspace_context_rail.html`

Foram criados três blocos semânticos separados da lista real:

- `#estado-loading-pendencias-mesa`
- `#texto-vazio-pendencias-mesa`
- `#estado-erro-pendencias-mesa`

Todos usam `technical-chat-empty` e não se passam por item de pendência real.

Regras atuais no runtime:

- loading:
  - `carregarPendenciasMesa(...)` mostra `#estado-loading-pendencias-mesa` em carregamentos não paginados
- empty:
  - `renderizarListaPendencias(...)` mostra `#texto-vazio-pendencias-mesa` quando o backend retorna zero itens reais
  - o texto muda conforme o filtro atual por `obterTextoVazioPendencias(...)`
- erro:
  - `carregarPendenciasMesa(...)` mostra `#estado-erro-pendencias-mesa` quando a carga inicial falha

### Como contagem, filtros e paginação passaram a refletir só dados reais

Arquivo principal: `web/static/js/inspetor/pendencias.js`

Campos usados:

- `estado.qtdPendenciasAbertas`
- `estado.totalPendenciasFiltradas`
- `estado.totalPendenciasExibidas`
- `estado.temMaisPendencias`

Esses valores agora continuam vindo apenas da resposta real do backend:

- `dados.abertas`
- `dados.total_filtrado`
- `dados.pendencias`
- `dados.tem_mais`

O resumo textual continua em:

- `#resumo-pendencias-mesa`

A paginação continua em:

- `#btn-carregar-mais-pendencias`

Os filtros continuam em:

- `[data-filtro-pendencias]`

Nenhum desses caminhos passou a depender de cards artificiais.

### Reflexo honesto em estado e dataset

Arquivo principal: `web/static/js/chat/chat_index_page.js`

Foi criado um espelho explícito para pendências:

- `construirResumoPendenciasWorkspace(...)`
- `espelharResumoPendenciasWorkspaceNoDataset(...)`
- `sincronizarResumoPendenciasWorkspace(...)`

Campos refletidos:

- `document.body.dataset.pendenciasCount`
- `document.body.dataset.pendenciasFilteredTotal`
- `document.body.dataset.pendenciasOpenCount`
- `document.body.dataset.pendenciasEmpty`
- `document.body.dataset.pendenciasSynthetic = "0"`
- `document.body.dataset.pendenciasError`
- `document.body.dataset.pendenciasLoading`
- `document.body.dataset.pendenciasHonestEmpty`
- `document.body.dataset.pendenciasState`

Os mesmos campos também são espelhados em:

- `#painel-chat.dataset.*`
- `#painel-pendencias-mesa.dataset.*`

Esses datasets são reflexo do estado reconciliado; não viraram nova fonte primária.

### Integração com o rail

O painel continua pertencendo ao rail do workspace:

- arquivo estrutural: `web/templates/inspetor/workspace/_workspace_context_rail.html`
- root do rail: `[data-workspace-rail-root]`

Nada nesta fase alterou as regras de visibilidade do rail por screen mode. Isso preserva o comportamento já consolidado:

- `portal_dashboard`: rail do workspace fora de disputa
- `assistant_landing`: rail oculto
- `inspection_record`: rail permitido
- `inspection_conversation`: rail permitido
- `new_inspection`: overlay continua dominante

### Hooks preservados

Continuam preservados:

- `#painel-pendencias-mesa`
- `#lista-pendencias-mesa`
- `[data-filtro-pendencias]`
- `#btn-carregar-mais-pendencias`
- `#btn-marcar-pendencias-lidas`
- `#btn-exportar-pendencias-pdf`
- `.btn-pendencia-item`

Também foram preservadas as ações reais:

- marcar pendência como lida
- reabrir pendência
- exportar PDF
- carregar mais

### O que não foi alterado

- backend
- endpoints
- payloads do backend
- SSE
- integração funcional com mesa
- finalização/reabertura
- histórico já corrigido na fase anterior
- autoridade de estado
- namespace canônico de eventos
- placeholders de outros subsistemas

## Inferência provável

- O painel de pendências agora deixa de distorcer a leitura do rail e da atividade recente, porque `estado.pendenciasItens` não é mais preenchido com exemplos artificiais.
- O uso de `technical-chat-empty` no rail reduz risco visual porque reaproveita um bloco já carregado no frontend do inspetor, sem introduzir mais uma gramática de estado.

## Dúvida aberta

- O código atual não expõe um evento canônico público específico para “pendências renderizadas”. Nesta fase isso não foi criado porque não apareceu consumer real exigindo esse evento.
- `btnAbrirPendenciasMesa` e `badgePendenciasMesa` continuam como referências legadas opcionais no módulo; não foram mexidos porque não fazem parte da remoção dos placeholders falsos.

## Arquivos tocados nesta fase

- `web/templates/inspetor/workspace/_workspace_context_rail.html`
- `web/static/js/inspetor/pendencias.js`
- `web/static/js/chat/chat_index_page.js`
- `web/docs/inspector-chat-pendencias-truthfulness.md`
