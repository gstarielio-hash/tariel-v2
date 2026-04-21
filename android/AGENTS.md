# AGENTS - Android

## Fonte de verdade

- ordem de execução: `/home/gabriel/Área de trabalho/Tarie 2/docs/migration/PLAN_MASTER.md`
- critério de aceite: `/home/gabriel/Área de trabalho/Tarie 2/docs/migration/ACCEPTANCE_MATRIX.md`
- baseline: `/home/gabriel/Área de trabalho/Tarie 2/docs/migration/CI_BASELINE.md`
- mapa do repo: `../PROJECT_MAP.md`

## Comandos obrigatórios

- `make mobile-ci`
- `make smoke-mobile`

## Regra prática

- tratar `InspectorMobileApp.tsx` como hotspot até ele ser quebrado em módulos;
- qualquer mudança em sync/offline precisa deixar retry e erro visíveis;
- qualquer mudança em contrato mobile precisa atualizar teste/fixture;
- não versionar artefato local de execução.
