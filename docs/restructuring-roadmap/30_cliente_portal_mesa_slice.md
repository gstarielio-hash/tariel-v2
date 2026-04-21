# Fase 2.4 - Extracao controlada do slice mesa do portal cliente

## Objetivo

Continuar a modularizacao interna do portal cliente sem alterar:

- backend;
- endpoints;
- payloads;
- regras de negocio;
- contratos do produto;
- UX do portal cliente.

Nesta fase, o corte escolhido foi o slice `mesa`, que passou a ser o maior bloco coeso restante em `web/static/js/cliente/portal.js` depois das extracoes de runtime, prioridades, admin e chat.

## O que era o slice mesa antes da fase

Antes desta fase, `web/static/js/cliente/portal.js` ainda concentrava o ciclo inteiro da mesa do portal cliente:

- render do resumo geral, triagem, movimentos, lista, contexto e timeline da mesa;
- loader `loadMesa()` do laudo selecionado;
- marcação local de whispers lidos depois do carregamento do laudo;
- handlers de resposta, resposta com anexo, resolucao/reabertura de pendencia e avaliacao;
- busca da fila e filtros rapidos da mesa;
- controle local de `AbortController` do carregamento da mesa.

Blocos que estavam no facade antes da extracao:

- `cancelarCarregamentoMesa()`
- `renderMesaList()`
- `renderMesaTriagem()`
- `renderMesaMovimentos()`
- `renderMesaContext()`
- `renderMesaResumoGeral()`
- `renderMesaResumo()`
- `tituloMensagemMesa()`
- `classeMensagemMesa()`
- `renderMesaMensagens()`
- `loadMesa()`
- `bindMesaActions()`

Leitura arquitetural:

- o slice `mesa` misturava render, fetch, abort, DOM e handlers de submit no mesmo facade;
- o bloco era coeso o suficiente para sair junto sem tocar contratos do backend;
- os helpers realmente sensiveis e compartilhados continuavam sendo `renderAvisosOperacionais()`, `renderAnexos()` e o roteador `bindCommercialActions()`.

## O que foi extraido

Novo modulo:

- `web/static/js/cliente/portal_mesa.js`

Namespace interno criado:

- `window.TarielClientePortalMesa`

Responsabilidades movidas para o modulo:

- cancelamento local de carregamento da mesa;
- render do resumo geral da mesa;
- render da triagem da mesa;
- render dos movimentos recentes da mesa;
- render da lista de laudos da mesa;
- render do contexto do laudo selecionado;
- render do resumo/pacote carregado;
- render da timeline de mensagens da mesa;
- loader `loadMesa()` do laudo selecionado;
- busca da mesa;
- filtros rapidos da mesa;
- bind das acoes operacionais da mesa.

Leitura pratica:

- `portal_mesa.js` agora concentra a area operacional da mesa do portal cliente;
- o facade deixou de ser dono direto do lifecycle da mesa;
- a integracao continua via `state` compartilhado, callbacks do facade e helpers compartilhados injetados.

## O que continuou em `portal.js`

`web/static/js/cliente/portal.js` continuou como facade e orquestrador central:

- `state` principal do portal;
- `atualizarBadgesTabs()` como helper de shell cross-slice;
- `sincronizarSelecoes()` entre `chat` e `mesa`;
- helpers compartilhados `renderAnexos()` e `renderAvisosOperacionais()`;
- `renderCentralPrioridades()`;
- `renderEverything()` como orquestrador do shell;
- `bootstrapPortal()`;
- `bindTabs()`, `bindFiltros()` e `bindCommercialActions()`;
- `init()`.

O que permaneceu propositalmente fora do modulo de mesa:

- `renderAvisosOperacionais()` porque continua atendendo `chat` e `mesa`;
- `renderAnexos()` porque continua sendo usado nas timelines de `chat` e `mesa`;
- `bindCommercialActions()` porque ainda orquestra prioridades, filtros rapidos e fluxos cross-slice (`admin`, `chat`, `mesa`);
- a logica de shell (`renderEverything()`, badges de aba, bootstrap e selecao cruzada).

## Ordem de carregamento apos a fase

Template:

- `web/templates/cliente_portal.html`

Ordem consolidada:

1. `/static/js/shared/api-core.js?v={{ v_app }}` quando `perf_mode`
2. `/static/js/cliente/portal_runtime.js?v={{ v_app }}`
3. `/static/js/cliente/portal_priorities.js?v={{ v_app }}`
4. `/static/js/cliente/portal_admin.js?v={{ v_app }}`
5. `/static/js/cliente/portal_chat.js?v={{ v_app }}`
6. `/static/js/cliente/portal_mesa.js?v={{ v_app }}`
7. `/static/js/cliente/portal.js?v={{ v_app }}`

Dependencias confirmadas:

- `portal_mesa.js` depende das bridges internas de runtime e prioridades;
- `portal.js` continua sendo o entrypoint final e consome os metodos expostos por `portal_mesa.js`;
- a ordem manual segue obrigatoria enquanto nao houver pipeline modular nativo.

## Reducao observada no facade

Tamanho observado nesta fase:

- `portal.js` passou de `1156` para `668` linhas
- `portal_mesa.js` entrou com `628` linhas

Leitura:

- o facade perdeu cerca de `488` linhas adicionais;
- o codigo remanescente agora representa majoritariamente shell, bootstrap e roteamento cross-slice;
- a mesa ganhou ownership claro sem reabrir contratos do backend.

## Dependencias e globals que ainda existem

Globais/bridges internas ativas:

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__`
- `window.TarielClientePortalRuntime`
- `window.TarielClientePortalPriorities`
- `window.TarielClientePortalAdmin`
- `window.TarielClientePortalChat`
- `window.TarielClientePortalMesa`

Dependencias internas ainda relevantes:

- `portal_mesa.js` recebe `state` compartilhado do facade;
- o modulo da mesa ainda chama `bootstrapPortal()` do facade depois de mutacoes;
- o modulo da mesa usa `atualizarBadgesTabs()` do facade quando marca whispers lidos localmente;
- `portal_mesa.js` ainda depende de `renderAnexos()` do facade para nao duplicar a renderizacao compartilhada com `chat`.

## Helpers compartilhados mantidos de proposito

Decisao desta fase:

- `renderAvisosOperacionais()` ficou no facade;
- `renderAnexos()` ficou no facade;
- `bindCommercialActions()` ficou no facade.

Motivo:

- os tres ainda atravessam mais de um slice;
- extrair qualquer um deles agora introduziria uma quebra artificial de ownership;
- a fase 2.4 tinha melhor custo-beneficio concentrando apenas o que era inequivocamente `mesa`.

## Riscos que ainda restam antes de mexer no facade final

- `portal.js` ainda concentra o roteador cross-slice em `bindCommercialActions()`;
- `bootstrapPortal()` e `renderEverything()` ainda reidratam o shell inteiro;
- a ordem `runtime -> priorities -> admin -> chat -> mesa -> portal` continua sendo um requisito manual do template;
- `window.TarielClientePortalMesa` ainda e uma bridge interna temporaria, nao contrato publico;
- `renderAvisosOperacionais()` e `renderAnexos()` seguem compartilhados, entao a proxima fase precisa decidir se ficam no facade final ou se viram um helper compartilhado interno.

## O que esta explicitamente fora desta fase

- alteracao de endpoints, payloads ou contratos da mesa;
- mudanca em pendencias, pacote, aprovacoes ou protocolo operacional;
- troca de pipeline de assets;
- reescrita do portal cliente como SPA ou ES modules;
- remocao das bridges em `window`.
