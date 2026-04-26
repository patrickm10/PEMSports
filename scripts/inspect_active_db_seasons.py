"""
Inspect the exact DuckDB file the backend would use and print distinct years.

This is meant to reconcile:
- DuckDB contents (direct SQL)
- query_seasons() output (backend logs)
- /api/v1/rankings/{pos}/seasons API response
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    db_path = Path(os.environ.get("NFL_STATS_DB_PATH", str(repo_root / "data" / "nfl_stats.db"))).resolve()
    print(f"NFL_STATS_DB_PATH env: {os.environ.get('NFL_STATS_DB_PATH')!r}")
    print(f"Resolved DB path:      {db_path}")
    print(f"Exists:               {db_path.exists()}")
    if not db_path.exists():
        raise SystemExit("DB file does not exist. This would cause backend 503.")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = con.execute("SELECT DISTINCT year FROM qb_seasonal ORDER BY year;").fetchall()
    finally:
        con.close()
    years = [r[0] for r in rows]
    print("DuckDB qb_seasonal distinct years:", years)


if __name__ == "__main__":
    main()

