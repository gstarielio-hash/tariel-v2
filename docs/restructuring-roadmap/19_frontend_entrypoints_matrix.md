# Fase 01.8 - Matriz de entrypoints frontend por portal

## Objetivo

Consolidar, em uma unica matriz, os entrypoints reais do frontend web por portal para servir como referencia operacional antes da Fase 2.

## Matriz canonica

| Portal | Template base | Shell principal | CSS principais | JS bootstrap | Globals obrigatorios | Service worker | Compat layers | Risco de ordem | Prioridade de limpeza futura |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `admin` | nenhum base compartilhado | `web/templates/dashboard.html` | `web/static/css/admin/admin.css`, Google Fonts `Inter`, Material Symbols remoto, CSS inline do template | `web/static/js/admin/painel.js` | `Chart`, `window.TARIEL` minimo para CSRF | nenhum | `shared/api-core.js` so em `perf_mode`; `window.TARIEL` inline | medio: `Chart.js` precisa vir antes do bootstrap | media |
| `cliente` | nenhum base compartilhado | `web/templates/cliente_portal.html` | `web/static/css/cliente/portal.css`, Google Fonts `IBM Plex Sans` | `web/static/js/cliente/portal_runtime.js`, `web/static/js/cliente/portal_priorities.js`, `web/static/js/cliente/portal_admin.js`, `web/static/js/cliente/portal_chat.js`, `web/static/js/cliente/portal_mesa.js`, `web/static/js/cliente/portal_shared_helpers.js`, `web/static/js/cliente/portal_shell.js`, `web/static/js/cliente/portal_bindings.js`, `web/static/js/cliente/portal.js` | `window.__TARIEL_CLIENTE_PORTAL_WIRED__`, `window.TarielClientePortalRuntime`, `window.TarielClientePortalPriorities`, `window.TarielClientePortalAdmin`, `window.TarielClientePortalChat`, `window.TarielClientePortalMesa`, `window.TarielClientePortalSharedHelpers`, `window.TarielClientePortalShell`, `window.TarielClientePortalBindings`; `window.TarielPerf` apenas em `perf_mode` | nenhum | instrumentacao opcional via `shared/api-core.js`; bridges internas `window.TarielClientePortal*` | medio: ordem manual entre modulos internos do portal e bridges `window.*` | media |
| `app` | `web/templates/inspetor/base.html` | `web/templates/index.html` + `web/templates/inspetor/_portal_main.html` | `web/static/css/shared/global.css`, `web/static/css/shared/material-symbols.css`, `web/static/css/inspetor/tokens.css`, `web/static/css/shared/app_shell.css`, `web/static/css/inspetor/reboot.css` | `web/static/js/shared/app_shell.js`, `web/static/js/shared/api-core.js`, `web/static/js/shared/api.js`, `web/static/js/chat/chat_index_page.js` | `window.TARIEL`, `window.TarielCore`, `window.TarielInspectorEvents`, `window.TarielAPI`, `window.TarielChatPainel`, `window.TarielInspetorModules` | `web/static/js/shared/trabalhador_servico.js` em `/app/` | `window.TarielScript`, `window.adicionarMensagemNaUI`, `window.adicionarMensagemInspetor`, `window.finalizarInspecaoCompleta`, `document._sidebarEl`, hooks historicos de sidebar | alto: cadeia longa de scripts com prerequisitos explicitos e service worker acoplado ao pacote nuclear | alta |
| `revisao` | nenhum base compartilhado | `web/templates/painel_revisor.html` | `web/static/css/revisor/painel_revisor.css`, Google Fonts `IBM Plex Sans` e `Space Grotesk`, Material Symbols remoto | `web/static/js/revisor/revisor_painel_core.js`, `web/static/js/revisor/painel_revisor_page.js` | `window.TarielRevisorPainel`, `#revisor-front-contract`, `window.TarielPerf` apenas em `perf_mode` | nenhum | namespace global do painel e contrato oculto via `data-*` | alto: `core` precisa preceder modulos e `page.js` assume namespace + front contract montados | alta |

## Notas de leitura

- `admin`, `cliente` e `revisao` ainda entram por templates monoliticos.
- `app` e o unico portal com shell compartilhado proprio, service worker proprio e cadeia extensa de compatibilidade global.
- `web/templates/base.html` nao aparece na matriz porque nao foi encontrado como entrypoint montado pelas rotas auditadas atuais.
- `web/static/js/admin/admin.js` e `web/static/js/painel.js` tambem nao entram na matriz porque nao apareceram carregados nos templates atuais.

## Dependencias de ordem mais sensiveis

### `app`

- `app_shell.js` antes do runtime do inspetor
- `api-core.js` antes dos consumidores de `TarielCore` e `TarielInspectorEvents`
- `chat-render.js` antes de `chat-network.js` e `api.js`
- `chat-network-utils.js` antes de `chat-network.js`
- `ui.js` antes de `hardware.js`
- `chat_painel_core.js` antes de `chat_painel_index.js`
- modulos `inspetor/*.js` antes de `chat_index_page.js`

### `revisao`

- `revisor_painel_core.js` antes de todos os submodulos
- `painel_revisor_page.js` por ultimo
- `#revisor-front-contract` precisa existir no HTML

### `admin`

- CDN do `Chart.js` antes de `admin/painel.js`

### `cliente`

- `portal_runtime.js` antes de `portal_priorities.js`
- `portal_priorities.js` antes de `portal_admin.js`, `portal_chat.js` e `portal_mesa.js`
- `portal_shared_helpers.js` antes de `portal_shell.js`
- `portal_shell.js` antes de `portal_bindings.js`
- `portal_bindings.js` antes de `portal.js`
- `portal.js` por ultimo como entrypoint final

## Uso recomendado desta matriz

- usar este documento como check-list antes de mover qualquer asset, trocar nome de arquivo, quebrar namespace global ou remover helper aparentemente legado;
- cruzar esta matriz com `docs/restructuring-roadmap/18_compat_layers_and_assets_by_portal.md` antes de iniciar a Fase 2.
