# Auditoria de Rolagem e Overflow do Inspetor

## Escopo desta correção

Esta fase atuou apenas no frontend visual do inspetor, sem alterar backend, endpoints, contratos, handlers ou lógica funcional.

O shell ativo desta tela continua vindo de:

- `web/templates/inspetor/base.html`
- `web/static/css/shared/global.css`
- `web/static/css/inspetor/tokens.css`
- `web/static/css/shared/app_shell.css`
- `web/static/css/inspetor/reboot.css`

As correções efetivas ficaram concentradas em `web/static/css/inspetor/reboot.css`, como override seguro do pipeline atual.

## Arquivos que participavam do corte de conteúdo

### `web/static/css/shared/global.css`

- `body` estava fixado em `height: 100vh / 100dvh` com `overflow: hidden`
- isso exigia que o shell interno definisse claramente suas regiões roláveis

### `web/static/css/inspetor/tokens.css`

- o shell já tinha `min-height: 0` em parte da cadeia
- porém o fluxo dependia de o layout final declarar explicitamente quem rola em cada screen

### `web/static/css/inspetor/reboot.css`

- `.container-app`, `.painel-chat` e `.inspetor-shell-grid` não fechavam a cadeia completa de altura
- `.inspetor-main` não era um contêiner rolável no portal/home
- `.inspetor-sidebar` e `.inspetor-sidebar-recentes__lista` usavam uma combinação que podia limitar a visibilidade inferior
- `.chat-dashboard-grid`, `.chat-dashboard-thread` e `.workspace-view-root*` não explicitavam toda a cadeia `min-height: 0`/`height: 100%`
- `.chat-dashboard-rail__panel` usava `height: fit-content` e `max-height` dependente de `vh`
- `.modal-overlay` dependia de posicionamento absoluto dentro do host e o rodapé do modal não ficava sempre acessível

## Wrappers que estavam bloqueando rolagem

- `body` global com `overflow: hidden`
- `.inspetor-main` sem `overflow-y: auto` no portal/home
- `.inspetor-sidebar-recentes__lista` com `max-height: 42vh`
- `.chat-dashboard-grid` sem altura fechada do shell
- `.chat-dashboard-thread` e `.workspace-view-root` sem cadeia completa de `min-height: 0`
- `.chat-dashboard-rail` sem altura/overflow explícitos para a coluna direita
- `.modal-overlay` e `.modal-footer` sem arquitetura consistente para viewport fixa + rolagem interna

## Regiões que passaram a rolar explicitamente

- portal/home: `.inspetor-main`
- sidebar esquerda: `.inspetor-sidebar-recentes__lista`
- workspace `assistant_landing`: `.workspace-view-root--assistant`
- workspace `inspection_record`: `.workspace-view-root--record`
- workspace `inspection_conversation`: `.area-mensagens`
- rail/contexto direito: `.chat-dashboard-rail__panel`
- modais: `.modal-overlay` e `.modal-body`
- rodapés de ação em modais: `.modal-footer`, `.gate-acoes`, `.perfil-chat-acoes` ficaram aderentes ao fim visível do conteúdo

## Regras aplicadas

### Cadeia de altura do shell

- `container-app`, `painel-chat` e `inspetor-shell-grid` passaram a usar `min-height: 100dvh`
- `painel-chat` e `inspetor-shell-grid` passaram a fechar `height: 100%`
- `inspetor-main` passou a ter `flex: 1 1 auto`, `min-height: 0` e `height: 100%`

### Scroll por contexto

- portal/home: `inspetor-main` virou o scroll vertical principal
- workspace: `#painel-chat[data-inspecao-ui="workspace"] .inspetor-main` ficou com `overflow-y: hidden`, deixando o scroll nas views internas corretas
- conversa: `.area-mensagens` segue como região principal de scroll da timeline
- rail: `.chat-dashboard-rail__panel` ganhou `min-height: 0`, `height: auto` e `max-height` em `100dvh`

### Flex/grid defensivo

- foram reforçados `min-height: 0` e `min-width: 0` na cadeia de `chat-dashboard-grid`, `chat-dashboard-thread`, `workspace-view-stack` e `workspace-view-root`
- `workspace-view-root--assistant` e `workspace-view-root--record` passaram a ter scroll próprio

### Sidebar

- a sidebar ganhou `height/max-height: 100dvh` e `overflow: hidden`
- a área de recentes perdeu o `max-height: 42vh` e passou a usar `overflow-y: auto`

### Modais

- o overlay passou a ser fixo na viewport
- o overlay ganhou `overflow-y: auto` com `padding` seguro
- o container do modal manteve `max-height` baseado na viewport
- o `modal-body` virou a região de scroll interno
- os rodapés de ação ficaram aderentes ao fim visível do modal para evitar botões inacessíveis

## Riscos remanescentes

- listas ou campos extremamente altos dentro de componentes legados ainda podem exigir ajuste fino local, mas não havia evidência segura para mexer além do shell ativo
- a viewport móvel com teclado virtual ainda depende de comportamento do navegador em `100dvh`
- arquivos CSS legados fora do pipeline atual do inspetor continuam no repositório; esta fase corrigiu apenas o pipeline realmente carregado por `inspetor/base.html`
