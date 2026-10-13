import pytest

from dashboard_helpers import (
    DEFAULT_MAPPING_TEXT,
    dependency_layout,
    filter_graph_data,
    parse_test_mapping,
    summarize_validation,
    validate_analysis_paths,
)


def test_mapping_parser_keeps_explicit_defaults_and_explains_invalid_json():
    mapping = parse_test_mapping(DEFAULT_MAPPING_TEXT)
    assert mapping["pricing.calculate_tax"] == [
        "tests/test_demo_project.py::test_calculate_tax"
    ]
    with pytest.raises(ValueError, match="line 1, column"):
        parse_test_mapping('{"pricing.tax": [}')
    with pytest.raises(ValueError, match="qualified function names"):
        parse_test_mapping('["not a mapping"]')


def test_path_validation_checks_directories_and_project_containment(tmp_path):
    repo = tmp_path / "repo"
    project = repo / "src"
    project.mkdir(parents=True)
    assert validate_analysis_paths(repo, project) == (repo.resolve(), project.resolve())
    with pytest.raises(ValueError, match="does not exist"):
        validate_analysis_paths(repo, repo / "missing")
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="inside the repository"):
        validate_analysis_paths(repo, outside)


def test_graph_filters_nodes_and_prunes_edges():
    data = {
        "nodes": [
            {"id": "pricing.tax", "status": "changed"},
            {"id": "checkout.run", "status": "affected"},
            {"id": "utils.log", "status": "other"},
        ],
        "edges": [
            {"source": "checkout.run", "target": "pricing.tax"},
            {"source": "utils.log", "target": "checkout.run"},
        ],
        "total_nodes": 3,
        "omitted_nodes": 0,
    }
    filtered = filter_graph_data(data, query="pricing", impact_only=True)
    assert [node["id"] for node in filtered["nodes"]] == ["pricing.tax"]
    assert filtered["edges"] == []
    assert filtered["filtered_nodes"] == 2


def test_validation_summary_does_not_treat_no_tests_as_success():
    empty = summarize_validation(
        {"selected_tests": [], "test_result": {"status": "not_run", "test_outcomes": []}}
    )
    assert empty["label"] == "No mapped tests"
    assert empty["passed"] == 0
    failed = summarize_validation(
        {
            "selected_tests": ["tests/test_x.py::test_x"],
            "test_result": {
                "status": "failed",
                "test_outcomes": [{"test": "tests/test_x.py::test_x", "status": "failed"}],
            },
        }
    )
    assert failed["label"] == "Failed"
    assert failed["failed"] == 1


def test_dependency_layout_places_callers_before_callees_deterministically():
    edges = [
        ("receipt.print", "checkout.run"),
        ("checkout.run", "pricing.tax"),
        ("main.run", "checkout.run"),
    ]
    first = dependency_layout(["pricing.tax", "main.run", "checkout.run", "receipt.print"], edges)
    second = dependency_layout(["receipt.print", "checkout.run", "main.run", "pricing.tax"], edges)
    assert first == second
    assert first["receipt.print"][0] < first["checkout.run"][0] < first["pricing.tax"][0]
    assert first["main.run"][0] < first["checkout.run"][0]
