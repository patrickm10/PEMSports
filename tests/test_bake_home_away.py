"""Home/away bake must not drop weekly tables on merge failure."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import duckdb
import polars as pl
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_bake_db():
    path = PROJECT_ROOT / "scripts" / "bake_db.py"
    spec = importlib.util.spec_from_file_location("bake_db", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_merge_home_away_preserves_table_on_sql_failure(monkeypatch, tmp_path):
    bake_db = _load_bake_db()
    monkeypatch.setattr(bake_db, "PROJECT_ROOT", tmp_path)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE qb_weekly AS
        SELECT 2024 AS year, 1 AS week, 'kansas_city_chiefs' AS team, 12.5 AS fpts_ppr
        """
    )
    schedule = pl.DataFrame(
        {
            "year": [2024],
            "week": [1],
            "team": ["kansas_city_chiefs"],
            "home_away": ["Home"],
        }
    )

    def bad_write_parquet(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("not-a-parquet-file")

    monkeypatch.setattr(pl.DataFrame, "write_parquet", bad_write_parquet)

    with pytest.raises(duckdb.Error):
        bake_db._merge_home_away_schedule(conn, "qb_weekly", schedule, source="test")

    count = conn.execute("SELECT COUNT(*) FROM qb_weekly").fetchone()[0]
    cols = {d[0].lower() for d in conn.execute("SELECT * FROM qb_weekly LIMIT 0").description}
    assert count == 1
    assert "home_away" not in cols
    conn.close()


def test_merge_home_away_adds_column(tmp_path, monkeypatch):
    bake_db = _load_bake_db()
    monkeypatch.setattr(bake_db, "PROJECT_ROOT", tmp_path)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE qb_weekly AS
        SELECT 2024 AS year, 1 AS week, 'kansas_city_chiefs' AS team, 12.5 AS fpts_ppr
        """
    )
    schedule = pl.DataFrame(
        {
            "year": [2024],
            "week": [1],
            "team": ["kansas_city_chiefs"],
            "home_away": ["Home"],
        }
    )

    bake_db._merge_home_away_schedule(conn, "qb_weekly", schedule, source="test")
    row = conn.execute(
        "SELECT home_away, fpts_ppr FROM qb_weekly WHERE year = 2024 AND week = 1"
    ).fetchone()
    assert row == ("Home", 12.5)
    conn.close()


def test_bake_keeps_existing_db_on_failure(tmp_path, monkeypatch):
    bake_db = _load_bake_db()
    data_dir = tmp_path / "data" / "rankings"
    data_dir.mkdir(parents=True)
    db_path = tmp_path / "data" / "nfl_stats.db"

    monkeypatch.setattr(bake_db, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(bake_db, "DATA_DIR", data_dir)
    monkeypatch.setattr(bake_db, "DB_PATH", db_path)
    monkeypatch.setattr(bake_db, "PLAYERS_CSV", tmp_path / "data" / "players.csv")

    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE marker AS SELECT 1 AS ok")
    conn.close()

    def boom(_conn):
        raise RuntimeError("bake aborted")

    monkeypatch.setattr(bake_db, "_bake_into", boom)

    with pytest.raises(RuntimeError, match="bake aborted"):
        bake_db.bake()

    assert db_path.exists()
    verify = duckdb.connect(str(db_path), read_only=True)
    assert verify.execute("SELECT ok FROM marker").fetchone()[0] == 1
    verify.close()
    assert not db_path.with_suffix(".db.baking").exists()
