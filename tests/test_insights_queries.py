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
    query_insights_context_values,
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


class TestOpponentNormalization:
    def test_kc_and_slug_return_same_insights(self):
        kwargs = dict(position="rb", context="opponent", year=2024, limit=15)
        by_abbr = query_insights_leaderboard(context_value="KC", **kwargs)
        by_slug = query_insights_leaderboard(
            context_value="kansas_city_chiefs", **kwargs
        )
        assert by_abbr["context_value"] == "KC"
        assert by_slug["context_value"] == "KC"
        abbr_rows = by_abbr.get("insights") or []
        slug_rows = by_slug.get("insights") or []
        if not abbr_rows and not slug_rows:
            kwargs = dict(
                position="rb",
                context="opponent",
                years=[2022, 2023, 2024],
                year=None,
                limit=15,
            )
            by_abbr = query_insights_leaderboard(context_value="KC", **kwargs)
            by_slug = query_insights_leaderboard(
                context_value="kansas_city_chiefs", **kwargs
            )
            abbr_rows = by_abbr.get("insights") or []
            slug_rows = by_slug.get("insights") or []
        if not abbr_rows and not slug_rows:
            pytest.skip("No RB vs KC insights in baked dataset")
        abbr_ids = [r["player_id"] for r in abbr_rows]
        slug_ids = [r["player_id"] for r in slug_rows]
        assert abbr_ids == slug_ids
        for a, s in zip(abbr_rows, slug_rows):
            assert a.get("insight_score") == s.get("insight_score")
            assert a.get("relative_delta_pct") == s.get("relative_delta_pct")
            assert a.get("sample_size") == s.get("sample_size")

    def test_opponent_context_values_are_abbreviations(self):
        result = query_insights_context_values(
            position="rb", context="opponent", year=2024
        )
        values = result.get("values") or []
        assert values, "Expected opponent context values for 2024"
        assert "kansas_city_chiefs" not in values
        assert all(isinstance(v, str) and v == v.strip() for v in values)
        if "KC" in values:
            driven = query_insights_leaderboard(
                position="rb",
                context="opponent",
                context_value="KC",
                year=2024,
                limit=5,
            )
            assert driven["context_value"] == "KC"
            assert driven["insights"] is not None


class TestAllContexts:
    def test_all_four_contexts_return_nonempty_leaderboards(self):
        for context in ("surface", "opponent", "stadium", "home_away"):
            ctx = query_insights_context_values(
                position="rb", context=context, year=2024
            )
            values = ctx.get("values") or []
            if not values:
                if context == "home_away":
                    continue
                pytest.fail(f"Expected context values for {context} in 2024")
            result = query_insights_leaderboard(
                position="rb",
                context=context,
                context_value=values[0],
                year=2024,
                limit=5,
            )
            insights = result.get("insights") or []
            if not insights:
                # One opponent game per season rarely meets min sample; use a 3-year window.
                result = query_insights_leaderboard(
                    position="rb",
                    context=context,
                    context_value=values[0],
                    years=[2022, 2023, 2024],
                    year=None,
                    limit=5,
                )
                insights = result.get("insights") or []
            if context == "home_away" and not insights:
                continue
            assert insights, f"Expected non-empty {context} leaderboard for 2024"

    def test_position_all_groups_for_each_context(self):
        for context, fallback in (
            ("surface", "Grass"),
            ("opponent", "KC"),
            ("stadium", None),
            ("home_away", "Home"),
        ):
            ctx = query_insights_context_values(
                position="all", context=context, year=2024
            )
            values = ctx.get("values") or []
            if not values:
                if context == "home_away":
                    continue
                if fallback:
                    values = [fallback]
                else:
                    pytest.skip(f"No {context} values for position=all")
            value = fallback if fallback in values else values[0]
            result = query_insights_leaderboard(
                position="all",
                context=context,
                context_value=value,
                year=2024,
                limit=3,
            )
            assert result["position"] == "all"
            assert result["groups"] is not None
            assert len(result["groups"]) == 4
            assert {g["position"] for g in result["groups"]} == {"qb", "rb", "wr", "te"}
            assert result["insights"] is None


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
                "in_context",
            ):
                assert key in obs

    def test_player_detail_nulls_are_present_not_omitted(self):
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
        detail = query_insights_player_detail(
            position="qb",
            player_id=insights[0]["player_id"],
            context="surface",
            context_value="Grass",
            year=2024,
        )
        summary = detail["summary"]
        for key in (
            "player_name",
            "team",
            "baseline_value",
            "context_average",
            "absolute_delta",
            "relative_delta_pct",
            "sample_strength",
            "insight_score",
        ):
            assert key in summary
