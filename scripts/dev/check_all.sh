#!/usr/bin/env bash
set -uo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

WITH_ANDROID_FORMAT=0
WITH_ANDROID_MAESTRO_SMOKE=0
WITH_ANDROID_EMULATOR_LANE=0
ANDROID_EMULATOR_MODE="boot"
ANDROID_EMULATOR_HEADLESS=0
ANDROID_EMULATOR_APK_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-android-format)
      WITH_ANDROID_FORMAT=1
      shift
      ;;
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
  scripts/dev/check_all.sh [--with-android-format] [--with-android-emulator-lane] [--android-emulator-mode boot|metro|dev|preview|apk|maestro-smoke|maestro-suite] [--android-emulator-headless] [--android-emulator-apk <caminho>] [--with-android-maestro-smoke]

EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

BACKEND_STATUS="ok"
REVIEWDESK_STATUS="ok"
ANDROID_STATUS="ok"

run_area_check() {
  local area_name="$1"
  shift

  echo "[devkit] Check area: $area_name"
  if "$@"; then
    echo "[devkit] Check area $area_name: OK"
    return 0
  fi

  echo "[devkit] Check area $area_name: FAIL" >&2
  return 1
}

run_area_check "backend" "$DEV_DIR/check_backend.sh" || BACKEND_STATUS="fail"
run_area_check "reviewdesk" "$DEV_DIR/check_reviewdesk.sh" || REVIEWDESK_STATUS="fail"

ANDROID_ARGS=()
if [[ "$WITH_ANDROID_FORMAT" == "1" ]]; then
  ANDROID_ARGS+=(--with-format)
fi
if [[ "$WITH_ANDROID_EMULATOR_LANE" == "1" ]]; then
  ANDROID_ARGS+=(--with-emulator-lane --emulator-mode "$ANDROID_EMULATOR_MODE")
fi
if [[ "$ANDROID_EMULATOR_HEADLESS" == "1" ]]; then
  ANDROID_ARGS+=(--emulator-headless)
fi
if [[ -n "$ANDROID_EMULATOR_APK_PATH" ]]; then
  ANDROID_ARGS+=(--emulator-apk "$ANDROID_EMULATOR_APK_PATH")
fi
if [[ "$WITH_ANDROID_MAESTRO_SMOKE" == "1" ]]; then
  ANDROID_ARGS+=(--with-maestro-smoke)
fi
run_area_check "android" "$DEV_DIR/check_android.sh" "${ANDROID_ARGS[@]}" || ANDROID_STATUS="fail"

echo "[devkit] Status consolidado:"
"$DEV_DIR/status.sh" || true

echo "[devkit] Resumo:"
printf '%-12s %s\n' "backend" "$BACKEND_STATUS"
printf '%-12s %s\n' "reviewdesk" "$REVIEWDESK_STATUS"
printf '%-12s %s\n' "android" "$ANDROID_STATUS"

if [[ "$BACKEND_STATUS" == "ok" && "$REVIEWDESK_STATUS" == "ok" && "$ANDROID_STATUS" == "ok" ]]; then
  echo "[devkit] Check all: OK"
  exit 0
fi

echo "[devkit] Check all: FAIL" >&2
exit 1
