# Fase 2.2 - Extracao controlada do slice admin do portal cliente

## Objetivo

Continuar a modularizacao interna do portal cliente sem alterar:

- backend;
- endpoints;
- payloads;
- regras de negocio;
- contratos do produto;
- UX do portal cliente.

Nesta fase, o corte escolhido foi apenas o slice `admin`, que era o bloco menos arriscado entre os renders restantes do monolito.

## O que era o slice admin antes da fase

Antes desta fase, `web/static/js/cliente/portal.js` ainda concentrava tres grupos grandes do admin:

- render de cards, saude, onboarding, auditoria, usuarios e preview de plano;
- handlers administrativos de plano e cadastro de usuarios;
- helpers de foco/filtro da tabela de usuarios e do fluxo guiado de upgrade.

Blocos que estavam no facade antes da extracao:

- `renderEmpresaCards()`
- `renderAdminResumo()`
- `renderSaudeEmpresa()`
- `renderOnboardingEquipe()`
- `renderAdminAuditoria()`
- `renderHistoricoPlanos()`
- `renderPreviewPlano()`
- `aplicarFiltrosUsuarios()`
- `focarUsuarioNaTabela()`
- `renderUsuarios()`
- `renderAdmin()`
- `registrarInteressePlano()`
- `prepararUpgradeGuiado()`
- `bindAdminActions()`

Leitura arquitetural:

- esse conjunto misturava render, manipulação de DOM, fetch e fluxos administrativos;
- o slice admin era coeso o suficiente para sair junto;
- chat e mesa continuavam mais sensiveis por dependerem de loaders, timeline e estado conversacional.

## O que foi extraido

Novo modulo:

- `web/static/js/cliente/portal_admin.js`

Namespace interno criado:

- `window.TarielClientePortalAdmin`

Responsabilidades movidas para o modulo:

- render do resumo admin;
- render dos cards da empresa;
- render de saude operacional;
- render de onboarding;
- render de auditoria;
- render do historico de planos;
- render do preview de plano;
- render da tabela de usuarios;
- bind das acoes administrativas (`form-plano`, `form-usuario`, reset/bloqueio/salvar usuario);
- fluxo de interesse em plano;
- fluxo guiado de upgrade;
- filtros e foco da tabela de usuarios.

## O que continuou em `portal.js`

`web/static/js/cliente/portal.js` continuou como facade e orquestrador central:

- `state` principal do portal;
- sincronizacao de selecoes e boot;
- renders e acoes de `chat` e `mesa`;
- `renderCentralPrioridades()`;
- `renderAvisosOperacionais()` e `renderChatCapacidade()`;
- `bootstrapPortal()`, `loadChat()`, `loadMesa()`;
- `bindTabs()`, `bindFiltros()`, `bindCommercialActions()`, `bindChatActions()`, `bindMesaActions()`;
- `init()`.

Leitura pratica:

- o admin saiu como modulo coeso;
- o facade continua controlando a navegacao e os fluxos cross-slice;
- chat e mesa nao foram tocados alem do minimo necessario para consumir o novo modulo.

## Ordem de carregamento apos a fase

Template:

- `web/templates/cliente_portal.html`

Ordem consolidada:

1. `/static/js/shared/api-core.js?v={{ v_app }}` quando `perf_mode`
2. `/static/js/cliente/portal_runtime.js?v={{ v_app }}`
3. `/static/js/cliente/portal_priorities.js?v={{ v_app }}`
4. `/static/js/cliente/portal_admin.js?v={{ v_app }}`
5. `/static/js/cliente/portal.js?v={{ v_app }}`

Dependencias confirmadas:

- `portal_admin.js` depende das bridges internas e helpers ja estabilizados em `portal_runtime.js` e `portal_priorities.js`;
- `portal.js` continua sendo o unico entrypoint final e consome os metodos expostos por `portal_admin.js`.

## Reducao observada no facade

Tamanho observado nesta fase:

- `portal.js` passou de `2352` para `1655` linhas
- `portal_admin.js` entrou com `817` linhas

Leitura:

- o facade perdeu cerca de `697` linhas adicionais;
- o codigo que restou em `portal.js` agora representa muito mais claramente o shell cross-slice e os slices `chat`/`mesa`.

## Dependencias e globals que ainda existem

Globais/bridges internas ativas:

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__`
- `window.TarielClientePortalRuntime`
- `window.TarielClientePortalPriorities`
- `window.TarielClientePortalAdmin`

Dependencias internas ainda relevantes:

- `portal_admin.js` recebe `state` compartilhado do facade;
- o modulo admin ainda chama `bootstrapPortal()` do facade para refletir mutacoes de plano e usuarios;
- `bindCommercialActions()` continua em `portal.js`, mas delega o que e admin para helpers do modulo;
- `renderEverything()` continua sendo um rerender total do shell.

## Riscos que ainda restam antes de mexer em chat/mesa

- `bindCommercialActions()` ainda mistura roteamento de acoes admin, chat e mesa na mesma funcao;
- `bootstrapPortal()` continua reidratando o shell inteiro apos mutacoes administrativas;
- os slices `chat` e `mesa` permanecem no facade e ainda concentram boa parte do risco funcional restante;
- os namespaces em `window` continuam sendo bridges internas temporarias, e a ordem de scripts segue manual.

## O que esta explicitamente fora desta fase

- extracao de `chat`;
- extracao de `mesa`;
- alteracao de endpoints ou payloads;
- troca de pipeline de assets;
- reescrita do portal cliente como SPA ou ES modules.
