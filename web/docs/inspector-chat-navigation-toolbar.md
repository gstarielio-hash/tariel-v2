# Inspector Chat Navigation Toolbar

Fase 3 da reorganização do frontend do inspetor consolidou a navegação superior e a toolbar do workspace sem tocar backend, endpoints ou regras de negócio.

## Ação central de Home

- A semântica única adotada foi `data-action="go-home"`.
- Essa ação agora é usada em:
  - `templates/inspetor/_sidebar.html`
  - `templates/inspetor/workspace/_workspace_header.html`
  - `templates/inspetor/base.html` no dock rápido
- O ponto de entrada compartilhado fica em `static/js/shared/ui.js`:
  - `solicitarNavegacaoHome(...)` despacha `tariel:navigate-home`
- A navegação funcional do inspetor continua centralizada em `static/js/chat/chat_index_page.js`:
  - `navegarParaHome(...)`
  - `processarAcaoHome(...)`

Resultado:

- não existe mais botão clicando em outro botão
- o dock rápido não procura `.btn-home-cabecalho` nem breadcrumb para simular clique
- o fluxo do inspetor continua preservando a retomada de contexto já existente

## Header compartilhado

- Partial criada: `templates/inspetor/workspace/_workspace_header.html`
- O shell do workspace agora inclui essa partial em `templates/inspetor/_workspace.html`

Esse header concentra:

- ação única de Home/Portal
- `#workspace-titulo-laudo`
- `#workspace-subtitulo-laudo`
- `#workspace-eyebrow`
- `#workspace-headline`
- `#workspace-description`
- `#workspace-status-badge`
- ações da direita:
  - `#btn-workspace-open-inspecao-modal`
  - `#btn-workspace-preview`
  - `#btn-finalizar-inspecao`

As views `assistant_landing`, `inspection_record` e `inspection_conversation` continuam consumindo o mesmo header compartilhado do shell do workspace, mantendo cada partial focada apenas no conteúdo específico.

## Toolbar compartilhada

- Partial criada: `templates/inspetor/workspace/_workspace_toolbar.html`
- O shell do workspace agora inclui essa partial em `templates/inspetor/_workspace.html`

Essa toolbar concentra:

- `.thread-nav`
- `.thread-tab[data-tab]`
- busca `#chat-thread-search`
- filtros `[data-chat-filter]`
- contador `#chat-thread-results`
- status `#chat-ai-status-chip` e `#chat-ai-status-text`

## Duplicações removidas

- breadcrumb interno deixou de competir com o botão Home
- a lógica de Home deixou de ficar espalhada entre header, breadcrumb e dock
- o fallback de `chat_painel_laudos.js` não volta a injetar breadcrumb no DOM
- header e toolbar deixaram de ficar escritos inline em `_workspace.html`

## Seletores e hooks preservados

- `.thread-nav`
- `.thread-tab`
- `#chat-thread-search`
- `[data-chat-filter]`
- `#chat-thread-results`
- `#chat-ai-status-chip`
- `#btn-finalizar-inspecao`
- `#area-mensagens`
- `#indicador-digitando`
- `#btn-ir-fim-chat`
- `.rodape-entrada`
- `.btn-home-cabecalho`

## O que esta fase nao alterou

- backend
- endpoints
- contratos de dados
- SSE
- mesa avaliadora
- anexos
- envio de mensagens
- pendências
- finalização
- regras de negócio do laudo
