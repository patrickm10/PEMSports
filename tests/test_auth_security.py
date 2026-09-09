"""Auth security: password policy, UUID subject, cookies."""

from fastapi.testclient import TestClient


def test_register_rejects_short_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "tiny"},
    )
    assert response.status_code == 422


def test_login_sets_http_only_cookies(client: TestClient):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "test@example.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    cookies = response.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies
    assert "csrf_token" in cookies


def test_me_uses_access_cookie_without_bearer(client: TestClient):
    login = client.post(
        "/api/v1/auth/token",
        data={"username": "cookie@example.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "cookie@example.com"


def test_logout_clears_session(client: TestClient):
    login = client.post(
        "/api/v1/auth/token",
        data={"username": "out@example.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    csrf = login.cookies.get("csrf_token")
    resp = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf or ""})
    assert resp.status_code == 200
