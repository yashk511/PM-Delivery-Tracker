# PM Delivery Tracker

A Streamlit + DuckDB tool for running delivery across multiple projects: sprint planning, workload balancing, an auto-flagging risk register, and one-click weekly status reports.

**Live demo:** [pm-delivery-tracker.streamlit.app](https://pm-delivery-tracker.streamlit.app/)

> All data is **synthetic**. A fixed "as of" date (2 Nov 2026) keeps the demo and the tests reproducible.

The dashboard uses a delivery-operations cockpit layout with a portfolio selector, KPI cards,
project health overview, sprint kanban, capacity view, proactive risk signals, and a
downloadable stakeholder report.

## What it does

| Tab | What you get |
|---|---|
| **Overview** | Portfolio KPIs, per-project progress, velocity by sprint |
| **Sprint Board** | Kanban by status, scope added mid-sprint, overdue and blocked markers, burndown vs ideal |
| **Workload** | Assigned points vs capacity per person, split by project; overloaded people flagged |
| **Risk Register** | 5 auto-flag rules plus a managed register, scored likelihood x impact, with a heatmap |
| **Weekly Report** | Progress table, top risks with mitigations, decisions from the last 14 days, next steps. Downloads as Markdown |

## Risk rules

| ID | Rule | Trigger |
|---|---|---|
| R1 | Overdue tasks | Open task past its due date |
| R2 | Scope creep | Points added mid-sprint > 20% of planned points |
| R3 | Overallocation | Assigned points > 110% of capacity |
| R4 | Blocked dependency | Task waiting on an unfinished blocker (impact +1 if the blocker is overdue) |
| R5 | Behind schedule | Sprint % done trails % of time elapsed by more than 15 points |

Score = likelihood (1-5) x impact (1-5). Bands: Low 1-5, Medium 6-11, High 12-19, Critical 20-25. Thresholds live in `src/config.py`.

## Architecture

```
data_gen.py  ->  CSVs  ->  DuckDB tables (schema.sql)  ->  SQL marts (marts.sql)
                                                          ->  risk_rules.py / metrics.py / report.py  ->  app.py
```

The generator plants known problems (an overdue project, scope creep, a blocked chain, an overloaded person) plus one healthy control project, so the tests can assert that each rule fires where it should and stays quiet where it shouldn't.

## Run locally

```bash
pip install -r requirements-dev.txt
python -m src.data_gen      # optional: regenerates data/*.csv
pytest                      # 30 tests
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repo (commit the `data/` CSVs).
2. Go to share.streamlit.io, click **New app**, pick the repo and branch.
3. Set the main file to `app.py` and deploy. (If the CSVs are missing, the app regenerates them on startup.)
4. Paste the live link at the top of this README.
