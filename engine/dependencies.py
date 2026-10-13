
import networkx as nx


def resolve_call(call, module, imports, functions):
    """Resolve a call expression to a known function node."""

    # Direct import: from pricing import calculate_total
    if call in imports:
        candidate = imports[call]
        if candidate in functions:
            return candidate

    # Qualified call: pricing.calculate_total()
    if "." in call:
        first, remainder = call.split(".", 1)

        # import pricing as p; p.calculate_total()
        if first in imports:
            candidate = f"{imports[first]}.{remainder}"
            if candidate in functions:
                return candidate

        # The expression may already be module-qualified.
        if call in functions:
            return call

    # Same-module call: calculate_tax()
    candidate = f"{module}.{call}"
    if candidate in functions:
        return candidate

    return None


def build_dependency_graph(functions):
    graph = nx.DiGraph()

    for qualified_name, details in functions.items():
        graph.add_node(
            qualified_name,
            file=details["file"],
            line=details["line"],
            end_line=details["end_line"],
            module=details["module"],
        )

    for qualified_name, details in functions.items():
        for call in details["calls"]:
            target = resolve_call(
                call,
                details["module"],
                details["imports"],
                functions,
            )

            if target and target != qualified_name:
                graph.add_edge(
                    qualified_name,
                    target,
                    kind="function_call",
                )

    return graph
