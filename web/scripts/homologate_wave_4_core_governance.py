from __future__ import annotations

import json
from pathlib import Path
from typing import Any


WEB_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = WEB_DIR.parents[0]
DOCS_DIR = REPO_ROOT / "docs"
FAMILY_SCHEMAS_DIR = DOCS_DIR / "family_schemas"
REGISTRY_PATH = DOCS_DIR / "nr_programming_registry.json"
OUTPUT_DOC_PATH = WEB_DIR / "docs" / "onda_4_fechamento_governanca.md"

WAVE_4_SCOPED_NORMAS: tuple[str, ...] = ("nr02", "nr03", "nr27", "nr28")
EXPECTED_WAVE_4_RULES: dict[str, dict[str, str]] = {
    "nr02": {
        "current_status": "revoked",
        "product_strategy": "revogada",
        "official_status": "revogada",
    },
    "nr03": {
        "current_status": "support_only",
        "product_strategy": "support_only",
        "official_status": "vigente",
    },
    "nr27": {
        "current_status": "revoked",
        "product_strategy": "revogada",
        "official_status": "revogada",
    },
    "nr28": {
        "current_status": "support_only",
        "product_strategy": "support_only",
        "official_status": "vigente",
    },
}


def load_registry_payload() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def collect_wave_4_normas(payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = payload or load_registry_payload()
    normas = [
        item
        for item in registry.get("normas") or []
        if str(item.get("programming_wave") or "") == "wave_4"
    ]
    return sorted(normas, key=lambda item: int(item.get("nr") or 0))


def detect_wave_4_family_schema_artifacts() -> list[str]:
    artifacts: list[str] = []
    for code in WAVE_4_SCOPED_NORMAS:
        artifacts.extend(str(path) for path in sorted(FAMILY_SCHEMAS_DIR.glob(f"{code}_*")))
    return artifacts


def validate_wave_4_governance(normas: list[dict[str, Any]]) -> dict[str, Any]:
    codes = [str(item.get("code") or "").strip().lower() for item in normas]
    if tuple(codes) != WAVE_4_SCOPED_NORMAS:
        raise RuntimeError(
            f"O escopo da wave_4 mudou. Esperado={WAVE_4_SCOPED_NORMAS} atual={tuple(codes)}"
        )

    for item in normas:
        code = str(item.get("code") or "").strip().lower()
        expected = EXPECTED_WAVE_4_RULES[code]
        for field, expected_value in expected.items():
            current_value = str(item.get(field) or "").strip().lower()
            if current_value != expected_value:
                raise RuntimeError(
                    f"{code}.{field} divergente. Esperado={expected_value} atual={current_value}"
                )
        if item.get("suggested_families"):
            raise RuntimeError(f"{code} nao pode expor suggested_families na wave_4.")

    artifacts = detect_wave_4_family_schema_artifacts()
    if artifacts:
        raise RuntimeError(
            "A wave_4 nao pode ter family_schemas vendaveis: " + ", ".join(artifacts)
        )

    return {
        "normas_fechadas": len(normas),
        "normas_revogadas": sum(
            1 for item in normas if str(item.get("current_status") or "").strip().lower() == "revoked"
        ),
        "normas_support_only": sum(
            1
            for item in normas
            if str(item.get("current_status") or "").strip().lower() == "support_only"
        ),
        "familias_catalogadas_detectadas": len(artifacts),
    }


def build_wave_4_governance_doc(
    *,
    normas: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Onda 4: Fechamento de Governanca",
        "",
        "Fechamento canônico da Onda 4, consolidando normas revogadas e itens de apoio/compliance fora da biblioteca vendável.",
        "",
        "## Normas cobertas",
        "",
        "| NR | Titulo | Estrategia | Status atual |",
        "| --- | --- | --- | --- |",
    ]
    for item in normas:
        lines.append(
            f"| `{str(item.get('code') or '').upper()}` | {str(item.get('title') or '').strip()} | "
            f"`{str(item.get('product_strategy') or '').strip()}` | "
            f"`{str(item.get('current_status') or '').strip()}` |"
        )
    lines.extend(
        [
            "",
            "## Encerramento",
            "",
            "- a Onda 4 foi encerrada sem criacao de templates vendaveis;",
            "- normas revogadas permanecem fora do catalogo;",
            "- normas de apoio/compliance permanecem como suporte operacional, nao como biblioteca primaria de laudos;",
            f"- normas fechadas neste gate: `{summary['normas_fechadas']}`;",
            f"- itens `support_only`: `{summary['normas_support_only']}`;",
            f"- itens `revoked`: `{summary['normas_revogadas']}`;",
            "",
            "## Escopo do fechamento",
            "",
            "- bloco canônico: `Governanca e excecoes`;",
            f"- documento gerado automaticamente a partir do registro nacional: `{REGISTRY_PATH}`;",
            f"- artefato de saida: `{OUTPUT_DOC_PATH}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    normas = collect_wave_4_normas()
    summary = validate_wave_4_governance(normas)
    OUTPUT_DOC_PATH.write_text(
        build_wave_4_governance_doc(normas=normas, summary=summary),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                **summary,
                "normas_no_gate": list(WAVE_4_SCOPED_NORMAS),
                "doc_saida": str(OUTPUT_DOC_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
