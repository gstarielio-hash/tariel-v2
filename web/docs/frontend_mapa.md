# Frontend Mapa

Mapa curto do frontend ativo.

## Shell global

- `templates/inspetor/base.html`
- `static/js/shared/ui.js`
- `static/js/shared/api.js`
- `static/css/shared/global.css`
- `static/css/shared/app_shell.css`
- `static/css/shared/official_visual_system.css`
- `static/css/inspetor/reboot.css`
- `static/css/inspetor/workspace_chrome.css`
- `static/css/inspetor/workspace_history.css`
- `static/css/inspetor/workspace_rail.css`
- `static/css/inspetor/workspace_states.css`

Use essa camada para:

- Home
- perfil do usuario
- modo foco
- dock flutuante
- toasts e shell visual

## Portal do inspetor

- `templates/inspetor/base.html`
- `templates/index.html`
- `static/js/chat/chat_index_page.js`
- `static/js/inspetor/modals.js`
- `static/js/inspetor/pendencias.js`
- `static/js/inspetor/mesa_widget.js`
- `static/js/inspetor/notifications_sse.js`
- `static/js/chat/chat_perfil_usuario.js`
- `static/css/inspetor/tokens.css`
- `static/css/shared/app_shell.css`
- `static/css/inspetor/reboot.css`

Use essa camada para:

- widget da mesa
- composer principal
- historico do chat
- modal de nova inspecao
- gate de qualidade
- pendencias da mesa

## Portal do revisor

- `templates/painel_revisor.html`
- `static/css/revisor/painel_revisor.css`
- `static/js/revisor/revisor_painel_core.js`
- `static/js/revisor/revisor_painel_mesa.js`
- `static/js/revisor/revisor_painel_historico.js`
- `static/js/revisor/painel_revisor_page.js`
- `static/css/revisor/` quando houver estilo dedicado fora do template

Use essa camada para:

- inbox da revisao
- timeline do laudo
- resposta da mesa
- painel operacional da mesa
- biblioteca/editor de templates

## Regra de divisao de CSS

- `global.css`: tokens, tipografia, base
- `app_shell.css`: comportamentos e componentes globais do shell
- `official_visual_system.css`: tokens e componentes canonicos compartilhados
- `inspetor/tokens.css`: tokens visuais e reset localizado do portal
- `inspetor/reboot.css`: camada estrutural residual do portal do inspetor
- `workspace_chrome.css`, `workspace_history.css`, `workspace_rail.css`, `workspace_states.css`: slices canonicos ativos do `/app`

## Legado visual removido

Os seguintes caminhos nao fazem mais parte do runtime oficial e foram removidos fisicamente:

- `templates/base.html`
- `static/css/shared/layout.css`
- `static/css/chat/chat_base.css`
- `static/css/chat/chat_mobile.css`
- `static/css/chat/chat_index.css`
- `static/css/inspetor/{shell,home,modals,profile,mesa,responsive,workspace}.css`

As superficies oficiais `/app`, `/cliente`, `/revisao` e `/admin` nao devem referenciar esses arquivos.

## Regra de divisao de JS

- `shared/`: comportamento global reutilizavel
- `chat/`: runtime compartilhado e integração do portal do inspetor
- `inspetor/`: módulos por feature do portal do inspetor
- `revisor/`: comportamento dedicado do portal do revisor

## Bugs comuns e por onde começar

- Home/perfil/modo foco: `templates/inspetor/base.html`, `ui.js`, `app_shell.css`, `reboot.css`
- Mesa no inspetor: `index.html`, `chat_index_page.js`, `static/js/inspetor/mesa_widget.js`, `static/css/inspetor/reboot.css`
- Perfil do usuario: `chat_perfil_usuario.js`
- Corte visual mobile: breakpoints em `reboot.css` e nos slices canonicos do inspetor
- Duplicacao visual: checar se a regra esta no arquivo certo antes de editar

## Validacao rapida

```powershell
python -m pytest tests/test_smoke.py -q
$env:RUN_E2E="1"; python -m pytest tests/e2e/test_portais_playwright.py -q -k "home or perfil or modo_foco or mesa"
node --check static/js/chat/chat_index_page.js
node --check static/js/inspetor/modals.js
node --check static/js/inspetor/pendencias.js
node --check static/js/inspetor/mesa_widget.js
node --check static/js/inspetor/notifications_sse.js
node --check static/js/shared/ui.js
```
