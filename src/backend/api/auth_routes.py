"""
Authentication API endpoints for registration and cookie session login.

Environment policy:
- The dev fallbacks (mint a session without hitting Postgres, accept any
  password) are only active when `config.app_env == 'development'`.
- In staging/production, if the database is unreachable we return 503
  instead of minting sessions. Startup would normally have aborted already
  (see `main.py` lifespan), but defense-in-depth: never let a running
  process issue credentials without a backing user record.

Session transport:
- POST /token sets httpOnly cookie `pem_session` (SameSite=Lax). The JWT
  is never returned in JSON.
- SameSite=None is forbidden; that would need a CSRF token.
"""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from backend.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    UserProfile,
    apply_session_cookie,
    clear_session_cookie,
    create_access_token,
    get_current_user,
    verify_password,
)
from backend.core.config import config
from backend.core.limiter import limiter
from backend.data.postgres import is_db_connected
from backend.services.user_service import create_user, get_user_by_email

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class SessionAck(BaseModel):
    ok: bool


def _db_unavailable_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication backend is unavailable.",
    )


def _mint_session(response: Response, subject: str) -> SessionAck:
    access_token = create_access_token(
        data={"sub": subject},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    apply_session_cookie(response, access_token)
    return SessionAck(ok=True)


@router.post("/register", response_model=UserProfile)
@limiter.limit("10/minute")
async def register(request: Request, user_in: UserCreate) -> Any:
    """Register a new user account."""
    if not is_db_connected():
        if config.allow_mock_auth:
            # Development-only: frontend can iterate without Postgres.
            return UserProfile(id="dev-fallback-id", email=user_in.email)
        raise _db_unavailable_response()

    existing_user = await get_user_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists.",
        )

    user = await create_user(user_in.email, user_in.password)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user.")
    return UserProfile(id=user["id"], email=user["email"])


@router.post("/token", response_model=SessionAck)
@limiter.limit("10/minute")
async def login_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    Form login — sets httpOnly `pem_session`. JWT is not in the JSON body.
    Expects application/x-www-form-urlencoded data (username = email).
    """
    if not is_db_connected():
        if config.allow_mock_auth:
            return _mint_session(response, form_data.username)
        raise _db_unavailable_response()

    user = await get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _mint_session(response, user["email"])


@router.post("/logout", response_model=SessionAck)
@limiter.limit("20/minute")
async def logout(request: Request, response: Response) -> SessionAck:
    """Clear the session cookie. Idempotent; does not require a valid session."""
    clear_session_cookie(response)
    return SessionAck(ok=True)


@router.get("/me", response_model=UserProfile)
@limiter.limit("30/minute")
async def read_current_user(
    request: Request,
    current_user: UserProfile = Depends(get_current_user),
) -> Any:
    """Get current logged in user."""
    return current_user
