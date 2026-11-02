-- Task-level view with derived overdue flag
CREATE VIEW v_task_enriched AS
SELECT t.*, p.name AS project, s.sprint_no, s.status AS sprint_status, pe.name AS assignee,
       (t.status NOT IN ('Done','Carried Over') AND t.due_date < c.as_of) AS is_overdue,
       CASE WHEN t.status NOT IN ('Done','Carried Over') AND t.due_date < c.as_of
            THEN date_diff('day', t.due_date, c.as_of) END AS days_overdue
FROM tasks t
JOIN sprints  s  ON s.sprint_id  = t.sprint_id
JOIN projects p  ON p.project_id = t.project_id
JOIN people   pe ON pe.person_id = t.assignee_id
CROSS JOIN config c;

-- One row per sprint: scope, scope creep, progress, velocity
CREATE VIEW v_sprint_summary AS
WITH agg AS (
  SELECT s.sprint_id, s.project_id, s.sprint_no, s.start_date, s.end_date, s.status,
         COALESCE(SUM(t.points) FILTER (WHERE t.added_mid_sprint = 0), 0)::INTEGER AS initial_points,
         COALESCE(SUM(t.points) FILTER (WHERE t.added_mid_sprint = 1), 0)::INTEGER AS added_points,
         COALESCE(SUM(t.points) FILTER (WHERE t.status = 'Done'), 0)::INTEGER      AS done_points,
         COUNT(t.task_id)::INTEGER AS task_count
  FROM sprints s LEFT JOIN tasks t ON t.sprint_id = s.sprint_id
  GROUP BY s.sprint_id, s.project_id, s.sprint_no, s.start_date, s.end_date, s.status
)
SELECT a.*, p.name AS project,
       (a.initial_points + a.added_points) AS total_points,
       ROUND(a.done_points * 1.0 / NULLIF(a.initial_points + a.added_points, 0), 3) AS pct_done,
       LEAST(1.0, GREATEST(0.0,
         (date_diff('day', a.start_date, c.as_of) + 1) /
         (date_diff('day', a.start_date, a.end_date) + 1.0))) AS elapsed_pct
FROM agg a
JOIN projects p ON p.project_id = a.project_id
CROSS JOIN config c;

-- One row per project
CREATE VIEW v_project_summary AS
SELECT p.project_id, p.name AS project, p.sponsor, p.start_date, p.end_date,
       COUNT(t.task_id)::INTEGER AS tasks,
       COALESCE(SUM(t.points), 0)::INTEGER AS total_points,
       COALESCE(SUM(t.points) FILTER (WHERE t.status = 'Done'), 0)::INTEGER AS done_points,
       ROUND(COALESCE(SUM(t.points) FILTER (WHERE t.status = 'Done'), 0) * 1.0
             / NULLIF(SUM(t.points), 0), 3) AS pct_complete,
       (COUNT(*) FILTER (WHERE t.is_overdue))::INTEGER AS overdue_tasks,
       (COUNT(*) FILTER (WHERE t.status = 'Blocked'))::INTEGER AS blocked_tasks
FROM projects p LEFT JOIN v_task_enriched t ON t.project_id = p.project_id
GROUP BY p.project_id, p.name, p.sponsor, p.start_date, p.end_date;

-- Points assigned in currently active sprints vs per-sprint capacity
CREATE VIEW v_workload AS
SELECT pe.person_id, pe.name, pe.role, pe.capacity_points AS capacity,
       COALESCE(SUM(t.points), 0)::INTEGER AS assigned_points,
       ROUND(COALESCE(SUM(t.points), 0) * 1.0 / pe.capacity_points, 2) AS utilization
FROM people pe
LEFT JOIN tasks t ON t.assignee_id = pe.person_id
  AND t.sprint_id IN (SELECT sprint_id FROM sprints WHERE status = 'Active')
GROUP BY pe.person_id, pe.name, pe.role, pe.capacity_points;
