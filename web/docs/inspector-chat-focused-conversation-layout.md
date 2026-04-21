# Inspector Chat Focused Conversation Layout

## Variant usada

- A conversa aberta a partir de `Novo Chat` agora aplica `data-conversation-variant="focused"` no shell do workspace, no header, na view de conversa, na thread e no composer.
- O fluxo técnico continua com `data-conversation-variant="technical"`.

## Problemas estruturais corrigidos

- A thread tinha duas fontes de action row: o render compartilhado criava `.acoes-mensagem` para respostas da IA e o controller do workspace injetava `.workspace-message-actions` nas outras mensagens.
- As actions da IA estavam sendo anexadas no nível da linha (`.linha-mensagem`), fora do card, o que deixava botões e ícones flutuando fora do eixo da conversa.
- A tipagem visual do indicador e das bubbles ainda vinha da composição técnica anterior, sem um shell comum de mensagem.

## Como a estrutura da mensagem ficou

- Cada linha passa a receber `workspace-message-row` com modifier por papel: `--assistant`, `--user`, `--mesa` ou `--system`.
- O shell interno foi normalizado para:
  - `workspace-message-shell`
  - `workspace-message-avatar`
  - `workspace-message-card`
  - `workspace-message-meta`
  - `workspace-message-body`
  - `workspace-message-actions`
- O render compartilhado e o controller do workspace agora convergem para a mesma estrutura visual, sem remover os hooks legados.

## Alinhamento da thread

- Usuário fica alinhado à direita com card de até `680px`.
- IA, sistema e mesa ficam alinhados à esquerda com card de até `760px`.
- A thread central usa largura máxima de `920px`, padding lateral controlado e `gap: 16px` entre mensagens.
- O indicador de digitando foi refeito usando o mesmo eixo visual das mensagens reais.

## Action row unificada

- A action row agora existe apenas uma vez por mensagem.
- Respostas da IA continuam vindo do render compartilhado, mas entram dentro de `workspace-message-card`.
- Mensagens do usuário/mesa continuam recebendo ações reais do workspace, usando a mesma classe estrutural.
- Separadores legados `.sep-acao` deixaram de ser renderizados nessa variante.

## Chrome técnico escondido

- Na variante focused ficam ocultos:
  - `thread-nav`
  - `technical-chat-bar`
  - `chat-dashboard-rail`
  - contexto do rodapé
  - ações operacionais do rodapé
  - sugestões rápidas e dica do composer
  - header técnico pesado da conversa

## Hooks preservados

- `#area-mensagens`
- `#campo-mensagem`
- `abrirChatLivreInspector(...)`
- `assistantLandingFirstSendPending`
- `freeChatConversationActive`
- `inspection_conversation` como destino visual do fluxo após a primeira mensagem
