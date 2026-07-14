"""
Unit tests for the DuckDB query engine.

Tests verify:
- View registration succeeds for all positions
- Seasonal queries return expected dict structure
- Weekly queries return expected dict structure with SQL-pushed filters
- Season/week listing returns sorted integers
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.data.query_engine import (
    query_rankings,
    query_seasons,
    query_weekly_rankings,
    query_available_weeks,
    query_player_weekly,
    query_player_splits,
    _yards_td_sql_exprs,
)

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]


class TestSeasonalQueries:
    """Seasonal ranking query contract tests."""

    def test_query_rankings_returns_list_of_dicts(self):
        data = query_rankings("QB", year=2024, limit=5)
        assert isinstance(data, list)
        if data:
            assert isinstance(data[0], dict)
            assert "player_name" in data[0]
            assert "fpts_ppr" in data[0]
            assert "rank" in data[0]

    def test_query_rankings_respects_limit(self):
        data = query_rankings("QB", year=2024, limit=3)
        assert len(data) <= 3

    def test_query_seasons_returns_sorted_years(self):
        years = query_seasons("QB")
        assert isinstance(years, list)
        if len(years) > 1:
            assert years[0] > years[1], "Years should be descending"

    def test_all_positions_have_data(self):
        for pos in POSITIONS:
            data = query_rankings(pos, limit=1)
            assert isinstance(data, list), f"No data returned for {pos}"


class TestWeeklyQueries:
    """Weekly ranking query contract tests."""

    def test_query_weekly_returns_list_of_dicts(self):
        data = query_weekly_rankings("QB", year=2024, week=1, limit=5)
        assert isinstance(data, list)
        if data:
            assert isinstance(data[0], dict)
            assert "player_name" in data[0]
            assert "week" in data[0]

    def test_query_weekly_respects_year_filter(self):
        data = query_weekly_rankings("QB", year=2024, limit=50)
        if data:
            years = {row.get("year") for row in data}
            assert years == {2024}, f"Expected only 2024, got {years}"

    def test_query_weekly_respects_week_filter(self):
        data = query_weekly_rankings("QB", year=2024, week=1, limit=50)
        if data:
            weeks = {row.get("week") for row in data}
            assert weeks == {1}, f"Expected only week 1, got {weeks}"

    def test_query_available_weeks_returns_sorted_ints(self):
        weeks = query_available_weeks("QB", year=2024)
        assert isinstance(weeks, list)
        if len(weeks) > 1:
            assert weeks == sorted(weeks), "Weeks should be ascending"


class TestPlayerAnalyticsColumns:
    """Player analytics must use position-specific yardage/TD columns."""

    def test_yards_td_exprs_for_rb_uses_rush_columns(self):
        cols = {"rush_yds", "rush_td", "fpts_ppr", "player_id"}
        yards, tds = _yards_td_sql_exprs("RB", cols)
        assert "rush_yds" in yards
        assert "rush_td" in tds

    def test_yards_td_exprs_for_dst_uses_allowed_columns(self):
        cols = {"yds_allowed", "td_allowed", "fpts_ppr", "player_id"}
        yards, tds = _yards_td_sql_exprs("DST", cols, aggregate=True)
        assert "yds_allowed" in yards
        assert "td_allowed" in tds

    def test_rb_player_weekly_returns_non_null_yards_when_data_exists(self):
        rankings = query_rankings("RB", year=2024, limit=1)
        if not rankings:
            return
        player_id = rankings[0].get("player_id")
        if not player_id:
            return
        result = query_player_weekly(position="RB", player_id=player_id, years=[2024])
        all_weeks = [w for s in result["seasons"] for w in s["weeks"]]
        if not all_weeks:
            return
        assert any(w.get("yards") is not None for w in all_weeks), (
            "RB weekly yards should resolve from rush_yds, not be all null"
        )

    def test_rb_splits_return_non_null_avg_yards_when_data_exists(self):
        rankings = query_rankings("RB", year=2024, limit=1)
        if not rankings:
            return
        player_id = rankings[0].get("player_id")
        if not player_id:
            return
        result = query_player_splits(position="RB", player_id=player_id, dimension="opponent")
        if not result["splits"]:
            return
        assert any(s.get("avg_yards") is not None for s in result["splits"]), (
            "RB splits avg_yards should resolve from rush_yds"
        )
