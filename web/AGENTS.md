# AGENTS - Web

## Fonte de verdade

- ordem de execução: `/home/gabriel/Área de trabalho/Tarie 2/docs/migration/PLAN_MASTER.md`
- critério de aceite: `/home/gabriel/Área de trabalho/Tarie 2/docs/migration/ACCEPTANCE_MATRIX.md`
- baseline: `/home/gabriel/Área de trabalho/Tarie 2/docs/migration/CI_BASELINE.md`
- mapa do repo: `../PROJECT_MAP.md`

## Comandos obrigatórios

- `make web-ci`
- `make contract-check`
- `make smoke-web`

## Regra prática

- se o problema for de botão/fluxo do inspetor: siga `template -> JS -> rota -> service -> persistência`;
- se o problema for de auth/tenant/sessão: comece por `app/shared/`;
- não alterar contrato sem atualizar teste ou fixture;
- não abrir frente nova com `web-ci` quebrado.
