# Verdade do Histórico no Chat Inspetor

## Objetivo

Registrar a FASE 8 da reorganização do frontend do inspetor: remover fillers sintéticos da timeline do chat e substituir isso por um empty state honesto, sem quebrar tabs, workspace, toolbar, rail ou composer.

## Confirmado no código

### Onde os fillers existiam

- Arquivo principal: `web/static/js/shared/api.js`
- Função afetada: `renderizarHistoricoCarregado(...)`
- O comportamento anterior fazia duas coisas artificiais:
  - quando `historicoLaudoPaginado` vinha vazio, criava mensagens falsas de sistema, assistente e inspetor
  - quando o histórico real tinha menos de 3 itens renderizáveis, completava a timeline com mensagens falsas

Os fillers imitavam mensagens reais porque usavam os mesmos renderizadores:

- `criarBolhaIA(...)`
- `adicionarMensagemInspetor(...)`

Isso gerava `.linha-mensagem` indistinguíveis do histórico verdadeiro.

### O que foi removido ou neutralizado

- Os blocos sintéticos de:
  - criação de sessão
  - saudação do assistente
  - mensagem simulada do inspetor com anexos
- A heurística `mensagensVisiveis.length < 3` deixou de completar a conversa.

Agora `renderizarHistoricoCarregado(...)` só percorre `mensagensVisiveis = obterMensagensHistoricoRenderizaveis()` e renderiza mensagens reais.

### Como o histórico real passou a ser tratado

Em `web/static/js/shared/api.js`:

- `mensagemPertenceAoTimelinePrincipal(...)`
  - mantém fora da timeline principal as mensagens da mesa que já têm widget dedicado
- `obterMensagensHistoricoRenderizaveis()`
  - calcula somente as mensagens reais renderizáveis na conversa principal
- `construirResumoHistoricoRenderizado(...)`
  - produz metadados honestos:
    - `totalMensagensBrutas`
    - `totalMensagensReais`
    - `mensagensOmitidasMesa`
    - `historicoVazio`
    - `teveFillersSinteticos = false`
    - `possuiEmptyStateHonesto`

### Empty state honesto

Arquivo: `web/templates/inspetor/workspace/_inspection_conversation.html`

Foi criado:

- `#workspace-conversation-empty`
- classes:
  - `technical-chat-empty`
  - `technical-chat-empty--conversation`

Regras:

- não usa `.linha-mensagem`
- não se apresenta como fala do assistente ou do inspetor
- vive dentro de `#area-mensagens`, mas como bloco semântico separado da timeline real

### Relação entre tab chat, histórico vazio e screen mode

Arquivo principal: `web/static/js/chat/chat_index_page.js`

Mudança central:

- `resolverInspectorBaseScreenPorSnapshot(...)` deixou de depender de `coletarLinhasWorkspace().length > 0`
- se `workspaceStage !== "assistant"` e `threadTab === "chat"`, o base screen agora pode ser `inspection_conversation` mesmo sem mensagens reais

Isso evita o acoplamento anterior:

- chat vazio -> sem fillers -> sem `.linha-mensagem` -> queda artificial para `inspection_record`

Agora a regra ficou:

- `assistant_landing`
  - só quando `workspaceStage === "assistant"`
- `inspection_conversation`
  - quando a tab ativa é `chat` em inspeção ativa, mesmo com histórico vazio
- `inspection_record`
  - quando a tab ativa não é `chat`

## Evento canônico preservado

Evento preservado:

- `tariel:historico-laudo-renderizado`

Payload atualizado para refletir a verdade:

- `totalMensagensBrutas`
- `totalMensagensReais`
- `mensagensOmitidasMesa`
- `historicoVazio`
- `teveFillersSinteticos = false`
- `possuiEmptyStateHonesto`

O evento continua sendo emitido por `web/static/js/shared/api.js`.

## Datasets de reflexo

Arquivo: `web/static/js/chat/chat_index_page.js`

Foram adicionados/refinados, como reflexo:

- `document.body.dataset.historyEmpty`
- `document.body.dataset.historyRealCount`
- `document.body.dataset.historySynthetic = "0"`
- `document.body.dataset.historyHonestEmpty`

Os mesmos campos também são espelhados em `#painel-chat.dataset.*`.

Esses datasets não viraram fonte primária de estado; servem só para debug e sincronização leve.

## Hooks preservados

Continuam preservados:

- `#area-mensagens`
- `#indicador-digitando`
- `#btn-ir-fim-chat`
- `.rodape-entrada`
- `.thread-nav`
- `.thread-tab`
- `document.body.dataset.threadTab`
- `tariel:historico-laudo-renderizado`

Também foram preservadas as mensagens reais renderizadas com:

- ações por mensagem
- citações
- fixar contexto
- envio para mesa
- anexos reais

## Arquivos tocados nesta fase

- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-render.js`
- `web/static/js/chat/chat_index_page.js`
- `web/templates/inspetor/workspace/_inspection_conversation.html`
- `web/docs/inspector-chat-history-truthfulness.md`

## O que não foi alterado

- backend
- endpoints
- payloads do backend
- SSE
- envio de mensagens reais
- upload/anexos reais
- mesa widget
- placeholders de pendências
- finalização/reabertura
- autoridade de estado consolidada
- canonicalização de eventos da fase anterior

## Riscos que restam para a próxima fase

## Confirmado no código

- `obterHistoricoLaudoAtual()` ainda retorna o histórico bruto, não o subconjunto renderizado da conversa principal.
- mensagens da mesa continuam fora da timeline principal e dentro do widget dedicado; isso é consistente com o estado atual do produto.

## Inferência provável

- Se algum fluxo futuro assumir que `historyRealCount` equivale ao total bruto do backend, isso vai gerar leitura errada. O nome correto agora é “mensagens reais renderizadas na conversa principal”.

## Dúvida aberta

- Não apareceu uma nova dependência funcional quebrada nesta fase.
- A próxima limpeza lógica ainda deve olhar com cuidado para a fronteira entre histórico bruto do laudo, timeline principal e widget da mesa.
