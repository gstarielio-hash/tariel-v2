# NR13 - Levantamento In Loco de Equipamentos

- family_key: `nr13_levantamento_in_loco_equipamentos`
- macro_categoria: `NR13`
- kind: `documentation`
- wave: `2`
- template_codes: `nr13_levantamento_in_loco_equipamentos`

## Objetivo do refino

Usar material real da empresa para ajustar linguagem, estrutura efetiva, anexos recorrentes, bindings e criterios operacionais dessa familia antes de mexer no template final ou no documento emitido.

## O que coletar agora

- `modelo_atual_vazio`: Modelo atual vazio usado pela empresa
  min_items=1 | required=true | pasta=`coleta_entrada/modelo_atual_vazio`
  finalidade: Comparar a estrutura atual com o template_master canonico.
- `documentos_finais_reais`: Documentos finais reais ja emitidos
  min_items=2 | required=true | pasta=`coleta_entrada/documentos_finais_reais`
  finalidade: Extrair linguagem, estrutura efetiva e variacoes recorrentes do documento real.
- `padrao_linguagem_tecnica`: Padrao de linguagem tecnica e conclusao
  min_items=1 | required=true | pasta=`coleta_entrada/padrao_linguagem_tecnica`
  finalidade: Fixar tom, parecer, ressalvas, clausulas e assinatura que a empresa realmente usa.
- `regras_comerciais_e_operacionais`: Regras comerciais e operacionais do servico
  min_items=1 | required=true | pasta=`coleta_entrada/regras_comerciais_e_operacionais`
  finalidade: Capturar o que varia por cliente, ativo, escopo e contratacao.
- `documentos_base_e_memoria`: Documentos base, memoria ou planilhas de apoio
  min_items=1 | required=true | pasta=`coleta_entrada/documentos_base_e_memoria`
  finalidade: Entender dados de entrada, memoria tecnica e dependencia de anexos externos.

## Slots obrigatorios para confronto com o material real

- `slot_referencia_principal`: Referencia principal
  binding_path=`identificacao.referencia_principal` | accepted=foto, documento
  finalidade: Vincular a referencia principal do objeto do servico nr13_levantamento_in_loco_equipamentos.
- `slot_evidencia_execucao`: Evidencia de execucao
  binding_path=`execucao_servico.evidencia_execucao` | accepted=foto, documento, texto
  finalidade: Registrar a execucao principal do servico com evidencia rastreavel.
- `slot_evidencia_principal`: Evidencia principal
  binding_path=`evidencias_e_anexos.evidencia_principal` | accepted=foto, documento, texto
  finalidade: Consolidar a evidencia principal que sustenta a conclusao do servico.
- `slot_documento_base`: Documento base
  binding_path=`evidencias_e_anexos.documento_base` | accepted=documento
  finalidade: Vincular o documento base ou memoria principal do servico.
- `slot_conclusao_servico`: Conclusao do servico
  binding_path=`conclusao.conclusao_tecnica` | accepted=texto
  finalidade: Registrar a conclusao tecnica estruturada para revisao.

## Secoes esperadas no documento final

- Identificacao do Pacote
- Escopo Documental
- Execucao do Levantamento
- Evidencias e Anexos
- Documentacao e Registros
- Lacunas ou Pendencias
- Recomendacoes
- Conclusao

## Perguntas que o material real precisa responder

- Qual documento atual a empresa considera referencia principal para esta familia?
- Quais anexos ou evidencias sao obrigatorios na pratica, mesmo quando nao estao escritos no modelo vazio?
- Quais campos sempre aparecem no documento final, mesmo quando o inspetor nao preencheu explicitamente em campo?
- Quais trechos de linguagem precisam seguir o padrao exato do engenheiro responsavel?

## Bloqueios estruturais da familia

- `escopo_principal_divergente_da_familia`
- `troca_silenciosa_da_familia_principal`
- `ausencia_de_objeto_principal`
- `ausencia_de_localizacao`
- `ausencia_de_slot_obrigatorio`
- `ausencia_de_conclusao_tecnica`

## Layout local da coleta

- `coleta_entrada/`: recepcao do material bruto da empresa
- `pacote_referencia/`: futuro pacote consolidado para importacao de filled_reference
- `status_refino.json`: checkpoint curto do estado da familia

## Regra

Nao adaptar o template final direto a partir de um PDF isolado. Primeiro fechar este pacote de coleta real, depois consolidar o blueprint/fill_reference e so entao revisar template e linguagem final.

Descricao canonica da familia: Levantamento em campo dos equipamentos abrangidos pela NR13 com inventario inicial e consolidacao de referencias para regularizacao.
