"""Synthetic portfolio generator.

Run:  python -m src.data_gen
Writes people/projects/sprints/tasks/risks/decisions CSVs to data/.

Random task data is seeded, then specific problems are planted on purpose so the
risk rules have something real to catch:
  * Project 1: overdue tasks and a sprint running behind schedule
  * Project 2: scope creep (points added mid-sprint)
  * Project 3: blocked dependency chain (blocker is itself overdue)
  * Project 4: a healthy control project (should raise no project-level flags)
  * Team: one person (Rohan) is assigned well beyond capacity
"""
import csv
import random
from datetime import timedelta
from pathlib import Path

from .config import AS_OF, DATA_DIR, SPRINT_DAYS

SEED = 42

PEOPLE = [  # id, name, role, capacity (story points per sprint)
    (1, "Aarav Mehta", "Data Engineer", 22),
    (2, "Diya Sharma", "ML Engineer", 22),
    (3, "Rohan Verma", "ML Engineer", 14),
    (4, "Isha Nair", "Business Analyst", 18),
    (5, "Kabir Singh", "Backend Engineer", 22),
    (6, "Meera Iyer", "QA Engineer", 16),
]
PROJECTS = [  # id, name, sponsor, days the active sprint has been running - 1
    (1, "Customer Churn Predictor", "Retail Analytics", 9),
    (2, "Support Chatbot Rollout", "Customer Success", 6),
    (3, "Data Platform Migration", "IT Infrastructure", 5),
    (4, "Sales Forecast Dashboard", "Sales Ops", 3),
]
TITLES = [
    "Define requirements", "Set up data pipeline", "Build feature store", "Train baseline model",
    "Write unit tests", "Design API contract", "Security review", "Prepare stakeholder demo",
    "Document runbook", "Integrate monitoring", "Fix data quality issues", "Optimise slow queries",
    "Deploy to staging", "Support UAT", "Update dashboard", "Refine backlog",
]
POINTS, POINT_WEIGHTS = [1, 2, 3, 5, 8], [2, 3, 3, 2, 1]
ROHAN = 3


def _write(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def generate(out_dir=DATA_DIR, seed=SEED):
    rng = random.Random(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sprints, tasks, task_id, sprint_id = [], [], 0, 0

    for pid, _, _, offset in PROJECTS:
        s1 = AS_OF - timedelta(days=2 * SPRINT_DAYS + offset)
        for no in range(1, 5):
            sprint_id += 1
            start = s1 + timedelta(days=(no - 1) * SPRINT_DAYS)
            end = start + timedelta(days=SPRINT_DAYS - 1)
            status = {1: "Completed", 2: "Completed", 3: "Active", 4: "Planned"}[no]
            sprints.append(dict(sprint_id=sprint_id, project_id=pid, sprint_no=no,
                                start_date=start, end_date=end, status=status))
            for _ in range(5 if no == 4 else 6):
                task_id += 1
                due = start + timedelta(days=rng.randint(3, SPRINT_DAYS - 1))
                t = dict(task_id=task_id, project_id=pid, sprint_id=sprint_id, sprint_no=no,
                         title=rng.choice(TITLES),
                         assignee_id=rng.choice([p[0] for p in PEOPLE]),
                         points=rng.choices(POINTS, POINT_WEIGHTS)[0],
                         due_date=due, completed_date=None, blocked_by=None,
                         added_mid_sprint=0, added_date=start)
                if status == "Completed":
                    t["status"] = "Done" if rng.random() < 0.85 else "Carried Over"
                elif status == "Active":
                    t["status"] = rng.choices(["Done", "In Progress", "To Do"], [35, 35, 30])[0]
                else:
                    t["status"] = "To Do"
                if t["status"] == "Done":
                    t["completed_date"] = min(max(start, due - timedelta(days=rng.randint(0, 3))), AS_OF)
                tasks.append(t)

    def sprint_tasks(pid, no):
        return [t for t in tasks if t["project_id"] == pid and t["sprint_no"] == no]

    def done(t):
        t["status"] = "Done"
        t["completed_date"] = max(t["added_date"], min(t["due_date"], AS_OF - timedelta(days=1)))

    def reset(t, status):
        t["status"], t["completed_date"] = status, None

    # --- Project 1: behind schedule + overdue tasks
    p1 = sprint_tasks(1, 3)
    done(p1[0])
    for t, st in zip(p1[1:], ["In Progress", "To Do", "In Progress", "To Do", "To Do"]):
        reset(t, st)
    p1[1]["due_date"], p1[2]["due_date"] = AS_OF - timedelta(days=4), AS_OF - timedelta(days=2)
    p1[1]["points"], p1[2]["points"] = 5, 8

    # --- Project 2: scope creep (three tasks added after sprint start)
    for k, (pts, assignee, status) in enumerate([(5, 2, "To Do"), (8, 4, "To Do"), (3, 5, "In Progress")]):
        task_id += 1
        d = AS_OF - timedelta(days=3 - k)
        tasks.append(dict(task_id=task_id, project_id=2, sprint_id=sprint_id_of(sprints, 2, 3),
                          sprint_no=3, title="Urgent stakeholder request", assignee_id=assignee,
                          points=pts, status=status, due_date=AS_OF + timedelta(days=5 + k),
                          completed_date=None, blocked_by=None, added_mid_sprint=1, added_date=d))

    # --- Project 3: blocked chain; the blocker is overdue
    p3 = sprint_tasks(3, 3)
    reset(p3[1], "In Progress")
    p3[1]["due_date"], p3[1]["title"] = AS_OF - timedelta(days=1), "Provision staging access"
    for t in (p3[2], p3[3]):
        reset(t, "Blocked")
        t["blocked_by"] = p3[1]["task_id"]
        t["due_date"] = AS_OF + timedelta(days=4)

    # --- Project 4: healthy control project
    for t, st in zip(sprint_tasks(4, 3), ["Done", "Done", "Done", "In Progress", "Done", "To Do"]):
        done(t) if st == "Done" else reset(t, st)

    # --- Workload: balance the active sprints across the team, except Rohan, who is
    # deliberately given the biggest task of projects 1-3 (over capacity).
    active = [t for t in tasks if t["sprint_no"] == 3]
    cap = {p[0]: p[3] for p in PEOPLE}
    load = {pid: 0 for pid in cap}
    rohan_tasks = []
    for pid in (1, 2, 3):
        pool = [t for t in active if t["project_id"] == pid and not t["added_mid_sprint"]]
        rohan_tasks += sorted(pool, key=lambda t: -t["points"])[:1]
    for t in rohan_tasks:
        t["assignee_id"] = ROHAN
        load[ROHAN] += t["points"]
    for t in sorted((t for t in active if t not in rohan_tasks), key=lambda t: -t["points"]):
        pid = min((p for p in cap if p != ROHAN), key=lambda p: (load[p] + t["points"]) / cap[p])
        t["assignee_id"] = pid
        load[pid] += t["points"]

    task_fields = ["task_id", "project_id", "sprint_id", "title", "assignee_id", "points", "status",
                   "due_date", "completed_date", "blocked_by", "added_mid_sprint", "added_date"]
    tasks.sort(key=lambda t: t["task_id"])
    _write(out / "tasks.csv", tasks, task_fields)
    _write(out / "sprints.csv", sprints, ["sprint_id", "project_id", "sprint_no", "start_date", "end_date", "status"])
    _write(out / "people.csv", [dict(person_id=a, name=b, role=c, capacity_points=d) for a, b, c, d in PEOPLE],
           ["person_id", "name", "role", "capacity_points"])
    proj_rows = []
    for pid, name, sponsor, _ in PROJECTS:
        sp = [s for s in sprints if s["project_id"] == pid]
        proj_rows.append(dict(project_id=pid, name=name, sponsor=sponsor,
                              start_date=sp[0]["start_date"], end_date=sp[-1]["end_date"]))
    _write(out / "projects.csv", proj_rows, ["project_id", "name", "sponsor", "start_date", "end_date"])

    d = lambda n: AS_OF - timedelta(days=n)
    risks = [
        (1, 1, "Training data refresh delayed by upstream team", 3, 4, 1, "Agree SLA with data owners; fall back to last month's snapshot", "Open", d(20)),
        (2, 1, "Key ML engineer overloaded across projects", 4, 3, 3, "Rebalance tasks to Diya and Isha", "Mitigating", d(10)),
        (3, 2, "Chatbot intents not signed off by support leads", 3, 4, 2, "Weekly review with support leads", "Open", d(15)),
        (4, 2, "Scope growing mid-sprint from new stakeholder asks", 4, 3, 4, "Freeze sprint scope; move new asks to backlog", "Open", d(3)),
        (5, 3, "Legacy warehouse cutover window may slip", 3, 5, 5, "Dry-run migration; pre-approve rollback plan", "Open", d(25)),
        (6, 3, "Dependency on infra ticket for staging access", 4, 3, 5, "Escalate to IT lead; agree a firm date", "Mitigating", d(6)),
        (7, 3, "Data quality issues in legacy tables", 4, 3, 1, "Add a validation suite before each load", "Open", d(18)),
        (8, 4, "Forecast accuracy below target on seasonal SKUs", 2, 3, 6, "Add seasonal features; backtest monthly", "Open", d(12)),
        (9, 4, "Low dashboard adoption by sales leads", 2, 2, 6, "Demo to sales leads and collect feedback", "Closed", d(30)),
        (10, 2, "LLM API cost overrun", 2, 4, 2, "Set usage caps and alerts", "Open", d(9)),
    ]
    _write(out / "risks.csv", [dict(zip(["risk_id", "project_id", "description", "likelihood", "impact",
                                         "owner_id", "mitigation", "status", "raised_date"], r)) for r in risks],
           ["risk_id", "project_id", "description", "likelihood", "impact", "owner_id", "mitigation", "status", "raised_date"])
    decisions = [
        (1, 1, d(13), "Use gradient boosting as the baseline model", "Fastest path to a benchmark for stakeholders", 2),
        (2, 1, d(6), "Descope the explainability dashboard to Sprint 4", "Training data delay; protect the core model date", 4),
        (3, 2, d(12), "Launch chatbot to the billing queue first", "Lowest-risk queue with the clearest intents", 4),
        (4, 2, d(2), "Freeze Sprint 3 scope; new asks go to backlog", "Scope grew by more than 20% after sprint start", 4),
        (5, 3, d(11), "Migrate in two waves (reporting, then operational tables)", "Limits blast radius of cutover", 5),
        (6, 3, d(1), "Escalate staging access to the IT lead", "Blocker is holding up two dependent tasks", 5),
        (7, 4, d(9), "Use weekly forecast granularity", "Matches how sales reviews run", 6),
        (8, 4, d(4), "Hold a UAT session with sales leads before release", "Reduce adoption risk", 6),
    ]
    _write(out / "decisions.csv", [dict(zip(["decision_id", "project_id", "decision_date", "decision",
                                             "rationale", "owner_id"], r)) for r in decisions],
           ["decision_id", "project_id", "decision_date", "decision", "rationale", "owner_id"])
    return out


def sprint_id_of(sprints, pid, no):
    return next(s["sprint_id"] for s in sprints if s["project_id"] == pid and s["sprint_no"] == no)


if __name__ == "__main__":
    print(f"Wrote synthetic data to {generate()}")
