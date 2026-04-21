# 22. Legacy Entrypoint Retirement

## Data da execucao

- 2026-04-05

## Decisao sobre `web/templates/base.html`

Decisao adotada nesta fase: `desativado`.

O arquivo deixou de ser um entrypoint visual com pipeline proprio e passou a ser apenas um shim:

- caminho mantido: `web/templates/base.html`
- runtime canonico apontado: `web/templates/inspetor/base.html`

Implementacao aplicada:

- o arquivo agora so contém comentario deprecado
- o template faz apenas `{% extends "inspetor/base.html" %}`
- o pipeline legado de CSS antigo nao e mais carregado por esse caminho

## Evidencia usada para a decisao

- `web/templates/index.html` continua estendendo `web/templates/inspetor/base.html`
- `rg -n 'extends "base.html"' web/templates` nao encontrou templates ativos usando `web/templates/base.html`
- `rg -n 'TemplateResponse\\(.*base.html|\"base.html\"' web/app` nao encontrou rota viva renderizando esse entrypoint
- o runtime oficial auditado do `/app` continua vindo de `web/templates/inspetor/base.html`

## Por que nao foi apagado

O arquivo nao foi apagado fisicamente nesta fase porque a regra foi de remocao controlada baseada em evidencia. O shim preserva o caminho para qualquer extensao nao auditada fora do recorte oficial, mas impede que o pipeline visual antigo continue sendo servido.

## Impacto pratico

Antes:

- `base.html` carregava `shared/layout.css`
- `base.html` carregava `chat/chat_base.css`
- `base.html` carregava `chat/chat_mobile.css`
- `base.html` carregava `inspetor/workspace.css`
- `base.html` carregava outros bundles antigos do inspetor

Depois:

- `base.html` herda o shell oficial do inspetor
- `base.html` nao injeta mais o pipeline legado
- qualquer extensao residual desse caminho cai no runtime canonico, nao no visual antigo

## Estado final do entrypoint antigo

- caminho: mantido
- ownership visual: aposentado
- status operacional: shim canônico
- risco residual: apenas dependencia fora do recorte auditado, se existir, herdara o visual oficial em vez do pipeline antigo

## Proximo passo recomendado

`janela curta de observacao e remocao fisica final dos placeholders legados`
