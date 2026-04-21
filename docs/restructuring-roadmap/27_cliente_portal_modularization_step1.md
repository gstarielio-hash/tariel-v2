# Fase 2.1 - Modularizacao controlada do portal cliente, passo 1

## Objetivo

Executar a primeira extracao interna segura de `web/static/js/cliente/portal.js`, mantendo:

- `portal.js` como facade e entrypoint;
- o mesmo boot externo do portal cliente;
- os mesmos endpoints, payloads e fluxos de negocio;
- o mesmo comportamento visual e operacional.

## O que foi extraido

## 1. Runtime local e infraestrutura do entrypoint

Novo arquivo:

- `web/static/js/cliente/portal_runtime.js`

Responsabilidades movidas:

- `perfSync`, `perfAsync`, `perfSnapshot`;
- `api`, `withBusy`, `feedback`;
- `escapeHtml`, `escapeAttr`, `texto`, `textoComQuebras`;
- `formatarInteiro`, `formatarPercentual`, `formatarCapacidadeRestante`, `formatarLimitePlano`, `formatarVariacao`, `formatarBytes`;
- `persistirTab`, `persistirSelecao`, `lerNumeroPersistido`, `restaurarTab`;
- `definirTab`;
- `scrollToPortalSection`.

Namespace interno exposto:

- `window.TarielClientePortalRuntime`

## 2. Estado derivado, prioridades, badges e filtros

Novo arquivo:

- `web/static/js/cliente/portal_priorities.js`

Responsabilidades movidas:

- `construirPrioridadesPortal`;
- `tomCapacidadeEmpresa`, `obterPlanoCatalogo`, `resumoCanalOperacional`;
- `slugPapel`, `obterNomePapel`;
- `variantStatusLaudo`, `prioridadeEmpresa`, `prioridadeUsuario`, `prioridadeChat`, `prioridadeMesa`;
- `laudoChatParado`, `laudoMesaParado`, `resumoEsperaHoras`;
- `roleBadge`, `userStatusBadges`, `laudoBadge`;
- `filtrarUsuarios`, `filtrarLaudosChat`, `filtrarLaudosMesa`;
- `htmlBarrasHistorico`.

Namespace interno exposto:

- `window.TarielClientePortalPriorities`

## O que continuou em `portal.js`

`web/static/js/cliente/portal.js` continua responsavel por:

- guardar o `state` principal do portal;
- sincronizar selecoes de laudo;
- carregar chat e mesa;
- montar os renders admin/chat/mesa;
- registrar todos os binds e fluxos de acao;
- executar `init()`;
- preservar o guard `window.__TARIEL_CLIENTE_PORTAL_WIRED__`.

Em outras palavras:

- `portal.js` deixou de ser o deposito de toda a infraestrutura e semantica derivada;
- mas continua sendo a fachada que orquestra boot, render e eventos.

## Template e ordem de carregamento apos o passo 1

Arquivo:

- `web/templates/cliente_portal.html`

Nova ordem:

1. `/static/js/shared/api-core.js?v={{ v_app }}` quando `perf_mode`
2. `/static/js/cliente/portal_runtime.js?v={{ v_app }}`
3. `/static/js/cliente/portal_priorities.js?v={{ v_app }}`
4. `/static/js/cliente/portal.js?v={{ v_app }}`

Leitura arquitetural:

- `portal.js` continua sendo o unico entrypoint funcional conhecido pelo template;
- os dois arquivos novos sao dependencias internas, carregadas antes do facade;
- a ordem ficou explicita e documentada, sem introduzir bundler ou `import`.

## Compatibilidade preservada

Compat layers e globais preservados:

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__`
- `window.TarielPerf`
- fluxo opcional com `/static/js/shared/api-core.js?v={{ v_app }}`

Novos globals internos desta fase:

- `window.TarielClientePortalRuntime`
- `window.TarielClientePortalPriorities`

Observacao importante:

- esses dois namespaces existem apenas como bridges internas desta etapa;
- nenhum contrato publico do produto passou a depender deles.

## Resultado estrutural do passo 1

Tamanho observado apos a extracao:

- `portal.js`: `2352` linhas
- `portal_runtime.js`: `297` linhas
- `portal_priorities.js`: `673` linhas

Leitura pratica:

- o entrypoint principal perdeu cerca de `728` linhas;
- o topo do arquivo ficou menos carregado;
- ownership interno agora esta mais claro entre:
  - facade/orquestracao;
  - runtime local;
  - derivacoes operacionais e filtros.

## O que nao mudou

- nenhuma rota backend;
- nenhum payload;
- nenhuma regra de negocio;
- nenhuma acao de admin, chat ou mesa;
- nenhum ID funcional do template;
- nenhum fluxo de login, sessao ou multiportal.

## Riscos remanescentes

- `portal.js` ainda segue grande porque continua dono dos renders e binds;
- a ordem de scripts do portal cliente agora precisa respeitar a cadeia `runtime -> priorities -> portal`;
- ainda nao existe isolamento por area funcional (`admin`, `chat`, `mesa`) no nivel de render e acoes;
- os namespaces `window.TarielClientePortalRuntime` e `window.TarielClientePortalPriorities` ainda sao bridges de compatibilidade, nao modulos nativos.

## Proximo corte seguro sugerido depois desta fase

Quando a Fase 2 continuar, o corte mais seguro seguinte passa a ser um destes:

- extracao de render-only adapters por area (`admin`, `chat`, `mesa`);
- extracao da camada de loaders/servicos do portal cliente;
- extracao dos binds por area funcional.

Nesta fase, isso ficou intencionalmente fora do escopo.
