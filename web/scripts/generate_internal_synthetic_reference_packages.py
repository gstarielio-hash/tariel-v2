from __future__ import annotations

import argparse
import json
import sys
import tempfile
import textwrap
import unicodedata
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

WEB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WEB_ROOT.parent
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from app.domains.revisor.reference_package_workspace import (  # noqa: E402
    discover_reference_workspace,
    promote_reference_package_to_workspace,
)

DEFAULT_FAMILIES = [
    "nr13_inspecao_tubulacao",
    "nr13_integridade_caldeira",
    "nr13_teste_hidrostatico",
    "nr13_teste_estanqueidade_tubulacao_gas",
    "nr12_inspecao_maquina_equipamento",
    "nr12_apreciacao_risco_maquina",
    "nr20_inspecao_instalacoes_inflamaveis",
    "nr20_prontuario_instalacoes_inflamaveis",
    "nr33_avaliacao_espaco_confinado",
    "nr33_permissao_entrada_trabalho",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera internamente pacotes sinteticos de referencia e promove para a workspace canonica.",
    )
    parser.add_argument(
        "--family-key",
        action="append",
        dest="family_keys",
        help="Family key alvo. Pode repetir a flag. Quando omitido, usa a fila prioritaria.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Raiz do repositorio.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regera mesmo quando a workspace ja tem baseline sintetica validada.",
    )
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ascii(text: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return normalized.encode("ascii", "ignore").decode("ascii")


def _slug(text: Any) -> str:
    value = _ascii(text).strip().lower()
    sanitized = "".join(ch if ch.isalnum() else "_" for ch in value)
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized.strip("_") or "item"


def _pick_first_str(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _summary_text(example: dict[str, Any], conclusion: dict[str, Any]) -> str:
    resumo = example.get("resumo_executivo")
    if isinstance(resumo, dict):
        candidate = _pick_first_str(
            resumo.get("texto"),
            resumo.get("summary"),
        )
        if candidate:
            return candidate
    if isinstance(resumo, str) and resumo.strip():
        return resumo.strip()
    return _pick_first_str(
        conclusion.get("conclusao_tecnica"),
        "Baseline sintetica produzida internamente para acelerar refinamento documental.",
    )


def _extract_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _normalize_snapshot_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, list):
        normalized = [_normalize_snapshot_value(item) for item in value]
        return [item for item in normalized if item not in (None, "", [])][:4]
    if isinstance(value, dict):
        compact = {
            _slug(key): _normalize_snapshot_value(item)
            for key, item in value.items()
            if _normalize_snapshot_value(item) not in (None, "", [], {})
        }
        return compact or None
    text = _pick_first_str(str(value) if value is not None else "")
    return _ascii(text) if text else None


def _load_family_inputs(repo_root: Path, family_key: str) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    workspace_root = discover_reference_workspace(repo_root, family_key)
    manifest = _read_json(workspace_root / "manifesto_coleta.json")
    schema = _read_json(repo_root / "docs" / "family_schemas" / f"{family_key}.json")
    example = _read_json(repo_root / "docs" / "family_schemas" / f"{family_key}.laudo_output_exemplo.json")
    return workspace_root, manifest, schema, example


def _should_skip_workspace(workspace_root: Path, *, force: bool) -> bool:
    if force:
        return False
    status_path = workspace_root / "status_refino.json"
    if not status_path.exists():
        return False
    status = _read_json(status_path)
    return str(status.get("status_refino") or "").strip() == "baseline_sintetica_externa_validada"


def _build_reference_slots(manifest: dict[str, Any], example: dict[str, Any]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for item in list(manifest.get("required_slots_snapshot") or []):
        if not isinstance(item, dict):
            continue
        slot_id = str(item.get("item_id") or item.get("slot_id") or "").strip()
        binding_path = str(item.get("binding_path") or "").strip()
        if not slot_id or not binding_path:
            continue
        normalized = _normalize_snapshot_value(_extract_path(example, binding_path))
        snapshot[_slug(slot_id.replace("slot_", ""))] = normalized or "a_confirmar"

    identification = _as_dict(example.get("identificacao"))
    conclusion = _as_dict(example.get("conclusao"))
    case_context = _as_dict(example.get("case_context"))
    snapshot.update(
        {
            "objeto_principal": _ascii(
                _pick_first_str(
                    identification.get("objeto_principal"),
                    case_context.get("ativo"),
                    case_context.get("objeto"),
                )
                or "objeto_tecnico_principal"
            ),
            "localizacao": _ascii(
                _pick_first_str(
                    identification.get("localizacao"),
                    case_context.get("local"),
                )
                or "localizacao_tecnica_a_confirmar"
            ),
            "status_final": _ascii(
                _pick_first_str(
                    conclusion.get("status"),
                    (example.get("tokens") or {}).get("status_final"),
                    "ajuste",
                )
            ),
        }
    )
    return snapshot


def _build_asset_blueprint(manifest: dict[str, Any], example: dict[str, Any]) -> list[dict[str, str]]:
    family_key = str(manifest.get("family_key") or "")
    family_label = _ascii(manifest.get("nome_exibicao") or family_key)
    identification = example.get("identificacao") if isinstance(example.get("identificacao"), dict) else {}
    object_label = _ascii(
        _pick_first_str(
            identification.get("objeto_principal"),
            identification.get("codigo_interno"),
            family_label,
        )
    )
    slots = [
        item for item in list(manifest.get("required_slots_snapshot") or []) if isinstance(item, dict)
    ]
    cards: list[dict[str, str]] = [
        {
            "file_name": "IMG_001_visao_geral.png",
            "title": "Visao geral do caso",
            "subtitle": object_label or family_label,
            "caption": f"{family_label} · referencia sintetica",
        }
    ]
    for index, item in enumerate(slots[:5], start=2):
        label = _ascii(item.get("label") or item.get("item_id") or f"slot_{index}")
        cards.append(
            {
                "file_name": f"IMG_{index:03d}_{_slug(label)}.png",
                "title": label,
                "subtitle": object_label or family_label,
                "caption": _ascii(item.get("purpose") or "evidencia sintetica guiada pelo schema"),
            }
        )
    return cards[:6]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ):
        candidate = Path(path)
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _create_asset_image(asset_path: Path, card: dict[str, str], accent: tuple[int, int, int]) -> None:
    width, height = 1400, 880
    image = Image.new("RGB", (width, height), color=(248, 245, 238))
    draw = ImageDraw.Draw(image)
    for step in range(height):
        ratio = step / height
        tone = (
            int(248 - ratio * 28),
            int(245 - ratio * 18),
            int(238 - ratio * 10),
        )
        draw.line((0, step, width, step), fill=tone, width=1)
    draw.rounded_rectangle((72, 72, width - 72, height - 72), radius=36, fill=(255, 252, 248), outline=(42, 48, 57), width=4)
    draw.rectangle((72, 72, width - 72, 170), fill=(accent[0], accent[1], accent[2]))
    draw.rounded_rectangle((120, 220, width - 120, height - 160), radius=28, fill=(232, 236, 241), outline=(102, 112, 126), width=3)
    draw.line((170, 310, width - 170, 310), fill=(102, 112, 126), width=3)
    draw.line((170, 430, width - 170, 430), fill=(102, 112, 126), width=2)
    draw.line((170, 550, width - 170, 550), fill=(102, 112, 126), width=2)
    draw.ellipse((width - 330, 280, width - 170, 440), outline=accent, width=12)
    draw.rectangle((220, 620, 560, 700), outline=accent, width=6)
    draw.rectangle((610, 620, 1010, 700), outline=accent, width=6)
    draw.text((112, 102), _ascii(card["title"]).upper(), fill=(255, 255, 255), font=_font(36))
    draw.text((138, 248), _ascii(card["title"]), fill=(33, 39, 46), font=_font(42))
    draw.text((138, 340), _ascii(card["subtitle"]), fill=(78, 86, 96), font=_font(28))
    caption_lines = textwrap.wrap(_ascii(card["caption"]), width=58)[:3]
    y = 470
    for line in caption_lines:
        draw.text((138, y), line, fill=(60, 68, 78), font=_font(24))
        y += 38
    draw.text((138, height - 118), "REFERENCIA SINTETICA · TARIEL", fill=(90, 96, 104), font=_font(24))
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(asset_path, format="PNG")


def _build_pdf(
    pdf_path: Path,
    *,
    manifest: dict[str, Any],
    example: dict[str, Any],
    asset_files: list[Path],
) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    family_label = _ascii(manifest.get("nome_exibicao") or manifest.get("family_key") or "Familia")
    family_key = _ascii(manifest.get("family_key") or "")
    tokens = _as_dict(example.get("tokens"))
    identification = _as_dict(example.get("identificacao"))
    conclusion = _as_dict(example.get("conclusao"))
    case_context = _as_dict(example.get("case_context"))
    document_code = _ascii(
        _pick_first_str(
            tokens.get("document_code"),
            tokens.get("laudo_id"),
            f"SYN-{family_key.upper()}-001",
        )
    )
    object_label = _ascii(
        _pick_first_str(
            identification.get("objeto_principal"),
            identification.get("codigo_interno"),
            family_label,
        )
    )
    local_label = _ascii(
        _pick_first_str(
            identification.get("localizacao"),
            case_context.get("local"),
            "Localizacao tecnica a confirmar",
        )
    )
    status_final = _ascii(
        _pick_first_str(
            conclusion.get("status"),
            tokens.get("status_final"),
            "ajuste",
        )
    )
    summary_text = _ascii(_summary_text(example, conclusion))
    sections = [
        _ascii(item)
        for item in list(manifest.get("output_sections_snapshot") or [])
        if _pick_first_str(item)
    ][:10]

    def header(page_label: str, page_no: int, total_pages: int) -> None:
        c.setFillColorRGB(0.12, 0.18, 0.27)
        c.rect(0, height - 68, width, 68, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 17)
        c.drawString(40, height - 42, family_label)
        c.setFont("Helvetica", 9)
        c.drawRightString(width - 40, height - 42, f"{page_label} · {page_no}/{total_pages}")
        c.setFillColorRGB(0.3, 0.34, 0.4)
        c.setFont("Helvetica", 8)
        c.drawString(40, 18, "REFERENCIA SINTETICA · pacote interno Tariel")
        c.drawRightString(width - 40, 18, document_code)

    total_pages = 4

    header("Capa", 1, total_pages)
    c.setFillColorRGB(0.1, 0.12, 0.16)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(40, height - 118, "Baseline sintetica validada")
    c.setFont("Helvetica", 12)
    c.drawString(40, height - 145, f"Family key: {family_key}")
    c.drawString(40, height - 164, f"Codigo documental: {document_code}")
    c.drawString(40, height - 183, f"Status final: {status_final}")
    c.drawString(40, height - 210, f"Objeto principal: {object_label}")
    c.drawString(40, height - 229, f"Localizacao: {local_label}")
    c.setFont("Helvetica", 11)
    for idx, line in enumerate(textwrap.wrap(summary_text, width=85)[:5]):
        c.drawString(40, height - 280 - idx * 16, line)
    if asset_files:
        c.drawImage(ImageReader(str(asset_files[0])), 40, 160, width=515, height=280, preserveAspectRatio=True, mask="auto")
    c.showPage()

    header("Metodo", 2, total_pages)
    c.setFillColorRGB(0.12, 0.18, 0.27)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, height - 110, "Estrutura documental prevista")
    c.setFillColorRGB(0.12, 0.14, 0.18)
    c.setFont("Helvetica", 11)
    y = height - 138
    for section in sections[:8]:
        c.drawString(54, y, f"- {section}")
        y -= 16
    c.setFont("Helvetica-Bold", 15)
    c.drawString(40, y - 18, "Conclusao base")
    c.setFont("Helvetica", 11)
    y -= 42
    for line in textwrap.wrap(_ascii(conclusion.get("conclusao_tecnica") or summary_text), width=88)[:6]:
        c.drawString(40, y, line)
        y -= 15
    if len(asset_files) > 1:
        c.drawImage(ImageReader(str(asset_files[1])), 40, 72, width=250, height=190, preserveAspectRatio=True, mask="auto")
    if len(asset_files) > 2:
        c.drawImage(ImageReader(str(asset_files[2])), 312, 72, width=243, height=190, preserveAspectRatio=True, mask="auto")
    c.showPage()

    header("Evidencias", 3, total_pages)
    c.setFillColorRGB(0.12, 0.18, 0.27)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, height - 110, "Painel de evidencias sinteticas")
    positions = [
        (40, 430, 245, 160),
        (312, 430, 245, 160),
        (40, 220, 245, 160),
        (312, 220, 245, 160),
    ]
    for asset_path, (x, y, w, h) in zip(asset_files[2:6], positions):
        c.drawImage(ImageReader(str(asset_path)), x, y, width=w, height=h, preserveAspectRatio=True, mask="auto")
    c.setFillColorRGB(0.18, 0.2, 0.24)
    c.setFont("Helvetica", 10)
    c.drawString(40, 190, "As imagens sao sinteticas e existem apenas para orientar slots, blocos fotograficos e acabamento do PDF.")
    c.showPage()

    header("Fechamento", 4, total_pages)
    c.setFillColorRGB(0.12, 0.18, 0.27)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, height - 110, "Governanca desta baseline")
    c.setFillColorRGB(0.12, 0.14, 0.18)
    c.setFont("Helvetica", 11)
    closing_lines = [
        "Esta baseline foi produzida internamente para acelerar a calibracao da familia.",
        "Ela nao substitui material real, mas ja permite refinar template, overlay e narrativa tecnica.",
        "O proximo salto de qualidade continua vindo de casos aprovados e evidencias reais do cliente.",
        f"Template alvo: {_ascii(example.get('template_code') or manifest.get('template_codes', [''])[0])}",
        f"Data de geracao: {date.today().isoformat()}",
    ]
    y = height - 146
    for line in closing_lines:
        c.drawString(40, y, line)
        y -= 18
    c.setFont("Helvetica-Bold", 15)
    c.drawString(40, y - 16, "Checklist operacional")
    c.setFont("Helvetica", 11)
    y -= 42
    checklist = [
        "receber documentos finais reais da empresa",
        "receber modelo atual vazio",
        "comparar linguagem tecnica e anexos recorrentes",
        "revisar PDF final com base em caso aprovado",
    ]
    for line in checklist:
        c.drawString(54, y, f"- {line}")
        y -= 16
    c.save()


def _build_bundle(
    *,
    manifest: dict[str, Any],
    example: dict[str, Any],
    asset_cards: list[dict[str, str]],
    pdf_name: str,
) -> dict[str, Any]:
    family_key = str(manifest.get("family_key") or "")
    template_code = _pick_first_str(
        example.get("template_code"),
        *(manifest.get("template_codes") or []),
        family_key,
    )
    tokens = _as_dict(example.get("tokens"))
    conclusion = _as_dict(example.get("conclusao"))
    summary_text = _summary_text(example, conclusion)
    document_code = _pick_first_str(
        tokens.get("document_code"),
        tokens.get("laudo_id"),
        f"SYN-{family_key.upper()}-001",
    )
    status_final = _pick_first_str(
        conclusion.get("status"),
        tokens.get("status_final"),
        "ajuste",
    )
    return {
        "schema_type": "tariel_filled_reference_bundle",
        "schema_version": 1,
        "family_key": family_key,
        "template_code": template_code,
        "reference_id": f"{family_key}.synthetic.internal.v1",
        "source_kind": "synthetic_repo_baseline",
        "reference_summary": {
            "title": f"Baseline sintetica interna - {_ascii(manifest.get('nome_exibicao') or family_key)}",
            "document_code": _ascii(document_code),
            "status_final": _ascii(status_final),
            "pdf_file": f"pdf/{pdf_name}",
            "asset_files": [f"assets/{item['file_name']}" for item in asset_cards],
            "resumo": _ascii(summary_text),
        },
        "required_slots_snapshot": _build_reference_slots(manifest, example),
        "documental_sections_snapshot": [
            _ascii(item)
            for item in list(manifest.get("output_sections_snapshot") or [])
            if _pick_first_str(item)
        ],
        "notes": [
            "Conteudo integralmente sintetico, produzido internamente para bootstrap da familia.",
            "Nao substitui material real nem documento emitido pelo cliente.",
            "Serve para calibrar template mestre, overlay, PDF final e revisao guiada por Mesa/mobile.",
        ],
        "laudo_output_snapshot": example,
    }


def _build_manifest(*, family_key: str) -> dict[str, Any]:
    return {
        "schema_type": "filled_reference_package_manifest",
        "schema_version": 1,
        "family_key": family_key,
        "package_status": "synthetic_baseline",
        "source_kind": "synthetic_repo_baseline",
        "bundle_file": "tariel_filled_reference_bundle.json",
        "reference_count": 1,
        "notes": [
            "Pacote sintetico interno gerado pelo proprio repositorio Tariel.",
        ],
    }


def _zip_directory(source_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for candidate in sorted(path for path in source_dir.rglob("*") if path.is_file()):
            archive.write(candidate, candidate.relative_to(source_dir).as_posix())


def _generate_package_for_family(repo_root: Path, family_key: str, *, force: bool) -> dict[str, Any]:
    workspace_root, manifest, _, example = _load_family_inputs(repo_root, family_key)
    if _should_skip_workspace(workspace_root, force=force):
        return {
            "family_key": family_key,
            "workspace_root": workspace_root.as_posix(),
            "skipped": True,
            "reason": "baseline_already_validated",
        }

    asset_cards = _build_asset_blueprint(manifest, example)
    pdf_name = f"{family_key}_referencia_sintetica.pdf"

    with tempfile.TemporaryDirectory(prefix=f"tariel-synth-{family_key}-") as temp_dir:
        package_root = Path(temp_dir) / "output" / family_key
        assets_dir = package_root / "assets"
        pdf_dir = package_root / "pdf"
        accent_palette = {
            "nr13": (32, 76, 122),
            "nr12": (76, 96, 38),
            "nr20": (138, 82, 22),
            "nr33": (110, 40, 66),
        }
        accent = next(
            (value for prefix, value in accent_palette.items() if family_key.startswith(prefix)),
            (42, 78, 108),
        )
        asset_paths: list[Path] = []
        for card in asset_cards:
            asset_path = assets_dir / card["file_name"]
            _create_asset_image(asset_path, card, accent)
            asset_paths.append(asset_path)

        pdf_path = pdf_dir / pdf_name
        _build_pdf(pdf_path, manifest=manifest, example=example, asset_files=asset_paths)

        bundle = _build_bundle(
            manifest=manifest,
            example=example,
            asset_cards=asset_cards,
            pdf_name=pdf_name,
        )
        manifest_payload = _build_manifest(family_key=family_key)
        _write_json(package_root / "manifest.json", manifest_payload)
        _write_json(package_root / "tariel_filled_reference_bundle.json", bundle)

        zip_path = Path(temp_dir) / f"{family_key}.zip"
        _zip_directory(package_root.parent, zip_path)

        promoted = promote_reference_package_to_workspace(
            zip_path=zip_path,
            workspace_root=workspace_root,
            validation_date=date.today().isoformat(),
        )
        return {
            "family_key": family_key,
            "workspace_root": workspace_root.as_posix(),
            "zip_name": zip_path.name,
            "promoted": promoted,
            "asset_count": len(asset_cards),
            "pdf_name": pdf_name,
            "skipped": False,
        }


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    family_keys = [str(item).strip() for item in list(args.family_keys or []) if str(item).strip()] or list(DEFAULT_FAMILIES)
    results = [
        _generate_package_for_family(repo_root, family_key, force=bool(args.force))
        for family_key in family_keys
    ]
    print(json.dumps({"families": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
