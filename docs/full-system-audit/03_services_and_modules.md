# 03. Mapa de Serviços e Módulos

Este documento resume os grandes módulos do sistema, explicando objetivo, dependências, responsabilidades e pontos de uso. A unidade de análise aqui não é “arquivo isolado”, e sim “bloco funcional”.

## 1. Bootstrap da aplicação web

| Item | Descrição |
| --- | --- |
| Objetivo | Subir a aplicação FastAPI, registrar middlewares, montar estáticos e incluir os portais. |
| Pasta principal | `web/` e `web/app/core/` |
| Arquivos centrais | `web/main.py`, `web/app/core/http_runtime_support.py`, `web/app/core/http_setup_support.py`, `web/app/domains/router_registry.py` |
| Dependências | FastAPI, SlowAPI, SQLAlchemy, SessionMiddleware, StaticFiles |
| Responsabilidades | Lifespan, readiness, segurança HTTP, OpenAPI custom, roteadores e redirecionamento inicial por perfil. |
| Onde é usado | Em toda a execução do backend web. |

Leitura arquitetural:

- `create_app()` em `web/main.py` é a origem real da aplicação.
- O bootstrap conhece explicitamente os portais admin, cliente, inspetor e revisor.
- O lifespan também inicializa banco e realtime do revisor.

## 2. Configuração e runtime compartilhado

| Item | Descrição |
| --- | --- |
| Objetivo | Centralizar configuração de ambiente, logging, segurança HTTP e apoio de runtime. |
| Pasta principal | `web/app/core/` |
| Arquivos centrais | `settings.py`, `logging_support.py`, `http_runtime_support.py`, `http_setup_support.py` |
| Dependências | Variáveis de ambiente, headers de segurança, CSP, GZip, TrustedHost, SlowAPI |
| Responsabilidades | Validar env vars, configurar logging, CSP, correlação de requisições, docs e endpoints operacionais. |
| Onde é usado | Em todo request do sistema web. |

Ponto importante:

- Essa camada concentra decisões de segurança e observabilidade mais do que de negócio.

## 3. Banco, modelos e sessão

| Item | Descrição |
| --- | --- |
| Objetivo | Persistir empresas, usuários, laudos, mensagens, templates, auditoria e sessões. |
| Pasta principal | `web/app/shared/` e `web/app/shared/db/` |
| Arquivos centrais | `database.py`, `db/runtime.py`, `db/models_auth.py`, `db/models_laudo.py`, `db/bootstrap.py` |
| Dependências | SQLAlchemy, Alembic, Postgres/SQLite |
| Responsabilidades | Engine, session factory, contrato transacional, modelos, índices, bootstrap e migrações. |
| Onde é usado | Em praticamente todos os domínios do backend. |

Leitura arquitetural:

- `web/app/shared/database.py` é a grande facade do ecossistema de dados.
- O sistema é multiempresa de verdade: `Empresa`, `Usuario`, `Laudo` e artefatos associados carregam `empresa_id`.
- A sessão do FastAPI com `obter_banco()` faz commit automático quando detecta mutação pendente.

## 4. Segurança, autenticação e isolamento por portal

| Item | Descrição |
| --- | --- |
| Objetivo | Autenticar usuários, aplicar RBAC e separar estado entre portais. |
| Pasta principal | `web/app/shared/` |
| Arquivos centrais | `security.py`, `security_session_store.py`, `security_portal_state.py`, `tenant_access.py` |
| Dependências | Sessão HTTP, bearer token mobile, Argon2, bcrypt legado, tabela `sessoes_ativas` |
| Responsabilidades | Login HTML, autenticação mobile, troca de senha, políticas de sessão, portal scoping, controle de acesso por empresa. |
| Onde é usado | Todos os portais e APIs autenticadas. |

Leitura arquitetural:

- O sistema suporta autenticação HTML por sessão e autenticação bearer para o app mobile.
- O isolamento entre `/admin`, `/cliente`, `/app` e `/revisao` não é implícito: ele é tratado como requisito explícito pelo código.
- `security_session_store.py` mistura memória e persistência em banco, o que aumenta controle, mas também acoplamento.

## 5. Domínio `admin`

| Item | Descrição |
| --- | --- |
| Objetivo | Operar a visão SaaS: clientes, empresas, planos, limites e usuários sob a diretoria. |
| Pasta principal | `web/app/domains/admin/` |
| Arquivos centrais | `routes.py`, `client_routes.py`, `services.py`, `portal_support.py` |
| Dependências | `app.shared.database`, `app.shared.security`, Jinja, métricas SQL |
| Responsabilidades | Login admin, dashboard, onboarding de cliente, gestão de plano, criação e bloqueio de usuários da empresa. |
| Onde é usado | Portal `/admin`. |

Leitura arquitetural:

- `services.py` concentra onboarding, métricas e regras comerciais.
- `client_routes.py` é a face HTTP/SSR da gestão de clientes.
- O admin CEO não parece ser o módulo mais complexo em UX, mas é sensível porque governa a configuração comercial do restante do sistema.

## 6. Domínio `chat` / portal do inspetor

| Item | Descrição |
| --- | --- |
| Objetivo | Concentrar o portal do inspetor, laudo, chat com IA, mesa, pendências, perfil e APIs mobile do inspetor. |
| Pasta principal | `web/app/domains/chat/` |
| Arquivos centrais | `router.py`, `auth_portal_routes.py`, `auth_mobile_routes.py`, `chat_stream_routes.py`, `laudo.py`, `mesa.py`, `learning.py`, `pendencias.py` |
| Dependências | `shared`, `nucleo/cliente_ia.py`, Jinja, SSE, sessão, RBAC |
| Responsabilidades | Login inspetor, home do portal, ciclo do laudo, chat IA, SSE de notificações, feed mobile, mesa e aprendizado visual. |
| Onde é usado | Portal `/app`, APIs `/app/api/*` e mobile `/app/api/mobile/*`. |

Leitura arquitetural:

- É o maior domínio do sistema.
- `router.py` agrega subrouters uma única vez, evitando duplicação ao incluir o portal.
- `chat_stream_routes.py` é o fluxo mais carregado do produto: valida request, cria laudo, salva mensagem, aciona IA, lida com comandos rápidos, mesa e streaming.

## 7. Domínio `cliente`

| Item | Descrição |
| --- | --- |
| Objetivo | Oferecer ao admin-cliente um portal unificado para administração da empresa, chat operacional e mesa. |
| Pasta principal | `web/app/domains/cliente/` |
| Arquivos centrais | `routes.py`, `chat_routes.py`, `management_routes.py`, `portal_bridge.py`, `dashboard_bootstrap.py` |
| Dependências | `admin.services`, `chat`, `revisor`, `shared`, Jinja |
| Responsabilidades | Login do admin-cliente, bootstrap do painel, resumo da empresa, gestão de usuários, chat company-scoped e operação company-scoped da mesa. |
| Onde é usado | Portal `/cliente`. |

Leitura arquitetural:

- `portal_bridge.py` é peça central porque explicita reuso entre domínios em vez de duplicar lógica.
- Esse portal é híbrido: usa suas próprias telas, mas reaproveita serviços do inspetor e do revisor.
- Arquiteturalmente é um módulo de composição e escopo multiempresa mais do que um domínio totalmente autônomo.

## 8. Domínio `revisor`

| Item | Descrição |
| --- | --- |
| Objetivo | Operar a mesa avaliadora, a fila técnica, whispers, learnings e a biblioteca de templates de laudo. |
| Pasta principal | `web/app/domains/revisor/` |
| Arquivos centrais | `panel.py`, `mesa_api.py`, `auth_portal.py`, `realtime.py`, `ws.py`, `templates_laudo.py`, `templates_laudo_editor_routes.py`, `templates_laudo_management_routes.py`, `service.py` |
| Dependências | `shared`, `mesa`, Jinja, Redis opcional, WebSocket |
| Responsabilidades | Login revisor, fila operacional, respostas ao campo, pendências, learnings, realtime e gestão de templates. |
| Onde é usado | Portal `/revisao`, APIs `/revisao/api/*`, WebSocket `/revisao/ws/whispers`. |

Leitura arquitetural:

- Esse domínio contém, na prática, dois produtos: a mesa avaliadora e a biblioteca/editor de templates.
- `realtime.py` implementa transporte plugável `memory` ou `redis`.
- `routes.py` é uma fachada compatível, não a origem principal da lógica.

## 9. Domínio `mesa`

| Item | Descrição |
| --- | --- |
| Objetivo | Manter contratos, anexos e montagem do pacote operacional da mesa. |
| Pasta principal | `web/app/domains/mesa/` |
| Arquivos centrais | `contracts.py`, `attachments.py`, `service.py` |
| Dependências | Modelos de laudo e mensagem, geração de PDF, domínios `chat` e `revisor` |
| Responsabilidades | Estruturar pacote de mesa, validar/serializar anexos e padronizar dados do canal inspetor-mesa. |
| Onde é usado | Inspetor, revisor e portal cliente. |

Leitura arquitetural:

- É um domínio de suporte técnico compartilhado por três superfícies: inspetor, revisor e cliente.
- Não aparece como portal autônomo, mas é decisivo na ligação entre campo e mesa.

## 10. Núcleo de IA e documentos

| Item | Descrição |
| --- | --- |
| Objetivo | Integrar LLM, OCR e geração/exportação de documentos. |
| Pasta principal | `web/nucleo/` |
| Arquivos centrais | `cliente_ia.py`, `gerador_laudos.py`, `template_editor_word.py`, `template_laudos.py` |
| Dependências | Google Gemini, Google Vision, PDF, DOCX, pypdf |
| Responsabilidades | Streaming de IA, OCR de imagem, saídas estruturadas, custos, preview e export de laudos/templates. |
| Onde é usado | Fluxo do inspetor, templates do revisor e exportações. |

Leitura arquitetural:

- `cliente_ia.py` é um dos módulos mais críticos para latência, custo e confiabilidade externa.
- A geração de PDF está espalhada entre fluxos operacionais e editor de template, o que sugere especialização crescente na parte documental.

## 11. Frontend web

| Item | Descrição |
| --- | --- |
| Objetivo | Entregar as interfaces web SSR e suas camadas de hidratação. |
| Pasta principal | `web/templates/` e `web/static/` |
| Arquivos centrais | `templates/index.html`, `templates/inspetor/base.html`, `templates/painel_revisor.html`, `templates/cliente_portal.html`, `static/js/chat/chat_index_page.js`, `static/js/cliente/portal.js` |
| Dependências | Jinja, JS modular sem bundler, CSS estático, service worker, SSE, WebSocket |
| Responsabilidades | Renderização inicial, boot JSON, interação, sincronização com APIs e shells por portal. |
| Onde é usado | Todos os portais web. |

Leitura arquitetural:

- O frontend web não usa bundler moderno dentro do repositório inspecionado.
- A ordem de carregamento dos scripts importa, porque os módulos compartilham objetos em `window`.
- O inspetor é a interface web mais rica e mais “SPA-like”, embora continue nascendo de SSR.

## 12. Frontend mobile

| Item | Descrição |
| --- | --- |
| Objetivo | Operar o inspetor em campo com foco em chat, mesa, offline e settings críticos. |
| Pasta principal | `android/` |
| Arquivos centrais | `App.tsx`, `src/features/InspectorMobileApp.tsx`, `src/config/api.ts`, `src/config/chatApi.ts`, `src/config/mesaApi.ts` |
| Dependências | Expo, React Native, APIs do backend web, settings locais, offline queue |
| Responsabilidades | Login mobile, bootstrap, histórico, chat, mesa, anexos, offline, atividade e configurações. |
| Onde é usado | App `Tariel Inspetor`. |

Leitura arquitetural:

- O mobile não reimplementa backend; ele consome as mesmas APIs centrais do domínio `chat`.
- `InspectorMobileApp.tsx` concentra muita coordenação de estado e é o equivalente móvel do grande controller web do inspetor.

## 13. Testes e qualidade

| Item | Descrição |
| --- | --- |
| Objetivo | Reduzir regressões em backend, portais web, realtime e app mobile. |
| Pasta principal | `web/tests/`, `android/`, `.github/workflows/` |
| Arquivos centrais | `tests/test_smoke.py`, `tests/test_regras_rotas_criticas.py`, `tests/e2e/test_portais_playwright.py`, `.github/workflows/ci.yml` |
| Dependências | pytest, Playwright, Jest, ESLint, TypeScript |
| Responsabilidades | Smoke, regras críticas, E2E, realtime, ws, typecheck e lint. |
| Onde é usado | Pipeline local e CI. |

Leitura arquitetural:

- A qualidade não é superficial: há cobertura de auth, portais, realtime, E2E web e mobile.
- O risco não é “ausência de testes”, e sim custo crescente para manter consistência em áreas muito grandes e acopladas.

## 14. Módulos com responsabilidade excessiva

Os arquivos abaixo merecem destaque por concentração de responsabilidade:

- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/mesa.py`
- `web/app/domains/admin/services.py`
- `web/app/shared/security_session_store.py`
- `web/app/domains/revisor/panel.py`
- `web/app/domains/revisor/templates_laudo_support.py`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/cliente/portal.js`
- `android/src/features/InspectorMobileApp.tsx`

Isso não significa que estejam errados por si só. Significa que são pontos com maior chance de concentrar bugs, regressões e custo de manutenção.

## Confirmado no código

- O sistema é um monólito modular multiportal, não um conjunto de microserviços.
- `chat`, `revisor` e `shared` são os módulos mais centrais do backend.
- `cliente` funciona como módulo de composição entre gestão empresarial, chat e mesa.
- O frontend web e o mobile têm superfícies próprias, mas compartilham a mesma fonte de verdade de backend.

## Inferência provável

- O domínio `cliente` é uma tentativa consciente de evitar duplicação total, mas paga isso com acoplamento entre domínios.
- O domínio `revisor` foi expandido além da fila de mesa e hoje já abriga um subsistema documental próprio.
- Os maiores ganhos futuros de modularidade tendem a vir menos da pasta `admin` e mais da separação interna de `chat`, `revisor` e dos grandes controllers de frontend.

## Dúvida aberta

- Não ficou totalmente claro se a biblioteca de templates do revisor é um produto estável de longo prazo ou uma frente ainda em consolidação. O volume de arquivos e a presença de editor rico indicam expansão, mas o código não explicita roadmap oficial.
