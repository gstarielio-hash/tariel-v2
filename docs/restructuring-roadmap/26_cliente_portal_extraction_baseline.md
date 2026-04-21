# Fase 2.1 - Baseline da extracao controlada de `web/static/js/cliente/portal.js`

## Objetivo

Abrir a Fase 2 por um hotspot frontend contido, com a menor intervencao segura possivel, sem alterar:

- backend;
- endpoints;
- payloads;
- contratos do produto;
- regras de negocio;
- UX ou HTML funcional do portal cliente.

Este documento registra o estado do monolito antes do corte desta fase e explica por que o primeiro passo escolhido foi a extracao de helpers internos, e nao de fluxos de negocio.

## Baseline do entrypoint antes da fase

Arquivo auditado:

- `web/static/js/cliente/portal.js`

Tamanho observado antes do corte:

- aproximadamente `3080` linhas;
- um unico IIFE;
- guard principal em `window.__TARIEL_CLIENTE_PORTAL_WIRED__`.

Template de entrada:

- `web/templates/cliente_portal.html`

Ordem real antes da fase:

1. `/static/js/shared/api-core.js?v={{ v_app }}` apenas quando `perf_mode`
2. `/static/js/cliente/portal.js?v={{ v_app }}`

Conclusao do baseline:

- o portal cliente era um entrypoint unico, com baixo risco de ordem entre multiplos arquivos;
- o risco maior era interno: responsabilidades demais concentradas em um unico arquivo.

## Responsabilidades misturadas no monolito

### 1. Runtime e infraestrutura local

Blocos observados no topo do arquivo:

- `perfSync`, `perfAsync`, `perfSnapshot`;
- `api`, `withBusy`, `feedback`;
- `escapeHtml`, `escapeAttr`, `textoComQuebras`, `formatar*`;
- persistencia de aba e selecao em `localStorage`;
- `definirTab()` e navegacao basica entre paineis.

Caracteristica:

- baixo acoplamento com regras de negocio;
- dependencia apenas de `state`, `document`, `window`, `fetch` e `TarielPerf`.

### 2. Estado derivado, prioridade e filtros

Blocos observados no mesmo arquivo:

- `construirPrioridadesPortal()`;
- `prioridadeEmpresa`, `prioridadeUsuario`, `prioridadeChat`, `prioridadeMesa`;
- `variantStatusLaudo`, `laudoChatParado`, `laudoMesaParado`;
- `filtrarUsuarios`, `filtrarLaudosChat`, `filtrarLaudosMesa`;
- badges e rotulos operacionais.

Caracteristica:

- logica majoritariamente pura ou semi-pura;
- depende de `state.bootstrap` e `state.ui`, mas nao faz fetch nem bind de eventos;
- alta reutilizacao por varios renders, o que aumenta o ruído dentro do entrypoint.

### 3. Render de DOM por area

Ainda no mesmo arquivo:

- render admin;
- render chat;
- render mesa;
- render de resumos, cards, listas, contexto e mensagens.

Caracteristica:

- forte acoplamento com IDs do template;
- maior risco de regressao visual se extraido cedo demais.

### 4. Orquestracao de boot e rede

Blocos observados:

- `bootstrapPortal()`;
- `loadChat()`;
- `loadMesa()`;
- sincronizacao de selecoes e estado atual.

Caracteristica:

- fronteira direta com APIs do portal cliente;
- altera estado global do entrypoint;
- alto risco funcional se quebrado nesta primeira extracao.

### 5. Bind de acoes e fluxos de negocio

Blocos observados:

- `bindAdminActions()`;
- `bindCommercialActions()`;
- `bindChatActions()`;
- `bindMesaActions()`;
- `init()`.

Caracteristica:

- concentra eventos criticos do portal;
- mistura DOM, estado, fetch e fluxo funcional;
- pior candidato para primeira extracao.

## Cortes considerados

## 1. Extrair apenas constants/selectors

Vantagem:

- risco baixissimo.

Desvantagem:

- ganho arquitetural pequeno demais;
- `portal.js` continuaria dono de quase toda a complexidade real.

## 2. Extrair runtime local e helpers derivados

Vantagem:

- remove o topo mais barulhento do monolito;
- preserva `portal.js` como facade;
- nao mexe em endpoints nem nos renders mais frageis;
- separa ownership entre infraestrutura local e semantica operacional.

Desvantagem:

- introduz dependencia de ordem entre tres scripts do portal cliente.

## 3. Extrair loaders de rede ou binds de acoes

Vantagem:

- reduziria mais linhas do entrypoint.

Desvantagem:

- risco funcional alto na primeira fase da modularizacao;
- fronteiras ainda muito acopladas a estado mutavel, DOM e fluxo de negocio.

## Corte escolhido

O corte escolhido foi o item `2`.

Razoes:

- era o maior ganho estrutural com risco ainda controlado;
- permitia criar ownership claro sem reescrever o portal;
- mantinha `portal.js` como entrypoint conhecido pelo template e pelo resto do sistema;
- nao exigia bundler, `import`, mudanca de backend nem troca de contrato com o HTML.

## O que ficou explicitamente fora desta fase

- extracao dos renders admin/chat/mesa;
- extracao dos binds de acoes do portal;
- mudanca de pipeline;
- adocao de ES modules;
- remocao de globals existentes;
- qualquer alteracao de endpoint, payload ou regra de negocio.
