# NR10 - Inspecao instalacoes eletricas

- family_key: `nr10_inspecao_instalacoes_eletricas`
- macro_categoria: `NR10`
- kind: `inspection`
- wave: `1`
- template_codes: `nr10_inspecao_instalacoes_eletricas`

## Objetivo do refino

Usar material real ou baseline sintetica externa para ajustar linguagem, estrutura recorrente, blocos fotograficos, verificacoes documentais e conclusao tecnica dessa familia antes de mexer no template final ou no documento emitido.

## O que coletar agora

- `modelo_atual_vazio`: modelo atual vazio usado pela empresa
- `documentos_finais_reais`: RTIs, laudos ou relatorios finais ja emitidos
- `padrao_linguagem_tecnica`: padrao de linguagem tecnica e conclusao
- `regras_comerciais_e_operacionais`: regras de escopo, ART, limites e variacoes do servico
- `evidencias_reais_associadas`: fotos, anexos, diagramas, RTIs ou documentos de apoio

## Slots obrigatorios para confronto com o material real

- `slot_referencia_principal`
- `slot_evidencia_execucao`
- `slot_evidencia_principal`
- `slot_documento_base`
- `slot_conclusao_servico`

## Proximo passo operacional ja preparado

- prompt externo salvo em `prompt_chatgpt_pro_nr10_inspecao_instalacoes_eletricas.md`
- pasta de raw import preparada em `coleta_entrada/referencia_sintetica_externa/`
- contrato de consolidacao continua sendo `manifest.json` + `tariel_filled_reference_bundle.json` + assets referenciados em `pacote_referencia/`
