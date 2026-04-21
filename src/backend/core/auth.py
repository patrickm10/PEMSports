from datetime import timedelta
from typing import Optional
from pydantic import BaseModel

ACCESS_TOKEN_EXPIRE_MINUTES = 30

class UserProfile(BaseModel):
    id: str
    email: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Mock token generation for dev phase."""
    return "dev_token_123"

async def get_current_user() -> UserProfile:
    """Mock user retrieval for dev phase."""
    return UserProfile(id="dev-user", email="dev@example.com")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Mock password verification."""
    return True

def get_password_hash(password: str) -> str:
    """Mock password hash."""
    return "dev_hash"
