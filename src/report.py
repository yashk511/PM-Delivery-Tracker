"""Weekly status report generator (Markdown)."""
from .config import AS_OF
from . import metrics
from .risk_rules import run_all_rules


def build_weekly_report(con, project_id=None):
    ps, ss = metrics.project_summary(con), metrics.sprint_summary(con)
    flags, dec = run_all_rules(con), metrics.decisions(con, days=14)
    scope = "Portfolio"
    if project_id is not None:
        ps = ps[ps.project_id == project_id]
        flags = flags[(flags.project_id == project_id) | flags.project_id.isna()]
        dec = dec[dec.project_id == project_id]
        scope = ps.iloc[0].project
    active = ss[ss.status == "Active"].set_index("project_id")

    lines = [f"# Weekly Status Report: {scope}", f"_As of {AS_OF:%d %b %Y}. All data is synthetic._", "",
             "## Progress",
             "| Project | Sprint | Sprint progress | Overall | Overdue | Blocked |",
             "|---|---|---|---|---|---|"]
    for r in ps.itertuples():
        a = active.loc[r.project_id]
        lines.append(f"| {r.project} | S{a.sprint_no} | {a.pct_done:.0%} ({a.done_points}/{a.total_points} pts) "
                     f"| {r.pct_complete:.0%} | {r.overdue_tasks} | {r.blocked_tasks} |")

    lines += ["", "## Top risks and issues"]
    if flags.empty:
        lines.append("- No risks flagged this week.")
    for r in flags.head(5).itertuples():
        lines.append(f"- **[{r.band} {r.score}] {r.project} / {r.rule_name}:** {r.detail}. "
                     f"_Mitigation:_ {r.mitigation}")

    lines += ["", "## Decisions logged (last 14 days)"]
    if dec.empty:
        lines.append("- None.")
    for r in dec.itertuples():
        lines.append(f"- {r.decision_date:%d %b}: **{r.decision}** ({r.project}, owner {r.owner}). {r.rationale}.")

    lines += ["", "## Next steps"]
    top = flags.drop_duplicates(subset=["rule_id", "project"]).head(3)
    if top.empty:
        lines.append("1. Continue as planned.")
    for i, r in enumerate(top.itertuples(), 1):
        lines.append(f"{i}. {r.mitigation} ({r.project}: {r.entity})")
    return "\n".join(lines) + "\n"
