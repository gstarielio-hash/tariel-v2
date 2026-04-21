# 01. Visão Geral do Repositório

Este documento descreve o repositório como sistema, não como coleção de arquivos. A leitura abaixo busca responder quais são os workspaces centrais, o que é backend, o que é frontend, o que é infraestrutura local e o que parece legado.

## Topologia da raiz

| Caminho | Papel arquitetural | Observações |
| --- | --- | --- |
| `web/` | Produto web principal e backend em produção | Workspace mais crítico do repositório. |
| `android/` | App mobile do inspetor | React Native + Expo, consumindo a mesma API do backend. |
| `docs/` | Documentação de produto, redesign e handoffs | Antes desta auditoria, já havia bastante material focado no inspetor. |
| `scripts/` | Automação local e runners de smoke mobile | Especialmente scripts para Maestro e API local mobile. |
| `.github/workflows/` | CI do repositório | Pipeline separado para web e mobile. |
| `render.yaml` | Blueprint de deploy da stack web | Define serviço web, Postgres e Redis. |
| `Makefile` | Orquestração local de comandos comuns | Agrega `web-ci`, `mobile-ci` e `ci`. |

## Leitura arquitetural de alto nível

O repositório tem dois produtos executáveis relevantes:

1. Um sistema web completo em `web/`, que acumula:
   - backend FastAPI;
   - templates SSR com Jinja2;
   - frontend web em JavaScript e CSS estáticos;
   - migrações Alembic;
   - testes backend, integração e E2E;
   - documentação técnica do workspace.
2. Um app mobile em `android/`, voltado ao inspetor, conectado ao mesmo backend.

Na prática, `web/` é o centro do sistema. O `android/` é importante, mas dependente da superfície HTTP definida pelo backend web.

## O que existe dentro de `web/`

Pelos arquivos e documentos do próprio projeto, o workspace `web/` é um monólito modular com os seguintes blocos:

- `main.py`: entrypoint FastAPI.
- `app/core/`: configuração, runtime HTTP, logging, OpenAPI e rotas operacionais.
- `app/domains/`: domínios de negócio e portais.
- `app/shared/`: dados, segurança, sessão, contratos e utilitários centrais.
- `nucleo/`: integrações pesadas e utilitários de domínio, incluindo IA e geração de PDF.
- `templates/`: SSR e shells dos portais.
- `static/`: JS, CSS, imagens e service worker.
- `tests/`: suíte crítica, realtime, integração, E2E e carga.
- `alembic/`: migrações versionadas.

## O que existe dentro de `android/`

O workspace `android/` é um app React Native + Expo com:

- `App.tsx` como ponto de entrada.
- `src/config/` concentrando clientes de API.
- `src/features/` concentrando o shell do app, chat, mesa, histórico, offline, segurança e configurações.
- `src/settings/` concentrando persistência e schema de settings locais.
- `maestro/` com smoke tests mobile reais.
- `eas.json` para build e submit.

## Partes centrais do sistema

As áreas que mais concentram responsabilidade de produto são:

- `web/main.py`
- `web/app/domains/chat/`
- `web/app/domains/revisor/`
- `web/app/domains/cliente/`
- `web/app/shared/`
- `web/templates/`
- `web/static/js/`
- `web/nucleo/`
- `android/src/features/InspectorMobileApp.tsx`

Essas áreas formam a espinha dorsal do produto: bootstrap, autenticação, laudo, chat, mesa, portal cliente, portal revisor, IA e shells de frontend.

## Partes claramente backend

- `web/main.py`
- `web/app/core/`
- `web/app/domains/admin/`
- `web/app/domains/chat/`
- `web/app/domains/cliente/`
- `web/app/domains/mesa/`
- `web/app/domains/revisor/`
- `web/app/shared/`
- `web/nucleo/`
- `web/alembic/`

## Partes claramente frontend

### Web

- `web/templates/`
- `web/static/js/`
- `web/static/css/`
- `web/static/img/`

### Mobile

- `android/App.tsx`
- `android/src/features/`
- `android/src/components/`
- `android/src/theme/`

## Partes de infraestrutura e configuração

- `render.yaml`
- `.github/workflows/ci.yml`
- `.github/workflows/e2e-local-stress.yml`
- `web/pyproject.toml`
- `web/requirements.txt`
- `web/alembic.ini`
- `web/.env.example`
- `android/package.json`
- `android/package-lock.json`
- `android/.env.example`
- `android/eas.json`
- `Makefile`

Não encontrei, no repositório inspecionado, `Dockerfile`, `docker-compose`, `nginx`, `Caddyfile`, unit `systemd` ou configuração `apache`. Isso sugere que o deploy codificado no repositório depende principalmente de `render.yaml`, e não de uma stack containerizada versionada aqui.

## Domínios funcionais do sistema

| Domínio | Papel |
| --- | --- |
| `admin` | Portal da diretoria/CEO, gestão SaaS, clientes e planos. |
| `chat` | Portal do inspetor, autenticação do inspetor, laudo, chat IA, mesa e pendências. |
| `cliente` | Portal do admin-cliente, gestão da empresa, chat company-scoped e mesa company-scoped. |
| `mesa` | Contratos e serviços do pacote da mesa avaliadora. |
| `revisor` | Painel da mesa, avaliação, whispers, learnings e templates de laudo. |
| `shared` | Base de dados, autenticação, RBAC, sessão, contratos, tenancy e utilitários globais. |
| `nucleo` | Integrações de IA, OCR, geração de PDF e utilidades mais pesadas. |

## Indícios de legado

Há duas famílias diferentes de legado visíveis.

### Wrappers legados na raiz de `web/`

Arquivos como:

- `web/banco_dados.py`
- `web/seguranca.py`
- `web/rotas_admin.py`
- `web/rotas_inspetor.py`
- `web/servicos_saas.py`
- `web/criar_admin.py`
- `web/resetar_senha.py`

apontam para uma camada de compatibilidade histórica. A própria suíte `web/tests/test_legacy_wrappers.py` confirma que esses wrappers hoje ficam bloqueados por padrão e só reativam sob `TARIEL_ALLOW_LEGACY_IMPORTS=1`.

### Fachadas compatíveis dentro dos domínios

Arquivos como:

- `web/app/domains/chat/routes.py`
- `web/app/domains/chat/auth.py`
- `web/app/domains/chat/chat.py`
- `web/app/domains/cliente/dashboard.py`
- `web/app/domains/revisor/routes.py`

existem mais como superfície de compatibilidade e agregação do que como fonte primária de lógica nova.

## Documentação já existente antes desta auditoria

O repositório já possuía documentação técnica relevante, sobretudo no workspace `web/`:

- `web/README.md`
- `web/PROJECT_MAP.md`
- `web/app/ARCHITECTURE.md`
- `web/app/domains/chat/ARCHITECTURE.md`
- `web/docs/frontend_mapa.md`
- `web/docs/mesa_avaliadora.md`
- `web/docs/inspector-understanding-packet/`
- `web/docs/inspector-performance-audit.md`

A leitura desses documentos mostra que o inspetor e o frontend do inspetor já vinham sendo auditados com profundidade. A lacuna maior era um mapa equivalente cobrindo o sistema inteiro, inclusive admin, cliente, revisor, infra, mobile e conexões entre eles.

## Pontos de entrada do sistema

### Entradas web

- `web/main.py`
- `web/app/domains/router_registry.py`
- `web/templates/index.html`
- `web/templates/painel_revisor.html`
- `web/templates/cliente_portal.html`
- `web/templates/dashboard.html`

### Entradas mobile

- `android/App.tsx`
- `android/src/features/InspectorMobileApp.tsx`
- `android/src/config/api.ts`

### Entradas operacionais

- `render.yaml`
- `.github/workflows/ci.yml`
- `Makefile`

## Confirmado no código

- O deploy versionado do backend web aponta para `web/` como raiz de produção.
- O backend registra quatro grandes roteadores: admin, cliente, inspetor e revisor.
- O sistema expõe múltiplos portais a partir da mesma app FastAPI.
- O app mobile é separado do web, mas consome a API do mesmo backend.
- Há documentação prévia extensa sobre o inspetor e documentação mais enxuta sobre os demais domínios.

## Inferência provável

- O projeto evoluiu primeiro como produto web multiportal e depois ganhou um app mobile acoplado à mesma API.
- O repositório passou por uma consolidação arquitetural recente, porque o código combina módulos novos por domínio com wrappers de compatibilidade ainda presentes.
- O maior custo cognitivo para manutenção hoje não é “entender o que é backend ou frontend”, mas “entender como os portais compartilham regras e dados sem se atropelar”.

## Dúvida aberta

- Não ficou 100% claro pelo código se existe alguma topologia de infraestrutura complementar fora do repositório, como proxy externo, CDN própria ou workers operacionais adicionais. O repositório só evidencia `Render + Postgres + Redis`.
