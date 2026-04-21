# 11. Índice de Arquivos

## Critérios

- `Alta`: arquivo muito sensível; alterações tendem a quebrar fluxo central
- `Média`: arquivo relevante, mas mais localizado
- `Baixa`: arquivo de apoio ou evidência complementar

## Templates e Shell

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/templates/index.html` | entrypoint HTML do inspetor | Alta | carrega shell, modais e todos os JS |
| `web/templates/inspetor/base.html` | shell global e boot JSON | Alta | injeta `#tariel-boot`, quick dock e CSS |
| `web/templates/inspetor/_portal_main.html` | shell funcional do inspetor | Alta | define datasets SSR e compõe sidebar, portal, workspace e mesa |
| `web/templates/inspetor/_sidebar.html` | sidebar esquerda | Alta | Home, histórico, nova inspeção, perfil, logout |
| `web/templates/inspetor/_portal_home.html` | portal/home | Alta | dashboard, cards e laudos recentes |
| `web/templates/inspetor/_workspace.html` | shell do workspace | Alta | concentra header, toolbar, views, composer e rail |
| `web/templates/inspetor/workspace/_workspace_header.html` | header interno compartilhado | Alta | Home, título, status, preview, finalizar |
| `web/templates/inspetor/workspace/_workspace_toolbar.html` | toolbar compartilhada | Alta | tabs, busca, filtros e status |
| `web/templates/inspetor/workspace/_assistant_landing.html` | landing do assistente | Média | fluxo antes da inspeção |
| `web/templates/inspetor/workspace/_inspection_record.html` | registro/anexos | Alta | visão técnica do laudo |
| `web/templates/inspetor/workspace/_inspection_conversation.html` | conversa ativa | Alta | histórico e timeline |
| `web/templates/inspetor/workspace/_workspace_context_rail.html` | rail direito | Alta | progresso, contexto, pendências, mesa, atividade |
| `web/templates/inspetor/_mesa_widget.html` | widget da mesa | Média | canal paralelo com mesa avaliadora |
| `web/templates/inspetor/modals/_nova_inspecao.html` | modal de nova inspeção | Alta | cria contexto de início do laudo |
| `web/templates/inspetor/modals/_gate_qualidade.html` | modal de gate | Média | bloqueio de finalização |
| `web/templates/inspetor/modals/_perfil.html` | modal de perfil | Média | edição de dados do usuário |
| `web/templates/inspetor/_macros.html` | macros de portal/cards | Média | ajuda a entender datasets dos cards |

## Frontend JS

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/static/js/chat/chat_index_page.js` | controlador principal do inspetor | Alta | screen mode, workspace, Home, toolbar, rail |
| `web/static/js/chat/chat_painel_core.js` | estado global legado do chat | Alta | `window.TarielChatPainel` |
| `web/static/js/chat/chat_painel_laudos.js` | seleção de laudo e URL | Alta | lê `home=1`, `laudo=`, `localStorage`; tem fallback `garantirThreadNav()` |
| `web/static/js/chat/chat_painel_relatorio.js` | read-only, finalizar e reabrir | Alta | espalha regras de estado do laudo |
| `web/static/js/chat/chat_painel_mesa.js` | atalho `@insp` para mesa | Média | coexistência com widget dedicado |
| `web/static/js/chat/chat_painel_historico_acoes.js` | pin/delete de laudos | Média | manipula histórico e estado lateral |
| `web/static/js/chat/chat_painel_index.js` | boot final do painel | Média | executa boot tasks |
| `web/static/js/chat/chat_sidebar.js` | sidebar/histórico | Média | ainda procura hook legado ausente |
| `web/static/js/chat/chat_perfil_usuario.js` | perfil do usuário | Média | integra endpoints de perfil |
| `web/static/js/shared/api.js` | bridge de API e histórico | Alta | `window.TarielAPI`, eventos, fillers de histórico |
| `web/static/js/shared/chat-network.js` | camada real de rede | Alta | `/app/api/chat`, status, laudo, PDF, upload |
| `web/static/js/shared/chat-render.js` | renderer visual das mensagens | Alta | emite ações de mensagem |
| `web/static/js/shared/ui.js` | shell UI e Home | Alta | quick dock, `data-action="go-home"`, `window.TarielUI` |
| `web/static/js/shared/hardware.js` | câmera, microfone e anexo | Média | integra hardware do navegador |
| `web/static/js/shared/app_shell.js` | bootstrap global do shell | Média | expõe `window.TARIEL` |
| `web/static/js/inspetor/modals.js` | nova inspeção e gate | Alta | contexto visual, validação modal |
| `web/static/js/inspetor/mesa_widget.js` | runtime do widget da mesa | Alta | resumo, mensagens, anexo e conexão |
| `web/static/js/inspetor/pendencias.js` | runtime de pendências | Alta | filtros, paginação e placeholders |
| `web/static/js/inspetor/notifications_sse.js` | notificações em tempo real | Alta | `EventSource("/app/api/notificacoes/sse")` |

## CSS

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/static/css/inspetor/tokens.css` | tokens visuais | Média | base de variáveis |
| `web/static/css/inspetor/reboot.css` | camada estrutural residual do inspetor | Alta | shell, overlays e compatibilidade ativa |
| `web/static/css/shared/app_shell.css` | shell global compartilhado | Alta | influencia quick dock, container e chrome global |
| `web/static/css/shared/official_visual_system.css` | sistema visual canônico compartilhado | Alta | tokens e componentes oficiais das superfícies web |
| `web/static/css/inspetor/workspace_chrome.css` | slice de chrome do workspace | Alta | header, tabs e toolbar do `/app` |
| `web/static/css/inspetor/workspace_history.css` | slice do histórico | Alta | timeline, foco e estados de leitura |
| `web/static/css/inspetor/workspace_rail.css` | slice da rail e da mesa | Alta | progresso, contexto, pendências e mesa card |
| `web/static/css/inspetor/workspace_states.css` | slice de estados compartilhados | Alta | empty states, composer e estados focados |

## Legado visual removido

Os seguintes caminhos ficaram apenas como rastreabilidade histórica e não existem mais no repositório:

- `web/templates/base.html`
- `web/static/css/shared/layout.css`
- `web/static/css/chat/chat_base.css`
- `web/static/css/chat/chat_mobile.css`
- `web/static/css/chat/chat_index.css`
- `web/static/css/inspetor/home.css`
- `web/static/css/inspetor/mesa.css`
- `web/static/css/inspetor/modals.css`
- `web/static/css/inspetor/profile.css`
- `web/static/css/inspetor/responsive.css`
- `web/static/css/inspetor/shell.css`
- `web/static/css/inspetor/workspace.css`

## Backend

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/app/domains/chat/router.py` | agregador de routers do domínio | Média | conecta auth, laudo, chat, mesa, pendências |
| `web/app/domains/chat/auth_portal_routes.py` | rota SSR principal e perfil | Alta | serve `/app/` |
| `web/app/domains/chat/auth_mobile_support.py` | contexto do portal e recentes | Alta | alimenta cards e sidebar |
| `web/app/domains/chat/session_helpers.py` | sessão, CSRF e estado do laudo | Alta | autoridade server-side de contexto |
| `web/app/domains/chat/laudo.py` | ciclo de vida do laudo | Alta | status, iniciar, finalizar, reabrir, pin, delete |
| `web/app/domains/chat/chat_stream_routes.py` | endpoint principal de chat | Alta | cria laudo, stream de IA, comandos |
| `web/app/domains/chat/chat_aux_routes.py` | mensagens, PDF, upload, feedback | Alta | endpoints auxiliares do chat |
| `web/app/domains/chat/chat_runtime_support.py` | SSE de notificações | Alta | heartbeat e fila SSE |
| `web/app/domains/chat/mesa.py` | backend da mesa | Alta | mensagens, resumo, anexos, feed mobile |
| `web/app/domains/chat/pendencias.py` | backend de pendências | Alta | filtros, paginação, update e exportação |
| `web/app/domains/chat/learning.py` | backend de aprendizados | Média | consumer frontend atual não confirmado |
| `web/app/domains/chat/chat.py` | façade de chat/SSE | Média | expõe `GET /app/api/notificacoes/sse` |

## Testes e Evidências

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/tests/test_smoke.py` | smoke estrutural do portal/inspetor | Alta | protege templates, CSS e hooks críticos |
| `web/tests/e2e/test_portais_playwright.py` | fluxo e2e do inspetor | Alta | valida assistant landing, Home, mesa, gate e navegação |
| `web/tests/test_chat_runtime_support.py` | SSE runtime support | Média | evidencia payload inicial e heartbeat |
| `web/tests/test_chat_notifications.py` | gerenciador SSE | Média | ajuda a entender notificações |
| `web/tests/test_mesa_mobile_sync.py` | sync/idempotência de mesa | Média | confirma contrato de mesa/feed |

## Observação Final

Os arquivos mais perigosos para mudança sem mapa prévio são:

- `web/static/js/chat/chat_index_page.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-network.js`
- `web/static/js/chat/chat_painel_core.js`
- `web/static/js/chat/chat_painel_laudos.js`
- `web/templates/inspetor/_workspace.html`
- `web/static/css/inspetor/reboot.css`
