# Portfolio Nacional de NRs: Provisionamento

## Escopo

Este documento registra o estado do provisionamento nacional da biblioteca Tariel por ondas a partir de:

- `docs/roadmap_nrs_brasil.md`
- `docs/nr_programming_registry.json`
- `web/docs/portfolio_nacional_nrs_artefatos.md`

## Estado consolidado em 2026-04-10

- `48` famílias vendáveis do roteiro nacional provisionadas no catálogo/Admin-CEO.
- `45` templates nacionais `v2` homologados nas ondas `1`, `2` e `3`.
- `3` templates nacionais já existentes reaproveitados durante o rollout.
- `69` famílias publicadas no catálogo local após a consolidação.
- `69` releases de família ativos para a empresa piloto.
- `69` releases de template ativos para a empresa piloto.
- `116` templates totais no tenant piloto após provisionamento e homologações.
- `51` templates ativos no tenant piloto ao final do fechamento nacional.
- `54` documentos finais emitidos no tenant piloto como trilha demo de homologação.

## Regra de rollout

- templates já ativos do piloto são preservados por padrão no provisionamento nacional;
- famílias novas entram em `em_teste`;
- apenas famílias já homologadas permanecem `ativo`;
- o rollout nacional scaffolda produto e catálogo, não substitui a homologação técnica família por família.

## Templates preservados como ativos

- `nr13_vaso_pressao`
- `nr13_caldeira`
- `nr13_inspecao_tubulacao`
- `nr13_integridade_caldeira`
- `nr13_teste_hidrostatico`
- `nr13_teste_estanqueidade_tubulacao_gas`

## Comando de provisionamento

```bash
python3 web/scripts/provision_national_nr_portfolio.py \
  --empresa-id 1 \
  --admin-email admin@tariel.ia
```

## Resultado operacional

- O catálogo local agora cobre todas as ondas programadas do registro nacional.
- As ondas `1`, `2` e `3` ficaram homologadas com promoção controlada para `ativo`.
- A onda `4` foi encerrada como governança, sem criação de templates vendáveis.
- `NR-2` e `NR-27` permanecem fora do catálogo vendável por estarem revogadas.
- Itens marcados como `support_only` no registro continuam fora do provisionamento automático.
- Os fechamentos canônicos estão registrados em:
  `web/docs/onda_1_homologacao_profissional.md`,
  `web/docs/onda_2_homologacao_profissional.md`,
  `web/docs/onda_3_homologacao_profissional.md` e
  `web/docs/onda_4_fechamento_governanca.md`.

## Próxima regra de execução

- refinar variantes comerciais dentro das famílias já homologadas;
- substituir base sintética por material real onde houver acervo;
- manter a trilha premium crítica de `NR13`, `NR12`, `NR20` e `NR33` já bootstrapada com baseline sintética interna, conforme `web/docs/fila_prioritaria_nrs_material_real.md`;
- manter a regra de caso demo + checklist de qualidade antes de qualquer promoção comercial nova.
