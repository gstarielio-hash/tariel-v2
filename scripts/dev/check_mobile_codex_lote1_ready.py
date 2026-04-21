#!/usr/bin/env python3
"""Valida se o lote 1 do agente mobile está pronto para revisão humana."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKLIST_PATH = REPO_ROOT / "docs" / "mobile_lote1_acceptance_checklist.md"
REPORT_PATH = REPO_ROOT / "docs" / "mobile_lote1_delivery_report.md"

UNSET_VALUES = {
    "",
    "-",
    "pendente",
    "pending",
    "todo",
    "tbd",
    "n/a",
    "na",
}

REQUIRED_EVIDENCE_LABELS = [
    "Chat livre evidência",
    "Guiado NR10 evidência",
    "Guiado NR12 evidência",
    "Guiado NR13 evidência",
    "Guiado NR35 evidência",
    "Configurações evidência",
    "Smoke/validação evidência",
]

REQUIRED_SECTIONS = [
    "## Resumo executivo",
    "## Evidências principais",
    "## Melhorias visuais aplicadas",
    "## Bugs silenciosos tratados",
    "## Riscos residuais",
    "## Próximo passo recomendado",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"Arquivo obrigatório ausente: {path}")


def normalize_value(value: str) -> str:
    return str(value or "").strip().lower().rstrip(".")


def validate_checklist(content: str) -> list[str]:
    errors: list[str] = []
    unchecked = re.findall(r"^\s*[-*]\s*\[ \]\s+(.+?)\s*$", content, flags=re.MULTILINE)
    for item in unchecked:
        errors.append(f"Checklist ainda possui item aberto: {item}")
    return errors


def validate_report(content: str) -> list[str]:
    errors: list[str] = []

    status_match = re.search(r"^Status:\s*(.+?)\s*$", content, flags=re.MULTILINE)
    status = status_match.group(1).strip() if status_match else ""
    if status != "ready_for_human_review":
        errors.append(
            "Relatório de entrega deve conter `Status: ready_for_human_review`."
        )

    for section in REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"Seção obrigatória ausente no relatório: {section}")

    for label in REQUIRED_EVIDENCE_LABELS:
        match = re.search(rf"^\s*-\s*{re.escape(label)}:\s*(.+?)\s*$", content, flags=re.MULTILINE)
        if not match:
            errors.append(f"Evidência obrigatória ausente no relatório: {label}")
            continue
        value = normalize_value(match.group(1))
        if value in UNSET_VALUES:
            errors.append(f"Evidência ainda não preenchida: {label}")

    for heading in (
        "## Resumo executivo",
        "## Melhorias visuais aplicadas",
        "## Bugs silenciosos tratados",
        "## Riscos residuais",
        "## Próximo passo recomendado",
    ):
        pattern = rf"{re.escape(heading)}\n\n(.+?)(?:\n## |\Z)"
        match = re.search(pattern, content, flags=re.DOTALL)
        body = match.group(1).strip() if match else ""
        if normalize_value(body) in UNSET_VALUES:
            errors.append(f"Conteúdo ainda não preenchido: {heading}")

    return errors


def main() -> int:
    checklist = read_text(CHECKLIST_PATH)
    report = read_text(REPORT_PATH)

    errors = [
        *validate_checklist(checklist),
        *validate_report(report),
    ]

    if errors:
        print("Mobile lote 1 readiness: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Mobile lote 1 readiness: PASS")
    print(f"- checklist: {CHECKLIST_PATH}")
    print(f"- report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
