# Ledger de Dívida Técnica do Inspetor

| Item | Arquivo(s) | Risco | Motivo de permanência | Condição para remover | Prioridade | Depende de produto? | Depende de backend? | Depende de telemetria? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Aliases legados de eventos canônicos | `web/static/js/shared/api-core.js` | Médio | Ainda há módulos e integrações antigas que podem despachar/escutar alias sem `:` | Confirmar ausência de tráfego/uso dos aliases e remover listeners/dispatch legado | Média | Não | Não | Sim |
| Compat API em `window.TarielScript` | `web/static/js/chat/chat_painel_index.js` | Médio | Mantém compatibilidade com scripts antigos que ainda não falam direto com `TarielAPI`/`TarielChatPainel` | Inventário completo de consumers reais e migração para API final | Média | Não | Não | Sim |
| Reconciliador com múltiplas fontes (`API`, `core`, `dataset`, `storage`, `local`) | `web/static/js/chat/chat_index_page.js` | Baixo/Médio | Garante robustez contra divergência de boot e estados parciais | Reduzir para fonte única depois de validar boot estável em produção | Média | Não | Não | Sim |
| `sessionStorage` para `forceHomeLanding` e retomada de home | `web/static/js/chat/chat_index_page.js` | Baixo | Evita quebra de navegação entre shell e retorno de contexto | Medir se o fluxo já está estável apenas com estado reconciliado | Baixa | Não | Não | Sim |
| `localStorage` de contexto fixado | `web/static/js/chat/chat_index_page.js` | Baixo | Preserva utilidade operacional entre recargas e retomadas do laudo | Definir se fixação deve virar persistência oficial do produto | Sim | Não | Não | Sim |
| Datasets reflexivos de shell/estado/honestidade | `web/static/js/chat/chat_index_page.js` | Baixo | CSS, debug local, ferramentas de inspeção e módulos de shell ainda leem esses espelhos | Consolidar consumers e substituir por API explícita de estado | Baixa | Não | Não | Sim |
| Debug de alias legado no DOM (`inspectorLegacyEvent*`) | `web/static/js/shared/api-core.js` | Baixo | Ajuda auditoria de compatibilidade enquanto aliases ainda existem | Remover junto com os aliases legados | Baixa | Não | Não | Sim |
| Alias de linguagem para mesa (`eng`, `@eng`, `mesa`, `revisor`, `avaliador`) | `web/static/js/chat/chat_painel_mesa.js`, `web/static/js/shared/ui.js` | Médio | Há ergonomia operacional e compatibilidade histórica com usuários e scripts | Definir prefixo oficial único para produto e descontinuar aliases | Média | Sim | Não | Sim |
| Dupla rota funcional para mesa (`widget` + comando textual) | `web/static/js/chat/chat_painel_mesa.js`, `web/static/js/inspetor/mesa_widget.js`, `web/static/js/shared/ui.js` | Médio | Produto ainda preserva widget dedicado e comando textual | Decisão explícita de produto sobre unificação ou permanência definitiva | Média | Sim | Não | Não |
| Botão de `Nova Inspeção` no header do workspace mantido como hook, porém fora da superfície primária | `web/templates/inspetor/workspace/_workspace_header.html`, `web/static/js/chat/chat_index_page.js` | Baixo | Mantido por segurança para não quebrar hook existente | Confirmar ausência de uso indireto e remover do template | Baixa | Não | Não | Sim |
| Compatibilidade com `btn-sidebar-engenheiro` e caminhos antigos de UI | `web/static/js/shared/ui.js` | Baixo | Outras superfícies antigas ainda podem depender desses seletores | Inventariar páginas antigas e remover seletores mortos | Baixa | Não | Não | Sim |
| `@insp` sem laudo ativo ainda depende de comportamento histórico do composer | `web/static/js/chat/chat_painel_mesa.js`, `web/static/js/shared/ui.js` | Médio | Nesta fase a exposição visual foi organizada, mas o caminho textual permanece | Decidir se a UX deve bloquear cedo ou deixar o backend rejeitar | Média | Sim | Possivelmente | Não |
| `forceHomeLanding` como conceito de shell | `web/static/js/chat/chat_index_page.js` | Baixo/Médio | Ainda simplifica a retomada previsível do portal/home | Validar se o roteamento por `screen mode` já cobre sozinho todos os retornos | Baixa | Não | Não | Sim |

## Remoção segura já feita nesta fase

| Item | Arquivo(s) | Motivo |
| --- | --- | --- |
| Branch de badge inexistente do widget de mesa | `web/static/js/inspetor/mesa_widget.js` | Não havia consumer real do elemento `badgeMesaWidget`; a atualização visual já era coberta pelo próprio botão e pelo resumo operacional |
