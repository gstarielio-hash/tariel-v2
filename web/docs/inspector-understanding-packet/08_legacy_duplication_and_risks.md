# 08. Legado, Duplicações e Riscos

## Visão Geral

O Chat Inspetor já tem uma estrutura visual mais organizada do que antes, mas ainda opera com duplicação de estado, aliases legados de eventos, fallbacks que recriam DOM e fillers visuais que mascaram a ausência de dados reais.

Esses pontos são os principais riscos para qualquer mudança futura.

## 1. Duplicação de Autoridade de Estado

### Confirmado no código

O estado relevante do sistema está espalhado entre:

- `web/app/domains/chat/session_helpers.py`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/shared/api.js`
- `document.body.dataset`
- `localStorage`
- `sessionStorage`

### Risco

- divergência entre laudo ativo do servidor e laudo ativo do cliente
- divergência entre screen mode visual e dados reais carregados
- bugs de navegação difíceis de reproduzir

## 2. Eventos Duplicados e Compatibilidade Retroativa

### Confirmado no código

`chat_index_page.js` escuta tanto eventos novos quanto aliases legados, por exemplo:

- `tariel:relatorio-iniciado`
- `tarielrelatorio-iniciado`

e equivalentes para finalização, cancelamento, mesa, gate e histórico.

### Risco

- dupla reação a um mesmo fato
- dificuldade de remover código antigo sem quebrar caminhos ocultos

## 3. Fallback que Recria a Toolbar de Tabs

### Confirmado no código

`web/static/js/chat/chat_painel_laudos.js::garantirThreadNav()` recria `.thread-nav` se o seletor não existir.

### Risco

- layout duplicado ou desalinhado
- markup divergente do template oficial
- bugs em refatorações do topo do workspace

## 4. Histórico Sintético quando Faltam Mensagens Reais

### Confirmado no código

`web/static/js/shared/api.js::renderizarHistoricoCarregado()` injeta mensagens sintéticas quando o histórico do laudo é vazio ou muito curto.

Os fillers incluem:

- mensagem de sistema de criação de sessão
- saudação do assistente
- mensagem de usuário simulada com anexos

### Risco

- confusão entre dado real e placeholder
- auditoria visual enganosa
- falsa percepção de conversa existente

## 5. Pendências Placeholder

### Confirmado no código

`web/static/js/inspetor/pendencias.js` injeta pendências exemplo quando o filtro está em `abertas` e não há itens reais.

Exemplos confirmados:

- "Certificado de calibração"
- "Medição de espessura"

### Risco

- operador ou IA assumir que há pendências reais
- confusão ao depurar inconsistências da mesa

## 6. Hook Legado na Sidebar

### Confirmado no código

`web/static/js/chat/chat_sidebar.js` ainda procura `#btn-sidebar-engenheiro`. Quando não encontra, emite warning.

### Risco

- ruído de console
- falsa impressão de quebra funcional
- evidência de acoplamento com um template já removido

## 7. Mesa em Dois Caminhos Conceituais

### Confirmado no código

Há dois caminhos de uso da mesa:

- widget dedicado em `web/static/js/inspetor/mesa_widget.js`
- prefixo `@insp ` no composer, tratado por `web/static/js/chat/chat_painel_mesa.js`

### Risco

- duplicação de UX
- regras de contexto diferentes
- dificuldade para definir uma única porta de entrada de mesa

## 8. Finalização com Mais de um Caminho

### Confirmado no código

`web/static/js/shared/chat-network.js` contém:

- finalização direta por endpoint `POST /app/api/laudo/{id}/finalizar`
- finalização via comando de sistema enviado ao chat

### Risco

- comportamento diferente conforme o caminho acionado
- maior superfície para regressão

## 9. Navegação Home depende de Storage e Sessão

### Confirmado no código

Apesar da semântica de Home ter sido centralizada em `data-action="go-home"`, a implementação ainda atravessa:

- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_index_page.js`
- `sessionStorage["tariel_force_home_landing"]`
- `sessionStorage["tariel_workspace_retomada_home_pendente"]`
- `localStorage["tariel_laudo_atual"]`
- `POST /app/api/laudo/desativar`

### Risco

- retorno inconsistente para Home em cenários de back/refresh
- laudo ativo "fantasma"

## 10. Estado de Leitura/Reabertura Espalhado

### Confirmado no código

O modo read-only e os botões de finalizar/reabrir dependem de:

- `web/static/js/chat/chat_painel_relatorio.js`
- `web/static/js/shared/chat-network.js`
- `web/static/js/shared/api.js`
- `web/static/js/chat/chat_index_page.js`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/chat/session_helpers.py`

### Risco

- inconsistência entre UI e backend
- botão visível quando a ação não é permitida, ou o oposto

## 11. Acoplamento por Seletor e Dataset

### Confirmado no código

O runtime inteiro depende de seletores e datasets como contrato implícito:

- `.thread-nav`
- `#area-mensagens`
- `#btn-finalizar-inspecao`
- `#chat-thread-search`
- `document.body.dataset.threadTab`
- `document.body.dataset.estadoRelatorio`
- `document.body.dataset.inspectorScreen`

### Risco

- pequenas mudanças de markup quebram módulos não relacionados
- o sistema é sensível a detalhes de DOM

## 12. Pontos Onde a UI Fica Bagunçada

### Confirmado no código

Os maiores geradores de bagunça visual/mental são:

- fillers do histórico em `shared/api.js`
- placeholder de pendências em `inspetor/pendencias.js`
- fallback `garantirThreadNav()` em `chat_painel_laudos.js`
- hook inexistente em `chat_sidebar.js`
- múltiplas autoridades de estado refletidas em dataset + storage + objetos globais

## 13. Mudanças de Alto Risco

### Muito arriscado mexer sem mapa completo

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/shared/api.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/static/js/shared/chat-network.js`
- `web/templates/inspetor/_workspace.html`
- `web/templates/inspetor/workspace/_workspace_toolbar.html`
- `web/templates/inspetor/workspace/_workspace_header.html`
- `web/static/css/inspetor/reboot.css`

### Por quê

- esses arquivos concentram layout, estado, URL, histórico, screen mode e integrações

## 14. Onde Uma Refatoração Segura Deveria Começar

### Ordem sugerida

1. Consolidar a autoridade de estado de laudo e screen mode.
2. Remover aliases legados de evento com telemetria e testes.
3. Eliminar fillers sintéticos de histórico e pendências.
4. Remover `garantirThreadNav()` depois de garantir cobertura de testes do toolbar shell.
5. Unificar a entrada para mesa.

## Confirmado no Código

- Há dívida técnica real e objetiva, não apenas percepção subjetiva.
- O sistema depende de compatibilidade para não quebrar partes antigas.
- As duplicações são principalmente de estado e sincronização, não mais tanto de template.

## Inferência

- O topo do workspace já está mais limpo porque a reorganização recente atacou a duplicação estrutural primeiro. O próximo gargalo evidente é reduzir a duplicação de estado.

## Dúvida Aberta

- Não está explícito no repositório quais fallbacks ainda são necessários em produção real e quais já poderiam ser removidos sem impacto.
