# 10. Priorização de Melhorias

Este documento não implementa mudanças. Ele organiza prioridades de melhoria por impacto, risco e pré-condições de medição, com base na leitura do código atual.

## 1. Princípio desta priorização

Como o sistema já possui cobertura de testes e vários fluxos críticos interdependentes, as melhores próximas melhorias não são necessariamente as “mais ambiciosas”. Em muitos pontos, o maior ganho vem de tornar observável, explícito e segmentado o que hoje já funciona, mas está concentrado demais.

## 2. Melhorias rápidas e seguras

Estas melhorias tendem a ter bom custo-benefício e risco estrutural mais baixo, desde que executadas com testes.

| Prioridade | Melhoria | Impacto esperado | Risco |
| --- | --- | --- | --- |
| Alta | Instrumentar tempos e contagem de queries nas rotas críticas | Melhora capacidade de decisão sem mexer em contrato | Baixo |
| Alta | Congelar e documentar formalmente os contratos consumidos pelo mobile | Reduz regressão silenciosa | Baixo |
| Alta | Consolidar documentação da fronteira entre `cliente`, `chat` e `revisor` | Reduz custo cognitivo | Baixo |
| Alta | Inventariar e marcar explicitamente compat layers legadas | Facilita futuras remoções controladas | Baixo |
| Média | Catalogar CSS/JS realmente ativos por portal | Reduz ambiguidade do frontend | Baixo |
| Média | Adicionar medição de payload e tempo de first load do inspetor | Permite priorização real de frontend | Baixo |

## 3. Melhorias médias

Estas melhorias exigem mais cuidado, mas ainda podem ser feitas incrementalmente.

| Prioridade | Melhoria | Impacto esperado | Risco |
| --- | --- | --- | --- |
| Alta | Quebrar `chat_stream_routes.py` em orquestração menor e serviços explícitos | Reduz hotspot principal do backend | Médio |
| Alta | Fragmentar `static/js/chat/chat_index_page.js` por feature real | Reduz fragilidade do inspetor web | Médio |
| Alta | Fragmentar `static/js/cliente/portal.js` por aba/domínio | Reduz acoplamento do portal cliente | Médio |
| Média | Isolar melhor geração de PDF/preview da trilha interativa | Reduz latência e risco operacional | Médio |
| Média | Tornar a sessão multiportal mais observável | Facilita debug de auth complexa | Médio |
| Média | Reduzir dependências diretas do bridge do cliente | Melhora clareza de fronteira entre domínios | Médio |

## 4. Melhorias grandes

Estas melhorias têm potencial alto, mas pedem planejamento e fases.

| Prioridade | Melhoria | Impacto esperado | Risco |
| --- | --- | --- | --- |
| Alta | Adotar pipeline moderna de assets no frontend web | Pode reduzir peso, acoplamento e ordem manual de scripts | Alto |
| Alta | Reorganizar o runtime do inspetor em módulos mais explícitos de estado | Ataca a maior fonte de complexidade do web | Alto |
| Média | Extrair subsistema de templates de laudo para fronteira mais nítida | Melhora evolução documental | Alto |
| Média | Introduzir camada de jobs assíncronos para exportações/IA pesada | Melhora throughput e previsibilidade | Alto |
| Média | Revisitar o desenho do portal cliente como shell única | Pode simplificar UX e código | Alto |

## 5. Melhorias perigosas

São melhorias que podem valer a pena, mas exigem muito cuidado por risco de regressão alta.

| Melhoria | Por que é perigosa |
| --- | --- |
| Remover compat layers sem mapa de consumidores | Pode quebrar imports e testes legados de forma difícil de rastrear |
| Alterar contrato do chat do inspetor | Afeta web, mobile e possivelmente fluxos internos do portal cliente |
| Mudar a política de sessão multiportal sem bateria forte de testes | Pode abrir regressão de segurança e vazamento entre perfis |
| Reestruturar radicalmente o fluxo de laudo/mesa | Atravessa quase todo o produto |
| Trocar de forma abrupta o runtime frontend do inspetor | Alto risco de quebrar UX operacional central |

## 6. O que documentar melhor antes de mexer

- contratos internos do `portal_bridge.py`;
- transições válidas de estado do laudo;
- relação entre mensagens, pendências, revisões e learnings;
- fronteira entre CSS ativo e CSS legado do inspetor;
- fluxo completo de publicação de template;
- contratos exatos usados pelo mobile em chat, mesa e settings.

## 7. O que medir melhor antes de mexer

- tempo médio e percentis de `/app/api/chat`;
- tempo de render e número de queries em `/revisao/painel`;
- tempo e tamanho de exportações PDF;
- first contentful load do portal do inspetor;
- latência e taxa de falha do WebSocket/SSE;
- volume por empresa de laudos, mensagens, revisões e anexos;
- custo e latência das chamadas Gemini/Vision.

## 8. Prioridade sugerida por impacto x risco

### Primeira onda

- observabilidade e profiling das rotas críticas;
- documentação formal de contratos internos e mobile;
- inventário de compat layers e assets ativos;
- redução de ambiguidade arquitetural sem mudar comportamento.

### Segunda onda

- quebra dos maiores arquivos de backend e frontend sem alterar contratos;
- racionalização da fronteira `cliente` -> `chat/revisor`;
- melhoria de fluxo documental e exportações.

### Terceira onda

- pipeline moderna de frontend web;
- jobs assíncronos dedicados para operações pesadas;
- redesenhos estruturais maiores de portal cliente e runtime do inspetor.

## 9. Melhorias que parecem gerar maior retorno

- tornar mensurável o fluxo do chat e da mesa;
- reduzir responsabilidade dos maiores arquivos;
- formalizar fronteiras entre domínios compartilhados;
- estabilizar o frontend web em módulos menos globais.

## 10. Melhorias que exigem maior cuidado

- tudo que toca sessão, auth multiportal e contratos do chat;
- tudo que muda a publicação de templates;
- qualquer mudança que altere a experiência operacional do inspetor em campo;
- qualquer alteração de rota usada pelo mobile.

## Confirmado no código

- Existem ganhos claros disponíveis sem precisar redesenhar o sistema inteiro.
- Os maiores retornos tendem a vir de observabilidade, delimitação de fronteiras e redução de hotspots.
- Mudanças estruturais profundas precisam preservar contratos do chat, da mesa e da sessão multiportal.

## Inferência provável

- Se o time tentar começar por uma “grande reescrita”, o risco de regressão será maior que o retorno inicial.
- A melhor estratégia futura parece ser: medir, explicitar fronteiras, quebrar hotspots, só então mexer em arquitetura mais profunda.

## Dúvida aberta

- Não há evidência suficiente no repositório para afirmar se a prioridade real do negócio hoje é escala, velocidade de feature ou estabilização. A ordem final de execução dessas melhorias depende dessa direção de produto.
