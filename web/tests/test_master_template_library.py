from __future__ import annotations

import json
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_master_template_library_contains_ready_inspection_standard() -> None:
    registry = json.loads(
        (_repo_root() / "docs" / "master_templates" / "library_registry.json").read_text(encoding="utf-8")
    )

    assert registry["version"] == 1
    assert registry["templates"][0]["master_template_id"] == "inspection_conformity"
    assert registry["templates"][0]["status"] == "ready"


def test_inspection_conformity_master_template_has_required_sections() -> None:
    payload = json.loads(
        (_repo_root() / "docs" / "master_templates" / "inspection_conformity.template_master.json").read_text(
            encoding="utf-8"
        )
    )

    headings = []
    for node in payload["documento_editor_json"]["doc"]["content"]:
        if node.get("type") == "heading":
            texts = []
            for part in node.get("content") or []:
                if part.get("type") == "text":
                    texts.append(str(part.get("text") or ""))
            headings.append("".join(texts))

    assert payload["master_template_id"] == "inspection_conformity"
    assert "1. Capa / Folha de Rosto" in headings
    assert "2. Controle Documental / Sumario / Ficha do Documento" in headings
    assert "6. Checklist Tecnico Item a Item" in headings
    assert "9. Conclusao" in headings
    assert "11. Assinaturas e Responsabilidade Tecnica" in headings
    assert "12. Anexos" in headings
