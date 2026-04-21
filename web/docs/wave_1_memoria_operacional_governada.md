# Wave 1 da Memoria Operacional Governada

Documento tecnico da primeira onda implementavel da memoria operacional governada.

Complementa:

- `web/docs/memoria_operacional_governada.md`
- `web/docs/roadmap_premium_memoria_operacional.md`

## Objetivo da Wave 1

Tirar a memoria operacional do campo de ideia e coloca-la em base versionada de produto.

Esta onda nao tenta resolver:

- coverage map completo na UI;
- quality gate visual com CV pesado;
- promotion desk automatizado;
- family memory index consolidado e materializado;
- endpoints publicos finais.

Esta onda resolve a infraestrutura minima para isso existir depois:

1. persistencia versionada do caso aprovado;
2. persistencia auditavel do evento operacional;
3. persistencia por evidencia da validacao operacional e da Mesa;
4. persistencia de irregularidade que leva a `refazer_inspetor`;
5. contratos de aplicacao para gravar e ler essa memoria;
6. servicos internos para registrar e resumir a memoria por familia.

## Escopo implementado

### Tabelas

1. `laudo_approved_case_snapshots`
   - fotografia canonica do caso aprovado;
   - suporta versoes por laudo;
   - guarda `laudo_output_snapshot`, manifesto de evidencia e resumo da Mesa.

2. `laudo_operational_events`
   - trilha de sinais operacionais do caso;
   - guarda tipo, origem, severidade, bloco/evidencia e metadata.

3. `laudo_evidence_validations`
   - estado consolidado por evidencia dentro do laudo;
   - guarda `quality_score`, `coherence_score`, status operacional e status da Mesa.

4. `laudo_operational_irregularities`
   - irregularidade que efetivamente exige correcao ou descarte;
   - liga opcionalmente evento e validacao de evidencia;
   - suporta resolucao auditavel.

## Contratos de aplicacao

Contratos versionados em:

- `app/shared/operational_memory_contracts.py`

Entradas:

- `ApprovedCaseSnapshotInput`
- `OperationalEventInput`
- `EvidenceValidationInput`
- `OperationalIrregularityInput`
- `OperationalIrregularityResolutionInput`

Saidas:

- `FamilyOperationalMemorySummary`
- `FamilyOperationalFrequencyItem`

## API interna inicial

Servicos internos versionados em:

- `app/shared/operational_memory.py`

Funcoes abertas nesta onda:

- `registrar_snapshot_aprovado`
- `registrar_evento_operacional`
- `registrar_validacao_evidencia`
- `abrir_irregularidade_operacional`
- `resolver_irregularidade_operacional`
- `build_family_operational_memory_summary`

Importante:

- isto ainda e `application API`, nao rota HTTP publica;
- o objetivo aqui e permitir integracao gradual por Mesa, chat, quality gate e jobs;
- os fluxos HTTP/UI entram depois, em cima de contrato ja estavel.

## Como a Wave 1 encaixa no produto

### Aprovacao da Mesa

Quando um laudo for aprovado, o fluxo passa a poder:

1. congelar `laudo_output_snapshot`;
2. armazenar manifesto de evidencias aceitas;
3. registrar resumo de resolucao da Mesa;
4. associar tags tecnicas validadas.

### Controle operacional

Durante preenchimento, quality gate ou Mesa, o fluxo passa a poder:

1. registrar sinal operacional;
2. atualizar a validacao da evidencia;
3. abrir irregularidade real;
4. resolver a irregularidade com modo de resolucao auditavel.

### Leitura inicial por familia

O produto passa a poder montar um resumo por `tenant + family_key` com:

- quantidade de snapshots aprovados;
- quantidade de eventos operacionais;
- quantidade de evidencias validadas como `ok`;
- quantidade de irregularidades ainda abertas;
- tipos de evento mais frequentes;
- irregularidades abertas mais frequentes.

Isto ainda nao e o `family_memory_index` final, mas ja e a base real para construi-lo.

## Decisoes de projeto desta onda

### 1. `family_key` derivado do laudo

A Wave 1 deriva `family_key` a partir de:

- `laudo.catalog_family_key`
- fallback para `laudo.tipo_template`

Isso permite iniciar a memoria sem travar em todos os legados.

### 2. Eventos e irregularidades sao diferentes

- `OperationalEvent` e trilha de fato operacional.
- `OperationalIrregularity` e o caso confirmado que exige refacao, resolucao ou descarte.

Nem todo evento vira irregularidade.

### 3. Validacao de evidencia tem linha propria

`EvidenceValidation` nao fica diluida no evento porque ela precisa sustentar:

- coverage map;
- estado atual por evidencia;
- scores;
- status operacional;
- status da Mesa;
- substituicao de evidencia.

### 4. `family_memory_index` ficou fora desta onda

O resumo por familia nesta onda e calculado a partir das tabelas-base.

Materializacao/cache/index consolidado ficam para a proxima onda, quando houver:

- mais volume;
- heuristica de distilacao;
- refresh policy clara.

## Fora do escopo nesta onda

- UI final de coverage map
- UI final de revisao por bloco
- estado canonico completo `refazer_inspetor` na maquina de estados do laudo
- promotion desk
- embeddings, clustering semantico ou CV avancado
- ingestao automatica de imagens pela camera/mobile
- endpoints publicos finais

## Proximo passo tecnico natural

Depois desta Wave 1, a proxima onda mais coerente e:

1. ligar `registrar_validacao_evidencia` ao quality gate;
2. ligar `abrir_irregularidade_operacional` ao fluxo `refazer_inspetor`;
3. ligar `registrar_snapshot_aprovado` ao aceite final da Mesa;
4. expor um primeiro `coverage map` e um primeiro painel de resumo por familia.
