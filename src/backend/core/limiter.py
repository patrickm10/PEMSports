from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_ip(request: Request) -> str:
    """Resolve the caller IP behind reverse proxies (e.g. Render).

    Without honoring X-Forwarded-For, every request appears to come from the
    proxy's address and all users share a single rate-limit bucket.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=get_client_ip)
