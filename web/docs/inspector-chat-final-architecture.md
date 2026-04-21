# Arquitetura Final do Frontend do Inspetor

## Shell final adotado

O frontend do inspetor agora opera com um shell único controlado por `screen mode`, com estas regiões principais:

- portal/home
- workspace
- overlay de `Nova Inspeção`
- rail lateral de contexto
- widget dedicado da mesa
- quick dock compacto

O host principal continua em `web/templates/inspetor/_portal_main.html`, com `data-screen-controller="inspector"` e metadados reflexivos no `body` e em `#painel-chat`.

## Screen modes finais

Os modos finais do shell são:

- `portal_dashboard`
- `assistant_landing`
- `new_inspection`
- `inspection_record`
- `inspection_conversation`

`chat_index_page.js` continua sendo a autoridade do `screen mode`, a partir do estado reconciliado do inspetor.

## Views do workspace

O workspace permanece dividido em views reais:

- `assistant_landing`: entrada sem laudo ativo
- `inspection_record`: contexto técnico/anexos/rail
- `inspection_conversation`: timeline real da conversa

Essas views seguem exclusivas entre si e são sincronizadas por `resolveWorkspaceView(...)` e `sincronizarInspectorScreen()`.

## Overlays

O overlay de `Nova Inspeção` continua sendo a única superfície modal operacional desta área.

- abre por `data-open-inspecao-modal`
- resolve `screen = new_inspection`
- mantém `workspace`/`portal` por baixo, porém inert quando aplicável
- agora também expõe a ação contextual `Abrir chat sem modelo`

Nenhuma regra funcional do overlay foi reaberta nesta fase.

## Autoridade de estado

O estado final continua reconciliado em `web/static/js/chat/chat_index_page.js`.

Fontes ainda consideradas:

- compat core (`window.TarielChatPainel`)
- compat API (`window.TarielAPI`)
- SSR/dataset
- storage defensivo
- estado local

O reconciliador continua sendo a autoridade para:

- `laudoAtualId`
- `estadoRelatorio`
- `modoInspecaoUI`
- `workspaceStage`
- `threadTab`
- `forceHomeLanding`
- `overlayOwner`
- `inspectorBaseScreen`
- `inspectorScreen`

Nesta fase foram adicionados apenas metadados reflexivos de superfície, como:

- `data-inspector-quick-dock`
- `data-inspector-context-rail`
- `data-inspector-mesa-entry`
- `data-inspector-finalize-entry`
- `data-inspector-nova-inspecao-entry`
- `data-inspector-abrir-chat-entry`

Eles não são fontes de verdade concorrentes; apenas espelham a matriz final de visibilidade.

## Autoridade de eventos

A autoridade canônica de eventos permanece em `web/static/js/shared/api-core.js`.

Eventos principais ainda consumidos nesta superfície:

- `tariel:screen-synced`
- `tariel:navigate-home`
- `tariel:relatorio-iniciado`
- `tariel:relatorio-finalizado`
- `tariel:cancelar-relatorio`
- `tariel:estado-relatorio`
- `tariel:historico-laudo-renderizado`
- `tariel:mesa-status`
- `tariel:mesa-avaliadora-ativada`

Aliases legados continuam aceitos por compatibilidade e estão listados no ledger de dívida técnica.

## Header, toolbar e CTA final

Header e toolbar seguem compartilhados pelo workspace.

Após a estabilização final:

- `Nova Inspeção` do header do workspace foi mantida como hook preservado, mas saiu da superfície primária
- `Nova Inspeção` primária do `assistant_landing` ficou na própria landing
- `Nova Inspeção` primária do `portal_dashboard` ficou no portal/home
- `Nova Inspeção` contextual em laudo ativo ficou na sidebar
- `Enviar para Mesa` ficou primário no rail em desktop e no header em layout compacto

## Mesa: widget dedicado vs comando

A decisão final de superfície ficou:

- widget dedicado é a superfície principal apenas em `inspection_record` e `inspection_conversation`
- no desktop, a entrada primária da mesa fica no rail
- no layout compacto, a entrada visual principal da mesa fica no composer
- `@insp` e aliases correlatos permanecem como caminho de comando/conversa por compatibilidade

Ou seja: o widget não compete mais visualmente fora do contexto de inspeção, mas o caminho textual legado continua preservado.

## Histórico e pendências honestos

As garantias das fases anteriores foram preservadas:

- histórico continua refletindo apenas histórico real
- pendências continuam refletindo pendências reais
- datasets de honestidade continuam espelhados para UI, debug e integração local

Nenhuma dessas regras foi reaberta nesta fase.

## Entrada “Abrir Chat”

A entrada livre do assistente continua resolvendo para `assistant_landing` sem criar laudo.

Superfícies mantidas:

- portal/home: `Abrir Chat`
- modal de `Nova Inspeção`: `Abrir chat sem modelo`

Nenhum backend ou contrato adicional foi introduzido.

## Legado mantido por segurança

Permaneceu por compatibilidade:

- aliases legados de eventos
- compat API em `window.TarielScript`
- fallbacks de storage/snapshot no reconciliador
- aliases de linguagem para mesa (`eng`, `@eng`, `mesa`, `revisor`, etc.)
- espelhamentos em dataset para shell, honestidade e debug

O detalhe operacional de cada item está em `web/docs/inspector-chat-tech-debt-ledger.md`.
