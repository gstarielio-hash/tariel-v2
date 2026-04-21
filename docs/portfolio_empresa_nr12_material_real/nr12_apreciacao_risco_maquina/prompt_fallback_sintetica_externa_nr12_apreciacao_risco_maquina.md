# Prompt Fallback Sintetica Externa - NR12 - Apreciacao risco maquina

Use este prompt apenas como fallback excepcional, quando ainda nao houver material real suficiente para consolidar a baseline da familia.

```text
Quero que voce gere um pacote sintetico externo completo para a familia Tariel `nr12_apreciacao_risco_maquina`.

Objetivo:
- produzir uma referencia sintetica profissional em portugues do Brasil;
- gerar `manifest.json`, `tariel_filled_reference_bundle.json`, `assets/` e `pdf/`;
- entregar tambem um ZIP bruto com todos os artefatos prontos para importacao.

Regra de produto:
- a familia principal e `nr12_apreciacao_risco_maquina`;
- o template principal deve ser `nr12_apreciacao_risco_maquina`;
- o kind operacional e `engineering`;
- nao misture outras familias principais no documento;
- o documento deve parecer vendavel, tecnico e auditavel;
- tudo deve ser sintetico, sem marcas reais;
- o conteudo deve vir em portugues do Brasil.

Estrutura de saida obrigatoria:
- `output/nr12_apreciacao_risco_maquina/assets/`
- `output/nr12_apreciacao_risco_maquina/pdf/`
- `output/nr12_apreciacao_risco_maquina/manifest.json`
- `output/nr12_apreciacao_risco_maquina/tariel_filled_reference_bundle.json`
- `output/nr12_apreciacao_risco_maquina/pdf/nr12_apreciacao_risco_maquina_referencia_sintetica.pdf`

Contrato obrigatorio do manifest:
- `schema_type`: `filled_reference_package_manifest`
- `schema_version`: `1`
- `family_key`: `nr12_apreciacao_risco_maquina`
- `package_status`: `synthetic_baseline`
- `source_kind`: `synthetic_repo_baseline`
- `bundle_file`: `tariel_filled_reference_bundle.json`
- `reference_count`: `1`

Contrato obrigatorio do bundle:
- `schema_type`: `tariel_filled_reference_bundle`
- `schema_version`: `1`
- `family_key`: `nr12_apreciacao_risco_maquina`
- `template_code`: `nr12_apreciacao_risco_maquina`
- `source_kind`: `synthetic_repo_baseline`
- incluir `reference_summary`, `required_slots_snapshot`, `documental_sections_snapshot`, `notes` e `laudo_output_snapshot`

Slots obrigatorios a representar no bundle:
- `slot_referencia_principal`: Referencia principal
- `slot_evidencia_execucao`: Evidencia de execucao
- `slot_evidencia_principal`: Evidencia principal
- `slot_documento_base`: Documento base
- `slot_conclusao_servico`: Conclusao do servico

Secoes esperadas no documento final:
- Identificacao do Objeto
- Escopo do Servico
- Execucao do Servico
- Evidencias e Anexos
- Documentacao e Registros
- Nao Conformidades ou Lacunas
- Recomendacoes
- Conclusao

No final:
- gere os arquivos prontos;
- compacte tudo em um ZIP;
- nao responda com pseudocodigo nem explicacao longa.
```
