#!/usr/bin/env bash

DEV_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$DEV_DIR/../.." && pwd)"
WEB_ROOT="$REPO_ROOT/web"
ANDROID_ROOT="$REPO_ROOT/android"
DEVKIT_RUNTIME_DIR="$REPO_ROOT/.tmp_online/devkit"

DEFAULT_BACKEND_HOST="${MESA_BACKEND_HOST:-127.0.0.1}"
DEFAULT_BACKEND_PORT="${MESA_BACKEND_PORT:-8000}"
DEFAULT_ANDROID_METRO_PORT="${ANDROID_METRO_PORT:-8081}"
DEFAULT_ANDROID_APP_ID="${ANDROID_APP_ID:-com.tarielia.inspetor}"
DEFAULT_ANDROID_EMULATOR_BOOT_TIMEOUT="${ANDROID_EMULATOR_BOOT_TIMEOUT:-300}"
DEFAULT_ANDROID_ADB_PROBE_TIMEOUT="${ANDROID_ADB_PROBE_TIMEOUT:-12}"

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

resolve_cmd() {
  command -v "$1" 2>/dev/null || true
}

run_with_timeout() {
  local timeout_seconds="${1:-$DEFAULT_ANDROID_ADB_PROBE_TIMEOUT}"
  shift || true

  if have_cmd timeout; then
    timeout "$timeout_seconds" "$@"
    return $?
  fi

  "$@"
}

resolve_web_python() {
  local candidates=(
    "${PYTHON_BIN:-}"
    "$WEB_ROOT/.venv-linux/bin/python"
    "$WEB_ROOT/.venv/bin/python"
    "$WEB_ROOT/venv/bin/python"
    "$REPO_ROOT/.venv-linux/bin/python"
    "$REPO_ROOT/.venv/bin/python"
    "$REPO_ROOT/venv/bin/python"
    "$WEB_ROOT/.venv-linux/Scripts/python.exe"
    "$WEB_ROOT/.venv/Scripts/python.exe"
    "$WEB_ROOT/venv/Scripts/python.exe"
    "$REPO_ROOT/.venv-linux/Scripts/python.exe"
    "$REPO_ROOT/.venv/Scripts/python.exe"
    "$REPO_ROOT/venv/Scripts/python.exe"
  )
  local candidate

  for candidate in "${candidates[@]}"; do
    if [[ -n "$candidate" && -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  if have_cmd python3; then
    printf '%s\n' "python3"
    return 0
  fi

  if have_cmd python; then
    printf '%s\n' "python"
    return 0
  fi

  echo "Python nao encontrado. Configure PYTHON_BIN ou crie uma venv em web/.venv-linux." >&2
  return 1
}

resolve_eas_runner() {
  if have_cmd eas; then
    resolve_cmd eas
    return 0
  fi

  if [[ -x "$ANDROID_ROOT/node_modules/.bin/eas" ]]; then
    printf '%s\n' "$ANDROID_ROOT/node_modules/.bin/eas"
    return 0
  fi

  return 1
}

resolve_android_sdk_root() {
  local candidates=(
    "${ANDROID_SDK_ROOT:-}"
    "${ANDROID_HOME:-}"
    "$HOME/.local/share/android-sdk"
    "$HOME/Android/Sdk"
    "$HOME/Android/sdk"
    "$HOME/.android/sdk"
  )
  local candidate

  for candidate in "${candidates[@]}"; do
    if [[ -n "$candidate" && -d "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

resolve_android_sdk_tool() {
  local tool_name="$1"
  local sdk_root="${2:-}"
  local candidates=()
  local candidate

  if have_cmd "$tool_name"; then
    resolve_cmd "$tool_name"
    return 0
  fi

  if [[ -z "$sdk_root" ]]; then
    sdk_root="$(resolve_android_sdk_root || true)"
  fi

  if [[ -z "$sdk_root" ]]; then
    return 1
  fi

  case "$tool_name" in
    adb)
      candidates=(
        "$sdk_root/platform-tools/adb"
        "$sdk_root/platform-tools/adb.exe"
      )
      ;;
    emulator)
      candidates=(
        "$sdk_root/emulator/emulator"
        "$sdk_root/emulator/emulator.exe"
      )
      ;;
    avdmanager|sdkmanager)
      candidates=(
        "$sdk_root/cmdline-tools/latest/bin/$tool_name"
        "$sdk_root/cmdline-tools/bin/$tool_name"
        "$sdk_root/tools/bin/$tool_name"
        "$sdk_root/cmdline-tools/latest/bin/$tool_name.bat"
        "$sdk_root/cmdline-tools/bin/$tool_name.bat"
        "$sdk_root/tools/bin/$tool_name.bat"
      )
      ;;
    *)
      candidates=(
        "$sdk_root/$tool_name"
      )
      ;;
  esac

  for candidate in "${candidates[@]}"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

resolve_adb_runner() {
  resolve_android_sdk_tool adb
}

resolve_emulator_runner() {
  resolve_android_sdk_tool emulator
}

resolve_avdmanager_runner() {
  resolve_android_sdk_tool avdmanager
}

resolve_sdkmanager_runner() {
  resolve_android_sdk_tool sdkmanager
}

resolve_expo_runner() {
  if have_cmd expo; then
    resolve_cmd expo
    return 0
  fi

  if [[ -x "$ANDROID_ROOT/node_modules/.bin/expo" ]]; then
    printf '%s\n' "$ANDROID_ROOT/node_modules/.bin/expo"
    return 0
  fi

  return 1
}

ensure_android_deps() {
  if [[ -d "$ANDROID_ROOT/node_modules" ]]; then
    return 0
  fi

  echo "[devkit] Instalando dependencias do Android..."
  (
    cd "$ANDROID_ROOT"
    npm install --no-fund --no-audit
  )
}

ensure_devkit_runtime_dir() {
  mkdir -p "$DEVKIT_RUNTIME_DIR"
}

curl_ok() {
  local url="$1"
  curl -fsS --max-time 3 "$url" >/dev/null 2>&1
}

curl_json_field() {
  local url="$1"
  local jq_expr="$2"

  if ! have_cmd curl; then
    return 1
  fi

  if ! have_cmd jq; then
    return 1
  fi

  curl -fsS --max-time 3 "$url" 2>/dev/null | jq -r "$jq_expr" 2>/dev/null
}

adb_device_count() {
  local adb_runner
  adb_runner="$(resolve_adb_runner || true)"

  if [[ -z "$adb_runner" ]]; then
    printf '%s\n' "0"
    return 0
  fi

  "$adb_runner" devices 2>/dev/null \
    | tail -n +2 \
    | awk 'NF > 0 && $2 == "device" {count += 1} END {print count + 0}'
}

adb_device_list() {
  local adb_runner
  adb_runner="$(resolve_adb_runner || true)"

  if [[ -z "$adb_runner" ]]; then
    return 0
  fi

  "$adb_runner" devices 2>/dev/null \
    | tail -n +2 \
    | awk 'NF > 0 && $2 == "device" {print $1}'
}

adb_device_list_with_state() {
  local adb_runner
  adb_runner="$(resolve_adb_runner || true)"

  if [[ -z "$adb_runner" ]]; then
    return 0
  fi

  "$adb_runner" devices 2>/dev/null \
    | tail -n +2 \
    | awk 'NF > 0 {print $1 "\t" $2}'
}

adb_attached_serials() {
  adb_device_list_with_state | awk -F '\t' 'NF > 0 {print $1}'
}

adb_emulator_serials() {
  adb_device_list_with_state \
    | awk -F '\t' '$1 ~ /^emulator-[0-9]+$/ {print $1}'
}

adb_running_emulator_serials() {
  adb_device_list_with_state \
    | awk -F '\t' '$1 ~ /^emulator-[0-9]+$/ && $2 == "device" {print $1}'
}

adb_is_emulator_serial() {
  local serial="${1:-}"
  [[ "$serial" =~ ^emulator-[0-9]+$ ]]
}

adb_running_avd_name() {
  local serial="${1:-}"
  local adb_runner

  adb_runner="$(resolve_adb_runner || true)"
  if [[ -z "$adb_runner" || -z "$serial" ]]; then
    return 1
  fi

  run_with_timeout "$DEFAULT_ANDROID_ADB_PROBE_TIMEOUT" "$adb_runner" -s "$serial" emu avd name 2>/dev/null \
    | tr -d '\r' \
    | awk 'NF > 0 && $0 != "OK" {print $0}' \
    | tail -n 1
}

adb_find_emulator_by_avd() {
  local target_avd="${1:-}"
  local serial
  local running_avd

  if [[ -z "$target_avd" ]]; then
    return 1
  fi

  while IFS= read -r serial; do
    [[ -n "$serial" ]] || continue
    running_avd="$(adb_running_avd_name "$serial" || true)"
    if [[ "$running_avd" == "$target_avd" ]]; then
      printf '%s\n' "$serial"
      return 0
    fi
  done < <(adb_running_emulator_serials)

  return 1
}

adb_select_single_device() {
  local preferred_serial="${1:-}"
  local device_list
  local device_count

  if [[ -n "$preferred_serial" ]]; then
    printf '%s\n' "$preferred_serial"
    return 0
  fi

  mapfile -t device_list < <(adb_device_list)
  device_count="${#device_list[@]}"

  if [[ "$device_count" -eq 1 ]]; then
    printf '%s\n' "${device_list[0]}"
    return 0
  fi

  return 1
}

adb_reverse_list() {
  local adb_runner

  adb_runner="$(resolve_adb_runner || true)"
  if [[ -z "$adb_runner" ]]; then
    return 0
  fi

  "$adb_runner" reverse --list 2>/dev/null || true
}

apply_adb_reverse() {
  local serial="${1:-}"
  shift || true
  local adb_runner
  local port

  adb_runner="$(resolve_adb_runner || true)"
  if [[ -z "$adb_runner" || -z "$serial" || "$#" -eq 0 ]]; then
    return 1
  fi

  for port in "$@"; do
    "$adb_runner" -s "$serial" reverse "tcp:$port" "tcp:$port" >/dev/null
  done
}

android_boot_status() {
  local serial="${1:-}"
  local prop_name="${2:-sys.boot_completed}"
  local adb_runner

  adb_runner="$(resolve_adb_runner || true)"
  if [[ -z "$adb_runner" || -z "$serial" ]]; then
    return 1
  fi

  run_with_timeout "$DEFAULT_ANDROID_ADB_PROBE_TIMEOUT" "$adb_runner" -s "$serial" shell getprop "$prop_name" 2>/dev/null \
    | tr -d '\r[:space:]'
}

android_service_list() {
  local serial="${1:-}"
  local adb_runner

  adb_runner="$(resolve_adb_runner || true)"
  if [[ -z "$adb_runner" || -z "$serial" ]]; then
    return 1
  fi

  run_with_timeout "$DEFAULT_ANDROID_ADB_PROBE_TIMEOUT" "$adb_runner" -s "$serial" shell service list 2>/dev/null | tr -d '\r'
}

android_has_service() {
  local serial="${1:-}"
  local service_name="${2:-}"
  local services

  if [[ -z "$serial" || -z "$service_name" ]]; then
    return 1
  fi

  services="$(android_service_list "$serial" || true)"
  [[ "$services" == *"$service_name:"* ]]
}

android_package_service_ready() {
  local serial="${1:-}"
  local adb_runner
  local output

  adb_runner="$(resolve_adb_runner || true)"
  if [[ -z "$adb_runner" || -z "$serial" ]]; then
    return 1
  fi

  output="$(
    run_with_timeout "$DEFAULT_ANDROID_ADB_PROBE_TIMEOUT" "$adb_runner" -s "$serial" shell cmd package resolve-activity --brief com.android.settings 2>/dev/null \
      | tr -d '\r'
  )"
  [[ "$output" == *"com.android.settings"* && "$output" == */* ]]
}

android_is_boot_completed() {
  local serial="${1:-}"
  local sys_boot
  local dev_boot
  local boot_anim

  if [[ -z "$serial" ]]; then
    return 1
  fi

  sys_boot="$(android_boot_status "$serial" "sys.boot_completed" || true)"
  dev_boot="$(android_boot_status "$serial" "dev.bootcomplete" || true)"
  boot_anim="$(android_boot_status "$serial" "init.svc.bootanim" || true)"

  if [[ "$sys_boot" == "1" && ( "$dev_boot" == "1" || -z "$dev_boot" ) ]]; then
    if [[ "$boot_anim" == "stopped" || -z "$boot_anim" ]]; then
      if android_package_service_ready "$serial"; then
        return 0
      fi
    fi
  fi

  if [[ "$sys_boot" == "1" && "$dev_boot" == "1" ]]; then
    if android_package_service_ready "$serial" && android_has_service "$serial" "activity_task"; then
      return 0
    fi
  fi

  return 1
}

list_android_avds() {
  local emulator_runner
  local avdmanager_runner

  emulator_runner="$(resolve_emulator_runner || true)"
  if [[ -n "$emulator_runner" ]]; then
    "$emulator_runner" -list-avds 2>/dev/null | awk 'NF > 0'
    return 0
  fi

  avdmanager_runner="$(resolve_avdmanager_runner || true)"
  if [[ -n "$avdmanager_runner" ]]; then
    "$avdmanager_runner" list avd 2>/dev/null \
      | awk '/^[[:space:]]+Name: / {sub(/^[[:space:]]+Name: /, ""); print}'
  fi
}

select_android_avd() {
  local requested_avd="${1:-${DEVKIT_ANDROID_AVD:-${ANDROID_EMULATOR_AVD:-}}}"
  local avd_name

  if [[ -n "$requested_avd" ]]; then
    printf '%s\n' "$requested_avd"
    return 0
  fi

  avd_name="$(list_android_avds | head -n 1 || true)"
  if [[ -n "$avd_name" ]]; then
    printf '%s\n' "$avd_name"
    return 0
  fi

  return 1
}

android_default_apk_path() {
  local candidates=(
    "$ANDROID_ROOT/android/app/build/outputs/apk/release/app-release.apk"
    "$ANDROID_ROOT/android/app/build/outputs/apk/debug/app-debug.apk"
  )
  local candidate

  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

resolve_android_apk_path() {
  local requested_path="${1:-}"

  if [[ -n "$requested_path" && -f "$requested_path" ]]; then
    printf '%s\n' "$requested_path"
    return 0
  fi

  android_default_apk_path
}

tool_status_detail() {
  local tool_name="$1"
  local detail="$2"
  printf '%-20s %-9s %s\n' "$tool_name" "$detail" ""
}
