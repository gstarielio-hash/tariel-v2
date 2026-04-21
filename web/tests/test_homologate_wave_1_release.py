from __future__ import annotations

from scripts.homologate_wave_1_release import (
    WAVE_1_PENDING_FAMILIES,
    WAVE_1_SCOPED_FAMILIES,
    build_wave_1_release_markdown,
    build_wave_1_release_steps,
)


def test_build_wave_1_release_steps_includes_gate_and_homologation() -> None:
    steps = build_wave_1_release_steps(
        python_executable="python3",
        skip_tests=False,
        skip_provisioning=False,
    )

    assert [step.key for step in steps] == [
        "runtime_unit",
        "fixtures_regression",
        "pdf_smoke",
        "route_gate",
        "catalog_homologation",
    ]
    assert steps[0].command[-2:] == ("tests/test_catalog_pdf_templates.py", "-q")
    assert "tests/test_catalog_wave1_fixtures.py" in steps[1].command
    assert "tests/test_catalog_wave1_pdf_smoke.py" in steps[2].command
    assert "tests/test_regras_rotas_criticas.py" in steps[3].command
    assert steps[4].command[-1] == "scripts/homologate_wave_1_core_templates.py"


def test_build_wave_1_release_markdown_highlights_scope_without_pending_family() -> None:
    report = {
        "finished_at": "2026-04-09T18:00:00+00:00",
        "ok": True,
        "familias_homologadas_no_gate": len(WAVE_1_SCOPED_FAMILIES),
        "wave_1_scoped_families": list(WAVE_1_SCOPED_FAMILIES),
        "wave_1_pending_families": list(WAVE_1_PENDING_FAMILIES),
        "catalog_doc_path": "/tmp/onda_1_homologacao_profissional.md",
        "report_json_path": "/tmp/report.json",
        "report_md_path": "/tmp/report.md",
        "homologation_summary": {
            "familias_homologadas": 12,
            "familias_ativas": 12,
            "demos_emitidas": 12,
            "doc_saida": "/tmp/onda_1_homologacao_profissional.md",
        },
        "steps": [
            {
                "label": "Runtime canônico por família",
                "ok": True,
                "duration_seconds": 12.4,
                "command": ("python3", "-m", "pytest", "tests/test_catalog_pdf_templates.py", "-q"),
                "stdout_log_path": "/tmp/01.stdout.log",
                "stderr_log_path": "/tmp/01.stderr.log",
                "stdout_tail": "12 passed",
                "stderr_tail": "",
            }
        ],
    }

    markdown = build_wave_1_release_markdown(report=report)

    assert "Onda 1: Homologacao Completa" in markdown
    assert "nr13_inspecao_caldeira" in markdown
    assert "familias ainda fora deste gate" not in markdown
    assert "/tmp/onda_1_homologacao_profissional.md" in markdown
    assert "12 passed" in markdown
