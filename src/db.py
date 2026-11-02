"""Builds an in-memory DuckDB database from the CSVs, then creates the SQL marts."""
from pathlib import Path

import duckdb

from .config import AS_OF, DATA_DIR, SQL_DIR
from .data_gen import generate

TABLES = ["people", "projects", "sprints", "tasks", "risks", "decisions"]


def build_connection(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    if not (data_dir / "tasks.csv").exists():
        generate(data_dir)
    con = duckdb.connect(":memory:")
    con.execute((SQL_DIR / "schema.sql").read_text())
    con.execute("INSERT INTO config VALUES (?)", [AS_OF])
    for name in TABLES:
        path = (data_dir / f"{name}.csv").as_posix()
        con.execute(f"INSERT INTO {name} BY NAME SELECT * FROM read_csv_auto('{path}')")
    con.execute((SQL_DIR / "marts.sql").read_text())
    return con
