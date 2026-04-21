# Fase 07 - Cliente e admin: fechamento operacional

Data: `2026-03-30`

## Objetivo fechado

Promover a `Fase 07 - Cliente e admin` sem depender de comportamento oculto nos portais administrativos.

## O que entrou neste fechamento

- onboarding SaaS e onboarding de usuarios da empresa mantidos como trilho explicito e testado
- plano, limite, uso e upgrade mantidos como comportamento explicito no backend e no portal cliente
- resets e acoes administrativas criticas mantidos com `RBAC`, `CSRF`, tenant alvo explicito e trilha duravel
- auditoria do `admin-geral` agora exposta por rota e tela proprias em `/admin/auditoria`
- diagnostico exportavel por tenant no `admin-geral` em `/admin/clientes/{empresa_id}/diagnostico`
- diagnostico exportavel do portal cliente em `/cliente/api/diagnostico`
- relato de suporte do portal cliente em `/cliente/api/suporte/report`
- fronteira explicita entre `cliente`, `admin`, `chat` e `mesa` preservada com matriz de tenant e recortes company-scoped

## Superficies tocadas

- `web/app/domains/admin/routes.py`
- `web/app/domains/admin/client_routes.py`
- `web/app/domains/admin/auditoria.py`
- `web/app/domains/cliente/management_routes.py`
- `web/app/domains/cliente/dashboard_bootstrap.py`
- `web/app/domains/cliente/diagnostics.py`
- `web/templates/admin_auditoria.html`
- `web/templates/cliente_detalhe.html`
- `web/templates/cliente_portal.html`
- `web/static/js/cliente/portal_admin.js`

## Validacao local

- `pytest` focal de `admin`, `cliente`, `tenant boundary`, `session/auth/audit` e contratos `v2` verde
- recorte de `test_smoke.py` para portais `cliente/admin/multiportal` verde

## Resultado

Com este slice:

- o `admin-geral` deixa de depender de auditoria invisivel para ler a trilha critica
- o `admin-cliente` ganha trilho explicito de suporte e exportacao de diagnostico
- a `Fase 07` pode ser promovida sem esconder lacunas operacionais dos portais administrativos
- a frente principal volta para `Fase 08 - Mobile`
