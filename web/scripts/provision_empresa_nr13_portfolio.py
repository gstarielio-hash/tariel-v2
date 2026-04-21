from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import select

WEB_DIR = Path(__file__).resolve().parents[1]
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from app.domains.admin.services import (  # noqa: E402
    PORTFOLIO_EMPRESA_NR13_FAMILIAS_OPERACAO_IMEDIATA,
    listar_family_schemas_canonicos,
    provisionar_familias_canonicas_empresa,
)
from app.shared.database import SessaoLocal, Usuario, commit_ou_rollback_integridade  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provisiona o portfolio canônico NR13/END da empresa piloto no catálogo/Admin-CEO.",
    )
    parser.add_argument("--empresa-id", type=int, default=1)
    parser.add_argument("--admin-email", default="admin@tariel.ia")
    parser.add_argument("--status-catalogo", default="publicado")
    parser.add_argument("--release-status", default="liberado")
    parser.add_argument("--status-template-padrao", default="em_teste")
    parser.add_argument("--versao-template", type=int, default=1)
    parser.add_argument(
        "--family-key",
        action="append",
        dest="family_keys",
        help="Restringe o provisionamento a uma família específica. Pode repetir a flag.",
    )
    parser.add_argument(
        "--ativar-family",
        action="append",
        dest="family_keys_ativas",
        help="Marca explicitamente uma família como ativa. Pode repetir a flag.",
    )
    parser.add_argument(
        "--ativar-todas",
        action="store_true",
        help="Promove todas as famílias provisionadas para template ativo.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    family_keys = args.family_keys or [str(item.get("family_key") or "").strip() for item in listar_family_schemas_canonicos()]
    if args.ativar_todas:
        family_keys_ativas = list(family_keys)
    elif args.family_keys_ativas:
        family_keys_ativas = list(args.family_keys_ativas)
    else:
        family_keys_ativas = list(PORTFOLIO_EMPRESA_NR13_FAMILIAS_OPERACAO_IMEDIATA)

    with SessaoLocal() as db:
        admin = db.scalar(select(Usuario).where(Usuario.email == str(args.admin_email or "").strip().lower()))
        provisionadas = provisionar_familias_canonicas_empresa(
            db,
            empresa_id=int(args.empresa_id),
            family_keys=family_keys,
            status_catalogo=str(args.status_catalogo or "publicado"),
            release_status=str(args.release_status or "liberado"),
            versao_template=int(args.versao_template or 1),
            status_template_padrao=str(args.status_template_padrao or "em_teste"),
            family_keys_ativas=family_keys_ativas,
            admin_id=int(admin.id) if admin is not None else None,
        )
        commit_ou_rollback_integridade(
            db,
            logger_operacao=logging.getLogger("tariel.portfolio.provision"),
            mensagem_erro="Falha ao provisionar o portfolio canônico da empresa.",
        )

    resumo = {
        "empresa_id": int(args.empresa_id),
        "admin_email": str(args.admin_email or "").strip().lower(),
        "familias_processadas": len(provisionadas),
        "familias_ativas": [item["family_key"] for item in provisionadas if item["template_active"]],
        "templates_criados": sum(1 for item in provisionadas if item["template_created"]),
        "templates_existentes_reaproveitados": sum(1 for item in provisionadas if not item["template_created"]),
        "familias": provisionadas,
    }
    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
