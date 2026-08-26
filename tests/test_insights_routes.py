"""HTTP tests for PEM Insights routes."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

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
            params={"position": "rb", "context": "weather", "context_value": "Rain"},
        )
        assert resp.status_code == 422


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
