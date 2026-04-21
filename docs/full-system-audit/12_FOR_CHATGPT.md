# Briefing Consolidado do Sistema Tariel

Atualizado em `2026-04-04`.

Este arquivo foi escrito para ser enviado a outra IA.
Ele resume o sistema de forma autoexplicativa, mas agora alinhado com o estado real atual do workspace.
Use como contexto-base antes de pedir analise, revisao, proposta de refatoracao ou investigacao de bug.

## 1. Snapshot rapido

- O sistema e um produto multiportal para inspecoes tecnicas.
- O backend principal esta em `web/`.
- O app mobile do inspetor esta em `android/`.
- O backend web e um monolito modular FastAPI.
- A mesma aplicacao atende quatro grandes superficies:
  - `/admin` para diretoria/plataforma
  - `/app` para o inspetor
  - `/cliente` para o admin-cliente
  - `/revisao` para a Mesa/revisor
- O backend combina SSR, APIs JSON, SSE e WebSocket.
- O banco usa SQLAlchemy + Alembic.
- O deploy versionado do web aponta para `Render`, com `Postgres`, `Redis` e disco persistente em `render.yaml`.

## 2. Estado atual que deve ser assumido como canonico

- A `Mesa` oficial e unica e a superficie `SSR` do `web/`.
- A antiga `mesa-next` foi removida do runtime do repositorio e nao deve mais ser tratada como superficie ativa.
- O legado visual antigo do inspetor foi removido fisicamente; nao assumir existencia de `web/templates/base.html`, `web/static/css/shared/layout.css` ou dos antigos bundles `chat_*`/`inspetor/*` aposentados na trilha visual.
- O gate oficial local da Mesa e `make mesa-smoke`.
- O aceite operacional da Mesa SSR e `make mesa-acceptance`.
- O runner documental oficial e `make document-acceptance`.
- O runner mobile real oficial e `make smoke-mobile`.
- O gate principal local do repositorio hoje continua sendo `make verify`, mas ele ainda nao inclui `smoke-mobile`.
- O mobile real esta funcional no runner oficial, mas a arquitetura de rollout V2 ainda esta em transicao.

## 3. Estrutura macro do repositorio

| Caminho | Papel |
| --- | --- |
| `web/` | Backend web, frontend SSR, templates, assets, migracoes e testes |
| `android/` | App mobile React Native + Expo do inspetor |
| `docs/` | Documentacao tecnica, auditorias, handoff e roadmap historico |
| `scripts/` | Automacao local, runners oficiais e utilitarios operacionais |
| `.github/workflows/` | Automacao CI |
| `render.yaml` | Blueprint versionado do deploy web |
| `Makefile` | Orquestracao local dos gates principais |

## 4. Entradas principais do sistema

### Backend web

- `web/main.py` e o entrypoint real.
- `create_app()` monta a app FastAPI.
- `lifespan()` inicializa banco e realtime do revisor.
- `web/app/domains/router_registry.py` expoe os roteadores dos portais.

### Frontend web

- `web/templates/index.html` e o portal do inspetor.
- `web/templates/painel_revisor.html` e o portal da Mesa/revisor.
- `web/templates/cliente_portal.html` e o portal admin-cliente.
- `web/templates/admin/dashboard.html` e o dashboard do admin da plataforma.

### Frontend mobile

- `android/App.tsx` entra no app.
- `android/src/features/InspectorMobileApp.tsx` e o shell principal.
- `android/src/config/api.ts` agrega os clientes de API.
- `android/src/config/mesaApi.ts` e a fronteira principal do mobile para a Mesa.

## 5. Arquitetura do backend

- O backend esta organizado como monolito modular em `web/app/domains/`.
- `web/app/core/` concentra runtime HTTP, seguranca de headers, logging e setup.
- `web/app/shared/` concentra banco, modelos, auth, sessao, tenancy e contratos.
- `web/nucleo/` concentra integracoes pesadas como IA, OCR e PDF.

### Dominios centrais

| Dominio | Papel | Arquivos mais importantes |
| --- | --- | --- |
| `admin` | gestao SaaS, clientes, planos, dashboard e governanca da plataforma | `routes.py`, `client_routes.py`, `services.py`, `portal_support.py` |
| `chat` | portal do inspetor, laudo, chat IA, mesa, pendencias e API mobile | `router.py`, `laudo.py`, `mesa.py`, `laudo_service.py`, `auth_*_routes.py` |
| `cliente` | portal admin-cliente, shell multiaba e bridge explicita para chat/mesa | `routes.py`, `chat_routes.py`, `management_routes.py`, `portal_bridge.py` |
| `mesa` | contratos, anexos e pacote operacional da Mesa | `contracts.py`, `attachments.py`, `service.py` |
| `revisor` | Mesa/revisor, fila, respostas, realtime, templates e shell SSR | `panel.py`, `mesa_api.py`, `realtime.py`, `ws.py`, `templates_laudo*.py` |

### Camada shared

- `web/app/shared/database.py` e a facade central do banco.
- `web/app/shared/security.py` e a facade central de auth e RBAC.
- `web/app/shared/security_session_store.py` mistura cache local e persistencia em banco para sessao ativa.
- `web/app/shared/security_portal_state.py` separa estado por portal.
- `web/app/shared/tenant_access.py` ajuda no escopo por empresa.

### Banco e modelos principais

- `Empresa`
- `Usuario`
- `LimitePlano`
- `SessaoAtiva`
- `PreferenciaMobileUsuario`
- `RegistroAuditoriaEmpresa`
- `AprendizadoVisualIa`
- `Laudo`
- `MensagemLaudo`
- `LaudoRevisao`
- `CitacaoLaudo`
- `TemplateLaudo`
- `AnexoMesa`

### Observacoes estruturais do banco

- Ha indices nas tabelas principais.
- Os hotspots conhecidos estao mais em composicao de consulta, agregacao, volume historico e codigo grande demais do que em ausencia total de indice.

## 6. Configuracao, runtime e seguranca

### Arquivos principais

- `web/app/core/settings.py`
- `web/app/core/http_runtime_support.py`
- `web/app/core/http_setup_support.py`
- `web/app/core/logging_support.py`

### O que essa camada faz

- valida env vars;
- configura logging;
- monta CSP e headers de seguranca;
- ativa `SessionMiddleware`, `TrustedHostMiddleware`, `GZipMiddleware` e `SlowAPIMiddleware`;
- gera `X-Correlation-ID`;
- registra `/health`, `/ready`, `/favicon.ico`, manifesto e service worker.

### Sessao e autenticacao

- O web usa sessao por cookie para os portais HTML.
- O mobile usa bearer token.
- Ha isolamento explicito entre `/admin`, `/cliente`, `/app` e `/revisao`.
- No admin, acesso valido nao depende so de role; tambem depende de contexto correto de portal e escopo de plataforma.
- O armazenamento de sessao atual ainda e hibrido memoria + banco, o que e funcional localmente mas segue como ponto de hardening para multi-instancia.

## 7. Integracoes externas

| Integracao | Onde | Papel |
| --- | --- | --- |
| Google Gemini | `web/nucleo/cliente_ia.py` | resposta IA, streaming e fluxos de geracao assistida |
| Google Vision | `web/nucleo/cliente_ia.py` | OCR de imagem |
| Redis | `web/app/domains/revisor/realtime.py` | backend distribuido do realtime do revisor |
| PDF/Doc generation | `web/nucleo/gerador_laudos.py`, `template_editor_word.py`, `template_laudos.py` | export, preview e geracao documental |
| Chart.js | `web/templates/admin/dashboard.html` | graficos do admin |
| PDF.js | `web/templates/revisor_templates_biblioteca.html` | preview de templates |

## 8. Rotas principais do sistema

### Operacionais

- `/`
- `/health`
- `/ready`
- `/debug-sessao`

### Admin da plataforma

- `/admin/login`
- `/admin/painel`
- `/admin/clientes`
- `/admin/clientes/{empresa_id}`
- `/admin/novo-cliente`
- `/admin/api/metricas-grafico`

### Inspetor web

- `/app/login`
- `/app/`
- `/app/planos`
- `/app/trocar-senha`
- `/app/api/chat`
- `/app/api/feedback`
- `/app/api/gerar_pdf`
- `/app/api/laudo/status`
- `/app/api/laudo/iniciar`
- `/app/api/laudo/cancelar`
- `/app/api/laudo/desativar`
- `/app/api/laudo/{laudo_id}/finalizar`
- `/app/api/laudo/{laudo_id}/reabrir`
- `/app/api/laudo/{laudo_id}/revisoes`
- `/app/api/laudo/{laudo_id}/mensagens`
- `/app/api/laudo/{laudo_id}/gate-qualidade`
- `/app/api/laudo/{laudo_id}/mesa/mensagem`
- `/app/api/laudo/{laudo_id}/mesa/anexo`
- `/app/api/laudo/{laudo_id}/mesa/mensagens`
- `/app/api/laudo/{laudo_id}/mesa/resumo`
- `/app/api/laudo/{laudo_id}/pendencias`
- `/app/api/notificacoes/sse`
- `/app/api/perfil`
- `/app/api/upload_doc`

### Inspetor mobile API

- `/app/api/mobile/auth/login`
- `/app/api/mobile/auth/logout`
- `/app/api/mobile/bootstrap`
- `/app/api/mobile/laudos`
- `/app/api/mobile/mesa/feed`
- `/app/api/mobile/account/profile`
- `/app/api/mobile/account/photo`
- `/app/api/mobile/account/password`
- `/app/api/mobile/account/settings`
- `/app/api/mobile/support/report`

### Admin-cliente

- `/cliente/login`
- `/cliente/painel`
- `/cliente/api/bootstrap`
- `/cliente/api/empresa/resumo`
- `/cliente/api/auditoria`
- `/cliente/api/usuarios`
- `/cliente/api/chat/laudos`
- `/cliente/api/chat/mensagem`
- `/cliente/api/chat/upload_doc`
- `/cliente/api/mesa/laudos`
- `/cliente/api/mesa/laudos/{laudo_id}/mensagens`
- `/cliente/api/mesa/laudos/{laudo_id}/completo`
- `/cliente/api/mesa/laudos/{laudo_id}/pacote`
- `/cliente/api/mesa/laudos/{laudo_id}/responder`
- `/cliente/api/mesa/laudos/{laudo_id}/responder-anexo`

### Revisor

- `/revisao/login`
- `/revisao/painel`
- `/revisao/templates-laudo`
- `/revisao/templates-laudo/editor`
- `/revisao/api/laudo/{laudo_id}/mensagens`
- `/revisao/api/laudo/{laudo_id}/completo`
- `/revisao/api/laudo/{laudo_id}/pacote`
- `/revisao/api/laudo/{laudo_id}/responder`
- `/revisao/api/laudo/{laudo_id}/responder-anexo`
- `/revisao/api/laudo/{laudo_id}/avaliar`
- `/revisao/api/laudo/{laudo_id}/pendencias/{mensagem_id}`
- `/revisao/api/laudo/{laudo_id}/aprendizados`
- `/revisao/api/aprendizados/{aprendizado_id}/validar`
- `/revisao/api/templates-laudo*`
- `/revisao/ws/whispers`

## 9. Frontend web

### Arquitetura geral

- O frontend web e SSR com Jinja2, mas varias paginas funcionam como shells fortemente hidratados.
- Nao ha bundler moderno dedicado no workspace web.
- Os scripts ainda dependem de ordem de carregamento.
- Ainda existem globais compartilhadas em `window`.
- Existe service worker em `web/static/js/shared/trabalhador_servico.js`.

### Telas principais

| Area | Template principal | Estilo de renderizacao |
| --- | --- | --- |
| Inspetor | `web/templates/index.html` | SSR + hidratacao forte |
| Revisor | `web/templates/painel_revisor.html` | SSR + shell operacional da Mesa |
| Cliente | `web/templates/cliente_portal.html` | SSR + shell quase SPA |
| Admin | `web/templates/admin/dashboard.html` | SSR com enhancement |
| Templates do revisor | `web/templates/revisor_templates_*.html` | SSR + app client-side dedicado |

### Arquivos web mais criticos

- `web/templates/index.html`
- `web/templates/inspetor/base.html`
- `web/templates/painel_revisor.html`
- `web/templates/cliente_portal.html`
- `web/templates/admin/dashboard.html`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/cliente/portal.js`
- `web/static/js/shared/api-core.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-network.js`
- `web/static/js/shared/ui.js`
- `web/static/js/revisor/templates_biblioteca_page.js`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/inspetor/reboot.css`
- `web/static/css/inspetor/workspace_chrome.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/inspetor/workspace_rail.css`
- `web/static/css/inspetor/workspace_states.css`
- `web/static/css/revisor/painel_revisor.css`
- `web/static/css/cliente/portal.css`

### Observacao importante

- A Mesa web atual deve ser entendida como uma unica superficie SSR.
- Qualquer documento antigo que fale de `mesa-next`, `frontend paralelo da Mesa` ou rollout de UI separado para o revisor pode estar historicamente correto, mas nao representa mais o estado canonico.

## 10. Frontend mobile

### Stack e estrutura

- Expo + React Native + TypeScript.
- Entrada em `android/App.tsx`.
- Shell principal em `android/src/features/InspectorMobileApp.tsx`.
- Clientes de API em `android/src/config/`.
- Features de chat, Mesa, historico, offline, seguranca, sessao e settings em `android/src/features/`.
- Persistencia local em `android/src/settings/`.

### APIs usadas pelo mobile

- `android/src/config/chatApi.ts` consome chat, status de laudo e historico.
- `android/src/config/mesaApi.ts` consome Mesa, anexos, resumo, feed e thread.
- `android/src/config/authApi.ts` consome login, bootstrap e logout.
- `android/src/config/mobileV2Rollout.ts` interpreta capacidades, rollout e fallback da trilha V2.

### Observacao importante

- O mobile reutiliza o backend do inspetor web.
- Nao existe backend movel separado.
- O mobile real ja possui runner oficial funcional (`make smoke-mobile`), mas ainda carrega complexidade de rollout/transicao V2.
- O estado atual do rollout mobile ainda inclui valores como `pilot_enabled`, `candidate_for_promotion`, `promoted`, `hold` e `rollback_forced`.

## 11. Fluxos principais do produto

### Login e autenticacao

- Cada portal possui login proprio.
- O isolamento por portal e requisito estrutural.
- O mobile usa bearer token.

### Inspetor web

- `GET /app/` renderiza `index.html`.
- A pagina injeta contexto inicial.
- O JS assume boa parte da operacao da interface.
- O frontend passa a chamar `/app/api/*` e `/app/api/notificacoes/sse`.

### Chat do inspetor

- Entrada principal: `POST /app/api/chat`.
- O fluxo faz:
  - validacao de request
  - criacao ou carregamento de `Laudo`
  - persistencia de `MensagemLaudo`
  - chamada a IA
  - streaming da resposta
  - persistencia de citacoes e metadados
  - interacao com Mesa quando necessario

### Mesa avaliadora

- Inspetor usa `/app/api/laudo/{id}/mesa/*`.
- Revisor usa `/revisao/api/laudo/{id}/*`.
- Cliente usa `/cliente/api/mesa/*`.
- Revisor tambem usa `/revisao/ws/whispers`.
- O shell oficial do revisor e o SSR em `web/templates/painel_revisor.html`.

### Portal cliente

- `cliente_portal.html` funciona como shell unica.
- Ha tres areas principais: admin, chat e Mesa.
- O portal reaproveita `chat` e `revisor` via `portal_bridge.py`.
- Esse bridge continua funcional, mas ainda representa um ponto de acoplamento arquitetural conhecido.

### Biblioteca de templates

- Biblioteca em `/revisao/templates-laudo`.
- Editor rico em `/revisao/templates-laudo/editor`.
- APIs para CRUD, diff, preview, publicar, status, clone e assets.

### Mobile

- login bearer
- bootstrap
- lista de laudos
- historico do laudo
- chat do laudo
- Mesa do laudo
- feed mobile de Mesa
- thread mobile da Mesa
- fila offline
- operator run e organic validation no runner oficial

## 12. Gates e validacao

### Gates principais do repositorio

- `make verify`: gate principal local rapido
- `make contract-check`: contratos sensiveis
- `make mesa-smoke`: gate oficial local da Mesa SSR
- `make mesa-acceptance`: aceite operacional via Playwright
- `make document-acceptance`: fase documental
- `make observability-acceptance`: observabilidade, operacao e seguranca
- `make smoke-mobile`: smoke real controlado do mobile com emulador + Maestro

### Leitura correta do estado atual

- `make verify` passa, mas nao cobre tudo o que define o projeto como funcional de ponta a ponta.
- `make smoke-mobile` e `make document-acceptance` devem ser considerados gates relevantes de pronto real, mesmo nao estando dentro de `verify`.
- Historicos antigos de CI e baseline podem ficar atras desse estado.

## 13. Pendencias e riscos abertos que outra IA deve conhecer

- O mobile V2 ainda nao esta arquiteturalmente encerrado; rollout e fallback legado continuam existindo.
- `portal_bridge.py` ainda e uma fronteira de acoplamento importante no portal cliente.
- `security_session_store.py` ainda mistura cache local e persistencia em banco.
- A politica operacional final de backup, retencao, limpeza e restore de anexos/uploads ainda precisa de fechamento explicito.
- Existe hotspot tecnico relevante em arquivos grandes como `web/app/domains/admin/services.py`, `web/app/v2/mobile_rollout.py`, `web/app/v2/mobile_organic_validation.py`, `web/static/js/chat/chat_index_page.js`, `android/src/config/mesaApi.ts` e `android/src/config/mobileV2MesaAdapter.ts`.
- Os testes de contrato administrativos ainda usam `jsonschema.RefResolver`, hoje depreciado.

## 14. Como interpretar a documentacao do repositorio

- `docs/full-system-audit/` e util para orientacao e auditoria, mas nem todo arquivo ali representa o estado mais recente.
- `docs/restructuring-roadmap/` contem muito material historico de execucao e pode estar defasado.
- Para estado operacional mais atual, consultar junto:
  - `Makefile`
  - `Tarie 2/docs/migration/CHECKPOINT_ATUAL.md`
  - `Tarie 2/docs/migration/FINALIZACAO_CHECKLIST_MASTER.md`
  - artifacts recentes em `artifacts/`

## 15. Regras de leitura para outra IA

- Nao assumir existencia de `mesa-next`; ela foi removida.
- Nao assumir que `verify` cobre todo o pronto real do produto.
- Nao tratar o mobile como arquitetura finalizada; ele esta funcional, mas ainda em transicao controlada de rollout.
- Nao confiar em um documento historico isolado quando ele conflitar com `Makefile`, testes atuais, runners oficiais ou artifacts recentes.
- Quando houver duvida entre documentacao e codigo, confiar primeiro no codigo e nos gates executaveis.
