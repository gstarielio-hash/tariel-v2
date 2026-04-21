# Tariel.ia

Aplicação SaaS de inspeções industriais com backend FastAPI, SQLAlchemy, templates Jinja2 e assets estáticos.

## Workspace Astro experimental

Existe um workspace isolado em `frontend-astro/` para evolucao de novas superficies com:

- Astro
- Node adapter oficial do Astro
- Tailwind CSS v4
- shadcn/ui
- React 19
- Lucide
- Prisma ORM
- Vite

Ele agora serve como alvo de migracao do frontend atual. A ideia e substituir gradualmente a camada visual existente por Astro + React e abrir a camada Node/TypeScript com Prisma falando com o mesmo PostgreSQL.

Comandos:

```bash
cd frontend-astro
./bin/npm22 install
./bin/npm22 run prisma:pull
./bin/npm22 run dev
```

Observacao operacional: em `2026-04-20`, o Astro mais recente exige Node `>=22.12.0`. Como este ambiente local usa Node `20.20.2`, o workspace inclui o wrapper `./bin/npm22` para rodar o stack atual sem trocar o Node global.

## Roadmap do produto

Backlog mestre da etapa antiga (priorizado e com status):

- `ROADMAP_BACKLOG.md`

## Stack detectada

- Python 3.14
- FastAPI + Uvicorn
- SQLAlchemy + Alembic (PostgreSQL local por padrão; SQLite isolado só para testes e previews)
- Redis local por padrão para realtime distribuído da Mesa
- Integrações opcionais: Google Gemini e Google Vision
- Qualidade: Ruff, Mypy, Pytest

## Estrutura por domínios

- `app/domains/chat`: portal do inspetor, chat IA e fluxo de laudos
- `app/domains/mesa`: contratos e serviços da mesa avaliadora
- `app/domains/admin`: painel administrativo e serviços SaaS
- `app/domains/revisor`: painel da engenharia/revisão
- `app/shared`: banco de dados, segurança e utilitários compartilhados
- `static/js/chat`, `static/js/admin`, `static/js/revisor`, `static/js/shared`: organização de scripts por domínio
- `static/css/revisor`: estilos dedicados da biblioteca de templates da mesa avaliadora

Observação: os wrappers legados de módulo na raiz estão desabilitados por padrão. Use apenas os módulos em `app/` (`app/domains/*` e `app/shared/*`). Se precisar de compatibilidade temporária durante migração controlada, habilite `TARIEL_ALLOW_LEGACY_IMPORTS=1` apenas no processo afetado.

## Setup local (do zero)

1. Criar e ativar ambiente virtual:

```bash
python3 -m venv .venv-linux
source .venv-linux/bin/activate
```

2. Instalar dependências:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Configurar variáveis de ambiente:

```bash
cp .env.example .env
```

Segurança: nunca versione `.env` nem credenciais JSON (`visao_wf.local.json`/equivalentes).
O `.env.example` já vem apontando para a stack local madura: `postgresql:///tariel_dev` e `redis://127.0.0.1:6379/0`.

4. Ajustar no `.env` principalmente:

- `AMBIENTE` (obrigatório: `dev`, `development`, `local`, `producao`, `production` ou `prod`)
- `DATABASE_URL` (padrão local: `postgresql:///tariel_dev`; crie o banco com `createdb tariel_dev` se ainda não existir)
- `REDIS_URL` (padrão local: `redis://127.0.0.1:6379/0`)
- `REVISOR_REALTIME_BACKEND` (`redis` no setup local maduro; use `memory` só em fallback pontual)
- `CHAVE_API_GEMINI` (necessária para recursos de IA)
- `GOOGLE_APPLICATION_CREDENTIALS` (arquivo de credenciais da Vision API, se usar OCR)
- `CHAVE_SECRETA_APP` (obrigatória em produção)
- `SEED_DEV_BOOTSTRAP` (`0` por padrão; use `1` apenas quando quiser criar usuários seed em dev)

5. Bootstrap de seed dev (opcional e explícito):

```bash
# 1) Habilite temporariamente no .env
SEED_DEV_BOOTSTRAP=1

# 2) Suba a aplicação para executar o bootstrap
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 3) Volte para 0 após criar os dados de dev
SEED_DEV_BOOTSTRAP=0
```

## Operação administrativa

Scripts oficiais de operação ficam em `scripts/`:

```bash
python scripts/criar_admin.py --help
python scripts/resetar_senha.py --help
python scripts/listar_modelos_gemini.py
```

Os wrappers de CLI da raiz (`criar_admin.py`, `resetar_senha.py`, `senhanova.py`, `modelo.py`) foram mantidos apenas para compatibilidade temporária e exibem aviso de descontinuação. Os wrappers legados de módulo (`banco_dados.py`, `seguranca.py`, `rotas_admin.py`, `rotas_inspetor.py`, `servicos_saas.py`) ficam bloqueados por padrão.

## Realtime distribuído da mesa

No setup local maduro, o realtime do portal do revisor usa Redis por padrão.
O backend em memória continua disponível como fallback em desenvolvimento pontual e instância única.

Para preparar múltiplos workers/instâncias, habilite o backend distribuído:

```bash
REDIS_URL=redis://localhost:6379/0
REVISOR_REALTIME_BACKEND=redis
REVISOR_REALTIME_CHANNEL_PREFIX=tariel:revisor
```

Observações:

- `REVISOR_REALTIME_BACKEND=redis` é o padrão recomendado e o valor padrão do `.env.example`.
- `REVISOR_REALTIME_BACKEND=memory` continua disponível como fallback local.
- `REVISOR_REALTIME_BACKEND=redis` falha rápido no startup se `REDIS_URL` não estiver configurado.
- `/ready` agora expõe `revisor_realtime_backend` e `revisor_realtime_distributed` para facilitar operação.

## Deploy no Render

O blueprint de produção fica na raiz do repositório em `../render.yaml`.
Ele usa `rootDir: web`, então o serviço do Render executa build, migrations e `uvicorn`
diretamente a partir desta pasta sem precisar de wrappers com `cd`.
O mesmo blueprint também provisiona o Key Value `tarie-ia-realtime` e injeta `REDIS_URL`
no serviço web para o realtime distribuído da mesa.

## Pipeline de validação

Execução completa recomendada (varredura recursiva com evidência por subpasta):

```bash
./validar_pipeline.sh
```

Esse script valida, nesta ordem:

- `ruff format`
- `ruff check`
- `scripts/check_chat_architecture.py` (guarda de arquitetura do domínio chat)
- `mypy`
- `pytest`
- `compileall` recursivo
- `node --check` em todos os `.js`
- parse de templates Jinja2 (`templates/**/*.html`)
- parse de arquivos JSON

Se quiser executar manualmente a parte Python:

```bash
python -m ruff format .
python -m ruff check .
python scripts/check_chat_architecture.py
python -m mypy
python -m pytest -q
python -m compileall -q .
```

## Arquitetura visual do inspetor

O portal do inspetor agora usa uma base visual mais previsível:

- `design_tokens/inspetor.tokens.json`: fonte canônica de tokens.
- `scripts/build_design_tokens.py`: gera o CSS versionado de tokens.
- `static/css/inspetor/tokens.generated.css`: saída gerada; não editar manualmente.
- `templates/inspetor/base.html`: ordem explícita de `@layer` para reduzir guerra de override.

Regenerar tokens após mexer na fonte:

```bash
python scripts/build_design_tokens.py
```

### GitHub Actions

- `ci.yml`: lint + guarda de arquitetura + `mypy` + suíte crítica de testes + job com Postgres/Redis.
- `e2e-local-stress.yml` (manual): stress E2E intenso local (sequencial + paralelo) com Playwright.

## Testes E2E (Playwright)

Os testes E2E estão em `tests/e2e` e sobem a aplicação automaticamente em uma porta local com:

- banco SQLite temporário (não usa seu banco real),
- seed DEV habilitado (`SEED_DEV_BOOTSTRAP=1`) para usuários de teste.

Usuários seed usados nos E2E:

- `admin@tariel.ia` / `Dev@123456`
- `admin-cliente@tariel.ia` / `Dev@123456`
- `inspetor@tariel.ia` / `Dev@123456`
- `revisor@tariel.ia` / `Dev@123456`

Executar:

```bash
RUN_E2E=1 python -m pytest tests/e2e -q --browser chromium
```

No ambiente local, os E2E agora abrem por padrao em modo visual quando houver janela disponivel:

- Chromium visivel (`headless = false`);
- janela maximizada;
- `slowmo` padrao de `350ms`;
- overlay em tela com o nome do teste e a ultima acao disparada.

Controles uteis:

```bash
E2E_VISUAL=0 RUN_E2E=1 python -m pytest tests/e2e -q --browser chromium
E2E_SLOWMO_MS=150 ./tests/e2e/run_playwright.sh
```

Com trace/vídeo/screenshot em falha:

```bash
./tests/e2e/run_playwright.sh
```

Captura visual dedicada do inspetor, salvando PNGs em `.test-artifacts/visual/`:

```bash
RUN_E2E=1 E2E_VISUAL=0 python -m pytest tests/e2e/test_inspetor_visual_playwright.py -q --browser chromium -s
```

Para assistir o fluxo em tela grande, com passos lentos e pausas de revisão:

```bash
RUN_E2E=1 \
E2E_VISUAL=1 \
E2E_SLOWMO_MS=900 \
E2E_VISUAL_STEP_PAUSE_MS=3200 \
E2E_VISUAL_FINAL_PAUSE_MS=9000 \
python -m pytest tests/e2e/test_inspetor_visual_playwright.py -q --browser chromium -s
```

Por padrão os E2E ficam desativados (skip) quando `RUN_E2E` não é `1`.

## Bancada avançada de testes

Ferramentas adicionais instaladas na `.venv-linux` (ou `.venv`, se você preferir um único ambiente compartilhado):

- `pytest-xdist`: execução paralela
- `pytest-cov`: cobertura
- `pytest-html` + `allure-pytest`: relatórios
- `hypothesis` + `schemathesis`: propriedade e schema/API fuzzing
- `locust`: carga
- `pytest-timeout` + `pytest-randomly`: robustez da suíte
- `Faker` + `factory-boy`: dados de teste

Scripts prontos:

```bash
# pytest em paralelo (mantém ordem estável por padrão)
./scripts/run_pytest_parallel.sh tests

# cobertura HTML/XML
./scripts/run_pytest_coverage.sh tests

# relatório HTML + JUnit + Allure results
./scripts/run_pytest_report.sh tests

# schema/property-based contra FastAPI local temporário
./scripts/run_schemathesis.sh --portal inspetor
./scripts/run_schemathesis.sh --portal revisor
./scripts/run_schemathesis.sh --portal admin

# carga básica com login seed e relatório HTML/CSV
./scripts/run_locust.sh --users 8 --spawn-rate 2 --run-time 1m
```

Saídas geradas:

- cobertura: `.test-artifacts/coverage`
- relatórios pytest: `.test-artifacts/reports`
- schemathesis: `.test-artifacts/schemathesis`
- locust: `.test-artifacts/locust`

Observação: `pytest-randomly` está instalado, mas os scripts de execução contínua desabilitam a randomização por padrão para evitar flake desnecessário no dia a dia. Se quiser forçar ordem aleatória, use `--random-order` nos scripts de pytest.

## Migrações de banco (Alembic)

Comandos principais:

```bash
# aplicar migrações até o head
python -m alembic upgrade head

# criar nova revisão autogerada
python -m alembic revision --autogenerate -m "descricao_da_mudanca"
```

## Start

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Também disponível em:

```bash
./iniciar_sistema.sh
```

## Preview online (URL pública temporária)

Para testar no navegador fora do `localhost` (celular, cliente, time):

```bash
./scripts/start_online_preview.sh
```

O script:

- sobe a app local na porta `8000`;
- abre um túnel Cloudflare (`trycloudflare.com`);
- imprime a URL pública no terminal;
- opcionalmente já abre o navegador.

Por padrão, ele usa um banco SQLite isolado em `.tmp_online/preview_online.db` (não mexe no banco principal).
Se quiser forçar o banco do projeto:

```bash
./scripts/start_online_preview.sh --use-project-database
```

Para encerrar tudo:

```bash
./scripts/stop_online_preview.sh
```
`run_schemathesis.sh` carrega automaticamente [scripts/schemathesis_hooks.py](./scripts/schemathesis_hooks.py) para desserializar respostas binárias (`PDF`, imagens e `octet-stream`) e evitar warnings desnecessários no contrato.

Observação: os wrappers PowerShell e `.bat` continuam disponíveis para quem ainda roda o workspace no Windows.

## Deploy inicial no Render

O repositório já possui um Blueprint em `render.yaml` para um primeiro deploy com:

- `Web Service` Python `free`
- `Render Postgres` `free`
- uploads em `local_fs` dentro de `static/uploads` no container

Passo a passo resumido:

1. No Render, escolha `New +` -> `Blueprint`.
2. Conecte o repositório GitHub.
3. Confirme a leitura do `render.yaml`.
4. Preencha os segredos pendentes:
   - `CHAVE_SECRETA_APP`
   - `CHAVE_API_GEMINI` (se usar IA)
   - `GOOGLE_APPLICATION_CREDENTIALS` (se usar OCR)
   - `APP_HOST_PUBLICO` / `ALLOWED_HOSTS` se quiser fixar domínio próprio desde o início
5. Aguarde a criação do Postgres e do Web Service.
6. Teste a aplicação na URL `onrender.com`.

Observações:

- O app agora aceita `PASTA_UPLOADS_PERFIS` e `PASTA_ANEXOS_MESA`, o que permite explicitar o diretório de uploads usado no deploy.
- O app também aceita `RENDER_EXTERNAL_HOSTNAME` como fallback para `APP_HOST_PUBLICO`, facilitando o primeiro deploy sem domínio customizado.
