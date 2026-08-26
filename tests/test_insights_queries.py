"""
Integration tests for PEM Insights queries.

Requires baked data/nfl_stats.db.
"""

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.data.insights_queries import (
    query_insights_leaderboard,
    query_insights_player_detail,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "nfl_stats.db"


pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(), reason="Baked nfl_stats.db required"
)


class TestInsightsLeaderboard:
    def test_surface_grass_returns_insights(self):
        result = query_insights_leaderboard(
            position="rb",
            context="surface",
            context_value="Grass",
            year=2024,
            limit=5,
        )
        assert result["position"] == "rb"
        assert result["context"] == "surface"
        insights = result["insights"]
        assert isinstance(insights, list)
        if insights:
            row = insights[0]
            for key in (
                "player_id",
                "sample_size",
                "baseline_value",
                "context_average",
                "absolute_delta",
                "relative_delta_pct",
                "sample_strength",
                "insight_score",
            ):
                assert key in row
            assert row["sample_size"] >= 3

    def test_all_position_returns_groups(self):
        result = query_insights_leaderboard(
            position="all",
            context="surface",
            context_value="Turf",
            year=2024,
            limit=3,
        )
        assert result["position"] == "all"
        assert result["groups"] is not None
        assert len(result["groups"]) == 4
        positions = {g["position"] for g in result["groups"]}
        assert positions == {"qb", "rb", "wr", "te"}

    def test_week_filter_does_not_zero_relative_delta(self):
        """LOO baseline must use full season; week filter only scopes observations."""
        full = query_insights_leaderboard(
            position="rb",
            context="surface",
            context_value="Grass",
            year=2024,
            limit=50,
        )
        week_only = query_insights_leaderboard(
            position="rb",
            context="surface",
            context_value="Grass",
            year=2024,
            week=1,
            limit=50,
        )
        full_insights = {r["player_id"]: r for r in (full.get("insights") or [])}
        week_insights = week_only.get("insights") or []

        for row in week_insights:
            pid = row["player_id"]
            if pid not in full_insights:
                continue
            full_row = full_insights[pid]
            if full_row.get("relative_delta_pct") is None:
                continue
            assert row.get("relative_delta_pct") is not None
            assert row["relative_delta_pct"] != 0 or full_row["relative_delta_pct"] == 0
            # Baseline must not collapse to context average when week filtered
            if row.get("baseline_value") is not None and row.get("context_average") is not None:
                assert row["baseline_value"] != row["context_average"] or row["absolute_delta"] == 0


class TestInsightsPlayerDetail:
    def test_player_detail_schema(self):
        leaderboard = query_insights_leaderboard(
            position="qb",
            context="surface",
            context_value="Grass",
            year=2024,
            limit=1,
        )
        insights = leaderboard.get("insights") or []
        if not insights:
            pytest.skip("No QB grass insights in dataset")

        player_id = insights[0]["player_id"]
        detail = query_insights_player_detail(
            position="qb",
            player_id=player_id,
            context="surface",
            context_value="Grass",
            year=2024,
        )
        assert detail["player_id"] == player_id
        assert "summary" in detail
        assert "observations" in detail
        assert detail["summary"]["sample_strength"] in ("Low", "Moderate", "Strong", None)

        if detail["observations"]:
            obs = detail["observations"][0]
            for key in (
                "season",
                "week",
                "opponent",
                "stadium_name",
                "surface_type",
                "home_away",
                "fantasy_points",
                "season_baseline",
                "relative_change_pct",
            ):
                assert key in obs
