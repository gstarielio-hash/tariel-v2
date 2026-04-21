# Fase 2.7 - Contrato de entrypoint do portal cliente

## Objetivo

Transformar o boot do portal cliente em um contrato explicito e endurecido, sem alterar:

- backend;
- endpoints;
- payloads;
- contratos do produto;
- regras de negocio;
- UX do portal cliente.

O foco desta fase nao foi nova extracao funcional. O foco foi reduzir o risco operacional de bootstrap parcial, falta de modulo e ordem incorreta de scripts.

## O que mudou no entrypoint

Arquivo principal:

- `web/static/js/cliente/portal.js`

Novo nucleo canonico de boot:

- `PORTAL_BOOT_CONTRACT`

Leitura:

- o facade continua sendo o entrypoint final;
- o boot agora declara, em um unico contrato, quais bridges/modulos sao obrigatorios;
- o contrato tambem registra ordem esperada de scripts e globals opcionais de compatibilidade.

## Estrutura do contrato

`PORTAL_BOOT_CONTRACT` passou a congelar:

- nome e versao do contrato de boot;
- seletor canonico dos scripts marcados no template;
- ordem esperada dos modulos internos;
- bridges obrigatorias para o boot atual;
- shape minima de exports de cada modulo;
- globals opcionais/contextuais.

Leitura pratica:

- antes, o portal apenas assumia que as bridges existiam;
- agora, o entrypoint valida tanto a existencia da factory quanto a API retornada por cada modulo;
- isso reduz risco de falha silenciosa quando um arquivo carrega incompleto ou regressa de forma parcial.

## Modulos obrigatorios para o boot atual

Bridges/modulos exigidos pelo contrato:

- `runtime` -> `window.TarielClientePortalRuntime`
- `priorities` -> `window.TarielClientePortalPriorities`
- `admin` -> `window.TarielClientePortalAdmin`
- `chat` -> `window.TarielClientePortalChat`
- `mesa` -> `window.TarielClientePortalMesa`
- `sharedHelpers` -> `window.TarielClientePortalSharedHelpers`
- `shell` -> `window.TarielClientePortalShell`
- `bindings` -> `window.TarielClientePortalBindings`

Entry final:

- `portal.js`

Leitura:

- todos os modulos acima continuam sendo obrigatorios no boot atual;
- a diferenca e que a falta deles agora gera falha explicita com mensagem legivel;
- alem da bridge, o facade valida a shape minima de exports de cada modulo antes de continuar.

## Modulos e globals opcionais/contextuais

Global contextual registrado no contrato:

- `window.TarielPerf`

Condicao:

- relevante apenas quando `meta[name="tariel-perf-mode"]` indica `1`.

Comportamento:

- se `TarielPerf` estiver ausente com `perf_mode` ativo, o boot nao para;
- o portal registra um aviso controlado uma unica vez e segue sem observabilidade opcional.

Leitura:

- a observabilidade continua sendo compat layer, nao pre-requisito funcional.

## Ordem de carregamento validada

Contrato canonico no template:

1. `portal_runtime.js`
2. `portal_priorities.js`
3. `portal_admin.js`
4. `portal_chat.js`
5. `portal_mesa.js`
6. `portal_shared_helpers.js`
7. `portal_shell.js`
8. `portal_bindings.js`
9. `portal.js`

Mecanismo usado:

- `data-portal-contract="cliente"`
- `data-portal-module="<nome>"` em cada script do bundle do portal cliente

Leitura:

- `portal.js` nao depende apenas do `src` do template;
- ele passa a inspecionar a ordem observada das tags marcadas;
- divergencia de ordem gera aviso controlado, registrado em estado de boot e no console uma unica vez.

## Estado do guard de boot

Global preservado:

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__`

O que ele virou nesta fase:

- deixou de ser apenas um booleano "ligado/desligado";
- passou a representar um estado estruturado de boot.

Estados relevantes:

- `booting`
- `ready`
- `failed`

Campos diagnosticos relevantes:

- `attempt`
- `startedAt`
- `finishedAt`
- `warnings`
- `errors`
- `missingRequired`
- `missingOptional`
- `scriptOrder`
- `modules`
- `contract`

Leitura:

- isso endurece o guard sem remover a global existente;
- o portal agora fica mais auditavel sem criar uma debug bar ruidosa;
- em caso de falha, o proprio guard preserva contexto suficiente para diagnostico.

## Falhas e avisos agora tratados de forma explicita

Falhas obrigatorias:

- bridge obrigatoria ausente;
- factory obrigatoria ausente;
- factory obrigatoria que falha ao inicializar;
- modulo que retorna API invalida;
- modulo que nao expõe exports obrigatorios;
- falha durante `init()`.

Avisos controlados:

- `TarielPerf` ausente com `perf_mode` ativo;
- ordem observada do template divergente do contrato canonico.

Garantias operacionais:

- o mesmo codigo/log nao e emitido em loop;
- as mensagens passam a usar codigos estaveis de boot;
- o boot deixa de falhar de forma opaca quando um modulo nao carregou.

## O que nao foi feito nesta fase

- remocao de `window.TarielClientePortal*`;
- migracao para `import` nativo, bundler ou import map;
- reescrita do carregamento do portal;
- mudanca de contratos funcionais de `admin`, `chat` ou `mesa`.
