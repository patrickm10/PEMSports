"""Tests for publish_rankings_pg incremental safety."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# publish_rankings_pg imports psycopg at module load; stub it for unit tests.
sys.modules.setdefault("psycopg", MagicMock())

from publish_rankings_pg import publish


def test_incremental_skips_delete_when_duckdb_slice_empty(tmp_path, monkeypatch):
    """Empty DuckDB slice must not delete an existing Postgres partition."""
    duck_path = tmp_path / "nfl_stats.db"
    duck_path.write_bytes(b"")  # existence check only; duck is mocked

    pg = MagicMock()
    duck = MagicMock()
    duck.execute.return_value.fetchall.return_value = []

    monkeypatch.setattr(
        "publish_rankings_pg.duckdb.connect",
        lambda *_args, **_kwargs: duck,
    )
    monkeypatch.setattr(
        "publish_rankings_pg.psycopg.connect",
        lambda *_args, **_kwargs: pg,
    )
    monkeypatch.setattr(
        "publish_rankings_pg._duck_tables",
        lambda _duck: ["qb_weekly"],
    )
    monkeypatch.setattr(
        "publish_rankings_pg._duck_schema",
        lambda _duck, _table: [("year", "INTEGER"), ("week", "INTEGER")],
    )
    monkeypatch.setattr("publish_rankings_pg._ensure_schema", lambda _pg: None)
    monkeypatch.setattr("publish_rankings_pg._ensure_table", lambda *_args: None)
    monkeypatch.setattr("publish_rankings_pg._copy_rows", lambda *_args: 0)
    monkeypatch.setattr("publish_rankings_pg._log_refresh", lambda *_args: None)

    publish(
        duck_path=duck_path,
        dsn="postgresql://example",
        mode="incremental",
        year=2025,
        week=10,
    )

    delete_calls = [
        c
        for c in pg.execute.call_args_list
        if "DELETE FROM stats.qb_weekly" in str(c.args[0])
    ]
    assert delete_calls == []
    pg.commit.assert_called_once()
