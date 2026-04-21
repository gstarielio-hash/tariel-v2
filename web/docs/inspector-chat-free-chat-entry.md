# Entrada de Chat Livre no Inspetor

## Escopo desta fase

- manter `Nova Inspeção` intacto
- adicionar uma segunda entrada de frontend para abrir o workspace do assistente sem criar laudo
- reutilizar o modo já existente `assistant_landing`
- não alterar backend, endpoints, contratos ou regras de negócio

## Pontos de entrada adicionados

- portal/home: botão secundário `Novo Chat` ao lado de `Nova Inspeção`
- modal de nova inspeção: ação discreta `Abrir chat sem modelo` no rodapé

Ambos usam o mesmo seletor semântico:

```html
data-action="open-assistant-chat"
```

## Caminho central

Função central no frontend:

```js
abrirChatLivreInspector(...)
```

Responsabilidades:

- manter o CTA `Novo Chat` visível na hero do `portal_dashboard`, mesmo com contexto restaurado localmente
- fechar o modal de nova inspeção quando estiver aberto
- fechar o modal de gate de qualidade se ele estiver aberto
- limpar `forceHomeLanding`
- sincronizar o estado reconciliado do inspetor para:
  - `modoInspecaoUI = "workspace"`
  - `workspaceStage = "assistant"`
  - `forceHomeLanding = false`
- manter `threadTab = "chat"`
- reaplicar o contexto visual do assistente
- sincronizar o screen controller para resolver em `assistant_landing`
- focar `#campo-mensagem` ao final da navegação

## Guard rails desta fase

- no `portal_dashboard`, o CTA da hero permanece visível mesmo quando existir laudo/contexto salvo em storage
- fora do portal, a entrada contextual continua condicionada à ausência de laudo ativo e de contexto de relatório
- se a entrada contextual fora do portal receber estado reconciliado com laudo ativo, a navegação não executa
- `Nova Inspeção` continua usando o modal existente e continua sendo o único caminho que chama `iniciarInspecao()`

## O que não mudou

- modal e validações de `Nova Inspeção`
- criação de laudo
- seleção de modelo/template
- mesa, anexos, histórico e pendências
- backend e contratos de dados
