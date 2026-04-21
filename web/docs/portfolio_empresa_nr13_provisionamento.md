# Portfolio Empresa NR13: Provisionamento

Fonte de verdade:
- `docs/family_schemas/*.json` define as familias canonicas.
- `docs/family_schemas/*.laudo_output_seed.json` define o contrato vazio do caso.
- `docs/family_schemas/*.laudo_output_exemplo.json` valida render e emissao.
- `docs/family_schemas/*.template_master_seed.json` define o `template_master` inicial.

Geracao em lote:
- script: `web/scripts/generate_empresa_nr13_portfolio.py`
- saida atual: 24 familias canonicas para a carteira real da empresa

Provisionamento em lote:
- servico: `app.domains.admin.services.provisionar_familias_canonicas_empresa`
- script: `web/scripts/provision_empresa_nr13_portfolio.py`
- portal Admin-CEO:
  - `/admin/catalogo-laudos` -> `Importar portfolio canonico completo`
  - `/admin/clientes/{empresa_id}` -> `Provisionar portfolio canonico`

Politica operacional atual:
- familias publicadas no catalogo: todas
- familias liberadas por empresa: todas
- templates liberados por empresa: 1 por familia canonica
- status padrao fora da onda imediata: `em_teste`

Onda operacional imediata:
- `nr13_inspecao_vaso_pressao`
- `nr13_inspecao_caldeira`
- `nr13_inspecao_tubulacao`
- `nr13_integridade_caldeira`
- `nr13_teste_hidrostatico`
- `nr13_teste_estanqueidade_tubulacao_gas`

Estado aplicado no piloto local em `2026-04-08`:
- empresa `1`
- banco local: `web/tariel_admin (1).db`
- backup local anterior ao lote: `web/tariel_admin (1).db.bak_portfolio_2026-04-08`
- familias no catalogo: `24`
- familias liberadas para empresa `1`: `24`
- templates da empresa `1`: `26`
- templates ativos da empresa `1`: `6`

Observacao:
- `nr13_inspecao_vaso_pressao` e `nr13_inspecao_caldeira` preservam alias legado de template (`nr13_vaso_pressao` e `nr13_caldeira`).
- as demais familias novas operam com `template_code` igual ao `family_key`.
