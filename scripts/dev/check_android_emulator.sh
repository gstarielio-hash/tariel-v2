#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

OUTPUT_MODE="table"
REQUIRE_BOOT=0
REQUESTED_AVD=""
STATE_FILE=""
TMP_FILE="$(mktemp)"

cleanup() {
  rm -f "$TMP_FILE"
}

trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --avd)
      REQUESTED_AVD="${2:?Valor ausente para --avd}"
      shift 2
      ;;
    --require-boot)
      REQUIRE_BOOT=1
      shift
      ;;
    --json)
      OUTPUT_MODE="json"
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/check_android_emulator.sh [--avd <nome>] [--require-boot] [--json]

Audita a capacidade real da lane Android Emulator no Linux:
  - SDK Android
  - emulator / adb / avdmanager / sdkmanager
  - AVDs disponiveis
  - emulador em execucao
  - boot completo
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
STATE_FILE="$DEVKIT_RUNTIME_DIR/android_emulator_status.json"

add_row() {
  local category="$1"
  local name="$2"
  local status="$3"
  local detail="$4"

  detail="${detail//$'\t'/ }"
  printf '%s\t%s\t%s\t%s\n' "$category" "$name" "$status" "$detail" >> "$TMP_FILE"
}

resolve_android_studio_path() {
  local candidates=(
    "$HOME/android-studio/bin/studio.sh"
    "/opt/android-studio/bin/studio.sh"
    "$HOME/.local/share/JetBrains/Toolbox/apps/AndroidStudio"
    "/snap/bin/android-studio"
  )
  local candidate

  for candidate in "${candidates[@]}"; do
    if [[ -e "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

ANDROID_STUDIO_PATH="$(resolve_android_studio_path || true)"
ANDROID_SDK_ROOT_PATH="$(resolve_android_sdk_root || true)"
ADB_RUNNER="$(resolve_adb_runner || true)"
EMULATOR_RUNNER="$(resolve_emulator_runner || true)"
AVDMANAGER_RUNNER="$(resolve_avdmanager_runner || true)"
SDKMANAGER_RUNNER="$(resolve_sdkmanager_runner || true)"

if [[ -n "$ANDROID_STUDIO_PATH" ]]; then
  add_row "host" "android_studio" "ok" "$ANDROID_STUDIO_PATH"
else
  add_row "host" "android_studio" "warn" "nao encontrado; SDK pode ter sido instalado sem Android Studio"
fi

if [[ -n "${ANDROID_HOME:-}" ]]; then
  add_row "host" "android_home_env" "ok" "${ANDROID_HOME}"
else
  add_row "host" "android_home_env" "warn" "ANDROID_HOME nao definido"
fi

if [[ -n "${ANDROID_SDK_ROOT:-}" ]]; then
  add_row "host" "android_sdk_root_env" "ok" "${ANDROID_SDK_ROOT}"
else
  add_row "host" "android_sdk_root_env" "warn" "ANDROID_SDK_ROOT nao definido"
fi

if [[ -n "$ANDROID_SDK_ROOT_PATH" ]]; then
  add_row "host" "android_sdk_root" "ok" "$ANDROID_SDK_ROOT_PATH"
else
  add_row "host" "android_sdk_root" "fail" "SDK Android nao encontrado"
fi

if [[ -e /dev/kvm ]]; then
  if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    add_row "host" "kvm" "ok" "/dev/kvm presente com acesso de leitura/escrita"
  else
    add_row "host" "kvm" "warn" "/dev/kvm presente sem acesso completo"
  fi
else
  add_row "host" "kvm" "warn" "/dev/kvm ausente"
fi

if [[ -n "$ADB_RUNNER" ]]; then
  add_row "tool" "adb" "ok" "$ADB_RUNNER"
else
  add_row "tool" "adb" "fail" "adb nao encontrado"
fi

if [[ -n "$EMULATOR_RUNNER" ]]; then
  add_row "tool" "emulator" "ok" "$EMULATOR_RUNNER"
else
  add_row "tool" "emulator" "fail" "emulator nao encontrado"
fi

if [[ -n "$AVDMANAGER_RUNNER" ]]; then
  add_row "tool" "avdmanager" "ok" "$AVDMANAGER_RUNNER"
else
  add_row "tool" "avdmanager" "fail" "avdmanager nao encontrado"
fi

if [[ -n "$SDKMANAGER_RUNNER" ]]; then
  add_row "tool" "sdkmanager" "ok" "$SDKMANAGER_RUNNER"
else
  add_row "tool" "sdkmanager" "fail" "sdkmanager nao encontrado"
fi

mapfile -t AVAILABLE_AVDS < <(list_android_avds)
SELECTED_AVD="$(select_android_avd "$REQUESTED_AVD" || true)"
AVD_FOUND=0

if [[ "${#AVAILABLE_AVDS[@]}" -gt 0 ]]; then
  add_row "emulator" "available_avds" "ok" "$(IFS=,; echo "${AVAILABLE_AVDS[*]}")"
else
  add_row "emulator" "available_avds" "fail" "nenhum AVD encontrado"
fi

if [[ -n "$SELECTED_AVD" ]]; then
  if printf '%s\n' "${AVAILABLE_AVDS[@]}" | grep -Fxq "$SELECTED_AVD"; then
    AVD_FOUND=1
    add_row "emulator" "selected_avd" "ok" "$SELECTED_AVD"
  else
    add_row "emulator" "selected_avd" "fail" "$SELECTED_AVD nao existe no host"
  fi
else
  add_row "emulator" "selected_avd" "fail" "nenhum AVD selecionado"
fi

RUNNING_SERIALS=()
RUNNING_DETAILS=()
SELECTED_SERIAL=""
BOOT_COMPLETED=0

while IFS= read -r serial; do
  [[ -n "$serial" ]] || continue
  RUNNING_SERIALS+=("$serial")
  running_avd="$(adb_running_avd_name "$serial" || true)"
  if android_is_boot_completed "$serial"; then
    RUNNING_DETAILS+=("$serial:${running_avd:-unknown}:booted")
  else
    RUNNING_DETAILS+=("$serial:${running_avd:-unknown}:booting")
  fi
done < <(adb_emulator_serials)

if [[ -n "$SELECTED_AVD" ]]; then
  SELECTED_SERIAL="$(adb_find_emulator_by_avd "$SELECTED_AVD" || true)"
fi

if [[ -z "$SELECTED_SERIAL" && "${#RUNNING_SERIALS[@]}" -eq 1 ]]; then
  SELECTED_SERIAL="${RUNNING_SERIALS[0]}"
fi

if [[ "${#RUNNING_SERIALS[@]}" -gt 0 ]]; then
  add_row "emulator" "running_emulators" "ok" "$(IFS=,; echo "${RUNNING_DETAILS[*]}")"
else
  add_row "emulator" "running_emulators" "warn" "nenhum emulador em execucao"
fi

if [[ -n "$SELECTED_SERIAL" ]]; then
  add_row "emulator" "selected_serial" "ok" "$SELECTED_SERIAL"
else
  add_row "emulator" "selected_serial" "warn" "nenhum serial de emulador resolvido"
fi

if [[ -n "$SELECTED_SERIAL" && "$(android_is_boot_completed "$SELECTED_SERIAL" && echo 1 || echo 0)" == "1" ]]; then
  BOOT_COMPLETED=1
  add_row "emulator" "boot_completed" "ok" "$SELECTED_SERIAL boot completo"
elif [[ -n "$SELECTED_SERIAL" ]]; then
  add_row "emulator" "boot_completed" "warn" "$SELECTED_SERIAL ainda nao concluiu o boot"
else
  add_row "emulator" "boot_completed" "warn" "sem emulador selecionado"
fi

OVERALL_STATUS="ok"
OVERALL_DETAIL="lane pronta para uso"

if [[ -z "$ANDROID_SDK_ROOT_PATH" || -z "$ADB_RUNNER" || -z "$EMULATOR_RUNNER" || -z "$AVDMANAGER_RUNNER" || -z "$SDKMANAGER_RUNNER" ]]; then
  OVERALL_STATUS="fail"
  OVERALL_DETAIL="toolchain Android incompleto no host"
elif [[ "${#AVAILABLE_AVDS[@]}" -eq 0 || "$AVD_FOUND" != "1" ]]; then
  OVERALL_STATUS="fail"
  OVERALL_DETAIL="nenhum AVD utilizavel configurado"
elif [[ "$REQUIRE_BOOT" == "1" && -z "$SELECTED_SERIAL" ]]; then
  OVERALL_STATUS="fail"
  OVERALL_DETAIL="nenhum emulador do AVD selecionado esta em execucao"
elif [[ "$REQUIRE_BOOT" == "1" && "$BOOT_COMPLETED" != "1" ]]; then
  OVERALL_STATUS="fail"
  OVERALL_DETAIL="emulador encontrado, mas o boot ainda nao concluiu"
fi

JSON_PAYLOAD="$(python3 - "$TMP_FILE" "$STATE_FILE" "$REPO_ROOT" "$OVERALL_STATUS" "$OVERALL_DETAIL" "$REQUIRE_BOOT" "$SELECTED_AVD" "$SELECTED_SERIAL" "$ANDROID_STUDIO_PATH" "$ANDROID_SDK_ROOT_PATH" <<'PY'
import json
import pathlib
import sys
from datetime import datetime

rows_path = pathlib.Path(sys.argv[1])
state_path = pathlib.Path(sys.argv[2])
workspace = pathlib.Path(sys.argv[3])
overall_status = sys.argv[4]
overall_detail = sys.argv[5]
require_boot = sys.argv[6] == "1"
selected_avd = sys.argv[7]
selected_serial = sys.argv[8]
android_studio_path = sys.argv[9]
android_sdk_root = sys.argv[10]

rows = []
grouped = {"host": [], "tool": [], "emulator": []}
for raw_line in rows_path.read_text(encoding="utf-8").splitlines():
    category, name, status, detail = raw_line.split("\t", 3)
    row = {
        "category": category,
        "name": name,
        "status": status,
        "detail": detail,
    }
    rows.append(row)
    grouped.setdefault(category, []).append(row)

payload = {
    "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
    "workspace": str(workspace),
    "status": overall_status,
    "detail": overall_detail,
    "requireBoot": require_boot,
    "selectedAvd": selected_avd,
    "selectedSerial": selected_serial,
    "androidStudioPath": android_studio_path,
    "androidSdkRoot": android_sdk_root,
    "rows": rows,
    "groups": grouped,
}

state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY
)"

if [[ "$OUTPUT_MODE" == "json" ]]; then
  printf '%s\n' "$JSON_PAYLOAD"
else
  for category in host tool emulator; do
    echo "[$category]"
    printf '%-20s %-9s %s\n' "item" "status" "detail"
    while IFS=$'\t' read -r row_category row_name row_status row_detail; do
      if [[ "$row_category" != "$category" ]]; then
        continue
      fi
      printf '%-20s %-9s %s\n' "$row_name" "$row_status" "$row_detail"
    done < "$TMP_FILE"
    echo
  done
  echo "[devkit] Android emulator status file: $STATE_FILE"
  echo "[devkit] Android emulator audit: $OVERALL_STATUS ($OVERALL_DETAIL)"
fi

if [[ "$OVERALL_STATUS" == "ok" ]]; then
  exit 0
fi

exit 1
