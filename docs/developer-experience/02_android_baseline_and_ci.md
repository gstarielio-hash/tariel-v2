# Android Baseline e CI do DevKit

## Objetivo

Consolidar o Android como trilho estável do DevKit sem reescrever o app e sem fingir verde.

O baseline oficial foi definido a partir do estado real do repositório e da falha encontrada na fase anterior do DevKit.

## O que falhava

Na fase anterior, `scripts/dev/check_android.sh` quebrava por uma divergência real entre teste e implementação:

- teste afetado: `android/src/config/mobileV2OrganicSessionSignal.test.ts`
- sintoma: o contrato esperado não incluía `operatorRunId`, mas a implementação devolvia a chave com `null`
- classificação: falha segura de código/contrato interno, não flaky

## Correção aplicada

Foi ajustado `android/src/config/mobileV2Rollout.ts` para só materializar `operatorRunId` quando houver valor válido.

Impacto:

- o teste específico voltou a refletir o contrato efetivo
- a suíte Jest Android inteira voltou a ficar verde
- não houve mudança pública de backend ou de regra de negócio do produto

## Baseline Android oficial

### Obrigatório no dia a dia

- `npm run typecheck`
- `npm run lint`
- `npm run test:baseline`

Wrapper oficial do DevKit:

```bash
scripts/dev/check_android.sh
```

### CI-equivalente

- baseline obrigatório

Wrapper oficial:

```bash
scripts/dev/check_ci_baseline.sh
```

### Opcional e dependente de device

- `scripts/dev/check_android.sh --with-format`
- `scripts/dev/check_android.sh --with-emulator-lane --emulator-mode boot`
- `scripts/dev/run_android_emulator_stack.sh --mode dev --with-api`
- `scripts/dev/run_android_emulator_stack.sh --mode apk --with-api`
- `scripts/dev/check_android_emulator.sh`
- `npm run quality:strict`
- `scripts/dev/check_android.sh --with-maestro-smoke`
- `npm run maestro:smoke`
- `npm run maestro:suite`
- `npm run android:dev`
- `npm run android:preview`

Esses checks não entram no baseline mínimo porque dependem de dispositivo/emulador e elevam atrito operacional.

## O que ficou isolado de forma explícita

`format:check` continua disponível, mas não entra na baseline oficial desta fase.

Motivo:

- o repositório Android ainda possui dívida de formatação em vários arquivos já alterados no worktree
- forçar Prettier agora criaria churn operacional alto em cima de mudanças correntes
- a baseline do DevKit precisa ser reprodutível e honesta, não artificialmente verde

Por isso:

- baseline oficial = `quality:baseline`
- lane estrita opcional = `quality:strict` ou `scripts/dev/check_android.sh --with-format`

## Scripts e automação

### Android

- `scripts/dev/check_android.sh`
  - executa o baseline device-less
  - grava status em `.tmp_online/devkit/android_baseline_status.json`
  - aceita `--with-format`
  - aceita `--with-emulator-lane`
  - aceita `--with-maestro-smoke`
  - aceita `--json`
- `scripts/dev/check_android_emulator.sh`
  - audita SDK, `emulator`, `adb`, `avdmanager`, `sdkmanager`, AVD e boot
  - grava status em `.tmp_online/devkit/android_emulator_status.json`
- `scripts/dev/run_android_emulator_stack.sh`
  - orquestra `boot`, `dev`, `preview`, `apk`, `maestro-smoke` e `maestro-suite`
  - grava a última lane em `.tmp_online/devkit/android_emulator_lane_status.json`
  - grava o último smoke em `.tmp_online/devkit/android_maestro_smoke_status.json`

### Kit completo

- `scripts/dev/check_all.sh`
  - backend + frontend + Android
  - agora aceita `--with-android-emulator-lane`
  - agora aceita `--with-android-maestro-smoke`
- `scripts/dev/check_ci_baseline.sh`
  - baseline operacional compartilhado entre uso local e CI
  - roda `check_all.sh` sem exigir `format:check`

### Status

`scripts/dev/status.sh` agora mostra também:

- última baseline Android registrada
- última auditoria da lane de emulador
- última lane do emulador executada
- último smoke Maestro conhecido
- horário da última execução
- quantidade de checks obrigatórios aprovados
- checks opcionais pedidos
- falhas, se existirem

## CI

Dois pontos foram alinhados com a baseline oficial:

- `ci.yml`
  - o job `mobile-quality` agora roda `npm run quality:baseline`
- `devkit-operational-baseline.yml`
  - workflow novo que instala backend, frontend e Android
  - roda `./scripts/dev/check_ci_baseline.sh`
  - publica `.tmp_online/devkit` como artifact

## Como rodar

### Android baseline local

```bash
scripts/dev/check_android.sh
```

### Android baseline CI-equivalente

```bash
scripts/dev/check_ci_baseline.sh
```

### Baseline operacional completa

```bash
scripts/dev/check_ci_baseline.sh
```

### Lane estrita opcional

```bash
scripts/dev/check_android.sh --with-format
npm run quality:strict
```

### Lane opcional de Android Emulator no Linux

```bash
scripts/dev/check_android_emulator.sh
scripts/dev/check_android.sh --with-emulator-lane --emulator-mode boot
scripts/dev/run_android_emulator_stack.sh --mode dev --with-api
scripts/dev/run_android_emulator_stack.sh --mode apk --with-api
```

### Smoke opcional com device

```bash
scripts/dev/check_android.sh --with-maestro-smoke
```

## Como interpretar o status

Exemplo esperado depois de uma execução bem-sucedida:

- `android_baseline ok`
- `mandatory=3/3`
- `optional=format:check` apenas quando rodado explicitamente
- `android_emulator_lane ok` quando a lane de emulador for executada com sucesso
- `android_maestro_smoke fail` ou `skipped` quando o smoke não fechar em verde

Se ainda não houver baseline registrada:

- `android_baseline warn`
- mensagem pedindo para rodar `scripts/dev/check_android.sh`

## Rollback

Para desfazer rapidamente esta fase:

- reverta `android/src/config/mobileV2Rollout.ts`
- reverta `android/package.json`
- reverta `android/README.md`
- reverta `scripts/dev/check_android.sh`
- reverta `scripts/dev/check_all.sh`
- reverta `scripts/dev/check_ci_baseline.sh`
- reverta `scripts/dev/status.sh`
- reverta `scripts/dev/lib.sh`
- reverta `.github/workflows/ci.yml`
- remova `.github/workflows/devkit-operational-baseline.yml`
- remova este documento

## Próximo passo recomendado

DevKit-V3F - estabilização do smoke Maestro no emulador e revisão dos seletores do login
