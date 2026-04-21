# Pacote de Referencia

Familia: `nr20_inspecao_instalacoes_inflamaveis`

Depois da triagem do material bruto, esta pasta deve receber a consolidacao do pacote que sera usado para derivar blueprints e, quando aplicavel, importar referencias preenchidas.

Contrato esperado pelo importador atual de filled_reference:
- arquivo `manifest.json`
- arquivo `tariel_filled_reference_bundle.json`
- anexos auxiliares que o bundle referenciar

Script de importacao existente:
- `web/scripts/importar_referencias_preenchidas_zip.py`

Fluxo recomendado para esta familia:
- primeiro consolidar material real e evidencias recorrentes da empresa
- se faltar base, usar o fallback externo em `../prompt_fallback_sintetica_externa_nr20_inspecao_instalacoes_inflamaveis.md`
- salvar o ZIP bruto em `../coleta_entrada/referencia_sintetica_externa/`
- promover `manifest.json`, `tariel_filled_reference_bundle.json`, `assets/` e `pdf/` para esta pasta
- depois importar ou derivar blueprints conforme a necessidade do runtime
