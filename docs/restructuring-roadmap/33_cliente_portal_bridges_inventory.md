# Fase 2.6 - Inventario canonico das bridges do portal cliente

## Objetivo

Congelar o mapa atual das bridges `window.*` usadas pelo portal cliente depois da modularizacao das fases 2.1 a 2.6.

Este documento nao muda comportamento. Ele registra:

- quais bridges existem;
- para que servem;
- quais sao necessarias no boot atual;
- quais sao temporarias;
- quais dependem de ordem;
- quais sao candidatas a remocao futura.

## Resumo executivo

Estado confirmado no codigo:

- nao foi encontrado consumidor externo dessas bridges fora do bundle do proprio portal cliente, alem do smoke e da documentacao;
- isso indica que elas continuam sendo compatibilidade interna do entrypoint, nao contrato publico de produto;
- todas as bridges modulares do portal cliente ainda dependem de ordem explicita de `<script>` no template;
- o facade agora concentra um contrato explicito de boot em `PORTAL_BOOT_CONTRACT` e preserva `PORTAL_BRIDGE_SPECS` como recorte canonico das bridges obrigatorias.

## Inventario canonico

| Bridge | Origem | Funcao atual | Necessaria no boot atual | Compatibilidade temporaria | Candidata a remocao futura | Dependente de ordem | Leitura |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `window.__TARIEL_CLIENTE_PORTAL_WIRED__` | `portal.js` | guard estruturado e estado diagnostico do boot | sim | nao | nao | nao | continua nao sendo bridge modular de feature, mas agora preserva status `booting/ready/failed` e trilha de diagnostico |
| `window.TarielPerf` | `shared/api-core.js` quando `perf_mode` | instrumentacao opcional de performance | nao | sim | nao | sim | o portal funciona sem ela; quando presente, precisa carregar antes dos consumidores |
| `window.TarielClientePortalRuntime` | `portal_runtime.js` | runtime local, helpers de fetch, tab, feedback e persistencia | sim | sim | sim | sim | continua sendo bridge interna enquanto nao houver pipeline modular nativo |
| `window.TarielClientePortalPriorities` | `portal_priorities.js` | prioridades, badges, filtros e helpers semanticos | sim | sim | sim | sim | bridge interna de bootstrap para o facade |
| `window.TarielClientePortalAdmin` | `portal_admin.js` | slice `admin` | sim | sim | sim | sim | modulo interno do portal, nao contrato publico |
| `window.TarielClientePortalChat` | `portal_chat.js` | slice `chat` | sim | sim | sim | sim | bridge interna dependente do facade |
| `window.TarielClientePortalMesa` | `portal_mesa.js` | slice `mesa` | sim | sim | sim | sim | bridge interna dependente do facade |
| `window.TarielClientePortalSharedHelpers` | `portal_shared_helpers.js` | helpers compartilhados de anexos e avisos operacionais | sim | sim | sim | sim | bridge interna de suporte aos slices e ao shell |
| `window.TarielClientePortalShell` | `portal_shell.js` | shell, bootstrap e reidratacao do portal | sim | sim | sim | sim | bridge interna do boot atual |
| `window.TarielClientePortalBindings` | `portal_bindings.js` | tabs, filtros e roteador cross-slice | sim | sim | sim | sim | nova bridge interna da fase 2.6 para explicitar o roteador compartilhado |

## Ordem de scripts que sustenta as bridges

Contrato confirmado em `web/templates/cliente_portal.html`:

1. `shared/api-core.js` quando `perf_mode`
2. `portal_runtime.js`
3. `portal_priorities.js`
4. `portal_admin.js`
5. `portal_chat.js`
6. `portal_mesa.js`
7. `portal_shared_helpers.js`
8. `portal_shell.js`
9. `portal_bindings.js`
10. `portal.js`

Leitura:

- `portal.js` depende de todas as bridges funcionais acima ja registradas em `window`;
- `window.TarielPerf` continua opcional;
- o contrato de ordem segue manual, mas agora esta duplicado de forma canonica em template, smoke e documentacao.

## Classificacao pratica

### Necessarias no boot atual

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__`
- `window.TarielClientePortalRuntime`
- `window.TarielClientePortalPriorities`
- `window.TarielClientePortalAdmin`
- `window.TarielClientePortalChat`
- `window.TarielClientePortalMesa`
- `window.TarielClientePortalSharedHelpers`
- `window.TarielClientePortalShell`
- `window.TarielClientePortalBindings`

### Compatibilidade temporaria

- `window.TarielPerf`
- todos os namespaces `window.TarielClientePortal*`

Motivo:

- existem para sustentar o boot modular sem bundler nem `import`;
- nao foram encontrados consumidores externos que justifiquem trata-los como API publica.

### Candidatas a remocao futura

- `window.TarielClientePortalRuntime`
- `window.TarielClientePortalPriorities`
- `window.TarielClientePortalAdmin`
- `window.TarielClientePortalChat`
- `window.TarielClientePortalMesa`
- `window.TarielClientePortalSharedHelpers`
- `window.TarielClientePortalShell`
- `window.TarielClientePortalBindings`

Condicao para remocao:

- so quando existir um pipeline de assets capaz de substituir a dependencia de ordem por imports explicitos ou bundling controlado.

### Dependentes de ordem

- `window.TarielPerf` quando `perf_mode`
- todos os namespaces `window.TarielClientePortal*`

Nao dependente de ordem:

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__`, porque continua sendo apenas o estado do proprio entrypoint ja carregado.

## O que o facade faz com esse inventario agora

`web/static/js/cliente/portal.js` passou a manter um contrato explicito em `PORTAL_BOOT_CONTRACT`, com `PORTAL_BRIDGE_SPECS` como subconjunto canonico das bridges obrigatorias, o que traz dois ganhos:

- o boot deixa explicito quais bridges sao exigidas para o portal funcionar;
- o contrato de compatibilidade temporaria deixa de ser um conjunto implicito de lookups espalhados.

Leitura:

- o facade nao remove as bridges;
- ele apenas passa a tratá-las como contrato interno mapeado e documentado.

## Riscos remanescentes

- a existencia do inventario nao elimina o risco de ordem manual entre scripts;
- as bridges continuam expostas em `window`, entao bugs de inicializacao ainda podem surgir se a ordem do template for quebrada;
- o proximo nivel de limpeza exigiria decisao estrutural de pipeline de frontend, nao apenas rearranjo interno do portal cliente.
