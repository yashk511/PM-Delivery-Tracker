from src.report import build_weekly_report
from src.risk_rules import run_all_rules


def test_portfolio_report_has_all_sections(con):
    md = build_weekly_report(con)
    for h in ("## Progress", "## Top risks and issues", "## Decisions logged", "## Next steps"):
        assert h in md
    assert run_all_rules(con).iloc[0].detail in md


def test_project_report_is_scoped(con):
    md = build_weekly_report(con, 3)
    assert "Data Platform Migration" in md
    assert "Customer Churn Predictor" not in md
