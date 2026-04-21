# Pacote de Referencia

Familia: `nr13_calculo_pmta_vaso_pressao`

Depois da triagem do material bruto, esta pasta deve receber a consolidacao do pacote que sera usado para derivar blueprints e, quando aplicavel, importar referencias preenchidas.

Contrato esperado pelo importador atual de filled_reference:
- arquivo `manifest.json`
- arquivo `tariel_filled_reference_bundle.json`
- anexos auxiliares que o bundle referenciar

Script de importacao existente:
- `web/scripts/importar_referencias_preenchidas_zip.py`
