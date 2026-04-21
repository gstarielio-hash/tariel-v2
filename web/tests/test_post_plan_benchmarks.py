from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_benchmark_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_post_plan_benchmarks.py"
    spec = importlib.util.spec_from_file_location("run_post_plan_benchmarks", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_post_plan_benchmark_summary_tem_estatisticas_ordenadas() -> None:
    module = _load_benchmark_module()
    summary = module.summarize_samples(samples_ms=[9.0, 5.0, 7.0], iterations=3, warmups=1)

    assert summary["sample_count"] == 3
    assert summary["min_ms"] == 5.0
    assert summary["median_ms"] == 7.0
    assert summary["max_ms"] == 9.0
    assert summary["samples_ms"] == [5.0, 7.0, 9.0]


def test_post_plan_benchmarks_executam_superficies_criticas() -> None:
    module = _load_benchmark_module()
    summary = module.run_post_plan_benchmarks(iterations=1, warmups=0)

    benchmark_names = {item["name"] for item in summary["benchmarks"]}
    assert summary["status"] == "ok"
    assert benchmark_names == {
        "chat_messages_request",
        "review_package_request",
        "document_pdf_request",
    }
    for item in summary["benchmarks"]:
        assert item["status"] == "ok"
        assert item["stats"]["sample_count"] == 1
        assert item["last_observation"]["status_code"] == 200


def test_post_plan_benchmarks_nao_dependem_do_cwd_do_web(monkeypatch) -> None:
    module = _load_benchmark_module()
    monkeypatch.chdir(module.REPO_ROOT)

    summary = module.run_post_plan_benchmarks(iterations=1, warmups=0)

    assert summary["status"] == "ok"
