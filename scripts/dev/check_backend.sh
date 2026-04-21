#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

PYTHON_EXE="$(resolve_web_python)"

echo "[devkit] Backend check: py_compile"
(
  cd "$WEB_ROOT"
  PYTHONPATH=. "$PYTHON_EXE" -m py_compile main.py
)

echo "[devkit] Backend check: pytest smoke"
(
  cd "$WEB_ROOT"
  PYTHONPATH=. "$PYTHON_EXE" -m pytest -q tests/test_smoke.py
)

echo "[devkit] Backend check: OK"
