# Fase 01.8 - Inventario canonico de compat layers e assets ativos por portal

## Contexto

A Fase 01.7 congelou o contrato real da shared API web/mobile. O criterio de saida seguinte da Fase 1 era fechar o inventario canonico dos assets ativos e das compat layers por portal antes de qualquer modularizacao mais profunda.

Sem esse mapa, a Fase 2 ficaria vulneravel a dois tipos de regressao silenciosa:

- remover ou mover um asset aparentemente legado que ainda participa do boot real;
- modularizar um portal sem perceber dependencias implicitas de ordem, `window` globals ou bridges de compatibilidade.

## Objetivo

Registrar, com base no codigo atual do repositorio, o estado real dos entrypoints frontend para:

- `/admin`
- `/cliente`
- `/app`
- `/revisao`

Este documento nao altera comportamento. Ele apenas fixa:

- templates de entrada;
- assets CSS e JS realmente carregados;
- compat layers ativas;
- globals relevantes;
- service workers envolvidos;
- riscos de modularizacao e itens com cara de legado que ainda nao podem ser removidos com seguranca.

## Fontes de verdade auditadas

### Templates

- `web/templates/index.html`
- `web/templates/inspetor/base.html`
- `web/templates/inspetor/_portal_main.html`
- `web/templates/inspetor/_sidebar.html`
- `web/templates/inspetor/_portal_home.html`
- `web/templates/inspetor/_workspace.html`
- `web/templates/dashboard.html`
- `web/templates/cliente_portal.html`
- `web/templates/painel_revisor.html`
- `web/templates/base.html`

### Frontend runtime

- `web/static/js/shared/app_shell.js`
- `web/static/js/shared/trabalhador_servico.js`
- `web/static/js/shared/api-core.js`
- `web/static/js/shared/chat-render.js`
- `web/static/js/shared/chat-network-utils.js`
- `web/static/js/shared/chat-network.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/ui.js`
- `web/static/js/shared/hardware.js`
- `web/static/js/chat/chat_sidebar.js`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_index.js`
- `web/static/js/chat/chat_painel_relatorio.js`
- `web/static/js/inspetor/modals.js`
- `web/static/js/inspetor/pendencias.js`
- `web/static/js/inspetor/mesa_widget.js`
- `web/static/js/inspetor/notifications_sse.js`
- `web/static/js/cliente/portal.js`
- `web/static/js/revisor/revisor_painel_core.js`
- `web/static/js/revisor/revisor_painel_mesa.js`
- `web/static/js/revisor/revisor_painel_historico.js`
- `web/static/js/revisor/revisor_painel_aprendizados.js`
- `web/static/js/revisor/painel_revisor_page.js`
- `web/static/js/admin/painel.js`
- `web/static/js/admin/admin.js`
- `web/static/js/painel.js`

### CSS

- `web/static/css/shared/global.css`
- `web/static/css/shared/material-symbols.css`
- `web/static/css/shared/app_shell.css`
- `web/static/css/inspetor/tokens.css`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/inspetor/shell.css`
- `web/static/css/inspetor/home.css`
- `web/static/css/inspetor/workspace.css`
- `web/static/css/inspetor/modals.css`
- `web/static/css/inspetor/profile.css`
- `web/static/css/inspetor/mesa.css`
- `web/static/css/inspetor/responsive.css`
- `web/static/css/admin/admin.css`
- `web/static/css/cliente/portal.css`
- `web/static/css/revisor/painel_revisor.css`

## Resumo executivo

- `/app` e o portal com maior superficie de compatibilidade: shell proprio, service worker proprio, cadeia longa de scripts com dependencia de ordem e varias APIs legadas ainda expostas em `window`.
- `/admin`, `/cliente` e `/revisao` ainda bootam a partir de templates monoliticos com um bootstrap JS principal por portal.
- `web/templates/base.html` nao aparece como entrypoint montado pelas rotas auditadas atuais; hoje o shell ativo do inspetor e `web/templates/inspetor/base.html`.
- `web/static/js/admin/admin.js` e `web/static/js/painel.js` existem no repositorio, mas nao aparecem carregados pelos templates atuais auditados.
- o maior risco de modularizacao continua em `/app`, seguido de `/revisao`, porque ambos dependem de namespaces globais e contratos implicitos de boot.

## Inventario por portal

## 1. Portal `/app`

### Entrada real

- template base: `web/templates/inspetor/base.html`
- shell principal: `web/templates/index.html`
- raiz SSR do conteudo: `web/templates/inspetor/_portal_main.html`

### Partials principais

- `web/templates/inspetor/_sidebar.html`
- `web/templates/inspetor/_portal_home.html`
- `web/templates/inspetor/_workspace.html`
- `web/templates/inspetor/_mesa_widget.html`
- `web/templates/inspetor/workspace/_workspace_header.html`
- `web/templates/inspetor/workspace/_workspace_toolbar.html`
- `web/templates/inspetor/workspace/_assistant_landing.html`
- `web/templates/inspetor/workspace/_inspection_record.html`
- `web/templates/inspetor/workspace/_inspection_conversation.html`
- `web/templates/inspetor/workspace/_workspace_context_rail.html`
- `web/templates/inspetor/modals/_nova_inspecao.html`
- `web/templates/inspetor/modals/_gate_qualidade.html`
- `web/templates/inspetor/modals/_perfil.html`

### CSS realmente ativo

Ativo e central:

- `/static/css/shared/global.css`
- `/static/css/shared/material-symbols.css`
- `/static/css/inspetor/tokens.css`
- `/static/css/shared/app_shell.css`
- `/static/css/inspetor/reboot.css`

Potencialmente legado, mas ainda existente no repositorio:

- `web/static/css/inspetor/shell.css`
- `web/static/css/inspetor/home.css`
- `web/static/css/inspetor/workspace.css`
- `web/static/css/inspetor/modals.css`
- `web/static/css/inspetor/profile.css`
- `web/static/css/inspetor/mesa.css`
- `web/static/css/inspetor/responsive.css`

Observacao:

- esses CSS antigos ainda aparecem em `web/templates/base.html`, mas nao aparecem no entrypoint atual `web/templates/index.html -> web/templates/inspetor/base.html`.

### JS realmente ativo

Ativo e central:

- `/static/js/shared/app_shell.js`
- `/static/js/shared/api-core.js`
- `/static/js/shared/chat-render.js`
- `/static/js/shared/chat-network-utils.js`
- `/static/js/shared/chat-network.js`
- `/static/js/shared/api.js`
- `/static/js/shared/ui.js`
- `/static/js/shared/hardware.js`
- `/static/js/chat/chat_index_page.js`
- `/static/js/chat/chat_painel_core.js`

Ativo e secundario:

- `/static/js/chat/chat_sidebar.js`
- `/static/js/chat/chat_perfil_usuario.js`
- `/static/js/chat/chat_painel_laudos.js`
- `/static/js/chat/chat_painel_historico_acoes.js`
- `/static/js/chat/chat_painel_mesa.js`
- `/static/js/chat/chat_painel_relatorio.js`
- `/static/js/inspetor/modals.js`
- `/static/js/inspetor/pendencias.js`
- `/static/js/inspetor/mesa_widget.js`
- `/static/js/inspetor/notifications_sse.js`

Compat layer ativa:

- `/static/js/shared/api.js`
- `/static/js/chat/chat_painel_index.js`
- aliases globais expostos por `chat-render.js`, `api.js` e `chat_painel_relatorio.js`

Arquivo critico de boot:

- `web/static/js/chat/chat_index_page.js`

### Compat layers e globals relevantes

Globais obrigatorios ou observados no boot:

- `window.TARIEL` em `shared/app_shell.js`
- `window.mostrarToast` em `shared/app_shell.js`
- `window.exibirToast` em `shared/ui.js`
- `window.TarielPerf`, `window.TarielCore` e `window.TarielInspectorEvents` em `shared/api-core.js`
- `window.TarielChatRender` em `shared/chat-render.js`
- `window.adicionarMensagemNaUI` e `window.adicionarMensagemInspetor` em `shared/chat-render.js`
- `window.TarielChatNetwork` em `shared/chat-network.js`
- `window.TarielAPI` em `shared/api.js`
- `window.preencherEntrada`, `window.limparPreview`, `window.prepararArquivoParaEnvio`, `window.finalizarInspecaoCompleta` em `shared/api.js`
- `window.TarielChatPainel` em `chat_painel_core.js`
- `window.TarielScript` em `chat_painel_index.js`
- `window.TarielInspectorState` e `window.TarielInspetorRuntime` em `chat_index_page.js`
- `window.TarielInspetorModules` como bridge entre `inspetor/*.js` e `chat_index_page.js`
- `document._sidebarEl` em `shared/app_shell.js` como alias de compatibilidade para a sidebar

### Service worker e shell

Ativo:

- o registro do worker e feito por `web/static/js/shared/app_shell.js`
- o worker real e `web/static/js/shared/trabalhador_servico.js`
- a rota servida e `/app/trabalhador_servico.js`
- o escopo do worker e `/app/`

Risco conhecido:

- o worker cacheia o pacote nuclear do inspetor e portanto amplia o acoplamento entre shell, ordem de scripts e nomes de arquivos.

### Dependencias de ordem

Dependencias fortes:

- `shared/app_shell.js` precisa rodar antes do restante do runtime do inspetor para preencher `window.TARIEL` e o shell global.
- `shared/api-core.js` precisa vir antes de qualquer modulo que consome `window.TarielCore`, `window.TarielPerf` ou `window.TarielInspectorEvents`.
- `shared/chat-render.js` precisa vir antes de `shared/chat-network.js` e `shared/api.js`.
- `shared/chat-network-utils.js` precisa vir antes de `shared/chat-network.js`.
- `shared/chat-network.js` precisa vir antes de `shared/api.js`.
- `shared/ui.js` deve carregar antes de `shared/hardware.js`, porque `hardware.js` assume `window.exibirToast` como fonte primaria.
- `chat_painel_core.js` precisa existir antes de `chat_painel_index.js`.
- `inspetor/modals.js`, `inspetor/pendencias.js`, `inspetor/mesa_widget.js` e `inspetor/notifications_sse.js` precisam estar prontos antes de `chat_index_page.js` consumir `window.TarielInspetorModules`.

Dependencias frageis ou historicas:

- `chat_painel_index.js` existe para expor a API de compatibilidade `window.TarielScript`.
- `shared/ui.js` ainda consulta seletores historicos como `#btn-sidebar-engenheiro`.
- `shared/app_shell.js` ainda publica `document._sidebarEl`.

## 2. Portal `/revisao`

### Entrada real

- template base: nao ha base dedicada separada
- shell principal: `web/templates/painel_revisor.html`
- partials principais: o template e monolitico; o contrato de frontend fica embutido no proprio HTML

### CSS realmente ativo

Ativo e central:

- `/static/css/revisor/painel_revisor.css`

Ativo e contextual:

- Google Fonts `IBM Plex Sans`
- Google Fonts `Space Grotesk`
- Google Material Symbols via stylesheet remoto

### JS realmente ativo

Ativo e central:

- `/static/js/revisor/revisor_painel_core.js`
- `/static/js/revisor/painel_revisor_page.js`

Ativo e secundario:

- `/static/js/revisor/revisor_painel_mesa.js`
- `/static/js/revisor/revisor_painel_historico.js`
- `/static/js/revisor/revisor_painel_aprendizados.js`

Compat layer ativa:

- `#revisor-front-contract` com `data-*` templates de URL e hooks de DOM
- namespace global `window.TarielRevisorPainel`

Arquivo critico de boot:

- `web/static/js/revisor/painel_revisor_page.js`

### Compat layers e globals relevantes

- `window.TarielRevisorPainel` em `revisor_painel_core.js`
- `window.__TARIEL_REVISOR_PAINEL_CORE_WIRED__` como guarda de boot
- `#revisor-front-contract` como contrato oculto entre HTML e JS
- `window.TarielPerf` apenas quando `perf_mode` injeta `shared/api-core.js`

### Service worker e shell

- nenhum service worker proprio identificado
- nao ha `app_shell.js` nem shell compartilhado do inspetor aqui

### Dependencias de ordem

- `revisor_painel_core.js` precisa carregar antes dos modulos de mesa, historico e aprendizados.
- `painel_revisor_page.js` precisa carregar por ultimo, pois assume `window.TarielRevisorPainel` montado.
- o boot depende do `#revisor-front-contract` presente no HTML com `data-*` e hooks esperados.
- o WebSocket `/revisao/ws/whispers` e parte do boot operacional; qualquer mudanca no contrato do contrato oculto ou dos IDs do DOM quebra o painel.

## 3. Portal `/cliente`

### Entrada real

- template base: nao ha base dedicada separada
- shell principal: `web/templates/cliente_portal.html`
- partials principais: o template e monolitico

### CSS realmente ativo

Ativo e central:

- `/static/css/cliente/portal.css`

Ativo e contextual:

- Google Fonts `IBM Plex Sans`

### JS realmente ativo

Ativo e central:

- `/static/js/cliente/portal_runtime.js`
- `/static/js/cliente/portal_priorities.js`
- `/static/js/cliente/portal_admin.js`
- `/static/js/cliente/portal_chat.js`
- `/static/js/cliente/portal_mesa.js`
- `/static/js/cliente/portal_shared_helpers.js`
- `/static/js/cliente/portal_shell.js`
- `/static/js/cliente/portal_bindings.js`
- `/static/js/cliente/portal.js`

Compat layer ativa:

- `shared/api-core.js` apenas quando `perf_mode` para observabilidade

Arquivo critico de boot:

- `web/static/js/cliente/portal.js`

### Compat layers e globals relevantes

- `window.__TARIEL_CLIENTE_PORTAL_WIRED__` como guarda de boot
- `window.TarielPerf` apenas quando `perf_mode`
- `window.TarielClientePortalRuntime`
- `window.TarielClientePortalPriorities`
- `window.TarielClientePortalAdmin`
- `window.TarielClientePortalChat`
- `window.TarielClientePortalMesa`
- `window.TarielClientePortalSharedHelpers`
- `window.TarielClientePortalShell`
- `window.TarielClientePortalBindings`
- armazenamento local em chaves `tariel.cliente.*`

### Service worker e shell

- nenhum service worker proprio identificado
- nao usa `app_shell.js`

### Dependencias de ordem

- `shared/api-core.js` continua opcional e so participa quando `perf_mode`.
- a ordem funcional atual do portal e `portal_runtime.js -> portal_priorities.js -> portal_admin.js -> portal_chat.js -> portal_mesa.js -> portal_shared_helpers.js -> portal_shell.js -> portal_bindings.js -> portal.js`.
- `portal.js` continua sendo o entrypoint final, mas depende das bridges internas acima ja registradas em `window`.
- a fragilidade principal deixou de ser um unico monolito e passou a ser a ordem manual das bridges internas.

## 4. Portal `/admin`

### Entrada real

- template base: nao ha base dedicada separada
- shell principal: `web/templates/dashboard.html`
- partials principais: o template e monolitico

### CSS realmente ativo

Ativo e central:

- `/static/css/admin/admin.css`

Ativo e contextual:

- Google Fonts `Inter`
- Google Material Symbols via stylesheet remoto
- bloco inline `<style>` dentro do template

### JS realmente ativo

Ativo e central:

- `/static/js/admin/painel.js`

Ativo e secundario:

- `shared/api-core.js` apenas quando `perf_mode`
- inline script de alertas/logout em `dashboard.html`

Compat layer ativa:

- `window.TARIEL = Object.freeze({ csrfToken })` no proprio template

Arquivo critico de boot:

- `web/static/js/admin/painel.js`

### Compat layers e globals relevantes

- `Chart` vindo do CDN de `chart.js`
- `window.TARIEL` com shape minimo para CSRF
- `window.TarielPerf` apenas quando `perf_mode`

### Service worker e shell

- nenhum service worker proprio identificado
- nao usa `app_shell.js`
- o template referencia `manifest` em `/app/manifesto.json`, o que cria um acoplamento leve com o dominio de assets do inspetor

### Dependencias de ordem

- `Chart.js` precisa carregar antes de `admin/painel.js`.
- `shared/api-core.js`, quando presente, vem antes de `admin/painel.js`, mas serve so para instrumentacao.
- o portal nao tem cadeia grande de modulos, mas depende de um asset externo remoto para o grafico.

## Compat layers ativas de maior importancia

## 1. Camadas de compatibilidade do inspetor ainda ativas

- `window.TarielScript` em `web/static/js/chat/chat_painel_index.js`
- `window.adicionarMensagemNaUI` em `web/static/js/shared/chat-render.js`
- `window.adicionarMensagemInspetor` em `web/static/js/shared/chat-render.js`
- `window.finalizarInspecaoCompleta` em `web/static/js/shared/api.js` e `web/static/js/chat/chat_painel_relatorio.js`
- `window.preencherEntrada` em `web/static/js/shared/api.js`
- `document._sidebarEl` em `web/static/js/shared/app_shell.js`
- `#btn-sidebar-engenheiro` ainda consultado por `web/static/js/shared/ui.js` e `web/static/js/chat/chat_sidebar.js`
- `window.TarielInspetorModules` como bridge entre modulos do shell e o bootstrap final

## 2. Camadas de compatibilidade do revisor ainda ativas

- `window.TarielRevisorPainel` como namespace comum
- `#revisor-front-contract` com URLs e hooks de DOM no HTML

## 3. Globais compartilhados que merecem cuidado

- `window.TARIEL` existe em pelo menos dois shapes diferentes: inspetor e admin
- `window.TarielPerf` pode existir em portais diferentes quando `perf_mode`
- `window.TarielCore` e `window.TarielInspectorEvents` ficam disponiveis globalmente no inspetor

## Itens com cara de legado que ainda nao podem ser removidos

- `web/static/js/shared/api.js`
- `web/static/js/chat/chat_painel_index.js`
- `window.TarielScript`
- `window.adicionarMensagemNaUI`
- `window.adicionarMensagemInspetor`
- `window.finalizarInspecaoCompleta`
- `document._sidebarEl`
- `#revisor-front-contract`
- hooks antigos como `#btn-sidebar-engenheiro`

Motivo:

- todos esses elementos ainda participam do runtime real ou preservam compatibilidade entre modulos novos e antigos.

## Legado aparentemente nao carregado pelos portais auditados

- `web/templates/base.html`
- `web/static/js/admin/admin.js`
- `web/static/js/painel.js`
- o conjunto antigo de CSS do inspetor:
  - `web/static/css/inspetor/shell.css`
  - `web/static/css/inspetor/home.css`
  - `web/static/css/inspetor/workspace.css`
  - `web/static/css/inspetor/modals.css`
  - `web/static/css/inspetor/profile.css`
  - `web/static/css/inspetor/mesa.css`
  - `web/static/css/inspetor/responsive.css`

Observacao:

- esses itens parecem fora do entrypoint principal atual, mas esta fase nao autoriza remocao. Eles devem permanecer ate uma validacao dedicada de consumers residuais e rotas secundarias.

## Duvidas abertas

- `web/PROJECT_MAP.md` e outros docs antigos ainda descrevem `templates/base.html` como shell base; isso nao bate com o entrypoint real atual do inspetor.
- o admin aponta `manifest` para `/app/manifesto.json` mesmo sem usar o shell do inspetor; isso e um acoplamento pequeno, mas real.
- a existencia simultanea de `web/static/js/admin/painel.js`, `web/static/js/admin/admin.js` e `web/static/js/painel.js` indica historico de migracao ainda nao encerrado.

## Riscos de modularizacao

## 1. `/app` pode cair com uma mudanca pequena de ordem

Fragilidades principais:

- ordem entre `api-core`, `chat-render`, `chat-network`, `api`, `ui`, `hardware` e `chat_index_page`
- dependencia de `window` globals e aliases legados
- service worker cacheando o pacote nuclear do inspetor
- contratos implicitos com IDs e datasets do shell

## 2. `/revisao` depende de contrato HTML escondido

Fragilidades principais:

- `painel_revisor_page.js` depende do namespace global comum
- o contrato `#revisor-front-contract` concentra URLs e hooks fora do proprio modulo JS
- o painel mistura WebSocket, fetch e varios submodulos que assumem o mesmo estado global

## 3. `/admin` depende de asset externo remoto

Fragilidades principais:

- o grafico depende de `Chart.js` por CDN
- o portal mistura CSS externo, CSS local e bloco inline no template
- ha duplicacao aparente de scripts administrativos no repositorio

## 4. `/cliente` concentra muita superficie num unico arquivo

Fragilidades principais:

- `cliente/portal.js` acumula tabs, painel admin, chat e mesa no mesmo bootstrap
- a modularizacao futura precisa preservar IDs, armazenamento local e binds de DOM antes de qualquer divisao

## Prioridade de limpeza futura

- prioridade alta: compat layers e ordem de boot do `/app`
- prioridade alta: contrato oculto e namespace global do `/revisao`
- prioridade media: scripts administrativos duplicados e dependencia de CDN no `/admin`
- prioridade media: decomposicao controlada de `cliente/portal.js`

## Efeito desta fase no roadmap

Esta fase fecha mais um criterio de saida da Fase 1:

- agora existe um inventario canonico dos assets reais e das compat layers por portal;
- isso reduz o risco de entrar na Fase 2 com remocao ou modularizacao baseada em docs desatualizados ou suposicoes de boot.

## Proximo passo recomendado

A proxima fase mais segura deixa de ser puramente documental e volta para hotspot real medido:

- Fase 01.9 - baseline dedicada e reducao segura do boot de `/revisao/painel`

Motivo:

- com shared API e inventario de assets congelados, o maior gargalo estrutural remanescente volta a ser o painel do revisor, que segue monolitico e sensivel a ordem/globais.
