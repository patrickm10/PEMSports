"""Player analytics yards/TDs must use position-aware baked columns."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import duckdb

from backend.data.query_engine import (
    _DB_PATH,
    query_player_splits,
    query_player_weekly,
)


def _sample_player_id(position: str) -> str:
    if not _DB_PATH.exists():
        pytest.skip(f"Serving DB missing at {_DB_PATH}")
    conn = duckdb.connect(str(_DB_PATH), read_only=True)
    try:
        row = conn.execute(
            f"SELECT player_id FROM {position.lower()}_weekly WHERE year = 2024 LIMIT 1"
        ).fetchone()
        assert row is not None, f"No 2024 rows for {position}"
        return row[0]
    finally:
        conn.close()


def test_kicker_weekly_does_not_expose_fgm_fga_as_yards_tds():
    pid = _sample_player_id("K")
    payload = query_player_weekly(position="k", player_id=pid, years=[2024])
    weeks = payload["seasons"][0]["weeks"] if payload["seasons"] else []
    assert weeks, "Expected kicker weekly rows"
    for week in weeks:
        assert week["yards"] is None, "K yds column stores FGM, not yards"
        assert week["tds"] is None, "K td column stores FGA, not TDs"


def test_kicker_splits_do_not_expose_fgm_fga_as_yards_tds():
    pid = _sample_player_id("K")
    payload = query_player_splits(position="k", player_id=pid, dimension="opponent")
    for split in payload["splits"]:
        assert split["avg_yards"] is None
        assert split["avg_tds"] is None


def test_rb_weekly_uses_rush_columns_when_present():
    pid = _sample_player_id("RB")
    payload = query_player_weekly(position="rb", player_id=pid, years=[2024])
    weeks = [w for s in payload["seasons"] for w in s["weeks"]]
    assert any(w["yards"] is not None for w in weeks), "RB rush_yds should populate yards"


def test_dst_weekly_uses_allowed_columns_when_present():
    pid = _sample_player_id("DST")
    payload = query_player_weekly(position="dst", player_id=pid, years=[2024])
    weeks = [w for s in payload["seasons"] for w in s["weeks"]]
    assert any(w["yards"] is not None for w in weeks), "DST yds_allowed should populate yards"
