# Roadmap de Reestruturação do Projeto Tariel

Este pacote define a governança da reestruturação do projeto inteiro antes de qualquer mudança estrutural no código. O objetivo desta fase não é refatorar o sistema, e sim criar regras profissionais para que a reestruturação futura aconteça com previsibilidade, rastreabilidade e rollback claro.

## Objetivo da reestruturação

Construir uma trilha de reestruturação que:

- reduza risco de regressão funcional;
- preserve regras de negócio, contratos e superfícies públicas enquanto a base é organizada;
- ataque hotspots já identificados em backend, frontend e integrações;
- trate auth/session/multiportal e mobile/shared API como superfícies de alto risco;
- permita pausar, reverter ou desacelerar a reestruturação sem comprometer a operação.

## Fontes de verdade usadas neste roadmap

- `docs/full-system-audit/12_FOR_CHATGPT.md`
- `docs/full-system-audit/08_performance_hotspots.md`
- `docs/full-system-audit/10_improvement_priorities.md`
- `docs/full-system-audit/09_tech_debt_and_risks.md`

## Princípios

1. Reestruturar sem alterar negócio.
2. Medir antes de otimizar.
3. Mover responsabilidades antes de remover código.
4. Congelar contratos externos antes de modularizar internamente.
5. Tratar auth/session/multiportal e mobile/shared API como áreas de risco máximo.
6. Separar claramente mudanças estruturais, mudanças de observabilidade e mudanças de produto.
7. Não avançar de fase sem critérios explícitos de saída.

## Escopo do que pode e do que não pode mudar nesta fase de governança

### Pode

- criar documentação;
- definir fases, guardrails, critérios de merge e rollback;
- consolidar convenções de documentação da reestruturação;
- estabelecer checkpoints e critérios de pausa.

### Não pode

- alterar regras de negócio;
- alterar backend funcional;
- alterar frontend funcional;
- alterar endpoints;
- alterar contratos;
- remover código;
- mexer em auth/session/multiportal;
- mexer em API compartilhada com o mobile;
- fazer otimização estrutural sem governança aprovada.

## Visão 30/60/90 dias

| Janela | Objetivo dominante | Resultado esperado |
| --- | --- | --- |
| 0-30 dias | Baseline, observabilidade, inventário e congelamento de superfícies | O time passa a medir e documentar antes de quebrar hotspots |
| 31-60 dias | Modularização interna controlada dos maiores hotspots | Arquivos centrais começam a ser quebrados sem alterar contrato |
| 61-90 dias | Consolidação de fronteiras, hardening e preparação de deprecações | A base fica mais governável sem remoções ou mudanças públicas |

## Dependências entre fases

- Fase 1 depende apenas da governança atual aprovada.
- Fase 2 depende de baseline, inventários, critérios de validação e guardrails ativos.
- Fase 3 depende de modularizações da Fase 2 já validadas, com métricas e rollback conhecidos.
- Nenhuma fase posterior deve começar se a fase anterior estiver com regressão aberta em produção, contrato indefinido ou rollout inconsistente.

## Critérios de pausa

Pausar imediatamente a reestruturação se ocorrer qualquer um dos itens abaixo:

- regressão funcional em fluxo crítico de laudo, mesa ou templates;
- quebra de auth/session ou vazamento entre portais;
- instabilidade na API usada pelo mobile;
- aumento significativo de latência em `/app/api/chat` ou `/revisao/painel` sem explicação;
- perda de rastreabilidade de rollback;
- mudanças maiores entrando sem classificação de fase e sem evidência de validação.

## Critérios de merge

Toda mudança futura ligada à reestruturação deve entrar apenas se:

- estiver classificada em uma fase e em uma classe de risco;
- declarar explicitamente o que não muda;
- descrever impacto por superfície;
- incluir plano de validação;
- incluir plano de rollback;
- não misturar reestruturação com mudança de produto;
- não ultrapassar os guardrails do documento `02_guardrails.md`.

## Critérios de rollback

Toda iniciativa futura de reestruturação precisa ser reversível por pelo menos um destes mecanismos:

- revert de commit/PR;
- feature flag ou kill switch;
- fallback para módulo anterior ainda preservado;
- rollback operacional do deploy;
- cancelamento da fase com congelamento do legado até nova avaliação.

## Riscos principais que governam o roadmap

### Backend

- `chat_stream_routes.py` concentra responsabilidade demais;
- `revisor/panel.py` monta fila e métricas no request;
- geração documental e IA estão no caminho síncrono;
- `shared.database` e `shared.security` têm alto acoplamento.

### Frontend

- `chat_index_page.js` e `cliente/portal.js` são controladores grandes demais;
- o web ainda depende de scripts globais e ordem manual de carga;
- o inspetor é a interface mais sensível à regressão de UX.

### Auth/session/multiportal

- sessão híbrida memória+banco;
- isolamento entre `/admin`, `/cliente`, `/app` e `/revisao`;
- qualquer erro nessa área vira regressão de segurança ou de acesso.

### Mobile/shared API

- o app mobile consome a mesma API principal do backend web;
- qualquer mudança implícita de contrato em rotas do inspetor atinge o app;
- o mobile amplia o custo de regressão silenciosa.

## Convenções de documentação para toda mudança futura de reestruturação

Todo PR ou pacote de mudança futura deve registrar:

1. fase do roadmap;
2. classe de mudança;
3. superfícies impactadas;
4. invariantes preservados;
5. o que explicitamente não muda;
6. validações executadas;
7. rollback planejado;
8. dependências desbloqueadas ou criadas.

Formato mínimo esperado em documentação de mudança:

- `Contexto`
- `Escopo`
- `Invariantes`
- `Impacto por superfície`
- `Validação`
- `Rollback`
- `Próximo passo`

## Estrutura deste pacote

- `README.md`: plano mestre e princípios.
- `01_phases.md`: ledger das fases 30/60/90 com dependências e limites.
- `02_guardrails.md`: regras fortes do que pode e não pode mudar.
- `03_validation_and_rollback.md`: critérios de validação, pausa, merge e rollback.
- `132_backend_execution_checkpoint.md`: checkpoint contínuo da evolução real do backend, com fase atual, validações e próximo ponto explícito.

## Regra final desta etapa

Este roadmap não autoriza reestruturação automática. Ele só cria a base de governança. Qualquer avanço para a próxima fase exige decisão explícita depois da leitura deste pacote.
