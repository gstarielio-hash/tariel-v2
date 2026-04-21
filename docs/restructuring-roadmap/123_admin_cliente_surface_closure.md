# Admin-Cliente - fechamento da superficie canonica

Criado em `2026-03-31`.

## Objetivo

Registrar o encerramento do pacote estrutural do portal `admin-cliente` no repositorio principal, depois da traducao do gap de produto para codigo real.

## O que ficou fechado

- governanca comercial do tenant ficou limitada a `preview + registro de interesse`, sem mutacao direta de plano;
- gestao de usuarios do tenant ficou restrita a `inspetor` e `revisor`, sem autoprovisionamento padrao de outro `admin_cliente`;
- login cliente passou a anunciar apenas capacidades reais do produto;
- residuos semanticos de `Admin-CEO` e da camada `temporaryCompat` foram drenados do portal cliente;
- a superficie administrativa foi reorganizada no mesmo endpoint em blocos explicitos de:
  - empresa e capacidade;
  - trilha comercial;
  - equipe operacional;
  - suporte e auditoria.
- `chat` e `mesa` deixaram de ser pilhas de blocos na mesma malha e passaram a operar como `workspace` com `rail + workbench`;
- o visual do portal cliente passou a usar CSS dedicado por superficie, com base compartilhada e camadas proprias para:
  - `portal_workspace.css`;
  - `portal_admin_surface.css`;
  - `portal_chat_surface.css`;
  - `portal_mesa_surface.css`.

## Hotspots consolidados

- `web/app/domains/cliente/management_routes.py`
- `web/app/domains/cliente/dashboard.py`
- `web/app/domains/cliente/dashboard_bootstrap.py`
- `web/app/domains/cliente/dashboard_bootstrap_shadow.py`
- `web/app/domains/cliente/dashboard_bootstrap_support.py`
- `web/templates/login_cliente.html`
- `web/templates/cliente_portal.html`
- `web/static/css/cliente/cliente_auth.css`
- `web/static/css/cliente/portal.css`
- `web/static/css/cliente/portal_workspace.css`
- `web/static/css/cliente/portal_admin_surface.css`
- `web/static/css/cliente/portal_chat_surface.css`
- `web/static/css/cliente/portal_mesa_surface.css`
- `web/static/js/cliente/portal.js`
- `web/static/js/cliente/portal_admin.js`
- `web/static/js/cliente/portal_bindings.js`
- `web/app/v2/adapters/tenant_admin_bootstrap.py`

## Validacao executada

Rodada focal:

```bash
pytest tests/test_cliente_portal_critico.py tests/test_cliente_route_support.py tests/test_portais_acesso_critico.py tests/test_smoke.py tests/test_v2_tenant_admin_projection.py -q
```

Resultado:

- `56 passed`

Recorte Playwright do portal unificado:

```bash
env RUN_E2E=1 pytest tests/e2e/test_portais_playwright.py -q -k 'admin_provisiona_admin_cliente_e_portal_unificado_funciona or admin_ceo_cria_empresa_ilimitada or admin_cliente_isola_empresas_no_portal_unificado' -rs
```

Resultado:

- `3 passed, 33 deselected`

## O que nao entra neste fechamento

- `modo suporte` operacional do `admin-geral` dentro do tenant;
- redesign premium amplo do portal cliente;
- reabertura de governanca global ou visao cross-tenant no `admin-cliente`.

## Leitura final

O `admin-cliente` fica encerrado como console administrativo de tenant. O que sobra daqui para frente deixa de ser correcao estrutural do papel do portal e passa a ser evolucao pontual de UX, operacao assistida e politicas de suporte da Tariel.

Follow-up operacional fechado em `2026-04-01`: `docs/restructuring-roadmap/124_admin_cliente_policy_completion.md`.
