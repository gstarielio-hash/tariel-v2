#!/usr/bin/env bash
set -uo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

WITH_ANDROID_MAESTRO_SMOKE=0
WITH_ANDROID_EMULATOR_LANE=0
ANDROID_EMULATOR_MODE="boot"
ANDROID_EMULATOR_HEADLESS=0
ANDROID_EMULATOR_APK_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-android-maestro-smoke)
      WITH_ANDROID_MAESTRO_SMOKE=1
      shift
      ;;
    --with-android-emulator-lane)
      WITH_ANDROID_EMULATOR_LANE=1
      shift
      ;;
    --android-emulator-mode)
      ANDROID_EMULATOR_MODE="${2:?Valor ausente para --android-emulator-mode}"
      shift 2
      ;;
    --android-emulator-headless)
      ANDROID_EMULATOR_HEADLESS=1
      shift
      ;;
    --android-emulator-apk)
      ANDROID_EMULATOR_APK_PATH="${2:?Valor ausente para --android-emulator-apk}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/check_ci_baseline.sh [--with-android-emulator-lane] [--android-emulator-mode boot|metro|dev|preview|apk|maestro-smoke|maestro-suite] [--android-emulator-headless] [--android-emulator-apk <caminho>] [--with-android-maestro-smoke]

EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

ARGS=()
if [[ "$WITH_ANDROID_MAESTRO_SMOKE" == "1" ]]; then
  ARGS+=(--with-android-maestro-smoke)
fi
if [[ "$WITH_ANDROID_EMULATOR_LANE" == "1" ]]; then
  ARGS+=(--with-android-emulator-lane --android-emulator-mode "$ANDROID_EMULATOR_MODE")
fi
if [[ "$ANDROID_EMULATOR_HEADLESS" == "1" ]]; then
  ARGS+=(--android-emulator-headless)
fi
if [[ -n "$ANDROID_EMULATOR_APK_PATH" ]]; then
  ARGS+=(--android-emulator-apk "$ANDROID_EMULATOR_APK_PATH")
fi

echo "[devkit] CI baseline do kit operacional"
echo "[devkit] Android baseline: quality:baseline"
"$DEV_DIR/check_all.sh" "${ARGS[@]}"
