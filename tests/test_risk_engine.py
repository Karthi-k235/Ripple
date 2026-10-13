import json
import sys
from pathlib import Path

from engine.risk import (
    run_selected_tests,
    select_relevant_tests,
    validate_risk,
)


def test_select_relevant_tests_deduplicates_and_reports_unmapped():
    selected, unmapped = select_relevant_tests(
        ["pricing.total", "pricing.tax", "checkout.run"],
        {
            "pricing.total": ["tests/test_pricing.py::test_total"],
            "pricing.tax": ["tests/test_pricing.py::test_tax"],
        },
    )

    assert selected == [
        "tests/test_pricing.py::test_tax",
        "tests/test_pricing.py::test_total",
    ]
    assert unmapped == ["checkout.run"]


def test_validate_risk_runs_mapped_tests_and_writes_json(tmp_path):
    repo = tmp_path
    project = repo / "demo_project"
    tests = repo / "tests"
    project.mkdir()
    tests.mkdir()
    (project / "pricing.py").write_text(
        "def calculate_tax(amount):\n    return amount * 0.18\n",
        encoding="utf-8",
    )
    (tests / "test_pricing.py").write_text(
        "def test_tax():\n    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )
    import git

    repository = git.Repo.init(repo)
    repository.index.add(["demo_project/pricing.py", "tests/test_pricing.py"])
    repository.index.commit("initial")
    (project / "pricing.py").write_text(
        "def calculate_tax(amount):\n    return amount * 0.20\n",
        encoding="utf-8",
    )

    report_path = repo / "reports" / "risk.json"
    report = validate_risk(
        repo,
        project,
        {"pricing.calculate_tax": ["tests/test_pricing.py::test_tax"]},
        timeout=10,
        report_path=report_path,
    )

    assert report["changed_functions"] == ["pricing.calculate_tax"]
    assert report["selected_tests"] == ["tests/test_pricing.py::test_tax"]
    assert report["test_result"]["status"] == "passed"
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_run_selected_tests_reports_timeout(tmp_path, monkeypatch):
    def timeout(*args, **kwargs):
        import subprocess
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output=b"partial")

    monkeypatch.setattr("engine.risk.subprocess.run", timeout)
    result = run_selected_tests(tmp_path, ["tests/test_slow.py::test_slow"], timeout=1)

    assert result["status"] == "timed_out"
    assert result["timed_out"] is True
    assert result["stdout"] == "partial"


def test_empty_selection_does_not_run_pytest(tmp_path, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("pytest should not run for an empty selection")

    monkeypatch.setattr("engine.risk.subprocess.run", unexpected)
    assert run_selected_tests(tmp_path, []) ["status"] == "not_run"
