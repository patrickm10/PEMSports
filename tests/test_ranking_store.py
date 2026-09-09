"""Ranking store SQL rewrite (no live Postgres required)."""

from unittest.mock import MagicMock, patch

from backend.data.ranking_store import _rewrite_postgres_sql, stats_generation


def test_rewrite_placeholders():
    sql, extra = _rewrite_postgres_sql("SELECT * FROM qb_weekly WHERE year = ? AND week = ?")
    assert extra is None
    assert sql.count("%s") == 2
    assert "?" not in sql


def test_rewrite_pragma_table_info():
    sql, extra = _rewrite_postgres_sql("PRAGMA table_info('qb_weekly')")
    assert extra == "qb_weekly"
    assert "information_schema.columns" in sql
    assert sql.count("%s") == 1


def test_rewrite_show_tables():
    sql, extra = _rewrite_postgres_sql("SHOW TABLES")
    assert extra is None
    assert "information_schema.tables" in sql


def test_stats_generation_uses_last_known_on_transient_pg_failure():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (7,)

    with patch("backend.data.ranking_store.is_postgres", return_value=True):
        with patch("backend.data.ranking_store._pg_conn", return_value=conn):
            assert stats_generation() == 7

        conn.execute.side_effect = RuntimeError("connection reset")
        assert stats_generation() == 7
