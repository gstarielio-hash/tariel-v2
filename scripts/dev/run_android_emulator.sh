#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

REQUESTED_AVD=""
REQUESTED_SERIAL=""
REQUESTED_PORT=""
HEADLESS=0
WIPE_DATA=0
FORCE_COLD_BOOT=0
NO_BOOT_WAIT=0
DRY_RUN=0
BOOT_TIMEOUT="$DEFAULT_ANDROID_EMULATOR_BOOT_TIMEOUT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --avd)
      REQUESTED_AVD="${2:?Valor ausente para --avd}"
      shift 2
      ;;
    --serial)
      REQUESTED_SERIAL="${2:?Valor ausente para --serial}"
      shift 2
      ;;
    --port)
      REQUESTED_PORT="${2:?Valor ausente para --port}"
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
    --no-boot-wait)
      NO_BOOT_WAIT=1
      shift
      ;;
    --boot-timeout)
      BOOT_TIMEOUT="${2:?Valor ausente para --boot-timeout}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/run_android_emulator.sh [--avd <nome>] [--serial <id>] [--port <5554>] [--headless] [--wipe-data] [--force-cold-boot] [--no-boot-wait] [--boot-timeout <segundos>] [--dry-run]
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
AUDIT_ARGS=()
if [[ -n "$REQUESTED_AVD" ]]; then
  AUDIT_ARGS+=(--avd "$REQUESTED_AVD")
fi
"$DEV_DIR/check_android_emulator.sh" "${AUDIT_ARGS[@]}" >/dev/null

SELECTED_AVD="$(select_android_avd "$REQUESTED_AVD" || true)"
EMULATOR_RUNNER="$(resolve_emulator_runner || true)"
ADB_RUNNER="$(resolve_adb_runner || true)"

if [[ -z "$SELECTED_AVD" ]]; then
  echo "Nenhum AVD disponivel. Rode scripts/dev/check_android_emulator.sh para auditar o host." >&2
  exit 1
fi

if [[ -z "$EMULATOR_RUNNER" ]]; then
  echo "Binary do emulator nao encontrado. Rode scripts/dev/check_android_emulator.sh para detalhes." >&2
  exit 1
fi

if [[ -z "$ADB_RUNNER" ]]; then
  echo "adb nao encontrado. Configure platform-tools antes de subir o emulador." >&2
  exit 1
fi

EXISTING_SERIAL="$(adb_find_emulator_by_avd "$SELECTED_AVD" || true)"
if [[ -n "$REQUESTED_SERIAL" ]]; then
  EXISTING_SERIAL="$REQUESTED_SERIAL"
fi

if [[ -n "$EXISTING_SERIAL" ]]; then
  if [[ "$FORCE_COLD_BOOT" == "1" || "$WIPE_DATA" == "1" ]]; then
    echo "[devkit] Reiniciando emulador existente para boot fresco: $EXISTING_SERIAL"
    "$ADB_RUNNER" -s "$EXISTING_SERIAL" emu kill >/dev/null 2>&1 || true
    DEADLINE=$((SECONDS + 45))
    while (( SECONDS < DEADLINE )); do
      if ! printf '%s\n' "$(adb_emulator_serials)" | grep -Fxq "$EXISTING_SERIAL"; then
        break
      fi
      sleep 2
    done
    sleep 5
  else
    echo "[devkit] Emulador ja em execucao para $SELECTED_AVD: $EXISTING_SERIAL"
    if [[ "$NO_BOOT_WAIT" != "1" ]]; then
      "$DEV_DIR/android_wait_for_boot.sh" --serial "$EXISTING_SERIAL" --timeout "$BOOT_TIMEOUT"
      "$DEV_DIR/check_android_emulator.sh" --avd "$SELECTED_AVD" --require-boot >/dev/null
    else
      "$DEV_DIR/check_android_emulator.sh" --avd "$SELECTED_AVD" >/dev/null
    fi
    printf '%s\n' "$EXISTING_SERIAL"
    exit 0
  fi
fi

mapfile -t SERIALS_BEFORE < <(adb_emulator_serials)

LOG_PATH="$DEVKIT_RUNTIME_DIR/android_emulator.log"
PID_PATH="$DEVKIT_RUNTIME_DIR/android_emulator.pid"
CMD_FILE="$DEVKIT_RUNTIME_DIR/android_emulator.command.txt"

EMULATOR_ARGS=(
  -avd "$SELECTED_AVD"
  -netdelay none
  -netspeed full
  -camera-back none
  -camera-front none
)

if [[ -n "$REQUESTED_PORT" ]]; then
  EMULATOR_ARGS+=(-port "$REQUESTED_PORT")
fi

if [[ "$HEADLESS" == "1" ]]; then
  EMULATOR_ARGS+=(-no-window -gpu swiftshader_indirect -no-audio)
fi

if [[ "$WIPE_DATA" == "1" ]]; then
  EMULATOR_ARGS+=(-wipe-data)
fi

if [[ "$FORCE_COLD_BOOT" == "1" || "$WIPE_DATA" == "1" ]]; then
  EMULATOR_ARGS+=(-no-snapshot-load -no-snapshot-save)
fi

printf '%q ' "$EMULATOR_RUNNER" "${EMULATOR_ARGS[@]}" > "$CMD_FILE"
printf '\n' >> "$CMD_FILE"

echo "[devkit] Subindo Android Emulator: avd=$SELECTED_AVD"
echo "[devkit] Log: $LOG_PATH"

if [[ "$DRY_RUN" == "1" ]]; then
  cat "$CMD_FILE"
  exit 0
fi

if have_cmd setsid; then
  setsid "$EMULATOR_RUNNER" "${EMULATOR_ARGS[@]}" < /dev/null >"$LOG_PATH" 2>&1 &
else
  nohup "$EMULATOR_RUNNER" "${EMULATOR_ARGS[@]}" < /dev/null >"$LOG_PATH" 2>&1 &
fi
EMULATOR_PID=$!
echo "$EMULATOR_PID" >"$PID_PATH"
disown "$EMULATOR_PID" 2>/dev/null || true

FOUND_SERIAL=""
DEADLINE=$((SECONDS + BOOT_TIMEOUT))
while (( SECONDS < DEADLINE )); do
  if [[ -n "$REQUESTED_SERIAL" ]]; then
    if printf '%s\n' "$(adb_emulator_serials)" | grep -Fxq "$REQUESTED_SERIAL"; then
      FOUND_SERIAL="$REQUESTED_SERIAL"
      break
    fi
  fi

  FOUND_SERIAL="$(adb_find_emulator_by_avd "$SELECTED_AVD" || true)"
  if [[ -n "$FOUND_SERIAL" ]]; then
    break
  fi

  while IFS= read -r candidate_serial; do
    [[ -n "$candidate_serial" ]] || continue
    if ! printf '%s\n' "${SERIALS_BEFORE[@]}" | grep -Fxq "$candidate_serial"; then
      FOUND_SERIAL="$candidate_serial"
      break
    fi
  done < <(adb_emulator_serials)

  if [[ -n "$FOUND_SERIAL" ]]; then
    break
  fi

  sleep 2
done

if [[ -z "$FOUND_SERIAL" ]]; then
  echo "O processo do emulator foi iniciado, mas nenhum serial adb apareceu a tempo. Consulte $LOG_PATH." >&2
  "$DEV_DIR/check_android_emulator.sh" --avd "$SELECTED_AVD" >/dev/null || true
  exit 1
fi

echo "[devkit] Serial do emulador: $FOUND_SERIAL"

if [[ "$NO_BOOT_WAIT" != "1" ]]; then
  "$DEV_DIR/android_wait_for_boot.sh" --serial "$FOUND_SERIAL" --timeout "$BOOT_TIMEOUT"
  "$DEV_DIR/check_android_emulator.sh" --avd "$SELECTED_AVD" --require-boot >/dev/null
else
  "$DEV_DIR/check_android_emulator.sh" --avd "$SELECTED_AVD" >/dev/null
fi

printf '%s\n' "$FOUND_SERIAL"
