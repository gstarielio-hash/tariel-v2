# Portfolio Empresa NR13

Documento curto para orientar a linha de execucao dos laudos e documentos de uma empresa cuja oferta real esta concentrada em NR13.

## Decisao principal

Nao vamos mais priorizar familias isoladas sem contexto comercial.

A unidade de execucao agora passa a ser:

- a carteira real de entregaveis da empresa;
- agrupada por linha tecnica;
- com prioridade operacional e comercial.

## Regra de modelagem

Nem todo item do portfolio da empresa vira uma familia principal da Mesa.

Separacao correta:

- `familia principal`: quando o produto final e um laudo ou documento tecnico principal;
- `modo de caso`: quando a variacao muda o contexto, mas nao precisa virar familia separada;
- `modulo de apoio`: quando o item funciona como ensaio, anexo tecnico ou evidencia complementar;
- `trilha documental`: quando o output principal e prontuario, livro, fluxograma ou pacote documental;
- `trilha de projeto`: quando o output principal e projeto, calculo ou aprovacao tecnica;
- `trilha de treinamento`: quando o output principal nao e laudo de inspecao.

## Regra pratica desta empresa

Para esta empresa:

- `inicial`, `periodica` e `extraordinaria` devem entrar primeiro como `modo_de_inspecao`, nao como familias separadas;
- `caldeira`, `vaso de pressao` e `tubulacao` continuam sendo familias principais porque o ativo muda;
- tecnicas de END entram primeiro como modulos de apoio, nao como familias principais vendidas isoladamente;
- calculos, projeto de instalacao, PAR e prontuario nao devem ser empurrados para a mesma familia de inspecao.

## Mapa do portfolio

### Linha 1. Inspecao e integridade

Estes sao os produtos nucleares da empresa e devem ser a frente principal da Tariel para esse caso.

1. `nr13_inspecao_caldeira`
   Campo recomendado:
   `modo_de_inspecao = inicial | periodica | extraordinaria`
   Campo recomendado:
   `escopo_avaliacao = seguranca | integridade`

2. `nr13_inspecao_vaso_pressao`
   Campo recomendado:
   `modo_de_inspecao = inicial | periodica | extraordinaria`

3. `nr13_inspecao_tubulacao`
   Campo recomendado:
   `modo_de_inspecao = inicial | periodica | extraordinaria`

Observacao:

- se `integridade caldeira` passar a exigir documento estruturalmente diferente do laudo de seguranca, essa variacao pode ser extraida depois como `nr13_integridade_caldeira`.

### Linha 2. Testes e validacoes

Estes itens sao produtos fortes da empresa, mas devem ficar separados das familias principais de inspecao.

4. `nr13_teste_hidrostatico`
   Campo recomendado:
   `ativo_tipo = caldeira | vaso_pressao | tubulacao`

5. `nr13_teste_estanqueidade_tubulacao_gas`

### Linha 3. Documentacao obrigatoria e organizacao tecnica

Esses entregaveis sao documentais, nao laudos de inspecao classicos.

6. `nr13_reconstituicao_prontuario`

7. `nr13_abertura_livro_registro_seguranca`

8. `nr13_levantamento_in_loco_equipamentos`

9. `nr13_fluxograma_linhas_acessorios`

10. `nr13_adequacao_planta_industrial`

### Linha 4. Projeto, alteracao e calculo

Esses entregaveis devem virar trilha propria, com estrutura diferente da Mesa de inspecao.

11. `nr13_projeto_instalacao`

12. `nr13_par_projeto_alteracao_reparo`

13. `nr13_calculo_pmta_vaso_pressao`

14. `nr13_calculo_espessura_minima_caldeira`

15. `nr13_calculo_espessura_minima_vaso_pressao`

16. `nr13_calculo_espessura_minima_tubulacao`

### Linha 5. Treinamento

Esses itens nao devem entrar agora como familia principal da Mesa.

17. `nr13_treinamento_operacao_caldeira`

18. `nr13_treinamento_operacao_unidades_processo`

## Modulos de apoio END

As tecnicas abaixo devem existir como modulos reutilizaveis e anexaveis a caldeira, vaso, tubulacao e testes:

- `end_medicao_espessura_ultrassom`
- `end_ultrassom_junta_soldada`
- `end_liquido_penetrante`
- `end_particula_magnetica`
- `end_visual_solda`

Esses modulos podem alimentar:

- evidencia estruturada;
- anexos do laudo principal;
- conclusao tecnica;
- documento complementar separado, quando o cliente contratar isso como entrega especifica.

## Ordem de execucao recomendada

### Onda 1. Operacao principal imediata

- `nr13_inspecao_caldeira`
- `nr13_inspecao_vaso_pressao`
- `nr13_inspecao_tubulacao`
- `nr13_teste_hidrostatico`
- `nr13_teste_estanqueidade_tubulacao_gas`

### Onda 2. Pacote documental NR13

- `nr13_reconstituicao_prontuario`
- `nr13_abertura_livro_registro_seguranca`
- `nr13_levantamento_in_loco_equipamentos`
- `nr13_fluxograma_linhas_acessorios`

### Onda 3. Engenharia e calculo

- `nr13_projeto_instalacao`
- `nr13_par_projeto_alteracao_reparo`
- `nr13_calculo_pmta_vaso_pressao`
- `nr13_calculo_espessura_minima_caldeira`
- `nr13_calculo_espessura_minima_vaso_pressao`
- `nr13_calculo_espessura_minima_tubulacao`
- `nr13_adequacao_planta_industrial`

### Onda 4. Treinamento

- `nr13_treinamento_operacao_caldeira`
- `nr13_treinamento_operacao_unidades_processo`

## Estado atual dentro do projeto

Ja temos prontos ou bem encaminhados:

- `nr13_inspecao_vaso_pressao`
- `nr13_inspecao_caldeira`

Faltam como proxima frente direta para essa empresa:

- `nr13_inspecao_tubulacao`
- `nr13_teste_hidrostatico`
- `nr13_teste_estanqueidade_tubulacao_gas`

## Consequencia pratica para a Tariel

Para esta empresa, o backlog nao deve ser montado por NR abstrata.

Deve ser montado por:

1. o que ela vende hoje;
2. o que gera laudo ou documento recorrente;
3. o que mais aproxima a Mesa da operacao real;
4. o que permite reaproveitar modulos entre caldeira, vaso, tubulacao e testes.

## Refino por material real

O proximo passo depois do portfolio canonico e do provisionamento nao e inventar mais familias.

E fechar o material real da empresa por familia:

- modelo atual vazio;
- documentos finais reais;
- evidencias e anexos reais;
- padrao de linguagem tecnica;
- regras comerciais e operacionais.

Workspace oficial para isso:

- `docs/portfolio_empresa_nr13_material_real/`

Base provisoria ja criada:

- `web/docs/portfolio_empresa_nr13_material_sintetico_base.md`
- dentro de cada familia em `docs/portfolio_empresa_nr13_material_real/<family_key>/coleta_entrada/`

Resumo operacional:

- cada familia tem `manifesto_coleta.json`, `briefing_real.md`, `coleta_entrada/` e `pacote_referencia/`;
- o material bruto entra primeiro em `coleta_entrada/`;
- depois ele e consolidado para `filled_reference`;
- so depois o template final da familia deve ser refinado.
