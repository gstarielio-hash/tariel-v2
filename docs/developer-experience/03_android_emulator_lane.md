# Android Emulator Lane no Linux

## Objetivo

Remover a dependência de cabo USB e device físico do fluxo mobile diário sem reescrever o app Android atual.

O DevKit mantém:

- baseline Android obrigatória e device-less
- fluxo Expo/React Native atual
- build nativa `android:dev`
- build preview/APK local
- Maestro como smoke opcional

## Modelo oficial escolhido

### Modo A: desenvolvimento diário

Usar emulador + build dev nativa.

Comando oficial:

```bash
scripts/dev/run_android_emulator_stack.sh --mode dev --with-api
```

Papel:

- trabalho diário no app
- integração com backend local
- uso de `adb reverse`
- sem depender de celular físico

### Modo B: instalação reprodutível

Usar emulador + APK local.

Comando oficial:

```bash
scripts/dev/run_android_emulator_stack.sh --mode apk --with-api
```

Papel:

- validação limpa
- reinstalação previsível
- smoke local sem rebuild dev obrigatório

Decisão pragmática:

- modo A para iteração diária
- modo B para instalação estável e debug operacional do host

## Requisitos mínimos no Linux

- `ANDROID_SDK_ROOT` ou SDK detectável em caminho padrão
- `platform-tools` com `adb`
- `emulator`
- `cmdline-tools` com `avdmanager` e `sdkmanager`
- ao menos um AVD configurado
- acesso a `/dev/kvm`
- `node` + `npm`
- dependências de `android/`

Android Studio não é obrigatório se o SDK e o AVD já estiverem prontos.

## Auditoria oficial

Comando:

```bash
scripts/dev/check_android_emulator.sh
```

Ele verifica:

- Android Studio instalado ou não
- `ANDROID_HOME` e `ANDROID_SDK_ROOT`
- `adb`
- `emulator`
- `avdmanager`
- `sdkmanager`
- AVDs existentes
- emulador em execução
- boot completo

Artifacts locais gerados pelo DevKit:

- `.tmp_online/devkit/android_emulator_status.json`
- `.tmp_online/devkit/android_emulator_lane_status.json`
- `.tmp_online/devkit/android_maestro_smoke_status.json`

## Configurando um AVD

Listar AVDs:

```bash
emulator -list-avds
avdmanager list avd
```

Criar um AVD de exemplo:

```bash
sdkmanager "platform-tools" "emulator" "platforms;android-35" "system-images;android-35;google_apis;x86_64"
avdmanager create avd -n Tariel_API_35 -k "system-images;android-35;google_apis;x86_64" -d pixel_7
```

Se o host não estiver pronto, a lane falha com motivo explícito em vez de marcar verde.

## Fluxo diário

### 1. Auditar o host

```bash
scripts/dev/check_android_emulator.sh
```

### 2. Subir o emulador

```bash
scripts/dev/run_android_emulator_stack.sh --mode boot --headless
```

Sem `--headless`, o AVD pode ser aberto com janela pelo runner direto:

```bash
scripts/dev/run_android_emulator.sh
```

### 3. Instalar APK local

```bash
scripts/dev/install_android_apk.sh --serial emulator-5554
```

Ou pelo orquestrador:

```bash
scripts/dev/run_android_emulator_stack.sh --mode apk --with-api
```

Detalhe operacional:

- a instalação usa `adb install --no-streaming -r`
- isso foi escolhido porque o modo streamed falhou no host desta fase com `Broken pipe (32)`

### 4. Rodar build dev nativa

```bash
scripts/dev/run_android_emulator_stack.sh --mode dev --with-api
```

### 5. Rodar preview nativo existente

```bash
scripts/dev/run_android_emulator_stack.sh --mode preview --with-api
```

### 6. Rodar Maestro no emulador

```bash
scripts/dev/run_android_emulator_stack.sh --mode maestro-smoke --with-api
```

## Modo headless local padrao

No host local, o fluxo oficial de smoke mobile agora privilegia execucao silenciosa:

- `make smoke-mobile` garante um emulador Android automaticamente quando necessario;
- o bootstrap local sobe o AVD em `headless` por padrao;
- o runner prefere um `emulator-*` em vez de um device fisico quando nenhum serial foi fixado;
- o modo visual virou opt-in via flag ou variavel de ambiente.

Controles uteis:

```bash
make smoke-mobile
python3 scripts/run_mobile_pilot_runner.py --no-visual
MOBILE_VISUAL=1 node scripts/run_mobile_maestro_smoke.cjs --flow android/maestro/login-smoke.yaml
MOBILE_VISUAL=1 python3 scripts/run_mobile_pilot_runner.py --visual
```

## adb reverse

O DevKit aplica `adb reverse` automaticamente quando a lane de emulador roda.

Portas usadas:

- `8000` para a API local
- `8081` quando Metro é relevante para a lane

Verificação:

```bash
adb reverse --list
```

## Status centralizado

Comando:

```bash
scripts/dev/status.sh
```

O painel mostra:

- `emulator` disponível ou ausente
- AVD encontrado
- emulador em execução
- boot completo
- baseline Android
- última lane do emulador
- último smoke Maestro

Leitura prática:

- `android_emulator_running ready`
  - há AVD ativo via `adb`
- `android_emulator_boot ready`
  - o host já pode instalar APK ou rodar build
- `android_emulator_lane ok|fail|skipped`
  - resultado da última lane executada
- `android_maestro_smoke ok|fail|skipped`
  - resultado do último smoke conhecido

## Resultado real desta fase

Validação conseguida no host:

- SDK Android detectado em `/home/gabriel/.local/share/android-sdk`
- `adb`, `emulator`, `avdmanager` e `sdkmanager` disponíveis
- AVD `Tariel_API_35` disponível
- boot real do emulador validado
- APK local instalado no `emulator-5554`
- app aberto com `com.tarielia.inspetor/.MainActivity`
- `adb reverse` validado

Resultado honesto do Maestro:

- o smoke rodou no emulador
- falhou no assert `id: chat-tab-button is visible`
- artifacts do Maestro ficaram em `~/.maestro/tests/...`

## Rollback

Para desfazer rapidamente esta fase:

- reverta `scripts/dev/lib.sh`
- reverta `scripts/dev/check_android.sh`
- reverta `scripts/dev/check_all.sh`
- reverta `scripts/dev/check_ci_baseline.sh`
- reverta `scripts/dev/status.sh`
- reverta `scripts/dev/run_android_stack.sh`
- remova:
  - `scripts/dev/check_android_emulator.sh`
  - `scripts/dev/android_wait_for_boot.sh`
  - `scripts/dev/run_android_emulator.sh`
  - `scripts/dev/install_android_apk.sh`
  - `scripts/dev/run_android_emulator_stack.sh`
  - este documento

## Próximo passo recomendado

DevKit-V3F - estabilização do smoke Maestro no emulador e revisão dos seletores do login
