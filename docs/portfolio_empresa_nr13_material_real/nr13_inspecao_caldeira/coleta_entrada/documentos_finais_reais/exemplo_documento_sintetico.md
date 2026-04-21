# Exemplo de Documento Sintetico

Status: sintetico_provisorio
Familia: `nr13_inspecao_caldeira`

Este exemplo existe para orientar a leitura da familia e nao deve ser tratado como documento real emitido pela empresa.

- objeto_principal: Caldeira horizontal CAL-01
- localizacao: Casa de caldeiras, unidade norte, setor de utilidades
- conclusao: A caldeira apresenta identificacao minima validada, evidencias obrigatorias suficientes, painel e dispositivos principais registrados, com necessidade de ajuste corretivo localizado associado ao isolamento termico e ao acompanhamento do trecho aparente da exaustao.

## Campos que precisam ser comparados com o material real

- Placa de identificacao: binding_path=`identificacao.placa_identificacao`
- Vista geral da caldeira: binding_path=`caracterizacao_do_equipamento.vista_geral_caldeira`
- Dispositivos de seguranca: binding_path=`dispositivos_e_controles.dispositivos_de_seguranca`
- Painel e comandos: binding_path=`dispositivos_e_controles.painel_e_comandos`
- Condicao geral: binding_path=`inspecao_visual.condicao_geral`
- Conclusao da inspecao: binding_path=`conclusao.conclusao_tecnica`
