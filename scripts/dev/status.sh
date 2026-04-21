#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

OUTPUT_MODE="table"
STRICT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      OUTPUT_MODE="json"
      shift
      ;;
    --strict)
      STRICT=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/status.sh [--json] [--strict]

EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

STRICT_FAILED=0

add_row() {
  local category="$1"
  local name="$2"
  local status="$3"
  local detail="$4"
  local required="$5"

  detail="${detail//$'\t'/ }"
  printf '%s\t%s\t%s\t%s\t%s\n' "$category" "$name" "$status" "$detail" "$required" >> "$TMP_FILE"

  if [[ "$STRICT" == "1" && "$required" == "1" ]]; then
    case "$status" in
      ok|ready|available)
        ;;
      *)
        STRICT_FAILED=1
        ;;
    esac
  fi
}

add_tool_row() {
  local name="$1"
  local required="$2"
  shift 2
  local detail="$*"
  local status="missing"

  if [[ -n "$detail" ]]; then
    status="ok"
  fi

  add_row "tool" "$name" "$status" "${detail:-nao encontrado}" "$required"
}

TMUX_PATH="$(resolve_cmd tmux)"
DIRENV_PATH="$(resolve_cmd direnv)"
UV_PATH="$(resolve_cmd uv)"
RUFF_PATH="$(resolve_cmd ruff)"
DOCKER_PATH="$(resolve_cmd docker)"
ADB_PATH="$(resolve_cmd adb)"
EMULATOR_PATH="$(resolve_emulator_runner || true)"
AVDMANAGER_PATH="$(resolve_avdmanager_runner || true)"
SDKMANAGER_PATH="$(resolve_sdkmanager_runner || true)"
ANDROID_SDK_ROOT_PATH="$(resolve_android_sdk_root || true)"
MAESTRO_PATH="$(resolve_cmd maestro)"
NODE_PATH="$(resolve_cmd node)"
NPM_PATH="$(resolve_cmd npm)"
PYTHON_PATH="$(resolve_web_python || true)"
GIT_PATH="$(resolve_cmd git)"
CURL_PATH="$(resolve_cmd curl)"
JQ_PATH="$(resolve_cmd jq)"
EAS_PATH="$(resolve_eas_runner || true)"
EXPO_PATH="$(resolve_expo_runner || true)"

add_tool_row "python" 1 "$PYTHON_PATH"
add_tool_row "node" 1 "$NODE_PATH"
add_tool_row "npm" 1 "$NPM_PATH"
add_tool_row "git" 1 "$GIT_PATH"
add_tool_row "curl" 1 "$CURL_PATH"
add_tool_row "jq" 0 "$JQ_PATH"
add_tool_row "ruff" 0 "$RUFF_PATH"
add_tool_row "adb" 1 "$ADB_PATH"
add_tool_row "emulator" 0 "$EMULATOR_PATH"
add_tool_row "avdmanager" 0 "$AVDMANAGER_PATH"
add_tool_row "sdkmanager" 0 "$SDKMANAGER_PATH"
add_tool_row "maestro" 0 "$MAESTRO_PATH"
add_tool_row "expo" 0 "$EXPO_PATH"
add_tool_row "eas" 0 "$EAS_PATH"
add_tool_row "tmux" 0 "$TMUX_PATH"
add_tool_row "direnv" 0 "$DIRENV_PATH"
add_tool_row "uv" 0 "$UV_PATH"
add_tool_row "docker" 0 "$DOCKER_PATH"

BACKEND_READY_URL="http://$DEFAULT_BACKEND_HOST:$DEFAULT_BACKEND_PORT/ready"
REVIEWDESK_LOGIN_URL="http://$DEFAULT_BACKEND_HOST:$DEFAULT_BACKEND_PORT/revisao/login"

if curl_ok "$BACKEND_READY_URL"; then
  BACKEND_STATUS_DETAIL="GET $BACKEND_READY_URL"
  if [[ -n "$JQ_PATH" ]]; then
    READY_STATUS="$(curl_json_field "$BACKEND_READY_URL" '.status // "ok"' || true)"
    READY_BACKEND="$(curl_json_field "$BACKEND_READY_URL" '.revisor_realtime_backend // empty' || true)"
    if [[ -n "$READY_STATUS" || -n "$READY_BACKEND" ]]; then
      BACKEND_STATUS_DETAIL="status=${READY_STATUS:-ok}${READY_BACKEND:+ backend=$READY_BACKEND}"
    fi
  fi
  add_row "service" "backend_ready" "ready" "$BACKEND_STATUS_DETAIL" 1
else
  add_row "service" "backend_ready" "down" "$BACKEND_READY_URL" 1
fi

if curl_ok "$REVIEWDESK_LOGIN_URL"; then
  add_row "service" "reviewdesk_login" "ready" "GET $REVIEWDESK_LOGIN_URL" 1
else
  add_row "service" "reviewdesk_login" "down" "$REVIEWDESK_LOGIN_URL" 1
fi

ANDROID_DEVICE_COUNT="$(adb_device_count)"
if [[ "$ANDROID_DEVICE_COUNT" -gt 0 ]]; then
  DEVICE_LIST="$(adb_device_list | paste -sd ',' -)"
  add_row "android" "adb_devices" "available" "${ANDROID_DEVICE_COUNT} dispositivo(s): ${DEVICE_LIST}" 0
else
  add_row "android" "adb_devices" "warn" "nenhum dispositivo conectado" 0
fi

if [[ -n "$ANDROID_SDK_ROOT_PATH" ]]; then
  add_row "android" "android_sdk_root" "available" "$ANDROID_SDK_ROOT_PATH" 0
else
  add_row "android" "android_sdk_root" "warn" "SDK Android nao encontrado" 0
fi

mapfile -t AVAILABLE_AVDS < <(list_android_avds)
SELECTED_AVD="$(select_android_avd || true)"
if [[ "${#AVAILABLE_AVDS[@]}" -gt 0 ]]; then
  add_row "android" "android_avds" "available" "$(IFS=,; echo "${AVAILABLE_AVDS[*]}")" 0
else
  add_row "android" "android_avds" "warn" "nenhum AVD configurado" 0
fi

if [[ -n "$SELECTED_AVD" ]]; then
  add_row "android" "android_selected_avd" "available" "$SELECTED_AVD" 0
else
  add_row "android" "android_selected_avd" "warn" "nenhum AVD selecionado" 0
fi

SELECTED_EMULATOR_SERIAL=""
if [[ -n "$SELECTED_AVD" ]]; then
  SELECTED_EMULATOR_SERIAL="$(adb_find_emulator_by_avd "$SELECTED_AVD" || true)"
fi
if [[ -z "$SELECTED_EMULATOR_SERIAL" ]]; then
  mapfile -t RUNNING_EMULATORS < <(adb_running_emulator_serials)
  if [[ "${#RUNNING_EMULATORS[@]}" -eq 1 ]]; then
    SELECTED_EMULATOR_SERIAL="${RUNNING_EMULATORS[0]}"
  fi
fi

if [[ -n "$SELECTED_EMULATOR_SERIAL" ]]; then
  RUNNING_AVD_NAME="$(adb_running_avd_name "$SELECTED_EMULATOR_SERIAL" || true)"
  add_row "android" "android_emulator_running" "ready" "serial=$SELECTED_EMULATOR_SERIAL avd=${RUNNING_AVD_NAME:-unknown}" 0
  if android_is_boot_completed "$SELECTED_EMULATOR_SERIAL"; then
    add_row "android" "android_emulator_boot" "ready" "$SELECTED_EMULATOR_SERIAL boot completo" 0
  else
    add_row "android" "android_emulator_boot" "warn" "$SELECTED_EMULATOR_SERIAL ainda inicializando" 0
  fi
else
  add_row "android" "android_emulator_running" "warn" "nenhum emulador em execucao" 0
  add_row "android" "android_emulator_boot" "warn" "nenhum emulador pronto" 0
fi

ADB_REVERSE_LIST="$(adb_reverse_list | paste -sd ';' -)"
if [[ -n "$ADB_REVERSE_LIST" ]]; then
  add_row "android" "adb_reverse" "available" "$ADB_REVERSE_LIST" 0
else
  add_row "android" "adb_reverse" "warn" "nenhum adb reverse ativo" 0
fi

if [[ -f "$ANDROID_ROOT/.env" ]]; then
  add_row "android" "android_env" "available" "$ANDROID_ROOT/.env" 0
else
  add_row "android" "android_env" "warn" "android/.env ausente" 0
fi

ANDROID_BASELINE_STATE_FILE="$DEVKIT_RUNTIME_DIR/android_baseline_status.json"
if [[ -f "$ANDROID_BASELINE_STATE_FILE" ]]; then
  BASELINE_ROW="$(
    python3 - "$ANDROID_BASELINE_STATE_FILE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
mandatory = payload.get("mandatoryChecks", [])
optional = payload.get("optionalChecks", [])
mandatory_total = len(mandatory)
mandatory_ok = sum(1 for item in mandatory if item.get("status") == "ok")
requested_optional = [
    item["name"]
    for item in optional
    if item.get("requested") and item.get("status") == "ok"
]
failed_checks = [
    item["name"]
    for item in mandatory + optional
    if item.get("status") == "fail"
]
detail_parts = [
    payload.get("baseline", "android-baseline"),
    f'last={payload.get("generatedAt", "unknown")}',
    f'mandatory={mandatory_ok}/{mandatory_total}',
]
if requested_optional:
    detail_parts.append(f'optional={",".join(requested_optional)}')
if failed_checks:
    detail_parts.append(f'fail={",".join(failed_checks)}')
print(f'{payload.get("status", "warn")}\t{" ".join(detail_parts)}')
PY
  )"
  BASELINE_STATUS="${BASELINE_ROW%%$'\t'*}"
  BASELINE_DETAIL="${BASELINE_ROW#*$'\t'}"
  add_row "android" "android_baseline" "$BASELINE_STATUS" "$BASELINE_DETAIL" 0
else
  add_row "android" "android_baseline" "warn" "nenhuma baseline Android registrada; rode scripts/dev/check_android.sh" 0
fi

ANDROID_EMULATOR_AUDIT_STATE_FILE="$DEVKIT_RUNTIME_DIR/android_emulator_status.json"
if [[ -f "$ANDROID_EMULATOR_AUDIT_STATE_FILE" ]]; then
  EMULATOR_AUDIT_ROW="$(
    python3 - "$ANDROID_EMULATOR_AUDIT_STATE_FILE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
status = payload.get("status", "warn")
detail = payload.get("detail", "sem detalhe")
generated_at = payload.get("generatedAt", "unknown")
selected_avd = payload.get("selectedAvd", "")
selected_serial = payload.get("selectedSerial", "")
parts = [detail, f"last={generated_at}"]
if selected_avd:
    parts.append(f"avd={selected_avd}")
if selected_serial:
    parts.append(f"serial={selected_serial}")
print(f"{status}\t{' '.join(parts)}")
PY
  )"
  EMULATOR_AUDIT_STATUS="${EMULATOR_AUDIT_ROW%%$'\t'*}"
  EMULATOR_AUDIT_DETAIL="${EMULATOR_AUDIT_ROW#*$'\t'}"
  add_row "android" "android_emulator_audit" "$EMULATOR_AUDIT_STATUS" "$EMULATOR_AUDIT_DETAIL" 0
else
  add_row "android" "android_emulator_audit" "warn" "nenhuma auditoria de emulador registrada; rode scripts/dev/check_android_emulator.sh" 0
fi

ANDROID_EMULATOR_LANE_STATE_FILE="$DEVKIT_RUNTIME_DIR/android_emulator_lane_status.json"
if [[ -f "$ANDROID_EMULATOR_LANE_STATE_FILE" ]]; then
  EMULATOR_LANE_ROW="$(
    python3 - "$ANDROID_EMULATOR_LANE_STATE_FILE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
status = payload.get("status", "warn")
mode = payload.get("mode", "unknown")
detail = payload.get("detail", "sem detalhe")
generated_at = payload.get("generatedAt", "unknown")
serial = payload.get("serial", "")
parts = [f"mode={mode}", detail, f"last={generated_at}"]
if serial:
    parts.append(f"serial={serial}")
print(f"{status}\t{' '.join(parts)}")
PY
  )"
  EMULATOR_LANE_STATUS="${EMULATOR_LANE_ROW%%$'\t'*}"
  EMULATOR_LANE_DETAIL="${EMULATOR_LANE_ROW#*$'\t'}"
  add_row "android" "android_emulator_lane" "$EMULATOR_LANE_STATUS" "$EMULATOR_LANE_DETAIL" 0
else
  add_row "android" "android_emulator_lane" "skipped" "lane ainda nao executada; rode scripts/dev/run_android_emulator_stack.sh --mode boot" 0
fi

ANDROID_MOBILE_PILOT_STATE_FILE="$DEVKIT_RUNTIME_DIR/mobile_pilot_lane_status.json"
if [[ -f "$ANDROID_MOBILE_PILOT_STATE_FILE" ]]; then
  MOBILE_PILOT_ROW="$(
    python3 - "$ANDROID_MOBILE_PILOT_STATE_FILE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
status = payload.get("status", "warn")
detail = payload.get("detail", "sem detalhe")
generated_at = payload.get("generatedAt", "unknown")
result = payload.get("result", "")
device = payload.get("device", "")
parts = [detail, f"last={generated_at}"]
if result:
    parts.append(f"result={result}")
if device:
    parts.append(f"device={device}")
print(f"{status}\t{' '.join(parts)}")
PY
  )"
  MOBILE_PILOT_STATUS="${MOBILE_PILOT_ROW%%$'\t'*}"
  MOBILE_PILOT_DETAIL="${MOBILE_PILOT_ROW#*$'\t'}"
  add_row "android" "android_mobile_acceptance" "$MOBILE_PILOT_STATUS" "$MOBILE_PILOT_DETAIL" 0
else
  add_row "android" "android_mobile_acceptance" "skipped" "lane oficial ainda nao executada; rode make smoke-mobile" 0
fi

ANDROID_MAESTRO_STATE_FILE="$DEVKIT_RUNTIME_DIR/android_maestro_smoke_status.json"
MAESTRO_STATUS_ROW=""
if [[ -f "$ANDROID_MAESTRO_STATE_FILE" ]]; then
  MAESTRO_STATUS_ROW="$(
    python3 - "$ANDROID_MAESTRO_STATE_FILE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
mode = payload.get("mode")
if mode not in {"maestro-smoke", "maestro-suite"}:
    print("")
    raise SystemExit(0)
status = payload.get("status", "warn")
detail = payload.get("detail", "sem detalhe")
generated_at = payload.get("generatedAt", "unknown")
serial = payload.get("serial", "")
parts = [f"mode={mode}", detail, f"last={generated_at}"]
if serial:
    parts.append(f"serial={serial}")
print(f"{status}\t{' '.join(parts)}")
PY
  )"
fi

if [[ -z "$MAESTRO_STATUS_ROW" && -f "$ANDROID_BASELINE_STATE_FILE" ]]; then
  MAESTRO_STATUS_ROW="$(
    python3 - "$ANDROID_BASELINE_STATE_FILE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
optional = payload.get("optionalChecks", [])
target = None
for item in optional:
    if item.get("name") == "maestro:smoke":
        target = item
        break

if not target:
    print("skipped\tnao executado")
    raise SystemExit(0)

status = target.get("status", "warn")
detail = target.get("detail", "sem detalhe")
requested = target.get("requested", False)
if not requested:
    print("skipped\tbaseline device-less")
else:
    print(f"{status}\t{detail}")
PY
  )"
fi

if [[ -n "$MAESTRO_STATUS_ROW" ]]; then
  MAESTRO_STATUS="${MAESTRO_STATUS_ROW%%$'\t'*}"
  MAESTRO_DETAIL="${MAESTRO_STATUS_ROW#*$'\t'}"
  if [[ -f "$ANDROID_MOBILE_PILOT_STATE_FILE" ]]; then
    MAESTRO_STATUS="stale"
    MAESTRO_DETAIL="runner auxiliar legado; consulte android_mobile_acceptance para a lane oficial. $MAESTRO_DETAIL"
  fi
  add_row "android" "android_maestro_smoke" "$MAESTRO_STATUS" "$MAESTRO_DETAIL" 0
else
  add_row "android" "android_maestro_smoke" "skipped" "nao executado" 0
fi

if [[ "$OUTPUT_MODE" == "json" ]]; then
  python3 - "$TMP_FILE" "$REPO_ROOT" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
workspace = pathlib.Path(sys.argv[2])
rows = []
for raw_line in path.read_text(encoding="utf-8").splitlines():
    category, name, status, detail, required = raw_line.split("\t", 4)
    rows.append(
        {
            "category": category,
            "name": name,
            "status": status,
            "detail": detail,
            "required_in_strict": required == "1",
        }
    )

payload = {
    "workspace": str(workspace),
    "rows": rows,
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY
else
  for category in tool service android; do
    echo "[$category]"
    printf '%-20s %-9s %s\n' "item" "status" "detail"
    while IFS=$'\t' read -r row_category row_name row_status row_detail row_required; do
      if [[ "$row_category" != "$category" ]]; then
        continue
      fi
      printf '%-20s %-9s %s\n' "$row_name" "$row_status" "$row_detail"
    done < "$TMP_FILE"
    echo
  done
fi

if [[ "$STRICT_FAILED" == "1" ]]; then
  exit 1
fi
