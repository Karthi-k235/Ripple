"""Git based risk analysis and targeted pytest execution."""

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from engine.dependencies import build_dependency_graph
from engine.git_analyzer import detect_changed_functions
from engine.impact import find_affected_functions
from engine.parser import parse_python_project


def select_relevant_tests(functions, test_mapping):
    """Select unique pytest node IDs mapped to changed or affected functions.

    The mapping is explicit because static call analysis cannot reliably infer
    which tests cover a function. Unmapped functions are reported as limits.
    """
    selected = set()
    unmapped = []
    for function in sorted(set(functions)):
        node_ids = test_mapping.get(function, ())
        if node_ids:
            selected.update(node_ids)
        else:
            unmapped.append(function)
    return sorted(selected), unmapped


def _text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _read_test_outcomes(report_file, node_ids):
    """Translate pytest's JUnit report into outcomes for selected node IDs."""
    try:
        root = ET.parse(report_file).getroot()
    except (ET.ParseError, OSError):
        return []

    cases_by_name = {}
    for case in root.iter("testcase"):
        status = "passed"
        detail = ""
        for child in case:
            if child.tag in {"failure", "error"}:
                status = "failed"
                detail = child.attrib.get("message") or (child.text or "").strip()
                break
            if child.tag == "skipped":
                status = "skipped"
                detail = child.attrib.get("message") or (child.text or "").strip()
        cases_by_name.setdefault(case.attrib.get("name", ""), []).append(
            {"status": status, "detail": detail}
        )

    outcomes = []
    for node_id in node_ids:
        test_name = node_id.rsplit("::", 1)[-1]
        matching_cases = cases_by_name.get(test_name, [])
        if matching_cases:
            for case in matching_cases:
                outcomes.append({"test": node_id, **case})
        else:
            outcomes.append({"test": node_id, "status": "not_reported", "detail": ""})
    return outcomes


def run_selected_tests(repo_root, node_ids, timeout=60):
    """Run selected pytest node IDs; an empty selection is explicitly not run."""
    if not node_ids:
        return {
            "status": "not_run",
            "returncode": None,
            "timed_out": False,
            "command": [],
            "stdout": "",
            "stderr": "",
        }

    with tempfile.TemporaryDirectory(prefix="ripple-pytest-") as temp_dir:
        junit_report = Path(temp_dir) / "results.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "--junitxml",
            str(junit_report),
            *node_ids,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(Path(repo_root).resolve()),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return {
                "status": "passed" if completed.returncode == 0 else "failed",
                "returncode": completed.returncode,
                "timed_out": False,
                "command": command,
                "stdout": _text(completed.stdout),
                "stderr": _text(completed.stderr),
                "test_outcomes": _read_test_outcomes(junit_report, node_ids),
            }
        except subprocess.TimeoutExpired as error:
            return {
                "status": "timed_out",
                "returncode": None,
                "timed_out": True,
                "command": command,
                "stdout": _text(error.stdout),
                "stderr": _text(error.stderr),
                "test_outcomes": _read_test_outcomes(junit_report, node_ids),
            }


def validate_risk(
    repo_root,
    project_root,
    test_mapping,
    timeout=60,
    report_path=None,
):
    """Analyze tracked changes, run mapped tests, and return a JSON-ready report.

    Git changes are compared with HEAD, so untracked files are not analyzed.
    Function discovery currently covers module-level functions only.
    """
    repo = Path(repo_root).resolve()
    project = Path(project_root).resolve()
    function_index = parse_python_project(project)
    graph = build_dependency_graph(function_index)
    changes = detect_changed_functions(repo, project, function_index)

    affected = set()
    for changed in changes["changed_functions"]:
        affected.update(find_affected_functions(graph, changed))
    affected_functions = sorted(affected)
    impacted = sorted(set(changes["changed_functions"]) | affected)
    selected_tests, unmapped_functions = select_relevant_tests(
        impacted, test_mapping
    )
    test_result = run_selected_tests(repo, selected_tests, timeout=timeout)

    report = {
        "schema_version": 1,
        "repository": str(repo),
        "project": str(project),
        "changed_files": changes["changed_files"],
        "changed_functions": changes["changed_functions"],
        "affected_functions": affected_functions,
        "impacted_functions": impacted,
        "selected_tests": selected_tests,
        "unmapped_files": changes["unmapped_files"],
        "unmapped_functions": unmapped_functions,
        "test_result": test_result,
        "analysis_limits": [
            "Only tracked working-tree changes relative to HEAD are analyzed; untracked files are excluded.",
            "Only module-level Python functions are discovered.",
            "Test selection depends on the caller-provided explicit function-to-test mapping and may miss coverage omitted from that mapping.",
        ],
    }

    if report_path is not None:
        destination = Path(report_path)
        if not destination.is_absolute():
            destination = repo / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report
