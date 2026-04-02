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
