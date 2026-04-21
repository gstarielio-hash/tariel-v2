# 06. Backend, API e Data Flow

## Mapa de Rotas do Domínio do Inspetor

## Encadeamento principal

- `web/main.py`
- `web/app/domains/router_registry.py`
- `web/app/domains/chat/router.py`
- routers específicos em `web/app/domains/chat/*.py`

## Rotas que servem a página

### `web/app/domains/chat/auth_portal_routes.py`

Rotas confirmadas:

- `GET /app/`
- `GET /app/laudo/{laudo_id}`
- `GET /app/api/perfil`
- `PUT /app/api/perfil`
- `POST /app/api/perfil/foto`
- `POST /app/logout`

## Rotas de laudo

### `web/app/domains/chat/laudo.py`

Rotas confirmadas:

- `GET /app/api/laudo/status`
- `POST /app/api/laudo/iniciar`
- `POST /app/api/laudo/{laudo_id}/finalizar`
- `GET /app/api/laudo/{laudo_id}/gate-qualidade`
- `POST /app/api/laudo/{laudo_id}/reabrir`
- `POST /app/api/laudo/cancelar`
- `POST /app/api/laudo/desativar`
- `GET /app/api/laudo/{laudo_id}/revisoes`
- `GET /app/api/laudo/{laudo_id}/revisoes/diff`
- `PATCH /app/api/laudo/{laudo_id}/pin`
- `DELETE /app/api/laudo/{laudo_id}`

## Rotas de chat e utilitários

### `web/app/domains/chat/chat_stream_routes.py`

- `POST /app/api/chat`

### `web/app/domains/chat/chat_aux_routes.py`

- `GET /app/api/laudo/{laudo_id}/mensagens`
- `POST /app/api/gerar_pdf`
- `POST /app/api/upload_doc`
- `POST /app/api/feedback`

## Rotas de mesa

### `web/app/domains/chat/mesa.py`

- `GET /app/api/laudo/{laudo_id}/mesa/mensagens`
- `GET /app/api/laudo/{laudo_id}/mesa/resumo`
- `POST /app/api/laudo/{laudo_id}/mesa/mensagem`
- `POST /app/api/laudo/{laudo_id}/mesa/anexo`
- `GET /app/api/mobile/mesa/feed`
- `GET /app/api/laudo/{laudo_id}/mesa/anexos/{anexo_id}`

## Rotas de pendências

### `web/app/domains/chat/pendencias.py`

- `GET /app/api/laudo/{laudo_id}/pendencias`
- `POST /app/api/laudo/{laudo_id}/pendencias/marcar-lidas`
- `PATCH /app/api/laudo/{laudo_id}/pendencias/{mensagem_id}`
- `GET /app/api/laudo/{laudo_id}/pendencias/exportar-pdf`

## Rotas de notificações e SSE

### `web/app/domains/chat/chat.py`

- `GET /app/api/notificacoes/sse`

### Implementação

- `web/app/domains/chat/chat_runtime_support.py::sse_notificacoes_inspetor()`

## Rotas de aprendizados

### `web/app/domains/chat/learning.py`

- `GET /app/api/laudo/{laudo_id}/aprendizados`
- `POST /app/api/laudo/{laudo_id}/aprendizados`

## Chamadores Frontend por Endpoint

| Endpoint | Chamador frontend | Papel |
| --- | --- | --- |
| `GET /app/` | navegação do browser | página SSR principal |
| `POST /app/api/laudo/iniciar` | `web/static/js/shared/chat-network.js` via `window.TarielAPI` | cria/inicia laudo |
| `GET /app/api/laudo/status` | `web/static/js/shared/chat-network.js`, `web/static/js/shared/api.js`, `chat_index_page.js` | sincroniza estado do laudo |
| `POST /app/api/chat` | `web/static/js/shared/chat-network.js` | conversa com IA, comandos, mesa via whisper, finalização indireta |
| `GET /app/api/laudo/{id}/mensagens` | `web/static/js/shared/api.js` | histórico paginado do laudo |
| `POST /app/api/upload_doc` | `web/static/js/shared/chat-network.js` / API bridge | upload de documento para o chat |
| `POST /app/api/gerar_pdf` | `web/static/js/shared/chat-network.js` | PDF/preview |
| `POST /app/api/laudo/{id}/finalizar` | `web/static/js/shared/chat-network.js` | finalização direta |
| `POST /app/api/laudo/{id}/reabrir` | `web/static/js/shared/api.js` / runtime de relatório | reabertura |
| `POST /app/api/laudo/desativar` | `web/static/js/chat/chat_index_page.js` | sair do contexto ativo ao voltar para Home |
| `PATCH /app/api/laudo/{id}/pin` | `web/static/js/chat/chat_painel_historico_acoes.js` | fixar/desafixar laudo |
| `DELETE /app/api/laudo/{id}` | `web/static/js/chat/chat_painel_historico_acoes.js` | excluir laudo |
| `GET /app/api/laudo/{id}/mesa/mensagens` | `web/static/js/inspetor/mesa_widget.js` | carregar mensagens da mesa |
| `GET /app/api/laudo/{id}/mesa/resumo` | `web/static/js/inspetor/mesa_widget.js` | resumo operacional da mesa |
| `POST /app/api/laudo/{id}/mesa/mensagem` | `web/static/js/inspetor/mesa_widget.js` | enviar mensagem para mesa |
| `POST /app/api/laudo/{id}/mesa/anexo` | `web/static/js/inspetor/mesa_widget.js` | anexar arquivo à mesa |
| `GET /app/api/laudo/{id}/pendencias` | `web/static/js/inspetor/pendencias.js` | listar pendências |
| `PATCH /app/api/laudo/{id}/pendencias/{mensagemId}` | `web/static/js/inspetor/pendencias.js` | atualizar pendência |
| `POST /app/api/laudo/{id}/pendencias/marcar-lidas` | `web/static/js/inspetor/pendencias.js` | marcar pendências |
| `GET /app/api/laudo/{id}/pendencias/exportar-pdf` | `web/static/js/inspetor/pendencias.js` | exportar PDF de pendências |
| `GET /app/api/notificacoes/sse` | `web/static/js/inspetor/notifications_sse.js` | notificações em tempo real |
| `GET/PUT/POST /app/api/perfil*` | `web/static/js/chat/chat_perfil_usuario.js` | perfil do usuário |

## Payloads e respostas relevantes

## `/app/api/chat`

### Request relevante

Campos confirmados em `web/static/js/shared/chat-network.js::enviarParaIA(...)`:

- `mensagem`
- `dados_imagem`
- `setor`
- `historico`
- `modo`
- `texto_documento`
- `nome_documento`
- `laudo_id`

### Response relevante

O frontend aceita JSON ou `text/event-stream`. O stream pode carregar:

- `laudo_id`
- `laudo_card`
- `texto`
- `citacoes`
- `confianca_ia`
- objetos de mensagem humana/mesa
- marcador final `[FIM]`

## `/app/api/laudo/status`

### Papel

- reconcilia estado do laudo atual
- alimenta read-only, finalize/reabrir e SSR posterior

## `/app/api/laudo/{id}/mesa/mensagens`

### Response relevante

- `itens`
- `cursor_proximo`
- `cursor_ultimo_id`
- `tem_mais`
- `estado`
- `permite_edicao`
- `permite_reabrir`
- `laudo_card`
- `resumo`
- `sync`

## `/app/api/laudo/{id}/pendencias`

### Response relevante

- `laudo_id`
- `filtro`
- `pagina`
- `tamanho`
- `abertas`
- `resolvidas`
- `total`
- `total_filtrado`
- `tem_mais`
- `pendencias`

## Integração com TarielAPI e TarielChatPainel

## `window.TarielAPI`

Definido em `web/static/js/shared/api.js`. É a ponte frontend que empacota operações como:

- iniciar relatório
- finalizar relatório
- cancelar relatório
- reabrir laudo
- sincronizar estado
- carregar laudo
- gerar PDF
- preparar arquivo

## `window.TarielChatPainel`

Definido em `web/static/js/chat/chat_painel_core.js`. Funciona como namespace compartilhado/legado, com boot tasks e utilitários de laudo, URL e histórico.

## SSE

## SSE de chat

### Confirmado no código

- o endpoint `POST /app/api/chat` pode responder em streaming SSE
- o parser frontend está em `web/static/js/shared/chat-network.js`

## SSE de notificações

### Confirmado no código

- `GET /app/api/notificacoes/sse`
- cliente: `web/static/js/inspetor/notifications_sse.js`
- backend: `web/app/domains/chat/chat_runtime_support.py::sse_notificacoes_inspetor()`

### Eventos relevantes confirmados

- conexão inicial
- heartbeat
- novas mensagens/pendências de mesa/engenharia
- atualização de banner e contadores

## SSR vs Hidratação Client-side

## Server-side render

O servidor renderiza:

- shell completo
- sidebar
- portal/home
- workspace base
- modais
- widgets
- dados iniciais do usuário, laudo e portal

## Client-side hydration

O cliente:

- recalcula screen mode
- carrega histórico do laudo
- envia prompts
- conecta SSE
- gerencia mesa, pendências e perfil
- alterna tabs, filtros e search

## Fluxos de dados ponta a ponta

## Fluxo: abrir a página

1. `GET /app/`
2. `pagina_inicial()` monta o contexto SSR
3. `index.html` renderiza shell e scripts
4. `app_shell.js`, `ui.js`, `chat_index_page.js`, `chat_painel_*`, `api.js` hidratam a tela

## Fluxo: iniciar inspeção

1. modal nova inspeção coleta template e contexto
2. frontend chama `POST /app/api/laudo/iniciar`
3. backend cria ou ativa laudo
4. frontend persiste/propaga `laudo_id`
5. histórico e workspace passam para modo de inspeção

## Fluxo: enviar mensagem ao chat

1. composer monta payload
2. `shared/chat-network.js` faz `POST /app/api/chat`
3. backend cria mensagem de usuário, processa IA/mesa/comando
4. frontend consome stream, atualiza histórico e datasets

## Fluxo: voltar para Home

1. `shared/ui.js` dispara `tariel:navigate-home`
2. `chat_index_page.js::navegarParaHome()` limpa client state
3. se necessário, faz `POST /app/api/laudo/desativar`
4. browser navega para `/app/?home=1`

## Fluxo: mesa

1. widget abre
2. frontend consulta resumo e mensagens
3. usuário envia mensagem/anexo
4. backend responde com estado atualizado e notifica SSE

## Confirmado no Código

- O produto mistura SSR forte com hidratação seletiva.
- O backend é dono da sessão e do contexto oficial de laudo ativo do ponto de vista do servidor.
- O frontend depende tanto de endpoints REST quanto de SSE.
- A mesa tem API dedicada, separada do chat principal.

## Inferência

- O sistema evoluiu para uma arquitetura híbrida: parte das ações são CRUD/REST tradicionais, e parte depende de streams e eventos customizados.

## Dúvida Aberta

- O papel operacional dos endpoints de `learning.py` no Chat Inspetor atual não ficou comprovado por um consumidor frontend ativo no runtime inspecionado.
