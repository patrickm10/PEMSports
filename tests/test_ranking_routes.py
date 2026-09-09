"""
Integration tests for API ranking routes.

Tests verify:
- All endpoints return 200 with valid params
- Response shapes match expected contracts
- Previously broken routes (impact, defense) now work
- Health endpoint returns structured response
"""
import pytest


class TestSeasonalEndpoints:
    """GET /api/v1/rankings/{pos}"""

    def test_get_rankings_returns_200(self, client):
        response = client.get("/api/v1/rankings/QB?year=2024&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_rankings_response_shape(self, client):
        response = client.get("/api/v1/rankings/QB?year=2024&limit=1")
        data = response.json()
        if data:
            record = data[0]
            assert "player_name" in record
            assert "fpts_ppr" in record
            assert "rank" in record

    def test_get_seasons_returns_list(self, client):
        response = client.get("/api/v1/rankings/QB/seasons")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_csv_export_returns_csv(self, client):
        response = client.get("/api/v1/rankings/QB/csv?year=2024")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")


class TestWeeklyEndpoints:
    """GET /api/v1/rankings/{pos}/weekly and /api/v1/weekly-rankings"""

    def test_get_weekly_rankings_returns_200(self, client):
        response = client.get("/api/v1/rankings/QB/weekly?year=2024&week=1&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_weeks_returns_list(self, client):
        response = client.get("/api/v1/rankings/QB/weeks?year=2024")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_weekly_alias_returns_200(self, client):
        response = client.get("/api/v1/weekly-rankings?pos=QB&year=2024&week=1&limit=5")
        assert response.status_code == 200

    def test_invalid_position_returns_422(self, client):
        response = client.get("/api/v1/rankings/notapos")
        assert response.status_code == 422

    def test_injection_position_returns_422(self, client):
        response = client.get("/api/v1/rankings/qb_seasonal%20t%20--")
        assert response.status_code == 422

    def test_week_19_returns_422(self, client):
        response = client.get("/api/v1/rankings/QB/weekly?year=2024&week=19")
        assert response.status_code == 422

    def test_year_2017_returns_422(self, client):
        response = client.get("/api/v1/rankings/QB?year=2017")
        assert response.status_code == 422


class TestPreviouslyBrokenRoutes:
    """Verify routes that previously crashed due to missing imports."""

    def test_impact_endpoint_does_not_crash(self, client):
        response = client.get("/api/v1/rankings/QB/impact/test_id?metric=surface")
        # May return empty data (no matching player_id) but should NOT return 500
        assert response.status_code in (200, 404)

    def test_defense_endpoint_does_not_crash(self, client):
        response = client.get("/api/v1/rankings/QB/defense")
        # May return empty data but should NOT return 500
        assert response.status_code == 200


class TestHealthEndpoint:
    """GET /health"""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "positions_available" in data
