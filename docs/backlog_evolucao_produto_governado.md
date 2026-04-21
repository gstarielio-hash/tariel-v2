# Backlog de Evolucao do Produto Governado

Este arquivo transforma as ideias adicionais de `docs/TARIEL_CONTEXT.md` em backlog tecnico priorizado e acionavel.

Ele nao substitui o contrato oficial do produto. Ele registra evolucao recomendada.

## Fontes de verdade antes deste backlog

Antes de abrir qualquer item abaixo, alinhar decisao com estes artefatos:

- `web/docs/catalog_document_contract.md`
- `web/docs/preenchimento_laudos_canonico.md`
- `docs/direcao_produto_laudos.md`
- `docs/nr_programming_registry.json`
- `docs/master_templates/library_registry.json`
- documentos de homologacao das ondas

## Invariantes que este backlog nao pode quebrar

- `family_schema -> master template -> family overlay -> laudo_output -> renderer -> PDF` continua sendo o pipeline canonico.
- `laudo_output` continua sendo a fonte de verdade do documento emitido.
- `Mesa` continua sendo revisao e aprovacao, nao autoria livre do laudo.
- cliente final nao ganha editor estrutural livre de template tecnico.
- catalogo continua governado por Tariel, com liberacao controlada por tenant.
- branding visual nao pode se misturar com regra tecnica da familia.

## Pre-condicao ativa do repositorio

Antes de abrir frentes grandes de produto, a baseline de engenharia precisa voltar ao verde.

Estado validado em `2026-04-10`:

- `make hygiene-check`: verde
- `make mesa-smoke`: verde
- `make mobile-ci`: verde
- `make web-lint`: verde
- `make web-test`: verde
- `make verify`: verde

Leitura pratica:

- o `P0` de estabilizacao de baseline web foi fechado;
- os itens `P1` ja podem ser especificados e implementados sem abrir nova frente de arquitetura;
- a regra passa a ser manter `make verify` e `make web-test` verdes enquanto as frentes de produto avancam.

## Ordem recomendada do backlog

| Ordem | Item | Prioridade | Camada principal | Dependencias mais fortes |
| --- | --- | --- | --- | --- |
| 0 | Estabilizacao de baseline web | `P0` | plataforma | nenhuma |
| 1 | QR Code ou hash publico de verificacao | `P1` | emissao e confianca documental | baseline minimamente estavel |
| 2 | `coverage map` de evidencia | `P1` | hard gate e UX operacional | contratos de evidencia por familia |
| 3 | revisao por bloco | `P1` | Mesa e governanca documental | seccionamento estavel do documento |
| 4 | `clone from last inspection` | `P1` | operacao do inspetor | snapshots confiaveis do caso anterior |
| 5 | `entitlements` por contrato | `P1` | comercial e governanca SaaS | catalogo governado por tenant |
| 6 | `red flags` por familia | `P2` | gate e risco tecnico | coverage map + revisao por bloco |
| 7 | diff entre emissoes | `P2` | rastreabilidade e auditoria | revisao por bloco + versionamento |
| 8 | signatarios governados | `P2` | emissao e responsabilidade tecnica | catalogo de familias + tenant policy |
| 9 | `release channels` do catalogo | `P2` | rollout de produto | catalogo governado + entitlements |
| 10 | `tenant policy profile` | `P2` | governanca por tenant | entitlements + red flags |
| 11 | `renewal engine` | `P3` | recorrencia operacional | datas e validade por familia |
| 12 | `anexo pack` automatico | `P3` | materializacao documental | emissao estavel + manifestos de anexo |
| 13 | `fit score` de familia e variante | `P3` | triagem e assistencia | coverage map + vocabulario controlado |
| 14 | biblioteca de linguagem por setor | `P3` | qualidade comercial do texto | familias maduras + variantes |
| 15 | pacotes comerciais | `P3` | go-to-market | entitlements + release channels |

## P0 - Estabilizacao de baseline web

Este nao e um item de produto novo. E o pre-requisito de engenharia com maior retorno imediato.

Escopo minimo:

- neutralizar `rate limit` em ambiente de teste web;
- recuperar `make verify`;
- recuperar `make web-test`;
- manter `mesa-smoke` e `mobile-ci` verdes;
- so depois abrir frentes largas de UX e governanca adicional.

## P1 - Itens de maior retorno

### 1. QR Code ou hash publico de verificacao

Objetivo:

- aumentar autenticidade documental;
- permitir verificacao externa controlada;
- fortalecer confianca comercial do PDF emitido.

Corte tecnico minimo:

- gerar `document_public_id` imutavel por emissao;
- gerar `verification_hash` derivado do `laudo_output`, fingerprint do template e metadados de emissao;
- incluir QR Code ou hash no rodape do PDF;
- expor endpoint publico somente leitura para conferenca;
- registrar verificacao na trilha de auditoria.

Camadas tocadas:

- contrato de emissao;
- renderer PDF;
- storage de emissao;
- pagina publica de verificacao;
- auditoria.

Fora do corte inicial:

- assinatura digital ICP;
- validacao criptografica pesada com cadeia externa.

### 2. `coverage map` de evidencia

Objetivo:

- deixar visivel o que a familia exige;
- mostrar o que foi coletado, aceito e rejeitado;
- reduzir emissao com lacuna escondida.

Corte tecnico minimo:

- declarar requisitos minimos e recomendados de evidencia por familia;
- calcular `coverage_snapshot` antes da emissao;
- exibir mapa simples para `Inspetor` e `Mesa`;
- usar o snapshot no hard gate;
- registrar override auditado quando houver excecao permitida.

Camadas tocadas:

- `family_schema`;
- gates de emissao;
- workspace do inspetor;
- painel da Mesa.

Dependencia principal:

- contratos de evidencia da familia precisam estar fechados por familia, nao por NR generica.

### 3. Revisao por bloco

Objetivo:

- permitir revisao objetiva por secao;
- reduzir reabertura total desnecessaria;
- melhorar diffs e comentarios da Mesa.

Corte tecnico minimo:

- dividir o documento em blocos canonicos: identificacao, metodologia, checklist, evidencias, conclusao e anexos;
- permitir status por bloco: `pendente`, `ajustar`, `aprovado`;
- permitir comentario por bloco;
- permitir reabertura parcial;
- refletir o estado agregado na decisao final da Mesa.

Camadas tocadas:

- contrato documental;
- `laudo_output`;
- UX da Mesa;
- auditoria de revisao.

Dependencia principal:

- o renderer e o catalogo precisam ter seccionamento estavel por familia.

### 4. `clone from last inspection`

Objetivo:

- acelerar casos periodicos;
- reaproveitar estrutura do caso anterior sem falsificar evidencia nova;
- reduzir retrabalho em identificacao do ativo.

Corte tecnico minimo:

- criar caso novo a partir da ultima inspecao da mesma familia e mesmo ativo;
- copiar apenas dados estaveis: identificacao, referencias recorrentes, anexos reutilizaveis marcados como historicos;
- bloquear reaproveitamento silencioso de conclusao e evidencias anteriores;
- marcar cada campo herdado como `revalidar`.

Camadas tocadas:

- abertura de caso;
- historico de inspecoes;
- UX do inspetor;
- auditoria de origem do dado.

Dependencia principal:

- chave estavel de ativo e ligacao confiavel entre emissoes anteriores.

### 5. `entitlements` por contrato

Objetivo:

- governar uso comercial real do tenant;
- diferenciar planos e bundles;
- limitar emissoes, usuarios e recursos premium sem hacks paralelos.

Corte tecnico minimo:

- modelo de contrato com quotas por tenant;
- quotas por papel de usuario;
- limite de emissoes;
- habilitacao de familias, variantes premium e recursos avancados;
- telemetria de consumo contratual.

Camadas tocadas:

- admin geral;
- catalogo por tenant;
- criacao de usuarios;
- emissao documental;
- billing futuro.

Fora do corte inicial:

- precificacao automatica;
- faturamento completo.

## P2 - Governanca e rastreabilidade

### 6. `red flags` por familia

Uso recomendado:

- impedir aprovacao simplificada quando houver combinacao de risco forte;
- forcar revisao humana mais rigida em familias criticas;
- restringir certos resultados finais em cenarios normativos graves.

Exemplos:

- `NR35` com nao conformidade critica;
- `NR13` com ausencia documental grave;
- documento controlado por permissao sem autorizacao valida.

### 7. Diff entre emissoes

Uso recomendado:

- mostrar mudanca entre revisoes emitidas;
- diferenciar alteracao de `laudo_output`, conclusao e materializacao visual;
- ampliar valor auditavel da Mesa.

Dependencia principal:

- versionamento de secao e snapshot de emissao.

### 8. Signatarios governados

Uso recomendado:

- manter cadastro de signatarios autorizados por tenant e familia;
- validar compatibilidade entre familia, funcao e registro profissional;
- evitar emissao com assinante incorreto ou vencido.

### 9. `release channels` do catalogo

Uso recomendado:

- liberar familias, variantes e templates em `pilot`, `limited_release` e `general_release`;
- fazer rollout progressivo com rollback mais seguro;
- separar produto maduro de ativo experimental.

### 10. `tenant policy profile`

Uso recomendado:

- endurecer ou aliviar exigencias por tenant, sempre sob governanca Tariel;
- configurar evidencia minima, review rigido, override e anexos obrigatorios;
- criar operacao empresarial sem quebrar o contrato da familia.

## P3 - Efetividade operacional, linguagem e comercial

### 11. `renewal engine`

Uso recomendado:

- gerar fila de renovacao a partir de validade ou proxima inspecao;
- produzir alerta operacional e oportunidade comercial;
- manter acompanhamento por ativo e familia.

### 12. `anexo pack` automatico

Uso recomendado:

- gerar pacote final com PDF principal, ART/RRT, certificados, fotos numeradas e documentos-base;
- padronizar entrega para cliente e auditoria;
- reduzir montagem manual externa.

### 13. `fit score` de familia e variante

Uso recomendado:

- priorizar triagem da Mesa;
- detectar mismatch entre caso, familia e variante;
- registrar discrepancia como alerta auditavel.

Dependencia principal:

- `coverage map`, vocabulario controlado e identificacao tecnica do objeto.

### 14. Biblioteca de linguagem por setor

Uso recomendado:

- adaptar vocabulario final por segmento sem mexer na estrutura tecnica;
- manter coerencia comercial em alimentos, mineracao, naval, saude, rural e oleo e gas;
- melhorar a percepcao de laudo premium.

### 15. Pacotes comerciais

Uso recomendado:

- vender bundles governados de familias e variantes;
- combinar catalogo, entitlements e canais de release;
- criar oferta comercial sem multiplicar configuracoes ad hoc.

Exemplos:

- `NR13 Core`
- `NR35 Altura`
- `Industrial Safety Pack`
- `Programas Legais SST`

## Sequencia tecnica recomendada

Se a equipe precisar escolher uma trilha unica, seguir nesta ordem:

1. estabilizar baseline web;
2. QR Code ou hash publico de verificacao;
3. `coverage map` de evidencia;
4. revisao por bloco;
5. `clone from last inspection`;
6. `entitlements` por contrato;
7. `red flags` por familia;
8. diff entre emissoes;
9. signatarios governados;
10. `release channels` e `tenant policy profile`;
11. `renewal engine`, `anexo pack`, `fit score`, linguagem por setor e pacotes comerciais.

## Regra de implementacao

Cada item deste backlog so deve subir para contrato oficial quando existir, ao mesmo tempo:

- documento canonico atualizado;
- cobertura de teste;
- gate compativel;
- impacto claro por papel: `Admin-CEO`, `Admin Cliente`, `Mesa` e `Inspetor`;
- trilha de auditoria coerente.

Sem isso, o item continua sendo backlog recomendado, nao capacidade oficial do produto.
