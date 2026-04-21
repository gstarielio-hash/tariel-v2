# 01. Ledger de Fases

Este ledger divide a reestruturação em fases governáveis. A proposta abaixo assume uma trilha de 90 dias com foco em segurança de mudança, e não em velocidade máxima de refactor.

## Visão geral

| Fase | Janela | Objetivo | Tipo dominante de mudança |
| --- | --- | --- | --- |
| Fase 0 | Atual | Governança e baseline | Documentação apenas |
| Fase 1 | 0-30 dias | Medir, congelar superfícies e inventariar hotspots | Observabilidade, testes e documentação |
| Fase 2 | 31-60 dias | Quebrar hotspots internamente sem mudar contrato | Modularização interna controlada |
| Fase 3 | 61-90 dias | Consolidar fronteiras, hardening e preparar deprecações | Estabilização estrutural |

## Fase 0: Governança e baseline documental

### Objetivo

Definir regras, fases, critérios de validação e rollback antes de qualquer refactor.

### Pode mudar

- documentação de governança;
- critérios de aceite;
- mapa de fases;
- políticas de merge/rollback.

### Não pode mudar

- qualquer código funcional;
- backend;
- frontend funcional;
- endpoints;
- contratos;
- regras de negócio;
- testes existentes;
- configuração de produção;
- código legado.

### Critério de saída

- roadmap aprovado pelo time;
- guardrails compreendidos;
- fases futuras definidas;
- áreas críticas explicitadas.

## Fase 1: 0-30 dias

### Objetivo

Criar baseline de segurança para mexer depois:

- medir o que importa;
- congelar contratos externos;
- inventariar superfícies críticas;
- ampliar capacidade de validar regressão sem alterar comportamento.

### Entregas esperadas

- inventário explícito dos contratos usados pelo mobile;
- inventário claro de assets ativos por portal;
- inventário dos compat layers ainda vigentes;
- medição de rotas críticas;
- critérios de alerta para `/app/api/chat` e `/revisao/painel`;
- fortalecimento de documentação de auth/session/multiportal.

### Mudanças permitidas

- documentação;
- testes novos;
- checks de CI;
- observabilidade e instrumentação;
- medições de performance;
- guards arquiteturais;
- feature flags novas, desde que inativas por padrão e sem impacto funcional.

### Mudanças proibidas

- alteração de endpoints;
- alteração de payloads;
- alteração de regras de negócio;
- alteração do comportamento do chat;
- alteração de sessão multiportal;
- alteração de fluxo mobile;
- remoção de código;
- reorganização estrutural grande de arquivos.

### Dependências

- aprovação da Fase 0;
- escolha das métricas mínimas obrigatórias;
- definição das superfícies de alto risco.

### Critério de merge da fase

- PRs pequenos;
- um objetivo técnico por PR;
- evidência explícita de que o comportamento não mudou;
- rollback imediato possível por revert simples.

### Critério de saída

- o time consegue medir hotspots e validar contratos;
- as superfícies críticas estão mapeadas;
- há baseline suficiente para refactor interno seguro.

## Fase 2: 31-60 dias

### Objetivo

Reduzir a concentração de responsabilidade dos hotspots principais sem mudar contrato externo.

### Alvos prioritários

- `web/app/domains/chat/chat_stream_routes.py`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/cliente/portal.js`
- fronteira `cliente` -> `chat/revisor`
- helpers muito densos de templates do revisor

### Mudanças permitidas

- extração de serviços internos;
- quebra de arquivos grandes em módulos menores;
- criação de facades internas;
- reorganização de helpers;
- melhoria de nomes e fronteiras internas;
- aumento de cobertura de testes;
- introdução de adaptadores e camadas de compatibilidade internas temporárias.

### Mudanças proibidas

- alterar rotas;
- alterar contratos JSON/HTML/WS/SSE;
- alterar auth/session/multiportal;
- alterar regras de negócio;
- remover legado ainda referenciado;
- alterar comportamento visível do frontend;
- alterar API consumida pelo mobile.

### Dependências

- baseline de medição da Fase 1;
- inventário de contratos;
- inventário dos módulos legados/compatíveis;
- política explícita de rollback por área.

### Critério de merge da fase

- uma superfície crítica por vez;
- mesma saída funcional antes e depois;
- testes existentes intactos;
- novos testes cobrindo a fronteira extraída;
- rollback ainda possível por revert limpo ou flag de fallback.

### Critério de pausa

- qualquer regressão em laudo, mesa, auth, templates ou mobile;
- queda de cobertura em área crítica sem compensação;
- PR misturando modularização com mudança de negócio.

### Critério de saída

- hotspots principais começam a ter fronteiras menores;
- a base fica mais legível sem alteração de contrato;
- o time consegue apontar o novo mapa interno sem depender dos arquivos monolíticos antigos.

## Fase 3: 61-90 dias

### Objetivo

Consolidar as fronteiras extraídas, endurecer validações e preparar deprecações futuras sem ainda remover código.

### Entregas esperadas

- ledger claro de compat layers candidatas a deprecação;
- documentação de fronteiras estabilizadas;
- critérios formais para futuras remoções;
- hardening de validação por superfície;
- trilha de rollback mais rápida por domínio.

### Mudanças permitidas

- documentação de deprecações futuras;
- reordenação interna final de módulos já extraídos;
- flags de fallback mais claras;
- testes e validações adicionais;
- limpeza de duplicação não funcional em pontos já estabilizados, desde que sem remover código ativo.

### Mudanças proibidas

- remoção de código legado ainda preservado como fallback;
- alteração de contrato externo;
- alteração de comportamento do usuário;
- troca de estratégia de auth/session;
- mudança de API compartilhada com o mobile.

### Dependências

- extrações da Fase 2 já validadas;
- métricas comparáveis pré e pós-mudança;
- documentação completa das novas fronteiras.

### Critério de merge da fase

- toda consolidação deve apontar fallback claro;
- toda deprecação deve estar apenas marcada, não executada;
- nada entra se enfraquecer rollback ou observabilidade.

### Critério de saída

- sistema mais governável;
- superfícies críticas com fronteiras mais claras;
- backlog pós-90 dias pronto para remoções e mudanças mais profundas, se houver aprovação explícita.

## Dependências cruzadas entre fases

| Origem | Destino | Dependência |
| --- | --- | --- |
| Fase 0 | Fase 1 | Guardrails aprovados |
| Fase 1 | Fase 2 | Métricas, inventários e contratos congelados |
| Fase 2 | Fase 3 | Hotspots parcialmente modularizados e validados |

## O que pode e o que não pode mudar por fase

| Tema | Fase 0 | Fase 1 | Fase 2 | Fase 3 |
| --- | --- | --- | --- | --- |
| Documentação | Pode | Pode | Pode | Pode |
| Testes e CI | Não alterar existentes; pode planejar | Pode ampliar | Pode ampliar | Pode ampliar |
| Observabilidade | Não | Pode | Pode | Pode |
| Modularização interna | Não | Muito limitada | Pode | Pode consolidar |
| Endpoints e contratos | Não | Não | Não | Não |
| Regras de negócio | Não | Não | Não | Não |
| Auth/session/multiportal | Não | Não | Não | Não |
| API usada pelo mobile | Não | Não | Não | Não |
| Remoção de código | Não | Não | Não | Não |

## Critério de transição de fase

Nunca avançar de fase porque “já passou tempo suficiente”. Só avançar quando os critérios de saída da fase atual forem atendidos e revisados explicitamente.
