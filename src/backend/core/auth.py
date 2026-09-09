"""
Authentication primitives: JWT access tokens, refresh sessions, password hashing.

Access tokens use `sub` = user UUID. Refresh tokens are opaque hashed values
stored in Postgres. Cookies are httpOnly; a non-httpOnly csrf_token cookie
pairs with X-CSRF-Token for cross-site cookie POSTs.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.core.config import config

ACCESS_TOKEN_EXPIRE_MINUTES = config.access_token_expire_minutes
REFRESH_COOKIE = "refresh_token"
ACCESS_COOKIE = "access_token"
CSRF_COOKIE = "csrf_token"
MIN_PASSWORD_LENGTH = 10

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserProfile(BaseModel):
    id: str
    email: str
    plan: str = "free"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    email: Optional[str] = None


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Sign and return a JWT containing the provided claims + expiry."""
    to_encode = dict(data)
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update(
        {
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "typ": "access",
        }
    )
    return jwt.encode(to_encode, config.jwt_secret, algorithm=config.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate a JWT. Raises `JWTError` on any failure."""
    payload = jwt.decode(
        token, config.jwt_secret, algorithms=[config.jwt_algorithm]
    )
    sub = payload.get("sub")
    exp = payload.get("exp")
    if not sub or not exp:
        raise JWTError("token missing required claims")
    return TokenPayload(sub=str(sub), exp=int(exp), email=payload.get("email"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time bcrypt verification."""
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Return a bcrypt hash suitable for storage."""
    return _pwd_context.hash(password)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _cookie_kwargs(*, max_age: int, httponly: bool) -> dict[str, Any]:
    return {
        "httponly": httponly,
        "secure": config.cookie_secure,
        "samesite": config.cookie_samesite,
        "max_age": max_age,
        "path": "/",
    }


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
) -> None:
    access_age = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    refresh_age = config.refresh_token_expire_days * 86400
    response.set_cookie(
        ACCESS_COOKIE, access_token, **_cookie_kwargs(max_age=access_age, httponly=True)
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, **_cookie_kwargs(max_age=refresh_age, httponly=True)
    )
    csrf_kw = _cookie_kwargs(max_age=refresh_age, httponly=False)
    response.set_cookie(CSRF_COOKIE, csrf_token, **csrf_kw)


def clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/")


def csrf_header_matches(request: Request) -> bool:
    header = request.headers.get("x-csrf-token") or ""
    cookie = request.cookies.get(CSRF_COOKIE) or ""
    if not header or not cookie:
        return False
    return secrets.compare_digest(header, cookie)


def _extract_access_token(
    request: Request, header_token: Optional[str]
) -> Optional[str]:
    if header_token:
        return header_token
    return request.cookies.get(ACCESS_COOKIE)


def _credentials_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _mock_profile(*, email: str = "dev@example.com") -> UserProfile:
    return UserProfile(id="dev-user", email=email, plan="premium")


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> UserProfile:
    """Resolve the caller to a UserProfile or raise 401."""
    raw = _extract_access_token(request, token)
    if raw is None:
        if config.allow_mock_auth:
            return _mock_profile()
        raise _credentials_exc()

    try:
        payload = decode_access_token(raw)
    except JWTError:
        raise _credentials_exc()

    from backend.services.user_service import get_user_by_id

    user = await get_user_by_id(payload.sub)
    if user is None:
        if config.allow_mock_auth:
            return _mock_profile(email=payload.email or payload.sub)
        raise _credentials_exc()

    return UserProfile(
        id=user["id"],
        email=user["email"],
        plan=user.get("plan") or "free",
    )


async def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[UserProfile]:
    raw = _extract_access_token(request, token)
    if raw is None and not config.allow_mock_auth:
        return None
    try:
        return await get_current_user(request, token)
    except HTTPException:
        return None
