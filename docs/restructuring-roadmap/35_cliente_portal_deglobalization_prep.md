# Fase 2.7 - Preparacao para desglobalizacao futura do portal cliente

## Objetivo

Registrar o que ainda prende o portal cliente ao modelo atual baseado em `window.*`, o que ja ficou maduro para futura remocao e o que ainda depende de mudanca estrutural maior.

Este documento nao remove globals. Ele organiza o caminho para uma desglobalizacao segura futura.

## O que ainda depende de `window.*`

No boot atual, o portal cliente ainda depende de tres grupos de globals:

### 1. Guard e estado de boot

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__`

Papel atual:

- impedir dupla inicializacao;
- expor estado estruturado do boot;
- registrar avisos, erros e inventario validado do contrato.

Leitura:

- essa global continua necessaria enquanto `portal.js` for o entrypoint SSR servido por `<script defer>`;
- o ganho desta fase foi transformar um guard opaco em um estado auditavel.

### 2. Bridges modulares internas

- `window.TarielClientePortalRuntime`
- `window.TarielClientePortalPriorities`
- `window.TarielClientePortalAdmin`
- `window.TarielClientePortalChat`
- `window.TarielClientePortalMesa`
- `window.TarielClientePortalSharedHelpers`
- `window.TarielClientePortalShell`
- `window.TarielClientePortalBindings`

Papel atual:

- sustentar a modularizacao incremental sem bundler;
- permitir que o facade monte os modulos por injeccao de dependencias;
- manter compatibilidade com o boot em ordem manual via template.

Leitura:

- essas bridges nao sao API publica do produto;
- continuam sendo compatibilidade interna do entrypoint.

### 3. Observabilidade opcional

- `window.TarielPerf`

Papel atual:

- instrumentacao opcional quando `perf_mode` estiver ativo.

Leitura:

- nao bloqueia o portal;
- ainda e uma dependencia global externa ao bundle do cliente.

## O que ja poderia ser removido numa fase futura

Itens candidatos a remocao futura, desde que exista loader modular mais forte:

- todas as bridges `window.TarielClientePortal*`

Por que agora ficaram mais proximas de remocao:

- o facade ja tem contrato explicito de boot;
- a ordem do template esta marcada de forma canonica;
- a shape minima de exports dos modulos ja foi congelada;
- o inventario de dependencias e bridges ja esta documentado.

Leitura:

- a parte mais dificil da desglobalizacao nao e mais descobrir dependencias;
- a parte mais dificil passa a ser trocar o mecanismo de carregamento.

## O que ainda impede a desglobalizacao total

Bloqueios tecnicos atuais:

- ausencia de bundler ou ES modules no pipeline do frontend web;
- dependencia de ordem manual entre `<script defer>`;
- facade ainda monta todos os modulos a partir de `window`;
- templates SSR ainda servem os assets como lista explicita de scripts.

Leitura:

- sem alterar esse mecanismo, remover `window.TarielClientePortal*` quebraria o boot;
- a base ja esta preparada para migrar, mas ainda nao migrou o carregador.

## O que exige bundler ou mudanca maior

Itens que provavelmente exigem passo estrutural posterior:

- remover a dependencia de `window.TarielClientePortal*`;
- substituir ordem manual por imports explicitos;
- colapsar o bundle do cliente em um grafo de modulos nativo;
- eliminar o guard global como fonte de estado de boot.

Leitura:

- essas mudancas nao sao apenas "limpeza de arquivo";
- exigem decisao de pipeline e rollout mais amplo do frontend web.

## O que fica como preparacao concreta apos a fase 2.7

O portal cliente agora ja oferece quatro pre-condicoes para uma desglobalizacao segura futura:

- contrato de boot explicito em `PORTAL_BOOT_CONTRACT`;
- ordem canonica congelada no template e no smoke;
- estado de boot auditavel no proprio guard global existente;
- verificacao de factories e exports antes do `init()`.

Em termos praticos:

- a futura remocao de globals nao parte mais do escuro;
- ela pode ser planejada como troca do mecanismo de carregamento, nao como arqueologia de dependencias.
