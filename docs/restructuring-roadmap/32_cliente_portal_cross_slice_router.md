# Fase 2.6 - Racionalizacao final do roteador cross-slice do portal cliente

## Objetivo

Fechar a modularizacao do portal cliente tornando explicito o que ainda restava como roteador e bindings compartilhados em `web/static/js/cliente/portal.js`, sem alterar:

- backend;
- endpoints;
- payloads;
- contratos do produto;
- regras de negocio;
- UX do portal cliente.

Depois das fases 2.1 a 2.5, o facade ja nao era mais dono de `admin`, `chat`, `mesa`, shell ou helpers compartilhados. O hotspot remanescente era a camada de eventos e roteamento cross-slice.

## O que era o roteador cross-slice antes da fase

Antes desta fase, `web/static/js/cliente/portal.js` ainda concentrava tres grupos de binding:

- `bindTabs()` para navegar entre as abas do shell;
- `bindFiltros()` para conectar busca/filtros de `admin`, `chat` e `mesa`;
- `bindCommercialActions()` para roteamento por `data-act` entre os tres slices.

Leitura arquitetural:

- o facade ainda acumulava wiring de UI junto da costura dos modulos;
- `bindCommercialActions()` era o ultimo ponto onde prioridades, filtros rapidos, upgrade e navegacao entre laudos conviviam no mesmo bloco;
- o roteador era funcionalmente pequeno, mas implicito e misturado com o entrypoint.

## O corte escolhido

O corte de menor risco foi extrair os bindings compartilhados para um modulo proprio:

- `web/static/js/cliente/portal_bindings.js`

Namespace interno criado:

- `window.TarielClientePortalBindings`

Motivo:

- `bindTabs()`, `bindFiltros()` e `bindCommercialActions()` ja compartilhavam o mesmo perfil: eram wiring de UI e roteamento cross-slice, nao render nem logica de negocio de um slice especifico;
- o facade podia passar a apenas montar dependencias e iniciar o boot;
- o contrato funcional existente foi preservado porque o modulo novo trabalha sobre o mesmo `state`, os mesmos callbacks e os mesmos helpers injetados pelo facade.

## O que foi reorganizado

Responsabilidades movidas para `portal_bindings.js`:

- bind das abas principais;
- bind dos inputs de filtro/busca compartilhados;
- roteamento por `data-act` para acoes cross-slice;
- definicao explicita do dispatcher de acoes compartilhadas.

Leitura pratica:

- o roteador cross-slice deixou de ser um bloco implicito no facade;
- `bindCommercialActions()` continua existindo como nome de compatibilidade interna, mas agora e um alias de um roteador explicito: `bindCrossSliceRouter()`;
- o modulo novo separa o dispatcher das funcoes handler, deixando visivel o ownership de cada acao sem alterar o comportamento do portal.

## Acoes cross-slice consolidadas no roteador

O dispatcher compartilhado continua sendo responsavel por:

- `abrir-prioridade`
- `filtrar-usuarios-status`
- `limpar-filtro-usuarios`
- `filtrar-chat-status`
- `limpar-chat-filtro`
- `filtrar-mesa-status`
- `limpar-mesa-filtro`
- `preparar-upgrade`
- `registrar-interesse-plano`

Leitura:

- essas acoes continuam sendo cross-slice porque combinam navegacao, shell, filtros rapidos e transicao entre contextos;
- elas nao foram empurradas artificialmente para `admin`, `chat` ou `mesa`, porque isso aumentaria acoplamento lateral em vez de reduzi-lo.

## O que permaneceu no facade

`web/static/js/cliente/portal.js` permaneceu responsavel por:

- `state` compartilhado do portal cliente;
- inventario canonico das bridges de boot em `PORTAL_BRIDGE_SPECS`;
- lookup das bridges internas em `window`;
- injecao de dependencias entre os modulos internos;
- `init()`;
- guard `window.__TARIEL_CLIENTE_PORTAL_WIRED__`.

Leitura:

- o facade deixou de registrar handlers de UI diretamente;
- o que ficou em `portal.js` agora e deliberadamente bootstrap final e costura entre modulos;
- isso fecha a modularizacao do portal cliente com um ownership mais nitido.

## Bindings compartilhados que ainda restam

Mesmo apos a extracao, alguns bindings continuam pertencendo ao nucleo e nao a um slice isolado:

- tabs do shell, porque alternam paineis que pertencem a `admin`, `chat` e `mesa`;
- filtros de topo, porque escrevem em `state.ui` compartilhado;
- dispatcher de `data-act`, porque continua sendo a fronteira entre prioridades, filtros e navegacao entre slices.

Decisao desta fase:

- deixar esses bindings em um modulo proprio foi mais seguro do que espalha-los artificialmente;
- o proximo nivel de reducao de acoplamento, se necessario, ja nao e extracao por slice e sim contrato de entrypoint/boot.

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
9. `/static/js/cliente/portal_bindings.js?v={{ v_app }}`
10. `/static/js/cliente/portal.js?v={{ v_app }}`

Dependencias confirmadas:

- `portal.js` continua sendo o unico entrypoint final do template;
- `portal_bindings.js` e uma dependencia interna do facade;
- a ordem manual continua obrigatoria e agora esta validada pelo smoke e documentada no template.

## Reducao observada no facade

Tamanho observado nesta fase:

- `portal.js` passou de `560` para `463` linhas
- `portal_bindings.js` entrou com `213` linhas

Leitura:

- o facade perdeu mais `97` linhas liquidas;
- o que restou em `portal.js` e quase exclusivamente state, bridges, wiring e boot;
- a superficie cross-slice ficou mais previsivel sem alterar contratos funcionais.

## Riscos que ainda restam

- o roteador compartilhado continua centralizado, apenas agora com ownership explicito;
- a ordem de scripts continua manual e dependente de template;
- as bridges `window.*` continuam temporarias e dependentes de ordem;
- `portal.js` ainda precisa conhecer todos os modulos internos para montar o boot final.

## O que esta explicitamente fora desta fase

- remocao das bridges internas em `window`;
- mudanca de endpoints, payloads ou contratos do portal cliente;
- migracao para ES modules, bundler ou carregamento automatico de assets;
- reescrita do portal cliente como SPA.
