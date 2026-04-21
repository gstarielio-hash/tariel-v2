from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import select

WEB_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = WEB_DIR.parents[0]
REGISTRY_PATH = REPO_ROOT / "docs" / "nr_programming_registry.json"

if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from app.domains.admin.services import provisionar_familias_canonicas_empresa  # noqa: E402
from app.shared.database import SessaoLocal, TemplateLaudo, Usuario, commit_ou_rollback_integridade  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provisiona o portfolio nacional de NRs por ondas no catalogo/Admin-CEO.",
    )
    parser.add_argument("--empresa-id", type=int, default=1)
    parser.add_argument("--admin-email", default="admin@tariel.ia")
    parser.add_argument("--status-catalogo", default="publicado")
    parser.add_argument("--release-status", default="liberado")
    parser.add_argument("--status-template-padrao", default="em_teste")
    parser.add_argument("--versao-template", type=int, default=1)
    parser.add_argument(
        "--wave",
        action="append",
        dest="waves",
        help="Restringe o provisionamento a uma ou mais ondas. Ex.: wave_1",
    )
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
    parser.add_argument(
        "--preserve-existing-active",
        dest="preserve_existing_active",
        action="store_true",
        default=True,
        help="Preserva templates já ativos da empresa quando o mesmo código reaparece no rollout.",
    )
    parser.add_argument(
        "--no-preserve-existing-active",
        dest="preserve_existing_active",
        action="store_false",
        help="Não preserva templates ativos já existentes; aplica apenas o status padrão informado.",
    )
    return parser.parse_args()


def _load_registry() -> dict[str, object]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _family_keys_from_registry(*, waves: set[str] | None = None) -> list[str]:
    payload = _load_registry()
    resolved: list[str] = []
    for item in payload.get("normas", []):
        if not isinstance(item, dict):
            continue
        current_status = str(item.get("current_status") or "").strip().lower()
        if current_status in {"revoked", "support_only"}:
            continue
        wave = str(item.get("programming_wave") or "").strip()
        if waves and wave not in waves:
            continue
        suggested_families = item.get("suggested_families")
        if not isinstance(suggested_families, list):
            continue
        for family_key_raw in suggested_families:
            family_key = str(family_key_raw or "").strip()
            if family_key and family_key not in resolved:
                resolved.append(family_key)
    return resolved


def _template_codes_ativos_empresa(db, *, empresa_id: int) -> list[str]:
    rows = db.scalars(
        select(TemplateLaudo.codigo_template).where(
            TemplateLaudo.empresa_id == int(empresa_id),
            TemplateLaudo.ativo.is_(True),
        )
    )
    encontrados: list[str] = []
    vistos: set[str] = set()
    for item in rows:
        codigo = str(item or "").strip()
        if not codigo or codigo in vistos:
            continue
        vistos.add(codigo)
        encontrados.append(codigo)
    return encontrados


def main() -> int:
    args = _parse_args()
    waves = {str(item).strip() for item in (args.waves or []) if str(item).strip()}
    family_keys = args.family_keys or _family_keys_from_registry(waves=waves or None)
    with SessaoLocal() as db:
        admin = db.scalar(select(Usuario).where(Usuario.email == str(args.admin_email or "").strip().lower()))
        template_codes_ativos = _template_codes_ativos_empresa(db, empresa_id=int(args.empresa_id)) if args.preserve_existing_active else []
        if args.ativar_todas:
            family_keys_ativas = list(family_keys)
        else:
            family_keys_ativas = list(args.family_keys_ativas or [])
        provisionadas = provisionar_familias_canonicas_empresa(
            db,
            empresa_id=int(args.empresa_id),
            family_keys=family_keys,
            status_catalogo=str(args.status_catalogo or "publicado"),
            release_status=str(args.release_status or "liberado"),
            versao_template=int(args.versao_template or 1),
            status_template_padrao=str(args.status_template_padrao or "em_teste"),
            family_keys_ativas=family_keys_ativas,
            template_codes_ativos=template_codes_ativos,
            admin_id=int(admin.id) if admin is not None else None,
        )
        commit_ou_rollback_integridade(
            db,
            logger_operacao=logging.getLogger("tariel.portfolio.nacional"),
            mensagem_erro="Falha ao provisionar o portfolio nacional de NRs.",
        )

    resumo = {
        "empresa_id": int(args.empresa_id),
        "waves": sorted(waves),
        "familias_processadas": len(provisionadas),
        "familias_ativas": [item["family_key"] for item in provisionadas if item["template_active"]],
        "template_codes_ativos_preservados": template_codes_ativos,
        "templates_criados": sum(1 for item in provisionadas if item["template_created"]),
        "templates_existentes_reaproveitados": sum(1 for item in provisionadas if not item["template_created"]),
        "familias": provisionadas,
    }
    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
