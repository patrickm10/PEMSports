"""
Authentication API endpoints for registration and token login.

Environment policy:
- The dev fallbacks (mint a token without hitting Postgres, accept any
  password) are only active when `config.app_env == 'development'`.
- In staging/production, if the database is unreachable we return 503
  instead of minting tokens. Startup would normally have aborted already
  (see `main.py` lifespan), but defense-in-depth: never let a running
  process issue credentials without a backing user record.
"""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from backend.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    UserProfile,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from backend.core.config import config
from backend.data.postgres import is_db_connected
from backend.services.user_service import create_user, get_user_by_email

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


def _db_unavailable_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication backend is unavailable.",
    )


@router.post("/register", response_model=UserProfile)
async def register(user_in: UserCreate) -> Any:
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
            detail="The user with this email already exists."
        )

    user = await create_user(user_in.email, user_in.password)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user.")
    return UserProfile(id=user["id"], email=user["email"])


@router.post("/token", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login — returns a signed JWT for future requests.
    Expects application/x-www-form-urlencoded data.
    """
    if not is_db_connected():
        if config.allow_mock_auth:
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": form_data.username},
                expires_delta=access_token_expires,
            )
            return {"access_token": access_token, "token_type": "bearer"}
        raise _db_unavailable_response()

    user = await get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserProfile)
async def read_current_user(
    current_user: UserProfile = Depends(get_current_user)
) -> Any:
    """Get current logged in user."""
    return current_user
