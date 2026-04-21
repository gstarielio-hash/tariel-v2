# Overlay de Nova Inspeção

## Objetivo desta fase

Esta fase reorganizou apenas a integração visual e estrutural do fluxo "Nova Inspeção", sem alterar backend, contratos, validações, submit ou regras de negócio.

## Onde o overlay passou a ser montado

### Confirmado no código

- O host estrutural de overlays agora está em `web/templates/inspetor/base.html` como `#inspetor-overlay-host`.
- Esse host fica fora de `.container-app`, portanto fora do grid principal do inspetor.
- `web/templates/index.html` deixou de montar os modais dentro do bloco principal de conteúdo e passou a montá-los no bloco `overlay_host`.
- `#modal-nova-inspecao` continua existindo com o mesmo id, mas agora vive dentro do host explícito de overlays, no mesmo plano estrutural dos outros modais do inspetor.

## Como ele se integra ao screen mode

### Confirmado no código

- `web/static/js/chat/chat_index_page.js::resolveInspectorScreen()` continua retornando `new_inspection` quando `#modal-nova-inspecao` está aberto.
- Foi introduzido o conceito prático de "screen base" em `resolveInspectorBaseScreen()`.
- `sincronizarInspectorScreen()` agora separa:
  - `screen`: o modo dominante do sistema, que pode ser `new_inspection`
  - `baseScreen`: a tela de fundo real, que continua sendo `portal_dashboard`, `assistant_landing`, `inspection_record` ou `inspection_conversation`
- Com isso, o overlay domina semanticamente o sistema sem desmontar o conteúdo que estava por baixo.

### Efeito prático

- abrir Nova Inspeção sobre o portal mantém o portal no fundo
- abrir Nova Inspeção sobre assistant landing mantém a landing no fundo
- abrir Nova Inspeção sobre record/conversation mantém o workspace técnico no fundo

## Hooks e seletores preservados

### Preservados

- `#modal-nova-inspecao`
- `#select-template-inspecao`
- `#select-template-custom`
- `#btn-select-template-custom`
- `#valor-select-template-custom`
- `#painel-select-template-custom`
- `#lista-select-template-custom`
- `#input-local-inspecao`
- `#input-cliente-inspecao`
- `#input-unidade-inspecao`
- `#textarea-objetivo-inspecao`
- `#btn-editar-nome-inspecao`
- `#preview-nome-inspecao`
- `#input-nome-inspecao`
- `#btn-cancelar-modal-inspecao`
- `#btn-confirmar-inspecao`
- `[data-open-inspecao-modal]`

### Atualizados internamente

- o fechamento de Nova Inspeção em `chat_index_page.js` passou a mirar `#modal-nova-inspecao .btn-fechar-modal`, reduzindo acoplamento com outros modais
- `#inspetor-overlay-host` virou o novo ponto estrutural estável dos overlays do inspetor

## Como o layout shift foi evitado

### Confirmado no código

- o overlay host é `position: fixed` e fica fora do grid principal
- `.modal-overlay` passou a ocupar a viewport inteira dentro desse host
- `.modal-container` recebeu largura estável de `420px` como teto prático para Nova Inspeção
- o formulário ganhou `max-height` e `overflow-y: auto` na região interna, com rolagem própria
- o fundo não é mais reestruturado pelo `new_inspection`
- `atualizarControlesWorkspaceStage()` deixou de tratar `new_inspection` como se o fundo inteiro fosse `assistant_landing`

### Efeito prático

- header, toolbar, landing, record e conversation não são mais empurrados
- o grid principal não muda de largura
- o rail direito não some só porque o overlay abriu sobre um laudo já ativo
- o conteúdo de fundo continua íntegro e apenas perde interatividade visual

## Entry points de abertura preservados

### Confirmado no código

Continuam abrindo o mesmo modal:

- `#btn-abrir-modal-novo` em `web/templates/inspetor/_portal_home.html`
- botão da sidebar com `[data-open-inspecao-modal]` em `web/templates/inspetor/_sidebar.html`
- botão do header `#btn-workspace-open-inspecao-modal` em `web/templates/inspetor/workspace/_workspace_header.html`
- CTA da landing em `web/templates/inspetor/workspace/_assistant_landing.html`
- cards rápidos do portal que já chamam o fluxo e fazem prefill

O listener continua em `web/static/js/chat/chat_index_page.js::bindEventosModal()`.

## Estado visual do fundo

### Confirmado no código

- `web/static/js/inspetor/modals.js` agora sincroniza o estado visual da Nova Inspeção com:
  - `body.inspetor-overlay-open`
  - `body.inspetor-overlay-new-inspection`
  - `body.dataset.overlayOwner = "new_inspection"`
  - `#inspetor-overlay-host[data-overlay-active="true"]`
- `#painel-chat` fica `inert` enquanto o overlay está aberto
- o quick dock é ocultado visualmente enquanto a Nova Inspeção domina a tela

## Limitações que permanecem

### Confirmado no código

- o sistema continua usando múltiplas autoridades de estado
- a lógica funcional do modal continua distribuída entre `modals.js` e `chat_index_page.js`
- não foi atacada nesta fase a precedência formal entre sessão, dataset e storage
- não foram atacados fillers, mesa, finalização, `garantirThreadNav()` ou placeholders de pendências

### Inferência

- esta fase resolveu a bagunça estrutural do overlay e da tela de fundo, mas não resolve a dívida técnica mais ampla de estado do Chat Inspetor
