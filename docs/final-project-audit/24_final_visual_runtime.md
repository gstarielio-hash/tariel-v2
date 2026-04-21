# 24. Final Visual Runtime

## Data da execucao

- 2026-04-05

## Runtime visual oficial final

O runtime oficial web do `/app` fica explicitamente concentrado em:

- `web/templates/index.html`
- `web/templates/inspetor/base.html`
- `web/static/css/shared/global.css`
- `web/static/css/shared/material-symbols.css`
- `web/static/css/inspetor/tokens.css`
- `web/static/css/shared/app_shell.css`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`
- `web/static/js/shared/trabalhador_servico.js`

## O que define o runtime final

- `web/templates/index.html` continua sendo o entrypoint HTML do inspetor
- `web/templates/inspetor/base.html` e o unico shell SSR vivo do `/app`
- `web/static/js/shared/trabalhador_servico.js` agora expõe apenas `PIPELINE_RUNTIME_OFICIAL`
- o service worker nao lista mais bundles legados aposentados

## Prova objetiva consolidada

- `rg -n 'extends "base.html"' web/templates` -> nenhum consumidor ativo do entrypoint antigo
- `rg -n 'TemplateResponse\\(.*base.html|\"base.html\"' web/app` -> nenhuma rota viva renderizando o entrypoint antigo
- `web/tests/test_smoke.py` agora protege a inexistencia fisica de:
  - `web/templates/base.html`
  - `web/static/css/shared/layout.css`
  - `web/static/css/chat/chat_base.css`
  - `web/static/css/chat/chat_mobile.css`
  - `web/static/css/inspetor/workspace.css`
- `web/tests/e2e/test_portais_playwright.py::test_e2e_css_versionado_e_tipografia_base_ativa` confirma que o `/app` nao carrega mais esses assets

## Estado final dos bundles antigos

Removidos fisicamente:

- `web/templates/base.html`
- `web/static/css/shared/layout.css`
- `web/static/css/chat/chat_base.css`
- `web/static/css/chat/chat_mobile.css`
- `web/static/css/chat/chat_index.css`
- `web/static/css/inspetor/shell.css`
- `web/static/css/inspetor/home.css`
- `web/static/css/inspetor/modals.css`
- `web/static/css/inspetor/profile.css`
- `web/static/css/inspetor/mesa.css`
- `web/static/css/inspetor/responsive.css`
- `web/static/css/inspetor/workspace.css`

Mantidos no runtime final:

- `web/static/css/inspetor/reboot.css`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`

## Leitura final

O produto saiu da fase de coexistencia entre shell antigo e shell novo. O `/app` oficial agora depende apenas do runtime canonico do inspetor e dos slices extraidos ao longo da trilha de padronizacao.

## Proximo passo recomendado

`rotina curta de higiene documental e consolidação de debt técnico restante fora da trilha visual`
