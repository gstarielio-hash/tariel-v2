#!/usr/bin/env python3
"""Fila local de handoff entre terminais/agentes no mesmo workspace.

Uso principal:
- backend registra itens que exigem frontend;
- frontend lista, assume e conclui;
- a fila vive em artifacts/ e nao entra no Git.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
QUEUE_DIR = REPO_ROOT / "artifacts" / "terminal_handoff"
QUEUE_FILE = QUEUE_DIR / "queue.json"
ALLOWED_STATUS = {"pending", "claimed", "done", "cancelled"}
ALLOWED_PRIORITY = {"low", "medium", "high"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_text(value: str, *, max_len: int) -> str:
    compact = " ".join(str(value or "").strip().split())
    return compact[:max_len]


def ensure_queue_file() -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    if QUEUE_FILE.exists():
        return
    payload = {
        "version": 1,
        "updated_at": utc_now_iso(),
        "items": [],
    }
    QUEUE_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def load_queue() -> dict[str, Any]:
    ensure_queue_file()
    try:
        payload = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"fila corrompida em {QUEUE_FILE}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"fila invalida em {QUEUE_FILE}")
    items = payload.get("items")
    if not isinstance(items, list):
        payload["items"] = []
    return payload


def save_queue(payload: dict[str, Any]) -> None:
    payload["updated_at"] = utc_now_iso()
    QUEUE_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def next_item_id(items: list[dict[str, Any]]) -> str:
    current_max = 0
    for item in items:
        raw = str(item.get("id", "")).strip()
        if not raw.startswith("HF-"):
            continue
        try:
            current_max = max(current_max, int(raw.split("-", 1)[1]))
        except ValueError:
            continue
    return f"HF-{current_max + 1:04d}"


def build_item(args: argparse.Namespace, existing_items: list[dict[str, Any]]) -> dict[str, Any]:
    now = utc_now_iso()
    return {
        "id": next_item_id(existing_items),
        "created_at": now,
        "updated_at": now,
        "status": "pending",
        "source": _normalize_text(args.source, max_len=40),
        "target": _normalize_text(args.target, max_len=40),
        "priority": args.priority,
        "title": _normalize_text(args.title, max_len=160),
        "summary": _normalize_text(args.summary, max_len=600),
        "frontend_request": _normalize_text(args.frontend_request or "", max_len=300),
        "routes": [_normalize_text(value, max_len=240) for value in (args.route or []) if str(value).strip()],
        "backend_paths": [_normalize_text(value, max_len=260) for value in (args.backend_path or []) if str(value).strip()],
        "frontend_paths": [_normalize_text(value, max_len=260) for value in (args.frontend_path or []) if str(value).strip()],
        "owner": "",
        "notes": [],
    }


def cmd_add(args: argparse.Namespace) -> int:
    payload = load_queue()
    items = payload["items"]
    item = build_item(args, items)
    items.append(item)
    save_queue(payload)
    print(f"adicionado {item['id']}: {item['title']}")
    print(f"fila: {QUEUE_FILE}")
    return 0


def _matches_filters(item: dict[str, Any], *, target: str, status: str) -> bool:
    if target and str(item.get("target", "")).strip() != target:
        return False
    if status != "all" and str(item.get("status", "")).strip() != status:
        return False
    return True


def _format_block(item: dict[str, Any]) -> str:
    lines = [
        f"{item.get('id', 'HF-????')} [{item.get('status', '?')}] [{item.get('priority', '?')}] {item.get('source', '?')} -> {item.get('target', '?')}",
        f"titulo: {item.get('title', '')}",
        f"resumo: {item.get('summary', '')}",
    ]
    frontend_request = str(item.get("frontend_request", "")).strip()
    if frontend_request:
        lines.append(f"frontend: {frontend_request}")
    owner = str(item.get("owner", "")).strip()
    if owner:
        lines.append(f"owner: {owner}")
    routes = item.get("routes") or []
    if routes:
        lines.append("rotas: " + ", ".join(str(route) for route in routes))
    backend_paths = item.get("backend_paths") or []
    if backend_paths:
        lines.append("backend: " + ", ".join(str(path) for path in backend_paths))
    frontend_paths = item.get("frontend_paths") or []
    if frontend_paths:
        lines.append("frontend_paths: " + ", ".join(str(path) for path in frontend_paths))
    notes = item.get("notes") or []
    if notes:
        lines.append("notas:")
        for note in notes[-3:]:
            lines.append(f"- {note}")
    lines.append(f"updated_at: {item.get('updated_at', '')}")
    return "\n".join(lines)


def cmd_list(args: argparse.Namespace) -> int:
    payload = load_queue()
    items = [item for item in payload["items"] if _matches_filters(item, target=args.target, status=args.status)]
    if not items:
        print("nenhum item encontrado")
        print(f"fila: {QUEUE_FILE}")
        return 0
    for index, item in enumerate(items):
        if index:
            print()
        print(_format_block(item))
    print()
    print(f"fila: {QUEUE_FILE}")
    return 0


def find_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    target_id = _normalize_text(item_id, max_len=40)
    for item in items:
        if str(item.get("id", "")).strip() == target_id:
            return item
    raise SystemExit(f"item nao encontrado: {target_id}")


def cmd_update(args: argparse.Namespace) -> int:
    payload = load_queue()
    item = find_item(payload["items"], args.item_id)
    if args.status:
        item["status"] = args.status
    if args.owner is not None:
        item["owner"] = _normalize_text(args.owner, max_len=80)
    if args.note:
        notes = item.setdefault("notes", [])
        if isinstance(notes, list):
            notes.append(f"{utc_now_iso()} - {_normalize_text(args.note, max_len=300)}")
    item["updated_at"] = utc_now_iso()
    save_queue(payload)
    print(f"atualizado {item['id']} para status={item['status']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fila local de handoff backend/frontend no mesmo workspace.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="adiciona uma nova pendencia na fila")
    add_parser.add_argument("--source", default="backend")
    add_parser.add_argument("--target", default="frontend")
    add_parser.add_argument("--priority", choices=sorted(ALLOWED_PRIORITY), default="medium")
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--summary", required=True)
    add_parser.add_argument("--frontend-request", default="")
    add_parser.add_argument("--route", action="append")
    add_parser.add_argument("--backend-path", action="append")
    add_parser.add_argument("--frontend-path", action="append")
    add_parser.set_defaults(func=cmd_add)

    list_parser = subparsers.add_parser("list", help="lista itens da fila")
    list_parser.add_argument("--target", default="")
    list_parser.add_argument("--status", choices=sorted(ALLOWED_STATUS | {"all"}), default="pending")
    list_parser.set_defaults(func=cmd_list)

    update_parser = subparsers.add_parser("update", help="atualiza status, owner ou nota de um item")
    update_parser.add_argument("item_id")
    update_parser.add_argument("--status", choices=sorted(ALLOWED_STATUS))
    update_parser.add_argument("--owner")
    update_parser.add_argument("--note")
    update_parser.set_defaults(func=cmd_update)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
