# Biblioteca de Templates Profissionais de Inspecao

Resumo da biblioteca profissionalizada para inspecoes, testes e tecnicas END da linha atual do projeto.

## Cobertura atual

- macro categorias presentes no projeto: `NR10`, `NR13` e `END`;
- templates profissionais desta biblioteca: `13`;
- isso cobre a carteira tecnica principal de inspecao da empresa, mas nao cobre ainda o universo inteiro das NRs brasileiras;
- continuam fora do projeto, por exemplo, frentes como `NR12`, `NR20`, `NR33`, `NR35` e outras familias nao modeladas.

## Templates profissionais

| Family key | Template code | Nome exibicao | Tipo |
| --- | --- | --- | --- |
| `nr10_implantacao_loto` | `nr10_implantacao_loto` | NR10 - Implantacao e gerenciamento de LOTO | `inspection` |
| `nr10_inspecao_spda` | `nr10_inspecao_spda` | NR10 - Inspecao de SPDA | `inspection` |
| `nr13_inspecao_vaso_pressao` | `nr13_vaso_pressao` | NR13 · Inspecao de Vaso de Pressao | `inspection` |
| `nr13_inspecao_caldeira` | `nr13_caldeira` | NR13 - Inspecao de Caldeira | `inspection` |
| `nr13_inspecao_tubulacao` | `nr13_inspecao_tubulacao` | NR13 - Inspecao de Tubulacao | `inspection` |
| `nr13_integridade_caldeira` | `nr13_integridade_caldeira` | NR13 - Integridade de Caldeira | `inspection` |
| `nr13_teste_hidrostatico` | `nr13_teste_hidrostatico` | NR13 - Teste Hidrostatico | `inspection` |
| `nr13_teste_estanqueidade_tubulacao_gas` | `nr13_teste_estanqueidade_tubulacao_gas` | NR13 - Teste de Estanqueidade em Tubulacao de Gas | `inspection` |
| `end_medicao_espessura_ultrassom` | `end_medicao_espessura_ultrassom` | END - Medicao de Espessura por Ultrassom | `ndt` |
| `end_ultrassom_junta_soldada` | `end_ultrassom_junta_soldada` | END - Ultrassom em Junta Soldada | `ndt` |
| `end_liquido_penetrante` | `end_liquido_penetrante` | END - Liquido Penetrante | `ndt` |
| `end_particula_magnetica` | `end_particula_magnetica` | END - Particula Magnetica | `ndt` |
| `end_visual_solda` | `end_visual_solda` | END - Ensaio Visual de Solda | `ndt` |

## Padrao adotado

- quadro de controle do documento;
- resumo executivo e escopo tecnico;
- matriz de evidencias e documentacao;
- conclusao tecnica e governanca da Mesa;
- bloco final de assinatura e responsabilidade.

## Operacao

1. manter a familia tecnica como fonte de verdade;
2. usar o template profissional como base comercial e operacional;
3. evoluir variantes por modalidade quando o portfolio pedir versoes separadas como inicial, periodica e extraordinaria.
