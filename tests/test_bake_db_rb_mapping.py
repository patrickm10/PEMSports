"""
RB bake mapping must preserve receiving yards (R_YDS) separately from rush_yds.

Runs _discover_and_build against parquet in-memory. Does not unlink or rewrite
data/nfl_stats.db.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import duckdb
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RB_PARQUET = PROJECT_ROOT / "data" / "rankings" / "RB_weekly.parquet"


def _load_bake_db():
    path = PROJECT_ROOT / "scripts" / "bake_db.py"
    spec = importlib.util.spec_from_file_location("bake_db", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rb_weekly_preserves_receiving_yds():
    if not RB_PARQUET.exists():
        pytest.skip("RB weekly parquet not present")

    bake_db = _load_bake_db()
    conn = duckdb.connect(":memory:")
    try:
        columns, select_stmt = bake_db._discover_and_build(conn, RB_PARQUET, "RB")
        colset = {c.lower() for c in columns}
        assert "rush_yds" in colset
        assert "yds" in colset, "receiving yards column (from R_YDS) missing after mapping"

        path_str = str(RB_PARQUET).replace("\\", "/")
        conn.execute(
            f"CREATE TABLE rb_weekly AS SELECT {select_stmt} "
            f"FROM read_parquet('{path_str}') src"
        )
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
