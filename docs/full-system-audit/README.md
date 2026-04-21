# Auditoria Completa do Sistema Tariel

Este pacote documenta o sistema inteiro a partir da leitura do repositório, com foco em arquitetura, fluxos, rotas, dependências, hotspots e riscos. O objetivo não é propor correções imediatas, mas criar um mapa confiável do que existe hoje e do que merece atenção antes de qualquer refatoração.

## Resumo executivo

O repositório é organizado como um monólito modular no workspace `web/`, com um backend FastAPI que atende múltiplos portais no mesmo processo: admin CEO, inspetor, admin-cliente e mesa/revisor. Esse backend combina SSR com Jinja2, APIs JSON, SSE e WebSocket, persistindo dados com SQLAlchemy e Alembic. O produto também possui um app mobile separado em `android/`, voltado ao inspetor, consumindo a mesma superfície de APIs do backend web.

O centro técnico do sistema está em `web/main.py`, `web/app/domains/*`, `web/app/shared/*`, `web/templates/*` e `web/static/*`. O domínio `chat` concentra boa parte da complexidade operacional: autenticação do inspetor, ciclo de vida do laudo, streaming com IA, mesa avaliadora, pendências e parte do aprendizado visual. O domínio `revisor` é o segundo núcleo mais crítico, por concentrar a fila da mesa, respostas técnicas, learnings e a biblioteca de templates de laudo.

Há bons sinais de organização: separação por domínios, camada compartilhada explícita, migrações versionadas, cobertura de testes relevante, CI para web e mobile e um backend de realtime plugável entre memória e Redis. Ao mesmo tempo, há fragilidades importantes: arquivos muito grandes, frontend web sem bundler moderno e com dependência de globais/ordem de scripts, além de módulos de backend que acumulam responsabilidade demais. Na trilha visual do inspetor, o legado antigo já foi retirado do runtime e removido fisicamente; o que resta é sobretudo documentação histórica e acoplamento de JS.

## Índice do pacote

| Arquivo | Papel no pacote |
| --- | --- |
| `README.md` | Índice, resumo executivo e forma de leitura. |
| `01_repo_overview.md` | Leitura de alto nível do repositório, áreas centrais e áreas legadas. |
| `02_directory_map.md` | Mapa das pastas principais com propósito arquitetural. |
| `03_services_and_modules.md` | Inventário dos grandes serviços, domínios e módulos. |
| `04_routes_map.md` | Mapeamento das rotas HTML, API, SSE e WebSocket por portal. |
| `05_backend_architecture.md` | Bootstrap, configuração, dados, autenticação, integrações e fluxo backend. |
| `06_frontend_architecture.md` | Templates, assets, hidratação, shell web e app mobile. |
| `07_end_to_end_flows.md` | Fluxos ponta a ponta do produto. |
| `08_performance_hotspots.md` | Hipóteses e evidências de gargalos. |
| `09_tech_debt_and_risks.md` | Leitura franca de dívida técnica, legado e risco. |
| `10_improvement_priorities.md` | Priorização de melhorias por impacto x risco. |
| `11_file_index.md` | Índice curado dos arquivos mais importantes. |
| `12_FOR_CHATGPT.md` | Briefing consolidado para outra IA. |
| `13_OPEN_QUESTIONS.md` | Lacunas, inferências e dúvidas abertas. |
| `14_UPLOAD_ORDER.md` | Ordem ideal para enviar os arquivos a outra IA. |

## Como ler este material

1. Comece por `01_repo_overview.md` para entender a topologia geral.
2. Em seguida leia `03_services_and_modules.md` e `04_routes_map.md` para localizar responsabilidades.
3. Use `05_backend_architecture.md` e `06_frontend_architecture.md` para entender os pontos de entrada e a montagem do sistema.
4. Depois leia `07_end_to_end_flows.md`, `08_performance_hotspots.md` e `09_tech_debt_and_risks.md` para formar opinião técnica.
5. Se o objetivo for repassar contexto a outra IA, use `12_FOR_CHATGPT.md` e `14_UPLOAD_ORDER.md`.

## Arquivos mais críticos do sistema

### Backend

- `web/main.py`
- `web/app/shared/database.py`
- `web/app/shared/security.py`
- `web/app/domains/chat/chat_stream_routes.py`
- `web/app/domains/chat/laudo.py`
- `web/app/domains/revisor/mesa_api.py`
- `web/app/domains/revisor/panel.py`
- `web/app/domains/admin/services.py`
- `web/nucleo/cliente_ia.py`

### Frontend web

- `web/templates/index.html`
- `web/templates/inspetor/base.html`
- `web/templates/painel_revisor.html`
- `web/templates/cliente_portal.html`
- `web/static/js/chat/chat_index_page.js`
- `web/static/js/cliente/portal.js`
- `web/static/js/shared/api.js`
- `web/static/js/shared/chat-network.js`
- `web/static/css/shared/official_visual_system.css`
- `web/static/css/inspetor/workspace_history.css`
- `web/static/css/revisor/painel_revisor.css`

### Mobile

- `android/App.tsx`
- `android/src/features/InspectorMobileApp.tsx`
- `android/src/config/api.ts`
- `android/src/config/chatApi.ts`
- `android/src/config/mesaApi.ts`

## Confirmado no código

- O backend principal em produção vive no workspace `web/`, com deploy descrito em `render.yaml`.
- O sistema web é um monólito modular FastAPI com domínios em `web/app/domains/`.
- O app Android em `android/` é um produto complementar, não um frontend web secundário.
- O repositório já contém documentação densa sobre o inspetor, mas não havia um pacote equivalente cobrindo o sistema inteiro.

## Inferência provável

- O domínio do inspetor recebeu mais iterações e patches do que os demais, o que explica a densidade de documentação pré-existente nessa área.
- A complexidade operacional atual do produto gira principalmente em torno do ciclo de vida do laudo e da mesa avaliadora, não do painel administrativo.

## Dúvida aberta

- Não há, no código inspecionado, evidência suficiente para concluir qual área do produto sofre mais volume real de tráfego em produção. O pacote trata isso como hipótese e não como fato.
