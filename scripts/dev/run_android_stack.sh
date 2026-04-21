#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

MODE="metro"
WITH_API=0
SKIP_ADB_REVERSE=0
DRY_RUN=0
METRO_PORT="$DEFAULT_ANDROID_METRO_PORT"
REQUESTED_AVD=""
REQUESTED_SERIAL=""
APK_PATH=""
HEADLESS=0
WIPE_DATA=0
FORCE_COLD_BOOT=0
BOOT_TIMEOUT="$DEFAULT_ANDROID_EMULATOR_BOOT_TIMEOUT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:?Valor ausente para --mode}"
      shift 2
      ;;
    --with-api)
      WITH_API=1
      shift
      ;;
    --skip-adb-reverse)
      SKIP_ADB_REVERSE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --metro-port)
      METRO_PORT="${2:?Valor ausente para --metro-port}"
      shift 2
      ;;
    --avd)
      REQUESTED_AVD="${2:?Valor ausente para --avd}"
      shift 2
      ;;
    --serial)
      REQUESTED_SERIAL="${2:?Valor ausente para --serial}"
      shift 2
      ;;
    --apk)
      APK_PATH="${2:?Valor ausente para --apk}"
      shift 2
      ;;
    --headless)
      HEADLESS=1
      shift
      ;;
    --wipe-data)
      WIPE_DATA=1
      shift
      ;;
    --force-cold-boot)
      FORCE_COLD_BOOT=1
      shift
      ;;
    --boot-timeout)
      BOOT_TIMEOUT="${2:?Valor ausente para --boot-timeout}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/run_android_stack.sh [--mode metro|android-dev|android-preview|maestro-smoke|maestro-suite|emulator-boot|emulator-metro|emulator-dev|emulator-preview|emulator-apk|emulator-maestro-smoke|emulator-maestro-suite] [--with-api] [--skip-adb-reverse] [--avd <nome>] [--serial <id>] [--apk <caminho>] [--headless] [--wipe-data] [--force-cold-boot] [--boot-timeout <segundos>] [--dry-run]

Modos:
  metro            Sobe apenas o Expo/Metro em modo nao interativo.
  android-dev      Roda o app Android nativo de desenvolvimento.
  android-preview  Instala a variante preview/release local.
  maestro-smoke    Dispara o smoke principal do Maestro.
  maestro-suite    Dispara a suite Maestro encadeada.
  emulator-*       Lane oficial de Android Emulator no Linux.

EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

EMULATOR_MODE=""
case "$MODE" in
  emulator|emulator-boot)
    EMULATOR_MODE="boot"
    ;;
  emulator-metro)
    EMULATOR_MODE="metro"
    ;;
  emulator-dev)
    EMULATOR_MODE="dev"
    ;;
  emulator-preview)
    EMULATOR_MODE="preview"
    ;;
  emulator-apk)
    EMULATOR_MODE="apk"
    ;;
  emulator-maestro-smoke)
    EMULATOR_MODE="maestro-smoke"
    ;;
  emulator-maestro-suite)
    EMULATOR_MODE="maestro-suite"
    ;;
esac

if [[ -n "$EMULATOR_MODE" ]]; then
  EMULATOR_ARGS=(--mode "$EMULATOR_MODE" --boot-timeout "$BOOT_TIMEOUT" --metro-port "$METRO_PORT")
  if [[ "$WITH_API" == "1" ]]; then
    EMULATOR_ARGS+=(--with-api)
  fi
  if [[ "$SKIP_ADB_REVERSE" == "1" ]]; then
    EMULATOR_ARGS+=(--skip-adb-reverse)
  fi
  if [[ -n "$REQUESTED_AVD" ]]; then
    EMULATOR_ARGS+=(--avd "$REQUESTED_AVD")
  fi
  if [[ -n "$REQUESTED_SERIAL" ]]; then
    EMULATOR_ARGS+=(--serial "$REQUESTED_SERIAL")
  fi
  if [[ -n "$APK_PATH" ]]; then
    EMULATOR_ARGS+=(--apk "$APK_PATH")
  fi
  if [[ "$HEADLESS" == "1" ]]; then
    EMULATOR_ARGS+=(--headless)
  fi
  if [[ "$WIPE_DATA" == "1" ]]; then
    EMULATOR_ARGS+=(--wipe-data)
  fi
  if [[ "$FORCE_COLD_BOOT" == "1" ]]; then
    EMULATOR_ARGS+=(--force-cold-boot)
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    EMULATOR_ARGS+=(--dry-run)
  fi
  exec "$DEV_DIR/run_android_emulator_stack.sh" "${EMULATOR_ARGS[@]}"
fi

ensure_android_deps

DEVICE_COUNT="$(adb_device_count)"
EAS_RUNNER="$(resolve_eas_runner || true)"
EXPO_RUNNER="$(resolve_expo_runner || true)"
ADB_RUNNER="$(resolve_adb_runner || true)"

if [[ "$WITH_API" == "1" ]]; then
  echo "[devkit] Subindo API local para o mobile..."
  "$REPO_ROOT/scripts/start_local_mobile_api_background.sh"
fi

if [[ "$SKIP_ADB_REVERSE" != "1" && "$DEVICE_COUNT" -gt 0 && -n "$ADB_RUNNER" ]]; then
  echo "[devkit] Aplicando adb reverse para a API local..."
  if [[ -n "$REQUESTED_SERIAL" ]]; then
    apply_adb_reverse "$REQUESTED_SERIAL" "$DEFAULT_BACKEND_PORT" >/dev/null
  else
    "$ADB_RUNNER" reverse "tcp:$DEFAULT_BACKEND_PORT" "tcp:$DEFAULT_BACKEND_PORT" >/dev/null
  fi
  if [[ "$MODE" == "metro" ]]; then
    if [[ -n "$REQUESTED_SERIAL" ]]; then
      apply_adb_reverse "$REQUESTED_SERIAL" "$METRO_PORT" >/dev/null || true
    else
      "$ADB_RUNNER" reverse "tcp:$METRO_PORT" "tcp:$METRO_PORT" >/dev/null || true
    fi
  fi
fi

case "$MODE" in
  metro)
    if [[ -z "$EXPO_RUNNER" ]]; then
      echo "Expo CLI nao encontrada. Rode npm install em android/." >&2
      exit 1
    fi
    echo "[devkit] Android Metro em http://127.0.0.1:$METRO_PORT"
    echo "[devkit] Expo runner: $EXPO_RUNNER"
    if [[ "$DRY_RUN" == "1" ]]; then
      exit 0
    fi
    cd "$ANDROID_ROOT"
    exec "$EXPO_RUNNER" start --non-interactive --port "$METRO_PORT"
    ;;
  android-dev)
    if [[ "$DEVICE_COUNT" -eq 0 ]]; then
      echo "Nenhum dispositivo Android conectado para --mode android-dev." >&2
      exit 1
    fi
    echo "[devkit] Android dev nativo via npm run android:dev"
    if [[ "$DRY_RUN" == "1" ]]; then
      exit 0
    fi
    cd "$ANDROID_ROOT"
    if [[ -n "$REQUESTED_SERIAL" ]]; then
      exec env ANDROID_SERIAL="$REQUESTED_SERIAL" npm run android:dev
    fi
    exec npm run android:dev
    ;;
  android-preview)
    if [[ "$DEVICE_COUNT" -eq 0 ]]; then
      echo "Nenhum dispositivo Android conectado para --mode android-preview." >&2
      exit 1
    fi
    echo "[devkit] Android preview local via npm run android:preview"
    if [[ "$DRY_RUN" == "1" ]]; then
      exit 0
    fi
    cd "$ANDROID_ROOT"
    if [[ -n "$REQUESTED_SERIAL" ]]; then
      exec env ANDROID_SERIAL="$REQUESTED_SERIAL" npm run android:preview
    fi
    exec npm run android:preview
    ;;
  maestro-smoke)
    if [[ "$DEVICE_COUNT" -eq 0 ]]; then
      echo "Nenhum dispositivo Android conectado para --mode maestro-smoke." >&2
      exit 1
    fi
    echo "[devkit] Maestro smoke do Android"
    if [[ "$DRY_RUN" == "1" ]]; then
      exit 0
    fi
    cd "$ANDROID_ROOT"
    if [[ -n "$REQUESTED_SERIAL" ]]; then
      exec env ANDROID_SERIAL="$REQUESTED_SERIAL" npm run maestro:smoke
    fi
    exec npm run maestro:smoke
    ;;
  maestro-suite)
    if [[ "$DEVICE_COUNT" -eq 0 ]]; then
      echo "Nenhum dispositivo Android conectado para --mode maestro-suite." >&2
      exit 1
    fi
    echo "[devkit] Maestro suite do Android"
    if [[ "$DRY_RUN" == "1" ]]; then
      exit 0
    fi
    cd "$ANDROID_ROOT"
    if [[ -n "$REQUESTED_SERIAL" ]]; then
      exec env ANDROID_SERIAL="$REQUESTED_SERIAL" npm run maestro:suite
    fi
    exec npm run maestro:suite
    ;;
  *)
    echo "Modo Android nao reconhecido: $MODE" >&2
    exit 1
    ;;
esac
