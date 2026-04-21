from __future__ import annotations

from scripts.homologate_wave_4_core_governance import (
    EXPECTED_WAVE_4_RULES,
    WAVE_4_SCOPED_NORMAS,
    build_wave_4_governance_doc,
    collect_wave_4_normas,
    detect_wave_4_family_schema_artifacts,
    validate_wave_4_governance,
)


def test_wave_4_registry_scope_matches_expected_normas() -> None:
    normas = collect_wave_4_normas()

    assert tuple(item["code"] for item in normas) == WAVE_4_SCOPED_NORMAS


def test_wave_4_registry_rules_remain_non_sellable() -> None:
    normas = collect_wave_4_normas()

    for item in normas:
        expected = EXPECTED_WAVE_4_RULES[item["code"]]
        assert item["current_status"] == expected["current_status"]
        assert item["product_strategy"] == expected["product_strategy"]
        assert item["official_status"] == expected["official_status"]
        assert item["suggested_families"] == []


def test_wave_4_has_no_family_schema_artifacts() -> None:
    assert detect_wave_4_family_schema_artifacts() == []


def test_wave_4_doc_builder_highlights_governance_closure() -> None:
    normas = collect_wave_4_normas()
    summary = validate_wave_4_governance(normas)

    document = build_wave_4_governance_doc(normas=normas, summary=summary)

    assert "Onda 4: Fechamento de Governanca" in document
    assert "NR02" in document
    assert "NR28" in document
    assert "sem criacao de templates vendaveis" in document
    assert "support_only" in document
