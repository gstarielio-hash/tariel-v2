# Exemplo de Documento Sintetico

Status: sintetico_provisorio
Familia: `nr13_levantamento_in_loco_equipamentos`

Este exemplo existe para orientar a leitura da familia e nao deve ser tratado como documento real emitido pela empresa.

- objeto_principal: Levantamento in loco dos ativos NR13 da unidade norte
- localizacao: Planta industrial da unidade norte
- conclusao: O servico nr13 - levantamento in loco de equipamentos foi consolidado com rastreabilidade suficiente, evidencias principais vinculadas e conclusao tecnica formalizada.

## Campos que precisam ser comparados com o material real

- Referencia principal: binding_path=`identificacao.referencia_principal`
- Evidencia de execucao: binding_path=`execucao_servico.evidencia_execucao`
- Evidencia principal: binding_path=`evidencias_e_anexos.evidencia_principal`
- Documento base: binding_path=`evidencias_e_anexos.documento_base`
- Conclusao do servico: binding_path=`conclusao.conclusao_tecnica`
