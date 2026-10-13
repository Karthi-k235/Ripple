"""Ripple Streamlit dashboard for targeted change risk analysis."""

import json
from pathlib import Path

import networkx as nx
import streamlit as st

try:
    import plotly.graph_objects as go
except ModuleNotFoundError:
    go = None

from engine.dependencies import build_dependency_graph
from engine.graph_view import build_graph_view
from engine.parser import parse_python_project
from engine.risk import validate_risk
from dashboard_helpers import (
    DEFAULT_MAPPING_TEXT,
    dependency_layout,
    filter_graph_data,
    parse_test_mapping,
    summarize_validation,
    validate_analysis_paths,
)


# Resolve defaults from this dashboard file so launching Streamlit from another
# working directory still targets the Ripple checkout.
RIPPLE_ROOT = Path(__file__).resolve().parent


def dependency_figure(
    graph_data, theme="Light", failed_functions=(), selected_function=None
):
    """Create a deterministic, selectable Plotly view of a dependency graph."""
    dark = theme == "Dark"
    text_color = "#e2e8f0" if dark else "#334155"
    paper_color = "#111827" if dark else "#ffffff"
    edge_color = "#475569" if dark else "#cbd5e1"
    failed_functions = set(failed_functions)
    nodes = graph_data["nodes"]
    node_ids = tuple(node["id"] for node in nodes)
    edge_pairs = tuple(
        (edge["source"], edge["target"]) for edge in graph_data["edges"]
    )
    positions = graph_positions(node_ids, edge_pairs)

    edge_x = []
    edge_y = []
    annotations = []
    for edge in graph_data["edges"]:
        source_x, source_y = positions[edge["source"]]
        target_x, target_y = positions[edge["target"]]
        edge_x.extend([source_x, target_x, None])
        edge_y.extend([source_y, target_y, None])
        # Stop each arrow before the target node so its head stays visible.
        annotations.append(
            {
                "x": source_x + 0.76 * (target_x - source_x),
                "y": source_y + 0.76 * (target_y - source_y),
                "ax": source_x + 0.58 * (target_x - source_x),
                "ay": source_y + 0.58 * (target_y - source_y),
                "xref": "x",
                "yref": "y",
                "axref": "x",
                "ayref": "y",
                "showarrow": True,
                "arrowhead": 2,
                "arrowsize": 1,
                "arrowwidth": 1,
                "arrowcolor": "#94a3b8",
                "opacity": 0.8,
            }
        )

    node_x = [positions[node["id"]][0] for node in nodes]
    node_y = [positions[node["id"]][1] for node in nodes]
    customdata = [
        [
            node["id"],
            node["file"],
            node["line"],
            node["end_line"],
            node["status"],
            ", ".join(node["dependencies"]) or "None",
            ", ".join(node["callers"]) or "None",
        ]
        for node in nodes
    ]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line={"color": edge_color, "width": 1.4},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=[node["label"].replace(".", ".<br>", 1) for node in nodes],
            textposition="top center",
            textfont={"size": 10, "color": text_color},
            customdata=customdata,
            marker={
                "size": 19,
                "symbol": ["diamond" if node["id"] in failed_functions else "circle" for node in nodes],
                "color": [node["color"] for node in nodes],
                "line": {
                    "color": ["#ef4444" if node["id"] in failed_functions else paper_color for node in nodes],
                    "width": [3 if node["id"] in failed_functions else 1.5 for node in nodes],
                },
            },
            selected={"marker": {"size": 26, "color": "#5146d8", "opacity": 1}},
            unselected={"marker": {"opacity": 0.68}},
            selectedpoints=(
                [index for index, node in enumerate(nodes) if node["id"] == selected_function]
                if selected_function in {node["id"] for node in nodes}
                else None
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Impact: %{customdata[4]}<br>"
                "%{customdata[1]}:%{customdata[2]}–%{customdata[3]}<br>"
                "Calls: %{customdata[5]}<br>"
                "Called by: %{customdata[6]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    figure.update_layout(
        height=min(780, max(440, 300 + len(nodes) * 2)),
        margin={"l": 10, "r": 10, "t": 15, "b": 10},
        paper_bgcolor=paper_color,
        plot_bgcolor=paper_color,
        font={"color": text_color},
        hoverlabel={"bgcolor": "#1f2937" if dark else "#ffffff", "font": {"color": text_color}},
        annotations=annotations,
        xaxis={"visible": False},
        yaxis={"visible": False},
        dragmode="pan",
    )
    return figure


def dependency_dot(graph_data, theme="Light", failed_functions=()):
    """Build a Streamlit-native graph fallback when Plotly is not installed."""
    node_ids = {node["id"]: f"function_{index}" for index, node in enumerate(graph_data["nodes"])}
    dark = theme == "Dark"
    colors = {
        "changed": ("#fee2e2", "#dc2626"),
        "affected": ("#fef3c7", "#d97706"),
        "other": (("#293244", "#94a3b8") if dark else ("#f1f5f9", "#64748b")),
    }
    lines = [
        "digraph Ripple {",
        f'graph [rankdir="LR", bgcolor="{"#111827" if dark else "white"}", pad="0.25", nodesep="0.35", ranksep="0.65"];',
        f'node [shape="box", style="rounded,filled", fontname="Segoe UI", fontsize="10", fontcolor="{"#e2e8f0" if dark else "#172033"}", margin="0.12,0.08"];',
        f'edge [color="{"#64748b" if dark else "#94a3b8"}", arrowsize="0.7"];',
    ]
    for node in graph_data["nodes"]:
        fill, border = colors[node["status"]]
        label = json.dumps(node["label"])
        badge = " ◆" if node["id"] in set(failed_functions) else ""
        lines.append(
            f'{node_ids[node["id"]]} [label={json.dumps(node["label"] + badge)}, fillcolor="{fill}", color="{border}"];'
        )
    for edge in graph_data["edges"]:
        lines.append(f'{node_ids[edge["source"]]} -> {node_ids[edge["target"]]};')
    lines.append("}")
    return "\n".join(lines)


@st.cache_data(show_spinner=False)
def graph_positions(node_ids, edge_pairs):
    """Cache a compact left-to-right call layout, with a cyclic fallback."""
    return dependency_layout(node_ids, edge_pairs)

st.set_page_config(
    page_title="Ripple | Change Risk",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard_helpers import DEFAULT_MAPPING, DEFAULT_MAPPING_TEXT

st.session_state.setdefault("ripple_theme", "Light")

with st.sidebar:
    st.markdown(
        '<div class="brand" style="margin-top: 0.15rem;">Ripple<span>.</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="color: var(--r-muted); margin-top: 0.1rem;">Change impact and validation workspace</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    theme = st.selectbox("Theme", ["Light", "Dark"], key="ripple_theme")

palette = {
    "Light": {
        "bg": "#f5f7fb", "surface": "#ffffff", "surface_alt": "#eef2f7",
        "text": "#172033", "muted": "#596579", "line": "#dce2eb",
        "accent": "#5146d8", "input": "#ffffff", "code_bg": "#eef2ff",
    },
    "Dark": {
        "bg": "#171b26", "surface": "#202635", "surface_alt": "#293244",
        "text": "#e8edf7", "muted": "#a8b3c7", "line": "#3a4559",
        "accent": "#a5a0ff", "input": "#202635", "code_bg": "#293244",
    },
}[theme]
st.markdown(
    f"""<style>
    :root {{ --r-bg:{palette['bg']}; --r-surface:{palette['surface']};
      --r-alt:{palette['surface_alt']}; --r-text:{palette['text']};
      --r-muted:{palette['muted']}; --r-line:{palette['line']};
      --r-accent:{palette['accent']}; --r-input:{palette['input']};
      --r-code:{palette['code_bg']}; color-scheme:{'dark' if theme == 'Dark' else 'light'}; }}
    html, body, .stApp {{ background:var(--r-bg) !important; color:var(--r-text) !important;
      font-family:Inter, 'Segoe UI', sans-serif; }}
    [data-testid="stHeader"] {{ background:transparent; }}
    [data-testid="stSidebar"] {{ background:var(--r-surface); border-right:1px solid var(--r-line); }}
    .block-container {{ max-width:1480px; padding-top:0.7rem; padding-bottom:2.5rem; }}
    h1,h2,h3,h4,p,label,span {{ color:var(--r-text); }}
    .brand {{ font-size:1.85rem; font-weight:800; letter-spacing:-.06em; color:var(--r-text); margin:0; }}
    .brand span {{ color:var(--r-accent); }}
    [data-testid="stCaptionContainer"] {{ margin-top: -0.15rem; }}
    [data-testid="stSidebar"] .block-container {{ padding-top: 0.4rem; }}
    [data-testid="stCaptionContainer"] p {{ color:var(--r-muted); }}
    [data-testid="stMetric"] {{ background:var(--r-surface); border:1px solid var(--r-line);
      border-radius:12px; padding:.8rem 1rem; }}
    [data-testid="stMetricLabel"] p {{ color:var(--r-muted); }}
    [data-testid="stMetricValue"] {{ color:var(--r-text); }}
    [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] {{
      border-color:var(--r-line) !important; background:var(--r-surface); border-radius:12px; }}
    input, textarea {{ background:var(--r-input) !important; color:var(--r-text) !important;
      border-color:var(--r-line) !important; }}
    [data-testid="stDataFrame"] {{ border:1px solid var(--r-line); border-radius:10px; }}
    code, pre {{ background:var(--r-code) !important; color:var(--r-text) !important; }}
    button {{ border-radius:9px !important; }}
    button[kind="primary"] {{ background:var(--r-accent) !important; color:white !important; }}
    button:focus-visible, input:focus-visible, textarea:focus-visible {{ outline:3px solid var(--r-accent) !important; }}
    @media (max-width:800px) {{ .block-container {{ padding-left:1rem; padding-right:1rem; }} }}
    </style>""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Analysis setup")
    repo_root = st.text_input(
        "Repository folder", value=str(RIPPLE_ROOT), key="ripple_repo_root",
        help="Git repository root. Full Windows paths are accepted.",
    )
    project_root = st.text_input(
        "Python source folder", value=str(RIPPLE_ROOT / "demo_project"),
        key="ripple_project_root", help="Python source folder inside the repository.",
    )
    with st.expander("Show full configured paths"):
        st.code(f"Repository\n{repo_root}\n\nPython source\n{project_root}", language="text")
    timeout = st.number_input(
        "Test timeout (seconds)", min_value=1, max_value=1800, value=60, step=10,
        help="Maximum duration for the selected pytest run.",
    )
    with st.expander("Advanced · function-to-test mapping", expanded=False):
        if "ripple_mapping_text" not in st.session_state:
            st.session_state["ripple_mapping_text"] = DEFAULT_MAPPING_TEXT
        if st.button("Restore example mapping", key="restore_mapping"):
            st.session_state["ripple_mapping_text"] = DEFAULT_MAPPING_TEXT
            st.rerun()
        mapping_text = st.text_area(
            "Qualified function → pytest node IDs", key="ripple_mapping_text", height=180,
            help='Example: {"pricing.calculate_tax": ["tests/test_demo_project.py::test_calculate_tax"]}',
        )
        st.caption("Only explicitly mapped tests are selected. Invalid JSON is reported when you run analysis.")
    run_clicked = st.button("Run risk analysis", type="primary", width="stretch")
    st.caption("Analysis runs only when you press this button.")

st.markdown('<div class="eyebrow">RIPPLE / CHANGE VALIDATION</div>', unsafe_allow_html=True)
st.markdown("## Understand the impact before trusting a change")
st.caption("Trace changed functions through their callers, then inspect the tests that actually ran.")

if run_clicked:
    try:
        resolved_repo, resolved_project = validate_analysis_paths(repo_root, project_root)
        mapping = parse_test_mapping(mapping_text)
        with st.spinner("Tracing dependencies and running mapped tests…"):
            fresh_report = validate_risk(
                repo_root=resolved_repo,
                project_root=resolved_project,
                test_mapping=mapping,
                timeout=int(timeout),
                report_path=resolved_repo / "reports" / "risk_report.json",
            )
        st.session_state["ripple_report"] = fresh_report
        st.session_state["ripple_report_mapping"] = mapping
        st.session_state.pop("ripple_error", None)
    except Exception as error:
        # Keep the last successful report visible while clearly flagging this attempt.
        st.session_state["ripple_error"] = str(error)

if st.session_state.get("ripple_error"):
    st.error("Latest analysis attempt failed: " + st.session_state["ripple_error"])
    if st.session_state.get("ripple_report"):
        st.caption("Showing the last successful analysis report below.")

report = st.session_state.get("ripple_report")
try:
    resolved_repo, resolved_project = validate_analysis_paths(repo_root, project_root)
    graph_function_index = parse_python_project(resolved_project)
    dependency_graph = build_dependency_graph(graph_function_index)
    graph_error = None
except Exception as error:
    graph_function_index, dependency_graph, graph_error = {}, nx.DiGraph(), str(error)

changed_functions = (report or {}).get("changed_functions", [])
affected_functions = (report or {}).get("affected_functions", [])
impacted_functions = set(changed_functions) | set(affected_functions)

if report:
    summary = summarize_validation(report)
    metrics = st.columns(4)
    metrics[0].metric("Changed functions", len(changed_functions), help="Detected in tracked source files")
    metrics[1].metric("Potentially affected", len(affected_functions), help="Transitive callers in the dependency graph")
    metrics[2].metric("Tests selected", summary["selected"], help="Unique pytest node IDs from the explicit mapping")
    metrics[3].metric(
        "Validation",
        "Analysis error" if st.session_state.get("ripple_error") else summary["label"],
        help="A pass means selected tests ran and pytest returned success",
    )
else:
    st.info("Configure the repository, source folder and test mapping in the sidebar, then run an analysis.")
    metrics = st.columns(4)
    for column, label in zip(metrics, ("Changed functions", "Potentially affected", "Tests selected", "Validation")):
        column.metric(label, "Analysis error" if label == "Validation" and st.session_state.get("ripple_error") else "—")

if graph_error:
    st.warning("Dependency graph unavailable: " + graph_error)

overview_tab, graph_tab, validation_tab, evidence_tab = st.tabs(
    ["Overview", "Dependency map", "Test validation", "Report & output"]
)
with overview_tab:
    if not report:
        st.markdown("#### A focused view of every change")
        st.write("Ripple follows source dependencies and runs only the mapped pytest cases relevant to tracked changes.")
    else:
        left, right = st.columns([1.1, 1], gap="large")
        with left:
            st.markdown("#### Change overview")
            st.markdown("**Changed functions**")
            if changed_functions:
                st.dataframe([{"Function": name} for name in changed_functions], hide_index=True, width="stretch")
            else:
                st.caption("No tracked function changes were detected.")
            st.markdown("**Potentially affected functions**")
            if affected_functions:
                st.dataframe([{"Function": name} for name in affected_functions], hide_index=True, width="stretch")
            else:
                st.caption("No callers were found in the current dependency graph.")
        with right:
            st.markdown("#### Evidence at a glance")
            st.write(f"**{summary['passed']} passed · {summary['failed']} failed · {summary['skipped']} skipped**")
            st.write(f"{summary['timed_out']} timed out · {summary['not_reported']} selected cases not reported")
            st.write(f"**{len(report.get('unmapped_functions', []))} impacted functions lack a test mapping**")
            if report.get("unmapped_functions"):
                st.warning("Unmapped: " + ", ".join(report["unmapped_functions"]))
            if report.get("unmapped_files"):
                st.warning("Changed files not mapped to a function: " + ", ".join(report["unmapped_files"]))
            st.caption("Predicted impact is not proof of coverage; only listed outcomes are execution evidence.")

with graph_tab:
    st.markdown("#### Dependency map")
    st.caption("Arrows point caller → callee. Changed functions are red; affected callers are amber. Diamonds mark functions with failing mapped tests.")
    if dependency_graph.number_of_nodes() == 0:
        st.info("No module-level Python functions were found in this source folder.")
    else:
        total_graph_nodes = dependency_graph.number_of_nodes()
        graph_limit = min(150, total_graph_nodes)
        if total_graph_nodes > 150:
            graph_limit = st.slider("Maximum functions before filters", 50, min(300, total_graph_nodes), 150, 25)
        raw_graph = build_graph_view(
            dependency_graph, graph_function_index,
            changed_functions=changed_functions, affected_functions=affected_functions,
            max_nodes=graph_limit,
        )
        filter_col, status_col, impact_col = st.columns([2, 2, 1])
        with filter_col:
            graph_query = st.text_input("Find a function", placeholder="module.function", key="graph_query")
        with status_col:
            graph_statuses = st.multiselect("Show classifications", ["changed", "affected", "other"], default=["changed", "affected", "other"], key="graph_statuses")
        with impact_col:
            impact_only = st.toggle("Impact path only", value=False, help="Hide neutral functions and show only changed and affected functions.")
        graph_data = filter_graph_data(raw_graph, graph_query, graph_statuses, impact_only)
        if raw_graph["omitted_nodes"]:
            st.caption(f"Showing up to {len(raw_graph['nodes'])} of {total_graph_nodes} discovered functions before filters. Increase the limit to explore more.")
        if graph_data["filtered_nodes"]:
            st.caption(f"Filters hide {graph_data['filtered_nodes']} functions.")
        if not graph_data["nodes"]:
            st.info("No functions match the current graph filters. Clear the search or include more classifications.")
        else:
            current_mapping = st.session_state.get("ripple_report_mapping", DEFAULT_MAPPING)
            outcome_status = {}
            if report:
                for outcome in report.get("test_result", {}).get("test_outcomes", []):
                    outcome_status[outcome.get("test")] = outcome.get("status")
            failed_functions = {
                function for function, test_ids in current_mapping.items()
                if any(outcome_status.get(test_id) == "failed" for test_id in test_ids)
            }
            selected_points = []
            if go is None:
                st.info("Plotly is unavailable. The dependency map remains available as a static graph.")
                st.graphviz_chart(
                    dependency_dot(graph_data, theme=theme, failed_functions=failed_functions),
                    width="stretch",
                )
            else:
                figure = dependency_figure(
                    graph_data,
                    theme=theme,
                    failed_functions=failed_functions,
                    selected_function=st.session_state.get("ripple_graph_selected_node"),
                )
                selection = st.plotly_chart(
                    figure, key="ripple_dependency_graph", on_select="rerun",
                    selection_mode="points", width="stretch",
                    config={"displaylogo": False, "scrollZoom": True, "modeBarButtonsToAdd": ["resetScale2d"]},
                    alt="Interactive function dependency graph",
                )
                selected_points = selection.selection.get("points", [])
            visible_ids = [node["id"] for node in graph_data["nodes"]]
            if selected_points:
                point_data = selected_points[-1].get("customdata", [])
                if point_data and point_data[0] in visible_ids:
                    st.session_state["ripple_graph_selected_node"] = point_data[0]
            default_node = next((name for name in changed_functions if name in visible_ids), visible_ids[0])
            if st.session_state.get("ripple_graph_selected_node") not in visible_ids:
                st.session_state["ripple_graph_selected_node"] = default_node
            selected_function = st.selectbox("Inspect function", visible_ids, key="ripple_graph_selected_node")
            details = next(node for node in graph_data["nodes"] if node["id"] == selected_function)
            status_label = {"changed": "Changed", "affected": "Potentially affected", "other": "No known impact"}[details["status"]]
            detail_columns = st.columns(3)
            detail_columns[0].markdown(f"**{selected_function}**")
            detail_columns[0].caption(f"{details.get('module', selected_function.rsplit('.', 1)[0])} · {status_label}")
            detail_columns[1].caption("Source")
            detail_columns[1].code(f"{details['file']}\nLines {details['line']}–{details['end_line']}", language="text")
            detail_columns[2].caption("Direct links")
            detail_columns[2].write(f"{len(details['dependencies'])} callees · {len(details['callers'])} callers")
            callers_transitive = sorted(set(nx.ancestors(dependency_graph, selected_function))) if selected_function in dependency_graph else []
            st.caption("Transitive callers: " + (", ".join(callers_transitive) if callers_transitive else "None"))
            mapped_tests = current_mapping.get(selected_function, [])
            if mapped_tests:
                st.markdown("**Mapped tests and latest outcomes**")
                st.dataframe([{"Test": test_id, "Outcome": outcome_status.get(test_id, "Not run / no latest outcome")} for test_id in mapped_tests], hide_index=True, width="stretch")
            else:
                st.caption("No tests are mapped directly to this function.")
            with st.expander("Direct callees and callers"):
                callees, callers = st.columns(2)
                callees.markdown("**Calls**")
                callees.write(details["dependencies"] or "None")
                callers.markdown("**Called by**")
                callers.write(details["callers"] or "None")

with validation_tab:
    st.markdown("#### Test validation")
    if not report:
        st.info("Run an analysis to see selected pytest cases and execution outcomes.")
    else:
        st.markdown(f"### {summary['label']}")
        st.caption(f"{summary['passed']} passed · {summary['failed']} failed · {summary['skipped']} skipped · {summary['timed_out']} timed out · {summary['not_reported']} not reported")
        test_result = report.get("test_result", {})
        selected = report.get("selected_tests", [])
        mapping_used = st.session_state.get("ripple_report_mapping", DEFAULT_MAPPING)
        outcome_by_id = {}
        details_by_id = {}
        for outcome in test_result.get("test_outcomes", []):
            outcome_by_id.setdefault(outcome.get("test"), []).append(outcome.get("status", "not_reported"))
            if outcome.get("detail"):
                details_by_id[outcome.get("test")] = outcome["detail"]
        if selected:
            st.dataframe([
                {
                    "Pytest case": test_id,
                    "Related functions": ", ".join(function for function, ids in mapping_used.items() if test_id in ids) or "Mapping not retained",
                    "Outcome": ", ".join(value.replace("_", " ").title() for value in outcome_by_id.get(test_id, ["not_reported"])),
                }
                for test_id in selected
            ], hide_index=True, width="stretch")
            if details_by_id:
                with st.expander("Failure and skip details"):
                    for test_id, detail in details_by_id.items():
                        st.markdown(f"**{test_id}**")
                        st.code(detail, language="text")
        else:
            st.warning("No tests were run. Open Advanced mapping in the sidebar and add pytest node IDs for impacted functions.")
        if report.get("unmapped_functions"):
            st.warning("Impacted functions without mapped coverage: " + ", ".join(report["unmapped_functions"]))
        if report.get("unmapped_files"):
            st.warning("Changed files that did not map to a discovered function: " + ", ".join(report["unmapped_files"]))
        st.caption("Test duration is not included in the current engine report.")

with evidence_tab:
    st.markdown("#### Run evidence")
    if not report:
        st.info("A JSON report is available after a successful analysis.")
    else:
        st.download_button("Download JSON report", data=json.dumps(report, indent=2), file_name="ripple-risk-report.json", mime="application/json", width="content")
        test_result = report.get("test_result", {})
        with st.expander("Pytest stdout / stderr", expanded=test_result.get("status") in {"failed", "timed_out"}):
            if test_result.get("stdout"):
                st.code(test_result["stdout"], language="text")
            if test_result.get("stderr"):
                st.code(test_result["stderr"], language="text")
            if not test_result.get("stdout") and not test_result.get("stderr"):
                st.caption("No test output was captured.")
        st.markdown("**Analysis limits**")
        for limit in report.get("analysis_limits", []):
            st.caption("• " + limit)
