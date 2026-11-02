import pytest

from src import metrics


def test_sprint_totals_match_raw_tasks(con):
    raw = dict(con.execute("SELECT sprint_id, SUM(points) FROM tasks GROUP BY sprint_id").fetchall())
    for r in metrics.sprint_summary(con).itertuples():
        assert r.total_points == raw[r.sprint_id]
        assert r.initial_points + r.added_points == r.total_points


def test_velocity_equals_done_points_in_completed_sprints(con):
    raw = con.execute("""SELECT SUM(t.points) FROM tasks t JOIN sprints s ON s.sprint_id = t.sprint_id
                         WHERE s.status = 'Completed' AND t.status = 'Done'""").fetchone()[0]
    assert metrics.velocity(con).velocity.sum() == raw


def test_workload_counts_only_active_sprints(con):
    raw = con.execute("""SELECT SUM(t.points) FROM tasks t JOIN sprints s ON s.sprint_id = t.sprint_id
                         WHERE s.status = 'Active'""").fetchone()[0]
    assert metrics.workload(con).assigned_points.sum() == raw


def test_project_summary_is_consistent(con):
    ps = metrics.project_summary(con)
    assert ((ps.pct_complete >= 0) & (ps.pct_complete <= 1)).all()
    assert (ps.done_points <= ps.total_points).all()


def test_burndown_final_point_matches_open_work(con):
    sid, total, done = con.execute("""SELECT sprint_id, total_points, done_points FROM v_sprint_summary
                                      WHERE status = 'Active' LIMIT 1""").fetchone()
    bd = metrics.burndown(con, sid)
    assert bd.iloc[-1].remaining == pytest.approx(total - done)
    assert bd.ideal.iloc[0] >= bd.ideal.iloc[-1]
