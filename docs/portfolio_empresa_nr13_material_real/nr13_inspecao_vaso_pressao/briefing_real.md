# NR13 · Inspecao de Vaso de Pressao

- family_key: `nr13_inspecao_vaso_pressao`
- macro_categoria: `NR13`
- kind: `inspection`
- wave: `1`
- template_codes: `nr13_vaso_pressao, nr13_inspecao_vaso_pressao`

## Objetivo do refino

Usar material real da empresa para ajustar linguagem, estrutura efetiva, anexos recorrentes, bindings e criterios operacionais dessa familia antes de mexer no template final ou no documento emitido.

## O que coletar agora

- `modelo_atual_vazio`: Modelo atual vazio usado pela empresa
  min_items=1 | required=true | pasta=`coleta_entrada/modelo_atual_vazio`
  finalidade: Comparar a estrutura atual com o template_master canonico.
- `documentos_finais_reais`: Documentos finais reais ja emitidos
  min_items=3 | required=true | pasta=`coleta_entrada/documentos_finais_reais`
  finalidade: Extrair linguagem, estrutura efetiva e variacoes recorrentes do documento real.
- `padrao_linguagem_tecnica`: Padrao de linguagem tecnica e conclusao
  min_items=1 | required=true | pasta=`coleta_entrada/padrao_linguagem_tecnica`
  finalidade: Fixar tom, parecer, ressalvas, clausulas e assinatura que a empresa realmente usa.
- `regras_comerciais_e_operacionais`: Regras comerciais e operacionais do servico
  min_items=1 | required=true | pasta=`coleta_entrada/regras_comerciais_e_operacionais`
  finalidade: Capturar o que varia por cliente, ativo, escopo e contratacao.
- `evidencias_reais_associadas`: Evidencias reais associadas aos documentos finais
  min_items=1 | required=true | pasta=`coleta_entrada/evidencias_reais_associadas`
  finalidade: Validar slots de imagem, anexos e criterios reais de evidencia.

## Slots obrigatorios para confronto com o material real

- `slot_placa_identificacao`: Placa de identificacao
  binding_path=`identificacao.placa_identificacao` | accepted=foto, documento
  finalidade: Vincular evidencia da identificacao do equipamento por placa ou documento equivalente disponivel.
- `slot_vista_geral_equipamento`: Vista geral do equipamento
  binding_path=`caracterizacao_do_equipamento.vista_geral_equipamento` | accepted=foto
  finalidade: Registrar a vista geral do vaso de pressao.
- `slot_dispositivo_seguranca`: Dispositivo de seguranca
  binding_path=`dispositivos_e_acessorios.dispositivos_de_seguranca` | accepted=foto
  finalidade: Registrar visualmente pelo menos um dispositivo de seguranca associado.
- `slot_condicao_geral`: Condicao geral
  binding_path=`inspecao_visual.condicao_geral` | accepted=texto, foto
  finalidade: Registrar a leitura da condicao geral por texto e/ou evidencia visual.
- `slot_conclusao_inspecao`: Conclusao da inspecao
  binding_path=`conclusao.conclusao_tecnica` | accepted=texto
  finalidade: Registrar a conclusao tecnica estruturada para revisao.

## Secoes esperadas no documento final

- Identificacao
- Caracterizacao do equipamento
- Inspecao visual
- Dispositivos e acessorios
- Documentacao e registros
- Nao conformidades
- Recomendacoes
- Conclusao

## Perguntas que o material real precisa responder

- Qual documento atual a empresa considera referencia principal para esta familia?
- Quais anexos ou evidencias sao obrigatorios na pratica, mesmo quando nao estao escritos no modelo vazio?
- Quais campos sempre aparecem no documento final, mesmo quando o inspetor nao preencheu explicitamente em campo?
- Quais trechos de linguagem precisam seguir o padrao exato do engenheiro responsavel?
- Quais evidencias fotograficas entram no PDF final e quais ficam apenas em anexo ou acervo?
- Quais nao conformidades ou ressalvas sao mais recorrentes nessa familia?

## Bloqueios estruturais da familia

- `escopo_principal_diferente_de_vaso_de_pressao`
- `troca_silenciosa_da_familia_principal`
- `ausencia_de_identificacao_do_vaso`
- `ausencia_de_localizacao`
- `ausencia_de_slot_obrigatorio`
- `quantidade_total_de_fotos_abaixo_do_minimo`
- `quantidade_total_de_textos_abaixo_do_minimo`
- `ausencia_de_registro_da_condicao_geral`

## Layout local da coleta

- `coleta_entrada/`: recepcao do material bruto da empresa
- `pacote_referencia/`: futuro pacote consolidado para importacao de filled_reference
- `status_refino.json`: checkpoint curto do estado da familia

## Regra

Nao adaptar o template final direto a partir de um PDF isolado. Primeiro fechar este pacote de coleta real, depois consolidar o blueprint/fill_reference e so entao revisar template e linguagem final.

Descricao canonica da familia: Familia tecnica para inspecao de vasos de pressao, com foco em identificacao do equipamento, condicoes visuais, dispositivos de seguranca, integridade aparente, placas, acessos, registros e conclusao tecnica estruturada para revisao da Mesa.
