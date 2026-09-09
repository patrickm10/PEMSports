"""
Authentication API endpoints for registration, token login, refresh, and logout.
"""
from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from backend.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    MIN_PASSWORD_LENGTH,
    REFRESH_COOKIE,
    UserProfile,
    clear_auth_cookies,
    create_access_token,
    csrf_header_matches,
    get_current_user,
    new_csrf_token,
    new_refresh_token,
    set_auth_cookies,
    verify_password,
)
from backend.core.config import config
from backend.core.limiter import limiter
from backend.data.postgres import is_db_connected
from backend.services.user_service import (
    create_user,
    get_user_by_email,
    revoke_refresh_token,
    rotate_refresh_token,
    store_refresh_token,
)

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class Token(BaseModel):
    access_token: str
    token_type: str


def _db_unavailable_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication backend is unavailable.",
    )


def _issue_session(response: Response, *, user_id: str, email: str) -> tuple[str, str]:
    access = create_access_token(
        data={"sub": user_id, "email": email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh = new_refresh_token()
    csrf = new_csrf_token()
    set_auth_cookies(response, access_token=access, refresh_token=refresh, csrf_token=csrf)
    return access, refresh


@router.post("/register", response_model=UserProfile)
@limiter.limit("5/minute")
async def register(request: Request, response: Response, user_in: UserCreate) -> Any:
    """Register a new user account."""
    if not is_db_connected():
        if config.allow_mock_auth:
            return UserProfile(id="dev-fallback-id", email=user_in.email, plan="premium")
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
    return UserProfile(
        id=user["id"],
        email=user["email"],
        plan=user.get("plan") or "free",
    )


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """OAuth2 password login — JWT in JSON and httpOnly cookies."""
    if not is_db_connected():
        if config.allow_mock_auth:
            access, refresh = _issue_session(
                response, user_id="dev-user", email=form_data.username
            )
            return {"access_token": access, "token_type": "bearer"}
        raise _db_unavailable_response()

    user = await get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access, refresh = _issue_session(
        response, user_id=user["id"], email=user["email"]
    )
    await store_refresh_token(user["id"], refresh)
    return {"access_token": access, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh_access_token(request: Request, response: Response) -> Any:
    if not csrf_header_matches(request):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="Missing refresh token.")

    if not is_db_connected():
        if config.allow_mock_auth:
            access, refresh = _issue_session(
                response, user_id="dev-user", email="dev@example.com"
            )
            return {"access_token": access, "token_type": "bearer"}
        raise _db_unavailable_response()

    user = await rotate_refresh_token(raw)
    if not user:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
    access, refresh = _issue_session(
        response, user_id=user["id"], email=user["email"]
    )
    await store_refresh_token(user["id"], refresh)
    return {"access_token": access, "token_type": "bearer"}


@router.post("/logout")
@limiter.limit("20/minute")
async def logout(request: Request, response: Response) -> dict[str, str]:
    if request.cookies.get(REFRESH_COOKIE) and not csrf_header_matches(request):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        await revoke_refresh_token(raw)
    clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=UserProfile)
async def read_current_user(
    current_user: UserProfile = Depends(get_current_user),
) -> Any:
    """Get current logged in user."""
    return current_user
