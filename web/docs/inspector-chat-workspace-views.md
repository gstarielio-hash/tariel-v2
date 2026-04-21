# Workspace Views do Inspetor

## Objetivo
Separar o workspace do inspetor em views internas claras, sem alterar backend, contratos, handlers de negócio ou integrações já existentes.

## Partials criadas
- `templates/inspetor/workspace/_assistant_landing.html`
- `templates/inspetor/workspace/_inspection_record.html`
- `templates/inspetor/workspace/_inspection_conversation.html`
- `templates/inspetor/workspace/_workspace_context_rail.html`

## Como o screen mode renderiza cada view
- `assistant_landing` -> ativa a root `data-workspace-view-root="assistant_landing"`
- `new_inspection` -> reaproveita a mesma root da landing nesta fase
- `inspection_record` -> ativa a root `data-workspace-view-root="inspection_record"`
- `inspection_conversation` -> ativa a root `data-workspace-view-root="inspection_conversation"`

## O que saiu de `_workspace.html`
- Hero e cards iniciais do assistente
- Bloco de anexos do registro técnico
- Área principal de mensagens e botão de ir para o fim do chat
- Rail lateral de contexto IA, pendências, mesa e atividade

## O que ficou no shell do workspace
- Cabeçalho técnico do workspace
- `thread-nav`
- Toolbar técnica com busca, filtros e status
- `#chat-thread-empty` como estado transitório compartilhado entre registro e conversa
- Composer (`.rodape-entrada`)
- Aviso de laudo bloqueado

## Hooks e seletores sensíveis preservados
- `#workspace-assistant-landing`
- `#workspace-anexos-panel`
- `#workspace-anexos-grid`
- `#workspace-anexos-empty`
- `#workspace-anexos-count`
- `#area-mensagens`
- `#indicador-digitando`
- `#btn-ir-fim-chat`
- `.thread-nav`
- `.rodape-entrada`
- `#btn-finalizar-inspecao`
- `.chat-dashboard-rail`
- Todos os IDs do context rail (`workspace-context-*`, `workspace-progress-*`, `painel-pendencias-mesa`, `workspace-activity-list`)

## Compatibilidade preservada
- `chat_index_page.js` continua usando os mesmos IDs principais
- `chat_painel_laudos.js` continua conseguindo localizar `#area-mensagens` e `.thread-nav`
- `chat_painel_relatorio.js` continua encontrando `#btn-finalizar-inspecao` e `.rodape-entrada`

## Efeito estrutural desta fase
- Landing do assistente deixou de coexistir dentro da área de mensagens
- Registro técnico deixou de compartilhar a mesma árvore do chat ativo
- Conversa ativa ganhou um root próprio
- O rail lateral saiu do template monolítico e virou partial reutilizável
