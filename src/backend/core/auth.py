"""
Authentication primitives: JWT issuance/verification and password hashing.

Design:
- Tokens are signed JWTs (HS256 by default). The secret and algorithm come
  from `backend.core.config` which refuses to start the process in
  production without a real `JWT_SECRET`.
- `get_current_user` is the single FastAPI dependency for protected
  routes. It prefers the httpOnly `pem_session` cookie, then
  `Authorization: Bearer`. Missing or invalid credentials are always 401
  (including development) so guest `/auth/me` probes stay guest.
- Session cookies are first-party (SameSite=Lax). SameSite=None is
  forbidden here — that would require a CSRF token and third-party cookies.
- Password hashing uses `passlib` with bcrypt.
- Never log cookie values, Authorization headers, or JWT strings.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.core.config import config

ACCESS_TOKEN_EXPIRE_MINUTES = config.access_token_expire_minutes
SESSION_COOKIE_NAME = "pem_session"
SESSION_COOKIE_PATH = "/api/v1/auth"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserProfile(BaseModel):
    id: str
    email: str


class TokenPayload(BaseModel):
    sub: str
    exp: int


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Sign and return a JWT containing the provided claims + expiry."""
    to_encode = dict(data)
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(datetime.now(timezone.utc).timestamp())})
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
    return TokenPayload(sub=sub, exp=exp)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time bcrypt verification."""
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Return a bcrypt hash suitable for storage."""
    return _pwd_context.hash(password)


def apply_session_cookie(response: Response, token: str) -> None:
    """Set the httpOnly session cookie. Do not log `token`."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=int(ACCESS_TOKEN_EXPIRE_MINUTES) * 60,
        path=SESSION_COOKIE_PATH,
        httponly=True,
        secure=not config.is_development,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    """Expire the session cookie (logout)."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value="",
        max_age=0,
        expires=0,
        path=SESSION_COOKIE_PATH,
        httponly=True,
        secure=not config.is_development,
        samesite="lax",
    )


async def get_current_user(
    bearer: Optional[str] = Depends(oauth2_scheme),
    pem_session: Optional[str] = Cookie(default=None),
) -> UserProfile:
    """FastAPI dependency: resolve the caller to a UserProfile or raise 401.

    Cookie wins when present. Bearer remains for tests and break-glass.
    A missing cookie/header is always 401 so guests are not mocked as signed in.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = pem_session or bearer
    if not token:
        raise credentials_exc

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exc

    # Lazy import to avoid a circular dependency with user_service → auth.
    from backend.services.user_service import get_user_by_email

    user = await get_user_by_email(payload.sub)
    if user is None:
        if config.allow_mock_auth:
            return UserProfile(id="dev-user", email=payload.sub)
        raise credentials_exc

    return UserProfile(id=user["id"], email=user["email"])
