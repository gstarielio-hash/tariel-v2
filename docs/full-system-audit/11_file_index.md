# 11. Índice de Arquivos Mais Importantes

Este índice é curado. Ele não tenta listar o repositório inteiro, e sim os arquivos que mais ajudam a entender o sistema ou que concentram maior criticidade técnica.

## Root, bootstrap e infraestrutura

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `render.yaml` | Blueprint de deploy da stack web | Muito alta | Define serviço web, Postgres e Redis versionados no repo. |
| `Makefile` | Orquestra comandos de CI local | Média | Útil para entender como web e mobile são validados. |
| `.github/workflows/ci.yml` | CI principal | Alta | Expõe a régua de qualidade do projeto. |
| `web/README.md` | Guia do workspace web | Alta | Resume domínios, setup e pipeline. |
| `web/PROJECT_MAP.md` | Mapa rápido do sistema web | Alta | Bom atalho arquitetural produzido pelo próprio projeto. |
| `web/app/ARCHITECTURE.md` | Visão formal do monólito modular | Alta | Complementa a leitura do código. |

## Backend core e shared

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/main.py` | Entry point FastAPI | Muito alta | Monta toda a aplicação. |
| `web/app/domains/router_registry.py` | Registro dos roteadores | Alta | Expõe a topologia dos portais. |
| `web/app/core/settings.py` | Configuração central | Muito alta | Fonte de verdade das env vars. |
| `web/app/core/http_runtime_support.py` | Middlewares e headers | Muito alta | Segurança HTTP, correlação e cache policy. |
| `web/app/core/http_setup_support.py` | OpenAPI, exceções e rotas operacionais | Alta | Também controla service worker e readiness. |
| `web/app/core/logging_support.py` | Logging estruturado | Alta | Base de observabilidade do backend. |
| `web/app/shared/database.py` | Facade de dados e sessão | Muito alta | Maior hub de importação interna. |
| `web/app/shared/db/runtime.py` | Engine e URL de banco | Alta | Separa runtime SQLite/Postgres. |
| `web/app/shared/db/models_auth.py` | Modelos de auth/empresa/sessão | Muito alta | Base de multiempresa e usuários. |
| `web/app/shared/db/models_laudo.py` | Modelos operacionais do laudo | Muito alta | Núcleo persistente do produto. |
| `web/app/shared/security.py` | Auth, RBAC e sessão | Muito alta | Segunda maior dependência transversal. |
| `web/app/shared/security_session_store.py` | Controle de sessões ativas | Muito alta | Mistura cache, persistência e política de sessão. |
| `web/app/shared/security_portal_state.py` | Isolamento por portal | Alta | Crítico para evitar vazamento entre áreas. |
| `web/app/shared/tenant_access.py` | Escopo por empresa | Alta | Requisito central de multiempresa. |

## Domínio admin

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/app/domains/admin/routes.py` | Login e painel admin CEO | Alta | Porta de entrada do SaaS admin. |
| `web/app/domains/admin/client_routes.py` | Gestão de clientes/empresas | Alta | Interface HTML e ações operacionais. |
| `web/app/domains/admin/services.py` | Regras SaaS e métricas | Muito alta | Arquivo grande e central na camada admin. |
| `web/app/domains/admin/portal_support.py` | Helpers de portal | Média | Suporte a template, CSRF e redirects. |

## Domínio chat / inspetor

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/app/domains/chat/router.py` | Agregador do portal inspetor | Alta | Inclui os subrouters do domínio. |
| `web/app/domains/chat/auth_portal_routes.py` | Login, home e perfil web do inspetor | Muito alta | Define a página principal `/app/`. |
| `web/app/domains/chat/auth_mobile_routes.py` | Auth e bootstrap mobile | Muito alta | Superfície usada pelo app Expo. |
| `web/app/domains/chat/chat_stream_routes.py` | Fluxo principal do chat | Muito alta | Hotspot principal do backend. |
| `web/app/domains/chat/chat_service.py` | Serviços de mensagens e uploads | Alta | Reusado por outras superfícies. |
| `web/app/domains/chat/laudo.py` | Ciclo de vida do laudo | Muito alta | Estados, revisões e gates. |
| `web/app/domains/chat/laudo_service.py` | Serviços do laudo | Alta | Reuso entre portais. |
| `web/app/domains/chat/mesa.py` | Mesa do inspetor e feed mobile | Muito alta | Liga campo, revisor e mobile. |
| `web/app/domains/chat/learning.py` | API de aprendizado visual | Alta | Registra e lista correções do inspetor. |
| `web/app/domains/chat/learning_helpers.py` | Regras de aprendizado visual | Alta | Lado mais denso da feature. |
| `web/app/domains/chat/pendencias.py` | APIs de pendências | Alta | Fluxo sensível de mesa/ajustes. |
| `web/app/domains/chat/gate_helpers.py` | Gate de qualidade do laudo | Alta | Regras críticas de finalização. |
| `web/app/domains/chat/chat_runtime.py` | Constantes e executor do chat | Alta | Limites e `ThreadPoolExecutor`. |
| `web/app/domains/chat/chat_runtime_support.py` | SSE e suporte do runtime | Alta | Notificações do inspetor. |

## Domínio cliente

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/app/domains/cliente/routes.py` | Login, shell e bootstrap do portal cliente | Muito alta | Porta de entrada do admin-cliente. |
| `web/app/domains/cliente/chat_routes.py` | Chat e mesa company-scoped | Muito alta | Grande superfície do portal cliente. |
| `web/app/domains/cliente/management_routes.py` | Gestão da empresa e usuários | Alta | Cruza com `admin.services`. |
| `web/app/domains/cliente/portal_bridge.py` | Bridge para `chat` e `revisor` | Muito alta | Melhor evidência de acoplamento entre domínios. |
| `web/app/domains/cliente/route_support.py` | Sessão, render e CSRF do portal cliente | Alta | Infra do próprio portal. |

## Domínio revisor e mesa

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/app/domains/revisor/routes.py` | Fachada compatível do domínio | Alta | Exporta a superfície consolidada do revisor. |
| `web/app/domains/revisor/base.py` | Router base, schemas e helpers comuns | Alta | Camada estrutural do revisor. |
| `web/app/domains/revisor/auth_portal.py` | Login/troca de senha do revisor | Alta | Entrada do portal da mesa. |
| `web/app/domains/revisor/panel.py` | Monta fila e métricas da mesa | Muito alta | Hotspot de consulta e renderização. |
| `web/app/domains/revisor/mesa_api.py` | APIs operacionais do revisor | Muito alta | Histórico, pacote, resposta e avaliação. |
| `web/app/domains/revisor/service.py` | Serviços de aplicação do revisor | Alta | Coordena operações centrais. |
| `web/app/domains/revisor/realtime.py` | Redis/memory realtime | Muito alta | Base do WebSocket e notificações. |
| `web/app/domains/revisor/ws.py` | WebSocket `/revisao/ws/whispers` | Alta | Canal realtime do revisor. |
| `web/app/domains/revisor/learning_api.py` | Validação de aprendizados | Alta | Fecha o ciclo inspetor -> revisor. |
| `web/app/domains/revisor/templates_laudo.py` | Biblioteca de templates | Muito alta | Subsystem grande e crítico. |
| `web/app/domains/revisor/templates_laudo_editor_routes.py` | Editor rico e assets | Muito alta | Rota de CRUD/preview do editor. |
| `web/app/domains/revisor/templates_laudo_management_routes.py` | Publicação, status e lote | Alta | Governa ciclo de vida do template. |
| `web/app/domains/revisor/templates_laudo_support.py` | Helpers do subsystem de templates | Muito alta | Grande e denso. |
| `web/app/domains/revisor/templates_laudo_diff.py` | Diff entre templates | Alta | Apoio documental especializado. |

## Domínio mesa e núcleo

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/app/domains/mesa/contracts.py` | Contratos da mesa | Alta | Estrutura dados compartilhados da operação. |
| `web/app/domains/mesa/attachments.py` | Anexos da mesa | Alta | Regras de arquivo e serialização. |
| `web/app/domains/mesa/service.py` | Pacote operacional da mesa | Alta | Reuso entre inspetor, cliente e revisor. |
| `web/nucleo/cliente_ia.py` | Integração com Gemini/Vision | Muito alta | Hotspot de IA, OCR e custo externo. |
| `web/nucleo/gerador_laudos.py` | PDFs operacionais | Alta | Exportações e relatórios. |
| `web/nucleo/template_editor_word.py` | Preview/export do editor rico | Alta | Ponto pesado do subsystem de templates. |

## Frontend web

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/templates/index.html` | Portal do inspetor | Muito alta | Página SSR mais importante do produto. |
| `web/templates/inspetor/base.html` | Shell moderna do inspetor | Muito alta | Base técnica da experiência web do inspetor. |
| `web/templates/painel_revisor.html` | Portal da mesa | Muito alta | Página principal do revisor. |
| `web/templates/cliente_portal.html` | Portal admin-cliente | Muito alta | Uma shell única para três áreas. |
| `web/templates/admin/dashboard.html` | Dashboard admin CEO | Alta | Painel administrativo e métricas. |
| `web/templates/revisor_templates_biblioteca.html` | Biblioteca de templates | Alta | Interface documental do revisor. |
| `web/templates/revisor_templates_editor_word.html` | Editor rico de templates | Alta | Tela especializada e sensível. |
| `web/static/js/chat/chat_index_page.js` | Controller central do inspetor | Muito alta | Maior JS do web. |
| `web/static/js/chat/chat_painel_core.js` | Núcleo dos painéis do chat | Alta | Apoio ao runtime do inspetor. |
| `web/static/js/inspetor/mesa_widget.js` | Widget da mesa no inspetor | Alta | Conecta parte crítica da UX. |
| `web/static/js/inspetor/notifications_sse.js` | Notificações SSE | Alta | Depende do fluxo realtime do inspetor. |
| `web/static/js/cliente/portal.js` | Runtime do portal cliente | Muito alta | Grande controller único. |
| `web/static/js/shared/api-core.js` | Base de chamadas HTTP | Muito alta | Compartilhado pelo runtime. |
| `web/static/js/shared/api.js` | API client compartilhado | Muito alta | Hub client-side importante. |
| `web/static/js/shared/chat-network.js` | Rede do chat | Alta | Ligação entre UI e backend do inspetor. |
| `web/static/js/shared/ui.js` | Utilitários de interface | Alta | Também participa do boot do inspetor. |
| `web/static/js/revisor/templates_biblioteca_page.js` | Runtime da biblioteca de templates | Alta | Grande JS do subsistema revisor. |
| `web/static/css/shared/official_visual_system.css` | Sistema visual canônico | Muito alta | Tokens e contratos compartilhados das superfícies oficiais. |
| `web/static/css/inspetor/reboot.css` | Shell visual do inspetor | Alta | Muito grande e estrutural. |
| `web/static/css/inspetor/workspace_chrome.css` | Slice de chrome do workspace | Alta | Header, tabs e toolbar do `/app`. |
| `web/static/css/inspetor/workspace_history.css` | Slice do histórico do inspetor | Alta | Timeline e estados de leitura do histórico. |
| `web/static/css/inspetor/workspace_rail.css` | Slice da rail e Mesa | Alta | Progresso, contexto, pendências e card da mesa. |
| `web/static/css/inspetor/workspace_states.css` | Slice de estados compartilhados | Alta | Empty states, composer e estados focados. |
| `web/static/css/revisor/painel_revisor.css` | Estilo da mesa | Alta | Grande e central na UX do revisor. |
| `web/static/css/cliente/portal.css` | Estilo do portal cliente | Alta | Sustenta uma tela muito grande. |
| `web/static/js/shared/trabalhador_servico.js` | Service worker | Alta | Estratégia de cache do inspetor. |

## Mobile

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `android/package.json` | Dependências e scripts do app | Alta | Resume o stack do mobile. |
| `android/App.tsx` | Entrada do app | Alta | Injeta o shell principal. |
| `android/src/features/InspectorMobileApp.tsx` | Shell e controller do app | Muito alta | Arquivo grande e central. |
| `android/src/config/api.ts` | Agregador dos clientes de API | Alta | Ponte formal com o backend. |
| `android/src/config/chatApi.ts` | Cliente do chat | Muito alta | Mostra rotas centrais consumidas. |
| `android/src/config/mesaApi.ts` | Cliente da mesa | Muito alta | Mostra rotas de mesa consumidas. |
| `android/src/config/authApi.ts` | Auth mobile | Alta | Login/bearer/bootstrap. |
| `android/src/settings/` | Persistência local e schema | Alta | Sustenta settings críticos e comportamento local. |
| `android/eas.json` | Pipeline de build/distribuição | Média | Importante para operação mobile. |

## Testes e documentação útil

| Caminho | Papel | Criticidade | Observações |
| --- | --- | --- | --- |
| `web/tests/test_smoke.py` | Smoke geral | Alta | Bom primeiro termômetro do sistema. |
| `web/tests/test_regras_rotas_criticas.py` | Regras críticas | Muito alta | Suíte enorme e sensível. |
| `web/tests/e2e/test_portais_playwright.py` | Fluxos E2E dos portais | Muito alta | Confirma o comportamento ponta a ponta. |
| `web/tests/test_revisor_realtime.py` | Realtime do revisor | Alta | Importante para SSE/WS/Redis. |
| `web/tests/test_portais_acesso_critico.py` | Isolamento de acesso | Alta | Muito útil para mudanças de auth. |
| `web/docs/frontend_mapa.md` | Mapa atual do frontend web | Alta | Complementa a auditoria. |
| `web/docs/inspector-understanding-packet/10_FOR_CHATGPT.md` | Handoff já existente do inspetor | Média | Útil quando o foco for apenas o inspetor. |

## Confirmado no código

- Os arquivos acima concentram os pontos de entrada, acoplamentos e riscos mais relevantes do sistema.
- O domínio `chat` e o subsistema `revisor/templates` merecem atenção proporcionalmente maior do que seu número bruto de arquivos sugeriria.

## Inferência provável

- Para qualquer análise futura, a melhor estratégia é começar por esse índice em vez de percorrer o repositório por ordem alfabética.

## Dúvida aberta

- Alguns documentos históricos ainda citam assets visuais já removidos do inspetor. O índice acima prioriza apenas caminhos vivos do runtime oficial.
