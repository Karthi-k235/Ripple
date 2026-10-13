
from engine.parser import parse_python_project
from engine.dependencies import build_dependency_graph


def test_graph_resolves_imported_function(tmp_path):
    (tmp_path / "pricing.py").write_text(
        "def calculate_total():\n"
        "    return calculate_tax()\n\n"
        "def calculate_tax():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    (tmp_path / "checkout.py").write_text(
        "from pricing import calculate_total as total\n\n"
        "def checkout():\n"
        "    return total()\n",
        encoding="utf-8",
    )

    functions = parse_python_project(tmp_path)
    graph = build_dependency_graph(functions)

    assert graph.has_edge(
        "pricing.calculate_total",
        "pricing.calculate_tax",
    )
    assert graph.has_edge(
        "checkout.checkout",
        "pricing.calculate_total",
    )


def test_graph_resolves_module_qualified_call(tmp_path):
    (tmp_path / "pricing.py").write_text(
        "def calculate_total():\n"
        "    return 10\n",
        encoding="utf-8",
    )

    (tmp_path / "checkout.py").write_text(
        "import pricing\n\n"
        "def checkout():\n"
        "    return pricing.calculate_total()\n",
        encoding="utf-8",
    )

    functions = parse_python_project(tmp_path)
    graph = build_dependency_graph(functions)

    assert graph.has_edge(
        "checkout.checkout",
        "pricing.calculate_total",
    )
