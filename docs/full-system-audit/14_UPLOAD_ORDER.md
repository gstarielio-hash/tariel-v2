# 14. Ordem Ideal de Envio para Outra IA

Este arquivo sugere a melhor ordem para compartilhar o pacote com outra IA, do mais importante ao complementar. A lógica é reduzir contexto desperdiçado e entregar primeiro o que estrutura o raciocínio.

## Ordem recomendada, do mais importante ao complementar

| Ordem | Arquivo | Por que enviar cedo |
| --- | --- | --- |
| 1 | `12_FOR_CHATGPT.md` | Briefing consolidado e autoexplicativo do sistema inteiro. |
| 2 | `01_repo_overview.md` | Dá o mapa mental do repositório e separa backend, frontend, mobile e infra. |
| 3 | `03_services_and_modules.md` | Explica o que é cada módulo importante e onde ele atua. |
| 4 | `04_routes_map.md` | Mostra a superfície do sistema real e como os portais se distribuem. |
| 5 | `05_backend_architecture.md` | Dá a leitura estrutural do backend e dos pontos de entrada. |
| 6 | `06_frontend_architecture.md` | Explica o web, o mobile e o acoplamento com o backend. |
| 7 | `07_end_to_end_flows.md` | Junta tudo em fluxos concretos de produto. |
| 8 | `08_performance_hotspots.md` | Direciona a IA para suspeitas técnicas com mais valor. |
| 9 | `09_tech_debt_and_risks.md` | Dá visão franca de fragilidade, legado e acoplamento. |
| 10 | `10_improvement_priorities.md` | Ajuda a IA a sugerir sequência de trabalho mais prudente. |
| 11 | `11_file_index.md` | Facilita navegação cirúrgica por arquivos reais. |
| 12 | `13_OPEN_QUESTIONS.md` | Evita que a IA invente respostas para lacunas do código. |
| 13 | `02_directory_map.md` | Complementa a topologia, mas é menos crítico que o overview. |
| 14 | `README.md` | Útil como índice, mas não precisa vir antes do briefing consolidado. |

## Ordem mínima se você puder mandar só 5 arquivos

1. `12_FOR_CHATGPT.md`
2. `01_repo_overview.md`
3. `03_services_and_modules.md`
4. `04_routes_map.md`
5. `05_backend_architecture.md`

## Ordem mínima se o foco for backend

1. `12_FOR_CHATGPT.md`
2. `05_backend_architecture.md`
3. `04_routes_map.md`
4. `03_services_and_modules.md`
5. `08_performance_hotspots.md`
6. `09_tech_debt_and_risks.md`
7. `11_file_index.md`

## Ordem mínima se o foco for frontend

1. `12_FOR_CHATGPT.md`
2. `06_frontend_architecture.md`
3. `07_end_to_end_flows.md`
4. `08_performance_hotspots.md`
5. `11_file_index.md`
6. `04_routes_map.md`

## Ordem mínima se o foco for performance

1. `12_FOR_CHATGPT.md`
2. `08_performance_hotspots.md`
3. `05_backend_architecture.md`
4. `06_frontend_architecture.md`
5. `07_end_to_end_flows.md`
6. `11_file_index.md`

## Ordem mínima se o foco for refatoração futura

1. `12_FOR_CHATGPT.md`
2. `09_tech_debt_and_risks.md`
3. `10_improvement_priorities.md`
4. `03_services_and_modules.md`
5. `05_backend_architecture.md`
6. `06_frontend_architecture.md`
7. `13_OPEN_QUESTIONS.md`

## Sugestão de envio em lotes

### Lote 1: contexto-base

- `12_FOR_CHATGPT.md`
- `01_repo_overview.md`
- `03_services_and_modules.md`
- `04_routes_map.md`
- `05_backend_architecture.md`

### Lote 2: interface e fluxos

- `06_frontend_architecture.md`
- `07_end_to_end_flows.md`

### Lote 3: diagnóstico técnico

- `08_performance_hotspots.md`
- `09_tech_debt_and_risks.md`
- `10_improvement_priorities.md`

### Lote 4: navegação complementar

- `11_file_index.md`
- `13_OPEN_QUESTIONS.md`
- `02_directory_map.md`
- `README.md`

## Confirmado no código

- A compreensão do sistema melhora bastante quando a IA recebe primeiro a visão consolidada, depois módulos e rotas, e só depois detalhes de arquivo.

## Inferência provável

- Enviar a outra IA apenas um subconjunto de arquivos do inspetor tende a distorcer a leitura, porque o sistema real depende fortemente de cliente, revisor, shared e mobile.

## Dúvida aberta

- A ordem ideal final pode variar conforme a tarefa futura da outra IA. Se o objetivo for correção pontual, talvez `11_file_index.md` suba de posição.
