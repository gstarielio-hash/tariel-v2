# Inspector Chat Focused Conversation Flow

## Objetivo

Esta fase separa a entry screen de `Novo Chat` da conversa resultante sem alterar backend, endpoints, contratos ou regras de negócio.

## O que mudou no frontend

- A tela `assistant_landing` continua sendo a entrada limpa do `Novo Chat`.
- O primeiro envio real a partir dessa tela arma a flag transitória `assistantLandingFirstSendPending`.
- Assim que existe base real de conversa no DOM, a UI promove o workspace para `inspection_conversation`.
- A conversa promovida ativa `freeChatConversationActive`, que aplica uma variante visual focada.

## Regra de transição

1. O usuário abre `Novo Chat` pelo caminho já existente `abrirChatLivreInspector(...)`.
2. O primeiro envio real marca a transição pendente no frontend.
3. Quando a primeira mensagem real já existe no histórico renderizado, a UI:
   - sai de `assistant_landing`
   - entra em `inspection_conversation`
   - força `threadTab = "chat"`
   - mantém `modoInspecaoUI = "workspace"`
4. Eventos de laudo/contexto continuam acontecendo pelo fluxo atual, mas o destino visual prioritário passa a ser a conversa focada quando a origem foi `Novo Chat`.

## Escopo visual da conversa focada

- Esconde header técnico pesado.
- Esconde busca, filtros e tabs técnicas.
- Esconde context rail e entradas operacionais da mesa.
- Mantém thread central e composer como elementos principais.
- Preserva `#campo-mensagem`, o fluxo de primeira mensagem e a renderização real das bubbles.

## Saída da variante focada

- Ao sair da aba `chat` para uma aba técnica, a flag visual do `Novo Chat` é limpa.
- Os fluxos normais de `inspection_record` e `inspection_conversation` continuam disponíveis para os outros entrypoints.
