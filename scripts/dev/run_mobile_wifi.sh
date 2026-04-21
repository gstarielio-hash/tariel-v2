#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

METRO_PORT="$DEFAULT_ANDROID_METRO_PORT"
BACKEND_PORT="$DEFAULT_BACKEND_PORT"
APP_ID="$DEFAULT_ANDROID_APP_ID"
REQUESTED_SERIAL="${ANDROID_SERIAL:-}"
NO_LAUNCH=0
SKIP_API=0
EXPO_LOG_PATH="$ANDROID_ROOT/expo-mobile.log"
EXPO_PID_PATH="$ANDROID_ROOT/expo-mobile.pid"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --serial)
      REQUESTED_SERIAL="${2:?Valor ausente para --serial}"
      shift 2
      ;;
    --no-launch)
      NO_LAUNCH=1
      shift
      ;;
    --skip-api)
      SKIP_API=1
      shift
      ;;
    --metro-port)
      METRO_PORT="${2:?Valor ausente para --metro-port}"
      shift 2
      ;;
    --backend-port)
      BACKEND_PORT="${2:?Valor ausente para --backend-port}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/run_mobile_wifi.sh [--serial <id>] [--no-launch] [--skip-api] [--metro-port <porta>] [--backend-port <porta>]

Descrição:
  Prepara o fluxo mobile por Wi-Fi em aparelho real:
  - sobe a API local em background;
  - reinicia o Metro em LAN com a API apontando para o IP atual da máquina;
  - converte um device USB autorizado em conexão adb via Wi-Fi;
  - abre o dev client do app no device selecionado.

Observação:
  Na primeira troca de rede pode ser necessário plugar o cabo USB, aceitar a
  depuração e então rodar o comando novamente.
EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

export ADB_VENDOR_KEYS="${ADB_VENDOR_KEYS:-$HOME/.android}"

ADB_RUNNER="$(resolve_adb_runner || true)"
EXPO_RUNNER="$(resolve_expo_runner || true)"

if [[ -z "$ADB_RUNNER" ]]; then
  echo "adb nao encontrado. Configure platform-tools antes de usar o fluxo Wi-Fi." >&2
  exit 1
fi

if [[ -z "$EXPO_RUNNER" ]]; then
  echo "Expo CLI nao encontrada. Rode npm install em android/." >&2
  exit 1
fi

ensure_android_deps

resolve_host_lan_ip() {
  local candidate=""

  if have_cmd ip; then
    candidate="$(
      ip route get 1.1.1.1 2>/dev/null \
        | awk '{for (i = 1; i <= NF; i += 1) if ($i == "src") {print $(i + 1); exit}}'
    )"
  fi

  if [[ -z "$candidate" ]] && have_cmd hostname; then
    candidate="$(
      hostname -I 2>/dev/null \
        | tr ' ' '\n' \
        | awk 'NF > 0 && $1 !~ /^127\./ {print $1; exit}'
    )"
  fi

  if [[ -z "$candidate" ]]; then
    echo "Nao consegui descobrir o IP LAN desta maquina." >&2
    return 1
  fi

  printf '%s\n' "$candidate"
}

adb_serial_state() {
  local serial="$1"

  "$ADB_RUNNER" devices 2>/dev/null \
    | awk -v serial="$serial" '$1 == serial {print $2; exit}'
}

resolve_usb_serial() {
  local requested="$1"

  if [[ -n "$requested" && "$requested" != *:* ]]; then
    if [[ "$(adb_serial_state "$requested")" == "device" ]]; then
      printf '%s\n' "$requested"
      return 0
    fi
    echo "Serial USB solicitado nao esta pronto: $requested" >&2
    return 1
  fi

  "$ADB_RUNNER" devices 2>/dev/null \
    | tail -n +2 \
    | awk 'NF > 0 && $2 == "device" && $1 !~ /:/ {print $1; exit}'
}

resolve_wifi_serial() {
  local requested="$1"

  if [[ -n "$requested" && "$requested" == *:* ]]; then
    if [[ "$(adb_serial_state "$requested")" == "device" ]]; then
      printf '%s\n' "$requested"
      return 0
    fi
    echo "Serial Wi-Fi solicitado nao esta pronto: $requested" >&2
    return 1
  fi

  "$ADB_RUNNER" devices 2>/dev/null \
    | tail -n +2 \
    | awk 'NF > 0 && $2 == "device" && $1 ~ /:5555$/ {print $1; exit}'
}

resolve_device_wifi_ip() {
  local serial="$1"

  run_with_timeout "$DEFAULT_ANDROID_ADB_PROBE_TIMEOUT" \
    "$ADB_RUNNER" -s "$serial" shell ip -f inet addr show wlan0 2>/dev/null \
      | awk '/inet / {sub(/\/.*/, "", $2); print $2; exit}'
}

wait_for_wifi_serial() {
  local serial="$1"
  local timeout_seconds="${2:-12}"
  local elapsed=0

  while [[ "$elapsed" -lt "$timeout_seconds" ]]; do
    if [[ "$(adb_serial_state "$serial")" == "device" ]]; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  return 1
}

kill_metro_on_port() {
  local port="$1"

  if have_cmd lsof; then
    local pids=""
    pids="$(lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      kill $pids 2>/dev/null || true
    fi
    return 0
  fi

  if have_cmd fuser; then
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
  fi
}

wait_for_http() {
  local url="$1"
  local timeout_seconds="${2:-20}"
  local elapsed=0

  while [[ "$elapsed" -lt "$timeout_seconds" ]]; do
    if curl_ok "$url"; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  return 1
}

wait_for_port() {
  local port="$1"
  local timeout_seconds="${2:-20}"
  local elapsed=0

  while [[ "$elapsed" -lt "$timeout_seconds" ]]; do
    if have_cmd ss; then
      if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "(^|[[:space:]])(\\*:|0\\.0\\.0\\.0:|127\\.0\\.0\\.1:)$port$"; then
        return 0
      fi
    elif have_cmd lsof; then
      if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        return 0
      fi
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  return 1
}

HOST_IP="$(resolve_host_lan_ip)"
BACKEND_URL="http://$HOST_IP:$BACKEND_PORT"
DEEP_LINK="tarielinspetor://expo-development-client/?url=http%3A%2F%2F${HOST_IP}%3A${METRO_PORT}"

if [[ "$SKIP_API" != "1" ]]; then
  echo "[devkit] Garantindo API local em $BACKEND_URL"
  "$REPO_ROOT/scripts/start_local_mobile_api_background.sh"
  if ! wait_for_http "http://127.0.0.1:$BACKEND_PORT/health" 30; then
    echo "API local nao respondeu em http://127.0.0.1:$BACKEND_PORT/health." >&2
    exit 1
  fi
  if ! wait_for_http "$BACKEND_URL/health" 10; then
    echo "API local nao ficou acessivel via LAN em $BACKEND_URL." >&2
    exit 1
  fi
fi

echo "[devkit] Reiniciando Metro em LAN na porta $METRO_PORT"
kill_metro_on_port "$METRO_PORT"
rm -f "$EXPO_PID_PATH"
: > "$EXPO_LOG_PATH"

(
  cd "$ANDROID_ROOT"
  env \
    EXPO_PUBLIC_API_BASE_URL="$BACKEND_URL" \
    EXPO_PUBLIC_AUTH_WEB_BASE_URL="$BACKEND_URL" \
    "$EXPO_RUNNER" start --dev-client --host lan --port "$METRO_PORT" \
      >>"$EXPO_LOG_PATH" 2>&1 &
  printf '%s\n' "$!" > "$EXPO_PID_PATH"
)

if ! wait_for_port "$METRO_PORT" 30; then
  echo "Metro nao abriu a porta $METRO_PORT." >&2
  tail -n 80 "$EXPO_LOG_PATH" >&2 || true
  exit 1
fi

TARGET_SERIAL="$(resolve_wifi_serial "$REQUESTED_SERIAL" || true)"

if [[ -z "$TARGET_SERIAL" ]]; then
  USB_SERIAL="$(resolve_usb_serial "$REQUESTED_SERIAL" || true)"
  if [[ -z "$USB_SERIAL" ]]; then
    echo "Nenhum device Android pronto. Conecte por USB ou reative uma sessao adb Wi-Fi." >&2
    echo "[devkit] Metro pronto em http://$HOST_IP:$METRO_PORT" >&2
    exit 1
  fi

  DEVICE_WIFI_IP="$(resolve_device_wifi_ip "$USB_SERIAL" || true)"
  if [[ -z "$DEVICE_WIFI_IP" ]]; then
    echo "Nao consegui descobrir o IP Wi-Fi do device $USB_SERIAL. Confirme se o aparelho esta no Wi-Fi." >&2
    exit 1
  fi

  echo "[devkit] Ativando adb Wi-Fi em $USB_SERIAL -> $DEVICE_WIFI_IP:5555"
  "$ADB_RUNNER" disconnect "$DEVICE_WIFI_IP:5555" >/dev/null 2>&1 || true
  "$ADB_RUNNER" -s "$USB_SERIAL" tcpip 5555 >/dev/null
  sleep 2
  "$ADB_RUNNER" connect "$DEVICE_WIFI_IP:5555" >/dev/null

  TARGET_SERIAL="$DEVICE_WIFI_IP:5555"
  if ! wait_for_wifi_serial "$TARGET_SERIAL" 15; then
    echo "Conectei o adb tcpip, mas o device nao ficou pronto em $TARGET_SERIAL." >&2
    exit 1
  fi
fi

if [[ "$NO_LAUNCH" != "1" ]]; then
  echo "[devkit] Abrindo dev client em $TARGET_SERIAL"
  "$ADB_RUNNER" -s "$TARGET_SERIAL" shell am start \
    -a android.intent.action.VIEW \
    -d "$DEEP_LINK" \
    "$APP_ID" >/dev/null
fi

echo "[devkit] mobile-wifi pronto"
echo "[devkit] host lan: $HOST_IP"
echo "[devkit] backend: $BACKEND_URL"
echo "[devkit] metro: http://$HOST_IP:$METRO_PORT"
echo "[devkit] adb wifi: $TARGET_SERIAL"
echo "[devkit] deep link: $DEEP_LINK"
