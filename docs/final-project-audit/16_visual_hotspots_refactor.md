# 16. Visual Hotspots Refactor

## Data da execucao

- 2026-04-04

## Objetivo desta fase

- reduzir a dependencia do rollout visual em overrides sobre folhas legacy
- mover aparencia e semantica visual para tokens e componentes canonicos
- simplificar hotspots grandes sem quebrar fluxos funcionais oficiais

## Baseline usado como before honesto

Como o workspace local ja continha o rollout visual da fase anterior, o before desta fase foi fixado no artifact validado:

- `artifacts/final_visual_audit/20260404_191730/visual_inventory_after.json`
- `artifacts/final_visual_audit/20260404_191730/source_inventory_after.json`
- `artifacts/final_visual_audit/20260404_191730/screenshots_after/`

O after desta fase ficou em:

- `artifacts/final_visual_refactor/20260404_202709/`

## Hotspots tratados

### 1. `web/static/css/inspetor/workspace.css`

- legado puro encontrado:
  - blocos repetidos de `technical-record-header`, `thread-tab`, `technical-chat-bar`, `technical-chat-empty`, `workspace-message-action` e `workspace-mesa-card-chip`
  - coexistencia de blocos de `fase 1`, `fase 2` e refinamentos posteriores para a mesma responsabilidade visual
- o que permaneceu:
  - grid do workspace
  - comportamento estrutural do stage `assistant`
  - regras de rail, anexos e responsividade
- o que foi migrado:
  - header, toolbar, tabs, status, empty state, actions de mensagem e chips de mesa para o contrato canonico em `web/static/css/shared/official_visual_system.css`
- remocao objetiva:
  - `3897 -> 2993` linhas
  - `rgba(`: `290 -> 208`
  - `gradient(`: `32 -> 28`

### 2. `web/static/css/inspetor/reboot.css`

- legado puro encontrado:
  - redefinicoes concorrentes de `thread-tab`, `technical-chat-bar`, `workspace-message-action` e `workspace-rail-card__body`
  - valores de surface/focus ainda ancorados em um shell escuro proprio
- o que permaneceu:
  - focused conversation
  - collapse/expansao de rail
  - ajustes estruturais do shell inspetor
- o que foi migrado:
  - `surface-strong`, `surface-muted`, `surface-soft` e `ring-focus` passaram a apontar para o sistema canonico
  - tabs, toolbar e actions migraram para o shared
- remocao objetiva:
  - `4132 -> 3818` linhas
  - `rgba(`: `280 -> 249`
  - `gradient(`: `62 -> 55`

### 3. `web/static/css/chat/chat_base.css`

- legado puro encontrado:
  - dashboard do `/app` ainda com blocos escuros e hardcodes fora do contrato canonico
  - tabs genericas e workspace toolbar com linguagem propria
- o que permaneceu:
  - estrutura do chat
  - scroll/composer
  - responsividade do painel
- o que foi migrado:
  - `overview cards`, `chat-thread-surface`, `chat-thread-toolbar`, `chat-thread-pill`
  - variant `data-inspecao-ui="workspace"` retonalizada para superfices claras e tokens `--vf-*`
- remocao objetiva:
  - `rgba(`: `607 -> 584`
  - hardcodes hex cresceram em pontos localizados por troca explicita para valores canonicos, mas o contraste proprietario caiu visualmente

### 4. `web/static/css/revisor/painel_revisor.css`

- legado puro encontrado:
  - sistema proprio de tokens `tariel-*`
  - fundo com imagens decorativas antigas
  - item ativo da fila com card escuro divergente
- o que permaneceu:
  - inbox da mesa
  - filtros, badges e lista operacional
- o que foi migrado:
  - tokens da mesa reancorados em `--vf-*`
  - shell claro sem dependencia do fundo antigo
  - item ativo convergido para a mesma familia clara do sistema canonico
- remocao objetiva:
  - `rgba(`: `342 -> 333`
  - `#`: `138 -> 110`

### 5. `web/static/css/revisor/templates_biblioteca.css`

- legado puro encontrado:
  - token set paralelo em `:root`
  - hero/chips/botoes com palette propria e mais quente que o restante da mesa
- o que permaneceu:
  - estrutura da biblioteca, filtros e audit panel
- o que foi migrado:
  - superficie `templates-shell` passou a alias de `--vf-*`
  - hero, topbar, chips e botoes foram retonalizados para o eixo canonico
- remocao objetiva:
  - `rgba(`: `101 -> 96`
  - `#`: `51 -> 29`

### 6. `web/static/js/chat/chat_index_page.js`

- legado puro encontrado:
  - `CONFIG_STATUS_MESA.classe` nao era consumido por nenhum CSS oficial
  - barra de progresso do workspace dependia de `style.width` direto
- o que permaneceu:
  - sincronizacao funcional do chat/workspace/mesa
- o que foi migrado:
  - `workspace-mesa-card-status` agora expõe `data-mesa-status`
  - progresso agora é aplicado por custom property `--workspace-progress-percent` no track
- remocao objetiva:
  - `6882 -> 6878` linhas
  - remoção de metadado visual morto sem impacto funcional

## Componente compartilhado promovido nesta fase

`web/static/css/shared/official_visual_system.css` passou a concentrar o contrato canonico do inspetor para:

- `technical-record-header`
- `thread-tabs` / `thread-tab`
- `technical-chat-bar`
- `technical-chat-status`
- `technical-chat-empty`
- `workspace-message-action`
- `workspace-mesa-card-chip`
- `technical-progress__bar` via `--workspace-progress-percent`

## Validacao executada

- `python -m py_compile web/scripts/final_visual_audit.py` -> `ok`
- `make verify` -> `ok`
- `make mesa-smoke` -> `ok`
- `make mesa-acceptance` -> `ok`
- `web/scripts/final_visual_audit.py --stage after --output-root ../artifacts/final_visual_refactor/20260404_202709` -> `ok`

## Artefatos principais

- `artifacts/final_visual_refactor/20260404_202709/visual_inventory_before.json`
- `artifacts/final_visual_refactor/20260404_202709/visual_inventory_after.json`
- `artifacts/final_visual_refactor/20260404_202709/visual_inventory.json`
- `artifacts/final_visual_refactor/20260404_202709/hotspots_matrix.json`
- `artifacts/final_visual_refactor/20260404_202709/legacy_reduction_report.md`
- `artifacts/final_visual_refactor/20260404_202709/style_tokens.json`

## O que ainda ficou para depois

- `chat_base.css` ainda segue muito grande e com muitas variantes nao componentizadas
- `reboot.css` ainda concentra regras estruturais demais para focused conversation e rail
- `workspace.css` ainda tem responsividade e layouts extensos que merecem fatiamento adicional por componente
