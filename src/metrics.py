"""Thin query layer over the DuckDB marts. Every function returns a DataFrame."""
import pandas as pd

from .config import AS_OF
from .scoring import band


def q(con, sql, params=None):
    return con.execute(sql, params or []).df()


def project_summary(con):
    return q(con, "SELECT * FROM v_project_summary ORDER BY project_id")


def sprint_summary(con):
    return q(con, "SELECT * FROM v_sprint_summary ORDER BY project_id, sprint_no")


def velocity(con):
    return q(con, """SELECT project, sprint_no, done_points AS velocity, total_points
                     FROM v_sprint_summary WHERE status = 'Completed' ORDER BY project_id, sprint_no""")


def workload(con):
    return q(con, "SELECT * FROM v_workload ORDER BY utilization DESC")


def workload_by_project(con):
    return q(con, """SELECT pe.name AS person, p.name AS project, SUM(t.points)::INTEGER AS points
                     FROM tasks t
                     JOIN sprints s ON s.sprint_id = t.sprint_id AND s.status = 'Active'
                     JOIN people pe ON pe.person_id = t.assignee_id
                     JOIN projects p ON p.project_id = t.project_id
                     GROUP BY pe.name, p.name""")


def sprint_tasks(con, sprint_id):
    return q(con, "SELECT * FROM v_task_enriched WHERE sprint_id = ? ORDER BY task_id", [sprint_id])


def risk_register(con):
    df = q(con, """SELECT r.risk_id, p.name AS project, r.description, r.likelihood, r.impact,
                          r.likelihood * r.impact AS score, pe.name AS owner, r.mitigation,
                          r.status, r.raised_date
                   FROM risks r JOIN projects p ON p.project_id = r.project_id
                   JOIN people pe ON pe.person_id = r.owner_id ORDER BY score DESC""")
    df["band"] = df["score"].map(band)
    return df


def decisions(con, days=None):
    df = q(con, """SELECT d.decision_id, d.project_id, p.name AS project, d.decision_date, d.decision,
                          d.rationale, pe.name AS owner
                   FROM decisions d JOIN projects p ON p.project_id = d.project_id
                   JOIN people pe ON pe.person_id = d.owner_id ORDER BY d.decision_date DESC""")
    if days is not None:
        df = df[pd.to_datetime(df["decision_date"]) >= pd.Timestamp(AS_OF) - pd.Timedelta(days=days)]
    return df


def burndown(con, sprint_id):
    """Daily remaining points (actual, including scope added mid-sprint) vs an ideal line."""
    start, end = con.execute("SELECT start_date, end_date FROM sprints WHERE sprint_id = ?", [sprint_id]).fetchone()
    t = q(con, "SELECT points, status, added_mid_sprint, added_date, completed_date FROM tasks WHERE sprint_id = ?",
          [sprint_id])
    t["added_date"] = pd.to_datetime(t["added_date"])
    t["completed_date"] = pd.to_datetime(t["completed_date"])
    initial = int(t.loc[t["added_mid_sprint"] == 0, "points"].sum())
    span = (end - start).days
    rows = []
    for day in pd.date_range(start, min(end, AS_OF)):
        added = t.loc[t["added_date"] <= day, "points"].sum()
        done = t.loc[(t["status"] == "Done") & (t["completed_date"] <= day), "points"].sum()
        ideal = max(0.0, initial * (1 - (day.date() - start).days / span))
        rows.append({"date": day, "remaining": int(added - done), "ideal": round(ideal, 1)})
    return pd.DataFrame(rows)
