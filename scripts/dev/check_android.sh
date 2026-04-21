#!/usr/bin/env bash
set -uo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

WITH_FORMAT=0
WITH_MAESTRO_SMOKE=0
WITH_EMULATOR_LANE=0
EMULATOR_MODE="boot"
EMULATOR_HEADLESS=0
EMULATOR_APK_PATH=""
OUTPUT_MODE="table"
OVERALL_STATUS="ok"
TMP_FILE="$(mktemp)"
STATE_FILE=""

cleanup() {
  rm -f "$TMP_FILE"
}

trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-format)
      WITH_FORMAT=1
      shift
      ;;
    --with-maestro-smoke)
      WITH_MAESTRO_SMOKE=1
      shift
      ;;
    --with-emulator-lane)
      WITH_EMULATOR_LANE=1
      shift
      ;;
    --emulator-mode)
      EMULATOR_MODE="${2:?Valor ausente para --emulator-mode}"
      shift 2
      ;;
    --emulator-headless)
      EMULATOR_HEADLESS=1
      shift
      ;;
    --emulator-apk)
      EMULATOR_APK_PATH="${2:?Valor ausente para --emulator-apk}"
      shift 2
      ;;
    --json)
      OUTPUT_MODE="json"
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/check_android.sh [--with-format] [--with-emulator-lane] [--emulator-mode boot|metro|dev|preview|apk|maestro-smoke|maestro-suite] [--emulator-headless] [--emulator-apk <caminho>] [--with-maestro-smoke] [--json]

Baseline oficial:
  - typecheck
  - lint
  - test:baseline

Checks opcionais:
  - format:check
  - android:emulator
  - maestro:smoke (depende de device conectado)
EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

ensure_android_deps
ensure_devkit_runtime_dir

record_check() {
  local scope="$1"
  local name="$2"
  local required="$3"
  local requested="$4"
  local status="$5"
  local detail="$6"

  detail="${detail//$'\t'/ }"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$scope" "$name" "$required" "$requested" "$status" "$detail" >> "$TMP_FILE"
}

run_check() {
  local scope="$1"
  local name="$2"
  local required="$3"
  local requested="$4"
  shift 4

  if "$@"; then
    record_check "$scope" "$name" "$required" "$requested" "ok" "ok"
    return 0
  fi

  OVERALL_STATUS="fail"
  record_check "$scope" "$name" "$required" "$requested" "fail" "falhou"
  return 1
}

print_table() {
  for scope in mandatory optional; do
    echo "[$scope]"
    printf '%-20s %-9s %-9s %s\n' "check" "status" "requested" "detail"
    while IFS=$'\t' read -r row_scope row_name row_required row_requested row_status row_detail; do
      if [[ "$row_scope" != "$scope" ]]; then
        continue
      fi
      printf '%-20s %-9s %-9s %s\n' "$row_name" "$row_status" "$row_requested" "$row_detail"
    done < "$TMP_FILE"
    echo
  done
}

echo "[devkit] Android baseline oficial: device-less"

echo "[devkit] Android check: typecheck"
run_check "mandatory" "typecheck" 1 1 bash -lc "cd \"$ANDROID_ROOT\" && npm run typecheck" || true

echo "[devkit] Android check: lint"
run_check "mandatory" "lint" 1 1 bash -lc "cd \"$ANDROID_ROOT\" && npm run lint" || true

echo "[devkit] Android check: test:baseline"
run_check "mandatory" "test:baseline" 1 1 bash -lc "cd \"$ANDROID_ROOT\" && npm run test:baseline" || true

if [[ "$WITH_FORMAT" == "1" ]]; then
  echo "[devkit] Android check: format:check"
  run_check "optional" "format:check" 0 1 bash -lc "cd \"$ANDROID_ROOT\" && npm run format:check" || true
else
  record_check "optional" "format:check" 0 0 "skipped" "nao solicitado"
fi

if [[ "$WITH_EMULATOR_LANE" == "1" ]]; then
  echo "[devkit] Android check: emulator lane ($EMULATOR_MODE)"
  EMULATOR_ARGS=(--mode "$EMULATOR_MODE")
  if [[ "$EMULATOR_HEADLESS" == "1" ]]; then
    EMULATOR_ARGS+=(--headless)
  fi
  if [[ -n "$EMULATOR_APK_PATH" ]]; then
    EMULATOR_ARGS+=(--apk "$EMULATOR_APK_PATH")
  fi
  case "$EMULATOR_MODE" in
    dev|preview|apk|maestro-smoke|maestro-suite)
      EMULATOR_ARGS+=(--with-api)
      ;;
  esac
  if "$DEV_DIR/run_android_emulator_stack.sh" "${EMULATOR_ARGS[@]}"; then
    record_check "optional" "android:emulator" 0 1 "ok" "mode=$EMULATOR_MODE"
  else
    OVERALL_STATUS="fail"
    record_check "optional" "android:emulator" 0 1 "fail" "mode=$EMULATOR_MODE"
  fi
else
  record_check "optional" "android:emulator" 0 0 "skipped" "nao solicitado"
fi

if [[ "$WITH_MAESTRO_SMOKE" == "1" ]]; then
  DEVICE_COUNT="$(adb_device_count)"
  if [[ "$DEVICE_COUNT" -eq 0 ]]; then
    OVERALL_STATUS="fail"
    record_check "optional" "maestro:smoke" 0 1 "fail" "nenhum dispositivo adb conectado"
  else
    echo "[devkit] Android check: maestro:smoke"
    run_check "optional" "maestro:smoke" 0 1 "$DEV_DIR/run_android_stack.sh" --mode maestro-smoke --with-api || true
  fi
else
  record_check "optional" "maestro:smoke" 0 0 "skipped" "baseline device-less"
fi

STATE_FILE="$DEVKIT_RUNTIME_DIR/android_baseline_status.json"
JSON_PAYLOAD="$(python3 - "$TMP_FILE" "$STATE_FILE" "$REPO_ROOT" "$OVERALL_STATUS" <<'PY'
import json
import pathlib
import sys
from datetime import datetime

rows_path = pathlib.Path(sys.argv[1])
state_path = pathlib.Path(sys.argv[2])
workspace = pathlib.Path(sys.argv[3])
overall_status = sys.argv[4]

mandatory = []
optional = []

for raw_line in rows_path.read_text(encoding="utf-8").splitlines():
    scope, name, required, requested, status, detail = raw_line.split("\t", 5)
    item = {
        "name": name,
        "required": required == "1",
        "requested": requested == "1",
        "status": status,
        "detail": detail,
    }
    if scope == "mandatory":
        mandatory.append(item)
    else:
        optional.append(item)

payload = {
    "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
    "workspace": str(workspace),
    "baseline": "android-stable-device-less",
    "status": overall_status,
    "mandatoryChecks": mandatory,
    "optionalChecks": optional,
}

state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY
)"

if [[ "$OUTPUT_MODE" == "json" ]]; then
  printf '%s\n' "$JSON_PAYLOAD"
else
  print_table
  echo "[devkit] Android baseline status file: $STATE_FILE"
fi

if [[ "$OVERALL_STATUS" == "ok" ]]; then
  echo "[devkit] Android check: OK"
  exit 0
fi

echo "[devkit] Android check: FAIL" >&2
exit 1
