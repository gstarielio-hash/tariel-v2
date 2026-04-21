# PROJECT MAP

Mapa curto do sistema vivo Tariel.

Atualizado em `2026-04-18`.

## Regra principal

Referencias locais atuais:

- `docs/STATUS_CANONICO.md`
- `PLANS.md`
- `docs/roadmap_execucao_funcional_web_mobile.md`
- `docs/restructuring-roadmap/131_dual_entry_resume_checkpoint.md`

Execução oficial:

- `/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado`

Não abrir frente nova antes de checar baseline.
- Quando houver risco de desatualizacao ou dependencia externa relevante, consultar a web antes de concluir a leitura tecnica ou a decisao de implementacao.
- Downloads necessarios para execucao, validacao ou ingestao operacional da frente atual sao permitidos.

## Linha de largada

Rodar nesta ordem:

```bash
cd "/home/gabriel/Área de trabalho/TARIEL/Tariel Control Consolidado"
git status --short
make verify
```

## Pastas principais

- `web/`: backend FastAPI, portais web, templates, JS, CSS e testes Python.
- `android/`: app mobile do inspetor, config de rollout, testes e automações.
- `docs/`: auditorias, roadmap, arquitetura, visual system e handoffs.
- `scripts/`: scripts de operação, smoke, rollout e suporte ao desenvolvimento.
- `artifacts/`: evidências e saídas de execução que precisam de política clara de retenção.

## Onde entrar por assunto

### Backend compartilhado

- `web/main.py`
- `web/app/core/settings.py`
- `web/app/core/http_runtime_support.py`
- `web/app/shared/database.py`
- `web/app/shared/security.py`
- `web/app/shared/tenant_access.py`

### Inspetor web

- backend:
  - `web/app/domains/chat/laudo.py`
  - `web/app/domains/chat/chat_stream_routes.py`
  - `web/app/domains/chat/chat_aux_routes.py`
  - `web/app/domains/chat/mesa.py`
- templates:
  - `web/templates/inspetor/_portal_home.html`
  - `web/templates/inspetor/_sidebar.html`
  - `web/templates/inspetor/_workspace.html`
- frontend:
  - `web/static/js/chat/chat_index_page.js`
  - `web/static/js/chat/chat_painel_core.js`
  - `web/static/js/chat/chat_sidebar.js`
  - `web/static/js/inspetor/notifications_sse.js`
  - `web/static/css/inspetor/tokens.css`

### Mesa SSR atual

- `web/app/domains/revisor/panel.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/app/domains/revisor/realtime.py`
- `web/templates/painel_revisor.html`
- `web/static/js/revisor/painel_revisor_page.js`

### Mobile

- `android/src/features/InspectorMobileApp.tsx`
- `android/src/features/common/`
- `android/src/features/chat/`
- `android/src/features/history/`
- `android/src/config/`
- `android/src/settings/`

### Cliente e admin

- cliente:
  - `web/app/domains/cliente/`
  - `web/templates/cliente_portal.html`
- admin:
  - `web/app/domains/admin/`
  - `web/templates/admin/dashboard.html`
  - `web/templates/admin/clientes.html`

### Documento, template e IA

- `web/app/domains/revisor/templates_laudo_management_routes.py`
- `web/app/domains/revisor/templates_laudo_support.py`
- `web/app/v2/document/`
- `web/app/domains/chat/learning.py`

## Estado conhecido em 2026-04-18

- `web-ci`, `mobile-ci` e `make verify` continuam como baseline local principal do repositório.
- a Mesa oficial foi consolidada no `SSR` do `web/`; o frontend paralelo legado foi arquivado.
- frentes ativas rastreadas neste checkout:
  - `PKT-CATALOGO-TEMPLATES-01`
  - `PKT-LAUDOS-01`
- ponto de retomada mais útil hoje:
  - observabilidade explícita do rollout de `report pack` antes de ampliar cobertura para novas famílias

## Arquivos de apoio mais úteis

- `README.md`
- `AGENTS.md`
- `docs/roadmap_execucao_funcional_web_mobile.md`
- `docs/tariel_visual_system.md`
- `docs/full-system-audit/README.md`
- `web/docs/inspector-understanding-packet/README.md`
- `android/README.md`

## Regras de navegação

- se o problema é de permissão, sessão ou tenant, comece por `web/app/shared/`;
- se o problema é de um botão do inspetor, siga: template -> JS -> rota -> service -> persistência;
- se o problema é de uma tela da Mesa, parta do `SSR` em `web/app/domains/revisor/` e `web/templates/painel_revisor.html`;
- se o problema é visual, confirme antes qual sistema de tokens está sendo usado e se ele converge para o padrão oficial;
- se o problema é rollout mobile, leia config, runtime e evidências antes de mexer na UI.
