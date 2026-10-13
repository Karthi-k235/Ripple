import networkx as nx

from engine.graph_view import build_graph_view


def test_graph_view_marks_impact_and_keeps_caller_to_callee_edges():
    graph = nx.DiGraph()
    graph.add_edges_from(
        [
            ("receipt.print_receipt", "checkout.checkout"),
            ("checkout.checkout", "pricing.calculate_tax"),
        ]
    )
    function_index = {
        name: {
            "file": f"{name.split('.')[0]}.py",
            "line": line,
            "end_line": line + 3,
        }
        for name, line in [
            ("receipt.print_receipt", 4),
            ("checkout.checkout", 8),
            ("pricing.calculate_tax", 12),
        ]
    }

    result = build_graph_view(
        graph,
        function_index,
        changed_functions=["pricing.calculate_tax"],
        affected_functions=["checkout.checkout", "receipt.print_receipt"],
    )

    nodes = {node["id"]: node for node in result["nodes"]}
    assert nodes["pricing.calculate_tax"]["status"] == "changed"
    assert nodes["pricing.calculate_tax"]["color"] == "#dc2626"
    assert nodes["checkout.checkout"]["status"] == "affected"
    assert nodes["checkout.checkout"]["dependencies"] == ["pricing.calculate_tax"]
    assert nodes["pricing.calculate_tax"]["callers"] == ["checkout.checkout"]
    assert {tuple(edge.values()) for edge in result["edges"]} == {
        ("checkout.checkout", "pricing.calculate_tax"),
        ("receipt.print_receipt", "checkout.checkout"),
    }
    assert result["omitted_nodes"] == 0


def test_graph_view_handles_empty_and_limits_large_graph():
    assert build_graph_view(nx.DiGraph(), {}) == {
        "nodes": [],
        "edges": [],
        "omitted_nodes": 0,
        "total_nodes": 0,
    }

    graph = nx.DiGraph()
    graph.add_nodes_from(["neutral.a", "neutral.b", "changed.c"])
    result = build_graph_view(
        graph,
        {},
        changed_functions=["changed.c"],
        max_nodes=2,
    )

    assert [node["id"] for node in result["nodes"]] == ["changed.c", "neutral.a"]
    assert result["omitted_nodes"] == 1
    assert result["total_nodes"] == 3
