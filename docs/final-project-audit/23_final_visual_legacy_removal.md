# 23. Final Visual Legacy Removal

## Data da execucao

- 2026-04-05

## Objetivo da fase

- remover o cluster visual antigo que ja nao participa do runtime oficial
- reduzir `shared/layout.css`, `chat_base.css` e `workspace.css` a placeholders nao-runtime
- provar que o `/app` oficial continua integro com o pipeline canonico

## Decisao sobre o cluster antigo

Decisao adotada: `removido`.

O cluster antigo remanescente em `web/static/css/shared/layout.css` foi removido do codigo ativo ao reduzir o arquivo a um placeholder deprecado sem seletores. Com isso, nao restou CSS executavel da familia visual antiga nos hotspots tratados.

## Arquivos tratados nesta fase

### `web/static/css/shared/layout.css`

- antes: `3199` linhas
- depois: `10` linhas
- estado final: placeholder nao-runtime

### `web/static/css/chat/chat_base.css`

- antes: `4536` linhas
- depois: `10` linhas
- estado final: placeholder nao-runtime

### `web/static/css/inspetor/workspace.css`

- antes: `2479` linhas
- depois: `5` linhas
- estado final: placeholder nao-runtime

### `web/static/js/shared/trabalhador_servico.js`

O service worker passou a explicitar dois grupos:

- `PIPELINE_RUNTIME_OFICIAL.css`
- `PIPELINE_RUNTIME_OFICIAL.cssRetired`

Com isso, o runtime oficial do `/app` fica declarado no proprio arquivo, e o legado aposentado fica apenas catalogado fora do `ARQUIVOS_NUCLEO`.

## Prova de runtime oficial

O runtime oficial do `/app` continua carregando apenas:

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

O inventario `after` desta fase e os testes atualizados confirmam que:

- `/app` nao carrega `shared/layout.css`
- `/app` nao carrega `chat/chat_base.css`
- `/app` nao carrega `inspetor/workspace.css`

## O que foi removido de verdade

- o cluster de seletores antigos do shell escuro e da familia visual antiga
- a injecao do pipeline legado por `base.html`
- a ultima justificativa para manter `layout.css`, `chat_base.css` e `workspace.css` como folhas vivas do runtime

## O que ficou

- os caminhos fisicos dos tres CSS foram mantidos como placeholders curtos para evitar 404 e permitir janela curta de observacao
- `chat_mobile.css` e outros bundles legados antigos permanecem no repositorio, mas fora do pipeline oficial

## Estado final do legado visual antigo

- fora do runtime oficial: sim
- cluster antigo executavel nos hotspots tratados: nao
- entrypoint antigo visualmente ativo: nao
- placeholders temporarios ainda existentes: sim

## Proximo passo recomendado

`remocao fisica final dos placeholders e atualizacao ampla da documentacao historica`
