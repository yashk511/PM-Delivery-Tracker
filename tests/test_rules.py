from src.risk_rules import run_all_rules


def flags(con):
    return run_all_rules(con)


def test_overdue_flagged_for_projects_1_and_3(con):
    f = flags(con)
    assert set(f[f.rule_id == "R1"].project_id) == {1, 3}


def test_scope_creep_flagged_for_project_2(con):
    f = flags(con)
    r = f[f.rule_id == "R2"]
    assert list(r.project_id) == [2] and r.iloc[0].impact == 4


def test_overallocated_person_flagged(con):
    r = flags(con)
    r = r[r.rule_id == "R3"]
    assert list(r.entity) == ["Rohan Verma"]


def test_blocked_dependency_chain_flagged(con):
    r = flags(con)
    r = r[r.rule_id == "R4"]
    assert len(r) == 2 and (r.project_id == 3).all() and (r.impact == 4).all()


def test_project_1_is_behind_schedule(con):
    r = flags(con)
    assert 1 in set(r[r.rule_id == "R5"].project_id)


def test_healthy_project_has_no_project_level_flags(con):
    assert (flags(con).project_id == 4).sum() == 0


def test_scores_are_product_and_sorted(con):
    f = flags(con)
    assert (f.score == f.likelihood * f.impact).all()
    assert f.score.is_monotonic_decreasing
