"""SlowAPI limiter keyed on the ASGI client address.

`backend.main` installs uvicorn `ProxyHeadersMiddleware` so that, behind
Render (or another reverse proxy), `request.client` is rewritten from
`X-Forwarded-For` before this key function runs. Do not parse
`X-Forwarded-For` here: an untrusted header is a rate-limit bypass.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
