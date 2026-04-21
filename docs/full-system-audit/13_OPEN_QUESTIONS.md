# 13. Dúvidas Abertas, Inferências e Lacunas

Este documento registra o que o código não deixou 100% claro. A ideia é separar lacunas reais do que já foi confirmado.

## 1. Infraestrutura e operação

| Tema | O que o código confirma | O que permanece em aberto | Impacto |
| --- | --- | --- | --- |
| Deploy | `render.yaml` descreve serviço web, Postgres e Redis | Não está claro se existe proxy/CDN/infra complementar fora do repo | Médio |
| Storage de uploads | Há rotas de upload e download; paths são configuráveis por env | Não está claro como é feita retenção, limpeza e backup de anexos em produção | Alto |
| Observabilidade | Há logging estruturado e correlation ID | Não ficou claro se existe APM, tracing ou dashboards fora do código | Médio |
| Escala real | O código tem hotspots claros | Não há dados de volume por tenant/portal/rota no repositório | Alto |

## 2. Banco e persistência

| Tema | O que o código confirma | O que permanece em aberto | Impacto |
| --- | --- | --- | --- |
| Índices | As tabelas principais têm índices relevantes | Não há evidência de planos reais de consulta em produção | Médio |
| Crescimento de histórico | `MensagemLaudo`, `LaudoRevisao` e `AnexoMesa` podem crescer muito | Não está claro o tamanho médio desses históricos em tenants reais | Alto |
| Sessões ativas | `SessaoAtiva` persiste estado de sessão | Não está claro o volume real de sessões concorrentes e limpeza em produção | Médio |

## 3. Backend funcional

| Tema | O que o código confirma | O que permanece em aberto | Impacto |
| --- | --- | --- | --- |
| Chat do inspetor | É o fluxo mais carregado do backend | Não está claro qual parte do tempo domina: IA, OCR, persistência ou stream | Alto |
| Portal cliente | Usa bridge para `chat` e `revisor` | Não está claro se isso é estratégia permanente ou transitória | Alto |
| Templates de laudo | Subsystem grande com CRUD, diff e editor | Não está claro se o escopo funcional desse subsystem ainda vai expandir muito | Médio |
| Learnings | Há feature de aprendizado visual | Não está claro o peso real dessa feature na operação cotidiana | Médio |

## 4. Frontend web

| Tema | O que o código confirma | O que permanece em aberto | Impacto |
| --- | --- | --- | --- |
| Trilha visual antiga do inspetor | Os assets antigos do inspetor e `web/templates/base.html` foram removidos fisicamente e protegidos por smoke/e2e | Ainda pode haver documentação histórica descrevendo o pipeline antigo como ativo se não for lida com contexto temporal | Baixo |
| Dependência de scripts globais | É explícita no código | Não está claro se já existe plano de migração para pipeline moderna | Médio |

## 5. Frontend mobile

| Tema | O que o código confirma | O que permanece em aberto | Impacto |
| --- | --- | --- | --- |
| Escopo do app | O mobile é do inspetor | Não está claro se haverá expansão para outros perfis no futuro | Médio |
| Offline | Existe fila offline e cache local | Não está claro o volume de uso real do modo offline em campo | Alto |
| Contratos críticos | O app usa APIs do inspetor e da mesa | Não está claro se existe política formal de versionamento entre app e backend | Alto |

## 6. Segurança e sessão

| Tema | O que o código confirma | O que permanece em aberto | Impacto |
| --- | --- | --- | --- |
| Isolamento por portal | O sistema trata isso explicitamente | Não está claro se já houve incidentes históricos que motivaram essa arquitetura | Baixo |
| Sessão híbrida memória+banco | Existe em `security_session_store.py` | Não está claro como esse comportamento se distribui em múltiplas instâncias fora do backend revisor com Redis | Médio |
| Auth social/fallback mobile | O mobile expõe URLs web externas por env | Não ficou claro se esses fluxos estão ativos em produção ou apenas preparados | Médio |

## 7. Performance

| Tema | O que o código confirma | O que permanece em aberto | Impacto |
| --- | --- | --- | --- |
| Painel do revisor | É montado com consultas e contadores em tempo real | Não está claro o custo real sob grandes empresas | Alto |
| Dashboard admin | Calcula métricas operacionais | Não está claro o peso real do `/admin/painel` em produção | Médio |
| Exportações PDF | Existem no caminho de uso | Não está claro se já são gargalo recorrente ou apenas potencial | Médio |

## 8. Produto e arquitetura

| Tema | O que o código confirma | O que permanece em aberto | Impacto |
| --- | --- | --- | --- |
| Portal cliente unificado | Admin, Chat e Mesa convivem na mesma tela | Não está claro se isso é decisão estratégica final ou etapa intermediária | Alto |
| Biblioteca de templates | É relevante e já madura o bastante para ter editor, diff e status | Não está claro se será tratada como produto interno de primeira classe | Médio |
| Realtime do inspetor | Existe SSE para notificações | Não está claro se haverá expansão de realtime mais rica além do estado atual | Médio |

## 9. Perguntas que valem investigação futura

1. Quais rotas realmente dominam tráfego e latência em produção?
2. Qual é o tamanho médio de histórico por laudo nas empresas maiores?
3. O portal cliente seguirá acoplado a bridges ou ganhará fronteiras próprias mais explícitas?
4. O subsystem de templates está estável ou ainda crescendo rapidamente?
5. O mobile precisa de versionamento de contrato mais formal?
6. A estratégia de sessão híbrida já foi validada sob escala real multi-instância?
7. O service worker atual está de fato melhorando a experiência do inspetor em campo?
8. Qual é a taxa de uso do OCR e do deep research nas inspeções reais?
9. Quais assets CSS/JS ainda existem só por legado?
10. Há necessidade prática de fila assíncrona para exportações e IA?

## Confirmado no código

- Existem várias dúvidas legítimas que o código sozinho não responde.
- As principais lacunas estão em métricas reais de produção, estratégia de evolução e infraestrutura externa ao repositório.

## Inferência provável

- A próxima rodada de entendimento profundo do sistema deveria combinar esta auditoria com métricas reais de produção e conversas de produto/ops.

## Dúvida aberta

- A principal dúvida transversal é: qual parte do sistema dói mais hoje para o negócio real, e não apenas para o leitor do código?
