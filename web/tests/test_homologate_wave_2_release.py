from __future__ import annotations

from scripts.homologate_wave_2_release import (
    WAVE_2_PENDING_FAMILIES,
    WAVE_2_SCOPED_FAMILIES,
    build_wave_2_release_markdown,
    build_wave_2_release_steps,
)


def test_build_wave_2_release_steps_includes_gate_and_homologation() -> None:
    steps = build_wave_2_release_steps(
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
    assert "tests/test_catalog_pdf_templates.py" in steps[0].command
    assert steps[0].command[-1].startswith("nr18 or nr22")
    assert "tests/test_catalog_wave2_fixtures.py" in steps[1].command
    assert "tests/test_catalog_wave2_pdf_smoke.py" in steps[2].command
    assert "tests/test_regras_rotas_criticas.py" in steps[3].command
    assert steps[4].command[-1] == "scripts/homologate_wave_2_core_templates.py"


def test_build_wave_2_release_markdown_highlights_scope_without_pending_family() -> None:
    report = {
        "finished_at": "2026-04-09T18:30:00+00:00",
        "ok": True,
        "familias_homologadas_no_gate": len(WAVE_2_SCOPED_FAMILIES),
        "wave_2_scoped_families": list(WAVE_2_SCOPED_FAMILIES),
        "wave_2_pending_families": list(WAVE_2_PENDING_FAMILIES),
        "catalog_doc_path": "/tmp/onda_2_homologacao_profissional.md",
        "report_json_path": "/tmp/report.json",
        "report_md_path": "/tmp/report.md",
        "homologation_summary": {
            "familias_homologadas": 13,
            "familias_ativas": 13,
            "demos_emitidas": 13,
            "doc_saida": "/tmp/onda_2_homologacao_profissional.md",
        },
        "steps": [
            {
                "label": "Runtime canônico por família da onda 2",
                "ok": True,
                "duration_seconds": 8.1,
                "command": ("python3", "-m", "pytest", "tests/test_catalog_pdf_templates.py", "-q", "-k", "nr18 or nr22"),
                "stdout_log_path": "/tmp/01.stdout.log",
                "stderr_log_path": "/tmp/01.stderr.log",
                "stdout_tail": "13 passed",
                "stderr_tail": "",
            }
        ],
    }

    markdown = build_wave_2_release_markdown(report=report)

    assert "Onda 2: Homologacao Completa" in markdown
    assert "nr38_inspecao_limpeza_urbana_residuos" in markdown
    assert "familias ainda fora deste gate" not in markdown
    assert "/tmp/onda_2_homologacao_profissional.md" in markdown
    assert "13 passed" in markdown
