#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

HOST="$DEFAULT_BACKEND_HOST"
PORT="$DEFAULT_BACKEND_PORT"
RELOAD=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:?Valor ausente para --host}"
      shift 2
      ;;
    --port)
      PORT="${2:?Valor ausente para --port}"
      shift 2
      ;;
    --no-reload)
      RELOAD=0
      shift
      ;;
    --reload)
      RELOAD=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/run_web_backend.sh [--host 127.0.0.1] [--port 8000] [--no-reload]

EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

PYTHON_EXE="$(resolve_web_python)"
export AMBIENTE="${AMBIENTE:-dev}"

echo "[devkit] Backend web em http://$HOST:$PORT"
echo "[devkit] Python: $PYTHON_EXE"

cd "$WEB_ROOT"

if [[ "$RELOAD" == "1" ]]; then
  exec "$PYTHON_EXE" -m uvicorn main:app --app-dir . --host "$HOST" --port "$PORT" --reload
fi

exec "$PYTHON_EXE" -m uvicorn main:app --app-dir . --host "$HOST" --port "$PORT"
