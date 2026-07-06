"""
Integration tests for API player analytics routes.

Verifies the players router is wired and endpoints return stable contracts.
"""
import pytest


class TestPlayerSearch:
    def test_search_returns_results_envelope(self, client):
        response = client.get("/api/v1/players/search?q=mahomes&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_search_hit_shape(self, client):
        response = client.get("/api/v1/players/search?q=mahomes&limit=1")
        data = response.json()
        if data["results"]:
            hit = data["results"][0]
            assert "player_id" in hit
            assert "player_name" in hit
            assert "match_score" in hit


class TestPlayerAnalytics:
    @pytest.fixture
    def qb_player_id(self, client):
        response = client.get("/api/v1/players/search?q=mahomes&limit=1")
        results = response.json().get("results") or []
        if not results:
            pytest.skip("No QB search results in baked database")
        return results[0]["player_id"]

    def test_splits_returns_200(self, client, qb_player_id):
        response = client.get(
            f"/api/v1/players/{qb_player_id}/splits/opponent?pos=QB"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dimension"] == "opponent"
        assert "splits" in data

    def test_splits_by_year_returns_200(self, client, qb_player_id):
        response = client.get(
            f"/api/v1/players/{qb_player_id}/splits/surface/by-year?pos=QB"
        )
        assert response.status_code == 200
        data = response.json()
        assert "rows" in data
        assert "years" in data

    def test_weekly_returns_200(self, client, qb_player_id):
        response = client.get(
            f"/api/v1/players/{qb_player_id}/weekly?pos=QB&seasons=2024"
        )
        assert response.status_code == 200
        data = response.json()
        assert "seasons" in data
        assert "metric_keys" in data

    def test_metadata_returns_200(self, client, qb_player_id):
        response = client.get(
            f"/api/v1/players/{qb_player_id}/metadata?pos=QB"
        )
        assert response.status_code == 200
        data = response.json()
        assert "splits" in data

    def test_invalid_dimension_returns_422(self, client, qb_player_id):
        response = client.get(
            f"/api/v1/players/{qb_player_id}/splits/not-a-dimension?pos=QB"
        )
        assert response.status_code == 422
