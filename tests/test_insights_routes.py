"""HTTP tests for PEM Insights routes."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.api.insights_routes import _parse_seasons
from backend.main import app

client = TestClient(app)
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "nfl_stats.db"


class TestInsightsRoutesValidation:
    def test_missing_context_value_returns_422(self):
        resp = client.get("/api/v1/insights", params={"position": "rb", "context": "surface"})
        assert resp.status_code == 422

    def test_invalid_position_returns_422(self):
        resp = client.get(
            "/api/v1/insights",
            params={"position": "dst", "context": "surface", "context_value": "Grass"},
        )
        assert resp.status_code == 422

    def test_invalid_context_returns_422(self):
        resp = client.get(
            "/api/v1/insights",
            params={"position": "rb", "context": "weather_impact", "context_value": "Yes"},
        )
        assert resp.status_code == 422

    def test_weather_context_stays_unregistered(self):
        resp = client.get(
            "/api/v1/insights",
            params={"position": "rb", "context": "weather", "context_value": "Indoor"},
        )
        assert resp.status_code == 422

    def test_week_22_returns_422(self):
        resp = client.get(
            "/api/v1/insights",
            params={
                "position": "rb",
                "context": "surface",
                "context_value": "Grass",
                "week": 22,
            },
        )
        assert resp.status_code == 422

    def test_garbage_seasons_does_not_500(self):
        resp = client.get(
            "/api/v1/insights",
            params={
                "position": "rb",
                "context": "surface",
                "context_value": "Grass",
                "seasons": "foo",
            },
        )
        assert resp.status_code != 500

    def test_parse_seasons_skips_non_ints(self):
        assert _parse_seasons("2024,foo,2023") == [2024, 2023]
        assert _parse_seasons("foo") is None
        assert _parse_seasons("2024") == [2024]

    def test_parse_seasons_skips_years_outside_rankings_bounds(self):
        assert _parse_seasons("2024,1999,2031") == [2024]
        assert _parse_seasons("2017") is None


@pytest.mark.skipif(not DB_PATH.exists(), reason="Baked nfl_stats.db required")
class TestInsightsRoutesSuccess:
    def test_insights_leaderboard(self):
        resp = client.get(
            "/api/v1/insights",
            params={
                "position": "rb",
                "context": "surface",
                "context_value": "Grass",
                "year": 2024,
                "limit": 5,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["position"] == "rb"
        assert "insights" in body
        assert body["insights"] is not None

    def test_insights_all_groups(self):
        resp = client.get(
            "/api/v1/insights",
            params={
                "position": "all",
                "context": "surface",
                "context_value": "Turf",
                "year": 2024,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["groups"] is not None
        assert len(body["groups"]) == 4

    def test_insights_contexts(self):
        resp = client.get(
            "/api/v1/insights/contexts",
            params={"position": "rb", "context": "surface", "year": 2024},
        )
        assert resp.status_code == 200
        values = resp.json().get("values") or []
        assert "Grass" in values or "Turf" in values

    def test_opponent_contexts_drive_leaderboard(self):
        resp = client.get(
            "/api/v1/insights/contexts",
            params={"position": "rb", "context": "opponent", "year": 2024},
        )
        assert resp.status_code == 200
        values = resp.json().get("values") or []
        assert values
        assert "kansas_city_chiefs" not in values
        sample = "KC" if "KC" in values else values[0]
        board = client.get(
            "/api/v1/insights",
            params={
                "position": "rb",
                "context": "opponent",
                "context_value": sample,
                "year": 2024,
                "limit": 5,
            },
        )
        assert board.status_code == 200
        body = board.json()
        assert body["context_value"] == sample
        assert body["insights"] is not None

    def test_location_contexts_drive_leaderboard(self):
        for context in ("indoor_outdoor", "elevation"):
            resp = client.get(
                "/api/v1/insights/contexts",
                params={"position": "rb", "context": context, "year": 2024},
            )
            assert resp.status_code == 200, context
            values = resp.json().get("values") or []
            assert values, context
            board = client.get(
                "/api/v1/insights",
                params={
                    "position": "rb",
                    "context": context,
                    "context_value": values[0],
                    "year": 2024,
                    "limit": 5,
                },
            )
            assert board.status_code == 200, context
            body = board.json()
            assert body["insights"] is not None
            for row in body["insights"] or []:
                assert row["sample_size"] >= 3
            scores = [
                r["insight_score"]
                for r in (body["insights"] or [])
                if r.get("insight_score") is not None
            ]
            assert scores == sorted(scores, reverse=True)

    def test_kc_and_slug_http_round_trip(self):
        abbr = client.get(
            "/api/v1/insights",
            params={
                "position": "rb",
                "context": "opponent",
                "context_value": "KC",
                "year": 2024,
                "limit": 10,
            },
        )
        slug = client.get(
            "/api/v1/insights",
            params={
                "position": "rb",
                "context": "opponent",
                "context_value": "kansas_city_chiefs",
                "year": 2024,
                "limit": 10,
            },
        )
        assert abbr.status_code == 200
        assert slug.status_code == 200
        a = abbr.json()
        s = slug.json()
        assert a["context_value"] == s["context_value"] == "KC"
        a_ids = [r["player_id"] for r in (a.get("insights") or [])]
        s_ids = [r["player_id"] for r in (s.get("insights") or [])]
        if not a_ids and not s_ids:
            pytest.skip("No RB vs KC insights in 2024 dataset")
        assert a_ids == s_ids

    def test_all_position_player_detail_uses_row_position(self):
        resp = client.get(
            "/api/v1/insights",
            params={
                "position": "all",
                "context": "surface",
                "context_value": "Grass",
                "year": 2024,
                "limit": 1,
            },
        )
        assert resp.status_code == 200
        groups = resp.json().get("groups") or []
        row = None
        for group in groups:
            if group.get("insights"):
                row = group["insights"][0]
                row_position = group["position"]
                break
        if row is None:
            pytest.skip("No grouped insights for 2024")
        detail = client.get(
            f"/api/v1/insights/player/{row['player_id']}",
            params={
                "position": row.get("position") or row_position,
                "context": "surface",
                "context_value": "Grass",
                "year": 2024,
            },
        )
        assert detail.status_code == 200
        body = detail.json()
        assert body["player_id"] == row["player_id"]
        assert "observations" in body
        if body["observations"]:
            obs = body["observations"][0]
            assert "stadium_name" in obs
            assert "home_away" in obs
            assert "weather_bucket" in obs
            assert "indoor_outdoor" in obs
            assert "elevation_band" in obs
