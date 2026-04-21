# Direcao de Produto para Laudos

Documento curto que consolida a linha de raciocinio amadurecida nos estudos de produto sobre laudos, Mesa e catalogo.

Ele registra direcao de produto e governanca. Nao descreve o estado atual completo do codigo. Para isso, usar:

- `web/docs/CANONICAL_SYSTEM.md`
- `web/docs/mesa_avaliadora.md`
- `web/docs/preenchimento_laudos_canonico.md`
- `docs/backlog_evolucao_produto_governado.md` para evolucao recomendada ainda nao transformada em contrato oficial

## Objetivo

Definir o modelo de produto para:

- familias tecnicas;
- templates coringas;
- templates customizados;
- liberacao por tenant;
- papel da IA;
- papel da Mesa.

## Vocabulario canonico

- `NR`: macrocategoria regulatoria. Nao e a unidade final de produto.
- `familia`: unidade vendavel e operacional do catalogo.
- `family_schema`: contrato tecnico da familia.
- `template_master`: template vazio oficial que materializa a familia.
- `filled_reference`: laudo real preenchido usado como referencia de engenharia.
- `laudo_output`: JSON final do caso revisado pela Mesa.
- `theme_pack`: variante visual controlada, sem alterar estrutura tecnica.

## Decisoes fechadas

- O cliente nao cria template tecnico nem checklist estrutural do zero.
- Tariel controla `family_schema`, `template_master`, `theme_packs` e templates customizados.
- O cliente escolhe apenas entre familias e templates liberados para o tenant.
- Branding do cliente deve ficar restrito a logo, dados institucionais e `theme_pack` permitido.
- A unidade real de produto e a `familia`, nao uma NR generica.
- A IA deve atuar como `draft engine`.
- A Mesa deve atuar como revisao e aprovacao, nao como autoria livre do laudo.
- Template customizado deve ser fluxo admin-only e tratado como servico controlado pela Tariel.
- `theme_packs` sao preferiveis a estilo livre por cliente.

## Regra de catalogo

O catalogo oficial pertence a Tariel.

Cada tenant recebe apenas um subconjunto dele:

- familias habilitadas;
- templates habilitados;
- estilos visuais habilitados;
- templates customizados opcionais.

## Estrutura correta do produto

O produto deve separar quatro camadas:

1. `family_schema`
2. `template_master`
3. `laudo_output`
4. `renderer`

`filled_reference` entra como apoio de engenharia para descobrir bindings, slots e variacoes reais da familia.

## Regra de modelagem

A modelagem correta deve seguir:

- NR como macrocategoria;
- familia como produto vendavel;
- template como materializacao visual.

Exemplos melhores:

- `nr35_inspecao_linha_de_vida`
- `nr12_maquinas`
- `nr13_inspecao_caldeira`
- `nr13_inspecao_vaso_pressao`

## Priorizacao recomendada

### Nucleo de plataforma

As primeiras familias fortes do produto devem ser poucas e bem resolvidas:

1. `nr35_inspecao_linha_de_vida`
2. `nr12_maquinas`
3. `nr13_inspecao_caldeira`
4. `nr13_inspecao_vaso_pressao`
5. `nr10_rti_eletrica`
6. `spda_inspecao`

### Piloto de negocio atual

Para a empresa de teste ja discutida, a validacao de negocio deve partir de `NR13`.

Primeiras familias do piloto:

1. `nr13_inspecao_caldeira`
2. `nr13_inspecao_vaso_pressao`
3. depois `nr13_inspecao_tubulacao`

Isso nao substitui o nucleo de plataforma; apenas reconhece que o piloto comercial atual e mais aderente a `NR13`.

## O que nao deve entrar como foco inicial

- cobrir todas as NRs vigentes de uma vez;
- entregar editor estrutural self-service para cliente final;
- tratar toda `NR13` ou toda `NR35` como um unico laudo generico;
- misturar regra tecnica com branding visual;
- depender de template customizado para o produto parecer pronto.

## Hipoteses em aberto

Ainda precisam de confirmacao operacional:

1. minimo duro e recomendado de fotos por familia;
2. grau de edicao manual que a Mesa pode manter depois do draft da IA;
3. familias que entram no primeiro pacote comercial fechado;
4. quantidade de `theme_packs` que vale oferecer no lancamento;
5. campos que podem aceitar override auditado da Mesa sem quebrar a familia.

## Regra de documentacao e rollout

Uma familia so deve ser tratada como oficial quando existir no codigo, com pelo menos:

- normalizacao de `tipo_template` ou equivalente;
- gate compativel;
- binding de template;
- caminho claro de revisao pela Mesa.

Sem isso, a familia continua sendo direcao de produto, nao capacidade implementada.
