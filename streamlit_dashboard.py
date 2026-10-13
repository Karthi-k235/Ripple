"""Ripple Streamlit dashboard for targeted change risk analysis."""

import json
from pathlib import Path

import streamlit as st

from engine.risk import validate_risk


# Resolve defaults from this dashboard file so launching Streamlit from another
# working directory still targets the Ripple checkout.
RIPPLE_ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Ripple | Change Risk",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --bg: #f8fafc;
        --panel: #ffffff;
        --panel-alt: #f8fafc;
        --sidebar: #ffffff;
        --line: #e2e8f0;
        --line-strong: #cbd5e1;
        --text: #0f172a;
        --muted: #475569;
        --muted-soft: #64748b;
        --primary: #4f46e5;
        --primary-strong: #4338ca;
        --primary-soft: #eef2ff;
        --success-bg: #ecfdf5;
        --success-border: #a7f3d0;
        --success-text: #166534;
        --error-bg: #fef2f2;
        --error-border: #fecaca;
        --error-text: #991b1b;
        --warning-bg: #fef3c7;
        --warning-border: #fde68a;
        --warning-text: #92400e;
        --info-bg: #eff6ff;
        --info-border: #bfdbfe;
        --info-text: #1d4ed8;
        --shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }

    html, body, [class*="css"] {
        font-family: Inter, "Segoe UI", sans-serif;
        background: var(--bg);
        color: var(--text);
    }

    .stApp {
        background: var(--bg);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: transparent;
        box-shadow: none;
    }

    [data-testid="stSidebar"] {
        background: var(--sidebar);
        border-right: 1px solid var(--line);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] .stCaptionContainer,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stDataFrameContainer {
        color: var(--muted);
    }

    .block-container {
        max-width: 1440px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, h4 {
        color: var(--text) !important;
        letter-spacing: -0.04em;
        margin-top: 0 !important;
    }

    .brand {
        font-size: 1.3rem;
        font-weight: 800;
        letter-spacing: -0.06em;
        color: var(--text);
        margin-bottom: 0.25rem;
    }

    .brand span {
        color: var(--primary);
    }

    .eyebrow {
        margin: 0;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted-soft);
    }

    .hero-title {
        margin-top: 0.45rem;
        font-size: clamp(2.2rem, 3vw, 3rem);
        line-height: 1.08;
        font-weight: 800;
        letter-spacing: -0.06em;
        color: var(--text);
    }

    .hero-sub {
        margin-top: 0.6rem;
        font-size: 1rem;
        color: var(--muted-soft);
    }

    .surface-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        box-shadow: var(--shadow);
    }

    .metric-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        box-shadow: var(--shadow);
        min-height: 130px;
    }

    .metric-label {
        color: var(--muted-soft);
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }

    .metric-value {
        margin-top: 0.55rem;
        font-size: clamp(1.7rem, 2vw, 2.2rem);
        line-height: 1.1;
        font-weight: 800;
        letter-spacing: -0.06em;
        color: var(--text);
    }

    .metric-note {
        margin-top: 0.4rem;
        color: var(--muted-soft);
        font-size: 0.8rem;
    }

    .section-title {
        margin: 0 0 0.7rem;
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: var(--text);
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 32px;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
    }

    .status-pass {
        background: var(--success-bg);
        border: 1px solid var(--success-border);
        color: var(--success-text);
    }

    .status-fail {
        background: var(--error-bg);
        border: 1px solid var(--error-border);
        color: var(--error-text);
    }

    .status-amber {
        background: var(--warning-bg);
        border: 1px solid var(--warning-border);
        color: var(--warning-text);
    }

    div[data-testid="stDataFrame"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
    }

    div[data-testid="stDataFrame"] > div {
        border-radius: 12px;
    }

    div[data-testid="stDataFrame"] table {
        border-collapse: collapse;
        width: 100%;
    }

    div[data-testid="stDataFrame"] th {
        background: var(--panel-alt);
        color: var(--muted-soft);
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 700;
        border-bottom: 1px solid var(--line);
    }

    div[data-testid="stDataFrame"] td {
        color: var(--text);
        border-bottom: 1px solid var(--line);
        background: var(--panel);
        font-size: 0.9rem;
    }

    div[data-testid="stDataFrame"] tbody tr:nth-child(even) td {
        background: #f8fafc;
    }

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background: var(--panel);
        color: var(--text);
        border: 1px solid var(--line-strong);
        border-radius: 10px;
        box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: rgba(79, 70, 229, 0.6);
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 10px;
        border: 1px solid transparent;
        font-weight: 700;
        min-height: 2.8rem;
        transition: all 0.2s ease;
    }

    .stButton > button[kind="primary"],
    .stDownloadButton > button {
        background: linear-gradient(180deg, var(--primary) 0%, var(--primary-strong) 100%);
        color: white;
        box-shadow: 0 12px 20px rgba(79, 70, 229, 0.18);
    }

    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button:hover {
        filter: brightness(0.98);
        box-shadow: 0 10px 18px rgba(79, 70, 229, 0.22);
    }

    .stButton > button[kind="secondary"] {
        background: var(--panel);
        color: var(--text);
        border: 1px solid var(--line-strong);
    }

    div[data-testid="stForm"] {
        border: none;
        padding: 0;
    }

    div[data-testid="stAlert"] {
        border-radius: 12px;
        border: 1px solid var(--warning-border);
        background: var(--warning-bg);
        color: var(--warning-text);
        padding: 0.8rem 0.9rem;
    }

    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] li,
    div[data-testid="stAlert"] strong {
        color: var(--warning-text) !important;
    }

    div[data-testid="stWarning"] {
        background: var(--warning-bg);
        border: 1px solid var(--warning-border);
        color: var(--warning-text);
    }

    div[data-testid="stWarning"] p,
    div[data-testid="stWarning"] li {
        color: var(--warning-text) !important;
    }

    div[data-testid="stError"] {
        background: var(--error-bg);
        border: 1px solid var(--error-border);
        color: var(--error-text);
    }

    div[data-testid="stError"] p,
    div[data-testid="stError"] li {
        color: var(--error-text) !important;
    }

    div[data-testid="stInfo"] {
        background: var(--info-bg);
        border: 1px solid var(--info-border);
        color: var(--info-text);
    }

    div[data-testid="stInfo"] p,
    div[data-testid="stInfo"] li {
        color: var(--info-text) !important;
    }

    code {
        color: #1d4ed8 !important;
        background: #eef2ff !important;
        border-radius: 8px;
    }

    .stExpander {
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--panel);
    }

    .stExpander summary {
        color: var(--text);
        font-weight: 600;
    }

    @media (max-width: 900px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .metric-card {
            min-height: auto;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown('<div class="brand">Ripple<span>.</span></div>', unsafe_allow_html=True)
    st.caption("CHANGE RISK WORKSPACE")
    st.divider()
    st.markdown("**Analysis setup**")

    with st.form("analysis_settings"):
        repo_root = st.text_input("Repository folder", value=str(RIPPLE_ROOT))
        project_root = st.text_input(
            "Python source folder",
            value=str(RIPPLE_ROOT / "demo_project"),
        )
        timeout = st.number_input(
            "Test timeout (seconds)",
            min_value=1,
            max_value=1800,
            value=60,
            step=10,
        )
        mapping_text = st.text_area(
            "Function to test mapping (JSON)",
            value='''{
  "pricing.calculate_tax": ["tests/test_demo_project.py::test_calculate_tax"],
  "pricing.calculate_total": ["tests/test_demo_project.py::test_calculate_total"],
  "checkout.checkout": ["tests/test_demo_project.py::test_checkout"],
  "receipt.print_receipt": ["tests/test_demo_project.py::test_print_receipt"],
  "main.run": ["tests/test_demo_project.py::test_main_run"]
}''',
            height=150,
            help="Map fully qualified function names to pytest node IDs. The default entries cover Ripple's demo checkout workflow.",
        )
        run_clicked = st.form_submit_button(
            "Run risk analysis",
            type="primary",
            width="stretch",
        )

    st.caption(
        "Analysis runs only when you press the button. Tests are executed using the configured timeout."
    )

st.markdown('<div class="eyebrow">Ripple · engineering health</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">Change risk, made clear.</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Crowdsource the impact, isolate the likely blast radius, and validate the right tests with a single workflow.</div>',
    unsafe_allow_html=True,
)
st.write("")

if run_clicked:
    try:
        mapping = json.loads(mapping_text)
        if not isinstance(mapping, dict) or any(
            not isinstance(key, str)
            or not isinstance(value, list)
            or any(not isinstance(item, str) for item in value)
            for key, value in mapping.items()
        ):
            raise ValueError(
                "Mapping must be a JSON object of function names to lists of pytest node IDs."
            )

        with st.spinner("Tracing dependencies and running selected tests…"):
            st.session_state["ripple_report"] = validate_risk(
                repo_root=repo_root,
                project_root=project_root,
                test_mapping=mapping,
                timeout=int(timeout),
                report_path=Path(repo_root) / "reports" / "risk_report.json",
            )
        st.session_state.pop("ripple_error", None)
    except Exception as error:
        st.session_state["ripple_error"] = str(error)

if st.session_state.get("ripple_error"):
    st.error(st.session_state["ripple_error"], icon="⚠️")

report = st.session_state.get("ripple_report")

if report is None:
    st.info(
        "Set your project folders and function-to-test mapping in the sidebar, then run an analysis.",
        icon="↗",
    )
    st.markdown(
        """
        <div class="surface-card" style="margin-top: 1rem;">
            <div class="section-title">A focused view of every change</div>
            <p style="margin: 0.5rem 0 0; color: #475569; line-height: 1.6;">
                Ripple traces changed functions, follows dependency impact, and runs only the selected pytest cases relevant to the change.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    test_result = report["test_result"]
    test_status = test_result["status"]
    status_style = "pass" if test_status == "passed" else ("fail" if test_status == "failed" else "amber")
    status_label = {
        "passed": "Tests passed",
        "failed": "Tests failed",
        "timed_out": "Timed out",
        "not_run": "No mapped tests",
    }.get(test_status, test_status.title())

    metric_columns = st.columns(4)
    metric_values = [
        ("Changed functions", len(report["changed_functions"]), "Detected in tracked files"),
        ("Potentially affected", len(report["affected_functions"]), "Callers in the dependency graph"),
        ("Selected tests", len(report["selected_tests"]), "From your explicit mapping"),
        ("Validation", status_label, "Pytest result"),
    ]

    for column, (label, value, note) in zip(metric_columns, metric_values):
        with column:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>',
                unsafe_allow_html=True,
            )

    st.write("")
    overview_col, validation_col = st.columns([1.2, 1.0], gap="large")

    with overview_col:
        st.markdown('<div class="section-title">Change overview</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("**Changed functions**")
            if report["changed_functions"]:
                st.dataframe(
                    [{"Function": name} for name in report["changed_functions"]],
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.caption("No tracked function changes were detected.")

            st.markdown("**Potentially affected functions**")
            if report["affected_functions"]:
                st.dataframe(
                    [{"Function": name} for name in report["affected_functions"]],
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.caption("No callers were found in the current dependency graph.")

    with validation_col:
        st.markdown('<div class="section-title">Test validation</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                f'<span class="status-pill status-{status_style}">{status_label}</span>',
                unsafe_allow_html=True,
            )

            if report["selected_tests"]:
                st.write("")
                test_outcomes = test_result.get("test_outcomes", [])
                outcomes_by_test = {}
                for outcome in test_outcomes:
                    outcomes_by_test.setdefault(outcome["test"], []).append(
                        outcome["status"].replace("_", " ").title()
                    )
                st.dataframe(
                    [
                        {
                            "Selected pytest case": node,
                            "Outcome": ", ".join(outcomes_by_test.get(node, ["Not reported"])),
                        }
                        for node in report["selected_tests"]
                    ],
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.caption("No tests were run. Add function-to-test entries in the sidebar mapping.")

            if report.get("unmapped_functions"):
                st.warning("Unmapped impacted functions: " + ", ".join(report["unmapped_functions"]))
            if report.get("unmapped_files"):
                st.warning("Changed files not mapped to a function: " + ", ".join(report["unmapped_files"]))

    with st.expander("Pytest output", expanded=test_status in {"failed", "timed_out"}):
        if test_result.get("stdout"):
            st.code(test_result["stdout"], language="text")
        if test_result.get("stderr"):
            st.code(test_result["stderr"], language="text")
        if not test_result.get("stdout") and not test_result.get("stderr"):
            st.caption("No test output.")

    st.caption(
        "Analysis limits: untracked files and nested functions are excluded. Test selection depends on the accuracy of the explicit function-to-test mapping."
    )

    st.download_button(
        "Download JSON report",
        data=json.dumps(report, indent=2),
        file_name="ripple-risk-report.json",
        mime="application/json",
        width="content",
    )

