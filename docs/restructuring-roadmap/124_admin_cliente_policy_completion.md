# Admin-Cliente - fechamento operacional de visibilidade, suporte e auditoria

Criado em `2026-04-01`.

## Objetivo

Fechar o residual operacional que sobrou depois do encerramento estrutural do portal `admin-cliente`, sem reabrir a tese de `admin-geral` operando "por dentro" do tenant.

## O que entrou

- a `visibility_policy` do `TenantAdminViewProjectionV1` deixou de ser placeholder e passou a refletir a politica final de visibilidade do tenant;
- o modo tecnico do `admin-cliente` ficou explicitado como `surface_scoped_operational`, mantendo evidencia bruta fora da projecao gerencial;
- o `admin-geral` ganhou abertura e encerramento auditavel de suporte excepcional por tenant, com `step-up`, justificativa, referencia de aprovacao e janela maxima controlada;
- a trilha de auditoria do tenant passou a carregar `categoria` e `scope`, com resumo agregado no bootstrap, na API e no diagnostico do portal cliente;
- a tela de detalhe do tenant no `Admin-CEO` passou a exibir politica de visibilidade, estado atual do suporte excepcional e timeline classificada do portal cliente;
- o portal cliente passou a explicitar melhor, na superficie de suporte, que o diagnostico exportado nao concede evidencia bruta por padrao.

## Regras que ficaram valendo

- `admin-cliente` continua restrito a visao gerencial e operacional por superficie;
- `support exceptional` continua governado pelo `admin-geral`, nunca como navegacao paralela dentro do `/cliente`;
- leitura tecnica bruta continua fora da projecao administrativa do tenant;
- auditoria do tenant passa a ser tratada como `tenant_operational_timeline`, com recortes por `admin`, `chat`, `mesa` e `support`.

## Hotspots fechados nesta rodada

- `web/app/v2/contracts/tenant_admin.py`
- `web/app/domains/cliente/dashboard_bootstrap_shadow.py`
- `web/app/domains/cliente/auditoria.py`
- `web/app/domains/cliente/dashboard_bootstrap.py`
- `web/app/domains/cliente/management_routes.py`
- `web/app/domains/cliente/diagnostics.py`
- `web/app/domains/admin/services.py`
- `web/app/domains/admin/client_routes.py`
- `web/templates/admin/cliente_detalhe.html`
- `web/templates/cliente/painel/_support.html`
- `web/static/js/cliente/portal_admin_surface.js`

## Validacao executada

Rodada ampla:

```bash
pytest tests/test_cliente_portal_critico.py tests/test_cliente_route_support.py tests/test_portais_acesso_critico.py tests/test_smoke.py tests/test_v2_tenant_admin_projection.py tests/test_admin_client_routes.py tests/test_session_auth_audit_matrix.py -q
```

Resultado:

- `79 passed`

Recorte browser do portal unificado:

```bash
env RUN_E2E=1 pytest tests/e2e/test_portais_playwright.py -q -k 'admin_provisiona_admin_cliente_e_portal_unificado_funciona or admin_cliente_isola_empresas_no_portal_unificado or admin_cliente_deep_links_por_secao_preservam_shell_e_historico' -rs
```

Resultado:

- `3 passed, 34 deselected`

## O que continua fora

- `modo suporte` navegavel do `admin-geral` dentro do tenant;
- redesign premium amplo do portal cliente;
- qualquer reabertura de visao cross-tenant dentro do `admin-cliente`.

## Leitura final

O portal `admin-cliente` deixa de ter residual funcional aberto de governanca. O que sobra daqui para frente e endurecimento, UX fina e evolucao de produto, nao lacuna estrutural do papel do portal.

Follow-up premium local concluido em `2026-04-01`: `docs/restructuring-roadmap/125_admin_cliente_premium_ux_checkpoint.md`.
