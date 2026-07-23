"""
Service layer for user interactions via the PostgreSQL connection pool.
"""
from typing import Optional, Dict, Any
from backend.data.postgres import get_db_connection, is_db_connected
from backend.core.auth import get_password_hash


def _normalize_email(email: str) -> str:
    """Canonicalize email for lookups and storage (case-insensitive auth)."""
    return email.strip().lower()


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user details and hashed password by email."""
    if not is_db_connected():
        return None

    email_norm = _normalize_email(email)
    sql = "SELECT id, email, password_hash, created_at FROM users WHERE LOWER(email) = %s"

    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (email_norm,))
            row = await cur.fetchone()
            
    if not row:
        return None
        
    return {
        "id": str(row[0]),
        "email": row[1],
        "password_hash": row[2],
        "created_at": row[3]
    }

async def create_user(email: str, plaintext_password: str) -> Optional[Dict[str, Any]]:
    """Create a new user by securely hashing their password prior to storage."""
    if not is_db_connected():
        return None

    email_norm = _normalize_email(email)
    hashed_pwd = get_password_hash(plaintext_password)

    sql = """
        INSERT INTO users (email, password_hash) 
        VALUES (%s, %s) 
        RETURNING id, email, created_at
    """

    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (email_norm, hashed_pwd))
            row = await cur.fetchone()
        await conn.commit()
    
    return {
        "id": str(row[0]) if row else None,
        "email": row[1] if row else email,
    }
