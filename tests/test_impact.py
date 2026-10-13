
import networkx as nx
import pytest

from engine.impact import find_affected_functions


def test_finds_direct_and_indirect_callers():
    graph = nx.DiGraph()
    graph.add_edges_from([
        ("receipt.print_receipt", "checkout.checkout"),
        ("checkout.checkout", "pricing.calculate_total"),
        ("pricing.calculate_total", "pricing.calculate_tax"),
    ])

    affected = find_affected_functions(
        graph,
        "pricing.calculate_tax",
    )

    assert affected == [
        "checkout.checkout",
        "pricing.calculate_total",
        "receipt.print_receipt",
    ]


def test_unknown_function_raises_error():
    graph = nx.DiGraph()
    graph.add_node("pricing.calculate_tax")

    with pytest.raises(ValueError):
        find_affected_functions(graph, "pricing.missing_function")
