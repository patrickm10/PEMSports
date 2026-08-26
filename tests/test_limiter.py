"""Rate limiter client IP after uvicorn proxy-header rewrite."""

import asyncio

from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


class _Capture:
    ip: str | None = None


def _inner_app() -> ASGIApp:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        _Capture.ip = get_remote_address(Request(scope))
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    return app


async def _call(app: ASGIApp, *, headers: list[tuple[bytes, bytes]], client: str) -> None:
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "client": (client, 0),
        "server": ("testserver", 80),
    }

    async def receive() -> dict:
        return {"type": "http.request"}

    async def send(_message: dict) -> None:
        return None

    await app(scope, receive, send)


def test_proxy_headers_rewrite_client_for_rate_limit_key():
    """Behind Render, SlowAPI must key on the forwarded client, not the proxy."""
    _Capture.ip = None
    wrapped = ProxyHeadersMiddleware(_inner_app(), trusted_hosts="*")
    asyncio.run(
        _call(
            wrapped,
            headers=[(b"x-forwarded-for", b"203.0.113.10, 10.0.0.1")],
            client="10.0.0.1",
        )
    )
    assert _Capture.ip == "203.0.113.10"


def test_direct_client_used_when_no_forwarded_header():
    _Capture.ip = None
    wrapped = ProxyHeadersMiddleware(_inner_app(), trusted_hosts="*")
    asyncio.run(
        _call(
            wrapped,
            headers=[],
            client="198.51.100.4",
        )
    )
    assert _Capture.ip == "198.51.100.4"
