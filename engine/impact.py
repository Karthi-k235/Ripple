
import networkx as nx


def find_affected_functions(graph, changed_function):
    """
    Find all functions that may be affected by a change.

    Graph direction:
        Caller -> Function it calls

    Therefore, we traverse the graph backwards
    from the changed function.
    """

    if changed_function not in graph:
        raise ValueError(
            f"Function '{changed_function}' was not found in the graph."
        )

    affected = nx.ancestors(graph, changed_function)

    return sorted(affected)
