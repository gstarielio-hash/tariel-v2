# 18. Visual Component Slices

## Data da execucao

- 2026-04-04

## Objetivo da fase

- quebrar o visual oficial do `/app` e da Mesa em slices menores e explicitamente canônicos
- reduzir a responsabilidade de `reboot.css`, `workspace.css` e `chat_base.css`
- preservar a aparencia aprovada da fase anterior com uma implementacao menos dependente de overrides globais

## Decisao estrutural principal

O runtime oficial do inspetor passou a carregar slices dedicados em `web/templates/inspetor/base.html`:

- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`

Esses arquivos entram depois de `web/static/css/shared/official_visual_system.css`, entao o shared continua sendo a fonte dos tokens e contratos canonicos, enquanto os slices passam a concentrar a composicao concreta do `/app`.

## Slices extraidos nesta fase

### 1. `workspace_chrome.css`

Recorte dono de:

- thread header
- hero strip do workspace
- tabs
- toolbar superior
- pequenos status e acoes de topo
- leitura operacional do historico

Pontos de entrada marcados:

- `data-component-slice="workspace-chrome"` em `web/templates/inspetor/workspace/_workspace_header.html`
- `data-component-slice="workspace-chrome"` em `web/templates/inspetor/workspace/_workspace_toolbar.html`
- `data-component-slice="workspace-chrome"` em `web/templates/inspetor/workspace/_inspection_history.html`

### 2. `workspace_rail.css`

Recorte dono de:

- rail cards
- progress bar
- blocos de contexto
- pendencias
- mesa card
- chips e facts do rail

Ponto de entrada marcado:

- `data-component-slice="workspace-rail"` em `web/templates/inspetor/workspace/_workspace_context_rail.html`

### 3. `workspace_states.css`

Recorte dono de:

- empty states
- acoes de mensagem
- shell do composer
- estados focados do workspace
- variacoes de leitura vazia para conversa, historico e rail

## O que saiu dos hotspots antigos

### `web/static/css/inspetor/reboot.css`

Saiu do ownership principal:

- thread header
- thread nav shell
- hero strip
- rail toggle
- rail card body
- context KPI
- progress visuals

O arquivo ficou mais estrutural e menos dono da identidade visual.

### `web/static/css/inspetor/workspace.css`

Saiu do ownership principal:

- top chrome do workspace
- blocos principais de rail
- empty states canonicos
- acoes pequenas do fluxo de conversa

O arquivo ficou como camada de compatibilidade e layout residual, nao como fonte oficial do slice.

### `web/static/css/chat/chat_base.css`

Saiu do ownership principal:

- bloco ativo do workspace do `/app`

O arquivo foi tratado explicitamente como legado nao carregado pelo runtime oficial do inspetor nesta fase. O bloco antigo foi removido para reduzir confusao de ownership.

## JS visual reduzido

`web/static/js/chat/chat_index_page.js` deixou de sustentar parte do visual por classe morta e `style` inline:

- toggles da rail agora usam `data-expanded` + `aria-expanded`
- progresso da mesa usa `--workspace-progress-percent` no card do progresso
- o card de progresso tambem expõe `data-progress-state`

Com isso, o CSS passa a reagir a estado sem que o JS precise continuar definindo apresentacao diretamente.

## Deltas objetivos desta componentizacao

- `web/static/css/inspetor/reboot.css`: `3818 -> 2856` linhas
- `web/static/css/inspetor/workspace.css`: `2993 -> 2504` linhas
- `web/static/css/chat/chat_base.css`: `5676 -> 5375` linhas
- diff do slice tratado: `190 insertions`, `3162 deletions`

Novos arquivos introduzidos:

- `web/static/css/inspetor/workspace_chrome.css` com `317` linhas
- `web/static/css/inspetor/workspace_rail.css` com `406` linhas
- `web/static/css/inspetor/workspace_states.css` com `535` linhas

## Como esta fase avanca o produto

- torna o `/app` menos dependente de folhas antigas monoliticas
- separa estrutura, componente e estado em ownership mais legivel
- facilita futuras remocoes de legado sem precisar redesenhar o produto
- cria um contrato mais claro entre templates SSR, JS visual e CSS canonico

## O que ainda restou

- `reboot.css` ainda concentra parte do historico focado e detalhes estruturais do shell
- `workspace.css` ainda guarda layout residual e responsividade antiga
- `chat_base.css` continua extenso como legado de compatibilidade, mesmo sem ser entrypoint oficial do `/app`

## Proximo passo recomendado

`Desativacao controlada do legado nao-runtime e componentizacao final do historico do inspetor`
