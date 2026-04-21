# Pacote de Referencia

Familia: `nr10_inspecao_instalacoes_eletricas`

Depois da triagem do material bruto, esta pasta deve receber a consolidacao do pacote que sera usado para derivar blueprints e, quando aplicavel, importar referencias preenchidas.

Contrato esperado:
- arquivo `manifest.json`
- arquivo `tariel_filled_reference_bundle.json`
- anexos auxiliares que o bundle referenciar

Fluxo recomendado:
- gerar o pacote externo usando `../prompt_chatgpt_pro_nr10_inspecao_instalacoes_eletricas.md`
- salvar o ZIP bruto em `../coleta_entrada/referencia_sintetica_externa/`
- promover `manifest.json`, `tariel_filled_reference_bundle.json`, `assets/` e `pdf/` para esta pasta
