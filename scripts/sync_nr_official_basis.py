from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FAMILY_SCHEMAS_DIR = REPO_ROOT / "docs" / "family_schemas"
CANONICAL_FAMILY_SCHEMAS_DIR = REPO_ROOT / "web" / "canonical_docs" / "family_schemas"
REGISTRY_PATH = REPO_ROOT / "docs" / "nr_programming_registry.json"

OFFICIAL_OVERVIEW_URL = (
    "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/"
    "seguranca-e-saude-no-trabalho/ctpp-nrs/normas-regulamentadoras-nrs"
)
OFFICIAL_PDF_BASE_URL = (
    "https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/"
    "conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/arquivos/"
    "normas-regulamentadoras"
)
OFFICIAL_SOURCE_OVERRIDES: dict[str, dict[str, Any]] = {
    "nr09": {
        "title": "Portaria SEPRT nº 6.735/2020 - NR-09",
        "url": (
            "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/"
            "seguranca-e-saude-no-trabalho/sst-portarias/2020/portaria_seprt_6-735_-altera_a_nr_09.pdf/%40%40download/file"
        ),
        "used_for": "Base oficial vigente da parte principal da NR-09 e suas atualizacoes estruturantes.",
    },
    "nr16": {
        "title": "Norma Regulamentadora No. 16 (NR-16)",
        "url": (
            "https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/"
            "conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/"
            "normas-regulamentadora/normas-regulamentadoras-vigentes/norma-regulamentadora-no-16-nr-16"
        ),
        "used_for": "Pagina oficial vigente da NR-16 e seus anexos publicados pelo MTE.",
    },
    "nr24": {
        "title": "Norma Regulamentadora No. 24 (NR-24)",
        "url": (
            "https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/"
            "conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/"
            "normas-regulamentadora/normas-regulamentadoras-vigentes/norma-regulamentadora-no-24-nr-24"
        ),
        "used_for": "Pagina oficial vigente da NR-24 e suas alteracoes publicadas pelo MTE.",
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _iter_family_schema_paths() -> list[Path]:
    paths: list[Path] = []
    for path in sorted(FAMILY_SCHEMAS_DIR.glob("nr*.json")):
        name = path.name
        if name.endswith(".laudo_output_exemplo.json") or name.endswith(".laudo_output_seed.json") or name.endswith(
            ".template_master_seed.json"
        ):
            continue
        paths.append(path)
    return paths


def _registry_by_code() -> dict[str, dict[str, Any]]:
    registry = _load_json(REGISTRY_PATH)
    normas = registry.get("normas") if isinstance(registry, dict) else None
    by_code: dict[str, dict[str, Any]] = {}
    if not isinstance(normas, list):
        return by_code
    for item in normas:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip().lower()
        if code:
            by_code[code] = item
    return by_code


def _nr_code_from_family_key(family_key: str) -> str | None:
    match = re.match(r"^(nr\d{2})_", str(family_key or "").strip().lower())
    if not match:
        return None
    return match.group(1)


def _nr_number_from_code(code: str) -> str | None:
    match = re.match(r"^nr(\d{2})$", str(code or "").strip().lower())
    if not match:
        return None
    return match.group(1)


def _official_pdf_url(code: str) -> str | None:
    number = _nr_number_from_code(code)
    if not number:
        return None
    return f"{OFFICIAL_PDF_BASE_URL}/nr-{number}.pdf"


def _default_normative_basis(*, code: str, title: str) -> dict[str, Any]:
    pdf_url = _official_pdf_url(code)
    sources: list[dict[str, Any]] = [
        {
            "authority": "Ministerio do Trabalho e Emprego",
            "title": "Normas Regulamentadoras - NR",
            "url": OFFICIAL_OVERVIEW_URL,
            "used_for": "Ponto de entrada oficial do projeto para localizar textos vigentes, anexos e atualizacoes das NRs.",
        }
    ]
    override = OFFICIAL_SOURCE_OVERRIDES.get(code)
    if override:
        sources.append(
            {
                "authority": "Ministerio do Trabalho e Emprego",
                "title": str(override.get("title") or title).strip(),
                "url": str(override.get("url") or "").strip(),
                "anchors": [],
                "used_for": str(override.get("used_for") or "").strip()
                or "Fonte oficial vigente da NR usada como base normativa primaria do family_schema.",
            }
        )
    elif pdf_url:
        sources.append(
            {
                "authority": "Ministerio do Trabalho e Emprego",
                "title": title,
                "url": pdf_url,
                "anchors": [],
                "used_for": "Texto oficial vigente da NR usado como base normativa primaria do family_schema.",
            }
        )
    return {
        "policy_version": 1,
        "status": "bootstrap_official_basis_registered",
        "nr_code": code,
        "nr_title": title,
        "editorial_inference_notice": (
            "A norma oficial define os requisitos de referencia; headings, ordem, linguagem editorial "
            "e acabamento visual do template sao decisoes de produto da Tariel."
        ),
        "implementation_note": (
            "Bootstrap oficial registrado. Ao endurecer a familia, preencher anchors granulares e "
            "mapear explicitamente o requisito normativo para checklist, documentacao, evidencias e conclusao."
        ),
        "sources": sources,
    }


def _merge_sources(existing: list[dict[str, Any]], required: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for source in existing + required:
        if not isinstance(source, dict):
            continue
        url = str(source.get("url") or "").strip()
        if not url:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        merged.append(source)
    return merged


def _prune_existing_sources(*, code: str, existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if code not in OFFICIAL_SOURCE_OVERRIDES:
        return existing
    obsolete_pdf_url = _official_pdf_url(code)
    if not obsolete_pdf_url:
        return existing
    pruned: list[dict[str, Any]] = []
    for source in existing:
        if not isinstance(source, dict):
            continue
        url = str(source.get("url") or "").strip()
        if url == obsolete_pdf_url:
            continue
        pruned.append(source)
    return pruned


def _sync_schema(path: Path, registry_by_code: dict[str, dict[str, Any]]) -> bool:
    payload = _load_json(path)
    family_key = str(payload.get("family_key") or path.stem).strip().lower()
    nr_code = _nr_code_from_family_key(family_key)
    if not nr_code:
        return False
    registry_item = registry_by_code.get(nr_code)
    title = str((registry_item or {}).get("title") or nr_code.upper()).strip()

    default_basis = _default_normative_basis(code=nr_code, title=title)
    current_basis = payload.get("normative_basis")
    if not isinstance(current_basis, dict):
        payload["normative_basis"] = default_basis
    else:
        payload["normative_basis"] = {**default_basis, **current_basis}
        existing_sources = current_basis.get("sources")
        normalized_existing_sources = _prune_existing_sources(
            code=nr_code,
            existing=existing_sources if isinstance(existing_sources, list) else [],
        )
        payload["normative_basis"]["sources"] = _merge_sources(
            normalized_existing_sources,
            default_basis["sources"],
        )

    _dump_json(path, payload)
    canonical_path = CANONICAL_FAMILY_SCHEMAS_DIR / path.name
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    _dump_json(canonical_path, payload)
    return True


def main() -> None:
    registry = _registry_by_code()
    updated = 0
    for path in _iter_family_schema_paths():
        if _sync_schema(path, registry):
            updated += 1
    print(json.dumps({"schemas_updated": updated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
