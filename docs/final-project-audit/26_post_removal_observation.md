# 26. Post-Removal Observation

## Data da execucao

- 2026-04-05

## Objetivo da fase

- observar o runtime oficial depois da remocao fisica final do legado visual
- provar ausencia de dependencia interna viva dos assets removidos
- registrar qualquer comportamento residual antes de encerrar definitivamente a trilha antiga

## Artefatos desta fase

- `artifacts/final_visual_post_removal/20260405_074453/runtime_observation_matrix.json`
- `artifacts/final_visual_post_removal/20260405_074453/visual_inventory_after.json`
- `artifacts/final_visual_post_removal/20260405_074453/source_inventory_after.json`
- `artifacts/final_visual_post_removal/20260405_074453/source_index.txt`
- `artifacts/final_visual_post_removal/20260405_074453/screenshots_after/`
- `artifacts/final_visual_post_removal/20260405_074453/runtime_reference_scan.txt`
- `artifacts/final_visual_post_removal/20260405_074453/removed_assets_404.json`

## Superficies observadas

- `/admin`
- `/cliente`
- `/app`
- `/revisao`

O inventario after desta fase recapturou:

- `admin_login`, `admin_dashboard`, `admin_clients`
- `cliente_login`, `cliente_admin`, `cliente_chat`, `cliente_mesa`
- `app_login`, `app_home`, `app_workspace`, `app_workspace_mesa`
- `revisao_login`, `revisao_painel`, `revisao_templates_biblioteca`, `revisao_templates_editor`

## Resultado objetivo da observacao

### Runtime oficial

O runtime observado permaneceu coerente com o estado final aprovado:

- `/app` carregou apenas `global.css`, `material-symbols.css`, `tokens.css`, `app_shell.css`, `reboot.css`, `official_visual_system.css` e os slices `workspace_{chrome,history,rail,states}.css`
- `/cliente` carregou `portal_*.css` e `official_visual_system.css`
- `/revisao` carregou `painel_revisor.css` ou `templates_*.css` junto de `official_visual_system.css`
- `/admin` carregou `admin*.css` junto de `official_visual_system.css`

Em nenhum shot do inventario `after` foi detectado carregamento de:

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

### Confirmacao de nao-uso interno

- `runtime_reference_scan.txt` zerou matches no codigo/runtime para os caminhos removidos
- `runtime_observation_matrix.json` registrou `matches: 0`
- os arquivos removidos continuam ausentes fisicamente do repositório

### Requests diretos aos caminhos aposentados

O check direto sem sessao autenticada registrou:

- `302 -> /app/login` para os caminhos removidos

Leitura correta:

- o acesso direto sem sessao cai no guard global do portal
- isso nao reabre o legado visual nem prova asset servido
- a prova principal continua sendo: inexistencia fisica + zero referencias internas + zero carregamento no inventario das superficies oficiais

## Validacao executada

- `cd web && ./.venv-linux/bin/python -m py_compile scripts/final_visual_audit.py` -> ok
- `cd web && ./.venv-linux/bin/python scripts/final_visual_audit.py --stage after --output-root ../artifacts/final_visual_post_removal/20260405_074453` -> ok
- `make verify` -> ok
- `make mesa-smoke` -> ok
- `make mesa-acceptance` -> ok

## Conclusao desta fase

- nao houve regressao observada no runtime oficial das superfícies web ativas
- nao apareceu dependencia interna viva dos assets visuais removidos
- o legado visual antigo permaneceu encerrado do ponto de vista de runtime
- a unica observacao residual relevante e o redirect de acesso sem sessao para `/app/login`, que pertence ao guard global e nao ao pipeline visual aposentado

## Proximo passo recomendado

`encerramento da trilha visual antiga e retomada de debt técnico fora do eixo visual`
