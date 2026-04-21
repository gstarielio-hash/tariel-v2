from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domains.chat.catalog_snapshot_backfill import (  # noqa: E402
    backfill_laudo_catalog_snapshots,
)
from app.shared.database import SessaoLocal, inicializar_banco  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Congela snapshots de catalogo/template em laudos antigos governados. "
            "O backfill registra explicitamente que a captura foi feita sobre o estado atual."
        )
    )
    parser.add_argument("--empresa-id", type=int, help="Restringe a operacao a uma empresa.")
    parser.add_argument(
        "--laudo-id",
        action="append",
        dest="laudo_ids",
        type=int,
        help="Restringe a operacao a IDs de laudo especificos. Pode repetir.",
    )
    parser.add_argument("--limit", type=int, help="Limita a quantidade de laudos avaliados.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra quantos laudos seriam congelados sem persistir alteracoes.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma a operacao sem prompt interativo.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.dry_run and not args.yes:
        confirmacao = input(
            "Este backfill vai congelar snapshots com a marca 'backfill_current_state'. Continuar? [y/N]: "
        ).strip().lower()
        if confirmacao not in {"y", "yes", "s", "sim"}:
            print("Operacao cancelada.")
            return 1

    inicializar_banco()

    with SessaoLocal() as banco:
        summary = backfill_laudo_catalog_snapshots(
            banco,
            empresa_id=args.empresa_id,
            laudo_ids=args.laudo_ids,
            limit=args.limit,
            dry_run=bool(args.dry_run),
        )
        if args.dry_run:
            banco.rollback()
        else:
            banco.commit()

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
