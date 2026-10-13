
from engine.parser import parse_python_project


def test_parser_discovers_functions_and_line_ranges(tmp_path):
    (tmp_path / "pricing.py").write_text(
        "def calculate_tax(amount):\n"
        "    return amount * 0.18\n",
        encoding="utf-8",
    )

    functions = parse_python_project(tmp_path)

    function = functions["pricing.calculate_tax"]

    assert function["name"] == "calculate_tax"
    assert function["line"] == 1
    assert function["end_line"] == 2
    assert function["calls"] == []
