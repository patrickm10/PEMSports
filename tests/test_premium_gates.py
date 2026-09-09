"""Premium feature gates (development mock user is premium)."""

from fastapi.testclient import TestClient


def test_rankings_remain_public(client: TestClient):
    resp = client.get("/api/v1/rankings/qb/seasons")
    assert resp.status_code != 401
    assert resp.status_code != 403


def test_insights_allowed_for_dev_mock_user(client: TestClient):
    resp = client.get(
        "/api/v1/insights",
        params={"position": "rb", "context": "surface", "context_value": "Grass"},
    )
    assert resp.status_code != 401
    assert resp.status_code != 403
