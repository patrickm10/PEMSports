"""Rate limiter client IP resolution behind reverse proxies."""

from starlette.requests import Request

from backend.core.limiter import get_client_ip


def _request(headers: dict[str, str] | None = None, client_host: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (client_host, 0),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
    }
    return Request(scope)


def test_get_client_ip_uses_x_forwarded_for_first_hop():
    request = _request(
        headers={"X-Forwarded-For": "203.0.113.10, 10.0.0.1"},
        client_host="10.0.0.1",
    )
    assert get_client_ip(request) == "203.0.113.10"


def test_get_client_ip_falls_back_to_direct_client():
    request = _request(client_host="198.51.100.4")
    assert get_client_ip(request) == "198.51.100.4"
