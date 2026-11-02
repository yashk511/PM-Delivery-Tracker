import filecmp

from src.data_gen import generate


def test_referential_integrity(con):
    q = lambda s: con.execute(s).fetchone()[0]
    assert q("SELECT COUNT(*) FROM tasks WHERE assignee_id NOT IN (SELECT person_id FROM people)") == 0
    assert q("SELECT COUNT(*) FROM tasks WHERE sprint_id NOT IN (SELECT sprint_id FROM sprints)") == 0
    assert q("""SELECT COUNT(*) FROM tasks t JOIN sprints s ON s.sprint_id = t.sprint_id
                WHERE s.project_id <> t.project_id""") == 0
    assert q("SELECT COUNT(*) FROM tasks WHERE blocked_by IS NOT NULL AND blocked_by NOT IN (SELECT task_id FROM tasks)") == 0


def test_done_tasks_have_completion_dates(con):
    q = lambda s: con.execute(s).fetchone()[0]
    assert q("SELECT COUNT(*) FROM tasks WHERE status = 'Done' AND completed_date IS NULL") == 0
    assert q("SELECT COUNT(*) FROM tasks WHERE status <> 'Done' AND completed_date IS NOT NULL") == 0


def test_completion_dates_are_plausible(con):
    q = lambda s: con.execute(s).fetchone()[0]
    assert q("SELECT COUNT(*) FROM tasks t, config c WHERE t.completed_date > c.as_of") == 0
    assert q("SELECT COUNT(*) FROM tasks WHERE completed_date < added_date") == 0


def test_generation_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate(a), generate(b)
    for name in ("tasks.csv", "sprints.csv", "risks.csv"):
        assert filecmp.cmp(a / name, b / name, shallow=False)
