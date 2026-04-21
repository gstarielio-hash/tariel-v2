# Portfolio Empresa NR13: Artefatos Canonicos

Resumo dos artefatos gerados para a carteira completa da empresa focada em NR13.

## Regra

- cada familia abaixo possui `family_schema`, `laudo_output_seed`, `laudo_output_exemplo` e `template_master_seed`;
- as familias existentes `nr13_inspecao_vaso_pressao` e `nr13_inspecao_caldeira` foram preservadas;
- os artefatos desta lista foram gerados em lote a partir do portfolio comercial real da empresa.

## Familias geradas neste lote

| Wave | Family key | Categoria | Kind | Template code |
| --- | --- | --- | --- | --- |
| 1 | `nr13_inspecao_tubulacao` | `NR13` | `inspection` | `nr13_inspecao_tubulacao` |
| 1 | `nr13_integridade_caldeira` | `NR13` | `inspection` | `nr13_integridade_caldeira` |
| 1 | `nr13_teste_hidrostatico` | `NR13` | `test` | `nr13_teste_hidrostatico` |
| 1 | `nr13_teste_estanqueidade_tubulacao_gas` | `NR13` | `test` | `nr13_teste_estanqueidade_tubulacao_gas` |
| 2 | `nr13_reconstituicao_prontuario` | `NR13` | `documentation` | `nr13_reconstituicao_prontuario` |
| 2 | `nr13_abertura_livro_registro_seguranca` | `NR13` | `documentation` | `nr13_abertura_livro_registro_seguranca` |
| 2 | `nr13_levantamento_in_loco_equipamentos` | `NR13` | `documentation` | `nr13_levantamento_in_loco_equipamentos` |
| 2 | `nr13_fluxograma_linhas_acessorios` | `NR13` | `documentation` | `nr13_fluxograma_linhas_acessorios` |
| 3 | `nr13_adequacao_planta_industrial` | `NR13` | `engineering` | `nr13_adequacao_planta_industrial` |
| 3 | `nr13_projeto_instalacao` | `NR13` | `engineering` | `nr13_projeto_instalacao` |
| 3 | `nr13_par_projeto_alteracao_reparo` | `NR13` | `engineering` | `nr13_par_projeto_alteracao_reparo` |
| 3 | `nr13_calculo_pmta_vaso_pressao` | `NR13` | `calculation` | `nr13_calculo_pmta_vaso_pressao` |
| 3 | `nr13_calculo_espessura_minima_caldeira` | `NR13` | `calculation` | `nr13_calculo_espessura_minima_caldeira` |
| 3 | `nr13_calculo_espessura_minima_vaso_pressao` | `NR13` | `calculation` | `nr13_calculo_espessura_minima_vaso_pressao` |
| 3 | `nr13_calculo_espessura_minima_tubulacao` | `NR13` | `calculation` | `nr13_calculo_espessura_minima_tubulacao` |
| 4 | `nr13_treinamento_operacao_caldeira` | `NR13` | `training` | `nr13_treinamento_operacao_caldeira` |
| 4 | `nr13_treinamento_operacao_unidades_processo` | `NR13` | `training` | `nr13_treinamento_operacao_unidades_processo` |
| 5 | `end_medicao_espessura_ultrassom` | `END` | `ndt` | `end_medicao_espessura_ultrassom` |
| 5 | `end_ultrassom_junta_soldada` | `END` | `ndt` | `end_ultrassom_junta_soldada` |
| 5 | `end_liquido_penetrante` | `END` | `ndt` | `end_liquido_penetrante` |
| 5 | `end_particula_magnetica` | `END` | `ndt` | `end_particula_magnetica` |
| 5 | `end_visual_solda` | `END` | `ndt` | `end_visual_solda` |

## Uso operacional

1. publicar as familias no catalogo do Admin-CEO;
2. bootstrapar os templates canônicos para a empresa piloto;
3. liberar familia e template por empresa;
4. ativar por codigo quando o servico entrar em operacao.
