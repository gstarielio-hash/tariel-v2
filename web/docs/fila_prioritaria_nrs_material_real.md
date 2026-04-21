# Fila Prioritaria de NRs: Material Real

## Objetivo

Transformar a cobertura nacional ja provisionada em maturidade premium de verdade, usando material real, pacote de referencia, refinamento de template mestre e linguagem operacional por familia.

## Regra

- cobertura nacional no catalogo nao basta por si so;
- a fila premium precisa priorizar familias criticas, vendaveis e recorrentes;
- o criterio principal de ataque e `criticidade regulatoria + potencial comercial + gap de material real`.

## Snapshot atual

- `38` NRs mapeadas no registro nacional;
- `34` em `implemented_core`;
- `2` revogadas: `NR-2` e `NR-27`;
- `2` como apoio: `NR-3` e `NR-28`;
- workspaces de material real com baseline sintetica externa validada: `14`;
- workspaces de material real ainda em `aguardando_material_real`: `18`.
- a fila critica de `NR13`, `NR12`, `NR20` e `NR33` ja recebeu baseline sintetica interna promovida pela esteira oficial do repositorio.

## Fila de ataque recomendada

### Fase 1: fechar NR13 wave 1

Objetivo: terminar a trilha premium da vertical mais madura e mais critica do repositorio.

Familias imediatas:

- `nr13_inspecao_tubulacao`
- `nr13_integridade_caldeira`
- `nr13_teste_hidrostatico`
- `nr13_teste_estanqueidade_tubulacao_gas`

Estado:

- baseline sintetica interna validada nas `4` familias imediatas;
- workspaces agora prontos para receber material real sem depender de geracao externa manual.

Motivo:

- ja existe portfolio real amplo de NR13;
- ja existem baselines validadas em `nr13_inspecao_caldeira` e `nr13_inspecao_vaso_pressao`;
- fechar a wave 1 de NR13 aumenta a forca do template mestre e das variantes comerciais mais vendaveis.

### Fase 2: consolidar NR12

Portfolio aberto:

- [portfolio_empresa_nr12_material_real.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/docs/portfolio_empresa_nr12_material_real.md)

Familias:

- `nr12_inspecao_maquina_equipamento`
- `nr12_apreciacao_risco_maquina`

Estado:

- baseline sintetica interna validada nas `2` familias do portfolio;
- trilha pronta para pressao de template e overlay assim que chegar acervo do cliente.

Motivo:

- NR12 e critica na wave 1;
- mistura bem inspeção e engenharia de risco;
- deve reforcar `inspection_conformity` e pressionar a evolucao de template mestre tecnico.

### Fase 3: consolidar NR20

Portfolio aberto:

- [portfolio_empresa_nr20_material_real.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/docs/portfolio_empresa_nr20_material_real.md)

Familias:

- `nr20_inspecao_instalacoes_inflamaveis`
- `nr20_prontuario_instalacoes_inflamaveis`

Estado:

- baseline sintetica interna validada nas `2` familias do portfolio;
- pacote de referencia, PDF e assets ja promovidos na workspace.

Motivo:

- alto peso comercial e regulatorio;
- combina documento tecnico de inspeção com documentacao controlada;
- bom candidato para fortalecer anexo pack e prontuario governado.

### Fase 4: consolidar NR33

Portfolio aberto:

- [portfolio_empresa_nr33_material_real.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/web/docs/portfolio_empresa_nr33_material_real.md)

Familias:

- `nr33_avaliacao_espaco_confinado`
- `nr33_permissao_entrada_trabalho`

Estado:

- baseline sintetica interna validada nas `2` familias do portfolio;
- fluxo premium ja preparado para casos bloqueantes e permissao controlada.

Motivo:

- fortalece o eixo de criticidade operacional e permissao controlada;
- conversa diretamente com `red flags`, `review_mode` e fluxo forte de Mesa/mobile;
- ajuda a amadurecer o comportamento premium do produto em casos bloqueantes.

## Portfolios reais ativos no repositorio

- [portfolio_empresa_nr10_material_real/README.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/docs/portfolio_empresa_nr10_material_real/README.md)
- [portfolio_empresa_nr12_material_real/README.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/docs/portfolio_empresa_nr12_material_real/README.md)
- [portfolio_empresa_nr13_material_real/README.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/docs/portfolio_empresa_nr13_material_real/README.md)
- [portfolio_empresa_nr20_material_real/README.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/docs/portfolio_empresa_nr20_material_real/README.md)
- [portfolio_empresa_nr33_material_real/README.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/docs/portfolio_empresa_nr33_material_real/README.md)
- [portfolio_empresa_nr35_material_real/README.md](/home/gabriel/Área%20de%20trabalho/TARIEL/Tariel%20Control%20Consolidado/docs/portfolio_empresa_nr35_material_real/README.md)

## Resultado esperado

Quando essa fila estiver madura:

- as familias criticas da wave 1 deixam de depender de base generica apenas;
- a biblioteca premium de templates passa a ser pressionada por material real recorrente;
- variantes comerciais ganham linguagem e anexos mais fortes;
- Mesa e mobile passam a revisar casos com referencia mais solida por familia.

## Proximo corte operacional

- substituir a baseline sintetica por material real aprovado assim que entrar o primeiro acervo do cliente;
- usar a fila ja aberta no admin para atacar primeiro `NR13`, depois `NR12`, `NR20` e `NR33`;
- promover refinamento de template mestre e overlay usando apenas caso aprovado e curadoria governada.
