# 06. Arquitetura do Frontend

Este documento cobre o frontend web e o frontend mobile, explicando como cada interface nasce, como os assets são carregados e como o backend se conecta a cada tela.

## 1. Leitura geral

O sistema possui duas camadas de frontend distintas:

1. Frontend web em `web/templates/` + `web/static/`
2. Frontend mobile React Native em `android/`

Elas compartilham a mesma fonte de verdade de negócio no backend, mas têm arquiteturas de renderização diferentes.

## 2. Frontend web

## 2.1 Modelo de renderização

O frontend web é majoritariamente SSR com Jinja2, mas várias páginas funcionam como shells altamente hidratados por JavaScript. O padrão dominante não é SPA puro nem SSR estático simples; é um híbrido:

- HTML inicial vem do servidor;
- o template injeta contexto e tokens;
- JS client-side assume quase toda a interação subsequente.

## 2.2 Templates base

### Entrypoint histórico removido

O antigo `web/templates/base.html` foi removido fisicamente na trilha final de limpeza visual.

Leitura:

- ele não participa mais do runtime web oficial;
- qualquer referência a esse caminho em docs antigas deve ser lida apenas como rastreabilidade;
- toda a experiência web viva do inspetor passa por `web/templates/inspetor/base.html`.

### Base isolada do inspetor

Arquivo: `web/templates/inspetor/base.html`

Pontos confirmados:

- injeta `csrf_token` e boot JSON em `<script id="tariel-boot">`;
- carrega CSS mínimo compartilhado e CSS isolado do inspetor;
- inclui `app_shell.js`;
- deixa `index.html` acrescentar a pilha de scripts específicos.

Observação arquitetural:

- o inspetor já ganhou um shell dedicado e mais controlado do que a base genérica antiga.

## 2.3 Portais e telas web

| Área | Template principal | Tipo de montagem | Observação |
| --- | --- | --- | --- |
| Inspetor | `web/templates/index.html` | SSR + hidratação muito forte | É a interface web mais rica do sistema. |
| Revisor | `web/templates/painel_revisor.html` | SSR + hidratação forte | Fila e operação em tempo real. |
| Cliente | `web/templates/cliente_portal.html` | SSR + shell quase SPA | Uma página grande com abas internas. |
| Admin CEO | `web/templates/admin/dashboard.html` | SSR + enhancement | Mais leve que os demais portais operacionais. |
| Logins | `web/templates/login*.html` | SSR leve | Interação limitada a formulário e UX de auth. |
| Templates de laudo | `web/templates/revisor_templates_*.html` | SSR + JS dedicado | Subproduto documental do revisor. |

## 2.4 Partials e composição de templates

No inspetor, o template principal inclui várias regiões menores:

- `web/templates/inspetor/_portal_main.html`
- `web/templates/inspetor/modals/_nova_inspecao.html`
- `web/templates/inspetor/modals/_gate_qualidade.html`
- `web/templates/inspetor/modals/_perfil.html`
- vários fragments em `web/templates/inspetor/workspace/`

Leitura:

- o HTML do inspetor foi decompondo regiões visuais, mas a lógica client-side continua muito concentrada.

No cliente e no revisor, a decomposição é menor. Os templates principais permanecem grandes e bastante auto-contidos.

## 2.5 JavaScript por área

### Inspetor

Template: `web/templates/index.html`

Scripts carregados explicitamente:

- `static/js/shared/api-core.js`
- `static/js/shared/chat-render.js`
- `static/js/shared/chat-network-utils.js`
- `static/js/shared/chat-network.js`
- `static/js/shared/api.js`
- `static/js/shared/ui.js`
- `static/js/shared/hardware.js`
- `static/js/chat/chat_sidebar.js`
- `static/js/inspetor/modals.js`
- `static/js/inspetor/pendencias.js`
- `static/js/inspetor/mesa_widget.js`
- `static/js/inspetor/notifications_sse.js`
- `static/js/chat/chat_index_page.js`
- `static/js/chat/chat_perfil_usuario.js`
- `static/js/chat/chat_painel_core.js`
- `static/js/chat/chat_painel_laudos.js`
- `static/js/chat/chat_painel_historico_acoes.js`
- `static/js/chat/chat_painel_mesa.js`
- `static/js/chat/chat_painel_relatorio.js`
- `static/js/chat/chat_painel_index.js`

Leitura:

- o inspetor depende de ordem de carregamento de scripts;
- a página nasce com SSR, mas a experiência prática é fortemente client-side;
- `chat_index_page.js` é o maior arquivo JS do frontend web e funciona como controller central.

### Revisor

Templates principais:

- `web/templates/painel_revisor.html`
- `web/templates/revisor_templates_biblioteca.html`
- `web/templates/revisor_templates_editor_word.html`

Scripts relevantes:

- `static/js/revisor/revisor_painel_core.js`
- `static/js/revisor/painel_revisor_page.js`
- `static/js/revisor/templates_biblioteca_page.js`
- `static/js/revisor/templates_editor_word.js`

Leitura:

- a mesa tem JS mais segmentado que o inspetor;
- a biblioteca de templates já forma um frontend próprio dentro do portal revisor.

### Cliente

Template principal: `web/templates/cliente_portal.html`

Script dominante:

- `web/static/js/cliente/portal.js`

Leitura:

- quase toda a interação do portal cliente está centralizada em um único arquivo;
- isso simplifica descoberta inicial, mas aumenta o custo de manutenção.

### Admin CEO

Template principal: `web/templates/dashboard.html`

Scripts:

- `web/static/js/admin/painel.js`
- Chart.js via CDN

Leitura:

- o dashboard administrativo parece ser o frontend web menos denso.

## 2.6 CSS por área

### Shared

- `web/static/css/shared/global.css`
- `web/static/css/shared/material-symbols.css`
- `web/static/css/shared/app_shell.css`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/shared/auth_shell.css`

### Inspetor

- `web/static/css/inspetor/tokens.css`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`

### Revisor

- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/revisor/templates_biblioteca.css`
- `web/static/css/revisor/templates_laudo.css`

### Cliente

- `web/static/css/cliente/portal.css`

### Admin

- `web/static/css/admin/admin.css`

Leitura:

- o runtime oficial do inspetor foi reduzido a um pipeline explícito e canônico;
- `layout.css`, `chat_base.css`, `chat_mobile.css`, `chat_index.css`, `shell.css`, `home.css`, `modals.css`, `profile.css`, `mesa.css`, `responsive.css` e `workspace.css` foram removidos fisicamente;
- a maior parte do risco visual agora está concentrada em `reboot.css` e no volume do JS do inspetor, não em múltiplos CSS concorrentes.

## 2.7 Build e pipeline de assets web

Ponto confirmado no código:

- não há bundler moderno explícito no workspace web.

O que isso implica:

- sem tree shaking;
- sem code splitting automatizado;
- sem pipeline explícita de minificação baseada em bundler no repositório inspecionado;
- dependência de ordem manual de `<script>`;
- assets servidos diretamente de `web/static/`.

### Service worker

Arquivo: `web/static/js/shared/trabalhador_servico.js`

Pontos confirmados por código e testes:

- existe service worker próprio;
- ele cacheia parte importante dos assets do inspetor;
- os testes smoke validam explicitamente quais CSS/JS devem ou não entrar nesse cache.

Leitura:

- o projeto compensa parcialmente a ausência de bundler com cache local e uma política explícita de assets.

## 2.8 Bibliotecas externas de frontend

Encontradas no código:

- Google Fonts
- Material Symbols
- Chart.js via CDN em `dashboard.html`
- PDF.js via CDN em `revisor_templates_biblioteca.html`

Leitura:

- a aplicação web não é “zero dependência client-side”.
- Parte da UX depende de rede externa para fontes e algumas bibliotecas.

## 2.9 Classificação das páginas por estilo de renderização

| Tela | Classificação | Justificativa |
| --- | --- | --- |
| `login.html`, `login_app.html`, `login_cliente.html`, `login_revisor.html` | SSR leve | Formulários pequenos, pouca lógica client-side. |
| `dashboard.html` | SSR com enhancement | Backend monta a maior parte do conteúdo e JS complementa gráficos. |
| `index.html` | SSR + hidratação muito forte | Shell nasce no servidor, mas a operação real depende de muitos módulos JS. |
| `painel_revisor.html` | SSR + hidratação forte | Fila, filtros, pacote e whispers ganham vida no client. |
| `cliente_portal.html` | SSR + comportamento quase SPA | Uma tela grande com múltiplos painéis operados por JS. |
| `revisor_templates_biblioteca.html` | SSR + app client-side dedicado | Busca, diff, preview e operações de template. |
| `revisor_templates_editor_word.html` | SSR + editor client-side | Fluxo rico e orientado a estado no navegador. |

## 3. Frontend mobile

## 3.1 Ponto de entrada

Arquivos principais:

- `android/App.tsx`
- `android/src/features/InspectorMobileApp.tsx`

Pontos confirmados:

- `App.tsx` injeta `SettingsStoreProvider`;
- `InspectorMobileApp` é o shell principal do app;
- o app mobile é todo orientado ao inspetor.

## 3.2 Estrutura do app mobile

| Caminho | Papel |
| --- | --- |
| `android/src/config/` | Clientes de API, observabilidade e crash reporting |
| `android/src/features/auth/` | Login e acesso externo |
| `android/src/features/bootstrap/` | Bootstrap e estado inicial |
| `android/src/features/chat/` | Chat do inspetor |
| `android/src/features/mesa/` | Mesa no app |
| `android/src/features/history/` | Histórico e navegação entre laudos |
| `android/src/features/offline/` | Fila offline |
| `android/src/features/security/` | App lock e eventos de segurança |
| `android/src/features/session/` | Sessão autenticada |
| `android/src/features/settings/` | Configurações e operações críticas |
| `android/src/features/activity/` | Central de atividade |
| `android/src/settings/` | Store persistida, schema e migrations locais |

## 3.3 Conexão do mobile com o backend

Arquivo agregador:

- `android/src/config/api.ts`

Clientes principais:

- `authApi`
- `settingsApi`
- `chatApi`
- `mesaApi`

Rotas consumidas pelo mobile, confirmadas no código:

- `/app/api/mobile/auth/login`
- `/app/api/mobile/bootstrap`
- `/app/api/mobile/laudos`
- `/app/api/laudo/status`
- `/app/api/laudo/{id}/mensagens`
- `/app/api/chat`
- `/app/api/laudo/{id}/mesa/mensagens`
- `/app/api/laudo/{id}/mesa/mensagem`
- `/app/api/laudo/{id}/mesa/anexo`
- `/app/api/laudo/{id}/mesa/resumo`
- `/app/api/mobile/mesa/feed`

Leitura:

- o mobile reutiliza o backend do inspetor web, com algumas rotas mobile específicas;
- não existe um backend móvel independente.

## 3.4 Estilo de arquitetura do mobile

O app mobile é um frontend cliente-stateful, sem SSR, com:

- shell React Native central;
- vários controllers/hooks por feature;
- persistência local de settings e cache;
- fila offline;
- consumo explícito de APIs HTTP;
- recursos nativos como document picker, image picker, sharing e file system.

## 4. Como backend e frontend se conectam

## 4.1 Web

Padrão dominante:

```text
rota HTML
  -> render Jinja2 com contexto inicial
    -> template inclui assets por portal
      -> JS lê `csrf_token`, boot JSON e atributos do DOM
        -> chamadas para APIs JSON/SSE/WS
```

### Exemplos

- Inspetor:
  - `GET /app/` renderiza `index.html`
  - JS chama `/app/api/chat`, `/app/api/laudo/*`, `/app/api/notificacoes/sse`
- Revisor:
  - `GET /revisao/painel` renderiza `painel_revisor.html`
  - JS chama `/revisao/api/laudo/*` e `/revisao/ws/whispers`
- Cliente:
  - `GET /cliente/painel` renderiza `cliente_portal.html`
  - JS chama `/cliente/api/bootstrap`, `/cliente/api/chat/*`, `/cliente/api/mesa/*`

## 4.2 Mobile

Padrão dominante:

```text
InspectorMobileApp
  -> auth/bootstrap local
    -> chamadas HTTP para backend web
      -> renderização nativa React Native
        -> persistência local, offline e retomada de fluxo
```

## 5. Arquivos frontend mais críticos

### Web

- `web/templates/index.html`
- `web/templates/inspetor/base.html`
- `web/templates/painel_revisor.html`
- `web/templates/cliente_portal.html`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/cliente/portal.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-network.js`
- `web/static/js/shared/ui.js`
- `web/static/js/revisor/templates_biblioteca_page.js`

### Mobile

- `android/App.tsx`
- `android/src/features/InspectorMobileApp.tsx`
- `android/src/config/api.ts`
- `android/src/config/chatApi.ts`
- `android/src/config/mesaApi.ts`
- `android/src/settings/`

## 6. Pontos fortes da arquitetura de frontend

- O inspetor ganhou uma base própria (`templates/inspetor/base.html`) em vez de depender apenas da base genérica.
- Há separação clara entre assets por portal.
- Existe service worker e política explícita de cache.
- O mobile tem organização por features e preocupação real com offline.

## 7. Fragilidades percebidas

- O frontend web depende muito de scripts globais e da ordem de carregamento.
- Existem arquivos JS e CSS muito grandes.
- O portal cliente concentra quase toda a lógica em um único JS.
- O inspetor ainda tem um runtime denso demais para uma única página.
- A existência de CSS e compat layers históricos aumenta a ambiguidade sobre o que está realmente ativo.

## Confirmado no código

- O web usa SSR com Jinja2 e hidratação forte via JS estático.
- O inspetor tem shell próprio e pipeline visual isolado.
- O revisor e o cliente têm frontends próprios, não apenas reaproveitamento visual do inspetor.
- O mobile consome a mesma API do backend web.
- Não há bundler moderno explícito no frontend web versionado.

## Inferência provável

- O maior risco de regressão de frontend está no inspetor web e no portal cliente, não nas telas de login ou no admin CEO.
- O service worker ajuda o runtime do inspetor, mas não elimina o custo da primeira carga nem a complexidade do JS global.
- Uma futura modernização do frontend web exigirá separar pelo menos runtime compartilhado, controller de página e módulos por feature antes de pensar em redesign profundo.

## Dúvida aberta

- Não ficou totalmente claro se todos os CSS “de referência de migração” ainda são consumidos em rotas secundárias antigas. Os testes e a base do inspetor sugerem que parte deles já não está na trilha principal, mas o repositório ainda carrega ambiguidade histórica.
