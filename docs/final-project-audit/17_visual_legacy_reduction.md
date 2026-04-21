# 17. Visual Legacy Reduction

## Resumo da fase

Esta execucao nao abriu feature nova. O foco foi converter o rollout visual anterior em uma base mais nativa, removendo redefines repetidos, trocando token systems paralelos por aliases do sistema canonico e reduzindo a parte do JS que ainda opinava sobre apresentacao.

## Resultado objetivo de reducao

### Corte estrutural mais relevante

- `web/static/css/inspetor/workspace.css`
  - `3897 -> 2993` linhas
  - `rgba(`: `290 -> 208`
  - `gradient(`: `32 -> 28`
  - reducao forte de blocos duplicados do topo, tabs, toolbar, empty state e acoes de mensagem

### Cortes secundarios

- `web/static/css/inspetor/reboot.css`
  - `4132 -> 3818` linhas
  - `rgba(`: `280 -> 249`
  - `gradient(`: `62 -> 55`
- `web/static/css/revisor/painel_revisor.css`
  - `#`: `138 -> 110`
  - retirada do fundo antigo no shell claro e convergencia do card ativo da fila
- `web/static/css/revisor/templates_biblioteca.css`
  - `#`: `51 -> 29`
  - token set local substituido por aliases do sistema canonico
- `web/static/js/chat/chat_index_page.js`
  - remocao da metadata visual morta `status-*`
  - progresso do workspace migrado para custom property CSS

## O que passou a ser nativo do sistema canonico

O shared agora é a fonte primaria dos componentes visuais oficiais do inspetor:

- `technical-record-header`
- `thread-tab`
- `technical-chat-bar`
- `technical-chat-status`
- `technical-chat-empty`
- `workspace-message-action`
- `workspace-mesa-card-chip`
- `technical-progress__bar`

Na pratica, isso reduz a dependencia do `/app` em estilos escuros locais sobrepostos e torna o novo visual menos dependente de “cola por cima do antigo”.

## O que foi removido de fato

- blocos repetidos de topo/tabs/toolbar em `workspace.css`
- redefinicoes concorrentes de actions/tabs/toolbar em `reboot.css`
- palette propria e mais quente da biblioteca de templates
- item ativo escuro e fundo antigo do painel da mesa
- metadados visuais mortos em `chat_index_page.js`

## O que ainda resta de legado

### Alto

- `web/static/css/chat/chat_base.css`
  - continua muito extenso
  - ainda mistura layout, variantes de tela, componentes e estados no mesmo arquivo

### Medio

- `web/static/css/inspetor/reboot.css`
  - ainda acumula regras de focused conversation, rail e overlays que deveriam ser fatiadas
- `web/static/css/inspetor/workspace.css`
  - ainda concentra muito layout e responsividade do workspace em um unico arquivo

### Baixo

- `web/static/css/revisor/painel_revisor.css`
  - ja opera no eixo canonico, mas ainda tem bastante detalhe local de inbox
- `web/static/css/revisor/templates_biblioteca.css`
  - ficou alinhado ao canonico, mas ainda pode absorver mais componentes compartilhados

## Dependencia remanescente do visual novo em legado

O visual novo continua funcionalmente dependente de folhas antigas grandes, mas a dependencia caiu de forma real:

- o shared agora define os componentes centrais do inspetor
- os hotspots locais ficaram mais estruturais e menos donos da identidade visual
- o JS passou a expor estado visual por dataset/custom property em vez de classes mortas ou width inline

## Como manter a consistencia daqui em diante

1. quando o problema for visual e sistêmico, alterar primeiro `web/static/css/shared/official_visual_system.css`
2. evitar criar novo token set local por portal
3. ao tocar `chat_base.css`, `reboot.css` ou `workspace.css`, remover o bloco velho no mesmo commit sempre que houver migracao segura
4. continuar usando artifacts de screenshot e inventario como baseline de cada fase

## Proximo passo recomendado

`Componentizacao visual do /app e da mesa por slices canonicos`

Recorte sugerido da proxima execucao:

- extrair `thread header/tabs/toolbar` do `/app` para um slice proprio
- extrair `rail cards / progress / pendencias / mesa card` para outro slice
- reduzir `chat_base.css` por remocao progressiva de variantes antigas nao oficiais
