# 07. Regiões da UI e Componentes

## Visão Anatômica

O Chat Inspetor é organizado como um shell de três grandes zonas:

- navegação lateral à esquerda
- conteúdo principal central, alternando portal e workspace
- trilho/context rail à direita dentro do workspace

Além disso, há overlays modais e um widget de mesa que coexistem com o shell principal.

## Shell Principal

### Template

- `web/templates/inspetor/base.html`
- `web/templates/inspetor/_portal_main.html`

### Elementos-chave

- `.container-app`
- `#painel-chat`
- `.inspetor-shell-grid`
- `#overlay-sidebar`
- `#btn-shell-home`
- `#btn-shell-profile`

### Papel

- hospeda toda a aplicação inspetor
- injeta dados bootstrap
- expõe quick dock global
- separa a página entre sidebar e região principal

## Sidebar Esquerda

### Template

- `web/templates/inspetor/_sidebar.html`

### JS

- `web/static/js/chat/chat_sidebar.js`
- `web/static/js/shared/ui.js`
- `web/static/js/chat/chat_perfil_usuario.js`

### Elementos-chave

- `#barra-historico`
- `#busca-historico-input`
- link Portal com `data-action="go-home"`
- botão `data-open-inspecao-modal`
- `#banner-relatorio-sidebar`
- `#lista-historico`
- `#estado-vazio-historico`
- `#btn-abrir-perfil-chat`
- formulário `POST /app/logout`

### Papel

- busca e navegação por laudos
- retorno ao portal
- entrada para nova inspeção
- abertura de perfil
- acesso a logout

### Observação relevante

`web/static/js/chat/chat_sidebar.js` ainda procura `#btn-sidebar-engenheiro`, mas esse botão não existe no template atual. Isso é um ponto legado confirmado.

## Portal/Home

### Template

- `web/templates/inspetor/_portal_home.html`

### Root

- `#tela-boas-vindas`

### Regiões internas

- hero/boas-vindas
- CTA `#btn-abrir-modal-novo`
- grid de status
- seção `#secao-home-recentes`
- cards `.portal-report-card`
- ações rápidas `.portal-model-card.btn-acao-rapida`

### Papel

- funcionar como dashboard e ponto de entrada
- listar laudos recentes
- permitir retomada rápida
- pré-selecionar template de nova inspeção

## Workspace

### Template shell

- `web/templates/inspetor/_workspace.html`

### Root

- `[data-screen-root="workspace"]`

### Papel

- reunir todas as áreas de trabalho quando o usuário não está no portal
- manter header, toolbar, views, composer e context rail com estrutura consistente

## Header Interno

### Partial

- `web/templates/inspetor/workspace/_workspace_header.html`

### Elementos-chave

- `.technical-record-header`
- `.btn-home-cabecalho.technical-record-back`
- `#workspace-eyebrow`
- `#workspace-headline`
- `#workspace-description`
- `#workspace-titulo-laudo`
- `#workspace-subtitulo-laudo`
- `#workspace-status-badge`
- `#btn-workspace-open-inspecao-modal`
- `#btn-workspace-preview`
- `#btn-finalizar-inspecao`

### Papel

- concentrar contexto de navegação e metadados do laudo
- expor ações principais do workspace

### Regra importante

- o botão Home aparece no workspace e não no conteúdo do portal
- a semântica de navegação é `data-action="go-home"`

## Toolbar

### Partial

- `web/templates/inspetor/workspace/_workspace_toolbar.html`

### Elementos-chave

- `.thread-nav`
- `.thread-tab[data-tab="chat"]`
- `.thread-tab[data-tab="anexos"]`
- `.technical-chat-bar`
- `#chat-thread-search`
- `[data-chat-filter]`
- `#chat-thread-results`
- `#chat-ai-status-chip`
- `#chat-ai-status-text`

### Papel

- alternar entre chat e anexos
- buscar na timeline
- filtrar por papel/origem da mensagem
- expor status do assistente

## Landing do Assistente

### Partial

- `web/templates/inspetor/workspace/_assistant_landing.html`

### Root

- `#workspace-assistant-landing`

### Elementos-chave

- CTA `data-open-inspecao-modal`
- prompts `[data-assistant-prompt]`

### Papel

- ocupar o workspace antes do laudo existir
- induzir o usuário a iniciar uma nova inspeção

## Registro Técnico / Anexos

### Partial

- `web/templates/inspetor/workspace/_inspection_record.html`

### Elementos-chave

- `#workspace-anexos-panel`
- `#workspace-anexos-count`
- `#workspace-anexos-grid`
- `#workspace-anexos-empty`

### Papel

- exibir a visão de registro técnico centrada em anexos e evidências

## Conversa Ativa

### Partial

- `web/templates/inspetor/workspace/_inspection_conversation.html`

### Elementos-chave

- `#area-mensagens`
- `#indicador-digitando`
- `#btn-ir-fim-chat`

### Papel

- exibir o histórico da conversa do laudo
- sustentar ações por mensagem via renderer

## Context Rail Direito

### Partial

- `web/templates/inspetor/workspace/_workspace_context_rail.html`

### Papel

- consolidar estado derivado e painéis auxiliares do laudo

### Subáreas confirmadas

#### Progresso

- `#workspace-progress-card`
- `#workspace-progress-percent`
- `#workspace-progress-bar`
- `#workspace-progress-evidencias`
- `#workspace-progress-pendencias`

#### Contexto IA

- `#workspace-context-template`
- `#workspace-context-evidencias`
- `#workspace-context-pendencias`
- `#workspace-context-mesa`
- `#workspace-context-equipment`
- `#workspace-context-operation`
- `#workspace-context-summary`
- `#workspace-context-pinned-list`
- `#btn-workspace-context-copy`
- `#btn-workspace-context-clear`

#### Pendências

- `#painel-pendencias-mesa`
- `#lista-pendencias-mesa`
- `#btn-exportar-pendencias-pdf`
- `#btn-marcar-pendencias-lidas`
- `#btn-carregar-mais-pendencias`

#### Mesa card

- `#workspace-mesa-card-text`
- `#workspace-mesa-card-status`
- `#workspace-mesa-card-unread`
- `#btn-mesa-widget-toggle`

#### Atividade

- `#workspace-activity-list`

## Composer

### Localização

- dentro de `web/templates/inspetor/_workspace.html`

### Elementos-chave

- `.rodape-entrada`
- `#preview-anexo`
- `#composer-suggestions`
- `#rodape-contexto-titulo`
- `#rodape-contexto-status`
- `#btn-anexo`
- `#btn-foto-rapida`
- `#btn-toggle-humano`
- `#btn-microfone`
- `#input-anexo`
- `#campo-mensagem`
- `#contador-chars`
- `#btn-enviar`
- `#slash-command-palette`

### Papel

- unificar input textual, anexo, câmera, microfone, sugestões e slash commands
- funcionar tanto para chat IA quanto para alguns atalhos de mesa

## Árvore de Mensagens

### Root

- `#area-mensagens`

### Renderização

- `web/static/js/shared/chat-render.js`

### Estruturas relevantes

- `.linha-mensagem`
- `.conteudo-mensagem`
- `.bloco-referencia-chat[data-ref-id]`

### Ações por mensagem

Eventos emitidos:

- `tariel:mensagem-copiar`
- `tariel:mensagem-citar`
- `tariel:mensagem-fixar-contexto`
- `tariel:mensagem-enviar-mesa`

## Overlay de Nova Inspeção

### Template

- `web/templates/inspetor/modals/_nova_inspecao.html`

### Root

- `#modal-nova-inspecao`

### Papel

- coletar template e contexto mínimo
- pré-montar nome da inspeção
- empurrar contexto visual para o workspace

## Gate de Qualidade

### Template

- `web/templates/inspetor/modals/_gate_qualidade.html`

### Papel

- bloquear finalização quando checklist/evidências não atendem a regra
- permitir voltar ao chat para corrigir pendências

## Widget da Mesa

### Template

- `web/templates/inspetor/_mesa_widget.html`

### JS

- `web/static/js/inspetor/mesa_widget.js`
- `web/static/js/chat/chat_painel_mesa.js`

### Elementos-chave

- `#painel-mesa-widget`
- `#mesa-widget-resumo`
- `#mesa-widget-lista`
- `#mesa-widget-input`
- `#mesa-widget-enviar`

### Papel

- canal paralelo com mesa avaliadora
- suporta anexo e referência a mensagem

## Relação entre Portal e Workspace

### Confirmado no código

- Portal e workspace coexistem no mesmo shell de `#painel-chat`.
- `chat_index_page.js::sincronizarInspectorScreen()` alterna qual root fica visível.
- O portal não desmonta a página; ele apenas oculta o workspace e vice-versa.

## Confirmado no Código

- O workspace é estruturalmente mais rico que o portal e concentra quase toda a lógica operacional.
- O composer e o context rail são compartilhados entre os modos do workspace.
- A toolbar e o header já foram extraídos para partials reutilizáveis.

## Inferência

- A organização visual atual tenta separar "navegação" de "trabalho ativo" sem quebrar contratos antigos, o que explica a coexistência de shell moderno com JS defensivo.

## Dúvida Aberta

- Não há uma taxonomia oficial no código que diga se "mesa widget" faz parte do workspace ou do shell. Na prática, ele é renderizado como um `data-screen-root="mesa-widget"` paralelo ao workspace.
