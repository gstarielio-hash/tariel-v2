#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web"
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

os.environ.setdefault("AMBIENTE", "dev")

from app.domains.admin.uploads_cleanup import run_uploads_cleanup  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa cleanup seguro de uploads/anexos com guardrails.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Aplica exclusões elegíveis.")
    mode.add_argument("--dry-run", action="store_true", help="Força dry-run explícito.")
    parser.add_argument("--json", action="store_true", help="Imprime o payload em JSON.")
    parser.add_argument("--strict", action="store_true", help="Falha com exit code 1 se houver blockers ou erros.")
    parser.add_argument("--source", default="cli", help="Identificador do disparo.")
    args = parser.parse_args()

    payload = run_uploads_cleanup(
        apply=bool(args.apply),
        source=str(args.source or "cli").strip() or "cli",
        strict=bool(args.strict),
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"status: {payload.get('status')}")
        print(f"mode: {payload.get('mode')}")
        print(f"report_path: {payload.get('report_path')}")
        totals = dict(payload.get("totals") or {})
        print(
            "totals:"
            f" scanned={totals.get('scanned_files')}"
            f" orphan={totals.get('orphan_files')}"
            f" eligible={totals.get('eligible_files')}"
            f" deleted={totals.get('deleted_files')}"
        )
        for warning in payload.get("warnings") or []:
            print(f"warning: {warning}")
        for blocker in payload.get("blockers") or []:
            print(f"blocker: {blocker}")
        for error in payload.get("errors") or []:
            print(f"error: {error}")

    strict_failure = bool(payload.get("strict_failure", False))
    errors = list(payload.get("errors") or [])
    blockers = list(payload.get("blockers") or [])
    return 1 if args.strict and (strict_failure or errors or blockers) else 0


if __name__ == "__main__":
    raise SystemExit(main())
