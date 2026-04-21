Cole este prompt em uma IA de UI:

```text
Quero que você redesenhe do zero a área web da Mesa Avaliadora de um produto B2B chamado Tariel.ia.

Importante:
- mantenha a função operacional da área
- ignore a estilização atual
- use a operação real da tela como base, não o visual atual

Contexto da área:
- a Mesa Avaliadora é usada por revisores técnicos
- ela recebe laudos em andamento e laudos aguardando avaliação
- ela precisa responder whispers, abrir pacote técnico, validar aprendizados, tratar pendências e concluir revisões
- isso é uma inbox técnica de alta responsabilidade

Referência atual do que já existe hoje:
- topbar com acesso a templates e logout
- coluna lateral de fila
- resumo operacional com métricas
- bloco de whispers urgentes
- filtros por inspetor, texto, aprendizados e fluxo
- listas separadas de laudos em andamento e aguardando avaliação
- workspace principal para análise, mensagens, histórico e decisão
- integração forte com templates e biblioteca documental

Blocos funcionais que devem permanecer no redesign:
- fila lateral com priorização
- contexto operacional da mesa
- filtros de trabalho
- destaque para whispers e pendências
- área de detalhe do laudo
- ações de responder, devolver, validar, concluir
- leitura clara de prioridade e próxima ação

Estrutura funcional atual:
- topbar com acesso a templates e logout
- coluna de lista/fila da mesa
- métricas operacionais
- whispers urgentes
- filtros por inspetor, busca, aprendizados e fluxo operacional
- lista de laudos em andamento
- lista de laudos aguardando avaliação
- workspace principal de análise do laudo
- contexto técnico, histórico, mensagens, pacote e decisão

Fontes funcionais atuais:
- web/templates/painel_revisor.html
- web/templates/login_revisor.html

Leitura estrutural da UI atual:
- layout de inbox técnica com coluna lateral e área de trabalho
- densidade informacional alta
- vários estados operacionais coexistindo na mesma tela
- distinção entre itens urgentes, fila normal e revisão final

O que deve ser preservado:
- percepção de inbox operacional
- priorização visual clara
- separação entre fila e área de trabalho
- contexto técnico suficiente para decidir sem trocar de tela
- clareza entre responder, validar, devolver e concluir

O que eu quero na nova proposta:
- uma nova tela principal da Mesa
- com visual mais forte, maduro e enterprise
- mantendo:
  - lista de trabalho lateral
  - resumo operacional
  - filtros
  - área de detalhe do laudo
  - ações críticas de revisão

Direção visual desejada:
- sala de controle técnica
- alta clareza de prioridade
- boa densidade informacional
- menos estética “dashboard genérico”
- mais sensação de workbench profissional

Não faça:
- cards demais sem função
- excesso de visual decorativo
- hierarquia fraca entre fila e conteúdo
- experiência parecida com CRM genérico
- proposta que esconda a fila de trabalho
- proposta que reduza demais a densidade e mate a operação

Quero que você responda com:
1. conceito visual da Mesa
2. estrutura de layout
3. organização da fila e da área de detalhe
4. proposta de componentes e estados
5. solução visual para prioridade, whispers, pendências e revisão final
6. HTML/CSS ou mockup textual detalhado
7. breve racional do porquê esse visual funciona para revisores técnicos
```
