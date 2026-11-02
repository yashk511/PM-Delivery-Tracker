import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import metrics
from src.config import AS_OF, OVERLOAD_THRESHOLD, STATUSES
from src.db import build_connection
from src.report import build_weekly_report
from src.risk_rules import run_all_rules


st.set_page_config(
    page_title="Pulse | PM Delivery Tracker",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
        --ink: #111827;
        --muted: #475569;
        --line: #d7dee9;
        --surface: #ffffff;
        --blue: #3867f0;
        --teal: #0e9f9a;
        --amber: #d97706;
        --rose: #e05270;
    }
    .stApp { background: #f5f7fb; color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(245,247,251,.86); }
    [data-testid="stSidebar"] {
        background: #101827;
        border-right: 1px solid #202c41;
    }
    [data-testid="stSidebar"] * { color: #f1f5f9; }
    [data-testid="stSidebar"] .stCaption { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] label { color: #f8fafc !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="select"] input,
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] [data-baseweb="select"] div {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] [class*="singleValue"],
    [data-testid="stSidebar"] [data-baseweb="select"] [class*="placeholder"],
    [data-testid="stSidebar"] [data-baseweb="select"] [aria-live],
    [data-testid="stSidebar"] [data-baseweb="select"] p {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] ::selection {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        background: #bfdbfe !important;
    }
    [data-baseweb="popover"] [role="option"],
    [data-baseweb="popover"] [role="option"] * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        background: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] svg {
        fill: #334155 !important;
        color: #334155 !important;
    }
    .block-container { max-width: 1440px; padding: 2rem 3rem 4rem; }
    h1, h2, h3, [data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif;
        letter-spacing: -.03em;
    }
    h1 { font-size: 2.45rem; margin-bottom: .15rem; }
    h2 { font-size: 1.35rem; margin-top: 1.6rem; }
    h3 { font-size: 1.05rem; }
    .hero {
        background: linear-gradient(115deg, #162440 0%, #243d73 58%, #3867f0 100%);
        border-radius: 22px;
        color: white;
        padding: 2rem 2.2rem;
        margin-bottom: 1.6rem;
        box-shadow: 0 16px 36px rgba(30, 55, 105, .16);
    }
    .hero h1 { color: white; margin: 0; font-size: 2.4rem; }
    .hero p { color: #cfdbef; margin: .45rem 0 0; font-size: 1rem; }
    .eyebrow {
        color: #a9c5ff; font-size: .73rem; font-weight: 700;
        letter-spacing: .14em; text-transform: uppercase; margin-bottom: .5rem;
    }
    .section-label {
        color: #475569; font-size: .72rem; font-weight: 700;
        letter-spacing: .12em; text-transform: uppercase; margin: 1.35rem 0 .45rem;
    }
    .kpi {
        background: var(--surface); border: 1px solid var(--line); border-radius: 15px;
        padding: 1.1rem 1.25rem; min-height: 108px;
        box-shadow: 0 5px 16px rgba(25, 45, 80, .045);
    }
    .kpi-label { color: #334155; font-size: .78rem; font-weight: 600; }
    .kpi-value { color: var(--ink); font-family: 'Space Grotesk'; font-size: 1.85rem; font-weight: 700; margin-top: .35rem; }
    .kpi-note { color: #64748b; font-size: .76rem; margin-top: .15rem; }
    .kpi-blue { border-top: 3px solid var(--blue); }
    .kpi-teal { border-top: 3px solid var(--teal); }
    .kpi-amber { border-top: 3px solid var(--amber); }
    .kpi-rose { border-top: 3px solid var(--rose); }
    .stTabs [data-baseweb="tab-list"] { gap: .45rem; border-bottom: 1px solid var(--line); }
    .stTabs [data-baseweb="tab"] { padding: .8rem 1rem; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: var(--blue); }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line); border-radius: 13px;
    }
    .legend { color: #475569; font-size: .78rem; margin-top: -.5rem; }
    .sidebar-brand { font-family: 'Space Grotesk'; font-size: 1.25rem; font-weight: 700; color: white; }
    .sidebar-brand span { color: #82a4ff; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_connection():
    return build_connection()


def kpi(label, value, note="", tone="blue"):
    st.markdown(
        f'<div class="kpi kpi-{tone}"><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(str(value))}</div>'
        f'<div class="kpi-note">{html.escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def chart_layout(fig, height=330):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=30, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#64748b"),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor="#e5eaf2")
    fig.update_yaxes(gridcolor="#edf0f5", zeroline=False)
    return fig


con = get_connection().cursor()
projects = metrics.project_summary(con)
names = dict(zip(projects.project_id, projects.project))

with st.sidebar:
    st.markdown('<div class="sidebar-brand">◈ <span>Pulse</span></div>', unsafe_allow_html=True)
    st.caption("Delivery intelligence for teams")
    st.divider()
    choice = st.selectbox("Portfolio view", ["All projects"] + list(names.values()))
    st.divider()
    st.caption("Synthetic portfolio")
    st.caption(f"Data refreshed through {AS_OF:%d %b %Y}")
    st.caption("Built for proactive planning, clear ownership, and early risk action.")

pid = next((key for key, value in names.items() if value == choice), None)
flags = run_all_rules(con)
view_flags = flags if pid is None else flags[(flags.project_id == pid) | flags.project_id.isna()]
view_projects = projects if pid is None else projects[projects.project_id == pid]

st.markdown(
    f'<div class="hero"><div class="eyebrow">Project operations cockpit</div>'
    f'<h1>Make delivery feel predictable.</h1>'
    f'<p>One place to see progress, capacity, decisions, and the risks that need an owner today.</p></div>',
    unsafe_allow_html=True,
)

tab_over, tab_board, tab_work, tab_risk, tab_report = st.tabs(
    ["Overview", "Sprint board", "Workload", "Risk register", "Weekly report"]
)

with tab_over:
    total = int(view_projects.total_points.sum())
    done = int(view_projects.done_points.sum())
    complete = done / total if total else 0
    active_flags = int(view_flags.band.isin(["High", "Critical"]).sum())
    cols = st.columns(4)
    with cols[0]:
        kpi("Projects", len(view_projects), "in selected view", "blue")
    with cols[1]:
        kpi("Portfolio complete", f"{complete:.0%}", f"{done} of {total} points delivered", "teal")
    with cols[2]:
        kpi("Overdue tasks", int(view_projects.overdue_tasks.sum()), "needs an owner", "amber")
    with cols[3]:
        kpi("High-priority flags", active_flags, "high or critical", "rose")

    st.markdown('<div class="section-label">Portfolio health</div>', unsafe_allow_html=True)
    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Projects at a glance")
        tbl = view_projects[
            ["project", "sponsor", "start_date", "end_date", "total_points", "done_points",
             "pct_complete", "overdue_tasks", "blocked_tasks"]
        ].copy()
        tbl["pct_complete"] = (tbl["pct_complete"] * 100).round(0)
        st.dataframe(
            tbl,
            hide_index=True,
            use_container_width=True,
            column_config={
                "start_date": st.column_config.DateColumn("Start", format="DD MMM YYYY"),
                "end_date": st.column_config.DateColumn("End", format="DD MMM YYYY"),
                "pct_complete": st.column_config.NumberColumn("Complete", format="%d%%"),
                "total_points": st.column_config.NumberColumn("Planned"),
                "done_points": st.column_config.NumberColumn("Done"),
            },
        )
    with right:
        st.subheader("Flag mix")
        bands = view_flags.groupby("band").size().reindex(["Critical", "High", "Medium", "Low"]).fillna(0)
        fig = px.pie(
            values=bands.values,
            names=bands.index,
            hole=.68,
            color=bands.index,
            color_discrete_map={"Critical": "#b4233f", "High": "#e05270", "Medium": "#d97706", "Low": "#0e9f9a"},
        )
        fig.update_traces(textinfo="none", hovertemplate="%{label}: %{value}<extra></extra>")
        fig.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0), showlegend=True,
                          legend=dict(orientation="h", y=-.05))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"**{active_flags}** high or critical items need active mitigation.", unsafe_allow_html=True)

    vel = metrics.velocity(con)
    if pid is not None:
        vel = vel[vel.project == names[pid]]
    st.subheader("Velocity trend")
    if vel.empty:
        st.info("Completed sprint history will appear here.")
    else:
        fig = px.line(vel, x="sprint_no", y="velocity", color="project", markers=True,
                      labels={"sprint_no": "Sprint", "velocity": "Points delivered"})
        fig.update_xaxes(dtick=1)
        st.plotly_chart(chart_layout(fig, 310), use_container_width=True)

with tab_board:
    st.subheader("Sprint board")
    b_pid = pid if pid is not None else st.selectbox(
        "Project", list(names), format_func=names.get, key="board_project"
    )
    ss = metrics.sprint_summary(con)
    ss = ss[ss.project_id == b_pid].reset_index(drop=True)
    if ss.empty:
        st.info("No sprint data is available for this project.")
    else:
        active_indexes = ss.index[ss.status == "Active"].tolist()
        default = active_indexes[0] if active_indexes else 0
        label = lambda i: f"Sprint {ss.iloc[i].sprint_no} · {ss.iloc[i].status}"
        pick = st.selectbox("Sprint", range(len(ss)), index=default, format_func=label)
        sp = ss.iloc[pick]
        k = st.columns(4)
        with k[0]:
            kpi("Planned", f"{sp.initial_points} pts", "original sprint scope", "blue")
        with k[1]:
            kpi("Scope added", f"{sp.added_points} pts", "mid-sprint change", "amber")
        with k[2]:
            kpi("Delivered", f"{sp.done_points} pts", "completed work", "teal")
        with k[3]:
            kpi("Progress", f"{(sp.pct_done or 0):.0%}", "of current scope", "blue")
        tasks = metrics.sprint_tasks(con, int(sp.sprint_id))
        cols = st.columns(len(STATUSES))
        for col, status in zip(cols, STATUSES):
            sub = tasks[tasks.status == status]
            with col:
                st.markdown(f"**{status}**  \n<span class='legend'>{len(sub)} tasks · {int(sub.points.sum())} pts</span>",
                            unsafe_allow_html=True)
                for row in sub.itertuples():
                    tag = " · overdue" if row.is_overdue else ""
                    new = " · new scope" if row.added_mid_sprint else ""
                    blocked = f" · blocked by #{int(row.blocked_by)}" if pd.notna(row.blocked_by) else ""
                    with st.container(border=True):
                        st.markdown(f"**#{row.task_id} {row.title}**")
                        st.caption(f"{row.assignee} · {row.points} pts · due {row.due_date:%d %b}{tag}{new}{blocked}")
        if sp.status != "Planned":
            bd = metrics.burndown(con, int(sp.sprint_id))
            fig = go.Figure()
            fig.add_scatter(x=bd.date, y=bd.remaining, name="Remaining", mode="lines+markers",
                            line=dict(color="#3867f0", width=3))
            fig.add_scatter(x=bd.date, y=bd.ideal, name="Ideal", mode="lines",
                            line=dict(color="#a8b4c7", dash="dash"))
            fig.update_layout(title="Burndown · including scope added mid-sprint", yaxis_title="Points remaining")
            st.plotly_chart(chart_layout(fig, 320), use_container_width=True)

with tab_work:
    st.subheader("Capacity and ownership")
    wl, wp = metrics.workload(con), metrics.workload_by_project(con)
    st.caption(f"Active-sprint assignments. Capacity above {OVERLOAD_THRESHOLD:.0%} is flagged for rebalancing.")
    fig = px.bar(wp, x="person", y="points", color="project", labels={"points": "Assigned points"})
    fig.add_scatter(x=wl.name, y=wl.capacity, mode="markers", name="Capacity",
                    marker=dict(symbol="line-ew", size=40, line=dict(width=3, color="#172033")))
    st.plotly_chart(chart_layout(fig, 340), use_container_width=True)
    wl = wl.copy()
    wl["status"] = wl.utilization.map(lambda u: "Overloaded" if u > OVERLOAD_THRESHOLD else "Healthy")
    st.dataframe(
        wl[["name", "role", "capacity", "assigned_points", "utilization", "status"]],
        hide_index=True,
        use_container_width=True,
        column_config={"utilization": st.column_config.ProgressColumn("Utilization", min_value=0, max_value=1.6, format="%.0f%%")},
    )

with tab_risk:
    st.subheader("Risk register")
    st.caption("Five proactive rules surface delivery risks before they become surprises.")
    risk_cols = st.columns(3)
    with risk_cols[0]:
        kpi("Open signals", len(view_flags), "automated detections", "rose")
    with risk_cols[1]:
        kpi("Critical", int((view_flags.band == "Critical").sum()), "requires escalation", "rose")
    with risk_cols[2]:
        kpi("Managed risks", len(metrics.risk_register(con)), "in the register", "amber")
    st.markdown('<div class="section-label">Automated signals</div>', unsafe_allow_html=True)
    st.dataframe(
        view_flags[["rule_name", "project", "entity", "detail", "likelihood", "impact", "score", "band", "mitigation"]],
        hide_index=True, use_container_width=True,
    )
    reg = metrics.risk_register(con)
    if pid is not None:
        reg = reg[reg.project == names[pid]]
    st.markdown('<div class="section-label">Managed register</div>', unsafe_allow_html=True)
    st.dataframe(
        reg.drop(columns=["risk_id"]), hide_index=True, use_container_width=True,
        column_config={"raised_date": st.column_config.DateColumn("Raised", format="DD MMM YYYY")},
    )
    allr = pd.concat([view_flags[["likelihood", "impact"]], reg[reg.status != "Closed"][["likelihood", "impact"]]])
    grid = (allr.groupby(["likelihood", "impact"]).size().unstack(fill_value=0)
            .reindex(index=range(1, 6), columns=range(1, 6), fill_value=0))
    st.markdown('<div class="section-label">Open-risk heatmap</div>', unsafe_allow_html=True)
    st.plotly_chart(
        chart_layout(px.imshow(
            grid.values, x=[str(i) for i in range(1, 6)], y=[str(i) for i in range(1, 6)],
            origin="lower", text_auto=True, color_continuous_scale=["#eef6f6", "#e05270"],
            labels=dict(x="Impact", y="Likelihood", color="Risks")
        ), 330),
        use_container_width=True,
    )

with tab_report:
    st.subheader("Weekly stakeholder update")
    report = build_weekly_report(con, pid)
    st.download_button("Download report (.md)", report, file_name="weekly_status_report.md", mime="text/markdown")
    st.markdown(report)
    st.subheader("Decision log")
    dl = metrics.decisions(con)
    if pid is not None:
        dl = dl[dl.project_id == pid]
    st.dataframe(
        dl.drop(columns=["decision_id", "project_id"]), hide_index=True, use_container_width=True,
        column_config={"decision_date": st.column_config.DateColumn("Date", format="DD MMM YYYY")},
    )
