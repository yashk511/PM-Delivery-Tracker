"""Central settings. All thresholds used by the risk rules live here."""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SQL_DIR = ROOT / "sql"

# Fixed "today" so the synthetic portfolio (and the tests) are reproducible.
AS_OF = date(2026, 11, 2)
SPRINT_DAYS = 14

STATUSES = ["To Do", "In Progress", "Blocked", "Done", "Carried Over"]

# Risk-rule thresholds
SCOPE_CREEP_THRESHOLD = 0.20   # points added mid-sprint / initial points
OVERLOAD_THRESHOLD = 1.10      # assigned points / capacity
BEHIND_SCHEDULE_GAP = 0.15     # elapsed % minus done % of the sprint
