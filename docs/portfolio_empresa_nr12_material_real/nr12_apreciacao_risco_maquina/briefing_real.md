# NR12 - Apreciacao risco maquina

- family_key: `nr12_apreciacao_risco_maquina`
- macro_categoria: `NR12`
- kind: `engineering`
- wave: `1`
- template_codes: `nr12_apreciacao_risco_maquina`

## Objetivo do refino

Usar material real da empresa para ajustar linguagem, estrutura efetiva, anexos recorrentes, bindings e criterios operacionais dessa familia antes de mexer no template final ou no documento emitido.

## O que coletar agora

- `modelo_atual_vazio`: Modelo atual vazio usado pela empresa
  min_items=1 | required=true | pasta=`coleta_entrada/modelo_atual_vazio`
  finalidade: Comparar a estrutura atual com o template mestre canonico.
- `documentos_finais_reais`: Documentos finais reais ja emitidos
  min_items=2 | required=true | pasta=`coleta_entrada/documentos_finais_reais`
  finalidade: Extrair linguagem, estrutura efetiva, anexos e variacoes recorrentes do documento real.
- `padrao_linguagem_tecnica`: Padrao de linguagem tecnica e conclusao
  min_items=1 | required=true | pasta=`coleta_entrada/padrao_linguagem_tecnica`
  finalidade: Fixar tom, parecer, ressalvas, clausulas e fechamento tecnico recorrente.
- `regras_comerciais_e_operacionais`: Regras comerciais e operacionais do servico
  min_items=1 | required=true | pasta=`coleta_entrada/regras_comerciais_e_operacionais`
  finalidade: Capturar escopo, limites, variacoes contratuais e amarracoes operacionais da familia.
- `documentos_base_e_memoria`: Documentos base, memoria ou planilhas de apoio
  min_items=1 | required=true | pasta=`coleta_entrada/documentos_base_e_memoria`
  finalidade: Mapear dados de entrada, memoria tecnica e anexos de apoio exigidos no documento final.

## Slots obrigatorios para confronto com o material real

- `slot_referencia_principal`: Referencia principal
  binding_path=`identificacao.referencia_principal` | accepted=foto, documento
  finalidade: Vincular a referencia principal do objeto do servico nr12_apreciacao_risco_maquina.
- `slot_evidencia_execucao`: Evidencia de execucao
  binding_path=`execucao_servico.evidencia_execucao` | accepted=foto, documento, texto
  finalidade: Registrar a execucao principal do servico com evidencia rastreavel.
- `slot_evidencia_principal`: Evidencia principal
  binding_path=`evidencias_e_anexos.evidencia_principal` | accepted=foto, documento, texto
  finalidade: Consolidar a evidencia principal que sustenta a conclusao do servico.
- `slot_documento_base`: Documento base
  binding_path=`evidencias_e_anexos.documento_base` | accepted=documento
  finalidade: Vincular o documento ancora ou memoria principal do servico.
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
- Quais premissas tecnicas e memoria de calculo precisam aparecer em secoes obrigatorias?
- Quais documentos base ou planilhas precisam virar anexo material do pacote final?

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

- prompt excepcional salvo em `prompt_fallback_sintetica_externa_nr12_apreciacao_risco_maquina.md`
- usar apenas se ainda nao houver material real suficiente para calibracao da familia
- o ZIP bruto deve entrar em `coleta_entrada/referencia_sintetica_externa/`

## Regra

Nao adaptar o template final direto a partir de um PDF isolado. Primeiro fechar este pacote de coleta real, depois consolidar o blueprint/fill_reference e so entao revisar template e linguagem final.

Descricao canonica da familia: Execucao do servico apreciacao risco maquina no contexto da norma seguranca no trabalho em maquinas e equipamentos, com consolidacao de evidencias, registros de campo ou base documental e conclusao tecnica auditavel.
