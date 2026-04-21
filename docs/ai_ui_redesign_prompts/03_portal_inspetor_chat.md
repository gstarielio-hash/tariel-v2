Cole este prompt em uma IA de UI:

```text
Quero que você redesenhe do zero a área web do Portal do Inspetor / Chat Operacional de um produto B2B chamado Tariel.ia.

Importante:
- preserve a função do fluxo existente
- não reutilize a estilização atual
- use a estrutura de operação como base, mas proponha um visual novo

Contexto da área:
- esta área é usada pelo inspetor em campo
- ela concentra a inspeção ativa, o chat com a IA, o histórico, o status da mesa avaliadora e as pendências do laudo
- é uma tela de trabalho contínuo, não uma landing page e não um chat casual

Referência atual do que já existe hoje:
- cabeçalho com status da conexão e ação de nova inspeção
- sidebar com histórico e navegação lateral
- área principal de conversa com a IA
- barra de status da inspeção ativa
- painel ou widget da mesa avaliadora
- pendências da mesa com filtros e exportação
- estados de laudo bloqueado, leitura e reabertura
- notificações de resposta da mesa

Blocos funcionais que devem continuar existindo:
- conversa principal
- histórico lateral
- status do laudo ativo
- ação de finalizar e enviar para a mesa
- feedback de conexão
- acesso às pendências
- integração visível com a Mesa Avaliadora

Funções existentes na área:
- cabeçalho com status da conexão e início de nova inspeção
- sidebar / histórico
- conversa principal com a IA
- barra de status da inspeção ativa
- botão de finalizar e enviar para a mesa
- widget ou painel da mesa avaliadora
- pendências abertas, resolvidas e exportação
- estados de laudo bloqueado, modo leitura e reabertura
- notificações de resposta da mesa

Fontes funcionais atuais:
- web/templates/index.html
- web/templates/base.html
- web/templates/componentes/sidebar.html
- web/static/js/chat/chat_index_page.js

Leitura estrutural da UI atual:
- layout de workspace, não de página institucional
- parte superior com controles de sessão e estado
- área central de interação contínua
- elementos de status e decisão acoplados ao fluxo da inspeção

O que deve ficar claro na nova proposta:
- este é um workspace de inspeção técnica
- existe uma inspeção ativa com contexto
- a IA é assistente operacional, não chatbot casual
- a mesa avaliadora é parte do fluxo
- há prioridade, evidência, checklist e decisão

O que eu quero que você desenhe:
- a tela principal do inspetor
- com:
  - cabeçalho
  - histórico lateral
  - área de conversa
  - status da inspeção
  - ações críticas
  - entrada para a mesa avaliadora

Direção visual desejada:
- ferramenta operacional robusta
- foco em produtividade
- boa hierarquia entre contexto, conversa e ação
- sensação de software profissional de campo e revisão técnica

Não faça:
- interface parecida com WhatsApp ou suporte genérico
- cara de chat de atendimento
- excesso de enfeite
- layout que esconda o status da inspeção
- proposta que trate a mesa como detalhe secundário
- proposta que dilua a noção de inspeção ativa

Quero que você responda com:
1. conceito visual da área
2. layout da tela principal
3. hierarquia entre histórico, conversa e status
4. desenho do bloco da mesa avaliadora dentro do portal
5. proposta de componentes
6. HTML/CSS ou mockup textual detalhado
7. breve racional do porquê esse visual funciona para o inspetor em campo
```
