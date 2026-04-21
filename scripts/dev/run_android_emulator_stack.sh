#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

MODE="boot"
WITH_API=0
SKIP_ADB_REVERSE=0
REQUESTED_AVD=""
REQUESTED_SERIAL=""
APK_PATH=""
HEADLESS=0
WIPE_DATA=0
FORCE_COLD_BOOT=0
DRY_RUN=0
BOOT_TIMEOUT="$DEFAULT_ANDROID_EMULATOR_BOOT_TIMEOUT"
METRO_PORT="$DEFAULT_ANDROID_METRO_PORT"
LANE_STATE_FILE=""

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
    --metro-port)
      METRO_PORT="${2:?Valor ausente para --metro-port}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/run_android_emulator_stack.sh [--mode boot|metro|dev|preview|apk|maestro-smoke|maestro-suite] [--with-api] [--skip-adb-reverse] [--avd <nome>] [--serial <id>] [--apk <caminho>] [--headless] [--wipe-data] [--force-cold-boot] [--boot-timeout <segundos>] [--metro-port <porta>] [--dry-run]

Modos:
  boot            Sobe o AVD e espera boot completo.
  metro           Sobe o AVD e inicia apenas o Expo/Metro.
  dev             Sobe o AVD e roda o fluxo npm run android:dev.
  preview         Sobe o AVD e roda o fluxo npm run android:preview.
  apk             Sobe o AVD e instala um APK local.
  maestro-smoke   Sobe o AVD e dispara npm run maestro:smoke.
  maestro-suite   Sobe o AVD e dispara npm run maestro:suite.
EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

ensure_devkit_runtime_dir
LANE_STATE_FILE="$DEVKIT_RUNTIME_DIR/android_emulator_lane_status.json"
MAESTRO_STATE_FILE="$DEVKIT_RUNTIME_DIR/android_maestro_smoke_status.json"

record_lane_status() {
  local status="$1"
  local detail="$2"
  local avd_name="$3"
  local serial="$4"
  local requested_apk="$5"

  python3 - "$LANE_STATE_FILE" "$REPO_ROOT" "$status" "$detail" "$MODE" "$avd_name" "$serial" "$WITH_API" "$SKIP_ADB_REVERSE" "$requested_apk" <<'PY'
import json
import pathlib
import sys
from datetime import datetime

state_path = pathlib.Path(sys.argv[1])
workspace = pathlib.Path(sys.argv[2])
status = sys.argv[3]
detail = sys.argv[4]
mode = sys.argv[5]
avd_name = sys.argv[6]
serial = sys.argv[7]
with_api = sys.argv[8] == "1"
skip_adb_reverse = sys.argv[9] == "1"
requested_apk = sys.argv[10]

payload = {
    "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
    "workspace": str(workspace),
    "mode": mode,
    "status": status,
    "detail": detail,
    "avd": avd_name,
    "serial": serial,
    "withApi": with_api,
    "skipAdbReverse": skip_adb_reverse,
    "apkPath": requested_apk,
}

state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

  if [[ "$MODE" == "maestro-smoke" || "$MODE" == "maestro-suite" ]]; then
    python3 - "$MAESTRO_STATE_FILE" "$REPO_ROOT" "$status" "$detail" "$MODE" "$avd_name" "$serial" "$WITH_API" "$SKIP_ADB_REVERSE" "$requested_apk" <<'PY'
import json
import pathlib
import sys
from datetime import datetime

state_path = pathlib.Path(sys.argv[1])
workspace = pathlib.Path(sys.argv[2])
status = sys.argv[3]
detail = sys.argv[4]
mode = sys.argv[5]
avd_name = sys.argv[6]
serial = sys.argv[7]
with_api = sys.argv[8] == "1"
skip_adb_reverse = sys.argv[9] == "1"
requested_apk = sys.argv[10]

payload = {
    "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
    "workspace": str(workspace),
    "mode": mode,
    "status": status,
    "detail": detail,
    "avd": avd_name,
    "serial": serial,
    "withApi": with_api,
    "skipAdbReverse": skip_adb_reverse,
    "apkPath": requested_apk,
}

state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
  fi
}

fail_lane() {
  local detail="$1"
  local avd_name="${2:-}"
  local serial="${3:-}"
  record_lane_status "fail" "$detail" "$avd_name" "$serial" "$APK_PATH"
  echo "$detail" >&2
  exit 1
}

BOOT_ARGS=()
if [[ -n "$REQUESTED_AVD" ]]; then
  BOOT_ARGS+=(--avd "$REQUESTED_AVD")
fi
if [[ -n "$REQUESTED_SERIAL" ]]; then
  BOOT_ARGS+=(--serial "$REQUESTED_SERIAL")
fi
if [[ "$HEADLESS" == "1" ]]; then
  BOOT_ARGS+=(--headless)
fi
if [[ "$WIPE_DATA" == "1" ]]; then
  BOOT_ARGS+=(--wipe-data)
fi
if [[ "$FORCE_COLD_BOOT" == "1" ]]; then
  BOOT_ARGS+=(--force-cold-boot)
fi
BOOT_ARGS+=(--boot-timeout "$BOOT_TIMEOUT")

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[devkit] Dry-run da lane de emulador"
  "$DEV_DIR/run_android_emulator.sh" "${BOOT_ARGS[@]}" --dry-run
  case "$MODE" in
    boot)
      ;;
    metro)
      echo "\"$(resolve_expo_runner || echo expo)\" start --non-interactive --port $METRO_PORT"
      ;;
    dev)
      echo "cd \"$ANDROID_ROOT\" && ANDROID_SERIAL=<serial> npm run android:dev"
      ;;
    preview)
      echo "cd \"$ANDROID_ROOT\" && ANDROID_SERIAL=<serial> npm run android:preview"
      ;;
    apk)
      echo "\"$DEV_DIR/install_android_apk.sh\" --serial <serial> --apk \"${APK_PATH:-<default>}\""
      ;;
    maestro-smoke)
      echo "cd \"$ANDROID_ROOT\" && ANDROID_SERIAL=<serial> npm run maestro:smoke"
      ;;
    maestro-suite)
      echo "cd \"$ANDROID_ROOT\" && ANDROID_SERIAL=<serial> npm run maestro:suite"
      ;;
    *)
      fail_lane "Modo de emulador nao reconhecido: $MODE"
      ;;
  esac
  record_lane_status "ok" "dry-run" "${REQUESTED_AVD:-}" "${REQUESTED_SERIAL:-}" "$APK_PATH"
  exit 0
fi

AUDIT_ARGS=()
if [[ -n "$REQUESTED_AVD" ]]; then
  AUDIT_ARGS+=(--avd "$REQUESTED_AVD")
fi
if ! "$DEV_DIR/check_android_emulator.sh" "${AUDIT_ARGS[@]}" >/dev/null; then
  fail_lane "Auditoria da lane Android Emulator falhou. Rode scripts/dev/check_android_emulator.sh para detalhes." "${REQUESTED_AVD:-}" "${REQUESTED_SERIAL:-}"
fi

SELECTED_SERIAL="$("$DEV_DIR/run_android_emulator.sh" "${BOOT_ARGS[@]}")" || fail_lane "Falha ao subir o Android Emulator." "${REQUESTED_AVD:-}" "${REQUESTED_SERIAL:-}"
SELECTED_SERIAL="$(printf '%s\n' "$SELECTED_SERIAL" | tail -n 1 | tr -d '\r')"
SELECTED_AVD="$(select_android_avd "$REQUESTED_AVD" || true)"

if [[ -z "$SELECTED_SERIAL" ]]; then
  fail_lane "Nenhum serial foi resolvido para a lane do emulador." "$SELECTED_AVD" ""
fi

if [[ "$WITH_API" == "1" ]]; then
  echo "[devkit] Subindo API local para o mobile..."
  "$REPO_ROOT/scripts/start_local_mobile_api_background.sh"
fi

if [[ "$SKIP_ADB_REVERSE" != "1" ]]; then
  REVERSE_PORTS=("$DEFAULT_BACKEND_PORT")
  case "$MODE" in
    metro|dev|maestro-smoke|maestro-suite)
      REVERSE_PORTS+=("$METRO_PORT")
      ;;
  esac
  echo "[devkit] Aplicando adb reverse em $SELECTED_SERIAL: $(IFS=,; echo "${REVERSE_PORTS[*]}")"
  apply_adb_reverse "$SELECTED_SERIAL" "${REVERSE_PORTS[@]}" \
    || fail_lane "Falha ao aplicar adb reverse no emulador." "$SELECTED_AVD" "$SELECTED_SERIAL"
fi

ensure_android_deps
EXPO_RUNNER="$(resolve_expo_runner || true)"

case "$MODE" in
  boot)
    record_lane_status "ok" "emulador iniciado e boot concluido" "$SELECTED_AVD" "$SELECTED_SERIAL" "$APK_PATH"
    echo "[devkit] Android Emulator pronto: avd=$SELECTED_AVD serial=$SELECTED_SERIAL"
    ;;
  metro)
    if [[ -z "$EXPO_RUNNER" ]]; then
      fail_lane "Expo CLI nao encontrada. Rode npm install em android/." "$SELECTED_AVD" "$SELECTED_SERIAL"
    fi
    echo "[devkit] Android Metro em http://127.0.0.1:$METRO_PORT"
    (
      cd "$ANDROID_ROOT"
      ANDROID_SERIAL="$SELECTED_SERIAL" "$EXPO_RUNNER" start --non-interactive --port "$METRO_PORT"
    ) || fail_lane "Falha ao iniciar Metro para o emulador." "$SELECTED_AVD" "$SELECTED_SERIAL"
    record_lane_status "ok" "metro encerrado sem erro" "$SELECTED_AVD" "$SELECTED_SERIAL" "$APK_PATH"
    ;;
  dev)
    echo "[devkit] Android dev nativo via npm run android:dev"
    (
      cd "$ANDROID_ROOT"
      ANDROID_SERIAL="$SELECTED_SERIAL" npm run android:dev
    ) || fail_lane "Falha no fluxo android:dev para o emulador." "$SELECTED_AVD" "$SELECTED_SERIAL"
    record_lane_status "ok" "android:dev concluido" "$SELECTED_AVD" "$SELECTED_SERIAL" "$APK_PATH"
    ;;
  preview)
    echo "[devkit] Android preview local via npm run android:preview"
    (
      cd "$ANDROID_ROOT"
      ANDROID_SERIAL="$SELECTED_SERIAL" npm run android:preview
    ) || fail_lane "Falha no fluxo android:preview para o emulador." "$SELECTED_AVD" "$SELECTED_SERIAL"
    record_lane_status "ok" "android:preview concluido" "$SELECTED_AVD" "$SELECTED_SERIAL" "$APK_PATH"
    ;;
  apk)
    INSTALL_ARGS=(--serial "$SELECTED_SERIAL")
    if [[ -n "$APK_PATH" ]]; then
      INSTALL_ARGS+=(--apk "$APK_PATH")
    fi
    "$DEV_DIR/install_android_apk.sh" "${INSTALL_ARGS[@]}" \
      || fail_lane "Falha ao instalar APK local no emulador." "$SELECTED_AVD" "$SELECTED_SERIAL"
    record_lane_status "ok" "apk instalado com sucesso" "$SELECTED_AVD" "$SELECTED_SERIAL" "${APK_PATH:-$(android_default_apk_path || true)}"
    ;;
  maestro-smoke)
    echo "[devkit] Maestro smoke no emulador"
    (
      cd "$ANDROID_ROOT"
      ANDROID_SERIAL="$SELECTED_SERIAL" npm run maestro:smoke
    ) || fail_lane "Falha no Maestro smoke do emulador." "$SELECTED_AVD" "$SELECTED_SERIAL"
    record_lane_status "ok" "maestro smoke concluido" "$SELECTED_AVD" "$SELECTED_SERIAL" "$APK_PATH"
    ;;
  maestro-suite)
    echo "[devkit] Maestro suite no emulador"
    (
      cd "$ANDROID_ROOT"
      ANDROID_SERIAL="$SELECTED_SERIAL" npm run maestro:suite
    ) || fail_lane "Falha na suite Maestro do emulador." "$SELECTED_AVD" "$SELECTED_SERIAL"
    record_lane_status "ok" "maestro suite concluida" "$SELECTED_AVD" "$SELECTED_SERIAL" "$APK_PATH"
    ;;
  *)
    fail_lane "Modo de emulador nao reconhecido: $MODE" "$SELECTED_AVD" "$SELECTED_SERIAL"
    ;;
esac
