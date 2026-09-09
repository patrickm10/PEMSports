"""Ranking store SQL rewrite (no live Postgres required)."""

from backend.data.ranking_store import _rewrite_postgres_sql


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
