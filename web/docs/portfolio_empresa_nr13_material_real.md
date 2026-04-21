# Portfolio Empresa NR13: Material Real

Workspace canonica para refino por material real da empresa.

## Regra

- cada familia tem um manifesto de coleta, um briefing de refino, uma area para material bruto e uma area para pacote de referencia;
- o objetivo aqui nao e guardar o family_schema; e fechar o gap entre a familia canonica e o jeito real como a empresa opera e escreve o documento;
- toda adaptacao do template final deve passar por essa workspace antes.

## Familias preparadas

| Wave | Family key | Kind | Pasta de trabalho |
| --- | --- | --- | --- |
| 1 | `nr13_inspecao_caldeira` | `inspection` | `docs/portfolio_empresa_nr13_material_real/nr13_inspecao_caldeira` |
| 1 | `nr13_inspecao_tubulacao` | `inspection` | `docs/portfolio_empresa_nr13_material_real/nr13_inspecao_tubulacao` |
| 1 | `nr13_inspecao_vaso_pressao` | `inspection` | `docs/portfolio_empresa_nr13_material_real/nr13_inspecao_vaso_pressao` |
| 1 | `nr13_integridade_caldeira` | `inspection` | `docs/portfolio_empresa_nr13_material_real/nr13_integridade_caldeira` |
| 1 | `nr13_teste_estanqueidade_tubulacao_gas` | `test` | `docs/portfolio_empresa_nr13_material_real/nr13_teste_estanqueidade_tubulacao_gas` |
| 1 | `nr13_teste_hidrostatico` | `test` | `docs/portfolio_empresa_nr13_material_real/nr13_teste_hidrostatico` |
| 2 | `nr13_abertura_livro_registro_seguranca` | `documentation` | `docs/portfolio_empresa_nr13_material_real/nr13_abertura_livro_registro_seguranca` |
| 2 | `nr13_fluxograma_linhas_acessorios` | `documentation` | `docs/portfolio_empresa_nr13_material_real/nr13_fluxograma_linhas_acessorios` |
| 2 | `nr13_levantamento_in_loco_equipamentos` | `documentation` | `docs/portfolio_empresa_nr13_material_real/nr13_levantamento_in_loco_equipamentos` |
| 2 | `nr13_reconstituicao_prontuario` | `documentation` | `docs/portfolio_empresa_nr13_material_real/nr13_reconstituicao_prontuario` |
| 3 | `nr13_adequacao_planta_industrial` | `engineering` | `docs/portfolio_empresa_nr13_material_real/nr13_adequacao_planta_industrial` |
| 3 | `nr13_calculo_espessura_minima_caldeira` | `calculation` | `docs/portfolio_empresa_nr13_material_real/nr13_calculo_espessura_minima_caldeira` |
| 3 | `nr13_calculo_espessura_minima_tubulacao` | `calculation` | `docs/portfolio_empresa_nr13_material_real/nr13_calculo_espessura_minima_tubulacao` |
| 3 | `nr13_calculo_espessura_minima_vaso_pressao` | `calculation` | `docs/portfolio_empresa_nr13_material_real/nr13_calculo_espessura_minima_vaso_pressao` |
| 3 | `nr13_calculo_pmta_vaso_pressao` | `calculation` | `docs/portfolio_empresa_nr13_material_real/nr13_calculo_pmta_vaso_pressao` |
| 3 | `nr13_par_projeto_alteracao_reparo` | `engineering` | `docs/portfolio_empresa_nr13_material_real/nr13_par_projeto_alteracao_reparo` |
| 3 | `nr13_projeto_instalacao` | `engineering` | `docs/portfolio_empresa_nr13_material_real/nr13_projeto_instalacao` |
| 4 | `nr13_treinamento_operacao_caldeira` | `training` | `docs/portfolio_empresa_nr13_material_real/nr13_treinamento_operacao_caldeira` |
| 4 | `nr13_treinamento_operacao_unidades_processo` | `training` | `docs/portfolio_empresa_nr13_material_real/nr13_treinamento_operacao_unidades_processo` |
| 5 | `end_liquido_penetrante` | `ndt` | `docs/portfolio_empresa_nr13_material_real/end_liquido_penetrante` |
| 5 | `end_medicao_espessura_ultrassom` | `ndt` | `docs/portfolio_empresa_nr13_material_real/end_medicao_espessura_ultrassom` |
| 5 | `end_particula_magnetica` | `ndt` | `docs/portfolio_empresa_nr13_material_real/end_particula_magnetica` |
| 5 | `end_ultrassom_junta_soldada` | `ndt` | `docs/portfolio_empresa_nr13_material_real/end_ultrassom_junta_soldada` |
| 5 | `end_visual_solda` | `ndt` | `docs/portfolio_empresa_nr13_material_real/end_visual_solda` |

## Fluxo curto

1. colocar o material bruto em `coleta_entrada/` da familia;
2. atualizar `status_refino.json` com o que chegou e o que ainda falta;
3. consolidar o pacote em `pacote_referencia/`;
4. importar o pacote de filled_reference quando ele estiver pronto;
5. so depois revisar template, linguagem e bind final do documento.
