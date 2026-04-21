#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

SERIAL=""
TIMEOUT_SECONDS="$DEFAULT_ANDROID_EMULATOR_BOOT_TIMEOUT"
SLEEP_SECONDS=5
STABLE_PASSES=0
REQUIRED_STABLE_PASSES=3

while [[ $# -gt 0 ]]; do
  case "$1" in
    --serial)
      SERIAL="${2:?Valor ausente para --serial}"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:?Valor ausente para --timeout}"
      shift 2
      ;;
    --sleep)
      SLEEP_SECONDS="${2:?Valor ausente para --sleep}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/android_wait_for_boot.sh [--serial <id>] [--timeout <segundos>] [--sleep <segundos>]
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
  echo "adb nao encontrado. Configure platform-tools antes de esperar o boot." >&2
  exit 1
fi

if [[ -z "$SERIAL" ]]; then
  SERIAL="$(adb_select_single_device || true)"
fi

if [[ -z "$SERIAL" ]]; then
  mapfile -t RUNNING_EMULATORS < <(adb_emulator_serials)
  if [[ "${#RUNNING_EMULATORS[@]}" -eq 1 ]]; then
    SERIAL="${RUNNING_EMULATORS[0]}"
  fi
fi

if [[ -z "$SERIAL" ]]; then
  echo "Nao foi possivel resolver um serial unico. Informe --serial <id>." >&2
  exit 1
fi

echo "[devkit] Aguardando dispositivo $SERIAL..."
"$ADB_RUNNER" -s "$SERIAL" wait-for-device

DEADLINE=$((SECONDS + TIMEOUT_SECONDS))
while (( SECONDS < DEADLINE )); do
  if android_is_boot_completed "$SERIAL"; then
    STABLE_PASSES=$((STABLE_PASSES + 1))
    if (( STABLE_PASSES >= REQUIRED_STABLE_PASSES )); then
      echo "[devkit] Boot completo e estavel: $SERIAL"
      exit 0
    fi
  else
    STABLE_PASSES=0
  fi

  SYS_BOOT="$(android_boot_status "$SERIAL" "sys.boot_completed" || true)"
  DEV_BOOT="$(android_boot_status "$SERIAL" "dev.bootcomplete" || true)"
  BOOT_ANIM="$(android_boot_status "$SERIAL" "init.svc.bootanim" || true)"
  if android_package_service_ready "$SERIAL"; then
    PACKAGE_READY="yes"
  else
    PACKAGE_READY="no"
  fi
  echo "[devkit] Boot pendente: serial=$SERIAL sys=${SYS_BOOT:-0} dev=${DEV_BOOT:-0} bootanim=${BOOT_ANIM:-unknown} package=${PACKAGE_READY} stable=${STABLE_PASSES}/${REQUIRED_STABLE_PASSES}"
  sleep "$SLEEP_SECONDS"
done

SYS_BOOT="$(android_boot_status "$SERIAL" "sys.boot_completed" || true)"
DEV_BOOT="$(android_boot_status "$SERIAL" "dev.bootcomplete" || true)"
BOOT_ANIM="$(android_boot_status "$SERIAL" "init.svc.bootanim" || true)"
if android_package_service_ready "$SERIAL"; then
  PACKAGE_READY="yes"
else
  PACKAGE_READY="no"
fi
echo "Timeout aguardando boot do Android: serial=$SERIAL sys=${SYS_BOOT:-0} dev=${DEV_BOOT:-0} bootanim=${BOOT_ANIM:-unknown} package=${PACKAGE_READY} stable=${STABLE_PASSES}/${REQUIRED_STABLE_PASSES}" >&2
exit 1
