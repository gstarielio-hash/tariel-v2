# 25. Physical Legacy Removal

## Data da execucao

- 2026-04-05

## Escopo da fase

Esta fase executou a remocao fisica final dos placeholders legados que tinham permanecido apenas como compatibilidade temporaria na etapa anterior.

## Arquivos removidos fisicamente

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

## Criterio usado para remover

Os arquivos acima so podiam sair se houvesse prova objetiva de nao-uso real. Essa prova foi confirmada por:

- ausencia de renderizacao viva no backend
- ausencia de `extends` ativos em templates
- ausencia no `ARQUIVOS_NUCLEO` do service worker
- ausencia no pipeline carregado pelo `/app` nos screenshots e inventarios after

## Saneamento de bundles órfãos

### `chat_mobile.css`

Decisao final: removido.

Motivo:

- nao havia template vivo carregando o arquivo
- nao havia JS vivo referenciando o arquivo
- o runtime oficial do inspetor ja distribuia responsividade em `reboot.css` e nos slices canonicos

### `chat_index.css` e antigos `inspetor/{shell,home,modals,profile,mesa,responsive}.css`

Decisao final: removidos.

Motivo:

- nao havia template vivo referenciando esses bundles
- nao havia service worker nem boot oficial usando esses caminhos
- os arquivos passaram a existir apenas como resíduo de migração

### `layout.css`, `chat_base.css`, `workspace.css`

Decisao final: removidos.

Motivo:

- nao havia rota oficial servindo esses caminhos
- os arquivos tinham virado apenas placeholders nao-runtime
- sua existencia passou a ser mais ruido do que protecao

## O que restou e por que

Restou como legado visual historico apenas o registro documental da trilha:

- auditorias e relatórios em `docs/final-project-audit/`
- journals de execução em `docs/restructuring-roadmap/99_execution_journal.md`

No runtime oficial, nao restou bundle legado antigo ativo nem placeholder fisico dos hotspots tratados.

## Efeito no repositório

- menos ambiguidade sobre qual shell e oficial
- menos risco de reintroduzir CSS antigo por engano
- menos lixo tecnico visual em busca, diff e manutenção

## Proximo passo recomendado

`consolidação final dos docs históricos que ainda citam o pipeline antigo como contexto passado`
