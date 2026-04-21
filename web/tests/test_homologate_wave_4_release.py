from __future__ import annotations

from scripts.homologate_wave_4_release import (
    WAVE_4_PENDING_NORMAS,
    WAVE_4_SCOPED_NORMAS,
    build_wave_4_release_markdown,
    build_wave_4_release_steps,
)


def test_build_wave_4_release_steps_includes_governance_gate_and_closure() -> None:
    steps = build_wave_4_release_steps(
        python_executable="python3",
        skip_tests=False,
        skip_provisioning=False,
    )

    assert [step.key for step in steps] == ["governance_gate", "governance_closure"]
    assert "tests/test_catalog_wave4_governance.py" in steps[0].command
    assert steps[1].command[-1] == "scripts/homologate_wave_4_core_governance.py"


def test_build_wave_4_release_markdown_highlights_scope_without_pending_norma() -> None:
    report = {
        "finished_at": "2026-04-09T19:30:00+00:00",
        "ok": True,
        "normas_fechadas_no_gate": len(WAVE_4_SCOPED_NORMAS),
        "wave_4_scoped_normas": list(WAVE_4_SCOPED_NORMAS),
        "wave_4_pending_normas": list(WAVE_4_PENDING_NORMAS),
        "catalog_doc_path": "/tmp/onda_4_fechamento_governanca.md",
        "report_json_path": "/tmp/report.json",
        "report_md_path": "/tmp/report.md",
        "homologation_summary": {
            "normas_fechadas": 4,
            "normas_revogadas": 2,
            "normas_support_only": 2,
            "familias_catalogadas_detectadas": 0,
            "doc_saida": "/tmp/onda_4_fechamento_governanca.md",
        },
        "steps": [
            {
                "label": "Gate de governanca da onda 4",
                "ok": True,
                "duration_seconds": 1.3,
                "command": ("python3", "-m", "pytest", "tests/test_catalog_wave4_governance.py", "-q"),
                "stdout_log_path": "/tmp/01.stdout.log",
                "stderr_log_path": "/tmp/01.stderr.log",
                "stdout_tail": "4 passed",
                "stderr_tail": "",
            }
        ],
    }

    markdown = build_wave_4_release_markdown(report=report)

    assert "Onda 4: Fechamento de Governanca" in markdown
    assert "nr28" in markdown
    assert "normas ainda fora deste gate" not in markdown
    assert "/tmp/onda_4_fechamento_governanca.md" in markdown
    assert "4 passed" in markdown
