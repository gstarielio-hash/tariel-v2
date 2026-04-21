# 09. Glossário e Dúvidas Abertas

## Glossário

## Termos de produto e UX

### Chat Inspetor

Nome do portal principal do inspetor. Entry point em `web/templates/index.html`, servido por `/app/`.

### Portal / Home

Modo dashboard do inspetor. No código, corresponde principalmente a `portal_dashboard` e ao template `web/templates/inspetor/_portal_home.html`.

### Workspace

Área operacional do inspetor fora do portal. Shell em `web/templates/inspetor/_workspace.html`.

### Landing do assistente

Tela inicial do workspace sem laudo ativo. No código, `assistant_landing`.

### Nova inspeção

Fluxo de criação de laudo. No código, é principalmente o modal `#modal-nova-inspecao` e o screen mode `new_inspection`.

### Registro técnico

Termo de negócio para a visão técnica/anexos do laudo. No runtime atual, a correspondência mais segura é `inspection_record`.

### Conversa ativa

Visão do chat do laudo ativo. No código, `inspection_conversation`.

### Mesa avaliadora / mesa

Canal paralelo de revisão/engenharia. UI em `web/templates/inspetor/_mesa_widget.html` e atalho `@insp `.

### Pendências

Itens da mesa/contexto que precisam ser resolvidos. UI principal no rail direito e backend em `web/app/domains/chat/pendencias.py`.

### Gate de qualidade

Bloqueio de finalização exibido em `#modal-gate-qualidade` quando faltam requisitos.

## Termos de frontend

### Screen mode

Estado visual de alto nível do inspetor. Resolvido por `chat_index_page.js::resolveInspectorScreen()`.

### Workspace stage

Subestado do workspace, armazenado em `estado.workspaceStage` e refletido em dataset. Valores confirmados: `"assistant"` e `"inspection"`.

### `modoInspecaoUI`

Estado do shell entre `home` e `workspace`, mantido em `chat_index_page.js`.

### Thread nav

Toolbar de tabs do workspace. Seletor crítico `.thread-nav`.

### Context rail

Painel direito do workspace. Partial `web/templates/inspetor/workspace/_workspace_context_rail.html`.

### Composer

Rodapé de entrada compartilhado no workspace, classe `.rodape-entrada`.

### `window.TarielAPI`

Namespace cliente para operações de API e sincronização, definido em `web/static/js/shared/api.js`.

### `window.TarielChatPainel`

Namespace legado/compartilhado do chat, definido em `web/static/js/chat/chat_painel_core.js`.

### `window.TarielUI`

Namespace global de UI, definido em `web/static/js/shared/ui.js`.

### `window.TARIEL`

Bootstrap global derivado de `#tariel-boot`, preenchido por `web/static/js/shared/app_shell.js`.

## Termos de backend

### Laudo

Entidade central do fluxo. Pode ser criada, selecionada, finalizada, reaberta, pinada e excluída.

### `laudo_card`

Payload resumido do laudo usado para sidebar, portal, cards e sincronizações UI.

### Estado do relatório

Estado operacional do laudo do ponto de vista de backend/UI. É reconciliado por `web/app/domains/chat/session_helpers.py::estado_relatorio_sanitizado()`.

## Dúvidas Abertas

## 1. O que exatamente o produto chama de "Registro Técnico"?

### Confirmado no código

- O screen mode confirmado é `inspection_record`.
- A view correspondente é `web/templates/inspetor/workspace/_inspection_record.html`.

### Dúvida

- O termo textual "Registro Técnico" não aparece como autoridade única em todos os arquivos. A correspondência operacional é forte, mas a nomenclatura ainda pode variar no produto.

## 2. Os endpoints de aprendizados estão ativos neste portal?

### Confirmado no código

- O backend expõe `GET/POST /app/api/laudo/{laudo_id}/aprendizados` em `web/app/domains/chat/learning.py`.

### Dúvida

- Não foi encontrado consumidor explícito no runtime atual do Chat Inspetor inspecionado.

## 3. Quais fallbacks ainda são necessários em produção?

### Confirmado no código

- há recriação de `.thread-nav`
- há fillers de histórico
- há placeholders de pendências

### Dúvida

- o repositório não marca claramente quais desses caminhos ainda protegem cenários reais e quais são apenas herança técnica.

## 4. Qual é a precedência oficial entre as fontes de verdade?

### Confirmado no código

- o sistema usa sessão, `chat_index_page.js`, `TarielChatPainel`, `TarielAPI`, dataset e storage

### Dúvida

- não há um contrato formal documentado definindo a ordem de precedência quando entram em conflito

## 5. A mesa deve ser widget ou atalho de composer?

### Confirmado no código

- ambos existem e funcionam

### Dúvida

- não está explícito qual dos dois é o caminho "oficial" de UX a longo prazo

## 6. A finalização oficial é direta ou via comando?

### Confirmado no código

- os dois caminhos existem em `shared/chat-network.js`

### Dúvida

- o código não declara um único caminho canônico para todos os cenários

## Confirmado no Código

- O vocabulário interno mistura termos de produto, termos técnicos e nomes de transição de arquitetura.

## Inferência

- Parte da confusão semântica atual nasce da migração progressiva da UI sem uma renomeação global do domínio.

## Dúvida Aberta

- Uma futura documentação oficial deveria definir um glossário canônico de produto e outro de runtime para reduzir ambiguidades.
