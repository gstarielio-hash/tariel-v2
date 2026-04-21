from __future__ import annotations

from scripts.homologate_wave_3_release import (
    WAVE_3_PENDING_FAMILIES,
    WAVE_3_SCOPED_FAMILIES,
    build_wave_3_release_markdown,
    build_wave_3_release_steps,
)


def test_build_wave_3_release_steps_includes_gate_and_homologation() -> None:
    steps = build_wave_3_release_steps(
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
    assert "tests/test_catalog_wave3_runtime.py" in steps[0].command
    assert "tests/test_catalog_wave3_fixtures.py" in steps[1].command
    assert "tests/test_catalog_wave3_pdf_smoke.py" in steps[2].command
    assert "tests/test_catalog_wave3_routes.py" in steps[3].command
    assert steps[4].command[-1] == "scripts/homologate_wave_3_core_templates.py"


def test_build_wave_3_release_markdown_highlights_scope_without_pending_family() -> None:
    report = {
        "finished_at": "2026-04-09T18:30:00+00:00",
        "ok": True,
        "familias_homologadas_no_gate": len(WAVE_3_SCOPED_FAMILIES),
        "wave_3_scoped_families": list(WAVE_3_SCOPED_FAMILIES),
        "wave_3_pending_families": list(WAVE_3_PENDING_FAMILIES),
        "catalog_doc_path": "/tmp/onda_3_homologacao_profissional.md",
        "report_json_path": "/tmp/report.json",
        "report_md_path": "/tmp/report.md",
        "homologation_summary": {
            "familias_homologadas": 22,
            "familias_ativas": 22,
            "demos_emitidas": 22,
            "doc_saida": "/tmp/onda_3_homologacao_profissional.md",
        },
        "steps": [
            {
                "label": "Runtime canônico por família da onda 3",
                "ok": True,
                "duration_seconds": 8.1,
                "command": ("python3", "-m", "pytest", "tests/test_catalog_wave3_runtime.py", "-q"),
                "stdout_log_path": "/tmp/01.stdout.log",
                "stderr_log_path": "/tmp/01.stderr.log",
                "stdout_tail": "22 passed",
                "stderr_tail": "",
            }
        ],
    }

    markdown = build_wave_3_release_markdown(report=report)

    assert "Onda 3: Homologacao Completa" in markdown
    assert "nr26_sinalizacao_seguranca" in markdown
    assert "familias ainda fora deste gate" not in markdown
    assert "/tmp/onda_3_homologacao_profissional.md" in markdown
    assert "22 passed" in markdown
