#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

ANDROID_MODE="none"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --android)
      ANDROID_MODE="${2:?Valor ausente para --android}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/run_repo_stack.sh [--android none|metro|android-dev|android-preview|maestro-smoke|maestro-suite]

EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done

  for pid in "${PIDS[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
}

trap cleanup EXIT INT TERM

echo "[devkit] Repo stack"
echo "[devkit] Backend    http://$DEFAULT_BACKEND_HOST:$DEFAULT_BACKEND_PORT"
echo "[devkit] Reviewdesk http://$DEFAULT_BACKEND_HOST:$DEFAULT_BACKEND_PORT/revisao/login"
echo "[devkit] Painel     http://$DEFAULT_BACKEND_HOST:$DEFAULT_BACKEND_PORT/revisao/painel"
if [[ "$ANDROID_MODE" != "none" ]]; then
  echo "[devkit] Android    mode=$ANDROID_MODE"
fi

"$DEV_DIR/run_web_backend.sh" &
PIDS+=($!)

if [[ "$ANDROID_MODE" != "none" ]]; then
  "$DEV_DIR/run_android_stack.sh" --mode "$ANDROID_MODE" &
  PIDS+=($!)
fi

wait -n "${PIDS[@]}"
