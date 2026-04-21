#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

PYTHON_EXE="$(resolve_web_python)"

echo "[devkit] Reviewdesk check: pytest smoke"
(
  cd "$WEB_ROOT"
  PYTHONPATH=. "$PYTHON_EXE" -m pytest -q \
    tests/test_reviewer_panel_boot_hotfix.py \
    tests/test_revisor_command_handlers.py \
    tests/test_revisor_command_side_effects.py \
    tests/test_revisor_mesa_api_side_effects.py \
    tests/test_revisor_realtime.py \
    tests/test_revisor_ws.py \
    tests/test_template_publish_contract.py \
    tests/test_v2_reviewdesk_projection.py \
    tests/test_v2_review_queue_projection.py \
    tests/test_mesa_mobile_sync.py
)

echo "[devkit] Reviewdesk check: OK"
