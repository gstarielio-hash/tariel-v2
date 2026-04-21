# 20. Inspector History Componentization

## Data da execucao

- 2026-04-04

## Objetivo da fase

- fechar a componentizacao visual do historico do inspetor
- tirar do `reboot.css` o ownership final do historico oficial do `/app`
- reduzir ainda mais a dependencia do runtime oficial de folhas grandes e antigas

## Ownership final do historico

O historico do inspetor passou a ter slice proprio e entrypoint explicito:

- CSS canonicamente dono: `web/static/css/inspetor/workspace_history.css`
- template de entrada: `web/templates/inspetor/workspace/_inspection_history.html`
- carga no runtime oficial: `web/templates/inspetor/base.html`

O slice novo assume de forma nativa:

- cabecalho do historico
- toolbar de busca e filtros
- cards da timeline
- grupos do historico
- details e acoes contextuais
- estado vazio do historico
- variacoes de leitura e foco

## Contrato SSR e JS adotado

O template do historico passou a expor ownership e estado por `data-*`, sem depender de classes visuais mortas:

- `data-component-slice="workspace-history"`
- `data-workspace-history-root`
- `data-workspace-history-toolbar`
- `data-history-state`
- `data-history-focus`
- `data-history-empty`
- `data-history-timeline`
- `data-history-continue`

O `web/static/js/chat/chat_index_page.js` foi ajustado para renderizar e sincronizar o historico por dataset:

- `data-history-role`
- `data-history-type`
- `data-history-has-attachments`
- `data-history-has-text`
- `data-history-group`
- `data-history-group-header`
- `data-history-group-items`

Com isso, o JS passa a declarar estado e semantica do historico, enquanto o CSS canonicamente declara a apresentacao.

## O que saiu dos hotspots antigos

### `web/static/css/inspetor/reboot.css`

Saiu do ownership do runtime oficial do historico:

- shell principal do historico
- timeline
- grupos
- cards
- icones e meta
- anexos e actions
- details
- menu contextual
- responsividade especifica do historico

Delta objetivo desta fase:

- `2856 -> 2594` linhas
- reducao de `262` linhas

### `web/static/css/inspetor/workspace.css`

Saiu do ownership residual do historico:

- referencias de compatibilidade a `technical-chat-bar`
- regras de empty state do historico
- clusters de alinhamento que ainda disputavam ownership com o slice canonico

Delta objetivo desta fase:

- `2504 -> 2479` linhas
- reducao de `25` linhas

## Evidencia de runtime oficial

O inventario `after` desta fase mostra que o `/app` oficial carrega:

- `web/static/css/shared/global.css`
- `web/static/css/shared/material-symbols.css`
- `web/static/css/inspetor/tokens.css`
- `web/static/css/shared/app_shell.css`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`

No recorte oficial do `/app`, o runtime nao carrega `web/static/css/chat/chat_base.css` nem `web/static/css/inspetor/workspace.css`.

## Como esta fase avanca o produto

- fecha o ultimo slice grande do historico do inspetor
- deixa o ownership do `/app` mais legivel no template base oficial
- reduz o peso do `reboot.css` sem mexer em fluxo de negocio
- prepara a retirada futura do legado nao-runtime com menos risco

## O que ainda restou

- `reboot.css` ainda segura detalhes estruturais gerais do shell do inspetor
- `workspace.css` ainda existe como camada de compatibilidade fora do runtime oficial do `/app`
- `chat_index_page.js` ainda e volumoso, apesar de mais semantico no recorte do historico

## Proximo passo recomendado

`aposentadoria controlada do entrypoint legado base.html e saneamento final do shared/layout.css fora do runtime oficial`
