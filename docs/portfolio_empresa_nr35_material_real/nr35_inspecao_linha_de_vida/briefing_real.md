# NR35 · Inspecao Linha de Vida

- family_key: `nr35_inspecao_linha_de_vida`
- macro_categoria: `NR35`
- kind: `inspection`
- wave: `1`
- template_codes: `nr35_inspecao_linha_de_vida, nr35_linha_vida`

## Objetivo do refino

Usar material real da empresa para ajustar linguagem, estrutura efetiva, capa, checklist de componentes, blocos fotograficos e criterios operacionais desta familia antes de mexer no documento final emitido.

## O que coletar agora

- `modelo_atual_vazio`: Modelo atual vazio usado pela empresa
  min_items=1 | required=true | pasta=`coleta_entrada/modelo_atual_vazio`
  finalidade: Comparar a estrutura real do laudo NR35 com o overlay canonico da familia.
- `documentos_finais_reais`: Documentos finais reais ja emitidos
  min_items=3 | required=true | pasta=`coleta_entrada/documentos_finais_reais`
  finalidade: Extrair linguagem, paginação, anexos e variacoes recorrentes do laudo real.
- `padrao_linguagem_tecnica`: Padrao de linguagem tecnica e conclusao
  min_items=1 | required=true | pasta=`coleta_entrada/padrao_linguagem_tecnica`
  finalidade: Fixar parecer, ressalvas, assinatura tecnica e clausulas recorrentes do engenheiro responsavel.
- `regras_comerciais_e_operacionais`: Regras comerciais e operacionais do servico
  min_items=1 | required=true | pasta=`coleta_entrada/regras_comerciais_e_operacionais`
  finalidade: Capturar o que muda por cliente, tipo de linha de vida, bloqueio, periodicidade e contratacao.
- `evidencias_reais_associadas`: Evidencias reais associadas aos documentos finais
  min_items=1 | required=true | pasta=`coleta_entrada/evidencias_reais_associadas`
  finalidade: Validar slots fotograficos, anexos, laudos base e criterios reais de evidencia por componente.

## Slots obrigatorios para confronto com o material real

- `slot_referencia_principal`: Referencia principal
  binding_path=`identificacao.referencia_principal` | accepted=foto, documento
  finalidade: Ancorar o ativo principal e a rastreabilidade do laudo.
- `slot_evidencia_execucao`: Evidencia de execucao
  binding_path=`execucao_servico.evidencia_execucao` | accepted=foto, documento, texto
  finalidade: Registrar a vistoria principal e os pontos verificados em campo.
- `slot_evidencia_principal`: Evidencia principal
  binding_path=`evidencias_e_anexos.evidencia_principal` | accepted=foto, documento, texto
  finalidade: Sustentar a conclusao tecnica e o eventual bloqueio do sistema.
- `slot_conclusao_servico`: Conclusao do servico
  binding_path=`conclusao.conclusao_tecnica` | accepted=texto
  finalidade: Registrar a conclusao final auditavel para a Mesa.

## Secoes esperadas no documento final

- Identificacao geral
- Objeto da inspecao
- Componentes e acessorios inspecionados
- Registros fotograficos
- Conclusao
- Governanca da Mesa

## Perguntas que o material real precisa responder

- Qual PDF atual a empresa considera referencia principal para NR35 linha de vida?
- Quais anexos ficam no corpo do laudo e quais ficam apenas em acervo?
- Quais componentes sempre aparecem no checklist final mesmo quando nao ha nao conformidade?
- Como a empresa expressa bloqueio, reprovacao e proxima inspecao periodica no texto final?
- Quais fotos entram obrigatoriamente no PDF final para linha de vida vertical?
- Que combinacoes de contratante, contratada, ART e laudo do fabricante precisam sempre aparecer na capa?

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

Descricao canonica da familia: Execucao do servico inspecao linha de vida no contexto da norma trabalho em altura, com consolidacao de evidencias, registros de campo ou base documental e conclusao tecnica auditavel.
