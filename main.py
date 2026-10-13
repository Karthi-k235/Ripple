
from engine.parser import parse_python_project
from engine.dependencies import build_dependency_graph
from engine.impact import find_affected_functions


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


if __name__ == "__main__":
    main()
