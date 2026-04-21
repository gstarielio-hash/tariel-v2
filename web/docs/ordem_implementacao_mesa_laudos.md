# Ordem de Implementacao da Mesa e dos Laudos

Documento curto para orientar a sequencia correta de trabalho entre Mesa, familias e templates.

## Objetivo

Evitar aprofundar a frente documental em cima de um fluxo operacional ainda frouxo.

## Regra principal

Antes de aprofundar `template_master`, `family_schema` e renderizacao final, a Mesa deve ficar estruturalmente correta.

Motivo:

- a Mesa define a revisao;
- a Mesa define a aceitacao da evidencia;
- a Mesa define o que bloqueia emissao;
- sem isso, o contrato do `laudo_output` fica instavel.

## Leitura do estado atual

Hoje ja existe base util para laudos:

- importacao de DOCX vazio para `editor_rico`;
- fundacao de `filled_reference`;
- pacote da Mesa;
- policy/document facade incremental no V2.

Mas a Mesa ainda esta muito apoiada em:

- mensagem livre;
- anexo livre;
- pendencia inferida por mensagem humana;
- contagem heuristica de evidencia.

## Ordem recomendada

### Fase 1. Reestruturar o contrato da Mesa

Entregar:

- pendencia estruturada;
- estado de evidencia;
- `family_key` por caso;
- `family_lock`;
- `scope_mismatch`;
- override auditado;
- bloco claro de itens bloqueantes.

### Fase 2. Reestruturar o pacote e a UX da Mesa

Entregar:

- pacote canonicamente orientado a pendencias;
- resumo "o que falta para aprovar";
- evidencias vinculadas a pendencia e slot;
- diferenciacao entre chat livre e evidencia elegivel;
- fila da Mesa orientada por bloqueio, prioridade e status.

### Fase 3. Fechar o contrato da familia

Entregar:

- registry de familias reais;
- `family_schema` por familia;
- politica de evidencia e fotos por familia;
- campos criticos, grupos de checklist e conclusao por familia.

### Fase 4. Retomar templates e referencias

Entregar:

- `template_master` vazio por familia;
- ligacao entre `template_master` e `filled_reference`;
- seed estrutural por familia;
- `laudo_output` canonico;
- renderer final mais uniforme.

## O que fica preservado

Nada do trabalho recente precisa ser descartado.

Mantem valor:

- `filled_reference`;
- importacao de DOCX vazio;
- biblioteca de templates;
- `editor_rico`;
- contrato incremental do V2.

Esses itens deixam de ser a frente principal e passam a ser fundacao para a fase documental posterior.

## O que nao fazer

- nao expandir familias so porque existe um DOCX vazio;
- nao tratar chat como contrato principal de revisao;
- nao adotar minimo global de fotos sem politica por familia;
- nao deixar template definir regra tecnica;
- nao fechar `family_schema` antes de estabilizar a revisao da Mesa.

## Critério de pronto para voltar aos templates

A frente documental volta a ser prioridade quando o caso ja tiver:

- familia principal estavel;
- pendencia estruturada;
- evidencia com estado;
- bloqueios documentais claros;
- override auditado;
- pacote da Mesa orientado por esses conceitos.
