# 19. App and Mesa Componentization

## Resumo executivo

Esta fase consolidou a implementacao nativa do visual aprovado no `/app` e nos blocos da Mesa dentro do inspetor. O foco nao foi abrir feature nova, e sim trocar ownership: sair de blocos grandes e difusos em folhas legacy para slices canonicos menores, com entrada clara no template base do inspetor.

## Recorte funcional preservado

Os fluxos oficiais preservados nesta fase foram:

- `/app/`
- `/app/?laudo=1&aba=conversa`
- `/app/?laudo=2&aba=mesa`
- `/revisao/painel`
- `/revisao/templates-laudo`

Os testes e screenshots foram regenerados sobre esse recorte.

## O que foi componentizado de verdade

### Chrome do workspace

Agora o topo operacional do laudo vive em um slice proprio:

- header do laudo
- tabs
- toolbar
- pequenos badges e acoes
- hero strip e resumo rapido

Esse ownership sai dos hotspots antigos e entra em `web/static/css/inspetor/workspace_chrome.css`.

### Rail operacional e Mesa

Agora a rail do inspetor e o card de mesa vivem em outro slice:

- cards laterais
- progresso
- pendencias
- facts de contexto
- chips e status da mesa

Esse ownership sai dos hotspots antigos e entra em `web/static/css/inspetor/workspace_rail.css`.

### Estados compartilhados do workspace

Agora os estados visuais mais repetidos tambem tem slice proprio:

- empty states
- actions pequenas de mensagem
- shell do composer
- estados focados da conversa

Esse ownership fica em `web/static/css/inspetor/workspace_states.css`.

## Impacto sobre os hotspots obrigatorios

### `web/static/css/inspetor/reboot.css`

- reduziu `962` linhas nesta fase
- perdeu ownership de chrome, rail e progresso
- ficou mais proximo de uma camada estrutural de suporte

### `web/static/css/inspetor/workspace.css`

- reduziu `489` linhas nesta fase
- deixou de ser a fonte principal do topo e dos estados canonicos
- permaneceu como compatibilidade e layout residual

### `web/static/css/chat/chat_base.css`

- reduziu `301` linhas nesta fase
- teve removido o bloco ativo antigo do workspace do inspetor
- ficou explicitamente tratado como legado fora do runtime oficial do `/app`

### `web/static/js/chat/chat_index_page.js`

- reduziu acoplamento visual adicional
- trocou controle por classe morta para `dataset`
- moveu o percentual do progresso para custom property CSS

## Evidencia de componentizacao

- `web/templates/inspetor/base.html` passou a carregar os tres slices novos
- templates do inspetor receberam `data-component-slice` para explicitar ownership
- `artifacts/final_visual_componentization/20260404_211656/screenshots_after/` capturou o after do `/app` e da Mesa
- `artifacts/final_visual_componentization/20260404_211656/component_slices_matrix.json` registra a matriz de ownership desta fase

## O que ainda depende de legado

- regras residuais do historico e alguns detalhes de shell ainda seguem em `reboot.css`
- responsividade antiga e partes de layout ainda seguem em `workspace.css`
- `chat_base.css` ainda precisa de desativacao controlada por inventario completo de dependencias nao-oficiais

## Proximo passo recomendado

`Desativacao controlada do legado nao-runtime e fechamento da componentizacao do historico`
