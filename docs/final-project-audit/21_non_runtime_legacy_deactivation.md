# 21. Non-Runtime Legacy Deactivation

## Data da execucao

- 2026-04-04

## Escopo da desativacao controlada

Esta fase tratou explicitamente o legado nao-runtime ligado ao antigo visual do chat sem apagar CSS no escuro. O alvo principal foi `web/static/css/chat/chat_base.css`, porque o arquivo ainda carregava uma familia visual antiga que ja nao participa das superficies oficiais.

## Prova de runtime oficial

As evidencias usadas para a desativacao foram:

- `web/templates/index.html` continua estendendo `web/templates/inspetor/base.html`
- `rg -n 'extends "base.html"' web/templates` nao encontrou nenhum template ativo usando `web/templates/base.html`
- `web/templates/inspetor/base.html` nao carrega `chat_base.css` nem `workspace.css`
- `web/static/js/shared/trabalhador_servico.js` tambem nao precacheia `chat_base.css` nem `workspace.css`
- `artifacts/final_visual_history_closure/20260404_220125/visual_inventory_after.json` confirma que os shots oficiais do `/app` carregam apenas o pipeline canonicamente aprovado

## O que foi desativado

Em `web/static/css/chat/chat_base.css`:

- a familia `body.pagina-chat-luminous` foi removida do CSS ativo
- o arquivo ganhou comentario explicito marcando esse bloco como legado nao-runtime desativado
- o delta do arquivo nesta fase foi `5375 -> 4536` linhas
- a reducao foi de `839` linhas

Esse corte foi seguro porque nao existe template, JS nem body class ativa produzindo `pagina-chat-luminous` nas superficies canonicas auditadas.

## O que ainda ficou e por que

### `web/templates/base.html`

O entrypoint legado ainda referencia:

- `web/static/css/chat/chat_base.css`
- `web/static/css/inspetor/workspace.css`

Ele nao foi apagado nesta fase porque a estrategia pedida foi de desativacao controlada, nao de destruicao cega. Hoje, porem, ele nao participa do runtime oficial do `/app`.

### `web/static/css/shared/layout.css`

O arquivo ainda contem seletores `body.pagina-chat-luminous`. Esse legado nao foi removido agora porque:

- ele nao esta no hotspot obrigatorio principal desta fase
- ele nao entra no runtime oficial do inspetor
- a remocao final precisa acontecer junto da aposentadoria formal do entrypoint legado

## Como a fase reduz risco

- o runtime oficial ficou ainda menos dependente do legado antigo
- a componentizacao do historico passou a ter ownership claro em arquivo proprio
- o legado remanescente ficou explicitamente catalogado, em vez de escondido em folhas grandes

## Risco residual honesto

- `base.html` ainda existe como entrada antiga e pode sustentar usos nao canonicos fora do recorte oficial
- `shared/layout.css` ainda guarda o cluster `pagina-chat-luminous` que deve sair junto do desligamento final do entrypoint legado

## Proximo passo recomendado

`aposentadoria controlada do entrypoint legado base.html e remocao final do cluster pagina-chat-luminous fora do runtime oficial`
