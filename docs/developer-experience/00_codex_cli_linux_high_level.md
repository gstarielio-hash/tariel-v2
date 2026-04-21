# DevKit Codex CLI Linux - Alto Nível

## Objetivo

Estabelecer uma camada de operação de alto nível para o repositório atual sem reescrever o produto.

O DevKit foi desenhado para uso diário com Codex CLI no Linux cobrindo:

- backend Python em `web/`
- Mesa oficial no `web/` via SSR
- stack mobile Android em `android/`
- checks rápidos por área
- status centralizado
- coordenação de workspace com `tmux` quando disponível

## Diagnóstico do estado atual

Antes deste DevKit, o repositório já tinha peças funcionais, mas espalhadas:

- backend web roda por `uvicorn` a partir de `web/main.py`
- a Mesa oficial já existia no SSR do backend, mas sem uma camada operacional centralizada no DevKit
- Android já tinha scripts úteis para Expo, build preview e Maestro
- checks existiam, mas divididos entre `Makefile`, `package.json`, `README` e scripts isolados
- não havia uma camada única para abrir workspace, checar saúde e navegar backend/web/mobile sem trocar de contexto mental o tempo todo

## Kit oficial escolhido

### Obrigatório no dia a dia

- `bash`
- `git`
- `python3` com ambiente compatível com `web/`
- `node` + `npm`
- backend FastAPI/Uvicorn atual
- `adb` para fluxo Android

### Oficial e já integrado

- `ruff` para lint Python
- `maestro` para automação Android
- `npx eas` ou binário local do `eas` para builds móveis

### Oficial, mas opcional por máquina

- `tmux` para workspace multiplexado de alto nível
- `direnv` para auto-load de ambiente
- `uv` como evolução progressiva do setup Python, sem migração forçada do repo
- `docker compose` como opcional para serviços auxiliares, não como pré-requisito

## Decisão pragmática por stack

### Python / backend

- o caminho oficial continua compatível com o setup atual de `venv` + `pip`
- `uv` fica tratado como opcional e progressivo
- `ruff` segue recomendado porque já existe no ambiente e no `web/README.md`

### Mesa SSR

- a superfície oficial da Mesa permanece em `web/`
- o DevKit trata a Mesa como parte do backend SSR, não como app paralelo
- os checks da Mesa usam `pytest` e Playwright do workspace `web/`
- a ergonomia local passa a ser a do próprio backend, sem runtime duplicado

### Android

- o eixo oficial continua sendo Expo + React Native + `adb`
- Android Emulator no Linux passa a ser lane oficial do DevKit para uso sem device físico
- `maestro` continua o runner automatizado
- `eas` é suportado via binário local ou `npx`

## Scripts de alto nível entregues

Todos os scripts novos ficam em `scripts/dev/`.

Principais comandos:

```bash
scripts/dev/status.sh
scripts/dev/run_web_backend.sh
scripts/dev/run_android_stack.sh --mode metro
scripts/dev/check_android_emulator.sh
scripts/dev/run_android_emulator_stack.sh --mode boot
scripts/dev/check_backend.sh
scripts/dev/check_reviewdesk.sh
scripts/dev/check_android.sh
scripts/dev/check_all.sh
scripts/dev/check_ci_baseline.sh
scripts/dev/run_repo_stack.sh --android metro
scripts/dev/open_codex_workspace_tmux.sh --plan
```

## Uso rápido no Linux

### 1. Backend web

```bash
scripts/dev/run_web_backend.sh
```

### 2. Mesa oficial

```bash
scripts/dev/run_web_backend.sh
# acessar http://127.0.0.1:8000/revisao/login
```

### 3. Android Metro

```bash
scripts/dev/run_android_stack.sh --mode metro
scripts/dev/check_android.sh
```

### 4. Android Emulator no Linux

```bash
scripts/dev/check_android_emulator.sh
scripts/dev/run_android_emulator_stack.sh --mode boot --headless
scripts/dev/run_android_emulator_stack.sh --mode apk --with-api
```

O modelo oficial ficou dividido em dois papéis:

- modo A, desenvolvimento diário: `scripts/dev/run_android_emulator_stack.sh --mode dev --with-api`
- modo B, instalação reprodutível: `scripts/dev/run_android_emulator_stack.sh --mode apk --with-api`

### 5. Stack coordenada sem tmux

```bash
scripts/dev/run_repo_stack.sh --android metro
```

### 6. Workspace tmux

```bash
scripts/dev/open_codex_workspace_tmux.sh --plan
scripts/dev/open_codex_workspace_tmux.sh --detached
```

Se `tmux` ainda não estiver instalado na máquina Linux, o script informa isso claramente e o modo `--plan` continua útil para revisar o layout.

## Status centralizado

O comando:

```bash
scripts/dev/status.sh
```

faz a leitura consolidada de:

- ferramentas base encontradas
- backend `GET /ready`
- reviewdesk SSR `GET /revisao/login`
- `adb` e dispositivos conectados
- SDK Android, `emulator`, AVD selecionado, emulador em execução e boot completo
- presença do `.env` do Android
- última baseline Android registrada pelo DevKit
- última lane do emulador
- último smoke Maestro conhecido

Para automação ou artifacts:

```bash
scripts/dev/status.sh --json
scripts/dev/status.sh --strict
```

## Checks rápidos por área

### Backend

```bash
scripts/dev/check_backend.sh
```

Executa:

- `py_compile` de `web/main.py`
- `pytest -q tests/test_smoke.py`

### Reviewdesk

```bash
scripts/dev/check_reviewdesk.sh
```

Executa a suíte oficial de smoke do `reviewdesk` SSR.

### Android

```bash
scripts/dev/check_android.sh
scripts/dev/check_android.sh --with-format
scripts/dev/check_android.sh --with-emulator-lane --emulator-mode boot
scripts/dev/check_android.sh --with-maestro-smoke
```

Executa:

- `npm run typecheck`
- `npm run lint`
- `npm run test:baseline`
- opcionalmente `npm run format:check`
- opcionalmente `scripts/dev/run_android_emulator_stack.sh` pela lane de emulador
- opcionalmente `maestro:smoke` quando houver device

### Geral

```bash
scripts/dev/check_all.sh
scripts/dev/check_all.sh --with-android-format
scripts/dev/check_ci_baseline.sh
```

## Direnv opcional

Existe um exemplo seguro em:

- `.envrc.example`

Ele não é obrigatório. O objetivo é acelerar bootstrap local sem impor a ferramenta ao repositório.

## Limites e postura desta fase

- não houve reescrita do produto
- não houve mudança de regra de negócio principal
- não houve migração de `npm` para `pnpm`
- não houve troca do backend Python
- não houve criação de banco novo
- `tmux`, `direnv`, `uv` e `docker compose` continuam opcionais do ponto de vista do repo
