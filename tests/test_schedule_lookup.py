"""Tests for schedule_lookup home/away derivation."""

import sys
from pathlib import Path

import polars as pl
import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pipelines.schedule_lookup import build_home_away_from_stadium, build_home_stadium_map

STADIUM_CSV = Path(__file__).resolve().parent.parent / "data" / "nfl_metadata" / "stadium.csv"
RB_WEEKLY = Path(__file__).resolve().parent.parent / "data" / "rankings" / "RB_weekly.parquet"


@pytest.mark.skipif(not STADIUM_CSV.exists(), reason="stadium.csv required")
def test_build_home_stadium_map_has_all_teams():
    mapping = build_home_stadium_map()
    assert not mapping.is_empty()
    assert "team" in mapping.columns
    assert "stadium_name" in mapping.columns
    assert mapping.filter(pl.col("team") == "kansas_city_chiefs").height == 1


@pytest.mark.skipif(
    not STADIUM_CSV.exists() or not RB_WEEKLY.exists(),
    reason="stadium.csv and RB weekly parquet required",
)
def test_stadium_fallback_produces_home_and_away():
    weekly = pl.read_parquet(RB_WEEKLY)
    schedule = build_home_away_from_stadium(weekly)
    assert not schedule.is_empty()
    values = set(schedule["home_away"].drop_nulls().unique().to_list())
    assert "Home" in values
    assert "Away" in values


@pytest.mark.skipif(not RB_WEEKLY.exists(), reason="RB weekly parquet required")
def test_stadium_fallback_matches_chiefs_home_games():
    weekly = pl.read_parquet(RB_WEEKLY)
    mapping = build_home_stadium_map()
    schedule = build_home_away_from_stadium(weekly, stadium_map=mapping)

    chiefs_home = mapping.filter(pl.col("team") == "kansas_city_chiefs")["stadium_name"][0]
    chiefs_home_games = weekly.filter(
        (pl.col("team") == "kansas_city_chiefs")
        & (pl.col("year") == 2024)
        & (pl.col("stadium_name") == chiefs_home)
    ).select(["year", "week", "team"]).unique()

    merged = chiefs_home_games.join(schedule, on=["year", "week", "team"], how="left")
    assert merged.height > 0
    assert merged.filter(pl.col("home_away") != "Home").height == 0
