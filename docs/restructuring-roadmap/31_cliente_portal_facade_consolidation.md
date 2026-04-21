# Fase 2.5 - Consolidacao final do facade e dos helpers compartilhados do portal cliente

## Objetivo

Consolidar `web/static/js/cliente/portal.js` como um facade intencional e fino, sem alterar:

- backend;
- endpoints;
- payloads;
- regras de negocio;
- contratos do produto;
- UX do portal cliente.

Depois das fases 2.1 a 2.4, o maior hotspot remanescente deixou de ser um slice funcional isolado e passou a ser o proprio facade. O corte desta fase separa, com baixo risco, o que era shell/bootstrap e o que era helper compartilhado.

## O que restava no facade antes da fase

Antes desta fase, `web/static/js/cliente/portal.js` ainda acumulava quatro grupos de responsabilidade:

- shell do portal e badges das abas;
- sincronizacao de selecao entre `chat` e `mesa`;
- render compartilhado de anexos e avisos operacionais;
- bootstrap completo e reidratacao do shell inteiro.

Blocos remanescentes no facade antes do corte:

- `atualizarBadgesTabs()`
- `sincronizarSelecoes()`
- `renderAnexos()`
- `renderAvisosOperacionais()`
- `renderCentralPrioridades()`
- `renderEverything()`
- `bootstrapPortal()`
- `bindTabs()`
- `bindFiltros()`
- `bindCommercialActions()`
- `init()`

Leitura arquitetural:

- `portal.js` ja nao era mais dono de `admin`, `chat` ou `mesa`, mas ainda era o dono direto do shell inteiro;
- os helpers compartilhados estavam misturados com bootstrap e com o roteador cross-slice;
- o facade ainda parecia "o resto que sobrou", nao um modulo explicitamente intencional.

## O corte escolhido

O corte de menor risco foi separar duas responsabilidades claras:

- helpers compartilhados de `chat` e `mesa`;
- shell/bootstrap do portal cliente.

Novos modulos internos criados:

- `web/static/js/cliente/portal_shared_helpers.js`
- `web/static/js/cliente/portal_shell.js`

Namespaces internos criados:

- `window.TarielClientePortalSharedHelpers`
- `window.TarielClientePortalShell`

Motivo do corte:

- `renderAnexos()` e `renderAvisosOperacionais()` ja eram explicitamente compartilhados entre slices;
- `atualizarBadgesTabs()`, `sincronizarSelecoes()`, `renderCentralPrioridades()`, `renderEverything()` e `bootstrapPortal()` ja formavam um bloco coeso de shell/orquestracao;
- `bindCommercialActions()` continuava sendo o ponto realmente cross-slice e, por isso, nao deveria sair de `portal.js` nesta fase.

## O que foi movido

### `portal_shared_helpers.js`

Responsabilidades movidas:

- `renderAnexos()`
- `renderAvisosOperacionais()`

Leitura pratica:

- o render compartilhado de timeline e avisos saiu do facade;
- `chat` e `mesa` continuam consumindo os mesmos helpers, agora por um modulo interno explicito;
- o comportamento visual e os gatilhos existentes foram preservados.

### `portal_shell.js`

Responsabilidades movidas:

- `atualizarBadgesTabs()`
- `sincronizarSelecoes()`
- `renderCentralPrioridades()`
- `renderEverything()`
- `bootstrapPortal()`

Leitura pratica:

- o shell do portal agora tem ownership proprio;
- o facade deixou de conter a reidratacao completa do portal;
- `portal_shell.js` continua operando sobre o mesmo `state` compartilhado, com callbacks e helpers injetados pelo facade.

## O que permaneceu em `portal.js`

`web/static/js/cliente/portal.js` permaneceu como entrypoint e facade final:

- declaracao do `state` compartilhado;
- lookup das bridges internas em `window`;
- injecao de dependencias entre `runtime`, `priorities`, `admin`, `chat`, `mesa`, `shared_helpers` e `shell`;
- `bindTabs()`;
- `bindFiltros()`;
- `bindCommercialActions()`;
- `init()`.

Decisao intencional:

- `portal.js` agora ficou responsavel apenas por bootstrap do entrypoint, wiring entre modulos e roteamento cross-slice que ainda nao tem ownership isolado;
- o facade deixou de carregar render de shell e helpers de UI que nao precisam estar no entrypoint.

## Helpers compartilhados avaliados nesta fase

### `renderAvisosOperacionais()`

Decisao:

- movido para `portal_shared_helpers.js`.

Motivo:

- atende `chat` e `mesa`;
- nao depende do roteamento cross-slice;
- o contrato local e simples e estava estavel o bastante para extracao.

### `renderAnexos()`

Decisao:

- movido para `portal_shared_helpers.js`.

Motivo:

- e um helper puro de render;
- atende mais de um slice;
- sair do facade reduz acoplamento sem reabrir nenhuma regra de negocio.

### `bindCommercialActions()`

Decisao:

- permaneceu em `portal.js`.

Motivo:

- ainda orquestra prioridades, filtros rapidos e navegacao que atravessa `admin`, `chat` e `mesa`;
- extrair esse roteador agora criaria uma camada artificial sem reduzir risco real;
- depois da saida de shell e helpers, ele virou o principal hotspot remanescente e deve ser tratado como fase propria.

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
7. `/static/js/cliente/portal_shared_helpers.js?v={{ v_app }}`
8. `/static/js/cliente/portal_shell.js?v={{ v_app }}`
9. `/static/js/cliente/portal.js?v={{ v_app }}`

Dependencias confirmadas:

- `portal.js` continua sendo o entrypoint final;
- `portal_shell.js` depende dos slices ja registrados em `window`;
- `portal_shared_helpers.js` precisa estar carregado antes do facade para ser injetado em `chat`, `mesa` e `shell`;
- a ordem manual segue obrigatoria enquanto o projeto nao migrar para um pipeline modular nativo.

## Reducao observada no facade

Tamanho observado nesta fase:

- `portal.js` passou de `668` para `560` linhas
- `portal_shared_helpers.js` entrou com `77` linhas
- `portal_shell.js` entrou com `186` linhas

Leitura:

- o facade perdeu mais `108` linhas liquidas;
- o que ficou em `portal.js` agora e majoritariamente wiring, binds e bootstrap do entrypoint;
- a consolidacao reduziu mistura entre shell, helpers compartilhados e orquestracao central.

## Bridges e globals que ainda existem

Globais/bridges internas ativas:

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__`
- `window.TarielClientePortalRuntime`
- `window.TarielClientePortalPriorities`
- `window.TarielClientePortalAdmin`
- `window.TarielClientePortalChat`
- `window.TarielClientePortalMesa`
- `window.TarielClientePortalSharedHelpers`
- `window.TarielClientePortalShell`

Leitura:

- as bridges continuam internas e temporarias;
- a fase 2.5 nao removeu bridges sem prova de seguranca;
- o ownership de cada bridge agora esta mais explicito por modulo.

## O que torna o facade intencional agora

Depois desta fase, `portal.js` deixou de ser um deposito residual e passou a representar claramente:

- o entrypoint do portal cliente;
- o wiring entre modulos internos;
- o registro e uso das bridges temporarias;
- o roteamento cross-slice que ainda precisa permanecer centralizado.

Em outras palavras:

- render compartilhado saiu do facade;
- shell/bootstrap saiu do facade;
- o que restou em `portal.js` e deliberadamente o que ainda precisa ser central.

## Riscos que ainda restam

- `bindCommercialActions()` continua sendo um roteador cross-slice central e merece uma fase propria;
- a ordem `runtime -> priorities -> admin -> chat -> mesa -> shared_helpers -> shell -> portal` continua sendo um contrato manual do template;
- as bridges `window.*` continuam temporarias e dependentes de ordem;
- `bindTabs()` e `bindFiltros()` seguem no facade porque ainda operam sobre mais de um modulo via `state` compartilhado.

## O que esta explicitamente fora desta fase

- alteracao de endpoints, payloads ou contratos do portal cliente;
- remocao de bridges em `window` sem prova clara;
- reescrita do portal como SPA ou migracao para ES modules;
- mudanca de UX, layout ou fluxo operacional do cliente;
- reestruturacao do roteador cross-slice alem do necessario para preservar o comportamento atual.
