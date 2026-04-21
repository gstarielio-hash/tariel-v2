from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WEB_ROOT.parent
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from app.domains.revisor.reference_package_workspace import (  # noqa: E402
    discover_reference_workspace,
    inspect_reference_package_zip,
    promote_reference_package_to_workspace,
    validate_reference_package_workspace_intake,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promove um pacote ZIP de referencia preenchida para a workspace canonica da familia.",
    )
    parser.add_argument("zip_path", help="Caminho para o pacote ZIP exportado.")
    parser.add_argument(
        "--workspace-root",
        help="Caminho explicito para a workspace da familia em docs/portfolio_empresa_*_material_real/.",
    )
    parser.add_argument(
        "--family-key",
        help="Family key da workspace. Quando omitido, o script tenta inferir a familia a partir do ZIP.",
    )
    parser.add_argument(
        "--pdf-path",
        help="PDF externo opcional para preservar junto ao raw import. Se omitido, usa o PDF contido no ZIP.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Raiz do repositorio. Padrao: repo atual.",
    )
    parser.add_argument(
        "--validation-date",
        help="Data de validacao a gravar no status_refino e no manifest promovido. Padrao: hoje.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida ZIP, family_key e readiness da workspace sem promover os arquivos.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    zip_path = Path(args.zip_path).expanduser().resolve()
    if not zip_path.exists() or not zip_path.is_file():
        parser.error(f"Arquivo nao encontrado: {zip_path}")

    workspace_root: Path
    if args.workspace_root:
        workspace_root = Path(args.workspace_root).expanduser().resolve()
    else:
        family_key = args.family_key
        if not family_key:
            family_key = inspect_reference_package_zip(zip_path)["family_key"]
        workspace_root = discover_reference_workspace(Path(args.repo_root), family_key)

    pdf_path = Path(args.pdf_path).expanduser().resolve() if args.pdf_path else None
    preflight = validate_reference_package_workspace_intake(
        zip_path=zip_path,
        workspace_root=workspace_root,
        pdf_path=pdf_path,
    )
    if args.dry_run:
        preflight["mode"] = "workspace_reference_package_preflight"
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0 if preflight.get("ok") else 2
    if not preflight.get("ok"):
        preflight["mode"] = "workspace_reference_package_preflight"
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 2

    result = promote_reference_package_to_workspace(
        zip_path=zip_path,
        workspace_root=workspace_root,
        pdf_path=pdf_path,
        validation_date=args.validation_date,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
