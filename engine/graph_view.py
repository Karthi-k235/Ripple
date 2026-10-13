"""Prepare dependency graph data for dashboard visualizations."""


NODE_COLORS = {
    "changed": "#dc2626",
    "affected": "#d97706",
    "other": "#64748b",
}


def build_graph_view(
    graph,
    function_index,
    changed_functions=(),
    affected_functions=(),
    max_nodes=150,
):
    """Return graph nodes and caller-to-callee edges with impact metadata.

    When the graph is larger than ``max_nodes``, changed functions and affected
    callers are kept ahead of neutral functions, with higher-degree nodes next.
    """
    changed = set(changed_functions)
    affected = set(affected_functions) - changed
    node_ids = list(graph.nodes)

    def priority(node_id):
        if node_id in changed:
            status_rank = 0
        elif node_id in affected:
            status_rank = 1
        else:
            status_rank = 2
        return (status_rank, -graph.degree(node_id), node_id)

    limit = max(0, int(max_nodes))
    visible_ids = sorted(node_ids, key=priority)[:limit]
    visible = set(visible_ids)

    nodes = []
    for node_id in sorted(visible_ids):
        details = function_index.get(node_id, graph.nodes[node_id])
        if node_id in changed:
            status = "changed"
        elif node_id in affected:
            status = "affected"
        else:
            status = "other"
        nodes.append(
            {
                "id": node_id,
                "label": node_id,
                "file": details.get("file", ""),
                "line": details.get("line"),
                "end_line": details.get("end_line"),
                "status": status,
                "color": NODE_COLORS[status],
                "dependencies": sorted(graph.successors(node_id)),
                "callers": sorted(graph.predecessors(node_id)),
            }
        )

    edges = [
        {"source": source, "target": target}
        for source, target in sorted(graph.edges())
        if source in visible and target in visible
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "omitted_nodes": max(0, len(node_ids) - len(nodes)),
        "total_nodes": len(node_ids),
    }
