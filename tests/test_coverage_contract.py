"""
Coverage contract tests — seasons × positions × weeks metadata and historical queries.

Guards against 2025-only regressions in parquet bake / seasons metadata.
"""
from __future__ import annotations

import pytest

EXPECTED_YEARS = list(range(2020, 2026))
EXPECTED_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]
EXPECTED_WEEKS = list(range(1, 19))


class TestCoverageSeasonsMetadata:
    @pytest.mark.parametrize("pos", EXPECTED_POSITIONS)
    def test_seasons_include_expected_years(self, client, pos):
        response = client.get(f"/api/v1/rankings/{pos}/seasons")
        assert response.status_code == 200
        seasons = response.json()
        assert isinstance(seasons, list)
        for year in EXPECTED_YEARS:
            assert year in seasons, f"{pos} missing season {year} in {seasons}"

    @pytest.mark.parametrize("pos", EXPECTED_POSITIONS)
    def test_seasons_ordered_descending(self, client, pos):
        seasons = client.get(f"/api/v1/rankings/{pos}/seasons").json()
        assert seasons == sorted(seasons, reverse=True)


class TestCoverageSeasonalQueries:
    @pytest.mark.parametrize("pos", EXPECTED_POSITIONS)
    @pytest.mark.parametrize("year", EXPECTED_YEARS)
    def test_seasonal_year_returns_rows(self, client, pos, year):
        response = client.get(f"/api/v1/rankings/{pos}?year={year}&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, f"{pos} seasonal year={year} returned empty"
        assert all(int(row.get("year", year)) == year for row in data)


class TestCoverageWeeklyQueries:
    @pytest.mark.parametrize("pos", EXPECTED_POSITIONS)
    @pytest.mark.parametrize("year", [2020, 2022, 2024, 2025])
    def test_weeks_metadata_complete(self, client, pos, year):
        response = client.get(f"/api/v1/rankings/{pos}/weeks?year={year}")
        assert response.status_code == 200
        weeks = response.json()
        for week in EXPECTED_WEEKS:
            assert week in weeks, f"{pos} year={year} missing week {week}"

    @pytest.mark.parametrize("pos", EXPECTED_POSITIONS)
    @pytest.mark.parametrize("year", [2020, 2024, 2025])
    def test_weekly_representative_week_has_rows(self, client, pos, year):
        response = client.get(
            f"/api/v1/rankings/{pos}/weekly?year={year}&week=1&limit=5"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, f"{pos} weekly year={year} week=1 empty"


class TestCoverageValidationBounds:
    def test_year_below_range_422(self, client):
        assert client.get("/api/v1/rankings/QB?year=2017").status_code == 422

    def test_year_above_range_422(self, client):
        assert client.get("/api/v1/rankings/QB?year=2031").status_code == 422

    def test_empty_array_not_404_for_valid_empty_combo(self, client):
        # Valid bounds but improbable filter — must be 200 + [] not 404
        response = client.get("/api/v1/rankings/QB?year=2019&limit=5")
        assert response.status_code == 200
        assert response.json() == []


class TestBranding:
    def test_root_message_pem_sports(self, client):
        data = client.get("/").json()
        assert data.get("message") == "PEM Sports API"
        assert "NFL Stats Analyzer" not in str(data)

    def test_health_service_pem_sports(self, client):
        data = client.get("/health").json()
        assert data.get("service") == "pem-sports-api"
