"""
Authentication API endpoints for registration and token login.
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
    verify_password,
)
from backend.data.postgres import is_db_connected
from backend.services.user_service import create_user, get_user_by_email

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


@router.post("/register", response_model=UserProfile)
async def register(user_in: UserCreate) -> Any:
    """Register a new user account."""
    if not is_db_connected():
        # Fallback for dev mode without DB
        return UserProfile(id="dev-fallback-id", email=user_in.email)

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
    OAuth2 compatible token login, get an access token for future requests.
    Expects application/x-www-form-urlencoded data.
    """
    # ── Dev Fallback: Accept any login if DB is disconnected ──
    if not is_db_connected():
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

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
