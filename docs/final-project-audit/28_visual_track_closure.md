# 28. Visual Track Closure

## Data da execucao

- 2026-04-05

## Decisao formal

- a trilha visual antiga esta encerrada
- as superficies oficiais ativas permanecem `/admin`, `/cliente`, `/app` e `/revisao`
- `mesa-next` segue fora da superficie oficial ativa

## Runtime visual canonico final

### Superficies oficiais

- `/admin`
- `/cliente`
- `/app`
- `/revisao`

### Entrypoints visuais oficiais

- `/app`: `web/templates/index.html` com shell em `web/templates/inspetor/base.html`
- `/cliente`: templates SSR do portal cliente
- `/revisao`: templates SSR do revisor e do fluxo de templates
- `/admin`: templates SSR administrativos

### CSS e JS oficiais que sustentam o runtime

- compartilhado: `web/static/css/shared/global.css`, `web/static/css/shared/material-symbols.css`, `web/static/css/shared/app_shell.css`, `web/static/css/shared/official_visual_system.css`
- `/app`: `web/static/css/inspetor/tokens.css`, `web/static/css/inspetor/reboot.css`, `web/static/css/inspetor/workspace_chrome.css`, `web/static/css/inspetor/workspace_history.css`, `web/static/css/inspetor/workspace_rail.css`, `web/static/css/inspetor/workspace_states.css`
- `/cliente`: `web/static/css/cliente/portal_foundation.css`, `web/static/css/cliente/portal_components.css`, `web/static/css/cliente/portal_workspace.css`, `web/static/css/cliente/portal_admin_surface.css`, `web/static/css/cliente/portal_chat_surface.css`, `web/static/css/cliente/portal_mesa_surface.css`, `web/static/css/cliente/portal_admin_theme.css`
- `/revisao`: `web/static/css/revisor/painel_revisor.css`, `web/static/css/revisor/templates_biblioteca.css`, `web/static/css/revisor/templates_laudo.css`, `web/static/js/revisor/painel_revisor_page.js`
- `/admin`: `web/static/css/admin/admin_icons.css`, `web/static/css/admin/admin_auth_shell.css`, `web/static/css/admin/admin_login.css`, `web/static/css/admin/admin_dashboard.css`, `web/static/css/admin/admin_clients.css`
- service worker oficial: `web/static/js/shared/trabalhador_servico.js`

## O que saiu e nao deve voltar

Removidos fisicamente e sem dependencia interna viva:

- `web/templates/base.html`
- `web/static/css/shared/layout.css`
- `web/static/css/chat/chat_base.css`
- `web/static/css/chat/chat_mobile.css`
- `web/static/css/chat/chat_index.css`
- `web/static/css/inspetor/workspace.css`
- `web/static/css/inspetor/shell.css`
- `web/static/css/inspetor/home.css`
- `web/static/css/inspetor/modals.css`
- `web/static/css/inspetor/profile.css`
- `web/static/css/inspetor/mesa.css`
- `web/static/css/inspetor/responsive.css`

## Gates rerodados nesta consolidacao

- `make verify` -> ok
- `make mesa-smoke` -> ok
- `make mesa-acceptance` -> ok
- `make document-acceptance` -> ok
- `make observability-acceptance` -> ok
- `make smoke-mobile` -> ok
- `make final-product-stamp` -> ok

## Evidencia de fechamento

- a observacao pos-remocao registrou zero referencia interna viva aos assets removidos
- os gates web, mesa, documentais, observabilidade e mobile permaneceram verdes apos a convergencia visual
- o `final-product-stamp` manteve `final_product_status=ready_except_post_deploy_observation` e `mobile_v2_status=closed_with_guardrails`, mostrando que o remanescente de produto nao e visual

## Rastreabilidade historica mantida

Mantidos como trilha de auditoria, nao como superficie ativa:

- `docs/final-project-audit/13_visual_system_audit.md`
- `docs/final-project-audit/14_visual_system_canonic.md`
- `docs/final-project-audit/15_visual_standardization_rollout.md`
- `docs/final-project-audit/16_visual_hotspots_refactor.md`
- `docs/final-project-audit/17_visual_legacy_reduction.md`
- `docs/final-project-audit/18_visual_component_slices.md`
- `docs/final-project-audit/19_app_and_mesa_componentization.md`
- `docs/final-project-audit/20_inspector_history_componentization.md`
- `docs/final-project-audit/21_non_runtime_legacy_deactivation.md`
- `docs/final-project-audit/22_legacy_entrypoint_retirement.md`
- `docs/final-project-audit/23_final_visual_legacy_removal.md`
- `docs/final-project-audit/24_final_visual_runtime.md`
- `docs/final-project-audit/25_physical_legacy_removal.md`
- `docs/final-project-audit/26_post_removal_observation.md`
- `docs/final-project-audit/27_historical_docs_cleanup.md`
- `docs/restructuring-roadmap/99_execution_journal.md`

## Conclusao

- nao resta blocker visual real nas superficies oficiais
- o runtime visual canonico final esta estabilizado e registrado
- qualquer passo remanescente do produto pertence a observacao pos-deploy do cleanup automatico, fora do eixo do legado visual antigo
