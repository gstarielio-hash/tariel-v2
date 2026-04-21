# 02. Mapa de Diretórios

Este mapa prioriza pastas com papel arquitetural real. O objetivo não é listar tudo, e sim destacar onde cada responsabilidade do sistema mora.

## Raiz do repositório

| Caminho | Propósito | Papel no sistema |
| --- | --- | --- |
| `web/` | Backend web, frontend web, templates, assets, testes e migrações | Núcleo do produto em produção. |
| `android/` | Aplicativo mobile do inspetor | Cliente nativo conectado à mesma API. |
| `docs/` | Documentação transversal do projeto | Planejamento, redesign, handoffs e esta auditoria. |
| `scripts/` | Automação local | Especialmente suporte ao mobile e suites smoke. |
| `.github/workflows/` | CI | Garante qualidade de web e mobile. |

## Workspace `web/`

| Caminho | Propósito | Observação arquitetural |
| --- | --- | --- |
| `web/main.py` | Cria a app FastAPI, monta middlewares e inclui roteadores | Ponto de entrada principal do backend. |
| `web/app/` | Código backend organizado por domínio | Centro da lógica de aplicação. |
| `web/app/core/` | Configuração HTTP, headers, logging, OpenAPI, readiness | Infraestrutura de runtime. |
| `web/app/domains/` | Domínios de negócio | Núcleo do monólito modular. |
| `web/app/shared/` | Banco, modelos, segurança, tenancy e utilitários globais | Camada transversal mais acoplada. |
| `web/nucleo/` | Integrações pesadas e utilitários centrais | IA, OCR e geração de PDF. |
| `web/templates/` | Templates SSR e shells dos portais | Camada HTML do frontend web. |
| `web/static/` | JS, CSS, imagens e service worker | Camada de assets estáticos do web. |
| `web/tests/` | Testes unitários, integração, realtime, carga e E2E | Cobertura relevante do sistema web. |
| `web/alembic/` | Migrações versionadas | Evolução do schema de banco. |
| `web/docs/` | Documentação técnica do workspace web | Bastante material focado no inspetor. |
| `web/artifacts/` | Relatórios gerados de inspeção visual | Evidência de automação auxiliar, não núcleo funcional. |

## `web/app/core/`

| Caminho | Propósito | Observação |
| --- | --- | --- |
| `web/app/core/settings.py` | Carregamento e validação de configuração | Fonte central de env vars. |
| `web/app/core/http_runtime_support.py` | Middlewares, CSP, headers, correlação e suporte HTTP | Camada crítica de segurança e runtime. |
| `web/app/core/http_setup_support.py` | Exceções, OpenAPI custom e rotas operacionais | Também concentra `/health`, `/ready` e service worker. |
| `web/app/core/logging_support.py` | Logging JSON em produção e texto em dev | Observabilidade base. |

## `web/app/domains/`

| Caminho | Propósito | Observação |
| --- | --- | --- |
| `web/app/domains/admin/` | Portal administrativo da diretoria/CEO | Gestão SaaS, clientes e planos. |
| `web/app/domains/chat/` | Portal do inspetor e núcleo operacional do laudo | Domínio mais denso do produto. |
| `web/app/domains/cliente/` | Portal admin-cliente | Reaproveita serviços de outros domínios via bridge. |
| `web/app/domains/mesa/` | Contratos e serviço do pacote da mesa | Domínio de suporte, não portal autônomo. |
| `web/app/domains/revisor/` | Portal da mesa/revisor | Fila, avaliação, whispers, learnings e templates. |
| `web/app/domains/router_registry.py` | Registro central dos roteadores | Ponto único de exposição dos portais. |

## `web/app/shared/`

| Caminho | Propósito | Observação |
| --- | --- | --- |
| `web/app/shared/database.py` | Facade de modelos, sessão e contrato transacional | Arquivo mais importado internamente. |
| `web/app/shared/db/` | Modelos, runtime e bootstrap do banco | Camada real de persistência. |
| `web/app/shared/security.py` | Hash de senha, RBAC, autenticação HTML e bearer | Segunda maior dependência transversal. |
| `web/app/shared/security_session_store.py` | Sessões ativas em memória e banco | Mistura cache, TTL, persistência e política de sessão. |
| `web/app/shared/security_portal_state.py` | Isolamento por portal | Importante para evitar vazamento de sessão entre áreas. |
| `web/app/shared/tenant_access.py` | Acesso por empresa e escopo | Crítico em multiempresa. |

## `web/nucleo/`

| Caminho | Propósito | Observação |
| --- | --- | --- |
| `web/nucleo/cliente_ia.py` | Integração com Google Gemini e Google Vision | Ponto mais sensível para latência externa. |
| `web/nucleo/gerador_laudos.py` | Geração de PDFs operacionais | Backend pesado para exportação. |
| `web/nucleo/template_editor_word.py` | Editor rico e preview/export de templates | Subsystem especializado de documentos. |
| `web/nucleo/inspetor/` | Utilidades específicas do chat do inspetor | Comandos, confiança da IA e referências. |

## `web/templates/`

| Caminho | Propósito | Observação |
| --- | --- | --- |
| `web/templates/index.html` | Página principal do inspetor | Shell SSR com hidratação intensa. |
| `web/templates/inspetor/` | Partials e estrutura interna do portal do inspetor | Reúne `_portal_main`, modais e regiões da workspace. |
| `web/templates/painel_revisor.html` | Página principal da mesa/revisor | SSR forte com JS específico. |
| `web/templates/cliente_portal.html` | Página principal do admin-cliente | Portal unificado com abas Admin, Chat e Mesa. |
| `web/templates/dashboard.html` | Painel da diretoria | Usa Chart.js via CDN. |
| `web/templates/login*.html` | Logins dos portais | Há login dedicado por portal. |
| `web/templates/revisor_templates_*.html` | Biblioteca/editor de templates | Frontend específico do revisor. |
| `web/templates/componentes/` | Partials compartilhados antigos | Indício de acúmulo de UI histórica. |

## `web/static/`

| Caminho | Propósito | Observação |
| --- | --- | --- |
| `web/static/js/shared/` | Utilitários compartilhados, API client, render, service worker | Base comum do runtime web. |
| `web/static/js/chat/` | Inspetor e painéis do chat/laudo | Contém o maior arquivo JS do projeto web. |
| `web/static/js/inspetor/` | Modais, pendências, mesa widget, SSE | Suporte específico à shell do inspetor. |
| `web/static/js/revisor/` | JS do painel e dos templates do revisor | Menor que o inspetor, mas ainda denso. |
| `web/static/js/cliente/` | Portal do admin-cliente | `portal.js` concentra quase toda a UI dessa área. |
| `web/static/js/admin/` | Dashboard administrativo | Superfície menor e mais simples. |
| `web/static/css/shared/` | Base visual compartilhada | Global, layout e shell técnico. |
| `web/static/css/chat/` | Estilos do chat/inspetor | Arquivos grandes e muito centrais. |
| `web/static/css/inspetor/` | Tokens e shell do inspetor | Mistura ativos novos e CSS de migração. |
| `web/static/css/revisor/` | Estilos do portal revisor e templates | Superfície própria do domínio revisor. |
| `web/static/css/cliente/` | Estilos do portal admin-cliente | Portal isolado. |
| `web/static/css/admin/` | Estilos do admin CEO | Camada específica do dashboard. |

## `web/tests/`

| Caminho | Propósito | Observação |
| --- | --- | --- |
| `web/tests/test_smoke.py` | Contratos e smoke geral | Bom ponto de entrada para garantias mínimas. |
| `web/tests/test_regras_rotas_criticas.py` | Regras e rotas sensíveis | Arquivo enorme e muito importante. |
| `web/tests/e2e/` | Playwright dos portais | Exercita fluxo cruzado entre áreas. |
| `web/tests/load/` | Carga com Locust | Há atenção explícita a carga, ainda que leve. |
| `web/tests/test_revisor_realtime.py` | Realtime Redis/memory | Confirma o backend distribuído do revisor. |
| `web/tests/test_portais_acesso_critico.py` | Isolamento de portais | Cobertura importante de auth/sessão. |

## Workspace `android/`

| Caminho | Propósito | Observação |
| --- | --- | --- |
| `android/App.tsx` | Entrada do app | Injeta `SettingsStoreProvider` e `InspectorMobileApp`. |
| `android/src/config/` | APIs, observabilidade e crash reporting | Ponte entre mobile e backend web. |
| `android/src/features/` | Shell do app e features por domínio | Centro do produto mobile. |
| `android/src/features/InspectorMobileApp.tsx` | Shell principal do inspetor mobile | Arquivo muito grande e crítico. |
| `android/src/settings/` | Store, schema, repository e migrations locais | Persistência local do app. |
| `android/src/theme/` | Sistema visual do app | Base visual mobile. |
| `android/maestro/` | Automação de smoke em device | Qualidade móvel de ponta a ponta. |
| `android/eas.json` | Perfis de build e submit | Pipeline de distribuição mobile. |

## `scripts/`

| Caminho | Propósito | Observação |
| --- | --- | --- |
| `scripts/start_local_mobile_api.sh` | Sobe a API local para o mobile | Utilitário de desenvolvimento. |
| `scripts/run_mobile_maestro_smoke.cjs` | Runner de smoke do Maestro | Integra web local com device. |
| `scripts/run_mobile_maestro_suite.cjs` | Runner da suíte mobile | Orquestra vários fluxos. |

## Infraestrutura ausente no repositório

Não encontrei diretórios ou arquivos de:

- Docker
- Compose
- Nginx
- Caddy
- Apache
- systemd
- fila dedicada com Celery/RQ/Dramatiq/Huey

Isso não prova que esses componentes não existam no ambiente real, mas prova que eles não são parte explícita do código versionado inspecionado.

## Confirmado no código

- A maior concentração de lógica está em `web/app/domains/`, `web/app/shared/`, `web/templates/` e `web/static/`.
- O backend e o frontend web convivem no mesmo workspace e na mesma base de deploy.
- O mobile é um workspace separado e consome a API do `web/`.
- Há infraestrutura de CI e migração versionada suficientemente madura para sustentar evolução contínua.

## Inferência provável

- O projeto está organizado para facilitar entrega integrada do produto, não para isolamento rígido entre backend e frontend.
- O maior custo de manutenção tende a aparecer onde diretórios “shared” e “domains” se cruzam demais, especialmente em `chat`, `cliente` e `revisor`.

## Dúvida aberta

- Não ficou claro se existe um repositório irmão de infra/ops contendo recursos não versionados aqui. A auditoria só consegue afirmar o que está neste repositório.
