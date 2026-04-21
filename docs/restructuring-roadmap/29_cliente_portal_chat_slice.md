# Fase 2.3 - Extracao controlada do slice chat do portal cliente

## Objetivo

Continuar a modularizacao interna do portal cliente sem alterar:

- backend;
- endpoints;
- payloads;
- regras de negocio;
- contratos do produto;
- UX do portal cliente.

Nesta fase, o corte escolhido foi apenas o slice `chat`, que passou a ser o maior bloco coeso restante em `web/static/js/cliente/portal.js` depois da extracao do runtime, das prioridades e do admin.

## O que era o slice chat antes da fase

Antes desta fase, `web/static/js/cliente/portal.js` ainda concentrava o ciclo quase completo do canal de chat:

- render do resumo, triagem, movimentos, lista, contexto e timeline;
- estado local de documento pendente e do laudo selecionado;
- loader de mensagens do laudo (`loadChat()`);
- handlers de criacao de laudo, importacao de documento, envio de mensagem, finalizacao e reabertura;
- filtros rapidos e busca da fila do chat.

Blocos que estavam no facade antes da extracao:

- `documentoChatPendenteAtivo()`
- `limparDocumentoChatPendente()`
- `renderChatDocumentoPendente()`
- `importarDocumentoChat()`
- `renderChatCapacidade()`
- `renderChatResumo()`
- `renderChatTriagem()`
- `renderChatMovimentos()`
- `renderChatList()`
- `renderChatContext()`
- `renderChatMensagens()`
- `loadChat()`
- `bindChatActions()`

Leitura arquitetural:

- o slice `chat` misturava render, fetch, DOM e handlers de submit no mesmo facade;
- as dependencias mais delicadas ainda eram `renderAvisosOperacionais()` e `renderAnexos()`, que continuam compartilhadas com `mesa`;
- por isso, a extracao segura ficou concentrada no que era claramente `chat`, sem reabrir ainda o contrato operacional da mesa.

## O que foi extraido

Novo modulo:

- `web/static/js/cliente/portal_chat.js`

Namespace interno criado:

- `window.TarielClientePortalChat`

Responsabilidades movidas para o modulo:

- render do resumo do chat;
- render da triagem do chat;
- render dos movimentos recentes do chat;
- render da lista de laudos do chat;
- render do contexto do laudo selecionado;
- render da timeline de mensagens do chat;
- render e limpeza do documento pendente;
- importacao de PDF/DOCX para rascunho do chat;
- loader `loadChat()` do laudo selecionado;
- bind das acoes do chat;
- atualizacao da busca do chat;
- filtros rapidos do chat.

Leitura pratica:

- o modulo novo concentra a area conversacional do portal cliente;
- o facade deixou de ser dono direto do lifecycle do chat;
- a integracao continua via `state` compartilhado e callbacks do facade.

## O que continuou em `portal.js`

`web/static/js/cliente/portal.js` continuou como facade e orquestrador central:

- `state` principal do portal;
- sincronizacao de selecoes entre `chat` e `mesa`;
- helpers compartilhados (`renderAnexos()`, `renderAvisosOperacionais()`);
- `renderCentralPrioridades()`;
- `renderEverything()` como orquestrador do shell;
- `bootstrapPortal()`;
- `loadMesa()` e todo o slice `mesa`;
- `bindTabs()`, `bindFiltros()`, `bindCommercialActions()`, `bindMesaActions()`;
- `init()`.

O que permaneceu propositalmente fora do modulo de chat:

- `renderAvisosOperacionais()` porque continua atendendo `chat` e `mesa`;
- `renderAnexos()` porque continua sendo usado na timeline do chat e da mesa;
- o roteador `bindCommercialActions()` porque ainda orquestra fluxos cross-slice (`admin`, `chat`, `mesa`);
- todo o slice `mesa`, que continua sendo a proxima fronteira sensivel.

## Ordem de carregamento apos a fase

Template:

- `web/templates/cliente_portal.html`

Ordem consolidada:

1. `/static/js/shared/api-core.js?v={{ v_app }}` quando `perf_mode`
2. `/static/js/cliente/portal_runtime.js?v={{ v_app }}`
3. `/static/js/cliente/portal_priorities.js?v={{ v_app }}`
4. `/static/js/cliente/portal_admin.js?v={{ v_app }}`
5. `/static/js/cliente/portal_chat.js?v={{ v_app }}`
6. `/static/js/cliente/portal.js?v={{ v_app }}`

Dependencias confirmadas:

- `portal_chat.js` depende das bridges internas de runtime e prioridades;
- `portal.js` continua sendo o entrypoint final e consome os metodos expostos por `portal_chat.js`;
- a ordem manual segue obrigatoria enquanto nao houver pipeline modular nativo.

## Reducao observada no facade

Tamanho observado nesta fase:

- `portal.js` passou de `1655` para `1156` linhas
- `portal_chat.js` entrou com `645` linhas

Leitura:

- o facade perdeu cerca de `499` linhas adicionais;
- o codigo remanescente agora evidencia melhor a fronteira entre shell/orquestracao e os slices `chat` e `mesa`;
- `portal.js` ficou mais proximo de um facade real e menos de um controlador monolitico.

## Dependencias e globals que ainda existem

Globais/bridges internas ativas:

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__`
- `window.TarielClientePortalRuntime`
- `window.TarielClientePortalPriorities`
- `window.TarielClientePortalAdmin`
- `window.TarielClientePortalChat`

Dependencias internas ainda relevantes:

- `portal_chat.js` recebe `state` compartilhado do facade;
- o modulo de chat ainda chama `bootstrapPortal()` do facade depois de mutacoes;
- `portal.js` ainda roteia acoes de prioridade e filtros rapidos entre slices;
- `portal_chat.js` ainda depende de `renderAnexos()` do facade para nao duplicar a renderizacao compartilhada com `mesa`.

## Riscos que ainda restam antes de mexer em mesa

- `portal.js` ainda concentra todo o slice `mesa`, inclusive loader, timeline e handlers;
- `bindCommercialActions()` continua sendo um roteador central com conhecimento dos tres slices;
- a ordem `runtime -> priorities -> admin -> chat -> portal` continua sendo um requisito manual do template;
- `window.TarielClientePortalChat` ainda e uma bridge interna temporaria, nao contrato publico;
- `renderAvisosOperacionais()` e `renderAnexos()` continuam acoplados a `chat` e `mesa`, entao uma extracao de `mesa` vai precisar decidir se esses helpers continuam no facade ou se viram um modulo compartilhado interno.

## O que esta explicitamente fora desta fase

- extracao de `mesa`;
- alteracao de endpoints, payloads ou contratos do chat;
- mudanca em SSE, websocket ou protocolo do canal;
- troca de pipeline de assets;
- reescrita do portal cliente como SPA ou ES modules.
