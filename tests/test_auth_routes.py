import pytest
from fastapi.testclient import TestClient
from backend.main import app

class TestAuthFallback:
    """
    Tests the graceful fallback and auth endpoints when Postgres is 
    unreachable (which is the default state for our current CI/CD environment).
    """

    def test_register_fallback(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["email"] == "test@example.com"
        assert data["id"] == "dev-fallback-id"

    def test_login_fallback(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "test@example.com", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_me_fallback(self, client: TestClient):
        # First get a token
        login_resp = client.post(
            "/api/v1/auth/token",
            data={"username": "test@example.com", "password": "password123"}
        )
        token = login_resp.json()["access_token"]

        # Then access /me
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    def test_invalid_token_rejected(self, client: TestClient):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_garbage_token"}
        )
        # Even in fallback mode, an explicitly invalid JWT syntax should 401
        assert response.status_code == 401
