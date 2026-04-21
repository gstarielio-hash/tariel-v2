#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

SERIAL=""
APK_PATH=""
APP_ID="$DEFAULT_ANDROID_APP_ID"
LAUNCH_ACTIVITY="${ANDROID_LAUNCH_ACTIVITY:-.MainActivity}"
LAUNCH_APP=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --serial)
      SERIAL="${2:?Valor ausente para --serial}"
      shift 2
      ;;
    --apk)
      APK_PATH="${2:?Valor ausente para --apk}"
      shift 2
      ;;
    --app-id)
      APP_ID="${2:?Valor ausente para --app-id}"
      shift 2
      ;;
    --launch-activity)
      LAUNCH_ACTIVITY="${2:?Valor ausente para --launch-activity}"
      shift 2
      ;;
    --no-launch)
      LAUNCH_APP=0
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/install_android_apk.sh [--serial <id>] [--apk <caminho>] [--app-id <package>] [--launch-activity <.MainActivity>] [--no-launch]

Se --apk nao for informado, tenta usar:
  android/android/app/build/outputs/apk/release/app-release.apk
EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

ADB_RUNNER="$(resolve_adb_runner || true)"
if [[ -z "$ADB_RUNNER" ]]; then
  echo "adb nao encontrado. Configure platform-tools antes de instalar o APK." >&2
  exit 1
fi

APK_PATH="$(resolve_android_apk_path "$APK_PATH" || true)"
if [[ -z "$APK_PATH" ]]; then
  echo "Nenhum APK local encontrado. Informe --apk ou gere android/app/build/outputs/apk/release/app-release.apk." >&2
  exit 1
fi

if [[ -z "$SERIAL" ]]; then
  SERIAL="$(adb_select_single_device || true)"
fi

if [[ -z "$SERIAL" ]]; then
  mapfile -t EMULATOR_SERIALS < <(adb_running_emulator_serials)
  if [[ "${#EMULATOR_SERIALS[@]}" -eq 1 ]]; then
    SERIAL="${EMULATOR_SERIALS[0]}"
  fi
fi

if [[ -z "$SERIAL" ]]; then
  echo "Nao foi possivel resolver um device unico para instalar o APK. Informe --serial <id>." >&2
  exit 1
fi

echo "[devkit] Instalando APK em $SERIAL"
echo "[devkit] APK: $APK_PATH"
"$ADB_RUNNER" -s "$SERIAL" install --no-streaming -r "$APK_PATH"

if [[ "$LAUNCH_APP" == "1" ]]; then
  LAUNCH_COMPONENT="$APP_ID/$LAUNCH_ACTIVITY"
  echo "[devkit] Abrindo app $LAUNCH_COMPONENT"
  "$ADB_RUNNER" -s "$SERIAL" shell am start -W -n "$LAUNCH_COMPONENT" >/dev/null
fi

echo "[devkit] APK instalado com sucesso em $SERIAL"
