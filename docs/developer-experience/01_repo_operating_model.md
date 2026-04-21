# Modelo Operacional do Repositório

## Princípio

O repositório atual é multiproduto e precisa ser operado como três trilhos técnicos que convivem:

- `web/`: backend FastAPI, portais e reviewdesk/Mesa oficial em SSR
- `android/`: app mobile do inspetor

O DevKit não tenta fundir tudo num único runtime mágico.
Ele organiza os trilhos existentes com comandos previsíveis, status centralizado e convenções de porta.

## Portas e endereços padrão

- backend web: `127.0.0.1:8000`
- reviewdesk login: `127.0.0.1:8000/revisao/login`
- reviewdesk painel: `127.0.0.1:8000/revisao/painel`
- Android Metro: `127.0.0.1:8081`

## Quem é fonte de verdade

### Backend

- `web/main.py`
- `GET /ready`
- `GET /health`

### Reviewdesk SSR

- o backend Python é a única fonte de verdade da Mesa
- não existe frontend paralelo oficial para a revisão
- os smokes da Mesa ficam no workspace `web/`

### Android

- o app continua em Expo/React Native
- o backend web local continua servindo como API do mobile em ambiente Linux
- o Android Emulator no Linux passa a ser a lane oficial para trabalho sem cabo USB

## Operação diária recomendada

### Fluxo web/backend + Mesa

1. subir backend:

```bash
scripts/dev/run_web_backend.sh
```

2. abrir o reviewdesk:

```bash
http://127.0.0.1:8000/revisao/login
```

3. acompanhar:

```bash
scripts/dev/status.sh
```

### Fluxo Android

Metro puro:

```bash
scripts/dev/run_android_stack.sh --mode metro
```

Build dev nativo:

```bash
scripts/dev/run_android_stack.sh --mode android-dev
```

APK preview local:

```bash
scripts/dev/run_android_stack.sh --mode android-preview
```

Smoke Maestro:

```bash
scripts/dev/run_android_stack.sh --mode maestro-smoke --with-api
```

Android Emulator no Linux:

```bash
scripts/dev/check_android_emulator.sh
scripts/dev/run_android_emulator_stack.sh --mode boot --headless
scripts/dev/run_android_emulator_stack.sh --mode dev --with-api
scripts/dev/run_android_emulator_stack.sh --mode apk --with-api
scripts/dev/run_android_emulator_stack.sh --mode maestro-smoke --with-api
```

## Workspace tmux

O script oficial é:

```bash
scripts/dev/open_codex_workspace_tmux.sh
```

Layout previsto:

- `backend`
- `reviewdesk`
- `checks`
- `android`
- `codex`

Detalhes do layout:

- a janela `checks` abre um terminal livre e um watcher de `scripts/dev/status.sh`
- a janela `android` usa `metro` por padrão para não depender de dispositivo já conectado
- a janela `codex` fica reservada para trabalho interativo

Modo de revisão sem abrir a sessão:

```bash
scripts/dev/open_codex_workspace_tmux.sh --plan
```

## Logs e observabilidade

### Backend web

- terminal do `run_web_backend.sh`
- `GET /ready`
- `GET /health`

### Reviewdesk SSR

- terminal do `run_web_backend.sh`
- `GET /revisao/login`
- artifacts Playwright do workspace `web/`

### Android

- terminal do Metro ou do build Android
- `adb devices`
- `scripts/dev/check_android_emulator.sh`
- `.tmp_online/devkit/android_emulator.log`
- `local-mobile-api.log`
- `local-mobile-api.error.log`
- `android/expo-mobile.log`

## Fluxo recomendado para Codex CLI

### Quando o foco for backend

- usar `scripts/dev/run_web_backend.sh`
- usar `scripts/dev/check_backend.sh`

### Quando o foco for Mesa

- usar `scripts/dev/run_web_backend.sh`
- usar `scripts/dev/check_reviewdesk.sh`
- usar `make mesa-smoke`

### Quando o foco for Android

- usar `scripts/dev/run_android_stack.sh --mode metro`
- usar `scripts/dev/check_android_emulator.sh` para auditar o host Linux
- usar `scripts/dev/run_android_emulator_stack.sh --mode boot` para garantir AVD pronto
- usar `scripts/dev/run_android_emulator_stack.sh --mode dev --with-api` para o fluxo diário
- usar `scripts/dev/run_android_emulator_stack.sh --mode apk --with-api` para instalação reprodutível
- usar `scripts/dev/check_android.sh`
- usar `scripts/dev/check_android.sh --with-format` para baseline CI-equivalente
- usar `scripts/dev/status.sh` para ver `adb`, AVD, boot e Maestro

### Quando o foco for integração do dia inteiro

- usar `scripts/dev/run_repo_stack.sh --android metro`
- usar `scripts/dev/check_ci_baseline.sh` para o baseline operacional compartilhado com CI
- ou `scripts/dev/open_codex_workspace_tmux.sh`, quando `tmux` estiver disponível

## O que é obrigatório vs opcional

### Obrigatório para este repo funcionar

- Python compatível com `web/`
- Node + npm
- adb para fluxo Android

### Opcional, mas oficialmente suportado

- `tmux`
- `direnv`
- `uv`
- `docker compose`

## Rollback operacional

O DevKit é de baixo risco porque:

- ele fica isolado em `scripts/dev/`
- reaproveita os runners já existentes
- não altera o backend público
- não reintroduz frontend paralelo para a Mesa
- não muda o fluxo Android principal

Se precisar desfazer rapidamente:

- remova `scripts/dev/`
- remova `.envrc.example`
- remova `docs/developer-experience/`
