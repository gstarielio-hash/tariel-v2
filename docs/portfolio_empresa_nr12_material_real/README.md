# Portfolio Empresa NR12: Material Real

Workspace canonica para refino por material real da empresa.

## Regra

- cada familia tem um manifesto de coleta, um briefing de refino, uma area para material bruto e uma area para pacote de referencia;
- o objetivo aqui nao e guardar o family_schema; e fechar o gap entre a familia canonica e o jeito real como a empresa opera e escreve o documento;
- toda adaptacao do template final deve passar por essa workspace antes.

## Familias preparadas

| Wave | Family key | Kind | Pasta de trabalho |
| --- | --- | --- | --- |
| 1 | `nr12_apreciacao_risco_maquina` | `engineering` | `docs/portfolio_empresa_nr12_material_real/nr12_apreciacao_risco_maquina` |
| 1 | `nr12_inspecao_maquina_equipamento` | `inspection` | `docs/portfolio_empresa_nr12_material_real/nr12_inspecao_maquina_equipamento` |

## Fluxo curto

1. colocar o material bruto em `coleta_entrada/` da familia;
2. atualizar `status_refino.json` com o que chegou e o que ainda falta;
3. consolidar o pacote em `pacote_referencia/`;
4. usar o fallback sintetico externo apenas quando a familia ainda nao tiver base real suficiente;
5. so depois revisar template, linguagem e bind final do documento.
