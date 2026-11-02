"""Rule-based risk detection. Each rule reads a SQL mart and emits scored flags.

R1 Overdue tasks        R2 Scope creep       R3 Overallocation
R4 Blocked dependency   R5 Sprint behind schedule
Score = likelihood x impact (1-5 each); see scoring.py for bands.
"""
import pandas as pd

from .config import BEHIND_SCHEDULE_GAP, OVERLOAD_THRESHOLD, SCOPE_CREEP_THRESHOLD
from .scoring import band, score

COLUMNS = ["rule_id", "rule_name", "project_id", "project", "entity", "detail",
           "likelihood", "impact", "score", "band", "mitigation"]

MITIGATIONS = {
    "R1": "Re-plan overdue tasks in stand-up, escalate blockers, and move work to teammates with spare capacity.",
    "R2": "Freeze sprint scope; route new requests to the backlog and agree trade-offs with the requester.",
    "R3": "Rebalance tasks to teammates with spare capacity or defer low-priority items.",
    "R4": "Unblock the dependency first: escalate to the blocker's owner and confirm a delivery date.",
    "R5": "Cut scope or add help now, and flag the likely slip to stakeholders early.",
}
NAMES = {"R1": "Overdue tasks", "R2": "Scope creep", "R3": "Overallocation",
         "R4": "Blocked dependency", "R5": "Sprint behind schedule"}


def _flag(rule, project_id, project, entity, detail, likelihood, impact):
    s = score(likelihood, impact)
    return dict(rule_id=rule, rule_name=NAMES[rule], project_id=project_id, project=project, entity=entity,
                detail=detail, likelihood=likelihood, impact=impact, score=s, band=band(s),
                mitigation=MITIGATIONS[rule])


def rule_overdue(con):
    df = con.execute("""SELECT project_id, project, COUNT(*) AS n, SUM(points)::INTEGER AS pts,
                               MAX(days_overdue) AS worst
                        FROM v_task_enriched WHERE is_overdue GROUP BY project_id, project""").df()
    return [_flag("R1", int(r.project_id), r.project, r.project,
                  f"{r.n} overdue tasks ({r.pts} pts), oldest {int(r.worst)} days late",
                  min(5, 2 + int(r.n) // 2), 4 if r.pts >= 10 else 3) for r in df.itertuples()]


def rule_scope_creep(con):
    df = con.execute("""SELECT project_id, project, sprint_no, initial_points, added_points
                        FROM v_sprint_summary
                        WHERE status = 'Active' AND initial_points > 0
                          AND added_points * 1.0 / initial_points > ?""", [SCOPE_CREEP_THRESHOLD]).df()
    out = []
    for r in df.itertuples():
        ratio = r.added_points / r.initial_points
        out.append(_flag("R2", int(r.project_id), r.project, f"Sprint {r.sprint_no}",
                         f"{r.added_points} pts added mid-sprint on {r.initial_points} planned (+{ratio:.0%})",
                         4, 4 if ratio >= 0.5 else 3))
    return out


def rule_overallocation(con):
    df = con.execute("SELECT name, capacity, assigned_points, utilization FROM v_workload WHERE utilization > ?",
                     [OVERLOAD_THRESHOLD]).df()
    return [_flag("R3", None, "Team", r.name,
                  f"{r.assigned_points} pts assigned vs {r.capacity} capacity ({r.utilization:.0%})",
                  5 if r.utilization >= 1.5 else 4, 3) for r in df.itertuples()]


def rule_blocked(con):
    df = con.execute("""SELECT t.project_id, t.project, t.task_id, t.title, b.task_id AS blocker_id,
                               b.title AS blocker_title, b.is_overdue AS blocker_overdue
                        FROM v_task_enriched t JOIN v_task_enriched b ON b.task_id = t.blocked_by
                        WHERE t.status <> 'Done' AND b.status <> 'Done'""").df()
    return [_flag("R4", int(r.project_id), r.project, f"Task #{r.task_id}",
                  f"'{r.title}' is waiting on #{r.blocker_id} '{r.blocker_title}'"
                  + (" (blocker is overdue)" if r.blocker_overdue else ""),
                  4, 4 if r.blocker_overdue else 3) for r in df.itertuples()]


def rule_behind_schedule(con):
    df = con.execute("""SELECT project_id, project, sprint_no, pct_done, elapsed_pct FROM v_sprint_summary
                        WHERE status = 'Active' AND elapsed_pct - pct_done > ?""", [BEHIND_SCHEDULE_GAP]).df()
    out = []
    for r in df.itertuples():
        gap = r.elapsed_pct - r.pct_done
        out.append(_flag("R5", int(r.project_id), r.project, f"Sprint {r.sprint_no}",
                         f"{r.pct_done:.0%} of points done with {r.elapsed_pct:.0%} of the sprint elapsed",
                         4 if gap >= 0.30 else 3, 3))
    return out


def run_all_rules(con):
    flags = (rule_overdue(con) + rule_scope_creep(con) + rule_overallocation(con)
             + rule_blocked(con) + rule_behind_schedule(con))
    df = pd.DataFrame(flags, columns=COLUMNS)
    return df.sort_values(["score", "rule_id"], ascending=[False, True]).reset_index(drop=True)
