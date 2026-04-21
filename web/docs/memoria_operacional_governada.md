# Memoria Operacional Governada

Documento de direcao para o Tariel evoluir de uma base generica inicial para uma base operacional forte, enriquecida pelo uso real e validada pela Mesa.

Para o recorte de priorizacao, valor premium e ondas de implementacao, ver tambem:

- `web/docs/roadmap_premium_memoria_operacional.md`
- `web/docs/wave_1_memoria_operacional_governada.md`
- `web/docs/mobile_review_operating_model.md`

## Objetivo

Permitir que o produto:

- nasca com uma base generica, governada e funcional por familia;
- detecte erro operacional do inspetor antes da aprovacao final;
- aprenda com o dia a dia da operacao;
- enriqueca chat, previa de laudo e geracao futura sem depender de autoaprendizado solto;
- promova apenas o que foi validado para a memoria de conteudo;
- mantenha promocao governada para qualquer mudanca estrutural de familia, overlay ou politica de evidencia.

## Invariantes

Nada neste documento quebra o pipeline canonico:

`family_schema -> master template -> family overlay -> laudo_output -> renderer -> PDF`

Regras que continuam fechadas:

- `laudo_output` continua sendo a fonte de verdade do caso;
- `PDF` continua sendo saida e nao memoria primaria;
- `Mesa` continua sendo revisao e aprovacao;
- cliente final nao recebe editor estrutural livre;
- o sistema nao aprende a partir de rascunho cru como se fosse verdade;
- mudanca oficial de familia ou overlay continua dependendo de promocao governada.

## Tese central

O Tariel precisa operar com duas memorias diferentes:

### 1. Memoria de conteudo aprovado

Serve para fortalecer:

- a previa mostrada para a Mesa;
- o chat contextual;
- a geracao dos proximos laudos;
- a linguagem tecnica por familia;
- o mapa de evidencias e achados recorrentes.

Esta memoria so pode receber material aprovado pela Mesa.

### 2. Memoria de controle operacional

Serve para detectar e prevenir erro operacional do inspetor.

Exemplos:

- foto borrada;
- foto escura ou cortada;
- foto que nao condiz com o ativo ou com a familia;
- foto duplicada;
- angulo obrigatorio faltando;
- imagem que contradiz o preenchimento;
- nao conformidade alegada sem evidencia suficiente;
- evidencia visual incoerente com a conclusao proposta.

Esta memoria pode aprender tambem com casos `refazer`, rejeicoes operacionais e correcao posterior do caso.

Regra critica:

- erro operacional confirmado melhora a fiscalizacao operacional;
- caso aprovado melhora a memoria de conteudo;
- uma base nao substitui a outra.

## Base inicial do produto

O produto nao deve esperar milhares de casos para comecar.

Ele nasce com uma base generica inicial por familia, derivada de:

- `family_schema`;
- `master template`;
- `family overlay`;
- politica minima de evidencia;
- linguagem tecnica base;
- red flags genericas;
- referencias sinteticas ou referencias curadas quando existirem.

Essa base inicial deve ser suficientemente boa para:

- orientar o preenchimento;
- gerar rascunho funcional;
- pedir evidencias minimas;
- montar previa revisavel pela Mesa.

O que falta nessa largada e preenchido pelo uso real e validado.

## Ciclo operacional desejado

1. O Tariel abre o caso usando a base generica da familia.
2. O inspetor preenche dados, envia fotos e anexa documentos.
3. A IA faz analise operacional do caso e da evidencia antes da Mesa.
4. Se houver irregularidade operacional, o caso ou bloco vai para `refazer_inspetor`.
5. O inspetor corrige o caso e reenvia.
6. O sistema gera a previa enriquecida para a Mesa.
7. A Mesa aprova, ajusta por bloco ou devolve.
8. Se aprovado, nasce um `approved_case_snapshot`.
9. O snapshot entra na memoria de conteudo aprovado.
10. Eventos de erro operacional entram na memoria de controle operacional.
11. Jobs de distilacao consolidam repeticao, novidade e padroes recorrentes.
12. A curadoria pode promover candidatos para regra oficial da familia.

## Estados recomendados

Estados de caso:

- `draft_inspetor`
- `em_analise_operacional`
- `refazer_inspetor`
- `pronto_para_mesa`
- `em_revisao_mesa`
- `ajustar_por_bloco`
- `aprovado_mesa`
- `rejeitado_mesa`
- `emitido`

Estados de evidencia:

- `capturada`
- `validacao_operacional_pendente`
- `operacional_ok`
- `operacional_irregular`
- `substituida`
- `aceita_mesa`
- `rejeitada_mesa`

## Entidades principais

### `approved_case_snapshot`

Fotografia canonica do caso aprovado.

Campos centrais:

- `family_key`
- `tenant_id`
- `case_id`
- `approved_at`
- `approval_version`
- `laudo_output_snapshot`
- `evidence_manifest`
- `mesa_resolution_summary`
- `document_outcome`
- `technical_tags`

Regra:

- este objeto pode alimentar chat, previa e geracao futura.

### `operational_event`

Evento auditavel do dia a dia.

Tipos esperados:

- `image_blurry`
- `image_dark`
- `image_duplicate`
- `image_family_mismatch`
- `image_asset_mismatch`
- `required_angle_missing`
- `evidence_conclusion_conflict`
- `document_missing`
- `field_reopened`
- `block_returned_to_inspector`

Regra:

- este objeto melhora a deteccao operacional;
- sozinho ele nao entra na memoria de conteudo aprovado.

### `evidence_validation`

Resultado da leitura operacional e da leitura da Mesa sobre cada evidencia.

Campos centrais:

- `evidence_id`
- `family_key`
- `component_type`
- `view_angle`
- `quality_score`
- `coherence_score`
- `operational_status`
- `mesa_status`
- `failure_reasons`
- `replacement_evidence_id`

### `operational_irregularity`

Irregularidade confirmada que exige refacao pelo inspetor.

Campos centrais:

- `case_id`
- `block_id`
- `evidence_id`
- `irregularity_type`
- `severity`
- `detected_by`
- `detected_at`
- `resolved_at`
- `resolution_mode`

### `image_reference_unit`

Unidade reaproveitavel de aprendizado visual.

Campos centrais:

- `family_key`
- `component_type`
- `view_angle`
- `condition_label`
- `defect_type`
- `approval_count`
- `rejection_count`
- `novelty_score`
- `quality_band`

Regra:

- so exemplos aprovados podem alimentar recuperacao visual futura;
- rejeicoes alimentam apenas politicas de controle.

### `family_memory_index`

Indice consolidado por familia usado por chat, previa e geracao.

Blocos esperados:

- texto tecnico recorrente validado;
- achados recorrentes;
- evidencias obrigatorias mais frequentes;
- imagens aprovadas por componente e angulo;
- conflitos operacionais frequentes;
- bloqueios comuns da Mesa;
- red flags observadas em campo;
- recomendacoes de reinspecao e proximos passos.

### `enrichment_candidate`

Sugestao derivada da operacao que ainda nao virou regra oficial.

Tipos:

- `suggested_overlay_text`
- `suggested_required_angle`
- `suggested_evidence_rule`
- `suggested_red_flag`
- `suggested_checklist_item`
- `suggested_conclusion_pattern`

### `promotion_decision`

Decisao humana sobre candidato de enriquecimento.

Estados:

- `pending_curadoria`
- `approved_for_runtime`
- `approved_for_family_rule`
- `rejected`
- `superseded`

## Regra do que entra em cada base

### Entra na memoria de conteudo aprovado

- `laudo_output` aprovado;
- evidencias aceitas pela Mesa;
- blocos aprovados;
- comentarios e sintese consolidados da Mesa;
- conclusao final validada;
- ligacao entre evidencia, achado e conclusao;
- linguagem recorrente aprovada.

### Nao entra na memoria de conteudo aprovado

- rascunho cru do inspetor;
- texto ainda nao aprovado;
- PDF como fonte primaria;
- evidencia operacionalmente invalida;
- item rejeitado pela Mesa;
- dado sensivel sem sanitizacao adequada.

### Entra na memoria de controle operacional

- reaberturas por evidencia fraca;
- fotos substituidas;
- conflitos entre imagem e preenchimento;
- erros recorrentes do inspetor;
- faltas de angulo;
- problemas de qualidade de imagem;
- inconsistencias entre ativo, placa, local e familia.

## Deduplicacao e novidade

Quando a base chegar a centenas ou milhares de casos, ela nao deve acumular repeticao bruta.

O sistema precisa consolidar:

- repeticao exata em frequencia;
- repeticao semantica em cluster;
- novidade aprovada em `novelty candidate`;
- imagem nova em componente/angulo/defeito novo;
- mesma imagem de referencia repetida em reforco estatistico, nao duplicata literal.

Campos uteis para consolidacao:

- `frequency`
- `confidence`
- `novelty_score`
- `approval_count`
- `reopen_count`
- `family_key`
- `component_type`
- `view_angle`
- `defect_type`
- `status_final`

## Uso pela Mesa

Antes da aprovacao, a Mesa deve ver uma previa enriquecida com base na memoria validada.

Essa previa pode mostrar:

- blocos sugeridos com base em casos similares aprovados;
- evidencias esperadas para a familia;
- angulos faltantes;
- achados recorrentes semelhantes;
- conflitos operacionais detectados;
- linguagem tecnica ja validada;
- o que parece padrao e o que parece novidade.

Se a Mesa aprovar:

- o caso entra na memoria de conteudo aprovado.

Se a Mesa devolver ou o sistema marcar `refazer_inspetor`:

- o erro operacional alimenta a memoria de controle operacional;
- o conteudo do caso nao entra como base aprovada.

## Uso pela IA do chat e pela geracao

### Chat

O chat deve consultar primeiro:

- base generica da familia;
- memoria de conteudo aprovado da mesma familia;
- memoria de controle operacional para alertar risco de preenchimento;
- exemplos visuais aprovados e red flags recorrentes.

### Geracao de laudo

A geracao deve usar:

- estrutura oficial da familia;
- evidencias do caso atual;
- padroes aprovados de linguagem;
- ligacoes validadas entre achado, evidencia e conclusao;
- alertas de irregularidade operacional antes da submissao a Mesa.

Regra:

- memoria ajuda a gerar melhor;
- memoria nao autoriza conclusao sem evidencia do caso atual.

## Impacto no fluxo atual de referencias sinteticas

O fluxo atual de pedir ao ChatGPT um pacote externo com:

- `manifest.json`
- `tariel_filled_reference_bundle.json`
- `PDF`
- `ZIP`

foi util como bootstrap.

No futuro desejado:

- o pacote continua existindo como envelope canonico;
- mas ele passa a ser gerado internamente pelo Tariel na maioria dos casos;
- o ChatGPT externo vira excecao, fallback ou acelerador de familias ainda sem massa critica.

## Ondas recomendadas de implementacao

### Onda 1. Memoria operacional minima

- persistir `approved_case_snapshot`;
- persistir `operational_event`;
- persistir `evidence_validation`;
- marcar `refazer_inspetor` por evidencia irregular;
- exibir alertas operacionais na previa.

### Onda 2. Distilacao e recuperacao

- consolidar `family_memory_index`;
- deduplicar padroes repetidos;
- classificar novidade;
- recuperar referencias aprovadas por familia, componente e angulo;
- alimentar chat e previa da Mesa.

### Onda 3. Promocao governada

- gerar `enrichment_candidate`;
- abrir fila de curadoria;
- permitir promocao para overlay, checklist, red flag e politica de evidencia;
- manter auditoria de promocao por familia e versao.

## Regra final

O Tariel nao deve ser um sistema que "aprende com qualquer coisa".

Ele deve:

- comecar com base generica forte;
- usar o dia a dia para detectar erro operacional;
- aprender com o que a Mesa aprova;
- consolidar repeticao e novidade;
- promover mudancas estruturais apenas com governanca.

Essa e a linha correta para tornar o produto mais forte a cada operacao sem perder controle tecnico.
