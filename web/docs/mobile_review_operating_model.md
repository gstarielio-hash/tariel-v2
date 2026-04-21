# Mobile Review Operating Model

Documento de direcao para o Tariel tratar o mobile como superficie operacional real de validacao e decisao, sem duplicar regra fora do backend.

Complementa:

- `web/docs/memoria_operacional_governada.md`
- `web/docs/roadmap_premium_memoria_operacional.md`
- `web/docs/wave_1_memoria_operacional_governada.md`
- `web/docs/preenchimento_laudos_canonico.md`

## Tese central

O mobile nao e apenas um cliente do chat do inspetor.

No desenho premium do Tariel:

- o mobile e a superficie operacional principal de campo;
- a Mesa Avaliadora e a superficie de governanca, auditoria e excecao;
- o backend continua sendo a unica engine de validacao, hard gate, policy e rastreabilidade.

Regra estrutural:

- a logica de decisao nao mora no app;
- a logica de decisao mora no backend;
- mobile e Mesa apenas materializam a mesma regra em experiencias diferentes.

## O que o mobile faz no produto

O chat do inspetor continua util para:

- contexto;
- coleta assistida;
- orientacao;
- explicacao da previa;
- comunicacao com a Mesa.

Mas o funcionamento real de operacao deve vir do mobile:

- capturar evidencia;
- validar cobertura;
- revisar por bloco;
- corrigir pendencias;
- decidir se sobe para Mesa ou se pode ser finalizado no proprio fluxo movel.

## Modos operacionais

O produto precisa operar com tres modos claros.

### 1. `mesa_required`

Uso:

- familias mais criticas;
- tenants com politica mais rigida;
- casos com red flags;
- contratos onde a Mesa faz a decisao final obrigatoria.

Comportamento:

- o mobile faz pre-validacao e organizacao;
- a decisao final sobe para a Mesa;
- aprovacao ou rejeicao final continuam na governanca web.

### 2. `mobile_review_allowed`

Uso:

- clientes que compram operacao mais autonoma;
- familias maduras;
- casos de menor risco;
- tenants com operadores habilitados para revisar em campo.

Comportamento:

- o mobile pode executar revisao operacional completa;
- o operador pode devolver, reabrir bloco ou concluir validacao local;
- a Mesa continua disponivel como escalonamento, auditoria e excecao.

Estado do projeto:

- este modo e desenho alvo;
- ainda precisa virar contrato explicito no backend.

### 3. `mobile_autonomous`

Uso:

- familias e tenants com autonomia governada;
- casos que passam nos hard gates e na policy do tenant;
- operacoes vendidas com fechamento no proprio mobile.

Comportamento:

- o caso pode ser materializado e emitido sem handoff obrigatorio para a Mesa;
- a decisao continua rastreavel;
- a trilha operacional continua alimentando memoria e auditoria.

## Os dois tipos de validacao e finalizacao no mobile

O mobile precisa suportar dois caminhos reais.

### A. Validacao com envio para Mesa

Fluxo:

1. inspetor ou operador executa coleta e revisao no mobile;
2. o backend calcula coverage, blockers, red flags e policy;
3. o mobile fecha o pacote de campo;
4. o caso sobe para a Mesa;
5. a Mesa aprova, devolve por item, devolve por bloco ou reabre.

Este e o caminho certo para:

- contratos mais conservadores;
- familias mais sensiveis;
- casos com risco ou evidencia fraca.

### B. Validacao e finalizacao no proprio mobile

Fluxo:

1. inspetor ou operador executa coleta e revisao no mobile;
2. o backend valida gates, policy e evidencia;
3. o mobile mostra o pacote de revisao;
4. se a policy permitir, o caso pode ser finalizado no proprio app;
5. a decisao aprovada entra na trilha auditavel e na memoria operacional.

Este e o caminho certo para:

- produtos vendidos com autonomia em campo;
- familias maduras;
- tenants com entitlements especificos;
- casos sem blockers e sem red flags impeditivas.

## Mapa de capacidades

O objetivo nao e copiar a UI da Mesa no mobile.

O objetivo e dar ao mobile as mesmas capacidades essenciais, com UX propria de campo.

| Capacidade | Backend compartilhado | Mesa web | Mobile |
| --- | --- | --- | --- |
| `review_mode` | Sim | Consome | Consome |
| `coverage_map` | Sim | Sim | Sim |
| `document_readiness` | Sim | Sim | Sim |
| `document_blockers` | Sim | Sim | Sim |
| `quality_gate_operacional` | Sim | Sim | Sim |
| `refazer_inspetor` por item | Sim | Sim | Sim |
| `historico_refazer_inspetor` | Sim | Sim | Sim |
| `revisao_por_bloco` | Sim | Sim | Sim |
| `aprovar` | Sim | Sim | Conforme policy |
| `devolver` | Sim | Sim | Conforme policy |
| `reabrir` | Sim | Sim | Conforme policy |
| `emitir/finalizar` | Sim | Excecao/governanca | Conforme policy |
| `audit trail` | Sim | Sim | Sim |

## Diferenca entre Mesa e mobile

As capacidades sao equivalentes, mas o papel nao e igual.

### Mesa web

Foco:

- governanca;
- auditoria;
- excecao;
- curadoria;
- aprovacao humana avancada;
- leitura comparativa mais densa.

### Mobile

Foco:

- execucao operacional;
- validacao rapida;
- recaptura de evidencia;
- revisao objetiva em campo;
- decisao guiada por policy.

## Contratos recomendados

### 1. `review_mode`

Campo canonico resolvido no backend.

Valores relevantes:

- `mesa_required`
- `mobile_review_allowed`
- `mobile_autonomous`

### 2. `mobile_review_package`

Pacote unico para a superficie movel revisar um caso.

Campos recomendados:

- `review_mode`
- `coverage_map`
- `document_readiness`
- `document_blockers`
- `revisao_por_bloco`
- `historico_refazer_inspetor`
- `memoria_operacional_familia` resumida
- `red_flags`
- `allowed_decisions`

### 3. `mobile_decision_command`

Comandos canonicos disparados pelo app:

- `send_to_mesa`
- `return_to_inspector`
- `reopen_block`
- `approve_mobile`
- `finalize_mobile`

Regra:

- todos os comandos passam pela mesma policy do backend;
- o app nao pode "aprovar" algo que o backend marcaria como `mesa_required`.

## Regras de governanca

- autonomia no mobile depende de policy e entitlement;
- o tenant pode restringir quem revisa e quem finaliza;
- familias criticas podem continuar sempre em `mesa_required`;
- red flags podem elevar automaticamente o caso para Mesa;
- override manual precisa ficar auditado;
- qualquer aprovacao relevante precisa gerar snapshot valido para memoria.

## Relacao com memoria operacional governada

Quando o caso fecha no mobile ou na Mesa, a regra de memoria continua a mesma:

- caso aprovado fortalece memoria de conteudo;
- erro operacional fortalece memoria de controle operacional;
- rejeicao ou refacao nao viram base de texto aprovado;
- a fonte de verdade continua sendo o caso validado, nao o PDF final.

## Mapa de implementacao

### O que ja existe no codigo

- `review_mode` no policy engine;
- `mesa_required` e `mobile_autonomous` como sinais de policy;
- `document_readiness` e `document_blockers` no V2;
- contexto operacional estruturado no thread;
- `coverage_map` e historico de `refazer_inspetor` na Mesa;
- sync mobile V2 com `operational_context`.

### O que precisa virar produto agora

1. `mobile_review_package` consolidado para o app
2. `revisao_por_bloco` consumivel no mobile
3. comandos de decisao no mobile usando policy do backend
4. `mobile_review_allowed` como modo explicito
5. entitlements e policy por tenant para finalizacao autonoma

## Ordem recomendada

1. manter uma unica engine de policy e revisao no backend
2. expor o mesmo nucleo para Mesa e mobile
3. fechar primeiro `coverage_map`, `revisao_por_bloco` e `refazer_inspetor`
4. depois liberar comandos de decisao no mobile
5. por ultimo abrir autonomia comercial por tenant e familia

## Regra de retomada

Se esta frente for retomada em outra sessao, ler nesta ordem:

1. este arquivo;
2. `web/docs/memoria_operacional_governada.md`;
3. `web/docs/roadmap_premium_memoria_operacional.md`;
4. `web/app/v2/policy/models.py`;
5. `web/app/v2/policy/engine.py`;
6. `web/app/v2/contracts/projections.py`;
7. `android/src/types/mobileV2.ts`.
