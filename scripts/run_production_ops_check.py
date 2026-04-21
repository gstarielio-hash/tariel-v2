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

from app.domains.admin.production_ops_summary import (  # noqa: E402
    build_admin_production_operations_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida e imprime o resumo operacional canônico de produção.",
    )
    parser.add_argument("--json", action="store_true", help="Imprime o payload em JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falha com exit code 1 se houver blockers operacionais.",
    )
    args = parser.parse_args()

    payload = build_admin_production_operations_summary()
    blockers = list(dict(payload.get("readiness") or {}).get("blockers") or [])

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"environment: {payload.get('environment')}")
        print(f"production_ready: {dict(payload.get('readiness') or {}).get('production_ready')}")
        print(
            "uploads:"
            f" mode={dict(payload.get('uploads') or {}).get('storage_mode')}"
            f" backup_required={dict(payload.get('uploads') or {}).get('backup_required')}"
            f" cleanup_enabled={dict(payload.get('uploads') or {}).get('cleanup_enabled')}"
        )
        cleanup_runtime = dict(dict(payload.get("uploads") or {}).get("cleanup_runtime") or {})
        print(
            "cleanup:"
            f" scheduler_running={cleanup_runtime.get('scheduler_running')}"
            f" last_status={cleanup_runtime.get('scheduler_last_status')}"
            f" latest_report_present={bool(cleanup_runtime.get('latest_report'))}"
        )
        print(
            "sessions:"
            f" mode={dict(payload.get('sessions') or {}).get('storage_mode')}"
            f" multi_instance_ready={dict(payload.get('sessions') or {}).get('multi_instance_ready')}"
            f" fail_closed={dict(payload.get('sessions') or {}).get('fail_closed_on_db_error')}"
        )
        if blockers:
            print("blockers:")
            for item in blockers:
                print(f"- {item}")

    return 1 if args.strict and blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
