"""
Authentication primitives: JWT issuance/verification and password hashing.

Design:
- Tokens are signed JWTs (HS256 by default). The secret and algorithm come
  from `backend.core.config` which refuses to start the process in
  production without a real `JWT_SECRET`.
- `get_current_user` is the single FastAPI dependency for protected
  routes. It reads the `Authorization: Bearer <token>` header via
  `OAuth2PasswordBearer`, validates the JWT, and looks up the user in
  Postgres. Any failure raises 401.
- Password hashing uses `passlib` with bcrypt.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.core.config import config

ACCESS_TOKEN_EXPIRE_MINUTES = config.access_token_expire_minutes

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


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> UserProfile:
    """FastAPI dependency: resolve the caller to a UserProfile or raise 401.

    In `development` mode, if no token is supplied we return a stable mock
    profile so the frontend can be iterated on without standing up
    Postgres. In staging/production, a missing or invalid token is always
    401.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        if config.allow_mock_auth:
            return UserProfile(id="dev-user", email="dev@example.com")
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
