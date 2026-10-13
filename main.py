
from engine.parser import parse_python_project
from engine.dependencies import build_dependency_graph
from engine.impact import find_affected_functions
from engine.git_analyzer import detect_changed_functions

def main():
    functions = parse_python_project("demo_project")
    graph = build_dependency_graph(functions)

    print("\n========== RIPPLE ANALYSIS ==========")

    print("\nDiscovered functions:")
    for name, details in functions.items():
        print(f"{name} (line {details['line']})")
        print(f"  Calls: {details['calls']}")

    print("\nDependency relationships:")
    for caller, callee in sorted(graph.edges()):
        print(f"  {caller} -> {callee}")

    changed_function = "pricing.calculate_tax"
    affected = find_affected_functions(graph, changed_function)

    print(f"\nImpact analysis for: {changed_function}")
    print("\nPotentially affected functions:")
    for name in affected:
        print(f"  - {name}")

    print("\n=====================================")

    print("\nGit change detection:")

    try:
        changes = detect_changed_functions(
            repo_root=".",
            project_root="demo_project",
            functions=functions,
        )

        print("Changed files:")
        for file_path in changes["changed_files"]:
            print(f"  - {file_path}")

        print("Changed functions:")
        for function in changes["changed_functions"]:
            print(f"  - {function}")

        print("Changes not mapped to a function:")
        for file_path in changes["unmapped_files"]:
            print(f"  - {file_path}")

    except Exception as error:
        print(f"Git analysis unavailable: {error}")


if __name__ == "__main__":
    main()
