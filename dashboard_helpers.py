"""Small, pure helpers used by Ripple's Streamlit presentation layer."""

import json
from pathlib import Path

import networkx as nx


DEFAULT_MAPPING = {
    "pricing.calculate_tax": ["tests/test_demo_project.py::test_calculate_tax"],
    "pricing.calculate_total": ["tests/test_demo_project.py::test_calculate_total"],
    "checkout.checkout": ["tests/test_demo_project.py::test_checkout"],
    "receipt.print_receipt": ["tests/test_demo_project.py::test_print_receipt"],
    "main.run": ["tests/test_demo_project.py::test_main_run"],
}

DEFAULT_MAPPING_TEXT = json.dumps(DEFAULT_MAPPING, indent=2)


def parse_test_mapping(mapping_text):
    """Parse the explicit function-to-pytest-node mapping or explain its shape."""
    try:
        mapping = json.loads(mapping_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Mapping JSON is invalid at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    if not isinstance(mapping, dict) or any(
        not isinstance(function, str)
        or not function.strip()
        or not isinstance(tests, list)
        or any(not isinstance(test, str) or not test.strip() for test in tests)
        for function, tests in mapping.items()
    ):
        raise ValueError(
            "Mapping must be a JSON object of qualified function names to lists of pytest node IDs."
        )
    return mapping


def validate_analysis_paths(repo_root, project_root):
    """Resolve configured paths and return actionable configuration errors."""
    repo = Path(repo_root).expanduser().resolve()
    project = Path(project_root).expanduser().resolve()
    if not repo.is_dir():
        raise ValueError(f"Repository folder does not exist or is not a directory: {repo}")
    if not project.is_dir():
        raise ValueError(f"Python source folder does not exist or is not a directory: {project}")
    try:
        project.relative_to(repo)
    except ValueError as error:
        raise ValueError("Python source folder must be inside the repository folder.") from error
    return repo, project


def filter_graph_data(graph_data, query="", statuses=None, impact_only=False):
    """Apply user-selected graph filters while retaining only valid visible edges."""
    statuses = set(statuses or {"changed", "affected", "other"})
    normalized_query = query.strip().casefold()
    kept = {
        node["id"]
        for node in graph_data.get("nodes", [])
        if node.get("status") in statuses
        and (not impact_only or node.get("status") in {"changed", "affected"})
        and (not normalized_query or normalized_query in node["id"].casefold())
    }
    nodes = [node for node in graph_data.get("nodes", []) if node["id"] in kept]
    edges = [
        edge
        for edge in graph_data.get("edges", [])
        if edge["source"] in kept and edge["target"] in kept
    ]
    return {**graph_data, "nodes": nodes, "edges": edges, "filtered_nodes": len(graph_data.get("nodes", [])) - len(nodes)}


def summarize_validation(report):
    """Summarize actual test evidence without equating an empty run with success."""
    result = (report or {}).get("test_result", {})
    selected = (report or {}).get("selected_tests", [])
    status = result.get("status", "not_run")
    outcomes = result.get("test_outcomes", [])
    counts = {key: 0 for key in ("passed", "failed", "skipped", "timed_out", "not_reported")}
    for outcome in outcomes:
        label = outcome.get("status", "not_reported")
        counts[label if label in counts else "not_reported"] += 1
    if not selected:
        label = "No mapped tests"
    else:
        label = {
            "passed": "Passed",
            "failed": "Failed",
            "timed_out": "Timed out",
            "not_run": "Not run",
        }.get(status, status.replace("_", " ").title())
        if status == "timed_out":
            counts["timed_out"] = max(counts["timed_out"], len(selected) - counts["passed"] - counts["failed"] - counts["skipped"])
    return {"status": status, "label": label, "selected": len(selected), **counts}


def dependency_layout(node_ids, edge_pairs):
    """Return deterministic caller-to-callee layers for acyclic graphs."""
    graph = nx.DiGraph()
    graph.add_nodes_from(node_ids)
    graph.add_edges_from(edge_pairs)
    if not graph:
        return {}
    if not nx.is_directed_acyclic_graph(graph):
        return nx.spring_layout(graph, seed=19, iterations=45, scale=1.25)

    depth = {node: 0 for node in graph}
    for node in nx.topological_sort(graph):
        for callee in graph.successors(node):
            depth[callee] = max(depth[callee], depth[node] + 1)
    layers = {}
    for node, level in depth.items():
        layers.setdefault(level, []).append(node)
    max_depth = max(layers, default=0)
    max_width = max(map(len, layers.values()), default=1)
    positions = {}
    for level, nodes in layers.items():
        nodes.sort()
        for index, node in enumerate(nodes):
            x = 0.0 if max_depth == 0 else -1.2 + 2.4 * level / max_depth
            y = (len(nodes) - 1) / 2 - index
            if len(nodes) > 1:
                y *= 2.0 / max(len(nodes) - 1, max_width - 1)
            positions[node] = (x, y)
    return positions
