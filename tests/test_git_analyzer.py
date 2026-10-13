
import git

from engine.parser import parse_python_project
from engine.git_analyzer import detect_changed_functions


def test_detects_modified_function(tmp_path):
    project = tmp_path / "demo_project"
    project.mkdir()

    source_file = project / "pricing.py"
    source_file.write_text(
        "def calculate_tax(amount):\n"
        "    return amount * 0.18\n",
        encoding="utf-8",
    )

    repo = git.Repo.init(tmp_path)
    repo.index.add([str(source_file.relative_to(tmp_path))])
    repo.index.commit("Initial version")

    # Modify a line inside calculate_tax().
    source_file.write_text(
        "def calculate_tax(amount):\n"
        "    return amount * 0.20\n",
        encoding="utf-8",
    )

    functions = parse_python_project(project)
    result = detect_changed_functions(tmp_path, project, functions)

    assert result["changed_files"] == ["demo_project/pricing.py"]
    assert result["changed_functions"] == ["pricing.calculate_tax"]
    assert result["unmapped_files"] == []
