# Portfolio Empresa WF

Documento de foco operacional para a carteira de servicos da WF dentro do Tariel.

## Decisao principal

Nao vamos seguir por familia avulsa.

O foco passa a ser a carteira real de servicos da empresa, agrupada por linha comercial e tecnica:

- eletrica e prontuarios;
- equipamentos e integridade;
- inflamaveis;
- espaco confinado;
- trabalho em altura.

## Correcao importante de enquadramento

O texto comercial enviado pela WF mistura duas trilhas diferentes:

- `NR11`: movimentacao, armazenagem e equipamentos de icamento;
- `NR12`: maquinas, zonas de risco, dispositivos de seguranca e seguranca eletrica aplicada a maquinas.

Portanto:

- se o foco real for movimentacao, armazenagem e icamento, o backlog correto e `NR11`;
- se o foco real for zonas de risco de maquinas, checklist de seguranca e dispositivos, o backlog correto e `NR12`.

Para nao confundir o produto, `NR11` e `NR12` nao devem ser tratados como a mesma coisa.

## Carteira focal da WF

### Linha 1. Eletrica industrial

Servicos comerciais observados:

- `RTI - Relatorio Tecnico de Instalacoes Eletricas`
- `PIE - Prontuario das Instalacoes Eletricas`
- `SPDA - Sistema de Protecao Contra Cargas Atmosfericas`
- `LOTO - Bloqueio e sinalizacao de energias perigosas`

Familias ja alinhadas no projeto:

1. `nr10_inspecao_instalacoes_eletricas`
   Uso comercial:
   `RTI`, levantamento em campo, diagnostico, avaliacao eletrica, laudo com ART.

2. `nr10_prontuario_instalacoes_eletricas`
   Uso comercial:
   `PIE`, trilha documental de prontuario eletrico.

Observacao:

- `SPDA` e `LOTO` pertencem claramente a essa linha comercial da WF, mas ainda devem ser tratados como frente focal secundaria enquanto `RTI` e `PIE` nao estiverem fechados com referencia forte.

### Linha 2. Movimentacao, armazenagem e icamento

Servicos comerciais observados:

- levantamento em campo;
- diagnostico de itens normativos;
- avaliacao operacional de seguranca;
- documentos com ART.

Familias ja alinhadas no projeto:

3. `nr11_inspecao_equipamento_icamento`

4. `nr11_inspecao_movimentacao_armazenagem`

Observacao:

- o texto de zonas de risco de maquinas e dispositivos de seguranca aponta mais para `NR12`;
- se a WF de fato vende essa frente, `NR12` deve entrar como linha adicional oficial, nao escondida dentro de `NR11`.

### Linha 3. Integridade e inspecao NR13

Servicos comerciais observados:

- inspecoes iniciais, periodicas e extraordinarias;
- medicao de espessura por ultrassom;
- calibracao de valvulas de seguranca e manometros;
- emissao de laudos tecnicos;
- emissao de livros de registro;
- testes hidrostaticos e de estanqueidade.

Familias nucleares da linha:

5. `nr13_inspecao_caldeira`

6. `nr13_inspecao_vaso_pressao`

7. `nr13_inspecao_tubulacao`

Familias complementares imediatas:

8. `nr13_teste_hidrostatico`

9. `nr13_teste_estanqueidade_tubulacao_gas`

10. `nr13_abertura_livro_registro_seguranca`

11. `nr13_levantamento_in_loco_equipamentos`

Modulos de apoio fortemente aderentes:

- `end_medicao_espessura_ultrassom`
- calibracao de valvula de seguranca e manometro como trilha de apoio ou caso especializado, nao como familia principal misturada ao laudo-base.

### Linha 4. Inflamaveis e combustiveis

Servicos comerciais observados:

- projeto de instalacao;
- plano de inspecoes e manutencoes;
- analises de riscos;
- planos de prevencao e controles.

Familias ja alinhadas no projeto:

12. `nr20_inspecao_instalacoes_inflamaveis`

13. `nr20_prontuario_instalacoes_inflamaveis`

### Linha 5. Espaco confinado

Servicos comerciais observados:

- classificacao e mapeamento de espaco confinado;
- padronizacoes e layouts;
- planos de resgate.

Familias ja alinhadas no projeto:

14. `nr33_avaliacao_espaco_confinado`

15. `nr33_permissao_entrada_trabalho`

Observacao:

- plano de resgate e padronizacoes entram como trilha futura especializada, mas a frente imediata deve ser avaliacao + permissao controlada.

### Linha 6. Trabalho em altura

Servicos comerciais observados:

- inspecoes em linhas de vida;
- projetos;
- fabricacao de linha de vida horizontal e vertical;
- pontos de ancoragem;
- montagem em geral.

Familias ja alinhadas no projeto:

16. `nr35_inspecao_linha_de_vida`

17. `nr35_inspecao_ponto_ancoragem`

Observacao:

- projeto, fabricacao e montagem nao devem ser misturados ao laudo de inspecao;
- isso tende a virar trilha de projeto/engenharia ou servico complementar controlado.

## Ordem de execucao recomendada

### Onda A. O que vira vitrine comercial imediata

- `nr10_inspecao_instalacoes_eletricas`
- `nr10_prontuario_instalacoes_eletricas`
- `nr13_inspecao_caldeira`
- `nr13_inspecao_vaso_pressao`
- `nr20_inspecao_instalacoes_inflamaveis`
- `nr33_avaliacao_espaco_confinado`
- `nr35_inspecao_linha_de_vida`

### Onda B. O que fecha a carteira operacional

- `nr11_inspecao_equipamento_icamento`
- `nr11_inspecao_movimentacao_armazenagem`
- `nr13_inspecao_tubulacao`
- `nr13_teste_hidrostatico`
- `nr13_teste_estanqueidade_tubulacao_gas`
- `nr20_prontuario_instalacoes_inflamaveis`
- `nr33_permissao_entrada_trabalho`
- `nr35_inspecao_ponto_ancoragem`

### Onda C. O que entra depois como extensao da carteira

- `SPDA`
- `LOTO`
- trilhas de projeto e adequacao;
- modulos END e calibracoes especializadas;
- eventual linha `NR12`, se a WF realmente vender maquinas e zonas de risco como frente principal.

## Referencias sinteticas ja absorvidas no repositorio

Artefatos gerados em `2026-04-09` e movidos para as workspaces corretas:

- `nr13_inspecao_vaso_pressao`
  caminhos locais:
  `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/docs/portfolio_empresa_nr13_material_real/nr13_inspecao_vaso_pressao/coleta_entrada/referencia_sintetica_externa/nr13_inspecao_vaso_pressao.zip`
  `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/docs/portfolio_empresa_nr13_material_real/nr13_inspecao_vaso_pressao/coleta_entrada/referencia_sintetica_externa/nr13_inspecao_vaso_pressao_referencia_sintetica.pdf`
  `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/docs/portfolio_empresa_nr13_material_real/nr13_inspecao_vaso_pressao/pacote_referencia/`

- `nr35_inspecao_linha_de_vida`
  caminhos locais:
  `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/docs/portfolio_empresa_nr35_material_real/nr35_inspecao_linha_de_vida/coleta_entrada/referencia_sintetica_externa/nr35_inspecao_linha_de_vida.zip`
  `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/docs/portfolio_empresa_nr35_material_real/nr35_inspecao_linha_de_vida/coleta_entrada/referencia_sintetica_externa/nr35_inspecao_linha_de_vida_referencia_sintetica.pdf`
  `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado/docs/portfolio_empresa_nr35_material_real/nr35_inspecao_linha_de_vida/pacote_referencia/`

Esses dois casos ja podem ser tratados como baselines sinteticas fortes da carteira WF.

Validacao objetiva executada em `2026-04-09`:

- `nr13_inspecao_vaso_pressao`
  resultado:
  ZIP autocontido, contrato JSON valido, PDF A4 com `7` paginas e status final `ajuste`.

- `nr35_inspecao_linha_de_vida`
  resultado:
  ZIP autocontido, contrato JSON valido, PDF A4 com `5` paginas e status final `bloqueio`.

Consequencia pratica:

- os dois artefatos ja podem ser usados para calibracao visual, linguagem de legenda, amarracao de conclusao e distribuicao de secoes no PDF;
- o raw import permanece em `coleta_entrada/referencia_sintetica_externa/` e o bundle oficial resolvivel permanece em `pacote_referencia/`;
- eles nao substituem material real da empresa, mas ja elevam a baseline sintetica da carteira WF para um patamar util de trabalho.

## Consequencia pratica para o Tariel

O backlog da WF deve ser montado por linha de servico vendida, nao por NR abstrata.

Pergunta operacional correta daqui para frente:

1. qual linha comercial da WF queremos fechar agora;
2. qual familia principal representa essa linha;
3. qual pacote de referencia precisamos para essa familia;
4. qual servico complementar entra como modulo, trilha documental ou trilha de projeto.

## Proximo passo recomendado

Se o foco continuar sendo a carteira WF, a sequencia mais forte e:

1. absorver `nr13_inspecao_vaso_pressao` e `nr35_inspecao_linha_de_vida` como referencia sintetica oficial de trabalho;
2. gerar `nr13_inspecao_caldeira`;
3. gerar `nr10_inspecao_instalacoes_eletricas`;
4. gerar `nr20_inspecao_instalacoes_inflamaveis`;
5. gerar `nr33_avaliacao_espaco_confinado`;
6. decidir se `NR11` entra mesmo ou se a carteira de maquinas da WF deve abrir uma frente formal de `NR12`.

Estado atual da proxima frente:

- `nr13_inspecao_caldeira` ja possui family schema, template master, workspace de material real e prompt operacional pronto para geracao externa do pacote sintetico.
