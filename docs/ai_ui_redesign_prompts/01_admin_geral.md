Cole este prompt em uma IA de UI:

```text
Quero que você redesenhe do zero a área web de Admin-Geral de um produto SaaS B2B chamado Tariel.ia.

Importante:
- use a estrutura funcional já existente como base
- não reutilize a estilização atual
- não copie cores, tipografia, espaçamentos, cards, tabelas ou navegação da versão atual
- trate isto como um redesign visual completo, mantendo o mesmo papel operacional

Contexto da área:
- esta área é usada pelo Admin-Geral / Admin-CEO
- ela controla empresas assinantes, planos, acessos e visão macro da operação
- o usuário precisa sentir que está num painel de controle corporativo, com autoridade, clareza e capacidade de decisão

Referência atual do que já existe hoje:
- existe um dashboard executivo principal
- existe uma área de empresas assinantes com busca, filtros, tabela e ações
- existe uma tela específica para provisionar nova empresa
- existe uma tela de planos com comparação entre opções
- o shell atual é administrativo, com navegação lateral e blocos de métricas
- o tom atual é operacional e corporativo, não promocional

Blocos funcionais atuais que você deve considerar no redesign:
- KPIs executivos
- gráficos ou leitura de tendência
- alertas ou estados de atenção
- listagem densa de empresas
- ações de gestão sobre empresa
- CTA claro para criar empresa
- percepção de plano, capacidade e risco operacional

Telas e fluxos que essa área já possui:
- dashboard executivo com métricas, gráficos, alertas e visão geral da operação
- lista de empresas assinantes com busca, filtros, status e ações rápidas
- criação de nova empresa assinante
- gestão de planos e capacidade contratada
- navegação lateral / shell administrativo

Arquitetura funcional que deve ser preservada:
- visão geral com KPIs e saúde operacional
- tabela ou lista densa de empresas
- ações principais: ver detalhe, bloquear/desbloquear, criar empresa, trocar plano
- contexto de operação multiempresa
- percepção clara de risco, crescimento, capacidade e onboarding

Fontes funcionais atuais:
- web/templates/dashboard.html
- web/templates/clientes.html
- web/templates/novo_cliente.html
- web/templates/planos.html

Leitura estrutural da UI atual:
- dashboard com cards de resumo, gráfico e alertas
- área de listagem com filtros no topo e ações por linha
- formulário de provisionamento com campos da empresa e do primeiro admin-cliente
- comparação de planos em cards/blocos separados

O que eu quero que você entregue:
- uma proposta visual nova para a tela principal do Admin-Geral
- essa tela deve conseguir acomodar:
  - KPIs executivos
  - gráfico ou resumo de tendência
  - tabela/lista de empresas
  - filtros
  - CTA de criação
  - alertas operacionais
- pense desktop primeiro, mas sem quebrar em mobile

Direção esperada:
- enterprise SaaS
- alta legibilidade
- densidade informacional controlada
- sensação de comando, não de landing page
- menos marketing, mais operação

Não faça:
- interface genérica de dashboard de template
- visual “startup brinquedo”
- excesso de cards iguais sem hierarquia
- cores chamativas demais sem propósito
- proposta que elimine a tabela/lista operacional de empresas
- proposta que esconda capacidade, status e ação administrativa

Quero que você responda com:
1. conceito visual da tela
2. estrutura da layout
3. hierarquia dos blocos
4. proposta de componentes
5. HTML/CSS ou mockup textual detalhado da tela
6. breve racional do porquê essa proposta funciona para um Admin-Geral
```
