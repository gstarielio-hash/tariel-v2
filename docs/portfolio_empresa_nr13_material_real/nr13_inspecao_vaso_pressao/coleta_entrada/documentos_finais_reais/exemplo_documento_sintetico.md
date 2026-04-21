# Exemplo de Documento Sintetico

Status: sintetico_provisorio
Familia: `nr13_inspecao_vaso_pressao`

Este exemplo existe para orientar a leitura da familia e nao deve ser tratado como documento real emitido pela empresa.

- objeto_principal: Vaso de pressao vertical VP-204
- localizacao: Casa de utilidades, linha de ar comprimido, bloco B
- conclusao: O vaso de pressao apresenta identificacao minima validada, evidencias obrigatorias suficientes e dispositivos de seguranca registrados, com necessidade de ajuste corretivo localizado associado a corrosao superficial observada.

## Campos que precisam ser comparados com o material real

- Placa de identificacao: binding_path=`identificacao.placa_identificacao`
- Vista geral do equipamento: binding_path=`caracterizacao_do_equipamento.vista_geral_equipamento`
- Dispositivo de seguranca: binding_path=`dispositivos_e_acessorios.dispositivos_de_seguranca`
- Condicao geral: binding_path=`inspecao_visual.condicao_geral`
- Conclusao da inspecao: binding_path=`conclusao.conclusao_tecnica`
