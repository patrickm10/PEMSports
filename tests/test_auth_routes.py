from fastapi.testclient import TestClient
from backend.main import app
from backend.core.auth import SESSION_COOKIE_NAME


def _client() -> TestClient:
    return TestClient(app)


class TestAuthFallback:
    """
    Cookie session + graceful fallback when Postgres is unreachable
    (default for current CI). Each test uses a fresh client so cookies
    cannot leak across cases (cookie is preferred over Bearer).
    """

    def test_register_fallback(self):
        with _client() as client:
            response = client.post(
                "/api/v1/auth/register",
                json={"email": "test@example.com", "password": "password123"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["email"] == "test@example.com"
            assert data["id"] == "dev-fallback-id"

    def test_login_sets_cookie_without_jwt_in_body(self):
        with _client() as client:
            response = client.post(
                "/api/v1/auth/token",
                data={"username": "test@example.com", "password": "password123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data == {"ok": True}
            assert "access_token" not in data
            assert SESSION_COOKIE_NAME in response.cookies
            assert response.cookies[SESSION_COOKIE_NAME]
            set_cookie = response.headers.get("set-cookie", "")
            assert "httponly" in set_cookie.lower()
            assert "samesite=lax" in set_cookie.lower()

    def test_me_with_session_cookie(self):
        with _client() as client:
            client.post(
                "/api/v1/auth/token",
                data={"username": "test@example.com", "password": "password123"},
            )
            response = client.get("/api/v1/auth/me")
            assert response.status_code == 200
            assert response.json()["email"] == "test@example.com"

    def test_me_with_bearer_still_works(self):
        with _client() as client:
            login_resp = client.post(
                "/api/v1/auth/token",
                data={"username": "bearer@example.com", "password": "password123"},
            )
            jwt = login_resp.cookies.get(SESSION_COOKIE_NAME)
            assert jwt
        with _client() as fresh:
            response = fresh.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {jwt}"},
            )
            assert response.status_code == 200
            assert response.json()["email"] == "bearer@example.com"

    def test_me_without_cookie_is_401(self):
        with _client() as client:
            response = client.get("/api/v1/auth/me")
            assert response.status_code == 401

    def test_invalid_token_rejected(self):
        with _client() as client:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid_garbage_token"},
            )
            assert response.status_code == 401

    def test_logout_clears_cookie(self):
        with _client() as client:
            client.post(
                "/api/v1/auth/token",
                data={"username": "test@example.com", "password": "password123"},
            )
            assert client.get("/api/v1/auth/me").status_code == 200
            out = client.post("/api/v1/auth/logout")
            assert out.status_code == 200
            assert out.json() == {"ok": True}
            assert client.get("/api/v1/auth/me").status_code == 401

    def test_login_not_rate_limited_on_first_attempt(self):
        with _client() as client:
            response = client.post(
                "/api/v1/auth/token",
                data={"username": "once@example.com", "password": "password123"},
            )
            assert response.status_code == 200
            assert response.status_code != 429
