"""
RB bake mapping must preserve receiving yards (R_YDS) separately from rush_yds.
"""
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "nfl_stats.db"
RB_PARQUET = PROJECT_ROOT / "data" / "rankings" / "RB_weekly.parquet"


@pytest.fixture(scope="module")
def baked_db():
    if not RB_PARQUET.exists():
        pytest.skip("RB weekly parquet not present")
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "bake_db.py")],
        check=True,
        cwd=PROJECT_ROOT,
    )
    return DB_PATH


def test_rb_weekly_preserves_receiving_yds(baked_db):
    conn = duckdb.connect(str(baked_db), read_only=True)
    try:
        cols = {d[0].lower() for d in conn.execute("SELECT * FROM rb_weekly LIMIT 0").description}
        assert "yds" in cols, "receiving yards column (from R_YDS) missing after bake"

        row = conn.execute(
            """
            SELECT rush_yds, yds, rec
            FROM rb_weekly
            WHERE player_name = 'Leonard Fournette' AND year = 2022 AND week = 8
            """
        ).fetchone()
        assert row is not None
        rush_yds, rec_yds, rec = row
        assert rush_yds == 24.0
        assert rec_yds == 34.0
        assert rec == 3.0
    finally:
        conn.close()
