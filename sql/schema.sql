CREATE TABLE config   (as_of DATE);
CREATE TABLE people   (person_id INTEGER PRIMARY KEY, name VARCHAR, role VARCHAR,
                       capacity_points INTEGER CHECK (capacity_points > 0));
CREATE TABLE projects (project_id INTEGER PRIMARY KEY, name VARCHAR, sponsor VARCHAR,
                       start_date DATE, end_date DATE);
CREATE TABLE sprints  (sprint_id INTEGER PRIMARY KEY, project_id INTEGER, sprint_no INTEGER,
                       start_date DATE, end_date DATE,
                       status VARCHAR CHECK (status IN ('Completed','Active','Planned')));
CREATE TABLE tasks    (task_id INTEGER PRIMARY KEY, project_id INTEGER, sprint_id INTEGER,
                       title VARCHAR, assignee_id INTEGER,
                       points INTEGER CHECK (points > 0),
                       status VARCHAR CHECK (status IN ('To Do','In Progress','Blocked','Done','Carried Over')),
                       due_date DATE, completed_date DATE, blocked_by INTEGER,
                       added_mid_sprint INTEGER CHECK (added_mid_sprint IN (0,1)),
                       added_date DATE);
CREATE TABLE risks    (risk_id INTEGER PRIMARY KEY, project_id INTEGER, description VARCHAR,
                       likelihood INTEGER CHECK (likelihood BETWEEN 1 AND 5),
                       impact INTEGER CHECK (impact BETWEEN 1 AND 5),
                       owner_id INTEGER, mitigation VARCHAR,
                       status VARCHAR CHECK (status IN ('Open','Mitigating','Closed')),
                       raised_date DATE);
CREATE TABLE decisions(decision_id INTEGER PRIMARY KEY, project_id INTEGER, decision_date DATE,
                       decision VARCHAR, rationale VARCHAR, owner_id INTEGER);
