#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

SESSION_NAME="tariel-codex"
ATTACH=1
PRINT_PLAN=0
KILL_EXISTING=0
ANDROID_MODE="metro"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session)
      SESSION_NAME="${2:?Valor ausente para --session}"
      shift 2
      ;;
    --detached)
      ATTACH=0
      shift
      ;;
    --plan)
      PRINT_PLAN=1
      shift
      ;;
    --kill-existing)
      KILL_EXISTING=1
      shift
      ;;
    --android)
      ANDROID_MODE="${2:?Valor ausente para --android}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  scripts/dev/open_codex_workspace_tmux.sh [--session nome] [--detached] [--plan] [--kill-existing] [--android metro|android-dev|android-preview|maestro-smoke|maestro-suite]

EOF
      exit 0
      ;;
    *)
      echo "Argumento nao reconhecido: $1" >&2
      exit 1
      ;;
  esac
done

WINDOW_NAMES=(
  "backend"
  "reviewdesk"
  "checks"
  "android"
  "codex"
)

WINDOW_COMMANDS=(
  "scripts/dev/run_web_backend.sh"
  "printf 'Mesa oficial no SSR: http://$DEFAULT_BACKEND_HOST:$DEFAULT_BACKEND_PORT/revisao/login\\nPainel: http://$DEFAULT_BACKEND_HOST:$DEFAULT_BACKEND_PORT/revisao/painel\\n'; exec bash"
  "printf 'Use scripts/dev/check_all.sh ou checks por area.\\n'; exec bash"
  "scripts/dev/run_android_stack.sh --mode $ANDROID_MODE"
  "exec bash"
)

if [[ "$PRINT_PLAN" == "1" ]]; then
  echo "session: $SESSION_NAME"
  for i in "${!WINDOW_NAMES[@]}"; do
    printf '%s\t%s\n' "${WINDOW_NAMES[$i]}" "${WINDOW_COMMANDS[$i]}"
  done
  exit 0
fi

if ! have_cmd tmux; then
  echo "tmux nao encontrado no PATH. O script esta pronto, mas a sessao nao pode ser criada nesta maquina." >&2
  echo "Use --plan para ver o layout ou instale tmux no Linux." >&2
  exit 1
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  if [[ "$KILL_EXISTING" == "1" ]]; then
    tmux kill-session -t "$SESSION_NAME"
  else
    if [[ "$ATTACH" == "1" ]]; then
      exec tmux attach-session -t "$SESSION_NAME"
    fi
    echo "Sessao tmux $SESSION_NAME ja existe."
    exit 0
  fi
fi

tmux new-session -d -s "$SESSION_NAME" -n "${WINDOW_NAMES[0]}"
tmux send-keys -t "$SESSION_NAME:${WINDOW_NAMES[0]}" "cd \"$REPO_ROOT\" && ${WINDOW_COMMANDS[0]}" C-m

for i in 1 2 3 4; do
  tmux new-window -t "$SESSION_NAME" -n "${WINDOW_NAMES[$i]}"
  tmux send-keys -t "$SESSION_NAME:${WINDOW_NAMES[$i]}" "cd \"$REPO_ROOT\" && ${WINDOW_COMMANDS[$i]}" C-m
done

tmux split-window -t "$SESSION_NAME:checks" -v
tmux send-keys -t "$SESSION_NAME:checks.2" "cd \"$REPO_ROOT\" && while true; do clear; scripts/dev/status.sh || true; sleep 5; done" C-m
tmux select-layout -t "$SESSION_NAME:checks" even-vertical
tmux select-window -t "$SESSION_NAME:codex"

if [[ "$ATTACH" == "1" ]]; then
  exec tmux attach-session -t "$SESSION_NAME"
fi

echo "Sessao tmux criada: $SESSION_NAME"
