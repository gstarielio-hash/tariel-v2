# NR20 - Inspecao instalacoes inflamaveis

- family_key: `nr20_inspecao_instalacoes_inflamaveis`
- macro_categoria: `NR20`
- kind: `inspection`
- wave: `1`
- template_codes: `nr20_inspecao_instalacoes_inflamaveis`

## Objetivo do refino

Usar material real da empresa para ajustar linguagem, estrutura efetiva, anexos recorrentes, bindings e criterios operacionais dessa familia antes de mexer no template final ou no documento emitido.

## O que coletar agora

- `modelo_atual_vazio`: Modelo atual vazio usado pela empresa
  min_items=1 | required=true | pasta=`coleta_entrada/modelo_atual_vazio`
  finalidade: Comparar a estrutura atual com o template mestre canonico.
- `documentos_finais_reais`: Documentos finais reais ja emitidos
  min_items=3 | required=true | pasta=`coleta_entrada/documentos_finais_reais`
  finalidade: Extrair linguagem, estrutura efetiva, anexos e variacoes recorrentes do documento real.
- `padrao_linguagem_tecnica`: Padrao de linguagem tecnica e conclusao
  min_items=1 | required=true | pasta=`coleta_entrada/padrao_linguagem_tecnica`
  finalidade: Fixar tom, parecer, ressalvas, clausulas e fechamento tecnico recorrente.
- `regras_comerciais_e_operacionais`: Regras comerciais e operacionais do servico
  min_items=1 | required=true | pasta=`coleta_entrada/regras_comerciais_e_operacionais`
  finalidade: Capturar escopo, limites, variacoes contratuais e amarracoes operacionais da familia.
- `evidencias_reais_associadas`: Evidencias reais associadas aos documentos finais
  min_items=1 | required=true | pasta=`coleta_entrada/evidencias_reais_associadas`
  finalidade: Validar blocos fotograficos, anexos materiais e criterio real de evidencia.

## Slots obrigatorios para confronto com o material real

- `slot_referencia_principal`: Referencia principal
  binding_path=`identificacao.referencia_principal` | accepted=foto, documento
  finalidade: Vincular a referencia principal do objeto do servico nr20_inspecao_instalacoes_inflamaveis.
- `slot_evidencia_execucao`: Evidencia de execucao
  binding_path=`execucao_servico.evidencia_execucao` | accepted=foto, documento, texto
  finalidade: Registrar a execucao principal do servico com evidencia rastreavel.
- `slot_evidencia_principal`: Evidencia principal
  binding_path=`evidencias_e_anexos.evidencia_principal` | accepted=foto, documento, texto
  finalidade: Consolidar a evidencia principal que sustenta a conclusao do servico.
- `slot_conclusao_servico`: Conclusao do servico
  binding_path=`conclusao.conclusao_tecnica` | accepted=texto
  finalidade: Registrar a conclusao tecnica estruturada para revisao.

## Secoes esperadas no documento final

- Identificacao do Objeto
- Escopo do Servico
- Execucao do Servico
- Evidencias e Anexos
- Documentacao e Registros
- Nao Conformidades ou Lacunas
- Recomendacoes
- Conclusao

## Perguntas que o material real precisa responder

- Qual documento atual a empresa considera referencia principal para esta familia?
- Quais anexos ou evidencias entram no documento final e quais ficam so em acervo?
- Quais campos sempre aparecem no documento final, mesmo quando o inspetor nao preencheu explicitamente em campo?
- Quais trechos de linguagem precisam seguir o padrao exato do responsavel tecnico?
- Quais evidencias fotograficas entram no PDF final e quais ficam apenas em anexo ou acervo?
- Quais nao conformidades, ressalvas ou pendencias sao mais recorrentes nessa familia?

## Bloqueios estruturais da familia

- `escopo_principal_divergente_da_familia`
- `troca_silenciosa_da_familia_principal`
- `ausencia_de_objeto_principal`
- `ausencia_de_localizacao`
- `ausencia_de_slot_obrigatorio`
- `ausencia_de_conclusao_tecnica`

## Layout local da coleta

- `coleta_entrada/`: recepcao do material bruto da empresa
- `coleta_entrada/referencia_sintetica_externa/`: fallback excepcional para baseline sintetica externa
- `pacote_referencia/`: futuro pacote consolidado para importacao de filled_reference
- `status_refino.json`: checkpoint curto do estado da familia

## Fallback sintetico externo

- prompt excepcional salvo em `prompt_fallback_sintetica_externa_nr20_inspecao_instalacoes_inflamaveis.md`
- usar apenas se ainda nao houver material real suficiente para calibracao da familia
- o ZIP bruto deve entrar em `coleta_entrada/referencia_sintetica_externa/`

## Regra

Nao adaptar o template final direto a partir de um PDF isolado. Primeiro fechar este pacote de coleta real, depois consolidar o blueprint/fill_reference e so entao revisar template e linguagem final.

Descricao canonica da familia: Execucao do servico inspecao instalacoes inflamaveis no contexto da norma seguranca e saude no trabalho com inflamaveis e combustiveis, com consolidacao de evidencias, registros de campo ou base documental e conclusao tecnica auditavel.
